# structure — Estructura y capas

## Árbol del proyecto

```
Avro-Rest-API-Gateway/
├── template.yaml                 # Plantilla SAM: todos los recursos AWS
├── samconfig.toml                # Config de despliegue (perfil developer, us-east-1)
│
├── src/
│   ├── api_handler/              # Lambda ApiFunction (endpoints HTTP)
│   │   ├── app.py                # POST /conversions y GET /conversions/{auditId}
│   │   └── requirements.txt
│   ├── conversion_worker/        # Lambda ConversionWorkerFunction (asíncrono)
│   │   ├── app.py                # Handler invocado por evento
│   │   └── requirements.txt
│   └── common/                   # Lógica de negocio compartida
│       ├── conversion.py         # Orquestación CSV→Avro
│       ├── validation.py         # Validación contra esquema + qualityRules
│       ├── avro_writer.py        # Serialización Avro (fastavro)
│       ├── audit.py              # Lectura/escritura del asiento en DynamoDB
│       ├── s3_repository.py      # Acceso al bucket (datos/schemas/output/logs)
│       └── responses.py          # Construcción de respuestas JSON UTF-8
│
└── tests/                        # Pruebas unitarias (pytest), 1 archivo por módulo
    ├── test_validation.py
    ├── test_conversion.py
    └── test_api_handler.py
```

## Organización del bucket S3

```
s3://<RepositoryBucket>/
├── datos/      # CSV de entrada            (datos/alumnos.csv)
├── schemas/    # Esquemas Avro en JSON     (schemas/alumnos.json)
├── output/     # Avro generados            (output/alumnos_{yyyymmdd}.avro)
└── logs/       # Logs de inconsistencias   (logs/alumnos_{yyyymmdd}.csv)
```

## Separación en capas

| Capa | Responsabilidad | Prohibido |
|---|---|---|
| Handler (`api_handler/`, `conversion_worker/`) | Adaptar el evento (HTTP o invocación asíncrona), delegar en `common/`, armar respuesta/estado | Lógica de negocio |
| Negocio (`common/`) | Validación, conversión, serialización Avro, acceso a S3/DynamoDB | Conocer API Gateway o el mecanismo de invocación |

La lógica de `common/` no conoce el handler: esto la hace testeable de forma aislada.

## Convenciones de nombres generados

- Avro de salida: `output/{nombre_base}_{yyyymmdd}.avro`.
- Log de inconsistencias: `logs/{nombre_base}_{yyyymmdd}.csv`.
- `{nombre_base}` se deriva del nombre del CSV de origen.
- Al reprocesar el mismo CSV el mismo día, los archivos se **sobrescriben** (sin versionado).

## Asociación CSV ↔ esquema

- Por convención de nombre: `datos/alumnos.csv` ↔ `schemas/alumnos.json`.
- El campo opcional `schemaKey` del request permite anular la convención.

## Pruebas

- Un archivo de prueba por módulo de negocio relevante en `tests/`.
- Priorizar `validation.py` y `conversion.py`, que concentran la lógica crítica.
