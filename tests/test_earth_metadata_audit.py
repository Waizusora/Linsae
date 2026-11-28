import struct
import tempfile
import unittest
import zlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from earth_metadata_audit import audit_gpt, audit_vbmeta_descriptors, compare_gpt_scatter


def make_gpt() -> bytes:
    sector = 512
    blob = bytearray(34 * sector)
    entries = bytearray(128 * 128)
    # One ordinary GPT partition occupying LBAs 3 through 5.
    row = bytearray(128)
    row[:16] = bytes.fromhex("28732ac11ff8d211ba4b00a0c93ec93b")
    row[16:32] = bytes.fromhex("00112233445566778899aabbccddeeff")
    struct.pack_into("<QQQ", row, 32, 3, 5, 0)
    row[56:68] = "system".encode("utf-16le")
    entries[:128] = row
    blob[2 * sector:2 * sector + len(entries)] = entries
    header = bytearray(92)
    header[:8] = b"EFI PART"
    struct.pack_into("<III", header, 8, 0x00010000, 92, 0)
    struct.pack_into("<QQQQ", header, 24, 1, 33, 3, 32)
    header[56:72] = bytes.fromhex("00112233445566778899aabbccddeeff")
    struct.pack_into("<QIII", header, 72, 2, 128, 128, zlib.crc32(entries) & 0xffffffff)
    struct.pack_into("<I", header, 16, zlib.crc32(header) & 0xffffffff)
    blob[sector:sector + 92] = header
    return bytes(blob)


def make_vbmeta_chain() -> bytes:
    name = b"vbmeta_system"
    key = b"public-key-placeholder"
    following = 76 + len(name) + len(key)
    descriptor = struct.pack(">QQ4I", 4, following, 2, len(name), len(key), 0)
    descriptor += bytes(60) + name + key
    header = bytearray(256)
    header[:4] = b"AVB0"
    struct.pack_into(">II", header, 4, 1, 0)
    struct.pack_into(">QQ", header, 12, 0, len(descriptor))
    struct.pack_into(">I", header, 28, 1)
    struct.pack_into(">QQ", header, 96, 0, len(descriptor))
    struct.pack_into(">Q", header, 112, 7)
    struct.pack_into(">II", header, 120, 0, 2)
    return bytes(header) + descriptor



def make_mediatek_pgpt() -> bytes:
    blob = bytearray(1024 + 128 * 128)
    header = bytearray(92)
    header[:8] = b"EFI PART"
    struct.pack_into("<III", header, 8, 0x00010000, 92, 0)
    # Match the real firmware header: a nominal 128-entry table at LBA 2,
    # but an invalid usable-LBA interval and zero header CRC.
    struct.pack_into("<QQQQ", header, 24, 1, 64, 64, 0)
    struct.pack_into("<QIII", header, 72, 2, 128, 128, 0)
    blob[512:512 + 92] = header
    for index, (name, first, last) in enumerate((("misc", 64, 1087), ("userdata", 0, 0))):
        row = bytearray(128)
        row[:32] = ("gpt" + f"{index + 1:029x}").encode("ascii")
        struct.pack_into("<QQQ", row, 32, first, last, 0)
        row[56:56 + len(name.encode("utf-16le"))] = name.encode("utf-16le")
        blob[1024 + index * 128:1024 + (index + 1) * 128] = row
    return bytes(blob)

class GptAuditTests(unittest.TestCase):
    def test_parses_valid_gpt_and_partition_geometry(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "PGPT_EMMC"
            path.write_bytes(make_gpt())
            result = audit_gpt(path)
            self.assertEqual(result["status"], "parsed", result)
            self.assertEqual(result["partition_count"], 1)
            self.assertEqual(result["partitions"][0]["name"], "system")
            self.assertEqual(result["partitions"][0]["start_bytes"], 1536)
            self.assertEqual(result["partitions"][0]["size_bytes"], 1536)


    def test_parses_mediatek_pgpt_and_marks_unmapped_partition(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "PGPT_EMMC"
            path.write_bytes(make_mediatek_pgpt())
            result = audit_gpt(path)
            self.assertEqual(result["status"], "mediatek_pgpt_parsed", result)
            self.assertEqual(result["partition_count"], 2)
            self.assertEqual(result["partitions"][0]["name"], "misc")
            self.assertEqual(result["partitions"][0]["start_bytes"], 32768)
            self.assertEqual(result["unmapped_partitions"], ["userdata"])
            comparison = compare_gpt_scatter(result, {"status": "parsed", "partitions": [
                {"partition_name": "misc", "linear_start_addr": "0x8000", "partition_size": "0x80000"},
                {"partition_name": "userdata", "linear_start_addr": "0x100000", "partition_size": "0x200000"}
            ]})
            self.assertEqual(comparison["matched_names"], 1)
            self.assertEqual(comparison["unverified_partitions"], ["userdata"])


    def test_non_downloadable_sentinel_entries_remain_unverified_without_blocking(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "PGPT_EMMC"
            blob = bytearray(make_mediatek_pgpt())
            for index, (name, first, last) in enumerate((
                ("otp", 0, 88064), ("flashinfo", 0, 32768)
            ), start=2):
                row = bytearray(128)
                row[:32] = ("gpt" + f"{index + 1:029x}").encode("ascii")
                struct.pack_into("<QQQ", row, 32, first, last, 0)
                encoded = name.encode("utf-16le")
                row[56:56 + len(encoded)] = encoded
                blob[1024 + index * 128:1024 + (index + 1) * 128] = row
            path.write_bytes(blob)
            result = audit_gpt(path)
            comparison = compare_gpt_scatter(result, {"status": "parsed", "partitions": [
                {"partition_name": "misc", "linear_start_addr": "0x8000", "partition_size": "0x80000", "is_download": "true"},
                {"partition_name": "userdata", "linear_start_addr": "0x100000", "partition_size": "0x200000", "is_download": "true"},
                {"partition_name": "otp", "linear_start_addr": "0xFFFF01d8", "partition_size": "0x2b00000", "is_download": "false"},
                {"partition_name": "flashinfo", "linear_start_addr": "0xFFFF0080", "partition_size": "0x1000000", "is_download": "false"}
            ]})
            self.assertEqual(comparison["unverified_partitions"], ["flashinfo", "otp", "userdata"])
            self.assertEqual(comparison["blocking_unverified_partitions"], ["userdata"])
            reasons = {x["partition"]: x["reason"] for x in comparison["unverified_partition_details"]}
            self.assertEqual(reasons["otp"], "non_physical_scatter_sentinel")
            self.assertEqual(reasons["flashinfo"], "non_physical_scatter_sentinel")
            self.assertEqual(reasons["userdata"], "required_geometry_unverified")

    def test_rejects_corrupt_gpt_header_crc(self):
        blob = bytearray(make_gpt())
        blob[512 + 16] ^= 0x01
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad-gpt"
            path.write_bytes(blob)
            self.assertEqual(audit_gpt(path)["status"], "gpt_header_crc_mismatch")

    def test_crc_failure_includes_header_diagnostics(self):
        blob = bytearray(make_gpt())
        blob[512 + 16] ^= 0x01
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad-gpt"
            path.write_bytes(blob)
            result = audit_gpt(path)
            self.assertEqual(result["status"], "gpt_header_crc_mismatch")
            self.assertEqual(result["header_offset"], 512)
            self.assertEqual(len(result["expected_crc32"]), 8)
            self.assertEqual(result["signature_offsets"], [512])


class AvbAuditTests(unittest.TestCase):
    def test_parses_chain_partition_without_exporting_key_material(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vbmeta.img"
            path.write_bytes(make_vbmeta_chain())
            result = audit_vbmeta_descriptors(path)
            self.assertEqual(result["status"], "parsed", result)
            self.assertEqual(result["descriptor_count"], 1)
            self.assertEqual(result["rollback_index_location"], 2)
            self.assertEqual(result["flags"], 0)
            self.assertEqual(result["chain_partitions"][0]["partition_name"], "vbmeta_system")
            self.assertNotIn("public-key-placeholder", str(result))

    def test_rejects_descriptor_outside_declared_area(self):
        blob = bytearray(make_vbmeta_chain())
        struct.pack_into(">Q", blob, 96, 0x1000)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad-vbmeta.img"
            path.write_bytes(blob)
            self.assertEqual(audit_vbmeta_descriptors(path)["status"], "invalid_vbmeta_range")


if __name__ == "__main__":
    unittest.main()
