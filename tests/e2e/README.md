# Fixtures de prueba end-to-end

Archivos de datos para validar el flujo completo contra el entorno desplegado en AWS.

| Archivo | Rol |
|---|---|
| `alumnos.json` | Esquema Avro con `qualityRules` (minLength, min, max) |
| `alumnos.csv` | 7 filas: 4 válidas y 3 inconsistentes (tipo, nulo, qualityRule) |

## Casos que ejercita el CSV

- `Pedro,abc,...` → tipo inválido en `edad` (se esperaba `int`)
- `,25,...` → `nombre` nulo no permitido
- `Jose,200,...` → `edad` incumple la qualityRule `max: 120`

Las otras 4 filas (Ana, Luis, Maria, Carla) son válidas y deben acabar en el Avro.

## Cómo correr la prueba manual

> Sustituye `<API_URL>` por el output `ApiEndpoint` del stack y usa el perfil/región del proyecto.

```bash
# 1. Subir datos y esquema al bucket
aws s3 cp tests/e2e/alumnos.csv  s3://<REPO_BUCKET>/datos/alumnos.csv
aws s3 cp tests/e2e/alumnos.json s3://<REPO_BUCKET>/schemas/alumnos.json

# 2. Solicitar la conversión
curl -X POST "<API_URL>/conversions" \
  -H "Content-Type: application/json" \
  -d '{"csvKey": "datos/alumnos.csv"}'

# 3. Consultar el estado con el auditId devuelto
curl "<API_URL>/conversions/<AUDIT_ID>"
```

Resultado esperado: `COMPLETED` con `totalRows=7`, `convertedRows=4`, `errorRows=3`,
el Avro en `output/` y el log de inconsistencias en `logs/`.
