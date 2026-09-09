"""
Módulo de desserialização para dados de contas Solana.

Fornece funções para decodificar e estruturar dados brutos de contas
em formatos mais legíveis e úteis para integração com programas comuns
como System Program, SPL Token, Metaplex, etc.
"""

import base64
import struct
from typing import Dict, Any, Union
from solders.pubkey import Pubkey


def decode_base64_to_bytes(data: str) -> bytes:
    """
    Decodifica string base64 para bytes.

    Args:
        data: String codificada em base64

    Returns:
        Dados decodificados como bytes

    Raises:
        ValueError: Se a string não for base64 válida
    """
    try:
        return base64.b64decode(data)
    except Exception as e:
        raise ValueError(f"Falha ao decodificar base64: {e}")


def decode_bytes_to_base64(data: bytes) -> str:
    """
    Codifica bytes para string base64.

    Args:
        data: Dados em bytes

    Returns:
        String codificada em base64
    """
    return base64.b64encode(data).decode("utf-8")


def parse_pubkey_from_bytes(data: bytes, offset: int = 0) -> Pubkey:
    """
    Extrai uma chave pública Solana de dados binários.

    Args:
        data: Dados binários contendo a chave pública
        offset: Posição inicial da chave pública nos dados

    Returns:
        Objeto Pubkey do solders

    Raises:
        ValueError: Se não houver bytes suficientes
    """
    if len(data) - offset < 32:
        raise ValueError(
            f"Dados insuficientes para pubkey: precisa de 32 bytes, disponível {len(data) - offset}"
        )
    return Pubkey.from_bytes(data[offset : offset + 32])


def parse_u64_from_bytes(data: bytes, offset: int = 0, little_endian: bool = True) -> int:
    """
    Extrai um inteiro de 64 bits de dados binários.

    Args:
        data: Dados binários contendo o inteiro
        offset: Posição inicial nos dados
        little_endian: Se True, usa little-endian (padrão Solana)

    Returns:
        Inteiro de 64 bits

    Raises:
        ValueError: Se não houver bytes suficientes
    """
    if len(data) - offset < 8:
        raise ValueError(
            f"Dados insuficientes para u64: precisa de 8 bytes, disponível {len(data) - offset}"
        )

    fmt = "<Q" if little_endian else ">Q"
    return int(struct.unpack(fmt, data[offset : offset + 8])[0])


def parse_u32_from_bytes(data: bytes, offset: int = 0, little_endian: bool = True) -> int:
    """
    Extrai um inteiro de 32 bits de dados binários.

    Args:
        data: Dados binários contendo o inteiro
        offset: Posição inicial nos dados
        little_endian: Se True, usa little-endian (padrão Solana)

    Returns:
        Inteiro de 32 bits

    Raises:
        ValueError: Se não houver bytes suficientes
    """
    if len(data) - offset < 4:
        raise ValueError(
            f"Dados insuficientes para u32: precisa de 4 bytes, disponível {len(data) - offset}"
        )

    fmt = "<I" if little_endian else ">I"
    return int(struct.unpack(fmt, data[offset : offset + 4])[0])


def parse_u8_from_bytes(data: bytes, offset: int = 0) -> int:
    """
    Extrai um inteiro de 8 bits de dados binários.

    Args:
        data: Dados binários contendo o inteiro
        offset: Posição inicial nos dados

    Returns:
        Inteiro de 8 bits (0-255)

    Raises:
        ValueError: Se não houver bytes suficientes
    """
    if len(data) - offset < 1:
        raise ValueError(
            f"Dados insuficientes para u8: precisa de 1 byte, disponível {len(data) - offset}"
        )

    return data[offset]


def decode_system_account(data: bytes) -> Dict[str, Any]:
    """
    Desserializa dados de uma conta do System Program.

    Nota: Contas do System Program geralmente não possuem dados significativos.
    Esta função existe para compatibilidade futura.

    Args:
        data: Dados brutos da conta

    Returns:
        Dicionário com campos estruturados
    """
    return {
        "program": "System Program",
        "data_length": len(data),
        "raw_data": data.hex() if data else None,
    }


def decode_spl_token_account(data: bytes) -> Dict[str, Any]:
    """
    Desserializa dados de uma conta SPL Token (Token Account).

    Estrutura esperada (~165 bytes):
    - mint: Pubkey (32 bytes)
    - owner: Pubkey (32 bytes)
    - amount: u64 (8 bytes)
    - delegate: Option<Pubkey> (1 + 32 bytes)
    - state: u8 (1 byte)
    - is_native: Option<u64> (1 + 8 bytes)
    - delegated_amount: u64 (8 bytes)
    - close_authority: Option<Pubkey> (1 + 32 bytes)

    Args:
        data: Dados brutos da conta token (mínimo 72 bytes)

    Returns:
        Dicionário com campos estruturados da conta token

    Raises:
        ValueError: Se os dados não tiverem tamanho esperado
    """
    if len(data) < 72:
        raise ValueError(f"Dados SPL Token inválidos: esperado 72 bytes, recebido {len(data)}")

    offset = 0
    mint = parse_pubkey_from_bytes(data, offset)
    offset += 32

    owner = parse_pubkey_from_bytes(data, offset)
    offset += 32

    amount = parse_u64_from_bytes(data, offset)
    offset += 8

    # Campo delegate (Option<Pubkey>): 1 byte flag + 32 bytes pubkey (ou padding)
    has_delegate = parse_u8_from_bytes(data, offset)
    offset += 1

    delegate = None
    if has_delegate == 1:
        delegate = str(parse_pubkey_from_bytes(data, offset))
    offset += 32  # Sempre avança 32 bytes (pubkey ou padding)

    # Estado da conta: 0=uninitialized, 1=initialized, 2=frozen
    state = parse_u8_from_bytes(data, offset)
    offset += 1

    state_map = {0: "uninitialized", 1: "initialized", 2: "frozen"}

    # Campo is_native (Option<u64>)
    is_native_option = parse_u8_from_bytes(data, offset)
    offset += 1

    is_native = False
    native_amount = 0
    if is_native_option == 1:
        is_native = True
        native_amount = parse_u64_from_bytes(data, offset)
        offset += 8

    # Delegated amount
    delegated_amount = parse_u64_from_bytes(data, offset)
    offset += 8

    # Close authority (Option<Pubkey>): 1 byte flag + 32 bytes pubkey (ou padding)
    has_close_authority = parse_u8_from_bytes(data, offset)
    offset += 1

    close_authority = None
    if has_close_authority == 1:
        close_authority = str(parse_pubkey_from_bytes(data, offset))

    return {
        "program": "SPL Token",
        "mint": str(mint),
        "owner": str(owner),
        "amount": amount,
        "delegate": delegate,
        "state": state_map.get(state, f"unknown({state})"),
        "is_native": is_native,
        "native_amount": native_amount,
        "delegated_amount": delegated_amount,
        "close_authority": close_authority,
    }


def decode_spl_token_mint(data: bytes) -> Dict[str, Any]:
    """
    Desserializa dados de uma conta Mint SPL Token.

    Estrutura esperada (82 bytes):
    - mint_authority: Option<Pubkey> (1 + 32 bytes)
    - supply: u64 (8 bytes)
    - decimals: u8 (1 byte)
    - is_initialized: bool (1 byte)
    - freeze_authority: Option<Pubkey> (1 + 32 bytes)

    Args:
        data: Dados brutos da conta mint (82 bytes)

    Returns:
        Dicionário com informações do mint

    Raises:
        ValueError: Se os dados não tiverem tamanho esperado
    """
    if len(data) < 82:
        raise ValueError(f"Dados Mint SPL Token inválidos: esperado 82 bytes, recebido {len(data)}")

    offset = 0

    # Mint authority (Option<Pubkey>): 1 byte flag + 32 bytes pubkey (ou padding)
    has_mint_authority = parse_u8_from_bytes(data, offset)
    offset += 1

    mint_authority = None
    if has_mint_authority == 1:
        mint_authority = str(parse_pubkey_from_bytes(data, offset))
    offset += 32  # Sempre avança 32 bytes (pubkey ou padding)

    supply = parse_u64_from_bytes(data, offset)
    offset += 8

    decimals = parse_u8_from_bytes(data, offset)
    offset += 1

    is_initialized = parse_u8_from_bytes(data, offset) == 1
    offset += 1

    # Freeze authority (Option<Pubkey>): 1 byte flag + 32 bytes pubkey (ou padding)
    has_freeze_authority = parse_u8_from_bytes(data, offset)
    offset += 1

    freeze_authority = None
    if has_freeze_authority == 1:
        freeze_authority = str(parse_pubkey_from_bytes(data, offset))

    return {
        "program": "SPL Token Mint",
        "mint_authority": mint_authority,
        "supply": supply,
        "decimals": decimals,
        "is_initialized": is_initialized,
        "freeze_authority": freeze_authority,
    }


def decode_account_data(
    data: Union[bytes, str, Dict[str, Any]], program_type: str = "auto"
) -> Dict[str, Any]:
    """
    Função genérica para desserializar dados de conta.

    Args:
        data: Dados brutos da conta (bytes, string ou dict)
        program_type: Tipo de programa para desserialização:
            - "auto": Tenta detectar automaticamente
            - "spl_token": SPL Token Account
            - "spl_token_mint": SPL Token Mint
            - "system": System Program
            - "raw": Retorna dados brutos

    Returns:
        Dicionário com dados estruturados

    Raises:
        ValueError: Se o tipo de programa for desconhecido
    """
    # Dados já parseados (jsonParsed)
    if isinstance(data, dict):
        return {"program": "jsonParsed", "parsed_data": data}

    # Converte string para bytes se necessário
    if isinstance(data, str):
        try:
            data_bytes = decode_base64_to_bytes(data)
        except ValueError:
            return {"program": "raw", "data": data, "encoding": "string"}
    elif isinstance(data, bytes):
        data_bytes = data
    else:
        return {"program": "raw", "data": str(data), "encoding": "unknown"}

    # Desserialização automática baseada no tamanho
    if program_type == "auto":
        # SPL Token Mint: exatamente 82 bytes (33+8+1+1+33)
        if len(data_bytes) == 82:
            program_type = "spl_token_mint"
        # SPL Token Account: >= 72 bytes (estrutura mínima)
        elif len(data_bytes) >= 72:
            program_type = "spl_token"
        else:
            program_type = "raw"

    # Desserializa conforme o tipo
    if program_type == "spl_token":
        try:
            return decode_spl_token_account(data_bytes)
        except ValueError:
            program_type = "raw"

    elif program_type == "spl_token_mint":
        try:
            return decode_spl_token_mint(data_bytes)
        except ValueError:
            program_type = "raw"

    elif program_type == "system":
        return decode_system_account(data_bytes)

    # Fallback: dados brutos
    return {
        "program": "raw",
        "data_hex": data_bytes.hex(),
        "data_length": len(data_bytes),
        "encoding": "bytes",
    }
