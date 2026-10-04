"""Handler HTTP para POST /conversions y GET /conversions/{auditId}."""

import json
import os

import boto3

from src.common import audit, responses

# ---------------------------------------------------------------------------
# Constante
# ---------------------------------------------------------------------------
_WORKER_FUNCTION_NAME: str = os.environ.get("WORKER_FUNCTION_NAME", "")


def _invoke_worker(audit_id: str, csv_key: str, schema_key: str | None) -> None:
    """Invoca ConversionWorkerFunction de forma asíncrona (InvocationType=Event).

    Args:
        audit_id: Identificador del asiento de auditoría.
        csv_key: Clave S3 del archivo CSV a convertir.
        schema_key: Clave S3 del esquema (puede ser None).
    """
    payload: dict = {"auditId": audit_id, "csvKey": csv_key}
    if schema_key:
        payload["schemaKey"] = schema_key

    boto3.client("lambda").invoke(
        FunctionName=_WORKER_FUNCTION_NAME,
        InvocationType="Event",
        Payload=json.dumps(payload),
    )


def _handle_post(body: dict) -> dict:
    """Procesa POST /conversions.

    Valida el body, crea el asiento PENDING e invoca el worker async.

    Args:
        body: Cuerpo JSON del request ya deserializado.

    Returns:
        Respuesta HTTP 202 o 400.
    """
    csv_key: str | None = body.get("csvKey")
    if not csv_key:
        return responses.bad_request("El campo 'csvKey' es obligatorio.")

    schema_key: str | None = body.get("schemaKey")

    audit_id = audit.create_audit_entry(csv_key, schema_key or "")
    _invoke_worker(audit_id, csv_key, schema_key)

    status_url = f"/conversions/{audit_id}"
    return responses.accepted(audit_id, status_url)


def _handle_get(audit_id: str) -> dict:
    """Procesa GET /conversions/{auditId}.

    Lee el asiento y construye la respuesta según el estado actual.

    Args:
        audit_id: Identificador del asiento a consultar.

    Returns:
        Respuesta HTTP 200 o 404.
    """
    entry = audit.get_audit_entry(audit_id)
    if entry is None:
        return responses.not_found(audit_id)

    status = entry.get("status", "")

    if status in (audit.STATUS_PENDING, audit.STATUS_PROCESSING):
        return responses.ok_pending(audit_id, status)

    if status == audit.STATUS_COMPLETED:
        return responses.ok_completed(
            audit_id=audit_id,
            avro_key=entry.get("avroKey", ""),
            log_key=entry.get("logKey", ""),
            total_rows=entry.get("totalRows", 0),
            converted_rows=entry.get("convertedRows", 0),
            error_rows=entry.get("errorRows", 0),
            file_size_bytes=entry.get("fileSizeBytes", 0),
        )

    if status == audit.STATUS_NO_VALID_RECORDS:
        return responses.ok_no_valid_records(
            audit_id=audit_id,
            log_key=entry.get("logKey", ""),
            total_rows=entry.get("totalRows", 0),
            error_rows=entry.get("errorRows", 0),
        )

    if status == audit.STATUS_ERROR:
        return responses.ok_error(
            audit_id=audit_id,
            error=entry.get("error", "UNKNOWN_ERROR"),
            message=entry.get("message", "Error desconocido."),
        )

    return responses.bad_request(f"Estado desconocido: '{status}'.")


def lambda_handler(event: dict, context: object) -> dict:
    """Punto de entrada del handler Lambda para la API REST.

    Enruta entre POST /conversions y GET /conversions/{auditId}.
    No contiene lógica de negocio: delega completamente en src/common/.

    Args:
        event: Evento de API Gateway con httpMethod, path y body.
        context: Contexto de ejecución Lambda (no utilizado).

    Returns:
        Respuesta HTTP compatible con API Gateway.
    """
    http_method: str = event.get("httpMethod", "")
    path: str = event.get("path", "")

    # POST /conversions
    if http_method == "POST" and path == "/conversions":
        raw_body = event.get("body") or "{}"
        try:
            body = json.loads(raw_body)
        except (json.JSONDecodeError, TypeError):
            return responses.bad_request("El body no es JSON válido.")
        return _handle_post(body)

    # GET /conversions/{auditId}
    if http_method == "GET" and path.startswith("/conversions/"):
        audit_id = path.split("/conversions/", 1)[1].strip("/")
        if not audit_id:
            return responses.bad_request("auditId no puede estar vacío.")
        return _handle_get(audit_id)

    return responses.bad_request(f"Ruta no soportada: {http_method} {path}.")
