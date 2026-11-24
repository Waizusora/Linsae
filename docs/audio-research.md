# Audio Research — Redmi 12C (earth)

**Research status:** stock-firmware runtime and configuration inventory  
**Device:** Xiaomi Redmi 12C, codename `earth`  
**Platform:** MediaTek MT6768  
**Stock software:** Android 14, build `V816.0.16.0.UCVMIXM`  
**Research date:** 2026-11-24

## Scope and confidence

This document records observations collected from the stock device using ADB. It distinguishes static declarations from services observed running and behavior verified through physical playback. It is a research baseline, not a ready-to-flash audio implementation.

## Audio HAL and service architecture

The merged vendor VINTF manifest at `/vendor/etc/vintf/manifest.xml` declares:

- `android.hardware.audio@7.0::IDevicesFactory/default`, HIDL over hwbinder.
- `android.hardware.audio.effect@7.0::IEffectsFactory/default`, HIDL over hwbinder.

The manifest root reports version 4.0 and `target-level="5"`. This target level is recorded as a VINTF declaration and should not be interpreted by itself as an Android release identifier.

The vendor init fragment `/vendor/etc/init/android.hardware.audio.service.mediatek.rc` declares `vendor.audio-hal`, launched as:

```text
/vendor/bin/hw/android.hardware.audio.service.mediatek
```

The service runs as user `audioserver`, class `hal`, with audio-related groups, `BLOCK_SUSPEND` and `SYS_NICE` capabilities, real-time I/O priority configuration, task profiles, and an `audio_hw_socket` socket. Its `onrestart` action restarts `audioserver`.

The process list showed both `android.hardware.audio.service.mediatek` and `audioserver` running. Framework service listing also showed `android.media.IAudioService`, `android.media.IAudioFlingerService`, and `android.media.IAudioPolicyService`.

An `lshal` query emitted warnings that the Audio 7.0 factory interfaces could not be fetched from the service manager. Those warnings are not sufficient to conclude that the HAL is absent or broken: the merged VINTF declaration and running vendor process were independently observed.

## Audio Policy configuration

The vendor directory contains several policy files, including:

- `/vendor/etc/audio_policy_configuration.xml`
- `/vendor/etc/usb_audio_policy_configuration.xml`
- `/vendor/etc/usb_audio_accessory_only_policy_configuration.xml`
- Bluetooth policy variants, including A2DP, Bluetooth, offload, and legacy configurations.
- `/vendor/etc/audio_policy_volumes.xml`
- Legacy `/vendor/etc/audio_policy.conf`

### Dedicated USB policy

`usb_audio_policy_configuration.xml` declares module `usb`, HAL version 2.0, and the following mixports:

- `usb_accessory output`: PCM 16-bit, 44.1 kHz, stereo.
- `usb_device output`: output mixport with FAST flag.
- `usb_device input`: input mixport with FAST flag.

Its device ports include:

- `USB Host Out` — `AUDIO_DEVICE_OUT_USB_ACCESSORY`.
- `USB Device Out` — `AUDIO_DEVICE_OUT_USB_DEVICE`.
- `USB Headset Out` — `AUDIO_DEVICE_OUT_USB_HEADSET`.
- `USB Device In` — `AUDIO_DEVICE_IN_USB_DEVICE`.
- `USB Headset In` — `AUDIO_DEVICE_IN_USB_HEADSET`.

Routes connect the accessory output mixport to USB Host Out, the USB device output mixport to USB Device Out and USB Headset Out, and the USB input mixport to USB Device In and USB Headset In.

The USB DAC tested in this research enumerated as a USB Audio device and was exposed by Android as USB Headset Out. Do not conflate this route with the distinct USB Host Out accessory route.

### Main policy cross-check

A grep of `audio_policy_configuration.xml` found USB device declarations and routes for USB Device Out, USB Headset Out, USB Device In, and USB Headset In. USB input devices also appear among the sources for several input routes, including the hifi input route.

This confirms USB device ports and routes are present in the main policy file as well as in the dedicated USB policy file. The grep output alone does not establish whether the dedicated USB module is loaded through an XML include or through another policy-loading mechanism. The exact include/selection mechanism remains to be verified.

## Primary speaker policy and kernel audio baseline

A stock `dumpsys media.audio_policy` snapshot reported the primary policy source as `/vendor/etc/audio_policy_configuration.xml` and exposed an available output device named `Speaker` (`AUDIO_DEVICE_OUT_SPEAKER`). Its declared profiles are:

- PCM 16-bit, 44.1 kHz and 48 kHz, stereo.
- PCM 32-bit, 44.1 kHz and 48 kHz, stereo.

The primary output mixport supports the Speaker device, as do the deep-buffer and VoIP receive mixports. This establishes Android Audio Policy recognition and declared routing support for the internal speaker; it does not prove that the speaker was active during the diagnostic snapshot or identify the physical amplifier.

The same snapshot lists `hifi_playback` as a separate mixport supporting USB Device Out and USB Headset Out. This is consistent with the separately validated USB DAC route.

Kernel and sysfs inspection provided these additional observations:

- Platform driver `mt6768-audio` has a bound device named `11220000.mt6768-afe-pcm`.
- Platform driver `mt6768-mt6358` has a bound device named `sound`.
- The I²C driver directory contains a generic `speaker_amp` driver, but its directory showed no bound I²C device symlink.
- Kernel module `snd_soc_mt6660` was present under `/sys/module/`, indicating that the module is loaded. This alone does not establish that a physical MT6660 amplifier is present or used by this handset.
- The module's sysfs directory exposed only `uevent` and `version`, whose metadata was inaccessible to the shell. No module version or device binding could be confirmed.

**Amplifier identification remains unresolved.** Do not select an MT6660 SmartPA configuration, remove alternative amplifier support, or modify speaker tuning based only on the loaded module. The stock SmartPA parameter XML contains several possible amplifier profiles; its entries are not proof of the fitted component.

## Audio effects

`/vendor/etc/audio_effects.xml` uses `audio_effects_conf` version 2.0 and registers these libraries:

| Library key | Shared library |
|---|---|
| bundle | `libbundlewrapper.so` |
| reverb | `libreverbwrapper.so` |
| visualizer | `libvisualizer.so` |
| downmix | `libdownmix.so` |
| loudness_enhancer | `libldnhncr.so` |
| dynamics_processing | `libdynproc.so` |
| pre_processing | `libaudiopreprocessing_mtk.so` |
| misoundfx | `libmisoundfx.so` |

Registered effects include Bass Boost, Virtualizer, Equalizer, Volume, four reverb variants, Visualizer, Downmix, Loudness Enhancer, Dynamics Processing, AEC, NS, AGC, and Xiaomi `misoundfx`.

The voice-communication preprocessing stream applies AEC, NS, and AGC. The XML registers these effects and libraries; it does not prove every effect is active on every output route. In particular, no evidence currently establishes that Xiaomi `misoundfx` is required for USB DAC playback.

The corresponding shared libraries and their transitive dependencies must be verified before reusing this configuration. Do not copy the XML independently of compatible implementations.

## Vendor audio parameter inventory

The stock vendor tree contains `/vendor/etc/audio_param/` and `/vendor/etc/audio_param_global/` with MediaTek audio parameter XML files. The observed inventory includes playback ACF/DRC/HCF and volume parameters, recording FIR/DMNR/UI parameters, SmartPA, speech, VoIP, VoW DSP AEC, headphone impedance, microphone information, USB device, and USB call parameters.

These files indicate a substantial vendor DSP/audio tuning layer. Their presence does not establish that they can be reused unchanged with a different kernel, DSP firmware, codec configuration, or Android 15 audio HAL.

## Kernel and USB Audio runtime observations

The stock kernel reports Linux 4.19.191-perf on arm64. USB-related modules observed loaded include:

- `snd_usb_audio`
- `usbcore`
- `usb20_host`
- `musb_hdrc`
- `usb_storage`
- `usbhid`

The USB device controller is `musb-hdrc` under the MediaTek `mt_usb` platform. The loaded module list is evidence of driver availability on stock firmware, not proof that the same modules or interfaces exist in a future Linsae kernel.

With the user's USB DAC connected, Android USB diagnostics reported host mode, source power, data role host, and a connected USB audio device. ALSA reported card 1, device 0, named `USB-Audio - KT-384/32 HIFI`, with output exposed. Android audio policy exposed USB Headset Out.

The device descriptor and Android diagnostics also reported an input interface / input capability. Practical recording capability has not been confirmed by the user and is outside the current DAC playback validation scope.

## Physical playback validation

The user confirmed audible output through the external USB DAC in both modes:

| Test | Result |
|---|---|
| USB OTG host enumeration | Pass |
| USB Audio device enumeration | Pass |
| USB Direct playback | Pass |
| Shared/Mixer playback | Pass |
| Unplug and reconnect DAC | Pass |
| Playback resumes without restarting the player app | Pass |
| USB Audio capture / recording | Not confirmed; out of scope |
| Screen-off playback (about 2 minutes) | Pass — playback continued with the display off |\n| Full suspend/resume cycle | Not independently verified |

For shared/mixer playback, AudioFlinger showed an active mixer output thread routed to `AUDIO_DEVICE_OUT_USB_HEADSET` at 48 kHz, PCM 32-bit, stereo, with writes occurring. The user independently confirmed audible playback. USB Direct playback was also confirmed audibly, although the available AudioFlinger snapshot did not expose a corresponding USB output stream; therefore no unsupported low-level routing explanation is asserted for that mode.

Reconnect testing showed the DAC was re-enumerated and playback returned without closing or restarting the player application. This is a confirmed stock-firmware behavior for the tested DAC and adapter combination, not a guarantee for every USB DAC.

## Porting implications for Linsae

1. Treat the MTK Audio HAL 7.0 service, its init configuration, VINTF declaration, and vendor dependencies as a coupled stack.
2. Preserve USB Host/USB Audio playback as a device requirement. The tested stock behavior covers both USB Direct and shared/mixer playback plus reconnect recovery.
3. Validate the Android 15 Audio HAL interface, policy XML schema, service registration, SELinux policy, kernel USB host controller, `snd_usb_audio`, ALSA device discovery, and power-management behavior together.
4. Do not copy the stock audio policy or effects XML blindly. Resolve policy selection/includes and verify every referenced library before adapting.
5. Treat MediaTek DSP parameter XML and Xiaomi `misoundfx` as vendor-specific dependencies requiring compatibility checks.
6. Do not treat input declarations as proof of a usable recording feature on the tested DAC.
7. Screen-off playback, suspend/resume, long-duration playback, and broader DAC compatibility remain untested.

## Next research items

- Determine how the main audio policy selects or includes the dedicated USB policy module.
- Identify the actual runtime audio policy file and verify XML loading/selection behavior.
- Inventory audio HAL and sound-effect shared libraries, without attempting to change stock permissions.
- Inspect relevant audio service/VINTF and SELinux dependencies for the Android 15 target.
- Investigate whether the screen-off playback test actually enters system suspend, then validate wake-up and repeated suspend/resume cycles.
