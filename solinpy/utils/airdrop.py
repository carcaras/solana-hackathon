import time
from typing import Any, Dict, Optional

from solders.keypair import Keypair

from solinpy.client.client import SolanaRPCClient
from solinpy.client.entities import RPCConfig


def request_airdrop(
    keypair: Keypair,
    cluster: str = "devnet",
    lamports: int = 1_000_000_000,
    timeout: float = 60.0,
    poll_interval: float = 2.0,
    custom_endpoint: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Backward-compatible alias para create_airdrop.

    Mantida para não quebrar código existente.
    """
    return create_airdrop(
        keypair=keypair,
        cluster=cluster,
        lamports=lamports,
        timeout=timeout,
        poll_interval=poll_interval,
        custom_endpoint=custom_endpoint,
    )


def create_airdrop(
    keypair: Keypair,
    cluster: str = "devnet",
    lamports: int = 1_000_000_000,
    timeout: float = 60.0,
    poll_interval: float = 2.0,
    custom_endpoint: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Solicita um airdrop de SOL para uma carteira em ambientes de teste (devnet ou testnet).

    Esta função envia a solicitação de airdrop e aguarda automaticamente
    até que a transação seja confirmada na rede.

    Args:
        keypair: O par de chaves da carteira que receberá o airdrop.
        cluster: A rede onde solicitar o airdrop. Apenas 'devnet' ou 'testnet' são permitidos.
        lamports: Quantidade de lamports a solicitar (1 SOL = 1_000_000_000 lamports).
        timeout: Tempo máximo em segundos para aguardar a confirmação.
        poll_interval: Intervalo em segundos entre cada verificação de confirmação.
        custom_endpoint: URL customizada do RPC (opcional).

    Returns:
        dict: Dicionário com as seguintes chaves:
            - 'signature' (str): A assinatura da transação de airdrop.
            - 'confirmed' (bool): Se o airdrop foi confirmado com sucesso.
            - 'balance' (int): O saldo atual da conta após o airdrop (em lamports).

    Raises:
        ValueError: Se o cluster não for 'devnet' ou 'testnet'.
        RPCError: Se a solicitação ou confirmação do airdrop falhar.
        TimeoutError: Se o tempo de espera pela confirmação exceder o timeout especificado.

    Example:
        >>> from solders.keypair import Keypair
        >>> from solinpy.utils import request_airdrop
        >>> keypair = Keypair()
        >>> result = request_airdrop(keypair, cluster="devnet")
        >>> print(result['signature'])
        >>> print(result['confirmed'])
    """
    if cluster not in ("devnet", "testnet"):
        raise ValueError(
            f"Airdrop disponível apenas para 'devnet' ou 'testnet'. Recebido: '{cluster}'"
        )

    config = RPCConfig(cluster=cluster, custom_endpoint=custom_endpoint)
    client = SolanaRPCClient(config)

    pub_key = keypair.pubkey()

    signature = client._call("requestAirdrop", [str(pub_key), lamports])["result"]

    start_time = time.time()
    while time.time() - start_time < timeout:
        resp = client._call("getSignatureStatuses", [[signature]])
        statuses = resp.get("result", {}).get("value", [])

        if statuses and statuses[0] is not None:
            status = statuses[0]
            if status.get("confirmationStatus") in ("confirmed", "finalized"):
                balance_resp = client._call("getBalance", [str(pub_key)])
                balance = balance_resp["result"]["value"]
                return {
                    "signature": signature,
                    "confirmed": True,
                    "balance": balance,
                }

        time.sleep(poll_interval)

    raise TimeoutError(
        f"Airdrop não foi confirmado dentro do timeout de {timeout}s. Assinatura: {signature}"
    )
