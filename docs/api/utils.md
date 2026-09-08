# Utils API Reference

The Utils module provides helper functions for common Solana operations including airdrops, account data decoding, and binary parsing.

## Overview

These utilities simplify common tasks when working with Solana:

- Requesting SOL airdrops on devnet/testnet
- Decoding raw account data for known programs (SPL Token, System Program)
- Parsing binary data from account blobs

## Quick Start

```python
from solders.keypair import Keypair
from solinpy.utils import create_airdrop, decode_account_data

# Request airdrop
keypair = Keypair()
result = create_airdrop(keypair, cluster="devnet")
print(f"Airdrop signature: {result['signature']}")
print(f"Balance: {result['balance']} lamports")

# Decode account data
data = get_account_info(pubkey)  # from RPC
decoded = decode_account_data(data)
print(decoded)
```

---

## Airdrop Functions

### `create_airdrop(keypair, cluster="devnet", lamports=1_000_000_000, timeout=60.0, poll_interval=2.0, custom_endpoint=None)`

Request a SOL airdrop for a wallet on devnet or testnet. Sends the request and polls until the transaction is confirmed.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `keypair` | `Keypair` | — | Wallet to receive the airdrop |
| `cluster` | `str` | `"devnet"` | Target cluster: `"devnet"` or `"testnet"` |
| `lamports` | `int` | `1_000_000_000` | Amount to request (1 SOL = 1e9 lamports) |
| `timeout` | `float` | `60.0` | Max seconds to wait for confirmation |
| `poll_interval` | `float` | `2.0` | Seconds between confirmation checks |
| `custom_endpoint` | `Optional[str]` | `None` | Custom RPC endpoint URL |

**Returns**: `dict` with keys:
- `"signature"` (`str`): Airdrop transaction signature
- `"confirmed"` (`bool`): Whether airdrop was confirmed
- `"balance"` (`int`): Account balance in lamports after airdrop

**Raises**:
- `ValueError` if `cluster` is not `"devnet"` or `"testnet"`
- `RPCError` if the request or confirmation fails
- `TimeoutError` if confirmation exceeds `timeout`

**Example**:

```python
from solders.keypair import Keypair
from solinpy.utils import create_airdrop

keypair = Keypair()
result = create_airdrop(keypair, cluster="devnet", lamports=2_000_000_000)
print(result)
# {'signature': '...', 'confirmed': True, 'balance': 2000000000}
```

---

### `request_airdrop(keypair, cluster="devnet", lamports=1_000_000_000, timeout=60.0, poll_interval=2.0, custom_endpoint=None)`

Backward-compatible alias for `create_airdrop`. Preserves existing code that uses the older name.

**Returns/Raises**: See `create_airdrop` above.

---

## Account Decoder Functions

### `decode_account_data(data, program_type="auto")`

Decode raw account bytes into a structured dictionary. Supports SPL Token accounts, SPL Token mints, and System Program accounts.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `data` | `bytes \| str \| dict` | — | Raw account data (bytes, base64 string, or pre-parsed dict) |
| `program_type` | `str` | `"auto"` | Decoder to use: `"auto"`, `"spl_token"`, `"spl_token_mint"`, `"system"`, `"raw"` |

**Returns**: `dict` with decoded fields. Structure depends on program type:

**SPL Token Account** (165 bytes):
```python
{
    "program": "SPL Token",
    "mint": "Pubkey...",
    "owner": "Pubkey...",
    "amount": 1000000,
    "delegate": None,  # or "Pubkey..."
    "state": "initialized",
    "is_native": False,
    "native_amount": 0,
    "delegated_amount": 0,
    "close_authority": None  # or "Pubkey..."
}
```

**SPL Token Mint** (82 bytes):
```python
{
    "program": "SPL Token Mint",
    "mint_authority": "Pubkey...",  # or None
    "supply": 1000000000,
    "decimals": 6,
    "is_initialized": True,
    "freeze_authority": "Pubkey..."  # or None
}
```

**Auto-detection logic**: 82 bytes → SPL Token Mint; ≥72 bytes → SPL Token Account; otherwise → raw.

---

### `decode_spl_token_account(data)`

Deserialize raw SPL Token account data. Expects at least 72 bytes.

**Returns**: `dict` with token account fields. See `decode_account_data` for structure.

**Raises**: `ValueError` if data is shorter than 72 bytes.

---

### `decode_spl_token_mint(data)`

Deserialize raw SPL Token mint data. Expects at least 82 bytes.

**Returns**: `dict` with mint account fields. See `decode_account_data` for structure.

**Raises**: `ValueError` if data is shorter than 82 bytes.

---

### `decode_system_account(data)`

Returns metadata for a System Program account. Currently returns `data_length` and `raw_data` since System accounts typically hold no structured data.

**Returns**: `dict` with `program`, `data_length`, and `raw_data`.

---

### Binary Parsing Helpers

Low-level functions for extracting values from raw bytes:

| Function | Returns | Description |
|----------|---------|-------------|
| `decode_base64_to_bytes(data)` | `bytes` | Decode base64 string to bytes |
| `decode_bytes_to_base64(data)` | `str` | Encode bytes to base64 string |
| `parse_pubkey_from_bytes(data, offset=0)` | `Pubkey` | Extract 32-byte Solana pubkey |
| `parse_u64_from_bytes(data, offset=0, little_endian=True)` | `int` | Extract 64-bit unsigned integer |
| `parse_u32_from_bytes(data, offset=0, little_endian=True)` | `int` | Extract 32-bit unsigned integer |
| `parse_u8_from_bytes(data, offset=0)` | `int` | Extract 8-bit unsigned integer |

All parsing helpers raise `ValueError` if the data is too short for the requested type at the given offset.

---

## Usage Examples

### Decode a Token Account from RPC

```python
from solinpy.client import SolanaRPCClient, RPCConfig
from solinpy.utils import decode_account_data

config = RPCConfig(cluster="devnet")
client = SolanaRPCClient(config)

info = client._call("getAccountInfo", ["TokenAccountPubkey..."])
raw_data = info["result"]["value"]["data"][0]  # base64

decoded = decode_account_data(raw_data)
print(f"Mint: {decoded['mint']}")
print(f"Balance: {decoded['amount']}")
```

### Manual Byte Parsing

```python
from solinpy.utils import parse_pubkey_from_bytes, parse_u64_from_bytes

raw_bytes = b'...'  # 72+ bytes
mint = parse_pubkey_from_bytes(raw_bytes, offset=0)
owner = parse_pubkey_from_bytes(raw_bytes, offset=32)
amount = parse_u64_from_bytes(raw_bytes, offset=64)
```

---

## Error Handling

| Error | Cause |
|-------|-------|
| `ValueError: Dados insuficientes` | Data too short for requested parse |
| `ValueError: Falha ao decodificar base64` | Invalid base64 input |
| `ValueError: Dados SPL Token inválidos` | Data below minimum SPL Token size |
| `ValueError: Dados Mint SPL Token inválidos` | Data below 82 bytes for mint |
