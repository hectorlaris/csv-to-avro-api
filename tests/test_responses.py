"""Pruebas unitarias para src/common/responses.py."""

import json


from src.common.responses import (
    accepted,
    bad_request,
    not_found,
    ok_completed,
    ok_error,
    ok_no_valid_records,
    ok_pending,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CONTENT_TYPE = "application/json; charset=utf-8"


def _body(response: dict) -> dict:
    """Deserializa el body JSON de una respuesta."""
    return json.loads(response["body"])


def _assert_content_type(response: dict) -> None:
    """Verifica que el header Content-Type es correcto."""
    assert response["headers"]["Content-Type"] == CONTENT_TYPE


# ---------------------------------------------------------------------------
# accepted (202)
# ---------------------------------------------------------------------------


class TestAccepted:
    """Pruebas para la respuesta 202 Accepted."""

    def test_status_code_202(self) -> None:
        """Debe retornar código HTTP 202."""
        assert accepted("id-1", "/conversions/id-1")["statusCode"] == 202

    def test_content_type_correcto(self) -> None:
        """Debe incluir Content-Type: application/json; charset=utf-8."""
        _assert_content_type(accepted("id-1", "/conversions/id-1"))

    def test_body_contiene_campos_requeridos(self) -> None:
        """El body debe incluir status PENDING, auditId y statusUrl."""
        body = _body(accepted("id-1", "/conversions/id-1"))
        assert body["status"] == "PENDING"
        assert body["auditId"] == "id-1"
        assert body["statusUrl"] == "/conversions/id-1"


# ---------------------------------------------------------------------------
# ok_pending (200 — PENDING / PROCESSING)
# ---------------------------------------------------------------------------


class TestOkPending:
    """Pruebas para la respuesta 200 con estado PENDING o PROCESSING."""

    def test_status_code_200(self) -> None:
        """Debe retornar código HTTP 200."""
        assert ok_pending("id-1", "PENDING")["statusCode"] == 200

    def test_content_type_correcto(self) -> None:
        """Debe incluir Content-Type correcto."""
        _assert_content_type(ok_pending("id-1", "PENDING"))

    def test_body_pending(self) -> None:
        """El body debe incluir status PENDING y auditId."""
        body = _body(ok_pending("id-1", "PENDING"))
        assert body["status"] == "PENDING"
        assert body["auditId"] == "id-1"

    def test_body_processing(self) -> None:
        """El body debe incluir status PROCESSING y auditId."""
        body = _body(ok_pending("id-2", "PROCESSING"))
        assert body["status"] == "PROCESSING"
        assert body["auditId"] == "id-2"


# ---------------------------------------------------------------------------
# ok_completed (200 — COMPLETED)
# ---------------------------------------------------------------------------


class TestOkCompleted:
    """Pruebas para la respuesta 200 con estado COMPLETED."""

    def _response(self) -> dict:
        return ok_completed(
            audit_id="id-1",
            avro_key="output/alumnos_20261004.avro",
            log_key="logs/alumnos_20261004.csv",
            total_rows=100,
            converted_rows=95,
            error_rows=5,
            file_size_bytes=20480,
        )

    def test_status_code_200(self) -> None:
        """Debe retornar código HTTP 200."""
        assert self._response()["statusCode"] == 200

    def test_content_type_correcto(self) -> None:
        """Debe incluir Content-Type correcto."""
        _assert_content_type(self._response())

    def test_body_contiene_todos_los_campos(self) -> None:
        """El body debe incluir todos los campos de resultado."""
        body = _body(self._response())
        assert body["status"] == "COMPLETED"
        assert body["avroKey"] == "output/alumnos_20261004.avro"
        assert body["logKey"] == "logs/alumnos_20261004.csv"
        assert body["totalRows"] == 100
        assert body["convertedRows"] == 95
        assert body["errorRows"] == 5
        assert body["fileSizeBytes"] == 20480


# ---------------------------------------------------------------------------
# ok_no_valid_records (200 — NO_VALID_RECORDS)
# ---------------------------------------------------------------------------


class TestOkNoValidRecords:
    """Pruebas para la respuesta 200 con estado NO_VALID_RECORDS."""

    def _response(self) -> dict:
        return ok_no_valid_records(
            audit_id="id-1",
            log_key="logs/alumnos_20261004.csv",
            total_rows=50,
            error_rows=50,
        )

    def test_status_code_200(self) -> None:
        """Debe retornar código HTTP 200."""
        assert self._response()["statusCode"] == 200

    def test_avro_key_es_null_explicito(self) -> None:
        """avroKey debe estar presente en el body con valor null explícito."""
        body = _body(self._response())
        assert "avroKey" in body
        assert body["avroKey"] is None

    def test_body_contiene_campos_requeridos(self) -> None:
        """El body debe incluir status, logKey y contadores."""
        body = _body(self._response())
        assert body["status"] == "NO_VALID_RECORDS"
        assert body["logKey"] == "logs/alumnos_20261004.csv"
        assert body["totalRows"] == 50
        assert body["convertedRows"] == 0
        assert body["errorRows"] == 50


# ---------------------------------------------------------------------------
# ok_error (200 — ERROR)
# ---------------------------------------------------------------------------


class TestOkError:
    """Pruebas para la respuesta 200 con estado ERROR."""

    def test_status_code_200(self) -> None:
        """Debe retornar código HTTP 200."""
        r = ok_error("id-1", "CSV_NOT_FOUND", "El CSV no existe.")
        assert r["statusCode"] == 200

    def test_content_type_correcto(self) -> None:
        """Debe incluir Content-Type correcto."""
        _assert_content_type(ok_error("id-1", "CSV_NOT_FOUND", "El CSV no existe."))

    def test_body_contiene_error_y_mensaje(self) -> None:
        """El body debe incluir el código de error y el mensaje descriptivo."""
        body = _body(ok_error("id-1", "CSV_NOT_FOUND", "El CSV no existe."))
        assert body["status"] == "ERROR"
        assert body["error"] == "CSV_NOT_FOUND"
        assert body["message"] == "El CSV no existe."


# ---------------------------------------------------------------------------
# bad_request (400)
# ---------------------------------------------------------------------------


class TestBadRequest:
    """Pruebas para la respuesta 400 Bad Request."""

    def test_status_code_400(self) -> None:
        """Debe retornar código HTTP 400."""
        assert bad_request("Falta csvKey.")["statusCode"] == 400

    def test_content_type_correcto(self) -> None:
        """Debe incluir Content-Type correcto."""
        _assert_content_type(bad_request("Falta csvKey."))

    def test_body_contiene_mensaje(self) -> None:
        """El body debe incluir el mensaje de error."""
        body = _body(bad_request("Falta csvKey."))
        assert body["message"] == "Falta csvKey."
        assert body["error"] == "BAD_REQUEST"


# ---------------------------------------------------------------------------
# not_found (404)
# ---------------------------------------------------------------------------


class TestNotFound:
    """Pruebas para la respuesta 404 Not Found."""

    def test_status_code_404(self) -> None:
        """Debe retornar código HTTP 404."""
        assert not_found("id-inexistente")["statusCode"] == 404

    def test_content_type_correcto(self) -> None:
        """Debe incluir Content-Type correcto."""
        _assert_content_type(not_found("id-inexistente"))

    def test_body_menciona_audit_id(self) -> None:
        """El body debe mencionar el auditId no encontrado."""
        body = _body(not_found("id-inexistente"))
        assert "id-inexistente" in body["message"]
        assert body["error"] == "NOT_FOUND"


# ---------------------------------------------------------------------------
# Omisión de campos nulos (regla general)
# ---------------------------------------------------------------------------


class TestOmisionCamposNulos:
    """Verifica que los campos nulos se omiten salvo avroKey."""

    def test_campos_nulos_omitidos_en_ok_pending(self) -> None:
        """Los campos no presentes no deben aparecer en el body."""
        body = _body(ok_pending("id-1", "PENDING"))
        assert "avroKey" not in body
        assert "logKey" not in body
        assert "totalRows" not in body

    def test_avro_key_null_presente_en_no_valid_records(self) -> None:
        """avroKey debe aparecer como null en NO_VALID_RECORDS, no omitirse."""
        raw_body = ok_no_valid_records("id-1", "logs/x.csv", 10, 10)["body"]
        assert '"avroKey": null' in raw_body
