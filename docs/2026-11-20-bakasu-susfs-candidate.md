# BakaSU / SUSFS test-only candidate (2026-11-20)

Base: PR #7 head `72231013dcf96a972468275a4e8c6c1faea55269`. Target a separate branch; no changes to `main` or the known-good PR #7 head.

- BakaSU `main`: `7b65bde0710b5e7c6f755545cb15a4abd417f3a8`.
- SUSFS `gki-android12-5.10`: `784ac9e6fd49bb02499b5b60c57ccc9d0c680204` (v2.4.0).
- SukiSU, manager, KPM and its prior SUSFS selection floor remain unchanged.
- BakaSU upstream #648 / #652 were merged into `sync-up`, not `main`. Keep the existing bridge and log-off fixes. Never accept an unknown patch automatically.

## Source validation

The new SUSFS revision changes inode labeling in `hooks.c` and policy helper code in `ss/services.c`. The existing BakaSU bridge applies at zero fuzz to the selected OEM files (`3e31a817f1b13a54312c21b3c53114ab76e42a16`) after applying the corresponding new SUSFS patch sections. The bridge itself is unchanged. The new test preserves the added inode label source byte-for-byte before the old setprocattr bridge hunk, validates all three bridge routes, then checks repeat application is a no-op. `services.c` is not modified by the bridge. The legacy fixture still covers the previous exact SUSFS patch; unknown source still fails closed.

The new fixture stores only the upstream patch and the two OEM files with the respective patch sections applied, as deterministic gzip assets. Real candidate source verification passed the bridge contract, feature contract, and symbol checks; 102 offline tests passed. Static source checks do not validate the complete OEM patch stack, LTO/linking, or runtime SELinux behavior.

## CI and device gates (pending)

On the candidate branch run **Build OnePlus Ace Race T Kernel**, `MANAGER_SOURCE=RESUKISU`, `KSU_META=//`, blank `SUSFS_META`, `SUSFS_DEV=false`, `RELEASE=false`. Confirm the build summary/provenance records both full SHAs and keep the successful artifact with its workflow run. Validate the existing known-good ROM/boot backup, boot and reboot, manager version and root authorization, modules, SELinux `Enforcing`, normal file labeling and no unexpected AVC/crash regressions. Retain the previous artifact and original boot backup. Do not advance `main` until native support lands in BakaSU `main` and full validation is repeated.
