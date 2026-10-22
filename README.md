**简体中文** | [English](README-en.md)

[![Build](https://img.shields.io/github/actions/workflow/status/suhuli/Action-Build-Plus/Build%20Kernel%20OnePlus.yml?branch=test%2Fbakasu-latest-susfs&label=Experimental&logo=github-actions&style=flat-square)](https://github.com/suhuli/Action-Build-Plus/actions/workflows/Build%20Kernel%20OnePlus.yml)

# Action-Build-Plus

用 GitHub Actions 为 **一加 Ace 竞速版**（`oneplus_ace_race_t`）编译带 **ReSukiSU / SukiSU-Ultra + SUSFS** 的内核，产物为可直接刷入的 AnyKernel3 刷机包。

> **当前为 `test/bakasu-latest-susfs` 实验分支，两个仓库的默认 main 均保持原样。** 默认选项 `BAKASU` 使用自己的 [BakaSU 修复分支](https://github.com/suhuli/BakaSU/tree/susfs-android12-5.10)，基于最新上游 main `dac2d186`；旧选项 `RESUKISU` / `RESUKISU_SPOOF` 保留为回退模式。

## 最新组合测试（本分支默认）

- **内核端**：[`suhuli/BakaSU@f7d829cb`](https://github.com/suhuli/BakaSU/commit/f7d829cb62e8555037bf5fada52ce273b92c1ac4)，基于最新官方 main，而不是旧 `sync-susfs` 分支。
- **SUSFS**：直接使用 `gki-android12-5.10` 最新 HEAD（本次适配为 `f43926dc` / v2.3.0）；新模式接口不匹配时立即失败，**不自动降级**。
- **启动链**：保留 BakaSU 现有 init.rc / ksud，显式 `KSU_NO_PREINIT`；**未实现、未启用新的 KernelSU preinit runner**，没有添加空接口。
- **管理器**：取未改动的官方源码基线 `dac2d186` 的官方签名 CI APK；内核版本号绑定为 **35236 / UAPI 5**，修补后的真实提交仍显示在内核名称里。工作流检查 manager/userspace/UAPI 未发生分叉，拒绝随意混用管理器。
- **回退**：选择 `RESUKISU` 可保留原来的 `5b76b884` + 最新兼容 SUSFS 逻辑；也可直接在原 main 上构建。

参数：`MANAGER_SOURCE=BAKASU`、`KSU_META=//`、`SUSFS_META` 留空、`SUSFS_DEV=false`、`RELEASE=false`。

默认 main 不包含新选项，所以 GitHub 网页的 Run workflow 表单可能仍显示旧选项。测试请明确指定分支与参数（或查看本次已触发的测试运行）：

```sh
gh workflow run 'Build Kernel OnePlus.yml' --repo suhuli/Action-Build-Plus \
  --ref test/bakasu-latest-susfs -f MANAGER_SOURCE=BAKASU \
  -f KSU_META=// -f SUSFS_META= -f SUSFS_DEV=false -f RELEASE=false
```

本地已完成真实 5.10.110 源码补丁应用、完整 BakaSU 驱动和 SELinux 对象编译、全部 23 个 SUSFS 修改 C 文件编译及关键对象部分链接（LLVM 19，非 LTO/CFI 配置）。**这些不等于完整生产工具链 Image 构建或实机验证。** 设计、来源、后续升级及验证边界见 [适配说明](docs/bakasu-latest-susfs.md)。

以下表格同时列出保留的旧模式，`RESUKISU` 的固定提交不是新默认 `BAKASU` 的源码。

| 项目 | 值 |
|---|---|
| 机型 | 一加 Ace 竞速版（MT6895） |
| 系统 | Android 13 |
| 内核 | 5.10.110（GKI，android12-5.10） |
| 源码 | [OnePlusOSS/android_kernel_5.10_oneplus_mt6895](https://github.com/OnePlusOSS/android_kernel_5.10_oneplus_mt6895) `oneplus/mt6895_t_13.0.0_ace_racing` |
| 编译方式 | 极速构建（make + ccache），失败时回退官方脚本 |
| BakaSU 旧版回退（RESUKISU） | [`5b76b884`](https://github.com/Baka-SU/BakaSU/commit/5b76b884c75f729a220bb317aa4a4fc78f0e0e9c)（35222 / UAPI 5，版本标签 v4.2.0-rc3；管理器取同一提交的 CI，不使用旧 release APK） |
| BakaSU 修复版（默认 BAKASU） | [`f7d829cb`](https://github.com/suhuli/BakaSU/commit/f7d829cb62e8555037bf5fada52ce273b92c1ac4)（最新上游 main + 5.10 适配；官方管理器基线 `dac2d186`，35236 / UAPI 5） |
| SukiSU-Ultra | [`builtin`](https://github.com/SukiSU-Ultra/SukiSU-Ultra/tree/builtin) 分支 [`05f5cdf0`](https://github.com/SukiSU-Ultra/SukiSU-Ultra/commit/05f5cdf082d32bbc651c205ba4bdd1dc66cca7f5)（固定提交，2026-10-20，UAPI 6；v4.2.1 正式版管理器仍是 UAPI 5，因此配套管理器取 UAPI 相同的 main 最新 CI 构建，内核版本号设为该管理器的 versionCode） |
| SUSFS | v2.3.0（`gki-android12-5.10` 分支；BAKASU 默认严格跟随最新 HEAD；旧模式**自动跟随最新兼容提交**，保底 [`31eb14ad`](https://gitlab.com/simonpunk/susfs4ksu/-/commit/31eb14add587b0a089dfe1819f92cc94920e141e)） |
| AnyKernel3 | [Numbersf/AnyKernel3](https://github.com/Numbersf/AnyKernel3) `0fc75698`（固定提交） |
| Baseband-guard | `a54e0dc6`（固定提交） |
| KPM 工具 | [SukiSU-Ultra/SukiSU_patch](https://github.com/SukiSU-Ultra/SukiSU_patch) `7c6289c9`（固定提交，仅 SukiSU-Ultra + KPM 使用） |
| 源码清单 | [`manifests/oneplus_ace_race_t.xml`](manifests/oneplus_ace_race_t.xml)，不依赖外部清单仓库 |
| 额外配置 | `CONFIG_USER_NS=y`（部分容器、沙盒类应用需要） |

本项目基于 [Numbersf/Action-Build](https://github.com/Numbersf/Action-Build) 精简而来，只保留这一台机型，默认值按日常使用组合设置，避免误操作。

## 使用

1. 打开 **Actions → Build OnePlus Ace Race T Kernel → Run workflow**。
2. 本测试分支默认使用修复后的最新 BakaSU + 最新 SUSFS，参数见上文。选择 `RESUKISU` 时才使用 `5b76b884` + 最新兼容 SUSFS（目前为 `31eb14ad`）。此新组合仍需在本机验证，刷入前备份 `boot`，不要将构建通过当作运行稳定的保证。
3. 等待约 15～20 分钟（缓存未命中时更久）。构建成功后在运行页面底部的 **Artifacts** 下载刷机包（匹配的管理器 CI 产物可用时附带 APK；不可用或版本号不匹配时不附带）。默认**不会**发布 Release；需要发布时运行前勾选 `RELEASE`，会发布到 [Releases](https://github.com/suhuli/Action-Build-Plus/releases)，附带刷机包、管理器 APK 和 SHA-256。
4. 用 Kernel Flasher / Horizon Kernel Flasher 等工具刷入刷机包，或在 Recovery 中刷入。

Artifacts 里的刷机包外面多套了一层 zip，需要先解压一次。

> [!CAUTION]
> 刷内核有风险。刷之前请备份当前 `boot` 分区，变砖时可用它恢复。

## 参数说明

| 参数 | 默认 | 说明 |
|---|---|---|
| 管理器调用方向 `MANAGER_SOURCE` | `BAKASU` | 内核里集成哪一个 KernelSU：`BAKASU` 为最新版修复分支，`RESUKISU` 为旧版回退，`SUKISU` 为 SukiSU-Ultra；带 `_SPOOF` 的附带伪装版管理器（随机包名）。SukiSU-Ultra 管理器的 MIUIX / Material 3 界面在管理器设置里切换，不再分两个选项 |
| 内核模块实现 `KPM` | `N/A` | `KPM`/`KPN` 仅 SukiSU-Ultra 可用，ReSukiSU 下会自动跳过 |
| SUSFS 版本 `SUSFS_META` | 空 | BAKASU 下留空严格使用最新 HEAD、接口不兼容就失败；RESUKISU / SUKISU 下留空自动使用最新兼容提交（保底 `31eb14ad`）；填提交哈希或回退次数可回退；填 `-1` 关闭 SUSFS（BAKASU 测试模式与 SukiSU-Ultra 不能关闭，见下文） |
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

### 保留的旧版 ReSukiSU 回退模式与 SukiSU-Ultra

下表仅描述 `RESUKISU` / `SUKISU`，不是新默认修复版 `BAKASU`。

| | ReSukiSU | SukiSU-Ultra |
|---|---|---|
| 内核源码 | Baka-SU/BakaSU `5b76b884`（标签 v4.2.0-rc3） | SukiSU-Ultra `builtin` 分支（专为内置 SUSFS 的 GKI 内核） |
| 管理器 | 普通版/伪装版都取 `5b76b884` 同一提交的 CI 构建，并校验 APK versionCode 与内核一致；找不到就不附带，不回退到旧 release 或最新 main APK | 按内核 **UAPI 版本**自动挑选：先找 UAPI 相同的最新正式版（伪装版取该版本的 CI 构建），再看 main 最新 CI；都不匹配就不附带。内核 KernelSU 版本号设为所选管理器的 versionCode |
| SUSFS | 可关闭 | **必须开启**：`builtin` 分支本身不带 kprobe/系统调用钩子，钩子全部由 SUSFS 补丁提供，关闭后能编译但无法获取 root，所以工作流直接拒绝 |
| KPM / KPN | 不支持 | 支持 |

> [!IMPORTANT]
> SukiSU-Ultra 管理器与内核的 UAPI 版本必须**完全相同**，否则管理器会提示"需要更新内核"（或"需要更新管理器"），并禁用超级用户、模块等大部分功能。`builtin` 分支的 UAPI 与正式版不一定相同（目前 `builtin` 内核为 6，v4.2.1 正式版管理器仍是 5；以后 main 也可能先升到更高版本），所以**不要自行安装正式版、main 分支或官网最新的管理器**，请使用刷机包里附带的版本。上游 `builtin` 的版本号按编译时 main 分支的提交数计算（越晚编译越大），会与较早的正式版管理器不同，管理器首页因此提示"管理器版本与 KernelSU 驱动版本不匹配"；工作流在编译前选好管理器，并把内核版本号改成该管理器 APK 的 versionCode（[`scripts/apk_version_code.py`](scripts/apk_version_code.py) 读取），两者完全一致。

SukiSU-Ultra `builtin` 分支和 SUSFS v2.3.0 对 `ksu_su_compat_enabled` 的类型定义不一致（SUSFS 2026-04 起改为 static key），[`scripts/ksu_susfs_compat.py`](scripts/ksu_susfs_compat.py) 会在打完 SUSFS 补丁后自动转换；遇到无法识别的代码结构会直接让构建失败，不会悄悄跳过。

### 旧版 RESUKISU 固定提交的限制与回退

新默认 BAKASU 使用修复后的独立分支和明确的集成检查，不通过删除旧版错误提示来伪装兼容。以下说明保留的 RESUKISU 回退模式。

`5b76b884` 是上游加入 SUSFS 编译限制前的最后一个主线提交，不等于已确认无缺陷。它不包含后续 SELinux 隐藏时间侧信道修复，且本项目的新 BakaSU + 5.10 + SUSFS 组合仍需构建及实机验证。工作流保留上游限制，遇到受限的新提交会报错，不删除 `Please wait susfs update.`。

在 `MANAGER_SOURCE=RESUKISU` 下保持 `KSU_META=//` 使用该旧版固定提交；如需回退原来的源码，填 `//239e1e8871b8fcd51a6e5b3002e0ba522fdd99fb`。源码对应该旧 release 时才会使用其 APK。刷机故障时优先恢复已备份且确认能用的 `boot`，修改构建参数不会自动恢复手机。

### 自定义版本标识

`KSU_META` 第二段会写进管理器显示的内核版本名，只保留字母、数字和 `._+~-`：

```
              ReSukiSU                              SukiSU-Ultra
留空      v4.2.0-rc3-5b76b884@BakaSU          v4.2.1-05f5cdf0@builtin
填 abc    v4.2.0-rc3-abc@BakaSU[5b76b884]     v4.2.1-abc@builtin[05f5cdf0]
```

第一段（分支）和第三段（提交哈希）留空时使用上表的固定版本；填写后改用指定的分支/提交，这类未经验证的构建若勾选了 `RELEASE`，会以**预发布**发布。

刷机包名中的版本号直接取自编译日志，和管理器里显示的一致。

## 补丁检查

SUSFS、Unicode 修复、BBRv3 补丁只要有一处没打上，构建就会直接失败并打印未打上的部分，不会产出缺功能的内核。本机内核与 SUSFS 补丁的兼容修复在 [`scripts/susfs_fixups.py`](scripts/susfs_fixups.py)。

### 旧模式：SUSFS 自动跟随最新兼容提交与回退

SUSFS 直接来自 [simonpunk/susfs4ksu](https://gitlab.com/simonpunk/susfs4ksu) 的 `gki-android12-5.10` 分支。在 `RESUKISU` / `SUKISU` 旧模式下，`SUSFS_META` 留空时，**每次构建都会自动使用分支上最新的、与当前 KernelSU 源码接口兼容的提交**。新 BAKASU 模式严格检查最新 HEAD，不走下面的自动回退：

1. 从分支 HEAD 开始往回逐个检查，最多回退到保底提交 [`31eb14ad`](https://gitlab.com/simonpunk/susfs4ksu/-/commit/31eb14add587b0a089dfe1819f92cc94920e141e)（v2.3.0）；
2. 检查由 [`scripts/susfs_ksu_check.py`](scripts/susfs_ksu_check.py) 完成：收集 SUSFS 内核补丁里所有 `extern` 声明的符号，确认 KernelSU 源码中都有**非 static** 的定义（或由内核自身提供）。不满足的提交即使能打上补丁，也会在最后链接时报 `undefined reference`；
3. 选中的不是 HEAD 时，构建日志会给出警告并列出缺少的符号，Release 说明的 SUSFS 一栏也会注明“已自动使用 xxx”；
4. 等 BakaSU / SukiSU-Ultra 跟进新版 SUSFS 并更新固定提交后，下一次构建会自动用上最新 SUSFS，不需要再改 `STABLE_SUSFS_COMMIT`。

> **目前状态（2026-10-21）**：SUSFS 在 2026-10-19 的 `5a3af83e` / `e24d1726` / `f43926dc` 同步了官方 KernelSU 主线，内核补丁开始要求 KernelSU 提供 `ksu_setup_preinit_file`、`ksu_preinit_handle_post_execveat`、`my_setprocattr`、`my_write_context`、`my_write_access`。原版 BakaSU（包括最新主线，它为此加了 `Please wait susfs update.`）和 SukiSU-Ultra `builtin` 最新提交都还没有提供（或只有 static 定义），所以旧模式自动选择的结果仍是 `31eb14ad`。本分支 BAKASU 是明确关闭新 preinit、修复 SELinux 接口的独立兼容方案，不代表原版主线已支持。

这只是接口层面的检查，不能代替完整编译和实机验证；新 SUSFS 被自动选中后，刷入前请备份 `boot`。

保底提交 `31eb14ad` 相对更早的固定提交 `ca7093a1` 包含：

- [`c06d5f8e`](https://gitlab.com/simonpunk/susfs4ksu/-/commit/c06d5f8ef2b53d04c5e1c6b86dc3076f1e0e9f33)：补丁上下文 rebase 到 android12-5.10.257，代码不变。
- [`31eb14ad`](https://gitlab.com/simonpunk/susfs4ksu/-/commit/31eb14add587b0a089dfe1819f92cc94920e141e)：继续修复 selinux_hide——`setprocattr`、`selinuxfs` 的 `context` / `access` 写入改为同时在真实与伪装策略的 sidtab 中注册上下文（对应上游 KernelSU [`a810677b`](https://github.com/tiann/KernelSU/commit/a810677b847ba564c5f9d3fa0fbabe54794b8eef)）。新增的 `my_security_context_to_sid()` 由补丁自身在 `ss/services.c` 中定义；KernelSU 侧仍只需提供 `fake_state` 等原有符号，BakaSU `5b76b884` 与 SukiSU-Ultra `7f1c299a` / `05f5cdf0` 都已提供。

已离线核对：三个提交的补丁都能完整打到本机 5.10.110 源码上（经 `susfs_fixups.py` 处理后无 `.rej`）。仍需完整内核编译和实机验证，刷入前备份 `boot`。

如需构建原来的 SUSFS，在 `SUSFS_META` 填 `ca7093a1a26f7911987110c34a1352d74cfb1d09`（更早的 `82f08351fadb8b19dd6591bd14634d02ad832145` 也可用）；填 `31eb14add587b0a089dfe1819f92cc94920e141e` 可固定使用保底提交；留空则自动跟随最新兼容提交，`SUSFS_DEV` 保持关闭。手动指定的提交如果接口检查不通过，只给警告、继续编译。该参数只改变后续构建，不会恢复已刷入的内核。

## 自动维护

实验分支不会自动合并新的 BakaSU main。以后升级时必须同步更新 fork 的 `kernel/tools/susfs_manager_commit`、本项目的 `manifests/bakasu-susfs.commit`，并重新验证接口、生产工具链构建和实机；不要把当前适配理解为对未来上游任意改动的保证。下面的原维护任务仍主要服务保留的旧模式。

[Daily Maintenance](.github/workflows/maintenance.yml) 每天北京时间 09:17 运行：

- **检查上游更新**：ReSukiSU（BakaSU）发布新版本，或 SukiSU-Ultra `builtin` 分支、SUSFS、AnyKernel3、Baseband-guard、SukiSU_patch 有新提交时，自动开一个 `upstream-update` Issue，列出新提交。SUSFS 一项还会用 `susfs_ksu_check.py` 检查最新提交与固定的 BakaSU / SukiSU-Ultra 是否兼容，并列出缺少的符号。不会自动构建，确认后再更新固定版本。
- **SUSFS 编译限制**：BakaSU 从 2026-10-10（48fa4bb）起在源码里禁止带 SUSFS 编译（`Please wait susfs update.`），要等 SUSFS 跟上新版 KernelSU 后才会解除。维护任务会检查最新 release 是否仍有这个限制（有的话在 Issue 里提示暂勿升级），并在 main 分支解除限制、但还没有新 release 时提醒，同时附上 [#622](https://github.com/Baka-SU/BakaSU/issues/622)（旧内核开启隐藏 SELinux 后终端 `exec` 被拒；上游说明为 5.4/4.19/4.14，不能直接套用到本项目 5.10）的状态。该问题已于 2026-10-13 在 BakaSU main 修复（sidtab 重复分配 SID，[#623](https://github.com/Baka-SU/BakaSU/pull/623) 等），但该修复不在固定的 `5b76b884` 里；是否需要回移要按具体源码判断。主线仍受限时保持固定提交，待 SUSFS 兼容和编译限制解除后再评估升级。
- **ccache 保活**：每天访问一次编译缓存，避免被 GitHub 删除。

## 缓存

极速构建会用 ccache 缓存编译结果。每次构建成功后保存新缓存并删除旧缓存，只保留最新一份。

需要清理缓存时，运行 **Workflow and Cache Cleanup** 工作流并勾选删除缓存。

## 致谢

- [Numbersf/Action-Build](https://github.com/Numbersf/Action-Build)：原始工作流与补丁
- [BakaSU（原 ReSukiSU）](https://github.com/Baka-SU/BakaSU) · [SukiSU-Ultra](https://github.com/SukiSU-Ultra/SukiSU-Ultra) · [KernelSU](https://github.com/tiann/KernelSU)
- [simonpunk/susfs4ksu](https://gitlab.com/simonpunk/susfs4ksu)
- [osm0sis/AnyKernel3](https://github.com/osm0sis/AnyKernel3) · [Numbersf/AnyKernel3](https://github.com/Numbersf/AnyKernel3)
- [vc-teahouse/Baseband-guard](https://github.com/vc-teahouse/Baseband-guard)

## 许可

见 [LICENSE](LICENSE)（沿用原项目许可）。
