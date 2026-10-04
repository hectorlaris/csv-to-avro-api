"""Pruebas de integración para src/api_handler/app.py."""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("AUDIT_TABLE", "avro-api-audit-test")
os.environ.setdefault("AUDIT_TTL_DAYS", "90")
os.environ.setdefault("WORKER_FUNCTION_NAME", "avro-worker-function-test")
os.environ.setdefault("REPOSITORY_BUCKET", "avro-api-repository-test")

from app import lambda_handler  # noqa: E402
from common import audit  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CONTENT_TYPE = "application/json; charset=utf-8"


def _event_post(body: dict | None = None, raw_body: str | None = None) -> dict:
    """Construye un evento API Gateway para POST /conversions."""
    return {
        "httpMethod": "POST",
        "path": "/conversions",
        "body": raw_body if raw_body is not None else json.dumps(body or {}),
    }


def _event_get(audit_id: str) -> dict:
    """Construye un evento API Gateway para GET /conversions/{auditId}."""
    return {
        "httpMethod": "GET",
        "path": f"/conversions/{audit_id}",
    }


def _body(response: dict) -> dict:
    """Deserializa el body JSON de la respuesta."""
    return json.loads(response["body"])


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_audit():
    """Parchea common.audit usado por el handler."""
    with patch("app.audit") as m:
        m.STATUS_PENDING = audit.STATUS_PENDING
        m.STATUS_PROCESSING = audit.STATUS_PROCESSING
        m.STATUS_COMPLETED = audit.STATUS_COMPLETED
        m.STATUS_NO_VALID_RECORDS = audit.STATUS_NO_VALID_RECORDS
        m.STATUS_ERROR = audit.STATUS_ERROR
        m.create_audit_entry.return_value = "audit-test-id"
        yield m


@pytest.fixture()
def mock_lambda_client():
    """Parchea boto3.client('lambda') para evitar invocaciones reales."""
    with patch("app.boto3") as mock_boto3:
        lambda_client = MagicMock()
        mock_boto3.client.return_value = lambda_client
        yield lambda_client


# ---------------------------------------------------------------------------
# POST /conversions — casos exitosos
# ---------------------------------------------------------------------------


class TestPostConversions:
    """Pruebas para POST /conversions."""

    def test_202_con_csv_key_presente(
        self, mock_audit: MagicMock, mock_lambda_client: MagicMock
    ) -> None:
        """POST con csvKey válido debe retornar 202 con auditId y status PENDING."""
        event = _event_post({"csvKey": "datos/alumnos.csv"})
        response = lambda_handler(event, None)

        assert response["statusCode"] == 202
        body = _body(response)
        assert body["status"] == "PENDING"
        assert body["auditId"] == "audit-test-id"
        assert "/conversions/audit-test-id" in body["statusUrl"]

    def test_content_type_correcto(
        self, mock_audit: MagicMock, mock_lambda_client: MagicMock
    ) -> None:
        """La respuesta debe incluir Content-Type: application/json; charset=utf-8."""
        event = _event_post({"csvKey": "datos/alumnos.csv"})
        response = lambda_handler(event, None)
        assert response["headers"]["Content-Type"] == CONTENT_TYPE

    def test_invoca_worker_asincrono(
        self, mock_audit: MagicMock, mock_lambda_client: MagicMock
    ) -> None:
        """Debe invocar el worker con InvocationType=Event."""
        event = _event_post({"csvKey": "datos/alumnos.csv"})
        lambda_handler(event, None)
        mock_lambda_client.invoke.assert_called_once()
        call_kwargs = mock_lambda_client.invoke.call_args[1]
        assert call_kwargs["InvocationType"] == "Event"

    def test_payload_del_worker_contiene_audit_id_y_csv_key(
        self, mock_audit: MagicMock, mock_lambda_client: MagicMock
    ) -> None:
        """El payload al worker debe incluir auditId y csvKey."""
        event = _event_post({"csvKey": "datos/alumnos.csv"})
        lambda_handler(event, None)
        call_kwargs = mock_lambda_client.invoke.call_args[1]
        payload = json.loads(call_kwargs["Payload"])
        assert payload["auditId"] == "audit-test-id"
        assert payload["csvKey"] == "datos/alumnos.csv"

    def test_schema_key_opcional_se_incluye_en_payload(
        self, mock_audit: MagicMock, mock_lambda_client: MagicMock
    ) -> None:
        """Si se incluye schemaKey, debe aparecer en el payload del worker."""
        event = _event_post(
            {"csvKey": "datos/alumnos.csv", "schemaKey": "schemas/custom.json"}
        )
        lambda_handler(event, None)
        call_kwargs = mock_lambda_client.invoke.call_args[1]
        payload = json.loads(call_kwargs["Payload"])
        assert payload["schemaKey"] == "schemas/custom.json"

    def test_crea_asiento_pending_en_dynamodb(
        self, mock_audit: MagicMock, mock_lambda_client: MagicMock
    ) -> None:
        """Debe llamar a create_audit_entry antes de invocar el worker."""
        event = _event_post({"csvKey": "datos/alumnos.csv"})
        lambda_handler(event, None)
        mock_audit.create_audit_entry.assert_called_once()


# ---------------------------------------------------------------------------
# POST /conversions — casos de error
# ---------------------------------------------------------------------------


class TestPostConversionesErrores:
    """Pruebas de validación del body en POST /conversions."""

    def test_400_sin_csv_key(
        self, mock_audit: MagicMock, mock_lambda_client: MagicMock
    ) -> None:
        """POST sin csvKey debe retornar 400 con mensaje descriptivo."""
        event = _event_post({})
        response = lambda_handler(event, None)
        assert response["statusCode"] == 400
        body = _body(response)
        assert "csvKey" in body["message"]

    def test_400_body_malformado(
        self, mock_audit: MagicMock, mock_lambda_client: MagicMock
    ) -> None:
        """POST con JSON malformado debe retornar 400."""
        event = _event_post(raw_body="{ no es json }")
        response = lambda_handler(event, None)
        assert response["statusCode"] == 400

    def test_400_body_nulo(
        self, mock_audit: MagicMock, mock_lambda_client: MagicMock
    ) -> None:
        """POST con body None debe retornar 400."""
        event = {"httpMethod": "POST", "path": "/conversions", "body": None}
        response = lambda_handler(event, None)
        assert response["statusCode"] == 400

    def test_no_invoca_worker_si_falta_csv_key(
        self, mock_audit: MagicMock, mock_lambda_client: MagicMock
    ) -> None:
        """Si falta csvKey no debe invocarse el worker ni crearse el asiento."""
        event = _event_post({})
        lambda_handler(event, None)
        mock_lambda_client.invoke.assert_not_called()
        mock_audit.create_audit_entry.assert_not_called()


# ---------------------------------------------------------------------------
# GET /conversions/{auditId} — estado PENDING
# ---------------------------------------------------------------------------


class TestGetConversionPending:
    """GET con auditId en estado PENDING."""

    def test_200_con_estado_pending(self, mock_audit: MagicMock) -> None:
        """Debe retornar 200 con status PENDING."""
        mock_audit.get_audit_entry.return_value = {
            "auditId": "audit-1",
            "status": "PENDING",
        }
        response = lambda_handler(_event_get("audit-1"), None)
        assert response["statusCode"] == 200
        assert _body(response)["status"] == "PENDING"


# ---------------------------------------------------------------------------
# GET /conversions/{auditId} — estado PROCESSING
# ---------------------------------------------------------------------------


class TestGetConversionProcessing:
    """GET con auditId en estado PROCESSING."""

    def test_200_con_estado_processing(self, mock_audit: MagicMock) -> None:
        """Debe retornar 200 con status PROCESSING."""
        mock_audit.get_audit_entry.return_value = {
            "auditId": "audit-1",
            "status": "PROCESSING",
        }
        response = lambda_handler(_event_get("audit-1"), None)
        assert response["statusCode"] == 200
        assert _body(response)["status"] == "PROCESSING"


# ---------------------------------------------------------------------------
# GET /conversions/{auditId} — estado COMPLETED
# ---------------------------------------------------------------------------


class TestGetConversionCompleted:
    """GET con auditId en estado COMPLETED."""

    def test_200_con_avro_key_y_contadores(self, mock_audit: MagicMock) -> None:
        """Debe retornar 200 con avroKey, logKey y contadores."""
        mock_audit.get_audit_entry.return_value = {
            "auditId": "audit-1",
            "status": "COMPLETED",
            "avroKey": "output/alumnos_20261004.avro",
            "logKey": "logs/alumnos_20261004.csv",
            "totalRows": 100,
            "convertedRows": 95,
            "errorRows": 5,
            "fileSizeBytes": 20480,
        }
        response = lambda_handler(_event_get("audit-1"), None)
        assert response["statusCode"] == 200
        body = _body(response)
        assert body["status"] == "COMPLETED"
        assert body["avroKey"] == "output/alumnos_20261004.avro"
        assert body["totalRows"] == 100
        assert body["convertedRows"] == 95
        assert body["errorRows"] == 5


# ---------------------------------------------------------------------------
# GET /conversions/{auditId} — estado NO_VALID_RECORDS
# ---------------------------------------------------------------------------


class TestGetConversionNoValidRecords:
    """GET con auditId en estado NO_VALID_RECORDS."""

    def test_200_con_avro_key_null_explicito(self, mock_audit: MagicMock) -> None:
        """Debe retornar 200 con avroKey: null explícito en el body."""
        mock_audit.get_audit_entry.return_value = {
            "auditId": "audit-1",
            "status": "NO_VALID_RECORDS",
            "logKey": "logs/alumnos_20261004.csv",
            "totalRows": 50,
            "convertedRows": 0,
            "errorRows": 50,
        }
        response = lambda_handler(_event_get("audit-1"), None)
        assert response["statusCode"] == 200
        body = _body(response)
        assert body["status"] == "NO_VALID_RECORDS"
        assert "avroKey" in body
        assert body["avroKey"] is None

    def test_avro_key_null_en_raw_json(self, mock_audit: MagicMock) -> None:
        """El JSON crudo debe contener 'avroKey': null, no omitirlo."""
        mock_audit.get_audit_entry.return_value = {
            "auditId": "audit-1",
            "status": "NO_VALID_RECORDS",
            "logKey": "logs/alumnos_20261004.csv",
            "totalRows": 50,
            "convertedRows": 0,
            "errorRows": 50,
        }
        response = lambda_handler(_event_get("audit-1"), None)
        assert '"avroKey": null' in response["body"]


# ---------------------------------------------------------------------------
# GET /conversions/{auditId} — estado ERROR
# ---------------------------------------------------------------------------


class TestGetConversionError:
    """GET con auditId en estado ERROR."""

    def test_200_con_codigo_y_mensaje_de_error(self, mock_audit: MagicMock) -> None:
        """Debe retornar 200 con código de error y mensaje descriptivo."""
        mock_audit.get_audit_entry.return_value = {
            "auditId": "audit-1",
            "status": "ERROR",
            "error": "CSV_NOT_FOUND",
            "message": "El archivo datos/alumnos.csv no existe.",
        }
        response = lambda_handler(_event_get("audit-1"), None)
        assert response["statusCode"] == 200
        body = _body(response)
        assert body["status"] == "ERROR"
        assert body["error"] == "CSV_NOT_FOUND"
        assert "no existe" in body["message"]


# ---------------------------------------------------------------------------
# GET /conversions/{auditId} — 404 Not Found
# ---------------------------------------------------------------------------


class TestGetConversionNotFound:
    """GET con auditId inexistente."""

    def test_404_si_audit_id_no_existe(self, mock_audit: MagicMock) -> None:
        """Debe retornar 404 si el auditId no existe en DynamoDB."""
        mock_audit.get_audit_entry.return_value = None
        response = lambda_handler(_event_get("audit-inexistente"), None)
        assert response["statusCode"] == 404

    def test_body_menciona_audit_id(self, mock_audit: MagicMock) -> None:
        """El body del 404 debe mencionar el auditId buscado."""
        mock_audit.get_audit_entry.return_value = None
        response = lambda_handler(_event_get("audit-xyz"), None)
        assert "audit-xyz" in _body(response)["message"]

    def test_content_type_en_404(self, mock_audit: MagicMock) -> None:
        """El 404 debe incluir Content-Type correcto."""
        mock_audit.get_audit_entry.return_value = None
        response = lambda_handler(_event_get("audit-xyz"), None)
        assert response["headers"]["Content-Type"] == CONTENT_TYPE
