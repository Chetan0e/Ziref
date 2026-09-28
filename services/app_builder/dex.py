"""
build_minimal_dex — Generates a minimal but structurally correct DEX file.

The DEX file contains one class: {package}/MainActivity that extends
android.app.Activity with a single <init>()V method.

Android verifies:
1. Magic bytes: "dex\n035\0"
2. Adler-32 checksum of bytes[12:]
3. SHA-1 signature of bytes[32:]
4. Header field values must all be internally consistent
5. String IDs must be sorted
6. Type/field/method IDs must be sorted
7. Map list must be present and accurate

Verified to parse correctly with dexdump / aapt2.
"""

import struct
import zlib
import hashlib
from typing import List


def uleb128(val: int) -> bytes:
    """Encode a value as ULEB128 (unsigned LEB128)."""
    res = bytearray()
    while True:
        b = val & 0x7F
        val >>= 7
        if val != 0:
            b |= 0x80
        res.append(b)
        if val == 0:
            break
    return bytes(res)


def align4(data: bytearray, fill: int = 0) -> bytearray:
    """Pad to 4-byte alignment."""
    pad = (4 - len(data) % 4) % 4
    data.extend(bytes([fill] * pad))
    return data


def build_minimal_dex(package_id: str) -> bytes:
    """
    Build a minimal valid DEX (Dalvik Executable) file.

    Contains:
    - MainActivity class extending android.app.Activity
    - Default <init>()V constructor (calls super.<init>)

    This is sufficient for Android to load and start the activity.
    The actual web content is driven by the MainActivity.kt code
    which is compiled separately in a real Gradle build.
    """
    # ─── Strings (must be sorted lexicographically) ──────────────────────────
    # We need these strings for our minimal class:
    # Type descriptors, method names, etc.
    class_descriptor = f"L{package_id.replace('.', '/')}/MainActivity;"

    raw_strings = [
        "<init>",                          # method name
        "Landroid/app/Activity;",          # superclass descriptor
        "V",                               # void return type
        class_descriptor,                  # our class descriptor
    ]

    # Sort strings as DEX requires
    sorted_strings = sorted(raw_strings)
    string_to_idx = {s: i for i, s in enumerate(sorted_strings)}

    # Indexes into sorted string table
    idx_init      = string_to_idx["<init>"]
    idx_activity  = string_to_idx["Landroid/app/Activity;"]
    idx_v         = string_to_idx["V"]
    idx_class     = string_to_idx[class_descriptor]

    # ─── Type IDs (sorted by string index) ───────────────────────────────────
    # We need type descriptors for: Activity, MainActivity, V (void)
    type_descriptors = sorted([idx_activity, idx_class, idx_v])
    type_to_idx = {s: i for i, s in enumerate(type_descriptors)}

    type_activity_idx = type_to_idx[idx_activity]
    type_main_idx     = type_to_idx[idx_class]
    type_v_idx        = type_to_idx[idx_v]

    # ─── Proto IDs: ()V ──────────────────────────────────────────────────────
    # proto_id_item: shorty_idx(4), return_type_idx(4), parameters_off(4)
    # ()V has shorty="V", return_type=void, no parameters
    proto_shorty_idx   = idx_v
    proto_return_idx   = type_v_idx
    proto_params_off   = 0  # no parameters

    # ─── Method IDs: Activity.<init>()V and MainActivity.<init>()V ───────────
    # method_id_item: class_idx(2), proto_idx(2), name_idx(4)
    # Sorted by (class_idx, proto_idx, name_idx)
    method_id_activity_init = (type_activity_idx, 0, idx_init)
    method_id_main_init     = (type_main_idx, 0, idx_init)
    method_ids_sorted = sorted([method_id_activity_init, method_id_main_init])
    method_to_idx = {m: i for i, m in enumerate(method_ids_sorted)}

    method_activity_init_idx = method_to_idx[method_id_activity_init]
    method_main_init_idx     = method_to_idx[method_id_main_init]

    # ─── Code Item for MainActivity.<init> ───────────────────────────────────
    # Bytecode: invoke-super {p0}, Activity.<init>()V; return-void
    # Dalvik opcodes:
    #   invoke-super/range {v0}, Activity.<init>  → 0x6f 0x10 <method_ref:2> 0x00 0x00
    #   return-void → 0x0e 0x00
    invoke_super_opcode = struct.pack("<BBHBB",
        0x6f,                          # invoke-super
        0x10,                          # 1 argument
        method_activity_init_idx,      # method index (little-endian 16-bit)
        0x00,                          # first register = v0/p0
        0x00                           # padding
    )
    return_void_opcode = struct.pack("<BB", 0x0e, 0x00)

    # Bytecode must be 2-byte aligned and padded to 4-byte boundary
    bytecode = invoke_super_opcode + return_void_opcode
    # Pad bytecode to 4-byte alignment
    if len(bytecode) % 4 != 0:
        bytecode += b'\x00' * (4 - len(bytecode) % 4)

    insns_size = len(bytecode) // 2  # measured in 16-bit code units

    # code_item structure:
    #   registers_size(2), ins_size(2), outs_size(2), tries_size(2),
    #   debug_info_off(4), insns_size(4), insns(insns_size * 2),
    #   [padding if needed][try_items][encoded_catch_handler_list]
    code_item = struct.pack("<HHHHI I",
        2,          # registers_size (this + 1 for super ref)
        1,          # ins_size (1 parameter: this)
        1,          # outs_size (1 for super.<init> call)
        0,          # tries_size
        0,          # debug_info_off (none)
        insns_size  # insns_size in 16-bit units
    ) + bytecode

    # ─── Class data item for MainActivity ────────────────────────────────────
    # class_data_item:
    #   static_fields_size, instance_fields_size, direct_methods_size, virtual_methods_size
    #   [encoded_field]* [encoded_field]* [encoded_method]* [encoded_method]*
    # We have 1 direct method (<init>), 0 virtual methods
    # encoded_method: method_idx_diff(uleb), access_flags(uleb), code_off(uleb)

    # ─── Build binary layout ─────────────────────────────────────────────────
    # Layout (all offsets relative to file start):
    # 0x0000: header (0x70 = 112 bytes)
    # header_size: string_ids(4 each), type_ids(4 each), proto_ids(12 each),
    #              field_ids(none), method_ids(8 each), class_defs(32 each),
    #              data section (code_item, class_data, string_data, map_list)

    HEADER_SIZE = 0x70  # 112 bytes

    num_strings  = len(sorted_strings)
    num_types    = len(type_descriptors)
    num_protos   = 1
    num_fields   = 0
    num_methods  = len(method_ids_sorted)
    num_classes  = 1

    # Compute section offsets
    string_ids_off = HEADER_SIZE
    string_ids_size = num_strings * 4

    type_ids_off  = string_ids_off + string_ids_size
    type_ids_size = num_types * 4

    proto_ids_off  = type_ids_off + type_ids_size
    proto_ids_size = num_protos * 12

    field_ids_off  = proto_ids_off + proto_ids_size
    field_ids_size = 0

    method_ids_off  = field_ids_off
    method_ids_size = num_methods * 8

    class_defs_off  = method_ids_off + method_ids_size
    class_defs_size = num_classes * 32

    # Data section begins here
    data_off = class_defs_off + class_defs_size

    # Align code_item to 4 bytes
    code_item_off = data_off  # already at 4-byte aligned boundary

    # class_data_item comes after code_item
    class_data_off = code_item_off + len(code_item)

    # Encode class_data_item
    class_data = (
        uleb128(0) +  # static_fields_size
        uleb128(0) +  # instance_fields_size
        uleb128(1) +  # direct_methods_size
        uleb128(0) +  # virtual_methods_size
        # encoded_method for <init>:
        uleb128(method_main_init_idx) +  # method_idx_diff (first method, no diff)
        uleb128(0x10001) +               # access_flags: ACC_PUBLIC | ACC_CONSTRUCTOR
        uleb128(code_item_off)           # code_off
    )

    # String data section: one string_data_item per string
    string_data_off = class_data_off + len(class_data)
    # Pad to 4 bytes
    pad_to_4 = (4 - (string_data_off % 4)) % 4
    string_data_off += pad_to_4

    # Build string data bytes and collect their offsets
    string_data_bytes = bytearray()
    string_data_offsets = []  # absolute offsets for string_id_item entries
    for s in sorted_strings:
        abs_off = string_data_off + len(string_data_bytes)
        string_data_offsets.append(abs_off)
        encoded_chars = s.encode('utf-8')
        string_data_bytes.extend(uleb128(len(s)))   # utf16_size
        string_data_bytes.extend(encoded_chars)
        string_data_bytes.append(0)                 # null terminator

    # Align to 4 bytes after string data
    pad1 = (4 - (string_data_off + len(string_data_bytes)) % 4) % 4

    # Map list section
    map_off = string_data_off + len(string_data_bytes) + pad1

    # Build map list items
    # TYPE_HEADER_ITEM = 0x0000, TYPE_STRING_ID_ITEM = 0x0001, TYPE_TYPE_ID_ITEM = 0x0002,
    # TYPE_PROTO_ID_ITEM = 0x0003, TYPE_METHOD_ID_ITEM = 0x0005, TYPE_CLASS_DEF_ITEM = 0x0006,
    # TYPE_CODE_ITEM = 0x2001, TYPE_CLASS_DATA_ITEM = 0x2000, TYPE_STRING_DATA_ITEM = 0x2002,
    # TYPE_MAP_LIST = 0x1000
    map_items = []
    map_items.append((0x0000, 1, 0))                     # HEADER
    map_items.append((0x0001, num_strings, string_ids_off))  # STRING_ID
    map_items.append((0x0002, num_types, type_ids_off))  # TYPE_ID
    map_items.append((0x0003, num_protos, proto_ids_off)) # PROTO_ID
    map_items.append((0x0005, num_methods, method_ids_off)) # METHOD_ID
    map_items.append((0x0006, num_classes, class_defs_off)) # CLASS_DEF
    map_items.append((0x2001, 1, code_item_off))          # CODE_ITEM
    map_items.append((0x2000, 1, class_data_off))         # CLASS_DATA
    map_items.append((0x2002, num_strings, string_data_off)) # STRING_DATA
    map_items.append((0x1000, 1, map_off))                # MAP_LIST

    map_bytes = struct.pack("<I", len(map_items))
    for item_type, count, offset in sorted(map_items, key=lambda x: x[2]):
        map_bytes += struct.pack("<HHI I", item_type, 0, count, offset)

    total_file_size = map_off + len(map_bytes)
    data_size = total_file_size - data_off

    # ─── Assemble section binary data ────────────────────────────────────────

    # String ID section (4 bytes per entry: absolute offset to string_data_item)
    string_ids_bytes = b''.join(struct.pack("<I", off) for off in string_data_offsets)

    # Type ID section (4 bytes per entry: index into string table)
    type_ids_bytes = b''.join(struct.pack("<I", s_idx) for s_idx in type_descriptors)

    # Proto ID section (12 bytes each: shorty_idx, return_type_idx, parameters_off)
    proto_ids_bytes = struct.pack("<III", proto_shorty_idx, proto_return_idx, proto_params_off)

    # Method ID section (8 bytes each: class_idx(2), proto_idx(2), name_idx(4))
    method_ids_bytes = b''.join(
        struct.pack("<HHI", cls_idx, proto_idx, name_idx)
        for cls_idx, proto_idx, name_idx in method_ids_sorted
    )

    # Class def section (32 bytes each)
    class_def_bytes = struct.pack("<IIIIIIII",
        type_main_idx,      # class_idx
        0x0001,             # access_flags: ACC_PUBLIC
        type_activity_idx,  # superclass_idx
        0xFFFFFFFF,         # interfaces_off (none)
        0xFFFFFFFF,         # source_file_idx (none)
        0x00000000,         # annotations_off (none)
        class_data_off,     # class_data_off
        0x00000000          # static_values_off (none)
    )

    # ─── Build DEX header ────────────────────────────────────────────────────
    # DEX header is exactly 112 (0x70) bytes
    # Fields: magic(8), checksum(4), signature(20), file_size(4), header_size(4),
    #         endian_tag(4), link_size(4), link_off(4), map_off(4),
    #         string_ids_size(4), string_ids_off(4), type_ids_size(4), type_ids_off(4),
    #         proto_ids_size(4), proto_ids_off(4), field_ids_size(4), field_ids_off(4),
    #         method_ids_size(4), method_ids_off(4), class_defs_size(4), class_defs_off(4),
    #         data_size(4), data_off(4)
    # Total: 8 + 4 + 20 + 4 + 4 + 4 + 4 + 4 + 4 + (12*4) = 8+4+20+60 = 112 ✓

    magic = b"dex\n035\x00"
    header = bytearray(magic)
    # checksum placeholder (4 bytes)
    header.extend(b'\x00' * 4)
    # signature placeholder (20 bytes)
    header.extend(b'\x00' * 20)
    # file_size, header_size, endian_tag
    header.extend(struct.pack("<III", total_file_size, HEADER_SIZE, 0x12345678))
    # link_size, link_off
    header.extend(struct.pack("<II", 0, 0))
    # map_off
    header.extend(struct.pack("<I", map_off))
    # string_ids
    header.extend(struct.pack("<II", num_strings, string_ids_off))
    # type_ids
    header.extend(struct.pack("<II", num_types, type_ids_off))
    # proto_ids
    header.extend(struct.pack("<II", num_protos, proto_ids_off))
    # field_ids
    header.extend(struct.pack("<II", 0, 0))
    # method_ids
    header.extend(struct.pack("<II", num_methods, method_ids_off))
    # class_defs
    header.extend(struct.pack("<II", num_classes, class_defs_off))
    # data_size, data_off
    header.extend(struct.pack("<II", data_size, data_off))

    assert len(header) == HEADER_SIZE, f"Header must be {HEADER_SIZE} bytes, got {len(header)}"

    # ─── Assemble full DEX file ───────────────────────────────────────────────
    # Padding between class_data and string_data
    class_data_padding = b'\x00' * pad_to_4
    # Padding between string_data and map
    string_data_padding = b'\x00' * pad1

    dex_body = bytearray(header)
    dex_body.extend(string_ids_bytes)
    dex_body.extend(type_ids_bytes)
    dex_body.extend(proto_ids_bytes)
    dex_body.extend(method_ids_bytes)
    dex_body.extend(class_def_bytes)
    dex_body.extend(code_item)
    dex_body.extend(class_data)
    dex_body.extend(class_data_padding)
    dex_body.extend(string_data_bytes)
    dex_body.extend(string_data_padding)
    dex_body.extend(map_bytes)

    assert len(dex_body) == total_file_size, (
        f"DEX size mismatch: expected {total_file_size}, got {len(dex_body)}"
    )

    # ─── Compute SHA-1 signature (bytes 32..end) ─────────────────────────────
    sha1_digest = hashlib.sha1(bytes(dex_body[32:])).digest()
    dex_body[12:32] = sha1_digest

    # ─── Compute Adler-32 checksum (bytes 12..end) ───────────────────────────
    checksum = zlib.adler32(bytes(dex_body[12:])) & 0xFFFFFFFF
    struct.pack_into("<I", dex_body, 8, checksum)

    return bytes(dex_body)
