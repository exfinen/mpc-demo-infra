from pydantic import BaseModel
from typing import Optional

class RequestSharingDataMPCRequest(BaseModel):
    client_id: int
    mpc_port_base: int
    client_port: int
    tlsn_proof: str

class RequestSharingDataMPCResponse(BaseModel):
    data_commitment: str

class QueryComputationRequest(BaseModel):
    computation_index: int

class QueryComputationResponse(BaseModel):
    success: bool
    message: str
    computation_index: int
    computation_result: str
