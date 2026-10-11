**简体中文** | [English](README-en.md)

[![Build](https://img.shields.io/github/actions/workflow/status/suhuli/Action-Build-Plus/Build%20Kernel%20OnePlus.yml?branch=main&label=Build&logo=github-actions&style=flat-square)](https://github.com/suhuli/Action-Build-Plus/actions/workflows/Build%20Kernel%20OnePlus.yml)

# Action-Build-Plus

用 GitHub Actions 为 **一加 Ace 竞速版**（`oneplus_ace_race_t`）编译带 **ReSukiSU / SukiSU-Ultra + SUSFS** 的内核，产物为可直接刷入的 AnyKernel3 刷机包。

| 项目 | 值 |
|---|---|
| 机型 | 一加 Ace 竞速版（MT6895） |
| 系统 | Android 13 |
| 内核 | 5.10.110（GKI，android12-5.10） |
| 源码 | [OnePlusOSS/android_kernel_5.10_oneplus_mt6895](https://github.com/OnePlusOSS/android_kernel_5.10_oneplus_mt6895) `oneplus/mt6895_t_13.0.0_ace_racing` |
| 编译方式 | 极速构建（make + ccache），失败时回退官方脚本 |
| ReSukiSU（默认） | [v4.2.0-rc3](https://github.com/Baka-SU/BakaSU/releases/tag/v4.2.0-rc3)（固定版本，管理器取自同一 release） |
| SukiSU-Ultra | [`builtin`](https://github.com/SukiSU-Ultra/SukiSU-Ultra/tree/builtin) 分支 `6c284e95`（固定提交，版本号 40971，管理器取自 main 分支 CI 构建） |
| SUSFS | v2.3.0（`gki-android12-5.10` 分支 `9892175b`） |
| AnyKernel3 | [Numbersf/AnyKernel3](https://github.com/Numbersf/AnyKernel3) `0fc75698`（固定提交） |
| Baseband-guard | `a54e0dc6`（固定提交） |
| KPM 工具 | [SukiSU-Ultra/SukiSU_patch](https://github.com/SukiSU-Ultra/SukiSU_patch) `547ae94b`（固定提交，仅 SukiSU-Ultra + KPM 使用） |
| 源码清单 | [`manifests/oneplus_ace_race_t.xml`](manifests/oneplus_ace_race_t.xml)，不依赖外部清单仓库 |
| 额外配置 | `CONFIG_USER_NS=y`（部分容器、沙盒类应用需要） |

本项目基于 [Numbersf/Action-Build](https://github.com/Numbersf/Action-Build) 精简而来，只保留这一台机型，默认值按日常使用组合设置，避免误操作。

## 使用

1. 打开 **Actions → Build OnePlus Ace Race T Kernel → Run workflow**。
2. 默认参数就是推荐组合，直接点 **Run workflow** 即可；需要时再调整。
3. 等待约 15～20 分钟（缓存未命中时更久）。构建成功后在运行页面底部的 **Artifacts** 下载刷机包（含配套管理器 APK）。默认**不会**发布 Release；需要发布时运行前勾选 `RELEASE`，会发布到 [Releases](https://github.com/suhuli/Action-Build-Plus/releases)，附带刷机包、管理器 APK 和 SHA-256。
4. 用 Kernel Flasher / Horizon Kernel Flasher 等工具刷入刷机包，或在 Recovery 中刷入。

Artifacts 里的刷机包外面多套了一层 zip，需要先解压一次。

> [!CAUTION]
> 刷内核有风险。刷之前请备份当前 `boot` 分区，变砖时可用它恢复。

## 参数说明

| 参数 | 默认 | 说明 |
|---|---|---|
| 管理器调用方向 `MANAGER_SOURCE` | `RESUKISU` | 内核里集成哪一个 KernelSU：`RESUKISU` 为 ReSukiSU，`SUKISU` 为 SukiSU-Ultra；带 `_SPOOF` 的附带伪装版管理器（随机包名）。SukiSU-Ultra 管理器的 MIUIX / Material 3 界面在管理器设置里切换，不再分两个选项 |
| 内核模块实现 `KPM` | `N/A` | `KPM`/`KPN` 仅 SukiSU-Ultra 可用，ReSukiSU 下会自动跳过 |
| SUSFS 版本 `SUSFS_META` | 空 | 留空使用工作流固定的已验证版本；填提交哈希或回退次数可回退；填 `-1` 关闭 SUSFS（SukiSU-Ultra 不能关闭，见下文） |
| 构建时间 `BUILD_TIME` | `F` | 写入 `uname -v` 的时间。`F` 为实际编译时间，也可填任意时间字符串 |
| 版本参数 `KSU_META` | `//` | 格式 `分支/自定义标识/提交哈希`，三段都可留空，但两个 `/` 不能删 |
| 内核后缀 `SUFFIX` | 空 | `uname -r` 的后缀，留空使用随机字符串 |
| 内核等级 `SUBLEVEL` | 空 | 伪装内核小版本号，系统更新后内核源码未同步导致无法开机时使用 |
| `LSM_BBG` | 开 | Baseband-guard，防止基带/关键分区被恶意改写 |
| `CCM` | 开 | BBR、BBRv3 拥塞控制 + ECN（只编进内核，默认算法不变，需要时用 sysctl 或调度类模块切换） |
| `UNICODE_BYPASS` | 开 | 修复用 Unicode 不可见字符绕过路径检测的漏洞 |
| `DROID_SPACES` / `RE_KERNEL` | 关 | Droid Spaces 容器支持 / Re:Kernel 墓碑支持 |
| `SUSFS_DEV` | 关 | 使用 SUSFS 开发分支，仅测试用 |
| `RELEASE` | 关 | 勾选后，构建成功时发布 Release；默认不发布 |
| `SPACE_NOCLEAN` / `BUILD_NOCCACHE` | 关 | 跳过磁盘清理 / 不使用 ccache |

原项目中对本机型无效的选项（ZRAM、NETFILTER、风驰调度、动态清单、SUSFS 模块打包等）已移除。ReSukiSU / SukiSU-Ultra 管理器都自带 SUSFS 设置，不需要另装 SUSFS 模块。

### ReSukiSU 与 SukiSU-Ultra

| | ReSukiSU | SukiSU-Ultra |
|---|---|---|
| 内核源码 | Baka-SU/BakaSU `v4.2.0-rc3` | SukiSU-Ultra `builtin` 分支（专为内置 SUSFS 的 GKI 内核） |
| 管理器 | 同一 release 的 arm64 APK；伪装版取同一提交的 CI 构建 | main 分支最近一次成功的 CI 构建（`Manager` / `Manager-spoofed`）；CI 产物过期时普通版改附最新正式版 |
| SUSFS | 可关闭 | **必须开启**：`builtin` 分支本身不带 kprobe/系统调用钩子，钩子全部由 SUSFS 补丁提供，关闭后能编译但无法获取 root，所以工作流直接拒绝 |
| KPM / KPN | 不支持 | 支持 |

SukiSU-Ultra `builtin` 分支和 SUSFS v2.3.0 对 `ksu_su_compat_enabled` 的类型定义不一致（SUSFS 2026-04 起改为 static key），[`scripts/ksu_susfs_compat.py`](scripts/ksu_susfs_compat.py) 会在打完 SUSFS 补丁后自动转换；遇到无法识别的代码结构会直接让构建失败，不会悄悄跳过。

### 自定义版本标识

`KSU_META` 第二段会写进管理器显示的内核版本名，只保留字母、数字和 `._+~-`：

```
              ReSukiSU                              SukiSU-Ultra
留空      v4.2.0-rc3-239e1e88@ReSukiSU          v4.2.0-6c284e95@builtin
填 abc    v4.2.0-rc3-abc@ReSukiSU[239e1e88]     v4.2.0-abc@builtin[6c284e95]
```

第一段（分支）和第三段（提交哈希）留空时使用上表的固定版本；填写后改用指定的分支/提交，这类未经验证的构建若勾选了 `RELEASE`，会以**预发布**发布。

刷机包名中的版本号直接取自编译日志，和管理器里显示的一致。

## 补丁检查

SUSFS、Unicode 修复、BBRv3 补丁只要有一处没打上，构建就会直接失败并打印未打上的部分，不会产出缺功能的内核。本机内核与 SUSFS 补丁的兼容修复在 [`scripts/susfs_fixups.py`](scripts/susfs_fixups.py)。

## 自动维护

[Daily Maintenance](.github/workflows/maintenance.yml) 每天北京时间 09:17 运行：

- **检查上游更新**：ReSukiSU 发布新版本，或 SukiSU-Ultra `builtin` 分支、SUSFS、AnyKernel3、Baseband-guard、SukiSU_patch 有新提交时，自动开一个 `upstream-update` Issue，列出新提交。不会自动构建，确认后再更新固定版本。
- **ccache 保活**：每天访问一次编译缓存，避免被 GitHub 删除。

## 缓存

极速构建会用 ccache 缓存编译结果。每次构建成功后保存新缓存并删除旧缓存，只保留最新一份。

需要清理缓存时，运行 **Workflow and Cache Cleanup** 工作流并勾选删除缓存。

## 致谢

- [Numbersf/Action-Build](https://github.com/Numbersf/Action-Build)：原始工作流与补丁
- [ReSukiSU](https://github.com/ReSukiSU/ReSukiSU) · [SukiSU-Ultra](https://github.com/SukiSU-Ultra/SukiSU-Ultra) · [KernelSU](https://github.com/tiann/KernelSU)
- [simonpunk/susfs4ksu](https://gitlab.com/simonpunk/susfs4ksu)
- [osm0sis/AnyKernel3](https://github.com/osm0sis/AnyKernel3) · [Numbersf/AnyKernel3](https://github.com/Numbersf/AnyKernel3)
- [vc-teahouse/Baseband-guard](https://github.com/vc-teahouse/Baseband-guard)

## 许可

见 [LICENSE](LICENSE)（沿用原项目许可）。
