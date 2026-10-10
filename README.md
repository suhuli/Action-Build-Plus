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

本项目基于 [Numbersf/Action-Build](https://github.com/Numbersf/Action-Build) 精简而来，只保留这一台机型，默认值按日常使用组合设置，避免误操作。

## 使用

1. 打开 **Actions → Build OnePlus Ace Race T Kernel → Run workflow**。
2. 默认参数就是推荐组合，直接点 **Run workflow** 即可；需要时再调整。
3. 等待约 25 分钟（缓存命中时更快），在运行页面底部 **Artifacts** 下载 `AnyKernel3_...` 压缩包。
4. 解压一次得到内层刷机包，用 Kernel Flasher / Horizon Kernel Flasher 等工具刷入，或在 Recovery 中刷入。

> [!CAUTION]
> 刷内核有风险。刷之前请备份当前 `boot` 分区，变砖时可用它恢复。

## 参数说明

| 参数 | 默认 | 说明 |
|---|---|---|
| 管理器调用方向 `MANAGER_SOURCE` | `RESUKISU` | 内核里集成哪一个 KernelSU 分支。`RESUKISU` 对应 ReSukiSU；`MIUIX`/`MD3` 对应 SukiSU-Ultra 的两种界面；`_SPOOF` 为伪装版管理器 |
| SUSFS 模块 `SUSFS_CI` | `N/A` | 是否把 SUSFS 用户态模块打包进刷机包 |
| 内核模块实现 `KPM` | `N/A` | `KPM`/`KPN` 仅 SukiSU-Ultra 可用，ReSukiSU 不支持 |
| SUSFS 版本 `SUSFS_META` | 空 | 留空使用工作流固定的已验证版本；填提交哈希或回退次数可回退；填 `-1` 关闭 SUSFS |
| 动态清单 `DYNAMIC_REPO` | `Numbersf` | 动态源码清单仓库的所有者，一般不用改 |
| 构建时间 `BUILD_TIME` | `F` | 写入 `uname -v` 的时间。`F` 为实际编译时间，也可填任意时间字符串 |
| 版本参数 `KSU_META` | `//` | 格式 `分支/自定义标识/提交哈希`，三段都可留空，但两个 `/` 不能删 |
| ZRAM `ZRAM` | `0/lz4kd/8589934592` | `开关/算法/大小`。5.10 内核找不到 `zram.ko`，目前不建议开启 |
| 内核后缀 `SUFFIX` | 空 | `uname -r` 的后缀，留空使用随机字符串 |
| 内核等级 `SUBLEVEL` | 空 | 伪装内核小版本号，系统更新后内核源码未同步导致无法开机时使用 |
| 极速构建 `FAST_BUILD` | 开 | MTK 机型必须开启 |
| `LSM_BBG` | 开 | Baseband-guard，防止基带/关键分区被恶意改写 |
| `CCM` | 开 | BBR 拥塞控制 + ECN |
| `NETFILTER` | 开 | 网络功能扩展，MTK 机型上不生效 |
| `UNICODE_BYPASS` | 开 | 修复用 Unicode 不可见字符绕过路径检测的漏洞 |
| `SCHED_HMBIRD` | 关 | 风驰调度，本机型不支持 |
| `DROID_SPACES` / `RE_KERNEL` | 关 | Droid Spaces 容器支持 / Re:Kernel 墓碑支持 |
| `SUSFS_DEV` | 关 | 使用 SUSFS 开发分支，仅测试用 |
| `SPACE_NOCLEAN` / `BUILD_NOCCACHE` | 关 | 跳过磁盘清理 / 不使用 ccache |

### 自定义版本标识

`KSU_META` 第二段会写进管理器显示的内核版本名，只保留字母、数字和 `._+~-`：

```
留空      v4.2.0-rc3-239e1e88@ReSukiSU
填 abc    v4.2.0-rc3-abc@ReSukiSU[239e1e88]
```

刷机包名中的版本号直接取自编译日志，和管理器里显示的一致。

## 缓存

极速构建会用 ccache 缓存编译结果。GitHub 会删除 7 天没被访问的缓存，所以隔一段时间再编译会变慢，这是正常的。

需要清理缓存时，运行 **Workflow and Cache Cleanup** 工作流并勾选删除缓存。

## 致谢

- [Numbersf/Action-Build](https://github.com/Numbersf/Action-Build)：原始工作流与补丁
- [ReSukiSU](https://github.com/ReSukiSU/ReSukiSU) · [SukiSU-Ultra](https://github.com/SukiSU-Ultra/SukiSU-Ultra) · [KernelSU](https://github.com/tiann/KernelSU)
- [simonpunk/susfs4ksu](https://gitlab.com/simonpunk/susfs4ksu)
- [osm0sis/AnyKernel3](https://github.com/osm0sis/AnyKernel3)
- [vc-teahouse/Baseband-guard](https://github.com/vc-teahouse/Baseband-guard)
- ZRAM 附加模块来自 [@FURLC](https://github.com/FURLC)

## 许可

见 [LICENSE](LICENSE)（沿用原项目许可）。
