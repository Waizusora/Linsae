# Redmi 12C firmware layout audit

Status: read-only analysis of the stock Android 14 firmware package and previously captured handset metadata. This document is not a flash layout recipe and does not authorize flashing, repartitioning, bootloader changes, or modification of protected partitions.

## Evidence set

- Device: Xiaomi Redmi 12C, codename `earth`, model `22120RN86G`.
- Stock firmware: `OS1.0.16.0.UCVMIXM`, Android 14.
- Fastboot archive: `earth_global_images_OS1.0.16.0.UCVMIXM_20260227.0000.00_14.0_global_b2ab987cbf.tgz`.
- Archive MD5 verified by CI: `b2ab987cbfb0b980cbbdca7174542672`.
- Firmware structure audit: scatter text parsed (60 entries); boot, dtbo and three vbmeta image headers recognized; Android sparse super image recognized; liblp metadata parsed.
- Device observations were collected from the user's stock handset through read-only ADB. They are kept distinct from package-derived data below.

## Physical layout: scatter package versus handset observations

The firmware scatter describes 60 entries. The important package entries are:

| Partition | Scatter start | Scatter size | Package image |
|---|---:|---:|---|
| `vbmeta_a` | `0x1808000` | `0x800000` (8 MiB) | `vbmeta.img` (4 KiB) |
| `vbmeta_system_a` | `0x2008000` | `0x800000` (8 MiB) | `vbmeta_system.img` (4 KiB) |
| `vbmeta_vendor_a` | `0x2808000` | `0x800000` (8 MiB) | `vbmeta_vendor.img` (4 KiB) |
| `vbmeta_b` | `0x3008000` | `0x800000` (8 MiB) | no image (`NONE`, download false) |
| `vbmeta_system_b` | `0x3808000` | `0x800000` (8 MiB) | no image (`NONE`, download false) |
| `vbmeta_vendor_b` | `0x4008000` | `0x800000` (8 MiB) | no image (`NONE`, download false) |
| `md_udc` | `0x4808000` | `0x169a000` | no image |
| `metadata` | `0x5ea2000` | `0x2000000` (32 MiB) | no image |
| `boot_a` | `0x1f200000` | `0x4000000` (64 MiB) | `boot.img` (64 MiB) |
| `dtbo_a` | `0x23200000` | `0x800000` (8 MiB) | `dtbo.img` (76,368 bytes) |
| `boot_b` | `0x3a200000` | `0x4000000` (64 MiB) | no image (`NONE`, download false) |
| `dtbo_b` | `0x3e200000` | `0x800000` (8 MiB) | no image (`NONE`, download false) |
| `cust` | `0x3ef00000` | `0x40000000` (1 GiB) | `cust.img` |
| `rescue` | `0x7ef00000` | `0x8000000` (128 MiB) | `rescue.img` |
| `super` | `0x89000000` | `0x1c0000000` (7,516,192,768 bytes) | `super.img` |
| `userdata` | `0x249000000` | `0x280000000` (10 GiB) | `userdata.img` |

The scatter's `super` interval ends exactly at the `userdata` start address:
`0x89000000 + 0x1c0000000 = 0x249000000`.
The expanded sparse image size and liblp block-device size are both 7,516,192,768 bytes, matching the scatter `super` size. This is a strong package-internal size consistency check.

The handset's by-name listing independently observed `super = mmcblk0p54`, `userdata = mmcblk0p55`, `boot_a/b = mmcblk0p27/p45`, `dtbo_a/b = mmcblk0p28/p46`, and `vbmeta_a/b = mmcblk0p6/p9`. These are observed Linux block-device node numbers, not scatter `partition_index` values. Do not equate the two numbering schemes or derive offsets from the mmcblk suffix.

The package scatter marks the listed `*_b` boot, dtbo and vbmeta entries as non-downloadable with `file_name: NONE`. This is a property of this package's flashing manifest; it does not mean the handset lacks the B-side partitions. The handset independently exposes paired by-name entries.

## Dynamic partition metadata

The sparse `super.img` expands to 7,516,192,768 bytes. Its liblp metadata was parsed from metadata slot 0:

- liblp metadata version: 10.2.
- Logical block size: 4,096 bytes.
- Metadata maximum size: 65,536 bytes.
- Metadata slot count: 3.
- One block device named `super`, size 7,516,192,768 bytes, first logical sector 2,048, alignment 1 MiB.
- Three groups: `default`, `main_a`, and `main_b`.
- `main_a` and `main_b` each declare a maximum size of 7,505,707,008 bytes.
- Ten logical partition records exist: `product_a/b`, `system_a/b`, `system_ext_a/b`, `vendor_a/b`, and `mi_ext_a/b`.

In metadata slot 0, the non-empty extents belong to the five `_a` records:

| Logical partition | Group | Extent size |
|---|---|---:|
| `product_a` | `main_a` | 2,756,812,800 bytes |
| `system_a` | `main_a` | 873,181,184 bytes |
| `system_ext_a` | `main_a` | 695,566,336 bytes |
| `vendor_a` | `main_a` | 296,566,784 bytes |
| `mi_ext_a` | `main_a` | 920,276,992 bytes |

The corresponding five `_b` records are present but have zero extents and zero size in the parsed metadata slot. The sum of non-empty logical partition sizes is 5,542,404,096 bytes. Each listed extent uses target type 0 and target source 0; the parser records the physical sector targets.

Important distinction: liblp's metadata slot count of three is not the Android A/B slot count. Parsing metadata slot 0 alone does not establish the contents of metadata slots 1 and 2, the update-time snapshot state, or the final target ROM layout. The stock handset separately reports `ro.boot.slot_suffix=_a`, dynamic partitions enabled, and Virtual A/B enabled. Keep those observations separate; do not infer that a three-slot metadata geometry means an A/B/C device.

The raw partition attribute value is 1 for each logical partition record. This audit does not yet decode attribute bits against the exact liblp header definitions, so it deliberately does not label that value as read-only or infer mount behavior from it.

## Boot image and AVB header observations

The package images have these recognized structures:

| Image | Header observation |
|---|---|
| `boot.img` | Android boot magic; header version 2; page size 2,048; kernel payload 12,632,173 bytes; ramdisk payload 16,215,138 bytes; total file 64 MiB |
| `dtbo.img` | DT table magic; one entry; header 32 bytes; entry size 32 bytes |
| `vbmeta.img` | AVB0 header; algorithm type 1; flags 0; rollback index 0; release string `avbtool 1.2.0` |
| `vbmeta_system.img` | AVB0 header; algorithm type 1; flags 0; rollback index 0; release string `avbtool 1.2.0` |
| `vbmeta_vendor.img` | AVB0 header; algorithm type 1; flags 0; rollback index 0; release string `avbtool 1.2.0` |

These are header-level observations only. The current audit has not decoded AVB hash/hashtree descriptors, chain partition descriptors, public-key identity, rollback-index locations across all descriptors, or signature verification. Therefore it does not yet prove the complete AVB chain topology or that any newly built image can be verified by the stock bootloader.

The firmware inventory does not contain separate `vendor_boot.img` or `init_boot.img` files. Do not infer that the target Android 15 build can omit or must add either image without checking the device's boot architecture, ramdisk contents, init first-stage requirements, and target boot image format. The stock handset reports a locked bootloader, AVB 1.2, green verified boot, and enforcing verity; those are security-state observations, not instructions to unlock or disable verification.

## Fstab reconciliation

The previously captured stock `/vendor/etc/fstab.mt6768` maps `md_udc` to `/metadata` (ext4) and `userdata` to `/data` (F2FS). The separate by-name partition called `metadata` is not the partition used for the stock `/metadata` mount. This resolves the earlier apparent mismatch: do not substitute `metadata` for `md_udc`.

The stock fstab declares `system`, `vendor`, `product`, `system_ext`, and `mi_ext` as logical, slot-selected, first-stage mounts, with AVB-related flags. This is consistent at a high level with the logical partition names in the parsed `super` metadata. It is not sufficient to copy the stock fstab into an Android 15 device tree: the target init version, AVB descriptor chain, filesystem support, encryption, Virtual A/B snapshot behavior, and Xiaomi-specific overlays still need explicit review.

The stock fstab also contains legacy aliases for bootloader/firmware partitions. Resolve these through actual init imports, symlinks, and the matching stock package before carrying any alias into a new configuration.

## Findings and remaining work

### Confirmed consistency

1. The scatter and sparse image agree exactly on the physical `super` partition size.
2. The scatter `super` region ends at the next `userdata` start address without a gap or overlap.
3. The package contains all five logical partition names that the stock fstab expects: system, vendor, product, system_ext, and mi_ext, with slot-selected records in liblp metadata.
4. The device's by-name observations include the expected A/B boot, dtbo, and vbmeta pairs, while the package scatter separately records the corresponding A/B entries.
5. The stock fstab's `md_udc` mapping to `/metadata` matches the observed mount backing device and avoids confusing it with the separate `metadata` partition.

### Not yet proven

1. A complete GPT-to-scatter-to-`/dev/block/by-name` byte-offset mapping. The handset's observed node names and scatter entries have not yet been reconciled against a parsed GPT.
2. Full liblp metadata slot coverage and Virtual A/B snapshot/COW metadata state.
3. AVB descriptor and chain topology, signing key identity, and signature verification.
4. Android 15 boot image packaging, vendor ramdisk requirements, and whether vendor_boot/init_boot are needed.
5. The exact Android 15 fstab, first-stage mount, encryption, and snapshot configuration.
6. Kernel source/config/module compatibility with the stock 4.19.191-perf kernel and Android 15 userspace.
7. Exact physical partition geometry from the device's GPT and confirmation of all scatter offsets against that table.

## Offline GPT and AVB parser implementation

The repository now includes `scripts/earth_metadata_audit.py`, integrated into `scripts/audit-earth-firmware.py`.

- The extractor retains the package's `images/PGPT_EMMC` metadata blob in the analysis directory; it does not execute vendor flashing tools.
- GPT parsing checks the GPT header CRC, partition-entry-array CRC, entry geometry, usable-LBA bounds, partition GUIDs, names, start LBAs, and sizes.
- A comparison routine matches GPT entries by partition name against scatter start addresses and sizes. Unmatched names remain unasserted rather than being guessed.
- AVB parsing checks the vbmeta authentication/auxiliary block bounds and descriptor-area bounds, enumerates descriptor tags, and extracts chain-partition names and rollback-index locations. Public-key bytes and signature contents are not emitted.
- Unit tests cover valid and corrupted GPT headers, AVB chain descriptors and descriptor bounds, alongside the existing sparse/liblp tests.

Repository validation completed successfully for commit `1919d0b66ee351d4a31c810d9f00b643a32dd956` (7 tests). This validates the parser fixtures, not yet the real package GPT or real vbmeta descriptor results.

## Real-package parser findings and fail-closed validation

The first real-package audit was run in extraction workflow #12 on commit `861d2a28600aa2fb080316e182d0fae1b4122707`. Download, MD5 verification, extraction, scatter parsing, and liblp parsing completed. The real `PGPT_EMMC` blob was found, but the GPT header CRC check returned `gpt_header_crc_mismatch`. The initial AVB descriptor parser also returned `invalid_vbmeta_range` for all three vbmeta images.

The AVB issue was caused by a second field-offset error in the parser. The AOSP `AvbVBMetaImageHeader` layout defines hash offset/size at bytes 32/40, signature offset/size at 48/56, public-key offset/size at 64/72, public-key-metadata offset/size at 80/88, descriptor offset/size at 96/104, rollback index at 112, flags at 120, and rollback-index location at 124. Run #13 still reported invalid signature ranges because the parser was reading these fields eight bytes too late. The parser and fixtures have now been aligned to the AOSP layout; the next real-package run must confirm the result.

Run #16 artifact includes the raw 17,408-byte `PGPT_EMMC` blob. Inspection shows an `EFI PART` marker with a zero header CRC and empty standard GPT entry-array fields, while the nominal entry-array geometry points to 128 records of 128 bytes at LBA 2 (byte 1,024), which use a MediaTek-specific 32-byte ASCII identifier followed by LBA start/end, attributes, and a UTF-16LE name. The parser now recognizes this as `MediaTek PGPT_EMMC`, not as a valid standard GPT, and compares only records with usable ranges against the scatter. The `userdata` record has a zero start/end range, so its geometry remains unverified; the audit intentionally fails closed instead of inventing its location from the scatter.

The extraction audit fails the job if GPT/PGPT parsing, comparable PGPT/scatter geometry, any required physical scatter geometry remains unverified, or any of the three AVB descriptor audits fail. Unmapped PGPT records remain listed as unverified. Non-downloadable `otp` and `flashinfo` scatter entries use high sentinel addresses rather than usable physical offsets; these remain unverified but do not block comparison as if the sentinel were physical geometry. `userdata` remains a blocking unresolved range because scatter supplies a physical start and size while PGPT supplies LBA 0/0. The report upload remains configured with `if: always()`, and retains the raw `PGPT_EMMC` blob alongside the JSON report. The previous extraction run is not evidence that GPT or AVB passed.

The audit remains offline and read-only. Do not read, copy, publish, or modify calibration, NVRAM, NV data, persist, modem identity, or other sensitive device partitions. No flashing or bootloader changes are part of this work.
