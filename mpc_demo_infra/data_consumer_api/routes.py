from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import logging
from datetime import datetime
import asyncio
from fastapi.applications import FastAPI

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
_background_task = None
_background_task_started = False

async def update_cache():
    global _computation_cache, _last_cache_update
    logger.info(f"Updating cache at {_last_cache_update}")
    results = await client_lib.query_computation_from_data_consumer_api(
        all_certs_path=Path(settings.certs_path),
        coordination_server_url=settings.coordination_server_url,
        computation_party_hosts=settings.party_hosts,
        poll_duration=settings.poll_duration,
        party_web_protocol=settings.party_web_protocol,
        certs_path=Path(settings.certs_path),
        party_hosts=settings.party_hosts,
        party_ports=settings.party_ports,
        max_client_wait=settings.max_client_wait,
    )
    _computation_cache = QueryComputationResponse(
        num_data_providers=results.num_data_providers,
        max=results.max,
        mean=results.mean,
        median=results.median,
        gini_coefficient=results.gini_coefficient,
    )
    _last_cache_update = datetime.now()
    logger.info(f"Cache updated at {_last_cache_update}. {_computation_cache=}")

async def update_cache_periodically():
    global _computation_cache, _last_cache_update
    while True:
        try:
            await update_cache()
        except asyncio.CancelledError:
            logger.info("Cache update task cancelled")
            break
        except Exception as e:
            logger.error(f"Error updating cache: {str(e)}")
        try:
            await asyncio.sleep(settings.cache_ttl_seconds)
        except asyncio.CancelledError:
            logger.info("Cache update task cancelled during sleep")
            break

@router.get("/query-computation")
async def query_computation():
    global _background_task_started

    # First time we fetch certs and update cache
    if not _background_task_started:
        await update_cache()
        # Start background task to update cache periodically
        _background_task = asyncio.create_task(update_cache_periodically())
        _background_task.set_name('cache_updater')
        _background_task_started = True
        logger.info("Started background cache update task")

    if _computation_cache is None:
        raise HTTPException(
            status_code=503,
            detail="Cache not yet initialized. Please try again in a few seconds."
        )

    return _computation_cache

# @router.on_event("startup")
# async def startup_event():
#     global _background_task, _background_task_started
#     if not _background_task_started:
#         _background_task = asyncio.create_task(update_cache_periodically())
#         _background_task.set_name('cache_updater')
#         _background_task_started = True
#         logger.info("Started background cache update task")

@router.on_event("shutdown")
async def shutdown_event():
    global _background_task, _background_task_started
    if _background_task_started and _background_task:
        logger.info("Cancelling background cache update task")
        _background_task.cancel()
        try:
            await _background_task
        except asyncio.CancelledError:
            pass
        _background_task_started = False
        logger.info("Background cache update task cancelled")
