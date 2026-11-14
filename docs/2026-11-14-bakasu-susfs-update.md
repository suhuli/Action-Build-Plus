# 2026-11-14 BakaSU / SUSFS pin update

Stacked on the BakaSU SELinux snapshot bridge (PR #6). SukiSU, SukiSU manager, KPM, AnyKernel3 and Baseband-guard pins are unchanged.

## Pins

| Component | Old | New |
|---|---|---|
| BakaSU main | `516d3e87fbc986ccefdde2c2765f1700612441a9` | `548d1dda060ca198823d8808804d01f5209ef4a9` |
| SUSFS gki-android12-5.10 (modern floor / BakaSU pin) | `b0e474642cf77ee797004a454fa441362723d0ba` (v2.3.0) | `5436438b5cc77f146e04f71070da153dabe17a9d` (v2.4.0) |

## What changed upstream

- BakaSU `516d3e87..548d1dda`: 2 commits, manager only (Weblate translations, card blur alignment). `kernel/` is byte-identical.
- SUSFS `b0e47464..5436438b`: 6 commits. Version string v2.3.0 -> v2.4.0, rate-limited logging in `fs/susfs.c` for sus type / AV rule insertion, and a refresh of `KernelSU/10_enable_susfs_for_ksu.patch` (not used by BakaSU/SukiSU builds here). `50_add_susfs_in_gki-android12-5.10.patch` is byte-identical.

## Is the bridge from PR #6 still needed? Yes.

The gap is that the SUSFS kernel patch routes the three SELinux hooks to its type/AV ledgers, which the KernelSU side must populate via `susfs_add_sus_type()` / `susfs_add_sus_avd_allowed_by_type()`.

- BakaSU `main` at `548d1dda` still contains no call to either function.
- Upstream has the adaptation only on the unmerged `sync-up` branch: `67b56452` "kernel: adapt new susfs's selinux changes (#648)" and `dc8e01e0` "Other SuSFS fixes for priority uid (#652)". That branch has diverged from `main` (7 behind / 10 ahead) and was last touched 2026-11-06. Issue Baka-SU/BakaSU#650 is still open.
- Re-evaluate and drop the bridge once `sync-up` (or an equivalent) lands on `main`. The bridge's SHA-256 contract will then fail closed and force that review.

## Validation done locally (no kernel compile)

- Bridge source contract (3 BakaSU files + SUSFS 50 patch SHA-256) accepted against the new pair, unchanged hashes.
- `susfs_feature_compat.py --check` and `susfs_ksu_check.py` give identical results for old and new SUSFS against both BakaSU `548d1dda` and the unchanged SukiSU pin `1cfa5734`, so raising the shared modern floor does not change SukiSU selection at source-check level.
- Upstream BakaSU "Build Manager" CI for `548d1dda` succeeded and its `Manager-release` artifact exists (the APK versionCode was not decoded here).
- 97 offline regression tests pass.

## Remaining acceptance

Full BakaSU and SukiSU workflow builds on this revision, then device validation. Back up the original boot image first.

## Build #49/#50 failure and fix (same day)

Both first builds on this revision failed in `fs/susfs.c`: `implicit declaration of function 'SUSFS_LOGI_RL'`. SUSFS `6485568` defines the new rate-limited log macros only when `CONFIG_KSU_SUSFS_ENABLE_LOG` is on; this repository builds with SUSFS logging off. This is an upstream SUSFS omission, unrelated to BakaSU or the SELinux bridge.

`scripts/susfs_fixups.py post` now adds empty fallbacks for log macros that are used but missing from the logging-off branch, mirroring upstream's own empty `SUSFS_LOGI` / `SUSFS_LOGE`. It is a no-op on older SUSFS and once upstream fixes it. 4 regression tests added (101 total).
