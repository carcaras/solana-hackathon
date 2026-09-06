import hashlib
import inspect
import json
import re
from typing import Any, Dict, List, Optional, Union
from solders.instruction import AccountMeta, Instruction
from solders.message import Message
from solders.pubkey import Pubkey
from solders.transaction import Transaction
from solders.hash import Hash

from solinpy.anchor import borsh


def snake_case(s: str) -> str:
    """Converte camelCase para snake_case."""
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", s)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


class InstructionCallable:
    """Um objeto chamável que representa uma instrução RPC dinâmica do Anchor."""

    def __init__(
        self,
        program: "Program",
        inst_def: Dict[str, Any],
        client: Any,
        build_only: bool = False,
    ):
        self.program = program
        self.inst_def = inst_def
        self.client = client
        self.build_only = build_only
        self.is_async = (
            not build_only
            and client is not None
            and (inspect.iscoroutinefunction(getattr(client, "send_transaction", None)))
        )

    def _build_ix(self, *args: Any, **kwargs: Any) -> Instruction:
        accounts_input = kwargs.get("accounts", {})

        idl_args = self.inst_def.get("args", [])
        mapped_args: Dict[str, Any] = {}

        for idx, arg_def in enumerate(idl_args):
            arg_name = arg_def["name"]
            if idx < len(args):
                mapped_args[arg_name] = args[idx]
            elif arg_name in kwargs:
                mapped_args[arg_name] = kwargs[arg_name]
            else:
                raise ValueError(f"Argumento obrigatório ausente: {arg_name}")

        idl_name = self.inst_def["name"]
        rust_name = snake_case(idl_name)
        preimage = f"global:{rust_name}".encode("utf-8")
        discriminator = hashlib.sha256(preimage).digest()[:8]

        serialized_data = b""
        types_registry = self.program.types_registry
        for arg_def in idl_args:
            arg_name = arg_def["name"]
            arg_type = arg_def["type"]
            arg_val = mapped_args[arg_name]
            serialized_data += borsh.serialize(arg_val, arg_type, types_registry)

        idl_accounts = self.inst_def.get("accounts", [])
        account_metas: List[AccountMeta] = []
        for acc_def in idl_accounts:
            acc_name = acc_def["name"]

            if acc_name not in accounts_input:
                raise ValueError(f"Conta obrigatória ausente no parâmetro accounts: {acc_name}")

            pubkey_str = str(accounts_input[acc_name])
            pubkey = Pubkey.from_string(pubkey_str)

            account_metas.append(
                AccountMeta(
                    pubkey=pubkey,
                    is_signer=acc_def.get("isSigner", acc_def.get("signer", False)),
                    is_writable=acc_def.get("isMut", acc_def.get("writable", False)),
                )
            )

        return Instruction(
            program_id=self.program.program_id,
            data=discriminator + serialized_data,
            accounts=account_metas,
        )

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        ix = self._build_ix(*args, **kwargs)
        if self.build_only:
            return ix

        signers = kwargs.get("signers", [])
        if not signers:
            raise ValueError(
                "Uma lista de assinantes (signers=[keypair]) é obrigatória para executar transações RPC."
            )

        if self.is_async:
            return self._execute_async(ix, signers)
        else:
            return self._execute_sync(ix, signers)

    def _prepare_tx(
        self, ix: Instruction, signers: List[Any], recent_blockhash: Any
    ) -> Transaction:
        payer = signers[0].pubkey()
        msg = Message([ix], payer)

        if hasattr(recent_blockhash, "blockhash"):
            bh = Hash.from_string(str(recent_blockhash.blockhash))
        elif hasattr(recent_blockhash, "value") and hasattr(recent_blockhash.value, "blockhash"):
            bh = Hash.from_string(str(recent_blockhash.value.blockhash))
        elif isinstance(recent_blockhash, str):
            bh = Hash.from_string(recent_blockhash)
        else:
            bh = recent_blockhash

        return Transaction(signers, msg, bh)

    async def _execute_async(self, ix: Instruction, signers: List[Any]) -> str:
        raw_bh = await self.client.get_latest_blockhash()
        blockhash_str = str(raw_bh)
        tx = self._prepare_tx(ix, signers, blockhash_str)
        return str(await self.client.send_transaction(tx))

    def _execute_sync(self, ix: Instruction, signers: List[Any]) -> str:
        raw_bh = self.client.get_latest_blockhash()
        blockhash_str = str(raw_bh)
        tx = self._prepare_tx(ix, signers, blockhash_str)
        return str(self.client.send_transaction(tx))


class RPCNamespace:
    """Namespace dinâmico para chamadas RPC do Anchor."""

    def __init__(self, program: "Program", client: Any, build_only: bool = False):
        self.program = program
        self.client = client
        self.build_only = build_only

    def __getattr__(self, name: str) -> InstructionCallable:
        target_name = name
        snake_target = snake_case(name)

        inst_def = None
        for inst in self.program.idl.get("instructions", []):
            inst_name = inst["name"]
            if inst_name == target_name or snake_case(inst_name) == snake_target:
                inst_def = inst
                break

        if not inst_def:
            raise AttributeError(
                f"Instrução '{name}' não encontrada no IDL do programa {self.program.name}."
            )

        return InstructionCallable(self.program, inst_def, self.client, self.build_only)


class Program:
    """Representa um Programa Anchor (smart contract) na Solana."""

    def __init__(self, idl: Dict[str, Any], program_id: Union[str, Pubkey], client: Any):
        self.idl = idl
        self.name = idl.get("name", "UnknownProgram")
        self.program_id = Pubkey.from_string(str(program_id))
        self.client = client

        self.types_registry: Dict[str, Any] = {}
        for type_def in idl.get("types", []):
            type_name = type_def.get("name")
            if not type_name:
                raise ValueError(f"IDL type definition missing 'name' field: {type_def}")
            self.types_registry[type_name] = type_def

        self.rpc = RPCNamespace(self, client, build_only=False)
        self.instruction = RPCNamespace(self, client, build_only=True)

    @classmethod
    def load(
        cls,
        idl_path_or_dict: Union[str, Dict[str, Any]],
        client: Any,
        program_id: Optional[Union[str, Pubkey]] = None,
    ) -> "Program":
        """Carrega uma IDL do Anchor a partir de um arquivo JSON ou dicionário Python."""
        if isinstance(idl_path_or_dict, str):
            with open(idl_path_or_dict, "r", encoding="utf-8") as f:
                idl = json.load(f)
        else:
            idl = idl_path_or_dict

        resolved_pid = program_id
        if not resolved_pid:
            metadata = idl.get("metadata", {})
            if "address" in metadata:
                resolved_pid = metadata["address"]
            else:
                raise ValueError(
                    "program_id não foi fornecido e não foi encontrado no campo 'metadata.address' da IDL."
                )

        return cls(idl, resolved_pid, client)
