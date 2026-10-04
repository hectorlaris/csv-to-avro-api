"""Pruebas unitarias para src/common/avro_writer.py."""

import pytest

from src.common.avro_writer import deserialize_from_avro, serialize_to_avro

# ---------------------------------------------------------------------------
# Esquemas de prueba
# ---------------------------------------------------------------------------

SCHEMA_ALUMNO = {
    "type": "record",
    "name": "Alumno",
    "fields": [
        {"name": "nombre", "type": "string"},
        {"name": "edad", "type": "int"},
        {"name": "promedio", "type": "double"},
        {"name": "activo", "type": "boolean"},
    ],
}

SCHEMA_CON_NULLABLE = {
    "type": "record",
    "name": "Contacto",
    "fields": [
        {"name": "nombre", "type": "string"},
        {"name": "telefono", "type": ["null", "string"], "default": None},
    ],
}


# ---------------------------------------------------------------------------
# serialize_to_avro
# ---------------------------------------------------------------------------


class TestSerializeToAvro:
    """Pruebas para serialize_to_avro."""

    def test_retorna_bytes(self) -> None:
        """Debe retornar un objeto bytes no vacío."""
        records = [{"nombre": "Ana", "edad": 20, "promedio": 9.5, "activo": True}]
        result = serialize_to_avro(records, SCHEMA_ALUMNO)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_avro_valido_con_un_registro(self) -> None:
        """El buffer resultante debe ser un Avro válido y legible."""
        records = [{"nombre": "Ana", "edad": 20, "promedio": 9.5, "activo": True}]
        avro_bytes = serialize_to_avro(records, SCHEMA_ALUMNO)
        deserialized = deserialize_from_avro(avro_bytes)
        assert len(deserialized) == 1
        assert deserialized[0]["nombre"] == "Ana"
        assert deserialized[0]["edad"] == 20

    def test_avro_valido_con_multiples_registros(self) -> None:
        """Debe serializar y recuperar correctamente varios registros."""
        records = [
            {"nombre": "Ana", "edad": 20, "promedio": 9.5, "activo": True},
            {"nombre": "Luis", "edad": 22, "promedio": 8.0, "activo": False},
            {"nombre": "María", "edad": 19, "promedio": 7.5, "activo": True},
        ]
        avro_bytes = serialize_to_avro(records, SCHEMA_ALUMNO)
        deserialized = deserialize_from_avro(avro_bytes)
        assert len(deserialized) == 3
        assert deserialized[1]["nombre"] == "Luis"
        assert deserialized[2]["promedio"] == 7.5

    def test_preserva_tipos_correctamente(self) -> None:
        """Los tipos de los valores deben preservarse tras serializar/deserializar."""
        records = [{"nombre": "Ana", "edad": 20, "promedio": 9.5, "activo": True}]
        avro_bytes = serialize_to_avro(records, SCHEMA_ALUMNO)
        deserialized = deserialize_from_avro(avro_bytes)
        assert isinstance(deserialized[0]["edad"], int)
        assert isinstance(deserialized[0]["promedio"], float)
        assert isinstance(deserialized[0]["activo"], bool)
        assert isinstance(deserialized[0]["nombre"], str)

    def test_serializa_campos_nullable(self) -> None:
        """Debe manejar correctamente campos con valor None en unions null."""
        records = [
            {"nombre": "Ana", "telefono": None},
            {"nombre": "Luis", "telefono": "555-1234"},
        ]
        avro_bytes = serialize_to_avro(records, SCHEMA_CON_NULLABLE)
        deserialized = deserialize_from_avro(avro_bytes)
        assert deserialized[0]["telefono"] is None
        assert deserialized[1]["telefono"] == "555-1234"

    def test_lanza_error_si_records_vacio(self) -> None:
        """Debe lanzar ValueError si la lista de registros está vacía."""
        with pytest.raises(ValueError, match="No hay registros"):
            serialize_to_avro([], SCHEMA_ALUMNO)


# ---------------------------------------------------------------------------
# deserialize_from_avro
# ---------------------------------------------------------------------------


class TestDeserializeFromAvro:
    """Pruebas para deserialize_from_avro."""

    def test_round_trip_completo(self) -> None:
        """Los datos deben sobrevivir un ciclo completo serializar→deserializar."""
        records = [
            {"nombre": "Ana", "edad": 20, "promedio": 9.5, "activo": True},
            {"nombre": "Luis", "edad": 22, "promedio": 8.0, "activo": False},
        ]
        avro_bytes = serialize_to_avro(records, SCHEMA_ALUMNO)
        recovered = deserialize_from_avro(avro_bytes)
        assert recovered == records

    def test_retorna_lista(self) -> None:
        """Debe retornar una lista aunque haya un solo registro."""
        records = [{"nombre": "Ana", "edad": 20, "promedio": 9.5, "activo": True}]
        avro_bytes = serialize_to_avro(records, SCHEMA_ALUMNO)
        result = deserialize_from_avro(avro_bytes)
        assert isinstance(result, list)
