from solders.system_program import create_account, CreateAccountParams
from solders.message import Message
from solders.transaction import Transaction
from solders.hash import Hash
from solinpy.transaction.token import (
    initialize_mint,
    InitializeMintParams,
    mint_to,
    MintToParams,
    set_authority,
    SetAuthorityParams,
    AuthorityType,
)

from solinpy.client.client import SolanaRPCClient
from solinpy.wallet.manager import WalletManager
from solinpy.utils.airdrop import request_airdrop
from solinpy.transaction.token import (
    TOKEN_PROGRAM_ID,
    get_associated_token_address,
    create_associated_token_account,
)


def run_mint_nft_flow() -> None:
    print("🚀 Iniciando Fluxo de Criação de NFT no Devnet...")

    # Conectar ao devnet
    client = SolanaRPCClient("https://api.devnet.solana.com")

    # 1. Gerar carteira pagadora
    print("🔑 Gerando carteira do pagador...")
    payer = WalletManager.generate_keypair()
    print(f"Carteira: {payer.pubkey()}")

    # Solicitar airdrop para cobrir taxas de transação e aluguel (rent)
    print("🪂 Solicitando Airdrop de 2 SOL...")
    airdrop = request_airdrop(payer, cluster="devnet", lamports=2_000_000_000)
    print(f"Airdrop confirmado! Assinatura: {airdrop['signature']}")

    # 2. Gerar par de chaves para a conta do NFT (Mint Account)
    nft_mint = WalletManager.generate_keypair()
    print(f"🪙 Endereço do NFT (Mint): {nft_mint.pubkey()}")

    # 3. Montar as instruções da transação
    # Tamanho de uma conta de Mint SPL standard é 82 bytes
    MINT_SIZE = 82
    rent_resp = client._call("getMinimumBalanceForRentExemption", [MINT_SIZE])
    rent_lamports = rent_resp["result"]

    # A. Criar a conta de dados para o Mint
    create_account_ix = create_account(
        CreateAccountParams(
            from_pubkey=payer.pubkey(),
            to_pubkey=nft_mint.pubkey(),
            lamports=rent_lamports,
            space=MINT_SIZE,
            program_id=TOKEN_PROGRAM_ID,
        )
    )

    # B. Inicializar a conta como Mint (0 decimais para NFTs)
    init_mint_ix = initialize_mint(
        InitializeMintParams(
            program_id=TOKEN_PROGRAM_ID,
            mint=nft_mint.pubkey(),
            decimals=0,
            mint_authority=payer.pubkey(),
            freeze_authority=payer.pubkey(),
        )
    )

    # C. Derivar e criar a Associated Token Account (ATA) do pagador
    payer_ata = get_associated_token_address(str(payer.pubkey()), str(nft_mint.pubkey()))
    create_ata_ix = create_associated_token_account(
        payer=payer.pubkey(), owner=payer.pubkey(), mint=nft_mint.pubkey()
    )

    # D. Cunhar (Mint) exatamente 1 token na conta ATA criada
    mint_to_ix = mint_to(
        MintToParams(
            program_id=TOKEN_PROGRAM_ID,
            mint=nft_mint.pubkey(),
            dest=payer_ata,
            mint_authority=payer.pubkey(),
            amount=1,
        )
    )

    # E. Revogar a autoridade de mint para travar o supply em 1 (tornando o token Não-Fungível)
    revoke_auth_ix = set_authority(
        SetAuthorityParams(
            program_id=TOKEN_PROGRAM_ID,
            account=nft_mint.pubkey(),
            authority_type=AuthorityType.MintTokens,
            current_authority=payer.pubkey(),
            new_authority=None,
        )
    )

    # 4. Agrupar instruções em uma transação atômica
    print("📦 Construindo transação atômica do NFT...")
    instructions = [create_account_ix, init_mint_ix, create_ata_ix, mint_to_ix, revoke_auth_ix]

    recent_blockhash_str = str(client.get_latest_blockhash())
    bh = Hash.from_string(recent_blockhash_str)

    msg = Message(instructions, payer.pubkey())
    # A transação precisa de ambas as assinaturas: payer (quem paga e autoriza) e nft_mint (nova conta criada)
    tx = Transaction([payer, nft_mint], msg, bh)

    print("📤 Transmitindo transação para a rede...")
    tx_sig = client.send_transaction(tx)
    print("🎉 Sucesso! NFT criado com sucesso.")
    print(f"Assinatura da Transação: {tx_sig}")
    print(f"Veja o NFT no Solscan: https://solscan.io/token/{nft_mint.pubkey()}?cluster=devnet")


if __name__ == "__main__":
    run_mint_nft_flow()
