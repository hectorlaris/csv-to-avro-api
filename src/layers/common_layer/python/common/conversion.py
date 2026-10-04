"""Módulo de orquestación: coordina el flujo completo CSV → Avro."""

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any

from common import audit, avro_writer, s3_repository, validation

# ---------------------------------------------------------------------------
# Códigos de error de negocio
# ---------------------------------------------------------------------------
ERR_CSV_NOT_FOUND = "CSV_NOT_FOUND"
ERR_SCHEMA_NOT_FOUND = "SCHEMA_NOT_FOUND"
ERR_INVALID_SCHEMA = "INVALID_SCHEMA"


def _derive_schema_key(csv_key: str) -> str:
    """Deriva la clave del esquema a partir del nombre base del CSV.

    Por convención: datos/{base}.csv → schemas/{base}.json

    Args:
        csv_key: Clave S3 del CSV (p. ej. 'datos/alumnos.csv').

    Returns:
        Clave S3 del esquema (p. ej. 'schemas/alumnos.json').
    """
    base = csv_key.split("/")[-1].rsplit(".", 1)[0]
    return f"schemas/{base}.json"


def _date_suffix() -> str:
    """Retorna el sufijo de fecha en formato yyyymmdd para los nombres de archivo.

    Returns:
        Fecha actual en formato 'yyyymmdd'.
    """
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def _derive_output_keys(csv_key: str) -> tuple[str, str]:
    """Deriva las claves de salida Avro y log a partir del CSV.

    Args:
        csv_key: Clave S3 del CSV de entrada.

    Returns:
        Tupla (avro_key, log_key).
    """
    base = csv_key.split("/")[-1].rsplit(".", 1)[0]
    suffix = _date_suffix()
    return f"output/{base}_{suffix}.avro", f"logs/{base}_{suffix}.csv"


def _read_csv_rows(csv_key: str) -> list[dict[str, str]]:
    """Lee el CSV de S3 por streaming y retorna las filas como lista de dicts.

    Args:
        csv_key: Clave S3 del archivo CSV.

    Returns:
        Lista de dicts {columna: valor_string}.
    """
    buffer = io.StringIO()
    for chunk in s3_repository.read_object_stream(csv_key):
        buffer.write(chunk.decode("utf-8"))
    buffer.seek(0)
    reader = csv.DictReader(buffer)
    return list(reader)


def _load_schema(schema_key: str) -> dict[str, Any]:
    """Lee y parsea el esquema Avro desde S3.

    Args:
        schema_key: Clave S3 del esquema JSON.

    Returns:
        Esquema Avro como diccionario Python.

    Raises:
        ValueError: Si el JSON es inválido o no es un esquema Avro válido.
    """
    raw = s3_repository.read_object_bytes(schema_key)
    try:
        schema = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON inválido en el esquema: {exc}") from exc
    if not isinstance(schema, dict) or schema.get("type") != "record":
        raise ValueError("El esquema no define un record Avro válido.")
    return schema


def _build_log_csv(inconsistencies: list[dict]) -> bytes:
    """Genera el contenido del log de inconsistencias como bytes CSV.

    Args:
        inconsistencies: Lista de dicts con row, column, value, error.

    Returns:
        Bytes del archivo CSV de log.
    """
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=["row", "column", "value", "error"],
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(inconsistencies)
    return buffer.getvalue().encode("utf-8")


def run_conversion(
    audit_id: str,
    csv_key: str,
    schema_key: str | None = None,
) -> None:
    """Orquesta la conversión completa CSV → Avro para un auditId dado.

    Flujo:
      1. Verifica idempotencia: si el asiento ya está en estado final, retorna.
      2. Marca el asiento como PROCESSING.
      3. Verifica existencia de CSV y esquema en S3.
      4. Carga y valida el esquema.
      5. Lee el CSV por streaming y valida cada fila.
      6. Escribe el Avro (solo si hay filas válidas) y el log (siempre).
      7. Actualiza el asiento al estado final con contadores.

    Args:
        audit_id: Identificador único del asiento de auditoría.
        csv_key: Clave S3 del archivo CSV a convertir.
        schema_key: Clave S3 del esquema. Si es None, se deriva por convención.
    """
    # 1. Idempotencia: si ya finalizó, no reejecutar
    entry = audit.get_audit_entry(audit_id)
    if entry and entry.get("status") in (
        audit.STATUS_COMPLETED,
        audit.STATUS_NO_VALID_RECORDS,
        audit.STATUS_ERROR,
    ):
        return

    # Resolver schema_key por convención si no se proporcionó
    resolved_schema_key = schema_key or _derive_schema_key(csv_key)
    avro_key, log_key = _derive_output_keys(csv_key)

    # 2. Marcar como PROCESSING
    audit.update_audit_entry(audit_id, audit.STATUS_PROCESSING)

    # 3. Verificar existencia de archivos en S3
    if not s3_repository.object_exists(csv_key):
        audit.update_audit_entry(
            audit_id,
            audit.STATUS_ERROR,
            error=ERR_CSV_NOT_FOUND,
            message=f"El archivo '{csv_key}' no existe en el repositorio S3.",
        )
        return

    if not s3_repository.object_exists(resolved_schema_key):
        audit.update_audit_entry(
            audit_id,
            audit.STATUS_ERROR,
            error=ERR_SCHEMA_NOT_FOUND,
            message=f"El esquema '{resolved_schema_key}' no existe en el repositorio S3.",
        )
        return

    # 4. Cargar y validar el esquema
    try:
        schema = _load_schema(resolved_schema_key)
    except ValueError as exc:
        audit.update_audit_entry(
            audit_id,
            audit.STATUS_ERROR,
            error=ERR_INVALID_SCHEMA,
            message=str(exc),
        )
        return

    # 5. Leer CSV y validar filas
    rows = _read_csv_rows(csv_key)
    valid_rows, inconsistencies = validation.validate_rows(rows, schema)

    total_rows = len(rows)
    converted_rows = len(valid_rows)
    error_rows = len(inconsistencies)

    # 6. Escribir log de inconsistencias (siempre)
    log_bytes = _build_log_csv(inconsistencies)
    s3_repository.write_object(log_key, log_bytes, "text/csv")

    # 6b. Escribir Avro solo si hay registros válidos
    if not valid_rows:
        audit.update_audit_entry(
            audit_id,
            audit.STATUS_NO_VALID_RECORDS,
            log_key=log_key,
            total_rows=total_rows,
            converted_rows=0,
            error_rows=error_rows,
        )
        return

    avro_bytes = avro_writer.serialize_to_avro(valid_rows, schema)
    s3_repository.write_object(avro_key, avro_bytes, "application/avro")
    file_size = len(avro_bytes)

    # 7. Actualizar asiento a COMPLETED
    audit.update_audit_entry(
        audit_id,
        audit.STATUS_COMPLETED,
        avro_key=avro_key,
        log_key=log_key,
        total_rows=total_rows,
        converted_rows=converted_rows,
        error_rows=error_rows,
        file_size_bytes=file_size,
    )
