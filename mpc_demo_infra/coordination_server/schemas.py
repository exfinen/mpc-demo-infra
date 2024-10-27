from pydantic import BaseModel
from typing import Optional


class RequestSharingDataRequest(BaseModel):
    voucher_code: str
    tlsn_proof: str
    client_id: int
    client_cert_file: str
    pop_key: str

class RequestSharingDataResponse(BaseModel):
    client_port_base: int

class RequestQueryComputationRequest(BaseModel):
    client_id: int
    client_cert_file: str
    pop_key: str

class RequestQueryComputationResponse(BaseModel):
    client_port_base: int

class RequestQueuePositionRequest(BaseModel):
    voucher_code: str

class RequestQueuePositionResponse(BaseModel):
    position: int
    pop_key: Optional[str]
