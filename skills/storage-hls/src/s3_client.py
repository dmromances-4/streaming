"""Cliente S3 compatible con MinIO y Cloudflare R2."""

from __future__ import annotations

import mimetypes
from functools import lru_cache
from typing import BinaryIO

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from config import settings
from errors import S3ConnectionError
from skill_telemetry import log, record_error


@lru_cache
def get_s3_client() -> BaseClient:
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.s3_region,
        config=Config(
            signature_version="s3v4",
            retries={"max_attempts": 3, "mode": "standard"},
        ),
    )


def ensure_bucket() -> None:
    """Crea el bucket si no existe (MinIO dev)."""
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=settings.s3_bucket)
    except ClientError:
        try:
            client.create_bucket(Bucket=settings.s3_bucket)
            log.info("s3_bucket_created", bucket=settings.s3_bucket)
        except (ClientError, BotoCoreError) as exc:
            record_error("s3_connection_error")
            raise S3ConnectionError(f"Cannot create bucket: {exc}") from exc


def upload_file(local_path: str, s3_key: str) -> str:
    """Sube un archivo a S3 y devuelve la clave."""
    client = get_s3_client()
    content_type, _ = mimetypes.guess_type(local_path)
    extra_args = {}
    if content_type:
        extra_args["ContentType"] = content_type

    try:
        client.upload_file(
            local_path,
            settings.s3_bucket,
            s3_key,
            ExtraArgs=extra_args or None,
        )
        log.debug("s3_uploaded", key=s3_key)
        return s3_key
    except (ClientError, BotoCoreError) as exc:
        record_error("s3_upload_error")
        raise S3ConnectionError(f"Upload failed for {s3_key}: {exc}") from exc


def upload_bytes(data: bytes, s3_key: str, content_type: str) -> str:
    client = get_s3_client()
    try:
        client.put_object(
            Bucket=settings.s3_bucket,
            Key=s3_key,
            Body=data,
            ContentType=content_type,
        )
        return s3_key
    except (ClientError, BotoCoreError) as exc:
        record_error("s3_upload_error")
        raise S3ConnectionError(f"Upload failed for {s3_key}: {exc}") from exc


def download_bytes(s3_key: str) -> bytes:
    client = get_s3_client()
    try:
        response = client.get_object(Bucket=settings.s3_bucket, Key=s3_key)
        return response["Body"].read()
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") == "NoSuchKey":
            from errors import NotFoundError

            raise NotFoundError(f"S3 object not found: {s3_key}") from exc
        record_error("s3_download_error")
        raise S3ConnectionError(f"Download failed for {s3_key}: {exc}") from exc
    except BotoCoreError as exc:
        record_error("s3_connection_error")
        raise S3ConnectionError(str(exc)) from exc


def get_object_stream(
    s3_key: str,
    byte_range: str | None = None,
) -> tuple[BinaryIO, str, int, str | None]:
    """Devuelve (body, content_type, content_length, content_range)."""
    client = get_s3_client()
    try:
        kwargs: dict = {"Bucket": settings.s3_bucket, "Key": s3_key}
        if byte_range:
            kwargs["Range"] = byte_range
        response = client.get_object(**kwargs)
        content_type = response.get("ContentType", "application/octet-stream")
        content_length = response.get("ContentLength", 0)
        content_range = response.get("ContentRange")
        return response["Body"], content_type, content_length, content_range
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") == "NoSuchKey":
            from errors import NotFoundError

            raise NotFoundError(f"S3 object not found: {s3_key}") from exc
        record_error("s3_download_error")
        raise S3ConnectionError(str(exc)) from exc
