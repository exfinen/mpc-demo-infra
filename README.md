# mpc-demo-infra

A demonstration infrastructure for Multi-Party Computation (MPC) using TLSN and MP-SPDZ.

## Table of Contents
- [Dependencies](#dependencies)
- [Documentation](#documentation)
- [Run it using test folder](#run-it-using-tests-folder)
- [Configurations](#configurations)
- [Troubleshooting](#troubleshooting)


## DevCon 2024

To participate in our demo [ETH Inequality @ DevCon 2024](https://demo.mpcstats.org/) and win some prizes, please refer to the [README](mpc_demo_infra/client_cli/docker/README.md) for the entire process.

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
  - need to add `MOD = -DGFP_MOD_SZ=5 -DRING_SIZE=257` to `CONFIG.mine`
  - install: `make setup`
  - build vm: `make replicated-ring-party.x`

## Documentation 
Visit the [Documentation Website](https://docs.mpcstats.org/) for more details.
 
### Run it using tests folder
- Here, we already prepopulate corresponding proof and secret file for two input providers from https://github.com/ZKStats/tlsn/tree/mpspdz-compat.

```
poetry run pytest -s tests/test_integration.py
```

## Configurations

See available configs in
- coordination server: [mpc_demo_infra/coordination_server/config.py](mpc_demo_infra/coordination_server/config.py)
- computation party server: [mpc_demo_infra/computation_party_server/config.py](mpc_demo_infra/computation_party_server/config.py)
- client CLI: [mpc_demo_infra/client_cli/config.py](mpc_demo_infra/client_cli/config.py)

You can use `.env.xxx` to override the default configs.
- `.env.coord`: coordination server. Example in [.env.coord.example](.env.coord.example)
- `.env.party`: computation party server. Example in [.env.party.example](.env.party.example)
- `.env.client_cli`: client CLI. Example in [.env.client_cli.example](.env.client_cli.example)

## Troubleshooting

If you encounter issues:
1. Ensure all dependencies are correctly installed.
2. Check that the required ports (8005-8008, 8010-8100) are not in use.
3. Verify that TLSN and MP-SPDZ are cloned in the correct locations (`../tlsn` and `../MP-SPDZ`).
4. For MP-SPDZ issues, ensure
  - you've added `MOD = -DGFP_MOD_SZ=5` to `CONFIG.mine`.
  - you've generated certificates for computation parties. If not, run `Scripts/setup-ssl.sh` under `../MP-SPDZ`.
  - you've rebuilt the VM. If not, run `make replicated-ring-party.x` under `../MP-SPDZ`.
