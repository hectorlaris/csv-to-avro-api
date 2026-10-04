"""Módulo de acceso al repositorio S3 (única fuente de verdad del proyecto)."""

import io
import os
from typing import Iterator

import boto3
from botocore.exceptions import ClientError

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
_BUCKET_NAME: str = os.environ.get("REPOSITORY_BUCKET", "")


def _s3_client() -> object:
    """Retorna un cliente S3 de boto3."""
    return boto3.client("s3")


def object_exists(key: str) -> bool:
    """Verifica si un objeto existe en el bucket S3.

    Args:
        key: Clave S3 del objeto (p. ej. 'datos/alumnos.csv').

    Returns:
        True si el objeto existe, False si no.
    """
    try:
        _s3_client().head_object(Bucket=_BUCKET_NAME, Key=key)
        return True
    except ClientError as exc:
        if exc.response["Error"]["Code"] in ("404", "NoSuchKey"):
            return False
        raise


def read_object_stream(key: str) -> Iterator[bytes]:
    """Lee un objeto de S3 como stream de chunks de bytes.

    Args:
        key: Clave S3 del objeto a leer.

    Yields:
        Chunks de bytes del contenido del objeto.

    Raises:
        ClientError: Si el objeto no existe o hay error de acceso.
    """
    response = _s3_client().get_object(Bucket=_BUCKET_NAME, Key=key)
    stream = response["Body"]
    chunk_size = 256 * 1024  # 256 KB
    while True:
        chunk = stream.read(chunk_size)
        if not chunk:
            break
        yield chunk


def write_object(
    key: str, data: bytes, content_type: str = "application/octet-stream"
) -> None:
    """Escribe un objeto en S3.

    Args:
        key: Clave S3 de destino.
        data: Contenido en bytes a escribir.
        content_type: Tipo MIME del objeto.
    """
    _s3_client().put_object(
        Bucket=_BUCKET_NAME,
        Key=key,
        Body=data,
        ContentType=content_type,
    )


def get_object_size(key: str) -> int:
    """Obtiene el tamaño en bytes de un objeto en S3.

    Args:
        key: Clave S3 del objeto.

    Returns:
        Tamaño del objeto en bytes.

    Raises:
        ClientError: Si el objeto no existe o hay error de acceso.
    """
    response = _s3_client().head_object(Bucket=_BUCKET_NAME, Key=key)
    return response["ContentLength"]


def read_object_bytes(key: str) -> bytes:
    """Lee un objeto de S3 completo y retorna sus bytes.

    Conveniente para objetos pequeños como esquemas JSON.

    Args:
        key: Clave S3 del objeto a leer.

    Returns:
        Contenido completo del objeto como bytes.
    """
    buffer = io.BytesIO()
    for chunk in read_object_stream(key):
        buffer.write(chunk)
    return buffer.getvalue()
