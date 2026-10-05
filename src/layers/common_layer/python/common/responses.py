"""Módulo de construcción de respuestas HTTP JSON UTF-8 para la API."""

import json
from decimal import Decimal
from typing import Any

# ---------------------------------------------------------------------------
# Constante de cabecera
# ---------------------------------------------------------------------------
_CONTENT_TYPE = "application/json; charset=utf-8"


class _DecimalEncoder(json.JSONEncoder):
    """Encoder JSON que serializa los Decimal de DynamoDB como int o float."""

    def default(self, o: Any) -> Any:
        """Convierte Decimal a int (si es entero) o float; delega el resto."""
        if isinstance(o, Decimal):
            return int(o) if o % 1 == 0 else float(o)
        return super().default(o)


def _build(status_code: int, body: dict[str, Any]) -> dict:
    """Construye la respuesta Lambda/API Gateway omitiendo campos nulos.

    La única excepción es `avroKey`, que puede incluirse como null explícito
    cuando el estado es NO_VALID_RECORDS (señal de que no se generó Avro).

    Args:
        status_code: Código HTTP de la respuesta.
        body: Diccionario con el cuerpo de la respuesta.

    Returns:
        Dict compatible con el formato de respuesta de API Gateway.
    """
    avro_key_value = body.pop("avroKey", _SENTINEL)
    cleaned = {k: v for k, v in body.items() if v is not None}

    if avro_key_value is not _SENTINEL:
        cleaned["avroKey"] = avro_key_value  # preserva None explícito

    return {
        "statusCode": status_code,
        "headers": {"Content-Type": _CONTENT_TYPE},
        "body": json.dumps(cleaned, ensure_ascii=False, cls=_DecimalEncoder),
    }


# Centinela interno para distinguir "no se pasó avroKey" de "se pasó None"
_SENTINEL = object()


def accepted(audit_id: str, status_url: str) -> dict:
    """Respuesta 202 Accepted para POST /conversions.

    Args:
        audit_id: Identificador único del asiento creado.
        status_url: URL relativa para consultar el estado.

    Returns:
        Respuesta HTTP 202 con auditId, status PENDING y statusUrl.
    """
    return _build(
        202,
        {
            "status": "PENDING",
            "auditId": audit_id,
            "statusUrl": status_url,
        },
    )


def ok_pending(audit_id: str, status: str) -> dict:
    """Respuesta 200 OK para estados PENDING o PROCESSING.

    Args:
        audit_id: Identificador único del asiento.
        status: Estado actual del procesamiento.

    Returns:
        Respuesta HTTP 200 con auditId y status.
    """
    return _build(200, {"status": status, "auditId": audit_id})


def ok_completed(
    audit_id: str,
    avro_key: str,
    log_key: str,
    total_rows: int,
    converted_rows: int,
    error_rows: int,
    file_size_bytes: int,
) -> dict:
    """Respuesta 200 OK para estado COMPLETED.

    Args:
        audit_id: Identificador único del asiento.
        avro_key: Clave S3 del archivo Avro generado.
        log_key: Clave S3 del log de inconsistencias.
        total_rows: Total de filas procesadas.
        converted_rows: Filas convertidas exitosamente.
        error_rows: Filas con errores.
        file_size_bytes: Tamaño del Avro en bytes.

    Returns:
        Respuesta HTTP 200 con todos los campos de resultado.
    """
    return _build(
        200,
        {
            "status": "COMPLETED",
            "auditId": audit_id,
            "avroKey": avro_key,
            "logKey": log_key,
            "totalRows": total_rows,
            "convertedRows": converted_rows,
            "errorRows": error_rows,
            "fileSizeBytes": file_size_bytes,
        },
    )


def ok_no_valid_records(
    audit_id: str,
    log_key: str,
    total_rows: int,
    error_rows: int,
) -> dict:
    """Respuesta 200 OK para estado NO_VALID_RECORDS.

    avroKey se incluye como null explícito (señal de que no se generó Avro).

    Args:
        audit_id: Identificador único del asiento.
        log_key: Clave S3 del log de inconsistencias.
        total_rows: Total de filas procesadas.
        error_rows: Filas con errores (igual a total_rows en este caso).

    Returns:
        Respuesta HTTP 200 con avroKey: null explícito.
    """
    return _build(
        200,
        {
            "status": "NO_VALID_RECORDS",
            "auditId": audit_id,
            "avroKey": None,
            "logKey": log_key,
            "totalRows": total_rows,
            "convertedRows": 0,
            "errorRows": error_rows,
        },
    )


def ok_error(audit_id: str, error: str, message: str) -> dict:
    """Respuesta 200 OK para estado ERROR.

    Args:
        audit_id: Identificador único del asiento.
        error: Código de error de negocio (CSV_NOT_FOUND, etc.).
        message: Mensaje descriptivo del error.

    Returns:
        Respuesta HTTP 200 con código y mensaje de error.
    """
    return _build(
        200,
        {
            "status": "ERROR",
            "auditId": audit_id,
            "error": error,
            "message": message,
        },
    )


def bad_request(message: str) -> dict:
    """Respuesta 400 Bad Request.

    Args:
        message: Descripción del error de validación.

    Returns:
        Respuesta HTTP 400 con mensaje de error.
    """
    return _build(400, {"error": "BAD_REQUEST", "message": message})


def not_found(audit_id: str) -> dict:
    """Respuesta 404 Not Found para auditId inexistente.

    Args:
        audit_id: Identificador que no existe en la tabla.

    Returns:
        Respuesta HTTP 404 con mensaje descriptivo.
    """
    return _build(
        404,
        {
            "error": "NOT_FOUND",
            "message": f"No existe un proceso con auditId '{audit_id}'.",
        },
    )
