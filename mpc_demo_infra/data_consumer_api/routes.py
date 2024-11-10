from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import logging
from datetime import datetime

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


@router.get("/query-computation")
async def query_computation():
    global _computation_cache, _last_cache_update

    try:
        current_time = datetime.now()

        # Check if cache is valid
        if (_computation_cache is not None and _last_cache_update is not None and
            (current_time - _last_cache_update).total_seconds() < settings.cache_ttl_seconds):
            logger.debug("Returning cached computation results")
            return _computation_cache

        # If cache is invalid or doesn't exist, perform computation
        await client_lib.fetch_parties_certs(
            party_web_protocol=settings.party_web_protocol,
            certs_path=Path(settings.certs_path),
            party_hosts=settings.party_hosts,
            party_ports=settings.party_ports,
        )
        logger.debug("Fetched party certs. Kicking off computation")
        results = await client_lib.query_computation_from_data_consumer_api(
            all_certs_path=Path(settings.certs_path),
            coordination_server_url=settings.coordination_server_url,
            computation_party_hosts=settings.party_hosts,
            poll_duration=settings.poll_duration,
        )
        logger.debug(f"Finished computation. Results={results}")

        # Update cache
        _computation_cache = QueryComputationResponse(
            num_data_providers=results.num_data_providers,
            max=results.max,
            mean=results.mean,
            median=results.median,
            gini_coefficient=results.gini_coefficient,
        )
        _last_cache_update = current_time
        return _computation_cache
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
