# error-handling — Errores de negocio e idempotencia

## Códigos de error de negocio

| Código | Causa | Dónde se detecta |
|---|---|---|
| `CSV_NOT_FOUND` | El objeto `csvKey` no existe en S3 | Worker, al resolver archivos |
| `SCHEMA_NOT_FOUND` | El esquema (por `schemaKey` o convención) no existe en S3 | Worker, al resolver archivos |
| `INVALID_SCHEMA` | El JSON del esquema no parsea / no es un esquema Avro válido | Worker, al cargar el esquema |

## Dónde se refleja cada error

- **Validación del request (síncrona)**: solo `400` en el `POST` (falta `csvKey`, JSON mal formado). No toca el worker.
- **Errores de procesamiento (asíncronos)**: se registran en el asiento de auditoría con `status=ERROR`, `error=<código>` y `message` descriptivo. El cliente los descubre vía `GET /conversions/{auditId}` (que responde `200` con el asiento en estado `ERROR`).
- Nunca se pierde un error en silencio: todo fallo del worker queda en la auditoría.

## Separación de inconsistencias vs. errores

- **Inconsistencia de dato** (una fila que no cumple el esquema o `qualityRules`): no es un error de ejecución. La fila se excluye del Avro y se anota en el log con `row`, `column`, `value`, `error`. El proceso continúa.
- **Error de negocio** (`CSV_NOT_FOUND`, etc.): detiene la conversión y cierra el asiento como `ERROR`.
- Si **ninguna** fila es válida pero el proceso corrió bien, el estado final es `NO_VALID_RECORDS` (no `ERROR`): se omite el Avro pero se escribe el log.

## Idempotencia del worker

Las invocaciones asíncronas (`InvocationType=Event`) **reintentan ante fallo**. El worker debe ser idempotente respecto al `auditId`:

- Reprocesar un `auditId` no debe duplicar asientos ni corromper el estado.
- La salida se sobrescribe de forma determinista: `output/{nombre}_{yyyymmdd}.avro` y `logs/{nombre}_{yyyymmdd}.csv` para el mismo CSV el mismo día.
- Conviene una DLQ (dead-letter queue) para diagnosticar invocaciones que agotan reintentos.

## Al escribir código de errores

- Mensajes en español, descriptivos y accionables (indicar la clave S3 afectada cuando aplique).
- No incluir secretos ni datos personales en mensajes ni logs.
- Validar la entrada antes de usarla; no confiar en el cuerpo del request.
