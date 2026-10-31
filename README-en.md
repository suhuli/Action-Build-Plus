[简体中文](README.md) | **English**

# Action-Build-Plus

Build a Linux **5.10.110** kernel for the **OnePlus Ace Racing Edition** (`oneplus_ace_race_t`, MT6895, Android 13), packaged with AnyKernel3.

## Exactly three build profiles

| `PROFILE` | Components |
|---|---|
| **`BAKASU` (default)** | **BakaSU + SUSFS, no KPM** — the user's daily configuration |
| `SUKISU` | SukiSU-Ultra builtin + SUSFS, no KPM |
| `SUKISU_KPM` | SukiSU-Ultra builtin + SUSFS + KPM |

Legacy rollback selectors, arbitrary KernelSU/SUSFS refs, disabling SUSFS, SUSFS dev, KPN and spoofed-manager options have been removed. This removes build configuration and old KPN binaries, not Git history, existing releases/artifacts or the kernel already installed on a phone.

## Reviewed versions — 2026-10-31

“Latest” means upstream heads reviewed for this update, **not an unreviewed moving HEAD on every build**. [`config/versions.json`](config/versions.json) is the single source of version pins.

| Component | Pin |
|---|---|
| BakaSU main | [`5785bdb8`](https://github.com/Baka-SU/BakaSU/commit/5785bdb8091304322f597f67d50e0b79f9815cb2) |
| SukiSU-Ultra builtin | [`b16e899a`](https://github.com/SukiSU-Ultra/SukiSU-Ultra/commit/b16e899a555e9b96aa1225f049cd7274820ca5b8), UAPI 6 |
| SUSFS | [`8930474a`](https://gitlab.com/simonpunk/susfs4ksu/-/commit/8930474a298d07ab9f1beca926779cbc3656b79e), `gki-android12-5.10`, v2.3.0; shared by all profiles |
| SukiSU main manager | [`a5742cda`](https://github.com/SukiSU-Ultra/SukiSU-Ultra/commit/a5742cdae02147973f9cc29db8888de62c1bae9d), UAPI 6 |
| SukiSU_patch KPM tools | [`eec45788`](https://github.com/SukiSU-Ultra/SukiSU_patch/commit/eec45788c9a115e5498040298133336d6b6071dd), with a pinned SHA-256 for `patch_linux` |
| Baseband-guard | [`028ff7fd`](https://github.com/vc-teahouse/Baseband-guard/commit/028ff7fd509e2104596da7cc1ef8e6ce2a0c9082) |
| AnyKernel3 | [`47f23f7e`](https://github.com/Numbersf/AnyKernel3/commit/47f23f7ece3ef212a392ec9ea5466e5f0b55d3c7), **v31.0 beta** |
| Device source | [OnePlusOSS/android_kernel_5.10_oneplus_mt6895](https://github.com/OnePlusOSS/android_kernel_5.10_oneplus_mt6895), `oneplus/mt6895_t_13.0.0_ace_racing` |
| Build environment | Ubuntu 22.04; make + ccache, with the official-script fallback retained |

> **These new combinations still require full builds and physical-device validation.** Offline tests, interface checks and even successful builds do not prove boot/runtime stability. The previously working build used older component pins. Keep a known-good package and a restorable boot backup. Current releases remain prereleases.

## Usage

1. Actions → **Build OnePlus Ace Race T Kernel** → Run workflow → `main`.
2. Keep **`PROFILE=BAKASU`** for the normal no-KPM configuration, or select one of the other two profiles.
3. `RELEASE=false` by default. Download from successful-run Artifacts; unpack the artifact wrapper before using the inner AnyKernel3 ZIP.
4. Verify device, profile, component versions and manager before flashing. Back up boot and prepare recovery access.
5. Explicitly enable `RELEASE` only when a prerelease is wanted.

Retained options: `BUILD_TIME` (stock timestamp; `F` for current UTC), `SUFFIX` (stock suffix; empty for a random suffix), `SUBLEVEL`, `LSM_BBG` (on), `CCM` (on; includes BBR/BBRv3 without changing the default algorithm), `UNICODE_BYPASS` (on), `DROID_SPACES`/`RE_KERNEL` (off), `RELEASE` (off), and `SPACE_NOCLEAN`/`BUILD_NOCCACHE` (off).

## Compatibility and managers

- All profiles require the exact pinned SUSFS. No implicit older fallback and no warn-and-continue on missing interfaces or failed patches.
- BakaSU's upstream SUSFS build restriction is preserved. Attach only successful **same-commit** CI manager artifacts with matching APK versionCode. Missing artifacts produce a warning and no bundled manager; never substitute an older release APK.
- SukiSU uses the pinned builtin kernel and pinned main manager. Verify UAPI before compiling, and pair the kernel version with APK versionCode. Missing or incompatible managers stop the build rather than falling back to legacy releases.
- Keep the existing bool-to-static-key adapter in `ksu_susfs_compat.py`; unexpected source structure fails closed.
- Only `SUKISU_KPM` enables `CONFIG_KPM`, downloads the pinned tool, verifies its SHA-256 and patches Image. Require successful execution and a nonempty, changed oImage. Neither no-KPM profile runs this tool.
- Static symbol checks do not prove types, ABI, Kbuild reachability or runtime correctness. A checksum verifies integrity, not binary safety or functionality.
- Do not claim complete end-to-end BakaSU SUSFS priority UID filter support without separate manager, scheduler and runtime validation.

## Offline tests and maintenance

```sh
python3 -m unittest discover -s tests -v
```

Tests use synthetic local sources, mocked network calls and fake tools. They do not compile a kernel or execute the upstream KPM binary. CI runs on main pushes and pull requests.

Daily maintenance compares all reviewed pins with upstream and maintains an update issue; it does not upgrade pins or trigger builds. Idempotent GETs have bounded retries for rate limiting, transient network errors and selected 5xx responses. Respect `Retry-After`; fail explicitly if its wait exceeds the retry budget. **If any upstream check fails, never report everything current or close an update issue.** Ccache keepalive is retained.

## Device validation

Check boot/reboot, manager recognition and root grants, module startup phases, SELinux enforcing/settings, SUSFS queries and used features, and new avc/exec errors. The KPM profile also needs module load/unload and reboot-persistence tests. Physical-device validation must be performed by the person holding the device.

## Credits and license

Based on [Numbersf/Action-Build](https://github.com/Numbersf/Action-Build). Thanks to BakaSU, SukiSU-Ultra, KernelSU, simonpunk/susfs4ksu, Numbersf/AnyKernel3, osm0sis/AnyKernel3 and vc-teahouse/Baseband-guard. Original license retained; see [LICENSE](LICENSE).
