---
name: csi-standards
description: Estándares técnicos del equipo CSI para el proyecto Avro REST API Gateway (stack serverless, estructura por capas, diseño de la API, manejo de errores). Úsala al diseñar, implementar o revisar cualquier cambio en el repo.
---

# Estándares técnicos CSI

Proyecto serverless en AWS que convierte CSV (en S3) a Apache Avro de forma asíncrona, con validación contra esquema, log de inconsistencias y auditoría en DynamoDB. Runtime Python 3.12, IaC con AWS SAM.

Lee la referencia que aplique antes de diseñar, implementar o revisar:

| Tema | Referencia | Cuándo |
|---|---|---|
| Stack, runtime, librerías y calidad de código | `references/tech.md` | Siempre |
| Estructura de carpetas y separación en capas | `references/structure.md` | Al crear o mover archivos |
| Diseño de la REST API (endpoints, estados, respuestas) | `references/api-standards.md` | Al tocar los handlers o la API |
| Manejo de errores e idempotencia del worker | `references/error-handling.md` | En el flujo asíncrono y los errores de negocio |

## Reglas de oro

1. **Separa negocio de handlers.** La lógica (validación + serialización Avro) vive en `src/common/` y no conoce API Gateway ni el mecanismo de invocación. Los handlers (`api_handler/`, `conversion_worker/`) adaptan el evento, delegan en `common/` y arman la respuesta/estado. Así `common/` es testeable de forma aislada.
2. **Solo datos válidos en el Avro.** Un registro entra al Avro únicamente si pasa tipos, enums, nulos y `qualityRules`. Los inconsistentes se excluyen y se reportan en el log con fila y columna.
3. **Nada silencioso.** Toda ejecución produce log de inconsistencias y asiento de auditoría, incluso cuando no hay registros válidos (`NO_VALID_RECORDS`).
4. **Respuestas predecibles.** JSON UTF-8 (`Content-Type: application/json; charset=utf-8`), omitiendo campos nulos salvo `avroKey`, que se retorna como `null` explícito.
5. **El worker es idempotente respecto al `auditId`.** Los reintentos de invocación asíncrona no deben duplicar ni corromper el estado.
6. **Perfil y región fijos.** Todo comando de AWS CLI y SAM CLI usa `--profile developer` y `--region us-east-1`.
7. **Si un estándar choca con el requerimiento, no lo ignores en silencio:** explica el conflicto y propón la decisión (p. ej. una entrada en Decisiones técnicas del `design.md`).

Cita la regla que justifica cada decisión o comentario de revisión (p. ej. `tech > Calidad de código`, `api-standards > Estados`, `error-handling > Idempotencia`).
