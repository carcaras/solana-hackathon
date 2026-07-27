# RPC Client API Reference

The core client interface for establishing robust connections to Solana clusters (Mainnet, Devnet, Localnet).

::: solinpy.client.client

## WebSocket Client

The `SolanaWebSocketClient` provides an async, high-level wrapper for Solana JSON-RPC WebSocket subscriptions. It manages connection lifecycle, subscriptions, and automatic reconnects.

Basic usage:

```python
import asyncio
from solinpy.client.websocket import SolanaWebSocketClient

async def on_balance_change(account_info):
	print("Instant update:", account_info)

async def main():
	async with SolanaWebSocketClient(cluster="devnet") as ws:
		await ws.subscribe_account(pubkey_str="<PUBKEY>", callback=on_balance_change)
		await asyncio.Future()

asyncio.run(main())
```

API highlights:

- `SolanaWebSocketClient(endpoint=None, cluster="devnet")`: construct the client.
- `async with SolanaWebSocketClient(...) as client`: use as an async context manager.
- `await client.subscribe_account(pubkey_str, callback)`: subscribe to account changes.
- `await client.subscribe_logs(pubkey_str, callback)`: subscribe to logs mentioning a pubkey.

The client will automatically reconnect and re-subscribe on transient network errors.