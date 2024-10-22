# mpc-demo-infra

## Dependencies
- python 3
- poetry
- cargo
- [TLSN](https://github.com/ZKStats/tlsn)
    - branch: `mpspdz-compat`
    - clone it as `../tlsn`
- [MP-SPDZ](https://github.com/ZKStats/MP-SPDZ) (only required for computation party server)
    - branch: `demo_client`
    - clone it as `../MP-SPDZ`
    - need to add `MOD = -DGFP_MOD_SZ=5` to `CONFIG.mine`
    - install: `make setup`
    - build vm: `make semi-party.x`

The above dependencies can be installed by running the following script `./setup_env.sh`.

## Getting started
### Coordination server
Prepare environment:
```bash
./setup_env.sh
```

To change configs, edit `.env.coord`:
```bash
cp .env.coord.example .env.coord
```

Run:
```bash
poetry run coord-run
```

### Computation party server
Prepare environment:
```bash
./setup_env.sh --setup-mpspdz
```

To change configs, edit `.env.party`:
```bash
cp .env.party.example .env.party
```

Generate vouchers:
```bash
poetry run coord-gen-vouchers <num_vouchers>
```

List vouchers:
```bash
poetry run coord-list-vouchers
```

Run the server:
```bash
poetry run party-run
```

### Client CLI

To change configs, edit `.env.client`:
```bash
cp .env.client.example .env.client
```

Share data:
```bash
poetry run client-share-data <voucher_code>
```

Query computation result:
```bash
poetry run client-query <computation_index>
```
