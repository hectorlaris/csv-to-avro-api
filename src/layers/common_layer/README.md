# Capa común (CommonLayer)

Contiene la lógica de negocio compartida del proyecto en `python/common/`
(validación, conversión CSV→Avro, serialización, auditoría, acceso a S3 y respuestas).

## Estructura

```
common_layer/
└── python/
    ├── common/          # Código fuente (se versiona en git)
    └── fastavro/        # Dependencia instalada (NO se versiona; ver .gitignore)
```

## Dependencias

La capa requiere `fastavro==1.12.2`. Las dependencias **no se versionan** en git
(están excluidas en `.gitignore`). Antes de `sam build`, instálalas en `python/`:

```bash
pip install fastavro==1.12.2 --target src/layers/common_layer/python
```

El pipeline de CI/CD debe ejecutar este paso antes de `sam build`.

> `boto3` no se instala: está incluido en el runtime de Lambda (Python 3.12).
