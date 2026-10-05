# De una necesidad a producción con Kiro: construí una API serverless CSV→Avro guiada por specs, powers y agentes

> Artículo para LinkedIn — Kiro University Challenge
> Repositorio público: https://github.com/hectorlaris/csv-to-avro-api

Durante el reto de Kiro University construí, de principio a fin, una solución **serverless en AWS**
que convierte archivos CSV a **Apache Avro** validando contra un esquema y reglas de calidad,
con auditoría y procesamiento asíncrono. Pero lo interesante no es solo el producto: es **cómo**
lo construí. Kiro no fue un autocompletado; fue un entorno donde el diseño, la gobernanza, la
automatización y el despliegue conviven. Aquí describo, lección por lección, cómo se demuestra
cada capacidad y dónde verla en el repositorio.

---

## 1. Spec-driven development

En vez de saltar al código, el trabajo arrancó por una **especificación en tres fases** —
requisitos, diseño y tareas — y recién después vino la implementación. Cada tarea referencia
los requisitos que satisface, y los requisitos usan criterios de aceptación en formato **EARS**.

**Evidencia en el repo:**
- [`.kiro/specs/requirements.md`](.kiro/specs/requirements.md) — 9 requerimientos (R1–R9) con historias de usuario y criterios EARS.
- [`.kiro/specs/design.md`](.kiro/specs/design.md) — decisiones técnicas justificadas, API, modelo de datos, flujo y estimación de costo.
- [`.kiro/specs/tasks.md`](.kiro/specs/tasks.md) — 16 tareas incrementales, cada una con `_Requerimientos: X.Y_` y marcadas como completadas.

El resultado: la implementación nunca improvisó. Cada módulo existía porque una tarea lo pedía,
y cada tarea trazaba a un requisito acordado.

---

## 2. Steering documents

El contexto permanente del proyecto vive en documentos de *steering* que Kiro incluye en cada
interacción. Son la fuente de verdad del producto, el stack y la estructura — y de hecho **moldearon
cada decisión** sin tener que repetir el contexto en cada prompt.

**Evidencia en el repo:**
- [`.kiro/steering/product.md`](.kiro/steering/product.md) — propósito, usuarios, principios.
- [`.kiro/steering/tech.md`](.kiro/steering/tech.md) — stack, convenciones de código, comandos.
- [`.kiro/steering/structure.md`](.kiro/steering/structure.md) — árbol del proyecto y separación de capas.

Un ejemplo concreto: cuando el perfil de AWS cambió, el steering `tech.md` se actualizó una vez
y toda la generación posterior lo respetó.

---

## 3. Hooks

Automaticé la gobernanza del repositorio con **agent hooks**: formato, linting, pruebas y
protección contra acciones destructivas, disparados por eventos del editor y del agente.

**Evidencia en el repo:**
- [`.kiro/hooks/py-quality-gate.json`](.kiro/hooks/py-quality-gate.json) — al terminar el turno del agente, corre `ruff` + `black --check` + `pytest`; si falla, no deja cerrar con código roto.
- [`.kiro/hooks/py-format-lint-on-save.json`](.kiro/hooks/py-format-lint-on-save.json) — formatea y lintea al guardar.
- [`.kiro/hooks/py-guard-destructive-commands.json`](.kiro/hooks/py-guard-destructive-commands.json) — bloquea `sam deploy`, `git push`, `rm -rf`, etc.
- [`.kiro/hooks/py-guard-secrets.json`](.kiro/hooks/py-guard-secrets.json) — impide escribir secretos.
- [`.kiro/hooks/py-test-for-new-module.json`](.kiro/hooks/py-test-for-new-module.json) y [`py-audit-tools.json`](.kiro/hooks/py-audit-tools.json).
- Scripts de soporte en [`scripts/hooks/`](scripts/hooks/).

Estos hooks **no fueron decorativos**: el guard de comandos destructivos bloqueó un `sam deploy`
manual y me obligó a desplegar por el pipeline, exactamente como manda la política del equipo.

---

## 4. Property-based testing

La solución tiene **120 pruebas**. Las de casos exhaustivos cubren validación de tipos,
enumeraciones, nulos, `qualityRules`, idempotencia, errores de negocio y todas las respuestas
HTTP. Y además hay **pruebas basadas en propiedades** (`hypothesis`): en lugar de ejemplos
elegidos a mano, `hypothesis` genera cientos de entradas aleatorias y verifica **invariantes**
que deben cumplirse para cualquier entrada posible.

**Evidencia en el repo:**
- [`tests/test_validation_properties.py`](tests/test_validation_properties.py) — 7 propiedades sobre `validate_rows`, entre ellas:
  - *Conservación*: `filas válidas + filas con error == total de filas` (cada fila es válida XOR inconsistente).
  - *Exclusión*: toda fila con una `edad` no numérica **siempre** queda fuera del Avro.
  - *Determinismo*: validar dos veces la misma entrada produce el mismo resultado.
  - *Completitud*: toda fila válida contiene exactamente los campos del esquema.
- Pruebas por casos en [`tests/test_validation.py`](tests/test_validation.py) y [`tests/test_conversion.py`](tests/test_conversion.py).

El property-based testing encontró su lugar natural en `validation.py`, el corazón de la
lógica: cada propiedad se ejecuta contra ~150–200 entradas generadas automáticamente, cubriendo
casos límite que un humano difícilmente enumeraría.

---

## 5. Powers

Empaqueté los estándares del equipo en un **Power** reutilizable: `csi-develop-standards`.
Un Power agrupa documentación, guías de trabajo (skills + steering) y servidores MCP, y se
activa por palabras clave.

**Evidencia en el repo** (carpeta [`powers/csi-develop-standards/`](powers/csi-develop-standards/)):
- [`plugin.json`](powers/csi-develop-standards/plugin.json) — metadatos y keywords (`spec`, `diseño`, `arquitectura`, `avro`, …).
- [`mcp.json`](powers/csi-develop-standards/mcp.json) — define 3 servidores MCP.
- `skills/` — 3 skills: `spec-authoring`, `csi-standards` (con 4 referencias técnicas) y `drawio-architecture`.
- `dev.kiro/steering/` — 2 steering del Power: `csi-standards.md` y `diagram-rules.md`.

Este Power fue el que convirtió el `design.md` de un diseño genérico en uno fundamentado en
estándares, documentación oficial y precios reales.

---

## 6. Model Context Protocol (MCP)

El Power bundlea **tres servidores MCP** que usé para fundamentar el diseño con datos reales,
no suposiciones:

- **`aws-docs`** — documentación oficial de AWS. La usé para justificar la idempotencia del worker
  (reintentos de invocación asíncrona de Lambda) y el formato del atributo `ttl` de DynamoDB.
- **`aws-pricing`** — precios reales de la Price List API para la estimación de costo del diseño.
- **`drawio-architect`** — generación de diagramas `.drawio`.

**Evidencia:** [`powers/csi-develop-standards/mcp.json`](powers/csi-develop-standards/mcp.json)
y las decisiones citadas con su fuente en [`.kiro/specs/design.md`](.kiro/specs/design.md).

---

## 7. Custom agents

Creé un agente especializado, **`spec-author`**, cuyo rol es dirigir el diseño (escribir specs
y diagramas) **sin implementar código de producción**. Sus permisos están acotados: escribe en
`.kiro/specs/` y `Documents/`, pero *pregunta* antes de tocar `src/` y *bloquea* despliegues.

**Evidencia en el repo:**
- [`.kiro/agents/spec-author.md`](.kiro/agents/spec-author.md) — front-matter con permisos por capacidad (`fs_write`, `shell`, `mcp`, `power`), carga de skills y mensaje de bienvenida.

El agente demuestra separación de responsabilidades: *quien diseña no implementa*, reforzado por
permisos, no solo por convención.

---

## Kiro Web, cloud sessions y cloud configuration — local vs. cloud

El desarrollo cruzó la frontera **local ↔ cloud** de forma deliberada:

- **Local**: implementación de los módulos, 113 pruebas con `pytest`, y validación en un
  **contenedor Lambda real** con `sam local invoke` — que destapó un defecto de empaquetado que
  los mocks no veían (los imports `from src.common` no resolvían en el runtime), resuelto con una
  **Lambda Layer**.
- **Cloud**: el despliegue corre por un **pipeline de CI/CD** ([`.github/workflows/ci-cd.yml`](.github/workflows/ci-cd.yml))
  que se autentica contra AWS por **OIDC** (sin credenciales estáticas) y despliega el stack con SAM.
  La configuración del rol y las policies está versionada en [`infra/oidc/`](infra/oidc/).

La solución quedó **operativa en AWS** y la validé end-to-end contra el entorno desplegado:
un `POST /conversions` devolvió `202`, el worker procesó 7 filas (4 válidas, 3 inconsistentes),
generó el Avro y el log, y el `GET` devolvió `COMPLETED` con los contadores correctos. Los
fixtures de esa prueba están en [`tests/e2e/`](tests/e2e/).

> **Para el video de demo**: muestro el flujo local (pytest + `sam local invoke`) frente al
> flujo cloud (merge → pipeline → `sam deploy` por OIDC → prueba contra la URL pública de la API).

---

## Entregable del Power (para empaquetar y compartir)

- **Repositorio público**: https://github.com/hectorlaris/csv-to-avro-api
- **Power `plugin.json`**: https://github.com/hectorlaris/csv-to-avro-api/blob/main/powers/csi-develop-standards/plugin.json
- **Qué bundlea el Power:**
  - **MCP** (`mcp.json`): `aws-docs`, `aws-pricing`, `drawio-architect`.
  - **Skills**: `spec-authoring`, `csi-standards` (+ 4 referencias: tech, structure, api-standards, error-handling), `drawio-architecture`.
  - **Steering del Power**: `csi-standards.md`, `diagram-rules.md`.

---

## Lo que me llevo

Kiro me permitió trabajar como ingeniero, no como mecanógrafo: **especificar antes de codificar**,
**gobernar con automatización**, **fundamentar decisiones con fuentes reales vía MCP**, **empaquetar
estándares reutilizables en un Power**, y **cruzar de local a cloud** con un pipeline que respeta las
políticas del equipo. El camino tuvo obstáculos reales — empaquetado de la layer, una cadena de siete
problemas de OIDC/despliegue diagnosticada con CloudTrail, y un bug de serialización de `Decimal` que
solo apareció contra DynamoDB real — y cada uno se resolvió con evidencia, sin atajos.

El resultado: una API serverless funcionando en AWS, con su spec, su gobernanza, su pipeline y su
documentación, toda versionada y reproducible.

🔗 **Repo**: https://github.com/hectorlaris/csv-to-avro-api

#KiroUniversity #AWS #Serverless #SpecDrivenDevelopment #MCP #DevOps
