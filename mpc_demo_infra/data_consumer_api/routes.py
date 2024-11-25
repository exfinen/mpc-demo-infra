from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import logging
from datetime import datetime
import asyncio

from ..client_lib import lib as client_lib
from .config import settings


class QueryComputationResponse(BaseModel):
    num_data_providers: int
    max: float
    mean: float
    median: float
    gini_coefficient: float

router = APIRouter()

logger = logging.getLogger(__name__)

# Add these at module level
_computation_cache = None
_last_cache_update = None
_background_task_started = False

async def update_cache():
    global _computation_cache, _last_cache_update
    logger.debug(f"Updating cache at {_last_cache_update}")
    results = await client_lib.query_computation_from_data_consumer_api(
        all_certs_path=Path(settings.certs_path),
        coordination_server_url=settings.coordination_server_url,
        computation_party_hosts=settings.party_hosts,
        poll_duration=settings.poll_duration,
        party_web_protocol=settings.party_web_protocol,
        certs_path=Path(settings.certs_path),
        party_hosts=settings.party_hosts,
        party_ports=settings.party_ports,
    )
    _computation_cache = QueryComputationResponse(
        num_data_providers=results.num_data_providers,
        max=results.max,
        mean=results.mean,
        median=results.median,
        gini_coefficient=results.gini_coefficient,
    )
    _last_cache_update = datetime.now()
    logger.debug(f"Cache updated at {_last_cache_update}. {_computation_cache=}")

async def update_cache_periodically():
    global _computation_cache, _last_cache_update

    while True:
        logger.debug(f"Periodically updating cache at {_last_cache_update}")
        try:
            await update_cache()
        except Exception as e:
            logger.error(f"Error updating cache: {str(e)}")
        logger.debug(f"Sleeping for {settings.cache_ttl_seconds} seconds")
        await asyncio.sleep(settings.cache_ttl_seconds)

@router.get("/query-computation")
async def query_computation():
    global _background_task_started

    # First time we fetch certs and update cache
    if not _background_task_started:
        await update_cache()
        # Start background task to update cache periodically
        asyncio.create_task(update_cache_periodically())
        _background_task_started = True
        logger.info("Started background cache update task")

    if _computation_cache is None:
        raise HTTPException(
            status_code=503,
            detail="Cache not yet initialized. Please try again in a few seconds."
        )

    return _computation_cache
