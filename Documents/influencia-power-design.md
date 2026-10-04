# Influencia del Power `csi-develop-standards` en la construcción del `design.md`

## Contexto

El `design.md` del proyecto **Avro REST API Gateway** es el segundo documento del spec CSI
(`requirements` → `design` → `tasks`). Su propósito es traducir los requerimientos a arquitectura,
API, modelo de datos y flujo de procesamiento, con decisiones técnicas fundamentadas.

Este documento explica qué aportó cada componente del power `csi-develop-standards` —
steering files, skills y servidores MCP — a ese resultado concreto.

---

## El Power como contenedor

El power `csi-develop-standards` es el punto de entrada que agrupa tres tipos de recursos:

| Tipo | Componentes |
|---|---|
| Steering files | `csi-standards.md`, `diagram-rules.md` |
| Skills | `spec-authoring`, `csi-standards`, `drawio-architecture` |
| Servidores MCP | `aws-docs`, `aws-pricing`, `drawio-architect` |

Sin activar el power no habría acceso a ninguna de estas herramientas ni guías. Su activación
entrega el mapa de qué usar para cada tarea y en qué orden.

---

## Influencia de los Steering Files

### `csi-standards.md` — Reglas de oro

Estableció los principios que no son negociables en ningún artefacto del proyecto:

- Separar negocio (`src/common/`) de handlers (`src/api_handler/`, `src/conversion_worker/`).
- Solo datos válidos en el Avro; nada silencioso.
- Respuestas predecibles: JSON UTF-8, omitir nulos salvo `avroKey`.
- Worker idempotente respecto al `auditId`.
- **Regla de conflicto**: si un estándar choca con un requerimiento, documentarlo y proponer
  la decisión — no ignorarlo en silencio.

Esta última regla fue la que motivó detectar y documentar en Decisiones técnicas la
discrepancia `DONE` → `COMPLETED` entre `requirements.md` y el estándar `api-standards`.

### `diagram-rules.md` — Reglas del diagrama

Definió las restricciones de construcción del diagrama de arquitectura:

- Dirección de las aristas según la acción real (lector → recurso, escritor → recurso).
- Una sola arista por par origen/destino; dos roles se combinan en la etiqueta.
- Sin nodos huérfanos ni aristas inventadas.
- Actores externos fuera del grupo de la nube; servicios AWS dentro.
- Numerar los pasos del flujo igual que en el `design.md` para mantener sincronía.
- Guardar bajo `Documents/` (raíz del MCP `drawio-architect`).

---

## Influencia de los Skills

### `spec-authoring` — Estructura del documento

Definió la **estructura obligatoria** del `design.md`. Sin esta skill el documento habría
sido un diseño genérico. Con ella, el resultado tiene exactamente las secciones del estándar CSI:

1. Visión general
2. Decisiones técnicas (tabla Área / Decisión / Justificación)
3. Arquitectura con diagrama
4. API con contrato completo
5. Modelo de datos
6. Flujo de procesamiento
7. Estimación de costo
8. Consideraciones y riesgos
9. Trazabilidad R1 → R9

También impuso el idioma (español en todo el spec), la regla de confirmar con el usuario
al cerrar cada documento, y que toda decisión no obvia se justifique con su fuente.

### `csi-standards` + referencias — Contenido técnico

Esta skill y sus cuatro archivos de referencia tuvieron el impacto más directo en el contenido:

#### `api-standards.md`
- Definió el contrato exacto de los dos endpoints: `POST /conversions` → `202 Accepted`,
  `GET /conversions/{auditId}` → `200 OK` / `404 Not Found`.
- Estableció los cinco estados del procesamiento:
  `PENDING → PROCESSING → COMPLETED | NO_VALID_RECORDS | ERROR`.
- Especificó los campos de cada respuesta (`avroKey`, `logKey`, `totalRows`,
  `convertedRows`, `errorRows`, `fileSizeBytes`).
- Definió la excepción de `avroKey: null` explícito para señalar que no hubo generación.
- **Permitió detectar el conflicto**: `requirements.md` usaba el estado `DONE`, pero el
  estándar define `COMPLETED`. Se corrigió `requirements.md` y se documentó la decisión.

#### `error-handling.md`
- Definió los tres códigos de error de negocio y dónde se detecta cada uno:

  | Código | Causa | Dónde |
  |---|---|---|
  | `CSV_NOT_FOUND` | `csvKey` no existe en S3 | Worker, al resolver archivos |
  | `SCHEMA_NOT_FOUND` | Esquema no existe en S3 | Worker, al resolver archivos |
  | `INVALID_SCHEMA` | JSON inválido o no es esquema Avro | Worker, al cargar |

- Estableció la separación entre **inconsistencia de fila** (excluye la fila, continúa el
  proceso) y **error de negocio** (detiene la conversión, cierra el asiento como `ERROR`).
- Recomendó la DLQ (Amazon SQS) para capturar invocaciones que agotan reintentos.

#### `tech.md` y `structure.md`
- Confirmaron el stack: Python 3.12, `fastavro`, `boto3`, módulo `csv` para streaming,
  `pytest`, `black`, `ruff`.
- Fijaron la separación de capas como eje del diseño: `src/common/` contiene la lógica
  de negocio; los handlers adaptan el evento y delegan.
- Establecieron la nomenclatura de archivos de salida:
  `output/{base}_{yyyymmdd}.avro` y `logs/{base}_{yyyymmdd}.csv`.

### `drawio-architecture` — Diagrama de arquitectura

Proporcionó:

- El **blueprint exacto** del diagrama para este proyecto: actores, servicios AWS, conexiones
  numeradas y tipos (`sync` / `async`).
- El flujo de construcción con el MCP: grupos → nodos → conexiones → `polish` → `inspect`
  → guardar en `Documents/`.
- La aclaración de que el MCP `drawio-architect` no expone herramientas sueltas sino
  agrupadas por acción (`diagram`, `draw`, `style`, `layout`, `inspect`).

Cuando el MCP `drawio-architect` no conectó (falta el binario `aim`), esta skill
proporcionó la base topológica para producir el diagrama equivalente en Mermaid con la
misma numeración de pasos, dejando el `.drawio` como pendiente explícito.

---

## Influencia de los Servidores MCP

### `aws-docs` — Fundamentación con documentación oficial

Consultado para justificar dos decisiones técnicas críticas que sin fuente oficial serían
solo opinión:

**Decisión 1 — Idempotencia obligatoria del worker**

Fuente: [Lambda async error handling](https://docs.aws.amazon.com/lambda/latest/dg/invocation-async-error-handling.html)

Confirmó que con `InvocationType=Event`:
- Lambda reintenta por defecto **2 veces** ante error de función (esperas de 1 min y 2 min).
- La cola de eventos es **eventualmente consistente**: el mismo evento puede entregarse
  más de una vez aunque la función no falle.
- La **DLQ** captura eventos descartados tras agotar los reintentos.

Impacto en el `design.md`: la idempotencia pasó de "buena práctica" a requerimiento técnico
obligatorio, la DLQ se incorporó a la arquitectura como componente explícito, y el flujo
de procesamiento documenta cómo el worker detecta un `auditId` ya finalizado.

**Decisión 2 — Formato del atributo `ttl` en DynamoDB**

Fuente: [DynamoDB Time to Live](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/TTL.html)

Confirmó tres detalles precisos:
- El atributo `ttl` debe ser de tipo `Number` en **epoch Unix en segundos**
  (no milisegundos, no string — DynamoDB ignora los que no cumplen este formato).
- El borrado ocurre **dentro de unos días** del vencimiento, no de forma inmediata.
- Las eliminaciones por TTL **no consumen write throughput**.

Impacto en el `design.md`: la Decisión técnica del `ttl` especifica el tipo y formato
exactos, el Modelo de datos los documenta, y Consideraciones y riesgos advierte que
el TTL no es inmediato.

### `aws-pricing` — Precios reales verificados

Consultado para reemplazar la estimación inicial (basada en precios públicos de lista) por
cifras verificadas directamente de la AWS Price List API.

**Precios confirmados (us-east-1, publicados 2026-09-01 a 2026-10-02):**

| Servicio | Dimensión | Precio real |
|---|---|---|
| AWS Lambda | Solicitudes | $0.20 / millón |
| AWS Lambda | Cómputo Tier-1 | $0.0000166667 / GB-s |
| API Gateway REST | Primeras 333M llamadas/mes | $3.50 / millón |
| DynamoDB on-demand | Write Request Units | $0.625 / millón |
| DynamoDB on-demand | Read Request Units | $0.125 / millón |
| S3 Standard | Almacenamiento (primeros 50 TB) | $0.023 / GB-mes |

**Corrección relevante:** el precio real de DynamoDB WRU ($0.625/M) es la mitad del valor
que tenía la estimación inicial ($1.25/M). Combinado con la capa gratuita de Lambda
que absorbe todo el cómputo del escenario base, el costo mensual bajó de ~$0.15 a ~$0.10.

### `drawio-architect` — Diagrama `.drawio` (pendiente)

No conectó en esta sesión por falta del binario `aim` (herramienta CLI del ecosistema
`agent-plugins.org` que arranca el servidor). Su rol habría sido generar el archivo
canónico `Documents/avro-rest-api-gateway-arquitectura.drawio` mediante las herramientas
`diagram`, `draw`, `layout` e `inspect`. Queda pendiente para cuando se instale `aim`.

---

## Resumen consolidado

| Componente | Contribución concreta al `design.md` |
|---|---|
| Steering `csi-standards.md` | Principios de diseño, regla de conflicto → corrección DONE→COMPLETED |
| Steering `diagram-rules.md` | Reglas de topología y construcción del diagrama |
| Skill `spec-authoring` | Estructura de secciones, idioma, trazabilidad R1→R9 |
| Skill `csi-standards` → `api-standards` | Contrato API completo, estados, campos de respuesta |
| Skill `csi-standards` → `error-handling` | Códigos de error, separación fila vs. negocio, DLQ |
| Skill `csi-standards` → `tech`/`structure` | Stack técnico, separación de capas, nomenclatura |
| Skill `drawio-architecture` | Blueprint del diagrama, topología, numeración de pasos |
| MCP `aws-docs` | Justificación técnica de idempotencia y formato del `ttl` con fuentes oficiales |
| MCP `aws-pricing` | Precios reales verificados, corrección de la estimación mensual |
| MCP `drawio-architect` | Pendiente — requiere instalar el binario `aim` |

En síntesis: el power convirtió el `design.md` de un documento de diseño genérico en uno
**fundamentado en estándares del equipo, en documentación oficial de AWS y en precios reales
verificados**, con un contrato de API preciso y cada decisión trazable a su fuente.
