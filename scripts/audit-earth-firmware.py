#!/usr/bin/env python3
"""Offline structural audit for the Redmi 12C earth Fastboot ROM."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import struct
import subprocess
import tarfile
from pathlib import Path, PurePosixPath

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
    rollback = struct.unpack_from(">Q", data, 32)[0]
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
        "logical_partition_metadata": {"status": "tool_unavailable"},
        "safety": "No image is flashed, modified, or written to a device.",
    }
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
        else:
            report["images"][name] = audit_sparse(path)
            tool = shutil.which("lpdump")
            if tool:
                try:
                    proc = subprocess.run([tool, str(path)], text=True, capture_output=True, timeout=120, check=False)
                    report["logical_partition_metadata"] = {
                        "status": "parsed" if proc.returncode == 0 else "tool_error",
                        "returncode": proc.returncode,
                        "stdout": proc.stdout[:200000],
                        "stderr": proc.stderr[:12000],
                    }
                except (OSError, subprocess.TimeoutExpired) as exc:
                    report["logical_partition_metadata"] = {"status": "tool_error", "error": str(exc)}
            else:
                report["logical_partition_metadata"] = {
                    "status": "lpdump_unavailable",
                    "note": "Sparse super image geometry was inspected; logical partition table was not decoded."
                }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Firmware structure audit written:", args.output)
    print("Scatter:", report["scatter"]["status"], "partitions:", report["scatter"].get("partition_count", 0))
    for name, result in report["images"].items():
        print(name + ":", result.get("status"))
    print("Logical partition metadata:", report["logical_partition_metadata"]["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
