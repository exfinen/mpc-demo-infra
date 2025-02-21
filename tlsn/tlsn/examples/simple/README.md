## Simple Example: Notarize Public Data from plain HTML page (Rust) <a name="rust-simple"></a>

This example demonstrates the simplest possible use case for TLSNotary that's compatible with mp-spdz, meaning that in the proof, we can privatize some part of the HTML page, while still attaching the sha3 commitment of those private parts in the proof to be used later.

Here, we notarize and generate proof of number of from either <https://jernkunpittaya.github.io/followers-page/party_0.html>, <https://jernkunpittaya.github.io/followers-page/party_1.html>, or <https://jernkunpittaya.github.io/followers-page/party_2.html>,

1. Run local notary server (If not having one running already)
2. Notarize: Fetch https://jernkunpittaya.github.io/followers-page/party_[i].html where i can be either 0, 1, or 2 and create a proof of its content.
3. Verify the proof.

Next, we will redact the content and verify it again:

1. Redact the `USER_AGENT` and Privatize the number of followers (i.e. number after "followers=")
2. Verify the proof.

### 1. Run local notary server (If not having one running already)

Run this command line in mpc-demo-infra/ folder

```
./setup_env.sh --notary
cd tlsn/notary/target/release
./notary-server
```

This will run local notary server, to be used with testing prover & verifier.

### 2. Notarize the website

Now open another terminal & Run a simple prover: (Make sure you run command line in mpc-demo-infra/tlsn/tlsn/examples/)

```shell
cargo run --release --example simple_prover <notary_host> <notary_port> <n> <proof_file_dest> <secret_file_dest> ../../../notary.crt
```

where
<notary_host> <notary_port> can be easily used as prod-notary.mpcstats.org 8003 since we already deployed remote notary to use with MPCStats
<n> is either 0, 1, or 2
<proof_file_dest> specifies the file destination (in json) to store the proof
<secret_file_dest> specifies the file destination to store private data like free ETH balance & its corresponding Nonce needed for proving the secret value in MP-SPDZ later on.

If the notarization was successful, you should see this output in the console: (this is example from n = 0)

```log
Starting an MPC TLS connection with the server
Got a response from the server
Response body:
<!DOCTYPE html>
<html>
<body>
followers=12
</body>
</html>

Party 0 has 12 followers
Received private ranges: [763..765]
Committing to private ranges
Committing to private range 763..765
Revealing private commitment CommitmentId(4)
Received private ranges: [763..765]
Notarization completed successfully!
```

### 3. Verify the Proof

When you open <proof_file_des> in an editor, you will see a JSON file with lots of non-human-readable byte arrays. You can decode this file by running: (Make sure you run command line in mpc-demo-infra/tlsn/tlsn/examples/)

```shell
cargo run --release --example simple_verifier <proof_file_dest>
```

where <proof_file_des> specifies the proof file destination to be read from.

This will output the TLS-transaction in clear text:

```log
Successfully verified that the bytes below came from a session with Dns("jernkunpittaya.github.io") at 2025-02-21 02:30:04 UTC.
Note that the bytes which the Prover chose not to disclose (redacted) are shown as X, while those which the Prover chose to privatize (redacted & include sha3 commitment in the proof) are shown as Y

Bytes sent:

GET /followers-page/party_0.html HTTP/1.1
host: jernkunpittaya.github.io
accept: */*
accept-encoding: identity
connection: close
user-agent: XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX


Bytes received:

HTTP/1.1 200 OK
Connection: close
Content-Length: 59
Server: GitHub.com
Content-Type: text/html; charset=utf-8
permissions-policy: interest-cohort=()
Last-Modified: Tue, 18 Feb 2025 13:20:53 GMT
Access-Control-Allow-Origin: *
Strict-Transport-Security: max-age=31556952
ETag: "67b48935-3b"
expires: Thu, 20 Feb 2025 02:49:06 GMT
Cache-Control: max-age=600
x-proxy-cache: MISS
X-GitHub-Request-Id: 6CF9:1BCC6E:B442C:C99F5:67B695C7
Accept-Ranges: bytes
Age: 376
Date: Fri, 21 Feb 2025 02:30:08 GMT
Via: 1.1 varnish
X-Served-By: cache-bkk2310020-BKK
X-Cache: HIT
X-Cache-Hits: 0
X-Timer: S1740105009.502612,VS0,VE3
Vary: Accept-Encoding
X-Fastly-Request-ID: 570efab5dcb6cab76a0906efa91a6ee1207f3995

<!DOCTYPE html>
<html>
<body>
followers=YY
</body>
</html>


```

We can see that YYYY is the only part of the data whose proof is included in the <proof_file_des> (as its corresponding sha3 commitment), other parts that are XX... are just redacted like in original TLSNotary. In this example, there is no redaction in the received message.

### Customization

> This is a bit different from original TLSNotary, because in addition to being able to specify "redacted" parts of data where they are just not shown in the proof, users can also specify the "private" parts in the proof, which are not only not shown in the proof, but also having their sha3 commitment in the proof such that they can be seamlessly integrated with MP-SPDZ to make sure that the inputs of MP-SPDZ actually come from the private parts of these data from TLSNotary. This guide will mostly focus on customizing this additional "private" feature.

Here is how you can customize your own TLSNotary proof with "private" data by modifying these following files:

> This "simple" folder only shows when we want to make parts of the message "private" aka accompanying with its sha3 commitment in the proof. If you want to have more granular control between "redacted" and "private" e.g. having some parts of received message as "redacted" while another as "private", see more in [binance example](../binance/)

#### simple_prover.rs

Here is the main file for creating proof, where you can make this following customizations for "private" part of data.

**In main()**:

- Specify "secret_file" format, the json format of the secret and its corresponding nonce to be written into the file containing all private information used to prove later that its sha3 hash is the sha3 commitment contained in the proof.

**In build_proof_with_redactions()**:

- Specify "redacted" parts in sent message.
  In this simple example, we basically just redacted user_agent like how it's done in original TLSNotary example, but yes feel free to redact more things that you found make sense in your use case. (Note that if you want more granular redact using regex, can see more in [binance example](../binance/))

- Specify "private" parts of the received message.  
  We specify the private part (recv_private_ranges)that will be accompanied with sha3 commitment in the proof while being censored from the proof itself by specifying our preferred regex. In this example, we specify the number of followers to be private.

#### simple_verifier.rs

Here, we specify what alphabet we want to replace the parts that are made private. (Ofc, you can change what alphabet to represent "redacted" parts as well)

```
    sent.set_redacted(b'X');
    recv.set_private(b'Y');
```
