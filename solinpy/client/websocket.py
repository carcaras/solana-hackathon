import asyncio
import json
import logging
import random
from typing import Any, Awaitable, Callable, Dict, Optional

import websockets

logger = logging.getLogger(__name__)

Callback = Callable[[Dict[str, Any]], Awaitable[None]]


class SolanaWebSocketClient:
    """Async WebSocket client for Solana JSON-RPC notifications.

    Features:
    - async context manager
    - subscribe_account(pubkey_str, callback)
    - subscribe_logs(mentioning_pubkey_str, callback)
    - automatic reconnect with exponential backoff
    """

    DEFAULT_WS = "wss://api.devnet.solana.com/"

    def __init__(self, endpoint: Optional[str] = None, cluster: Optional[str] = None):
        if endpoint:
            self._endpoint = endpoint
        elif cluster:
            if cluster.lower() == "devnet":
                self._endpoint = "wss://api.devnet.solana.com/"
            elif cluster.lower() == "mainnet":
                self._endpoint = "wss://api.mainnet-beta.solana.com/"
            else:
                self._endpoint = self.DEFAULT_WS
        else:
            self._endpoint = self.DEFAULT_WS

        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._recv_task: Optional[asyncio.Task] = None
        self._id_counter = 1
        self._subscriptions: Dict[int, Callback] = {}
        self._subs_meta: Dict[int, Dict[str, Any]] = {}
        self._closed = False
        self._connect_lock = asyncio.Lock()

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def connect(self) -> None:
        async with self._connect_lock:
            if self._ws and self._is_ws_open(self._ws):
                return

            backoff = 0.5
            while not self._closed:
                try:
                    logger.debug("Connecting to %s", self._endpoint)
                    self._ws = await websockets.connect(self._endpoint)
                    self._recv_task = asyncio.create_task(self._recv_loop())
                    logger.info("WebSocket connected to %s", self._endpoint)
                    # re-subscribe existing subscriptions after reconnect
                    await self._resubscribe_all()
                    return
                except Exception as e:
                    logger.warning("WS connect failed: %s", e)
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 30) + random.random() * 0.1

    async def _resubscribe_all(self) -> None:
        # collect existing callbacks and metadata then re-subscribe
        existing = list(self._subs_meta.values())
        self._subscriptions.clear()
        self._subs_meta.clear()
        for meta in existing:
            if meta["type"] == "account":
                await self.subscribe_account(meta["pubkey"], meta["callback"]) 
            elif meta["type"] == "logs":
                await self.subscribe_logs(meta["pubkey"], meta["callback"]) 

    async def _recv_loop(self) -> None:
        assert self._ws is not None
        try:
            async for raw in self._ws:
                try:
                    msg = json.loads(raw)
                except Exception:
                    logger.debug("Non-json message: %s", raw)
                    continue

                # Handle notifications
                if msg.get("method") and msg.get("params"):
                    params = msg["params"]
                    sub_id = params.get("subscription")
                    if sub_id and sub_id in self._subscriptions:
                        cb = self._subscriptions[sub_id]
                        # schedule callback
                        asyncio.create_task(cb(params.get("result")))
                # Handle subscription responses
                elif "id" in msg and ("result" in msg or "error" in msg):
                    # map id to subscription id when result contains a sub id
                    req_id = msg["id"]
                    # result may be a subscription id
                    res = msg.get("result")
                    if isinstance(res, int):
                        # request id -> subscription id mapping stored in meta
                        meta = self._subs_meta.get(req_id)
                        if meta:
                            sub_cb = meta["callback"]
                            self._subscriptions[res] = sub_cb
                            # replace meta keyed by subscription id
                            self._subs_meta[res] = meta
                            if req_id in self._subs_meta:
                                # clear the temporary req_id entry
                                del self._subs_meta[req_id]
        except Exception as e:
            logger.warning("Receive loop error: %s", e)
        finally:
            # attempt reconnect unless closed
            if not self._closed:
                logger.info("WebSocket disconnected, reconnecting...")
                await self.connect()

    async def _send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self._ws or not self._is_ws_open(self._ws):
            await self.connect()
        assert self._ws is not None
        payload.setdefault("jsonrpc", "2.0")
        payload.setdefault("id", self._next_id())
        text = json.dumps(payload)
        await self._ws.send(text)
        return payload

    @staticmethod
    def _is_ws_open(ws: Any) -> bool:
        state = getattr(ws, "state", None)
        if state is not None:
            return str(state).lower() in {"open", "1"}
        return not getattr(ws, "closed", False)

    def _next_id(self) -> int:
        v = self._id_counter
        self._id_counter += 1
        return v

    async def subscribe_account(self, pubkey_str: str, callback: Callback, encoding: str = "jsonParsed") -> int:
        """Subscribe to account changes for `pubkey_str`.

        Returns the request id (not the subscription id) which will be used internally.
        The internal subscription id will be mapped to the callback when the server responds.
        """
        req_id = self._next_id()
        params = [pubkey_str, {"encoding": encoding, "commitment": "final"}]
        payload = {"method": "accountSubscribe", "params": params, "id": req_id}
        # store meta keyed by req_id until server returns the subscription id
        self._subs_meta[req_id] = {"type": "account", "pubkey": pubkey_str, "callback": callback}
        await self._send(payload)
        return req_id

    async def subscribe_logs(self, mentioning_pubkey_str: str, callback: Callback, commitment: str = "final") -> int:
        """Subscribe to program logs mentioning a pubkey (or program id).
        Uses logsSubscribe with filter 'mentions'.
        """
        req_id = self._next_id()
        params = [{"mentions": [mentioning_pubkey_str]}, {"commitment": commitment}]
        payload = {"method": "logsSubscribe", "params": params, "id": req_id}
        self._subs_meta[req_id] = {"type": "logs", "pubkey": mentioning_pubkey_str, "callback": callback}
        await self._send(payload)
        return req_id

    async def close(self) -> None:
        self._closed = True
        if self._recv_task:
            self._recv_task.cancel()
            self._recv_task = None
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None
