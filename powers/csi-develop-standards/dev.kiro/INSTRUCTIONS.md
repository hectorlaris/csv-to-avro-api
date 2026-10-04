# CSI Develop Standards

Estándares de desarrollo del equipo CSI para el proyecto **Avro REST API Gateway**: specs con EARS, diseño fundamentado con AWS Docs y Pricing, diagramas de arquitectura en draw.io y APIs Lambda sobre AWS serverless (Python 3.12 + SAM).

Empieza por el steering `csi-standards.md`, que resume las reglas de oro. Después abre la skill de la tarea que tienes entre manos. Las skills se leen con `readSkill` y el steering con `readSteering` (power `csi-develop-standards`).

## Qué skill usar

| Tarea | Skill | Steering de apoyo |
|---|---|---|
| Cualquier cambio en el repo (diseñar, implementar, revisar) | `csi-standards` | `csi-standards.md` |
| Redactar o actualizar un spec (requirements / design / tasks) | `spec-authoring` | `csi-standards.md` |
| Diagrama de arquitectura, dentro de un `design.md` o suelto | `drawio-architecture` | `diagram-rules.md` |

## Servidores MCP

| Servidor | Para qué | Herramientas clave |
|---|---|---|
| `aws-docs` | Documentación oficial de AWS para fundamentar decisiones de diseño | `search_documentation`, `read_documentation` (solo si los fragmentos no alcanzan) |
| `aws-pricing` | Estimar el costo del diseño antes de implementar | `get_pricing_service_codes` → `get_pricing_service_attributes` → `get_pricing_attribute_values` → `get_pricing`; `generate_cost_report` |
| `drawio-architect` | Crear, inspeccionar y pulir diagramas `.drawio` | `diagram`, `draw`, `style`, `layout`, `inspect` |

> El server `drawio-architect` de este Power expone herramientas **agrupadas por acción** (`diagram`, `draw`, `style`, `layout`, `inspect`), cada una con un parámetro `action`. No existen herramientas sueltas tipo `create_diagram` o `add_node`: usa `diagram(action="create")`, `draw(action="add_vertices")`, etc. La skill `drawio-architecture` detalla el flujo.

## Contexto del proyecto

- **Stack**: AWS serverless — API Gateway (REST), Lambda (Python 3.12), S3 (repositorio oficial), DynamoDB (auditoría on-demand con `ttl`). IaC con AWS SAM.
- **Dominio**: conversión asíncrona de CSV (en S3) a Apache Avro con validación contra esquema y `qualityRules`, log de inconsistencias y asiento de auditoría.
- **Perfil/región**: todos los comandos de AWS CLI y SAM CLI usan `--profile developer` y `--region us-east-1`.
- **Fuente de verdad del proyecto**: los steering del repo en `.kiro/steering/` (`product.md`, `tech.md`, `structure.md`) y los specs en `.kiro/specs/`. Este Power no los reemplaza: los complementa con el *cómo* de cada tarea.
