## Binance Example: Notarize Private Ethereum Balance from spot account from api.binance.com (Rust)

This example demonstrates using TLSNotary with Binance API.

1. Run local notary server (If not having one running already)
2. Notarize: Fetch <https://api.binance.com/api/v3/account?/> followed by time, signature, and omitZeroBalances=true to query all non-zero balance of this user. Then we create a proof of the amount of free ETH token in spot account. Most parts of the proof are redacted, while the amount of free ETH in spot account up to 2 decimal points is redacted and included in the proof for further mpspdz usage.
3. Verify the proof.

### 1. Run local notary server (If not having one running already)

Run this command line in mpc-demo-infra/ folder

```
./setup_env.sh --notary
cd tlsn/notary/target/release
./notary-server
```

This will run local notary server, to be used with testing prover & verifier.

### 2. Notarize <https://api.binance.com/api/v3/account?> with the queries

Now open another terminal & Run a binance prover: (Make sure you run command line in mpc-demo-infra/tlsn/tlsn/examples/)

```shell
cargo run --release --example binance_prover <notary_host> <notary_port> <api_key> <api_secret> <proof_file_dest> <secret_file_dest> ../../../notary.crt
```

where
<notary_host> <notary_port> can be easily used as 127.0.0.1 8003 since we already deployed local notary server to use with MPCStats with the previous step
<api_key> <api_secret> can be optained from your Binance account by following this [guide](https://github.com/ZKStats/mpc-demo-infra/blob/main/mpc_demo_infra/client_cli/docker/README.md#step-1-get-your-binance-api-key).
<proof_file_dest> specifies the file destination (in json) to store the proof
<secret_file_dest> specifies the file destination to store private data like free ETH balance & its corresponding Nonce needed for proving the secret value in MP-SPDZ later on.

Note that we only create a proof for ETH balance up to 2 decimal points.

If the notarization was successful, you should see this output end like this in the console:

```log
The free amount of ETH is: <eth_bal>
2-decimal free ETH: <two_dec_eth_bal>
!@# Actual sent data size: 447 bytes
!@# Actual received data size: 3513 bytes
Received private ranges: [1380..1384]
Committing to private ranges
Committing to private range 1380..1384
Revealing private commitment CommitmentId(8)
Received private ranges: [1380..1384]
Notarization completed successfully!
```

Note that there're gonna be lots more outputs like all the response we got from Binance API, which would be shown before the log above. <eth_bal> and <two_dec_eth_bal> would be replaced with plaintext of your full ETH balance (8-decimal in this Binance example) and 2-decimal ETH balance of your own correspondingly.

### 3. Verify the Proof

When you open <proof_file_des> in an editor, you will see a JSON file with lots of non-human-readable byte arrays. You can decode this file by running: (Make sure you run command line in mpc-demo-infra/tlsn/tlsn/examples/)

```
cargo run --release --example binance_verifier <proof_file_dex>
```

where <proof_file_des> specifies the proof file destination to be read from.

We can see the output like this
...

```log
Successfully verified that the bytes below came from a session with Dns("api.binance.com") at 2025-02-21 02:37:58 UTC.
Note that the bytes which the Prover chose not to disclose (redacted) are shown as X, while those which the Prover chose to privatize (redacted & include sha3 commitment in the proof) are shown as Y

Bytes sent:

GET /api/v3/account?omitZeroBalances=true&recvWindow=60000&signature=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX&timestamp=1740105479062 HTTP/1.1
host: api.binance.com
x-mbx-apikey: XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
accept: */*
accept-encoding: identity
connection: close
user-agent: XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX


Bytes received:

HTTP/1.1 200 OKXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX{"asset":"ETH","free":"YYYYXXXXXX"XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"uid":79594445}
```

We can see that YYYY is the only part of the data whose proof is included in the <proof_file_des> (as its corresponding sha3 commitment), other parts that are XX... are just redacted like in original TLSNotary

### Customization

> This is a bit different from original TLSNotary, because in addition to being able to specify "redacted" parts of data where they are just not shown in the proof, users can also specify the "private" parts in the proof, which are not only not shown in the proof, but also having their sha3 commitment in the proof such that they can be seamlessly integrated with MP-SPDZ to make sure that the inputs of MP-SPDZ actually come from the private parts of these data from TLSNotary. This guide will mostly focus on customizing this additional "private" feature.

Here is how you can customize your own TLSNotary proof with "private" data by modifying these following files:

> This "binance" folder shows more granular control over "redacted" and "private". If you are new to this codebase, maybe it's better to first look at [simple example](../simple/) where we only focus on making "private" part on received message. (No redacted parts like in original TLSNotary)

#### binance_prover.rs

Here is the main file for creating proof, where you can make this following customizations for "private" part of data.

**In main()**:

- Specify "secret_file" format, the json format of the secret and its corresponding nonce to be written into the file containing all private information used to prove later that its sha3 hash is the sha3 commitment contained in the proof.

**In build_proof_with_redactions()**:

- Specify "redacted" parts in sent message.
  In this Binance example, we want to redact lots of things like user_agent, api_key and signature. We achieve so by specifying both the exact variable to make private (e.g. user_agent & api_key in this case) and specific regex (in this case, to censor things after "signature="). Then we took the whole range of sent message deducted those ranges above we want to redact to achieve sent_public_ranges.

- Specify "public" parts of the received message.
  We specify the part that we want to make it publicly shown in the proof (recv_public_ranges), by specifying the regex that must be "redacted" & "private" (So, just specify what you expect to be not shown in the plain text verifier)

- Specify "private" parts of the received message.  
  We specify the private part (recv_private_ranges)that will be accompanied with sha3 commitment in the proof while being censored from the proof itself by specifying our preferred regex. In Binance example, we specify to make ETH free balance of only 2 decimlals precision private.

> With this structure, there will be some parts of received message that is not in either recv_public_ranges or recv_private_ranges. Those will be just redacted data that are censored without its correponding commitment (like in original TLSNotary)

> Since we decide which part to censor based on regex, it is very important to make sure that the returned data is formatted as you expect when you write regex or else there may result in unexpected data leaking. In our case, we enforce the check that recv transcript ends with uid because this is the assumption that we used to constrain regex in determining recv_public_ranges

> In getting data from API, it's recommended to specify as many arguments for API query as possible because we prefer the data sent back from API to be as smallest as possible.

#### binance_verifier.rs

Here, we specify what alphabet we want to replace the parts that are made private. (Ofc, you can change what alphabet to represent "redacted" parts as well)

```
    sent.set_redacted(b'X');
    recv.set_redacted(b'X');
    recv.set_private(b'Y');
```
