[简体中文](README.md) | **English**

[![Build](https://img.shields.io/github/actions/workflow/status/suhuli/Action-Build-Plus/Build%20Kernel%20OnePlus.yml?branch=main&label=Build&logo=github-actions&style=flat-square)](https://github.com/suhuli/Action-Build-Plus/actions/workflows/Build%20Kernel%20OnePlus.yml)

# Action-Build-Plus

GitHub Actions workflow that builds a **ReSukiSU / SukiSU-Ultra + SUSFS** kernel for the **OnePlus Ace Racing Edition** (`oneplus_ace_race_t`) and packages it as a flashable AnyKernel3 zip.

> ReSukiSU was renamed **BakaSU** on 2026-10-05 ([Baka-SU/BakaSU](https://github.com/Baka-SU/BakaSU)). The pinned v4.2.0-rc3 predates the rename, so the kernel version name, manager and zip still say ReSukiSU; this repo keeps the ReSukiSU option names for consistency.

| Item | Value |
|---|---|
| Device | OnePlus Ace Racing Edition (MT6895) |
| OS | Android 13 |
| Kernel | 5.10.110 (GKI, android12-5.10) |
| Source | [OnePlusOSS/android_kernel_5.10_oneplus_mt6895](https://github.com/OnePlusOSS/android_kernel_5.10_oneplus_mt6895) `oneplus/mt6895_t_13.0.0_ace_racing` |
| Build | Fast build (make + ccache), falls back to the official script |
| ReSukiSU (default) | [v4.2.0-rc3](https://github.com/Baka-SU/BakaSU/releases/tag/v4.2.0-rc3) (pinned; manager APK from the same release) |
| SukiSU-Ultra | [`builtin`](https://github.com/SukiSU-Ultra/SukiSU-Ultra/tree/builtin) branch @ `6c284e95` (pinned, UAPI 2; bundled manager is v4.2.0 with the same UAPI, kernel version code set to the manager's 40900) |
| SUSFS | v2.3.0 (`gki-android12-5.10` @ `82f08351`) |
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
| `BUILD_TIME` | `Mon Oct 24 22:45:30 UTC 2022` | Value of `uname -v` (prefixed with `#1 SMP PREEMPT`); default matches the stock kernel, `F` = actual build time |
| `SUFFIX` | `9-00011-g8efa13274425-ab9212784` | Part of `uname -r` after `5.10.110-android12-`; default matches the stock kernel, clear it for a random suffix |
| `KSU_META` | `//` | `branch/custom-tag/commit`, each part optional, keep both slashes |
| `LSM_BBG` | on | Baseband-guard partition write protection |
| `CCM` | on | BBR + BBRv3 congestion control (default algorithm unchanged). ECN needs no kernel option: toggle it with `sysctl net.ipv4.tcp_ecn` |
| `RELEASE` | off | Tick to publish a GitHub Release after a successful build (off by default) |
| `UNICODE_BYPASS` | on | Fix for invisible-Unicode path bypass |

**SukiSU-Ultra notes:** the `builtin` branch is made for GKI kernels with built-in SUSFS and has no kprobe/syscall hooks of its own — all hooks come from the SUSFS patch, so the workflow refuses `SUSFS_META=-1` with SukiSU-Ultra. SUSFS v2.3.0 declares `ksu_su_compat_enabled` as a static key while `builtin` defines a bool; [`scripts/ksu_susfs_compat.py`](scripts/ksu_susfs_compat.py) converts it after the SUSFS patch and fails the build on any unexpected code. The SukiSU-Ultra manager must have **exactly the same UAPI version** as the kernel, otherwise it says the kernel needs an update and disables most features. `builtin` lags behind main (kernel UAPI 2, latest main manager UAPI 5), so the workflow picks the newest release with a matching UAPI (spoofed variant from that release's CI run), then the latest main CI build, and attaches nothing if none match. Upstream `builtin` derives its version code from main's commit count at build time, which differs from the older release manager and triggers the "manager version does not match KernelSU driver version" warning; the workflow therefore picks the manager before compiling and sets the kernel's version code to that APK's versionCode (read by [`scripts/apk_version_code.py`](scripts/apk_version_code.py)). Do not install the latest manager from main/the website — use the one in the zip.

Leaving the branch and commit parts of `KSU_META` empty uses the pinned versions; any explicit branch/commit is marked as a **pre-release** when `RELEASE` is ticked.

Options that had no effect on this device (ZRAM, NETFILTER, HMBIRD, dynamic manifest, SUSFS module bundling) were removed. See the Chinese README for the full list. The version code in the zip name is read from the build log and matches what the manager shows.

Builds fail if any part of the SUSFS, Unicode or BBRv3 patches does not apply.

## Maintenance

[Daily Maintenance](.github/workflows/maintenance.yml) runs every day: it opens an `upstream-update` issue when ReSukiSU (BakaSU), SukiSU-Ultra `builtin`, SUSFS, AnyKernel3, Baseband-guard or SukiSU_patch has a newer version than the pinned one, and touches the ccache so GitHub does not evict it. Since 2026-10-10 BakaSU refuses to build with SUSFS (`Please wait susfs update.`); the check warns if the latest release still has that block and reports when `main` lifts it before a new release, together with the state of [#622](https://github.com/Baka-SU/BakaSU/issues/622) (terminal `exec` denied with SELinux hiding on 5.10; fixed on BakaSU `main` on 2026-10-13, but the fix is not in v4.2.0-rc3 and cannot be picked up until the next release lifts the SUSFS block). Run **Workflow and Cache Cleanup** to wipe caches manually.

## Credits

[Numbersf/Action-Build](https://github.com/Numbersf/Action-Build) · [BakaSU (formerly ReSukiSU)](https://github.com/Baka-SU/BakaSU) · [SukiSU-Ultra](https://github.com/SukiSU-Ultra/SukiSU-Ultra) · [KernelSU](https://github.com/tiann/KernelSU) · [susfs4ksu](https://gitlab.com/simonpunk/susfs4ksu) · [AnyKernel3](https://github.com/osm0sis/AnyKernel3) · [Baseband-guard](https://github.com/vc-teahouse/Baseband-guard)

## License

See [LICENSE](LICENSE) (inherited from the original project).
