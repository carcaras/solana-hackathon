from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from solders.hash import Hash
from solders.keypair import Keypair
from solders.pubkey import Pubkey

from solinpy.transaction.token import (
    ASSOCIATED_TOKEN_PROGRAM_ID,
    TOKEN_PROGRAM_ID,
    get_associated_token_address,
    send_token_transfer,
)


def test_get_associated_token_address_matches_program_derivation() -> None:
    owner = "4ND3y8d4Q6r3QJ6VwY2w2TnY4A2D6dYj3q3p8eQmB9QZ"
    mint = "So11111111111111111111111111111111111111112"

    derived = get_associated_token_address(owner, mint)
    expected, _ = Pubkey.find_program_address(
        [
            bytes(Pubkey.from_string(owner)),
            bytes(TOKEN_PROGRAM_ID),
            bytes(Pubkey.from_string(mint)),
        ],
        ASSOCIATED_TOKEN_PROGRAM_ID,
    )

    assert derived == expected


@patch("solinpy.transaction.token.Transaction")
@patch("solinpy.transaction.token.Message")
@patch("solinpy.transaction.token.transfer_checked")
@patch("solinpy.transaction.token.create_associated_token_account")
@patch("solinpy.transaction.token.get_associated_token_address")
def test_send_token_transfer_creates_receiver_ata_when_missing(
    mock_get_ata,
    mock_create_ata,
    mock_transfer_checked,
    mock_message,
    mock_transaction,
) -> None:
    sender = Keypair()
    receiver_wallet = "4ND3y8d4Q6r3QJ6VwY2w2TnY4A2D6dYj3q3p8eQmB9QZ"
    mint = "So11111111111111111111111111111111111111112"
    sender_ata = Pubkey.from_string("11111111111111111111111111111111")
    receiver_ata = Pubkey.from_string("SysvarRent111111111111111111111111111111111")

    mock_get_ata.side_effect = [sender_ata, receiver_ata]
    mock_create_ata.return_value = "create-ata-ix"
    mock_transfer_checked.return_value = "transfer-ix"
    mock_message.return_value = "message"
    mock_transaction.return_value = "signed-tx"

    client = MagicMock()
    client.get_account_info.return_value = SimpleNamespace(value=None)
    blockhash = "11111111111111111111111111111111"
    client.get_latest_blockhash.return_value = SimpleNamespace(
        value=SimpleNamespace(blockhash=blockhash)
    )
    client.send_transaction.return_value = "tx-sig"

    result = send_token_transfer(client, sender, receiver_wallet, mint, amount=25, decimals=6)

    assert result == "tx-sig"
    mock_create_ata.assert_called_once()
    mock_transfer_checked.assert_called_once()
    mock_message.assert_called_once_with(["create-ata-ix", "transfer-ix"], sender.pubkey())
    mock_transaction.assert_called_once_with([sender], "message", Hash.from_string(blockhash))
    client.send_transaction.assert_called_once_with("signed-tx")

    params = mock_transfer_checked.call_args.args[0]
    assert params.program_id == TOKEN_PROGRAM_ID
    assert params.source == sender_ata
    assert params.dest == receiver_ata
    assert params.amount == 25
    assert params.decimals == 6


@patch("solinpy.transaction.token.Transaction")
@patch("solinpy.transaction.token.Message")
@patch("solinpy.transaction.token.transfer_checked")
@patch("solinpy.transaction.token.create_associated_token_account")
@patch("solinpy.transaction.token.get_associated_token_address")
def test_send_token_transfer_skips_receiver_ata_creation_when_present(
    mock_get_ata,
    mock_create_ata,
    mock_transfer_checked,
    mock_message,
    mock_transaction,
) -> None:
    sender = Keypair()
    receiver_wallet = "4ND3y8d4Q6r3QJ6VwY2w2TnY4A2D6dYj3q3p8eQmB9QZ"
    mint = "So11111111111111111111111111111111111111112"
    sender_ata = Pubkey.from_string("11111111111111111111111111111111")
    receiver_ata = Pubkey.from_string("SysvarRent111111111111111111111111111111111")

    mock_get_ata.side_effect = [sender_ata, receiver_ata]
    mock_transfer_checked.return_value = "transfer-ix"
    mock_message.return_value = "message"
    mock_transaction.return_value = "signed-tx"

    client = MagicMock()
    client.get_account_info.return_value = SimpleNamespace(value=object())
    blockhash = "SysvarRent111111111111111111111111111111111"
    client.get_latest_blockhash.return_value = SimpleNamespace(
        value=SimpleNamespace(blockhash=blockhash)
    )
    client.send_transaction.return_value = "tx-sig-2"

    result = send_token_transfer(client, sender, receiver_wallet, mint, amount=10, decimals=9)

    assert result == "tx-sig-2"
    mock_create_ata.assert_not_called()
    mock_transfer_checked.assert_called_once()
    mock_message.assert_called_once_with(["transfer-ix"], sender.pubkey())
    mock_transaction.assert_called_once_with([sender], "message", Hash.from_string(blockhash))
    client.send_transaction.assert_called_once_with("signed-tx")
