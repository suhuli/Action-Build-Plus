#!/usr/bin/env python3
"""Compare reviewed pins with upstream. Never upgrade or silently ignore failed reads."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import quote

from http_get import get_json

ROOT = Path(__file__).resolve().parents[1]
LABEL = 'upstream-update'


def gh(*args):
    return subprocess.run(['gh', *args], check=True, text=True, capture_output=True).stdout.strip()


def collect_updates(versions):
    updates = []
    # Collect every result before allowing an issue to be edited or closed.
    for name, item in versions.items():
        if not isinstance(item, dict):
            continue
        if name == 'susfs':
            branch = quote(item['branch'], safe='')
            data = get_json('https://gitlab.com/api/v4/projects/simonpunk%2Fsusfs4ksu/repository/branches/' + branch)
            sha = data['commit']['id']
            url = 'https://gitlab.com/simonpunk/susfs4ksu/-/commit/' + sha
        else:
            data = get_json(f"https://api.github.com/repos/{item['repo']}/commits/{item.get('branch', 'HEAD')}")
            sha, url = data['sha'], data['html_url']
        if not re.fullmatch('[0-9a-f]{40}', sha):
            raise ValueError(f'{name}: invalid upstream commit')
        if sha != item['commit']:
            updates.append(f"- **{name}**: `{item['commit'][:8]}` → [`{sha[:8]}`]({url})")
    return updates


def sync_issue(repo, updates):
    issues = json.loads(gh('issue', 'list', '--repo', repo, '--label', LABEL,
                           '--state', 'open', '--json', 'number,body'))
    issue = issues[0] if issues else None
    if not updates:
        print('All upstream reads succeeded; reviewed pins are current.')
        if issue:
            gh('issue', 'close', str(issue['number']), '--repo', repo,
               '--comment', '所有上游查询成功；固定提交已与当前上游一致。')
        return
    body = ('上游有新提交。默认预设为 `BAKASU`、`SUKISU`、`SUKISU_KPM`；另保留显式高级选项。\n\n'
            + '\n'.join(updates) + '\n\n'
            '版本统一记录在 `config/versions.json`，不会自动升级或回退。'
            '升级前重新核对 SUSFS 接口、SukiSU static-key 适配、管理器 UAPI/versionCode，以及 KPM 工具 SHA-256；'
            '完整编译及实机验收后再用于日常。新提交不等于兼容或稳定。\n')
    print(body)
    if issue:
        if issue['body'] != body:
            gh('issue', 'edit', str(issue['number']), '--repo', repo, '--body', body)
    else:
        labels = json.loads(gh('label', 'list', '--repo', repo, '--limit', '1000', '--json', 'name'))
        if not any(label['name'] == LABEL for label in labels):
            gh('label', 'create', LABEL, '--repo', repo, '--color', 'FBCA04', '--description', '上游有新版本')
        gh('issue', 'create', '--repo', repo, '--title', '上游有新版本', '--label', LABEL, '--body', body)


def main():
    try:
        versions = json.loads((ROOT / 'config/versions.json').read_text())
        updates = collect_updates(versions)
        sync_issue(os.environ['GITHUB_REPOSITORY'], updates)
    except Exception as exc:
        # Do not expose request headers or tokens; do not close stale issues on failure.
        print(f'::error title=Upstream check failed::{type(exc).__name__}: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
