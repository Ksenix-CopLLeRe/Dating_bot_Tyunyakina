from __future__ import annotations

import logging
import uuid
from io import BytesIO

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from .config import (
    S3_ACCESS_KEY_ID,
    S3_BUCKET_NAME,
    S3_ENDPOINT_URL,
    S3_REGION_NAME,
    S3_SECRET_ACCESS_KEY,
)


logger = logging.getLogger(__name__)


def s3_client():
    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT_URL,
        aws_access_key_id=S3_ACCESS_KEY_ID,
        aws_secret_access_key=S3_SECRET_ACCESS_KEY,
        region_name=S3_REGION_NAME,
    )


def ensure_bucket_exists() -> None:
    client = s3_client()
    try:
        client.head_bucket(Bucket=S3_BUCKET_NAME)
    except ClientError:
        client.create_bucket(Bucket=S3_BUCKET_NAME)
        logger.info("s3.bucket_created", extra={"bucket": S3_BUCKET_NAME})


def build_profile_photo_key(telegram_id: str, filename: str | None = None) -> str:
    extension = "jpg"
    if filename and "." in filename:
        extension = filename.rsplit(".", 1)[-1].lower()[:10]
    return f"profiles/{telegram_id}/{uuid.uuid4().hex}.{extension}"


def upload_profile_photo(
    *,
    telegram_id: str,
    content: bytes,
    content_type: str | None,
    filename: str | None = None,
) -> str:
    ensure_bucket_exists()
    object_key = build_profile_photo_key(telegram_id, filename)
    client = s3_client()
    client.put_object(
        Bucket=S3_BUCKET_NAME,
        Key=object_key,
        Body=content,
        ContentType=content_type or "application/octet-stream",
    )
    logger.info(
        "s3.photo_uploaded",
        extra={"telegram_id": telegram_id, "bucket": S3_BUCKET_NAME, "key": object_key},
    )
    return object_key


def download_photo(object_key: str) -> tuple[bytes, str]:
    client = s3_client()
    try:
        response = client.get_object(Bucket=S3_BUCKET_NAME, Key=object_key)
    except (BotoCoreError, ClientError) as exc:
        logger.warning("s3.photo_download_failed", extra={"key": object_key, "error": str(exc)})
        raise

    body = response["Body"].read()
    content_type = response.get("ContentType") or "application/octet-stream"
    return body, content_type


def is_s3_photo_reference(value: str | None) -> bool:
    return bool(value and value.startswith("profiles/"))
