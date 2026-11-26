import hashlib
import struct
import tempfile
import unittest
from pathlib import Path

import importlib.util

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "audit-earth-firmware.py"
SPEC = importlib.util.spec_from_file_location("audit_earth_firmware", MODULE_PATH)
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)
SparseImageReader = AUDIT.SparseImageReader
audit_logical_partitions = AUDIT.audit_logical_partitions


def sparse_image(expanded: bytes, block_size: int = 4096) -> bytes:
    if len(expanded) % block_size:
        raise ValueError("expanded image must be block aligned")
    blocks = len(expanded) // block_size
    chunk = struct.pack("<2H2I", 0xCAC1, 0, blocks, 12 + len(expanded)) + expanded
    header = struct.pack("<I4H4I", 0xED26FF3A, 1, 0, 28, 12,
                         block_size, blocks, 1, 0)
    return header + chunk


def build_super_image(corrupt_geometry_checksum: bool = False) -> bytes:
    expanded = bytearray(65536)

    geometry = bytearray(struct.pack(
        "<II32sIII", 0x616C4467, 52, bytes(32), 65536, 1, 4096
    ))
    geometry[8:40] = hashlib.sha256(geometry).digest()
    if corrupt_geometry_checksum:
        geometry[8] ^= 0xFF
    expanded[4096:4096 + 52] = geometry

    partition = struct.pack("<36sIIII", b"system", 0, 0, 1, 0)
    extent = struct.pack("<QIQI", 8, 0, 4096, 0)
    group = struct.pack("<36sIQ", b"default", 0, 0)
    device = struct.pack("<QIIQ36sI", 0, 0, 0, 7_516_192_768, b"super", 0)
    tables = partition + extent + group + device

    header = bytearray(128)
    struct.pack_into("<IHHI", header, 0, 0x414C5030, 10, 0, 128)
    struct.pack_into("<I", header, 44, len(tables))
    header[48:80] = hashlib.sha256(tables).digest()
    descriptors = (
        (80, 0, 1, 52),
        (92, 52, 1, 24),
        (104, 76, 1, 48),
        (116, 124, 1, 64),
    )
    for offset, table_offset, count, entry_size in descriptors:
        struct.pack_into("<III", header, offset, table_offset, count, entry_size)
    header[12:44] = hashlib.sha256(header).digest()

    metadata_base = 2 * 4096
    expanded[metadata_base:metadata_base + 128] = header
    expanded[metadata_base + 128:metadata_base + 128 + len(tables)] = tables
    return sparse_image(bytes(expanded))


class SparseReaderTests(unittest.TestCase):
    def test_reads_fill_and_dont_care_chunks_as_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mixed.sparse"
            raw = b"ABCD"
            fill = b"\x11\x22\x33\x44"
            chunks = [
                struct.pack("<2H2I", 0xCAC1, 0, 1, 16) + raw,
                struct.pack("<2H2I", 0xCAC2, 0, 2, 16) + fill,
                struct.pack("<2H2I", 0xCAC3, 0, 1, 12),
            ]
            header = struct.pack("<I4H4I", 0xED26FF3A, 1, 0, 28, 12, 4, 4, 3, 0)
            path.write_bytes(header + b"".join(chunks))
            reader = SparseImageReader(path)
            try:
                self.assertEqual(reader.read_at(0, 16),
                                 raw + fill + fill + bytes(4))
            finally:
                reader.close()

    def test_reads_valid_liblp_metadata_at_primary_offset(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "super.sparse"
            path.write_bytes(build_super_image())
            result = audit_logical_partitions(path)
            self.assertEqual(result["status"], "parsed", result)
            self.assertEqual(result["partition_count"], 1)
            self.assertEqual(result["partitions"][0]["name"], "system")
            self.assertEqual(result["partitions"][0]["size_bytes"], 4096)
            self.assertEqual(result["block_devices"][0]["partition_name"], "super")

    def test_rejects_corrupt_geometry_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad-super.sparse"
            path.write_bytes(build_super_image(corrupt_geometry_checksum=True))
            result = audit_logical_partitions(path)
            self.assertEqual(result["status"], "geometry_checksum_mismatch")


if __name__ == "__main__":
    unittest.main()
