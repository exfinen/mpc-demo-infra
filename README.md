# mpc-demo-infra

A demonstration infrastructure for Multi-Party Computation (MPC) using TLSN and MP-SPDZ.

## Table of Contents
- [DevCon 2024](#devcon-2024)
- [Run it using test folder](#run-it-using-tests-folder)
- [Documentation](#documentation)


## DevCon 2024

To participate in our demo [ETH Inequality @ DevCon 2024](https://demo.mpcstats.org/) and win some prizes, please refer to the [README](mpc_demo_infra/client_cli/docker/README.md) for the entire process.

### Run it using tests folder
- Here, we already prepopulate corresponding proof and secret file for two input providers from https://github.com/ZKStats/tlsn/tree/mpspdz-compat.

```
poetry run pytest -s tests/test_integration.py
```

## Documentation 
Visit the [Documentation Website](https://docs.mpcstats.org/) for more details.
 
