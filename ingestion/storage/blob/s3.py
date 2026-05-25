from __future__ import annotations

import asyncio
import logging

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class S3Blob:
    def __init__(
        self,
        bucket: str,
        region: str = "us-east-1",
        endpoint_url: str | None = None,
    ) -> None:
        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint_url,  # None = real AWS; set to http://localhost:4566 for LocalStack
        )

    async def put(self, key: str, data: bytes, metadata: dict[str, str] | None = None) -> None:
        kwargs: dict = {"Bucket": self._bucket, "Key": key, "Body": data}
        if metadata:
            kwargs["Metadata"] = metadata
        await asyncio.to_thread(self._client.put_object, **kwargs)
        logger.info("blob.s3.put key=%s bytes=%s", key, len(data))

    async def exists(self, key: str) -> bool:
        try:
            await asyncio.to_thread(self._client.head_object, Bucket=self._bucket, Key=key)
            return True
        except ClientError as exc:
            if exc.response["Error"]["Code"] in ("404", "NoSuchKey"):
                return False
            raise
