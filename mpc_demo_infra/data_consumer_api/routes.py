from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import logging

from ..client_lib import lib as client_lib
from .config import settings


class QueryComputationResponse(BaseModel):
    results: list[float]

router = APIRouter()

logger = logging.getLogger(__name__)


@router.post("/query-computation")
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
        return QueryComputationResponse(results=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
