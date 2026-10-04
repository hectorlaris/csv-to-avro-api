# Plan de Trabajo — Fase de Tasks (tasks.md)
## Proyecto: Avro REST API Gateway

> **Propósito de este documento:** servir de referencia operativa para producir `tasks.md`,
> la tercera y última fase del spec CSI. Resume el estado actual del spec, la estrategia de
> descomposición en tareas, el rol de cada recurso Kiro disponible y el orden de trabajo
> recomendado para el equipo.

---

## 1. Estado del spec

| Fase | Archivo | Estado |
|---|---|---|
| Requerimientos | `.kiro/specs/requirements.md` | ✅ Aprobado — 9 requerimientos (R1–R9) con criterios EARS |
| Diseño | `.kiro/specs/design.md` | ✅ Aprobado — arquitectura, API, modelo de datos, flujo, costos |
| Tasks | `.kiro/specs/tasks.md` | ⏳ **Pendiente — próximo paso** |

Los dos documentos base están completos y son coherentes entre sí (la discrepancia `DONE` →
`COMPLETED` ya fue corregida en `requirements.md`). El único pendiente estructural del
`design.md` es el diagrama `.drawio` canónico, que queda como tarea explícita dentro del plan.

---

## 2. Qué debe contener `tasks.md`

Según la skill `spec-authoring` del Power, el `tasks.md` es un **plan incremental de
implementación** donde cada tarea:

- Tiene un identificador único (`T-01`, `T-02`, …).
- Describe un entregable concreto y verificable.
- Referencia el/los requerimientos que satisface (`→ R2, R7`).
- Sigue el orden: **andamiaje → lógica de negocio → handlers → infra SAM → verificación**.
- Es lo suficientemente pequeña para completarse en una sesión de trabajo.

---

## 3. Descomposición propuesta en tareas

Las tareas están organizadas en cinco grupos que siguen el orden de dependencias naturales
del proyecto. Cada grupo puede trabajarse en paralelo dentro del grupo una vez que el anterior
está completo.

### Grupo A — Andamiaje e infraestructura SAM

| ID | Descripción | Refs |
|---|---|---|
| T-01 | Crear `template.yaml` con todos los recursos AWS: bucket S3, REST API (2 endpoints), `ApiFunction`, `ConversionWorkerFunction`, tabla DynamoDB (TTL habilitado), DLQ SQS y roles IAM con privilegios mínimos | R5, R6 |
| T-02 | Crear `samconfig.toml` con perfil `developer` y región `us-east-1` | R6.5 |
| T-03 | Crear `src/api_handler/requirements.txt` y `src/conversion_worker/requirements.txt` con dependencias fijadas (`fastavro`, versiones pinned) | R5 |
| T-04 | ~~Generar el diagrama canónico `Documents/avro-rest-api-gateway-arquitectura.drawio`~~ **BLOCKED** — requiere el binario `aim` del MCP `drawio-architect`; no bloquea el avance del resto de tareas | — |

### Grupo B — Módulos de lógica de negocio (`src/common/`) + prueba al cierre

> **Decisión adoptada:** cada tarea incluye como último paso la escritura y aprobación del
> test unitario del módulo (prueba al cierre, Opción 2). El Grupo D queda reservado solo
> para los tests de integración de los handlers. El hook `py-test-for-new-module.json`
> refuerza esto automáticamente al crear cualquier archivo en `src/common/`.

| ID | Descripción | Pasos | Refs |
|---|---|---|---|
| T-05 | `src/common/audit.py` | 1. Implementar `create_audit_entry`, `update_audit_entry`, `get_audit_entry` (DynamoDB, `ttl` epoch Unix segundos). 2. Escribir y pasar `tests/test_audit.py`. | R4, R7, R9 |
| T-06 | `src/common/s3_repository.py` | 1. Implementar `object_exists`, `read_object_stream`, `write_object`, `get_object_size` (acceso IAM). 2. Escribir y pasar `tests/test_s3_repository.py`. | R1, R2 |
| T-07 | `src/common/validation.py` | 1. Implementar validación por fila (tipos, enums, nulos, `qualityRules`); retornar filas válidas e inconsistencias. 2. Escribir y pasar `tests/test_validation.py` (casos: tipo correcto, tipo incorrecto, enum, nulo, `qualityRules`). | R2.1, R2.2 |
| T-08 | `src/common/avro_writer.py` | 1. Implementar serialización de registros válidos a Avro con `fastavro`; buffer listo para S3. 2. Escribir y pasar `tests/test_avro_writer.py`. | R2.4 |
| T-09 | `src/common/conversion.py` | 1. Implementar orquestación CSV→Avro: streaming `csv`, resolución esquema por convención/`schemaKey`, log de inconsistencias, idempotencia por `auditId`. 2. Escribir y pasar `tests/test_conversion.py` (flujo completo, sin registros válidos, reintento idempotente). | R1.3, R1.4, R2, R8 |
| T-10 | `src/common/responses.py` | 1. Implementar constructores de respuestas JSON UTF-8; omitir nulos salvo `avroKey`. 2. Escribir y pasar `tests/test_responses.py`. | R3 |

### Grupo C — Handlers Lambda

| ID | Descripción | Refs |
|---|---|---|
| T-11 | Implementar `src/api_handler/app.py`: handler `POST /conversions` (valida request, genera UUID, escribe `PENDING`, invoca worker async) y `GET /conversions/{auditId}` (lee asiento, responde según estado); delega en `common/` | R3, R7, R9 |
| T-12 | Implementar `src/conversion_worker/app.py`: handler invocado por evento; guarda `PROCESSING`, llama a `conversion.py`, actualiza estado final; idempotencia ante `auditId` ya finalizado | R8, R9 |

### Grupo D — Pruebas de integración de handlers (`tests/`)

> Los tests unitarios de los módulos de `src/common/` se escriben dentro de cada tarea del
> Grupo B (prueba al cierre). Este grupo cubre únicamente los tests de los handlers, que
> dependen de que B y C estén completos.

| ID | Descripción | Refs |
|---|---|---|
| T-13 | Escribir `tests/test_api_handler.py`: `POST` con request válido, `POST` con `csvKey` ausente, `GET` por cada estado (`PENDING`, `PROCESSING`, `COMPLETED`, `NO_VALID_RECORDS`, `ERROR`, `404`) | R3, R7, R9 |

### Grupo E — Verificación integral

| ID | Descripción | Refs |
|---|---|---|
| T-14 | Ejecutar `sam build` + `sam validate` y confirmar que la plantilla no tiene errores | R6 |
| T-15 | Ejecutar `pytest` completo; confirmar cobertura de todos los requerimientos críticos | todos |
| T-16 | Ejecutar `black .` + `ruff check .` y confirmar cero advertencias | — |

---

## 4. Orden de ejecución recomendado

```
A (T-01 → T-03, T-04 BLOCKED)
    │
    ▼
B (T-05 → T-10)   ← un módulo por tarea; cada una incluye su test al cierre
    │
    ▼
C (T-11 → T-12)   ← requiere que B esté completo
    │
    ▼
D (T-13)          ← test de handlers; requiere C completo
    │
    ▼
E (T-14 → T-16)   ← verificación integral; requiere A + B + C + D
```

> T-04 no bloquea: el flujo avanza de A a E sin esperar el diagrama `.drawio`. Cuando
> `aim` esté disponible, T-04 se retoma como tarea independiente.

---

## 5. Recursos Kiro disponibles y cómo usarlos en esta fase

### 5.1 Agente `spec-author` → para generar `tasks.md`

El agente está en `.kiro/agents/spec-author.md`. Su rol es producir el documento de tareas
siguiendo el estándar CSI sin implementar código.

**Cómo activarlo:**
1. En el selector de agentes de Kiro, selecciona **`spec-author`**.
2. Prompt sugerido:

   > *"Tenemos `requirements.md` y `design.md` aprobados en `.kiro/specs/`. Redacta
   > `tasks.md` siguiendo el estándar CSI: plan incremental (andamiaje → lógica en
   > `common/` → handlers → SAM → verificación), cada tarea con ID, descripción
   > verificable y referencias a requerimientos."*

El agente leerá las skills `spec-authoring` y `csi-standards` del Power para estructurar
el documento conforme al estándar.

### 5.2 Power `csi-develop-standards` → para fundamentar decisiones de implementación

| Skill / MCP | Cuándo usarlo en la fase de tasks |
|---|---|
| `csi-standards` → `tech.md` / `structure.md` | Al redactar cada tarea; confirma convenciones de nombres, capas y stack |
| `csi-standards` → `api-standards.md` | Al detallar T-11 (handler API): contrato exacto de endpoints y estados |
| `csi-standards` → `error-handling.md` | Al detallar T-12 (worker) y T-05 (audit): manejo de errores e idempotencia |
| `spec-authoring` | Estructura y formato de `tasks.md` |
| `drawio-architecture` + MCP `drawio-architect` | T-04: generar el diagrama `.drawio` pendiente cuando `aim` esté disponible |
| MCP `aws-docs` | Si surge alguna duda técnica sobre SAM, Lambda async o DynamoDB TTL durante las tasks |
| MCP `aws-pricing` | No es necesario en esta fase (la estimación ya está en `design.md`) |

**Cómo activar el Power manualmente** (si no se usa el agente `spec-author`):

> *"Usando el Power csi-develop-standards, y en particular la skill spec-authoring,
> redacta el tasks.md para el proyecto Avro REST API Gateway…"*

### 5.3 Hooks → protección automática durante la implementación

Los 6 hooks activos en `.kiro/hooks/` se disparan automáticamente durante la implementación.
No requieren acción manual, pero conviene que el equipo los conozca:

| Hook | Qué protege en la fase de tasks |
|---|---|
| `py-format-lint-on-save.json` | Cada `.py` guardado se formatea con `black` y se lint con `ruff --fix` |
| `py-quality-gate.json` | Al cerrar el turno del agente, si cambió `src/` o `tests/`, corre `ruff + black --check + pytest`; bloquea si falla |
| `py-test-for-new-module.json` | Al crear un módulo en `src/common/`, recuerda crear su prueba en `tests/` |
| `py-guard-destructive-commands.json` | Bloquea `sam deploy`, `git push`, `reset --hard`, `rm -rf`, etc. |
| `py-guard-secrets.json` | Bloquea escrituras a `.env`, llaves privadas o contenido con credenciales |
| `py-audit-tools.json` | Registra cada invocación de herramienta en `.kiro-audit/tool-calls.jsonl` |

> El quality gate (`py-quality-gate.json`) es el más crítico: asegura que el código nunca
> quede en estado roto al final de cada turno del agente.

### 5.4 Steering del repositorio → contexto siempre activo

Los tres archivos en `.kiro/steering/` se incluyen en **todas** las interacciones sin
necesidad de pedirlo:

- `product.md` — propósito, usuarios y principios del producto.
- `tech.md` — stack, servicios AWS, convenciones de código y comandos.
- `structure.md` — árbol del proyecto, organización del bucket S3, separación de capas.

Esto garantiza que el agente que implemente las tareas tenga siempre el contexto correcto
sobre indentación (4 espacios), docstrings, type hints, f-strings y funciones < 30 líneas.

---

## 6. Decisiones tomadas

| # | Decisión | Opción adoptada |
|---|---|---|
| 1 | **Granularidad de tareas** | Una tarea por módulo de `common/` (Opción A) — mayor trazabilidad y asignación paralela por persona |
| 2 | **TDD vs. post-implementación** | Prueba al cierre del módulo, en la misma tarea (Opción 2) — más pragmático; el hook `py-test-for-new-module.json` lo refuerza |
| 3 | **T-04 (diagrama `.drawio`)** | No bloqueante — se marca `BLOCKED` y el resto del plan avanza sin esperar el binario `aim` |

---

## 7. Checklist para dar por aprobado `tasks.md`

- [ ] Todas las tareas del Grupo A al E están presentes y tienen ID único.
- [ ] Cada tarea referencia al menos un requerimiento (R1–R9).
- [ ] El orden respeta las dependencias (andamiaje antes de lógica, lógica antes de handlers).
- [ ] Cada tarea del Grupo B incluye como último paso la escritura y aprobación de su test.
- [ ] El Grupo D cubre los tests de integración de los handlers (`test_api_handler.py`).
- [ ] T-04 está marcada como `BLOCKED` y no figura como prerequisito de ninguna otra tarea.
- [ ] T-14 (`sam validate`) y T-16 (`black + ruff`) están incluidas como criterio de cierre.
- [ ] El documento fue producido o revisado con la skill `spec-authoring` del Power.
- [ ] El agente `spec-author` (o quien redacte el documento) confirmó con el usuario antes de cerrar.

---

## 8. Resumen ejecutivo

El spec tiene dos tercios completos y aprobados. Las tres decisiones de planificación están
tomadas: granularidad por módulo (Opción A), prueba al cierre de cada módulo (Opción 2) y
T-04 no bloqueante. El siguiente paso es producir `tasks.md` usando el agente `spec-author`
con el Power `csi-develop-standards` activado. Las tareas siguen un orden de cinco grupos
(A → E): andamiaje SAM → módulos de negocio con sus tests → handlers → test de handlers →
verificación integral. Los hooks activos garantizan formato, lint y pruebas sin intervención
manual durante toda la implementación.

