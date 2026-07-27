import struct
from typing import Any, Optional
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.message import Message
from solders.transaction import Transaction
from solders.hash import Hash
from solders.instruction import Instruction, AccountMeta
from solders.system_program import ID as SYS_PROGRAM_ID

# Constants for SPL Token Program
TOKEN_PROGRAM_ID = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
ASSOCIATED_TOKEN_PROGRAM_ID = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")


class AuthorityType:
    MintTokens = 0
    FreezeAccount = 1
    AccountOwner = 2
    CloseAccount = 3


def get_associated_token_address(owner_address: str, token_mint_address: str) -> Pubkey:
    """Deriva o ATA (Associated Token Account) para a carteira e mint informados."""
    owner_pubkey = Pubkey.from_string(owner_address)
    mint_pubkey = Pubkey.from_string(token_mint_address)

    ata, _ = Pubkey.find_program_address(
        [bytes(owner_pubkey), bytes(TOKEN_PROGRAM_ID), bytes(mint_pubkey)],
        ASSOCIATED_TOKEN_PROGRAM_ID,
    )
    return ata


def create_associated_token_account(payer: Pubkey, owner: Pubkey, mint: Pubkey) -> Instruction:
    """Cria uma instrução para criar uma conta de token associada (ATA)."""
    ata = get_associated_token_address(str(owner), str(mint))

    return Instruction(
        program_id=ASSOCIATED_TOKEN_PROGRAM_ID,
        data=b"",
        accounts=[
            AccountMeta(pubkey=payer, is_signer=True, is_writable=True),
            AccountMeta(pubkey=ata, is_signer=False, is_writable=True),
            AccountMeta(pubkey=owner, is_signer=False, is_writable=False),
            AccountMeta(pubkey=mint, is_signer=False, is_writable=False),
            AccountMeta(pubkey=SYS_PROGRAM_ID, is_signer=False, is_writable=False),
            AccountMeta(pubkey=TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),
        ],
    )


class TransferCheckedParams:
    def __init__(
        self,
        program_id: Pubkey,
        source: Pubkey,
        mint: Pubkey,
        dest: Pubkey,
        owner: Pubkey,
        amount: int,
        decimals: int,
    ):
        self.program_id = program_id
        self.source = source
        self.mint = mint
        self.dest = dest
        self.owner = owner
        self.amount = amount
        self.decimals = decimals


def transfer_checked(params: TransferCheckedParams) -> Instruction:
    """Cria uma instrução transfer_checked para tokens SPL."""
    data = struct.pack("<BQB", 12, params.amount, params.decimals)

    return Instruction(
        program_id=params.program_id,
        data=data,
        accounts=[
            AccountMeta(pubkey=params.source, is_signer=False, is_writable=True),
            AccountMeta(pubkey=params.mint, is_signer=False, is_writable=False),
            AccountMeta(pubkey=params.dest, is_signer=False, is_writable=True),
            AccountMeta(pubkey=params.owner, is_signer=True, is_writable=False),
        ],
    )


class InitializeMintParams:
    def __init__(
        self,
        program_id: Pubkey,
        mint: Pubkey,
        decimals: int,
        mint_authority: Pubkey,
        freeze_authority: Optional[Pubkey] = None,
    ):
        self.program_id = program_id
        self.mint = mint
        self.decimals = decimals
        self.mint_authority = mint_authority
        self.freeze_authority = freeze_authority


def initialize_mint(params: InitializeMintParams) -> Instruction:
    """Cria uma instrução initialize_mint2 para tokens SPL."""
    data = struct.pack("<BB", 20, params.decimals) + bytes(params.mint_authority)
    if params.freeze_authority:
        data += b"\x01" + bytes(params.freeze_authority)
    else:
        data += b"\x00"

    return Instruction(
        program_id=params.program_id,
        data=data,
        accounts=[
            AccountMeta(pubkey=params.mint, is_signer=False, is_writable=True),
        ],
    )


class MintToParams:
    def __init__(
        self, program_id: Pubkey, mint: Pubkey, dest: Pubkey, mint_authority: Pubkey, amount: int
    ):
        self.program_id = program_id
        self.mint = mint
        self.dest = dest
        self.mint_authority = mint_authority
        self.amount = amount


def mint_to(params: MintToParams) -> Instruction:
    """Cria uma instrução mint_to para tokens SPL."""
    data = struct.pack("<BQ", 7, params.amount)

    return Instruction(
        program_id=params.program_id,
        data=data,
        accounts=[
            AccountMeta(pubkey=params.mint, is_signer=False, is_writable=True),
            AccountMeta(pubkey=params.dest, is_signer=False, is_writable=True),
            AccountMeta(pubkey=params.mint_authority, is_signer=True, is_writable=False),
        ],
    )


class SetAuthorityParams:
    def __init__(
        self,
        program_id: Pubkey,
        account: Pubkey,
        authority_type: int,
        current_authority: Pubkey,
        new_authority: Optional[Pubkey] = None,
    ):
        self.program_id = program_id
        self.account = account
        self.authority_type = authority_type
        self.current_authority = current_authority
        self.new_authority = new_authority


def set_authority(params: SetAuthorityParams) -> Instruction:
    """Cria uma instrução set_authority para tokens SPL."""
    data = struct.pack("<BBB", 6, params.authority_type, 1 if params.new_authority else 0)
    if params.new_authority:
        data += bytes(params.new_authority)

    return Instruction(
        program_id=params.program_id,
        data=data,
        accounts=[
            AccountMeta(pubkey=params.account, is_signer=False, is_writable=True),
            AccountMeta(pubkey=params.current_authority, is_signer=True, is_writable=False),
        ],
    )


def send_token_transfer(
    client: Any,
    sender_keypair: Keypair,
    destination_wallet: str,
    token_mint: str,
    amount: int,
    decimals: int,
) -> Any:
    """Executa uma transferência de tokens SPL completa usando a arquitetura Solders."""
    sender_pubkey = sender_keypair.pubkey()
    receiver_pubkey = Pubkey.from_string(destination_wallet)
    mint_pubkey = Pubkey.from_string(token_mint)

    # Derivar ATAs
    sender_ata = get_associated_token_address(str(sender_pubkey), token_mint)
    receiver_ata = get_associated_token_address(destination_wallet, token_mint)

    instructions = []

    # Verificar se a conta receptora existe
    account_info = client.get_account_info(receiver_ata)

    if account_info.value is None:
        create_ata_ix = create_associated_token_account(
            payer=sender_pubkey, owner=receiver_pubkey, mint=mint_pubkey
        )
        instructions.append(create_ata_ix)

    # Preparar instrução de transferência
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

    # Construção de Transação Solana
    recent_blockhash_raw = client.get_latest_blockhash().value.blockhash
    try:
        recent_blockhash = Hash.from_string(str(recent_blockhash_raw))
    except Exception:
        recent_blockhash = recent_blockhash_raw

    msg = Message(instructions, sender_pubkey)
    tx = Transaction([sender_keypair], msg, recent_blockhash)

    return client.send_transaction(tx)
