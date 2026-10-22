# 最新 BakaSU + 最新 SUSFS：5.10 独立适配测试

本分支用于一加 Ace 竞速版 / MT6895 / Android 13 / Linux 5.10.110（GKI android12-5.10）。**不修改两个仓库的默认 main，不把构建通过当作实机稳定保证。**

## 版本与来源

- BakaSU 修复仓库：`suhuli/BakaSU`，分支 `susfs-android12-5.10`。精确提交记录在 [`manifests/bakasu-susfs.commit`](../manifests/bakasu-susfs.commit)。
- 上游基线：官方 main `dac2d186406a0d2b0ce3c67cad5a1fa1adbf9f4d`，不是回退到旧 `sync-susfs`。
- SUSFS：`simonpunk/susfs4ksu` 的 `gki-android12-5.10` 最新 HEAD；适配时为 `f43926dc94b8ffbf9b74321313536600f69367b1`，v2.3.0。
- 机型内核：`OnePlusOSS/android_kernel_5.10_oneplus_mt6895`，`oneplus/mt6895_t_13.0.0_ace_racing`，提交 `3e31a817f1b13a54312c21b3c53114ab76e42a16`。
- SELinux 实现参考官方 [PR #624](https://github.com/Baka-SU/BakaSU/pull/624) 与 [xmicro 的修复](https://github.com/xmicro/BakaSU/commit/0e5b14206b0ee2fa9d8ce62f4b351ad01e2ea4cc)。保留所有原许可证与来源说明。

## 修复内容与明确边界

### SELinux 是真实修复，不是空实现

开放并编译真正的 `my_write_context`、`my_write_access`，增加 `my_setprocattr` 包装，SUSFS 调用路径不再回落到未安装的自动 hook。保留 5.10 所需、6.12 构建无法覆盖的 `<6.6` `fake_state` 声明与初始化。

### 初始化采用显式兼容模式

**没有移植新的 KernelSU preinit runner。** BakaSU 目前还有自己的 init.rc / ksud 启动链。本次使用 SUSFS 官方支持的 `KSU_NO_PREINIT` 可选路径，保留该旧启动链，不添加假的 `ksu_setup_preinit_file` 或 `ksu_preinit_handle_post_execveat`。

完整 preinit 不只是两个接口，还包括 runner ELF、构建规则、生命周期、用户态模块准备、失败启动计数等。当前改动没有宣称具备这些新增功能，仍需验证普通 root、模块、启动事件及 SELinux 隐藏的实机表现。

### 跨仓库编译契约

1. Fork 提供版本化 `kernel/include/bakasu_susfs_compat.h`；
2. 项目 [`scripts/bakasu_susfs_compat.py`](../scripts/bakasu_susfs_compat.py) 验证版本、完整 preinit 条件保护、目标 5.10、SELinux hook 和现有启动链，然后把原样头文件复制到内核 `include/linux/`，在 `fs/exec.c` 的可选接口之前引用；
3. Fork Kbuild 检查目标版本、built-in KSU、当前 SUSFS hook、已安装头文件与引用，不是删除旧 `Please wait...` 后无条件继续；
4. 接口检查器只有显式 `--bakasu-legacy-init` 且源码契约通过时才排除被宏真正保护的 preinit 引用。不永久忽略两个函数，也不忽略任何其他缺失接口。未知条件分支保守保留；
5. 安装器支持 `--check`，重复执行幂等；不支持的源码结构直接失败。

现有 `susfs_fixups.py` 仍处理本机 5.10.110 补丁上下文和缺失 VMA 宏，不搬用 xmicro 的 6.12 task_mmu 修补。

## 管理器为什么不从 Fork 随意拿 APK

下游只改内核，`manager/`、`userspace/`、`uapi/` 与官方 `dac2d186` 完全相同。Fork 没有官方签名私钥，而且多出的修补提交会让按 HEAD 提交数计算的版本号增加。

因此：

- Fork 的 `kernel/tools/susfs_manager_commit` 记录正式的上游源码基线，SUSFS 构建按它计算版本号（当前 **35236 / UAPI 5**）；内核显示名仍含修补提交，不隐藏下游身份。
- [`scripts/bakasu_manager_pair.py`](../scripts/bakasu_manager_pair.py) 验证完整提交图、基线存在、三个用户态/UAPI 目录无改动（包括未跟踪源文件）及 Kbuild 版本绑定。
- 下载管理器时使用官方仓库的**精确基线提交**成功 CI，仍检查 APK `versionCode`；找不到则不附带，不退回旧 Release，也不下载另一个 main 最新 APK 充数。
- 构建日志不能确认内核版本号与预期一致时，新模式直接失败，不产出配错版本的刷机包。
- 不要求、不复制上游签名秘密，也不削弱内核的 APK 信任检查。

## 默认行为与回退

| 选项 | 内核来源 | SUSFS 留空行为 |
|---|---|---|
| **BAKASU / BAKASU_SPOOF** | 自己的修复 Fork，提交固定在清单文件 | **最新 HEAD，严格检查，不自动降级** |
| RESUKISU / RESUKISU_SPOOF | 原官方 `5b76b884` 回退组合 | 保留“最新兼容提交，保底 31eb14ad” |
| SUKISU / SUKISU_SPOOF | 原 builtin 固定提交 | 保留原逻辑 |

`BAKASU` 是 SUSFS 适配测试配置，拒绝 `SUSFS_META=-1`；要关闭 SUSFS 请切换 RESUKISU（需要最新原版、无 SUSFS 时可指定 main）。手动指定 SUSFS hash/回退次数仍是显式覆盖，但新模式检查失败会停止。任何上游 API 破坏都不通过静默回退来掩盖。

`KSU_META` 仍为三段 `分支/自定义标识/提交哈希`，不是 xmicro 工作流的四段格式。默认 `//` 固定精确适配提交；自定义 ref 仍必须满足本分支契约。

## 运行独立测试分支

保持主分支原样时，GitHub 网页 Run workflow 表单可能只显示主分支里的旧选项。可靠方式是显式指定测试 ref：

```sh
gh workflow run 'Build Kernel OnePlus.yml' --repo suhuli/Action-Build-Plus \
  --ref test/bakasu-latest-susfs -f MANAGER_SOURCE=BAKASU \
  -f KSU_META=// -f SUSFS_META= -f SUSFS_DEV=false -f RELEASE=false
```

不会默认发布 Release；即使手动勾选 RELEASE，实验配置也始终标记预发布。ZIP 内新增 `build-info.json`，记录实际修补 SHA、管理器源码基线、SUSFS 完整 SHA、初始化模式及 Image/APK 校验和；仅写白名单字段，不序列化环境变量或凭据。

## 构建环境修正

第一次完整工作流运行在 Ubuntu 26.04，旧 APT 缓存 action 没有实际安装依赖，导致 ccache 初始化退出（未进入内核编译）。本测试分支已改为固定 Ubuntu 22.04，以匹配旧 OnePlus/Android 构建工具链；使用显式 apt 安装并验证必需工具，ccache 缺失直接报错。原项目 main 未改动。Fork 同时固定 clang-format 19.1.7，修正两处继承的上游空白格式问题，不改用户态或 UAPI。

## 已做的本地检查与尚待验证

- 新旧模式回归、严格选源、条件引用、头文件契约、安装幂等、管理器基线拒绝分叉、APK 版本检查、构建版本不匹配失败、来源记录不泄露凭据；
- 原始机型源码上的最新 SUSFS 完整补丁应用，无 `.rej`；
- 真实 arm64 对象编译：完整 BakaSU 驱动、SELinux 子目录、SUSFS 全部 23 个修改 C 文件及 `fs/susfs.c`；
- 用真实对象部分链接，验证三个 SELinux 外部接口、5.10 `fake_state` 及关闭 preinit 后无相应未定义引用。

**本地对象检查使用 Debian LLVM 19，`CONFIG_LTO_NONE=y`、CFI 关闭。它不是原生产 Android 工具链的完整 Image / LTO / CFI 构建，也不是开机验证。** 完整构建需查看测试分支的 Actions 运行；产物仍须在备份 boot 后进行实机验收。

实机至少核对：开机、管理器识别与版本、授权 root、模块 post-fs-data/service/boot-completed、重启后状态、SELinux enforcing 与隐藏开关、SUSFS 功能查询及已启用功能、不出现新增 avc/exec 异常。异常时恢复已备份的已知可用 boot，不是改参数就能恢复手机。

## 以后如何继续跟进最新 main

这不是自动绕过未来接口变化的“永久兼容”补丁。更新流程：

1. 在 Fork 测试分支合入最新上游 main，保留并审查本次修补；
2. 更新 `kernel/tools/susfs_manager_commit`，确认用户态/UAPI 未分叉，管理器 CI 可获得；
3. 跑 Fork 测试及项目测试，记录新的下游提交，更新本项目 `manifests/bakasu-susfs.commit`；
4. 对当前 SUSFS HEAD 重跑完整项目构建与实机回归，再决定是否合并默认分支。

现有 maintenance 工作流仍主要维护旧模式，不会自动把未经验证的新主线合进这个 Fork。
