# BakaSU 63ad1ea3 + SUSFS 784ac9e6：改用上游原生适配（2026-11-23）

已合入 `main`。SukiSU、SukiSU 管理器、KPM、AnyKernel3、Baseband-guard 均未改动。

| 组件 | 旧 | 新 |
|---|---|---|
| BakaSU main | `7b65bde0710b5e7c6f755545cb15a4abd417f3a8`（测试分支）/ `516d3e87`（原 main） | `63ad1ea3a90455dee9d77163cdafb028d8a90416` |
| SUSFS gki-android12-5.10 | `784ac9e6`（测试分支）/ `b0e47464`（原 main） | `784ac9e6fd49bb02499b5b60c57ccc9d0c680204`（v2.4.0） |

## 上游变化

- `0799a678` kernel, ksud, manager: sync with latest susfs：`selinux/sepolicy.c` 的 `add_type()` / `add_rule_raw()` 直接调用 `susfs_add_sus_type()` / `susfs_add_sus_avd_allowed_by_type()`（原 sync-up 分支的 #648），并加入 priority UID filter Kconfig、supercall 守卫与刷新（#652），以及 sus_path UID filter 刷新。
- `2b558ca5` kernel: fix detection point caused by susfs skip commits：selinux_hide 拆为 `feature/selinux_hide/`；检测到 SUSFS 手动 hook 时编译 `selinux_hide_susfs.c`，否则用 `selinux_hide_auto.c`。
- 另有 SELinux hide 解析、policy generation 跟踪、inode_setxattr LSM hook、logd 读取 root 进程属性等 KernelSU 移植修复。

## 本仓库改动

- 移除本地 SELinux 快照桥接：`scripts/bakasu_selinux_compat.py`、`patches/bakasu/`、桥接测试与 fixtures、桥接说明文档。SUSFS 内核补丁原样使用。
- 失败即停：所选 SUSFS 带 SELinux 类型/规则账本（`fs/susfs.c` 含 `susfs_add_sus_type`）时，BakaSU 必须在 `selinux/sepolicy.c` 原生调用，否则报错。早于 `0799a678` 的 BakaSU 不能再搭配这类 SUSFS。
- `susfs_feature_compat.py` 识别上游新的 `case ...: { ... }` priority ioctl 写法；上游已自带 `#ifdef` 守卫，脚本不做修改。
- 构建记录 `SELINUX_BACKEND=bakasu-native-susfs-ledger`。

## 验证

- 源码级：用真实源码（BakaSU `63ad1ea3`、SUSFS `784ac9e6`、OEM `security/selinux`）运行 `susfs_ksu_check.py`，54 个外部符号全部有定义；`susfs_feature_compat.py --check` 无改动计划。
- CI：[#45153926661](https://github.com/suhuli/Action-Build-Plus/actions/runs/45153926661)（默认参数）构建成功，管理器按 versionCode 校验后附带。
- 实机：2026-11-23 刷入一加 Ace 竞速版，使用正常。
