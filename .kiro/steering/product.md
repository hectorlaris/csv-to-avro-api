# Producto

## Propósito

Solución **serverless** en AWS que expone una **REST API** (API Gateway + Lambda) para convertir archivos **CSV** alojados en un bucket **S3** a formato **Apache Avro**, aplicando un esquema personalizado definido en JSON.

El cliente invoca un endpoint indicando el archivo CSV a procesar; el sistema valida cada registro contra su esquema Avro, genera el archivo Avro con los registros aprobados, produce un log de inconsistencias y deja un registro de auditoría de la ejecución.

## Problema que resuelve

El proceso actual de generación de archivos Avro para reportar información a entidades externas es **manual**, lo que introduce retrasos y riesgo de error humano. Esta solución automatiza y hace confiable esa generación, con validación contra esquema, trazabilidad de errores y auditoría.

## Usuarios

- **Cliente del Sistema Escolaris**: responsable del reporte de información a entidades externas. Es quien solicita la conversión y consume los archivos Avro generados.
- **Administrador del sistema**: consulta la auditoría para saber qué archivos se generaron, cuándo, de qué tamaño y con cuántas filas procesadas y con errores.
- **Desarrollador integrador**: integra la REST API desde otras aplicaciones y espera respuestas JSON consistentes.
- **Operador**: despliega y mantiene la infraestructura de forma reproducible mediante SAM.

## Valor central

- **Automatización**: elimina el proceso manual de conversión CSV a Avro.
- **Confiabilidad**: valida los datos contra un esquema formal y excluye los registros inconsistentes.
- **Trazabilidad**: registra el detalle de errores por fila y columna, y audita cada ejecución.
- **Eficiencia operativa**: arquitectura serverless con escalado automático y pago por uso, sin administración de servidores.

## Principios de producto

- **Única fuente de verdad**: el repositorio S3 mantiene los CSV y sus esquemas Avro vigentes y asociados entre sí.
- **Solo datos válidos en el Avro**: el archivo Avro contiene únicamente registros que cumplen el esquema y las reglas de calidad; los inconsistentes se excluyen y se reportan.
- **Nada silencioso**: toda ejecución produce log de resultados y asiento de auditoría, incluso cuando no hay registros válidos.
- **Respuestas predecibles**: la API responde siempre en JSON UTF-8, omitiendo campos nulos y con errores descriptivos.

## Fuera de alcance (por ahora)

- Disparo automático de la conversión por evento de carga en S3 (el disparador definido es la REST API).
- Interfaz de usuario / frontend.
- Estándares de dominio bancario (p. ej. BIAN), que no aplican a este proyecto.
