---
name: drawio-architecture
description: Dibujar diagramas de arquitectura AWS en draw.io con el MCP drawio-architect (crear, inspeccionar, pulir y guardar un .drawio). Úsala para la sección Arquitectura de un design.md o cuando pidan un diagrama de arquitectura.
---

# Diagramas de arquitectura con drawio-architect

El MCP `drawio-architect` de este Power expone **cinco herramientas agrupadas por acción**, cada una con un parámetro `action`:

| Herramienta | Acciones principales | Para qué |
|---|---|---|
| `diagram` | `create`, `save`, `load`, `add_page`, `get_xml`, `list` | Ciclo de vida del `.drawio` |
| `draw` | `add_vertices`, `add_edges`, `add_group`, `add_title`, `add_legend`, `update_cells`, `delete_cells`, `build_dag`, `build_full` | Contenido del diagrama |
| `style` | `build`, `apply_theme`, `list_vertex_presets`, `list_edge_presets`, `list_themes` | Estilos y temas |
| `layout` | `sugiyama`, `tree`, `flowchart`, `smart_connect`, `polish`, `relayout`, `compact`, `reroute_edges`, `resolve_overlaps` | Posicionamiento y limpieza |
| `inspect` | `cells`, `overlaps`, `ports`, `info` | Inspección de solo lectura |

> No existen herramientas sueltas tipo `create_diagram`, `add_node` o `drawio_validate_diagram`. Usa `diagram(action="create")`, `draw(action="add_vertices")`, etc. Este server **no** valida íconos oficiales de AWS ni los descarga: trabaja con formas y estilos genéricos de draw.io.

## 1. Elige el modo

| Modo | Cuándo | Blueprint | Confirmación | Archivo |
|---|---|---|---|---|
| **Spec** | Escribes la sección Arquitectura de un `design.md` | Las tablas de componentes y flujos del `design.md` | La aprobación del diseño. No hagas preguntas de descubrimiento | `Documents/<feature>-arquitectura.drawio` |
| **Suelto** | Piden un diagrama fuera de un spec | Descubrimiento con el usuario, una pregunta por turno | Resume el plan y pregunta "¿lo dibujo?" antes de construir | `Documents/<nombre>.drawio` |

## 2. Flujo

1. **Blueprint.** Antes de tocar el MCP, lista en texto: actores externos, servicios AWS (nombre oficial + rol) y conexiones en orden `origen → destino`, con estilo (`sync` / `async`), número de paso y etiqueta corta. Incluye solo lo que está en el spec o confirmó el usuario; no agregues servicios "de buena práctica". Lee el steering `diagram-rules.md` con `readSteering`.
2. **Fundamento.** Si un servicio o relación incierta cambia la topología, confírmalo con `search_documentation` del MCP `aws-docs` (y `read_documentation` solo si los fragmentos no alcanzan).
3. **Crea el lienzo.** `diagram(action="create", name="<nombre>")`.
4. **Construye el contenido.** En este orden: grupos (`draw` → `add_group`) → nodos (`draw` → `add_vertices`) → conexiones (`draw` → `add_edges`). Para un grafo dirigido sencillo puedes usar `draw(action="build_dag", edges=[...])` en una sola llamada; para posicionamiento manual completo, `build_full`. Añade título con `add_title` y, si ayuda, `add_legend`.
5. **Ordena y pule.** `layout(action="polish")` reorganiza, separa solapes, compacta y rerutea aristas de una vez. Afina con `relayout`, `resolve_overlaps` o `reroute_edges` si hace falta.
6. **Inspecciona.** `inspect(action="overlaps")` y `inspect(action="cells")` para detectar solapes o nodos mal ubicados. Corrige antes de dar por bueno; el diagrama lo genera IA y puede cruzar aristas o superponer etiquetas.
7. **Guarda.** `diagram(action="save", name="<nombre>", file_path="<ruta>")`. El server solo escribe bajo `DRAWIO_FILES_ROOT` (carpeta `Documents/` del repo): usa rutas dentro de ella.
8. **Presenta** una tabla de servicios y conexiones, enlaza el `.drawio` desde `design.md` (modo spec) y pregunta qué ajustarías. Para cambios de 1 a 3 nodos usa `draw(action="update_cells")`; para cambios mayores, repite desde el paso 4.

Con más de 15 nodos, propón dividir en páginas con `diagram(action="add_page")`.

## 3. Reglas

- Todo pasa por las herramientas MCP: nunca edites el XML del `.drawio` a mano.
- La dirección sigue la acción: lector → recurso, escritor → recurso, productor → consumidor.
- Una sola conexión por par origen/destino; si hay dos roles, combínalos en la etiqueta ("lee/escribe").
- Todo servicio no transversal tiene al menos una conexión real. Nada de nodos huérfanos ni conexiones inventadas.
- Actores externos (el Cliente) fuera del grupo de la nube; servicios administrados de AWS dentro.
- Nombres oficiales de AWS ("Amazon DynamoDB", no "DDB"). Las etiquetas de los flujos van en español, como el resto del repo.
- No hay render a imagen (sin CLI de draw.io instalado): el entregable es el `.drawio`.

## 4. Blueprint de referencia (este proyecto)

Para la arquitectura del `design.md` actual (CSV→Avro asíncrono):

- **Actor**: Cliente (externo).
- **Servicios**: API Gateway (REST), Lambda ApiHandler, Lambda ConversionWorker, Amazon S3 (repositorio), Amazon DynamoDB (auditoría).
- **Conexiones**: Cliente →(POST) API Gateway → ApiHandler; ApiHandler →(escribe PENDING) DynamoDB; ApiHandler →(invoca async) ConversionWorker; ConversionWorker →(lee/escribe) S3; ConversionWorker →(actualiza) DynamoDB; Cliente →(GET) API Gateway → ApiHandler →(lee) DynamoDB.
