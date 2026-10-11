#!/usr/bin/env python3
"""SukiSU-Ultra（builtin 分支）与 SUSFS 内核补丁之间的接口兼容修复。

用法:
  ksu_susfs_compat.py <KernelSU/kernel 目录> <内核 common 目录>

SUSFS 从 1886ea1（2026-04-26，v2.1.0 之后）起把 ksu_su_compat_enabled 当作
static key 使用：

    extern struct static_key_true ksu_su_compat_enabled;
    if (static_branch_likely(&ksu_su_compat_enabled)) ...

同一提交里 SUSFS 也把 KernelSU 侧的定义改成了 DEFINE_STATIC_KEY_TRUE，ReSukiSU 也已跟进；
但 SukiSU-Ultra builtin 分支仍定义为 bool。两边类型不一致时编译和链接都不会报错，
运行时却会出问题：
  - 开机时 jump_label_init() 会把这个 1 字节的 bool 当成 struct static_key，
    写入其后 8 字节偏移处的 entries 字段，覆盖相邻变量；
  - 管理器里关闭「su 兼容」后，SUSFS 内联钩子中的分支不会随之关闭。

本脚本按 SUSFS 对 KernelSU 的同款修改，把 SukiSU 的定义改成 static key。
只在「内核补丁按 static key 引用、KernelSU 仍定义为 bool」时修改，其他情况跳过；
源码结构与预期不符时直接报错退出，不会产出半改的内核。
"""
import re
import sys
from pathlib import Path

SYM = "ksu_su_compat_enabled"


def fail(msg: str) -> None:
    sys.exit(f"::error title=KSU/SUSFS compat::{msg}")


def kernel_wants_static_key(common: Path) -> bool:
    pat = re.compile(r"extern\s+struct\s+static_key_true\s+" + SYM + r"\s*;")
    for rel in ("fs/exec.c", "fs/open.c", "fs/stat.c", "fs/read_write.c", "kernel/reboot.c"):
        p = common / rel
        if p.exists() and pat.search(p.read_text(errors="replace")):
            return True
    return False


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    ksu, common = Path(sys.argv[1]), Path(sys.argv[2])
    c_file, h_file = ksu / "feature/sucompat.c", ksu / "feature/sucompat.h"
    if not c_file.exists() or not h_file.exists():
        fail(f"找不到 {c_file} / {h_file}，KernelSU 源码结构与预期不符")

    if not kernel_wants_static_key(common):
        print(f"内核侧没有按 static key 引用 {SYM}，跳过")
        return

    c, h = c_file.read_text(), h_file.read_text()
    if re.search(r"DEFINE_STATIC_KEY_TRUE\(\s*" + SYM + r"\s*\)", c):
        print(f"KernelSU 已将 {SYM} 定义为 static key，跳过")
        return

    # ---- sucompat.c ----
    # 先改读取处（此时文件里还没有 DEFINE_STATIC_KEY_TRUE(...)，不会误改）：
    # if (!ksu_su_compat_enabled) / if (ksu_su_compat_enabled)
    c = re.sub(r"(?<![&\w])!\s*" + SYM + r"\b", f"!static_branch_likely(&{SYM})", c)
    c = re.sub(r"\(\s*" + SYM + r"\s*\)", f"(static_branch_likely(&{SYM}))", c)
    edits = [
        (r"^bool\s+" + SYM + r"\s+__read_mostly\s*=\s*true\s*;",
         f"DEFINE_STATIC_KEY_TRUE({SYM});"),
        (r"\*value\s*=\s*" + SYM + r"\s*\?\s*1\s*:\s*0\s*;",
         f"*value = static_key_enabled(&{SYM}) ? 1 : 0;"),
        (r"^(?P<ind>[ \t]*)" + SYM + r"\s*=\s*enable\s*;",
         r"\g<ind>if (enable)\n\g<ind>    static_branch_enable(&" + SYM + r");\n"
         r"\g<ind>else\n\g<ind>    static_branch_disable(&" + SYM + r");"),
    ]
    for pat, rep in edits:
        c, n = re.subn(pat, rep, c, count=1, flags=re.M)
        if n != 1:
            fail(f"sucompat.c 中没有找到预期的写法: {pat}")
    leftovers = [l.strip() for l in c.splitlines()
                 if re.search(r"(?<![&\w])" + SYM + r"\b", l) and "DEFINE_STATIC_KEY_TRUE" not in l]
    if leftovers:
        fail("sucompat.c 中还有未处理的用法: " + " | ".join(leftovers))

    # ---- sucompat.h ----
    h, n = re.subn(r"extern\s+bool\s+" + SYM + r"\s*;",
                   f"extern struct static_key_true {SYM};", h, count=1)
    if n != 1:
        fail(f"sucompat.h 中没有找到 extern bool {SYM};")
    if "#include <linux/jump_label.h>" not in h:
        h, n = re.subn(r"^(#include <linux/types.h>\n)", r"\1#include <linux/jump_label.h>\n", h, count=1, flags=re.M)
        if n != 1:
            h = re.sub(r"^(#include [^\n]+\n)", r"\1#include <linux/jump_label.h>\n", h, count=1, flags=re.M)

    # 其他文件不应直接读写这个变量（否则同样类型不一致）
    others = [str(p.relative_to(ksu)) for p in ksu.rglob("*.[ch]")
              if p not in (c_file, h_file)
              and re.search(r"(?<![&\w])" + SYM + r"\b", p.read_text(errors="replace"))]
    if others:
        fail(f"以下文件也直接使用了 {SYM}，需要一并适配: {', '.join(others)}")

    c_file.write_text(c)
    h_file.write_text(h)
    print(f"已将 SukiSU-Ultra 的 {SYM} 改为 static key（与 SUSFS 内核补丁一致）")


if __name__ == "__main__":
    main()
