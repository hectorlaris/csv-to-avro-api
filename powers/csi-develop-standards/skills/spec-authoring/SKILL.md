---
name: spec-authoring
description: Redactar o actualizar un spec de CSI (requirements.md, design.md, tasks.md) con criterios de aceptación en formato EARS en español. Úsala al crear una feature nueva o evolucionar una existente antes de implementar.
---

# Redacción de specs CSI

Un spec son tres documentos en `.kiro/specs/` (o `.kiro/specs/<feature>/` si hay varias features): `requirements.md`, `design.md` y `tasks.md`. Se construyen **en ese orden** y cada uno se aprueba antes de pasar al siguiente. Antes de escribir, lee la skill `csi-standards` (stack, estructura, API, errores).

## Flujo

1. **Requirements.** Captura el problema y los criterios de aceptación en EARS. No propongas solución técnica aquí.
2. **Design.** Traduce los requerimientos a arquitectura, API, modelo de datos y flujo. Fundamenta las decisiones no triviales con el MCP `aws-docs` y estima el costo con `aws-pricing`. Si el design incluye arquitectura, usa la skill `drawio-architecture` para el diagrama.
3. **Tasks.** Deriva un plan incremental y accionable; cada tarea referencia los requerimientos que satisface.

Confirma con el usuario al cerrar cada documento antes de avanzar.

## requirements.md

- **Introducción**: contexto y objetivo en prosa.
- **Glosario**: términos del dominio (p. ej. *Esquema Avro*, *qualityRules*, *Repositorio oficial*).
- **Requerimientos numerados**, cada uno con:
  - **Historia de usuario**: "Como \<rol\>, quiero \<capacidad\>, para \<beneficio\>, porque \<motivo\>."
  - **Criterios de aceptación** en EARS (ver abajo), numerados.

### Formato EARS (en español)

- **CUANDO** \<evento\> **ENTONCES** EL sistema **DEBERÁ** \<respuesta\>.
- **SI** \<condición\> **ENTONCES** EL sistema **DEBERÁ** \<respuesta\>.
- **DADO** \<estado previo\> ... para condiciones de contexto.
- Para requisitos siempre activos: **EL sistema DEBERÁ** \<capacidad\>.

Cada criterio debe ser verificable, atómico y sin ambigüedad. Evita "rápido", "amigable", "si es posible".

## design.md

Secciones esperadas: **Visión general**, **Decisiones técnicas** (tabla Área / Decisión / Justificación), **Arquitectura** (componentes + diagrama), **API**, **Modelo de datos**, **Flujo de procesamiento**, **Consideraciones y riesgos**.

- Toda decisión técnica no obvia se justifica; si contradice un estándar de `csi-standards`, dilo explícitamente.
- Fundamenta con documentación oficial antes de fijar una topología (`search_documentation`, y `read_documentation` solo si hace falta).
- Mapea el diseño a los requerimientos que cubre.

## tasks.md

- Lista de tareas con checkbox, de abajo hacia arriba: andamiaje → lógica de negocio (`common/`, testeable) → handlers → infraestructura SAM → verificación.
- Cada tarea cierra con `_Requerimientos: X.Y, ..._`.
- Las sub-tareas usan numeración anidada (`2.1`, `2.2`).
- Solo trabajo de código/infra accionable por un agente; nada de "reunión" o "investigar" sin entregable.

## Reglas

- Español en todo el spec, incluidas etiquetas y mensajes de ejemplo.
- No inventes requerimientos ni servicios "de buena práctica": refleja lo acordado.
- Mantén los tres documentos coherentes entre sí; si cambia uno, revisa los otros.
