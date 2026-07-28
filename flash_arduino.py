# -*- coding: utf-8 -*-
"""아두이노(Leonardo) 펌웨어 업로드 + 진단 로그.

로그 근거(2341:8036 유지 = 스케치 모드):
  1200bps 자동리셋이 안 먹으면 부트로더(2341:0036)로 절대 안 들어감.
  → 수동 더블리셋 대기 후 avr109 업로드가 정석.
"""
from __future__ import annotations

import os
import ssl
import sys
import time
import traceback
import tempfile
import threading
import subprocess
import urllib.request
from datetime import datetime

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
FLASH_LOG = os.path.join(DESKTOP, "뚱힐러_펌업로그.txt")
# Leonardo: 스케치 8036 / 부트로더 0036
LEONARDO_SKETCH_PID = "8036"
LEONARDO_BOOT_PID = "0036"
LEONARDO_VID = "2341"
NEEDED = [
    ("firmware/뚱힐러.hex", HEX_NAME),
    ("firmware/avrdude/avrdude.exe", os.path.join("avrdude", "avrdude.exe")),
    ("firmware/avrdude/avrdude.conf", os.path.join("avrdude", "avrdude.conf")),
    ("firmware/avrdude/libusb0.dll", os.path.join("avrdude", "libusb0.dll")),
]

LAST_FLASH_LOG = ""


class FlashLogger:
    def __init__(self):
        self.lines = []
        self.path = FLASH_LOG
        self.started = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        line = f"[{ts}] {msg}"
        self.lines.append(line)

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
            mode = _port_mode(p)
            self.log(
                f"  {p.device} [{mode}] desc={p.description!r} "
                f"mfg={p.manufacturer!r} hwid={p.hwid!r}"
            )

    def save(self, ok, summary):
        global LAST_FLASH_LOG
        body = "\n".join(self.lines)
        text = (
            f"뚱힐러 펌업 로그\n"
            f"시작: {self.started}\n"
            f"결과: {'성공' if ok else '실패'} — {summary}\n"
            f"{'=' * 60}\n"
            f"{body}\n"
            f"{'=' * 60}\n"
            f"끝: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        try:
            os.makedirs(DESKTOP, exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                f.write(text)
            if not ok:
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                bak = os.path.join(DESKTOP, f"뚱힐러_펌업로그_{stamp}.txt")
                with open(bak, "w", encoding="utf-8") as f:
                    f.write(text)
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write(f"백업: {bak}\n")
            LAST_FLASH_LOG = self.path
        except Exception as e:
            LAST_FLASH_LOG = ""
            self.log(f"로그 저장 실패: {e}")
        return self.path


def _port_mode(p):
    h = (p.hwid or "").upper().replace(":", "")
    # USB VID:PID=2341:8036 → 23418036 after removing colons in "VID:PID=2341:8036"
    hu = (p.hwid or "").upper()
    if LEONARDO_VID in hu and LEONARDO_BOOT_PID in hu:
        return "BOOTLOADER"
    if LEONARDO_VID in hu and LEONARDO_SKETCH_PID in hu:
        return "SKETCH"
    return "OTHER"


def _is_bootloader_port(p):
    return _port_mode(p) == "BOOTLOADER"


def _is_leonardo_any(p):
    hu = (p.hwid or "").upper()
    return LEONARDO_VID in hu


def _ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def firmware_candidates():
    return [
        os.path.join(HERE, "firmware"),
        os.path.join(DESKTOP, "뚱힐러_github", "firmware"),
        os.path.join(tempfile.gettempdir(), "ddong_firmware"),
    ]


def _has_tools(root):
    return (
        os.path.isfile(os.path.join(root, HEX_NAME))
        and os.path.isfile(os.path.join(root, "avrdude", "avrdude.exe"))
        and os.path.isfile(os.path.join(root, "avrdude", "avrdude.conf"))
    )


def ensure_firmware(flog=None, callback=None):
    for root in firmware_candidates():
        if _has_tools(root):
            flog and flog.log(f"펌웨어 폴더: {root}")
            return root
    root = os.path.join(tempfile.gettempdir(), "ddong_firmware")
    os.makedirs(os.path.join(root, "avrdude"), exist_ok=True)
    flog and flog.log(f"TEMP 다운로드: {root}")
    ctx = _ssl_ctx()
    for remote, local in NEEDED:
        dest = os.path.join(root, local)
        if os.path.isfile(dest) and os.path.getsize(dest) > 1000:
            continue
        if callback:
            callback(5, f"다운로드: {os.path.basename(local)}")
        from urllib.parse import quote
        parts = remote.split("/")
        url = GH_RAW + "/" + "/".join(
            quote(p, safe="") if any(ord(c) > 127 for c in p) else p for p in parts
        )
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ddong"})
            data = urllib.request.urlopen(req, timeout=60, context=ctx).read()
            if len(data) < 1000:
                return None
            with open(dest, "wb") as f:
                f.write(data)
        except Exception as e:
            flog and flog.log(f"다운로드 실패: {e}")
            return None
    return root if _has_tools(root) else None


def find_arduino_ports():
    if list_ports is None:
        return []
    found = []
    for p in list_ports.comports():
        if _is_leonardo_any(p) or _is_bootloader_port(p):
            if p.device not in found:
                found.append(p.device)
            continue
        d = f"{p.description or ''} {p.manufacturer or ''}"
        du = d.upper()
        if any(k in du for k in ("CH340", "ARDUINO", "LEONARDO", "USB", "SERIAL", "CP210")) or "직렬" in d:
            if p.device not in found:
                found.append(p.device)
    return found


def find_arduino(preferred=None):
    ports_now = {p.device for p in list_ports.comports()} if list_ports else set()
    if preferred and preferred in ports_now:
        return preferred
    ports = find_arduino_ports()
    return ports[0] if ports else None


def find_bootloader_port():
    """부트로더 모드(PID 0036) COM 찾기."""
    if list_ports is None:
        return None
    for p in list_ports.comports():
        if _is_bootloader_port(p):
            return p.device
    return None


def _ports_snapshot():
    if list_ports is None:
        return []
    out = []
    for p in list_ports.comports():
        out.append({
            "device": p.device,
            "hwid": p.hwid or "",
            "desc": p.description or "",
            "mode": _port_mode(p),
        })
    return out


def _kill_stray_avrdude(flog=None):
    try:
        r = subprocess.run(
            ["taskkill", "/F", "/IM", "avrdude.exe"],
            capture_output=True,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
        )
        flog and flog.log(f"taskkill avrdude rc={r.returncode}")
    except Exception as e:
        flog and flog.log(f"taskkill: {e}")


def trigger_1200_touch(port, flog=None):
    """시도는 하되, 성공 여부는 PID가 BOOTLOADER로 바뀌는지로만 판단."""
    if serial is None or not port:
        return False
    try:
        flog and flog.log(f"1200bps touch: {port}")
        s = serial.Serial()
        s.port = port
        s.baudrate = 1200
        s.timeout = 0.1
        try:
            s.setDTR(False)
        except Exception:
            pass
        s.open()
        time.sleep(0.05)
        s.close()
        flog and flog.log("1200bps touch close OK")
        return True
    except Exception as e:
        flog and flog.log(f"1200bps touch 실패: {e!r}")
        return False


def wait_bootloader(timeout=10.0, callback=None, flog=None, hint=""):
    """PID 0036(BOOTLOADER) 포트가 나타날 때까지 대기."""
    t0 = time.time()
    last = -1
    while time.time() - t0 < timeout:
        sec = int(time.time() - t0)
        boot = find_bootloader_port()
        snap = _ports_snapshot()
        if sec != last:
            last = sec
            flog and flog.log(f"부트로더대기 {sec}s boot={boot} ports={snap}")
            if callback:
                msg = f"부트로더 대기 {sec}s"
                if hint:
                    msg = f"{hint} ({sec}s)"
                callback(30, msg)
        if boot:
            time.sleep(0.3)
            flog and flog.log(f"부트로더 포트 확정: {boot}")
            return boot
        time.sleep(0.12)
    flog and flog.log("부트로더(PID 0036) 미검출")
    return None


def _run_avrdude(root, hex_path, boot_port, callback=None, flog=None, timeout_sec=25):
    avrdude = os.path.join(root, "avrdude", "avrdude.exe")
    conf = os.path.join(root, "avrdude", "avrdude.conf")
    cmd = [
        avrdude, "-C", conf,
        "-c", "avr109",
        "-p", "atmega32u4",
        "-P", boot_port,
        "-b", "57600",
        "-D",
        "-U", f"flash:w:{hex_path}:i",
    ]
    flog and flog.log("CMD: " + " ".join(cmd))
    if callback:
        callback(50, f"avrdude 업로드 ({boot_port})...")

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
        )
    except Exception as e:
        return False, str(e)

    out_lines = []
    t0 = time.time()
    done = {"v": False}

    def _reader():
        try:
            for line in proc.stdout or []:
                line = (line or "").rstrip("\r\n")
                if not line.strip():
                    continue
                out_lines.append(line)
                flog and flog.log(f"  [avrdude] {line}")
                low = line.lower()
                if callback:
                    if "writing" in low:
                        callback(70, line[:70])
                    elif "verifying" in low:
                        callback(90, "검증 중...")
        finally:
            done["v"] = True

    th = threading.Thread(target=_reader, daemon=True)
    th.start()
    while True:
        if time.time() - t0 > timeout_sec:
            try:
                proc.kill()
            except Exception:
                pass
            th.join(timeout=2)
            return False, f"{timeout_sec}초 타임아웃"
        if proc.poll() is not None:
            th.join(timeout=3)
            break
        time.sleep(0.1)
    try:
        proc.wait(timeout=3)
    except Exception:
        pass
    ok = proc.returncode == 0
    detail = out_lines[-1] if out_lines else f"code {proc.returncode}"
    flog and flog.log(f"avrdude rc={proc.returncode} detail={detail!r}")
    return ok, detail


def flash(callback=None, port=None, ask_manual_reset=None):
    """업로드. ask_manual_reset: UI에서 더블리셋 안내 후 True/False 반환하는 callable.
    return (ok, msg, log_path)
    """
    flog = FlashLogger()
    flog.section("펌업 진단 시작")
    flog.log(f"python={sys.version}")
    flog.log(f"cwd={os.getcwd()}")
    flog.log(f"HERE={HERE}")
    flog.log(f"preferred_port={port!r}")
    flog.log("참고: Leonardo 스케치=2341:8036 / 부트로더=2341:0036")
    flog.dump_ports("시작")

    try:
        if serial is None or list_ports is None:
            msg = "pyserial 없음"
            return False, msg, flog.save(False, msg)

        _kill_stray_avrdude(flog)
        root = ensure_firmware(flog=flog, callback=callback)
        if not root:
            msg = "펌웨어 확보 실패"
            return False, msg, flog.save(False, msg)

        hex_path = os.path.join(root, HEX_NAME)
        flog.log(f"hex={hex_path} size={os.path.getsize(hex_path)}")

        com = find_arduino(preferred=port)
        flog.log(f"스케치 COM={com!r}")
        if not com:
            msg = "아두이노 COM 없음"
            return False, msg, flog.save(False, msg)

        if callback:
            callback(10, f"장치: {com}")

        # --- 1) 자동 1200bps 시도 (짧게) ---
        flog.section("자동 1200bps 리셋 시도")
        time.sleep(1.0)
        trigger_1200_touch(com, flog)
        boot = wait_bootloader(timeout=3.0, callback=callback, flog=flog, hint="자동리셋 확인")
        flog.dump_ports("1200 이후")

        # --- 2) 실패 시 수동 더블리셋 ---
        if not boot:
            flog.log("자동리셋 실패(PID가 8036에 머무름) → 수동 더블리셋 필요")
            if callback:
                callback(20, "수동 리셋 필요")
            go = True
            if callable(ask_manual_reset):
                try:
                    go = bool(ask_manual_reset())
                except Exception as e:
                    flog.log(f"ask_manual_reset 예외: {e}")
                    go = True
            if not go:
                msg = "사용자가 수동 리셋 취소"
                return False, msg, flog.save(False, msg)

            flog.section("수동 더블리셋 대기 (최대 15초)")
            if callback:
                callback(25, "리셋 2번 누른 뒤 대기중...")
            # 안내 직후 바로 대기 — 사용자가 이미 눌렀거나 곧 누름
            boot = wait_bootloader(
                timeout=15.0,
                callback=callback,
                flog=flog,
                hint="리셋버튼 2번 후 대기",
            )
            flog.dump_ports("수동리셋 이후")

        if not boot:
            msg = (
                "부트로더 진입 실패 (PID 0036 안 보임).\n"
                "보드 리셋 버튼을 빠르게 두 번 누르고 바로 다시 [펌업] 하세요.\n"
                f"로그: {FLASH_LOG}"
            )
            return False, msg, flog.save(False, msg)

        # --- 3) 부트로더 포트에만 업로드 ---
        flog.section(f"avrdude 업로드 port={boot}")
        if callback:
            callback(40, f"부트로더 확인: {boot}")
        ok, detail = _run_avrdude(root, hex_path, boot, callback=callback, flog=flog)
        if ok:
            if callback:
                callback(100, "업로드 완료!")
            return True, f"완료 ({boot})", flog.save(True, f"완료 ({boot})")

        msg = f"avrdude 실패: {detail}\n로그: {FLASH_LOG}"
        return False, msg, flog.save(False, msg)
    except Exception as e:
        flog.log(traceback.format_exc())
        return False, str(e), flog.save(False, str(e))


if __name__ == "__main__":
    def _ask():
        print("보드 리셋 버튼을 빠르게 2번 누르세요. 엔터...")
        input()
        return True

    ok, msg, path = flash(lambda p, m: print(f"{p}% {m}"), ask_manual_reset=_ask)
    print(("OK" if ok else "FAIL"), msg)
    print("LOG", path)
    sys.exit(0 if ok else 1)
