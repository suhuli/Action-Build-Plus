#!/usr/bin/env bash
# Run from kernel_workspace/susfs4ksu after cloning/fetching. Inputs are validated env values.
set -euo pipefail
susfs_ok() {
  python3 "$GITHUB_WORKSPACE/scripts/susfs_ksu_check.py" kernel_patches "$KSU_SRC" "$COMMON_SRC"
}
SUSFS_NOTE=""
case "$SUSFS_SELECTION" in
  pinned)
    [[ "$(git rev-parse HEAD)" == "$SUSFS_COMMIT" ]] || { echo '::error::SUSFS pin mismatch'; exit 1; }
    ;;
  manual)
    if [[ "$SUSFS_META" =~ ^[0-9]+$ ]]; then
      ref="HEAD~${SUSFS_META}"
    else
      ref="$SUSFS_META"
    fi
    resolved=$(git rev-parse --verify "${ref}^{commit}" 2>/dev/null) ||
      resolved=$(git rev-parse --verify "origin/${ref}^{commit}")
    git -c advice.detachedHead=false checkout -q --detach "$resolved"
    ;;
  branch) : ;;  # Explicit branch/dev opt-in; never used by the normal pinned profiles.
  compatible)
    head=$(git rev-parse HEAD)
    if git cat-file -e "${LEGACY_SUSFS_FLOOR}^{commit}" 2>/dev/null &&
       git merge-base --is-ancestor "$LEGACY_SUSFS_FLOOR" HEAD; then
      candidates="$(git rev-list --first-parent --max-count=50 "${LEGACY_SUSFS_FLOOR}..HEAD") $LEGACY_SUSFS_FLOOR"
    else
      echo '::warning::Compatibility floor not in branch history; only checking branch HEAD'
      candidates="$head"
    fi
    picked=""
    for commit in $candidates; do
      git -c advice.detachedHead=false checkout -q --detach "$commit"
      if susfs_ok; then picked="$commit"; break; fi
    done
    [[ -n "$picked" ]] || { echo '::error::No compatible SUSFS for custom KernelSU; specify a compatible pair'; exit 1; }
    [[ "$picked" == "$head" ]] || SUSFS_NOTE="Explicit custom KernelSU: SUSFS ${head:0:8} -> ${picked:0:8}"
    ;;
  *) echo '::error::Unknown SUSFS selection'; exit 1 ;;
esac
# Even advanced manual modes cannot bypass missing interfaces.
susfs_ok
SUSFS_VER=$(grep -o 'SUSFS_VERSION "[^"]*"' kernel_patches/include/linux/susfs.h | cut -d'"' -f2)
{
  echo "SUSFS_VER=$SUSFS_VER"
  echo "SUSFS_SHA=$(git rev-parse --short=8 HEAD)"
  echo "SUSFS_ACTUAL_COMMIT=$(git rev-parse HEAD)"
  echo "SUSFS_NOTE=$SUSFS_NOTE"
} >> "$GITHUB_ENV"
