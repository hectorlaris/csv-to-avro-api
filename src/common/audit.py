"""Módulo de auditoría: lectura y escritura de asientos en DynamoDB."""

import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

import boto3

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
_TABLE_NAME: str = os.environ.get("AUDIT_TABLE", "")
_TTL_DAYS: int = int(os.environ.get("AUDIT_TTL_DAYS", "90"))

# Estados válidos del procesamiento
STATUS_PENDING = "PENDING"
STATUS_PROCESSING = "PROCESSING"
STATUS_COMPLETED = "COMPLETED"
STATUS_NO_VALID_RECORDS = "NO_VALID_RECORDS"
STATUS_ERROR = "ERROR"


def _table() -> object:
    """Retorna la referencia a la tabla DynamoDB de auditoría."""
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(_TABLE_NAME)


def _now_iso() -> str:
    """Retorna el timestamp actual en formato ISO-8601 UTC."""
    return datetime.now(timezone.utc).isoformat()


def _ttl_epoch() -> int:
    """Retorna el TTL como epoch Unix en segundos (ahora + _TTL_DAYS días)."""
    expiry = datetime.now(timezone.utc) + timedelta(days=_TTL_DAYS)
    return int(expiry.timestamp())


def create_audit_entry(
    csv_key: str,
    schema_key: str,
) -> str:
    """Crea un asiento de auditoría con estado PENDING y retorna el auditId.

    Args:
        csv_key: Clave S3 del archivo CSV a convertir.
        schema_key: Clave S3 del esquema Avro a aplicar.

    Returns:
        auditId generado (UUID v4).
    """
    audit_id = str(uuid.uuid4())
    now = _now_iso()

    item = {
        "auditId": audit_id,
        "status": STATUS_PENDING,
        "csvKey": csv_key,
        "schemaKey": schema_key,
        "createdAt": now,
        "updatedAt": now,
        "ttl": _ttl_epoch(),
    }

    _table().put_item(Item=item)
    return audit_id


def update_audit_entry(
    audit_id: str,
    status: str,
    avro_key: Optional[str] = None,
    log_key: Optional[str] = None,
    total_rows: Optional[int] = None,
    converted_rows: Optional[int] = None,
    error_rows: Optional[int] = None,
    file_size_bytes: Optional[int] = None,
    error: Optional[str] = None,
    message: Optional[str] = None,
) -> None:
    """Actualiza el estado y los campos opcionales de un asiento de auditoría.

    Args:
        audit_id: Identificador único del asiento.
        status: Nuevo estado del procesamiento.
        avro_key: Clave S3 del archivo Avro generado (puede ser None).
        log_key: Clave S3 del log de inconsistencias.
        total_rows: Total de filas procesadas.
        converted_rows: Filas convertidas exitosamente.
        error_rows: Filas con errores.
        file_size_bytes: Tamaño en bytes del archivo Avro generado.
        error: Código de error de negocio (CSV_NOT_FOUND, etc.).
        message: Mensaje descriptivo del error.
    """
    update_expr_parts = ["#st = :status", "updatedAt = :updated_at"]
    expr_names = {"#st": "status"}
    expr_values: dict = {
        ":status": status,
        ":updated_at": _now_iso(),
    }

    optional_fields = {
        "avroKey": avro_key,
        "logKey": log_key,
        "totalRows": total_rows,
        "convertedRows": converted_rows,
        "errorRows": error_rows,
        "fileSizeBytes": file_size_bytes,
        "error": error,
        "message": message,
    }

    for field, value in optional_fields.items():
        if value is not None:
            placeholder = f":{field}"
            update_expr_parts.append(f"{field} = {placeholder}")
            expr_values[placeholder] = value

    _table().update_item(
        Key={"auditId": audit_id},
        UpdateExpression="SET " + ", ".join(update_expr_parts),
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values,
    )


def get_audit_entry(audit_id: str) -> Optional[dict]:
    """Lee un asiento de auditoría por auditId.

    Args:
        audit_id: Identificador único del asiento.

    Returns:
        Diccionario con los atributos del asiento, o None si no existe.
    """
    response = _table().get_item(Key={"auditId": audit_id})
    return response.get("Item")
