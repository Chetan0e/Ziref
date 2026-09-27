import struct
import zlib
import hashlib

def uleb128(val: int) -> bytes:
    res = bytearray()
    while True:
        b = val & 0x7f
        val >>= 7
        if val != 0:
            b |= 0x80
            res.append(b)
        else:
            res.append(b)
            break
    return bytes(res)

def build_minimal_dex(package_id: str) -> bytes:
    class_descriptor = f"L{package_id.replace('.', '/')}/MainActivity;"
    strings = [
        "Landroid/app/Activity;",
        class_descriptor,
        "V",
        "<init>"
    ]
    indexed_strings = sorted(list(enumerate(strings)), key=lambda x: x[1])
    sorted_strings = [x[1] for x in indexed_strings]
    string_remap = {orig_idx: new_idx for new_idx, (orig_idx, _) in enumerate(indexed_strings)}

    string_data_bytes = bytearray()
    string_offsets = []
    for s in sorted_strings:
        string_offsets.append(len(string_data_bytes))
        string_data_bytes.extend(uleb128(len(s)))
        string_data_bytes.extend(s.encode('utf-8'))
        string_data_bytes.append(0)

    type_activity_idx = string_remap[0]
    type_main_idx = string_remap[1]
    type_v_idx = string_remap[2]
    type_init_idx = string_remap[3]

    type_ids_bytes = struct.pack("<III", type_activity_idx, type_main_idx, type_v_idx)
    proto_ids_bytes = struct.pack("<III", type_v_idx, type_v_idx, 0)
    method_ids_bytes = struct.pack("<HHI", type_main_idx, 0, type_init_idx)
    code_item_bytes = struct.pack("<HHHHIIH", 1, 1, 0, 0, 0, 1, 0x000e)

    header_size = 0x70
    string_ids_off = header_size
    string_ids_size = len(sorted_strings)
    
    type_ids_off = string_ids_off + string_ids_size * 4
    type_ids_size = 3

    proto_ids_off = type_ids_off + type_ids_size * 4
    proto_ids_size = 1

    field_ids_off = proto_ids_off + proto_ids_size * 12
    field_ids_size = 0

    method_ids_off = field_ids_off
    method_ids_size = 1

    class_defs_off = method_ids_off + method_ids_size * 8
    class_defs_size = 1

    data_off = class_defs_off + class_defs_size * 32

    code_item_off = data_off
    pad0 = (4 - (len(code_item_bytes) % 4)) % 4
    code_item_padded = code_item_bytes + b"\x00" * pad0

    class_data_bytes = uleb128(0) + uleb128(0) + uleb128(1) + uleb128(0) + uleb128(0) + uleb128(0x10001) + uleb128(code_item_off)
    class_data_off = code_item_off + len(code_item_padded)

    string_data_off = class_data_off + len(class_data_bytes)
    string_ids_bytes = bytearray()
    for off in string_offsets:
        string_ids_bytes.extend(struct.pack("<I", string_data_off + off))

    class_def_bytes = struct.pack("<IIIIIIII", type_main_idx, 0x0001, type_activity_idx, 0, 0xFFFFFFFF, 0, class_data_off, 0)

    map_items = [
        (0x0000, string_ids_size, string_ids_off),
        (0x0001, type_ids_size, type_ids_off),
        (0x0002, proto_ids_size, proto_ids_off),
        (0x0005, method_ids_size, method_ids_off),
        (0x0006, class_defs_size, class_defs_off),
        (0x2001, 1, code_item_off),
        (0x2000, 1, class_data_off),
        (0x2002, string_ids_size, string_data_off),
        (0x1000, 1, 0)
    ]
    
    data_end = string_data_off + len(string_data_bytes)
    pad1 = (4 - (data_end % 4)) % 4
    map_off = data_end + pad1

    map_items[-1] = (0x1000, 1, map_off)

    map_bytes = struct.pack("<I", len(map_items))
    for item_type, size, off in map_items:
        map_bytes += struct.pack("<HHII", item_type, 0, size, off)

    total_file_size = map_off + len(map_bytes)

    magic = b"dex\n035\x00"
    header = bytearray(magic)
    header.extend(b"\x00" * 24)
    header.extend(struct.pack("<20I", 
        total_file_size,
        header_size,
        0x12345678,
        0, 0,
        map_off,
        string_ids_size, string_ids_off,
        type_ids_size, type_ids_off,
        proto_ids_size, proto_ids_off,
        field_ids_size, field_ids_off,
        method_ids_size, method_ids_off,
        class_defs_size, class_defs_off,
        total_file_size - data_off, data_off
    ))

    dex_body = header + string_ids_bytes + type_ids_bytes + proto_ids_bytes + method_ids_bytes + class_def_bytes + code_item_padded + class_data_bytes + string_data_bytes + (b"\x00" * pad1) + map_bytes

    sha1 = hashlib.sha1(dex_body[32:]).digest()
    dex_body[12:32] = sha1

    checksum = zlib.adler32(dex_body[12:]) & 0xffffffff
    dex_body[8:12] = struct.pack("<I", checksum)

    return bytes(dex_body)
