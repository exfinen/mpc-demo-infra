# Running Notary Server with Docker

## Running the server
Run the following commands, replacing %NOTARY_IP% with the IP address of the server on which the Notary server runs:

```bash
docker build  --build-arg NOTARY_IP=%NOTARY_IP% -t notary .
docker run --init -it -p 8003:8003 notary
```

