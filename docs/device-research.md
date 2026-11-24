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

## Vendor init inventory

A directory listing of `/vendor/etc/init/hw/` was captured from the stock handset. It contains the following platform and project init configuration files:

- `init.mt6768.rc` and `init.mt6768.usb.rc`
- `init.project.rc` and `factory_init.project.rc`
- `factory_init.rc`
- `init.cgroup.rc`
- `init.sensor_1_0.rc`
- `init.modem.rc`
- Connectivity configuration: `init.connectivity.rc`, `init.connectivity.common.rc`, `init_connectivity.rc`, and corresponding factory/meta variants
- Meta/factory configuration: `meta_init.rc`, `meta_init.vendor.rc`, `meta_init.project.rc`, `meta_init.modem.rc`, and related connectivity files
- Diagnostic configuration: `init.aee.rc` and `init.ago.rc`

This inventory confirms that the stock vendor image supplies a substantial MediaTek init configuration layer. The filenames alone do not establish which services, properties, device nodes, or actions are required for an Android 15 device configuration. Inspect imports, service declarations, triggers, and executable dependencies before deciding what belongs in a Linsae device tree.
Do not copy the vendor init directory wholesale. In particular, factory/meta-mode actions, diagnostic services, USB policy, modem setup, and project-specific properties must be evaluated individually against the target build and the exact proprietary vendor image.

## Next init and ODM captures

Continue the read-only audit with:

```sh
adb shell ls -l /vendor/etc/init/
adb shell ls -l /odm/etc/
adb shell grep -nE '^(import|service|on |#.*import)' /vendor/etc/init/hw/init.mt6768.rc
adb shell grep -nE '^(import|service|on |#.*import)' /vendor/etc/init/hw/init.project.rc
```

If `grep` is unavailable in the host shell, run it through `adb shell` as shown. Review output for serial numbers or other identifiers before sharing. The next analysis should trace imported rc files and vendor services, not reproduce the full contents of large init scripts.


## Vendor init service and ODM inventory

A read-only directory listing from the stock Redmi 12C shows a substantial set of vendor init service fragments under `/vendor/etc/init/`. The observed service fragments cover, among others:

- Audio, Bluetooth, boot control, DRM, dumpstate, gatekeeper, GNSS, graphics allocator/composer, health, keymaster, media codec/OMX, memtrack, sensors, thermal, USB, Wi-Fi, and supplicant.
- MediaTek-specific services and support: AEE, modem/RIL, NVRAM, power, PQ, GPS/AGPS, connectivity, fuel gauge, and related vendor daemons.
- Xiaomi-specific services: display feature, misys, device information, and other Xiaomi hardware interfaces.
- Device-specific NFC configuration: `init.vnd_earth.nfc.rc`.
- Other fragments include camera HAL server, fingerprint, vibrator, lights, and vendor service manager configuration.

This is an inventory of filenames only. A service fragment being present does not prove that its service is enabled, registered in VINTF, or required by the target Android 15 build. Determine executable paths, service users/groups, triggers, SELinux domains, init imports, and VINTF declarations before integrating any service.

The `/odm/etc/` listing contains variant property files `build_earth.prop`, `build_earth_la.prop`, and `build_earth_p.prop`, as well as `build_aether.prop`. It also contains a camera configuration directory, an init directory, permissions, VINTF declarations, and device information QR configuration. The existence of multiple variant files requires checking which one is actually selected on this handset; do not merge all variant properties into one product configuration.

The attempted init-script grep did not produce results: the device shell returned `/system/bin/sh: syntax error: unexpected '('`. Treat the init action/import/service inventory as pending. Use simpler commands that avoid shell metacharacters or quote the expression carefully.

## Next read-only init and ODM inspection

Run these commands separately and share the output in batches:

```sh
adb shell ls -lR /odm/etc/init
adb shell ls -lR /odm/etc/vintf
adb shell ls -lR /odm/etc/permissions
adb shell ls -l /vendor/etc/init/hw
```

Then inspect the platform init file in manageable sections:

```sh
adb shell sed -n '1,180p' /vendor/etc/init/hw/init.mt6768.rc
adb shell sed -n '181,360p' /vendor/etc/init/hw/init.mt6768.rc
```

Do not paste serial numbers, IMEI/MEID, or account identifiers. Do not modify or execute any vendor init script.

### ODM init directory observation

The stock handset's `/odm/etc/init/` directory contains an `aether/` subdirectory with two service fragments:

- `android.hardware.nfc@1.2-service.rc`
- `android.hardware.secure_element@1.2-service-mediatek.rc`

The running handset reports product/device codename `earth`, while the observed ODM init fragments are stored under an `aether` directory. This is a directory-layout observation only; it does not establish that these fragments are imported or active for the earth variant. Verify ODM property selection, init imports, service executable availability, and matching VINTF declarations before considering NFC or secure-element integration.


### ODM VINTF manifest inventory

The stock handset's `/odm/etc/vintf/` directory contains five manifest files:

- `manifest_aether.xml`
- `manifest_dsds.xml`
- `manifest_qsqs.xml`
- `manifest_ss.xml`
- `manifest_tsts.xml`

This inventory confirms that multiple ODM VINTF manifest variants are present. Filenames alone do not identify which manifest is selected on the running `earth` device, nor do they establish which HAL instances are active. Inspect manifest contents and the device's VINTF assembly/selection mechanism before reusing any declarations.


### ODM permission feature inventory

The stock handset's `/odm/etc/permissions/` directory contains a `sku_aether/` subdirectory with seven XML feature declarations:

- `android.hardware.nfc.xml`
- `android.hardware.nfc.hce.xml`
- `android.hardware.nfc.hcef.xml`
- `android.hardware.nfc.uicc.xml`
- `android.hardware.se.omapi.uicc.xml`
- `com.nxp.mifare.xml`
- `com.nxp.nfc.xml`

These filenames indicate that NFC, host-card emulation, UICC-related NFC/Secure Element, and NXP/MIFARE feature declarations are present for the `sku_aether` directory. They do not prove those features are selected or supported by the running `earth` variant. Inspect XML contents and SKU selection before adding corresponding feature declarations to Linsae.


### MediaTek init configuration: `init.mt6768.rc` lines 1–180

The first 180 lines of the stock `/vendor/etc/init/hw/init.mt6768.rc` were inspected.

**Imports observed:** connectivity, MT6768 USB, project, AEE, VoLTE, MAL, sensor, AGO, ST NFC, and modem init fragments. The file explicitly states that `init.modem.rc` must be the final import and that no new imports should follow it. ST NFC is referenced from both `/vendor/etc/init/hw/` and `/system/etc/init/hw/`; actual file presence and import behavior must be checked before inferring whether both are used.

**Boot actions observed:**
- `early-init` writes boot profiling and MediaTek performance controls, mounts debugfs, and changes debugfs permissions.
- `init` creates legacy storage symlinks, a CD-ROM mountpoint, a bootdevice symlink, and applies permissions to MediaTek proc/sys nodes.
- `charger` runs filesystem checks and mounts cache/nvcfg, adjusts power and LED node permissions, and starts fuel-gauge and light services.
- `fs` starts `vendor.boot-hal-1-2`, invokes `mount_all /vendor/etc/fstab.mt6768 --early`, configures zram-related settings, mounts the vendor ISO image, and mounts the rescue partition.
- `post-fs` begins additional performance and proc-node permission configuration.

**Porting implications:** This file contains hardware-specific MediaTek kernel interfaces (including `/proc/perfmgr`, `/proc/bootprof`, DVFSRC sysfs paths, `/proc/lk_env`, and `/dev/spm`). These actions must not be copied wholesale into Linsae until the target kernel exposes the corresponding nodes and their expected semantics are verified. Service start commands are configuration evidence, not proof that the named services are available or running. The early fstab mount call is consistent with the previously captured MT6768 fstab; exact mount behavior and slot resolution still require verification.


### MediaTek init configuration: `init.mt6768.rc` lines 181–360

The next section of the stock MT6768 init file was inspected.

**Boot-region symlinks:** The init rules create aliases for `/dev/block/mmcblk0boot0` and `/dev/block/mmcblk0boot1`, then expose them as `preloader_a` and `preloader_b` through bootdevice and by-name paths. These are runtime init actions, not proof that the target Linsae kernel uses the same underlying block-device names. Verify the actual kernel block layout before adapting them.

**Late filesystem stage:** The `late-fs` trigger waits for `hwservicemanager.ready=true`, sets the userspace reboot userdata remount timeout, then invokes `mount_all /vendor/etc/fstab.mt6768 --late`. It also runs a `tune2fs` command against the userdata path. The exact effects and suitability of this command must be evaluated against the target filesystem and Android version before reuse.

**Post-fs-data directories:** The file creates vendor data directories for Silead/FPC fingerprint components, camera flash/shading/OTP/debug/flicker data, and other vendor components. It also adjusts ownership and SELinux labels for NVRAM-related mounts and creates radio and media support paths. These directory names are clues to vendor dependencies, not proof that every subsystem is present or active on the `earth` SKU.

**Kernel interface permissions:** The section applies permissions to MediaTek SCP/SSPM, Mali, touch-panel, M4U, CMDQ, MDP sync, GPS, SPM, and other proc/sys/device nodes. Some permissions are broad (including world-readable or world-writable modes). Do not transplant these rules blindly: validate node existence, driver semantics, service identities, SELinux policy, and least-privilege requirements on the target build.


### MediaTek init configuration: `init.mt6768.rc` lines 361–540

This section of the stock init file applies permissions and ownership to additional hardware interfaces.

**Subsystems observed:**
- Audio DSP and SmartPA: `/dev/audio_ipi`, `/dev/audio_scp`, and RT5509/MT6660 parameter sysfs nodes.
- Fingerprint: `/dev/goodix_fp`.
- Video codec: `/dev/vcu`, `/dev/video0`, `/dev/video1`, and vendor codec data directories.
- Sensors: MediaTek accelerometer/magnetometer sysfs paths and input-device attributes `input1` through `input10`.
- Display: framebuffer, MediaTek display manager, vsync, and sync device nodes.
- Bluetooth/input: `/dev/hid-keyboard` and `/dev/uinput`.
- Other interfaces: FM radio, HDMI/TV-out, secure device node, PMIC engineering interfaces, and diagnostic/baseband tools.

**Important uncertainty:** The init file references Goodix fingerprint, while the previously inventoried vendor data directories include Silead and FPC paths. This may reflect bundled support for multiple components or variants; it does not identify the active fingerprint hardware on this handset. Confirm against ODM properties, VINTF declarations, running services, device nodes, and kernel drivers.

**Porting implications:** The display, audio, codec, sensor, Bluetooth, and security nodes are useful clues for later HAL and kernel bring-up. Do not copy the permission rules wholesale. Confirm node existence and driver behavior, service UID/GID, SELinux labels and policy, and whether each interface is actually used on the `earth` variant.


### MediaTek init configuration: `init.mt6768.rc` lines 541–720

This section configures additional device nodes and reaches the `zygote-start`, `early-boot`, and `boot` triggers.

**Camera and imaging interfaces:** The rules cover camera ISP/SYSRAM/DIP/DPE/TSF/MFB/RSC/OWE/FDVT/WPE/PipeMgr nodes, sensor interface (`seninf`), flashlight, camera calibration, autofocus, CCU, and VPU. Most are assigned to the `camera` group. These names provide a useful driver inventory, but actual camera HAL compatibility, sensor modules, calibration data, and kernel interfaces remain unverified.

**Other multimedia interfaces:** The section includes MDP, SMI, DFRC, scheduler, ANC, voice-wakeup, and MATV nodes, along with thermal and power data-directory creation. The thermal directories include `/data/vendor/thermal/`, `/data/vendor/thermal/config/`, and `/data/vendor/.tp/`.

**Sensitive partition interfaces:** Permission changes are applied to MTD-style paths for security, preloader, pro_info, boot image, recovery, NVRAM, seccfg, and misc. These rules must not be copied into a new ROM without understanding the underlying device nodes, access requirements, SELinux policy, and security implications.

**Boot triggers observed:** The file writes boot-profiler markers at `zygote-start`, `early-boot`, and `boot`; the `early-boot` trigger also calls `verity_update_state`. The `boot` trigger begins additional VM, power, and LED permission tuning.

**Porting implications:** Camera and thermal are likely major bring-up work areas. Confirm active hardware and services using ODM/VINTF selection, vendor service declarations, device nodes, kernel driver configuration, and runtime service state rather than relying on init filenames alone.


### MediaTek init configuration: `init.mt6768.rc` lines 721–900

This section is primarily performance, CPU, touch-panel, power, and kernel-interface permission setup.

**CPU and scheduling:** It configures CPU hotplug and cpufreq policy nodes, runqueue statistics, HMP controls, CPU loading controls, and CPU frequency limits. The file references `policy0` and `policy6`, but the target kernel's cpufreq topology must be inspected rather than inferred from these names.

**MediaTek PPM and performance manager:** Numerous `/proc/ppm/` nodes configure policy limits, CPU frequency/core limits, DVFS tables, and HICA settings. Additional `/proc/perfmgr/` and `/proc/fliperfs/` nodes configure performance and bandwidth-monitor behavior. These interfaces are kernel-specific and should not be carried over without matching driver support and verified semantics.

**Touch and display controls:** The rules include Huaqin panel information, Novatek pocket/palm and edge rejection controls, FocalTech touch-controller attributes, and touchscreen self-test. These are evidence of available stock integration paths, not confirmation that every listed interface is used by the running `earth` unit.

**Power and diagnostics:** The section also adjusts LED controls, hibernation-related nodes, Smartbook state, DCM state, and selected network diagnostic proc entries.

**Porting implications:** Treat the CPU policy, PPM, HMP, perfmgr, bandwidth monitor, and touch-controller rules as stock-kernel-specific. Before adapting any rule, verify the target kernel's actual node paths, CPU topology, driver implementation, ownership requirements, SELinux labels, and Android power/performance HAL integration.

### MediaTek init configuration: init.mt6768.rc lines 901–1080

This section continues the stock MT6768 init configuration with runtime triggers, thermal and Wi-Fi controls, scheduler tuning, battery properties, and display services.

**Network and modem diagnostics:** The file adjusts ownership for selected /proc/net/ netfilter/iptables entries, WMT diagnostic nodes, and USB serial gadget ports /dev/ttyGS0 through /dev/ttyGS3. These are diagnostic and modem/connectivity interfaces; their presence in init does not establish that each port is active in the selected product configuration.

**Thermal service:** On sys.boot_completed=1, init starts mi_thermald and changes ownership of /sys/class/thermal/thermal_message/sconfig. This identifies a vendor thermal daemon dependency. Inspect its service declaration, executable, configuration files, SELinux domain, and thermal HAL relationship before deciding how Linsae should provide thermal management. Do not assume the daemon alone is a complete thermal solution.

**Wi-Fi SAR:** Properties vendor.sysctl.tx=0..3 trigger /vendor/bin/iwpriv wlan0 driver "SET_PWR_CTRL MySar N". This is a MediaTek/vendor-driver-specific transmit-power control path. Preserve it only if the selected Wi-Fi driver, firmware, property producer, and command syntax are verified compatible.

**Boot and storage tuning:** After boot completion, init adjusts queue statistics, read-ahead, and request counts for mmcblk0, sdc, and several device-mapper nodes. Device-mapper node numbers are runtime allocations and must not be treated as stable partition identities. Any replacement tuning must identify the actual block devices and be justified by measurements on the target kernel.

**CPU scheduler and EAS:** The boot-completed action enables the vendor EAS control, adjusts scheduler tunables, clears several MediaTek performance-manager boot-boost controls, requests DDR OPP reset, and switches policy0 and policy6 to schedutil. These writes depend on MediaTek-specific kernel interfaces and the stock CPU topology. Do not copy them into Linsae until kernel configuration, exposed sysfs/proc nodes, cpufreq policies, and the Android power HAL integration are verified.

**Battery and fuel gauge:** Properties under persist.vendor.mediatek.fg.* change fuel-gauge daemon behavior, force a reported 25°C state, or increase logging. These are vendor debug/control hooks. Do not expose or enable test overrides in production builds; verify the actual battery driver and fuel-gauge service behavior first.

**Display feature:** The file declares a displayfeature service using /system/bin/displayfeature, running as root in late_start. The supplied output ends at the next trigger, on property:init.svc.surfaceflinger=stopped, so the service's remaining actions and the rest of the init file have not yet been captured.

**Porting implications:** This section reinforces that stock performance, thermal, Wi-Fi SAR, battery, and display behavior relies on vendor daemons and MediaTek kernel extensions. Treat the init script as an inventory of dependencies, not a ready-to-use Android 15 configuration. Validate each service against its executable, init imports, VINTF declarations, SELinux policy, kernel driver, and runtime state.

### MediaTek init configuration: init.mt6768.rc lines 1081–1260

This section exposes additional service definitions and lifecycle dependencies in the stock vendor init configuration.

**DisplayFeature lifecycle:** Init stops the displayfeature service when SurfaceFlinger is stopped or restarting, and starts it when SurfaceFlinger is running. This indicates an explicit dependency on SurfaceFlinger lifecycle. The service implementation, interface, property controls, SELinux domain, and compatibility with Android 15 must be inspected before considering integration.

**Thermal daemon definition:** The file defines mi_thermald at /system/vendor/bin/mi_thermald, running as root under the dedicated SELinux domain u:r:mi_thermald:s0, disabled by default and started by the earlier boot-completed action. This confirms the executable path and declared security context in the stock init configuration, but not its runtime health or complete thermal policy. Inspect its configuration, dependencies, service logs, and thermal HAL relationship.

**Factory and diagnostic services:** meta_tst and factory_no_image are declared disabled/oneshot services with AT command sockets and elevated capabilities. A property gate starts meta_tst only when sys.boot_completed=1 and ro.boot.atm=enable. These are factory/diagnostic paths and must not be enabled as ordinary user-facing services. Their privileged capabilities and sockets require particular security scrutiny.

**Charge logger:** charge_logger is declared as a disabled oneshot service and started after boot completion. Its role appears to be vendor charge logging; establish whether it is required for battery functionality or only diagnostics before retaining it.

**Kernel module:** An on-boot action runs insmod on /vendor/lib/modules/fpsgo.ko. This creates a direct dependency on a compatible FPSGO kernel module and its dependencies. Verify module ABI, kernel configuration, signing/loading policy, and whether the module is needed by the target kernel before adapting the action.

**Other vendor services:** The file declares an OSI/VSIM service and an initprop_bin helper triggered by vendor.service.nvram_init=Ready. The latter indicates a dependency on NVRAM initialization state. Service availability and relevance to the earth SKU remain unverified.

**Sensitive identity properties:** Several property triggers copy persistent ODM RIL values into read-only RIL properties, including device serial/IMEI and Wi-Fi/Bluetooth MAC-related identifiers. This documents an identity-property flow only. Do not collect, publish, or hardcode actual identifier values in project files, logs, or build configuration.

**Porting implications:** The init file contains factory-only services, privileged diagnostic sockets, identity-property handling, a kernel module load, and vendor display/thermal integration. These are not generic AOSP requirements. Audit each service's binary, imports, property namespace, SELinux policy, VINTF declaration (if applicable), and runtime state. Do not enable factory services or copy privileged capabilities by default.

The complete init.mt6768.rc file has now been captured and reviewed through its final line. A subsequent `wc -l` check reported 1311 total lines; therefore, there is no content after line 1311 and the earlier request for lines 1312–1440 covered an empty range.


### MediaTek init configuration: init.mt6768.rc lines 1261–1440

This section completes several factory-mode helper declarations and adds headset and charging-display controls.

**Factory helper services:** The file declares `maxcurrentIncall`, `headset_in_screenmode`, and `headset_out_screenmode`, each invoking `/system/vendor/bin/factory_bin` with a short command/argument pair. All three are `disabled` and `oneshot`, so their declarations do not make them ordinary boot-start services. The headset helpers are started by property triggers when `persist.audio.headset.plug.status` changes to `on` or `off`. The executable's command semantics and the producer of this property remain unverified.

**Mishow charging control:** The file declares `mishow_start` and `mishow_stop`, which invoke `/vendor/bin/mishow.sh` with arguments `1` and `0`. They run as user/group `system`, are disabled/oneshot, and specify SELinux domain `u:r:mishow:s0`. Property `vendor.charge.mishow.ctl` starts the corresponding helper, while `persist.vendor.battery.mishow=true` sets the control property to true. This establishes a property-driven vendor charging feature, but does not prove that the script exists, the domain is defined in the active policy, or the feature is selected for this SKU.

**Porting implications:**
- Do not add the factory_bin helpers to normal boot startup. First identify whether their property triggers are emitted by an active vendor component and whether the commands affect user-visible behavior.
- Treat headset screen-mode behavior as optional vendor integration, not a prerequisite for audio routing. Verify the property producer, audio policy, and display behavior before adapting it.
- Treat Mishow as an optional charging/UI integration. Verify the script, its invoked binaries, property ownership, SELinux type enforcement, and compatibility with the target battery/charger implementation.
- Do not copy the SELinux domain declaration as a substitute for a complete policy. A matching domain, file labels, property contexts, and allowed transitions/accesses must all be validated.

The supplied capture covers lines 1261–1440. The total file length has not yet been confirmed, so any content after line 1440 remains pending inspection.


## MediaTek project init configuration: init.project.rc (174 lines)

The complete stock `/vendor/etc/init/hw/init.project.rc` was captured from the Redmi 12C. It contains project-level module loading, ODM imports, device-node permissions, USB OTG storage, vendor helper services, and touch controls.

### SKU-based ODM service imports

The file imports NFC and MediaTek Secure Element init fragments using `${ro.boot.product.hardware.sku}` under `/vendor/odm/etc/init/`. The handset's previously captured SKU property is `earth`, while the directory inventory previously showed an `aether/` directory. This is an unresolved discrepancy. Verify the resolved runtime path, symlinks, actual files, and import errors before deciding whether NFC or Secure Element services are available for this SKU. An import statement alone does not prove that the referenced service starts or registers successfully.

### Kernel module and tracing

An `early-init` action invokes `modprobe -a -d /vendor/lib/modules trace_mmstat.ko` under SELinux domain `vendor_modprobe`. After `sys.boot_completed=1`, the file creates a tracefs instance named `mmstat`, configures its buffer, enables the `mmstat` event, and turns tracing on. This depends on a compatible kernel module, tracefs support, event availability, and SELinux permissions. It is diagnostic/performance instrumentation, not a generic AOSP boot requirement.

### Device-node permissions and hardware clues

The post-fs-data action changes permissions/ownership for:
- `/dev/fpsensor` and several SPI fingerprint sysfs attributes.
- Multiple camera autofocus nodes, including MAINAF/SUBAF and named actuator interfaces.
- SMB screen communication, SPM, SAR, touch palm-sensor, flashlight, and QVGA depth-light nodes.
- The vendor `metis` device and module parameter path.

These paths provide clues about bundled fingerprint, camera, touch, SAR, and auxiliary hardware support. They do not establish which components are physically present or active on the exact earth handset. Some listed paths may belong to alternative board/component variants. Verify node existence, kernel drivers, runtime HALs, service access, and SELinux labels before creating device permissions. Do not copy broad permissions or the unusual metis ownership commands without checking their exact semantics.

### USB OTG storage
The file creates `/mnt/media_rw/usbotg` and `/storage/usbotg`, then declares a disabled `fuse_usbotg` service using `/system/bin/sdcard`. This is an optional vendor USB-OTG storage path. Validate Android 15 storage/FUSE architecture, vold integration, USB host support, and mount lifecycle before adapting it.

### Vendor helper services

- `setsarcal` runs `/system/vendor/bin/setsarcal.sh` as root, oneshot, with SELinux domain `meta_tst`.
- `panel-info-sh` runs `/vendor/bin/init.panel_info.sh` as root, oneshot, also using `meta_tst`; it is started after boot completion.
- `service_nv_protect` runs `/vendor/bin/misc_writer --nv_protect`, disabled/oneshot, and is started by property `vendor.service_nv_protect=start`.

These are vendor-specific calibration, panel-information, and NV-protection helpers. Verify binary/script presence, property producers, SELinux policy, and whether the function is required for normal operation. Do not enable diagnostic-domain services by default or reproduce privileged behavior without a security review.

### Touch edge/grip controls

Three groups of property triggers react to `sys.tp.grip_enable` values `0`, `90`, and `270`. They write different mode values to:
- `/proc/nvt_edge_reject_switch`
- FocalTech `fts_edge_mode`
- Another touch driver's `misc/edge_restain`

This indicates support for multiple possible touch-controller interfaces and orientation-dependent edge rejection. The active driver and exact value semantics remain unverified. Do not assume all three interfaces exist on the same handset or copy all triggers into a target device tree.

### Porting conclusions

The project init file adds evidence for dynamic SKU-based ODM selection, optional NFC/Secure Element integration, MediaTek trace instrumentation, fingerprint/camera/touch/SAR interfaces, USB OTG FUSE storage, and vendor calibration/NV helpers. These should be treated as audit leads rather than ready-to-port configuration. The next useful checks are the resolved SKU import paths and actual active hardware/service state; no device makefiles or init rules should be generated from these declarations alone.


## ODM SKU resolution: earth handset versus aether NFC variant

Runtime checks on the user's Redmi 12C report `ro.boot.product.hardware.sku=earth`. The directory `/vendor/odm/etc/init/` contains only `aether/`; `/vendor/odm/etc/init/earth/` does not exist. The two ODM init fragments for NFC and MediaTek Secure Element are present only in `aether/`. ODM product properties identify the handset as Redmi / `earth` / `earth_global` / model `22120RN86G`.

The user confirms this Redmi 12C unit has no NFC; a related Poco variant has NFC. This supports treating the `aether` NFC/Secure Element configuration as variant-specific and excluding it from the baseline `earth` device configuration. Do not copy or enable those NFC/SE services for the non-NFC earth unit.

The stock `init.project.rc` uses SKU-substituted imports under `/vendor/odm/etc/init/${ro.boot.product.hardware.sku}/`, which resolve to a missing `earth/` path on this unit. The exact init behavior for missing imported files and any resulting boot-time log messages have not yet been verified. Check relevant init logs before deciding whether the missing imports are harmless or require a guarded/variant-specific adaptation. Do not alter stock partitions or attempt to create the missing directory on the running device.


### Runtime log check for the missing earth ODM import path

A filtered `logcat -b all -d` query was run after observing that the SKU-expanded ODM import path points to the absent `/vendor/odm/etc/init/earth/` directory. The returned output contained numerous unrelated `ENOENT` messages from framework/vendor components (including PinnerService, LockSettingsStorage, libPowerHal, and libprocessgroup), but no explicit init import error matching the filter. This is inconclusive: the output does not prove the import succeeded, that init silently ignored it, or that the missing files have no boot impact. A narrower init-tag/log query and runtime NFC feature/service checks are still required. Do not attribute the unrelated ENOENT messages to the ODM import.


### NFC runtime capability check on the earth unit

The user ran all three checks with empty output:
- filtered init log query (`logcat -b all -d -s init`);
- `pm list features | grep -i nfc`;
- `service list | grep -i nfc`.

Together with the confirmed `earth` SKU, absence of an `earth/` ODM init directory, NFC/Secure Element init fragments only under `aether/`, and the user's confirmation that this Redmi 12C unit has no NFC, the device baseline should be treated as **no NFC support**. Do not declare NFC package features or include NFC/Secure Element services in the earth device configuration. Empty filtered logs alone do not establish the precise init handling of the missing imports; they only show no matching message was returned by that check.


## MediaTek USB gadget configuration: init.mt6768.usb.rc (940 lines)

The complete stock `/vendor/etc/init/hw/init.mt6768.usb.rc` was captured in four ranges and reviewed through line 940. The script configures a ConfigFS USB gadget around the MediaTek `musb-hdrc` controller. It is a vendor policy inventory, not a drop-in Android 15 USB configuration.

### ConfigFS gadget and functions

The earlier sections (lines 1–480) establish the ConfigFS gadget at `/config/usb_gadget/g1`, use the `musb-hdrc` UDC, and create FunctionFS and vendor functions including ADB, MTP, PTP, RNDIS, MIDI, Android Accessory, Audio Source, ACM serial, mass storage, HID, and MediaTek VIA modem/diagnostic channels. The init rules select combinations using `sys.usb.config`, `sys.usb.ffs.ready`, `vendor.usb.acm_*`, and product-ID properties. Several vendor-specific VID/PID and ACM combinations are present.

The script also configures charger-mode HID, resets gadget links for `none`, and applies MediaTek controller power-saving settings. USB function availability depends on the matching kernel ConfigFS functions, FunctionFS userspace services, gadget controller, property triggers, and SELinux policy. Do not copy vendor VID/PID values or every function combination into Linsae without verifying the intended product identity and host interoperability.

### Mass storage, BICR, and ACM routing (lines 481–720)

The middle section adds:
- `via_bypass` combinations with VIA modem, ETS, ATC, ADB, and optional ACM serial ports.
- `mass_storage` and `mass_storage,adb` gadget configurations.
- `bicr` and `bicr,adb` configurations that expose `/dev/block/loop0` as a CD-ROM LUN.
- Dynamic ACM port selection using `persist.vendor.radio.port_index`, including single and paired `gs0`–`gs3` mappings.

The ACM mapping is tied to the vendor radio/modem integration. Mass-storage and BICR are legacy/vendor gadget modes and are not baseline requirements for a modern Android 15 device configuration. Do not expose arbitrary block devices or copy loop-device rules without a reviewed security and storage design.

### Test, charging, PHY, and raw-bulk controls (lines 721–940)

The final section adds:
- More dual-ACM combinations: `gs0+gs1`, `gs0+gs3`, and `gs1+gs3`.
- Android Test Mode gadget configurations `atm_gs0` and `atm_gs0gs3`, including MTP, ADB, and ACM.
- A gadget cleanup path that disconnects the UDC, removes function symlinks, and removes the RNDIS function directory.
- Charging-related `cdp`, `charging_yes`, and `charging_no` property handling, including MediaTek UDC `cmode`.
- BICR controls through legacy `android_usb` sysfs paths.
- USB/UART port switching through `/sys/devices/platform/mt_usb/portmode`.
- USB PHY engineering controls under `/proc/mtk_usb/usb-phy0/u2_phy/`.
- MediaTek raw-bulk channel enable/disable controls for GPS, PCV, ATC, ETS, and data.
- USB electrical test modes (SE0 NAK, J, K, and test packet), plus vendor test/printk property forwarding.

These are factory, engineering, modem, and platform-specific controls. They must not be exposed to ordinary users or enabled by default without a security review and confirmed kernel/property dependencies.

### USB gadget versus USB host and external DAC

This init file primarily describes the phone acting as a USB peripheral (gadget) connected to a host computer. Its `audio_source.gs3` gadget function is not evidence of USB host audio support.

The user reports successfully using a USB-C-female-to-Micro-USB adapter/converter to connect an external USB DAC to this stock handset. Record this as a required real-device compatibility test for Linsae, not as proof that the gadget init rules implement it.

External DAC operation must be validated separately across:
- USB host/OTG controller and role switching, including VBUS power delivery.
- Kernel USB host and USB Audio Class driver support.
- Android USB device enumeration, audio policy, USB audio HAL/framework routing, and permission behavior.
- Suspend/resume, reconnect, and power-management behavior.

USB OTG storage and external USB DAC are separate test cases. The presence of a vendor `fuse_usbotg` service elsewhere in project init does not establish complete Android 15 host-storage or USB-audio compatibility.

### Linsae integration priorities

For the initial earth bring-up, prioritize standard ADB and MTP, then verify PTP and RNDIS as needed. Preserve USB host/OTG and external USB DAC as explicit hardware validation requirements. Treat MIDI and Android Accessory as optional until tested. Defer mass-storage/BICR gadget modes, VIA bypass, ACM multiport, ATM, raw-bulk engineering controls, PHY tuning, and USB electrical test modes unless a demonstrated product requirement and matching kernel/vendor support justify them.

Do not transplant the 940-line stock rc wholesale. Reconcile the Android 15 USB framework and init configuration with the actual kernel ConfigFS functions, UDC, HAL/services, property contexts, SELinux policy, and exact vendor firmware. No USB device makefiles, init fragments, or flashable images should be generated from this inventory alone.


## USB kernel and Android runtime observations

Read-only diagnostics were captured from the stock Redmi 12C while no USB peripheral was connected.

### Kernel and controller

- `uname -a` reports Linux `4.19.191-perf-ga3711314e5c2`, built for `aarch64`.
- `ro.kernel.version` reports `4.19`.
- The UDC class exposes `musb-hdrc`, linked under the MediaTek `mt_usb` platform device.
- The USB platform-driver directory lists `mt_usb`, `mtk-extcon-usb`, `musb-hdrc`, and `usb_phy_generic`.
- The USB sysfs bus listing exposes the root hub `usb1` and its root-hub interface.

### Loaded USB-related modules

The captured `/sys/module` listing includes:
- `snd_usb_audio`
- `usbcore`
- `musb_hdrc`
- `usb20` and `usb20_host`
- `usb_storage`
- `usbhid`
- `usb_f_mtp` and `usb_f_rndis`
- `usb_boost`
- `c2k_usb`

This is evidence that the stock kernel has loaded USB Audio, USB core, MUSB, host, storage, HID, and selected gadget-related components. It does not by itself prove that a given module is built-in versus loadable in every build, that all host functions are operational, or that Android audio routing is correctly integrated.

### Android USB manager snapshot

The captured `dumpsys usb` reports:
- Current gadget function: `MTP`; function application marked true.
- No USB device connection and no host connection at capture time.
- USB port advertises `supported_modes=dual`.
- Current port mode is `none`, with no power or data role active.
- `can_change_mode`, `can_change_power_role`, and `can_change_data_role` are false in this disconnected snapshot.
- USB HAL version 13.
- ALSA manager reports `cards_parser=-1` in this snapshot.

These are runtime observations while disconnected. They do not establish that host mode is unavailable; role-change capability and USB audio enumeration must be checked with an actual attached peripheral and the correct cable/adapter.

### USB audio and OTG validation requirements

The loaded `snd_usb_audio` module, together with the user's report of successfully using an external USB DAC through a USB-C-female-to-Micro-USB adapter/converter on stock firmware, provides evidence supporting USB Audio Class host-mode testing as a device requirement.

Before declaring Linsae USB DAC support, test with a known-working DAC and adapter:
1. Verify host role transition and VBUS power when the DAC is connected.
2. Inspect USB enumeration and kernel logs for the DAC; record vendor/product IDs only if they are not personal identifiers.
3. Check ALSA card/device creation and USB audio interface formats.
4. Confirm Android USB audio routing through AudioFlinger/audio policy and actual playback.
5. Test disconnect/reconnect, screen-off playback, suspend/resume, and power stability.

Keep USB host storage and USB DAC as separate validation cases. A loaded kernel module is necessary evidence, not proof of complete Android framework/HAL integration. Do not write USB role-switch or audio policy configuration until the actual connected-device behavior and kernel interfaces have been inspected.

### Connected USB DAC enumeration and Android audio snapshot

A follow-up capture was taken with the user's KT-384/32 HIFI USB DAC attached through the known-working OTG adapter. This confirms host-mode enumeration and Android USB/ALSA recognition, but does not yet confirm active AudioFlinger output routing.

**USB host and port state:**
- `host_connected=true`.
- Port mode is `dfp` (downstream-facing/host), with power role `source` and data role `host`.
- `connected=true` is reported by the USB port manager.
- Android USB manager lists the attached DAC at `/dev/bus/usb/001/003`.
- The current USB gadget function remains MTP; that gadget setting is separate from the phone's host-side DAC connection.

**Enumerated USB audio device:**
- Product string: `KT-384/32 HIFI`; manufacturer string: `KTMicro`.
- USB IDs observed: vendor `0x31B2` and product `0x0111`.
- USB configuration exposes Audio Class interfaces for playback and capture, plus a HID interface.
- Android USB host manager records the device as supporting both input and output audio.

**ALSA/USB audio manager:**
- `alsa_manager.cards_parser=0`.
- Android reports ALSA card `1`, device `0`, named `USB-Audio - KT-384/32 HIFI`.
- `has_output=true` and `has_input=true`.
- Direct reads of `/proc/asound/cards` and `/proc/asound/pcm` from the shell were denied with `Permission denied`. Treat this as a shell-access restriction; the USB manager's ALSA parser independently reports the recognized card/device.

**AudioFlinger snapshot and USB Direct playback result:**

The first AudioFlinger capture, taken while the DAC was attached, reported:
- `USB audio module: No output streams` and `No input streams`.
- The visible primary mixer output thread was routed to `AUDIO_DEVICE_OUT_SPEAKER`, not the USB device.

The user clarified that the player was operating in **USB Direct mode** and confirmed that audio was physically audible through the external DAC. The accompanying AudioFlinger capture still showed no USB output streams in the USB audio module, while the visible mixer threads remained routed to the speaker. This is not sufficient evidence of a failure: a direct/exclusive playback path may not appear as a normal AudioFlinger mixer output stream. The precise direct-playback implementation is not established by these dumps.

**Confirmed at this stage:**
- USB host role transition and VBUS source operation.
- Enumeration of the KT-384/32 HIFI USB Audio device.
- Android USB host manager recognition of playback and capture interfaces.
- ALSA manager recognition of card 1, device 0, with output and input capability.
- Audio policy exposure of USB headset input/output ports and dynamic PCM profiles up to 192 kHz.
- Successful audible playback through the DAC using the player's USB Direct mode, as confirmed by the user.

**Still unverified:** ordinary Android shared/mixer playback routing to the DAC, capture/input recording through the DAC, supported format negotiation in each playback mode, and reconnect/suspend/resume behavior. Do not infer these from USB Direct playback alone.

For future validation, test shared-mode playback separately from USB Direct mode, then test recording, disconnect/reconnect, screen-off playback, and suspend/resume. Capture AudioFlinger and audio-policy state during each test; redact device serial numbers and other identifiers before sharing.

### Shared/mixer playback routing to the external USB DAC

A subsequent capture was taken while testing ordinary player playback with USB Direct disabled. AudioFlinger showed a live primary-module mixer output thread routed to the connected USB DAC:

- Thread: `AudioOut_15`, type `MIXER`.
- I/O handle: `21`.
- `Standby: no`.
- HAL sample rate: `48000 Hz`.
- Output device: `0x4000000 (AUDIO_DEVICE_OUT_USB_HEADSET)`.
- `Total writes: 17644`.
- Last write was reported 61 ms before the capture.
- The thread reported `Blocked in write: yes` in the supplied snapshot; this is a transient thread-state observation and is not by itself evidence of a playback fault.
- AudioFlinger local history recorded creation of an audio patch from the speaker route to `AUDIO_DEVICE_OUT_USB_HEADSET`, followed by release/recreation events as playback and routing changed.
- The USB audio module section continued to report no separate output streams. The active USB route was visible instead in the primary audio module's mixer thread.

This establishes that Android's shared/mixer path can open an output thread and submit audio writes to the USB headset device on the stock firmware. It is distinct from the previously confirmed USB Direct playback path. Physical audibility during this particular shared-mode test should be recorded separately if not explicitly confirmed by the tester.

**Updated USB DAC status:** USB host enumeration, USB Direct playback, and AudioFlinger shared/mixer routing to the USB headset are evidenced. Recording/input, format negotiation across modes, disconnect/reconnect, and suspend/resume remain unverified.


### User confirmation: audible USB DAC playback in both modes

The user explicitly confirmed that audio is physically audible through the connected KT-384/32 HIFI DAC in both:
- USB Direct mode.
- Ordinary playback with USB Direct disabled (shared/mixer mode).

This closes the earlier physical-audibility uncertainty for shared/mixer playback. The stock Redmi 12C baseline therefore has confirmed audible external USB DAC playback in both tested modes. This does not yet validate recording/input, every advertised sample format/rate, hot-unplug/reconnect, or suspend/resume behavior.

### USB DAC hot-unplug/reconnect and playback recovery

A further read-only USB manager capture was taken after repeatedly disconnecting and reconnecting the user's KT-384/32 HIFI USB DAC. The capture was sanitized to remove the USB serial-number line before sharing.

**Current host and device state after reconnect:**
- `host_connected=true` and `source_power=true`.
- USB port reports `connected=true`, `current_mode=dfp`, `power_role=source`, and `data_role=host`.
- The device is enumerated again as `KT-384/32 HIFI`, manufacturer `KTMicro`, with the previously observed USB vendor/product IDs.
- Android USB Audio/ALSA manager again recognizes card `1`, device `0`, with `has_output=true` and `has_input=true`.
- The USB device address changed after re-enumeration, consistent with a fresh USB enumeration.
- The USB host connection history contains multiple connect/disconnect records. The current device remains connected at the time of capture.

**Playback recovery test:**

The user explicitly confirmed that after unplugging and reconnecting the DAC, audio output resumes without closing or restarting the music-player application.

This verifies the following stock-firmware behavior for the tested DAC and adapter:
1. USB host role and VBUS source operation remain functional across reconnection.
2. The DAC is enumerated again by Android USB host manager.
3. Android USB Audio/ALSA manager recreates recognition of the playback/capture device.
4. Playback resumes without restarting the player application.

This is a successful hot-unplug/reconnect and playback-recovery test for this specific DAC/adapter and handset firmware. It does not establish behavior for every USB DAC, adapter, power load, player application, audio format, or suspend/resume cycle. Recording/input and screen-off suspend/resume remain unverified.
