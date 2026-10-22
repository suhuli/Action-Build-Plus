#!/usr/bin/env python3
"""Write non-secret source/build provenance into the experimental flash ZIP."""
import argparse
import hashlib
import json
import os
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def provenance(directory: Path, env=None) -> dict:
    # Explicit whitelist: never serialize the environment or GitHub credentials.
    env = os.environ if env is None else env
    result = {
        "schema_version": 1,
        "device": "oneplus_ace_race_t",
        "experimental": env.get("IS_BAKASU_COMPAT") == "true",
        "kernel": {
            "repo": env.get("KSU_KERNEL_REPO"),
            "commit": env.get("KSU_SHA"),
            "version_code": env.get("KSUVER"),
            "version_name": env.get("KSU_NAME"),
        },
        "manager": {
            "repo": env.get("BUILD_MANAGER_REPO"),
            "source_commit": env.get("KSU_MANAGER_SHA"),
            "expected_version_code": env.get("MANAGER_VERSION_CODE"),
            "uapi_version": env.get("KSU_UAPI"),
        },
        "susfs": {
            "version": env.get("SUSFS_VER"),
            "commit": env.get("SUSFS_FULL_SHA"),
            "branch_head_at_clone": env.get("SUSFS_BRANCH_HEAD"),
            "note": env.get("SUSFS_NOTE"),
        },
        "initialization": env.get("BAKASU_INIT_MODE"),
        "new_preinit_runner_enabled": False,
        "workflow": {
            "repository": env.get("GITHUB_REPOSITORY"),
            "commit": env.get("GITHUB_SHA"),
            "ref": env.get("GITHUB_REF_NAME"),
            "run_id": env.get("GITHUB_RUN_ID"),
        },
        "apks": [{"file": p.name, "sha256": sha256(p)}
                 for p in sorted(directory.glob("*.apk"))],
    }
    image = directory / "Image"
    if image.is_file():
        result["kernel"]["image_sha256"] = sha256(image)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if os.environ.get("IS_BAKASU_COMPAT") != "true":
        parser.error("provenance writer is only defined for the experimental BakaSU profile")
    for name in ("KSU_SHA", "KSU_MANAGER_SHA", "SUSFS_FULL_SHA", "BAKASU_INIT_MODE"):
        if not os.environ.get(name):
            parser.error(f"missing required provenance field {name}")
    args.output.write_text(json.dumps(provenance(args.output.parent), ensure_ascii=False, indent=2) + "\n")
    print(f"Build provenance: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
