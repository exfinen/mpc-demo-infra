#!/usr/bin/env python3

import argparse
import json
import os
from pathlib import Path

def parse_args():
  parser = argparse.ArgumentParser(description="docker-compose generation script")
  parser.add_argument(
    'coord_host',
    type=str,
    help='Coordination server host',
  )
  parser.add_argument(
    'party_hosts',
    type=str,
    help='Comma-separated list of computation party server hosts',
  )
  parser.add_argument(
    '--transport',
    choices=['http', 'https'],
    default='http',
    help="Transport to use'"
  )
  parser.add_argument(
    '--https',
    action='store_true',
    help='Use HTTPS',
  )
  parser.add_argument(
    '--dry-run',
    action='store_true',
    help='Print out docker-compose.yml without creating a file',
  )
  return parser.parse_args()

args = parse_args()

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

def gen_docker_compose(num_parties: int):
  output_1 = """\
version: "3.8"

services:
  coord:
    build:
      context: ./mpc_demo_infra/coordination_server/docker
    ports:
      - "8005-8100:8005-8100"
    volumes:
      - coord-data:/root/mpc-demo-infra/
    stdin_open: true
    tty: true
    init: true

  notary:
    build:
      context: ./mpc_demo_infra/notary_server/docker
    ports:
      - "8003:8003"
    stdin_open: true
    tty: true
    init: true

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
    ports:
      - "8000-8100:8000-8100"
    environment:
      - PARTY_ID=0
    volumes:
      - party0-data:/root/MP-SPDZ/
    stdin_open: true
    tty: true
    init: true

  party_1:
    build:
      context: ./mpc_demo_infra/computation_party_server/docker
      args:
        PORT: 8007
        PARTY_ID: 1
    ports:
      - "8000-8100:8000-8100"
    environment:
      - PARTY_ID=1
    volumes:
      - party1-data:/root/MP-SPDZ/
    stdin_open: true
    tty: true
    init: true
"""

  output_2 = """\
  party_2:
    build:
      context: ./mpc_demo_infra/computation_party_server/docker
      args:
        PORT: 8008
        PARTY_ID: 2
    ports:
      - "8000-8100:8000-8100"
    environment:
      - PARTY_ID=2
    volumes:
      - party1-data:/root/MP-SPDZ/
    stdin_open: true
    tty: true
    init: true
"""

  output_3 = """\
volumes:
  coord-data:
  party0-data:
  party1-data:
  party2-data:
"""

  output = output_1 + (output_2 if num_parties == 3 else "") + output_3
  return output

def write_file(file_path: Path, content: str, args):
  if args.dry_run:
    print(f"----> {file_path}")
    print(content)
  else:
    if os.path.exists('docker-compose.yml') and not args.overwrite:
      print(f"{str(file_path)} already exists")
    else:
      with open(file_path, 'w') as f:
        f.write(content)

party_hosts = [host.strip() for host in args.party_hosts.split(',')]
if len(party_hosts) != 2 and len(party_hosts) != 3:
  raise ValueError(f"Only 2 or 3 computation parties are supported, but got {party_hosts}")

num_parties = len(party_hosts)

party_ports =[8006, 8007]
if num_parties == 3:
  party_hosts.append(8008)

# write .env.consumer_api
dot_env_consumer_api = gen_env_consumer_api(
  args.transport,
  args.coord_host,
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
  args.coord_host,
  party_hosts,
  party_ports,
)
write_file(mpc_demo_infra / 'computation_party_server' / 'docker' / '.env.party', dot_env_party, args)

# write docker-compose.yml
docker_compose_yml = gen_docker_compose(num_parties)
write_file(Path('docker-compose.yml'), docker_compose_yml, args)

