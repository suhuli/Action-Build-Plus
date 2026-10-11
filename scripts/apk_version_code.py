#!/usr/bin/env python3
"""打印 APK 的 versionCode（读取 AndroidManifest.xml 二进制 XML，不依赖 aapt/Android SDK）。

用法: apk_version_code.py <file.apk>
成功时输出一个整数并返回 0；读取失败返回 1。
"""
import struct
import sys
import zipfile

RES_STRING_POOL = 0x0001
RES_XML = 0x0003
RES_XML_RESOURCE_MAP = 0x0180
RES_XML_START_ELEMENT = 0x0102
ATTR_VERSION_CODE = 0x0101021B  # android:versionCode
TYPE_INT_DEC = 0x10
TYPE_INT_HEX = 0x11
TYPE_STRING = 0x03


def parse_string_pool(buf, off):
    _, header_size, _ = struct.unpack_from("<HHI", buf, off)
    count, _, flags, strings_start, _ = struct.unpack_from("<IIIII", buf, off + 8)
    utf8 = bool(flags & 0x100)
    offsets = struct.unpack_from(f"<{count}I", buf, off + header_size)
    base = off + strings_start
    out = []
    for o in offsets:
        p = base + o
        if utf8:
            # UTF-16 长度（1～2 字节）+ UTF-8 字节长度（1～2 字节）
            n = buf[p]; p += 2 if n & 0x80 else 1
            n = buf[p]
            if n & 0x80:
                n = ((n & 0x7F) << 8) | buf[p + 1]; p += 2
            else:
                p += 1
            out.append(buf[p:p + n].decode("utf-8", "replace"))
        else:
            (n,) = struct.unpack_from("<H", buf, p); p += 2
            if n & 0x8000:
                (lo,) = struct.unpack_from("<H", buf, p); p += 2
                n = ((n & 0x7FFF) << 16) | lo
            out.append(buf[p:p + n * 2].decode("utf-16-le", "replace"))
    return out


def version_code(apk):
    with zipfile.ZipFile(apk) as z:
        buf = z.read("AndroidManifest.xml")
    typ, header_size, _ = struct.unpack_from("<HHI", buf, 0)
    if typ != RES_XML:
        raise ValueError("AndroidManifest.xml 不是二进制 XML")
    strings, res_ids = [], []
    off = header_size
    while off + 8 <= len(buf):
        typ, hsize, size = struct.unpack_from("<HHI", buf, off)
        if size == 0:
            break
        if typ == RES_STRING_POOL:
            strings = parse_string_pool(buf, off)
        elif typ == RES_XML_RESOURCE_MAP:
            res_ids = list(struct.unpack_from(f"<{(size - hsize) // 4}I", buf, off + hsize))
        elif typ == RES_XML_START_ELEMENT:
            _, name = struct.unpack_from("<iI", buf, off + 16)
            attr_start, attr_size, attr_count = struct.unpack_from("<HHH", buf, off + 24)
            if strings[name] == "manifest":
                for i in range(attr_count):
                    a = off + 16 + attr_start + i * attr_size
                    _, aname, raw, _, _, dtype, data = struct.unpack_from("<iIiHBBI", buf, a)
                    is_vc = (aname < len(res_ids) and res_ids[aname] == ATTR_VERSION_CODE) \
                        or strings[aname] == "versionCode"
                    if not is_vc:
                        continue
                    if dtype in (TYPE_INT_DEC, TYPE_INT_HEX):
                        return data
                    if dtype == TYPE_STRING:
                        return int(strings[data])
                    if raw >= 0:
                        return int(strings[raw])
                raise ValueError("manifest 中没有 versionCode")
        off += size
    raise ValueError("找不到 manifest 元素")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    try:
        print(version_code(sys.argv[1]))
    except Exception as e:  # noqa: BLE001
        print(f"读取 versionCode 失败: {e}", file=sys.stderr)
        sys.exit(1)
