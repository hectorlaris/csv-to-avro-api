# Avro REST API Gateway

Solución **serverless** en AWS que expone una **REST API** para convertir archivos **CSV**
alojados en Amazon S3 a formato **Apache Avro**, aplicando un esquema personalizado en JSON
y reglas de calidad (`qualityRules`). El procesamiento es **asíncrono**: el cliente solicita
la conversión, recibe un identificador de seguimiento y consulta el estado por sondeo (polling).

Automatiza un proceso que antes era manual, validando cada registro contra su esquema,
excluyendo los inconsistentes, generando un log de errores y dejando auditoría de cada ejecución.

## Características

- **Validación contra esquema Avro**: tipos de dato, enumeraciones, campos nulos y `qualityRules`.
- **Solo datos válidos en el Avro**: los registros inconsistentes se excluyen y se reportan.
- **Nada silencioso**: cada ejecución produce log de inconsistencias y asiento de auditoría.
- **Procesamiento asíncrono e idempotente**: el worker tolera reintentos sin duplicar ni corromper estado.
- **Respuestas predecibles**: JSON UTF-8, omitiendo campos nulos (salvo `avroKey`).
- **100% serverless**: escalado automático y pago por uso, sin administrar servidores.

## Arquitectura

```
Cliente ──POST /conversions──► API Gateway ──► ApiFunction ──(async)──► ConversionWorkerFunction
   │                                               │                            │
   └──GET /conversions/{id}──► API Gateway ────────┘              ┌─────────────┼─────────────┐
                                                                  ▼             ▼             ▼
                                                            S3 (datos/      DynamoDB      SQS (DLQ)
                                                         schemas/output/     (auditoría
                                                              logs)          + TTL)
```

El flujo numerado (1 = `POST`, 8 = `GET`) y los estados del procesamiento se detallan en la
sección [API](#api) y en el diseño ([`.kiro/specs/design.md`](.kiro/specs/design.md)).

| Componente | Servicio AWS | Rol |
|---|---|---|
| REST API | API Gateway (REST) | Expone `POST /conversions` y `GET /conversions/{auditId}` |
| `ApiFunction` | Lambda (Python 3.12) | Valida el request, crea el asiento `PENDING`, invoca el worker async, responde `202`; en `GET` lee el asiento |
| `ConversionWorkerFunction` | Lambda (Python 3.12) | Invocada por evento; resuelve CSV/esquema, valida, serializa Avro, escribe log y actualiza el asiento |
| Repositorio oficial | Amazon S3 | Única fuente de verdad: prefijos `datos/`, `schemas/`, `output/`, `logs/` |
| Auditoría | DynamoDB (on-demand, TTL) | Estado y resumen del proceso por `auditId` |
| DLQ | Amazon SQS | Captura invocaciones del worker que agotan reintentos |
| Lógica compartida | Lambda Layer | Negocio reutilizado por ambas funciones (`common/`) |

## API

Siempre `Content-Type: application/json; charset=utf-8`. Se omiten campos nulos salvo `avroKey`.

### `POST /conversions` → `202 Accepted`

```json
{ "csvKey": "datos/alumnos.csv", "schemaKey": "schemas/alumnos.json" }
```

- `csvKey` (obligatorio): clave S3 del CSV.
- `schemaKey` (opcional): si se omite, se resuelve por convención (`datos/{base}.csv` ↔ `schemas/{base}.json`).

Respuesta:
```json
{ "status": "PENDING", "auditId": "a1b2c3d4-...", "statusUrl": "/conversions/a1b2c3d4-..." }
```
`400` si falta `csvKey` o el JSON está mal formado.

### `GET /conversions/{auditId}` → `200 OK` / `404 Not Found`

Respuesta según estado:
- **PENDING / PROCESSING**: `{ "status": "...", "auditId": "..." }`
- **COMPLETED**: incluye `avroKey`, `logKey`, `totalRows`, `convertedRows`, `errorRows`, `fileSizeBytes`
- **NO_VALID_RECORDS**: `avroKey: null` explícito, con `logKey` y contadores
- **ERROR**: incluye `error` (código de negocio) y `message`

### Estados

```
PENDING ──► PROCESSING ──► COMPLETED | NO_VALID_RECORDS | ERROR
```

### Códigos de error de negocio

| Código | Causa |
|---|---|
| `CSV_NOT_FOUND` | `csvKey` no existe en `datos/` |
| `SCHEMA_NOT_FOUND` | Esquema no existe en `schemas/` |
| `INVALID_SCHEMA` | El esquema no es un JSON válido o no define un esquema Avro |

## Stack tecnológico

- **Runtime**: Python 3.12
- **Serialización Avro**: `fastavro` (sin JVM)
- **SDK AWS**: `boto3` (incluido en el runtime de Lambda)
- **IaC**: AWS SAM
- **Pruebas**: `pytest` · **Formato/lint**: `black`, `ruff`

## Estructura del proyecto

```
csv-to-avro-api/
├── template.yaml                 # Plantilla SAM: todos los recursos AWS
├── samconfig.toml                # Config de despliegue (ignorado en git)
├── src/
│   ├── api_handler/app.py        # Handler HTTP (POST/GET)
│   ├── conversion_worker/app.py  # Handler del worker asíncrono
│   └── layers/common_layer/      # Lambda Layer con la lógica de negocio
│       └── python/common/
│           ├── conversion.py     # Orquestación CSV→Avro
│           ├── validation.py     # Validación contra esquema + qualityRules
│           ├── avro_writer.py    # Serialización Avro (fastavro)
│           ├── audit.py          # Lectura/escritura del asiento (DynamoDB)
│           ├── s3_repository.py  # Acceso al bucket
│           └── responses.py      # Respuestas JSON UTF-8
├── tests/                        # Pruebas unitarias + fixtures e2e
├── infra/oidc/                   # Rol y policies OIDC del pipeline
├── .github/workflows/ci-cd.yml   # Pipeline CI/CD
└── .kiro/specs/                  # requirements.md · design.md · tasks.md
```

La **lógica de negocio** (`common/`) está separada de los **handlers**, de modo que es
testeable de forma aislada e independiente del mecanismo de invocación.

## Desarrollo local

Requisitos: Python 3.12, AWS SAM CLI, Docker (para `sam local`), y un perfil AWS configurado.

```bash
# Instalar herramientas de calidad y dependencias
pip install black==24.10.0 ruff==0.9.10 pytest==9.0.2 fastavro==1.12.2 boto3

# Pruebas
pytest

# Formato y linting
black .
ruff check .

# Validar la plantilla SAM
sam validate --lint --profile <PERFIL> --region us-east-1

# Build e invocación local (requiere Docker)
sam build
sam local invoke ApiFunction --event tests/events/post_sin_csvkey.json
```

> La capa común instala sus dependencias en `src/layers/common_layer/python/`.
> Antes de `sam build`:
> `pip install fastavro==1.12.2 --target src/layers/common_layer/python`

## Despliegue

El despliegue se realiza **por el pipeline de CI/CD** (GitHub Actions), no manualmente
(política de gobernanza del equipo). Al mergear a `main`:

1. **CI**: `black --check` + `ruff check` + `pytest`.
2. **Deploy**: autenticación OIDC con AWS, `sam build` y despliegue del stack.

La configuración del rol OIDC está documentada en [`infra/oidc/README.md`](infra/oidc/README.md).

## Prueba end-to-end

Fixtures y pasos en [`tests/e2e/README.md`](tests/e2e/README.md). Resumen:

```bash
aws s3 cp tests/e2e/alumnos.csv  s3://<REPO_BUCKET>/datos/alumnos.csv
aws s3 cp tests/e2e/alumnos.json s3://<REPO_BUCKET>/schemas/alumnos.json
curl -X POST "<API_URL>/conversions" -H "Content-Type: application/json" -d '{"csvKey":"datos/alumnos.csv"}'
curl "<API_URL>/conversions/<AUDIT_ID>"
```

Resultado esperado: `COMPLETED` con `totalRows=7`, `convertedRows=4`, `errorRows=3`.

## Documentación del proyecto

- Especificación: [`.kiro/specs/requirements.md`](.kiro/specs/requirements.md), [`design.md`](.kiro/specs/design.md), [`tasks.md`](.kiro/specs/tasks.md)
- Arquitectura: diagrama en la sección [Arquitectura](#arquitectura) y detalle en [`.kiro/specs/design.md`](.kiro/specs/design.md)
- Guía de despliegue OIDC: [`infra/oidc/README.md`](infra/oidc/README.md)
- Prueba end-to-end: [`tests/e2e/README.md`](tests/e2e/README.md)
