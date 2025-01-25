#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

def gen_env_consumer_api(
  transport: str,
  coord_host: str,
  party_hosts: list[str],
  party_ports: list[int],
):
  output = f"""\
COORDINATION_SERVER_URL={transport}://{coord_host}:8005
CERTS_PATH=certs
PARTY_HOSTS={json.dumps(party_hosts)}
PARTY_PORTS={json.dumps(party_ports)}
PRIVKEY_PEM_PATH=ssl_certs/privkey.pem
FULLCHAIN_PEM_PATH=ssl_certs/fullchain.pem
PARTY_WEB_PROTOCOL={transport}
PORT=8004
"""
  return output

def gen_env_coord(
  transport: str,
  party_hosts: list[str],
  party_ports: list[int],
):
  output = f"""\
PORT=8005
PARTY_HOSTS={json.dumps(party_hosts)}
PARTY_PORTS={json.dumps(party_ports)}
PARTY_API_KEY=81f47c24b9fbe22421ea3ae92a9cc8f6
PARTY_WEB_PROTOCOL={transport}
PROHIBIT_MULTIPLE_CONTRIBUTIONS=False
USER_QUEUE_HEAD_TIMEOUT=60
PRIVKEY_PEM_PATH=ssl_certs/privkey.pem
FULLCHAIN_PEM_PATH=ssl_certs/fullchain.pem
"""
  return output

def gen_env_party(
  transport: str,
  coord_host: str,
  party_hosts: list[str],
  party_ports: list[int], 
):
  output = f"""\
PORT=8006
PARTY_ID=0
COORDINATION_SERVER_URL={transport}://{coord_host}:8005
PARTY_API_KEY=81f47c24b9fbe22421ea3ae92a9cc8f6
PARTY_HOSTS={json.dumps(party_hosts)}
PARTY_PORTS={json.dumps(party_ports)}
PARTY_WEB_PROTOCOL={transport}
MAX_DATA_PROVIDERS=1000
PERFORM_COMMITMENT_CHECK=False
PRIVKEY_PEM_PATH=ssl_certs/privkey.pem
FULLCHAIN_PEM_PATH=ssl_certs/fullchain.pem
"""
  return output

def gen_docker_compose(coord_ip: str):
  return """\
services:
  coord:
    build:
      context: ./mpc_demo_infra/coordination_server/docker
    ports:
      - "8005:8005"
    volumes:
      - coord-data:/root/mpc-demo-infra/
    stdin_open: true
    tty: true
    init: true
    extra_hosts:
      - "tlsnotaryserver.io:127.0.0.1"
    depends_on:
      - party_0
      - party_1
      - party_2
  notary:
    build:
      context: ./mpc_demo_infra/notary_server/docker
      args:
        COORD_IP: {coord_ip}
    ports:
      - "8003:8003"
    environment:
      - COORD_IP={coord_ip}
    stdin_open: true
    tty: true
    init: true
    extra_hosts:
      - "tlsnotaryserver.io:127.0.0.1"

  data_consumer_api:
    build:
      context: ./mpc_demo_infra/data_consumer_api/docker
    ports:
      - "8004:8004"
    stdin_open: true
    tty: true
    init: true

  party_0:
    build:
      context: ./mpc_demo_infra/computation_party_server/docker
      args:
        PORT: 8006
        PARTY_ID: 0
        NUM_PARTIES: {num_parties}
    ports:
      - "8006:8006"
      - "8019:8019"
    environment:
      - PARTY_ID=0
    volumes:
      - party0-data:/root/MP-SPDZ/
    stdin_open: true
    tty: true
    init: true
    extra_hosts:
      - "tlsnotaryserver.io:127.0.0.1"

  party_1:
    build:
      context: ./mpc_demo_infra/computation_party_server/docker
      args:
        PORT: 8007
        PARTY_ID: 1
        NUM_PARTIES: {num_parties}
    ports:
      - "8007:8007"
      - "8020:8020"
    environment:
      - PARTY_ID=1
    volumes:
      - party1-data:/root/MP-SPDZ/
    stdin_open: true
    tty: true
    init: true
    extra_hosts:
      - "tlsnotaryserver.io:127.0.0.1"
  party_2:
    build:
      context: ./mpc_demo_infra/computation_party_server/docker
      args:
        PORT: 8008
        PARTY_ID: 2
        NUM_PARTIES: {num_parties}
    ports:
      - "8008:8008"
      - "8021:8021"
    environment:
      - PARTY_ID=2
    volumes:
      - party2-data:/root/MP-SPDZ/
    stdin_open: true
    tty: true
    init: true
    extra_hosts:
      - "tlsnotaryserver.io:127.0.0.1"
volumes:
  coord-data:
  party0-data:
  party1-data:
  party2-data:
"""
  return s

def parse_args():
  parser = argparse.ArgumentParser(description="config-file generation script")
  parser.add_argument(
    '--transport',
    choices=['http', 'https'],
    default='http',
    help=f"Transport to use. http is used by default",
  )
  parser.add_argument(
    '--coord-ip',
    type=str,
    default='127.0.0.1',
    help="IP address of the server on which the coordination server runs",
  )
  parser.add_argument(
    '--dry-run',
    action='store_true',
    help='Print out the contents of config files',
  )
  return parser.parse_args()

args = parse_args()

def write_file(file_path: Path, content: str, args):
  if args.dry_run:
    print(f"----> {file_path}")
    print(content)
  else:
    with open(file_path, 'w') as f:
      f.write(content)
    print(f"Created {str(file_path)}")

party_hosts = ["party_0", "party_1", "party_2"]
party_ports =[8006, 8007, 8008]

# write .env.consumer_api
dot_env_consumer_api = gen_env_consumer_api(
  args.transport,
  args.coord_ip,
  party_hosts,
  party_ports,
)

mpc_demo_infra = Path('mpc_demo_infra')
write_file(mpc_demo_infra / 'data_consumer_api' / 'docker' / '.env.consumer_api', dot_env_consumer_api, args)

# write .env.coord
dot_env_coord = gen_env_coord(
  args.transport,
  party_hosts,
  party_ports,
)
write_file(mpc_demo_infra / 'coordination_server' / 'docker' / '.env.coord', dot_env_coord, args)

# write .env.party for partys
dot_env_party = gen_env_party(
  args.transport,
  args.coord_ip,
  party_hosts,
  party_ports,
)
write_file(mpc_demo_infra / 'computation_party_server' / 'docker' / '.env.party', dot_env_party, args)

# write docker-compose.yml
docker_compose_yml = gen_docker_compose(args.coord_ip)
write_file(Path('docker-compose.yml'), docker_compose_yml, args)

