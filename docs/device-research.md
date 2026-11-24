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
