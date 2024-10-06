from pydantic import BaseModel
from typing import Optional

class ShareDataRequest(BaseModel):
    identity: str
    tlsn_proof: str

class ShareDataResponse(BaseModel):
    success: bool
    message: Optional[str] = None

class QueryComputationRequest(BaseModel):
    computation_index: int

class QueryComputationResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    computation_result: str
