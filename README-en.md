[简体中文](README.md) | **English**

# Action-Build-Plus

GitHub Actions kernel build for **OnePlus Ace Racing Edition** (`oneplus_ace_race_t`, MT6895, Android 13, Linux 5.10.110), with **BakaSU / SukiSU-Ultra + SUSFS**, packaged as an AnyKernel3 flashable zip.

## Current sources (2026-10-28)

This update targets `main` directly. It uses official BakaSU, not the old experimental Fork. Existing `RESUKISU` / `RESUKISU_SPOOF` input names are retained for compatibility.

| Component | Pin / policy |
|---|---|
| Device source | OnePlusOSS/android_kernel_5.10_oneplus_mt6895, `oneplus/mt6895_t_13.0.0_ace_racing` |
| BakaSU (default) | Official [`d5e9e025`](https://github.com/Baka-SU/BakaSU/commit/d5e9e025b8b49155f8014684d64c91742b465f65), native upstream preinit; no old Fork `KSU_NO_PREINIT` bridge |
| SUSFS (default BakaSU) | v2.3.0, newest compatible `gki-android12-5.10` commit; minimum [`eb95da08`](https://gitlab.com/simonpunk/susfs4ksu/-/commit/eb95da080c76724c4962d0c62e9af3be37d9d439), including priority UID filter UAF / worker fixes |
| SukiSU-Ultra (unchanged) | `builtin` @ `05f5cdf082d32bbc651c205ba4bdd1dc66cca7f5`, UAPI 6 |
| SUSFS minimum for SukiSU / explicit legacy BakaSU | [`31eb14ad`](https://gitlab.com/simonpunk/susfs4ksu/-/commit/31eb14add587b0a089dfe1819f92cc94920e141e) |
| Baseband-guard | [`028ff7fd`](https://github.com/vc-teahouse/Baseband-guard/commit/028ff7fd509e2104596da7cc1ef8e6ce2a0c9082), backported `selinux_cred` compatibility |
| AnyKernel3 | Numbersf [`47f23f7e`](https://github.com/Numbersf/AnyKernel3/commit/47f23f7ece3ef212a392ec9ea5466e5f0b55d3c7), **v31.0 beta**, updated magiskboot / magiskpolicy binaries |
| KPM tools (unchanged) | SukiSU_patch `7c6289c9`, only for SukiSU-Ultra + KPM |
| Build environment | Ubuntu 22.04, explicit apt dependencies and required-tool validation; make + ccache with official-script fallback |

> **Warning:** This updated combination requires a complete build and device testing. Passing static checks, applying patches, or compiling successfully does not establish boot/runtime stability. Back up the current `boot` partition and retain a tested recovery method.

## Usage

1. Open **Actions → Build OnePlus Ace Race T Kernel → Run workflow**, ref `main`.
2. Defaults: `MANAGER_SOURCE=RESUKISU`, `KSU_META=//`, empty `SUSFS_META`.
3. Download Artifacts after success; unzip the outer artifact archive once to obtain the flashable zip.
4. `RELEASE` defaults to false. Explicitly enabled releases using this AnyKernel3 beta are always marked **prerelease**.
5. BakaSU manager APKs must come from the exact source commit's successful official CI and match kernel versionCode; unavailable/mismatched APKs are omitted, not replaced with an older release or another main commit.

See the [Chinese parameter table](README.md#参数说明) for all existing inputs. BakaSU supports SUSFS disabled (`-1`); SukiSU builtin requires SUSFS. KPM/KPN remain SukiSU-only. BBR/BBRv3 compilation does not change the default congestion control. Unicode and baseband protection remain enabled by default; Droid Spaces / Re:Kernel remain opt-in.

## Compatibility, source selection and rollback

- Empty `SUSFS_META` searches backward from branch HEAD to the applicable minimum; default BakaSU cannot silently fall back before `eb95da08`. SukiSU and explicitly selected legacy BakaSU retain `31eb14ad`. No compatible automatic candidate is a hard failure; explicit overrides retain the previous warning-and-build behavior.
- `scripts/susfs_ksu_check.py` checks real non-static definitions. The audited BakaSU `my_setprocattr` alias is accepted only when the selected SUSFS hook, upstream Kbuild detection contract and real function definition all exist. Missing symbols are not ignored and no stub implementation is added.
- This is not a full C preprocessor, ABI/type/configuration validation or runtime proof. Complete compilation and device tests remain necessary.
- Current official BakaSU does not provide the full manager/scheduling integration for the new SUSFS priority UID filter. Updating the kernel-side code and fixes does **not** claim end-to-end support for that feature.
- SukiSU managers are selected by matching UAPI, with kernel versionCode bound to the selected APK. Do not manually mix unrelated latest manager builds.

Explicit rollback options:

- Current SUSFS: `eb95da080c76724c4962d0c62e9af3be37d9d439`.
- Previous BakaSU: `KSU_META=//5b76b884c75f729a220bb317aa4a4fc78f0e0e9c`, with SUSFS `31eb14add587b0a089dfe1819f92cc94920e141e`.
- Older release source: `KSU_META=//239e1e8871b8fcd51a6e5b3002e0ba522fdd99fb`.
- Historical SUSFS refs: `ca7093a1a26f7911987110c34a1352d74cfb1d09` or `82f08351fadb8b19dd6591bd14634d02ad832145`; not a promise of compatibility with current BakaSU.

`KSU_META` remains `branch/custom-label/commit`. Custom refs override pins and are prereleases. Changing build inputs cannot recover an already flashed device.

## Maintenance and testing

Explicit apt installation and tool checks fail early for missing prerequisites, without depending on an APT cache hit. Failed SUSFS, Unicode or BBRv3 patches stop the build; `susfs_fixups.py` handles device-specific 5.10.110 differences.

Run `python3 -m unittest discover -s tests -v`. Offline regressions also run on main pushes / PRs. Daily maintenance reports upstream changes and compatibility, and keeps ccache alive; it does not automatically update pins. Use **Workflow and Cache Cleanup** for caches. No experimental branch or downstream Fork is required.

On device, check boot, manager recognition, root grants, module boot events, reboot persistence, SELinux enforcing/hiding, SUSFS queries and enabled features, and new AVC/exec failures. Keep a known-good boot backup.

## Credits and license

Based on Numbersf/Action-Build. Thanks to BakaSU, SukiSU-Ultra, KernelSU, simonpunk/susfs4ksu, Numbersf/AnyKernel3, osm0sis/AnyKernel3 and vc-teahouse/Baseband-guard. See [LICENSE](LICENSE).
