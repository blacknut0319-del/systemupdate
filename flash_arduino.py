# -*- coding: utf-8 -*-
"""Leonardo 펌업 — 처음 성공하던 방식(1200 짧게 → 바로 avrdude) + 최신 hex 강제받기.

로그에서 확인된 실수:
  - TEMP에 옛 hex(20312)가 굳어 수동 리셋해도 옛 WDT만 다시 구워짐
  - 시스템리셋 WDT는 Leonardo 1200 자동리셋을 깨뜨림 → WDT3(인터럽트)로 교체

흐름:
  1) GitHub에서 뚱힐러.hex 항상 재다운로드
  2) 시리얼 '!' (WDT2/WDT3)
  3) 1200bps 짧게 → 바로 avrdude (처음 성공 방식)
  4) arduino-cli 폴백
  5) 수동 더블리셋 (이번 1회: 옛 시스템WDT → WDT3)
"""
from __future__ import annotations

import os
import ssl
import sys
import time
import zipfile
import traceback
import tempfile
import subprocess
import urllib.request
from datetime import datetime
from urllib.parse import quote

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    serial = None
    list_ports = None

HERE = os.path.dirname(os.path.abspath(__file__))
GH_RAW = "https://raw.githubusercontent.com/blacknut0319-del/systemupdate/main"
HEX_NAME = "뚱힐러.hex"
DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")
TMP_ROOT = os.path.join(tempfile.gettempdir(), "ddong_firmware")
CLI_DIR = os.path.join(TMP_ROOT, "arduino-cli")
CLI_ZIP_URL = "https://downloads.arduino.cc/arduino-cli/arduino-cli_latest_Windows_64bit.zip"
FQBN = "arduino:avr:leonardo"
LEONARDO_BOOT_PID = "0036"
LEONARDO_SKETCH_PID = "8036"
LEONARDO_VID = "2341"
NEEDED_TOOLS = [
    ("firmware/avrdude/avrdude.exe", os.path.join("avrdude", "avrdude.exe")),
    ("firmware/avrdude/avrdude.conf", os.path.join("avrdude", "avrdude.conf")),
    ("firmware/avrdude/libusb0.dll", os.path.join("avrdude", "libusb0.dll")),
]


class FlashLogger:
    """메모리만 기록 (바탕화면 txt 저장 안 함)."""

    def __init__(self):
        self.lines = []

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.lines.append(f"[{ts}] {msg}")

    def section(self, title):
        self.log("=" * 60)
        self.log(title)
        self.log("=" * 60)

    def dump_ports(self, tag="PORTS"):
        self.log(f"--- {tag} ---")
        if list_ports is None:
            self.log("list_ports 없음")
            return
        ports = list(list_ports.comports())
        if not ports:
            self.log("(COM 0개)")
            return
        for p in ports:
            self.log(
                f"  {p.device} [{_port_mode(p)}] desc={p.description!r} hwid={p.hwid!r}"
            )

    def save(self, ok, summary):
        return ""

def _port_mode(p):
    hu = (p.hwid or "").upper()
    if LEONARDO_VID in hu and LEONARDO_BOOT_PID in hu:
        return "BOOTLOADER"
    if LEONARDO_VID in hu and LEONARDO_SKETCH_PID in hu:
        return "SKETCH"
    return "OTHER"


def _is_bootloader_port(p):
    return _port_mode(p) == "BOOTLOADER"


def _is_leonardo_any(p):
    return LEONARDO_VID in (p.hwid or "").upper()


def _ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _gh_url(remote):
    parts = remote.split("/")
    return GH_RAW + "/" + "/".join(
        quote(p, safe="") if any(ord(c) > 127 for c in p) else p for p in parts
    )


def _download(remote, dest, flog=None, callback=None, label=None):
    if callback:
        callback(5, f"다운로드: {label or os.path.basename(dest)}")
    url = _gh_url(remote)
    flog and flog.log(f"GET {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "ddong", "Cache-Control": "no-cache"})
    data = urllib.request.urlopen(req, timeout=60, context=_ssl_ctx()).read()
    if len(data) < 1000:
        raise RuntimeError(f"너무 작음: {len(data)}")
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    with open(dest, "wb") as f:
        f.write(data)
    flog and flog.log(f"저장 {dest} size={len(data)}")
    return len(data)


def ensure_firmware(flog=None, callback=None):
    """avrdude는 캐시 OK. hex는 매번 GitHub에서 강제 갱신(옛 20312 고착 방지)."""
    root = TMP_ROOT
    os.makedirs(os.path.join(root, "avrdude"), exist_ok=True)

    # 로컬 개발폴더에 avrdude 있으면 복사(네트워크 절약)
    for cand in (
        os.path.join(HERE, "firmware"),
        os.path.join(DESKTOP, "뚱힐러_github", "firmware"),
    ):
        if os.path.isfile(os.path.join(cand, "avrdude", "avrdude.exe")):
            for name in ("avrdude.exe", "avrdude.conf", "libusb0.dll"):
                src = os.path.join(cand, "avrdude", name)
                dst = os.path.join(root, "avrdude", name)
                if os.path.isfile(src) and (
                    not os.path.isfile(dst) or os.path.getsize(dst) < 1000
                ):
                    try:
                        import shutil
                        shutil.copy2(src, dst)
                    except Exception:
                        pass
            break

    for remote, local in NEEDED_TOOLS:
        dest = os.path.join(root, local)
        if os.path.isfile(dest) and os.path.getsize(dest) > 1000:
            continue
        try:
            _download(remote, dest, flog=flog, callback=callback)
        except Exception as e:
            flog and flog.log(f"도구 다운로드 실패: {e}")
            return None

    # ★ hex는 항상 다시 받음
    hex_dest = os.path.join(root, HEX_NAME)
    old = os.path.getsize(hex_dest) if os.path.isfile(hex_dest) else 0
    try:
        new_sz = _download(
            f"firmware/{HEX_NAME}", hex_dest, flog=flog, callback=callback, label=HEX_NAME
        )
        flog and flog.log(f"hex 강제갱신: {old} → {new_sz}")
    except Exception as e:
        flog and flog.log(f"hex 다운로드 실패: {e}")
        # 로컬 폴백
        for cand in (
            os.path.join(HERE, "firmware", HEX_NAME),
            os.path.join(DESKTOP, "뚱힐러_github", "firmware", HEX_NAME),
        ):
            if os.path.isfile(cand) and os.path.getsize(cand) > 1000:
                import shutil
                shutil.copy2(cand, hex_dest)
                flog and flog.log(f"hex 로컬폴백: {cand} size={os.path.getsize(hex_dest)}")
                break
        else:
            return None

    flog and flog.log(f"펌웨어 폴더: {root}")
    return root


def find_arduino(preferred=None):
    if list_ports is None:
        return None
    ports_now = {p.device for p in list_ports.comports()}
    if preferred and preferred in ports_now:
        return preferred
    for p in list_ports.comports():
        if _is_leonardo_any(p) or _is_bootloader_port(p):
            return p.device
    for p in list_ports.comports():
        d = f"{p.description or ''} {p.manufacturer or ''}".upper()
        if any(k in d for k in ("CH340", "ARDUINO", "LEONARDO", "USB", "SERIAL", "CP210")) or "직렬" in (p.description or ""):
            return p.device
    return None


def find_bootloader_port():
    if list_ports is None:
        return None
    for p in list_ports.comports():
        if _is_bootloader_port(p):
            return p.device
    return None


def _kill_stray_avrdude(flog=None):
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", "avrdude.exe"],
            capture_output=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
        )
    except Exception:
        pass


def wait_bootloader(timeout=8.0, callback=None, flog=None, hint="부트로더 대기"):
    t0 = time.time()
    last = -1
    while time.time() - t0 < timeout:
        sec = int(time.time() - t0)
        boot = find_bootloader_port()
        if sec != last:
            last = sec
            flog and flog.dump_ports(f"{hint} {sec}s boot={boot}")
            if callback:
                callback(30, f"{hint} {sec}s")
        if boot:
            time.sleep(0.35)
            return boot
        time.sleep(0.12)
    return None


def _enter_bootloader_serial_cmd(port, flog=None):
    s = serial.Serial()
    s.port = port
    s.baudrate = 9600
    s.timeout = 0.2
    s.write_timeout = 1.0
    s.dsrdtr = False
    s.rtscts = False
    s.open()
    try:
        try:
            s.reset_input_buffer()
        except Exception:
            pass
        time.sleep(0.2)
        # 여러 번 — 한 바이트 유실 대비
        for _ in range(3):
            s.write(b"!")
            try:
                s.flush()
            except Exception:
                pass
            time.sleep(0.05)
    finally:
        try:
            s.close()
        except Exception:
            pass
    flog and flog.log("touch: serial '!' OK")


def _touch_1200_simple(port, flog=None):
    """처음 성공하던 짧은 1200 open/close."""
    try:
        s = serial.Serial(port, 1200)
        try:
            s.dtr = False
        except Exception:
            pass
        time.sleep(0.1)
        s.close()
    except Exception:
        s = serial.Serial()
        s.port = port
        s.baudrate = 1200
        s.dtr = False
        s.open()
        time.sleep(0.1)
        s.close()
    flog and flog.log("touch: simple 1200 OK")


def _run_avrdude(root, hex_path, boot_port, callback=None, flog=None):
    avrdude = os.path.join(root, "avrdude", "avrdude.exe")
    conf = os.path.join(root, "avrdude", "avrdude.conf")
    cmd = [
        avrdude, "-C", conf,
        "-c", "avr109", "-p", "atmega32u4",
        "-P", boot_port, "-b", "57600", "-D",
        "-U", f"flash:w:{hex_path}:i",
    ]
    flog and flog.log("CMD: " + " ".join(cmd))
    if callback:
        callback(55, f"avrdude ({boot_port})")
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
    )
    lines = []
    t0 = time.time()
    while True:
        if time.time() - t0 > 30:
            try:
                proc.kill()
            except Exception:
                pass
            return False, "avrdude 30초 타임아웃"
        line = proc.stdout.readline() if proc.stdout else ""
        if line:
            line = line.rstrip()
            lines.append(line)
            flog and flog.log(f"  [avrdude] {line}")
            if callback and "writing" in line.lower():
                callback(75, line[:70])
        elif proc.poll() is not None:
            break
        else:
            time.sleep(0.05)
    return proc.returncode == 0, (lines[-1] if lines else f"code {proc.returncode}")


def ensure_arduino_cli(flog=None, callback=None):
    exe = os.path.join(CLI_DIR, "arduino-cli.exe")
    if os.path.isfile(exe):
        return exe
    os.makedirs(CLI_DIR, exist_ok=True)
    zip_path = os.path.join(TMP_ROOT, "arduino-cli.zip")
    if callback:
        callback(12, "arduino-cli 다운로드...")
    try:
        req = urllib.request.Request(CLI_ZIP_URL, headers={"User-Agent": "ddong"})
        with urllib.request.urlopen(req, timeout=180, context=_ssl_ctx()) as r:
            data = r.read()
        with open(zip_path, "wb") as f:
            f.write(data)
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(CLI_DIR)
        if not os.path.isfile(exe):
            for root, _, files in os.walk(CLI_DIR):
                if "arduino-cli.exe" in files:
                    import shutil
                    shutil.copy2(os.path.join(root, "arduino-cli.exe"), exe)
                    break
        return exe if os.path.isfile(exe) else None
    except Exception as e:
        flog and flog.log(f"arduino-cli 설치 실패: {e!r}")
        return None


def flash_via_arduino_cli(hex_path, port, flog=None, callback=None):
    cli = ensure_arduino_cli(flog=flog, callback=callback)
    if not cli:
        return False, "arduino-cli 없음"
    try:
        subprocess.run(
            [cli, "core", "install", "arduino:avr"],
            capture_output=True,
            timeout=300,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
        )
    except Exception:
        pass
    cmd = [cli, "upload", "-p", port, "--fqbn", FQBN, "--input-file", hex_path, "-v"]
    flog and flog.log("CMD: " + " ".join(cmd))
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
        )
    except Exception as e:
        return False, str(e)
    lines = []
    t0 = time.time()
    while True:
        if time.time() - t0 > 90:
            try:
                proc.kill()
            except Exception:
                pass
            return False, "cli 타임아웃"
        line = proc.stdout.readline() if proc.stdout else ""
        if line:
            line = line.rstrip()
            lines.append(line)
            flog and flog.log(f"  [cli] {line}")
        elif proc.poll() is not None:
            break
        else:
            time.sleep(0.05)
    return proc.returncode == 0, (lines[-1] if lines else f"code {proc.returncode}")


def flash(callback=None, port=None, ask_manual_reset=None):
    """return (ok, msg, log_path)."""
    flog = FlashLogger()
    flog.section("펌업 시작 (최신hex강제 + 1200빠른업로드)")
    flog.log(f"python={sys.version}")
    flog.log(f"preferred={port!r}")
    flog.dump_ports("시작")

    try:
        if serial is None:
            msg = "pyserial 없음"
            return False, msg, flog.save(False, msg)

        _kill_stray_avrdude(flog)
        root = ensure_firmware(flog=flog, callback=callback)
        if not root:
            msg = "펌웨어 확보 실패"
            return False, msg, flog.save(False, msg)
        hex_path = os.path.join(root, HEX_NAME)
        hex_sz = os.path.getsize(hex_path)
        flog.log(f"hex={hex_path} size={hex_sz}")
        if hex_sz < 20500:
            flog.log(f"경고: hex가 너무 작음({hex_sz}) — 옛 펌일 수 있음")

        com = find_arduino(preferred=port)
        if not com:
            msg = "아두이노 COM 없음"
            return False, msg, flog.save(False, msg)
        if callback:
            callback(10, f"장치: {com}")
        time.sleep(1.2)

        # 이미 부트로더면 바로
        boot = find_bootloader_port()
        if boot:
            ok, detail = _run_avrdude(root, hex_path, boot, callback=callback, flog=flog)
            if ok:
                if callback:
                    callback(100, "업로드 완료!")
                return True, f"완료(이미부트로더/{boot})", flog.save(True, f"완료/{boot}")

        # 1) '!' → 부트로더 대기
        flog.section("시도: 시리얼 '!'")
        try:
            _enter_bootloader_serial_cmd(com, flog=flog)
        except Exception as e:
            flog.log(f"'!' 예외: {e!r}")
        boot = wait_bootloader(timeout=5.0, callback=callback, flog=flog, hint="!후")
        if boot:
            ok, detail = _run_avrdude(root, hex_path, boot, callback=callback, flog=flog)
            if ok:
                if callback:
                    callback(100, "업로드 완료!")
                return True, f"완료(!/{boot})", flog.save(True, f"완료(!/{boot})")
            flog.log(f"avrdude 실패: {detail}")

        # 2) 처음 성공 방식: 1200 짧게 → 0.5초 → 같은COM 또는 부트로더COM
        flog.section("시도: 1200 빠른업로드 (처음 성공방식)")
        com = find_arduino(preferred=port) or com
        try:
            _touch_1200_simple(com, flog=flog)
        except Exception as e:
            flog.log(f"1200 예외: {e!r}")
        time.sleep(0.5)
        boot = find_bootloader_port() or com
        flog.dump_ports(f"1200후 boot={find_bootloader_port()}")
        ok, detail = _run_avrdude(root, hex_path, boot, callback=callback, flog=flog)
        if ok:
            if callback:
                callback(100, "업로드 완료!")
            return True, f"완료(1200/{boot})", flog.save(True, f"완료(1200/{boot})")
        flog.log(f"1200 avrdude 실패: {detail}")

        # 3) cli
        flog.section("시도: arduino-cli")
        com2 = find_arduino(preferred=port) or com
        ok2, detail2 = flash_via_arduino_cli(hex_path, com2, flog=flog, callback=callback)
        if ok2:
            if callback:
                callback(100, "업로드 완료!(cli)")
            return True, "완료(cli)", flog.save(True, "완료(cli)")
        flog.log(f"cli 실패: {detail2}")

        # 4) 수동 1회 (옛 시스템WDT → WDT3)
        if callable(ask_manual_reset):
            flog.section("최후: 수동 더블리셋 (옛WDT→WDT3 1회)")
            if callback:
                callback(25, "수동 안내")
            try:
                go = bool(ask_manual_reset())
            except Exception:
                go = False
            if go:
                boot = wait_bootloader(timeout=15.0, callback=callback, flog=flog, hint="수동")
                if boot:
                    ok3, detail3 = _run_avrdude(root, hex_path, boot, callback=callback, flog=flog)
                    if ok3:
                        if callback:
                            callback(100, "업로드 완료!")
                        return True, f"완료(수동/{boot})", flog.save(True, f"완료(수동/{boot})")
                    flog.log(f"수동 avrdude 실패: {detail3}")

        msg = (
            "자동 펌업 실패.\n"
            "· 이번 hex는 최신으로 받았습니다. 리셋버튼 있으면 더블리셋 1회로 WDT3 올리세요.\n"
            "· WDT3 이후엔 처음처럼 1200 자동펌업이 다시 됩니다.\n"
            f"· cli: {detail2}"
        )
        return False, msg, flog.save(False, msg.replace("\n", " / "))
    except Exception as e:
        flog.log(traceback.format_exc())
        return False, str(e), flog.save(False, str(e))


if __name__ == "__main__":
    ok, msg, path = flash(lambda p, m: print(f"{p}% {m}"))
    print(("OK" if ok else "FAIL"), msg)
    print("LOG", path)
    sys.exit(0 if ok else 1)
