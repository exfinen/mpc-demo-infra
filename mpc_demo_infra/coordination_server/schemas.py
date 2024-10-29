from pydantic import BaseModel
from typing import Optional


class RequestSharingDataRequest(BaseModel):
    voucher_code: str
    tlsn_proof: str
    client_id: int
    client_cert_file: str
    computation_key: str

class RequestSharingDataResponse(BaseModel):
    client_port_base: int

class RequestQueryComputationRequest(BaseModel):
    client_id: int
    client_cert_file: str
    computation_key: str

class RequestQueryComputationResponse(BaseModel):
    client_port_base: int

class RequestGetPositionRequest(BaseModel):
    voucher_code: str

class RequestGetPositionResponse(BaseModel):
    position: Optional[int]
    computation_key: Optional[str]

class RequestValidateComputationKeyRequest(BaseModel):
    computation_key: str

class RequestValidateComputationKeyResponse(BaseModel):
    is_valid: bool

class RequestFinishComputationRequest(BaseModel):
    computation_key: str

class RequestFinishComputationResponse(BaseModel):
    is_finished: bool
