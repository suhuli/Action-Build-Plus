[简体中文](README.md) | **English**

[![Build](https://img.shields.io/github/actions/workflow/status/suhuli/Action-Build-Plus/Build%20Kernel%20OnePlus.yml?branch=test%2Fbakasu-latest-susfs&label=Experimental&logo=github-actions&style=flat-square)](https://github.com/suhuli/Action-Build-Plus/actions/workflows/Build%20Kernel%20OnePlus.yml)

# Action-Build-Plus

GitHub Actions workflow that builds a **ReSukiSU / SukiSU-Ultra + SUSFS** kernel for the **OnePlus Ace Racing Edition** (`oneplus_ace_race_t`) and packages it as a flashable AnyKernel3 zip.

> **Experimental branch `test/bakasu-latest-susfs`; both default main branches are unchanged.** The new default `BAKASU` uses [suhuli/BakaSU `f7d829cb`](https://github.com/suhuli/BakaSU/commit/f7d829cb62e8555037bf5fada52ce273b92c1ac4), based on the latest upstream main `dac2d186`. `RESUKISU` remains the legacy rollback mode.

## Latest BakaSU + latest SUSFS test

- Default inputs: `MANAGER_SOURCE=BAKASU`, `KSU_META=//`, empty `SUSFS_META`, `SUSFS_DEV=false`, `RELEASE=false`.
- Uses the current `gki-android12-5.10` HEAD (adaptation baseline `f43926dc`, v2.3.0). New-mode interface failures stop the build; there is no silent SUSFS downgrade.
- Preserves BakaSU's existing init.rc/ksud path with explicit `KSU_NO_PREINIT`. **The new KernelSU preinit runner is NOT ported or enabled. There are no dummy preinit functions.**
- Reuses the officially signed APK from the unchanged upstream manager source commit `dac2d186` (35236 / UAPI 5). Kernel versionCode is paired with that base while its displayed name still identifies our patched commit. Changed manager/userspace/UAPI sources are rejected.
- Local validation includes all BakaSU/SELinux objects, all 23 SUSFS-patched C targets and partial linking on the real vendor 5.10.110 tree, using LLVM 19 without LTO/CFI. This is **not** a full production-toolchain Image build or device boot validation.

Because the default main is untouched, the web dispatch form may still show its old choices. Explicitly dispatch the test ref and the new input:

```sh
gh workflow run 'Build Kernel OnePlus.yml' --repo suhuli/Action-Build-Plus \
  --ref test/bakasu-latest-susfs -f MANAGER_SOURCE=BAKASU \
  -f KSU_META=// -f SUSFS_META= -f SUSFS_DEV=false -f RELEASE=false
```

Details: [adaptation notes](docs/bakasu-latest-susfs.md). The legacy RESUKISU sections below describe the retained rollback combination, **not** the new default.

| Item | Value |
|---|---|
| Device | OnePlus Ace Racing Edition (MT6895) |
| OS | Android 13 |
| Kernel | 5.10.110 (GKI, android12-5.10) |
| Source | [OnePlusOSS/android_kernel_5.10_oneplus_mt6895](https://github.com/OnePlusOSS/android_kernel_5.10_oneplus_mt6895) `oneplus/mt6895_t_13.0.0_ace_racing` |
| Build | Fast build (make + ccache), falls back to the official script |
| Legacy BakaSU (RESUKISU rollback input) | [`5b76b884`](https://github.com/Baka-SU/BakaSU/commit/5b76b884c75f729a220bb317aa4a4fc78f0e0e9c) (35222 / UAPI 5; v4.2.0-rc3 label; manager from the same commit CI, not the older release APK) |
| Patched BakaSU (default BAKASU) | [`f7d829cb`](https://github.com/suhuli/BakaSU/commit/f7d829cb62e8555037bf5fada52ce273b92c1ac4), latest upstream main + 5.10 compatibility; official manager base `dac2d186`, 35236 / UAPI 5 |
| SukiSU-Ultra | [`builtin`](https://github.com/SukiSU-Ultra/SukiSU-Ultra/tree/builtin) branch @ [`05f5cdf0`](https://github.com/SukiSU-Ultra/SukiSU-Ultra/commit/05f5cdf082d32bbc651c205ba4bdd1dc66cca7f5) (pinned, 2026-10-20, UAPI 6; the v4.2.1 release manager is still UAPI 5, so the bundled manager is the latest main CI build with the same UAPI, and the kernel version code is set to its versionCode) |
| SUSFS | v2.3.0 (`gki-android12-5.10`, BAKASU: strict latest HEAD; legacy modes: **latest compatible commit**, fallback [`31eb14ad`](https://gitlab.com/simonpunk/susfs4ksu/-/commit/31eb14add587b0a089dfe1819f92cc94920e141e)) |
| AnyKernel3 | [Numbersf/AnyKernel3](https://github.com/Numbersf/AnyKernel3) @ `0fc75698` (pinned) |
| Baseband-guard | `a54e0dc6` (pinned) |
| KPM tool | [SukiSU-Ultra/SukiSU_patch](https://github.com/SukiSU-Ultra/SukiSU_patch) @ `7c6289c9` (pinned, SukiSU-Ultra + KPM only) |
| Manifest | [`manifests/oneplus_ace_race_t.xml`](manifests/oneplus_ace_race_t.xml), no external manifest repo |

Derived from [Numbersf/Action-Build](https://github.com/Numbersf/Action-Build), trimmed to this single device with sensible defaults.

## Usage

1. Go to **Actions → Build OnePlus Ace Race T Kernel → Run workflow**.
2. The experimental default uses the repaired latest BakaSU + current SUSFS HEAD. Select RESUKISU to retain BakaSU `5b76b884` + the latest compatible SUSFS (currently `31eb14ad`). This new combination still needs device validation; back up `boot` before flashing. A successful build is not proof of runtime stability.
3. After ~15–20 minutes download the flashable zip (with a matching manager APK only when that commit CI artifact is available and versionCode matches) from **Artifacts** at the bottom of the run page (unzip once). Nothing is published by default; tick `RELEASE` before running to publish a [Release](https://github.com/suhuli/Action-Build-Plus/releases) with the zip, manager APK and SHA-256.
4. Flash the zip with Kernel Flasher / Horizon Kernel Flasher or from recovery.

> [!CAUTION]
> Back up your current `boot` partition before flashing.

## Key inputs

| Input | Default | Meaning |
|---|---|---|
| `MANAGER_SOURCE` | `BAKASU` | KernelSU variant: `BAKASU` = patched latest source, `RESUKISU` = legacy rollback, `SUKISU` = SukiSU-Ultra; `_SPOOF` adds the disguised manager (random package name). SukiSU-Ultra's MIUIX / Material 3 UI is switched inside the manager settings |
| `KPM` | `N/A` | `KPM`/`KPN` only work with SukiSU-Ultra (skipped for ReSukiSU) |
| `SUSFS_META` | empty | BAKASU: empty = strict latest HEAD, fail on incompatibility. Legacy modes: empty = latest SUSFS commit whose interface matches the KernelSU source (fallback `31eb14ad`; the new BakaSU combination still requires device validation); commit hash or step count = roll back; `-1` = disable SUSFS (not allowed with SukiSU-Ultra) |
| `BUILD_TIME` | `Mon Oct 24 22:45:30 UTC 2022` | Value of `uname -v` (prefixed with `#1 SMP PREEMPT`); default matches the stock kernel, `F` = actual build time |
| `SUFFIX` | `9-00011-g8efa13274425-ab9212784` | Part of `uname -r` after `5.10.110-android12-`; default matches the stock kernel, clear it for a random suffix |
| `KSU_META` | `//` | `branch/custom-tag/commit`, each part optional, keep both slashes |
| `LSM_BBG` | on | Baseband-guard partition write protection |
| `CCM` | on | BBR + BBRv3 congestion control (default algorithm unchanged). ECN needs no kernel option: toggle it with `sysctl net.ipv4.tcp_ecn` |
| `RELEASE` | off | Tick to publish a GitHub Release after a successful build (off by default) |
| `UNICODE_BYPASS` | on | Fix for invisible-Unicode path bypass |

**SukiSU-Ultra notes:** the `builtin` branch is made for GKI kernels with built-in SUSFS and has no kprobe/syscall hooks of its own — all hooks come from the SUSFS patch, so the workflow refuses `SUSFS_META=-1` with SukiSU-Ultra. SUSFS v2.3.0 declares `ksu_su_compat_enabled` as a static key while `builtin` defines a bool; [`scripts/ksu_susfs_compat.py`](scripts/ksu_susfs_compat.py) converts it after the SUSFS patch and fails the build on any unexpected code. The SukiSU-Ultra manager must have **exactly the same UAPI version** as the kernel, otherwise it says the kernel needs an update and disables most features. `builtin` does not necessarily share the release's UAPI (currently `builtin` is 6 while the v4.2.1 release manager is 5), so the workflow picks the newest release with a matching UAPI (spoofed variant from that release's CI run), then the latest main CI build, and attaches nothing if none match. Upstream `builtin` derives its version code from main's commit count at build time, which differs from the older release manager and triggers the "manager version does not match KernelSU driver version" warning; the workflow therefore picks the manager before compiling and sets the kernel's version code to that APK's versionCode (read by [`scripts/apk_version_code.py`](scripts/apk_version_code.py)). Do not install a release, main or website manager yourself — use the one in the zip.

Leaving the branch and commit parts of `KSU_META` empty uses the pinned versions; any explicit branch/commit is marked as a **pre-release** when `RELEASE` is ticked.

Options that had no effect on this device (ZRAM, NETFILTER, HMBIRD, dynamic manifest, SUSFS module bundling) were removed. See the Chinese README for the full list. The version code in the zip name is read from the build log and matches what the manager shows.

Builds fail if any part of the SUSFS, Unicode or BBRv3 patches does not apply.

## Legacy RESUKISU pin and rollback

Both normal and spoofed managers are selected from the same `5b76b884` CI commit and checked against the kernel versionCode. If no matching artifact exists, no manager is bundled; the workflow never substitutes the old release or latest main manager for this pin.

This is the last mainline commit before the SUSFS build block, not a guarantee of bug-free operation. It lacks the later SELinux-hiding timing side-channel fix. The workflow preserves the upstream block and fails early for blocked custom commits. The new BakaSU + 5.10 + SUSFS combination needs compilation and device testing.

Keep `KSU_META=//` for the new pin. To build the previous source, use `//239e1e8871b8fcd51a6e5b3002e0ba522fdd99fb`; only that source is eligible for the old release APK. Restore a known-good backed-up `boot` if flashing fails.

## SUSFS auto-update and rollback

SUSFS comes directly from [simonpunk/susfs4ksu](https://gitlab.com/simonpunk/susfs4ksu), branch `gki-android12-5.10`. With `SUSFS_META` empty, **every build uses the newest commit on the branch whose interface matches the KernelSU source**: it walks back from the branch HEAD, at most down to the fallback commit [`31eb14ad`](https://gitlab.com/simonpunk/susfs4ksu/-/commit/31eb14add587b0a089dfe1819f92cc94920e141e) (v2.3.0). [`scripts/susfs_ksu_check.py`](scripts/susfs_ksu_check.py) collects every `extern` symbol declared by the SUSFS kernel patch and requires a **non-static** definition in KernelSU (or the kernel itself); otherwise the patch would apply but linking would fail with `undefined reference`. If HEAD is skipped, the build log warns and lists the missing symbols, and the release notes say which commit was used. Once BakaSU / SukiSU-Ultra catch up and their pins are bumped, the next build picks up the latest SUSFS automatically.

> **Status (2026-10-21):** SUSFS `5a3af83e` / `e24d1726` / `f43926dc` (2026-10-19) synced with upstream KernelSU and now require `ksu_setup_preinit_file`, `ksu_preinit_handle_post_execveat`, `my_setprocattr`, `my_write_context` and `my_write_access` from KernelSU. Neither BakaSU (even its latest main, which added `Please wait susfs update.` for this reason) nor the latest SukiSU-Ultra `builtin` provides them (or only as static), so auto-selection still resolves to `31eb14ad`.

This is an interface check only, not a substitute for a full build and device testing.

Compared with the older `ca7093a1` pin, the fallback commit includes:

- [`c06d5f8e`](https://gitlab.com/simonpunk/susfs4ksu/-/commit/c06d5f8ef2b53d04c5e1c6b86dc3076f1e0e9f33): patch context rebased onto android12-5.10.257; no code change.
- [`31eb14ad`](https://gitlab.com/simonpunk/susfs4ksu/-/commit/31eb14add587b0a089dfe1819f92cc94920e141e): more selinux_hide fixes — `setprocattr` and the selinuxfs `context` / `access` writes now register contexts in both the real and fake policy sidtabs (mirrors upstream KernelSU [`a810677b`](https://github.com/tiann/KernelSU/commit/a810677b847ba564c5f9d3fa0fbabe54794b8eef)). The new `my_security_context_to_sid()` is defined by the patch itself in `ss/services.c`; the KernelSU side still only needs the existing `fake_state` symbols, which both BakaSU `5b76b884` and SukiSU-Ultra `7f1c299a` / `05f5cdf0` provide.

Checked offline: all three commits apply completely to this device's 5.10.110 source (no `.rej` after `susfs_fixups.py`). A full kernel build and device validation are still required; back up `boot` before flashing.

To rebuild with the previous SUSFS source, set `SUSFS_META` to `ca7093a1a26f7911987110c34a1352d74cfb1d09` (the older `82f08351fadb8b19dd6591bd14634d02ad832145` also still works). Set `31eb14add587b0a089dfe1819f92cc94920e141e` to pin the fallback commit; leave it empty to follow the latest compatible commit, and keep `SUSFS_DEV` off. A manually chosen commit that fails the interface check only produces a warning. This changes future builds only; it does not restore an already-flashed kernel.

## Maintenance

[Daily Maintenance](.github/workflows/maintenance.yml) runs every day: it opens an `upstream-update` issue when ReSukiSU (BakaSU), SukiSU-Ultra `builtin`, SUSFS, AnyKernel3, Baseband-guard or SukiSU_patch has a newer version than the pinned one (for SUSFS it also reports whether the latest commit is interface-compatible with the pinned BakaSU / SukiSU-Ultra), and touches the ccache so GitHub does not evict it. Since 2026-10-10 BakaSU refuses to build with SUSFS (`Please wait susfs update.`); the check warns if the latest release still has that block and reports when `main` lifts it before a new release, together with the state of [#622](https://github.com/Baka-SU/BakaSU/issues/622) (terminal `exec` denied with SELinux hiding on older 5.4/4.19/4.14 trees, not directly applicable to this 5.10 kernel; fixed on BakaSU `main` on 2026-10-13, but absent from pinned `5b76b884`; assess compatibility and any required backport before upgrading). Run **Workflow and Cache Cleanup** to wipe caches manually.

## Credits

[Numbersf/Action-Build](https://github.com/Numbersf/Action-Build) · [BakaSU (formerly ReSukiSU)](https://github.com/Baka-SU/BakaSU) · [SukiSU-Ultra](https://github.com/SukiSU-Ultra/SukiSU-Ultra) · [KernelSU](https://github.com/tiann/KernelSU) · [susfs4ksu](https://gitlab.com/simonpunk/susfs4ksu) · [AnyKernel3](https://github.com/osm0sis/AnyKernel3) · [Baseband-guard](https://github.com/vc-teahouse/Baseband-guard)

## License

See [LICENSE](LICENSE) (inherited from the original project).
