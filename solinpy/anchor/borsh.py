from typing import Any, Dict, Optional
from solders.pubkey import Pubkey


import struct


def serialize(val: Any, type_def: Any, types_registry: Optional[Dict[str, Any]] = None) -> bytes:
    """Serializa um valor Python em bytes Borsh com base em sua definição de tipo do IDL."""
    types_registry = types_registry or {}

    # 1. Tipo básico representado como string
    if isinstance(type_def, str):
        if type_def == "u8":
            return struct.pack("<B", val)
        elif type_def == "u16":
            return struct.pack("<H", val)
        elif type_def == "u32":
            return struct.pack("<I", val)
        elif type_def == "u64":
            return struct.pack("<Q", val)
        elif type_def == "u128":
            if not (0 <= val < (1 << 128)):
                raise ValueError(f"Value out of range for u128: {val}")
            return struct.pack("<QQ", val & 0xFFFFFFFFFFFFFFFF, (val >> 64) & 0xFFFFFFFFFFFFFFFF)
        elif type_def == "i8":
            return struct.pack("<b", val)
        elif type_def == "i16":
            return struct.pack("<h", val)
        elif type_def == "i32":
            return struct.pack("<i", val)
        elif type_def == "i64":
            return struct.pack("<q", val)
        elif type_def == "i128":
            if not (-(1 << 127) <= val < (1 << 127)):
                raise ValueError(f"Value out of range for i128: {val}")
            unsigned_val = val if val >= 0 else (1 << 128) + val
            return struct.pack(
                "<QQ", unsigned_val & 0xFFFFFFFFFFFFFFFF, (unsigned_val >> 64) & 0xFFFFFFFFFFFFFFFF
            )
        elif type_def == "f32":
            return struct.pack("<f", float(val))
        elif type_def == "f64":
            return struct.pack("<d", float(val))
        elif type_def == "bool":
            return struct.pack("?", val)
        elif type_def == "publicKey":
            pubkey = Pubkey.from_string(str(val))
            return bytes(pubkey)
        elif type_def == "string":
            encoded: bytes = val.encode("utf-8")
            return struct.pack("<I", len(encoded)) + encoded
        elif type_def == "bytes":
            if isinstance(val, str):
                try:
                    val_bytes = bytes.fromhex(val)
                except ValueError as e:
                    raise ValueError(f"Invalid hexadecimal value for type 'bytes': {val!r}") from e
            else:
                val_bytes = bytes(val)
            return struct.pack("<I", len(val_bytes)) + val_bytes
        else:
            raise ValueError(f"Tipo básico não suportado: {type_def}")

    # 2. Definição de tipo complexo como dicionário
    if isinstance(type_def, dict):
        if "option" in type_def:
            if val is None:
                return b"\x00"
            else:
                return b"\x01" + serialize(val, type_def["option"], types_registry)

        elif "vec" in type_def:
            serialized_elements = [serialize(x, type_def["vec"], types_registry) for x in val]
            return struct.pack("<I", len(val)) + b"".join(serialized_elements)

        elif "array" in type_def:
            elem_type, size = type_def["array"]
            if len(val) != size:
                raise ValueError(
                    f"Tamanho do array incorreto: esperado {size}, recebido {len(val)}"
                )
            serialized_elements = [serialize(x, elem_type, types_registry) for x in val]
            return b"".join(serialized_elements)

        elif "defined" in type_def:
            struct_name = type_def["defined"]
            if struct_name not in types_registry:
                raise ValueError(f"Tipo definido '{struct_name}' não encontrado no registro")

            struct_def = types_registry[struct_name]

            if struct_def.get("type", {}).get("kind") == "struct":
                fields = struct_def["type"]["fields"]
                res = b""
                is_dict = isinstance(val, dict)
                for field in fields:
                    f_name = field["name"]
                    f_type = field["type"]
                    f_val = val[f_name] if is_dict else getattr(val, f_name)
                    res += serialize(f_val, f_type, types_registry)
                return res

            elif struct_def.get("type", {}).get("kind") == "enum":
                variants = struct_def["type"]["variants"]
                variant_names = [v["name"] for v in variants]

                if isinstance(val, str):
                    if val not in variant_names:
                        raise ValueError(
                            f"Variante enum inválida '{val}' para o enum '{struct_name}'"
                        )
                    idx = variant_names.index(val)
                    return struct.pack("<B", idx)

                elif isinstance(val, dict):
                    if len(val) != 1:
                        raise ValueError(
                            f"Enum variant dict must have exactly one key, "
                            f"got {len(val)}: {list(val.keys())}"
                        )
                    variant_name = list(val.keys())[0]
                    if variant_name not in variant_names:
                        raise ValueError(
                            f"Variante enum inválida '{variant_name}' para o enum '{struct_name}'"
                        )
                    idx = variant_names.index(variant_name)
                    res = struct.pack("<B", idx)

                    variant_def = variants[idx]
                    if "fields" in variant_def:
                        payload = val[variant_name]
                        for i, field in enumerate(variant_def["fields"]):
                            if isinstance(field, dict) and "type" in field:
                                f_type = field["type"]
                                f_name = field.get("name", i)
                                f_val = payload[f_name] if isinstance(payload, dict) else payload[i]
                            else:
                                f_type = field
                                f_val = payload[i] if isinstance(payload, list) else payload
                            res += serialize(f_val, f_type, types_registry)
                    return res
            else:
                raise ValueError(
                    f"Tipo de definição não suportado para '{struct_name}' (kind: {struct_def.get('type', {}).get('kind')})"
                )

    raise ValueError(f"Definição de tipo inválida: {type_def}")
