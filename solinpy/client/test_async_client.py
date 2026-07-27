import unittest
from unittest.mock import AsyncMock, MagicMock
import httpx

from solinpy.client.entities import RPCConfig
from solinpy.client.async_client import SolanaAsyncRPCClient


class TestSolanaAsyncRPCClient(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.config = RPCConfig(cluster="devnet", retries=1, timeout=1.0)
        self.mock_client = AsyncMock(spec=httpx.AsyncClient)
        self.client = SolanaAsyncRPCClient(self.config, client=self.mock_client)

    def _mock_response(self, data: dict, status_code: int = 200):
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = status_code
        mock_resp.json.return_value = data
        return mock_resp

    async def test_endpoint_resolution(self):
        c1 = SolanaAsyncRPCClient(RPCConfig(cluster="mainnet"))
        self.assertEqual(c1.endpoint, "https://api.mainnet-beta.solana.com")

        c2 = SolanaAsyncRPCClient(RPCConfig(custom_endpoint="https://meu-rpc-async.com"))
        self.assertEqual(c2.endpoint, "https://meu-rpc-async.com")

        c3 = SolanaAsyncRPCClient("https://api.devnet.solana.com")
        self.assertEqual(c3.endpoint, "https://api.devnet.solana.com")

    async def test_get_health_success(self):
        self.mock_client.post.return_value = self._mock_response({"result": "ok"})
        health = await self.client.get_health()
        self.assertEqual(health, "ok")

    async def test_get_latest_blockhash(self):
        self.mock_client.post.return_value = self._mock_response(
            {"result": {"value": {"blockhash": "abc123async"}}}
        )
        bh = await self.client.get_latest_blockhash()
        self.assertEqual(bh, "abc123async")
        self.assertEqual(bh.value.blockhash, "abc123async")

    async def test_get_balance(self):
        addr = "4ND3y8d4Q6r3QJ6VwY2w2TnY4A2D6dYj3q3p8eQmB9QZ"
        self.mock_client.post.return_value = self._mock_response({"result": {"value": 1500000000}})
        bal = await self.client.get_balance(addr)
        self.assertEqual(bal, 1500000000)

        sol_bal = await self.client.get_sol_balance(addr)
        self.assertEqual(sol_bal, 1.5)

    async def test_get_account_info(self):
        addr = "4ND3y8d4Q6r3QJ6VwY2w2TnY4A2D6dYj3q3p8eQmB9QZ"
        self.mock_client.post.return_value = self._mock_response(
            {"result": {"value": {"data": ["base64data", "base64"], "lamports": 10000}}}
        )
        info = await self.client.get_account_info(addr)
        self.assertIsNotNone(info.value)
        self.assertEqual(info.value["lamports"], 10000)
