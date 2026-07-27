import random
import asyncio
from typing import Optional, Dict, Any, Union, List, cast
import httpx
from solders.pubkey import Pubkey

from solinpy.client.entities import RPCConfig
from solinpy.client.execptions import RPCError
from solinpy.client.client import _normalize_address, _json_safe, BlockhashResult


class SolanaAsyncRPCClient:
    """Cliente RPC Assíncrono para interação com a rede Solana usando httpx."""

    cfg: RPCConfig

    def __init__(
        self,
        config: Optional[Union[RPCConfig, str]] = None,
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.cfg: RPCConfig
        if isinstance(config, str):
            self.cfg = RPCConfig(custom_endpoint=config)
        else:
            self.cfg = config or RPCConfig()
        self.endpoint = self.cfg.custom_endpoint or self._resolve_cluster_url()
        self._request_id = 0
        self._client = client

    def _resolve_cluster_url(self) -> str:
        urls = {
            "devnet": "https://api.devnet.solana.com",
            "testnet": "https://api.testnet.solana.com",
            "mainnet": "https://api.mainnet-beta.solana.com",
        }
        return urls.get(self.cfg.cluster, urls["devnet"])

    def _calc_backoff(self, attempt: int) -> float:
        delay = min(self.cfg.base_delay * (2**attempt), self.cfg.max_delay)
        jitter = random.uniform(0, delay * 0.5)
        return delay + jitter

    def _is_retryable(
        self, exc: Optional[Exception], rpc_error: Optional[Dict[str, Any]] = None
    ) -> bool:
        if isinstance(exc, httpx.HTTPStatusError):
            return exc.response.status_code in self.cfg.retryable_http_codes
        if isinstance(exc, (httpx.RequestError, ConnectionError, OSError, TimeoutError)):
            return True
        if rpc_error and rpc_error.get("code") in self.cfg.retryable_rpc_codes:
            return True
        return False

    def _raise_rpc_error(
        self, method: str, rpc_error: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> None:
        raise RPCError.from_rpc_error(method, rpc_error, context=context)

    async def _call(
        self,
        method: str,
        params: Optional[List[Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": _json_safe(params or []),
        }

        client = self._client or httpx.AsyncClient()
        last_exc: Optional[Exception] = None

        try:
            for attempt in range(self.cfg.max_retries + 1):
                try:
                    resp = await client.post(
                        self.endpoint,
                        json=payload,
                        headers={"Content-Type": "application/json"},
                        timeout=self.cfg.timeout,
                    )
                    resp.raise_for_status()
                    body: Dict[str, Any] = cast(Dict[str, Any], resp.json())

                    if "error" in body:
                        err = body["error"]
                        if self._is_retryable(None, rpc_error=err):
                            if attempt < self.cfg.max_retries:
                                await asyncio.sleep(self._calc_backoff(attempt))
                                continue
                        self._raise_rpc_error(method, err, context=context)
                    return body

                except httpx.HTTPStatusError as e:
                    last_exc = e
                    if self._is_retryable(e) and attempt < self.cfg.max_retries:
                        await asyncio.sleep(self._calc_backoff(attempt))
                        continue
                    raise RPCError.from_transport_error(
                        method,
                        e,
                        context={**(context or {}), "endpoint": self.endpoint},
                        message=f"Falha HTTP ao executar {method}. Verifique o endpoint configurado.",
                    ) from e
                except (httpx.RequestError, ConnectionError, OSError, TimeoutError) as e:
                    last_exc = e
                    if self._is_retryable(e) and attempt < self.cfg.max_retries:
                        await asyncio.sleep(self._calc_backoff(attempt))
                        continue
                    break
                except Exception as e:
                    last_exc = e
                    raise RPCError.from_transport_error(
                        method,
                        e,
                        context={**(context or {}), "endpoint": self.endpoint},
                        message=f"Falha inesperada ao executar {method}.",
                    ) from e
            raise RPCError(
                f"Falha de comunicação ao executar {method} após {self.cfg.max_retries + 1} tentativas.",
                method=method,
                context={**(context or {}), "endpoint": self.endpoint},
                cause=last_exc,
            ) from last_exc
        finally:
            if self._client is None:
                await client.aclose()

    async def get_health(self) -> str:
        resp = await self._call("getHealth")
        return str(resp["result"])

    async def get_latest_blockhash(self, commitment: str = "confirmed") -> BlockhashResult:
        resp = await self._call(
            "getLatestBlockhash", [{"commitment": commitment}], {"commitment": commitment}
        )
        return BlockhashResult(resp["result"]["value"]["blockhash"])

    async def get_account_info(
        self, address: Union[str, Pubkey], commitment: str = "confirmed"
    ) -> Any:
        """Busca as informações básicas da conta (útil para verificar se existe)."""
        sanitized_address = _normalize_address(address)
        resp = await self._call(
            "getAccountInfo",
            [sanitized_address, {"encoding": "base64", "commitment": commitment}],
            {"address": sanitized_address, "commitment": commitment},
        )
        val = resp["result"]["value"]

        class AccountInfoResult:
            def __init__(self, value: Any):
                self.value = value

        return AccountInfoResult(val)

    async def send_transaction(self, tx_base64: str, max_retries: int = 5) -> str:
        resp = await self._call(
            "sendTransaction",
            [tx_base64, {"encoding": "base64", "maxRetries": max_retries}],
            {"tx_size": len(tx_base64), "max_retries": max_retries},
        )
        return str(resp["result"])

    async def get_balance(self, address: Union[str, Pubkey]) -> int:
        """Retorna o saldo da conta em Lamports."""
        sanitized_address = _normalize_address(address)
        resp = await self._call("getBalance", [sanitized_address], {"address": sanitized_address})
        return int(resp["result"]["value"])

    async def get_token_accounts_by_owner(
        self, address: Union[str, Pubkey]
    ) -> List[Dict[str, Any]]:
        """Retorna as contas de tokens SPL associadas ao endereço."""
        TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
        sanitized_address = _normalize_address(address)
        params = [
            sanitized_address,
            {"programId": TOKEN_PROGRAM_ID},
            {"encoding": "jsonParsed", "commitment": "confirmed"},
        ]
        resp = await self._call("getTokenAccountsByOwner", params, {"address": sanitized_address})
        return cast(List[Dict[str, Any]], resp["result"]["value"])

    async def get_sol_balance(self, address: Union[str, Pubkey]) -> float:
        """Retorna o saldo convertido para SOL."""
        lamports = await self.get_balance(address)
        return lamports / 1_000_000_000

    async def get_token_balances(self, address: Union[str, Pubkey]) -> List[Dict[str, Any]]:
        """Retorna saldos simplificados de tokens SPL."""
        raw_accounts = await self.get_token_accounts_by_owner(address)
        balances = []
        for account in raw_accounts:
            info = account["account"]["data"]["parsed"]["info"]
            token_amount = info["tokenAmount"]
            balances.append(
                {
                    "mint": info["mint"],
                    "amount": token_amount["uiAmount"],
                    "decimals": token_amount["decimals"],
                }
            )
        return balances

    async def get_transaction_history(
        self,
        address: Union[str, Pubkey],
        limit: int = 20,
        before: Optional[str] = None,
        until: Optional[str] = None,
        commitment: str = "confirmed",
    ) -> List[Dict[str, Any]]:
        """Busca o histórico de assinaturas de transações do endereço."""
        sanitized_address = _normalize_address(address)
        config: Dict[str, Any] = {
            "limit": limit,
            "commitment": commitment,
        }
        if before is not None:
            config["before"] = before
        if until is not None:
            config["until"] = until

        resp = await self._call(
            "getSignaturesForAddress",
            [sanitized_address, config],
            {
                "address": sanitized_address,
                "limit": limit,
                "before": before,
                "until": until,
                "commitment": commitment,
            },
        )
        return cast(List[Dict[str, Any]], resp["result"])
