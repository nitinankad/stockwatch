from __future__ import annotations

import asyncio

from dotenv import load_dotenv

from llm_analyzer.analyzer import LLMAnalyzer
from llm_analyzer.config import Settings
from llm_analyzer.worker import LLMAnalyzerWorker
from shared.logging import configure
from shared.queue import RabbitMQQueue


def _build_blob(settings: Settings):
    if settings.blob_backend == "local":
        from ingestion.storage.blob.local import LocalFilesystemBlob
        return LocalFilesystemBlob(settings.local_blob_root)
    from ingestion.storage.blob.s3 import S3Blob
    return S3Blob(
        bucket=settings.s3_bucket,
        region=settings.s3_region,
        endpoint_url=settings.s3_endpoint_url,
    )


def build_worker(settings: Settings) -> LLMAnalyzerWorker:
    if not settings.deepseek_api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is required for llm_analyzer")
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required for llm_analyzer")
    if not settings.rabbitmq_url:
        raise RuntimeError("RABBITMQ_URL is required for llm_analyzer")

    return LLMAnalyzerWorker(
        analyzer=LLMAnalyzer(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            model=settings.deepseek_model,
        ),
        blob=_build_blob(settings),
        queue=RabbitMQQueue(settings.rabbitmq_url, settings.queue_name),
        database_url=settings.database_url,
        outbound_queue=RabbitMQQueue(settings.rabbitmq_url, settings.outbound_queue_name),
    )


def main() -> None:
    load_dotenv()
    settings = Settings()
    configure(settings.log_level)
    asyncio.run(build_worker(settings).run())


if __name__ == "__main__":
    main()
