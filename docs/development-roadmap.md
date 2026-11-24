# Development roadmap

## Stage 0 — Repository foundation

- [x] Create the project repository and initial documentation.
- [x] Add lightweight GitHub Actions validation.
- [ ] Verify all project metadata and workflow checks.

## Stage 1 — Source baseline

- [ ] Confirm the Android 15 release tag used by the project.
- [ ] Document the exact `repo init` and synchronization procedure.
- [ ] Establish a reproducible local-manifest mechanism.
- [ ] Record source revision and toolchain provenance.

## Stage 2 — Redmi 12C hardware audit

- [ ] Confirm the exact device variant and codename from the device.
- [ ] Record product name, board/platform identifiers, Android version, and vendor security patch.
- [ ] Record bootloader state, boot image format, partition map, dynamic partition status, and AVB configuration.
- [ ] Identify the exact kernel source branch and matching stock firmware baseline.
- [ ] Inventory hardware components and required vendor interfaces.

## Stage 3 — Device configuration

- [ ] Add verified device configuration and product makefiles.
- [ ] Integrate the matching kernel source and defconfig.
- [ ] Prepare vendor extraction metadata and proprietary interface declarations.
- [ ] Validate boot image and recovery integration.

## Stage 4 — Hardware bring-up

- [ ] Boot to userspace.
- [ ] Validate display, touch, storage, and charging.
- [ ] Validate Wi-Fi, Bluetooth, telephony, and mobile data.
- [ ] Validate audio, camera, sensors, GPS, and power management.
- [ ] Review SELinux denials and enforce enforcing mode.

## Stage 5 — Reproducible builds

- [ ] Define runner capacity and disk strategy.
- [ ] Add staged source-sync and build workflows.
- [ ] Publish checksums and build metadata with artifacts.
- [ ] Test installation, update, recovery, and rollback procedures.

No stage should be marked complete without logs or other reproducible evidence.
