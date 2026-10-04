# Informe Tech Lead — Recursos de Kiro para el proyecto Avro REST API Gateway

Este documento resume los recursos que configuramos en Kiro para estandarizar y acelerar el desarrollo del proyecto **Avro REST API Gateway** (serverless en AWS: API Gateway REST + Lambda Python 3.12 + S3 + DynamoDB, IaC con SAM; dominio: conversión asíncrona de CSV a Apache Avro).

El objetivo es que cualquier integrante del equipo entienda qué hay, para qué sirve, y cómo arrancar un **spec** apoyándose en el Power.

## Visión general

Configuramos cinco bloques de recursos que trabajan juntos:

| Recurso | Dónde vive | Qué aporta |
|---|---|---|
| **Power** `csi-develop-standards` | `powers/csi-develop-standards/` (desarrollo) e instalado en Kiro | Skills, steering y 3 servidores MCP (AWS Docs, AWS Pricing, draw.io) |
| **Hooks** | `.kiro/hooks/` + `scripts/hooks/` | Automatizan formato, lint, pruebas, gobernanza y auditoría |
| **Agent** `spec-author` | `.kiro/agents/spec-author.md` | Agente que redacta specs y diseños, sin implementar código |
| **Steering** del repo | `.kiro/steering/` | Contexto permanente del proyecto (producto, stack, estructura) |
| **Specs** | `.kiro/specs/` | Requerimientos, diseño y plan de tareas de la solución |

---

## 1. Power: `csi-develop-standards`

Un Power empaqueta **documentación, guías de trabajo (skills + steering) y servidores MCP**. Este Power es el núcleo de nuestros estándares: lo activa Kiro cuando detecta palabras clave como *spec, requirements, diseño, arquitectura, diagrama, api, avro*.

### Contenido

```
csi-develop-standards/
├── plugin.json                 # Metadatos y keywords del Power
├── mcp.json                    # 3 servidores MCP
├── dev.kiro/
│   ├── INSTRUCTIONS.md         # Índice: qué skill usar para cada tarea
│   └── steering/
│       ├── csi-standards.md    # Reglas de oro del equipo (resumen)
│       └── diagram-rules.md    # Reglas para diagramas de arquitectura
└── skills/
    ├── csi-standards/          # Estándares técnicos + 4 referencias
    │   ├── SKILL.md
    │   └── references/
    │       ├── tech.md             # Stack, runtime, calidad de código
    │       ├── structure.md        # Estructura de carpetas y capas
    │       ├── api-standards.md    # Endpoints, estados y respuestas
    │       └── error-handling.md   # Errores de negocio e idempotencia
    ├── spec-authoring/         # Cómo redactar specs con EARS
    └── drawio-architecture/    # Cómo dibujar la arquitectura en draw.io
```

### Skills (se leen bajo demanda)

| Skill | Para qué sirve |
|---|---|
| `csi-standards` | Estándares técnicos: separación negocio/handlers, calidad Python, diseño de la API, manejo de errores. Úsala al diseñar, implementar o revisar. |
| `spec-authoring` | Guía para redactar `requirements.md`, `design.md` y `tasks.md` con criterios de aceptación en **EARS en español**. |
| `drawio-architecture` | Flujo para crear el diagrama de arquitectura con el MCP de draw.io. |

### Servidores MCP

| Servidor | Para qué | Ejemplos de herramientas |
|---|---|---|
| `aws-docs` | Fundamentar decisiones con documentación oficial de AWS | `search_documentation`, `read_documentation` |
| `aws-pricing` | Estimar el costo del diseño antes de implementar | `get_pricing`, `generate_cost_report` |
| `drawio-architect` | Crear, inspeccionar y pulir diagramas `.drawio` | `diagram`, `draw`, `style`, `layout`, `inspect` |

> **Nota sobre draw.io**: este server expone herramientas **agrupadas por acción** (`diagram`, `draw`, etc.), cada una con un parámetro `action` (p. ej. `diagram(action="create")`). Los diagramas se guardan bajo la carpeta `Documents/`.

### Cómo se instaló

El Power se desarrolla en `powers/csi-develop-standards/` y se **instala** en Kiro (copia en `~/.kiro/powers/installed/`). Si editas el contenido del Power, hay que **reinstalarlo** desde la UI de Powers de Kiro para que los cambios surtan efecto. Verificamos que la instalación actual expone correctamente las 3 skills, el steering y los 3 MCP.

---

## 2. Hooks

Los hooks automatizan tareas en eventos del editor/agente. Están definidos en `.kiro/hooks/*.json` y ejecutan scripts Python en `scripts/hooks/`. Todos están alineados al stack **Python / pytest / black / ruff** de este proyecto.

| Hook (archivo) | Evento | Qué hace |
|---|---|---|
| `py-format-lint-on-save.json` | Al guardar un `.py` | Formatea con `black` y corrige con `ruff --fix` solo ese archivo |
| `py-quality-gate.json` | Al terminar el turno del agente | Si cambió `src/` o `tests/`, corre `ruff` + `black --check` + `pytest`; si fallan, no deja cerrar con código roto |
| `py-test-for-new-module.json` | Al crear un módulo en `src/common/` | Recuerda crear/actualizar su prueba en `tests/` |
| `py-guard-destructive-commands.json` | Antes de ejecutar un comando | Bloquea `force push`, push a `main`, `reset --hard`, `rm -rf`, `sam deploy`, `curl \| sh`, etc. |
| `py-guard-secrets.json` | Antes de escribir un archivo | Bloquea escrituras a `.env`, llaves privadas o contenido que parezca credencial |
| `py-audit-tools.json` | Después de cada herramienta | Registra la invocación en `.kiro-audit/tool-calls.jsonl` |

**Scripts de soporte** (`scripts/hooks/`): `quality_gate.py`, `format_on_save.py`, `guard.py`, `audit.py`. Leen el evento por `stdin` (JSON); el guard bloquea con *exit 2* y mensaje por `stderr`.

> Los hooks nuevos se activan al **iniciar sesión** en Kiro. Verificamos que el quality gate corre sin bloquear cuando no hay cambios, y que los guards bloquean efectivamente comandos destructivos y escrituras de secretos.

---

## 3. Agent: `spec-author`

Un **custom agent** especializado en producir specs y diseños. Vive en `.kiro/agents/spec-author.md` y se selecciona desde el selector de agentes de Kiro.

- **Rol**: dirige el diseño, **no** implementa código de producción.
- **Flujo**: entender → `requirements.md` (EARS) → `design.md` (fundamentado con AWS Docs y Pricing + diagrama) → `tasks.md`.
- **Usa el Power**: carga las skills `spec-authoring`, `csi-standards` y `drawio-architecture`, y los MCP `aws-docs`, `aws-pricing`, `drawio-architect`.

### Permisos (resumen)

| Acción | Comportamiento |
|---|---|
| Leer el repo | Permitido |
| Escribir en `.kiro/specs/**` y `Documents/**` | Permitido (specs y diagramas) |
| Escribir en `src/`, `tests/`, `template.yaml`, `samconfig.toml` | **Pregunta** (el agente dirige, no implementa) |
| Shell de lectura (`git status/diff/log`, `pytest`, `ruff`, `black`, `sam validate`) | Permitido |
| Destructivo / despliegue (`git push`, `rm -rf`, `sam deploy`, `aws`, `curl`) | **Bloqueado** |

---

## 4. Steering del repositorio

El steering es contexto que Kiro incluye **siempre** en las interacciones. Vive en `.kiro/steering/` y describe el proyecto.

| Archivo | Contenido |
|---|---|
| `product.md` | Propósito, usuarios, valor y principios del producto |
| `tech.md` | Stack, servicios AWS, runtime, librerías, convenciones y comandos |
| `structure.md` | Árbol del proyecto, organización del bucket S3, separación en capas |

> Diferencia clave: el **steering del repo** (`.kiro/steering/`) es la fuente de verdad del proyecto y se aplica siempre. El **steering del Power** (`dev.kiro/steering/`) son guías de trabajo que se leen bajo demanda. El Power complementa el steering del repo con el *cómo* de cada tarea; no lo reemplaza.

---

## 5. Cómo iniciar un spec usando el Power

Flujo recomendado para una feature nueva:

1. **Selecciona el agente.** En el selector de agentes de Kiro, elige **`spec-author`**. Verás su saludo de bienvenida.
2. **Describe la necesidad.** Ejemplo: *"Quiero un endpoint `GET /conversions` que liste las últimas conversiones registradas."* El agente aclarará dudas antes de escribir.
3. **Requirements.** El agente redacta `.kiro/specs/requirements.md` con historias de usuario y criterios **EARS en español**. Revísalo y apruébalo.
4. **Design.** Redacta `.kiro/specs/design.md`: decisiones técnicas justificadas, API, modelo de datos y flujo. Fundamenta con **AWS Docs** y estima costo con **AWS Pricing** (ambos vía el Power). Para la arquitectura, genera el `.drawio` en `Documents/` con la skill `drawio-architecture`.
5. **Tasks.** Deriva `.kiro/specs/tasks.md`: plan incremental (andamiaje → lógica en `common/` → handlers → infraestructura SAM → verificación), cada tarea referenciando sus requerimientos.
6. **Implementa.** Con el spec aprobado, otro agente (o tú) implementa las tareas. Los hooks aseguran formato, lint y pruebas en cada paso.

### Alternativa sin seleccionar el agente

Como el Power se activa por palabras clave, también puedes trabajar en una sesión normal y pedir, por ejemplo: *"Usando el Power csi-develop-standards, redacta el spec para…"*. Kiro activará el Power y leerá las skills correspondientes.

---

## Estado actual

- Power `csi-develop-standards` **instalado y verificado** (3 skills, 2 steering, 3 MCP operativos; probamos una consulta real a AWS Docs).
- 6 hooks del stack Python **activos** con sus 4 scripts de soporte.
- Agent `spec-author` **creado** y con front-matter válido.
- Steering y specs del proyecto en su lugar.

Todo listo para iniciar specs de forma estandarizada. Ante dudas sobre un estándar concreto, la fuente es la skill `csi-standards` del Power y el steering del repo.
