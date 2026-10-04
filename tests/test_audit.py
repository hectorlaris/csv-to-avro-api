"""Pruebas unitarias para src/common/audit.py."""

import os
from unittest.mock import MagicMock, patch

import pytest

# Configurar variables de entorno antes de importar el módulo
os.environ.setdefault("AUDIT_TABLE", "avro-api-audit-test")
os.environ.setdefault("AUDIT_TTL_DAYS", "90")

from common.audit import (  # noqa: E402
    STATUS_COMPLETED,
    STATUS_ERROR,
    STATUS_NO_VALID_RECORDS,
    STATUS_PENDING,
    STATUS_PROCESSING,
    create_audit_entry,
    get_audit_entry,
    update_audit_entry,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_table():
    """Retorna un mock de la tabla DynamoDB y parchea _table()."""
    table = MagicMock()
    with patch("common.audit._table", return_value=table):
        yield table


# ---------------------------------------------------------------------------
# create_audit_entry
# ---------------------------------------------------------------------------


class TestCreateAuditEntry:
    """Pruebas para create_audit_entry."""

    def test_retorna_uuid(self, mock_table: MagicMock) -> None:
        """Debe retornar un auditId con formato UUID."""
        import re

        audit_id = create_audit_entry("datos/alumnos.csv", "schemas/alumnos.json")
        assert re.match(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
            audit_id,
        )

    def test_estado_inicial_pending(self, mock_table: MagicMock) -> None:
        """El asiento creado debe tener estado PENDING."""
        create_audit_entry("datos/alumnos.csv", "schemas/alumnos.json")
        call_args = mock_table.put_item.call_args[1]["Item"]
        assert call_args["status"] == STATUS_PENDING

    def test_incluye_csv_y_schema_key(self, mock_table: MagicMock) -> None:
        """El asiento debe incluir csvKey y schemaKey."""
        create_audit_entry("datos/alumnos.csv", "schemas/alumnos.json")
        item = mock_table.put_item.call_args[1]["Item"]
        assert item["csvKey"] == "datos/alumnos.csv"
        assert item["schemaKey"] == "schemas/alumnos.json"

    def test_incluye_timestamps_y_ttl(self, mock_table: MagicMock) -> None:
        """El asiento debe incluir createdAt, updatedAt y ttl."""
        create_audit_entry("datos/alumnos.csv", "schemas/alumnos.json")
        item = mock_table.put_item.call_args[1]["Item"]
        assert "createdAt" in item
        assert "updatedAt" in item
        assert isinstance(item["ttl"], int)
        assert item["ttl"] > 0


# ---------------------------------------------------------------------------
# update_audit_entry
# ---------------------------------------------------------------------------


class TestUpdateAuditEntry:
    """Pruebas para update_audit_entry."""

    def test_actualiza_a_processing(self, mock_table: MagicMock) -> None:
        """Debe actualizar el estado a PROCESSING."""
        update_audit_entry("audit-123", STATUS_PROCESSING)
        call_kwargs = mock_table.update_item.call_args[1]
        assert ":status" in call_kwargs["ExpressionAttributeValues"]
        assert call_kwargs["ExpressionAttributeValues"][":status"] == STATUS_PROCESSING

    def test_actualiza_a_completed_con_campos(self, mock_table: MagicMock) -> None:
        """Debe actualizar a COMPLETED incluyendo campos de resultado."""
        update_audit_entry(
            "audit-123",
            STATUS_COMPLETED,
            avro_key="output/alumnos_20261004.avro",
            log_key="logs/alumnos_20261004.csv",
            total_rows=100,
            converted_rows=95,
            error_rows=5,
            file_size_bytes=20480,
        )
        values = mock_table.update_item.call_args[1]["ExpressionAttributeValues"]
        assert values[":status"] == STATUS_COMPLETED
        assert values[":avroKey"] == "output/alumnos_20261004.avro"
        assert values[":totalRows"] == 100
        assert values[":convertedRows"] == 95
        assert values[":errorRows"] == 5
        assert values[":fileSizeBytes"] == 20480

    def test_actualiza_a_error_con_codigo(self, mock_table: MagicMock) -> None:
        """Debe actualizar a ERROR incluyendo código y mensaje."""
        update_audit_entry(
            "audit-123",
            STATUS_ERROR,
            error="CSV_NOT_FOUND",
            message="El archivo datos/alumnos.csv no existe en S3.",
        )
        values = mock_table.update_item.call_args[1]["ExpressionAttributeValues"]
        assert values[":status"] == STATUS_ERROR
        assert values[":error"] == "CSV_NOT_FOUND"
        assert "no existe" in values[":message"]

    def test_actualiza_a_no_valid_records(self, mock_table: MagicMock) -> None:
        """Debe actualizar a NO_VALID_RECORDS sin avroKey."""
        update_audit_entry(
            "audit-123",
            STATUS_NO_VALID_RECORDS,
            log_key="logs/alumnos_20261004.csv",
            total_rows=50,
            converted_rows=0,
            error_rows=50,
        )
        values = mock_table.update_item.call_args[1]["ExpressionAttributeValues"]
        assert values[":status"] == STATUS_NO_VALID_RECORDS
        assert ":avroKey" not in values

    def test_omite_campos_none(self, mock_table: MagicMock) -> None:
        """Los campos con valor None no deben incluirse en la actualización."""
        update_audit_entry("audit-123", STATUS_PROCESSING)
        values = mock_table.update_item.call_args[1]["ExpressionAttributeValues"]
        none_placeholders = [
            ":avroKey",
            ":logKey",
            ":totalRows",
            ":convertedRows",
            ":errorRows",
            ":fileSizeBytes",
            ":error",
            ":message",
        ]
        for placeholder in none_placeholders:
            assert placeholder not in values


# ---------------------------------------------------------------------------
# get_audit_entry
# ---------------------------------------------------------------------------


class TestGetAuditEntry:
    """Pruebas para get_audit_entry."""

    def test_retorna_item_existente(self, mock_table: MagicMock) -> None:
        """Debe retornar el asiento cuando existe."""
        mock_table.get_item.return_value = {
            "Item": {
                "auditId": "audit-123",
                "status": STATUS_PENDING,
                "csvKey": "datos/alumnos.csv",
            }
        }
        result = get_audit_entry("audit-123")
        assert result is not None
        assert result["auditId"] == "audit-123"
        assert result["status"] == STATUS_PENDING

    def test_retorna_none_si_no_existe(self, mock_table: MagicMock) -> None:
        """Debe retornar None cuando el auditId no existe."""
        mock_table.get_item.return_value = {}
        result = get_audit_entry("audit-inexistente")
        assert result is None

    def test_llama_con_audit_id_correcto(self, mock_table: MagicMock) -> None:
        """Debe consultar DynamoDB con la clave correcta."""
        mock_table.get_item.return_value = {}
        get_audit_entry("audit-xyz")
        mock_table.get_item.assert_called_once_with(Key={"auditId": "audit-xyz"})
