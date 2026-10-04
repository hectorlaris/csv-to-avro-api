"""Handler invocado por evento para la conversión asíncrona CSV → Avro."""

from src.common import conversion


def lambda_handler(event: dict, context: object) -> None:
    """Punto de entrada del worker Lambda invocado de forma asíncrona.

    Lee auditId, csvKey y schemaKey del evento y delega la conversión
    completa en conversion.run_conversion(). La idempotencia respecto
    al auditId está implementada en run_conversion.

    No contiene lógica de negocio: delega completamente en src/common/.

    Args:
        event: Evento con auditId, csvKey y schemaKey opcional.
        context: Contexto de ejecución Lambda (no utilizado).
    """
    audit_id: str = event["auditId"]
    csv_key: str = event["csvKey"]
    schema_key: str | None = event.get("schemaKey")

    conversion.run_conversion(audit_id, csv_key, schema_key)
