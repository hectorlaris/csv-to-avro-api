"""Pruebas unitarias para src/common/conversion.py."""

import json
import os
from unittest.mock import patch

import pytest

os.environ.setdefault("AUDIT_TABLE", "avro-api-audit-test")
os.environ.setdefault("REPOSITORY_BUCKET", "avro-api-repository-test")
os.environ.setdefault("AUDIT_TTL_DAYS", "90")

from common import audit  # noqa: E402
from common.conversion import (  # noqa: E402
    ERR_CSV_NOT_FOUND,
    ERR_INVALID_SCHEMA,
    ERR_SCHEMA_NOT_FOUND,
    run_conversion,
)

# ---------------------------------------------------------------------------
# Esquema y datos de prueba
# ---------------------------------------------------------------------------

SCHEMA = {
    "type": "record",
    "name": "Alumno",
    "fields": [
        {"name": "nombre", "type": "string"},
        {"name": "edad", "type": "int"},
    ],
}

SCHEMA_BYTES = json.dumps(SCHEMA).encode("utf-8")

CSV_MIXTO = "nombre,edad\nAna,20\nLuis,xx\nMaria,19\n"
CSV_SIN_VALIDOS = "nombre,edad\n,20\n,19\n"
CSV_TODOS_VALIDOS = "nombre,edad\nAna,20\nLuis,22\n"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mocks():
    """Parchea audit, s3_repository y devuelve los mocks."""
    with (
        patch("common.conversion.audit") as mock_audit,
        patch("common.conversion.s3_repository") as mock_s3,
    ):
        # Estado inicial: asiento en PENDING (no finalizado)
        mock_audit.STATUS_COMPLETED = audit.STATUS_COMPLETED
        mock_audit.STATUS_NO_VALID_RECORDS = audit.STATUS_NO_VALID_RECORDS
        mock_audit.STATUS_ERROR = audit.STATUS_ERROR
        mock_audit.STATUS_PROCESSING = audit.STATUS_PROCESSING
        mock_audit.get_audit_entry.return_value = {"status": "PENDING"}

        # S3: por defecto todos los objetos existen
        mock_s3.object_exists.return_value = True
        mock_s3.read_object_stream.return_value = iter(
            [CSV_TODOS_VALIDOS.encode("utf-8")]
        )
        mock_s3.read_object_bytes.return_value = SCHEMA_BYTES

        yield mock_audit, mock_s3


# ---------------------------------------------------------------------------
# Caso 1: flujo completo con registros mixtos
# ---------------------------------------------------------------------------


class TestFlujoCompleto:
    """Flujo CSV→Avro con filas válidas e inválidas."""

    def test_actualiza_estado_a_completed(self, mocks) -> None:
        """El asiento debe quedar en COMPLETED cuando hay filas válidas."""
        mock_audit, mock_s3 = mocks
        mock_s3.read_object_stream.return_value = iter([CSV_MIXTO.encode("utf-8")])
        run_conversion("audit-1", "datos/alumnos.csv")
        call_args = mock_audit.update_audit_entry.call_args_list[-1]
        assert call_args[0][1] == audit.STATUS_COMPLETED

    def test_contadores_correctos(self, mocks) -> None:
        """Los contadores de filas deben reflejar el resultado real."""
        mock_audit, mock_s3 = mocks
        mock_s3.read_object_stream.return_value = iter([CSV_MIXTO.encode("utf-8")])
        run_conversion("audit-1", "datos/alumnos.csv")
        final_call = mock_audit.update_audit_entry.call_args_list[-1][1]
        assert final_call["total_rows"] == 3
        assert final_call["converted_rows"] == 2
        assert final_call["error_rows"] == 1

    def test_escribe_avro_y_log(self, mocks) -> None:
        """Debe escribir tanto el Avro como el log de inconsistencias en S3."""
        mock_audit, mock_s3 = mocks
        mock_s3.read_object_stream.return_value = iter([CSV_MIXTO.encode("utf-8")])
        run_conversion("audit-1", "datos/alumnos.csv")
        keys_escritas = [c[0][0] for c in mock_s3.write_object.call_args_list]
        avro_escritos = [k for k in keys_escritas if k.startswith("output/")]
        logs_escritos = [k for k in keys_escritas if k.startswith("logs/")]
        assert len(avro_escritos) == 1
        assert len(logs_escritos) == 1

    def test_marca_processing_antes_de_convertir(self, mocks) -> None:
        """El estado PROCESSING debe establecerse antes de la conversión."""
        mock_audit, mock_s3 = mocks
        run_conversion("audit-1", "datos/alumnos.csv")
        primera_actualizacion = mock_audit.update_audit_entry.call_args_list[0]
        assert primera_actualizacion[0][1] == audit.STATUS_PROCESSING


# ---------------------------------------------------------------------------
# Caso 2: sin registros válidos → NO_VALID_RECORDS
# ---------------------------------------------------------------------------


class TestSinRegistrosValidos:
    """Cuando ninguna fila pasa la validación."""

    def test_estado_no_valid_records(self, mocks) -> None:
        """El asiento debe quedar en NO_VALID_RECORDS."""
        mock_audit, mock_s3 = mocks
        mock_s3.read_object_stream.return_value = iter(
            [CSV_SIN_VALIDOS.encode("utf-8")]
        )
        run_conversion("audit-1", "datos/alumnos.csv")
        final_call = mock_audit.update_audit_entry.call_args_list[-1]
        assert final_call[0][1] == audit.STATUS_NO_VALID_RECORDS

    def test_no_escribe_avro(self, mocks) -> None:
        """No debe escribirse ningún archivo Avro en S3."""
        mock_audit, mock_s3 = mocks
        mock_s3.read_object_stream.return_value = iter(
            [CSV_SIN_VALIDOS.encode("utf-8")]
        )
        run_conversion("audit-1", "datos/alumnos.csv")
        keys_escritas = [c[0][0] for c in mock_s3.write_object.call_args_list]
        avro_escritos = [k for k in keys_escritas if k.startswith("output/")]
        assert len(avro_escritos) == 0

    def test_escribe_log_aunque_no_haya_validos(self, mocks) -> None:
        """El log de inconsistencias debe escribirse aunque no haya válidos."""
        mock_audit, mock_s3 = mocks
        mock_s3.read_object_stream.return_value = iter(
            [CSV_SIN_VALIDOS.encode("utf-8")]
        )
        run_conversion("audit-1", "datos/alumnos.csv")
        keys_escritas = [c[0][0] for c in mock_s3.write_object.call_args_list]
        logs_escritos = [k for k in keys_escritas if k.startswith("logs/")]
        assert len(logs_escritos) == 1


# ---------------------------------------------------------------------------
# Caso 3: idempotencia — reintento sobre auditId ya finalizado
# ---------------------------------------------------------------------------


class TestIdempotencia:
    """El worker no debe reejecutar si el asiento ya está en estado final."""

    @pytest.mark.parametrize(
        "estado_final",
        [
            audit.STATUS_COMPLETED,
            audit.STATUS_NO_VALID_RECORDS,
            audit.STATUS_ERROR,
        ],
    )
    def test_no_reejecuta_si_ya_finalizo(self, mocks, estado_final: str) -> None:
        """No debe actualizar el asiento ni acceder a S3 si ya está en estado final."""
        mock_audit, mock_s3 = mocks
        mock_audit.get_audit_entry.return_value = {"status": estado_final}
        run_conversion("audit-1", "datos/alumnos.csv")
        mock_audit.update_audit_entry.assert_not_called()
        mock_s3.object_exists.assert_not_called()


# ---------------------------------------------------------------------------
# Caso 4: CSV_NOT_FOUND
# ---------------------------------------------------------------------------


class TestCsvNotFound:
    """Cuando el CSV no existe en S3."""

    def test_estado_error_csv_not_found(self, mocks) -> None:
        """El asiento debe quedar en ERROR con código CSV_NOT_FOUND."""
        mock_audit, mock_s3 = mocks
        mock_s3.object_exists.side_effect = lambda key: not key.startswith("datos/")
        run_conversion("audit-1", "datos/alumnos.csv")
        final_call = mock_audit.update_audit_entry.call_args_list[-1][1]
        assert final_call["error"] == ERR_CSV_NOT_FOUND

    def test_no_escribe_nada_en_s3(self, mocks) -> None:
        """No debe escribirse ningún archivo en S3."""
        mock_audit, mock_s3 = mocks
        mock_s3.object_exists.side_effect = lambda key: not key.startswith("datos/")
        run_conversion("audit-1", "datos/alumnos.csv")
        mock_s3.write_object.assert_not_called()


# ---------------------------------------------------------------------------
# Caso 5: SCHEMA_NOT_FOUND
# ---------------------------------------------------------------------------


class TestSchemaNNotFound:
    """Cuando el esquema no existe en S3."""

    def test_estado_error_schema_not_found(self, mocks) -> None:
        """El asiento debe quedar en ERROR con código SCHEMA_NOT_FOUND."""
        mock_audit, mock_s3 = mocks
        mock_s3.object_exists.side_effect = lambda key: not key.startswith("schemas/")
        run_conversion("audit-1", "datos/alumnos.csv")
        final_call = mock_audit.update_audit_entry.call_args_list[-1][1]
        assert final_call["error"] == ERR_SCHEMA_NOT_FOUND


# ---------------------------------------------------------------------------
# Caso 6: INVALID_SCHEMA
# ---------------------------------------------------------------------------


class TestInvalidSchema:
    """Cuando el esquema existe pero no es válido."""

    def test_json_invalido_produce_error(self, mocks) -> None:
        """JSON malformado debe producir ERROR con código INVALID_SCHEMA."""
        mock_audit, mock_s3 = mocks
        mock_s3.read_object_bytes.return_value = b"{ invalid json }"
        run_conversion("audit-1", "datos/alumnos.csv")
        final_call = mock_audit.update_audit_entry.call_args_list[-1][1]
        assert final_call["error"] == ERR_INVALID_SCHEMA

    def test_schema_sin_record_type_produce_error(self, mocks) -> None:
        """Un JSON válido pero sin type=record debe producir INVALID_SCHEMA."""
        mock_audit, mock_s3 = mocks
        mock_s3.read_object_bytes.return_value = json.dumps(
            {"type": "array", "items": "string"}
        ).encode("utf-8")
        run_conversion("audit-1", "datos/alumnos.csv")
        final_call = mock_audit.update_audit_entry.call_args_list[-1][1]
        assert final_call["error"] == ERR_INVALID_SCHEMA

    def test_no_escribe_nada_en_s3(self, mocks) -> None:
        """No debe escribirse nada en S3 si el esquema es inválido."""
        mock_audit, mock_s3 = mocks
        mock_s3.read_object_bytes.return_value = b"not json"
        run_conversion("audit-1", "datos/alumnos.csv")
        mock_s3.write_object.assert_not_called()


# ---------------------------------------------------------------------------
# Caso 7: resolución de schemaKey por convención y por override
# ---------------------------------------------------------------------------


class TestResolucionSchemaKey:
    """Verifica la resolución del schema key."""

    def test_derivacion_por_convencion(self, mocks) -> None:
        """Sin schemaKey explícito debe derivarse schemas/{base}.json."""
        mock_audit, mock_s3 = mocks
        run_conversion("audit-1", "datos/alumnos.csv")
        calls_object_exists = [c[0][0] for c in mock_s3.object_exists.call_args_list]
        assert "schemas/alumnos.json" in calls_object_exists

    def test_override_schema_key(self, mocks) -> None:
        """Con schemaKey explícito debe usarse ese y no el derivado."""
        mock_audit, mock_s3 = mocks
        run_conversion("audit-1", "datos/alumnos.csv", "schemas/custom.json")
        calls_object_exists = [c[0][0] for c in mock_s3.object_exists.call_args_list]
        assert "schemas/custom.json" in calls_object_exists
        assert "schemas/alumnos.json" not in calls_object_exists
