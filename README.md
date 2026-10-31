**简体中文** | [English](README-en.md)

# Action-Build-Plus

为 **一加 Ace 竞速版**（`oneplus_ace_race_t` / MT6895 / Android 13）编译 Linux **5.10.110** 内核，生成 AnyKernel3 刷机包。

## 仅保留三个组合

| `PROFILE` | 组合 | 用途 |
|---|---|---|
| **`BAKASU`（默认）** | **BakaSU + SUSFS，无 KPM** | 用户常用方案；不下载或运行 KPM 工具 |
| `SUKISU` | SukiSU-Ultra builtin + SUSFS，无 KPM | SukiSU 方案 |
| `SUKISU_KPM` | SukiSU-Ultra builtin + SUSFS + KPM | 需要 KPM 模块的测试方案 |

不再提供旧版回退、自定义 KernelSU/SUSFS 分支或提交、关闭 SUSFS、SUSFS 开发分支、KPN、伪装版管理器等额外入口。删除的是构建配置与旧 KPN 工具，不删除历史 Git 提交、Release、Artifacts，也不会改变手机里现有的内核。

## 本轮固定版本（2026-10-31 核对）

**“最新版”指本轮核实的上游最新提交，而不是每次构建自动漂移到未知 HEAD。** 所有组件统一记录在 [`config/versions.json`](config/versions.json)。今后的更新先核对兼容性，再更新该清单。

| 组件 | 固定提交 |
|---|---|
| BakaSU main | [`5785bdb8`](https://github.com/Baka-SU/BakaSU/commit/5785bdb8091304322f597f67d50e0b79f9815cb2) |
| SukiSU-Ultra builtin | [`b16e899a`](https://github.com/SukiSU-Ultra/SukiSU-Ultra/commit/b16e899a555e9b96aa1225f049cd7274820ca5b8)，UAPI 6 |
| SUSFS | [`8930474a`](https://gitlab.com/simonpunk/susfs4ksu/-/commit/8930474a298d07ab9f1beca926779cbc3656b79e)，`gki-android12-5.10`，v2.3.0，三个组合共用 |
| SukiSU 管理器 main | [`a5742cda`](https://github.com/SukiSU-Ultra/SukiSU-Ultra/commit/a5742cdae02147973f9cc29db8888de62c1bae9d)，UAPI 6 |
| KPM 工具 SukiSU_patch | [`eec45788`](https://github.com/SukiSU-Ultra/SukiSU_patch/commit/eec45788c9a115e5498040298133336d6b6071dd)，运行前校验 `patch_linux` SHA-256 |
| Baseband-guard | [`028ff7fd`](https://github.com/vc-teahouse/Baseband-guard/commit/028ff7fd509e2104596da7cc1ef8e6ce2a0c9082) |
| AnyKernel3 | [`47f23f7e`](https://github.com/Numbersf/AnyKernel3/commit/47f23f7ece3ef212a392ec9ea5466e5f0b55d3c7)，**v31.0 beta** |
| 机型源码 | [OnePlusOSS/android_kernel_5.10_oneplus_mt6895](https://github.com/OnePlusOSS/android_kernel_5.10_oneplus_mt6895)，`oneplus/mt6895_t_13.0.0_ace_racing` |
| 构建环境 | Ubuntu 22.04；make + ccache，保留官方构建脚本回退 |

> **新组合仍需完整编译和实机验证。** 静态接口检查、补丁成功、离线测试通过或构建成功，都不能证明能稳定开机。此前可用的是旧组合，并非这轮新组合。保留当前可用刷机包和可恢复的 boot 备份。所有这轮产物仍标记预发布。

## 使用

1. Actions → **Build OnePlus Ace Race T Kernel** → Run workflow，选择 `main`。
2. 常用 BakaSU 无 KPM 直接保留 **`PROFILE=BAKASU`**；另外两种从同一下拉框选择。
3. 默认 `RELEASE=false`，不自动发布；从成功运行的 Artifacts 下载。外层 Artifacts zip 需先解压，再使用里面的 AnyKernel3 zip。
4. 刷机前核对机型、构建 PROFILE、版本清单和管理器，备份当前 boot，准备恢复途径。
5. 只有显式勾选 `RELEASE` 才发布预发布版本。

### 其他保留参数

| 参数 | 默认 | 说明 |
|---|---|---|
| `BUILD_TIME` | `Mon Oct 24 22:45:30 UTC 2022` | 构建时间，`F` 为实际 UTC 时间 |
| `SUFFIX` | `9-00011-g8efa13274425-ab9212784` | 内核后缀；清空时使用随机字符串 |
| `SUBLEVEL` | 空 | 自定义内核小版本标识 |
| `LSM_BBG` | 开 | Baseband-guard 关键分区写入保护 |
| `CCM` | 开 | 编入 BBR / BBRv3，不更改默认拥塞算法 |
| `UNICODE_BYPASS` | 开 | Unicode 不可见字符路径检测绕过修复 |
| `DROID_SPACES` / `RE_KERNEL` | 关 | 容器 / Re:Kernel 支持 |
| `RELEASE` | 关 | 显式发布预发布版本 |
| `SPACE_NOCLEAN` / `BUILD_NOCCACHE` | 关 | 跳过空间清理 / 禁用 ccache |

## 兼容性与管理器

- 三种组合均强制启用固定 SUSFS。不再自动回到较旧兼容提交，也不再“检查失败但继续编译”。接口检查或补丁失败即停止。
- BakaSU 不绕过上游 SUSFS 编译限制。只附带与内核**同一提交**的成功 CI 管理器，并核对 APK versionCode；缺失时警告且不附带，不拿旧 release APK 代替。
- SukiSU 内核来自 builtin，管理器来自清单中固定的 main 提交。构建前核对 UAPI，绑定 APK versionCode；找不到该提交管理器或无法配对时停止，不降级到旧 release 管理器。
- 保留 `ksu_susfs_compat.py` 的 bool → static-key 适配；脚本只在预期源码结构下修改，结构不符停止。
- `SUKISU_KPM` 才启用 `CONFIG_KPM`、下载固定工具并检查 SHA-256、处理 Image。补丁程序必须成功生成非空且改变后的 oImage；其他两个组合不执行该工具。
- 静态检查不是完整预处理器，不验证所有类型、Kbuild 可达性、ABI 或实机行为。SHA-256 只核对下载完整性，不证明二进制功能正确或安全。
- 不把 BakaSU 的 SUSFS priority UID filter 声称为已完成端到端支持；管理器、调度集成和实际功能另行验证。

## 测试与维护

```sh
python3 -m unittest discover -s tests -v
```

离线测试使用本地合成源码、模拟网络和模拟工具，不触发内核构建或执行上游 KPM 二进制。CI 在 main 推送 / PR 时运行。

`maintenance.yml` 每日比对版本清单与上游，只更新提示 Issue，不自动升级或触发编译。幂等 GET 对限流、网络错误和部分 5xx 做有限重试，尊重 `Retry-After`；等待时间过长则明确失败。**任一上游查询失败，不得报告“已是最新”或关闭更新 Issue。** 保留 ccache 保活。

## 实机验收

至少检查开机、重启、管理器识别和 root 授权、现有模块的各启动阶段、SELinux enforcing 与相关开关、SUSFS 查询及所用功能、无新增 avc/exec 异常。KPM 组合额外验证模块加载、卸载与重启持久性。实机验收必须由持有设备的人完成。

## 致谢与许可

基于 [Numbersf/Action-Build](https://github.com/Numbersf/Action-Build)。感谢 BakaSU、SukiSU-Ultra、KernelSU、simonpunk/susfs4ksu、Numbersf/AnyKernel3、osm0sis/AnyKernel3、vc-teahouse/Baseband-guard。沿用原许可，见 [LICENSE](LICENSE)。
