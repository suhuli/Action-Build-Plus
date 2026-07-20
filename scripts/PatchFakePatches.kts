#!/usr/bin/env kotlin
import java.io.File
import kotlin.system.exitProcess

/** sed '/pattern/a text' —— 在匹配到的每一行之后插入若干新行 */
fun File.insertAfter(anchor: Regex, vararg newLines: String) {
    val out = mutableListOf<String>()
    for (line in readLines()) {
        out.add(line)
        if (anchor.containsMatchIn(line)) out.addAll(newLines)
    }
    writeText(out.joinToString("\n") + "\n")
}

fun File.insertAfterFirst(anchor: Regex, vararg newLines: String) {
    val out = mutableListOf<String>()
    var inserted = false
    for (line in readLines()) {
        out.add(line)
        if (!inserted && anchor.containsMatchIn(line)) {
            out.addAll(newLines)
            inserted = true
        }
    }
    writeText(out.joinToString("\n") + "\n")
}

/** sed '/pattern/i text' —— 在匹配到的每一行之前插入若干新行 */
fun File.insertBefore(anchor: Regex, vararg newLines: String) {
    val out = mutableListOf<String>()
    for (line in readLines()) {
        if (anchor.containsMatchIn(line)) out.addAll(newLines)
        out.add(line)
    }
    writeText(out.joinToString("\n") + "\n")
}

/** sed '/pattern/d' —— 删除匹配到的行 */
fun File.deleteLine(pattern: Regex) {
    val out = readLines().filterNot { pattern.containsMatchIn(it) }
    writeText(out.joinToString("\n") + "\n")
}

/** sed '/start/,/end/d' —— 删除从 start 到 end(含首尾)的整段,支持多段 */
fun File.deleteBlock(start: Regex, end: Regex) {
    val out = mutableListOf<String>()
    var inBlock = false
    for (line in readLines()) {
        if (!inBlock && start.containsMatchIn(line)) {
            inBlock = true
            continue
        }
        if (inBlock) {
            if (end.containsMatchIn(line)) inBlock = false
            continue
        }
        out.add(line)
    }
    writeText(out.joinToString("\n") + "\n")
}

/** perl -pe 's/pattern/repl/' —— 逐行做正则替换(支持 pattern 内的反向引用 \1) */
fun File.replaceEachLine(pattern: Regex, replacement: String) {
    val out = readLines().map { pattern.replace(it, replacement) }
    writeText(out.joinToString("\n") + "\n")
}

/** sed 's/exact_old/exact_new/' —— 整行精确替换 */
fun File.replaceWholeLine(oldLine: String, newLine: String) {
    val out = readLines().map { if (it == oldLine) newLine else it }
    writeText(out.joinToString("\n") + "\n")
}

val kmi = System.getenv("KMI") ?: ""
val sublevel = (System.getenv("SUBLEVEL") ?: "0").toIntOrNull() ?: 0
val mode = args.getOrNull(0) ?: "apply" // apply | revert
val workDir = args.getOrNull(1) ?: "kernel_workspace/kernel_platform/common"

fun f(relPath: String) = File(workDir, relPath)

val fdinfoCommentStart = Regex("""^[ \t]*/\*$""")
val fdinfoCommentEnd = Regex("""^[ \t]*u32 mask = mark->mask & IN_ALL_EVENTS;$""")

fun applyFdinfo(file: File) {
    file.deleteBlock(fdinfoCommentStart, fdinfoCommentEnd)
    file.replaceEachLine(Regex("""\bmask,\s*mark->ignored_mask"""), "inotify_mark_user_mask(mark)")
    file.replaceEachLine(Regex("""ignored_mask:%x"""), "ignored_mask:0")
}

fun revertFdinfo(file: File) {
    file.insertAfter(
        Regex("""^\s+if \(inode\) \{"""),
        "\t\t/*",
        "\t\t * IN_ALL_EVENTS represents all of the mask bits",
        "\t\t * that we expose to userspace.  There is at",
        "\t\t * least one bit (FS_EVENT_ON_CHILD) which is",
        "\t\t * used only internally to the kernel.",
        "\t\t */",
        "\t\tu32 mask = mark->mask & IN_ALL_EVENTS;"
    )
    file.replaceEachLine(Regex("""\binotify_mark_user_mask\(mark\)"""), "mask, mark->ignored_mask")
    file.replaceEachLine(Regex("""ignored_mask:0"""), "ignored_mask:%x")
}

// android15-6.6 SUBLEVEL<=30 特殊单独处理

fun applyAndroid15VmaBlock(taskMmu: File, namespace: File) {
    // 1) 在含 smap_gather_stats(vma, &mss, last_vma_end); 的行之后插入新语句
    taskMmu.insertAfter(
        Regex("""smap_gather_stats\(vma, &mss, last_vma_end\);"""),
        "last_vma_end = vma->vm_end;"
    )

    // 2) 从文件末尾往前找最后一处 "last_vma_end = vma->vm_end;"，
    //    给它加缩进并在其后补一个 "}"，再往前找最近的
    //    "if (vma->vm_end > last_vma_end)" 把行尾的 ")" 换成 ") {"
    val lines = taskMmu.readLines().toMutableList()
    val ifPattern = Regex("""if\s*\(vma->vm_end > last_vma_end\)""")
    val trailingParen = Regex("""\)\s*$""")

    for (i in lines.indices.reversed()) {
        if (lines[i].contains("last_vma_end = vma->vm_end;")) {
            lines[i] = "\t\t\t\t" + lines[i]
            lines.add(i + 1, "\t\t\t}")
            for (j in i downTo 0) {
                if (ifPattern.containsMatchIn(lines[j])) {
                    lines[j] = trailingParen.replace(lines[j], ") {")
                    break
                }
            }
            break
        }
    }
    taskMmu.writeText(lines.joinToString("\n") + "\n")

    // 3) namespace.c: 在 trace/hooks/blk.h 之后插入 trace/hooks/fs.h
    namespace.insertAfter(Regex("""#include <trace/hooks/blk\.h>"""), "#include <trace/hooks/fs.h>")

    // 4) task_mmu.c: 在 "int ret = 0, copied = 0;" 之后插入两行
    taskMmu.insertAfter(
        Regex("""int ret = 0, copied = 0;"""),
        "\tunsigned int nr_subpages = __PAGE_SIZE / PAGE_SIZE;",
        "\tpagemap_entry_t *res = NULL;"
    )
}

fun revertAndroid15VmaBlock(taskMmu: File, namespace: File) {
    namespace.deleteLine(Regex("""#include <trace/hooks/fs\.h>"""))
    taskMmu.deleteLine(Regex("""unsigned int nr_subpages = __PAGE_SIZE / PAGE_SIZE;"""))
    taskMmu.deleteLine(Regex("""pagemap_entry_t \*res = NULL;"""))
}

// Main
fun apply() {
    if (kmi == "android12-5.10") {
        if (sublevel <= 43) {
            println("Applying base.c Android 12 5.10 Fake Patch")
            f("fs/proc/base.c").replaceEachLine(
                Regex("""(int|size_t)\s+this_len\s*=\s*min_t\s*\(\s*\1\s*,"""),
                "size_t this_len = min_t(size_t,"
            )
        }
        if (sublevel <= 117) {
            println("Applying fdinfo.c Android 12 5.10 Fake Patch")
            applyFdinfo(f("fs/notify/fdinfo.c"))
        }
    }

    if (kmi == "android13-5.15") {
        if (sublevel <= 41) {
            println("Applying namespace.c Android 13 5.15 SUSFS fixes")
            f("fs/namespace.c").insertAfter(
                Regex("""^#include <linux/shmem_fs\.h>$"""),
                "#include <linux/mnt_idmapping.h>"
            )
            println("Applying open.c Android 13 5.15 Fake Patch")
            f("fs/open.c").insertAfter(
                Regex("""^#include <linux/compat\.h>$"""),
                "#include <linux/mnt_idmapping.h>"
            )
            println("Applying fdinfo.c Android 13 5.15 Fake Patch")
            applyFdinfo(f("fs/notify/fdinfo.c"))
        }
        if (sublevel >= 123) {
            println("Applying memory.c Android 13 5.15 Fake Patch")
            f("mm/memory.c").deleteLine(Regex("""#include <linux/swap_slots\.h>"""))
        }
        if (sublevel >= 197) {
            println("Applying namespace.c Android 13 5.15 Fake Patch")
            f("fs/namespace.c").deleteLine(Regex("""^#include <trace/hooks/blk\.h>$"""))
        }
        if (sublevel >= 206) {
            println("Applying task_mmu.c Android 13 5.15 Fake Patch")
            f("fs/proc/task_mmu.c").deleteLine(Regex("""^#include <trace/hooks/mm\.h>$"""))
        }
    }

    if (kmi == "android14-6.1") {
        if (sublevel <= 141) {
            println("Applying base.c Android 14 6.1 Fake Patch")
            f("fs/proc/base.c").insertAfter(
                Regex("""^#include <linux/cpufreq_times\.h>$"""),
                "#include <linux/dma-buf.h>"
            )
        }
        if (sublevel >= 157) {
            println("Applying namespace.c Android 14 6.1 Fake Patch")
            f("fs/namespace.c").deleteLine(Regex("""^#include <trace/hooks/blk\.h>$"""))
        }
    }

    if (kmi == "android15-6.6") {
        if (sublevel <= 30) {
            println("Applying taskmmu.c、namespace.c Android 15 6.6 Fake Patch")
            applyAndroid15VmaBlock(f("fs/proc/task_mmu.c"), f("fs/namespace.c"))
        }
        if (sublevel <= 57) {
            println("Applying memory.c Android 15 6.6 Fake Patch")
            f("mm/memory.c").insertAfter(
                Regex("""^#include <linux/sched/sysctl\.h>$"""),
                "#include <linux/zswap.h>"
            )
        }
        if (sublevel <= 92) {
            println("Applying base.c Android 15 6.6 Fake Patch")
            f("fs/proc/base.c").insertAfter(
                Regex("""^#include <linux/cpufreq_times\.h>$"""),
                "#include <linux/dma-buf.h>"
            )
        }
    }

    if (kmi == "android16-6.12") {
        if (sublevel >= 58) {
            println("Applying exec.c Android 16 6.12 Fake Patch")
            f("fs/exec.c").deleteLine(Regex("""^#include <linux/dma-buf\.h>$"""))
        }
    }
}

fun revert() {
    if (kmi == "android12-5.10") {
        if (sublevel <= 43) {
            println("Reverting base.c Android 12 5.10 Fake Patch")
            f("fs/proc/base.c").replaceWholeLine(
                "size_t this_len = min_t(size_t, count, PAGE_SIZE);",
                "int this_len = min_t(int, count, PAGE_SIZE);"
            )
        }
        if (sublevel <= 117) {
            println("Reverting fdinfo.c Android 12 5.10 Fake Patch")
            revertFdinfo(f("fs/notify/fdinfo.c"))
        }
    }

    if (kmi == "android13-5.15") {
        if (sublevel <= 41) {
            println("Reverting namespace.c Android 13 5.15 Fake Patch")
            f("fs/namespace.c").deleteLine(Regex("""#include <linux/mnt_idmapping\.h>$"""))
            println("Reverting open.c Android 13 5.15 Fake Patch")
            f("fs/open.c").deleteLine(Regex("""#include <linux/mnt_idmapping\.h>$"""))
            println("Reverting fdinfo.c Android 13 5.15 Fake Patch")
            revertFdinfo(f("fs/notify/fdinfo.c"))
            f("fs/susfs.c").replaceEachLine(
                Regex(Regex.escape("i_uid_into_mnt(i_user_ns(&fi->inode), &fi->inode).val")),
                "i_uid_into_mnt(&init_user_ns, &fi->inode).val"
            )
            f("fs/susfs.c").replaceEachLine(
                Regex(Regex.escape("i_uid_into_mnt(i_user_ns(inode), inode).val")),
                "i_uid_into_mnt(&init_user_ns, inode).val"
            )
        }
        if (sublevel >= 123) {
            println("Reverting memory.c Android 13 5.15 Fake Patch")
            f("mm/memory.c").insertBefore(
                Regex("""#ifdef CONFIG_KSU_SUSFS_SUS_MAP"""),
                "#include <linux/swap_slots.h>"
            )
        }
        if (sublevel >= 197) {
            println("Reverting namespace.c Android 13 5.15 Fake Patch")
            f("fs/namespace.c").insertAfter(
                Regex("""^#include "internal\.h"$"""),
                "#include <trace/hooks/blk.h>"
            )
        }
        if (sublevel >= 206) {
            println("Reverting task_mmu.c Android 13 5.15 Fake Patch")
            f("fs/proc/task_mmu.c").insertAfter(
                Regex("""^#include <linux/pkeys\.h>$"""),
                "#include <trace/hooks/mm.h>"
            )
        }
    }

    if (kmi == "android14-6.1") {
        if (sublevel <= 141) {
            println("Reverting base.c Android 14 6.1 Fake Patch")
            f("fs/proc/base.c").deleteLine(Regex("""^#include <linux/dma-buf\.h>$"""))
        }
        if (sublevel >= 157) {
            println("Reverting namespace.c Android 14 6.1 Fake Patch")
            f("fs/namespace.c").insertAfter(
                Regex("""^#include "internal\.h"$"""),
                "#include <trace/hooks/blk.h>"
            )
        }
    }

    if (kmi == "android15-6.6") {
        if (sublevel <= 30) {
            println("Reverting taskmmu.c、namespace.c Android 15 6.6 Fake Patch")
            revertAndroid15VmaBlock(f("fs/proc/task_mmu.c"), f("fs/namespace.c"))
        }
        if (sublevel <= 57) {
            println("Reverting memory.c Android 15 6.6 Fake Patch")
            f("mm/memory.c").deleteLine(Regex("""^#include <linux/zswap\.h>$"""))
        }
        if (sublevel <= 92) {
            println("Reverting base.c Android 15 6.6 Fake Patch")
            f("fs/proc/base.c").deleteLine(Regex("""^#include <linux/dma-buf\.h>$"""))
        }
    }

    if (kmi == "android16-6.12") {
        if (sublevel >= 58) {
            println("Reverting exec.c Android 16 6.12 Fake Patch")
            f("fs/exec.c").insertAfterFirst(Regex("""^#include """), "#include <linux/dma-buf.h>")
        }
    }
}

when (mode) {
    "apply" -> apply()
    "revert" -> revert()
    else -> {
        println("Usage: kotlin PatchFakePatches.main.kts <apply|revert> [workDir]")
        exitProcess(1)
    }
}
