from pydantic import BaseModel


class RequestSharingDataRequest(BaseModel):
    voucher_code: str
    tlsn_proof: str
    client_id: int
    client_cert_file: str

class RequestSharingDataResponse(BaseModel):
    client_port_base: int

class RequestQueryComputationRequest(BaseModel):
    client_id: int
    client_cert_file: str

class RequestQueryComputationResponse(BaseModel):
    client_port_base: int
