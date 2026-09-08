# SolInPy

SolInPy is a Python SDK for Solana designed to simplify interactions with the network without building everything from scratch.

It focuses on three main areas:

- Accessing the Solana JSON-RPC with retries, timeouts, and error handling
- Creating and importing wallets
- Helpers for airdrops and SPL token transfers

The goal is to provide a simple entry point for prototypes, automations, and small integrations on devnet, testnet, or mainnet.

## What the SDK covers

- RPC client: `SolanaRPCClient`
- Network configuration: `RPCConfig`
- Wallets: `WalletManager`
- Testnet airdrops: `create_airdrop` and `request_airdrop`
- SPL token transfers: `send_token_transfer`
- Account decoding utilities in `solinpy.utils.account_decoder`

## Requirements

- Python 3.10+
- Internet access for real RPC calls

## Installation

Install from PyPI:

```bash
pip install solinpy
```


After that, run your scripts from the project root so the `solinpy` package can be imported correctly.

## Quickstart

### 1. Make a basic RPC call

```python
from solinpy.client.client import SolanaRPCClient
from solinpy.client.entities import RPCConfig

client = SolanaRPCClient(RPCConfig(cluster="devnet"))

print(client.get_health())
print(client.get_latest_blockhash())
```

### 2. Create or import a wallet

```python
from solinpy.wallet.manager import WalletManager

keypair = WalletManager.generate_keypair()
print(keypair.pubkey())

loaded_keypair = WalletManager.import_from_json("my-wallet.json")
print(loaded_keypair.pubkey())
```

### 3. Request an airdrop on devnet

```python
from solinpy.utils.airdrop import request_airdrop

result = request_airdrop(keypair, cluster="devnet")
print(result["signature"])
print(result["balance"])
```

### 4. Read balance and history

```python
wallet_address = str(keypair.pubkey())

print(client.get_balance(wallet_address))
print(client.get_sol_balance(wallet_address))
print(client.get_transaction_history(wallet_address, limit=5))
```

### 5. Transfer an SPL token

```python
from solinpy.transaction.token import send_token_transfer

signature = send_token_transfer(
	client=client,
	sender_keypair=keypair,
	destination_wallet="<destination-wallet-address>",
	token_mint="<token-mint>",
	amount=25,
	decimals=6,
)

print(signature)
```

This helper will automatically create the recipient's associated token account if it does not already exist.

## Complete example

```python
from solinpy.client.client import SolanaRPCClient
from solinpy.client.entities import RPCConfig
from solinpy.utils.airdrop import request_airdrop
from solinpy.wallet.manager import WalletManager

config = RPCConfig(cluster="devnet")
client = SolanaRPCClient(config)

wallet = WalletManager.generate_keypair()
airdrop = request_airdrop(wallet, cluster="devnet")

address = str(wallet.pubkey())
balance_lamports = client.get_balance(address)

print("Airdrop:", airdrop["signature"])
print("Balance in lamports:", balance_lamports)
print("Balance in SOL:", client.get_sol_balance(address))
```

## Project structure

```text
solinpy/
├── client/
├── wallet/
├── transaction/
└── utils/
```

## Usage notes

- `devnet` and `testnet` are the safest networks to get started.
- `request_airdrop` and `create_airdrop` only make sense on those networks.
- `send_token_transfer` assumes you already have the token mint and the recipient's wallet address.

## Contributing

The project tests use `pytest`, and the codebase is also checked with `ruff` and `mypy`.

```bash
pip install -e ".[dev]"
pytest
python -m ruff check .
python -m mypy solinpy
```
