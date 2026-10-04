# api-standards — Diseño de la REST API

La API tiene exactamente dos endpoints y un patrón de procesamiento **asíncrono**: el `POST` acepta y delega, el `GET` consulta el estado.

## Endpoints

| Método | Recurso | Propósito | Éxito |
|---|---|---|---|
| `POST` | `/conversions` | Aceptar una solicitud de conversión | `202 Accepted` |
| `GET` | `/conversions/{auditId}` | Consultar el estado/resumen | `200 OK` |

## `POST /conversions`

**Request**
```json
{ "csvKey": "datos/alumnos.csv", "schemaKey": "schemas/alumnos.json" }
```
- `csvKey` (obligatorio): clave S3 del CSV.
- `schemaKey` (opcional): si se omite, se resuelve por convención de nombre.

**202 Accepted** — procesamiento en curso
```json
{ "status": "PENDING", "auditId": "a1b2c3d4", "statusUrl": "/conversions/a1b2c3d4" }
```

**400** — request inválido (falta `csvKey`, JSON mal formado).

> La existencia del CSV/esquema en S3 se verifica **dentro del worker**. Los errores "no encontrado" o "esquema inválido" se reflejan en el estado del asiento (vía `GET`), no en la respuesta del `POST`.

## `GET /conversions/{auditId}`

Devuelve el asiento según su estado. `404` si el `auditId` no existe.

- **PROCESSING**: `{ "status": "PROCESSING", "auditId": "..." }`
- **COMPLETED**: incluye `avroKey`, `logKey`, `totalRows`, `convertedRows`, `errorRows`, `fileSizeBytes`.
- **NO_VALID_RECORDS**: `avroKey: null` explícito, con `logKey` y contadores.
- **ERROR**: incluye `error` (código) y `message`.

## Estados del procesamiento

```
PENDING ──► PROCESSING ──► COMPLETED
                       ├──► NO_VALID_RECORDS
                       └──► ERROR
```

## Reglas de respuesta

- Siempre `Content-Type: application/json; charset=utf-8`.
- Omitir del cuerpo los campos con valor nulo, **salvo `avroKey`**, que se retorna como `null` explícito para señalar que no hubo generación.
- Ante error, código HTTP apropiado + cuerpo JSON con mensaje descriptivo.
- `auditId` es un UUID generado por el servidor; fechas en ISO-8601.
- Helpers de `common/responses.py` para `202`, `200` y errores (`400`, `404`).
