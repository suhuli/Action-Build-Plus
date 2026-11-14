[简体中文](README.md) | **English**

> **2026-11-06 BakaSU SELinux bridge (candidate)**: default BakaSU builds pin the latest reviewed SUSFS SHA, with no silent fallback. Three SELinux hooks use BakaSU's policy-snapshot backend; unreviewed combinations fail closed, including unsupported custom legacy/dev sources. Dependencies are not downgraded. Full CI and device acceptance are still required. See [repair notes](docs/2026-11-bakasu-selinux-bridge.md).

# Action-Build-Plus

GitHub Actions kernel build for **OnePlus Ace Racing Edition** (`oneplus_ace_race_t`, MT6895, Android 13, Linux 5.10.110), with **BakaSU / SukiSU-Ultra + SUSFS**, packaged as an AnyKernel3 flashable zip.

## Current sources (2026-11-14)

The complete pre-redesign input layout, ordering, defaults and direct-selection flow are restored, without PROFILE or an override layer. The four reviewed dependencies are updated; this revision still needs CI build verification. BakaSU retains the original RESUKISU / RESUKISU_SPOOF names.

| Component | Pin / policy |
|---|---|
| Device source | OnePlusOSS/android_kernel_5.10_oneplus_mt6895, `oneplus/mt6895_t_13.0.0_ace_racing` |
| BakaSU (default) | Official [`548d1dda`](https://github.com/Baka-SU/BakaSU/commit/548d1dda060ca198823d8808804d01f5209ef4a9), native upstream preinit; no old Fork `KSU_NO_PREINIT` bridge |
| SUSFS (default latest BakaSU/SukiSU) | v2.4.0, newest compatible `gki-android12-5.10` commit; minimum [`5436438b`](https://gitlab.com/simonpunk/susfs4ksu/-/commit/5436438b5cc77f146e04f71070da153dabe17a9d), including the SELinux hide rework and independent priority UID filter configuration |
| SukiSU-Ultra | `builtin` @ `1cfa57340590971cba7521ed536da8ebbedc5f0a`, UAPI 6 |
| SUSFS minimum for explicitly selected legacy sources | [`31eb14ad`](https://gitlab.com/simonpunk/susfs4ksu/-/commit/31eb14add587b0a089dfe1819f92cc94920e141e) |
| Baseband-guard | [`028ff7fd`](https://github.com/vc-teahouse/Baseband-guard/commit/028ff7fd509e2104596da7cc1ef8e6ce2a0c9082), backported `selinux_cred` compatibility |
| AnyKernel3 | Numbersf [`47f23f7e`](https://github.com/Numbersf/AnyKernel3/commit/47f23f7ece3ef212a392ec9ea5466e5f0b55d3c7), **v31.0 beta**, updated magiskboot / magiskpolicy binaries |
| KPM tools | SukiSU_patch [`eec45788`](https://github.com/SukiSU-Ultra/SukiSU_patch/commit/eec45788c9a115e5498040298133336d6b6071dd), only for SukiSU-Ultra + KPM |
| Default ordinary SukiSU manager | [`645ef986`](https://github.com/SukiSU-Ultra/SukiSU-Ultra/commit/645ef9860b9b7f900bb5d1b27e224f2c311d39c0), UAPI 6; versionCode 41150; same main commit as release v4.3.0-r2, paired by exact-commit CI (CI filenames still contain r1) |
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

- `susfs_feature_compat.py` checks candidates without mutation, then adds the real upstream priority Kconfig, guards the ioctl and package-observer calls, and aligns the reviewed SELinux helper argument width. The effective `.config` is checked before compilation; unknown layouts fail closed.
- Current BakaSU no longer builds spoof managers. `RESUKISU_SPOOF` fails before compilation and asks for ordinary `RESUKISU`; explicit legacy sources still require both spoof CI support and an exact-commit APK. No silent ordinary-APK substitution.
- The symbol checker now also checks KSU → SUSFS calls and rejects missing new SELinux helpers. These checks are not a full C preprocessor or a replacement for compilation/device testing.

- Empty `SUSFS_META` searches backward from branch HEAD to the applicable minimum; default latest BakaSU/SukiSU cannot silently fall back before `5436438b`. Explicit custom/legacy sources retain `31eb14ad`. No compatible automatic candidate is a hard failure; incompatible explicit overrides also stop rather than forcing a broken build.
- `scripts/susfs_ksu_check.py` checks real non-static definitions. The audited BakaSU `my_setprocattr` alias is accepted only when the selected SUSFS hook, upstream Kbuild detection contract and real function definition all exist. Missing symbols are not ignored and no stub implementation is added.
- This is not a full C preprocessor, ABI/type/configuration validation or runtime proof. Complete compilation and device tests remain necessary.
- Current official BakaSU does not provide the full manager/scheduling integration for the new SUSFS priority UID filter. Updating the kernel-side code and fixes does **not** claim end-to-end support for that feature.
- Default pinned SukiSU ordinary builds use the exact reviewed manager main commit. Custom/spoofed managers retain UAPI-based selection, with kernel versionCode bound to the selected APK. Do not manually mix unrelated latest manager builds.

Explicit rollback options:

- Current SUSFS: `5436438b5cc77f146e04f71070da153dabe17a9d`.
- Previous BakaSU: `KSU_META=//5b76b884c75f729a220bb317aa4a4fc78f0e0e9c`, with SUSFS `31eb14add587b0a089dfe1819f92cc94920e141e`.
- Older release source: `KSU_META=//239e1e8871b8fcd51a6e5b3002e0ba522fdd99fb`.
- Historical SUSFS refs: `ca7093a1a26f7911987110c34a1352d74cfb1d09` or `82f08351fadb8b19dd6591bd14634d02ad832145`; not a promise of compatibility with current BakaSU.

`KSU_META` remains `branch/custom-label/commit`. Custom refs override pins and are prereleases. Changing build inputs cannot recover an already flashed device.

## Maintenance and testing

Explicit apt installation and tool checks fail early for missing prerequisites, without depending on an APT cache hit. Failed SUSFS, Unicode or BBRv3 patches stop the build; `susfs_fixups.py` handles device-specific 5.10.110 differences.

Run `python3 -m unittest discover -s tests -v`. Offline regressions also run on main pushes / PRs. Daily maintenance reports upstream changes and keeps ccache alive without upgrading pins. Bounded GET retries respect rate limits and never report failed checks as current. The version inventory in config/versions.json is checked against workflow pins by tests. Use **Workflow and Cache Cleanup** for caches. No experimental branch or downstream Fork is required.

On device, check boot, manager recognition, root grants, module boot events, reboot persistence, SELinux enforcing/hiding, SUSFS queries and enabled features, and new AVC/exec failures. Keep a known-good boot backup.

## Credits and license

Based on Numbersf/Action-Build. Thanks to BakaSU, SukiSU-Ultra, KernelSU, simonpunk/susfs4ksu, Numbersf/AnyKernel3, osm0sis/AnyKernel3 and vc-teahouse/Baseband-guard. See [LICENSE](LICENSE).
