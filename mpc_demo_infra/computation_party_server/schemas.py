from pydantic import BaseModel

class RequestSharingDataMPCRequest(BaseModel):
    tlsn_proof: str
    mpc_port_base: int
    secret_index: int
    client_id: int
    client_port: int
    client_cert_file: str

class RequestSharingDataMPCResponse(BaseModel):
    data_commitment: str

class QueryComputationRequest(BaseModel):
    computation_index: int

class QueryComputationResponse(BaseModel):
    success: bool
    message: str
    computation_index: int
    computation_result: str


class RequestCertResponse(BaseModel):
    cert_file: str
