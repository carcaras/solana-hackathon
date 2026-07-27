from unittest.mock import MagicMock
from solders.instruction import Instruction
from solders.keypair import Keypair
from solders.pubkey import Pubkey

from solinpy.anchor import borsh
from solinpy.anchor.program import Program

MOCK_IDL = {
    "version": "0.1.0",
    "name": "basic_vault",
    "instructions": [
        {
            "name": "initializeVault",
            "accounts": [
                {"name": "vault", "isMut": True, "isSigner": False},
                {"name": "authority", "isMut": True, "isSigner": True},
                {"name": "systemProgram", "isMut": False, "isSigner": False},
            ],
            "args": [
                {"name": "bump", "type": "u8"},
                {"name": "amount", "type": "u64"},
                {"name": "name", "type": "string"},
            ],
        }
    ],
    "types": [
        {
            "name": "MyStruct",
            "type": {
                "kind": "struct",
                "fields": [
                    {"name": "id", "type": "u32"},
                    {"name": "active", "type": "bool"},
                ],
            },
        },
        {
            "name": "Direction",
            "type": {
                "kind": "enum",
                "variants": [
                    {"name": "North"},
                    {"name": "South"},
                    {"name": "East"},
                    {"name": "West"},
                ],
            },
        },
    ],
    "metadata": {"address": "4ND3y8d4Q6r3QJ6VwY2w2TnY4A2D6dYj3q3p8eQmB9QZ"},
}


def test_borsh_basic_serialization() -> None:
    assert borsh.serialize(255, "u8") == b"\xff"
    assert borsh.serialize(1000, "u64") == b"\xe8\x03\x00\x00\x00\x00\x00\x00"
    assert borsh.serialize(True, "bool") == b"\x01"
    assert borsh.serialize(False, "bool") == b"\x00"
    assert borsh.serialize("SolInPy", "string") == b"\x07\x00\x00\x00SolInPy"
    pub = Pubkey.from_string("11111111111111111111111111111111")
    assert borsh.serialize(pub, "publicKey") == bytes(pub)


def test_borsh_complex_serialization() -> None:
    registry = {"MyStruct": MOCK_IDL["types"][0], "Direction": MOCK_IDL["types"][1]}

    struct_val = {"id": 42, "active": True}
    expected = b"\x2a\x00\x00\x00\x01"
    assert borsh.serialize(struct_val, {"defined": "MyStruct"}, registry) == expected

    assert borsh.serialize("South", {"defined": "Direction"}, registry) == b"\x01"

    assert borsh.serialize(None, {"option": "u8"}) == b"\x00"
    assert borsh.serialize(5, {"option": "u8"}) == b"\x01\x05"

    assert borsh.serialize([1, 2, 3], {"vec": "u8"}) == b"\x03\x00\x00\x00\x01\x02\x03"


def test_program_instruction_building() -> None:
    client = MagicMock()
    program = Program.load(MOCK_IDL, client)

    vault_pub = Pubkey.from_string("SysvarRent111111111111111111111111111111111")
    auth_key = Keypair()
    sys_prog = Pubkey.from_string("11111111111111111111111111111111")

    ix = program.instruction.initialize_vault(
        255,
        1000000,
        "my-vault",
        accounts={
            "vault": vault_pub,
            "authority": auth_key.pubkey(),
            "systemProgram": sys_prog,
        },
    )

    assert isinstance(ix, Instruction)
    assert ix.program_id == program.program_id
    assert len(ix.accounts) == 3
    assert ix.accounts[0].pubkey == vault_pub
    assert ix.accounts[1].is_signer is True
    assert ix.accounts[2].is_writable is False

    assert len(ix.data) > 8


def test_program_rpc_execution() -> None:
    client = MagicMock()
    client.get_latest_blockhash.return_value = "11111111111111111111111111111111"
    client.send_transaction.return_value = "transaction-signature"

    program = Program.load(MOCK_IDL, client)

    vault_pub = Pubkey.from_string("SysvarRent111111111111111111111111111111111")
    auth_key = Keypair()
    sys_prog = Pubkey.from_string("11111111111111111111111111111111")

    sig = program.rpc.initialize_vault(
        255,
        1000000,
        "my-vault",
        accounts={
            "vault": vault_pub,
            "authority": auth_key.pubkey(),
            "systemProgram": sys_prog,
        },
        signers=[auth_key],
    )

    assert sig == "transaction-signature"
    client.send_transaction.assert_called_once()
