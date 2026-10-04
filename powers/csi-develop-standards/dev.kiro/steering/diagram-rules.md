# Reglas de diagramas de arquitectura (CSI)

Guía de apoyo de la skill `drawio-architecture`. El MCP `drawio-architect` de este Power expone herramientas agrupadas por acción (`diagram`, `draw`, `style`, `layout`, `inspect`); cada una recibe un parámetro `action`. No uses nombres como `create_diagram` o `add_node`: no existen en este server.

## Contrato de validez de las conexiones

- La dirección sigue la acción real: lector → recurso, escritor → recurso, productor → consumidor.
- Una sola arista por par origen/destino. Si hay dos roles entre los mismos nodos, combínalos en una etiqueta ("lee/escribe").
- Todo servicio no transversal tiene al menos una conexión real. Prohibido: nodos huérfanos y aristas inventadas para "rellenar".
- Nunca conectes dos nodos que representen el mismo servicio canónico de AWS.
- Si un servicio solo resuelve nombres (p. ej. Route 53/DNS), va actor → DNS y actor → endpoint, nunca DNS → endpoint.

## Reglas de traducción de la arquitectura

- Incluye solo lo que está en el `design.md` o lo que confirmó el usuario. No agregues servicios "de buena práctica".
- Actores externos (el Cliente) fuera del grupo de la nube; servicios administrados de AWS dentro.
- Nombres oficiales de AWS ("Amazon DynamoDB", "AWS Lambda", "Amazon API Gateway"). Las etiquetas de los flujos, en español.
- Numera los pasos del flujo igual que el `design.md` para que diagrama y texto queden sincronizados.

## Layout y limpieza

- Construye en orden: grupos → nodos → conexiones. Luego `layout(action="polish")` para reorganizar, separar solapes, compactar y rerutear.
- Verifica con `inspect(action="overlaps")` e `inspect(action="cells")` antes de dar por bueno el diagrama. El resultado lo genera IA: revisa que no haya aristas cruzadas, etiquetas superpuestas ni nodos mal agrupados.
- Con más de 15 nodos, divide en páginas (`diagram(action="add_page")`).

## Entregable

- Guarda bajo `DRAWIO_FILES_ROOT` (carpeta `Documents/` del repo); usa rutas dentro de ella.
- No hay render a PNG (sin CLI de draw.io): el entregable es el `.drawio`. Enlázalo desde el `design.md` en modo spec.
- Nunca edites el XML del `.drawio` a mano; todo cambio pasa por las herramientas MCP (`draw(action="update_cells")` para ajustes puntuales).
