# Estructura del Proyecto

## Árbol de directorios

```
Avro-Rest-API-Gateway/
├── template.yaml                 # Plantilla SAM: todos los recursos AWS
├── samconfig.toml                # Configuración de despliegue SAM (perfil developer, región us-east-1)
├── README.md
│
├── src/                          # Código de las funciones Lambda
│   ├── api_handler/              # Lambda ApiFunction (endpoints HTTP)
│   │   ├── app.py                # Handler: POST /conversions y GET /conversions/{auditId}
│   │   └── requirements.txt
│   │
│   ├── conversion_worker/        # Lambda ConversionWorkerFunction (procesamiento asíncrono)
│   │   ├── app.py                # Handler invocado por evento
│   │   └── requirements.txt
│   │
│   └── common/                   # Lógica de negocio compartida (independiente del handler)
│       ├── conversion.py         # Orquestación CSV→Avro
│       ├── validation.py         # Validación contra esquema + qualityRules
│       ├── avro_writer.py        # Serialización Avro (fastavro)
│       ├── audit.py              # Lectura/escritura del asiento en DynamoDB
│       ├── s3_repository.py      # Acceso al bucket (datos/schemas/output/logs)
│       └── responses.py          # Construcción de respuestas JSON UTF-8
│
├── tests/                        # Pruebas unitarias (pytest)
│   ├── test_validation.py
│   ├── test_conversion.py
│   └── test_api_handler.py
│
└── .kiro/
    ├── specs/
    │   ├── requirements.md
    │   └── design.md
    └── steering/
        ├── product.md
        ├── tech.md
        └── structure.md
```

## Organización del bucket S3 (repositorio oficial)

```
s3://<RepositoryBucket>/
├── datos/      # CSV de entrada            (datos/alumnos.csv)
├── schemas/    # Esquemas Avro en JSON     (schemas/alumnos.json)
├── output/     # Avro generados            (output/alumnos_{yyyymmdd}.avro)
└── logs/       # Logs de inconsistencias   (logs/alumnos_{yyyymmdd}.csv)
```

## Convenciones

### Separación de responsabilidades
- **Handlers** (`api_handler/`, `conversion_worker/`): adaptan el evento de entrada (HTTP o invocación asíncrona), delegan en `common/` y arman la respuesta/estado. No contienen lógica de negocio.
- **Lógica de negocio** (`common/`): validación, conversión y serialización. No conoce API Gateway ni el mecanismo de invocación; esto la hace testeable de forma aislada.

### Nombres de archivos generados
- Avro de salida: `output/{nombre_base}_{yyyymmdd}.avro`.
- Log de inconsistencias: `logs/{nombre_base}_{yyyymmdd}.csv`.
- `{nombre_base}` se deriva del nombre del CSV de origen.
- Al reprocesar el mismo CSV el mismo día, los archivos se **sobrescriben** (sin versionado).

### Asociación CSV↔esquema
- Por convención de nombre: `datos/alumnos.csv` ↔ `schemas/alumnos.json`.
- El campo opcional `schemaKey` del request permite anular la convención.

### Pruebas
- Un archivo de prueba por módulo de negocio relevante en `tests/`.
- Priorizar pruebas de `validation.py` y `conversion.py`, que concentran la lógica crítica.

### Nombres y estilo (Python)
- Módulos y funciones en `snake_case`; clases en `PascalCase`.
- Aplican las convenciones de código definidas en `tech.md` (4 espacios, docstrings, type hints, f-strings, funciones < 30 líneas).
