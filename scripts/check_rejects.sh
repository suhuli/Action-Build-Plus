#!/bin/bash

check_rejects() {
  local SEARCH_DIR="${1:-.}"
  local REJECT_FILES
  REJECT_FILES=$(find "$SEARCH_DIR" -name "*.rej" 2>/dev/null)
  if [ -z "$REJECT_FILES" ]; then
    return 0
  fi
  while IFS= read -r REJ_FILE; do
    local ORIG_FILE="${REJ_FILE%.rej}"
    ORIG_FILE="${ORIG_FILE#./}"
    echo "::group::❌ 补丁在 ${ORIG_FILE} 出现 hunk FAILED，点击查看具体信息"
    cat "$REJ_FILE"
    echo "::endgroup::"
  done <<< "$REJECT_FILES"
}