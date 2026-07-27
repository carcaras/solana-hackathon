from typing import Any
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.message import Message
from solders.transaction import Transaction
from solders.hash import Hash
from spl.token.instructions import (
    transfer_checked,
    TransferCheckedParams,
    create_associated_token_account,
)

# Constants for SPL Token Program
TOKEN_PROGRAM_ID = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
ASSOCIATED_TOKEN_PROGRAM_ID = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")


def get_associated_token_address(owner_address: str, token_mint_address: str) -> Pubkey:
    """
    Derives the ATA (Associated Token Account) for the given wallet and mint.
    """
    owner_pubkey = Pubkey.from_string(owner_address)
    mint_pubkey = Pubkey.from_string(token_mint_address)

    ata, _ = Pubkey.find_program_address(
        [bytes(owner_pubkey), bytes(TOKEN_PROGRAM_ID), bytes(mint_pubkey)],
        ASSOCIATED_TOKEN_PROGRAM_ID,
    )
    return ata


def send_token_transfer(
    client: Any,
    sender_keypair: Keypair,
    destination_wallet: str,
    token_mint: str,
    amount: int,
    decimals: int,
) -> Any:
    """
    Executes a complete SPL token transfer using the modern Solders architecture.
    """
    sender_pubkey = sender_keypair.pubkey()
    receiver_pubkey = Pubkey.from_string(destination_wallet)
    mint_pubkey = Pubkey.from_string(token_mint)

    # Derive ATAs
    sender_ata = get_associated_token_address(str(sender_pubkey), token_mint)
    receiver_ata = get_associated_token_address(destination_wallet, token_mint)

    instructions = []

    # Verify if receiver account exists
    account_info = client.get_account_info(receiver_ata)

    if account_info.value is None:
        # Adds instruction to create the account if it's missing
        create_ata_ix = create_associated_token_account(
            payer=sender_pubkey, owner=receiver_pubkey, mint=mint_pubkey
        )
        instructions.append(create_ata_ix)

    # Prepare transfer instruction
    transfer_ix = transfer_checked(
        TransferCheckedParams(
            program_id=TOKEN_PROGRAM_ID,
            source=sender_ata,
            mint=mint_pubkey,
            dest=receiver_ata,
            owner=sender_pubkey,
            amount=amount,
            decimals=decimals,
        )
    )
    instructions.append(transfer_ix)

    # Modern Solana Transaction Building
    # 1. Get the latest blockhash from the network
    recent_blockhash_raw = client.get_latest_blockhash().value.blockhash
    try:
        recent_blockhash = Hash.from_string(str(recent_blockhash_raw))
    except Exception:
        recent_blockhash = recent_blockhash_raw

    # 2. Build the message with our instructions
    msg = Message(instructions, sender_pubkey)

    # 3. Create and sign the transaction
    tx = Transaction([sender_keypair], msg, recent_blockhash)

    # Finalize and send
    return client.send_transaction(tx)
