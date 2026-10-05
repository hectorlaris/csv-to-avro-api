# Plan de Tareas — Avro REST API Gateway

> Plan incremental de implementación derivado de `requirements.md` y `design.md`.
> Orden: andamiaje → lógica de negocio → handlers → pruebas de handlers → verificación integral.
> Decisiones de planificación: una tarea por módulo de `src/common/`; prueba al cierre de cada módulo; T-04 entregada en Mermaid (`.drawio` canónico pendiente del binario `aim`).
> Ver decisiones de planificación en `Documents/plan-de-trabajo.md`.

---

## Grupo A — Andamiaje e infraestructura SAM

- [x] **T-01** — Crear `template.yaml` con todos los recursos AWS: bucket S3 (privado, sin acceso público), REST API en API Gateway (`POST /conversions` y `GET /conversions/{auditId}`), `ApiFunction` (Lambda Python 3.12), `ConversionWorkerFunction` (Lambda Python 3.12, invocación asíncrona), tabla DynamoDB on-demand con partition key `auditId` y TTL habilitado sobre el atributo `ttl`, cola SQS como DLQ del worker, y roles IAM con privilegios mínimos para cada función.
  _Requerimientos: R5.1, R5.2, R6.1, R6.2, R6.3_

- [x] **T-02** — Crear `samconfig.toml` con el perfil `AdministratorAccess-962682390364`, región `us-east-1` y los parámetros de despliegue (`stack_name`, `s3_prefix`, `capabilities = CAPABILITY_IAM CAPABILITY_NAMED_IAM`).
  _Requerimientos: R6.5_

- [x] **T-03** — Crear `src/api_handler/requirements.txt` y `src/conversion_worker/requirements.txt` con versiones fijadas (pinned): `fastavro`, y cualquier dependencia adicional requerida. `boto3` no se declara (incluido en el runtime de Lambda).
  _Requerimientos: R5.1_

- [x] **T-04** — Diagrama de arquitectura entregado en **Mermaid** como alternativa práctica: `Documents/avro-rest-api-gateway-arquitectura.md` (componentes + flujo numerado 1-8, diagrama de estados y leyenda). El entregable canónico `.drawio` con el MCP `drawio-architect` queda pendiente (requiere el binario `aim`), sin bloquear el proyecto.
  _Requerimientos: —_

---

## Grupo B — Módulos de lógica de negocio (`src/common/`)

> Cada tarea tiene dos pasos: (1) implementar el módulo y (2) escribir y pasar su test unitario antes de cerrar la tarea. El hook `py-test-for-new-module.json` lo recuerda automáticamente al crear cada archivo en `src/common/`.

- [x] **T-05** — `src/common/audit.py`
  1. Implementar las funciones `create_audit_entry`, `update_audit_entry` y `get_audit_entry` sobre DynamoDB. El atributo `ttl` debe ser de tipo `Number` en epoch Unix en segundos. Los timestamps `createdAt` y `updatedAt` en ISO-8601.
  2. Escribir `tests/test_audit.py`: verificar creación del asiento con estado `PENDING`, actualización a `PROCESSING` / `COMPLETED` / `ERROR`, lectura por `auditId` y manejo de `auditId` inexistente.
  _Requerimientos: R4.1, R4.2, R6.3, R7.1, R9_

- [x] **T-06** — `src/common/s3_repository.py`
  1. Implementar las funciones `object_exists`, `read_object_stream`, `write_object` y `get_object_size`. El acceso al bucket es exclusivamente por IAM; ninguna función genera URLs públicas.
  2. Escribir `tests/test_s3_repository.py`: verificar existencia de objeto presente y ausente, lectura por streaming, escritura y obtención de tamaño; usar mocks de `boto3`.
  _Requerimientos: R1.1, R1.2, R2.3, R2.4, R6.2_

- [x] **T-07** — `src/common/validation.py`
  1. Implementar la validación fila por fila del CSV contra el esquema Avro: tipos de dato, valores fuera de enumeraciones, campos nulos no permitidos e incumplimiento de `qualityRules`. Retornar dos listas: filas válidas y lista de inconsistencias con `row`, `column`, `value`, `error`.
  2. Escribir `tests/test_validation.py`: caso con todas las filas válidas, caso con tipo incorrecto, caso con valor fuera de enumeración, caso con campo nulo no permitido, caso con incumplimiento de `qualityRules`, caso con todas las filas inválidas.
  _Requerimientos: R2.1, R2.2_

- [x] **T-08** — `src/common/avro_writer.py`
  1. Implementar la serialización de una lista de registros válidos a formato Avro usando `fastavro`. Retornar un buffer `BytesIO` listo para escribir en S3. El esquema se recibe como diccionario Python ya parseado.
  2. Escribir `tests/test_avro_writer.py`: serialización de uno o más registros, verificar que el buffer resultante es un Avro válido con `fastavro.reader`.
  _Requerimientos: R2.4_

- [x] **T-09** — `src/common/conversion.py`
  1. Implementar la orquestación completa CSV→Avro: lectura del CSV por streaming con el módulo estándar `csv`, resolución del esquema por convención de nombre (`datos/{base}.csv` ↔ `schemas/{base}.json`) con override por `schemaKey`, llamada a `validation.py`, llamada a `avro_writer.py`, escritura de `output/{base}_{yyyymmdd}.avro` (solo si hay ≥1 fila válida) y `logs/{base}_{yyyymmdd}.csv` (siempre), e idempotencia: si el asiento ya está en estado final (`COMPLETED`, `NO_VALID_RECORDS`, `ERROR`) no reejecutar.
  2. Escribir `tests/test_conversion.py`: flujo completo con registros mixtos (válidos e inválidos), caso sin ningún registro válido (estado `NO_VALID_RECORDS`, sin Avro), caso de reintento sobre `auditId` ya finalizado (idempotencia), caso `CSV_NOT_FOUND`, caso `SCHEMA_NOT_FOUND`, caso `INVALID_SCHEMA`.
  _Requerimientos: R1.3, R1.4, R2.1, R2.2, R2.3, R2.4, R8.1, R8.2, R8.3, R9.1, R9.2, R9.3_

- [x] **T-10** — `src/common/responses.py`
  1. Implementar los constructores de respuestas JSON UTF-8 para cada estado del procesamiento: `202 Accepted` (POST), `200 OK` con cuerpo según estado (`PENDING`, `PROCESSING`, `COMPLETED`, `NO_VALID_RECORDS`, `ERROR`), `400 Bad Request` y `404 Not Found`. Omitir campos nulos salvo `avroKey`, que se incluye como `null` explícito en `NO_VALID_RECORDS`. Siempre incluir `Content-Type: application/json; charset=utf-8`.
  2. Escribir `tests/test_responses.py`: verificar el cuerpo y los headers de cada tipo de respuesta; verificar que los campos nulos se omiten salvo `avroKey`.
  _Requerimientos: R3.1, R3.2, R3.3_

---

## Grupo C — Handlers Lambda

- [x] **T-11** — `src/api_handler/app.py`
  1. Implementar el handler HTTP con dos rutas:
     - `POST /conversions`: validar que `csvKey` está presente en el body JSON (→ `400` si no); generar `auditId` (UUID); delegar en `audit.py` para crear el asiento `PENDING`; invocar `ConversionWorkerFunction` con `InvocationType=Event` pasando `{ auditId, csvKey, schemaKey }`; responder `202` usando `responses.py`.
     - `GET /conversions/{auditId}`: leer el asiento con `audit.py`; responder `404` si no existe; responder `200` con el cuerpo correspondiente al estado actual usando `responses.py`.
  2. Verificar que ninguna lógica de negocio reside en el handler: toda validación, serialización y acceso a datos se delega a `src/common/`.
  _Requerimientos: R3.1, R3.2, R3.3, R7.1, R7.2, R7.3, R7.4, R7.5, R7.6, R9.4_

- [x] **T-12** — `src/conversion_worker/app.py`
  1. Implementar el handler invocado por evento: leer `auditId`, `csvKey` y `schemaKey` del evento; verificar idempotencia consultando el asiento con `audit.py` (si ya está en estado final, retornar sin reejecutar); marcar `PROCESSING`; llamar a `conversion.py`; actualizar el asiento al estado final (`COMPLETED`, `NO_VALID_RECORDS` o `ERROR`) con los contadores y `fileSizeBytes`.
  2. Verificar que ninguna lógica de negocio reside en el handler: toda validación, serialización y acceso a datos se delega a `src/common/`.
  _Requerimientos: R8.1, R8.2, R8.3, R9.1, R9.2, R9.3_

---

## Grupo D — Pruebas de integración de handlers

- [x] **T-13** — `tests/test_api_handler.py`
  1. Escribir pruebas de integración del handler HTTP con mocks de DynamoDB y Lambda:
     - `POST` con `csvKey` presente → `202` con `auditId` y `status: PENDING`.
     - `POST` sin `csvKey` → `400` con mensaje descriptivo.
     - `POST` con body malformado → `400`.
     - `GET` con `auditId` en estado `PENDING` → `200` con estado.
     - `GET` con `auditId` en estado `PROCESSING` → `200` con estado.
     - `GET` con `auditId` en estado `COMPLETED` → `200` con `avroKey`, `logKey` y contadores.
     - `GET` con `auditId` en estado `NO_VALID_RECORDS` → `200` con `avroKey: null` explícito.
     - `GET` con `auditId` en estado `ERROR` → `200` con código de error y mensaje.
     - `GET` con `auditId` inexistente → `404`.
  _Requerimientos: R3.1, R3.2, R3.3, R7.1, R7.2, R7.3, R7.4, R7.5, R7.6, R9.4_

---

## Grupo E — Verificación integral

- [x] **T-14** — Ejecutar `sam build` y `sam validate --profile AdministratorAccess-962682390364 --region us-east-1 --lint`. Corregir cualquier error de la plantilla hasta que la validación pase sin advertencias.
  _Requerimientos: R6.1, R6.4, R6.5_

- [x] **T-15** — Ejecutar `pytest` completo. Confirmar que todos los tests de los Grupos B y D pasan. Revisar que los casos críticos de idempotencia (R8) y errores de negocio (R9) están cubiertos.
  _Requerimientos: R1–R9_

- [x] **T-16** — Ejecutar `black .` y `ruff check .`. Corregir cualquier advertencia de formato o linting hasta obtener salida limpia.
  _Requerimientos: —_
