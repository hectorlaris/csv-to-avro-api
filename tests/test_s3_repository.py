"""Pruebas unitarias para src/common/s3_repository.py."""

import os
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

os.environ.setdefault("REPOSITORY_BUCKET", "avro-api-repository-test")

from src.common.s3_repository import (  # noqa: E402
    get_object_size,
    object_exists,
    read_object_bytes,
    read_object_stream,
    write_object,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _client_error(code: str) -> ClientError:
    """Crea un ClientError de botocore con el código dado."""
    return ClientError({"Error": {"Code": code, "Message": "test"}}, "operation")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_s3():
    """Parchea _s3_client() y retorna el mock del cliente."""
    client = MagicMock()
    with patch("src.common.s3_repository._s3_client", return_value=client):
        yield client


# ---------------------------------------------------------------------------
# object_exists
# ---------------------------------------------------------------------------


class TestObjectExists:
    """Pruebas para object_exists."""

    def test_retorna_true_si_existe(self, mock_s3: MagicMock) -> None:
        """Debe retornar True cuando head_object no lanza excepción."""
        mock_s3.head_object.return_value = {"ContentLength": 1024}
        assert object_exists("datos/alumnos.csv") is True

    def test_retorna_false_si_no_existe_404(self, mock_s3: MagicMock) -> None:
        """Debe retornar False cuando head_object lanza 404."""
        mock_s3.head_object.side_effect = _client_error("404")
        assert object_exists("datos/inexistente.csv") is False

    def test_retorna_false_si_no_existe_no_such_key(self, mock_s3: MagicMock) -> None:
        """Debe retornar False cuando head_object lanza NoSuchKey."""
        mock_s3.head_object.side_effect = _client_error("NoSuchKey")
        assert object_exists("datos/inexistente.csv") is False

    def test_propaga_otros_errores(self, mock_s3: MagicMock) -> None:
        """Debe propagar ClientError que no sea 404 ni NoSuchKey."""
        mock_s3.head_object.side_effect = _client_error("403")
        with pytest.raises(ClientError):
            object_exists("datos/privado.csv")


# ---------------------------------------------------------------------------
# read_object_stream
# ---------------------------------------------------------------------------


class TestReadObjectStream:
    """Pruebas para read_object_stream."""

    def test_retorna_chunks(self, mock_s3: MagicMock) -> None:
        """Debe retornar los bytes del objeto en chunks."""
        contenido = b"col1,col2\nval1,val2\n"
        stream_mock = MagicMock()
        stream_mock.read.side_effect = [contenido, b""]
        mock_s3.get_object.return_value = {"Body": stream_mock}

        chunks = list(read_object_stream("datos/alumnos.csv"))
        assert b"".join(chunks) == contenido

    def test_llama_con_bucket_y_key_correctos(self, mock_s3: MagicMock) -> None:
        """Debe llamar a get_object con el bucket y key correctos."""
        stream_mock = MagicMock()
        stream_mock.read.return_value = b""
        mock_s3.get_object.return_value = {"Body": stream_mock}

        list(read_object_stream("datos/alumnos.csv"))
        mock_s3.get_object.assert_called_once_with(
            Bucket="avro-api-repository-test", Key="datos/alumnos.csv"
        )


# ---------------------------------------------------------------------------
# write_object
# ---------------------------------------------------------------------------


class TestWriteObject:
    """Pruebas para write_object."""

    def test_llama_put_object_con_parametros_correctos(
        self, mock_s3: MagicMock
    ) -> None:
        """Debe llamar a put_object con bucket, key, body y content_type."""
        data = b"\x00\x01\x02"
        write_object("output/alumnos_20261004.avro", data, "application/avro")

        mock_s3.put_object.assert_called_once_with(
            Bucket="avro-api-repository-test",
            Key="output/alumnos_20261004.avro",
            Body=data,
            ContentType="application/avro",
        )

    def test_content_type_por_defecto(self, mock_s3: MagicMock) -> None:
        """Debe usar application/octet-stream como content_type por defecto."""
        write_object("output/alumnos_20261004.avro", b"data")
        call_kwargs = mock_s3.put_object.call_args[1]
        assert call_kwargs["ContentType"] == "application/octet-stream"

    def test_no_genera_urls_publicas(self, mock_s3: MagicMock) -> None:
        """write_object no debe llamar a generate_presigned_url ni similar."""
        write_object("output/test.avro", b"data")
        mock_s3.generate_presigned_url.assert_not_called()


# ---------------------------------------------------------------------------
# get_object_size
# ---------------------------------------------------------------------------


class TestGetObjectSize:
    """Pruebas para get_object_size."""

    def test_retorna_content_length(self, mock_s3: MagicMock) -> None:
        """Debe retornar el ContentLength del objeto."""
        mock_s3.head_object.return_value = {"ContentLength": 20480}
        size = get_object_size("output/alumnos_20261004.avro")
        assert size == 20480

    def test_propaga_error_si_no_existe(self, mock_s3: MagicMock) -> None:
        """Debe propagar ClientError si el objeto no existe."""
        mock_s3.head_object.side_effect = _client_error("404")
        with pytest.raises(ClientError):
            get_object_size("output/inexistente.avro")


# ---------------------------------------------------------------------------
# read_object_bytes
# ---------------------------------------------------------------------------


class TestReadObjectBytes:
    """Pruebas para read_object_bytes."""

    def test_retorna_bytes_completos(self, mock_s3: MagicMock) -> None:
        """Debe retornar el contenido completo como bytes."""
        contenido = b'{"type": "record", "name": "Alumno"}'
        stream_mock = MagicMock()
        stream_mock.read.side_effect = [contenido, b""]
        mock_s3.get_object.return_value = {"Body": stream_mock}

        result = read_object_bytes("schemas/alumnos.json")
        assert result == contenido
