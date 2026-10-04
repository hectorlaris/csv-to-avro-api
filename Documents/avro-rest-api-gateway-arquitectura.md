# Arquitectura — Avro REST API Gateway

> Diagrama de arquitectura del proyecto en formato Mermaid. Alternativa al `.drawio`
> canónico (T-04 BLOCKED hasta que el binario `aim` del MCP `drawio-architect` esté
> disponible). La numeración de los pasos coincide con la sección "Flujo de procesamiento"
> del `design.md`.

## Diagrama de componentes y flujo

```mermaid
flowchart LR
    Cliente(["Cliente<br/>(Sistema Escolaris)"])

    subgraph AWS["Nube AWS — us-east-1"]
        APIGW["Amazon API Gateway<br/>(REST API)<br/>POST /conversions<br/>GET /conversions/{auditId}"]
        ApiFn["AWS Lambda<br/>ApiFunction<br/>(Python 3.12)"]
        Worker["AWS Lambda<br/>ConversionWorkerFunction<br/>(Python 3.12, async)"]
        DDB[("Amazon DynamoDB<br/>Auditoría<br/>on-demand + TTL")]
        S3[("Amazon S3<br/>datos / schemas<br/>output / logs")]
        DLQ["Amazon SQS<br/>Dead-letter queue"]
    end

    Cliente -->|"1 POST /conversions"| APIGW
    Cliente -->|"8 GET /conversions/auditId"| APIGW
    APIGW -->|"enruta"| ApiFn

    ApiFn -->|"2 escribe asiento PENDING"| DDB
    ApiFn -->|"3 invoca async (Event)"| Worker
    ApiFn -->|"8b lee asiento"| DDB

    Worker -->|"4 marca PROCESSING"| DDB
    Worker -->|"5 lee CSV + esquema"| S3
    Worker -->|"6 escribe Avro + log"| S3
    Worker -->|"7 actualiza estado final"| DDB
    Worker -.->|"invocaciones agotadas"| DLQ

    classDef lambda fill:#FF9900,stroke:#232F3E,color:#232F3E;
    classDef storage fill:#3F8624,stroke:#232F3E,color:#fff;
    classDef gateway fill:#CC2264,stroke:#232F3E,color:#fff;
    classDef queue fill:#C925D1,stroke:#232F3E,color:#fff;
    classDef actor fill:#232F3E,stroke:#000,color:#fff;

    class ApiFn,Worker lambda;
    class DDB,S3 storage;
    class APIGW gateway;
    class DLQ queue;
    class Cliente actor;
```

## Leyenda del flujo

| # | Paso | Tipo |
|---|---|---|
| 1 | El cliente solicita la conversión en `POST /conversions` | sync |
| 2 | `ApiFunction` crea el asiento de auditoría en estado `PENDING` | sync |
| 3 | `ApiFunction` invoca al worker con `InvocationType=Event` | async |
| 4 | El worker marca el asiento como `PROCESSING` | sync |
| 5 | El worker lee el CSV y el esquema desde S3 | sync |
| 6 | El worker escribe el Avro (si hay filas válidas) y el log de inconsistencias | sync |
| 7 | El worker actualiza el asiento al estado final (`COMPLETED`, `NO_VALID_RECORDS` o `ERROR`) | sync |
| 8 | El cliente consulta el estado en `GET /conversions/{auditId}` (polling) | sync |
| — | Si el worker agota reintentos, el evento se envía a la DLQ (SQS) para diagnóstico | async |

## Estados del procesamiento

```mermaid
stateDiagram-v2
    [*] --> PENDING: POST /conversions
    PENDING --> PROCESSING: worker inicia
    PROCESSING --> COMPLETED: hay filas válidas
    PROCESSING --> NO_VALID_RECORDS: sin filas válidas
    PROCESSING --> ERROR: CSV_NOT_FOUND /<br/>SCHEMA_NOT_FOUND /<br/>INVALID_SCHEMA
    COMPLETED --> [*]
    NO_VALID_RECORDS --> [*]
    ERROR --> [*]
```

## Notas

- El bucket S3 **no es público**; el acceso es solo por roles IAM con privilegios mínimos.
- La tabla DynamoDB usa el atributo `ttl` (epoch Unix en segundos) para expirar asientos antiguos.
- El worker es **idempotente** respecto al `auditId`: si el asiento ya está en estado final, no reejecuta.
- Para renderizar: pega los bloques Mermaid en [mermaid.live](https://mermaid.live) o en cualquier
  visor compatible (VS Code con extensión Mermaid, GitHub, etc.).
