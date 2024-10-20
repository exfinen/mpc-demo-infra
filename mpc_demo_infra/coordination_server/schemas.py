from pydantic import BaseModel


class RegisterDataProviderRequest(BaseModel):
    identity: str
    voucher_code: str

class RegisterDataProviderResponse(BaseModel):
    provider_id: int

class RequestSharingDataRequest(BaseModel):
    identity: str
    tlsn_proof: str
    client_id: int
    client_cert_file: str
    input_bytes: int

class RequestSharingDataResponse(BaseModel):
    client_port_base: int

class RequestQueryComputationRequest(BaseModel):
    client_id: int
    client_cert_file: str

class RequestQueryComputationResponse(BaseModel):
    client_port_base: int
