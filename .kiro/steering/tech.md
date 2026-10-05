# Stack Tecnológico

## Plataforma

- **Nube**: AWS (serverless).
- **Infraestructura como código**: AWS SAM (`template.yaml`).
- **Perfil y región**: todos los comandos de AWS CLI y SAM CLI usan `--profile AdministratorAccess-962682390364` y `--region us-east-1`.

## Servicios AWS

- **API Gateway (REST API)**: expone `POST /conversions` y `GET /conversions/{auditId}`.
- **AWS Lambda**: dos funciones.
  - `ApiFunction` — atiende los endpoints HTTP; acepta la solicitud, crea el asiento de auditoría e invoca al worker de forma asíncrona.
  - `ConversionWorkerFunction` — invocada por evento (`InvocationType=Event`); ejecuta la conversión CSV→Avro.
- **Amazon S3**: repositorio oficial (única fuente de verdad). Prefijos: `datos/`, `schemas/`, `output/`, `logs/`.
- **Amazon DynamoDB**: tabla de auditoría y estado del procesamiento asíncrono; facturación on-demand; atributo `ttl` para expiración automática.

## Lenguaje y librerías

- **Runtime**: Python 3.12.
- **Serialización Avro**: `fastavro` (sin dependencia de JVM).
- **SDK de AWS**: `boto3` (incluido en el runtime de Lambda).
- **Procesamiento CSV**: módulo estándar `csv`, con lectura por streaming.
- **Pruebas**: `pytest`.
- **Estilo/formato**: `black` (formato) y `ruff` (linting).

## Convenciones de código

- Indentación de **4 espacios** en todos los archivos Python.
- **Todas las funciones** llevan docstring.
- **Type hints** en todos los parámetros y valores de retorno de las funciones.
- Preferir **f-strings** sobre `.format()` o `%`.
- Mantener las funciones por debajo de **30 líneas** siempre que sea posible.
- Separar la **lógica de negocio** (validación + serialización Avro) de los **handlers** (HTTP y worker), de modo que sea testeable e independiente del mecanismo de invocación.
- Respuestas HTTP siempre en **JSON UTF-8** (`Content-Type: application/json; charset=utf-8`), omitiendo campos nulos (salvo `avroKey`, que puede retornarse como `null` explícito).

## Manejo de errores

- Códigos de error de negocio: `CSV_NOT_FOUND`, `SCHEMA_NOT_FOUND`, `INVALID_SCHEMA`.
- En el flujo asíncrono, los errores de procesamiento se registran en el asiento de auditoría (`status=ERROR`) y se consultan vía `GET /conversions/{auditId}`.
- El worker debe ser **idempotente** respecto al `auditId` (los reintentos de invocación asíncrona no deben duplicar ni corromper el estado).

## Comandos frecuentes

> Todos incluyen `--profile AdministratorAccess-962682390364` y `--region us-east-1` donde aplica.

### Build y despliegue (SAM)
```bash
sam build
sam deploy --profile AdministratorAccess-962682390364 --region us-east-1
```

### Validación de la plantilla
```bash
sam validate --profile AdministratorAccess-962682390364 --region us-east-1
```

### Pruebas locales
```bash
pytest
```

### Formato y linting
```bash
black .
ruff check .
```

## Dependencias

- Las dependencias de Python se declaran con versiones fijadas (pinned) en el `requirements.txt` de cada función Lambda.
- Preferir paquetes conocidos y mantenidos activamente.
