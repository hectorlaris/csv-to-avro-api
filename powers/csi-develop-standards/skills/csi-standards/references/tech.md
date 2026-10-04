# tech — Stack, runtime y calidad de código

## Plataforma

- **Nube**: AWS, modelo serverless (escalado automático, pago por uso).
- **IaC**: AWS SAM (`template.yaml`), despliegue reproducible.
- **Perfil y región**: `--profile developer` y `--region us-east-1` en todo comando de AWS CLI y SAM CLI.

## Servicios AWS

| Servicio | Rol |
|---|---|
| API Gateway (REST API) | Expone `POST /conversions` y `GET /conversions/{auditId}`. |
| Lambda `ApiFunction` | Atiende los endpoints HTTP: valida, crea el asiento de auditoría e invoca al worker de forma asíncrona (`InvocationType=Event`). |
| Lambda `ConversionWorkerFunction` | Invocada por evento; ejecuta la conversión CSV→Avro. |
| Amazon S3 | Repositorio oficial (única fuente de verdad). Prefijos: `datos/`, `schemas/`, `output/`, `logs/`. |
| Amazon DynamoDB | Tabla de auditoría y estado del procesamiento asíncrono; facturación on-demand; atributo `ttl` para expiración automática. |

## Runtime y librerías

- **Runtime**: Python 3.12.
- **Serialización Avro**: `fastavro` (sin dependencia de JVM).
- **SDK de AWS**: `boto3` (incluido en el runtime de Lambda; no se fija en `requirements.txt`).
- **Procesamiento CSV**: módulo estándar `csv`, con lectura por streaming.
- **Pruebas**: `pytest`.
- **Formato / linting**: `black` (formato) y `ruff` (linting).

## Calidad de código

- Indentación de **4 espacios** en todos los archivos Python.
- **Docstring** en todas las funciones.
- **Type hints** en todos los parámetros y valores de retorno.
- Preferir **f-strings** sobre `.format()` o `%`.
- Mantener las funciones por debajo de **30 líneas** siempre que sea posible.
- Módulos y funciones en `snake_case`; clases en `PascalCase`.

## Dependencias

- Declaradas con versiones **fijadas (pinned)** en el `requirements.txt` de cada función Lambda.
- Preferir paquetes conocidos y mantenidos activamente.

## Comandos frecuentes

```bash
# Build y despliegue
sam build
sam deploy --profile developer --region us-east-1

# Validación de la plantilla
sam validate --profile developer --region us-east-1

# Pruebas
pytest

# Formato y linting
black .
ruff check .
```
