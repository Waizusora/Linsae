# Project architecture

## Layers

Linsae is organized around the standard Android platform layers:

1. **AOSP platform** — framework, runtime, native services, system applications, and build system.
2. **Product configuration** — product makefiles, product packages, overlays, init configuration, and system properties.
3. **Device configuration** — board configuration, device makefiles, fstab, recovery/boot integration, and hardware-specific policies.
4. **Vendor integration** — device-specific proprietary interfaces and firmware, kept separate from generic platform configuration.
5. **Kernel** — the device-compatible Linux kernel source, configuration, modules, and boot image integration.

## Repository boundaries

- `device/xiaomi/earth/` is reserved for device-specific configuration.
- `vendor/xiaomi/earth/` is reserved for legally distributable device-specific vendor files or extraction metadata. Do not commit proprietary blobs without confirming redistribution rights.
- `kernel/` is reserved for the verified kernel source integration.
- `manifest/` documents source initialization and future local manifest entries.
- `.github/workflows/` runs lightweight repository checks.

The directories for kernel and vendor source are intentionally not populated until compatible upstream sources and licensing are verified.

## Build strategy

GitHub Actions is the orchestration layer. Workflows should be split by responsibility:

- repository validation and metadata checks;
- source synchronization and cache preparation;
- compilation on a runner with sufficient CPU, RAM, and disk;
- artifact inspection and publication.

A successful metadata check must never be reported as a successful Android build. Android compilation is a separate milestone and requires a suitably provisioned runner.
