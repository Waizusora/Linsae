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
