# mpc-demo-infra

## Dependencies
- python 3
- poetry
- cargo
- [TLSN](https://github.com/ZKStats/tlsn)
    - clone it as `../tlsn`
    - branch: `mpspdz-compat`
- [MP-SPDZ](https://github.com/ZKStats/MP-SPDZ) (only required for computation party server)
    - clone it as `../MP-SPDZ`
    - branch: `demo_client`
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

Edit `.env.coord`:
```bash
cp .env.coord.example .env.coord
```

Run:
```bash
poetry run coordination-server-run
```

### Computation party server
Prepare environment:
```bash
./setup_env.sh --setup-mpspdz
```

Edit `.env.party`:
```bash
cp .env.party.example .env.party
```

Run:
```bash
poetry run computation-party-server-run
```

### Data provider client

### Computation query client
