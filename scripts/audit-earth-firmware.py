#!/usr/bin/env python3
"""Offline structural audit for the Redmi 12C earth Fastboot ROM."""
from __future__ import annotations

import argparse
import json
import re
import struct
import tarfile
import sys
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))
from earth_metadata_audit import audit_gpt, audit_vbmeta_descriptors, compare_gpt_scatter

SPARSE_MAGIC = 0xED26FF3A
DTBO_MAGIC = 0xD7B7AB1E


def read_scatter(archive: Path) -> dict:
    candidates = []
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar.getmembers():
            name = PurePosixPath(member.name).name.lower()
            if member.isfile() and "scatter" in name and name.endswith((".txt", ".cfg")):
                candidates.append(member)
        if not candidates:
            return {"status": "not_found", "partitions": []}
        member = max(candidates, key=lambda m: m.size)
        if member.size > 8 * 1024 * 1024:
            return {"status": "rejected_oversize", "path": member.name, "partitions": []}
        stream = tar.extractfile(member)
        if stream is None:
            return {"status": "unreadable", "path": member.name, "partitions": []}
        content = stream.read().decode("utf-8", "replace")

    partitions = []
    current = None
    for line in content.splitlines():
        match = re.match(r"\s*-\s*partition_index\s*:\s*(.*?)\s*$", line)
        if match:
            if current:
                partitions.append(current)
            current = {"partition_index": match.group(1)}
            continue
        match = re.match(
            r"\s*(partition_name|file_name|linear_start_addr|physical_start_addr|partition_size|is_download|type|region)\s*:\s*(.*?)\s*$",
            line,
        )
        if match:
            if current is None:
                current = {}
            current[match.group(1)] = match.group(2)
    if current:
        partitions.append(current)
    return {
        "status": "parsed",
        "path": member.name,
        "partition_count": len(partitions),
        "partitions": partitions,
    }

def audit_boot(path: Path) -> dict:
    with path.open("rb") as f:
        data = f.read(48)
    if len(data) < 48 or data[:8] != b"ANDROID!":
        return {"status": "unknown_header", "size_bytes": path.stat().st_size}
    kernel_size = struct.unpack_from("<I", data, 8)[0]
    ramdisk_size = struct.unpack_from("<I", data, 16)[0]
    page_size = struct.unpack_from("<I", data, 36)[0]
    header_version = struct.unpack_from("<I", data, 40)[0]
    os_version = struct.unpack_from("<I", data, 44)[0]
    return {
        "status": "recognized",
        "size_bytes": path.stat().st_size,
        "magic": "ANDROID!",
        "kernel_size": kernel_size,
        "ramdisk_size": ramdisk_size,
        "page_size": page_size,
        "header_version": header_version,
        "os_version_field": os_version,
    }

def audit_dtbo(path: Path) -> dict:
    with path.open("rb") as f:
        data = f.read(32)
    if len(data) < 32:
        return {"status": "truncated", "size_bytes": path.stat().st_size}
    if data[:4] != bytes.fromhex("d7b7ab1e"):
        return {
            "status": "unknown_header",
            "size_bytes": path.stat().st_size,
            "magic_hex": "0x" + data[:4].hex(),
        }
    magic, total, header, entry_size, count, entries_offset, page_size, version = struct.unpack(">8I", data)
    return {
        "status": "recognized",
        "size_bytes": path.stat().st_size,
        "magic": f"0x{magic:08x}",
        "total_size": total,
        "header_size": header,
        "entry_size": entry_size,
        "entry_count": count,
        "entries_offset": entries_offset,
        "page_size": page_size,
        "version": version,
    }

def audit_vbmeta(path: Path) -> dict:
    with path.open("rb") as f:
        data = f.read(256)
    if len(data) < 256 or data[:4] != b"AVB0":
        return {"status": "unknown_header", "size_bytes": path.stat().st_size}
    auth_size, aux_size = struct.unpack_from(">QQ", data, 12)
    algorithm = struct.unpack_from(">I", data, 28)[0]
    rollback = struct.unpack_from(">Q", data, 112)[0]
    flags = struct.unpack_from(">I", data, 120)[0]
    rollback_location = struct.unpack_from(">I", data, 124)[0]
    release = data[128:176].split(b"\0", 1)[0].decode("ascii", "replace")
    return {
        "status": "recognized", "size_bytes": path.stat().st_size, "magic": "AVB0",
        "authentication_data_block_size": auth_size, "auxiliary_data_block_size": aux_size,
        "algorithm_type": algorithm, "rollback_index": rollback, "flags": flags,
        "rollback_index_location": rollback_location, "release_string": release,
    }


def audit_sparse(path: Path) -> dict:
    with path.open("rb") as f:
        data = f.read(28)
    if len(data) < 28:
        return {"status": "too_small", "size_bytes": path.stat().st_size}
    magic, major, minor, file_hdr, chunk_hdr, block_size, total_blocks, total_chunks, checksum = struct.unpack("<I4H4I", data)
    if magic != SPARSE_MAGIC:
        return {"status": "not_android_sparse", "size_bytes": path.stat().st_size, "magic_hex": f"0x{magic:08x}"}
    return {
        "status": "android_sparse", "size_bytes": path.stat().st_size,
        "major_version": major, "minor_version": minor,
        "file_header_size": file_hdr, "chunk_header_size": chunk_hdr,
        "block_size": block_size, "total_blocks": total_blocks,
        "expanded_size_bytes": block_size * total_blocks, "total_chunks": total_chunks,
        "image_checksum": f"{checksum:08x}",
    }



class SparseImageReader:
    """Read selected expanded ranges from Android sparse images without expanding them."""
    def __init__(self, path: Path):
        self.file = path.open("rb")
        h = self.file.read(28)
        if len(h) != 28:
            raise ValueError("Truncated sparse header")
        magic, major, minor, fh, ch, block, blocks, count, checksum = struct.unpack("<I4H4I", h)
        if magic != SPARSE_MAGIC or major != 1 or fh < 28 or ch < 12:
            raise ValueError("Unsupported sparse image header")
        self.size = block * blocks
        self.chunks = []
        self.file.seek(fh)
        logical = 0
        for _ in range(count):
            h = self.file.read(ch)
            if len(h) != ch:
                raise ValueError("Truncated sparse chunk header")
            kind, _, nblocks, total = struct.unpack_from("<2H2I", h)
            length, payload = nblocks * block, self.file.tell()
            extra = total - ch
            if extra < 0:
                raise ValueError("Invalid sparse chunk size")
            if kind == 0xCAC1 and extra == length:
                self.chunks.append((logical, length, "raw", payload, b""))
                self.file.seek(extra, 1)
            elif kind == 0xCAC2 and extra == 4:
                fill = self.file.read(4)
                self.chunks.append((logical, length, "fill", 0, fill))
            elif kind == 0xCAC3 and extra == 0:
                self.chunks.append((logical, length, "zero", 0, b""))
            elif kind == 0xCAC4 and extra == 4:
                self.file.seek(4, 1)
                continue
            else:
                raise ValueError(f"Invalid sparse chunk type/size: {kind:#x}/{extra}")
            logical += length
        if logical != self.size:
            raise ValueError("Sparse chunk lengths do not match image geometry")

    def read_at(self, offset: int, size: int) -> bytes:
        if offset < 0 or size < 0 or offset + size > self.size:
            raise ValueError("Read outside sparse image")
        out = bytearray()
        end = offset + size
        for start, length, kind, payload, fill in self.chunks:
            left, right = max(start, offset), min(start + length, end)
            if left >= right:
                continue
            n, within = right - left, left - start
            if kind == "raw":
                self.file.seek(payload + within)
                data = self.file.read(n)
                if len(data) != n:
                    raise ValueError("Truncated RAW chunk")
                out.extend(data)
            elif kind == "fill":
                out.extend(bytes(fill[(within+i) % 4] for i in range(n)))
            else:
                out.extend(b"\0" * n)
            if len(out) == size:
                break
        if len(out) != size:
            raise ValueError("Sparse range not fully mapped")
        return bytes(out)

    def close(self):
        self.file.close()


def audit_logical_partitions(path: Path) -> dict:
    import hashlib
    reader = None
    try:
        reader = SparseImageReader(path)
        # liblp geometry copies occupy the first two 4 KiB blocks.
        g = reader.read_at(4096, 52)
        magic, struct_size = struct.unpack_from("<II", g)
        if magic != 0x616C4467 or not 52 <= struct_size <= 4096:
            return {"status": "geometry_not_recognized", "magic_hex": f"0x{magic:08x}"}
        g = reader.read_at(4096, struct_size)
        checksum = g[8:40]
        check = bytearray(g); check[8:40] = b"\0" * 32
        if hashlib.sha256(check).digest() != checksum:
            return {"status": "geometry_checksum_mismatch"}
        max_size, slots, block_size = struct.unpack_from("<III", g, 40)
        if not 0 < max_size <= 16 * 1024 * 1024 or not 1 <= slots <= 4:
            return {"status": "invalid_geometry", "metadata_max_size": max_size, "metadata_slot_count": slots}
        # liblp reserves the first 4 KiB, stores primary and backup geometry
        # in the next two blocks, then begins primary metadata at 12 KiB.
        base = 3 * 4096
        h = reader.read_at(base, 128)
        magic, major, minor, hsize = struct.unpack_from("<IHHI", h)
        if magic != 0x414C5030 or not 128 <= hsize <= 4096:
            return {"status": "metadata_header_not_recognized", "magic_hex": f"0x{magic:08x}"}
        h = reader.read_at(base, hsize)
        tsize = struct.unpack_from("<I", h, 44)[0]
        if tsize > max_size or hsize + tsize > max_size:
            return {"status": "invalid_table_size", "tables_size": tsize}
        hc = bytearray(h); expected_h = bytes(h[12:44]); hc[12:44] = b"\0" * 32
        if hashlib.sha256(hc).digest() != expected_h:
            return {"status": "header_checksum_mismatch", "metadata_version": f"{major}.{minor}"}
        tables = reader.read_at(base + hsize, tsize)
        if hashlib.sha256(tables).digest() != h[48:80]:
            return {"status": "tables_checksum_mismatch", "metadata_version": f"{major}.{minor}"}
        desc = {name: struct.unpack_from("<III", h, pos) for name, pos in
                (("partitions",80),("extents",92),("groups",104),("block_devices",116))}
        sizes = {"partitions":52, "extents":24, "groups":48, "block_devices":64}
        rows = {}
        for name, (off, count, entry_size) in desc.items():
            if entry_size != sizes[name] or off + count * entry_size > tsize:
                return {"status": "invalid_table_descriptor", "table": name, "entry_size": entry_size}
            rows[name] = [tables[off+i*entry_size:off+(i+1)*entry_size] for i in range(count)]
        groups = []
        for b in rows["groups"]:
            groups.append({"name": b[:36].split(b"\0",1)[0].decode("ascii","replace"),
                           "flags": struct.unpack_from("<I",b,36)[0],
                           "maximum_size_bytes": struct.unpack_from("<Q",b,40)[0]})
        devices = []
        for b in rows["block_devices"]:
            first, align, align_off, size = struct.unpack_from("<QIIQ",b)
            devices.append({"first_logical_sector":first,"alignment":align,"alignment_offset":align_off,
                            "size_bytes":size,"partition_name":b[24:60].split(b"\0",1)[0].decode("ascii","replace"),
                            "flags":struct.unpack_from("<I",b,60)[0]})
        extents = []
        for b in rows["extents"]:
            sectors, target, data, source = struct.unpack("<QIQI",b)
            extents.append({"sectors":sectors,"size_bytes":sectors*512,"target_type":target,
                            "target_data":data,"target_source":source})
        partitions = []
        for b in rows["partitions"]:
            name = b[:36].split(b"\0",1)[0].decode("ascii","replace")
            attrs, first, count, group = struct.unpack_from("<IIII",b,36)
            if first + count > len(extents) or group >= len(groups):
                return {"status":"invalid_partition_reference","partition":name}
            owned = extents[first:first+count]
            partitions.append({"name":name,"attributes":attrs,"group":groups[group]["name"],
                               "first_extent_index":first,"extent_count":count,
                               "size_bytes":sum(x["size_bytes"] for x in owned),"extents":owned})
        return {"status":"parsed","metadata_slot":0,"geometry":{"metadata_max_size":max_size,
                "metadata_slot_count":slots,"logical_block_size":block_size},
                "metadata_version":f"{major}.{minor}","header_size":hsize,"tables_size":tsize,
                "partition_count":len(partitions),"group_count":len(groups),
                "block_device_count":len(devices),"groups":groups,"block_devices":devices,
                "partitions":partitions}
    except (OSError, ValueError, struct.error) as exc:
        return {"status":"parse_error","error":str(exc)}
    finally:
        if reader:
            reader.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", required=True, type=Path)
    ap.add_argument("--images", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    images = args.images
    report = {
        "device": "Xiaomi Redmi 12C", "codename": "earth",
        "firmware": "OS1.0.16.0.UCVMIXM", "audit_mode": "offline_metadata_only",
        "scatter": read_scatter(args.archive),
        "images": {},
        "logical_partition_metadata": {"status": "not_checked"},
        "gpt": {"status": "not_checked"},
        "gpt_scatter_comparison": {"status": "not_checked"},
        "avb_descriptors": {},
        "safety": "No image is flashed, modified, or written to a device.",
    }
    gpt_path = images / "PGPT_EMMC"
    if gpt_path.is_file():
        report["gpt"] = audit_gpt(gpt_path)
    for name in ("boot.img", "dtbo.img", "vbmeta.img", "vbmeta_system.img", "vbmeta_vendor.img", "super.img"):
        path = images / name
        if not path.is_file():
            report["images"][name] = {"status": "not_present"}
        elif name == "boot.img":
            report["images"][name] = audit_boot(path)
        elif name == "dtbo.img":
            report["images"][name] = audit_dtbo(path)
        elif name.startswith("vbmeta"):
            report["images"][name] = audit_vbmeta(path)
            report["avb_descriptors"][name] = audit_vbmeta_descriptors(path)
        else:
            report["images"][name] = audit_sparse(path)
            report["logical_partition_metadata"] = audit_logical_partitions(path)
    report["gpt_scatter_comparison"] = compare_gpt_scatter(report["gpt"], report["scatter"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Firmware structure audit written:", args.output)
    print("Scatter:", report["scatter"]["status"], "partitions:", report["scatter"].get("partition_count", 0))
    for name, result in report["images"].items():
        print(name + ":", result.get("status"))
    print("GPT:", report["gpt"]["status"], "partitions:", report["gpt"].get("partition_count", 0))
    print("GPT/scatter comparison:", report["gpt_scatter_comparison"]["status"],
          "matched:", report["gpt_scatter_comparison"].get("matched_names", 0))
    print("AVB descriptors:", {k: v.get("status") for k, v in report["avb_descriptors"].items()})
    logical_status = report["logical_partition_metadata"]["status"]
    print("Logical partition metadata:", logical_status)
    if logical_status != "parsed":
        print("ERROR: logical partition metadata audit did not complete successfully.")
        return 1
    if report["gpt"].get("status") != "parsed":
        print("ERROR: GPT audit did not complete successfully.")
        return 1
    if report["gpt_scatter_comparison"].get("status") != "compared":
        print("ERROR: GPT/scatter comparison did not complete.")
        return 1
    comparison = report["gpt_scatter_comparison"]
    if comparison.get("matched_names", 0) == 0 or not comparison.get("all_start_matches") or not comparison.get("all_size_matches"):
        print("ERROR: GPT/scatter geometry does not match for all comparable partitions.")
        return 1
    avb = report["avb_descriptors"]
    expected_avb = {"vbmeta.img", "vbmeta_system.img", "vbmeta_vendor.img"}
    if set(avb) != expected_avb or any(item.get("status") != "parsed" for item in avb.values()):
        print("ERROR: one or more AVB descriptor audits did not complete successfully.")
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
