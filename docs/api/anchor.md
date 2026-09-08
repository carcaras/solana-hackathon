# Anchor API Reference

The Anchor module provides Python integration for Anchor-based Solana programs. It handles IDL parsing, instruction serialization via Borsh, and dynamic RPC method construction.

## Overview

Anchors programs on Solana expose an Interface Description Language (IDL) that defines instructions, accounts, and types. This module dynamically generates callable RPC methods from an IDL, handling serialization and account metadata resolution automatically.

## Key Concepts

- **IDL**: JSON descriptor of the program's interface (instructions, accounts, types)
- **Borsh**: Binary serialization format used by Solana/Anchor
- **Instruction**: A serialized program call with account metadata and data
- **Program ID**: The on-chain address of the deployed Anchor program

## Quick Start

```python
from solinpy.anchor import Program

# Load from IDL file
program = Program.load("path/to/idl.json", client, program_id="...")

# Or load from an IDL dict
import json
with open("idl.json") as f:
    idl = json.load(f)
program = Program.load(idl, client)

# Call an instruction dynamically
result = program.rpc.initialize(arg1, arg2, accounts={
    "account1": "Pubkey...",
    "account2": "Pubkey...",
}, signers=[keypair])
```

---

## Program

::: solinpy.anchor.program.Program

### Methods

#### `__init__(idl, program_id, client)`

Creates a new Program instance from an IDL definition.

| Parameter | Type | Description |
|-----------|------|-------------|
| `idl` | `Dict[str, Any]` | The Anchor IDL as a parsed dictionary |
| `program_id` | `str \| Pubkey` | The on-chain program address |
| `client` | `SolanaRPCClient` | RPC client for transaction submission |

**Raises**: `ValueError` if IDL types are missing required fields.

#### `Program.load(idl_path_or_dict, client, program_id=None)`

Class method that loads an IDL from a JSON file path or a Python dict.

| Parameter | Type | Description |
|-----------|------|-------------|
| `idl_path_or_dict` | `str \| Dict[str, Any]` | File path to IDL JSON or pre-parsed dict |
| `client` | `SolanaRPCClient` | RPC client for transaction submission |
| `program_id` | `str \| Pubkey \| None` | Optional override; falls back to `metadata.address` |

**Returns**: A fully initialized `Program` instance.

**Raises**: `ValueError` if `program_id` is not provided and `metadata.address` is absent.

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `idl` | `Dict[str, Any]` | Raw IDL dictionary |
| `name` | `str` | Program name from IDL |
| `program_id` | `Pubkey` | Program's on-chain address |
| `types_registry` | `Dict[str, Any]` | Map of type name to type definition |
| `rpc` | `RPCNamespace` | Dynamic namespace for RPC instruction calls (executes transactions) |
| `instruction` | `RPCNamespace` | Dynamic namespace for building instructions only (no RPC) |

### Usage Notes

- Use `program.rpc.<instruction_name>()` to execute an instruction via RPC.
- Use `program.instruction.<instruction_name>()` to build an `Instruction` object without sending it.
- Instruction names are matched by both camelCase and snake_case (e.g., both `program.rpc.initialize()` and `program.rpc.initialize()` work).

---

## RPCNamespace

::: solinpy.anchor.program.RPCNamespace

Dynamically resolves instruction names from the IDL. Each attribute access returns an `InstructionCallable` for the matching instruction definition.

### Methods

#### `__getattr__(name) -> InstructionCallable`

Looks up an instruction by name in the IDL's `instructions` list. Matches both exact name and snake_case-converted variants.

**Raises**: `AttributeError` if the instruction is not found.

---

## InstructionCallable

::: solinpy.anchor.program.InstructionCallable

Represents a single instruction call bound to a program definition. Handles argument mapping, Borsh serialization, and transaction construction.

### Methods

#### `__call__(*args, **kwargs)`

Builds and (optionally) executes the instruction.

| Parameter | Type | Description |
|-----------|------|-------------|
| `*args` | `Any` | Positional arguments mapped to IDL instruction args in order |
| `accounts` | `Dict[str, str]` | Named account public keys required by the instruction |
| `signers` | `List[Keypair]` | Keypairs for signing (first keypair is the payer) |

**Returns**: Transaction signature (`str`) if executed via RPC, or `Instruction` if `build_only=True`.

**Raises**:
- `ValueError` on missing arguments or accounts
- `ValueError` if no signers provided for RPC execution

#### `_build_ix(*args, **kwargs) -> Instruction`

Builds the `Instruction` with discriminator, serialized data, and account metadata.

#### `_execute_sync(ix, signers) -> str`

Synchronous RPC execution: gets latest blockhash, builds transaction, sends it.

#### `_execute_async(ix, signers) -> str`

Asynchronous RPC execution (when client has async methods).

---

## Borsh Serialization

::: solinpy.anchor.borsh

The `borsh` module handles serialization of Python values into Borsh binary format for Anchor instruction data.

### Functions

#### `serialize(val, type_def, types_registry=None) -> bytes`

Serializes a Python value according to an Anchor IDL type definition.

| Parameter | Type | Description |
|-----------|------|-------------|
| `val` | `Any` | The Python value to serialize |
| `type_def` | `str \| Dict[str, Any]` | IDL type (string for primitives, dict for complex types) |
| `types_registry` | `Optional[Dict[str, Any]]` | Map of user-defined type names to definitions |

**Supported types**:
- Primitives: `u8`, `u16`, `u32`, `u64`, `u128`, `i8`, `i16`, `i32`, `i64`, `i128`, `f32`, `f64`, `bool`, `string`, `bytes`, `publicKey`
- Complex: `{ "option": T }`, `{ "vec": T }`, `{ "array": [T, size] }`, `{ "defined": "TypeName" }`

**Returns**: Serialized bytes ready for instruction data.

**Raises**:
- `ValueError` for unsupported types or out-of-range values
- `ValueError` if `defined` type not found in registry

### How it Works

1. Computes the 8-byte discriminator from the instruction name (SHA-256 of `global:<snake_case_name>`)
2. Serializes each argument using `borsh.serialize()`
3. Constructs `AccountMeta` list from the instruction's accounts definition and the user-provided `accounts` dict
4. Returns the complete `Instruction` object

---

## AccountMeta Construction

For each instruction, account metadata is built from the IDL's `accounts` array:

| IDL Field | Default | Description |
|-----------|---------|-------------|
| `isSigner` / `signer` | `False` | Whether this account must sign |
| `isMut` / `writable` | `False` | Whether this account is writable |

Accounts are resolved by matching the `accounts` dict keys to the IDL account names. Missing required accounts raise `ValueError`.

---

## Error Handling

| Error | Cause |
|-------|-------|
| `ValueError: Argumento obrigatório ausente` | Missing positional or keyword arg |
| `ValueError: Conta obrigatória ausente` | Missing account in `accounts` dict |
| `ValueError: Uma lista de assinantes` | No signers provided for RPC call |
| `ValueError: Tipo básico não suportado` | Unknown primitive type in IDL |
| `ValueError: Tipo definido 'X' não encontrado` | Referenced type not in IDL's `types` |
| `AttributeError: Instrução 'X' não encontrada` | Instruction name not in IDL |
