# Configuración OIDC para el pipeline de despliegue

Estos archivos definen el rol IAM que **GitHub Actions** asume mediante **OIDC**
(sin credenciales estáticas) para desplegar el stack `avro-rest-api-gateway` a AWS.

> Todos los comandos usan el perfil `AdministratorAccess-962682390364` y la región `us-east-1`.
> Ejecútalos una sola vez al configurar el pipeline. Requieren permisos de administración de IAM.

## Archivos

| Archivo | Propósito |
|---|---|
| `trust-policy.json` | Quién puede asumir el rol: solo el workflow desde `main` del repo `hectorlaris/csv-to-avro-api` |
| `deploy-permissions-policy.json` | Permisos mínimos para desplegar el stack (CloudFormation, Lambda, API Gateway, DynamoDB, SQS, IAM acotado) |

## Paso 1 — Proveedor OIDC de GitHub (una vez por cuenta)

Verifica si ya existe:

```bash
aws iam list-open-id-connect-providers --profile AdministratorAccess-962682390364
```

Si no existe uno con `token.actions.githubusercontent.com`, créalo:

```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 \
  --profile AdministratorAccess-962682390364
```

## Paso 2 — Rol IAM

```bash
aws iam create-role \
  --role-name github-actions-avro-deploy \
  --assume-role-policy-document file://infra/oidc/trust-policy.json \
  --description "Rol asumido por GitHub Actions (OIDC) para desplegar avro-rest-api-gateway" \
  --profile AdministratorAccess-962682390364

aws iam put-role-policy \
  --role-name github-actions-avro-deploy \
  --policy-name avro-deploy-permissions \
  --policy-document file://infra/oidc/deploy-permissions-policy.json \
  --profile AdministratorAccess-962682390364

aws iam get-role \
  --role-name github-actions-avro-deploy \
  --query "Role.Arn" --output text \
  --profile AdministratorAccess-962682390364
```

## Paso 3 — Secret en GitHub

Con el ARN del rol:

```bash
gh secret set AWS_DEPLOY_ROLE_ARN \
  --body "arn:aws:iam::962682390364:role/github-actions-avro-deploy" \
  --repo hectorlaris/csv-to-avro-api
```

## Notas de seguridad

- La trust policy restringe el `sub` a `repo:hectorlaris/csv-to-avro-api:ref:refs/heads/main`.
  Ninguna otra rama ni repositorio puede asumir el rol.
- Los permisos están acotados por ARN a los recursos de **este** proyecto.
  La excepción es Lambda (`Resource: *`), requerida por cómo CloudFormation nombra
  algunos recursos durante el despliegue.
- Si el deploy debe ejecutarse bajo el environment `production` con aprobación manual,
  ajustar el `sub` de la trust policy a `repo:hectorlaris/csv-to-avro-api:environment:production`.
