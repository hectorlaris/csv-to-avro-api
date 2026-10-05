# Documento de Requerimientos

## Introducción

Este documento define los requerimientos para una solución **serverless** sobre el stack de AWS que expone una **REST API** (API Gateway + Lambda) capaz de tomar un archivo **CSV** alojado en un bucket **S3** y convertirlo a formato **Apache Avro** aplicando un esquema personalizado definido en JSON.

La solución está orientada al Cliente del Sistema Escolaris, responsable de reportar información a entidades externas. Actualmente ese proceso es manual, lo que introduce retrasos y riesgo de error humano. El objetivo es automatizar y hacer confiable la generación de archivos Avro a partir de los CSV oficiales, con validación contra esquema, registro de inconsistencias y auditoría.

El procesamiento es **asíncrono**: el cliente solicita la conversión, recibe un identificador de seguimiento y consulta el estado del proceso mediante sondeo (polling) hasta su finalización.

## Glosario

- **Cómputo serverless de AWS**: modelo que permite construir y ejecutar aplicaciones sin administrar servidores, con escalado automático, alta disponibilidad y facturación por uso (pay-per-use).
- **Cliente**: usuario del Sistema Escolaris responsable del proceso de reporte de información a entidades externas.
- **Apache Avro**: formato de datos binario ampliamente usado en arquitecturas de streaming de eventos, orientado a serialización compacta y evolución de esquemas.
- **Esquema Avro**: definición formal, escrita en JSON, que estructura los datos indicando con precisión los campos, nombres y tipos de datos que contiene cada registro.
- **Repositorio oficial**: bucket S3 que actúa como única fuente de verdad para los archivos CSV de datos y los esquemas Avro en JSON.
- **qualityRules**: reglas de calidad de datos adicionales, definidas junto al esquema, que un registro debe cumplir para ser considerado válido.

## Convención de criterios de aceptación

Los criterios de aceptación se expresan en formato EARS (en español):
- **CUANDO** \<evento\> **ENTONCES** el sistema **DEBERÁ** \<respuesta\>.
- **SI** \<condición\> **ENTONCES** el sistema **DEBERÁ** \<respuesta\>.
- **DADO** \<estado previo\> ... para condiciones de contexto.

---

## Requerimientos

### Requerimiento 1: Repositorio único de archivos CSV y esquemas Avro

**Historia de usuario:**
Como Cliente del Sistema Escolaris responsable del reporte de información a entidades externas,
quiero un repositorio en S3 con mis archivos de datos CSV y sus esquemas Avro en JSON actualizados y sincronizados,
para contar con una única fuente de verdad sobre la versión vigente de los archivos y esquemas,
porque será la fuente oficial para generar los archivos Avro que entrego a las entidades solicitantes de forma segura y eficiente.

#### Criterios de aceptación
1. EL sistema DEBERÁ mantener en el repositorio oficial (bucket S3) los archivos `.csv` de datos y sus correspondientes esquemas Avro en `.json`.
2. CUANDO se cargue o actualice un archivo CSV o un esquema JSON en el repositorio, ENTONCES EL sistema DEBERÁ usar el objeto vigente en su prefijo S3 (`datos/` para CSV, `schemas/` para esquemas), entendido como la última escritura que sobrescribe a la anterior, sin mantener historial de versiones.
3. EL sistema DEBERÁ asociar cada archivo CSV con el esquema Avro que le corresponde por convención de nombre (`datos/{nombre_base}.csv` ↔ `schemas/{nombre_base}.json`), de modo que la conversión use siempre la definición correcta.
4. SI el request incluye el campo opcional `schemaKey`, ENTONCES EL sistema DEBERÁ usar ese esquema en lugar del derivado por la convención de nombre.

### Requerimiento 2: Generación automática de archivos Avro

**Historia de usuario:**
Como Cliente del Sistema Escolaris responsable del reporte de información a entidades externas,
quiero que la generación de los archivos Avro se realice de manera automática a partir de los archivos CSV alojados en el repositorio oficial, aplicando la definición del esquema JSON correspondiente,
para agilizar y hacer más eficiente la entrega de dichos archivos a las entidades que los requieren,
porque mi oficina es responsable de garantizar la entrega oportuna y correcta de estos reportes, y el proceso manual actual introduce retrasos y riesgo de error humano.

#### Criterios de aceptación
1. CUANDO se solicite la conversión de un archivo CSV (`nombre_archivo_procesado`) a través de la REST API, ENTONCES EL sistema DEBERÁ validar cada registro del CSV contra su esquema Avro, detectando y registrando todas las inconsistencias (tipos de dato, valores fuera de enumeraciones, campos nulos no permitidos e incumplimiento de `qualityRules`).
2. SI un registro presenta al menos una inconsistencia con el esquema, ENTONCES EL sistema DEBERÁ excluir ese registro de la generación del archivo Avro y registrar el detalle del error.
3. CUANDO finalice la validación, ENTONCES EL sistema DEBERÁ generar un archivo de log de inconsistencias en el prefijo `logs/` con el nombre `logs/{nombre_base}_{yyyymmdd}.csv`, accesible para revisión, que incluya, como mínimo:
   - Total de filas procesadas.
   - Filas convertidas exitosamente.
   - Filas con errores.
   - Detalle de errores por fila y columna, con información suficiente para identificar el registro y el campo afectado.
4. DADO que existen registros válidos tras la validación, CUANDO se genere el archivo Avro, ENTONCES EL sistema DEBERÁ producir un archivo Avro válido en el prefijo `output/` con el nombre `output/{nombre_base}_{yyyymmdd}.avro`, que contenga únicamente los registros aprobados, aplicando el esquema personalizado.
5. SI no existe ningún registro válido tras la validación, ENTONCES EL sistema DEBERÁ omitir la creación del archivo Avro e informar el resultado indicando que no hubo registros aprobados.

### Requerimiento 3: Serialización y formato de las respuestas de la API

**Historia de usuario:**
Como desarrollador integrador,
quiero que la API retorne respuestas en formato JSON consistente y bien estructurado,
para poder integrar el sistema con otras aplicaciones de forma confiable.

#### Criterios de aceptación
1. EL sistema DEBERÁ serializar todas las respuestas de la API en JSON con codificación UTF-8, incluyendo el header `Content-Type: application/json; charset=utf-8`.
2. EL sistema DEBERÁ omitir del cuerpo de la respuesta los campos cuyo valor sea nulo, con la excepción de `avroKey`, que PODRÁ retornarse como `null` explícito cuando no se haya generado archivo Avro.
3. CUANDO ocurra un error, ENTONCES EL sistema DEBERÁ retornar una respuesta JSON con un código de estado HTTP apropiado y un mensaje de error descriptivo.

### Requerimiento 4: Auditoría de la ejecución del proceso de generación

**Historia de usuario:**
Como administrador del sistema,
quiero disponer de un mecanismo de auditoría de los archivos Avro generados,
para saber qué archivos se han generado, en qué fecha, de qué tamaño, con cuántas filas procesadas y cuántas filas con errores.

#### Criterios de aceptación
1. CUANDO finalice la generación de un archivo Avro, ENTONCES EL sistema DEBERÁ registrar un asiento de auditoría con, como mínimo: nombre del archivo generado, fecha y hora de generación, tamaño del archivo, número de filas procesadas y número de filas con errores.
2. EL sistema DEBERÁ conservar los registros de auditoría de forma persistente y consultable.

### Requerimiento 5: Arquitectura serverless (escalado automático y pago por uso)

**Historia de usuario:**
Como desarrollador integrador,
quiero que la solución se implemente y despliegue sobre una arquitectura serverless,
para no administrar servidores y pagar únicamente por el uso real.

#### Criterios de aceptación
1. EL sistema DEBERÁ implementarse sin requerir administración de servidores, usando servicios gestionados de AWS bajo el modelo de facturación por uso (pay-per-use).
2. EL sistema DEBERÁ soportar escalado automático en función de la demanda.

### Requerimiento 6: Infraestructura en AWS definida con SAM

**Historia de usuario:**
Como operador,
quiero que toda la infraestructura esté definida en una plantilla SAM,
para poder desplegar y eliminar la aplicación completa de forma reproducible.

#### Criterios de aceptación
1. LA plantilla SAM DEBERÁ definir todos los recursos de AWS de la solución: el bucket S3 (repositorio oficial), la REST API en API Gateway (endpoints `POST /conversions` y `GET /conversions/{auditId}`), la función Lambda que atiende la API, la función Lambda de conversión (CSV a Avro) invocada de forma asíncrona y la tabla DynamoDB de auditoría.
2. EL bucket S3 NO DEBERÁ ser de acceso público; el acceso DEBERÁ realizarse únicamente mediante políticas y roles de IAM con privilegios mínimos.
3. LA tabla DynamoDB de auditoría DEBERÁ tener un atributo TTL (`ttl`) para permitir la expiración automática de asientos antiguos, y DEBERÁ permitir el registro persistente de los asientos definidos en el Requerimiento 4.
4. SI el stack ya existe CUANDO se despliegue la plantilla SAM, ENTONCES EL despliegue DEBERÁ actualizar los recursos existentes sin pérdida de datos.
5. TODOS los comandos de AWS CLI y SAM CLI DEBERÁN usar `--profile developer` y `--region us-east-1`.
### Requerimiento 7: Contrato asíncrono de la REST API (solicitud y seguimiento)

**Historia de usuario:**
Como desarrollador integrador,
quiero solicitar una conversión y obtener un identificador de seguimiento para consultar el estado del proceso,
para integrar la conversión de forma asíncrona sin bloquear mi aplicación mientras finaliza,
porque el procesamiento del CSV puede tardar y necesito un contrato predecible de solicitud y sondeo (polling).

#### Criterios de aceptación
1. CUANDO se reciba una solicitud válida en `POST /conversions`, ENTONCES EL sistema DEBERÁ crear un asiento de auditoría con un `auditId` único y estado inicial `PENDING`, e invocar al worker de conversión de forma asíncrona (`InvocationType=Event`).
2. CUANDO se acepte la solicitud en `POST /conversions`, ENTONCES EL sistema DEBERÁ responder de inmediato con un código HTTP `202 Accepted` y un cuerpo JSON que incluya al menos el `auditId` y el estado inicial, sin esperar a que finalice la conversión.
3. CUANDO se consulte `GET /conversions/{auditId}` para un `auditId` existente, ENTONCES EL sistema DEBERÁ responder con HTTP `200 OK` y el estado actual del proceso, que DEBERÁ ser uno de: `PENDING`, `PROCESSING`, `COMPLETED`, `NO_VALID_RECORDS` o `ERROR`.
4. CUANDO el estado consultado sea `COMPLETED`, ENTONCES EL sistema DEBERÁ incluir en la respuesta la referencia al archivo Avro generado (`avroKey`) y el resumen de filas procesadas, convertidas y con errores.
5. CUANDO el estado consultado sea `NO_VALID_RECORDS`, ENTONCES EL sistema DEBERÁ retornar `avroKey` como `null` explícito y el resumen de la validación.
6. SI se consulta `GET /conversions/{auditId}` con un `auditId` inexistente, ENTONCES EL sistema DEBERÁ responder con HTTP `404 Not Found` y un mensaje de error descriptivo en JSON.

### Requerimiento 8: Idempotencia del worker de conversión

**Historia de usuario:**
Como operador,
quiero que el worker de conversión sea idempotente respecto al `auditId`,
para que los reintentos automáticos de la invocación asíncrona no dupliquen ni corrompan el estado del proceso,
porque la invocación `InvocationType=Event` de Lambda puede reintentar la ejecución ante fallos transitorios.

#### Criterios de aceptación
1. CUANDO el worker se ejecute más de una vez para el mismo `auditId`, ENTONCES EL sistema DEBERÁ producir el mismo resultado final sin duplicar asientos de auditoría ni archivos de salida.
2. CUANDO se reprocese el mismo CSV el mismo día, ENTONCES EL sistema DEBERÁ sobrescribir los archivos `output/{nombre_base}_{yyyymmdd}.avro` y `logs/{nombre_base}_{yyyymmdd}.csv` existentes, sin crear versiones adicionales.
3. SI un reintento ocurre sobre un `auditId` cuyo proceso ya finalizó (`COMPLETED`, `NO_VALID_RECORDS` o `ERROR`), ENTONCES EL sistema DEBERÁ evitar reejecutar la conversión y conservar el estado final ya registrado.

### Requerimiento 9: Errores de negocio y su registro en la auditoría

**Historia de usuario:**
Como administrador del sistema,
quiero que los errores de negocio queden identificados con un código y registrados en el asiento de auditoría,
para diagnosticar por qué una conversión no se completó y comunicarlo de forma consultable,
porque en el flujo asíncrono el error no se devuelve en la respuesta inicial sino que se consulta por `GET /conversions/{auditId}`.

#### Criterios de aceptación
1. SI el archivo CSV solicitado no existe en el prefijo `datos/`, ENTONCES EL sistema DEBERÁ registrar en el asiento de auditoría el estado `ERROR` con el código de error de negocio `CSV_NOT_FOUND`.
2. SI el esquema Avro asociado no existe en el prefijo `schemas/`, ENTONCES EL sistema DEBERÁ registrar en el asiento de auditoría el estado `ERROR` con el código de error de negocio `SCHEMA_NOT_FOUND`.
3. SI el esquema Avro existe pero no es un JSON válido o no define una estructura de esquema válida, ENTONCES EL sistema DEBERÁ registrar en el asiento de auditoría el estado `ERROR` con el código de error de negocio `INVALID_SCHEMA`.
4. CUANDO se consulte `GET /conversions/{auditId}` para un proceso en estado `ERROR`, ENTONCES EL sistema DEBERÁ incluir en la respuesta JSON el código de error de negocio y un mensaje descriptivo.
