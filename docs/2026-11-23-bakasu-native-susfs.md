# BakaSU 63ad1ea3 + SUSFS 784ac9e6：改用上游原生适配（2026-11-23）

基于 `test/bakasu-susfs-20261120`（BakaSU `7b65bde0` + SUSFS `784ac9e6` + 快照桥接）。SukiSU、SukiSU 管理器、KPM、AnyKernel3、Baseband-guard 均未改动。

| 组件 | 旧 | 新 |
|---|---|---|
| BakaSU main | `7b65bde0710b5e7c6f755545cb15a4abd417f3a8` | `63ad1ea3a90455dee9d77163cdafb028d8a90416` |
| SUSFS gki-android12-5.10 | `784ac9e6fd49bb02499b5b60c57ccc9d0c680204` | 不变（仍是分支最新） |

## 上游变化

- `0799a678` kernel, ksud, manager: sync with latest susfs —— `selinux/sepolicy.c` 的 `add_type()` / `add_rule_raw()` 直接调用 `susfs_add_sus_type()` / `susfs_add_sus_avd_allowed_by_type()`（即原 sync-up 分支的 #648），并加入 priority UID filter Kconfig、supercall 守卫与刷新（#652），以及 sus_path UID filter 刷新。
- `2b558ca5` kernel: fix detection point caused by susfs skip commits —— selinux_hide 拆为 `feature/selinux_hide/`；检测到 SUSFS 手动 hook（`KSU_COMPAT_HAS_SUSFS_FEATURE_SELINUX_HIDE`）时编译 `selinux_hide_susfs.c`（只修 SEL_ACCESS 的 avd seqno），否则用 `selinux_hide_auto.c`。
- 另有 SELinux hide 解析、policy generation 跟踪、inode_setxattr LSM hook、logd 读取 root 进程属性等 KernelSU 移植修复。

## 本仓库改动

- `bakasu_selinux_compat.py`：按源码布局选择后端。新布局（无 `feature/selinux_hide.c`，有 `selinux_hide/selinux_hide_susfs.c`，`sepolicy.c` 有两个账本函数的真实调用，SUSFS 提供这两个函数）走 **native**：不修改 SUSFS 补丁，并确认内核里没有桥接路由。旧布局仍按原 SHA-256 合约打桥接。其他布局一律失败。后端标签由脚本写入 `SELINUX_BACKEND`（`bakasu-native-susfs-ledger` / `bakasu-snapshot-bridge-v1`）。
- `susfs_feature_compat.py`：priority ioctl 识别同时接受新版 BakaSU 的 `case ...: { ... }` 写法（上游已自带 `#ifdef` 守卫，因此不做任何修改）。SukiSU 写法不变。
- 固定值：工作流 `RESUKISU_COMMIT`、`config/versions.json`、README 与测试同步为 `63ad1ea3`。
- 新增 `tests/test_bakasu_native_susfs.py`。

## 已做验证（未编译）

- 用真实源码（BakaSU `63ad1ea3` kernel/、SUSFS `784ac9e6` kernel_patches/）：`susfs_ksu_check.py` 符号检查与旧版结果一致（未给 common 目录时仅 `selinux_state` 待内核提供），`susfs_feature_compat.py --check` 通过且无改动计划，`bakasu_selinux_compat.py --check` 选中 native。
- 旧版 `7b65bde0` 仍选中 bridge，原有桥接测试不受影响。

## 待验收

完整 CI 编译（`MANAGER_SOURCE=RESUKISU`、`KSU_META=//`、`SUSFS_META` 留空、`RELEASE=false`），确认 provenance 记录 `SELINUX_BACKEND=bakasu-native-susfs-ledger`。刷机前备份 boot；实机检查开机/重启、管理器版本与授权、模块、SELinux Enforcing、无新增 AVC/崩溃，并用同一检测工具对比。通过后合并到 main，删除测试分支。
