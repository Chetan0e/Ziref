import struct

class AXMLBuilder:
    def __init__(self):
        self.strings = []
        self.string_map = {}

    def get_string(self, s: str) -> int:
        if s not in self.string_map:
            self.string_map[s] = len(self.strings)
            self.strings.append(s)
        return self.string_map[s]

    def build_manifest(
        self,
        package_id: str,
        app_name: str,
        version_code: int = 1,
        version_name: str = "1.0.0",
        website_url: str = "https://ziref.app",
        permissions: list = None
    ) -> bytes:
        if permissions is None:
            permissions = []

        self.strings = []
        self.string_map = {}

        # Pre-register standard strings
        ns_prefix_idx = self.get_string("android")
        ns_uri_idx = self.get_string("http://schemas.android.com/apk/res/android")

        # Tags
        manifest_tag = self.get_string("manifest")
        uses_perm_tag = self.get_string("uses-permission")
        application_tag = self.get_string("application")
        activity_tag = self.get_string("activity")
        intent_filter_tag = self.get_string("intent-filter")
        action_tag = self.get_string("action")
        category_tag = self.get_string("category")

        # Attribute Names
        attr_package = self.get_string("package")
        attr_version_code = self.get_string("versionCode")
        attr_version_name = self.get_string("versionName")
        attr_name = self.get_string("name")
        attr_label = self.get_string("label")
        attr_exported = self.get_string("exported")
        attr_has_code = self.get_string("hasCode")
        attr_uses_cleartext = self.get_string("usesCleartextTraffic")

        # String Values
        val_package = self.get_string(package_id)
        val_version_name = self.get_string(version_name)
        val_app_name = self.get_string(app_name)
        val_main_activity = self.get_string(f"{package_id}.MainActivity")
        val_action_main = self.get_string("android.intent.action.MAIN")
        val_cat_launcher = self.get_string("android.intent.category.LAUNCHER")

        # Permission Strings
        perm_strings = [
            self.get_string("android.permission.INTERNET"),
            self.get_string("android.permission.ACCESS_NETWORK_STATE")
        ]
        for p in permissions:
            p_str = p if p.startswith("android.permission.") else f"android.permission.{p.upper()}"
            perm_strings.append(self.get_string(p_str))

        # Map attributes to Android resource IDs
        res_id_map = {
            attr_label: 0x01010001,
            attr_name: 0x01010003,
            attr_has_code: 0x0101000f,
            attr_exported: 0x01010010,
            attr_version_code: 0x0101021b,
            attr_version_name: 0x0101021c,
            attr_uses_cleartext: 0x0101028a
        }

        # Build Resource Map
        res_map_data = bytearray()
        for idx in range(len(self.strings)):
            res_id = res_id_map.get(idx, 0)
            res_map_data.extend(struct.pack("<I", res_id))

        res_map_chunk = struct.pack("<HHI", 0x0180, 0x0008, 8 + len(res_map_data)) + res_map_data

        # Build String Pool Chunk
        string_offsets = bytearray()
        string_bytes = bytearray()
        current_offset = 0

        for s in self.strings:
            string_offsets.extend(struct.pack("<I", current_offset))
            encoded = s.encode("utf-16le")
            char_len = len(s)
            s_data = struct.pack("<H", char_len) + encoded + b"\x00\x00"
            string_bytes.extend(s_data)
            current_offset += len(s_data)

        pad_len = (4 - (len(string_bytes) % 4)) % 4
        string_bytes.extend(b"\x00" * pad_len)

        header_size = 28
        strings_start = header_size + len(string_offsets)
        sp_total_size = strings_start + len(string_bytes)

        string_pool_chunk = struct.pack(
            "<HHIIIIII",
            0x0001,
            header_size,
            sp_total_size,
            len(self.strings),
            0,
            0,
            strings_start,
            0
        ) + string_offsets + string_bytes

        def pack_attr(name_idx, val_str_idx, data_type, data_val, ns_idx=ns_uri_idx):
            return struct.pack("<IIIHBB I", ns_idx, name_idx, val_str_idx if val_str_idx != 0xFFFFFFFF else 0xFFFFFFFF, 8, 0, data_type, data_val)

        def pack_start_elem(tag_idx, line_num, attrs_bytes):
            attr_count = len(attrs_bytes) // 20
            elem_len = 0x0024 + len(attrs_bytes)
            header_bytes = struct.pack("<HHIIIIIHHHHHH",
                0x0102, 0x0010, elem_len, line_num, 0xFFFFFFFF, 0xFFFFFFFF, tag_idx,
                0x0014, 0x0014, attr_count, 0, 0, 0
            )
            return header_bytes + attrs_bytes

        def pack_end_elem(tag_idx, line_num):
            return struct.pack("<HHIIIII", 0x0103, 0x0010, 0x0018, line_num, 0xFFFFFFFF, 0xFFFFFFFF, tag_idx)

        body = bytearray()

        # 1. Start Namespace
        body.extend(struct.pack("<HHIIIII", 0x0100, 0x0010, 0x0018, 1, 0xFFFFFFFF, ns_prefix_idx, ns_uri_idx))

        # 2. Start <manifest>
        manifest_attrs = bytearray()
        manifest_attrs.extend(pack_attr(attr_package, val_package, 0x03, val_package, ns_idx=0xFFFFFFFF))
        manifest_attrs.extend(pack_attr(attr_version_code, 0xFFFFFFFF, 0x10, version_code))
        manifest_attrs.extend(pack_attr(attr_version_name, val_version_name, 0x03, val_version_name))
        body.extend(pack_start_elem(manifest_tag, 1, manifest_attrs))

        # 3. <uses-permission> tags
        for perm_str_idx in perm_strings:
            perm_attrs = pack_attr(attr_name, perm_str_idx, 0x03, perm_str_idx)
            body.extend(pack_start_elem(uses_perm_tag, 2, perm_attrs))
            body.extend(pack_end_elem(uses_perm_tag, 2))

        # 4. Start <application>
        app_attrs = bytearray()
        app_attrs.extend(pack_attr(attr_label, val_app_name, 0x03, val_app_name))
        app_attrs.extend(pack_attr(attr_has_code, 0xFFFFFFFF, 0x12, 1))
        app_attrs.extend(pack_attr(attr_uses_cleartext, 0xFFFFFFFF, 0x12, 1))
        body.extend(pack_start_elem(application_tag, 5, app_attrs))

        # 5. Start <activity>
        act_attrs = bytearray()
        act_attrs.extend(pack_attr(attr_name, val_main_activity, 0x03, val_main_activity))
        act_attrs.extend(pack_attr(attr_exported, 0xFFFFFFFF, 0x12, 1))
        body.extend(pack_start_elem(activity_tag, 6, act_attrs))

        # 6. Start <intent-filter>
        body.extend(pack_start_elem(intent_filter_tag, 7, b""))

        # <action android:name="android.intent.action.MAIN"/>
        act_main_attr = pack_attr(attr_name, val_action_main, 0x03, val_action_main)
        body.extend(pack_start_elem(action_tag, 8, act_main_attr))
        body.extend(pack_end_elem(action_tag, 8))

        # <category android:name="android.intent.category.LAUNCHER"/>
        cat_launch_attr = pack_attr(attr_name, val_cat_launcher, 0x03, val_cat_launcher)
        body.extend(pack_start_elem(category_tag, 9, cat_launch_attr))
        body.extend(pack_end_elem(category_tag, 9))

        # End <intent-filter>
        body.extend(pack_end_elem(intent_filter_tag, 7))

        # End <activity>
        body.extend(pack_end_elem(activity_tag, 6))

        # End <application>
        body.extend(pack_end_elem(application_tag, 5))

        # End <manifest>
        body.extend(pack_end_elem(manifest_tag, 1))

        # End Namespace
        body.extend(struct.pack("<HHIIIII", 0x0101, 0x0010, 0x0018, 1, 0xFFFFFFFF, ns_prefix_idx, ns_uri_idx))

        total_axml_size = 8 + len(string_pool_chunk) + len(res_map_chunk) + len(body)
        axml_header = struct.pack("<HHI", 0x0003, 0x0008, total_axml_size)

        return axml_header + string_pool_chunk + res_map_chunk + body

axml_builder = AXMLBuilder()
