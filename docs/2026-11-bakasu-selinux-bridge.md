# BakaSU + SUSFS SELinux compatibility repair (2026-11-06)

## Scope and reviewed upstream

- BakaSU main: `516d3e87fbc986ccefdde2c2765f1700612441a9`
- SUSFS gki-android12-5.10: `b0e474642cf77ee797004a454fa441362723d0ba`
- Both were upstream branch HEAD when rechecked for this repair.
- Device/OEM: OnePlus Ace Race Android 13, kernel 5.10; source used for patch validation: `OnePlusOSS/android_kernel_5.10_oneplus_mt6895` commit `3e31a817f1b13a54312c21b3c53114ab76e42a16`.

## Confirmed integration gap in build #44

SUSFS routes SEL_CONTEXT, SEL_ACCESS and the app/current setprocattr path to its new ledger-backed functions. The selected BakaSU does not populate the SUSFS type/AV ledgers. Its existing policy snapshot backend is consequently bypassed despite the manual-hook feature macro being detected. This is a source-level incompatibility; it does not establish that every device detector result has the same cause.

## Chosen repair and change from initial proposal

Do NOT partially transplant upstream ledger registration. Correct registration would require auditing effective permissions (including attribute and conditional rules), rollback/publication of policy changes, reloads and type-ID reuse. Two insertion calls alone are insufficient evidence of compatibility.

Instead, retain BOTH latest source revisions and apply a BakaSU-only backend bridge after the standard SUSFS kernel patch:

- `handle_sel_write_context` calls BakaSU `my_write_context`.
- `handle_sel_write_access` calls BakaSU `my_write_access`.
- `handle_selinux_setprocattr` calls BakaSU `my_setprocattr`.

The three replaced SUSFS static helper bodies are removed, not left as unused alternative implementations. Latest SUSFS changes elsewhere are retained. The existing UID >= 10000, running flag and current-attribute conditions are unchanged. Ordinary fallback paths and BakaSU's permission checks are unchanged. Enforcement is not disabled. No forced-success state or fake implementation is added.

BakaSU's existing snapshot creation, lifetime, initialisation failure and cleanup behavior remains unchanged. This deliberately avoids a second, unsynchronised policy ledger; it does NOT claim to fix every pre-existing BakaSU lifecycle or state-reporting issue. The enabled/running distinction still exists. No new manager protocol is introduced.

## Fail-closed application

`scripts/bakasu_selinux_compat.py` verifies exact SHA-256 contracts for the upstream SUSFS patch and BakaSU feature, rules and hook-selection sources. It dry-runs an independently reviewable patch with zero fuzz, then applies and reverse-verifies it. Reapplication is idempotent. Unknown sources/layouts fail before compilation; they require renewed review, not an automatic hash refresh.

Default BakaSU SUSFS selection now pins the latest reviewed SHA instead of silently walking branch history. SukiSU selection is unchanged. Explicit BakaSU old/dev sources are not guaranteed supported: unreviewed SELinux contracts are rejected. Explicit SUSFS-off builds do not use the bridge.

`AnyKernel3/build-provenance.json` records full KSU/SUSFS/workflow SHA and backend label. It labels the result CI-only until device validation.

## Validation

- 97 offline tests pass (89 existing + 8 bridge regressions).
- Real OEM sources with the selected SUSFS patch: bridge applies, reverse-checks and re-applies idempotently.
- Negative tests reject changed upstream sources and changed hook layout without mutating the target.
- Tests verify all three routes, unchanged eligibility guards/fallbacks and unchanged BakaSU backend sources.
- Workflow YAML and all bash run-block syntax checks pass.
- Full CI compile and real-device acceptance must be recorded separately. Synthetic/source tests are not boot or stability evidence.

## Required device acceptance

Back up boot first. Confirm kernel/manager versions, root grants, module operation, Enforcing status, reboot persistence, backend initialisation logs and lack of new AVC/crash issues. Re-test the same detector without root privilege. Compare enabled and disabled behavior. Do not infer general security or universal detection resistance from a green detector result.

## Fixture provenance

`tests/fixtures/bakasu_selinux/**/*.gz` contains deterministic gzip copies of the cited upstream sources (BakaSU feature/rules/hook selection, SUSFS patch, and the two OEM files after applying SUSFS). Original upstream licenses apply. Fixtures enable offline reproduction of the exact contract and patch checks; they are not installed on the device.
