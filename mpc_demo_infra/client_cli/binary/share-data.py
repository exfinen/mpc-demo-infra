import os
import certifi
from mpc_demo_infra.client_cli.main import notarize_and_share_data_cli

os.environ['SSL_CERT_FILE'] = certifi.where()

if __name__ == "__main__":
    notarize_and_share_data_cli()

