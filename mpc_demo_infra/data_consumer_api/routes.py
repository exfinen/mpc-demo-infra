from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import logging

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


@router.get("/query-computation")
async def query_computation():
    try:
        # TODO: add cache for different computation index
        await client_lib.fetch_parties_certs(
            party_web_protocol=settings.party_web_protocol,
            certs_path=Path(settings.certs_path),
            party_hosts=settings.party_hosts,
            party_ports=settings.party_ports,
        )
        logger.debug(f"Fetched party certs. Kicking off computation")
        results = await client_lib.query_computation_from_data_consumer_api(
            all_certs_path=Path(settings.certs_path),
            coordination_server_url=settings.coordination_server_url,
            computation_party_hosts=settings.party_hosts,
            poll_duration=settings.poll_duration,
        )
        logger.debug(f"Finished computation. Results={results}")
        return QueryComputationResponse(
            num_data_providers=results.num_data_providers,
            max=results.max,
            mean=results.mean,
            median=results.median,
            gini_coefficient=results.gini_coefficient,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
