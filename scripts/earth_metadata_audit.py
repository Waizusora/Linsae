"""Read-only GPT and AVB metadata parsers for offline firmware audits."""
from __future__ import annotations

import struct
import uuid
import zlib
from pathlib import Path


def audit_gpt(path: Path, sector_size: int = 512) -> dict:
    data = path.read_bytes()
    header_offset = next((x for x in (sector_size, 0)
                          if len(data) >= x + 92 and data[x:x + 8] == b"EFI PART"), None)
    if header_offset is None:
        return {"status": "gpt_header_not_found", "size_bytes": len(data)}
    header = bytearray(data[header_offset:header_offset + 92])
    revision, header_size, expected_crc = struct.unpack_from("<III", header, 8)
    if header_size < 92 or header_size > sector_size or header_offset + header_size > len(data):
        return {"status": "invalid_gpt_header_size", "header_size": header_size}
    full = bytearray(data[header_offset:header_offset + header_size])
    full[16:20] = bytes(4)
    actual_crc = zlib.crc32(full) & 0xffffffff
    if actual_crc != expected_crc:
        current_lba, backup_lba, first_usable, last_usable = struct.unpack_from("<QQQQ", header, 24)
        entries_lba, entry_count, entry_size, entries_crc = struct.unpack_from("<QIII", header, 72)
        return {
            "status": "gpt_header_crc_mismatch",
            "header_offset": header_offset,
            "header_size": header_size,
            "expected_crc32": f"{expected_crc:08x}",
            "actual_crc32": f"{actual_crc:08x}",
            "revision": revision,
            "current_lba": current_lba,
            "backup_lba": backup_lba,
            "first_usable_lba": first_usable,
            "last_usable_lba": last_usable,
            "entries_lba": entries_lba,
            "entry_count": entry_count,
            "entry_size": entry_size,
            "signature_offsets": [i for i in range(len(data)) if data.startswith(b"EFI PART", i)],
            "prefix_hex": data[:128].hex(),
        }
    current_lba, backup_lba, first_usable, last_usable = struct.unpack_from("<QQQQ", header, 24)
    disk_guid = str(uuid.UUID(bytes_le=bytes(header[56:72])))
    entries_lba, entry_count, entry_size, entries_crc = struct.unpack_from("<QIII", header, 72)
    if not entry_count or entry_size < 128 or entry_size % 8:
        return {"status": "invalid_gpt_entry_geometry"}
    array_offset = entries_lba * sector_size
    array_size = entry_count * entry_size
    if array_offset < 0 or array_offset + array_size > len(data):
        return {"status": "gpt_partition_array_out_of_bounds"}
    array = data[array_offset:array_offset + array_size]
    if zlib.crc32(array) & 0xffffffff != entries_crc:
        return {"status": "gpt_partition_array_crc_mismatch"}
    partitions = []
    for i in range(entry_count):
        row = array[i * entry_size:(i + 1) * entry_size]
        if row[:16] == bytes(16):
            continue
        first, last, attrs = struct.unpack_from("<QQQ", row, 32)
        name = row[56:entry_size].decode("utf-16le", "replace").split(chr(0), 1)[0]
        if last < first or first < first_usable or last > last_usable:
            return {"status": "invalid_gpt_partition_range", "partition": name}
        partitions.append({"name": name, "type_guid": str(uuid.UUID(bytes_le=row[:16])),
                           "unique_guid": str(uuid.UUID(bytes_le=row[16:32])),
                           "first_lba": first, "last_lba": last, "attributes": attrs,
                           "start_bytes": first * sector_size,
                           "size_bytes": (last - first + 1) * sector_size})
    return {"status": "parsed", "size_bytes": len(data), "sector_size": sector_size,
            "header_offset": header_offset, "revision": revision, "header_size": header_size,
            "current_lba": current_lba, "backup_lba": backup_lba,
            "first_usable_lba": first_usable, "last_usable_lba": last_usable,
            "disk_guid": disk_guid, "entry_count": entry_count,
            "partition_count": len(partitions), "partitions": partitions}


def audit_vbmeta_descriptors(path: Path) -> dict:
    data = path.read_bytes()
    if len(data) < 256 or data[:4] != b"AVB0":
        return {"status": "unknown_header", "size_bytes": len(data)}
    required_major, required_minor = struct.unpack_from(">II", data, 4)
    auth_size, aux_size = struct.unpack_from(">QQ", data, 12)
    algorithm = struct.unpack_from(">I", data, 28)[0]
    rollback = struct.unpack_from(">Q", data, 32)[0]
    hash_off, hash_size, sig_off, sig_size = struct.unpack_from(">4Q", data, 40)
    # AVB header offsets are fixed by avb_vbmeta_image.h.
    key_off, key_size, key_meta_off, key_meta_size = struct.unpack_from(">4Q", data, 72)
    desc_off, desc_size = struct.unpack_from(">QQ", data, 104)
    rollback_location, flags = struct.unpack_from(">II", data, 120)
    total = 256 + auth_size + aux_size
    ranges = {"hash": (hash_off, hash_size, auth_size),
              "signature": (sig_off, sig_size, auth_size),
              "public_key": (key_off, key_size, aux_size),
              "public_key_metadata": (key_meta_off, key_meta_size, aux_size),
              "descriptors": (desc_off, desc_size, aux_size)}
    for label, (offset, size, limit) in ranges.items():
        if offset > limit or size > limit - offset:
            return {"status": "invalid_vbmeta_range", "range": label}
    if total > len(data):
        return {"status": "truncated_vbmeta_blocks", "declared_size_bytes": total}
    desc_start = 256 + auth_size + desc_off
    pos, end = desc_start, desc_start + desc_size
    names = {0: "property", 1: "hashtree", 2: "hash", 3: "kernel_cmdline", 4: "chain_partition"}
    descriptors, chains = [], []
    while pos < end:
        if end - pos < 16:
            return {"status": "truncated_descriptor_header", "descriptor_count": len(descriptors)}
        tag, following = struct.unpack_from(">QQ", data, pos)
        record_size = 16 + following
        if record_size > end - pos:
            return {"status": "descriptor_out_of_bounds", "tag": tag}
        item = {"tag": tag, "type": names.get(tag, "unknown"), "size_bytes": record_size}
        if tag == 4:
            if following < 76:
                return {"status": "truncated_chain_descriptor"}
            rollback_loc, name_len, key_len, chain_flags = struct.unpack_from(">4I", data, pos + 16)
            if 76 + name_len + key_len > following:
                return {"status": "invalid_chain_descriptor_lengths"}
            name_start = pos + 92
            partition = data[name_start:name_start + name_len].decode("utf-8", "replace")
            item.update({"partition_name": partition, "rollback_index_location": rollback_loc,
                         "flags": chain_flags})
            chains.append({"partition_name": partition, "rollback_index_location": rollback_loc,
                           "flags": chain_flags})
        descriptors.append(item)
        pos += record_size
    return {"status": "parsed", "size_bytes": len(data), "required_major": required_major,
            "required_minor": required_minor, "authentication_data_block_size": auth_size,
            "auxiliary_data_block_size": aux_size, "algorithm_type": algorithm,
            "rollback_index": rollback, "flags": flags, "rollback_index_location": rollback_location,
            "descriptor_count": len(descriptors), "descriptor_types": [x["type"] for x in descriptors],
            "chain_partitions": chains}


def compare_gpt_scatter(gpt: dict, scatter: dict) -> dict:
    if gpt.get("status") != "parsed" or scatter.get("status") != "parsed":
        return {"status": "not_comparable"}
    by_name = {p["name"].lower(): p for p in gpt["partitions"]}
    checks = []
    for row in scatter.get("partitions", []):
        name = row.get("partition_name", "").lower()
        if name not in by_name:
            continue
        try:
            start = int(row.get("linear_start_addr", row.get("physical_start_addr", "0")), 0)
            size = int(row.get("partition_size", "0"), 0)
        except ValueError:
            continue
        actual = by_name[name]
        checks.append({"partition": name, "scatter_start_bytes": start,
                       "gpt_start_bytes": actual["start_bytes"], "scatter_size_bytes": size,
                       "gpt_size_bytes": actual["size_bytes"], "start_match": start == actual["start_bytes"],
                       "size_match": size == actual["size_bytes"]})
    return {"status": "compared", "matched_names": len(checks),
            "all_start_matches": all(x["start_match"] for x in checks),
            "all_size_matches": all(x["size_match"] for x in checks), "partitions": checks}
