import asyncio
import os

import pytest

from solinpy.client.websocket import SolanaWebSocketClient


pytestmark = pytest.mark.asyncio


@pytest.mark.skipif(os.environ.get("CI") == "true", reason="Integration test; skip on CI by default")
async def test_subscribe_account_devnet():
    """Integration smoke test: connect to Devnet and subscribe to an account.

    This test is light: it connects, subscribes, waits a short time, then closes.
    It is skipped on CI by default.
    """
    events = []

    async def cb(data):
        events.append(data)

    async with SolanaWebSocketClient(cluster="devnet") as client:
        await client.subscribe_account("2o1frvCuy5r2b6c1rQ5P8WnM1k1a3r1x6a9k1r3YV1ZP", cb)
        # wait briefly to allow for subscription handshake
        await asyncio.sleep(2)

    # we don't assert events; success is no exception
