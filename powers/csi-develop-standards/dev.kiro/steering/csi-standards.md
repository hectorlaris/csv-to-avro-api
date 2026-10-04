# CSI — Reglas de oro

Resumen operativo del equipo CSI para el proyecto Avro REST API Gateway. Para el detalle, abre la skill `csi-standards` (`readSkill`) y sus referencias. Lee esto antes de diseñar, implementar o revisar.

## Arquitectura y stack

- Serverless en AWS: API Gateway (REST) + Lambda (Python 3.12) + S3 + DynamoDB. IaC con AWS SAM.
- Procesamiento **asíncrono**: el `POST` acepta y delega; el worker convierte; el estado se consulta por `GET`.
- Todo comando de AWS CLI / SAM CLI usa `--profile developer` y `--region us-east-1`.

## Diseño del código

- Separa **negocio** (`src/common/`) de **handlers** (`src/api_handler/`, `src/conversion_worker/`). El negocio no conoce API Gateway ni el mecanismo de invocación.
- Calidad Python: 4 espacios, docstrings, type hints, f-strings, funciones < 30 líneas.
- Dependencias fijadas (pinned) en el `requirements.txt` de cada Lambda.

## Comportamiento del sistema

- **Solo datos válidos en el Avro**: un registro entra solo si pasa tipos, enums, nulos y `qualityRules`.
- **Nada silencioso**: cada ejecución produce log de inconsistencias y asiento de auditoría, incluso sin registros válidos (`NO_VALID_RECORDS`).
- **Respuestas predecibles**: JSON UTF-8, omitiendo nulos salvo `avroKey` (null explícito).
- **Worker idempotente** respecto al `auditId`: los reintentos no duplican ni corrompen estado.
- Errores de negocio: `CSV_NOT_FOUND`, `SCHEMA_NOT_FOUND`, `INVALID_SCHEMA`, registrados en el asiento como `status=ERROR`.

## Flujo de trabajo

- Antes de implementar una feature, hay spec (`requirements` → `design` → `tasks`). Usa la skill `spec-authoring`.
- Fundamenta decisiones de diseño con el MCP `aws-docs` y estima costo con `aws-pricing`.
- Para diagramas de arquitectura, usa la skill `drawio-architecture` y el steering `diagram-rules.md`.

## Regla de conflicto

Si un estándar choca con un requerimiento, no lo ignores en silencio: explica el conflicto y propón la decisión (p. ej. en la sección Decisiones técnicas del `design.md`). Cita la regla que respalda cada decisión o comentario de revisión.
