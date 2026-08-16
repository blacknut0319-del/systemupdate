# -*- coding: utf-8 -*-
"""pythonw.exe 복사본 → sooplive client.exe / sooplive service.exe (작업관리자 프로세스명용)."""
import os
import shutil
import struct
import sys

CLIENT = "sooplive client.exe"
SERVICE = "sooplive service.exe"
LOCAL_DIR_NAME = "ddong_launchers"
LANG_TABLE = "040904b0"


def local_launcher_dir():
    base = os.environ.get("LOCALAPPDATA", "") or os.path.expanduser("~")
    return os.path.join(base, LOCAL_DIR_NAME)


def _pythonw_source():
    """항상 설치된 원본 pythonw.exe (패치된 sooplive 복사본 제외)."""
    for p in (
        r"C:\Program Files\Python311\pythonw.exe",
        os.path.expandvars(r"%LocalAppData%\Programs\Python\Python311\pythonw.exe"),
    ):
        if os.path.isfile(p):
            return p
    exe = os.path.abspath(sys.executable or "")
    base = os.path.basename(exe).lower()
    if base in ("pythonw.exe", "python.exe"):
        pyw = os.path.join(os.path.dirname(exe), "pythonw.exe")
        return pyw if os.path.isfile(pyw) else exe
    return ""


def _valid_launcher(path):
    try:
        return bool(path) and os.path.isfile(path) and os.path.getsize(path) > 50000
    except Exception:
        return False


def resolve_launcher(name, app_dir=None):
    """쓸 수 있는 런처 경로. 공유폴더 읽기전용이면 LOCALAPPDATA 우선."""
    app_dir = app_dir or os.getcwd()
    local = os.path.join(local_launcher_dir(), name)
    if _valid_launcher(local):
        return local
    app = os.path.join(app_dir, name)
    if _valid_launcher(app):
        return app
    exe = os.path.abspath(sys.executable or "")
    if _valid_launcher(exe) and os.path.basename(exe).lower() == name.lower():
        return exe
    return ""


def _align4(x):
    return (x + 3) & ~3


def _read_utf16z(data, off):
    chars = []
    while off + 1 < len(data):
        c = struct.unpack_from("<H", data, off)[0]
        off += 2
        if c == 0:
            break
        chars.append(chr(c))
    return "".join(chars), off


def _extract_rt_version(path):
    import pefile

    pe = pefile.PE(path, fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]])
    if not hasattr(pe, "DIRECTORY_ENTRY_RESOURCE"):
        return None
    for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if entry.id != pefile.RESOURCE_TYPE["RT_VERSION"]:
            continue
        for res in entry.directory.entries:
            for lang in res.directory.entries:
                rva = lang.data.struct.OffsetToData
                size = lang.data.struct.Size
                return pe.get_data(rva, size)
    return None


def _parse_string_block(data, off):
    wlen, wvlen, _wtype = struct.unpack_from("<HHH", data, off)
    base = off
    off += 6
    key, off = _read_utf16z(data, off)
    off = _align4(off)
    val = ""
    child_start = off
    if wvlen > 0:
        val, off = _read_utf16z(data, off)
        off = _align4(off)
        child_start = off
    return {
        "key": key,
        "value": val,
        "base": base,
        "end": base + wlen,
        "child_start": child_start,
        "wvlen": wvlen,
    }


def _is_lang_table(key):
    return len(key) == 8 and all(c in "0123456789abcdefABCDEF" for c in key)


def _collect_string_pairs(data, off, end, out):
    guard = 0
    while off < end:
        guard += 1
        if guard > 64 or off + 6 > end:
            break
        blk = _parse_string_block(data, off)
        if blk["end"] <= off:
            break
        if blk["wvlen"] > 0:
            if blk["key"] not in ("VS_VERSION_INFO", "StringFileInfo") and not _is_lang_table(blk["key"]):
                out[blk["key"]] = blk["value"]
        elif blk["key"] == "StringFileInfo" or _is_lang_table(blk["key"]):
            if blk["child_start"] < blk["end"]:
                _collect_string_pairs(data, blk["child_start"], blk["end"], out)
        off = _align4(blk["end"])


def _parse_version_strings(data):
    if not data:
        return {}, b"", b""
    wlen, wvlen, _wtype = struct.unpack_from("<HHH", data, 0)
    off = 6
    _root_key, off = _read_utf16z(data, off)
    off = _align4(off)
    fixed = data[off : off + wvlen]
    off = _align4(off + wvlen)
    strings = {}
    varfileinfo = b""
    while off < wlen:
        if off + 6 > wlen:
            break
        blk = _parse_string_block(data, off)
        if blk["end"] <= off:
            break
        if blk["key"] == "StringFileInfo":
            _collect_string_pairs(data, blk["child_start"], blk["end"], strings)
        elif blk["key"] == "VarFileInfo":
            varfileinfo = data[blk["base"] : blk["end"]]
        off = _align4(blk["end"])
    return strings, fixed, varfileinfo


def _build_string(key, value):
    key_b = key.encode("utf-16le") + b"\x00\x00"
    val_b = value.encode("utf-16le") + b"\x00\x00"
    key_pad = _align4(6 + len(key_b))
    val_end = _align4(key_pad + len(val_b))
    wlen = val_end
    wvlen = len(value) + 1
    buf = bytearray(wlen)
    struct.pack_into("<HHH", buf, 0, wlen, wvlen, 1)
    buf[6:key_pad] = key_b.ljust(key_pad - 6, b"\x00")
    buf[key_pad : key_pad + len(val_b)] = val_b
    return bytes(buf)


def _build_container(key, children, wvalue=0):
    key_b = key.encode("utf-16le") + b"\x00\x00"
    key_pad = _align4(6 + len(key_b))
    wlen = _align4(key_pad + len(children))
    buf = bytearray(wlen)
    struct.pack_into("<HHH", buf, 0, wlen, wvalue, 1)
    buf[6:key_pad] = key_b.ljust(key_pad - 6, b"\x00")
    buf[key_pad : key_pad + len(children)] = children
    return bytes(buf)


def _build_version_resource(strings, fixed, varfileinfo):
    order = (
        "CompanyName",
        "FileDescription",
        "FileVersion",
        "InternalName",
        "LegalCopyright",
        "OriginalFilename",
        "ProductName",
        "ProductVersion",
    )
    table_children = b"".join(_build_string(k, strings[k]) for k in order if k in strings)
    string_table = _build_container(LANG_TABLE, table_children)
    string_file_info = _build_container("StringFileInfo", string_table)
    children = string_file_info + (varfileinfo or b"")
    key_b = "VS_VERSION_INFO".encode("utf-16le") + b"\x00\x00"
    key_pad = _align4(6 + len(key_b))
    fixed = fixed or (b"\x00" * 52)
    child_start = _align4(key_pad + len(fixed))
    total = _align4(child_start + len(children))
    buf = bytearray(total)
    struct.pack_into("<HHH", buf, 0, total, len(fixed), 1)
    buf[6:key_pad] = key_b.ljust(key_pad - 6, b"\x00")
    buf[key_pad : key_pad + len(fixed)] = fixed
    buf[child_start : child_start + len(children)] = children
    return bytes(buf)


def _write_rt_version(path, resource):
    import win32api

    h = win32api.BeginUpdateResource(path, 0)
    try:
        win32api.UpdateResource(h, 16, 1, resource, 1033)
        win32api.EndUpdateResource(h, 0)
    except Exception:
        try:
            win32api.EndUpdateResource(h, 1)
        except Exception:
            pass
        raise


def _patch_app_display_name(path, is_client=True):
    """VERSIONINFO FileDescription/ProductName 을 soop client / soop service 로 교체."""
    try:
        original = _extract_rt_version(_pythonw_source() or path)
        if not original:
            original = _extract_rt_version(path)
        strings, fixed, varfileinfo = _parse_version_strings(original)
        if not strings:
            return
        if is_client:
            overrides = {
                "CompanyName": "Soop Client",
                "FileDescription": "soop client",
                "InternalName": "soop client",
                "OriginalFilename": "soop client",
                "ProductName": "soop client",
                "LegalCopyright": "Copyright (c) Soop Client",
            }
        else:
            overrides = {
                "CompanyName": "Soop Service",
                "FileDescription": "soop service",
                "InternalName": "soop service",
                "OriginalFilename": "soop service",
                "ProductName": "soop service",
                "LegalCopyright": "Copyright (c) Soop Service",
            }
        strings.update(overrides)
        resource = _build_version_resource(strings, fixed, varfileinfo)
        _write_rt_version(path, resource)
    except Exception:
        pass


def reexec_target(name, app_dir=None):
    """선호 런처(LOCALAPPDATA 패치본)가 아니면 그 경로 반환."""
    if os.environ.get("DDONG_LAUNCHER") == "1":
        return ""
    app_dir = app_dir or os.getcwd()
    sync_launcher(name, app_dir)
    pref = resolve_launcher(name, app_dir)
    if not _valid_launcher(pref):
        return ""
    cur = os.path.normcase(os.path.abspath(sys.executable or ""))
    if cur == os.path.normcase(os.path.abspath(pref)):
        return ""
    base = os.path.basename(sys.executable or "").lower()
    if base in ("python.exe", "pythonw.exe") or base == name.lower():
        return pref
    return ""


def sync_launcher(name, app_dir=None):
    app_dir = app_dir or os.getcwd()
    src = _pythonw_source()
    if not (src and os.path.isfile(src)):
        return resolve_launcher(name, app_dir) or os.path.join(app_dir, name)
    is_client = "client" in name.lower()
    try:
        os.makedirs(local_launcher_dir(), exist_ok=True)
        local_dst = os.path.join(local_launcher_dir(), name)
        shutil.copy2(src, local_dst)
        _patch_app_display_name(local_dst, is_client=is_client)
    except Exception:
        pass
    try:
        app_dst = os.path.join(app_dir, name)
        shutil.copy2(src, app_dst)
        _patch_app_display_name(app_dst, is_client=is_client)
    except Exception:
        pass
    return resolve_launcher(name, app_dir) or os.path.join(app_dir, name)


def sync_all(app_dir=None):
    app_dir = app_dir or os.path.dirname(os.path.abspath(__file__))
    sync_launcher(CLIENT, app_dir)
    sync_launcher(SERVICE, app_dir)
    return app_dir


if __name__ == "__main__":
    ad = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    sync_all(ad)
    print("ok", ad)
