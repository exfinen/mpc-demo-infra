# ETH Inequality @ DevCon 2024

Welcome to the [ETH Inequality Demo @ DevCon 2024](https://demo.mpcstats.org/). Join us in the [Telegram](https://t.me/mpcstats) to stay tuned for more updates!

This guide will help you participate in our survey of ETH distribution across Binance users at DevCon 2024. Don't worry - your data stays private and secure through [MPCStats](https://github.com/ZKStats/mpc-demo-infra) and [TLSNotary](https://tlsnotary.org/). You'll be eligible for an NFT from us and a chance to win $100 only if you complete the [share your balance](#share-your-binance-eth-balance-privately) step successfully.


## Table of Contents
- [Privacy & Security Details](#privacy--security-details)
- [Share Your Binance ETH Balance Privately](#share-your-binance-eth-balance-privately)
  - [Before You Start](#before-you-start)
  - [Step 1: Get Your Binance API Key](#step-1-get-your-binance-api-key)
  - [Step 2: Run the Privacy-Preserving Script](#step-2-run-the-privacy-preserving-script)


## Privacy & Security Details
- Your exact balance remains private throughout the secure multi-party computation (MPC)
- The computing parties **MAY** learn the number of digits of your balance, but not the exact balance
- Security relies on the assumption that our 3 computing parties do not collude
- Your API keys are only used once to fetch your balance and are not stored

## Share Your Binance ETH Balance Privately

### Before You Start
You'll need:
- Docker installed and running on your computer ([Get Docker here](https://docs.docker.com/get-docker/))
- A Binance account with some ETH holdings

### Step 1: Get Your Binance API Key
1. Log into [Binance.com](https://www.binance.com) and navigate to:
   - Click "Account"
   - Select "API Management"
   - [Direct link to API Management](https://www.binance.com/en/my/settings/api-management)
![alt text](pics/image.png)
![alt text](pics/image-1.png)

2. Create a new API key:
   - Click the yellow "Create API" button
   - Choose "System generated"
   - Enter a name for your API key (can be anything)
   - Complete any required verification steps
![alt text](pics/image-2.png)

3. Important Security Settings:
   - ✅ Make sure ONLY "Enable Reading" is selected
   - ❌ Leave all other permissions disabled
   - Save both keys somewhere safe:
     - API Key (looks like: "aBc1234...")
     - Secret Key (looks like: "xYz5678...")
![alt text](pics/image-3.png)

🔒 Security Note: Keep your Secret Key private! Our demo only needs read-only access to check your ETH balance, and we never store your keys.

### Step 2: Run the Privacy-Preserving Script

First, make sure Docker is running on your computer!

Open a terminal/command prompt and run these commands:

```bash
git clone https://github.com/ZKStats/mpc-demo-infra.git
cd mpc-demo-infra/mpc_demo_infra/client_cli/docker
./build.sh
```

Run the script with your details. Please make sure the ETH address is correct to receive the prizes. It will take several minutes to run.
```bash
./share-data.sh <eth-address> <binance-api-key> <binance-api-secret>

# Example (DO NOT COPY, USE YOUR OWN VALUES):
# ./share-data.sh 0x123...abc aBc1234... xYz5678...
```

You'll see the following output:

```
Binance ETH balance data has been shared secretly to MPC parties.
```

### Step 3:Query the Results
Visit https://demo.mpcstats.org/ to see the results.

(You can also run [query-results.sh](query-results.sh) to see the raw results but it takes a while to run.)

### Important Notes
Only 'Free' ETH in your spot account will be counted. This excludes:
- ETH in open orders
- ETH in locked staking
- ETH in savings products
- ETH used as collateral
- ETH in futures/margin accounts


### Need Help?
- Having trouble? Contact us on [Telegram](https://t.me/mpcstats)

### Troubleshooting
Common issues:
1. Docker not running → Start Docker Desktop or Docker daemon
2. Script fails → Check your API key and secret are copied correctly
