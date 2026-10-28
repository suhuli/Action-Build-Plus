**简体中文** | [English](README-en.md)

[![Build](https://img.shields.io/github/actions/workflow/status/suhuli/Action-Build-Plus/Build%20Kernel%20OnePlus.yml?branch=main&label=Build&logo=github-actions&style=flat-square)](https://github.com/suhuli/Action-Build-Plus/actions/workflows/Build%20Kernel%20OnePlus.yml)

# Action-Build-Plus

为 **一加 Ace 竞速版**（`oneplus_ace_race_t` / MT6895 / Android 13）编译带 **BakaSU / SukiSU-Ultra + SUSFS** 的 Linux 5.10.110 内核，生成 AnyKernel3 刷机包。

## 当前版本（2026-10-28）

本轮直接更新 `main`，使用官方 BakaSU，不依赖旧测试分支或修复 Fork。为兼容旧参数，BakaSU 的选项仍叫 `RESUKISU` / `RESUKISU_SPOOF`。

| 组件 | 固定版本 / 策略 |
|---|---|
| 机型源码 | [OnePlusOSS/android_kernel_5.10_oneplus_mt6895](https://github.com/OnePlusOSS/android_kernel_5.10_oneplus_mt6895)，`oneplus/mt6895_t_13.0.0_ace_racing` |
| BakaSU（默认） | 官方 [`d5e9e025`](https://github.com/Baka-SU/BakaSU/commit/d5e9e025b8b49155f8014684d64c91742b465f65)（2026-10-24），包含上游原生 preinit；不绕过上游 SUSFS 限制，不沿用旧 Fork 的 `KSU_NO_PREINIT` 适配 |
| SUSFS（默认 BakaSU） | v2.3.0，`gki-android12-5.10` 最新兼容提交；保底 [`eb95da08`](https://gitlab.com/simonpunk/susfs4ksu/-/commit/eb95da080c76724c4962d0c62e9af3be37d9d439)，包含 priority UID filter 的 UAF / worker 修复 |
| SukiSU-Ultra（本轮未升级） | `builtin` [`05f5cdf0`](https://github.com/SukiSU-Ultra/SukiSU-Ultra/commit/05f5cdf082d32bbc651c205ba4bdd1dc66cca7f5)，UAPI 6 |
| SukiSU / 显式旧版 BakaSU 的 SUSFS 保底 | [`31eb14ad`](https://gitlab.com/simonpunk/susfs4ksu/-/commit/31eb14add587b0a089dfe1819f92cc94920e141e)，保留旧组合的回退能力 |
| Baseband-guard | [`028ff7fd`](https://github.com/vc-teahouse/Baseband-guard/commit/028ff7fd509e2104596da7cc1ef8e6ce2a0c9082)，适配回移的 `selinux_cred` |
| AnyKernel3 | Numbersf [`47f23f7e`](https://github.com/Numbersf/AnyKernel3/commit/47f23f7ece3ef212a392ec9ea5466e5f0b55d3c7)，**v31.0 beta**；这次上游更新更换 `magiskboot` / `magiskpolicy` 二进制 |
| KPM 工具（本轮未升级） | SukiSU_patch `7c6289c9`，仅 SukiSU-Ultra + KPM 使用 |
| 构建环境 | 固定 Ubuntu 22.04，显式安装依赖并验证工具；make + ccache，失败时回退官方构建脚本 |

> [!CAUTION]
> 新 BakaSU + SUSFS + AnyKernel3 beta 组合仍需完整构建和实机验证。静态检查、补丁成功或构建通过都不代表能稳定开机。刷入前备份当前 `boot`，异常时恢复已知可用的备份。

## 使用

1. 打开 **Actions → Build OnePlus Ace Race T Kernel → Run workflow**，选择 `main`。
2. 默认 `MANAGER_SOURCE=RESUKISU`、`KSU_META=//`、`SUSFS_META` 留空。
3. 默认不发布 Release；从成功运行的 **Artifacts** 下载刷机包。Artifacts 外层 zip 需先解压一次。
4. 管理器仅在同提交的成功 CI 产物可下载且 APK versionCode 匹配时附带；不可用则不附带，不拿旧 release 或另一个 main APK 代替。
5. 手动勾选 `RELEASE` 才发布；使用当前 AnyKernel3 beta 的构建始终标记**预发布**。

## 参数说明

| 参数 | 默认 | 说明 |
|---|---|---|
| 管理器调用方向 `MANAGER_SOURCE` | `RESUKISU` | 内核里集成哪一个 KernelSU：`RESUKISU` 为 BakaSU，`SUKISU` 为 SukiSU-Ultra；带 `_SPOOF` 的附带伪装版管理器（随机包名）。SukiSU-Ultra 管理器的 MIUIX / Material 3 界面在管理器设置里切换，不再分两个选项 |
| 内核模块实现 `KPM` | `N/A` | `KPM`/`KPN` 仅 SukiSU-Ultra 可用，BakaSU 下会自动跳过 |
| SUSFS 版本 `SUSFS_META` | 空 | 留空自动使用 SUSFS 分支上与当前 KernelSU 接口兼容的最新提交（默认 BakaSU 保底 `eb95da08`；SukiSU/旧版回退保底 `31eb14ad`）；填提交哈希或回退次数可回退；填 `-1` 关闭 SUSFS（SukiSU-Ultra 不能关闭，见下文） |
| 构建时间 `BUILD_TIME` | `Mon Oct 24 22:45:30 UTC 2022` | 写入 `uname -v` 的时间（自动加上 `#1 SMP PREEMPT`）。默认与原厂内核一致；`F` 为实际编译时间，也可填任意时间字符串 |
| 版本参数 `KSU_META` | `//` | 格式 `分支/自定义标识/提交哈希`，三段都可留空，但两个 `/` 不能删 |
| 内核后缀 `SUFFIX` | `9-00011-g8efa13274425-ab9212784` | `uname -r` 中 `5.10.110-android12-` 之后的部分。默认与原厂内核一致；清空则使用随机字符串 |
| 内核等级 `SUBLEVEL` | 空 | 伪装内核小版本号，系统更新后内核源码未同步导致无法开机时使用 |
| `LSM_BBG` | 开 | Baseband-guard，防止基带/关键分区被恶意改写 |
| `CCM` | 开 | BBR、BBRv3 拥塞控制（只编进内核，默认算法不变，需要时用 sysctl 或调度类模块切换）。ECN 不需要编译选项，任何内核都可以用 `sysctl net.ipv4.tcp_ecn` 开关 |
| `UNICODE_BYPASS` | 开 | 修复用 Unicode 不可见字符绕过路径检测的漏洞 |
| `DROID_SPACES` / `RE_KERNEL` | 关 | Droid Spaces 容器支持 / Re:Kernel 墓碑支持 |
| `SUSFS_DEV` | 关 | 使用 SUSFS 开发分支，仅测试用 |
| `RELEASE` | 关 | 勾选后，构建成功时发布 Release；默认不发布 |
| `SPACE_NOCLEAN` / `BUILD_NOCCACHE` | 关 | 跳过磁盘清理 / 不使用 ccache |

原项目中对本机型无效的选项（ZRAM、NETFILTER、风驰调度、动态清单、SUSFS 模块打包等）已移除。ReSukiSU / SukiSU-Ultra 管理器都自带 SUSFS 设置，不需要另装 SUSFS 模块。

## 管理器与接口检查

- BakaSU 使用与固定源码**同一提交**的官方 CI 管理器，校验 APK versionCode。源码与旧 release 完全相同时，才允许使用相应 release APK。
- SukiSU-Ultra 按内核 **UAPI** 选择兼容的正式版 / main CI，并将内核版本号绑定到管理器 APK versionCode。不要自行混装不匹配的最新管理器。
- SukiSU `builtin` 必须开启 SUSFS，否则即使能编译也无法正常获取 root。BakaSU 可通过 `SUSFS_META=-1` 关闭。
- `scripts/susfs_ksu_check.py` 检查补丁需要的非 static 符号。本轮增加对 BakaSU 已审查的 `my_setprocattr` 宏别名识别：要求真实函数定义、SUSFS hook 与上游 Kbuild 检测契约同时存在，不忽略缺失符号、不生成空实现。
- 该检查不是完整 C 预处理器，不验证所有类型、配置、Kbuild 可达性或运行语义，不能代替完整编译和实机测试。
- BakaSU 最新源码不包含 SUSFS priority UID filter 的完整管理器/调度集成；本次更新 SUSFS 内核侧与修复，**不宣称已启用该新功能的端到端支持**。

## SUSFS 选源和回退

留空时从分支 HEAD 向后检查，默认 BakaSU 最多回退到 `eb95da08`，不能悄悄回退到这次更新之前。SukiSU 和显式旧版 BakaSU 保留 `31eb14ad` 保底。自动模式无兼容提交则停止；显式指定的提交接口检查失败时沿用旧行为：警告并继续编译。

- 固定本次 SUSFS：`SUSFS_META=eb95da080c76724c4962d0c62e9af3be37d9d439`。
- 回退上一次 BakaSU：`KSU_META=//5b76b884c75f729a220bb317aa4a4fc78f0e0e9c`，配 `SUSFS_META=31eb14add587b0a089dfe1819f92cc94920e141e`。
- 更早 BakaSU release：`KSU_META=//239e1e8871b8fcd51a6e5b3002e0ba522fdd99fb`。
- 更早 SUSFS：`ca7093a1a26f7911987110c34a1352d74cfb1d09` 或 `82f08351fadb8b19dd6591bd14634d02ad832145`，仅用于明确的兼容性回退，不保证适合新 BakaSU。

`KSU_META` 格式仍为 `分支/自定义标识/提交哈希`。自定义分支/哈希优先于默认固定版本；未验证组合保持预发布。修改参数不会恢复已经刷入的手机。

## 构建与自动维护

- 依赖显式 apt 安装，缺少 `ccache`、编译器等必需工具时提前失败，不依赖 APT 缓存命中。
- SUSFS、Unicode 和 BBRv3 补丁失败即停止；`susfs_fixups.py` 处理本机 5.10.110 的上下文差异和 VMA 宏。
- `.github/workflows/compat-tests.yml` 在 main 推送 / PR 时跑离线回归，可本地执行：`python3 -m unittest discover -s tests -v`。
- `maintenance.yml` 每日检查 BakaSU 主线、SUSFS、SukiSU、AnyKernel3、Baseband-guard、KPM 工具并维护更新 Issue，不自动升级固定版本；保留 ccache 保活。
- 缓存清理使用 **Workflow and Cache Cleanup**，无需保留旧测试分支。未请求升级的 SukiSU 和 KPM 固定版本不变。

## 实机验收

至少检查：开机、管理器识别与授权 root、模块 post-fs-data/service/boot-completed、重启后状态、SELinux enforcing / 隐藏开关、SUSFS 查询及已启用功能、无新增 avc/exec 异常。保留可恢复的原始 boot。

## 致谢与许可

基于 [Numbersf/Action-Build](https://github.com/Numbersf/Action-Build)。感谢 BakaSU、SukiSU-Ultra、KernelSU、simonpunk/susfs4ksu、Numbersf/AnyKernel3、osm0sis/AnyKernel3、vc-teahouse/Baseband-guard。沿用原项目许可，见 [LICENSE](LICENSE)。
