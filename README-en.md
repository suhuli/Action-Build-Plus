[简体中文](README.md) | **English**

[![Build](https://img.shields.io/github/actions/workflow/status/suhuli/Action-Build-Plus/Build%20Kernel%20OnePlus.yml?branch=main&label=Build&logo=github-actions&style=flat-square)](https://github.com/suhuli/Action-Build-Plus/actions/workflows/Build%20Kernel%20OnePlus.yml)

# Action-Build-Plus

GitHub Actions workflow that builds a **ReSukiSU / SukiSU-Ultra + SUSFS** kernel for the **OnePlus Ace Racing Edition** (`oneplus_ace_race_t`) and packages it as a flashable AnyKernel3 zip.

| Item | Value |
|---|---|
| Device | OnePlus Ace Racing Edition (MT6895) |
| OS | Android 13 |
| Kernel | 5.10.110 (GKI, android12-5.10) |
| Source | [OnePlusOSS/android_kernel_5.10_oneplus_mt6895](https://github.com/OnePlusOSS/android_kernel_5.10_oneplus_mt6895) `oneplus/mt6895_t_13.0.0_ace_racing` |
| Build | Fast build (make + ccache), falls back to the official script |
| ReSukiSU (default) | [v4.2.0-rc3](https://github.com/Baka-SU/BakaSU/releases/tag/v4.2.0-rc3) (pinned; manager APK from the same release) |
| SukiSU-Ultra | [`builtin`](https://github.com/SukiSU-Ultra/SukiSU-Ultra/tree/builtin) branch @ `6c284e95` (pinned, version code 40971; manager APK from the main-branch CI build) |
| SUSFS | v2.3.0 (`gki-android12-5.10` @ `9892175b`) |
| AnyKernel3 | [Numbersf/AnyKernel3](https://github.com/Numbersf/AnyKernel3) @ `0fc75698` (pinned) |
| Baseband-guard | `a54e0dc6` (pinned) |
| KPM tool | [SukiSU-Ultra/SukiSU_patch](https://github.com/SukiSU-Ultra/SukiSU_patch) @ `547ae94b` (pinned, SukiSU-Ultra + KPM only) |
| Manifest | [`manifests/oneplus_ace_race_t.xml`](manifests/oneplus_ace_race_t.xml), no external manifest repo |

Derived from [Numbersf/Action-Build](https://github.com/Numbersf/Action-Build), trimmed to this single device with sensible defaults.

## Usage

1. Go to **Actions → Build OnePlus Ace Race T Kernel → Run workflow**.
2. The defaults are the recommended combination; just click **Run workflow**.
3. After ~15–20 minutes download the flashable zip (with the matching manager APK) from **Artifacts** at the bottom of the run page (unzip once). Nothing is published by default; tick `RELEASE` before running to publish a [Release](https://github.com/suhuli/Action-Build-Plus/releases) with the zip, manager APK and SHA-256.
4. Flash the zip with Kernel Flasher / Horizon Kernel Flasher or from recovery.

> [!CAUTION]
> Back up your current `boot` partition before flashing.

## Key inputs

| Input | Default | Meaning |
|---|---|---|
| `MANAGER_SOURCE` | `RESUKISU` | KernelSU variant: `RESUKISU` = ReSukiSU, `SUKISU` = SukiSU-Ultra; `_SPOOF` adds the disguised manager (random package name). SukiSU-Ultra's MIUIX / Material 3 UI is switched inside the manager settings |
| `KPM` | `N/A` | `KPM`/`KPN` only work with SukiSU-Ultra (skipped for ReSukiSU) |
| `SUSFS_META` | empty | Empty = pinned, tested SUSFS; commit hash or step count = roll back; `-1` = disable SUSFS (not allowed with SukiSU-Ultra) |
| `BUILD_TIME` | `F` | Value of `uname -v`; `F` = actual build time |
| `KSU_META` | `//` | `branch/custom-tag/commit`, each part optional, keep both slashes |
| `LSM_BBG` | on | Baseband-guard partition write protection |
| `CCM` | on | BBR + BBRv3 congestion control + ECN (default algorithm unchanged) |
| `RELEASE` | off | Tick to publish a GitHub Release after a successful build (off by default) |
| `UNICODE_BYPASS` | on | Fix for invisible-Unicode path bypass |

**SukiSU-Ultra notes:** the `builtin` branch is made for GKI kernels with built-in SUSFS and has no kprobe/syscall hooks of its own — all hooks come from the SUSFS patch, so the workflow refuses `SUSFS_META=-1` with SukiSU-Ultra. SUSFS v2.3.0 declares `ksu_su_compat_enabled` as a static key while `builtin` defines a bool; [`scripts/ksu_susfs_compat.py`](scripts/ksu_susfs_compat.py) converts it after the SUSFS patch and fails the build on any unexpected code. The manager APK comes from the latest successful main-branch CI run (falls back to the latest release APK for the normal manager).

Leaving the branch and commit parts of `KSU_META` empty uses the pinned versions; any explicit branch/commit is marked as a **pre-release** when `RELEASE` is ticked.

Options that had no effect on this device (ZRAM, NETFILTER, HMBIRD, dynamic manifest, SUSFS module bundling) were removed. See the Chinese README for the full list. The version code in the zip name is read from the build log and matches what the manager shows.

Builds fail if any part of the SUSFS, Unicode or BBRv3 patches does not apply.

## Maintenance

[Daily Maintenance](.github/workflows/maintenance.yml) runs every day: it opens an `upstream-update` issue when ReSukiSU, SukiSU-Ultra `builtin`, SUSFS, AnyKernel3, Baseband-guard or SukiSU_patch has a newer version than the pinned one, and touches the ccache so GitHub does not evict it. Run **Workflow and Cache Cleanup** to wipe caches manually.

## Credits

[Numbersf/Action-Build](https://github.com/Numbersf/Action-Build) · [ReSukiSU](https://github.com/ReSukiSU/ReSukiSU) · [SukiSU-Ultra](https://github.com/SukiSU-Ultra/SukiSU-Ultra) · [KernelSU](https://github.com/tiann/KernelSU) · [susfs4ksu](https://gitlab.com/simonpunk/susfs4ksu) · [AnyKernel3](https://github.com/osm0sis/AnyKernel3) · [Baseband-guard](https://github.com/vc-teahouse/Baseband-guard)

## License

See [LICENSE](LICENSE) (inherited from the original project).
