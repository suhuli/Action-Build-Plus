#!/usr/bin/env python3
"""SUSFS 补丁与本机内核（5.10.110）之间的兼容修复。

用法:
  susfs_fixups.py pre  <内核 common 目录>   打补丁前：把源码改成补丁期望的写法
  susfs_fixups.py post <内核 common 目录>   打补丁后：补齐补丁用到但内核缺少的定义

每项修复都会先检查是否需要，不需要则跳过；源码结构与预期不符时直接报错退出。
"""
import re
import sys
from pathlib import Path


def fix_fdinfo(root: Path) -> None:
    # 旧版 5.10 的 inotify_fdinfo() 使用局部变量 mask，新版改用 inotify_mark_user_mask()。
    # SUSFS 补丁按新版写法生成，旧写法会导致 fdinfo.c 第 4 块打不上（隐藏 inotify 痕迹的代码缺失）。
    p = root / "fs/notify/fdinfo.c"
    if not p.exists():
        return
    s = p.read_text()
    if "inotify_mark_user_mask" in s:
        print("fdinfo.c: 已是新写法，跳过")
        return
    head = "static void inotify_fdinfo(struct seq_file *m, struct fsnotify_mark *mark)\n"
    start = s.find(head)
    if start < 0:
        sys.exit("fdinfo.c: 找不到 inotify_fdinfo()，请检查源码")
    end = s.find("\n}\n", start)
    body = s[start:end]
    new = re.sub(
        r"\n[ \t]*/\*\n(?:[ \t]*\*[^\n]*\n)*?[ \t]*\*/\n[ \t]*u32 mask = mark->mask & IN_ALL_EVENTS;\n",
        "\n", body, count=1)
    new = new.replace("ignored_mask:%x", "ignored_mask:0", 1)
    new = re.sub(r"(?<![>\w])mask,\s*mark->ignored_mask\)", "inotify_mark_user_mask(mark))", new, count=1)
    if new.count("inotify_mark_user_mask(mark)") != 1 or "u32 mask" in new:
        sys.exit("fdinfo.c: inotify_fdinfo() 结构与预期不符，请检查源码")
    helper = ("static inline u32 inotify_mark_user_mask(struct fsnotify_mark *mark)\n"
              "{\n\treturn mark->mask & IN_ALL_EVENTS;\n}\n\n")
    # 辅助函数放在 #ifdef CONFIG_INOTIFY_USER 之前，避免改变补丁上下文
    anchor = s.rfind("#ifdef CONFIG_INOTIFY_USER\n", 0, start)
    if anchor < 0:
        sys.exit("fdinfo.c: 找不到 CONFIG_INOTIFY_USER，请检查源码")
    p.write_text(s[:anchor] + helper + s[anchor:start] + new + s[end:])
    print("fdinfo.c: 已改为 inotify_mark_user_mask() 写法")


def fix_vma_pad_start(root: Path) -> None:
    # SUSFS v2.3.0 起 show_map_vma() 的新增代码使用 VMA_PAD_START()（来自 pgsize 迁移补丁），
    # 本机内核没有该补丁；此时 VMA 末尾没有填充页，VMA_PAD_START 就等于 vm_end。
    p = root / "fs/proc/task_mmu.c"
    if not p.exists():
        return
    s = p.read_text()
    if "VMA_PAD_START(" not in s:
        return
    if re.search(r"#include <linux/pgsize_migration(_inline)?\.h>|define VMA_PAD_START", s):
        print("task_mmu.c: 内核已定义 VMA_PAD_START，跳过")
        return
    lines = s.split("\n")
    last_inc = max(i for i, l in enumerate(lines) if l.startswith("#include"))
    lines[last_inc + 1:last_inc + 1] = [
        "#ifndef VMA_PAD_START",
        "#define VMA_PAD_START(vma) ((vma)->vm_end)",
        "#endif",
    ]
    p.write_text("\n".join(lines))
    print("task_mmu.c: 已补充 VMA_PAD_START 回退定义")


def _enclosing_returns_void(s: str, pos: int) -> bool:
    # 内核代码风格：函数体的 { 位于行首，函数头在它前面
    brace = s.rfind("\n{\n", 0, pos)
    if brace < 0:
        sys.exit("task_mmu.c: 找不到 goto show_pad 所在的函数，请检查源码")
    head_start = max(s.rfind("\n}\n", 0, brace), s.rfind("\n\n", 0, brace))
    head = s[head_start:brace]
    m = re.search(r"(\w[\w\s\*]*?)\b(\w+)\s*\(", head)
    if not m:
        sys.exit("task_mmu.c: 无法识别 goto show_pad 所在函数的返回类型，请检查源码")
    return re.fullmatch(r"(?:static\s+)?(?:inline\s+)?void\s*", m.group(1).strip() + " ") is not None


def fix_show_pad(root: Path) -> None:
    # 部分 SUSFS 版本的 show_map_vma() 新增代码会 goto show_pad，而该标签来自本机内核没有的
    # pgsize 迁移补丁。没有这个标签时直接返回（等价于没有填充页），否则编译失败。
    # show_map_vma() 返回 void，要用 "return;"；返回 int 的函数才用 "return 0;"。
    p = root / "fs/proc/task_mmu.c"
    if not p.exists():
        return
    s = p.read_text()
    if not re.search(r"goto\s+show_pad;", s) or re.search(r"^show_pad:", s, re.M):
        return
    out, last = [], 0
    for m in re.finditer(r"goto\s+show_pad;", s):
        out.append(s[last:m.start()])
        out.append("return;" if _enclosing_returns_void(s, m.start()) else "return 0;")
        last = m.end()
    out.append(s[last:])
    p.write_text("".join(out))
    print("task_mmu.c: 内核没有 show_pad 标签，已改为直接返回")


def main() -> None:
    if len(sys.argv) != 3 or sys.argv[1] not in ("pre", "post"):
        sys.exit(__doc__)
    root = Path(sys.argv[2])
    if sys.argv[1] == "pre":
        fix_fdinfo(root)
    else:
        fix_vma_pad_start(root)
        fix_show_pad(root)


if __name__ == "__main__":
    main()
