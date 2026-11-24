# Linsae

Linsae is an Android operating system project built around the Android Open Source Project (AOSP), with Android 15 as its initial platform target.

## Initial target

| Item | Value |
|---|---|
| Platform | Android 15 |
| Initial device | Xiaomi Redmi 12C |
| Device codename | `earth` |
| SoC family | MediaTek Helio G85 |
| Build orchestration | GitHub Actions |
| Product direction | AOSP-style system experience |

Device support is under development. The current repository establishes project structure and validation; it does not yet produce a flashable image.

## Repository layout

- `.github/workflows/` — repository validation workflows
- `device/xiaomi/earth/` — device bring-up notes and future product configuration
- `docs/` — architecture, development stages, and device research
- `manifest/` — AOSP source initialization and local manifest guidance
- `scripts/` — project consistency checks

## Development stages

1. Establish repository conventions and automated validation.
2. Pin the Android 15 source baseline and define reproducible source synchronization.
3. Verify Redmi 12C hardware identifiers, partition layout, boot chain, kernel source, and firmware requirements.
4. Implement device configuration and integrate required vendor components.
5. Bring up boot, display, touch, storage, connectivity, audio, camera, sensors, and power management.
6. Produce and validate installable builds, then expand device support.

## Build status

The initial GitHub Actions workflow checks repository metadata and documentation structure. It is not an Android compilation workflow. Full AOSP compilation and device image generation will be introduced after the source and hardware integration are verified.

## Contributing

Changes should be scoped, reproducible, and accompanied by validation. Do not add unverified device configuration, proprietary binaries, or guessed partition values.

## License

A project-wide license has not been selected yet. Individual upstream components retain their respective licenses and notices.
