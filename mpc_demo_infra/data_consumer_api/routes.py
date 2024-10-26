from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..client_lib import lib as client_lib
from .config import settings


class QueryComputationRequest(BaseModel):
    computation_index: int = Field(..., ge=0)

class QueryComputationResponse(BaseModel):
    results: list[float]

router = APIRouter()


@router.post("/query-computation")
async def query_computation(request: QueryComputationRequest):
    try:
        # TODO: add cache for different computation index
        await client_lib.fetch_parties_certs(
            party_web_protocol=settings.party_web_protocol,
            certs_path=Path(settings.certs_path),
            party_hosts=settings.party_hosts,
            party_ports=settings.party_ports,
        )
        results = await client_lib.query_computation(
            all_certs_path=Path(settings.certs_path),
            coordination_server_url=settings.coordination_server_url,
            computation_party_hosts=settings.party_hosts,
            computation_index=request.computation_index,
        )
        return QueryComputationResponse(results=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
