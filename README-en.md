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

Derived from [Numbersf/Action-Build](https://github.com/Numbersf/Action-Build), trimmed to this single device with sensible defaults.

## Usage

1. Go to **Actions → Build OnePlus Ace Race T Kernel → Run workflow**.
2. The defaults are the recommended combination; just click **Run workflow**.
3. After ~25 minutes, download `AnyKernel3_...` from **Artifacts** at the bottom of the run page.
4. Unzip once and flash the inner zip with Kernel Flasher / Horizon Kernel Flasher or from recovery.

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
| `ZRAM` | `0/lz4kd/8589934592` | `on/algorithm/size`; not recommended on 5.10 |
| `LSM_BBG` | on | Baseband-guard partition write protection |
| `CCM` | on | BBR congestion control + ECN |
| `UNICODE_BYPASS` | on | Fix for invisible-Unicode path bypass |

See the Chinese README for the full list. The version code in the zip name is read from the build log and matches what the manager shows.

## Cache

ccache entries are evicted by GitHub after 7 days without use, so the first build after a break is slower. Run **Workflow and Cache Cleanup** to wipe caches manually.

## Credits

[Numbersf/Action-Build](https://github.com/Numbersf/Action-Build) · [ReSukiSU](https://github.com/ReSukiSU/ReSukiSU) · [SukiSU-Ultra](https://github.com/SukiSU-Ultra/SukiSU-Ultra) · [KernelSU](https://github.com/tiann/KernelSU) · [susfs4ksu](https://gitlab.com/simonpunk/susfs4ksu) · [AnyKernel3](https://github.com/osm0sis/AnyKernel3) · [Baseband-guard](https://github.com/vc-teahouse/Baseband-guard) · ZRAM module by [@FURLC](https://github.com/FURLC)

## License

See [LICENSE](LICENSE) (inherited from the original project).
