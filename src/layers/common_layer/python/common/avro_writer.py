"""Módulo de serialización Avro usando fastavro."""

import io
from typing import Any

import fastavro


def serialize_to_avro(
    records: list[dict[str, Any]],
    schema: dict,
) -> bytes:
    """Serializa una lista de registros válidos a formato Avro.

    Usa fastavro para escribir los registros en un buffer en memoria.
    El esquema debe estar ya parseado como diccionario Python (no como string).

    Args:
        records: Lista de dicts con los registros válidos a serializar.
                 Los valores deben estar ya convertidos al tipo correcto.
        schema: Esquema Avro parseado como diccionario Python.

    Returns:
        Bytes del archivo Avro listo para escribir en S3.

    Raises:
        ValueError: Si records está vacío.
        fastavro.schema.UnknownType: Si el esquema tiene tipos no reconocidos.
    """
    if not records:
        raise ValueError("No hay registros válidos para serializar.")

    parsed_schema = fastavro.parse_schema(schema)
    buffer = io.BytesIO()
    fastavro.writer(buffer, parsed_schema, records)
    return buffer.getvalue()


def deserialize_from_avro(data: bytes) -> list[dict[str, Any]]:
    """Deserializa bytes Avro y retorna la lista de registros.

    Útil para verificar que el Avro generado es válido y legible.

    Args:
        data: Bytes del archivo Avro a leer.

    Returns:
        Lista de dicts con los registros deserializados.
    """
    buffer = io.BytesIO(data)
    return list(fastavro.reader(buffer))
