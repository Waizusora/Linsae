# AOSP source initialization

The initial platform target is Android 15. The project baseline is pinned to the AOSP manifest tag:

- `android-15.0.0_r36`

The tag is a source baseline, not a complete device build configuration. Re-evaluate the pin deliberately when updating the platform baseline.

## Initialize the source tree

On a Linux build host or a suitably provisioned GitHub Actions runner:

```sh
mkdir -p ~/android/linsae
cd ~/android/linsae
repo init -u https://android.googlesource.com/platform/manifest -b android-15.0.0_r36
repo sync -c -j"$(nproc)" --no-clone-bundle
```

The complete AOSP source tree is large. Do not run a full sync on a standard GitHub-hosted runner until storage, runtime, network limits, and caching have been evaluated.

## Local manifests

Device-specific repositories should be introduced through a reviewed local manifest under `.repo/local_manifests/`. Add entries only after confirming:

- repository ownership and availability;
- branch or commit compatibility with the selected Android baseline;
- exact device and kernel compatibility;
- license and redistribution requirements.

No device or kernel remote is pinned yet. This avoids embedding unverified source dependencies into the project.
