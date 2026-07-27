import unittest
from unittest.mock import patch, MagicMock
import json
import urllib.error
from .client import SolanaRPCClient
from .rpc_mock import RPCMockTransport
from .execptions import RPCError
from .entities import RPCConfig


class TestSolanaRPCClient(unittest.TestCase):
    def setUp(self):
        # max_retries=1 para testes rápidos (1 chamada inicial + 1 retry = 2 total)
        self.config = RPCConfig(cluster="devnet", max_retries=1, timeout=1.0)

    def _mock_urlopen_response(self, data: dict):
        """Helper para criar um mock compatível com context manager"""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(data).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    #  1. Resolução de endpoints
    def test_endpoint_resolution(self):
        c1 = SolanaRPCClient(RPCConfig(cluster="mainnet"))
        self.assertEqual(c1.endpoint, "https://api.mainnet-beta.solana.com")

        c2 = SolanaRPCClient(RPCConfig(custom_endpoint="https://meu-rpc.com"))
        self.assertEqual(c2.endpoint, "https://meu-rpc.com")

        c3 = SolanaRPCClient("https://api.devnet.solana.com")
        self.assertEqual(c3.endpoint, "https://api.devnet.solana.com")

    #  2. Sucesso básico
    def test_get_health_success(self):
        transport = RPCMockTransport()
        transport.queue_result("getHealth", "ok")
        client = SolanaRPCClient(self.config, transport=transport)
        self.assertEqual(client.get_health(), "ok")

    @patch("urllib.request.urlopen")
    def test_get_latest_blockhash(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_urlopen_response(
            {"result": {"value": {"blockhash": "8xYz...abc"}}}
        )
        client = SolanaRPCClient(self.config)
        self.assertEqual(client.get_latest_blockhash(), "8xYz...abc")

    #  3. Retry em falhas de rede
    @patch("urllib.request.urlopen")
    def test_retry_on_network_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("connection refused")
        client = SolanaRPCClient(self.config)
        with self.assertRaises(RPCError):
            client.get_health()
        # 1 tentativa inicial + 1 retry = 2 chamadas
        self.assertEqual(mock_urlopen.call_count, 2)

    #  4. Tratamento de erro RPC
    @patch("urllib.request.urlopen")
    def test_rpc_error_response(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_urlopen_response(
            {"error": {"code": -32600, "message": "Invalid Request"}}
        )
        client = SolanaRPCClient(self.config)
        with self.assertRaises(RPCError) as ctx:
            client.get_health()
        self.assertIn("Requisição RPC inválida", str(ctx.exception))

    #  5. Validação do payload de sendTransaction
    def test_send_transaction_payload(self):
        transport = RPCMockTransport()
        transport.queue_result("sendTransaction", "5sig...")
        client = SolanaRPCClient(self.config, transport=transport)
        sig = client.send_transaction("base64payload==")
        self.assertEqual(sig, "5sig...")

        # Verifica se o JSON-RPC foi montado corretamente
        payload = {
            "method": transport.requests[0]["method"],
            "params": transport.requests[0]["params"],
        }
        self.assertEqual(payload["method"], "sendTransaction")
        self.assertEqual(payload["params"][0], "base64payload==")
        self.assertEqual(payload["params"][1]["encoding"], "base64")
        self.assertEqual(payload["params"][1]["maxRetries"], 5)

    def test_get_transaction_history_payload_and_result(self):
        history = [
            {
                "signature": "sig-1",
                "slot": 123,
                "confirmationStatus": "confirmed",
            },
            {
                "signature": "sig-2",
                "slot": 122,
                "confirmationStatus": "finalized",
            },
        ]
        transport = RPCMockTransport()
        transport.queue_result("getSignaturesForAddress", history)
        client = SolanaRPCClient(self.config, transport=transport)

        result = client.get_transaction_history(
            "  wallet-address  ",
            limit=2,
            before="before-sig",
            until="until-sig",
            commitment="finalized",
        )

        self.assertEqual(result, history)
        payload = {
            "method": transport.requests[0]["method"],
            "params": transport.requests[0]["params"],
        }
        self.assertEqual(payload["method"], "getSignaturesForAddress")
        self.assertEqual(payload["params"][0], "wallet-address")
        self.assertEqual(payload["params"][1]["limit"], 2)
        self.assertEqual(payload["params"][1]["before"], "before-sig")
        self.assertEqual(payload["params"][1]["until"], "until-sig")
        self.assertEqual(payload["params"][1]["commitment"], "finalized")


class TestRPCRetryAndTimeout(unittest.TestCase):
    def setUp(self):
        self.config = RPCConfig(
            cluster="devnet", max_retries=2, base_delay=0.01, max_delay=0.1, timeout=1.0
        )

    def _mock_resp(self, data: dict) -> MagicMock:
        mock: MagicMock = MagicMock()
        mock.read.return_value = json.dumps(data).encode()
        mock.__enter__ = MagicMock(return_value=mock)
        mock.__exit__ = MagicMock(return_value=False)
        return mock

    @patch("urllib.request.urlopen")
    @patch("time.sleep")
    def test_retry_on_http_429(self, mock_sleep, mock_urlopen):
        # Falha 2x, sucesso na 3ª
        mock_urlopen.side_effect = [
            urllib.error.HTTPError("url", 429, "Too Many", {}, MagicMock()),
            urllib.error.HTTPError("url", 429, "Too Many", {}, MagicMock()),
            self._mock_resp({"result": "ok"}),
        ]
        client = SolanaRPCClient(self.config)
        self.assertEqual(client.get_health(), "ok")
        self.assertEqual(mock_urlopen.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)

    @patch("urllib.request.urlopen")
    @patch("time.sleep")
    def test_no_retry_on_fatal_rpc_error(self, mock_sleep, mock_urlopen):
        mock_urlopen.return_value = self._mock_resp(
            {"error": {"code": -32600, "message": "Invalid Request"}}
        )
        client = SolanaRPCClient(self.config)
        with self.assertRaises(RPCError) as ctx:
            client.get_health()
        self.assertIn("Requisição RPC inválida", str(ctx.exception))
        mock_sleep.assert_not_called()

    @patch("urllib.request.urlopen")
    @patch("time.sleep")
    def test_retry_exhausted_on_network_error(self, mock_sleep, mock_urlopen):
        mock_urlopen.side_effect = ConnectionError("refused")
        client = SolanaRPCClient(self.config)
        with self.assertRaises(RPCError):
            client.get_health()
        self.assertEqual(mock_urlopen.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)

    def test_timeout_applied_to_config(self):
        client = SolanaRPCClient(RPCConfig(timeout=5.0))
        self.assertEqual(client.cfg.timeout, 5.0)

    @patch("urllib.request.urlopen")
    def test_invalid_account_error_is_friendly(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_resp(
            {"error": {"code": -32602, "message": "Invalid params"}}
        )
        client = SolanaRPCClient(self.config)
        with self.assertRaises(RPCError) as ctx:
            client.get_balance("   bad-account   ")

        error_text = str(ctx.exception)
        self.assertIn("Parâmetros inválidos", error_text)
        self.assertIn("address=bad-account", error_text)

    @patch("urllib.request.urlopen")
    def test_insufficient_funds_error_is_friendly(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_resp(
            {"error": {"code": -32000, "message": "insufficient funds for rent"}}
        )
        client = SolanaRPCClient(self.config)

        with self.assertRaises(RPCError) as ctx:
            client.send_transaction("base64payload==")

        error_text = str(ctx.exception)
        self.assertIn("Saldo insuficiente", error_text)
        self.assertIn("método=sendTransaction", error_text)


if __name__ == "__main__":
    unittest.main()
