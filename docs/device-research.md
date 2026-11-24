# Redmi 12C hardware research

Initial target: Xiaomi Redmi 12C, reported device codename `earth`.

The codename and SoC family are project targets, not a substitute for auditing the exact handset. Regional variants, firmware releases, and board revisions can affect compatibility.

## Required device capture

Collect the following from the actual handset before writing device makefiles:

```sh
adb shell getprop ro.product.device
adb shell getprop ro.product.vendor.device
adb shell getprop ro.product.model
adb shell getprop ro.board.platform
adb shell getprop ro.hardware
adb shell getprop ro.boot.hardware
adb shell getprop ro.build.fingerprint
adb shell getprop ro.vendor.build.fingerprint
adb shell getprop ro.boot.slot_suffix
adb shell getprop ro.boot.dynamic_partitions
adb shell getprop ro.boot.verifiedbootstate
adb shell cat /proc/cmdline
adb shell cat /proc/partitions
```

If a property is unavailable, record it as unavailable rather than inferring its value. Some information may require bootloader fastboot variables or stock firmware images.

## Evidence required before integration

- Exact product and board identifiers.
- Partition names, sizes, slot layout, and logical partition metadata.
- Boot, vendor_boot, init_boot, dtbo, vbmeta, and recovery image formats as applicable.
- Kernel version, source lineage, configuration, and module dependencies.
- Vendor and firmware versions that match the selected stock baseline.
- Display panel, touch controller, audio codec, camera sensors, modem, Wi-Fi/Bluetooth, and sensor inventory.

## Source compatibility

Do not select a kernel repository based only on the marketing chipset name. Confirm the source branch against the handset's kernel version, vendor release, device tree, and boot image requirements. Do not invent partition sizes, offsets, fstab entries, or proprietary file lists.

## Privacy

Remove serial numbers, IMEI/MEID, phone numbers, account identifiers, and other personal identifiers before sharing diagnostic output.

## Verified handset baseline

Captured from the user's Redmi 12C through ADB on the stock Android 14 installation:

| Property | Observed value |
|---|---|
| `ro.product.device` | `earth` |
| `ro.product.vendor.device` | `earth` |
| `ro.product.model` | `22120RN86G` |
| `ro.board.platform` | `mt6768` |
| `ro.hardware` | `mt6768` |
| `ro.boot.hardware` | `mt6768` |
| `ro.build.fingerprint` | `Redmi/earth_global/earth:14/UP1A.231005.007/V816.0.16.0.UCVMIXM:user/release-keys` |
| `ro.vendor.build.fingerprint` | Same as system fingerprint |
| `ro.boot.slot_suffix` | `_a` |
| `ro.boot.dynamic_partitions` | `true` |
| `ro.boot.verifiedbootstate` | `green` |

The handset reports an A/B slot suffix and dynamic partitions enabled. The verified boot state is green on the captured stock boot. These observations do not reveal partition sizes, the complete partition map, AVB chain configuration, or boot image header version.

The following reads were denied by the device's shell permissions and remain unknown:

- `/proc/cmdline`
- `/proc/partitions`

Do not infer their contents. Continue the audit using fastboot variables, read-only partition metadata where accessible, and stock firmware image inspection.

## Hardware identity notes

The device reports `mt6768`. Public device specifications identify this platform family with the Helio G85, but device configuration must use the exact platform string observed from the handset. Keep `mt6768` as the board platform identifier unless further verified evidence requires otherwise.

## Next required captures

From Android:

```sh
adb shell getprop | grep -E 'ro.boot.(.*)|ro.product.(.*)|ro.vendor.(.*)'
adb shell ls -l /dev/block/by-name
adb shell ls -l /dev/block/mapper
adb shell cat /proc/mounts
```

Some paths may remain inaccessible on a production build. If so, record the permission error and use stock firmware package inspection instead.

From bootloader fastboot mode:

```sh
fastboot getvar product
fastboot getvar current-slot
fastboot getvar is-userspace
fastboot getvar all
```

Review the output before sharing and redact serial numbers and other identifiers. Fastboot variables are device/bootloader dependent; unavailable variables are not evidence that a feature is absent.


## Storage and partition observations

Captured from the same stock Android 14 handset through ADB. These are observations of the running device, not a complete flash-layout specification.

### Physical by-name entries

The device exposes an eMMC-style block layout through `/dev/block/by-name`, with the following important entries:

| Name | Block device |
|---|---|
| `boot_a` / `boot_b` | `mmcblk0p27` / `mmcblk0p45` |
| `dtbo_a` / `dtbo_b` | `mmcblk0p28` / `mmcblk0p46` |
| `vbmeta_a` / `vbmeta_b` | `mmcblk0p6` / `mmcblk0p9` |
| `vbmeta_system_a` / `vbmeta_system_b` | `mmcblk0p7` / `mmcblk0p10` |
| `vbmeta_vendor_a` / `vbmeta_vendor_b` | `mmcblk0p8` / `mmcblk0p11` |
| `super` | `mmcblk0p54` |
| `userdata` | `mmcblk0p55` |
| `metadata` | `mmcblk0p13` |
| `md_udc` | `mmcblk0p12` |

Other paired firmware partitions are visible, including `gz`, `lk`, `logo`, `md1img`, `scp`, `spmfw`, `sspm`, and `tee`. Preserve the complete raw ADB capture as the source of truth; this summary is not an instruction to flash or modify any of these partitions.

### Logical partitions and snapshot-related devices

The mapper directory exposes active logical devices including:

- `system_a`, `vendor_a`, `product_a`, `system_ext_a`, and `mi_ext_a`
- Corresponding `*-verity` devices
- Corresponding `*-cow` devices for several logical partitions

This is consistent with dynamic partitions and snapshot/COW update infrastructure. The precise Virtual A/B configuration, group definitions, metadata contents, and inactive-slot state still require verification from super metadata and relevant device properties.

### Mounted filesystems

Observed mount types:

| Mount point | Observed backing / filesystem |
|---|---|
| `/` | `/dev/block/dm-10`, EROFS, read-only |
| `/vendor` | `/dev/block/dm-11`, EROFS, read-only |
| `/product` | `/dev/block/dm-12`, EROFS, read-only |
| `/system_ext` | `/dev/block/dm-14`, EROFS, read-only |
| `/mnt/vendor/mi_ext` and `/mi_ext` | `/dev/block/dm-13`, EROFS, read-only |
| `/data` | `/dev/block/dm-52`, F2FS, read-write |
| `/metadata` | `/dev/block/by-name/md_udc`, ext4, read-write |
| `/cust` | by-name `cust`, EROFS, read-only |

The mount output reports `/metadata` backed by `md_udc` (block p12), while the by-name listing separately exposes `metadata` (block p13). This discrepancy is unresolved. Do not assume the two names are interchangeable; verify fstab, init configuration, and stock firmware metadata before defining the device fstab.

### Remaining unknowns

The ADB listing does not provide partition byte sizes, GPT/eMMC geometry, super logical partition group limits, boot image header version, AVB descriptors/keys/rollback indexes, or the exact contents of boot/vendor firmware images. Those must be obtained from trusted stock firmware metadata/images or read-only bootloader diagnostics. Do not write partition sizes, offsets, flash commands, or image packaging rules from block numbering alone.


## Boot, AVB, and Virtual A/B observations

Additional read-only properties captured from the stock handset:

| Property | Observed value |
|---|---|
| `ro.boot.slot` | `a` |
| `ro.boot.slot_suffix` | `_a` |
| `ro.boot.dynamic_partitions` | `true` |
| `ro.virtual_ab.enabled` | `true` |
| `ro.virtual_ab.compression.enabled` | `true` |
| `ro.boot.avb_version` | `1.2` |
| `ro.boot.vbmeta.avb_version` | `1.2` |
| `ro.boot.vbmeta.device_state` | `locked` |
| `ro.boot.flash.locked` | `1` |
| `ro.boot.verifiedbootstate` | `green` |
| `ro.boot.veritymode` | `enforcing` |
| `ro.boot.veritymode.managed` | `yes` |
| `ro.boot.secureboot` | `1` |
| `ro.boot.vbmeta.hash_alg` | `sha256` |
| `ro.boot.vbmeta.size` | `9792` (reported property; unit/interpretation not independently verified) |
| `ro.boot.dtb_idx` | `0` |
| `ro.boot.dtbo_idx` | `0` |
| `ro.boot.product.hardware.sku` | `earth` |
| `ro.boot.hwc` | `Global` |
| `ro.boot.hwlevel` | `MP` |
| `ro.boot.hwversion` | `6390A.19.0` |
| `ro.boot.rsc` | `earth_qpa_ap` |

The properties explicitly confirm Virtual A/B and compressed snapshot support. AVB is enabled and enforcing on the stock boot; the bootloader is locked and verified boot state is green. These are stock security-state observations, not permission or instruction to unlock, disable verification, or flash modified images.

The `ro.bootimage.build.*` properties report an Android 12 / SDK 31 boot-image build identity, while the system fingerprint captured above reports Android 14. This mismatch is recorded as an observed vendor/boot image property discrepancy and must be investigated against the stock firmware package; do not assume it identifies the target OS or kernel version.

A device serial property was present in the raw diagnostic output. It is intentionally omitted from this document and must not be copied into public logs, commits, or issue reports.


## Stock fstab and first-stage mount configuration

Captured from `/vendor/etc/fstab.mt6768` on the stock Redmi 12C firmware. This is a device-specific observation and should be treated as a reference for analysis, not copied wholesale into a new ROM without reconciling Android 15 init, AVB, and partition requirements.

### Dynamic logical partitions

The stock fstab declares these logical mount points with EROFS and ext4 alternatives:

| Logical partition | Mount point | Slot / mount flags | AVB target |
|---|---|---|---|
| `system` | `/system` | `wait,slotselect,logical,first_stage_mount` | `vbmeta_system` |
| `vendor` | `/vendor` | `wait,slotselect,logical,first_stage_mount` | default AVB chain |
| `product` | `/product` | `wait,slotselect,logical,first_stage_mount` | default AVB chain |
| `system_ext` | `/system_ext` | `wait,slotselect,logical,first_stage_mount` | `vbmeta_system` |
| `mi_ext` | `/mnt/vendor/mi_ext` | `wait,slotselect,logical,first_stage_mount,nofail` | `vbmeta` |

The stock fstab includes EROFS and ext4 alternatives for these logical partitions. It also defines Xiaomi-specific overlay mounts sourced from `mi_ext` and `product/pangu`. Those overlays are stock-firmware behavior and must not be blindly carried into Linsae.

The system and system_ext entries reference AVB public keys under `/avb`. Their compatibility and trust model must be evaluated for the target build; do not assume stock keys can verify newly built images.

### Metadata and userdata

The stock fstab explicitly maps:

- `/dev/block/by-name/md_udc` to `/metadata` as ext4.
- `/dev/block/by-name/userdata` to `/data` as F2FS.

This resolves the earlier apparent discrepancy: the by-name partition called `metadata` is a separate entry from `md_udc`; the stock fstab uses `md_udc` for the `/metadata` mount. Do not substitute one for the other.

The userdata entry includes metadata encryption using `/metadata/vold/metadata_encryption`, file-based encryption parameters, quota, resize, and checkpoint-related options. These options are security- and data-integrity-sensitive; preserve no values without validating them against the Android 15 implementation and device requirements.

### Other stock mounts

The fstab also references `rescue` as `/cache`, and mounts `protect1`, `protect2`, `nvdata`, `nvcfg`, `persist`, and `persistbak` under vendor paths. It declares removable storage and USB OTG vold-managed devices.

Several legacy-style emmc mount declarations refer to aliases such as `lk`, `lk2`, `tee1`, `tee2`, `scp1`, `scp2`, `sspm_1`, `sspm_2`, `gz1`, `gz2`, and unsuffixed `boot`, `dtbo`, and `vbmeta`. The live by-name listing instead exposes several differently named A/B entries (for example `lk_a/lk_b`, `tee_a/tee_b`, `scp_a/scp_b`, `boot_a/boot_b`, `dtbo_a/dtbo_b`, and `vbmeta_a/vbmeta_b`). Resolve these aliases through the actual init/device symlink setup and stock firmware before using them in a new fstab.

### Bring-up implications and unresolved work

- Use first-stage mount semantics for required logical partitions, consistent with the target Android release.
- Preserve correct slot selection and AVB chain relationships only after validating the target vbmeta topology.
- Determine whether the target ROM should retain or replace Xiaomi-specific `mi_ext` overlays and `cust` behavior.
- Reconcile the fstab's legacy partition aliases with the live A/B by-name map.
- Validate Android 15 encryption, metadata, F2FS, EROFS, rescue/cache, and Virtual A/B requirements before writing the final fstab.
- Do not use the stock fstab as a ready-to-flash Linsae fstab. Do not create flash instructions from this data.
