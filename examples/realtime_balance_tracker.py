import asyncio
from solinpy.client.websocket import SolanaWebSocketClient


async def on_balance_change(account_info):
    print("⚡ Instant update detected! New data:", account_info)


async def main():
    target_pubkey = "HXyFmHK21YGwu2ZpTUUF2pz5aFuWuFsBCXtJLwBMFzhi"
    async with SolanaWebSocketClient(cluster="devnet") as ws_client:
        await ws_client.subscribe_account(pubkey_str=target_pubkey, callback=on_balance_change)
        # Keep listening indefinitely
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
