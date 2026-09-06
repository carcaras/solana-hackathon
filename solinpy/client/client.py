import json
import random
import time
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, Callable, Union
from solders.pubkey import Pubkey
from solinpy.client.entities import RPCConfig
from solinpy.client.execptions import RPCError


def _normalize_address(address: Union[str, Pubkey]) -> str:
    """Converte Pubkey ou string para uma string limpa de endereço."""
    return str(address).strip()


def _json_safe(params: Any) -> Any:
    """Converte parâmetros para formatos seguros para JSON (ex: Pubkey para string)."""
    if isinstance(params, list):
        return [_json_safe(p) for p in params]
    if isinstance(params, dict):
        return {k: _json_safe(v) for k, v in params.items()}
    if isinstance(params, Pubkey):
        return str(params)
    if hasattr(params, "pubkey"):
        return str(params.pubkey())
    return params


class BlockhashResult(str):
    """Classe utilitária para manter compatibilidade com retorno de blockhash (str ou obj)."""

    @property
    def value(self) -> "BlockhashResult":
        return self

    @property
    def blockhash(self) -> str:
        return str(self)


class SolanaRPCClient:
    def __init__(
        self,
        config: Optional[Union[RPCConfig, str]] = None,
        transport: Optional[Callable[..., Any]] = None,
    ):
        if isinstance(config, str):
            self.cfg = RPCConfig(custom_endpoint=config)
        else:
            self.cfg = config or RPCConfig()
        self.endpoint = self.cfg.custom_endpoint or self._resolve_cluster_url()
        self._request_id = 0
        self._transport = transport or urllib.request.urlopen

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

    def _is_retryable(self, exc: Optional[Exception], rpc_error: Optional[dict] = None) -> bool:
        if isinstance(exc, urllib.error.HTTPError):
            return exc.code in self.cfg.retryable_http_codes
        if isinstance(exc, (urllib.error.URLError, ConnectionError, OSError, TimeoutError)):
            return True
        if rpc_error and rpc_error.get("code") in self.cfg.retryable_rpc_codes:
            return True
        return False

    def _raise_rpc_error(
        self, method: str, rpc_error: dict, context: Optional[Dict[str, Any]] = None
    ) -> None:
        raise RPCError.from_rpc_error(method, rpc_error, context=context)

    def _call(
        self,
        method: str,
        params: Optional[list] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": _json_safe(params or []),
        }
        data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            self.endpoint, data=data, headers={"Content-Type": "application/json"}, method="POST"
        )

        last_exc: Optional[Exception] = None
        for attempt in range(self.cfg.max_retries + 1):
            try:
                with self._transport(req, timeout=self.cfg.timeout) as resp:
                    body = json.loads(resp.read())
                    if "error" in body:
                        err = body["error"]
                        if self._is_retryable(None, rpc_error=err):
                            if attempt < self.cfg.max_retries:
                                time.sleep(self._calc_backoff(attempt))
                                continue
                        self._raise_rpc_error(method, err, context=context)
                    return body

            except RPCError:
                raise
            except urllib.error.HTTPError as e:
                last_exc = e
                if self._is_retryable(e) and attempt < self.cfg.max_retries:
                    time.sleep(self._calc_backoff(attempt))
                    continue
                raise RPCError.from_transport_error(
                    method,
                    e,
                    context={**(context or {}), "endpoint": self.endpoint},
                    message=f"Falha HTTP ao executar {method}. Verifique o endpoint configurado.",
                ) from e
            except (urllib.error.URLError, ConnectionError, OSError, TimeoutError) as e:
                last_exc = e
                if self._is_retryable(e) and attempt < self.cfg.max_retries:
                    time.sleep(self._calc_backoff(attempt))
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

    def get_health(self) -> str:
        return self._call("getHealth")["result"]

    def get_latest_blockhash(self, commitment: str = "confirmed") -> BlockhashResult:
        resp = self._call(
            "getLatestBlockhash", [{"commitment": commitment}], {"commitment": commitment}
        )
        return BlockhashResult(resp["result"]["value"]["blockhash"])

    def get_account_info(self, address: Union[str, Pubkey], commitment: str = "confirmed") -> Any:
        """Busca as informações básicas da conta (útil para verificar se existe)."""
        sanitized_address = _normalize_address(address)
        resp = self._call(
            "getAccountInfo",
            [sanitized_address, {"encoding": "base64", "commitment": commitment}],
            {"address": sanitized_address, "commitment": commitment},
        )
        val = resp["result"]["value"]

        class AccountInfoResult:
            def __init__(self, value: Any):
                self.value = value

        return AccountInfoResult(val)

    def send_transaction(self, tx_base64: str, max_retries: int = 5) -> str:
        resp = self._call(
            "sendTransaction",
            [tx_base64, {"encoding": "base64", "maxRetries": max_retries}],
            {"tx_size": len(tx_base64), "max_retries": max_retries},
        )
        return resp["result"]

    def get_balance(self, address: str) -> int:
        """
        Returns the account balance in Lamports.

        Args:
            address: The base58-encoded public key of the account.

        Returns:
            int: The balance in Lamports.
        """
        sanitized_address = _normalize_address(address)
        resp = self._call("getBalance", [sanitized_address], {"address": sanitized_address})
        return resp["result"]["value"]

    def get_token_accounts_by_owner(self, address: str | Pubkey) -> list[Dict[str, Any]]:
        """
        Returns the list of SPL token accounts associated with an address.
        """
        TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"

        sanitized_address = address.strip()

        params = [
            sanitized_address,
            {"programId": TOKEN_PROGRAM_ID},
            {"encoding": "jsonParsed", "commitment": "confirmed"},  # Adicionado o commitment
        ]

        resp = self._call("getTokenAccountsByOwner", params, {"address": sanitized_address})
        return resp["result"]["value"]

    def get_sol_balance(self, address: str) -> float:
        """
        Returns the account balance converted to SOL (user-friendly unit).

        Args:
            address: The base58-encoded public key of the account.

        Returns:
            float: The balance in SOL.
        """
        lamports = self.get_balance(address)
        # 1 SOL is equivalent to 1,000,000,000 Lamports
        return lamports / 1_000_000_000

    def get_token_balances(self, address: str) -> list[dict]:
        """
        Retrieves a simplified list of token balances for a given address.
        """
        raw_accounts = self.get_token_accounts_by_owner(address)
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

    def get_transaction_history(
        self,
        address: str,
        limit: int = 20,
        before: Optional[str] = None,
        until: Optional[str] = None,
        commitment: str = "confirmed",
    ) -> list[Dict[str, Any]]:
        """List recent transaction signatures for a wallet address."""
        sanitized_address = address.strip()
        config: Dict[str, Any] = {
            "limit": limit,
            "commitment": commitment,
        }

        if before is not None:
            config["before"] = before
        if until is not None:
            config["until"] = until

        resp = self._call(
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
        return resp["result"]
