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
| ReSukiSU | [v4.2.0-rc3](https://github.com/Baka-SU/BakaSU/releases/tag/v4.2.0-rc3) (pinned; manager APK from the same release) |
| SUSFS | v2.3.0 (`gki-android12-5.10` @ `9892175b`) |
| AnyKernel3 | [Numbersf/AnyKernel3](https://github.com/Numbersf/AnyKernel3) @ `0fc75698` (pinned) |
| Baseband-guard | `a54e0dc6` (pinned) |
| Manifest | [`manifests/oneplus_ace_race_t.xml`](manifests/oneplus_ace_race_t.xml), no external manifest repo |

Derived from [Numbersf/Action-Build](https://github.com/Numbersf/Action-Build), trimmed to this single device with sensible defaults.

## Usage

1. Go to **Actions → Build OnePlus Ace Race T Kernel → Run workflow**.
2. The defaults are the recommended combination; just click **Run workflow**.
3. After ~15–20 minutes the build is published to [Releases](https://github.com/suhuli/Action-Build-Plus/releases) with the flashable zip, matching manager APK and SHA-256.
4. Flash the zip with Kernel Flasher / Horizon Kernel Flasher or from recovery.

> [!CAUTION]
> Back up your current `boot` partition before flashing.

## Key inputs

| Input | Default | Meaning |
|---|---|---|
| `MANAGER_SOURCE` | `RESUKISU` | KernelSU variant: ReSukiSU, or SukiSU-Ultra (`MIUIX` / `MD3`); `_SPOOF` = disguised manager |
| `KPM` | `N/A` | `KPM`/`KPN` only work with SukiSU-Ultra |
| `SUSFS_META` | empty | Empty = pinned, tested SUSFS; commit hash or step count = roll back; `-1` = disable SUSFS |
| `BUILD_TIME` | `F` | Value of `uname -v`; `F` = actual build time |
| `KSU_META` | `//` | `branch/custom-tag/commit`, each part optional, keep both slashes |
| `LSM_BBG` | on | Baseband-guard partition write protection |
| `CCM` | on | BBR + BBRv3 congestion control + ECN (default algorithm unchanged) |
| `RELEASE` | on | Publish a GitHub Release after a successful build |
| `UNICODE_BYPASS` | on | Fix for invisible-Unicode path bypass |

Options that had no effect on this device (ZRAM, NETFILTER, HMBIRD, dynamic manifest, SUSFS module bundling) were removed. See the Chinese README for the full list. The version code in the zip name is read from the build log and matches what the manager shows.

Builds fail if any part of the SUSFS, Unicode or BBRv3 patches does not apply.

## Maintenance

[Daily Maintenance](.github/workflows/maintenance.yml) runs every day: it opens an `upstream-update` issue when ReSukiSU, SUSFS, AnyKernel3 or Baseband-guard has a newer version than the pinned one, and touches the ccache so GitHub does not evict it. Run **Workflow and Cache Cleanup** to wipe caches manually.

## Credits

[Numbersf/Action-Build](https://github.com/Numbersf/Action-Build) · [ReSukiSU](https://github.com/ReSukiSU/ReSukiSU) · [SukiSU-Ultra](https://github.com/SukiSU-Ultra/SukiSU-Ultra) · [KernelSU](https://github.com/tiann/KernelSU) · [susfs4ksu](https://gitlab.com/simonpunk/susfs4ksu) · [AnyKernel3](https://github.com/osm0sis/AnyKernel3) · [Baseband-guard](https://github.com/vc-teahouse/Baseband-guard)

## License

See [LICENSE](LICENSE) (inherited from the original project).
