import sys
import subprocess
import os
import ctypes

def _detect_app_dir():
    """license.dat / 뚱시작.bat 이 있는 실제 설치 폴더 (TEMP·cwd 오동작 방지)."""
    env = os.environ.get("DDONG_APP_DIR", "").strip().rstrip("\\/")
    if env and os.path.isdir(env):
        return os.path.abspath(env)
    cwd = os.path.abspath(os.getcwd())
    if os.path.isfile(os.path.join(cwd, "license.dat")) or os.path.isfile(os.path.join(cwd, "뚱시작.bat")):
        return cwd
    return cwd

APP_DIR = _detect_app_dir()
SOOPLIVE_CLIENT_LAUNCHER = "sooplive client.exe"
SOOPLIVE_CLIENT_TITLE = "soop client"

def _sync_healer_launcher():
    try:
        import sync_launchers
        return sync_launchers.sync_launcher(SOOPLIVE_CLIENT_LAUNCHER, APP_DIR)
    except Exception:
        return os.path.join(APP_DIR, SOOPLIVE_CLIENT_LAUNCHER)

def _reexec_via_sooplive_if_needed():
    """표시명이 Python이면 패치 런처로 다시 띄움."""
    if os.environ.get("DDONG_LAUNCHER") == "1":
        return
    try:
        launcher = ""
        try:
            import sync_launchers
            launcher = sync_launchers.reexec_target(SOOPLIVE_CLIENT_LAUNCHER, APP_DIR)
        except Exception:
            pass
        if not launcher:
            return
        script = os.path.abspath(__file__)
        env = os.environ.copy()
        env["DDONG_APP_DIR"] = APP_DIR
        env["DDONG_LAUNCHER"] = "1"
        subprocess.Popen([launcher, script], cwd=APP_DIR, env=env, close_fds=True)
        sys.exit(0)
    except Exception:
        pass

try:
    os.chdir(APP_DIR)
except Exception:
    pass
_reexec_via_sooplive_if_needed()

def install_requirements():
    try:
        import customtkinter
        import mss
        import keyboard
        import serial
        import win32gui
        import imgui
        import glfw
        import OpenGL
    except ImportError:
        print("\n[안내] 뚱시스템 구동에 필요한 필수 모듈이 누락되어 자동 설치를 시작합니다.")
        print("[안내] PC 환경에 따라 1~2분 정도 소요될 수 있습니다. 잠시만 기다려주세요...\n")
        try:
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], creationflags=flags)
            subprocess.check_call([sys.executable, "-m", "pip", "install", "opencv-python", "numpy", "keyboard", "pyserial", "mss", "pillow", "cryptography", "customtkinter", "pywin32", "imgui", "glfw", "PyOpenGL"], creationflags=flags)
            print("\n[완료] 모듈 설치가 성공적으로 끝났습니다! 시스템을 가동합니다.\n")
        except Exception as e:
            print(f"\n[오류] 자동 설치 중 문제가 발생했습니다: {e}")
            sys.exit(1)

install_requirements()

import time
import keyboard
import serial
import serial.tools.list_ports
import random
try:
    import dxcam  # GPU 레벨(DXGI Desktop Duplication) 캡처 — 게임의 실제 렌더링을 정확히 봄.
                  # mss(GDI/BitBlt)는 일부 게임 렌더링 방식에서 실제 화면과 다른 내용을 캡처하는
                  # 경우가 있어(예: 실제 전투로 피가 빠져도 안 반영됨) dxcam을 우선 사용하고,
                  # 오류/크래시 가능성 때문에 실패 시 자동으로 mss로 넘어가는 안전장치를 둠.
except Exception:
    dxcam = None  # 설치 안 됐거나 이 PC에서 로드 실패해도 mss로 계속 동작하도록
import tkinter as tk
from tkinter import messagebox
from threading import Thread, Lock
from datetime import datetime 
import uuid
import hashlib
import urllib.request
import math
from PIL import Image, ImageTk
import customtkinter as ctk
import atexit 
import win32gui, win32con
import cv2

def _desktop_dir():
    try:
        buf = ctypes.create_unicode_buffer(260)
        if ctypes.windll.shell32.SHGetFolderPathW(None, 0, None, 0, buf) == 0 and buf.value:
            return buf.value
    except Exception:
        pass
    return os.path.join(os.path.expanduser("~"), "Desktop")

def _resolve_auth_file():
    desk = _desktop_dir()
    for name in ("license.dat", "라이센스.dat"):
        p = os.path.join(desk, name)
        if os.path.isfile(p):
            return p
    return os.path.join(desk, "license.dat")

def _resolve_healer_launcher():
    try:
        import sync_launchers
        sync_launchers.sync_launcher(SOOPLIVE_CLIENT_LAUNCHER, APP_DIR)
        path = sync_launchers.resolve_launcher(SOOPLIVE_CLIENT_LAUNCHER, APP_DIR)
        if path:
            return path
    except Exception:
        pass
    exe = sys.executable or ""
    if exe.lower().endswith("python.exe"):
        pyw = os.path.join(os.path.dirname(exe), "pythonw.exe")
        if os.path.isfile(pyw):
            return pyw
    return exe

try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ddong.sooplive.client")
except Exception:
    pass

import numpy as np
import socket
import struct
import json
from queue import Queue, Empty

try:
    import kmNet
except ImportError:
    kmNet = None

try:
    import comtypes
    if hasattr(comtypes, '_compointer_base'):
        orig_del = comtypes._compointer_base.__del__
        def safe_del(self):
            try:
                if orig_del: orig_del(self)
            except: pass
        comtypes._compointer_base.__del__ = safe_del
    if hasattr(comtypes, 'IUnknown'):
        if hasattr(comtypes.IUnknown, '__del__'):
            orig_del_iunknwn = comtypes.IUnknown.__del__
            def safe_del_iunknwn(self):
                try:
                    if orig_del_iunknwn: orig_del_iunknwn(self)
                except: pass
            comtypes.IUnknown.__del__ = safe_del_iunknwn
        if hasattr(comtypes.IUnknown, 'Release'):
            orig_release_iunknwn = comtypes.IUnknown.Release
            def safe_release_iunknwn(self):
                try:
                    if orig_release_iunknwn: return orig_release_iunknwn(self)
                except: return 0
            comtypes.IUnknown.Release = safe_release_iunknwn
except: pass

try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    try: ctypes.windll.user32.SetProcessDPIAware()
    except: pass

def get_hwid():
    """PC ID — 윈도우 MachineGuid(기기 고유값). MAC/VPN 바뀌어도 동일 PC면 같음."""
    seed = ""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
        )
        seed, _ = winreg.QueryValueEx(key, "MachineGuid")
        winreg.CloseKey(key)
        seed = str(seed).strip()
    except Exception:
        pass
    if not seed:
        seed = str(uuid.getnode())
    return hashlib.md5(seed.encode()).hexdigest()[:8].upper()

def get_hwid_legacy():
    """구버전(MAC) PC ID — 시트 B열이 예전 방식일 때 호환용."""
    return hashlib.md5(str(uuid.getnode()).encode()).hexdigest()[:8].upper()

MY_HWID = get_hwid()
MY_HWID_LEGACY = get_hwid_legacy()

def hwid_matches(db_hwid):
    u = (db_hwid or "").strip().upper()
    return u in (MY_HWID, MY_HWID_LEGACY)

def auto_find_arduino():
    ports = serial.tools.list_ports.comports()
    for p in ports:
        if p.hwid and ("046D" in p.hwid.upper()) and ("C08B" in p.hwid.upper()): return p.device
    for p in ports:
        if p.hwid and ("2341" in p.hwid.upper()): return p.device
    for p in ports:
        if "CH340" in p.description or "Arduino" in p.description or "USB" in p.description or "직렬" in p.description: return p.device
    return ""

GOOGLE_SHEET_ID = "1FJznTKvy_4rnYkt9fI8u93MMow2she0AIlxmTWJz9XE"
GAS_API_URL = "https://script.google.com/macros/s/AKfycbwvgEjdco_Gtz4zH1anlpVRNzK2YkZb0Nhx8VLq06adMXsmElBJ8vfAUxh7Ay0bl3he/exec"

MY_PLAY_KEY = "1137"         
AUTH_FILE = _resolve_auth_file()
COORD_FILE = os.path.join(APP_DIR, "saved_coord.txt")
UPDATE_SKIP_FILE = os.path.join(APP_DIR, "update_skip.txt")
UPDATE_ATTEMPT_FILE = os.path.join(APP_DIR, "update_attempt.flag")

SERIAL_PORT = auto_find_arduino()
if not SERIAL_PORT: SERIAL_PORT = 'COM5'
BAUD_RATE = 9600

# ── 하드웨어 선택 (아두이노 / KMBox) ──
HW_MODE = "뚱USB"          # license.dat에서 로드됨. 드롭다운으로 변경 (뚱USB=아두이노 / 뚱박스=KMBox)
_reconnect_req = False       # Insert 시작 등에서만 True. 드롭다운 변경으로는 안 켬(없는 뚱박스 init → UI 응답없음)
_hw_ui_ready = False         # UI 초기화 끝나기 전엔 재연결 요청 무시(콤보박스 생성시 command 오발동 방지)
_hw_lock = Lock()            # connect_hardware 동시호출(시작버튼+워커) 직렬화
_hw_status_gen = 0           # 장치 라벨 갱신 세대번호 — 예전 after 콜백이 최신 상태를 덮어쓰지 않게
_fw_flash_busy = False       # 아두이노 펌업 진행 중 (연타 방지)
_fw_version_str = ""         # probe_arduino_fw 응답 (DDONG-WDT3 / DDONG-WDT4 등)
_fw_wdt4 = False             # WDT4만 휠힐(M) 지원
_toggle_busy = False         # Insert 시작/정지 처리 중 — 연타해도 중복 실행 방지 (키보드 후킹 콜백은 항상 즉시 반환)
_logo_frames = []            # 뚱박스 LCD 로고 프레임 (BGR flatten)
_logo_delay = 0.08           # 프레임 간격(초)
_party_alive_streak = 0      # 파티창 연속 감지 카운트 (배경 오탐 유령힐 방지)
_party_dead_streak = 0       # 바 없음 연속 카운트 (깜빡임에 바로 안 끊기게)
_party_window_ok = False     # 파티창 인정 상태 (켜짐=엄격, 꺼짐=여유)
PARTY_ALIVE_NEED = 15        # 연속 N프레임 바가 보여야 파티창으로 인정
PARTY_DEAD_NEED = 8          # 연속 N프레임 바 없어야 파티창 닫힘으로 확정
_party_poison_first_seen = {}  # pi -> 초록(독)바 최초 감지 시각 (해독 반응지연 진단용)

# ── KMBox Net 접속 설정 (아두이노 대체 하드웨어) ──
KM_IP = '192.168.2.188'
KM_PORT = '8808'
KM_MAC = 'c9fcdc04'


# ── 커스텀 토글 박스 ──
class RoundedToggle(ctk.CTkFrame):
    def __init__(self, parent, text, color, var=None, cmd=None):
        super().__init__(parent, fg_color="transparent")
        self.on_color = color; self.off_color = "#484f5a"
        self.var = var if var else tk.BooleanVar(value=True)
        self.initial = var.get() if var else True
        self.box = ctk.CTkFrame(self, width=18, height=18, fg_color=color if self.initial else self.off_color, corner_radius=4)
        self.box.pack(side="left", padx=(0,3))
        self.lbl = ctk.CTkLabel(self, text=text, font=("Malgun Gothic",9,"bold"), text_color="#cdd6f4")
        self.lbl.pack(side="left")
        self.box.bind("<Button-1>", self._toggle); self.lbl.bind("<Button-1>", self._toggle)
        self.cmd = cmd
        # 외부에서 var 변경 시 시각적 동기화
        self._trace_id = self.var.trace_add("write", self._sync)
    def _sync(self, *a):
        self.box.configure(fg_color=self.on_color if self.var.get() else self.off_color)
    def _toggle(self, e=None):
        v = not self.var.get(); self.var.set(v)
        self.box.configure(fg_color=self.on_color if v else self.off_color)
        if self.cmd: self.cmd()
    def get(self): return self.var.get()
    def set(self, v): self.var.set(v); self.box.configure(fg_color=self.on_color if v else self.off_color)


SLIDER_PROGRESS_DEFAULT = "#f38ba8"  # HP·힐% 임계값 공통
SLIDER_PROGRESS_MNA = "#89b4fa"      # 파랭이(마나)만 파랑


def make_pct_slider(parent, from_, to, variable, progress_color=SLIDER_PROGRESS_DEFAULT, width=68, steps=None):
    """힐% 슬라이더 — 얇은 트랙 + 동그란 골드 손잡이."""
    kw = dict(
        from_=from_, to=to, variable=variable, width=width, height=8,
        corner_radius=4, button_corner_radius=7, button_length=7,
        fg_color="#16161f", border_color="#3b3d4a", border_width=1,
        button_color="#d4af37", button_hover_color="#f0d878",
        progress_color=progress_color,
    )
    if steps is not None:
        kw["number_of_steps"] = steps
    return ctk.CTkSlider(parent, **kw)


class Collapsible(ctk.CTkFrame):
    """▶/▼ 접이식 섹션 (뚱헌터 Collapsible과 동일 개념)."""
    def __init__(self, parent, title, start_open=False, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._title = title
        self._open = start_open
        self.btn = ctk.CTkButton(
            self, text=self._btn_text(), height=22, fg_color="#313244", hover_color="#45475a",
            anchor="w", font=("Malgun Gothic", 9, "bold"), text_color="#cdd6f4",
            command=self._flip,
        )
        self.btn.pack(fill="x", padx=2, pady=1)
        self.body = ctk.CTkFrame(self, fg_color="#313244", corner_radius=6)
        if start_open:
            self.body.pack(fill="x", padx=2, pady=(0, 2))

    def _btn_text(self):
        return f"{'▼' if self._open else '▶'} {self._title}"

    def _flip(self):
        self._open = not self._open
        self.btn.configure(text=self._btn_text())
        if self._open:
            self.body.pack(fill="x", padx=2, pady=(0, 2))
        else:
            self.body.pack_forget()
        try:
            self.update_idletasks()
        except Exception:
            pass
        top = self.winfo_toplevel()
        if top and top.winfo_exists():
            def _sync():
                try:
                    top.update_idletasks()
                    fn = globals().get("sync_window_height")
                    if fn:
                        fn()
                except Exception:
                    pass
            top.after(50, _sync)



# ── UI 반응성: 팝업/오버레이 중 topmost·리사이즈·제어판 갱신 일시정지 ──
_ui_popup_depth = 0
_admin_ui_pause = False

def _ui_busy():
    return _ui_popup_depth > 0 or _admin_ui_pause

def _ui_popup_enter():
    global _ui_popup_depth
    _ui_popup_depth += 1

def _ui_popup_leave():
    global _ui_popup_depth
    _ui_popup_depth = max(0, _ui_popup_depth - 1)

def _set_admin_ui_pause(v):
    global _admin_ui_pause
    _admin_ui_pause = bool(v)


def _ui_alert(title, msg, kind="info"):
    try:
        import imgui_ui
        if imgui_ui.show_alert(title, msg):
            return
    except Exception:
        pass
    try:
        if kind == "error":
            messagebox.showerror(title, msg)
        elif kind == "warning":
            messagebox.showwarning(title, msg)
        else:
            messagebox.showinfo(title, msg)
    except Exception:
        pass

def _ui_yesno(title, msg, on_yes, on_no=None):
    try:
        import imgui_ui
        if imgui_ui.show_yesno(title, msg, on_yes, on_no):
            return
    except Exception:
        pass
    try:
        if messagebox.askyesno(title, msg):
            on_yes()
        elif on_no:
            on_no()
    except Exception:
        pass

def _request_admin_refresh():
    try:
        import imgui_ui
        imgui_ui.admin_mark_dirty()
    except Exception:
        pass

def _admin_grab_rgb(roi):
    if not roi or roi[2] <= roi[0] or roi[3] <= roi[1]:
        return None
    import mss as _mss
    sct = _mss.MSS()
    x1, y1, x2, y2 = roi
    img = sct.grab({"left": x1, "top": y1, "width": max(x2-x1,1), "height": max(y2-y1,1)})
    return np.array(img, dtype=np.uint8)[:, :, :3][:, :, ::-1]

def _admin_preview_label(roi, ref100, is_blue=False, strict=True):
    if roi[0] == 0:
        return "", "#f0f0f0"
    arr = _admin_grab_rgb(roi)
    if arr is None:
        return "", "#f0f0f0"
    x1, y1, x2, y2 = roi
    if is_blue:
        Rq = arr[:,:,0].astype(int); Gq = arr[:,:,1].astype(int); Bq = arr[:,:,2].astype(int)
        blue = (Bq>50)&(Bq>Rq*1.1)&(Bq>Gq*1.1)
        raw = int(np.sum(blue)); wh = max(x2-x1,1)*max(y2-y1,1)
        pct = round(raw/ref100*100,1) if (ref100 and ref100>0) else round(raw/max(wh,1)*100,1)
        return "ROI=(%s,%s,%s,%s) | MP:%s%% | 100%%ref:%spx" % (x1, y1, x2-x1, y2-y1, int(pct), ref100 or "?"), "#f0f0f0"
    if strict:
        if not party_slot_active_rgb(arr):
            return "ROI=(%s,%s,%s,%s) | 없음 (빈칸/사망)" % (x1, y1, x2-x1, y2-y1), "#6c7086"
        pct = bar_fill_pct_from_rgb(arr, ref100, strict=True)
        return "ROI=(%s,%s,%s,%s) | HP:%s%% | 100%%ref:%scol" % (x1, y1, x2-x1, y2-y1, int(pct), ref100 or "?"), "#f0f0f0"
    _R, _G, _B = arr[:, :, 0].astype(int), arr[:, :, 1].astype(int), arr[:, :, 2].astype(int)
    _tot = arr.shape[0] * arr.shape[1]
    _gray = (abs(_R - _G) < 35) & (abs(_G - _B) < 35) & (abs(_R - _B) < 35) & (_R > 20) & (_R < 170)
    _red = (_R > 80) & (_R > _G * 1.2) & (_R > _B * 1.2)
    _pet = (int(np.sum(_gray)) > _tot * 0.15 and int(np.sum(_red)) < _tot * 0.03) or (
        abs(float(np.mean(_R)) - float(np.mean(_G))) < 25
        and abs(float(np.mean(_G)) - float(np.mean(_B))) < 25
        and abs(float(np.mean(_R)) - float(np.mean(_B))) < 25
        and float(np.mean(_R)) > 50 and float(np.mean(_R)) < 180
    )
    pct = _self_hp_pct_from_arr(arr, ref100, petrified=_pet)
    return "ROI=(%s,%s,%s,%s) | HP:%s%% | 100%%ref:%spx" % (x1, y1, x2-x1, y2-y1, int(pct), ref100 or "?"), "#f0f0f0"

def _admin_stream_label():
    roi = _stream_roi
    if roi[2] <= roi[0] or roi[3] <= roi[1]:
        return "미설정 → 격수 쫄화면에 주 모니터 전체 송출", "#6c7086"
    x1, y1, x2, y2 = roi
    return "송출 ROI=(%s,%s) %sx%s" % (x1, y1, x2-x1, y2-y1), "#f0f0f0"

def open_self_hp_overlay():
    ov = tk.Toplevel(root); ov.overrideredirect(True)
    _set_admin_ui_pause(True); ov.bind("<Destroy>", lambda e: _set_admin_ui_pause(False))
    sx = ctypes.windll.user32.GetSystemMetrics(76); sy = ctypes.windll.user32.GetSystemMetrics(77)
    sw = ctypes.windll.user32.GetSystemMetrics(78); sh = ctypes.windll.user32.GetSystemMetrics(79)
    ov.geometry(f"{sw}x{sh}+{sx}+{sy}"); ov.attributes("-alpha",0.35)
    ov.configure(bg="black"); ov.attributes("-topmost",True); ov.focus_force()
    cv = tk.Canvas(ov,bg="black",highlightthickness=0); cv.pack(fill="both",expand=True)
    d = {"x1":0,"y1":0,"x2":0,"y2":0,"r":None}
    def dn(e):
        d["x1"],d["y1"]=e.x_root,e.y_root
        d["r"]=cv.create_rectangle(e.x_root-sx,e.y_root-sy,e.x_root-sx,e.y_root-sy,
                    outline="#10b981", width=4)
    def mv(e):
        cv.coords(d["r"],d["x1"]-sx,d["y1"]-sy,e.x_root-sx,e.y_root-sy)
    def up(e):
        d["x2"],d["y2"]=e.x_root,e.y_root
        x1=min(d["x1"],d["x2"]); y1=min(d["y1"],d["y2"]); x2=max(d["x1"],d["x2"]); y2=max(d["y1"],d["y2"])
        if x2-x1<8 or y2-y1<3: ov.destroy(); return
        global SELF_HP_ROI; SELF_HP_ROI=(x1,y1,x2,y2)
        save_hidden_config(loaded_pwd if (loaded_pwd) else "")
        ov.destroy()
        _request_admin_refresh()
    cv.bind("<ButtonPress-1>",dn); cv.bind("<B1-Motion>",mv); cv.bind("<ButtonRelease-1>",up)
    tk.Label(ov,text="🟢 쫄법 피통 왼쪽→오른쪽 드래그",fg="#10b981",bg="black",font=("Malgun Gothic",13,"bold")).place(relx=0.5,rely=0.02,anchor="n")
    tk.Label(ov,text="ESC=취소",fg="#6c7086",bg="black",font=("",9)).place(relx=0.5,rely=0.06,anchor="n")
    ov.bind("<Escape>",lambda e:ov.destroy())

def set_self_100ref():
    global SELF_HP_100_REF
    x1,y1,x2,y2=SELF_HP_ROI
    if x1==0 and x2==0: return
    arr = _admin_grab_rgb(SELF_HP_ROI)
    if arr is None: return
    R, G, B = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    red = (R > 80) & (R > G * 1.2) & (R > B * 1.2)
    grn = (G > 80) & (G > R * 1.2) & (G > B * 1.2)
    SELF_HP_100_REF = max(1, int(np.sum(red | grn)))
    save_hidden_config(loaded_pwd if (loaded_pwd) else "")
    _ui_alert("100% 기준","[내피통] 저장됨: "+str(SELF_HP_100_REF)+"px")
    _request_admin_refresh()

def open_mna_roi_overlay():
    ov=tk.Toplevel(root); ov.overrideredirect(True)
    _set_admin_ui_pause(True); ov.bind("<Destroy>", lambda e: _set_admin_ui_pause(False))
    sx3 = ctypes.windll.user32.GetSystemMetrics(76); sy3 = ctypes.windll.user32.GetSystemMetrics(77)
    sw3 = ctypes.windll.user32.GetSystemMetrics(78); sh3 = ctypes.windll.user32.GetSystemMetrics(79)
    ov.geometry(f"{sw3}x{sh3}+{sx3}+{sy3}"); ov.attributes("-alpha",0.35)
    ov.configure(bg="black"); ov.attributes("-topmost",True); ov.focus_force()
    cv=tk.Canvas(ov,bg="black",highlightthickness=0); cv.pack(fill="both",expand=True)
    d={"x1":0,"y1":0,"x2":0,"y2":0,"r":None}
    def dn(e): d["x1"],d["y1"]=e.x_root,e.y_root; d["r"]=cv.create_rectangle(e.x,e.y,e.x,e.y,outline="#89b4fa",width=4)
    def mv(e):
        if d["r"]: cv.coords(d["r"],d["x1"]-ov.winfo_rootx(),d["y1"]-ov.winfo_rooty(),e.x,e.y)
    def up(e):
        d["x2"],d["y2"]=e.x_root,e.y_root
        x1=min(d["x1"],d["x2"]); y1=min(d["y1"],d["y2"]); x2=max(d["x1"],d["x2"]); y2=max(d["y1"],d["y2"])
        if x2-x1<8 or y2-y1<3: ov.destroy(); return
        global MNA_ROI; MNA_ROI=(x1,y1,x2,y2)
        save_hidden_config(loaded_pwd if (loaded_pwd) else "")
        ov.destroy()
        _request_admin_refresh()
    cv.bind("<ButtonPress-1>",dn); cv.bind("<B1-Motion>",mv); cv.bind("<ButtonRelease-1>",up)
    tk.Label(ov,text="💙 마나바 왼쪽→오른쪽 드래그",fg="#89b4fa",bg="black",font=("Malgun Gothic",13,"bold")).place(relx=0.5,rely=0.02,anchor="n")
    tk.Label(ov,text="ESC=취소",fg="#6c7086",bg="black",font=("",9)).place(relx=0.5,rely=0.06,anchor="n")
    ov.bind("<Escape>",lambda e:ov.destroy())

def set_mna_100ref():
    global MNA_100_REF
    x1,y1,x2,y2=MNA_ROI
    if x1==0 and x2==0: return
    arr = _admin_grab_rgb(MNA_ROI)
    if arr is None: return
    blue = (arr[:,:,2]>50)&(arr[:,:,2]>arr[:,:,0]*1.1)&(arr[:,:,2]>arr[:,:,1]*1.1)
    MNA_100_REF = int(np.sum(blue))
    save_hidden_config(loaded_pwd if (loaded_pwd) else "")
    _ui_alert("100% 기준","[마나] 저장됨: "+str(MNA_100_REF)+"px")
    _request_admin_refresh()

def set_party_100ref(pi):
    x1,y1,x2,y2=PARTY_ROIS[pi]
    if x1==0: return
    arr = _admin_grab_rgb(PARTY_ROIS[pi])
    if arr is None: return
    PARTY_HP_100_REF[pi]=max(1, _hp_bar_band_cols(arr)[0])
    save_hidden_config(loaded_pwd if (loaded_pwd) else "")
    _request_admin_refresh()

def open_party_roi_overlay(pi):
    ov = tk.Toplevel(root); ov.attributes("-fullscreen",True); ov.attributes("-alpha",0.35)
    _set_admin_ui_pause(True); ov.bind("<Destroy>", lambda e: _set_admin_ui_pause(False))
    ov.configure(bg="black"); ov.attributes("-topmost",True); ov.focus_force()
    cv = tk.Canvas(ov,bg="black",highlightthickness=0); cv.pack(fill="both",expand=True)
    d = {"x1":0,"y1":0,"x2":0,"y2":0,"r":None}
    def dn(e): d["x1"],d["y1"]=e.x_root,e.y_root; d["r"]=cv.create_rectangle(e.x,e.y,e.x,e.y,outline="#10b981",width=4)
    def mv(e):
        if d["r"]: cv.coords(d["r"],d["x1"]-ov.winfo_rootx(),d["y1"]-ov.winfo_rooty(),e.x,e.y)
    def up(e):
        d["x2"],d["y2"]=e.x_root,e.y_root
        x1=min(d["x1"],d["x2"]); y1=min(d["y1"],d["y2"]); x2=max(d["x1"],d["x2"]); y2=max(d["y1"],d["y2"])
        if x2-x1<8 or y2-y1<3: ov.destroy(); return
        x1, y1, x2, y2 = _tighten_party_roi_from_drag(x1, y1, x2, y2)
        PARTY_ROIS[pi]=(x1,y1,x2,y2)
        PARTY_COORDS[pi]=[(x1+x2)//2,(y1+y2)//2]
        save_hidden_config(loaded_pwd if (loaded_pwd) else "")
        ov.destroy()
        _request_admin_refresh()
    cv.bind("<ButtonPress-1>",dn); cv.bind("<B1-Motion>",mv); cv.bind("<ButtonRelease-1>",up)
    tk.Label(ov,text=f"🔴 P{pi+1} 빨간 막대 드래그 (넓게 잡아도 막대만 자동 맞춤)",fg="#ef4444",bg="black",font=("Malgun Gothic",12,"bold")).place(relx=0.5,rely=0.02,anchor="n")
    tk.Label(ov,text="ESC=취소 · 놓으면 빨간 HP막대만 ROI 저장",fg="#6c7086",bg="black",font=("",9)).place(relx=0.5,rely=0.06,anchor="n")
    ov.bind("<Escape>",lambda e:ov.destroy())

def open_party_name_roi_overlay(pi):
    ov = tk.Toplevel(root); ov.attributes("-fullscreen",True); ov.attributes("-alpha",0.35)
    _set_admin_ui_pause(True); ov.bind("<Destroy>", lambda e: _set_admin_ui_pause(False))
    ov.configure(bg="black"); ov.attributes("-topmost",True); ov.focus_force()
    cv = tk.Canvas(ov,bg="black",highlightthickness=0); cv.pack(fill="both",expand=True)
    d = {"x1":0,"y1":0,"x2":0,"y2":0,"r":None}
    def dn(e): d["x1"],d["y1"]=e.x_root,e.y_root; d["r"]=cv.create_rectangle(e.x,e.y,e.x,e.y,outline="#f9e2af",width=4)
    def mv(e):
        if d["r"]: cv.coords(d["r"],d["x1"]-ov.winfo_rootx(),d["y1"]-ov.winfo_rooty(),e.x,e.y)
    def up(e):
        d["x2"],d["y2"]=e.x_root,e.y_root
        x1=min(d["x1"],d["x2"]); y1=min(d["y1"],d["y2"]); x2=max(d["x1"],d["x2"]); y2=max(d["y1"],d["y2"])
        if x2-x1<8 or y2-y1<3: ov.destroy(); return
        PARTY_NAME_ROIS[pi]=(x1,y1,x2,y2)
        save_hidden_config(loaded_pwd if (loaded_pwd) else "")
        ov.destroy()
        _request_admin_refresh()
    cv.bind("<ButtonPress-1>",dn); cv.bind("<B1-Motion>",mv); cv.bind("<ButtonRelease-1>",up)
    tk.Label(ov,text=f"🖼️ P{pi+1} 아이콘(초상화) 드래그 — HP바 옆 캐릭터 아이콘만",fg="#f9e2af",bg="black",font=("Malgun Gothic",13,"bold")).place(relx=0.5,rely=0.02,anchor="n")
    tk.Label(ov,text="ESC=취소",fg="#6c7086",bg="black",font=("",9)).place(relx=0.5,rely=0.06,anchor="n")
    ov.bind("<Escape>",lambda e:ov.destroy())

def open_stream_roi_overlay():
    ov = tk.Toplevel(root); ov.overrideredirect(True)
    _set_admin_ui_pause(True); ov.bind("<Destroy>", lambda e: _set_admin_ui_pause(False))
    sx = ctypes.windll.user32.GetSystemMetrics(76); sy = ctypes.windll.user32.GetSystemMetrics(77)
    sw = ctypes.windll.user32.GetSystemMetrics(78); sh = ctypes.windll.user32.GetSystemMetrics(79)
    ov.geometry(f"{sw}x{sh}+{sx}+{sy}"); ov.attributes("-alpha",0.35)
    ov.configure(bg="black"); ov.attributes("-topmost",True); ov.focus_force()
    cv = tk.Canvas(ov,bg="black",highlightthickness=0); cv.pack(fill="both",expand=True)
    d = {"x1":0,"y1":0,"x2":0,"y2":0,"r":None}
    def dn(e):
        d["x1"],d["y1"]=e.x_root,e.y_root
        d["r"]=cv.create_rectangle(e.x_root-sx,e.y_root-sy,e.x_root-sx,e.y_root-sy,outline="#a6e3a1",width=4)
    def mv(e):
        if d["r"]: cv.coords(d["r"],d["x1"]-sx,d["y1"]-sy,e.x_root-sx,e.y_root-sy)
    def up(e):
        d["x2"],d["y2"]=e.x_root,e.y_root
        x1=min(d["x1"],d["x2"]); y1=min(d["y1"],d["y2"]); x2=max(d["x1"],d["x2"]); y2=max(d["y1"],d["y2"])
        if x2-x1<20 or y2-y1<20: ov.destroy(); return
        global _stream_roi
        _stream_roi = (x1, y1, x2, y2)
        save_hidden_config(loaded_pwd if (loaded_pwd) else "")
        ov.destroy()
        _request_admin_refresh()
    cv.bind("<ButtonPress-1>",dn); cv.bind("<B1-Motion>",mv); cv.bind("<ButtonRelease-1>",up)
    tk.Label(ov,text="📡 격수 쫄화면 송출 영역 드래그 (게임창)",fg="#a6e3a1",bg="black",font=("Malgun Gothic",13,"bold")).place(relx=0.5,rely=0.02,anchor="n")
    tk.Label(ov,text="ESC=취소 · 격수 PC에서 📡전송 ON 후 쫄화면으로 확인",fg="#6c7086",bg="black",font=("",9)).place(relx=0.5,rely=0.06,anchor="n")
    ov.bind("<Escape>",lambda e:ov.destroy())

def clear_stream_roi():
    global _stream_roi
    _stream_roi = (0, 0, 0, 0)
    save_hidden_config(loaded_pwd if (loaded_pwd) else "")
    _request_admin_refresh()


def open_scroll_pick(anchor, values, on_pick, width=None, max_h=220, current=None):
    """CTk 기본 드롭다운 대신 스크롤 픽 팝업."""
    if not values:
        return
    _ui_popup_enter()
    try:
        pop = ctk.CTkToplevel(root)
    except Exception:
        _ui_popup_leave()
        return
    pop.withdraw()
    try:
        pop.overrideredirect(True)
        pop.attributes("-topmost", True)
    except Exception:
        pass
    pop.configure(fg_color="#0b0b10")
    try:
        w = int(width or max(100, anchor.winfo_width()))
    except Exception:
        w = int(width or 100)
    h = min(int(max_h), max(44, 30 * len(values) + 16))
    try:
        ax = anchor.winfo_rootx()
        ay = anchor.winfo_rooty() + anchor.winfo_height() + 2
    except Exception:
        ax, ay = 100, 100
    pop.geometry(f"{w}x{h}+{ax}+{ay}")
    closed = {"v": False}

    def close():
        if closed["v"]:
            return
        closed["v"] = True
        try:
            pop.grab_release()
        except Exception:
            pass
        try:
            pop.destroy()
        except Exception:
            pass
        _ui_popup_leave()

    shell = ctk.CTkFrame(
        pop, fg_color="#14141c", corner_radius=10,
        border_width=1, border_color="#3d3a2f",
    )
    shell.pack(fill="both", expand=True, padx=1, pady=1)
    sf = ctk.CTkScrollableFrame(
        shell, fg_color="#14141c", width=max(80, w - 14), height=max(32, h - 14),
        corner_radius=8,
    )
    sf.pack(fill="both", expand=True, padx=4, pady=4)

    def pick(v):
        try:
            on_pick(v)
        finally:
            close()

    cur = str(current) if current is not None else ""
    for v in values:
        sel = (str(v) == cur)
        ctk.CTkButton(
            sf, text=str(v), height=28,
            fg_color="#2a2118" if sel else "#1a1a22",
            hover_color="#3d2e1f",
            text_color="#f0d9a8" if sel else "#c8c3b8",
            border_width=1,
            border_color="#c9a84c" if sel else "#2a2a32",
            font=("Malgun Gothic", 10, "bold" if sel else "normal"),
            anchor="w", corner_radius=6,
            command=lambda vv=v: pick(vv),
        ).pack(fill="x", pady=2, padx=1)

    try:
        pop.deiconify()
        pop.lift()
        pop.focus_force()
        pop.grab_set()
    except Exception:
        pass
    pop.bind("<Escape>", lambda e: close())

def make_pick_btn(parent, values, textvariable, command=None, width=80, height=22, font=("Malgun Gothic", 9),
                  fg_color=None, hover_color=None, border_color=None, text_color=None, premium=False, arrow=True):
    """콤보 대체: 현재값 버튼 + 스크롤 픽 팝업."""
    if premium:
        # 고급: 딥차콜 + 뮤트골드
        fg_color = "#16161f"
        hover_color = "#22222c"
        border_color = "#c9a84c"
        text_color = "#f0d9a8"
        corner = 8
        bwidth = 1
        font = ("Malgun Gothic", 10, "bold")
    else:
        corner = 6
        bwidth = 1
        fg_color = fg_color or "#1e1e2e"
        hover_color = hover_color or "#45475a"
        border_color = border_color or "#45475a"
        text_color = text_color or "#cdd6f4"

    def _label():
        v = textvariable.get()
        return f"{v} ▾" if arrow else v

    btn = ctk.CTkButton(
        parent, text=_label(), width=width, height=height, font=font,
        fg_color=fg_color, hover_color=hover_color, border_width=bwidth, border_color=border_color,
        text_color=text_color, corner_radius=corner,
    )
    state = {"cmd": command}

    def _sync(*a):
        try:
            btn.configure(text=_label())
        except Exception:
            pass

    try:
        textvariable.trace_add("write", _sync)
    except Exception:
        pass

    def _on_pick(v):
        textvariable.set(v)
        cmd = state["cmd"]
        if cmd:
            try:
                cmd(v)
            except TypeError:
                cmd()

    def _open():
        open_scroll_pick(btn, list(values), _on_pick, width=max(width, 100), current=textvariable.get())

    btn.configure(command=_open)

    def set_command(cmd):
        state["cmd"] = cmd

    btn.set_pick_command = set_command
    return btn


BUFF_SLOT_LABELS = ["F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12"]
BUFF_SLOT_KEYS = {"F5": "5", "F6": "6", "F7": "7", "F8": "8", "F9": "9", "F10": "X", "F11": "Y", "F12": "Z"}
BUFF_HOTBARS = ["F1", "F2", "F3"]
_buff_cfg = {}
last_buff_times = {}
buff_next_due = {}
last_buff_global = 0
saved_buff_on = "0"
saved_buff_grid = {}
saved_self_buff_on = "0"
saved_self_buff_hotbar = "F1"
saved_self_buff_slot = "F5"
saved_self_buff_sec = "1200"
SELF_BUFF_COUNT = 4
saved_self_buff_grid = {}
_self_buff_cfg = []


def buff_grid_key(hb, slot):
    return f"{hb}_{slot}"


def buff_time_key(hb, slot):
    return f"_buff_{hb}_{slot}"


def cast_buff(hb_label, slot_label):
    """버프 시전. F2/F3이면 시전 후 F1 복귀.
    고정(클릭 OFF)이면 스킬 → K(대상 클릭) → F1 — 예전엔 무한클릭이 대신했음."""
    hb = hb_label.replace("F", "")
    sk = BUFF_SLOT_KEYS[slot_label]
    need_click = not attack_click_active()
    if need_click:
        was_fixed, was_follow = _pause_attack_click()
        if was_fixed:
            _suspend_fix_shift_restore(1.2)
        try:
            focus_lineage_window()
            time.sleep(0.02)
            if hb == "1":
                execute_keys([sk], 0.45, skip_follow_toggle=True, key_gap=(0.08, 0.18))
                _buff_target_click()
            else:
                execute_keys([hb, sk], 0.45, skip_follow_toggle=True, key_gap=(0.08, 0.18))
                _buff_target_click()
                execute_keys(["1"], 0.35, skip_follow_toggle=True, key_gap=(0.08, 0.15))
        finally:
            _resume_attack_click(was_fixed, was_follow)
    else:
        if hb == "1":
            execute_keys([sk], 0.5)
        else:
            execute_keys([hb, sk, "1"], 0.55, key_gap=(0.08, 0.18))


def cast_self_buff(hb_label, slot_label):
    """자기 대상 버프(헤이스트 등) — 슬롯 키 두 번 연타. 자힐처럼 F1 복귀."""
    hb = hb_label.replace("F", "")
    sk = BUFF_SLOT_KEYS[slot_label]
    tap_gap = (0.09, 0.18)
    if hb == "1":
        execute_keys(["1", sk, sk], 0.55, key_gap=tap_gap)
    else:
        execute_keys([hb, sk, sk, "1"], 0.55, key_gap=tap_gap)


def self_buff_time_key(idx):
    return f"_self_buff_{idx}"


def _parse_self_buff_saved(idx):
    raw = saved_self_buff_grid.get(str(idx))
    if not raw and idx == 1:
        on = saved_self_buff_on in ("1", "true", "True")
        return on, saved_self_buff_hotbar, saved_self_buff_slot, str(saved_self_buff_sec or "1200")
    if not raw:
        return False, "F1", "F5", "1200"
    parts = raw.split(":")
    on = parts[0] in ("1", "true", "True") if parts else False
    hb = parts[1] if len(parts) > 1 and parts[1] in BUFF_HOTBARS else "F1"
    slot = parts[2] if len(parts) > 2 and parts[2] in BUFF_SLOT_LABELS else "F5"
    sec = parts[3] if len(parts) > 3 else "1200"
    return on, hb, slot, sec


def migrate_legacy_self_buff():
    global saved_self_buff_grid
    if saved_self_buff_grid:
        return
    if saved_self_buff_on in ("1", "true", "True") or saved_self_buff_hotbar != "F1" or saved_self_buff_slot != "F5":
        saved_self_buff_grid["1"] = f"{saved_self_buff_on}:{saved_self_buff_hotbar}:{saved_self_buff_slot}:{saved_self_buff_sec}"


def mna_potion_keys():
    """파랭이 위치(핫바+슬롯)를 UI에서 바꿀 수 있게 — 예전엔 F2+F8로 고정이었는데,
    F1의 F8 슬롯에 귀환주문서가 있는 경우 핫바전환 타이밍이 어긋나면 그게 눌려서
    파랭이 대신 베르(귀환)가 나가는 사고가 있었음. 파랭이를 F1 슬롯이나 다른 자리로
    옮겨두면 핫바전환 자체가 없어져서(F1) 이 사고가 원천적으로 안 생김."""
    hb_label = mna_hotbar_var.get() if mna_hotbar_var else MNA_HOTBAR
    slot_label = mna_slot_var.get() if mna_slot_var else MNA_SLOT
    hb = hb_label.replace("F", "")
    sk = BUFF_SLOT_KEYS.get(slot_label, "8")
    if hb == "1":
        return [sk]
    return [hb, sk, "1"]


def get_heal_hotbar_slot(strong=False):
    """UI·저장값에서 일반/상위힐 핫바+슬롯."""
    if strong:
        hb = strong_heal_hotbar_var.get() if strong_heal_hotbar_var else STRONG_HEAL_HOTBAR
        sl = strong_heal_slot_var.get() if strong_heal_slot_var else STRONG_HEAL_SLOT
        d_slot = "F7"
    else:
        hb = heal_hotbar_var.get() if heal_hotbar_var else HEAL_HOTBAR
        sl = heal_slot_var.get() if heal_slot_var else HEAL_SLOT
        d_slot = "F9"
    if hb not in BUFF_HOTBARS:
        hb = "F1"
    if sl not in BUFF_SLOT_LABELS:
        sl = d_slot
    return hb, sl


def heal_action_keys(hotbar_label, slot_label, double=False):
    """힐 단축키 → 펌웨어 키 시퀀스. F1이면 슬롯만, F2/F3이면 핫바전환+슬롯."""
    hb = (hotbar_label or "F1").replace("F", "")
    slot = slot_label if slot_label in BUFF_SLOT_LABELS else "F9"
    sk = BUFF_SLOT_KEYS.get(slot, "9")
    if hb == "1":
        keys = [sk]
    else:
        keys = [hb, sk]
    if double:
        keys.append(sk)
    return keys


def heal_slot_label(hotbar_label, slot_label):
    return "%s+%s" % (hotbar_label, slot_label)


def buff_interval_jitter(base_sec):
    """설정 초 ± 랜덤 (기계적 1200초 고정 방지)."""
    base = max(5, int(base_sec))
    spread = max(12, min(240, int(base * 0.14)))
    return max(8, int(base + human_delay(-spread, spread)))


def schedule_buff(tk, base_iv, soon=False):
    global buff_next_due
    if soon:
        buff_next_due[tk] = time.time() + human_delay(3, 18)
    else:
        buff_next_due[tk] = time.time() + buff_interval_jitter(base_iv)


def migrate_legacy_buffs():
    """예전 V_BL/V_SH/V_BLU/V_F10/V_F11 설정을 그리드로 이전."""
    global saved_buff_grid
    if saved_buff_grid:
        return
    legacy = [
        ("F2", "F5", saved_v_bl),
        ("F2", "F6", saved_v_sh),
        ("F2", "F11", saved_v_blu),
        ("F1", "F10", saved_v_f10),
        ("F1", "F11", saved_v_f11),
    ]
    for hb, slot, iv in legacy:
        try:
            sec = int(iv)
        except Exception:
            sec = BASE_BUFF_INTERVAL
        if sec > 0:
            saved_buff_grid[buff_grid_key(hb, slot)] = f"0:{sec}"


PARTY_COORDS = [
    [348, 611], [268, 646], [264, 612],  
    [340, 612], [347, 645], [276, 678], [347, 678], [347, 711]
]
PARTY_ROIS = [(0,0,0,0)] * 8
PARTY_HP_THRESHOLDS = [50] * 8
PARTY_USE_ROI = [True] * 8
PARTY_HP_100_REF = [None] * 8
# 아이콘(초상화) ROI — 배경(나무 등)이 우연히 HP바 모양으로 오탐되는 것을 막는 이중체크용.
# HP바 옆 캐릭터 아이콘 자리를 지정하면, 그 자리에 아이콘 뒤판 특유의 검정 픽셀이 있을 때만 진짜 파티원으로 인정.
# 미설정(0,0,0,0)이면 기존처럼 아이콘 체크 없이 HP바만으로 판정(하위호환).
PARTY_NAME_ROIS = [(0,0,0,0)] * 8
ICON_BLACK_PCT_THRESHOLD = 0.15  # 임시값 — 실측 진단수치(검은픽셀비율) 보고 조정 예정
# 파티창 사망 직전 깜빡임 때 전체 ROI가 잠깐 '바 없음'으로 떨어지는 것 방지.
# 슬롯별로 직전 정상 HP%를 잠시 유지(홀드). 진짜 사망/빈칸은 시간 지나면 폐기.
_party_hp_hold = {}          # pi -> (hp_pct, last_ok_time)
PARTY_HP_HOLD_SEC = 2.0
PARTY_HEAL_HOLD_SEC = 0.4    # 힐 타겟용 짧은 홀드 — 깜빡임에 타겟 놓치지 않게 (유령클릭은 짧게만)
MAIN_ATTACKER_COORD = PARTY_COORDS[1] 

SELF_HP_COORD = [512, 591] 
SELF_HP_RGB = [74, 69, 78]
SELF_HP_ROI = (0,0,0,0)
SELF_HP_100_REF = None
self_hp_threshold = 30

NOPARTY_HP_COORD = [1040, 111]
NOPARTY_RGB = [162, 146, 150]
attacker_hp_threshold = 85.0
UDP_ATTACKER_PORT = 9999
STREAM_TCP_PORT = 9100

def _ensure_udp_firewall(port, rule_name):
    """UDP 수신 허용 — 포트 규칙은 항상, exe 규칙은 sooplive/pythonw일 때만."""
    try:
        import subprocess
        flags = 0x08000000
        port_rule = "%s (port)" % rule_name
        subprocess.run(
            ["netsh", "advfirewall", "firewall", "delete", "rule", "name=%s" % port_rule],
            capture_output=True, timeout=5, creationflags=flags,
        )
        subprocess.run(
            [
                "netsh", "advfirewall", "firewall", "add", "rule",
                "name=%s" % port_rule,
                "dir=in", "action=allow", "protocol=UDP",
                "localport=%d" % int(port),
                "enable=yes",
            ],
            capture_output=True,
            timeout=10,
            creationflags=flags,
        )
        exe = os.path.abspath(sys.executable)
        if not exe.lower().endswith(".exe"):
            return
        subprocess.run(
            ["netsh", "advfirewall", "firewall", "delete", "rule", "name=%s" % rule_name],
            capture_output=True, timeout=5, creationflags=flags,
        )
        subprocess.run(
            [
                "netsh", "advfirewall", "firewall", "add", "rule",
                "name=%s" % rule_name,
                "dir=in", "action=allow", "protocol=UDP",
                "localport=%d" % int(port),
                "program=%s" % exe,
                "enable=yes",
            ],
            capture_output=True,
            timeout=10,
            creationflags=flags,
        )
    except Exception:
        pass
_stream_active = False
_stream_client = None
_stream_client_lock = Lock()
_stream_frame_lock = Lock()
_stream_frame_bgr = None
_stream_offer_ts = 0.0
_stream_roi = (0, 0, 0, 0)   # 0=미설정 → 주 모니터 전체
_remote_control_until = 0.0
_remote_mouse_lock = Lock()
_remote_mouse_queue = Queue(maxsize=32)
attacker_hp_udp = 100.0
attacker_poisoned = False
attacker_petrified = False
last_udp_time = 0
last_auth_check = 0

DANGER_HP_COORD = [594, 593] 
DANGER_HP_RGB = [78, 69, 74]
DANGER_HP_ROI = (0,0,0,0)
DANGER_HP_100_REF = None
danger_hp_threshold = 20

MNA_ROI = (0,0,0,0)
MNA_100_REF = None
mna_threshold = 30
MNA_HOTBAR = "F2"   # 파랭이가 실제로 있는 핫바(F1/F2/F3) — UI에서 바꿀 수 있음
MNA_SLOT = "F8"     # 파랭이가 실제로 있는 슬롯(F5~F12) — 기본값은 예전 하드코딩(F2+F8)과 동일
mna_hotbar_var = None
mna_slot_var = None
HEAL_HOTBAR = "F1"
HEAL_SLOT = "F9"
STRONG_HEAL_HOTBAR = "F1"
STRONG_HEAL_SLOT = "F7"
heal_hotbar_var = None
heal_slot_var = None
strong_heal_hotbar_var = None
strong_heal_slot_var = None
strong_heal_pct = 30
self_strong_heal_pct = 30
chk_strong_heal = None
chk_self_strong_heal = None
last_mna_potion = 0
chk_mna = None
# 힐·물약 스위치 저장값 (재시작 복원) — 기본은 기존 UI 기본과 동일
saved_chk_self_heal = "1"
saved_chk_danger = "1"
saved_chk_strong_heal = "1"
saved_chk_self_strong_heal = "1"
saved_chk_attacker = "1"
saved_chk_mna = "0"
saved_chk_end_bert = "0"
saved_chk_wheel_heal = "1"

LOG_FILE = os.path.join(APP_DIR, "ddong.log")
last_log = ""
log_history = []
def log_event(msg):
    global last_log
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    log_history.append(line)
    if len(log_history) > 50: log_history.pop(0)
    last_log = "\n".join(log_history[-8:])
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except: pass

SELF_POISON_COORD = [504, 589]
SELF_POISON_RGB = [10, 81, 0]
TARGET_POISON_COORD = [1000, 100] 
TARGET_POISON_RGB = [10, 81, 0]

BUFF_BAR_X1, BUFF_BAR_Y1, BUFF_BAR_X2, BUFF_BAR_Y2 = 0, 0, 0, 0
buff_templates = {}
buff_template_hu = {}

camera = None
ser = None


class KmBox:
    """아두이노 시리얼 대체 하드웨어. serial.Serial 호환 인터페이스(.write/.is_open/.flush/.close).
    아두이노코드.txt 펌웨어의 바이트 프로토콜을 그대로 kmNet 호출로 변환한다."""
    FKEY = {'1': 0x3A, '2': 0x3B, '3': 0x3C, '4': 0x3D, '5': 0x3E, '6': 0x3F,
            '7': 0x40, '8': 0x41, '9': 0x42, 'X': 0x43, 'Y': 0x44, 'Z': 0x45}
    SHIFT = 0xE1

    def __init__(self, ip, port, mac):
        if kmNet is None:
            raise RuntimeError("kmNet 모듈(pyd) 없음")
        # kmNet.init 이 잘못된 IP에서 수십 초~무한 블로킹 + GIL 점유 → 폼 '응답 없음'.
        # 별도 스레드 + 2초 타임아웃으로 막음 (예전 a64cab2 복구).
        box = {"r": None, "err": None}

        def _do_init():
            try:
                box["r"] = kmNet.init(str(ip), str(port), str(mac))
            except Exception as e:
                box["err"] = e

        t = Thread(target=_do_init, daemon=True)
        t.start()
        t.join(2.0)
        if t.is_alive():
            raise RuntimeError("뚱박스 연결 타임아웃(2초) — IP/전원/케이블 확인")
        if box["err"] is not None:
            raise box["err"]
        if box["r"] != 0:
            raise RuntimeError("뚱박스 연결 실패(%s)" % box["r"])
        self.is_open = True
        self._buf = b""
        self._auto = False
        self._alive = True
        self._lk = Lock()
        Thread(target=self._auto_loop, daemon=True).start()

    # 자동클릭 루프 (펌웨어 loop()의 autoClick 재현: 30~75ms 누름, 85~180ms 간격)
    def _auto_loop(self):
        while self._alive:
            if self._auto and self.is_open and _attack_follow and not _attack_fix:
                with self._lk:
                    if not self._auto or _attack_fix or not _attack_follow:
                        self._auto = False
                        continue
                    try:
                        kmNet.left(1); time.sleep(random.uniform(0.030, 0.075)); kmNet.left(0)
                    except: pass
                time.sleep(random.uniform(0.085, 0.180))
            else:
                if _attack_fix:
                    self._auto = False
                time.sleep(0.005)

    # 펌웨어 humanPress: 누르고 80~150ms 유지 후 뗌
    def _human_press(self, vk):
        with self._lk:
            try:
                kmNet.keydown(vk); time.sleep(random.uniform(0.080, 0.150)); kmNet.keyup(vk)
            except: pass

    def move_smooth(self, dx, dy, ms):
        """하드웨어 부드러운 이동(move_auto). 박스가 ms 동안 직선을 보간 → 뚝뚝거림 제거.
        move_auto 미지원 pyd면 False 반환(호출측이 기존 스텝방식으로 폴백)."""
        if not self.is_open or kmNet is None: return False
        dx, dy = int(dx), int(dy)
        if dx == 0 and dy == 0: return True
        fn = getattr(kmNet, "enc_move_auto", None) or getattr(kmNet, "move_auto", None)
        if fn is None: return False
        with self._lk:
            try: fn(dx, dy, int(ms))
            except: return False
        return True

    def write(self, data):
        if not self.is_open or kmNet is None: return
        if isinstance(data, str): data = data.encode()
        self._buf += data
        while self._buf:
            c = self._buf[:1]
            if c == b'<':                          # <dx,dy> 마우스 이동
                end = self._buf.find(b'>')
                if end == -1: return               # 토큰 미완성 → 다음 write 대기
                token = self._buf[1:end].decode(errors='ignore')
                self._buf = self._buf[end + 1:]
                try:
                    xs, ys = token.split(',')
                    with self._lk: kmNet.move(int(xs), int(ys))
                except: pass
            else:
                self._buf = self._buf[1:]
                self._cmd(chr(c[0]))

    def _cmd(self, cmd):
        if cmd == 'K':                             # 좌클릭 20~50ms
            with self._lk:
                try: kmNet.left(1); time.sleep(random.uniform(0.020, 0.050)); kmNet.left(0)
                except: pass
            return
        if cmd == 'M':                             # 휠클릭(가운데) 20~50ms — WDT4 휠힐
            with self._lk:
                try:
                    mid = getattr(kmNet, "middle", None)
                    if mid:
                        mid(1); time.sleep(random.uniform(0.020, 0.050)); mid(0)
                except: pass
            return
        if cmd == 'U':                             # 자동클릭 OFF + 전체키 해제
            self._auto = False
            with self._lk:
                try: kmNet.keyup(self.SHIFT)
                except: pass
            return
        if cmd == 'H':                             # 강제고정 — 시프트 ON. 클릭은 끄지 않음(제자리공격)
            with self._lk:
                try:
                    kmNet.keydown(self.SHIFT)
                except: pass
            return
        if cmd == 'R':                             # Shift 뗌 + 자동클릭 OFF
            with self._lk:
                try: kmNet.keyup(self.SHIFT)
                except: pass
            self._auto = False
            return
        if cmd == 'T':                             # 따라가기 — 클릭만. 고정이면 무시
            if _attack_fix or not _attack_follow:
                self._auto = False
                return
            with self._lk:
                try:
                    if not _force_fix:
                        kmNet.keyup(self.SHIFT)
                except: pass
            self._auto = True
            return
        if cmd == 'A':                             # F9
            self._human_press(0x42); return
        if cmd == 'B':                             # F9 두 번
            self._human_press(0x42); time.sleep(random.uniform(0.070, 0.130)); self._human_press(0x42); return
        if cmd == 'E':                             # F5
            self._human_press(0x3E); return
        if cmd == 'C':                             # 자동클릭OFF + 전체해제 + F8 1.1~1.4초 꾹
            self._auto = False
            with self._lk:
                try:
                    kmNet.keyup(self.SHIFT); time.sleep(0.01); kmNet.keydown(0x41)
                    time.sleep(random.uniform(1.1, 1.4)); kmNet.keyup(0x41)
                except: pass
            return
        if cmd in self.FKEY:                        # 1~9,X,Y,Z → F1~F12
            self._human_press(self.FKEY[cmd]); return

    def flush(self): pass

    def wheel(self, delta):
        if not self.is_open or kmNet is None:
            return
        fn = getattr(kmNet, "wheel", None) or getattr(kmNet, "mouse_wheel", None)
        if not fn:
            return
        d = max(-127, min(127, int(delta)))
        with self._lk:
            try:
                fn(d)
            except Exception:
                pass

    def lcd(self, frame):
        # LCD에 이미지 프레임 표시 (봇 명령이랑 같은 Lock으로 순서 보장)
        if not self.is_open or kmNet is None or not hasattr(kmNet, "lcd_picture"): return
        with self._lk:
            try: kmNet.lcd_picture(frame)
            except: pass

    def close(self):
        self._alive = False
        self._auto = False
        try: kmNet.keyup(self.SHIFT)
        except: pass
        self.is_open = False


running = False
BASE_BUFF_INTERVAL = 1200
BUFF_SEQ_GAP = 5.0
CLICK_JITTER_PCT = 10
_buff_cfg_save_after_id = None


def _click_jitter_xy(x, y, roi=None, pct=CLICK_JITTER_PCT):
    """클릭 목표 좌표 ±pct% 흔들림."""
    if roi and len(roi) >= 4:
        w = max(6, abs(int(roi[2]) - int(roi[0])))
        h = max(6, abs(int(roi[3]) - int(roi[1])))
        jx = max(1, int(w * pct / 100))
        jy = max(1, int(h * pct / 100))
    else:
        jx = jy = max(1, int(24 * pct / 100))
    return x + random.randint(-jx, jx), y + random.randint(-jy, jy)


def _buff_sec_str(iv, grid_key):
    raw = (iv.get() or "").strip()
    if raw:
        return raw
    prev = saved_buff_grid.get(grid_key, "")
    if ":" in prev:
        return prev.split(":", 1)[1]
    return str(BASE_BUFF_INTERVAL)


def _self_buff_sec_str(sec_var, idx):
    raw = (sec_var.get() or "").strip()
    if raw:
        return raw
    prev = saved_self_buff_grid.get(str(idx), "")
    parts = prev.split(":")
    if len(parts) > 3 and parts[3]:
        return parts[3]
    return "1200"


def _schedule_buff_cfg_save():
    global _buff_cfg_save_after_id
    if "root" not in globals() or not root:
        return
    try:
        if _buff_cfg_save_after_id is not None:
            root.after_cancel(_buff_cfg_save_after_id)
    except Exception:
        pass
    _buff_cfg_save_after_id = root.after(350, _save_buff_cfg_now)


def _save_buff_cfg_now():
    global _buff_cfg_save_after_id
    _buff_cfg_save_after_id = None
    try:
        save_hidden_config(loaded_pwd if loaded_pwd else "")
    except Exception:
        pass
last_loot = 0
last_buff_seq = 0
last_loot_sent_time = 0
loot_interval = 5.0
debounce = {'caps': 0, 'tab': 0, 'main': 0, 'space': 0, 'f4': 0, 'pageup': 0}

# ── 채팅 타이핑 감지 ──
# 주의: 고정(Home)은 아두이노가 Shift를 누른 채로 둠.
# Windows가 Shift 키다운을 반복 발생시키면 '채팅 중'으로 오인되어
# 파랭이·버프·줍기·해독이 영구 정지됨(힐은 예외라 혼자만 동작). → 수정자/매크로키는 무시.
last_typing_time = 0.0
TYPING_PAUSE_SEC = 1.5
_fix_shift_hold_off_until = 0.0   # 고정 중 Tab 등 사용자 키 누를 때 Shift 잠깐 해제
_fix_shift_macro_until = 0.0      # 연동단축키/힐 중 워커가 H 재적용하지 않게
_USER_PASS_VKS = (0x09, 0x1B, 0x0D)  # Tab, Esc, Enter
_TYPING_POLL_VKS = list(range(0x30, 0x3A)) + list(range(0x41, 0x5B)) + [0x20, 0x0D, 0x08]

def _typing_poll_worker():
    """채팅 타이핑 감지 — 전역 키 후킹 없이 폴링(게임 Tab 등 간섭 방지)."""
    global last_typing_time
    user32 = ctypes.windll.user32
    GetAsyncKeyState = user32.GetAsyncKeyState
    while timer_thread_active:
        try:
            if running:
                for vk in _TYPING_POLL_VKS:
                    if GetAsyncKeyState(vk) & 0x8000:
                        last_typing_time = time.time()
                        break
        except Exception:
            pass
        time.sleep(0.05)

def _user_keys_passthrough_worker():
    """강제고정(Shift) 중 Tab·Esc·Enter 누르면 Shift 잠깐 풀어서 게임에 키가 들어가게."""
    global _fix_shift_hold_off_until
    user32 = ctypes.windll.user32
    GetAsyncKeyState = user32.GetAsyncKeyState
    was_down = {vk: False for vk in _USER_PASS_VKS}
    while timer_thread_active:
        try:
            if running and _force_fix:
                if time.time() < _fix_shift_macro_until:
                    time.sleep(0.02)
                    continue
                for vk in _USER_PASS_VKS:
                    down = bool(GetAsyncKeyState(vk) & 0x8000)
                    if down and not was_down[vk]:
                        _fix_shift_hold_off_until = time.time() + 0.55
                        _fix_shift_up()
                    was_down[vk] = down
                if time.time() >= _fix_shift_hold_off_until:
                    _fix_shift_down()
            else:
                for vk in _USER_PASS_VKS:
                    was_down[vk] = False
        except Exception:
            pass
        time.sleep(0.02)
current_f9_prob = 0.3  # 예전 확률% — 자힐은 do_self_heal로 대체됨 (호환용 잔존)
last_self_heal = 0
last_party_heal = 0
last_party_cure = 0
last_noparty_heal = 0

selected_party_flags = [0, 1, 0, 0, 0, 0, 0, 0]
saved_party_flags = "0,1,0,0,0,0,0,0"
party_mode_flags = [1, 1, 1, 1, 1, 1, 1, 1]
saved_party_mode_flags = "1,1,1,1,1,1,1,1"

saved_v_bl = "1200"
saved_v_sh = "1200"
saved_v_blu = "1200"
saved_v_f10 = "1200"
saved_v_f11 = "1200"
saved_expire_start = ""
saved_expire_days = "0"
saved_win_w = 178
saved_win_h = 380
sheet_expire_info = ""   # 구글시트 C열 (일수 또는 만료일) — 표시·판정은 여기만 사용
sheet_expire_end = ""    # 구글시트 D열 (만료일)

root = None
main_body = None  # 옵션·버프·힐 스크롤 영역
chk_fix = None
chk_follow = None
chk_force_fix = None
_attack_follow = False  # 펌웨어 무한클릭 ON. Home/힐 resume 은 chk_follow 대신 이거 봄
_attack_fix = False     # Home 고정(클릭·시프트 OFF). 힐 resume 이 T 로 클릭을 다시 켜지 않게
_force_fix = False      # 강제고정(PageUp) 시프트 제자리공격
_attack_ser_lock = Lock()  # Home 과 힐 resume 이 섞이지 않게
_fix_hw_shift_on = False  # 아두이노에 시프트 켠 뒤. 강제고정 유지용
chk_space_save = None
mode_var = None
chk_poison = None
chk_target_poison = None
chk_party_poison = None
chk_loot = None
chk_end_bert = None
chk_wheel_heal = None
toggle_wheel_heal = None
lbl_status = None
lbl_buff = None
lbl_saved_coord = None
lbl_coords = None
lbl_ard = None

shutdown_time = None
timer_thread_active = False

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

def check_google_sheet(input_code):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=csv"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = response.read().decode('utf-8-sig', errors='ignore').splitlines()
        for i, line in enumerate(data):
            if i == 0: continue 
            cols = [c.strip('"') for c in line.split(',')]
            if len(cols) >= 1:
                db_code = cols[0].strip()
                db_hwid = cols[1].strip().upper() if len(cols) >= 2 else ""
                db_expire = cols[2].strip() if len(cols) >= 3 else ""
                db_start = cols[3].strip() if len(cols) >= 4 else ""
                if input_code == db_code:
                    if not db_hwid or db_hwid == "":
                        return "REGISTER", db_expire, db_start
                    if db_hwid == "ANY":
                        return "PASS", db_expire, db_start
                    if not hwid_matches(db_hwid):
                        return "ALREADY_IN_USE", "", ""
                    return "PASS", db_expire, db_start
        return "NOT_FOUND", "", "" 
    except:
        return "ERROR", "", ""

def _parse_expire_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(str(s).strip(), "%Y-%m-%d")
    except Exception:
        return None

def _effective_expire_date(cs_info, cs_start=None):
    """만료일 우선순위: D열(만료일) → C열(날짜). C열 숫자(일수)는 D 없을 때만 참고 안 함."""
    end_dt = _parse_expire_date(cs_start)
    if end_dt:
        return end_dt
    if cs_info == "0":
        return None
    return _parse_expire_date(cs_info)

def _is_code_expired(cs_info, cs_start=None):
    """구글시트 만료 판정 — D열 만료일 최우선."""
    end_dt = _effective_expire_date(cs_info, cs_start)
    if end_dt:
        return datetime.now().date() > end_dt.date()
    if cs_info == "0":
        return True
    if not cs_info:
        return False
    return False

def _sync_expire_cache(cs_info, cs_start=None):
    """구글시트 C/D → 메모리만 반영 (license.dat에는 만료일 저장 안 함)."""
    global sheet_expire_info, sheet_expire_end
    sheet_expire_info = (cs_info or "").strip()
    sheet_expire_end = (cs_start or "").strip()

def _auth_expire_text(cs_info=None, cs_start=None):
    """🔑 N일 남음 표시 — D열 만료일 최우선, 구글시트 기준."""
    info = cs_info if cs_info is not None else sheet_expire_info
    end_raw = cs_start if cs_start is not None else sheet_expire_end
    end_dt = _effective_expire_date(info, end_raw)
    if end_dt:
        days_left = (end_dt.date() - datetime.now().date()).days
        if days_left < 0:
            days_left = 0
        return f"🔑 {days_left}일 남음 ({end_dt.strftime('%m/%d')} 만료)"
    if info == "0":
        return ""
    if not info:
        return "🔑 영구 사용" if loaded_pwd else ""
    return "🔑 영구 사용"

def load_hidden_config():
    global MAIN_ATTACKER_COORD, SELF_HP_COORD, SELF_HP_RGB, NOPARTY_HP_COORD, NOPARTY_RGB, PARTY_COORDS
    global SELF_POISON_COORD, SELF_POISON_RGB, TARGET_POISON_COORD, TARGET_POISON_RGB, DANGER_HP_COORD, DANGER_HP_RGB
    global saved_v_bl, saved_v_sh, saved_v_blu, saved_v_f10, saved_v_f11
    global saved_buff_on, saved_buff_grid
    global saved_self_buff_on, saved_self_buff_hotbar, saved_self_buff_slot, saved_self_buff_sec, saved_self_buff_grid
    global BUFF_BAR_X1, BUFF_BAR_Y1, BUFF_BAR_X2, BUFF_BAR_Y2
    global saved_expire_start, saved_expire_days
    global saved_party_flags, saved_party_mode_flags
    global SELF_HP_ROI, SELF_HP_100_REF, DANGER_HP_ROI, DANGER_HP_100_REF
    global MNA_ROI, MNA_100_REF, mna_threshold, MNA_HOTBAR, MNA_SLOT
    global HEAL_HOTBAR, HEAL_SLOT, STRONG_HEAL_HOTBAR, STRONG_HEAL_SLOT
    global self_hp_threshold, danger_hp_threshold, attacker_hp_threshold
    global PARTY_ROIS, PARTY_HP_100_REF, PARTY_HP_THRESHOLDS, PARTY_USE_ROI
    global _stream_roi
    global saved_chk_self_heal, saved_chk_danger, saved_chk_strong_heal, saved_chk_self_strong_heal, saved_chk_attacker, saved_chk_mna, saved_chk_end_bert, saved_chk_wheel_heal
    global strong_heal_pct, self_strong_heal_pct, saved_win_w, saved_win_h
    
    text_value_keys = {"V_BL", "V_SH", "V_BLU", "V_F10", "V_F11",
                       "PARTY_FLAGS", "PARTY_MODE_FLAGS", "BUFF_ON"}
    saved_pwd = None
    saved_expire_start = ""
    saved_expire_days = "0"
    saved_buff_on = "0"
    saved_buff_grid = {}
    saved_self_buff_on = "0"
    saved_self_buff_hotbar = "F1"
    saved_self_buff_slot = "F5"
    saved_self_buff_sec = "1200"
    saved_self_buff_grid = {}
    saved_chk_self_heal = "1"
    saved_chk_danger = "1"
    saved_chk_strong_heal = "1"
    saved_chk_self_strong_heal = "1"
    saved_chk_attacker = "1"
    saved_chk_mna = "0"
    saved_chk_end_bert = "0"
    saved_chk_wheel_heal = "1"
    
    if os.path.exists(AUTH_FILE):
        ctypes.windll.kernel32.SetFileAttributesW(AUTH_FILE, 2)
        try:
            with open(AUTH_FILE, "r", encoding="utf-8") as f: lines = f.readlines()
            if not lines: return None
            saved_pwd = lines[0].strip() 
            text_key_map = {
                "V_BL": "saved_v_bl", "V_SH": "saved_v_sh", "V_BLU": "saved_v_blu",
                "V_F10": "saved_v_f10", "V_F11": "saved_v_f11",
                "PARTY_FLAGS": "saved_party_flags", "PARTY_MODE_FLAGS": "saved_party_mode_flags",
                "BUFF_ON": "saved_buff_on",
            }
            coord_map = {
                "MAIN_ATTACKER_X": (MAIN_ATTACKER_COORD, 0), "MAIN_ATTACKER_Y": (MAIN_ATTACKER_COORD, 1),
                "SELF_HP_X": (SELF_HP_COORD, 0), "SELF_HP_Y": (SELF_HP_COORD, 1),
                "SELF_HP_R": (SELF_HP_RGB, 0), "SELF_HP_G": (SELF_HP_RGB, 1), "SELF_HP_B": (SELF_HP_RGB, 2),
                "NOPARTY_X": (NOPARTY_HP_COORD, 0), "NOPARTY_Y": (NOPARTY_HP_COORD, 1),
                "NOPARTY_R": (NOPARTY_RGB, 0), "NOPARTY_G": (NOPARTY_RGB, 1), "NOPARTY_B": (NOPARTY_RGB, 2),
                "SELF_POISON_X": (SELF_POISON_COORD, 0), "SELF_POISON_Y": (SELF_POISON_COORD, 1),
                "SELF_POISON_R": (SELF_POISON_RGB, 0), "SELF_POISON_G": (SELF_POISON_RGB, 1), "SELF_POISON_B": (SELF_POISON_RGB, 2),
                "TARGET_POISON_X": (TARGET_POISON_COORD, 0), "TARGET_POISON_Y": (TARGET_POISON_COORD, 1),
                "TARGET_POISON_R": (TARGET_POISON_RGB, 0), "TARGET_POISON_G": (TARGET_POISON_RGB, 1), "TARGET_POISON_B": (TARGET_POISON_RGB, 2),
                "DANGER_HP_X": (DANGER_HP_COORD, 0), "DANGER_HP_Y": (DANGER_HP_COORD, 1),
                "DANGER_HP_R": (DANGER_HP_RGB, 0), "DANGER_HP_G": (DANGER_HP_RGB, 1), "DANGER_HP_B": (DANGER_HP_RGB, 2),
                "BUFF_BAR_X1": (None, 0), "BUFF_BAR_Y1": (None, 1), "BUFF_BAR_X2": (None, 2), "BUFF_BAR_Y2": (None, 3),
            }
            buff_bar_vals = [0, 0, 0, 0]
            self_roi_vals = [0, 0, 0, 0]
            danger_roi_vals = [0, 0, 0, 0]
            mna_roi_vals = [0, 0, 0, 0]
            stream_roi_vals = [0, 0, 0, 0]
            party_roi_vals = [[0,0,0,0] for _ in range(8)]
            party_name_roi_vals = [[0,0,0,0] for _ in range(8)]
            
            for line in lines[1:]:
                line = line.strip()
                if not line or "=" not in line: continue
                key, val = line.split('=', 1)
                val_str = val.strip()
                if key == "HW_MODE": globals()['HW_MODE'] = {"KMBox": "뚱박스", "아두이노": "뚱USB"}.get(val_str, val_str); continue
                if key == "WIN_W":
                    try: globals()['saved_win_w'] = max(165, min(420, int(val_str)))
                    except Exception: pass
                    continue
                if key == "WIN_H":
                    try: globals()['saved_win_h'] = max(180, min(900, int(val_str)))
                    except Exception: pass
                    continue
                if key == "KM_IP": globals()['KM_IP'] = val_str; continue
                if key == "KM_PORT": globals()['KM_PORT'] = val_str; continue
                if key == "KM_MAC": globals()['KM_MAC'] = val_str; continue
                if key in text_value_keys:
                    if key in text_key_map: globals()[text_key_map[key]] = val_str
                    continue
                if key.startswith("BUFF_") and key.count("_") >= 2:
                    # BUFF_F2_F5=1:1800
                    parts = key.split("_", 2)
                    if len(parts) == 3 and parts[1] in BUFF_HOTBARS and parts[2] in BUFF_SLOT_LABELS:
                        saved_buff_grid[f"{parts[1]}_{parts[2]}"] = val_str
                    continue
                if key == "SELF_HP_ROI_X1": self_roi_vals[0] = int(val_str) if val_str.lstrip('-').isdigit() else 0; continue
                if key == "SELF_HP_ROI_Y1": self_roi_vals[1] = int(val_str) if val_str.lstrip('-').isdigit() else 0; continue
                if key == "SELF_HP_ROI_X2": self_roi_vals[2] = int(val_str) if val_str.lstrip('-').isdigit() else 0; continue
                if key == "SELF_HP_ROI_Y2": self_roi_vals[3] = int(val_str) if val_str.lstrip('-').isdigit() else 0; continue
                if key == "SELF_HP_100_REF": SELF_HP_100_REF = int(val_str) if val_str.lstrip('-').isdigit() else None; continue
                if key == "DANGER_HP_ROI_X1": danger_roi_vals[0] = int(val_str) if val_str.lstrip('-').isdigit() else 0; continue
                if key == "DANGER_HP_ROI_Y1": danger_roi_vals[1] = int(val_str) if val_str.lstrip('-').isdigit() else 0; continue
                if key == "DANGER_HP_ROI_X2": danger_roi_vals[2] = int(val_str) if val_str.lstrip('-').isdigit() else 0; continue
                if key == "DANGER_HP_ROI_Y2": danger_roi_vals[3] = int(val_str) if val_str.lstrip('-').isdigit() else 0; continue
                if key == "DANGER_HP_100_REF": DANGER_HP_100_REF = int(val_str) if val_str.lstrip('-').isdigit() else None; continue
                if key == "SELF_HP_THRESHOLD": self_hp_threshold = int(val_str) if val_str.lstrip('-').isdigit() else 30; continue
                if key == "DANGER_HP_THRESHOLD": danger_hp_threshold = int(val_str) if val_str.lstrip('-').isdigit() else 20; continue
                if key == "ATTACKER_HP_THRESHOLD": attacker_hp_threshold = int(val_str) if val_str.lstrip('-').isdigit() else 85; continue
                if key == "MNA_ROI_X1": mna_roi_vals[0] = int(val_str) if val_str.lstrip('-').isdigit() else 0; continue
                if key == "MNA_ROI_Y1": mna_roi_vals[1] = int(val_str) if val_str.lstrip('-').isdigit() else 0; continue
                if key == "MNA_ROI_X2": mna_roi_vals[2] = int(val_str) if val_str.lstrip('-').isdigit() else 0; continue
                if key == "MNA_ROI_Y2": mna_roi_vals[3] = int(val_str) if val_str.lstrip('-').isdigit() else 0; continue
                if key == "STREAM_ROI_X1": stream_roi_vals[0] = int(val_str) if val_str.lstrip('-').isdigit() else 0; continue
                if key == "STREAM_ROI_Y1": stream_roi_vals[1] = int(val_str) if val_str.lstrip('-').isdigit() else 0; continue
                if key == "STREAM_ROI_X2": stream_roi_vals[2] = int(val_str) if val_str.lstrip('-').isdigit() else 0; continue
                if key == "STREAM_ROI_Y2": stream_roi_vals[3] = int(val_str) if val_str.lstrip('-').isdigit() else 0; continue
                if key == "MNA_100_REF": MNA_100_REF = int(val_str) if val_str.lstrip('-').isdigit() else None; continue
                if key == "MNA_THRESHOLD": mna_threshold = int(val_str) if val_str.lstrip('-').isdigit() else 30; continue
                if key == "MNA_HOTBAR": MNA_HOTBAR = val_str if val_str in BUFF_HOTBARS else "F2"; continue
                if key == "MNA_SLOT": MNA_SLOT = val_str if val_str in BUFF_SLOT_LABELS else "F8"; continue
                if key == "HEAL_HOTBAR": HEAL_HOTBAR = val_str if val_str in BUFF_HOTBARS else "F1"; continue
                if key == "HEAL_SLOT": HEAL_SLOT = val_str if val_str in BUFF_SLOT_LABELS else "F9"; continue
                if key == "STRONG_HEAL_HOTBAR": STRONG_HEAL_HOTBAR = val_str if val_str in BUFF_HOTBARS else "F1"; continue
                if key == "STRONG_HEAL_SLOT": STRONG_HEAL_SLOT = val_str if val_str in BUFF_SLOT_LABELS else "F7"; continue
                if key == "STRONG_HEAL_PCT": strong_heal_pct = int(val_str) if val_str.lstrip('-').isdigit() else 30; continue
                if key == "SELF_STRONG_HEAL_PCT": self_strong_heal_pct = int(val_str) if val_str.lstrip('-').isdigit() else 30; continue
                if key == "CHK_SELF_HEAL": saved_chk_self_heal = val_str; continue
                if key == "CHK_DANGER": saved_chk_danger = val_str; continue
                if key == "CHK_STRONG_HEAL": saved_chk_strong_heal = val_str; continue
                if key == "CHK_SELF_STRONG_HEAL": saved_chk_self_strong_heal = val_str; continue
                if key == "CHK_ATTACKER": saved_chk_attacker = val_str; continue
                if key == "CHK_MNA": saved_chk_mna = val_str; continue
                if key == "CHK_END_BERT": saved_chk_end_bert = val_str; continue
                if key == "CHK_WHEEL_HEAL": saved_chk_wheel_heal = val_str; continue
                if key == "SELF_BUFF_ON": saved_self_buff_on = val_str; continue
                if key == "SELF_BUFF_HOTBAR":
                    saved_self_buff_hotbar = val_str if val_str in BUFF_HOTBARS else "F1"; continue
                if key == "SELF_BUFF_SLOT":
                    saved_self_buff_slot = val_str if val_str in BUFF_SLOT_LABELS else "F5"; continue
                if key == "SELF_BUFF_SEC": saved_self_buff_sec = val_str; continue
                if key.startswith("SELF_BUFF_"):
                    sb_idx = key[10:]
                    if sb_idx.isdigit():
                        saved_self_buff_grid[sb_idx] = val_str
                        continue
                for pi in range(8):
                    if key == f"PARTY_ROI_P{pi+1}_X1": party_roi_vals[pi][0] = int(val_str) if val_str.lstrip('-').isdigit() else 0; break
                    if key == f"PARTY_ROI_P{pi+1}_Y1": party_roi_vals[pi][1] = int(val_str) if val_str.lstrip('-').isdigit() else 0; break
                    if key == f"PARTY_ROI_P{pi+1}_X2": party_roi_vals[pi][2] = int(val_str) if val_str.lstrip('-').isdigit() else 0; break
                    if key == f"PARTY_ROI_P{pi+1}_Y2": party_roi_vals[pi][3] = int(val_str) if val_str.lstrip('-').isdigit() else 0; break
                    if key == f"PARTY_NAME_ROI_P{pi+1}_X1": party_name_roi_vals[pi][0] = int(val_str) if val_str.lstrip('-').isdigit() else 0; break
                    if key == f"PARTY_NAME_ROI_P{pi+1}_Y1": party_name_roi_vals[pi][1] = int(val_str) if val_str.lstrip('-').isdigit() else 0; break
                    if key == f"PARTY_NAME_ROI_P{pi+1}_X2": party_name_roi_vals[pi][2] = int(val_str) if val_str.lstrip('-').isdigit() else 0; break
                    if key == f"PARTY_NAME_ROI_P{pi+1}_Y2": party_name_roi_vals[pi][3] = int(val_str) if val_str.lstrip('-').isdigit() else 0; break
                    if key == f"PARTY_HP_100_REF_P{pi+1}": PARTY_HP_100_REF[pi] = int(val_str) if val_str.lstrip('-').isdigit() else None; break
                    if key == f"PARTY_HP_THR_P{pi+1}": PARTY_HP_THRESHOLDS[pi] = int(val_str) if val_str.lstrip('-').isdigit() else 50; break
                    if key == f"PARTY_USE_ROI_P{pi+1}": PARTY_USE_ROI[pi] = bool(int(val_str)) if val_str in ('0','1') else True; break
                try: val = int(val_str)
                except: continue
                if key in coord_map:
                    if key.startswith("BUFF_BAR"):
                        idx = {"BUFF_BAR_X1": 0, "BUFF_BAR_Y1": 1, "BUFF_BAR_X2": 2, "BUFF_BAR_Y2": 3}[key]
                        buff_bar_vals[idx] = val
                    else:
                        target_list, target_idx = coord_map[key]
                        target_list[target_idx] = val
                else:
                    for i in range(8):
                        if key == f"P{i+1}_X": PARTY_COORDS[i][0] = val
                        elif key == f"P{i+1}_Y": PARTY_COORDS[i][1] = val
        except: pass
        if buff_bar_vals[0] != 0: BUFF_BAR_X1 = buff_bar_vals[0]
        if buff_bar_vals[1] != 0: BUFF_BAR_Y1 = buff_bar_vals[1]
        if buff_bar_vals[2] != 0: BUFF_BAR_X2 = buff_bar_vals[2]
        if buff_bar_vals[3] != 0: BUFF_BAR_Y2 = buff_bar_vals[3]
        if self_roi_vals[0] != 0 or self_roi_vals[2] != 0: SELF_HP_ROI = tuple(self_roi_vals)
        if danger_roi_vals[0] != 0 or danger_roi_vals[2] != 0: DANGER_HP_ROI = tuple(danger_roi_vals)
        if mna_roi_vals[0] != 0 or mna_roi_vals[2] != 0: MNA_ROI = tuple(mna_roi_vals)
        if stream_roi_vals[2] > stream_roi_vals[0] and stream_roi_vals[3] > stream_roi_vals[1]:
            _stream_roi = tuple(stream_roi_vals)
        for pi in range(8):
            if party_roi_vals[pi][0] != 0 or party_roi_vals[pi][2] != 0: PARTY_ROIS[pi] = tuple(party_roi_vals[pi])
            if party_name_roi_vals[pi][0] != 0 or party_name_roi_vals[pi][2] != 0: PARTY_NAME_ROIS[pi] = tuple(party_name_roi_vals[pi])
        globals()["saved_buff_on"] = saved_buff_on
        globals()["saved_buff_grid"] = saved_buff_grid
    migrate_legacy_buffs()
    migrate_legacy_self_buff()
    return saved_pwd

PRESET_FILE = os.path.join(_desktop_dir(), "healer_presets.json")
_DEFAULT_PRESET_NAMES = ("파티", "솔로", "노파티")

def _read_presets_file():
    try:
        if os.path.isfile(PRESET_FILE):
            with open(PRESET_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {"slots": {}, "last": ""}

def _write_presets_file(data):
    try:
        with open(PRESET_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def list_preset_names():
    data = _read_presets_file()
    names = list(data.get("slots", {}).keys())
    for n in _DEFAULT_PRESET_NAMES:
        if n not in names:
            names.append(n)
    return names

def capture_ui_preset():
    """ROI·% 제외 UI 스위치만."""
    d = {}
    if mode_var:
        d["mode"] = mode_var.get()
    if buff_mode_var:
        d["buff_mode"] = buff_mode_var.get()
    for key, var in [
        ("fix", chk_fix), ("follow", chk_follow), ("force_fix", chk_force_fix),
        ("poison", chk_poison), ("target_poison", chk_target_poison),
        ("party_poison", chk_party_poison), ("loot", chk_loot),
        ("end_bert", chk_end_bert), ("wheel_heal", chk_wheel_heal),
        ("buff_on", chk_buff_on),
        ("self_heal", chk_self_heal_sw), ("self_strong", chk_self_strong_heal),
        ("danger", chk_danger_sw), ("strong_heal", chk_strong_heal),
        ("attacker", chk_attacker_sw), ("mna", chk_mna),
    ]:
        if var is not None:
            try:
                d[key] = bool(var.get())
            except Exception:
                pass
    bg = {}
    for hb in BUFF_HOTBARS:
        for slot in BUFF_SLOT_LABELS:
            gk = buff_grid_key(hb, slot)
            if hb in _buff_cfg:
                for sl, cb, iv in _buff_cfg[hb]:
                    if sl == slot:
                        bg[gk] = bool(cb.get())
                        break
    d["buff_grid"] = bg
    sb = {}
    for idx, (cb_sb, hb_var, slot_var, sec_var) in enumerate(_self_buff_cfg, 1):
        try:
            sb[str(idx)] = bool(cb_sb.get())
        except Exception:
            pass
    d["self_buff"] = sb
    return d

def apply_ui_preset(d):
    if not d:
        return
    if mode_var and d.get("mode"):
        mode_var.set(d["mode"])
    if buff_mode_var and d.get("buff_mode"):
        buff_mode_var.set(d["buff_mode"])
    for key, var in [
        ("fix", chk_fix), ("follow", chk_follow), ("force_fix", chk_force_fix),
        ("poison", chk_poison), ("target_poison", chk_target_poison),
        ("party_poison", chk_party_poison), ("loot", chk_loot),
        ("end_bert", chk_end_bert), ("wheel_heal", chk_wheel_heal),
        ("buff_on", chk_buff_on),
        ("self_heal", chk_self_heal_sw), ("self_strong", chk_self_strong_heal),
        ("danger", chk_danger_sw), ("strong_heal", chk_strong_heal),
        ("attacker", chk_attacker_sw), ("mna", chk_mna),
    ]:
        if var is not None and key in d:
            try:
                var.set(bool(d[key]))
            except Exception:
                pass
    bg = d.get("buff_grid") or {}
    for hb in BUFF_HOTBARS:
        for slot in BUFF_SLOT_LABELS:
            gk = buff_grid_key(hb, slot)
            if gk not in bg or hb not in _buff_cfg:
                continue
            for sl, cb, iv in _buff_cfg[hb]:
                if sl == slot:
                    try:
                        cb.set(bool(bg[gk]))
                    except Exception:
                        pass
                    break
    sb = d.get("self_buff") or {}
    for idx, (cb_sb, hb_var, slot_var, sec_var) in enumerate(_self_buff_cfg, 1):
        if str(idx) in sb:
            try:
                cb_sb.set(bool(sb[str(idx)]))
            except Exception:
                pass

def save_named_preset(name):
    name = str(name or "").strip()
    if not name:
        return False
    data = _read_presets_file()
    slots = data.get("slots")
    if not isinstance(slots, dict):
        slots = {}
    slots[name] = capture_ui_preset()
    data["slots"] = slots
    data["last"] = name
    _write_presets_file(data)
    try:
        save_hidden_config(loaded_pwd if loaded_pwd else "")
    except Exception:
        pass
    try:
        log_event("💾 프리셋 저장: %s" % name)
    except Exception:
        pass
    return True

def load_named_preset(name):
    name = str(name or "").strip()
    if not name:
        return False
    data = _read_presets_file()
    slot = (data.get("slots") or {}).get(name)
    if not slot:
        try:
            log_event("⚠️ 프리셋 없음: %s" % name)
        except Exception:
            pass
        return False
    apply_ui_preset(slot)
    data["last"] = name
    _write_presets_file(data)
    try:
        save_hidden_config(loaded_pwd if loaded_pwd else "")
    except Exception:
        pass
    try:
        log_event("📂 프리셋 불러옴: %s" % name)
    except Exception:
        pass
    return True

def collect_status_chips():
    """끊김·미설정 등 이상 상태를 한 줄로."""
    chips = []
    if running:
        chips.append(("▶", "#a6e3a1"))
    else:
        chips.append(("■", "#6c7086"))
    usb_ok = bool(ser and getattr(ser, "is_open", False))
    chips.append(("USB" if usb_ok else "USB×", "#a6e3a1" if usb_ok else "#f38ba8"))
    hp_ok = SELF_HP_ROI[0] != 0 and SELF_HP_ROI[2] > SELF_HP_ROI[0]
    chips.append(("HP" if hp_ok else "HP?", "#a6e3a1" if hp_ok else "#f9e2af"))
    mode = mode_var.get() if mode_var else ""
    if mode in ("파티", "솔로(파티)"):
        party_ok = any(PARTY_ROIS[i][0] != 0 and PARTY_ROIS[i][2] > PARTY_ROIS[i][0] for i in range(8))
        chips.append(("P" if party_ok else "P?", "#a6e3a1" if party_ok else "#f9e2af"))
    elif mode == "노파티":
        np_ok = NOPARTY_HP_COORD[0] != 0
        chips.append(("NP" if np_ok else "NP?", "#a6e3a1" if np_ok else "#f9e2af"))
    try:
        atk_on = bool(chk_attacker_sw and chk_attacker_sw.get())
    except Exception:
        atk_on = False
    if atk_on:
        udp_ok = (time.time() - last_udp_time) < 5
        chips.append(("격수" if udp_ok else "격수×", "#a6e3a1" if udp_ok else "#f9e2af"))
    return chips

def save_hidden_config(pwd_to_save):
    try:
        def _buff_iv(hb, slot, default):
            if hb in _buff_cfg:
                for sl, _cb, iv in _buff_cfg[hb]:
                    if sl == slot:
                        return iv.get() if iv.get() else default
            return default

        cur_v_bl = _buff_iv("F2", "F5", saved_v_bl)
        cur_v_sh = _buff_iv("F2", "F6", saved_v_sh)
        cur_v_blu = _buff_iv("F2", "F11", saved_v_blu)
        cur_v_f10 = _buff_iv("F1", "F10", saved_v_f10)
        cur_v_f11 = _buff_iv("F1", "F11", saved_v_f11)
        cur_km_ip = ent_km_ip.get().strip() if ('ent_km_ip' in globals() and ent_km_ip and ent_km_ip.get().strip()) else KM_IP
        cur_km_port = ent_km_port.get().strip() if ('ent_km_port' in globals() and ent_km_port and ent_km_port.get().strip()) else KM_PORT
        cur_km_mac = ent_km_mac.get().strip() if ('ent_km_mac' in globals() and ent_km_mac and ent_km_mac.get().strip()) else KM_MAC
        cur_hw = hw_var.get() if ('hw_var' in globals() and hw_var) else HW_MODE
        globals()['KM_IP'] = cur_km_ip; globals()['KM_PORT'] = cur_km_port; globals()['KM_MAC'] = cur_km_mac; globals()['HW_MODE'] = cur_hw
        tmp_auth_file = AUTH_FILE + ".tmp"
        if os.path.exists(AUTH_FILE): ctypes.windll.kernel32.SetFileAttributesW(AUTH_FILE, 128)

        with open(AUTH_FILE, "w", encoding="utf-8") as f:
            f.write(f"{pwd_to_save}\n")
            for key, value in [
                ("MAIN_ATTACKER_X", MAIN_ATTACKER_COORD[0]), ("MAIN_ATTACKER_Y", MAIN_ATTACKER_COORD[1]),
                # Self coord removed
                ("SELF_HP_R", SELF_HP_RGB[0]), ("SELF_HP_G", SELF_HP_RGB[1]), ("SELF_HP_B", SELF_HP_RGB[2]),
                ("NOPARTY_X", NOPARTY_HP_COORD[0]), ("NOPARTY_Y", NOPARTY_HP_COORD[1]),
                ("NOPARTY_R", NOPARTY_RGB[0]), ("NOPARTY_G", NOPARTY_RGB[1]), ("NOPARTY_B", NOPARTY_RGB[2]),
                ("SELF_POISON_X", SELF_POISON_COORD[0]), ("SELF_POISON_Y", SELF_POISON_COORD[1]),
                ("SELF_POISON_R", SELF_POISON_RGB[0]), ("SELF_POISON_G", SELF_POISON_RGB[1]), ("SELF_POISON_B", SELF_POISON_RGB[2]),
                ("TARGET_POISON_X", TARGET_POISON_COORD[0]), ("TARGET_POISON_Y", TARGET_POISON_COORD[1]),
                ("TARGET_POISON_R", TARGET_POISON_RGB[0]), ("TARGET_POISON_G", TARGET_POISON_RGB[1]), ("TARGET_POISON_B", TARGET_POISON_RGB[2]),
                # Danger coord removed
                ("DANGER_HP_R", DANGER_HP_RGB[0]), ("DANGER_HP_G", DANGER_HP_RGB[1]), ("DANGER_HP_B", DANGER_HP_RGB[2]),
            ]: f.write(f"{key}={value}\n")
            # Old PARTY_COORDS save removed
            for key, value in [("BUFF_BAR_X1", BUFF_BAR_X1), ("BUFF_BAR_Y1", BUFF_BAR_Y1), ("BUFF_BAR_X2", BUFF_BAR_X2), ("BUFF_BAR_Y2", BUFF_BAR_Y2)]:
                f.write(f"{key}={value}\n")
            for key, value in [("V_BL", cur_v_bl), ("V_SH", cur_v_sh), ("V_BLU", cur_v_blu), ("V_F10", cur_v_f10), ("V_F11", cur_v_f11)]:
                f.write(f"{key}={value}\n")
            # 버프 자동 — OFF일 때 saved_buff_on으로 폴백하면 꺼도 계속 1로 저장되던 버그 수정
            if chk_buff_on is not None:
                try:
                    cur_buff_on = "1" if chk_buff_on.get() else "0"
                except Exception:
                    cur_buff_on = "1" if str(saved_buff_on).strip() in ("1", "true", "True") else "0"
            else:
                cur_buff_on = "1" if str(saved_buff_on).strip() in ("1", "true", "True") else "0"
            globals()["saved_buff_on"] = cur_buff_on
            f.write(f"BUFF_ON={cur_buff_on}\n")
            for hb in BUFF_HOTBARS:
                for slot in BUFF_SLOT_LABELS:
                    gk = buff_grid_key(hb, slot)
                    on_s, sec_s = "0", str(BASE_BUFF_INTERVAL)
                    if hb in _buff_cfg:
                        for sl, cb, iv in _buff_cfg[hb]:
                            if sl == slot:
                                on_s = "1" if cb.get() else "0"
                                sec_s = _buff_sec_str(iv, gk)
                                break
                    elif gk in saved_buff_grid:
                        parts = saved_buff_grid[gk].split(":", 1)
                        if len(parts) == 2:
                            on_s, sec_s = parts[0], parts[1]
                    saved_buff_grid[gk] = f"{on_s}:{sec_s}"
                    f.write(f"BUFF_{hb}_{slot}={on_s}:{sec_s}\n")
            f.write(f"HW_MODE={cur_hw}\nKM_IP={cur_km_ip}\nKM_PORT={cur_km_port}\nKM_MAC={cur_km_mac}\n")
            f.write(f"WIN_W={saved_win_w}\n")
            f.write(f"PARTY_FLAGS={saved_party_flags}\nPARTY_MODE_FLAGS={saved_party_mode_flags}\n")
            f.write(f"SELF_HP_ROI_X1={SELF_HP_ROI[0]}\nSELF_HP_ROI_Y1={SELF_HP_ROI[1]}\nSELF_HP_ROI_X2={SELF_HP_ROI[2]}\nSELF_HP_ROI_Y2={SELF_HP_ROI[3]}\n")
            if SELF_HP_100_REF is not None: f.write(f"SELF_HP_100_REF={SELF_HP_100_REF}\n")
            f.write(f"DANGER_HP_ROI_X1={DANGER_HP_ROI[0]}\nDANGER_HP_ROI_Y1={DANGER_HP_ROI[1]}\nDANGER_HP_ROI_X2={DANGER_HP_ROI[2]}\nDANGER_HP_ROI_Y2={DANGER_HP_ROI[3]}\n")
            if DANGER_HP_100_REF is not None: f.write(f"DANGER_HP_100_REF={DANGER_HP_100_REF}\n")
            f.write(f"SELF_HP_THRESHOLD={self_hp_threshold}\nDANGER_HP_THRESHOLD={danger_hp_threshold}\nATTACKER_HP_THRESHOLD={int(attacker_hp_threshold)}\n")
            f.write(f"MNA_ROI_X1={MNA_ROI[0]}\nMNA_ROI_Y1={MNA_ROI[1]}\nMNA_ROI_X2={MNA_ROI[2]}\nMNA_ROI_Y2={MNA_ROI[3]}\n")
            f.write(f"STREAM_ROI_X1={_stream_roi[0]}\nSTREAM_ROI_Y1={_stream_roi[1]}\nSTREAM_ROI_X2={_stream_roi[2]}\nSTREAM_ROI_Y2={_stream_roi[3]}\n")
            if MNA_100_REF is not None: f.write(f"MNA_100_REF={MNA_100_REF}\n")
            f.write(f"MNA_THRESHOLD={mna_threshold}\n")
            cur_mna_hb = mna_hotbar_var.get() if ('mna_hotbar_var' in globals() and mna_hotbar_var) else MNA_HOTBAR
            cur_mna_slot = mna_slot_var.get() if ('mna_slot_var' in globals() and mna_slot_var) else MNA_SLOT
            f.write(f"MNA_HOTBAR={cur_mna_hb}\nMNA_SLOT={cur_mna_slot}\n")
            cur_heal_hb = heal_hotbar_var.get() if ('heal_hotbar_var' in globals() and heal_hotbar_var) else HEAL_HOTBAR
            cur_heal_slot = heal_slot_var.get() if ('heal_slot_var' in globals() and heal_slot_var) else HEAL_SLOT
            cur_str_hb = strong_heal_hotbar_var.get() if ('strong_heal_hotbar_var' in globals() and strong_heal_hotbar_var) else STRONG_HEAL_HOTBAR
            cur_str_slot = strong_heal_slot_var.get() if ('strong_heal_slot_var' in globals() and strong_heal_slot_var) else STRONG_HEAL_SLOT
            f.write(f"HEAL_HOTBAR={cur_heal_hb}\nHEAL_SLOT={cur_heal_slot}\n")
            f.write(f"STRONG_HEAL_HOTBAR={cur_str_hb}\nSTRONG_HEAL_SLOT={cur_str_slot}\n")
            f.write(f"STRONG_HEAL_PCT={strong_heal_pct}\nSELF_STRONG_HEAL_PCT={self_strong_heal_pct}\n")
            def _sw01(var, fallback):
                if var is not None:
                    try: return "1" if var.get() else "0"
                    except Exception: pass
                return "1" if str(fallback).strip() in ("1", "true", "True") else "0"
            # 힐·물약 스위치 — 껏다 켜도 유지
            cur_self = _sw01(chk_self_heal_sw if 'chk_self_heal_sw' in globals() else None, saved_chk_self_heal)
            cur_danger = _sw01(chk_danger_sw if 'chk_danger_sw' in globals() else None, saved_chk_danger)
            cur_strong = _sw01(chk_strong_heal, saved_chk_strong_heal)
            cur_self_strong = _sw01(chk_self_strong_heal if 'chk_self_strong_heal' in globals() else None, saved_chk_self_strong_heal)
            cur_atk = _sw01(chk_attacker_sw if 'chk_attacker_sw' in globals() else None, saved_chk_attacker)
            cur_mna = _sw01(chk_mna, saved_chk_mna)
            cur_end_bert = _sw01(chk_end_bert if 'chk_end_bert' in globals() else None, saved_chk_end_bert)
            cur_wheel_heal = _sw01(chk_wheel_heal if 'chk_wheel_heal' in globals() else None, saved_chk_wheel_heal)
            globals()['saved_chk_self_heal'] = cur_self
            globals()['saved_chk_danger'] = cur_danger
            globals()['saved_chk_strong_heal'] = cur_strong
            globals()['saved_chk_self_strong_heal'] = cur_self_strong
            globals()['saved_chk_attacker'] = cur_atk
            globals()['saved_chk_mna'] = cur_mna
            globals()['saved_chk_end_bert'] = cur_end_bert
            globals()['saved_chk_wheel_heal'] = cur_wheel_heal
            f.write(f"CHK_SELF_HEAL={cur_self}\nCHK_DANGER={cur_danger}\nCHK_STRONG_HEAL={cur_strong}\nCHK_SELF_STRONG_HEAL={cur_self_strong}\nCHK_ATTACKER={cur_atk}\nCHK_MNA={cur_mna}\nCHK_END_BERT={cur_end_bert}\nCHK_WHEEL_HEAL={cur_wheel_heal}\n")
            for idx, (cb_sb, hb_var, slot_var, sec_var) in enumerate(_self_buff_cfg, 1):
                on_sb = "1" if cb_sb.get() else "0"
                hb_sb = hb_var.get() if hb_var.get() in BUFF_HOTBARS else "F1"
                slot_sb = slot_var.get() if slot_var.get() in BUFF_SLOT_LABELS else "F5"
                sec_sb = _self_buff_sec_str(sec_var, idx)
                saved_self_buff_grid[str(idx)] = f"{on_sb}:{hb_sb}:{slot_sb}:{sec_sb}"
                f.write(f"SELF_BUFF_{idx}={on_sb}:{hb_sb}:{slot_sb}:{sec_sb}\n")
            if _self_buff_cfg:
                cb1, hb1, slot1, sec1 = _self_buff_cfg[0]
                cur_self_buff = "1" if cb1.get() else "0"
                cur_sb_hb = hb1.get()
                cur_sb_slot = slot1.get()
                cur_sb_sec = sec1.get()
                globals()['saved_self_buff_on'] = cur_self_buff
                globals()['saved_self_buff_hotbar'] = cur_sb_hb
                globals()['saved_self_buff_slot'] = cur_sb_slot
                globals()['saved_self_buff_sec'] = cur_sb_sec
                f.write(f"SELF_BUFF_ON={cur_self_buff}\nSELF_BUFF_HOTBAR={cur_sb_hb}\nSELF_BUFF_SLOT={cur_sb_slot}\nSELF_BUFF_SEC={cur_sb_sec}\n")
            for pi in range(8):
                r = PARTY_ROIS[pi]
                f.write(f"PARTY_ROI_P{pi+1}_X1={r[0]}\nPARTY_ROI_P{pi+1}_Y1={r[1]}\nPARTY_ROI_P{pi+1}_X2={r[2]}\nPARTY_ROI_P{pi+1}_Y2={r[3]}\n")
                nr = PARTY_NAME_ROIS[pi]
                f.write(f"PARTY_NAME_ROI_P{pi+1}_X1={nr[0]}\nPARTY_NAME_ROI_P{pi+1}_Y1={nr[1]}\nPARTY_NAME_ROI_P{pi+1}_X2={nr[2]}\nPARTY_NAME_ROI_P{pi+1}_Y2={nr[3]}\n")
                if PARTY_HP_100_REF[pi] is not None: f.write(f"PARTY_HP_100_REF_P{pi+1}={PARTY_HP_100_REF[pi]}\n")
                f.write(f"PARTY_HP_THR_P{pi+1}={PARTY_HP_THRESHOLDS[pi]}\nPARTY_USE_ROI_P{pi+1}={1 if PARTY_USE_ROI[pi] else 0}\n")
        ctypes.windll.kernel32.SetFileAttributesW(AUTH_FILE, 2)
        try:
            import base64, zlib
            src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.path.basename(__file__))
            dst_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.txt")
            with open(src_path, "r", encoding="utf-8") as src: source = src.read()
            compressed = zlib.compress(source.encode("utf-8"))
            b64 = base64.b64encode(compressed).decode("utf-8")
            with open(dst_path, "w", encoding="utf-8") as dst: dst.write("".join(chr(ord(c) + 1) for c in b64))
        except: pass
    except: pass

loaded_pwd = load_hidden_config()

try:
    parts = saved_party_flags.split(',')
    if len(parts) == 8: selected_party_flags = [int(p.strip()) for p in parts]
    else: selected_party_flags = [0, 1, 0, 0, 0, 0, 0, 0]
except: selected_party_flags = [0, 1, 0, 0, 0, 0, 0, 0]

try:
    parts = saved_party_mode_flags.split(',')
    if len(parts) == 8: party_mode_flags = [int(p.strip()) for p in parts]
    else: party_mode_flags = [1,1,1,1,1,1,1,1]
except: party_mode_flags = [1,1,1,1,1,1,1,1]

def get_pixel_color_native(x, y):
    hdc = ctypes.windll.user32.GetDC(0)
    color = ctypes.windll.gdi32.GetPixel(hdc, x, y)
    ctypes.windll.user32.ReleaseDC(0, hdc)
    if color == -1: return 0, 0, 0
    return color & 0xff, (color >> 8) & 0xff, (color >> 16) & 0xff

def ask_admin_pw():
    open_admin_panel()

def open_admin_panel():
    try:
        _open_admin_panel_impl()
    except Exception as e:
        import traceback
        ctypes.windll.user32.MessageBoxW(0, f"제어판 오류:\n{e}", "오류", 0x10)

def _open_admin_panel_impl():
    try:
        import imgui_ui
        if imgui_ui.open_admin():
            return
    except Exception:
        pass
    ctypes.windll.user32.MessageBoxW(0, "제어판을 열 수 없습니다.", "오류", 0x10)

def open_guide_panel():
    try:
        import imgui_ui
        if imgui_ui.open_guide():
            return
    except Exception:
        pass
    guide = ctk.CTkToplevel(root)
    guide.title("📖 뚱힐러 사용 가이드")
    w, h = 460, 680
    sw = guide.winfo_screenwidth(); sh = guide.winfo_screenheight()
    guide.geometry(f"{w}x{h}+{int((sw-w)/2)}+{int((sh-h)/2)}")
    guide.attributes("-topmost", True); guide.focus_force()
    guide.configure(fg_color="#181825")

    hdr = ctk.CTkFrame(guide, fg_color="#1e1e2e", corner_radius=0)
    hdr.pack(fill="x", padx=0, pady=0)
    ctk.CTkLabel(hdr, text="📖 뚱힐러 가이드", text_color="#f9e2af",
                 font=("Malgun Gothic", 15, "bold")).pack(pady=(10, 2))
    ctk.CTkLabel(hdr, text="⚠️ 사용 책임은 사용자에게 있습니다 · 항상 후원 감사합니다 ❤️",
                 text_color="#a6adc8", font=("Malgun Gothic", 9)).pack(pady=(0, 8))

    sf = ctk.CTkScrollableFrame(guide, fg_color="#181825", corner_radius=0)
    sf.pack(fill="both", expand=True, padx=8, pady=(0, 4))

    def add_sep():
        ctk.CTkFrame(sf, fg_color="#313244", height=1).pack(fill="x", padx=4, pady=10)
    def add_t(txt, color="#89b4fa"):
        ctk.CTkLabel(sf, text=txt, text_color=color, font=("Malgun Gothic", 12, "bold")).pack(anchor="w", padx=6, pady=(4, 6))
    def add_d(key, desc):
        row = ctk.CTkFrame(sf, fg_color="#1e1e2e", corner_radius=8)
        row.pack(fill="x", padx=4, pady=3)
        ctk.CTkLabel(row, text=key, text_color="#f9e2af", font=("Malgun Gothic", 10, "bold"),
                     width=78, anchor="w").pack(side="left", padx=(10, 4), pady=7)
        ctk.CTkLabel(row, text=desc, text_color="#cdd6f4", font=("Malgun Gothic", 10),
                     justify="left", wraplength=300).pack(side="left", padx=(0, 10), pady=7)
    def add_w(txt):
        ctk.CTkLabel(sf, text="• " + txt, text_color="#bac2de", font=("Malgun Gothic", 10),
                     justify="left", wraplength=380).pack(anchor="w", padx=14, pady=2)

    add_t("🚀 시작하기", "#a6e3a1")
    add_w("리니지 클래식 — 휠고정 무조건 하세요 (게임 설정에서 마우스 휠 고정)")
    add_w("Insert 로 시작 · 다시 누르면 정지 (시작할 때 자동클릭은 안 켜짐)")
    add_w("시작 전 제어판에서 파티원 HP바·100% 기준 저장 필수")
    add_sep()

    add_t("⌨️ 단축키")
    add_d("Insert", "시작 / 정지")
    add_d("Home", "따라가기 ON ↔ 전부 끄기 (사냥 중에만)")
    add_d("PageUp", "강제고정 — 시프트 제자리공격 ON/OFF (격수도 동일)")
    add_d("Delete", "창 숨기기 / 다시 보이기")
    add_d("F4", "주변 줍기 켜기 / 끄기")
    add_sep()

    add_t("🖱️ Home — 따라가기 / 고정", "#cba6f7")
    add_d("1번 누름", "따라가기 ON — 몹 따라가며 자동 공격")
    add_d("2번 누름", "전부 끄기 — 클릭·시프트 없음 (F1~F3 단축창 이동 가능)")
    add_d("다시 Home", "따라가기로 복귀")
    add_w("옵션 칸의 [따라가기(Home)]·[고정(Home)] 스위치로도 같은 동작")
    add_w("격수 모니터 [따라가기]·[고정] 버튼도 동일")
    add_w("[강제고정(PageUp)] — 시프트로 제자리 공격. 켜 두면 F1~F3 단축창이 안 바뀜")
    add_sep()

    add_t("💚 힐 · 휠힐 설정", "#94e2d5")
    add_w("게임 단축창: 힐·물약 섹션에서 F1~F3 + F5~F12 슬롯 지정 (기본 일반 F9 / 상위 F7)")
    add_w("WDT4 펌이면 Insert 연결 시 휠힐 자동 ON (별도 펌업 불필요)")
    add_w("최신 펌웨어: 일반 파티힐·격수힐 → 가운데 휠클릭으로 대상 지정 (항상 켜짐)")
    add_w("상위힐은 휠이 아니라 좌클릭으로 대상 지정 — 슬롯은 힐·물약에서 변경")
    add_w("버프·해독·줍기는 항상 좌클릭")
    add_sep()

    add_t("🛡️ 옵션 설명")
    add_d("버프", "▶ 버프 펼침 → 단축창(F1~F3) · 슬롯(F5~F12) 체크·초 설정")
    add_d("자힐", "평소 힐만 · 50% 이하 물약+힐 · 자힐 상위% 이하면 F7")
    add_d("상위힐", "파티·격수용 % (자힐 상위%는 자힐 슬라이더 옆)")
    add_d("독 해독", "본인 독 → F2단축창 엔줄복용(F9) 자동")
    add_d("격수 해독", "격수 독 → F2단축창 큐어포이즌(F10) 자동")
    add_d("파티 해독", "파티원 HP바 초록(독) → 큐어포이즌+대상 클릭")
    add_d("파랭이", "엠통% 이하 시 10분마다 파란물약")
    add_d("격수 HP", "격수 모니터 연결 시 체력% 표시")
    add_sep()

    add_t("📡 쫄화면 송출 (격수 ↔ 쫄)", "#89b4fa")
    add_w("쫄 PC 제어판 → [📡 송출 영역 드래그]로 게임 화면만 지정 (미설정이면 주 모니터 전체)")
    add_w("격수 PC: IP 맞춘 뒤 [📡 전송 ON] → [📺 쫄화면] 창 열기")
    add_w("쫄화면에서 Alt 누른 채 마우스 이동·클릭 → 쫄 PC 마우스 원격 조종")
    add_w("[📡 전송 OFF] 또는 격수 종료 시 송출 정지")
    add_sep()

    add_t("🚨 주의사항")
    add_w("파티창 UI를 켜 두지 않아도 파티힐 됩니다 (제어판 HP바 ROI만 맞으면 됨)")
    add_w("노파티: 배경 오탐 방지용 아이콘 ROI 설정 권장")
    add_w("채팅 중: 힐·귀환은 계속, 버프·줍기·해독만 잠깐 쉼")
    add_sep()

    add_t("🕹️ 뚱USB", "#f9e2af")
    add_w("상단 [장치] → 뚱USB 선택")
    add_w("USB 꽂으면 COM 포트 자동 표시 (대기 중에도 확인 가능)")
    add_w("Insert 로 시작 · 정지할 때도 Insert")
    add_w("[펌업] — 옛 펌일 때만 (이미 WDT4면 불필요)")
    add_w("Insert 연결 시 펌 자동 확인 → WDT4면 휠힐 바로 사용")
    add_w("[확인] — 펌 버전 수동 조회")
    add_sep()

    add_t("🕹️ 뚱박스 — 처음 세팅", "#cba6f7")
    add_w("① [장치] → 뚱박스 선택 → IP·포트·UUID 칸이 나타남")
    add_w("② [드라이버] — 랜드라이버 설치 (처음 1회, 재부팅 권장)")
    add_w("③ [IP설정] — PC 랜 IP 맞추기 (박스와 같은 대역, 예: 192.168.2.x)")
    add_w("   · 네트워크 어댑터 열기 → USB 이더넷 → IPv4 수동 입력")
    add_w("   · Wi-Fi/인터넷 어댑터는 건드리지 않기")
    add_w("④ [설정도구] — 중국어 프로그램 + 한글 통역 창")
    add_w("   · 连接盒子(연결) 클릭 · 박스 LCD의 IP/포트/UUID 입력")
    add_w("   · 禁用Bypass 체크 (Bypass 끄기) ← 필수")
    add_w("⑤ 뚱힐러 폼에 IP·포트·UUID 입력 → [설정저장]")
    add_w("⑥ Insert 로 연결 · 사냥 중 박스 LCD에 로고 표시")
    add_w("※ 연결 안 되면: ping 테스트 · 드라이버 · Bypass · IP 대역 재확인")

    ctk.CTkButton(guide, text="닫기", command=guide.destroy, fg_color="#313244",
                  hover_color="#45475a", text_color="#ffffff", font=("Malgun Gothic", 12, "bold"),
                  height=32).pack(pady=10)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

authenticated = False

if loaded_pwd:
    # 🔒 실시간 구글시트 검증 (마스터키 없음, HWID 강제)
    cs_result, cs_info, cs_start = check_google_sheet(loaded_pwd)
    if cs_result == "PASS":
        # 만료일 검사 (절대날짜/일수 공통 판정 — _is_code_expired, 5분 재검증과 동일 기준)
        if _is_code_expired(cs_info, cs_start):
            ctypes.windll.user32.MessageBoxW(0, "사용 기간이 만료된 코드입니다.", "만료", 0x10)
            sys.exit()
        _sync_expire_cache(cs_info, cs_start)
        authenticated = True
    elif cs_result == "REGISTER":
        # HWID 자동 등록 시도
        if GAS_API_URL:
            try:
                reg_data = json.dumps({"code": loaded_pwd, "hwid": MY_HWID}).encode()
                reg_req = urllib.request.Request(GAS_API_URL, data=reg_data, headers={"Content-Type": "application/json"})
                reg_resp = json.loads(urllib.request.urlopen(reg_req, timeout=8).read())
                if reg_resp.get("result") == "OK":
                    _r, _i, _s = check_google_sheet(loaded_pwd)
                    if _r not in ("ERROR",):
                        _sync_expire_cache(_i, _s)
                    authenticated = True
                else:
                    ctypes.windll.user32.MessageBoxW(0, "HWID 등록 실패. 관리자에게 문의하세요.", "등록 오류", 0x10)
                    sys.exit()
            except:
                ctypes.windll.user32.MessageBoxW(0, "인증 서버 연결 실패.", "네트워크 오류", 0x10)
                sys.exit()
        else:
            authenticated = True
    elif cs_result == "ALREADY_IN_USE":
        ctypes.windll.user32.MessageBoxW(0, "다른 PC에서 사용중인 코드입니다.", "HWID 불일치", 0x10)
        sys.exit()
    elif cs_result == "NOT_FOUND":
        if os.path.exists(AUTH_FILE):
            ctypes.windll.kernel32.SetFileAttributesW(AUTH_FILE, 128)
            try: os.remove(AUTH_FILE)
            except: pass
        authenticated = False
    elif cs_result == "ERROR":
        ctypes.windll.user32.MessageBoxW(0, "인증 서버 연결 실패. 인터넷을 확인하세요.", "네트워크 오류", 0x10)
        sys.exit()
    else:
        authenticated = False

else:
    try:
        import imgui_ui
        imgui_ui.run_auth(globals())
    except Exception:
        auth_root = ctk.CTk()
        auth_root.title("뚱시스템 VIP 인증")
        sw = auth_root.winfo_screenwidth(); sh = auth_root.winfo_screenheight()
        aw, ah = 280, 280
        auth_root.geometry(f"{aw}x{ah}+{int((sw-aw)/2)}+{int((sh-520)/2)}")
        auth_root.attributes("-topmost", True)
        auth_root.configure(fg_color='#1e1e2e')
        def check_login(event=None):
            global authenticated, SERIAL_PORT, loaded_pwd
            pwd = pw_entry.get().strip()
            user_com = com_entry.get().strip().upper()
            if not pwd: return
            if user_com: SERIAL_PORT = user_com
            server_result, server_info, server_start = check_google_sheet(pwd)
            if server_result == "PASS":
                if server_info == "0":
                    err_lbl.configure(text="만료된 코드입니다")
                    return
                _sync_expire_cache(server_info, server_start)
                save_hidden_config(pwd); loaded_pwd = pwd; authenticated = True
                auth_root.destroy()
            elif server_result == "REGISTER":
                global GAS_API_URL
                if GAS_API_URL:
                    try:
                        reg_data = json.dumps({"code": pwd, "hwid": MY_HWID}).encode()
                        reg_req = urllib.request.Request(GAS_API_URL, data=reg_data, headers={"Content-Type": "application/json"})
                        reg_resp = json.loads(urllib.request.urlopen(reg_req, timeout=8).read())
                        if reg_resp.get("result") == "OK":
                            _r, _i, _s = check_google_sheet(pwd)
                            if _r not in ("ERROR",):
                                _sync_expire_cache(_i, _s)
                            save_hidden_config(pwd); loaded_pwd = pwd; authenticated = True
                            auth_root.destroy()
                        else:
                            err_lbl.configure(text="이미 다른 PC에서 등록된 코드입니다")
                    except:
                        err_lbl.configure(text="인증 서버 연결 실패")
                else:
                    err_lbl.configure(text="API 설정이 필요합니다")
            elif server_result == "ALREADY_IN_USE":
                err_lbl.configure(text="다른 PC에서 사용 중인 코드입니다")
            elif server_result == "NOT_FOUND":
                err_lbl.configure(text="등록되지 않은 코드입니다")
            else:
                err_lbl.configure(text="인증에 실패했습니다")
        ctk.CTkLabel(auth_root, text="🔑 인증 코드를 입력하세요", text_color='#cba6f7', font=('Malgun Gothic', 13, 'bold')).pack(pady=(20, 5))
        pw_entry = ctk.CTkEntry(auth_root, show="●", font=('Malgun Gothic', 12), justify='center', fg_color='#313244', text_color='#cdd6f4', width=180, height=28)
        pw_entry.pack(pady=5); pw_entry.bind('<Return>', check_login)
        ctk.CTkLabel(auth_root, text="🔌 포트 번호", text_color='#a6adc8', font=('Malgun Gothic', 10)).pack(pady=(10, 2))
        com_entry = ctk.CTkEntry(auth_root, font=('Malgun Gothic', 11), justify='center', fg_color='#313244', text_color='#a6e3a1', width=120, height=28)
        com_entry.pack(pady=5); com_entry.insert(0, SERIAL_PORT)
        err_lbl = ctk.CTkLabel(auth_root, text="", text_color="#ef4444", font=("Malgun Gothic", 9))
        err_lbl.pack(pady=(0, 5))
        ctk.CTkLabel(auth_root, text=f"PC ID: {MY_HWID}", text_color="#6c7086", font=("Consolas", 9)).pack(pady=(0, 4))
        ctk.CTkButton(auth_root, text="시스템 잠금 해제", command=check_login, fg_color='#89b4fa', hover_color="#74c7ec", text_color='#1e1e2e', font=('Malgun Gothic', 11, 'bold'), width=180, height=30).pack(pady=15)
        auth_root.mainloop()

if not authenticated:
    sys.exit()

import mss as _mss
import threading as _threading

class MSSCamera:
    """스레드 안전 mss 캡처.
    - 스레드마다 별도 MSS 인스턴스(thread-local) → mss는 스레드 안전하지 않으므로 필수.
    - grab 일시 오류 시 마지막 정상 프레임 반환 → None/검은프레임 오작동 방지.
    - dxcam 미사용 → Desktop Duplication 네이티브 크래시 원천 제거."""
    def __init__(self):
        self._local = _threading.local()
        self._monitor = None
        self._last_frame = None
        self._flock = Lock()
        try:
            _s = _mss.MSS()
            self._monitor = _s.monitors[1]
            _s.close()
        except Exception:
            self._monitor = None
    def _get_sct(self):
        sct = getattr(self._local, "sct", None)
        if sct is None:
            sct = _mss.MSS()
            self._local.sct = sct
            if self._monitor is None:
                self._monitor = sct.monitors[1]
        return sct
    def start(self, **kw): pass
    def stop(self): pass
    def release(self):
        sct = getattr(self._local, "sct", None)
        if sct is not None:
            try: sct.close()
            except Exception: pass
            self._local.sct = None
    def get_latest_frame(self):
        try:
            sct = self._get_sct()
            img = sct.grab(self._monitor)
            arr = np.array(img, dtype=np.uint8)[:, :, :3][:, :, ::-1]
            with self._flock:
                self._last_frame = arr
            return arr
        except Exception:
            with self._flock:
                return self._last_frame
    def grab_roi(self, roi):
        """ROI 좌표만 직접 캡처(전체화면 프레임을 잘라쓰지 않음) — 미리보기(refresh_preview)와
        완전히 동일한 방식. 모니터 오프셋 등으로 전체화면 프레임 슬라이싱이 실제 화면과
        어긋날 가능성을 원천적으로 없애기 위해, 절대좌표로 그 부분만 바로 캡처한다."""
        try:
            x1, y1, x2, y2 = roi
            sct = self._get_sct()
            img = sct.grab({"left": x1, "top": y1, "width": max(x2 - x1, 1), "height": max(y2 - y1, 1)})
            return np.array(img, dtype=np.uint8)[:, :, :3][:, :, ::-1]
        except Exception:
            return None

class HybridCamera:
    """dxcam(GPU/DXGI Desktop Duplication)을 우선 사용 — 게임의 실제 렌더링을 정확히 캡처.
    mss(GDI/BitBlt)는 일부 렌더링 방식에서 실제 화면과 다른 내용을 보여줄 수 있어서(예:
    전투로 실제 피가 빠져도 인식이 안 되던 문제) dxcam을 기본으로 되돌림.
    단, dxcam은 간헐적으로 오류/크래시가 날 수 있으므로 모든 호출을 try/except로 감싸고,
    연속 실패시 자동으로 mss로 전환(그리고 잠시 후 dxcam 재시도)해서 프로그램이 죽지 않게 함."""
    def __init__(self):
        self._mss = MSSCamera()
        self._dx = None
        self._dx_ok = False
        self._fail_streak = 0
        self._last_retry = 0.0
        self._lock = Lock()
        self._init_dxcam()
    def _init_dxcam(self):
        if dxcam is None:
            self._dx_ok = False
            return
        try:
            with self._lock:
                if self._dx is not None:
                    try: self._dx.release()
                    except Exception: pass
                self._dx = dxcam.create(output_color="RGB")
                self._dx.start(target_fps=60)
                self._dx_ok = True
                self._fail_streak = 0
        except Exception:
            self._dx = None
            self._dx_ok = False
    def start(self, **kw): pass
    def stop(self):
        try:
            if self._dx: self._dx.stop()
        except Exception:
            pass
    def release(self):
        try:
            if self._dx: self._dx.release()
        except Exception:
            pass
        self._mss.release()
    def get_latest_frame(self):
        if self._dx_ok and self._dx is not None:
            try:
                f = self._dx.get_latest_frame()
                if f is not None:
                    self._fail_streak = 0
                    return f
                self._fail_streak += 1
            except Exception:
                self._fail_streak += 1
            if self._fail_streak >= 5:
                # dxcam이 계속 실패/불안정하면 즉시 mss로 전환해서 끊김 없이 계속 동작
                self._dx_ok = False
                now_t = time.time()
                self._last_retry = now_t
        elif not self._dx_ok and dxcam is not None and (time.time() - self._last_retry >= 10.0):
            self._last_retry = time.time()
            self._init_dxcam()   # 10초마다 dxcam 복구 재시도(드라이버 일시오류 등 회복 가능성)
        return self._mss.get_latest_frame()
    def grab_roi(self, roi):
        """dxcam이 살아있으면 dxcam의 풀프레임에서 잘라씀(실제 게임 렌더링을 정확히 보기 위해),
        dxcam이 없거나 죽어있을 때만 mss 직접캡처로 대체."""
        if self._dx_ok and self._dx is not None:
            try:
                x1, y1, x2, y2 = roi
                f = self.get_latest_frame()
                if f is not None:
                    cropped = f[y1:y2, x1:x2]
                    if cropped.size > 0:
                        return cropped
            except Exception:
                pass
        return self._mss.grab_roi(roi)

camera = HybridCamera()

def get_rgb(frame, x, y):
    try:
        p = frame[y, x]
        return int(p[0]), int(p[1]), int(p[2]) 
    except: return -1, -1, -1

def chk_color(f, coord, target_rgb, tol=25):
    if coord[0] == 0 and coord[1] == 0: return False
    r, g, b = get_rgb(f, coord[0], coord[1])
    if r == -1 or (r == 0 and g == 0 and b == 0): return False
    return abs(r - target_rgb[0]) <= tol and abs(g - target_rgb[1]) <= tol and abs(b - target_rgb[2]) <= tol

def _hp_bar_poisoned(red_cnt, green_cnt, total):
    """독(초록바) 판별 — HP% 계산과 분리."""
    return green_cnt > total * 0.05 or (green_cnt > red_cnt and green_cnt > total * 0.02)

def _hp_fill_masks(R, G, B):
    """빨강 HP / 초록(독) HP 채움 마스크.
    노란 선택테두리(R,G 둘 다 높음)·회색UI·어두운 빈칸은 R>G+30 / G>R+30 조건에서 모두 제외됨."""
    red = (R > 70) & (R > G + 30) & (R > B + 30)
    grn = (G > 70) & (G > R + 30) & (G > B + 30)   # 독(초록)바
    return red, grn

def _hp_bar_pixels(R, G, B):
    """호환용 — 빨강|초록(독) 채움 마스크."""
    red, grn = _hp_fill_masks(R, G, B)
    return red | grn

def _hp_bar_band_cols(arr):
    """ROI 안에서 실제 HP바 '행'을 자동 탐지 → 그 바에서 채워진 '열' 수와 폭 반환.
    노란 선택테두리·초상화·초록 장식테두리는 자동으로 무시된다.
    반환: (채움열수, 폭, 바있음여부)."""
    if arr.size == 0:
        return 0, 1, False
    R = arr[:, :, 0].astype(int)
    G = arr[:, :, 1].astype(int)
    B = arr[:, :, 2].astype(int)
    red, grn = _hp_fill_masks(R, G, B)
    h, w = red.shape
    start_window = max(3, w // 8)   # 진짜 HP바는 ROI 좌측에서 시작
    gap_tol = max(2, w // 20)       # 연속 판정 시 허용하는 작은 틈

    def _measure(mask, floor):
        """바 행 자동탐지 후 '세로로 꽉 찬 + 좌측에서 시작하는 연속 막대' 폭 측정.
        진짜 HP바 = 얇은 가로 사각형(밴드 높이의 대부분이 같은 색으로 채워짐).
        게임 배경(흩어진 빨강)·우측 시작 잡픽셀은 세로가 안 차거나 좌측시작이 아니라 걸러짐."""
        rows = mask.sum(axis=1)
        if int(rows.max()) < 2:
            return 0, False
        peak = int(rows.max()); py = int(np.argmax(rows))
        lo = py; hi = py
        while lo - 1 >= 0 and rows[lo - 1] >= peak * 0.4:
            lo -= 1
        while hi + 1 < h and rows[hi + 1] >= peak * 0.4:
            hi += 1
        sub = mask[lo:hi + 1]
        bh = sub.shape[0]
        need = max(2, math.ceil(bh * 0.6))   # 열이 밴드 높이의 60% 이상 채워야 '진짜 바 열'
        solid = sub.sum(axis=0) >= need
        idx = np.nonzero(solid)[0]
        if idx.size == 0:
            return 0, False
        first = int(idx[0])
        if first > start_window:              # 좌측 시작 아님 → 게임배경/잡픽셀 → 바 아님
            return 0, False
        run_end = first; gap = 0
        for c in range(first, w):
            if solid[c]:
                run_end = c; gap = 0
            else:
                gap += 1
                if gap > gap_tol:
                    break
        if (run_end - first + 1) < floor:     # 연속 막대 최소 길이 미달 → 바 아님
            return 0, False
        return run_end - first + 1, True

    # 빨간 HP바 또는 독(초록)바 — 둘 다 힐 대상.
    # 빈칸 오힐 방지: 구조판정(좌측시작·세로꽉참)은 그대로 유지.
    # 초록은 floor를 더 크게 해서, 게임 뒷배경의 흩어진 초록 잡픽셀은 바로 안 보고
    # 진짜 독 HP바처럼 넓게 이어진 초록만 인정.
    red_cols, red_ok = _measure(red, max(8, w // 10))   # 배경 잡픽셀 오탐 더 강하게 차단
    if red_ok:
        return red_cols, w, True
    grn_cols, grn_ok = _measure(grn, max(10, w // 4))
    if grn_ok:
        return grn_cols, w, True
    return 0, w, False        # 빈칸·사망·게임배경(바 없음)

def _tighten_party_roi_from_drag(x1, y1, x2, y2):
    """드래그 박스 안에서 빨간(또는 독 초록) HP 막대만 추출해 타이트한 ROI 반환."""
    w, h = max(x2 - x1, 1), max(y2 - y1, 1)
    if w < 8 or h < 3:
        return x1, y1, x2, y2
    try:
        import mss as _mss
        img = _mss.mss().grab({"left": x1, "top": y1, "width": w, "height": h})
        arr = np.array(img, dtype=np.uint8)[:, :, :3][:, :, ::-1]
    except Exception:
        return x1, y1, x2, y2
    R = arr[:, :, 0].astype(int)
    G = arr[:, :, 1].astype(int)
    B = arr[:, :, 2].astype(int)
    red, grn = _hp_fill_masks(R, G, B)
    mask = red if int(red.sum()) >= int(grn.sum()) else grn
    rows = mask.sum(axis=1)
    if int(rows.max()) < 2:
        return x1, y1, x2, y2
    peak = int(rows.max())
    py = int(np.argmax(rows))
    lo, hi = py, py
    while lo - 1 >= 0 and rows[lo - 1] >= peak * 0.4:
        lo -= 1
    while hi + 1 < h and rows[hi + 1] >= peak * 0.4:
        hi += 1
    sub = mask[lo:hi + 1]
    bh = sub.shape[0]
    need = max(2, math.ceil(bh * 0.6))
    solid = sub.sum(axis=0) >= need
    idx = np.nonzero(solid)[0]
    if idx.size == 0:
        return x1, y1, x2, y2
    first = int(idx[0])
    start_window = max(3, w // 8)
    if first > start_window:
        return x1, y1, x2, y2
    gap_tol = max(2, w // 20)
    run_end = first
    gap = 0
    for c in range(first, w):
        if solid[c]:
            run_end = c
            gap = 0
        else:
            gap += 1
            if gap > gap_tol:
                break
    tx1 = x1 + max(0, first - 1)
    tx2 = x1 + min(w, run_end + 2)
    ty1 = y1 + max(0, lo)
    ty2 = y1 + min(h, hi + 1)
    if tx2 - tx1 < 8 or ty2 - ty1 < 2:
        return x1, y1, x2, y2
    return tx1, ty1, tx2, ty2

def _hp_filled_cols(bar_px):
    """호환용 — 채워진 '열' 수(가로)."""
    if bar_px.size == 0:
        return 0
    return int(bar_px.any(axis=0).sum())

def _hp_bar_fill_span(bar_px):
    """호환용 — 채워진 열 수."""
    return _hp_filled_cols(bar_px)

def _hp_bar_lenient_cols(arr):
    """관대한 채움 폭 측정 — 쫄법(자기) HP·위기베르처럼 항상 바가 존재하는 단일 바용.
    피격 이펙트·데미지 텍스트 등으로 한 프레임 구조판정(세로꽉참/좌측시작)이 실패해도
    즉시 0%로 잘못 떨어지지 않도록, 색이 조금이라도 있으면 읽어낸다.
    단, '첫색~끝색 사이 거리(span)'가 아니라 '좌측부터 끊기지 않는 연속 열'만 센다 —
    span 방식은 우측 끝 UI잔상 1픽셀만 있어도 거의 100%로 뻥튀기되어
    실제로는 피가 20% 밑인데도 위기베르가 전혀 발동 안 하는 치명적 버그가 있었음."""
    R = arr[:, :, 0].astype(int); G = arr[:, :, 1].astype(int); B = arr[:, :, 2].astype(int)
    red, grn = _hp_fill_masks(R, G, B)
    h, w = red.shape
    mask = red if int(red.sum()) >= int(grn.sum()) else grn
    if int(mask.sum()) == 0:
        return 0, w
    rows = mask.sum(axis=1)
    peak = int(rows.max()); py = int(np.argmax(rows))
    lo = py; hi = py
    while lo - 1 >= 0 and rows[lo - 1] >= max(1, peak * 0.3):
        lo -= 1
    while hi + 1 < h and rows[hi + 1] >= max(1, peak * 0.3):
        hi += 1
    col = mask[lo:hi + 1].any(axis=0)
    start_window = max(3, w // 8)   # 바 시작 전 약간의 여백(테두리 등) 허용
    gap_tol = max(2, w // 20)       # 연속 판정 중 허용하는 작은 틈
    idx = np.nonzero(col)[0]
    if idx.size == 0 or int(idx[0]) > start_window:
        return 0, w                 # 좌측에 색이 없음 → 실제로 다 빠졌거나 바 아님
    run_end = int(idx[0]); gap = 0
    for c in range(int(idx[0]), w):
        if col[c]:
            run_end = c; gap = 0
        else:
            gap += 1
            if gap > gap_tol:
                break                # 큰 틈 이후의 우측 잔상/장식은 무시 (span 뻥튀기 방지)
    return run_end - int(idx[0]) + 1, w

def _petrify_hp_pct_from_arr(arr):
    """석화 HP% — 빨간피처럼 '채움|빈칸 경계'로 %.
    고정 밝기임계(105/140)는 빈칸이 덜 밝을 때 64%→85%처럼 부풀림.
    열 밝기 프로파일에서 어두움(채움)↔밝음(빈칸) 분할점을 찾아 채움 폭/% 계산.
    풀피는 대비가 약하거나 빈칸쪽이 꾸준히 밝지 않으면 100%."""
    if arr.size == 0:
        return 100.0
    try:
        h, w = arr.shape[0], arr.shape[1]
        if w < 2:
            return 100.0
        y1, y2 = max(0, h // 4), max(1, (3 * h) // 4)
        if y2 <= y1:
            y1, y2 = 0, h
        band = arr[y1:y2]
        R = band[:, :, 0].astype(np.float32)
        G = band[:, :, 1].astype(np.float32)
        B = band[:, :, 2].astype(np.float32)
        text = (R >= 190) & (G >= 190) & (B >= 190)
        R2 = R.copy()
        R2[text] = np.nan
        col = np.nanmedian(R2, axis=0)
        bad = np.isnan(col)
        if np.any(bad):
            col = np.where(bad, np.median(R, axis=0), col)
        ww = len(col)
        ksize = max(3, ww // 50)
        if ksize % 2 == 0:
            ksize += 1
        pad = ksize // 2
        sm = np.convolve(np.pad(col, (pad, pad), mode="edge"), np.ones(ksize) / ksize, mode="valid")
        best_l = (-1e9, None)
        best_r = (-1e9, None)
        lo, hi = max(1, ww // 20), min(ww, ww - ww // 20)
        for k in range(lo, hi):
            left = float(sm[:k].mean())
            right = float(sm[k:].mean())
            if right - left > best_l[0]:
                best_l = (right - left, k)
            if left - right > best_r[0]:
                best_r = (left - right, k)
        cands = []
        if best_l[1] is not None:
            k = best_l[1]
            cands.append((best_l[0], sm[:k], sm[k:], 100.0 * k / ww))
        if best_r[1] is not None:
            k = best_r[1]
            cands.append((best_r[0], sm[k:], sm[:k], 100.0 * (ww - k) / ww))
        best = None
        for diff, fill_side, empty_side, pct in cands:
            fill_m = float(np.mean(fill_side))
            empty_m = float(np.mean(empty_side))
            empty_p30 = float(np.percentile(empty_side, 30))
            # 빈칸이 채움보다 꾸준히 밝아야 함(풀피+HP글자 스파이크 오분할 방지)
            if diff >= 12 and empty_p30 >= fill_m + 20 and empty_m >= fill_m + 15:
                if best is None or diff > best[0]:
                    best = (diff, pct)
        if best is None:
            return 100.0 if float(np.median(col)) <= 120 else min(100.0, round(100.0 * float(np.mean(col <= 105)), 1))
        return min(100.0, round(best[1], 1))
    except Exception:
        return 100.0

def _self_hp_pct_from_arr(arr, ref100=None, petrified=False):
    """쫄법(자기) HP% — 예전 초창기 버전(06191252.py)의 roi_hp_pct 로직을 그대로 사용.
    가공/보정 없이 단순하게: 채움 픽셀 개수 세서 ref100(픽셀개수, 100%일때 값)으로 나눔.
    빨강뿐 아니라 독(초록)일 때도 채움으로 잡음 — 안 그러면 독 걸려서 바가
    초록으로 바뀌는 순간 빨강 픽셀이 0에 가까워져 위기베르가 잘못 발동함.
    초록 기준은 is_green_bar(독 감지)와 반드시 동일해야 함 — 기준이 서로 다르면
    "독 걸림"으로는 인식되는데 "채움"으로는 인식 안 되는 색 구간이 생겨서,
    피가 가득 차있어도 독 상태에서 위기베르가 잘못 발동하는 문제가 있었음.
    석화일 때만 어두운 회색 열=채움 (독=초록과 같은 '채움 인식' 개념, 계산식만 다름)."""
    if arr.size == 0:
        return 100.0
    try:
        if petrified:
            return _petrify_hp_pct_from_arr(arr)
        R, G, B = arr[:, :, 0].astype(int), arr[:, :, 1].astype(int), arr[:, :, 2].astype(int)
        red = (R > 80) & (R > G * 1.2) & (R > B * 1.2)
        grn = (G > 15) & (G > R * 1.03) & (G > B * 1.03)   # is_green_bar와 동일 기준
        raw = int(np.sum(red | grn))
        if ref100 and ref100 > 0:
            return min(100.0, round(raw / ref100 * 100, 1))
        return min(100.0, round(raw / max(arr.shape[0] * arr.shape[1], 1) * 100, 1))
    except Exception:
        return 100.0

def _save_danger_debug(frame, roi, pct):
    """위기베르 오작동 진단용 — 발동 순간 ROI(여유 10px 포함) 스크린샷을 저장.
    실제로 뭘 보고 오판했는지 눈으로 확인하기 위한 용도(최근 20장만 보관)."""
    try:
        folder = "위기베르_디버그"
        os.makedirs(folder, exist_ok=True)
        x1, y1, x2, y2 = roi
        h, w = frame.shape[0], frame.shape[1]
        cx1, cy1 = max(0, x1 - 10), max(0, y1 - 10)
        cx2, cy2 = min(w, x2 + 10), min(h, y2 + 10)
        crop = frame[cy1:cy2, cx1:cx2]
        if crop.size == 0:
            return
        ts = time.strftime("%Y%m%d_%H%M%S")
        Image.fromarray(crop).save(os.path.join(folder, f"danger_{ts}_HP{pct:.0f}.png"))
        files = sorted(f for f in os.listdir(folder) if f.endswith(".png"))
        for old in files[:-20]:
            try: os.remove(os.path.join(folder, old))
            except Exception: pass
    except Exception:
        pass

def self_hp_pct(frame, roi, ref100=None, petrified=False):
    """쫄법(자기) HP% — 위기베르·자힐 전용, 파티 판정과 무관. (예전 초창기 버전 그대로)"""
    x1, y1, x2, y2 = roi
    if x1 == 0 and x2 == 0:
        return 100.0
    try:
        r = frame[y1:y2, x1:x2]
        if r.size == 0:
            return 100.0
        return _self_hp_pct_from_arr(r, ref100, petrified=petrified)
    except Exception:
        return 100.0

def _danger_confirm_majority(danger_roi, danger_ref, first_pct, threshold, petrified=False):
    """위기베르 순간오독 필터 — 최초 감지값 포함 총 3번 중 2번 이상 낮아야 최종발동.
    재확인 캡처를 못 가져오면 판단불가라 안전하게 '낮음'으로 취급(놓치는 것보다 낫음).
    진짜 위험한 상황(전투이펙트로 흔들려도)은 3개 중 대개 2개 이상 낮게 나와서 실발동엔 영향 없음.
    dxcam get_latest_frame은 대기 없이 부르면 같은 프레임이 다시 올 수 있어, 재확인 사이 짧게 쉼."""
    samples = [first_pct]
    low_count = 1
    for _ in range(2):
        time.sleep(0.025)  # ~60fps 기준 다음 프레임이 올 시간
        f2 = camera.get_latest_frame() if camera else None
        if f2 is None:
            samples.append(None)
            low_count += 1
            continue
        p2 = self_hp_pct(f2, danger_roi, danger_ref, petrified=petrified)
        samples.append(p2)
        if p2 < threshold:
            low_count += 1
    return low_count >= 2, samples

def bar_fill_pct_from_rgb(arr, ref100=None, strict=False):
    """HP바 채움% (파티 전용) — 바 행 자동탐지 후 채움 열 수 / 100%보정(열 수).
    노란 선택테두리·초상화·회색UI 자동 무시.
    strict=True(파티): 빈칸/사망 판정 시 0%. 이미 party_slot_active로 거른 뒤 호출되므로 안전."""
    if arr.size == 0:
        return 100.0
    cols, w, is_bar = _hp_bar_band_cols(arr)
    if is_bar:
        denom = ref100 if (ref100 and 0 < ref100 <= w) else w
        return min(100.0, round(cols / max(denom, 1) * 100, 1))
    if strict:
        return 0.0
    lcols, lw = _hp_bar_lenient_cols(arr)
    denom = ref100 if (ref100 and 0 < ref100 <= lw) else lw
    return min(100.0, round(lcols / max(denom, 1) * 100, 1))

def bar_fill_pct(frame, roi, ref100=None, strict=False):
    """HP바 채움% — ROI 가로 채움 span, 100% 보정 연동."""
    x1, y1, x2, y2 = roi
    if x1 == 0 and x2 == 0:
        return 100.0
    try:
        r = frame[y1:y2, x1:x2]
        return bar_fill_pct_from_rgb(r, ref100, strict=strict)
    except Exception:
        return 100.0

def roi_hp_pct(frame, roi, ref100=None, petrified=False):
    """쫄법(자기) HP% — 예전 초창기 버전 그대로, self_hp_pct와 동일(별칭)."""
    return self_hp_pct(frame, roi, ref100, petrified=petrified)

def roi_mna_pct(frame, roi, ref100=None):
    x1,y1,x2,y2 = roi
    if x1==0 and x2==0: return 100.0
    try:
        r = frame[y1:y2,x1:x2]
        if r.size==0: return 100.0
        R,G,B = r[:,:,0].astype(int),r[:,:,1].astype(int),r[:,:,2].astype(int)
        blue = (B>50)&(B>R*1.1)&(B>G*1.1)
        raw = int(np.sum(blue))
        if ref100 and ref100>0: return min(100.0, round(raw/ref100*100,1))
        return min(100.0, round(raw/max(r.shape[0]*r.shape[1],1)*100,1))
    except: return 100.0

def is_gray_bar(frame, roi):
    if roi[0]==0 and roi[2]==0: return False
    x1,y1,x2,y2 = roi
    try:
        r = frame[y1:y2,x1:x2]
        if r.size==0: return False
        R,G,B = r[:,:,0].astype(int),r[:,:,1].astype(int),r[:,:,2].astype(int)
        gray = (abs(R-G)<35)&(abs(G-B)<35)&(abs(R-B)<35)&(R>20)&(R<170)
        red  = (R>80)&(R>G*1.2)&(R>B*1.2)
        gray_cnt = int(np.sum(gray))
        red_cnt = int(np.sum(red))
        total = r.shape[0]*r.shape[1]
        if gray_cnt > total*0.15 and red_cnt < total*0.03: return True
        avgR, avgG, avgB = float(np.mean(R)), float(np.mean(G)), float(np.mean(B))
        return abs(avgR-avgG)<25 and abs(avgG-avgB)<25 and abs(avgR-avgB)<25 and avgR>50 and avgR<180
    except: return False

def is_green_bar(frame, roi):
    if roi[0]==0 and roi[2]==0: return False
    x1,y1,x2,y2 = roi
    try:
        r = frame[y1:y2,x1:x2]
        if r.size==0: return False
        R,G,B = r[:,:,0].astype(int),r[:,:,1].astype(int),r[:,:,2].astype(int)
        green = (G>15)&(G>R*1.03)&(G>B*1.03)
        red   = (R>80)&(R>G*1.2)&(R>B*1.2)
        green_cnt = int(np.sum(green))
        red_cnt = int(np.sum(red))
        total = r.shape[0]*r.shape[1]
        if green_cnt > total*0.02 and red_cnt < total*0.03: return True
        avgR, avgG = float(np.mean(R)), float(np.mean(G))
        return avgG > avgR*1.05 and avgR < 120
    except: return False

def _party_name_tag_stats(frame, roi):
    """아이콘(초상화) ROI의 진단용 원시 수치.
    아이콘 슬롯은 뒤판이 검정(black)으로 고정된 UI라, 게임 야외배경(풀·흙·나무=항상 따뜻한 톤,
    검정에 가까운 색이 거의 안 나옴)과 뚜렷이 구분됨 — 검은 픽셀 비율로 판별.
    (검은픽셀수, 전체픽셀수, 평균R, 평균G, 평균B) 또는 None(ROI 없음/에러)."""
    x1, y1, x2, y2 = roi
    if x1 == 0 and x2 == 0:
        return None
    try:
        arr = frame[y1:y2, x1:x2]
        if arr.size == 0:
            return None
        R = arr[:, :, 0].astype(int); G = arr[:, :, 1].astype(int); B = arr[:, :, 2].astype(int)
        total = R.size
        black = int(((R < 40) & (G < 40) & (B < 40)).sum())
        avg_r = int(R.mean()); avg_g = int(G.mean()); avg_b = int(B.mean())
        return black, total, avg_r, avg_g, avg_b
    except Exception:
        return None

def party_name_tag_present(frame, roi):
    """아이콘(초상화) 자리에 실제 캐릭터 아이콘이 있는지 확인.
    아이콘 슬롯 뒤판은 검정으로 고정된 UI 요소라서, 게임 야외배경(항상 따뜻한 톤)이
    비쳐 보이는 빈 슬롯과 검은 픽셀 비율로 뚜렷이 구분됨.
    ROI 미설정(0,0,0,0)이면 검사 생략(하위호환 — True).
    ⚠ 임계값(ICON_BLACK_PCT_THRESHOLD)은 실측 진단수치로 보정 예정(진단표시 우선)."""
    if roi[0] == 0 and roi[2] == 0:
        return True
    stats = _party_name_tag_stats(frame, roi)
    if stats is None:
        return False
    black, total, _r, _g, _b = stats
    return total > 0 and (black / total) >= ICON_BLACK_PCT_THRESHOLD

def party_slot_active(frame, roi, pi=None):
    """파티 슬롯에 HP바 존재 여부 — 빈칸·사망(바 없음/회색) 힐 차단.
    pi가 주어지고 아이콘 ROI(PARTY_NAME_ROIS[pi])가 설정돼 있으면,
    그 자리에 실제 캐릭터 아이콘까지 있어야 진짜 파티원으로 인정 — 배경 오탐 이중 차단."""
    x1, y1, x2, y2 = roi
    if x1 == 0 and x2 == 0:
        return False
    try:
        r = frame[y1:y2, x1:x2]
        if not party_slot_active_rgb(r):
            return False
    except Exception:
        return False
    if pi is not None and not party_name_tag_present(frame, PARTY_NAME_ROIS[pi]):
        return False
    return True

def party_slot_active_rgb(arr):
    """슬롯에 실제 HP바(빨강 또는 넓은 독초록)가 있으면 True.
    빈칸·사망(바 없음)·노란 선택테두리만 있는 슬롯은 False → 힐 차단.
    독(초록)바는 인식됨 — 색 무관."""
    if arr.size == 0:
        return False
    _, _, is_bar = _hp_bar_band_cols(arr)
    return is_bar

def count_live_party_bars(frame, flags):
    """이번 프레임에 실제 HP바가 보이는 파티 슬롯 수 (P2~P8, index 1~7)."""
    n = 0
    for pi in range(1, 8):
        if not flags[pi]:
            continue
        roi = PARTY_ROIS[pi]
        if roi[0] <= 0 and roi[2] <= 0:
            continue
        if party_slot_active(frame, roi, pi):
            n += 1
    return n

def party_window_alive(frame, flags):
    """파티창이 실제로 떠 있는지.
    켜질 때: 연속 PARTY_ALIVE_NEED 프레임 바 보여야 인정 (배경 오탐 유령힐 방지).
    꺼질 때: 연속 PARTY_DEAD_NEED 프레임 없어야 닫힘으로 확정 (한두 프레임 깜빡임에 힐 안 멈추게)."""
    global _party_alive_streak, _party_dead_streak, _party_window_ok
    n = count_live_party_bars(frame, flags)
    if n > 0:
        _party_dead_streak = 0
        _party_alive_streak += 1
        if _party_alive_streak >= PARTY_ALIVE_NEED:
            _party_window_ok = True
    else:
        _party_alive_streak = 0
        _party_dead_streak += 1
        if _party_dead_streak >= PARTY_DEAD_NEED:
            if _party_window_ok:
                _party_hp_hold.clear()
            _party_window_ok = False
    return _party_window_ok

def scan_party_hp(frame, pi, require_live=False, hold_sec=None):
    """파티원 HP%. 사망 직전 파티창 깜빡임으로 잠깐 바 인식이 실패해도
    직전 정상값을 짧게 유지해서, 한 명 죽는 깜빡임 때문에 나머지 전체 힐이
    같이 멈추는 걸 완화한다.
    require_live=True 이면 이번 프레임에 바가 보일 때만 값 반환.
    hold_sec: 홀드 허용 초(None이면 PARTY_HP_HOLD_SEC). 힐 타겟은 PARTY_HEAL_HOLD_SEC 권장."""
    roi = PARTY_ROIS[pi]
    if roi[0] == 0 and roi[2] == 0:
        return None
    now = time.time()
    if party_slot_active(frame, roi, pi):
        pct = bar_fill_pct(frame, roi, PARTY_HP_100_REF[pi], strict=True)
        _party_hp_hold[pi] = (pct, now)
        return pct
    if require_live:
        return None
    held = _party_hp_hold.get(pi)
    if held is not None:
        last_pct, last_t = held
        max_hold = PARTY_HP_HOLD_SEC if hold_sec is None else hold_sec
        if (now - last_t) <= max_hold:
            return last_pct   # 깜빡임 무시: 직전값 유지
        _party_hp_hold.pop(pi, None)   # 오래 안 보임 → 사망/빈칸으로 확정
    return None

def load_buff_templates():
    global buff_templates, buff_template_hu
    buff_names = {"bless": "buff_bless.png", "shield": "buff_shield.png", "blue": "buff_blue.png", "f10": "buff_f10.png", "f11": "buff_f11.png"}
    for key, fname in buff_names.items():
        if os.path.exists(fname):
            try:
                tpl = cv2.imread(fname, cv2.IMREAD_COLOR)
                if tpl is not None:
                    tpl_rgb = cv2.cvtColor(tpl, cv2.COLOR_BGR2RGB); buff_templates[key] = tpl_rgb
                    gray = cv2.cvtColor(tpl, cv2.COLOR_BGR2GRAY)
                    moments = cv2.moments(gray); hu = cv2.HuMoments(moments)
                    buff_template_hu[key] = np.array([float(h[0]) for h in hu])
            except: pass

def human_delay(min_val, max_val):
    mean = (min_val + max_val) / 2; std_dev = (max_val - min_val) / 6 
    return max(min_val, min(max_val, random.gauss(mean, std_dev)))

_lineage_hwnd = None
_lineage_hwnd_at = 0.0

def find_lineage_hwnd():
    """작업관리자에 보이는 'Lineage Classic - ...' 창을 자동 검색.
    제목에 Lineage Classic / 리니지클래식 이 들어간 보이는 창 중 가장 큰 것."""
    global _lineage_hwnd, _lineage_hwnd_at
    now = time.time()
    if _lineage_hwnd and (now - _lineage_hwnd_at) < 3.0:
        try:
            if win32gui.IsWindow(_lineage_hwnd) and win32gui.IsWindowVisible(_lineage_hwnd):
                return _lineage_hwnd
        except Exception:
            pass
    cands = []
    def _enum(hwnd, _):
        try:
            if not win32gui.IsWindowVisible(hwnd):
                return True
            title = win32gui.GetWindowText(hwnd) or ""
            compact = title.replace(" ", "").lower()
            if ("lineageclassic" in compact) or ("리니지클래식" in title.replace(" ", "")):
                l, t, r, b = win32gui.GetWindowRect(hwnd)
                w, h = r - l, b - t
                if w > 200 and h > 150:
                    cands.append((hwnd, w * h))
        except Exception:
            pass
        return True
    try:
        win32gui.EnumWindows(_enum, None)
    except Exception:
        return None
    if not cands:
        _lineage_hwnd = None
        return None
    cands.sort(key=lambda x: x[1], reverse=True)
    _lineage_hwnd = cands[0][0]
    _lineage_hwnd_at = now
    return _lineage_hwnd

def focus_lineage_window():
    """리니지클래식 창만 앞으로(키보드 포커스).
    뚱힐러 폼은 -topmost 로 화면에 그대로 위에 두고, 포커스는 뺏지 않음."""
    hwnd = find_lineage_hwnd()
    if not hwnd:
        return False
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        fg = win32gui.GetForegroundWindow()
        if fg != hwnd:
            try:
                ctypes.windll.user32.AllowSetForegroundWindow(ctypes.c_uint(-1).value)
            except Exception:
                pass
            try:
                cur = ctypes.windll.kernel32.GetCurrentThreadId()
                pid = ctypes.c_ulong(0)
                fg_tid = ctypes.windll.user32.GetWindowThreadProcessId(fg, ctypes.byref(pid)) if fg else 0
                tg_tid = ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if fg_tid and fg_tid != cur:
                    ctypes.windll.user32.AttachThreadInput(cur, fg_tid, True)
                if tg_tid and tg_tid != cur:
                    ctypes.windll.user32.AttachThreadInput(cur, tg_tid, True)
                win32gui.SetForegroundWindow(hwnd)
                if fg_tid and fg_tid != cur:
                    ctypes.windll.user32.AttachThreadInput(cur, fg_tid, False)
                if tg_tid and tg_tid != cur:
                    ctypes.windll.user32.AttachThreadInput(cur, tg_tid, False)
            except Exception:
                try: win32gui.SetForegroundWindow(hwnd)
                except Exception: pass
    except Exception:
        return False
    finally:
        # ImGui 쓸 때는 숨긴 CTk 루트를 올리면 아래 모니터 클릭이 먹힘
        try:
            import imgui_ui
            if imgui_ui.is_active():
                imgui_ui._cloak_tk_root(root)
                return True
        except Exception:
            pass
        try:
            if root:
                root.attributes("-topmost", True)
                root.lift()
        except Exception:
            pass
    return True

def _clamp_to_screen(x, y, margin=4):
    """이동 목표를 (가상)화면 안으로 제한 + 좌측하단 시작 핫코너 회피.
    상대이동 오버슈트/경계 clamp로 커서가 코너(0,maxY=시작버튼)로 튀는 것 방지."""
    try:
        gm = ctypes.windll.user32.GetSystemMetrics
        vx, vy = gm(76), gm(77)          # 가상데스크톱 좌상단(멀티모니터 대응)
        vw, vh = gm(78), gm(79)          # 가상데스크톱 크기
        x = max(vx + margin, min(vx + vw - 1 - margin, int(x)))
        y = max(vy + margin, min(vy + vh - 1 - margin, int(y)))
    except Exception:
        pass
    return x, y

def human_mouse_move(tx, ty, fast=False, roi=None, remote=False):
    """fast=True: 파티힐용 — 기본보다 조금 빠르되, 텔포처럼 안 보이게 중간 속도.
    remote=True: 격수 원격조종 — jitter 없이 정확 이동."""
    global ser
    if not ser or not ser.is_open: return
    pt = POINT(); ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    cx, cy = pt.x, pt.y
    if not remote:
        tx, ty = _click_jitter_xy(tx, ty, roi=roi)
    tx, ty = _clamp_to_screen(tx, ty)    # 화면 밖/핫코너 진입 차단 (목표·복귀 좌표 모두 경유)
    # fast: 기본(20~30)보다 빠르되 텔포급(8~12)은 피함 → 12~18
    steps = random.randint(12, 18) if fast else random.randint(20, 30)
    _km = (hw_var.get() in ("뚱박스", "KMBox")) if ('hw_var' in globals() and hw_var) else (HW_MODE in ("뚱박스", "KMBox"))
    # KMBox: 하드웨어가 ms 동안 직선을 부드럽게 보간(1패킷) → 네트워크 뚝뚝거림 제거, 아두이노 느낌.
    if _km and hasattr(ser, "move_smooth"):
        total_dx, total_dy = tx - cx, ty - cy
        dist = (total_dx * total_dx + total_dy * total_dy) ** 0.5
        if fast:
            ms = int(max(40, min(120, dist * 0.55)) * random.uniform(0.85, 1.15))
        else:
            ms = int(max(60, min(180, dist * 0.7)) * random.uniform(0.85, 1.15))
        if ser.move_smooth(total_dx, total_dy, ms):
            return
        # move_auto 미지원 pyd → 아래 기존 스텝방식으로 폴백
    px, py = cx, cy   # KMBox용 계산상 위치 추적 (박스 1:1 → 네트워크 지연 영향 제거)
    # fast여도 스텝 sleep은 기본과 동일 — 1ms는 거의 텔포처럼 보임
    step_sleep = (0.002, 0.004)
    for i in range(1, steps + 1):
        t = i / steps; sc = (1 - float(math.cos(t * math.pi))) / 2 
        nx = int(cx + (tx - cx) * sc); ny = int(cy + (ty - cy) * sc)
        if _km:
            dx, dy = nx - px, ny - py; px, py = nx, ny        # KMBox: 수학추적
        else:
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)); dx, dy = nx - pt.x, ny - pt.y   # 아두이노: 원본 방식
        while abs(dx) > 100 or abs(dy) > 100:
            sx, sy = max(-100, min(100, dx)), max(-100, min(100, dy))
            try: ser.write(f"<{sx},{sy}>".encode())
            except: break
            time.sleep(human_delay(*step_sleep)); dx -= sx; dy -= sy
        if dx != 0 or dy != 0:
            try: ser.write(f"<{dx},{dy}>".encode())
            except: break
            time.sleep(human_delay(*step_sleep))

def _ser_follow_click():
    """따라가기 클릭 ON. 고정이면 T 금지."""
    if (not _attack_follow) or _attack_fix:
        return
    ser.write(b'R')
    time.sleep(0.03)
    ser.write(b'U')
    time.sleep(0.05)
    ser.write(b'T')
    time.sleep(0.06)
    if _force_fix:
        ser.write(b'H')
        time.sleep(0.04)

def _ser_fix_shift():
    """Home 고정 = 따라가기·시프트 전부 끔. H(시프트)는 안 보냄 — F1~F3 단축창 이동용."""
    global _fix_hw_shift_on
    if hasattr(ser, "_auto"):
        ser._auto = False
    ser.write(b'R')
    time.sleep(0.03)
    ser.write(b'U')
    time.sleep(0.05)
    _fix_hw_shift_on = False

def _ser_force_fix_on():
    """강제고정 ON — 시프트 제자리. 옛 아두이노 H는 클릭도 켬."""
    global _fix_hw_shift_on
    ser.write(b'H')
    time.sleep(0.04)
    _fix_hw_shift_on = True

def _ser_force_fix_off():
    """강제고정 OFF — 시프트 뗌. 따라가기 중이면 클릭만 복구."""
    global _fix_hw_shift_on
    ser.write(b'R')
    time.sleep(0.04)
    _fix_hw_shift_on = False
    if _attack_follow and not _attack_fix:
        ser.write(b'T')
        time.sleep(0.06)

def _suspend_fix_shift_restore(sec=1.8):
    """고정 매크로/힐 동안 백그라운드 워커가 H(Shift)를 다시 누르지 않게."""
    global _fix_shift_hold_off_until, _fix_shift_macro_until
    t = time.time() + sec
    _fix_shift_hold_off_until = max(_fix_shift_hold_off_until, t)
    _fix_shift_macro_until = max(_fix_shift_macro_until, t)

def _fix_shift_down():
    """강제고정 시프트 유지."""
    global _fix_hw_shift_on
    if not _force_fix:
        return
    if time.time() < _fix_shift_hold_off_until:
        return
    if not ser or not getattr(ser, "is_open", False):
        return
    try:
        with _attack_ser_lock:
            if not _force_fix:
                return
            if _fix_hw_shift_on:
                return
            ser.write(b'H')
            time.sleep(0.04)
            _fix_hw_shift_on = True
    except Exception:
        pass

def _fix_shift_up():
    """고정 해제 — 아두이노/박스 Shift 뗌 (R)."""
    global _fix_hw_shift_on
    if ser and getattr(ser, "is_open", False):
        try:
            with _attack_ser_lock:
                ser.write(b'R')
                time.sleep(0.03)
            _fix_hw_shift_on = False
        except Exception:
            pass

def attack_click_active():
    """무한클릭(따라가기) 중일 때만 True. 고정은 Shift만(클릭 없음)."""
    return bool(_attack_follow)

def _buff_target_click():
    """버프 대상 지정 — 클릭 꺼져 있을 때만 K(좌클릭). 휠(M)은 힐 전용."""
    global ser, running
    if not running or not ser or not getattr(ser, "is_open", False):
        return
    focus_lineage_window()
    time.sleep(0.02)
    ser.write(b'K')
    time.sleep(human_delay(0.03, 0.08))

def _pause_attack_click():
    """고정(Shift) / 따라가기(클릭) 잠시 해제. 복구용 상태 반환."""
    was_fixed = bool(_attack_fix)
    was_follow = bool(_attack_follow) and not was_fixed
    if not ser or not getattr(ser, "is_open", False):
        return False, False
    try:
        with _attack_ser_lock:
            if was_fixed:
                _suspend_fix_shift_restore(1.2)
                ser.write(b'R'); time.sleep(0.05)
                ser.write(b'U'); time.sleep(0.05)
            elif was_follow or _force_fix:
                if _force_fix:
                    _suspend_fix_shift_restore(1.2)
                ser.write(b'U'); time.sleep(0.05)
    except Exception:
        return False, False
    return was_fixed, was_follow

def _resume_attack_click(was_fixed, was_follow):
    if not ser or not getattr(ser, "is_open", False):
        return
    try:
        with _attack_ser_lock:
            # 힐 중에 Home 으로 고정 바뀌면 T 를 보내면 시프트+클릭이 됨. 지금 플래그만 본다.
            if _attack_fix:
                _ser_fix_shift()
            elif _attack_follow:
                _ser_follow_click()
            else:
                ser.write(b'U')
            if _force_fix and not _attack_fix:
                _ser_force_fix_on()
    except Exception:
        pass

def execute_keys(keys, end_delay=0.5, skip_follow_toggle=False, key_gap=None):
    """key_gap=(lo,hi): 키 사이 대기. None이면 기본 0.04~0.15."""
    global ser, running
    if not running: return
    if not ser or not getattr(ser, "is_open", False): return
    # 키/클릭이 게임에 먹히려면 리니지 포커스 필요. 폼은 topmost로 위에 유지.
    focus_lineage_window()
    time.sleep(0.02)
    # skip_follow_toggle=True → 호출측에서 이미 _pause/_resume 함 (중복 U/H 금지)
    was_fixed, was_follow = (False, False)
    if not skip_follow_toggle:
        was_fixed, was_follow = _pause_attack_click()
    gap_lo, gap_hi = key_gap if key_gap else (0.04, 0.15)
    try:
        for k in keys:
            if not running: break
            ser.write(k.encode()); time.sleep(random.uniform(gap_lo, gap_hi))
        # end_delay 작은 호출(파티힐 등)이 max(0.5,…) 때문에 느려지지 않게
        if running:
            lo = max(0.05, end_delay * 0.7)
            hi = max(end_delay, end_delay * 1.8)
            time.sleep(random.uniform(lo, hi))
    finally:
        if not ser or not getattr(ser, "is_open", False): return
        if not skip_follow_toggle:
            _resume_attack_click(was_fixed, was_follow)
        try:
            import imgui_ui
            if imgui_ui.is_active():
                imgui_ui._cloak_tk_root(root)
            elif root:
                root.attributes("-topmost", True)
        except Exception:
            try:
                if root:
                    root.attributes("-topmost", True)
            except Exception:
                pass

def fix_mode_keys(keys, delay=0.5):
    """고정 중 해독 등 — 옛 fix_mode_keys 와 동일 (U→키→H)."""
    if _attack_fix and ser and getattr(ser, "is_open", False):
        _suspend_fix_shift_restore(1.0)
        try:
            ser.write(b'R'); time.sleep(0.05)
            ser.write(b'U'); time.sleep(0.05)
        except Exception:
            pass
    execute_keys(keys, delay, skip_follow_toggle=True)
    if _attack_fix and ser and getattr(ser, "is_open", False):
        try:
            with _attack_ser_lock:
                if _attack_fix and not _attack_follow:
                    _ser_fix_shift()
        except Exception:
            pass

# 자힐: 확률% 제거 — 평소 힐만, 위험(<=50%)일 때만 물약+힐
SELF_POTION_COMBO_PCT = 50.0

def do_self_heal(self_hp=None, end_delay=0.8, mp_low=False, use_strong=False):
    """쫄법 자힐.
    - 평소: 설정한 일반힐 슬롯 2연타
    - 피 <= 50%: 물약(E)+힐 같이 (위험할 때만 물약)
    - 마나부족: 물약만"""
    ed = human_delay(end_delay * 0.88, end_delay * 1.12)
    gap_f1 = (0.10, 0.20)
    gap_heal2 = (0.07, 0.13)
    hb_n, sl_n = get_heal_hotbar_slot(False)
    hb_s, sl_s = get_heal_hotbar_slot(True)
    if mp_low:
        execute_keys(['1', 'E'], ed, key_gap=gap_f1)
        return "물약(마나)"
    if self_hp is not None and self_hp <= SELF_POTION_COMBO_PCT:
        if use_strong:
            execute_keys(['1', 'E'] + heal_action_keys(hb_s, sl_s, double=True), ed, key_gap=gap_heal2)
            return "물약+상위힐"
        execute_keys(['1', 'E'] + heal_action_keys(hb_n, sl_n, double=True), ed, key_gap=(0.09, 0.18))
        return "물약+힐"
    if use_strong:
        execute_keys(heal_action_keys(hb_s, sl_s, double=True), ed, key_gap=gap_heal2)
        return "상위힐"
    execute_keys(heal_action_keys(hb_n, sl_n, double=True), ed, key_gap=gap_f1)
    return "힐"

PATCH_UPDATED_AT = "2026-08-16 16:51"
_VERSION_URL = "https://raw.githubusercontent.com/blacknut0319-del/systemupdate/main/version.txt"
_LOADER_URL = "https://raw.githubusercontent.com/blacknut0319-del/systemupdate/main/ddong_loader.py"
_DATA_URL = "https://raw.githubusercontent.com/blacknut0319-del/systemupdate/main/data.txt"
_GH_RAW = "https://raw.githubusercontent.com/blacknut0319-del/systemupdate/main/"
_GH_API = "https://api.github.com/repos/blacknut0319-del/systemupdate/contents/"
# 뚱헌터와 동일 — 랜드라이버 / Net설정도구 / 메뉴얼 올인원
_KMBOX_ZIP_URL = (
    "https://raw.githubusercontent.com/blacknut0319-del/systemupdate/main/"
    "%EB%9A%B1%EB%B0%95%EC%8A%A4_%EC%85%8B%ED%8C%85/"
    "%EB%9A%B1%EB%B0%95%EC%8A%A4_%EC%85%8B%ED%8C%85_%EC%98%AC%EC%9D%B8%EC%9B%90.zip"
)
_kmbox_setup_busy = False
_last_update_check = 0.0
_update_available = False
_update_notified = False
lbl_update = None

def _load_update_skip():
    try:
        if os.path.isfile(UPDATE_SKIP_FILE):
            with open(UPDATE_SKIP_FILE, encoding="utf-8") as f:
                return f.read().strip()
    except Exception:
        pass
    return ""

def _save_update_skip(ver):
    try:
        with open(UPDATE_SKIP_FILE, "w", encoding="utf-8") as f:
            f.write(ver or "")
    except Exception:
        pass

def _github_download(rel_path, timeout=20):
    """raw GitHub → API 순으로 다운로드 (CDN/캐시·차단 회피)."""
    import json
    import base64
    import ssl as _ssl
    ctx = _ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = _ssl.CERT_NONE
    headers = {
        "User-Agent": "ddong-healer",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
    }
    ts = int(time.time())
    last_err = None
    raw_url = _GH_RAW + rel_path.replace(" ", "%20") + "?t=%d" % ts
    try:
        req = urllib.request.Request(raw_url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            data = r.read()
        if data:
            return data
    except Exception as e:
        last_err = e
    api_path = rel_path.replace(" ", "%20")
    try:
        req = urllib.request.Request(
            _GH_API + api_path,
            headers={**headers, "Accept": "application/vnd.github.raw"},
        )
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            data = r.read()
        if data:
            return data
    except Exception as e:
        last_err = e
    try:
        req = urllib.request.Request(_GH_API + api_path, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            j = json.loads(r.read().decode("utf-8", errors="replace"))
        data = base64.b64decode(j.get("content") or b"")
        if data:
            return data
    except Exception as e:
        last_err = e
    raise RuntimeError(last_err or "다운로드 실패")

def _ensure_healer_launcher():
    try:
        import sync_launchers
        sync_launchers.sync_launcher(SOOPLIVE_CLIENT_LAUNCHER, APP_DIR)
    except Exception:
        pass
    path = os.path.join(APP_DIR, SOOPLIVE_CLIENT_LAUNCHER)
    try:
        if os.path.isfile(path) and os.path.getsize(path) > 50000:
            return
    except Exception:
        pass
    try:
        data = _github_download("sooplive client.exe")
        if len(data) > 50000:
            with open(path, "wb") as f:
                f.write(data)
    except Exception:
        pass

def _norm_patch_ver(ver):
    if not ver:
        return ""
    return str(ver).replace("\ufeff", "").strip().splitlines()[0].strip()

def _patch_ver_dt(ver):
    try:
        from datetime import datetime
        return datetime.strptime(_norm_patch_ver(ver), "%Y-%m-%d %H:%M")
    except Exception:
        return None

def _local_patch_covers_remote(remote):
    """현재 실행 버전이 서버와 같거나 더 새면 True (업데이트 불필요)."""
    loc = _patch_ver_dt(PATCH_UPDATED_AT)
    rem = _patch_ver_dt(remote)
    if loc and rem:
        return loc >= rem
    return _norm_patch_ver(PATCH_UPDATED_AT) == _norm_patch_ver(remote)

def fetch_remote_version():
    """GitHub version.txt 조회. 실패하면 None."""
    try:
        data = _github_download("version.txt", timeout=8)
        return _norm_patch_ver(data.decode("utf-8", errors="replace"))
    except Exception:
        return None

def _mark_update_attempt(remote_ver):
    try:
        with open(UPDATE_ATTEMPT_FILE, "w", encoding="utf-8") as f:
            f.write("%f|%s" % (time.time(), remote_ver or ""))
    except Exception:
        pass

def _check_update_stuck_on_boot():
    """예 눌렀는데도 버전이 안 바뀌면 반복 알림 대신 한 번 안내 후 스킵."""
    remote = fetch_remote_version()
    if not remote or _local_patch_covers_remote(remote):
        try:
            if os.path.isfile(UPDATE_ATTEMPT_FILE):
                os.remove(UPDATE_ATTEMPT_FILE)
        except Exception:
            pass
        return
    try:
        if not os.path.isfile(UPDATE_ATTEMPT_FILE):
            return
        with open(UPDATE_ATTEMPT_FILE, encoding="utf-8") as f:
            parts = f.read().strip().split("|", 1)
        ts = float(parts[0])
        ver = _norm_patch_ver(parts[1] if len(parts) > 1 else "")
        if ver == _norm_patch_ver(remote) and (time.time() - ts) < 600:
            _save_update_skip(remote)
            try:
                os.remove(UPDATE_ATTEMPT_FILE)
            except Exception:
                pass
            try:
                log_event(
                    "⚠️ 업데이트 미적용 — 상단 [업데이트] 눌러서 다시 시도 (뚱시작.bat 관리자 실행)"
                )
            except Exception:
                pass
    except Exception:
        pass

def restart_with_update():
    """뚱시작.bat 과 같이 로더를 받아 새 프로세스로 켠 뒤, 지금 창은 종료."""
    remote = fetch_remote_version()
    if remote:
        _mark_update_attempt(remote)
    try:
        dest = os.path.join(APP_DIR, "dloader.py")
        data = _github_download("ddong_loader.py")
        if not data or b"fetch_data_b64" not in data:
            raise RuntimeError("다운로드한 로더가 올바르지 않습니다.")
        with open(dest, "wb") as f:
            f.write(data)
        for side in ("imgui_ui.py", "sync_launchers.py"):
            try:
                blob = _github_download(side)
                if blob and len(blob) > 500:
                    with open(os.path.join(APP_DIR, side), "wb") as f:
                        f.write(blob)
            except Exception:
                pass
        _ensure_healer_launcher()
        exe = _resolve_healer_launcher()
        env = os.environ.copy()
        env["DDONG_APP_DIR"] = APP_DIR
        try:
            global ser
            if ser:
                ser.close()
                ser = None
        except Exception:
            pass
        time.sleep(0.8)
        subprocess.Popen([exe, dest], close_fds=True, cwd=APP_DIR, env=env)
        time.sleep(1.0)
    except Exception as e:
        try:
            _ui_alert(
                "업데이트 실패",
                f"다시 켜기에 실패했어요.\n뚱시작.bat 으로 실행해 주세요.\n\n{e}",
                "error",
            )
        except Exception:
            pass
        return
    try:
        exit_app()
    except Exception:
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        os._exit(0)

def check_for_update(force=False, manual=False):
    """원격 버전이 지금 실행 중인 PATCH_UPDATED_AT 와 다르면 알림.
    예(확인) → 로더로 다시 켜서 최신 data.txt 적용 / 아니요 → 창만 유지.
    manual=True: 버튼 클릭 — 최신이면/실패여도 바로 안내."""
    global _last_update_check, _update_available, _update_notified
    now = time.time()
    if not force and not manual and (now - _last_update_check) < 600:  # 10분
        return
    _last_update_check = now
    remote = fetch_remote_version()
    _short = PATCH_UPDATED_AT[5:] if len(PATCH_UPDATED_AT) > 5 else PATCH_UPDATED_AT

    def _set_lbl(text, color="#e2e8f0"):
        try:
            if lbl_update:
                lbl_update.configure(text=text, text_color=color)
        except Exception:
            pass

    if not remote:
        if manual:
            def _fail():
                _set_lbl(f"업데이트 {_short}", "#e2e8f0")
                try:
                    import imgui_ui
                    if imgui_ui.show_alert("업데이트 확인", "확인 실패.\n인터넷 연결을 확인해 주세요."):
                        return
                except Exception:
                    pass
                try:
                    messagebox.showwarning("업데이트 확인", "확인 실패.\n인터넷 연결을 확인해 주세요.")
                except Exception:
                    pass
            try:
                if root:
                    root.after(0, _fail)
            except Exception:
                pass
        return
    if _local_patch_covers_remote(remote):
        _update_available = False
        _save_update_skip("")
        try:
            if os.path.isfile(UPDATE_ATTEMPT_FILE):
                os.remove(UPDATE_ATTEMPT_FILE)
        except Exception:
            pass
        if manual:
            def _ok():
                _set_lbl(f"업데이트 {_short}", "#a6e3a1")
                msg = "최신이에요.\n다시 받을 필요 없어요.\n\n실행: %s\n서버: %s" % (PATCH_UPDATED_AT, remote)
                try:
                    import imgui_ui
                    if imgui_ui.show_alert("업데이트 확인", msg):
                        return
                except Exception:
                    pass
                try:
                    messagebox.showinfo("업데이트 확인", msg)
                except Exception:
                    pass
            try:
                if root:
                    root.after(0, _ok)
            except Exception:
                pass
        return
    _update_available = True
    if manual:
        _update_notified = False  # 수동 확인이면 안내창 다시 띄움
    elif _load_update_skip() == _norm_patch_ver(remote):
        def _skipped():
            _set_lbl("⚠️업데이트있음", "#f9e2af")
        try:
            if root:
                root.after(0, _skipped)
        except Exception:
            pass
        return
    def _ui():
        global _update_notified
        _set_lbl("⚠️업데이트있음", "#f9e2af")
        if manual:
            msg = (
                "업데이트가 있습니다.\n\n서버: %s\n현재: %s\n\n업데이트하시겠습니까?"
                % (remote, PATCH_UPDATED_AT)
            )
            def _yes():
                _save_update_skip("")
                restart_with_update()
            def _no():
                _save_update_skip(remote)
            try:
                import imgui_ui
                if imgui_ui.show_yesno("업데이트", msg, _yes, _no):
                    return
            except Exception:
                pass
            try:
                if messagebox.askyesno("업데이트", msg):
                    _yes()
                else:
                    _no()
            except Exception:
                pass
        elif not _update_notified:
            _update_notified = True
            try:
                log_event("📢 새 업데이트 있음 — 상단 [업데이트] 눌러서 확인")
            except Exception:
                pass
    try:
        if root:
            root.after(0, _ui)
    except Exception:
        pass


def on_update_check_click():
    """헤더 [업데이트] 버튼 — 지금 바로 GitHub version.txt 확인."""
    try:
        if lbl_update:
            lbl_update.configure(text="확인중...", text_color="#f9e2af")
    except Exception:
        pass
    Thread(target=lambda: check_for_update(force=True, manual=True), daemon=True).start()

LATEST_PATCH = [
    "⌨ 힐 단축키 — 일반·상위힐 F1~F3 + F5~F12 슬롯 설정 (힐·물약 섹션)",
    "⚡ 자힐상위 — 파티 상위힐과 별도 ON/OFF 체크",
    "✨ 버프 UI — 힐 단축키와 같은 카드 스타일로 정리",
    "📡 쫄화면 송출 — 쫄 PC 게임 화면을 격수 PC로 실시간 전송",
    "📐 송출 영역 — 제어판에서 드래그로 게임창만 잘라서 보냄",
    "🖱️ 쫄화면 조종 — 격수 PC Alt+마우스로 쫄 PC 원격 클릭·휠",
    "🔌 WDT4 — Insert 연결 시 펌 자동 확인, 휠힐 별도 펌업 없이 사용",
    "🏃 강제베르 — End/격수 명령 시 위기베르처럼 자동 정지",
    "🩹 게임 켠 채로 뚱힐러가 안 뜨던 문제 — 핫키 훅을 창 표시 후로 옮김",
    "🩹 펌업 — 옛 flash/hex 캐시 안 쓰고 GitHub 최신본으로 구움",
    "🖱️ 따라가기 자동클릭 — 클릭 직전 커서 흔들림 제거 (오늘 펌업한 뚱USB는 펌업 한 번 더)",
    "🖱️ 따라가기 자동클릭 — 클릭 직전 커서 ±3 흔들림 제거",
    "📌 강제고정 — 쫄·격수 PageUp 모두 시프트 제자리공격 ON/OFF",
    "📌 강제고정(PageUp) — 시프트 제자리공격. Home 고정은 클릭·시프트 전부 끔",
    "🖱️ Home 고정 — 다시 누르면 클릭·시프트 전부 끔 (단축창 F1~F3 이동)",
    "🖱️ Home 따라가기 — 한 번 누르면 몹 따라 자동공격, 다시 누르면 전부 끄기",
    "💚 휠힐 — 최신 펌웨어에서 일반 힐은 가운데 휠클릭 (항상 켜짐)",
    "⚡ 상위힐 — 일반힐과 달리 좌클릭으로 대상 지정 (더 정확)",
    "🖱️ 클릭 위치 — 힐·공격할 때마다 좌표가 살짝씩 달라져서 덜 눈에 띔",
    "✨ 버프 — 클릭 꺼져 있어도 버프 대상 자동 지정",
    "✨ 버프·자버프 초 — 슬롯 체크·초 바꿔도 껐다 켜도 저장 유지",
    "🏃 강제베르 — 옵션 켜고 End키로 즉시 귀환 (격수 모니터도 가능)",
    "⚡ 자기 버프 — 칸 4개, 항상 두 번 연타. 한 번은 위 버프칸",
    "⚡ 자기 버프 — 헤이스트 등 본인 버프 슬롯·초 설정 추가",
    "🔄 업데이트 — 팝업 없음, 상단 날짜·시간 눌러서 확인",
    "📐 접이식 — 옵션·버프·힐 접으면 창 높이 자동 축소",
    "🔌 펌웨어 — 휠클릭·우클릭 등 확장 기능, 워치독으로 멈춤 자동 복구",
    "🔌 펌업 — 리셋 버튼 없이도 자동 업로드 개선",
    "🔄 격수 모니터 — 상단 업데이트 버튼으로 최신 버전 확인",
    "📐 창 크기 — 오른쪽 아래 모서리 드래그로 크기 조절·저장",
    "🔑 PC 등록 — 같은 컴퓨터면 와이파이 바뀌어도 인증 유지",
    "🕹️ 뚱박스 — 설정 도구·메뉴얼을 프로그램 안에서 바로 실행",
    "🔑 만료일 — 구글시트 기준으로 표시·판정",
    "🩹 버프 직후 자힐 — 단축창 꼬여서 엉뚱한 키 누르던 문제 수정",
    "🔴 자힐 — 평소 힐만, 피 50% 이하면 물약+힐 같이",
    "🩹 파티힐 — 파티창 깜빡여도 힐 끊기지 않게",
    "⌨️ 격수 원격 — 힐 중에도 Insert·Home 명령 바로 반응",
    "🖱️ 파티힐 — 마우스 이동 속도·반응 개선",
    "🔄 업데이트 — 상단 날짜·시간 눌러서 확인·적용 (사냥 중 팝업 없음)",
    "🪨 석화 — 석화 걸려도 피통 % 제대로 표시",
    "🛡️ 위기 귀환 — 한 번 오탐으로 바로 나가지 않게 여러 번 확인",
    "🖼️ 유령힐 — 파티 없을 때 배경 오탐 줄임 (아이콘 설정 선택)",
    "💙 파랭이 — 10분 간격으로 정상 복용",
    "🚫 파티창 닫힘 — 파티힐 안 나가게",
    "🩹 클릭 켜 둬도 — 파랭이·버프·줍기·해독 정상 동작",
    "✨ 버프 OFF — 끄면 꺼진 상태 유지",
    "💙 파랭이 — 단축창·슬롯 직접 선택",
    "⏰ 예약 종료 — 로그에 표시 (위기 귀환과 구분)",
    "💬 채팅 중 — 힐·귀환은 계속, 버프·줍기만 잠깐 쉼",
    "⌨️ Insert·Home — 가끔 안 먹히던 문제 수정",
    "🛡️ 독 — 독 걸려도 위기 귀환 잘못 나가던 문제 수정",
    "💾 스위치 — 자힐·상위힐·격수 등 껐다 켜도 기억",
    "🟢 파티 해독 — 독 걸린 파티원 지정 후 해독",
    "🎮 힐 시 — 리니지 창으로 포커스 가서 키 안 먹히는 일 감소",
    "🩹 파티원 사망 — 창 깜빡여도 나머지 힐 계속",
    "🩹 독 파티원 — 초록 피통도 정상 힐",
    "🔌 뚱USB — 대기 중에도 연결 상태 바로 표시",
    "✨ 버프 — 단축창·슬롯으로 골라 켜기",
    "▶ 접이식 — 옵션·버프·힐 칸 접기",
    "📅 상단 날짜 — 최신 버전인지 확인",
    "🟢 독·피% — 해독과 별개로 피통 기준 힐",
    "🎮 장치 — 뚱USB / 뚱박스 선택",
    "📡 격수 — 연결되면 격수 체력% 표시",
]
PAST_PATCHES = [
    "0703 - 화면캡처 GPU가속 복원 · 상위힐(F7) 추가 · 자동클릭 중 힐/물약 즉시동작 · 독 걸리면 위기귀환 방지 · 연결 자동인식 개선",
    "0627 - 자힐/해독 타이밍 랜덤화 · 고정상태 해독 · 석화시 위험베르 방지 · 마나부족시 자힐중단 · 인증재검사 강화",
    "0626 - 배치파일 개선 (파이썬·패키지 한방 설치) · 쫄법사/격수 배치파일 이름 변경",
    "0619 - 독·석화 감지 추가 · UI 타이머 개선 · 독해독 우선순위",
    "0618 - 격수 컴퓨터에서 쫄법사 키보드 직접 제어 · 단축키 매크로 · 격수원격제어 통합 · 창 디자인 개선",
    "0618 - 시작·따라가기·고정·줍기 토글을 격수 컴퓨터 버튼으로 조종 · 제어판 파티원 정렬 · 격수 체력 감지창 2줄 배치",
    "0617 - 피통 설정 오류 수정 · 격수감시 아이피 유지 · 마우스 속도 느리게 조정",
    "0616 - 파티원별 피통영역 드래그 설정 · 체력 퍼센트 자동감지 · 개별 힐 기준 조절",
    "0615 - 메인창과 제어판 체크박스 분리 · 파티 상태에서 선택된 파티원만 힐",
    "0612 - 버프 감지 정밀 판정 · 고정 풀 때 클릭 자동 복원 · 단축키 반응 2배 향상",
]

def open_patch_notes_panel():
    try:
        import imgui_ui
        if imgui_ui.open_patch():
            return
    except Exception:
        pass
    patch = ctk.CTkToplevel(root)
    patch.title("패치노트")
    w, h = 460, 480; sw = patch.winfo_screenwidth(); sh = patch.winfo_screenheight()
    patch.geometry(f"{w}x{h}+{int((sw-w)/2)}+{int((sh-h)/2)}")
    patch.attributes("-topmost", True); patch.focus_force()
    patch.configure(fg_color="#181825")

    ctk.CTkLabel(patch, text="최신 업데이트 (%s)" % PATCH_UPDATED_AT,
                 text_color="#f9e2af", font=("Malgun Gothic", 13, "bold")).pack(pady=(12, 6))

    # 공지
    ctk.CTkLabel(patch, text="⚠️ 본 프로그램 사용 시 책임은 사용자에게 있습니다.",
                 text_color="#f38ba8", font=("Malgun Gothic", 9, "bold")).pack(pady=(0, 1))
    ctk.CTkLabel(patch, text="감수하시고 사용하시고 6개월째 제것만 정지 없습니다.",
                 text_color="#a6adc8", font=("Malgun Gothic", 9)).pack(pady=(0, 1))
    ctk.CTkLabel(patch, text="항상 후원 감사합니다. ❤️",
                 text_color="#f9e2af", font=("Malgun Gothic", 9)).pack(pady=(0, 6))

    sf = ctk.CTkScrollableFrame(patch, fg_color="#1e1e2e", corner_radius=8, width=430, height=300)
    sf.pack(fill="both", expand=True, padx=10, pady=(0, 6))
    for item in LATEST_PATCH:
        ctk.CTkLabel(sf, text="[NEW] " + item, text_color="#a6e3a1", font=("Malgun Gothic", 10, "bold"),
                     wraplength=400, justify="left").pack(anchor="w", pady=(4, 0), padx=8)
    ctk.CTkLabel(sf, text="", height=4).pack()
    ctk.CTkLabel(sf, text="━" * 50, text_color="#45475a", font=("", 6)).pack(pady=6)
    ctk.CTkLabel(sf, text="지난 업데이트", text_color="#89b4fa", font=("Malgun Gothic", 11, "bold")).pack(anchor="w", padx=8, pady=(0, 4))
    for item in PAST_PATCHES:
        ctk.CTkLabel(sf, text=item, text_color="#6c7086", font=("Malgun Gothic", 9),
                     wraplength=400, justify="left").pack(anchor="w", pady=(2, 0), padx=8)

    ctk.CTkButton(patch, text="닫기", command=patch.destroy, fg_color="#800020", hover_color="#9e1a3a",
                  text_color="#ffffff", font=("Malgun Gothic", 12, "bold")).pack(pady=10)

def do_manual_bert():
    """END 키 / 격수 UDP — 귀환(F8 꾹) 즉시. 아두이노·뚱박스 공통 ser.write(b'C')."""
    global ser
    if not chk_end_bert or not chk_end_bert.get():
        return
    if not ser or not getattr(ser, "is_open", False):
        try:
            log_event("🏃 강제베르 실패(장치 미연결)")
        except Exception:
            pass
        return
    try:
        focus_lineage_window()
        ser.write(b"C")
        log_event("🏃 강제베르")
        stop_everything("🏃 강제베르")
    except Exception:
        pass

_end_bert_debounce = 0.0

def on_end_bert(e=None):
    global _end_bert_debounce
    now = time.time()
    if now - _end_bert_debounce < 0.5:
        return
    _end_bert_debounce = now
    if not chk_end_bert or not chk_end_bert.get():
        return
    Thread(target=do_manual_bert, daemon=True).start()

def stop_everything(reason="💤 대기 중"):
    global running, ser, root, chk_follow, chk_fix, chk_force_fix, lbl_status, _attack_follow, _attack_fix, _force_fix
    running = False; time.sleep(0.05)
    _attack_follow = False
    _attack_fix = False
    _force_fix = False
    if root:
        if chk_follow and chk_follow.get():
            if ser and ser.is_open:
                try: time.sleep(0.02); ser.write(b'U')
                except: pass
            root.after(0, lambda: chk_follow.set(False))
        if chk_fix and chk_fix.get():
            if ser and ser.is_open:
                try: time.sleep(0.05); ser.write(b'R'); ser.write(b'U'); time.sleep(0.1)
                except: pass
            root.after(0, lambda: chk_fix.set(False))
        if chk_force_fix and chk_force_fix.get():
            root.after(0, lambda: chk_force_fix.set(False))
        if lbl_status: root.after(0, lambda: lbl_status.configure(text=reason, text_color="#f38ba8"))
    if ser and ser.is_open:
        try: time.sleep(0.05); ser.write(b'R'); ser.write(b'U'); time.sleep(0.1)
        except: pass

def force_auth_exit(reason="인증 만료"):
    """인증 실패/만료 시 사냥만 멈추지 말고 프로그램 자체를 종료.
    (stop_everything만 하면 UI가 남아 다시 시작 버튼으로 잠깐 더 돌릴 수 있음)"""
    try:
        stop_everything(reason)
    except Exception:
        pass
    try:
        ctypes.windll.user32.MessageBoxW(0, f"{reason}\n프로그램을 종료합니다.", "인증", 0x10)
    except Exception:
        pass
    try:
        keyboard.unhook_all()
    except Exception:
        pass
    os._exit(0)

def get_safe_int(var, default=1200):
    try: return int(var.get())
    except: return default

def update_ui_timer():
    global running, root, lbl_buff, lbl_status
    global last_buff_seq, BUFF_SEQ_GAP, last_auth_check, loaded_pwd, last_log, lbl_log
    global shutdown_time, lbl_auth, sheet_expire_info, sheet_expire_end
    global chk_buff_on, _buff_cfg, buff_next_due, last_buff_global
    _upd_boot = True
    while True:
        if root and lbl_auth:
            auth_text = _auth_expire_text()
            root.after(0, lambda t=auth_text: lbl_auth.configure(text=t))
        if root and lbl_log and last_log:
            txt = last_log
            def _upd(t=txt):
                lbl_log.configure(state="normal")
                lbl_log.delete("1.0", "end")
                lbl_log.insert("1.0", t)
                lbl_log.see("end")
                lbl_log.configure(state="disabled")
            root.after(0, _upd)
        # 업데이트 확인: 시작 15초 후 1회, 이후 10분마다
        now_ts = time.time()
        if _upd_boot:
            _upd_boot = False
            try:
                if root:
                    root.after(3000, _check_update_stuck_on_boot)
                    root.after(15000, lambda: check_for_update(force=True))
            except Exception:
                pass
        else:
            try:
                check_for_update(force=False)
            except Exception:
                pass
        # 1분마다 구글시트에서 만료일 재조회 (표시·만료 판정 모두 시트 기준)
        if loaded_pwd and (now_ts - last_auth_check > 60):
            last_auth_check = now_ts
            cs_result, cs_info, cs_start = check_google_sheet(loaded_pwd)
            if cs_result == "ERROR":
                time.sleep(2)
                cs_result, cs_info, cs_start = check_google_sheet(loaded_pwd)
            if cs_result in ("NOT_FOUND", "ALREADY_IN_USE"):
                force_auth_exit("인증 만료")
            elif cs_result != "ERROR" and _is_code_expired(cs_info, cs_start):
                force_auth_exit("코드 만료")
            elif cs_result not in ("ERROR",):
                _sync_expire_cache(cs_info, cs_start)
        if running:
            now = time.time(); txt_parts = []
            gap_remain = max(0, int(BUFF_SEQ_GAP - (now - last_buff_seq)))
            if chk_buff_on and chk_buff_on.get():
                for hb in BUFF_HOTBARS:
                    for slot, cb, iv in _buff_cfg.get(hb, []):
                        if not cb.get():
                            continue
                        tk = buff_time_key(hb, slot)
                        due = buff_next_due.get(tk, now)
                        remain = max(max(0, int(due - now)), gap_remain)
                        hb_tag = hb if hb != "F1" else "F1"
                        txt_parts.append(f"▶ {hb_tag}-{slot}: {remain}초")
            if shutdown_time is not None:
                rem = int(shutdown_time - now)
                if rem > 0: rh = rem // 3600; rm = (rem % 3600) // 60; rs = rem % 60; txt_parts.append(f"⏰ 예약 : {rh:02d}시 {rm:02d}분 {rs:02d}초")
                else: txt_parts.append("⏰ 예약종료...!")
            if txt_parts and root and lbl_buff: root.after(0, lambda t="\n".join(txt_parts): lbl_buff.configure(text=f"✨ 버프 대기 ✨\n{t}", text_color='#a6e3a1'))
            elif root and lbl_buff: root.after(0, lambda: lbl_buff.configure(text=""))
        time.sleep(1)

def on_space_save(e=None):
    global debounce, chk_space_save, running, camera, root, lbl_saved_coord
    if not chk_space_save or not chk_space_save.get(): return
    if time.time() - debounce['space'] < 0.5: return
    debounce['space'] = time.time()
    if not running:
        pt = POINT(); ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)); cx, cy = pt.x, pt.y
        try:
            frame = camera.get_latest_frame() if camera else None
            r, g, b = get_rgb(frame, cx, cy) if frame is not None else (0,0,0)
        except: r, g, b = 0, 0, 0
        with open(COORD_FILE, 'a', encoding='utf-8') as f: f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')},{cx},{cy},{r},{g},{b}\n") 

def _sync_attack_mode_ui(mode):
    try:
        if not root:
            return
        if mode == 'follow':
            chk_fix.set(False)
            chk_follow.set(True)
        else:
            chk_follow.set(False)
            chk_fix.set(True)
            if chk_force_fix:
                chk_force_fix.set(False)
    except Exception:
        pass

def _apply_attack_mode(mode):
    """mode='follow' 따라가기 ON / mode='fix' 클릭·시프트 전부 OFF."""
    global ser, running, root, chk_follow, chk_fix, _attack_follow, _attack_fix, _fix_hw_shift_on, _force_fix
    if not running or not ser or not getattr(ser, "is_open", False):
        return
    if mode == 'follow':
        _attack_fix = False
        _attack_follow = True
        _fix_hw_shift_on = False
    else:
        _attack_follow = False
        _attack_fix = True
        _force_fix = False
        _fix_hw_shift_on = False
    try:
        if root:
            root.after(0, lambda m=mode: _sync_attack_mode_ui(m))
    except Exception:
        pass
    try:
        with _attack_ser_lock:
            if mode == 'follow':
                _ser_follow_click()
            else:
                _ser_fix_shift()
    except Exception:
        return

def _sync_force_fix_ui(on):
    try:
        if root and chk_force_fix:
            chk_force_fix.set(bool(on))
    except Exception:
        pass

def _apply_force_fix(on):
    """PageUp 강제고정 — 시프트 제자리공격 ON/OFF."""
    global _force_fix, _fix_hw_shift_on
    if not running or not ser or not getattr(ser, "is_open", False):
        return
    _force_fix = bool(on)
    try:
        if root:
            root.after(0, lambda v=on: _sync_force_fix_ui(v))
    except Exception:
        pass
    try:
        with _attack_ser_lock:
            if _force_fix:
                _ser_force_fix_on()
            else:
                _ser_force_fix_off()
    except Exception:
        return

def on_home_click_toggle(e=None):
    """Home — 따라가기 ON ↔ 전부 끔. Insert는 시작/종료만."""
    global debounce, running
    if time.time() - debounce['caps'] < 0.15:
        return
    debounce['caps'] = time.time()
    if not running:
        return
    if _attack_follow:
        _apply_attack_mode('fix')
        log_event("📌 고정 (따라가기·시프트 끄기)")
    else:
        _apply_attack_mode('follow')
        log_event("🖱️ 따라가기 ON")

def on_pageup_force_fix(e=None):
    """PageUp — 강제고정(시프트 제자리공격) 토글."""
    global debounce, running
    if time.time() - debounce.get('pageup', 0) < 0.15:
        return
    debounce['pageup'] = time.time()
    if not running:
        return
    if _force_fix:
        _apply_force_fix(False)
        log_event("📌 강제고정 OFF")
    else:
        _apply_force_fix(True)
        log_event("📌 강제고정 ON (시프트 제자리)")

def on_f4_toggle(e=None):
    global debounce, chk_loot, root, last_loot_sent_time
    if last_loot_sent_time and time.time() - last_loot_sent_time < 1.0: return
    if time.time() - debounce['f4'] < 0.15: return 
    debounce['f4'] = time.time()
    if root and chk_loot: root.after(0, lambda: chk_loot.set(not chk_loot.get()))

def _start_worker():
    """Insert(시작) 실제 처리 — 백그라운드 스레드에서 실행.
    connect_hardware()·check_google_sheet()가 느릴 수 있어서, 키보드 후킹 콜백 안에서
    직접 돌리면 Windows가 300ms 넘는 후킹을 조용히 끊어버려 Insert/Home이
    전부 안 먹히게 됨. 그래서 후킹 콜백(on_main_toggle)은 이 스레드만 띄우고 바로 반환."""
    global running, last_buff_seq, root, lbl_status
    global last_loot, loot_interval, buff_next_due, last_buff_global
    global last_self_heal, last_party_heal, last_noparty_heal
    try:
        # 워커의 대기중 재연결과 시작버튼 연결이 겹치지 않게 재연결 요청 취소
        globals()['_reconnect_req'] = False
        connect_hardware()
        if not ser or not getattr(ser, "is_open", False):
            _hw = hw_var.get() if ('hw_var' in globals() and hw_var) else HW_MODE
            msg = "○ 뚱박스 연결실패" if _hw in ("뚱박스", "KMBox") else "○ 장치 연결실패"
            if root and lbl_status:
                root.after(0, lambda m=msg: lbl_status.configure(text=m, text_color="#f85149"))
            # lbl_ard는 connect_hardware가 이미 최신 세대로 갱신함 — 여기서 또 after하면 덮어쓸 수 있음
            return
        # 시작 직 인증 즉시 재검증 — 만료 후 다시 시작해서 잠깐 더 돌리는 꼼수 차단
        # ERROR(네트워크)는 무시하고 시작 허용. USB/뚱박스 연결과 무관하게 인증만 봄.
        if loaded_pwd:
            cs_result, cs_info, cs_start = check_google_sheet(loaded_pwd)
            if cs_result in ("NOT_FOUND", "ALREADY_IN_USE") or (
                cs_result not in ("ERROR",) and _is_code_expired(cs_info, cs_start)
            ):
                force_auth_exit("인증 만료")
                return
        running = True; now = time.time()
        _fix_shift_hold_off_until = 0.0
        last_loot = now; loot_interval = random.uniform(4.0, 7.0)
        last_buff_seq = now
        last_buff_global = now
        for hb in BUFF_HOTBARS:
            for slot, cb, iv in _buff_cfg.get(hb, []):
                if cb.get():
                    schedule_buff(buff_time_key(hb, slot), get_safe_int(iv, BASE_BUFF_INTERVAL), soon=True)
        for idx, (cb_sb, hb_var, slot_var, sec_var) in enumerate(_self_buff_cfg, 1):
            if cb_sb.get():
                schedule_buff(self_buff_time_key(idx), get_safe_int(sec_var, int(saved_self_buff_sec or 1200)), soon=True)
        last_self_heal = now
        last_party_heal = now
        last_noparty_heal = now
        if root and lbl_status: root.after(0, lambda: lbl_status.configure(text="🟢 시스템 정상 가동 중", text_color="#a6e3a1"))
    except Exception:
        if root and lbl_status:
            root.after(0, lambda: lbl_status.configure(text="○ 연결 오류", text_color="#f85149"))
    finally:
        globals()['_toggle_busy'] = False

def _stop_worker():
    """정지 처리도 스레드로 — stop_everything() 안의 짧은 sleep들도 후킹 콜백 밖에서 돌게."""
    try:
        stop_everything()
    finally:
        globals()['_toggle_busy'] = False

def on_main_toggle(e=None):
    """키보드 후킹 콜백 — 무조건 즉시 반환. 실제 연결/정지는 스레드에 넘김.
    _toggle_busy로 연타 시 중복 연결·중복 정지를 막음(무반응처럼 보이는 것도 방지:
    처리 중엔 상태라벨에 '연결 확인 중...'을 바로 띄워서 눌린 건 확인 가능)."""
    global running, debounce, root, lbl_status
    if time.time() - debounce['main'] < 0.25: return 
    debounce['main'] = time.time()
    if globals().get('_toggle_busy'):
        return   # 이미 시작/정지 처리 중 — 끝날 때까지 추가 입력은 무시(중복연결 방지)
    globals()['_toggle_busy'] = True
    if not running:
        if root and lbl_status:
            root.after(0, lambda: lbl_status.configure(text="🟡 연결 확인 중...", text_color="#f9e2af"))
        Thread(target=_start_worker, daemon=True).start()
    else:
        Thread(target=_stop_worker, daemon=True).start()

def reserve_shutdown_worker():
    global shutdown_time, timer_thread_active, running, root, ser
    while timer_thread_active:
        if shutdown_time is not None:
            if time.time() >= shutdown_time:
                log_event("⏰ 예약종료 시간 도달 — 자동 베르+정지")   # 위험베르와 구분되게 반드시 로그에 남김
                if ser and ser.is_open:
                    try: ser.write(b'C'); ser.flush()
                    except: pass
                    time.sleep(4.0) 
                stop_everything("⏰ 자동 차단 정지 완료")
                time.sleep(0.5)
                if root: root.after(100, exit_app)
                break
        time.sleep(1.0)

def set_shutdown_timer(value):
    global shutdown_time
    if value == "예약OFF" or value == "예약오프": shutdown_time = None
    else:
        try: shutdown_time = time.time() + int(value.replace("시간", "").strip()) * 3600
        except: shutdown_time = None

def ensure_kmnet():
    """뚱박스용 kmNet.pyd 가 없으면 GitHub에서 파이썬 버전에 맞는 걸 자동 다운로드 후 로드."""
    global kmNet
    if kmNet is not None and hasattr(kmNet, "lcd_picture"):
        return True
    if kmNet is None:
        try:
            import kmNet as _k; kmNet = _k
        except ImportError:
            pass
        if kmNet is not None and hasattr(kmNet, "lcd_picture"):
            return True
    try:
        import ssl, importlib
        ver = f"cp{sys.version_info.major}{sys.version_info.minor}"
        fname = f"kmNet.{ver}-win_amd64.pyd"
        dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), fname)
        ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
        # lcd_picture(LCD 이미지) 함수가 있는 2024-05-27 버전. 최신 릴리스판은 이 함수가 빠져있음.
        urls = [
            f"https://raw.githubusercontent.com/blacknut0319-del/systemupdate/main/{fname}",
            f"https://raw.githubusercontent.com/kvmaibox/kmboxnet/e5bfcd00652c4ee00b2125829c52bf8c6349a6c5/python_pyd/{fname}",
        ]
        got = False
        for u in urls:
            try:
                data = urllib.request.urlopen(u, context=ctx, timeout=30).read()
                if len(data) > 10000:
                    if os.path.exists(dest):
                        try: ctypes.windll.kernel32.SetFileAttributesW(dest, 128)
                        except: pass
                    with open(dest, "wb") as f: f.write(data)
                    try: ctypes.windll.kernel32.SetFileAttributesW(dest, 2)   # 숨김 속성
                    except: pass
                    got = True; break
            except: continue
        if not got: return False
        importlib.invalidate_caches()
        if kmNet is None:
            try: import kmNet as _k; kmNet = _k
            except: pass
        return kmNet is not None
    except Exception:
        return False

# ── 뚱박스 셋팅 도우미 (뚱헌터와 동일: 랜드라이버 / Net설정도구 / 메뉴얼) ──
_KMBOX_SETUP_ZIP_URL = (
    "https://raw.githubusercontent.com/blacknut0319-del/systemupdate/main/"
    "%EB%9A%B1%EB%B0%95%EC%8A%A4_%EC%85%8B%ED%8C%85/"
    "%EB%9A%B1%EB%B0%95%EC%8A%A4_%EC%85%8B%ED%8C%85_%EC%98%AC%EC%9D%B8%EC%9B%90.zip"
)
_KMBOX_GUIDE_URL = (
    "https://raw.githubusercontent.com/blacknut0319-del/systemupdate/main/"
    "%EB%9A%B1%EB%B0%95%EC%8A%A4_%EC%85%8B%ED%8C%85/"
    "%EC%84%A4%EC%A0%95%EB%8F%84%EA%B5%AC_%ED%95%9C%EA%B8%80%ED%86%B5%EC%97%AD.html"
)
_kmbox_setup_busy = False
_kmbox_translator_dlg = None

def _kmbox_runtime_dir():
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    d = os.path.join(base, "ddong_healer", "kmbox_runtime")
    os.makedirs(d, exist_ok=True)
    return d

def _kmbox_find_file(*names):
    """런타임/하위폴더에서 파일 찾기."""
    rd = _kmbox_runtime_dir()
    for root_dir, _, files in os.walk(rd):
        lower = {f.lower(): f for f in files}
        for name in names:
            hit = lower.get(name.lower())
            if hit:
                return os.path.join(root_dir, hit)
    return None

def ensure_kmbox_setup_pack():
    """GitHub 올인원 zip을 받아 %LOCALAPPDATA%\\ddong_healer\\kmbox_runtime 에 풀어둔다."""
    import zipfile
    import ssl as _ssl
    rd = _kmbox_runtime_dir()
    driver = _kmbox_find_file("WCHUSBNIC.EXE")
    setup = _kmbox_find_file("kmboxNet_setup.exe")
    guide = _kmbox_find_file("설정도구_한글통역.html")
    if driver and setup and guide:
        return True, rd
    zip_path = os.path.join(rd, "뚱박스_셋팅_올인원.zip")
    ctx = _ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = _ssl.CERT_NONE
    req = urllib.request.Request(
        _KMBOX_SETUP_ZIP_URL + "?t=%d" % int(time.time()),
        headers={"User-Agent": "ddong-healer", "Cache-Control": "no-cache"},
    )
    with urllib.request.urlopen(req, timeout=120, context=ctx) as r:
        data = r.read()
    if len(data) < 100000:
        return False, "셋팅 파일 다운로드 실패 (용량 이상)"
    with open(zip_path, "wb") as f:
        f.write(data)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(rd)
    driver = _kmbox_find_file("WCHUSBNIC.EXE")
    setup = _kmbox_find_file("kmboxNet_setup.exe")
    if not driver or not setup:
        return False, "셋팅 파일 압축 해제 후 실행파일을 찾지 못했어요"
    try:
        open(os.path.join(rd, "kmbox_ready.flag"), "w", encoding="utf-8").write("ok")
    except Exception:
        pass
    return True, rd

def _kmbox_setup_action(kind):
    """kind: driver | setup | manual — 백그라운드에서 zip확보 후 실행."""
    global _kmbox_setup_busy
    if _kmbox_setup_busy:
        _ui_alert("뚱박스 셋팅", "이미 준비 중이에요. 잠시만 기다려 주세요.")
        return
    _kmbox_setup_busy = True
    try:
        log_event("⬇ 뚱박스 셋팅 준비중...")
    except Exception:
        pass

    def _work():
        global _kmbox_setup_busy
        try:
            ok, info = ensure_kmbox_setup_pack()
            if not ok:
                def _fail():
                    _ui_alert("뚱박스 셋팅", str(info), "error")
                if root:
                    root.after(0, _fail)
                return
            if kind == "driver":
                path = _kmbox_find_file("WCHUSBNIC.EXE")
                if not path:
                    raise RuntimeError("WCHUSBNIC.EXE 없음")
                subprocess.Popen([path], cwd=os.path.dirname(path), shell=True)
                msg = "랜드라이버 설치를 실행했어요.\n설치 후 PC 재부팅을 권장합니다."
            elif kind == "setup":
                launch_kmbox_official_setup_with_guide()
                msg = "뚱박스 설정도구 + 한글 통역 창을 열었어요.\n통역 창 보면서 连接盒子(연결) 하세요."
            else:
                path = _kmbox_find_file("랜설정_메뉴얼.html", "랜설정_메뉴얼.txt")
                if not path:
                    raise RuntimeError("메뉴얼 파일 없음")
                os.startfile(path)
                msg = "랜설정 메뉴얼을 열었어요."
            def _ok():
                try:
                    log_event(f"✅ 뚱박스 셋팅: {kind}")
                except Exception:
                    pass
                _ui_alert("뚱박스 셋팅", msg)
            if root:
                root.after(0, _ok)
        except Exception as e:
            def _err():
                _ui_alert("뚱박스 셋팅", f"실패: {e}", "error")
            try:
                if root:
                    root.after(0, _err)
            except Exception:
                pass
        finally:
            _kmbox_setup_busy = False

    Thread(target=_work, daemon=True).start()

def _kmbox_open_html_guide():
    guide = _kmbox_find_file("설정도구_한글통역.html")
    if guide:
        try:
            os.startfile(guide)
            return
        except Exception:
            pass
    try:
        import webbrowser
        webbrowser.open(_KMBOX_GUIDE_URL)
    except Exception:
        pass

def _kmbox_open_adapters():
    try:
        subprocess.Popen(["ncpa.cpl"], shell=True)
    except Exception as ex:
        _ui_alert("뚱박스 셋팅", str(ex), "error")

def _kmbox_open_manual():
    path = _kmbox_find_file("랜설정_메뉴얼.html", "랜설정_메뉴얼.txt")
    if path:
        os.startfile(path)
    else:
        _ui_alert("뚱박스 셋팅", "메뉴얼 파일을 찾지 못했어요.")

def _kmbox_open_chinese_tool():
    def _work():
        try:
            ok, info = ensure_kmbox_setup_pack()
            if not ok:
                root.after(0, lambda: _ui_alert("뚱박스 셋팅", str(info), "error"))
                return
            launch_kmbox_official_setup_with_guide()
        except Exception as ex:
            root.after(0, lambda: _ui_alert("뚱박스 셋팅", str(ex), "error"))
    Thread(target=_work, daemon=True).start()

def open_kmbox_setup_translator_dlg():
    """설정도구 한글 통역 — 앱 안 창 (파일 없어도 항상 뜸)."""
    global root, _kmbox_translator_dlg
    if not root:
        return
    try:
        import imgui_ui
        if imgui_ui.open_km_trans():
            return
    except Exception:
        pass
    try:
        if _kmbox_translator_dlg and _kmbox_translator_dlg.winfo_exists():
            _kmbox_translator_dlg.lift()
            _kmbox_translator_dlg.focus_force()
            return
    except Exception:
        pass
    dlg = ctk.CTkToplevel(root)
    _kmbox_translator_dlg = dlg
    dlg.title("뚱박스 설정도구 — 한글 통역")
    dlg.attributes("-topmost", True)
    dlg.configure(fg_color="#1e1e2e")
    sw, sh = dlg.winfo_screenwidth(), dlg.winfo_screenheight()
    dlg.geometry(f"440x560+{max(0, sw-460)}+{max(0, (sh-560)//2)}")
    ctk.CTkLabel(dlg, text="설정도구 한글 통역", font=("Malgun Gothic", 14, "bold"), text_color="#cba6f7").pack(pady=(10, 4))
    ctk.CTkLabel(dlg, text="옆 중국어 프로그램 보면서 이 창만 보세요", font=("Malgun Gothic", 10), text_color="#a6adc8").pack(pady=(0, 8))
    txt = ctk.CTkTextbox(dlg, width=410, height=430, font=("Malgun Gothic", 10), fg_color="#181825", text_color="#cdd6f4")
    txt.pack(padx=12, pady=4)
    body = (
        "【① 가장 먼저】\n"
        "  连接盒子  =  뚱박스 연결 버튼 (클릭!)\n"
        "  IP / Port / UUID = 뚱박스 LCD 숫자 그대로\n\n"
        "【② 뚱힐러 사용자 필수】\n"
        "  禁用Bypass  =  Bypass 끄기 (체크!) ← KM 모드\n"
        "  启用Bypass  =  Bypass 켜기 (건드리지 마세요)\n\n"
        "【자주 보는 글자】\n"
        "  网络畅通     =  연결 OK\n"
        "  网络不通     =  연결 실패 → 드라이버·PC IP 확인\n"
        "  键鼠功能测试  =  키·마우스 테스트 (안 써도 됨)\n"
        "  硬件曲线修正  =  마우스 궤적 보정 (체크 해제 유지)\n"
        "  盒子固件升级  =  펌웨어 업그레이드 (필요할 때만)\n\n"
        "【뚱박스 LCD 아이콘】\n"
        "  游戏机口 ✓  =  게임 PC 연결됨\n"
        "  网口 ✓      =  뚱힐러/설정도구 연결됨\n"
        "  打叉 ✗      =  끊김\n\n"
        "뚱힐러만 쓸 때: 연결 + 禁用Bypass 후\n"
        "뚱힐러 IP/포트/UUID 입력 → 설정저장 → 시작"
    )
    txt.insert("1.0", body)
    txt.configure(state="disabled")

    def _open_html():
        guide = _kmbox_find_file("설정도구_한글통역.html")
        if guide:
            try:
                os.startfile(guide)
                return
            except Exception:
                pass
        try:
            import webbrowser
            webbrowser.open(_KMBOX_GUIDE_URL)
        except Exception:
            pass

    row = ctk.CTkFrame(dlg, fg_color="transparent")
    row.pack(fill="x", padx=12, pady=6)
    ctk.CTkButton(row, text="상세 통역(브라우저)", command=_open_html, height=28, font=("Malgun Gothic", 10, "bold"), fg_color="#313244", hover_color="#45475a").pack(side="left", expand=True, fill="x", padx=(0, 4))
    ctk.CTkButton(row, text="닫기", command=dlg.destroy, height=28, font=("Malgun Gothic", 10, "bold"), fg_color="#45475a", hover_color="#585b70").pack(side="left", expand=True, fill="x", padx=(4, 0))
    dlg.protocol("WM_DELETE_WINDOW", lambda: (dlg.destroy(), globals().__setitem__("_kmbox_translator_dlg", None)))

def launch_kmbox_official_setup_with_guide():
    """중국어 kmboxNet_setup.exe + 한글 통역 창(앱 내) 동시 오픈."""
    if root:
        root.after(0, open_kmbox_setup_translator_dlg)
    path = _kmbox_find_file("kmboxNet_setup.exe")
    if not path:
        raise RuntimeError("kmboxNet_setup.exe 없음")
    subprocess.Popen([path], cwd=os.path.dirname(path), shell=True)
    guide = _kmbox_find_file("설정도구_한글통역.html")
    if guide:
        try:
            os.startfile(guide)
        except Exception:
            try:
                import webbrowser
                webbrowser.open("file:///" + guide.replace("\\", "/"))
            except Exception:
                pass

def _kmbox_suggest_pc_ip(box_ip):
    """박스 IP와 같은 대역의 PC용 IP 제안."""
    try:
        parts = str(box_ip or "").strip().split(".")
        if len(parts) == 4 and all(p.isdigit() for p in parts):
            last = int(parts[3])
            pc_last = 100 if last != 100 else 101
            return ".".join(parts[:3] + [str(pc_last)])
    except Exception:
        pass
    return "192.168.2.100"

def open_kmbox_korean_setup():
    """Net 설정 — 한글 안내 (중국어 kmboxNet_setup.exe 대신)."""
    global root
    if not root:
        return
    try:
        ensure_kmbox_setup_pack()
    except Exception:
        pass
    box_ip = (ent_km_ip.get().strip() if 'ent_km_ip' in globals() and ent_km_ip else KM_IP) or "192.168.2.188"
    pc_ip = _kmbox_suggest_pc_ip(box_ip)
    try:
        import imgui_ui
        if imgui_ui.open_km_ip(box_ip, pc_ip):
            return
    except Exception:
        pass
    dlg = ctk.CTkToplevel(root)
    dlg.title("뚱박스 Net IP 설정 (한글)")
    dlg.attributes("-topmost", True)
    dlg.configure(fg_color="#1e1e2e")
    sw, sh = dlg.winfo_screenwidth(), dlg.winfo_screenheight()
    dlg.geometry(f"420x520+{int((sw-420)/2)}+{int((sh-520)/2)}")
    ctk.CTkLabel(dlg, text="뚱박스 랜(IP) 설정", font=("Malgun Gothic", 14, "bold"), text_color="#cba6f7").pack(pady=(12, 4))
    ctk.CTkLabel(dlg, text="박스 화면 IP와 PC가 같은 대역이어야 연결됩니다.", font=("Malgun Gothic", 10), text_color="#a6adc8").pack(pady=(0, 8))
    info = ctk.CTkFrame(dlg, fg_color="#313244", corner_radius=8)
    info.pack(fill="x", padx=14, pady=4)
    ctk.CTkLabel(info, text=f"박스 IP (위 입력칸):  {box_ip}", font=("Malgun Gothic", 11, "bold"), text_color="#a6e3a1").pack(anchor="w", padx=12, pady=(10, 2))
    ctk.CTkLabel(info, text=f"PC에 넣을 IP 예시:  {pc_ip}", font=("Malgun Gothic", 11, "bold"), text_color="#89b4fa").pack(anchor="w", padx=12, pady=(2, 10))
    txt = ctk.CTkTextbox(dlg, width=392, height=240, font=("Malgun Gothic", 10), fg_color="#181825", text_color="#cdd6f4")
    txt.pack(padx=14, pady=8)
    guide = (
        "【설정 순서】\n"
        "1. [드라이버] 버튼으로 랜드라이버 설치 (처음 1회)\n"
        "2. 아래 [네트워크 어댑터 열기] 클릭\n"
        "3. 새로 생긴 이더넷(USB/WCH 등) 우클릭 → 속성\n"
        "4. IPv4 → 다음 IP 주소 사용\n"
        f"     IP: {pc_ip}\n"
        "     서브넷: 255.255.255.0\n"
        "     게이트웨이·DNS: 비워둠\n"
        "5. 위 폼에 박스 IP·포트·UUID 입력 후 [설정저장]\n\n"
        "※ Wi-Fi/인터넷 쓰는 어댑터는 건드리지 마세요.\n"
        "※ ping 테스트: cmd → ping " + box_ip + "\n"
    )
    txt.insert("1.0", guide)
    txt.configure(state="disabled")
    btn_row = ctk.CTkFrame(dlg, fg_color="transparent")
    btn_row.pack(fill="x", padx=14, pady=4)
    btn_row.grid_columnconfigure(0, weight=1)
    btn_row.grid_columnconfigure(1, weight=1)

    def _open_adapters():
        try:
            subprocess.Popen(["ncpa.cpl"], shell=True)
        except Exception as ex:
            messagebox.showerror("뚱박스 셋팅", str(ex))

    def _open_manual():
        path = _kmbox_find_file("랜설정_메뉴얼.html", "랜설정_메뉴얼.txt")
        if path:
            os.startfile(path)
        else:
            messagebox.showinfo("뚱박스 셋팅", "메뉴얼 파일을 찾지 못했어요.")

    def _open_chinese_tool():
        def _work():
            try:
                ok, info = ensure_kmbox_setup_pack()
                if not ok:
                    root.after(0, lambda: messagebox.showerror("뚱박스 셋팅", str(info)))
                    return
                launch_kmbox_official_setup_with_guide()
            except Exception as ex:
                root.after(0, lambda: messagebox.showerror("뚱박스 셋팅", str(ex)))
        Thread(target=_work, daemon=True).start()

    ctk.CTkButton(btn_row, text="네트워크 어댑터 열기", command=_open_adapters, height=30, font=("Malgun Gothic", 10, "bold"), fg_color="#89b4fa", hover_color="#74c7ec", text_color="#1e1e2e").grid(row=0, column=0, padx=(0, 4), sticky="ew")
    ctk.CTkButton(btn_row, text="한글 메뉴얼", command=_open_manual, height=30, font=("Malgun Gothic", 10, "bold"), fg_color="#313244", hover_color="#45475a").grid(row=0, column=1, padx=(4, 0), sticky="ew")
    ctk.CTkButton(dlg, text="공식 설정도구 + 한글통역", command=_open_chinese_tool, height=28, font=("Malgun Gothic", 10, "bold"), fg_color="#a6e3a1", hover_color="#7bd88f", text_color="#1e1e2e").pack(fill="x", padx=14, pady=(4, 2))
    ctk.CTkButton(dlg, text="닫기", command=dlg.destroy, height=28, font=("Malgun Gothic", 10, "bold"), fg_color="#45475a", hover_color="#585b70").pack(fill="x", padx=14, pady=(2, 12))

def on_kmbox_driver_click():
    _kmbox_setup_action("driver")

def on_kmbox_setup_click():
    open_kmbox_korean_setup()

def on_kmbox_net_setup_click():
    _kmbox_setup_action("setup")

def on_kmbox_manual_click():
    _kmbox_setup_action("manual")

def ensure_logo():
    """뚱박스 LCD 로고(뚱힐러.gif) 없으면 GitHub에서 자동 다운로드(숨김) 후 프레임 로드."""
    global _logo_frames, _logo_delay
    if _logo_frames:
        return True
    try:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "뚱힐러.gif")
        if not os.path.exists(path):
            import ssl
            ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
            for u in ["https://raw.githubusercontent.com/blacknut0319-del/systemupdate/main/%EB%9A%B1%ED%9E%90%EB%9F%AC.gif"]:
                try:
                    data = urllib.request.urlopen(u, context=ctx, timeout=30).read()
                    if len(data) > 1000:
                        with open(path, "wb") as f: f.write(data)
                        try: ctypes.windll.kernel32.SetFileAttributesW(path, 2)
                        except: pass
                        break
                except: continue
        if not os.path.exists(path):
            return False
        im = Image.open(path)
        _logo_delay = (im.info.get("duration") or 80) / 1000.0
        fr = []
        for i in range(getattr(im, "n_frames", 1)):
            im.seek(i)
            arr = np.array(im.convert("RGB").resize((128, 160)), dtype=np.uint8)[:, :, ::-1]  # RGB→BGR
            fr.append(np.ascontiguousarray(arr).flatten())
        _logo_frames = fr
        return True
    except Exception:
        return False

def lcd_logo_worker():
    """사냥 중(running)일 때만 뚱박스 LCD에 로고 애니 재생. 멈추면 박스 정보 놔둠."""
    while True:
        try:
            if running and _logo_frames and ser is not None and getattr(ser, "is_open", False) and hasattr(ser, "lcd"):
                for f in _logo_frames:
                    if not running: break
                    ser.lcd(f)
                    time.sleep(_logo_delay)
            else:
                time.sleep(0.3)
        except Exception:
            time.sleep(0.3)

def _set_hw_label(text, color, gen):
    """장치 상태 라벨 갱신 — gen이 최신(_hw_status_gen)이 아니면 무시(예전 실패문구가 성공을 덮는 것 방지)."""
    def _apply(t=text, c=color, g=gen):
        if g != globals().get('_hw_status_gen'):
            return
        if lbl_ard:
            try: lbl_ard.configure(text=t, text_color=c)
            except Exception: pass
    if root:
        try: root.after(0, _apply)
        except Exception: pass

def _load_flash_module():
    """flash_arduino.py — 펌업마다 GitHub 최신본 받음. TEMP 옛 캐시 쓰면 흔들림 hex 재구움."""
    import importlib.util
    import tempfile

    def _load_path(path):
        try:
            spec = importlib.util.spec_from_file_location("ddong_flash_arduino", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "flash"):
                return mod
        except Exception:
            return None
        return None

    tmp = os.path.join(tempfile.gettempdir(), "ddong_firmware", "flash_arduino.py")
    try:
        import ssl
        ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
        url = (
            "https://raw.githubusercontent.com/blacknut0319-del/systemupdate/main/flash_arduino.py"
            f"?t={int(time.time())}"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "ddong", "Cache-Control": "no-cache"})
        data = urllib.request.urlopen(req, timeout=30, context=ctx).read()
        if len(data) > 500 and b"def flash" in data:
            os.makedirs(os.path.dirname(tmp), exist_ok=True)
            with open(tmp, "wb") as f:
                f.write(data)
            mod = _load_path(tmp)
            if mod:
                return mod
    except Exception:
        pass

    cands = []
    dd = os.environ.get("DDONG_APP_DIR", "").strip()
    if dd:
        cands.append(os.path.join(dd, "flash_arduino.py"))
    try:
        cands.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "flash_arduino.py"))
    except Exception:
        pass
    cands.append(os.path.join(os.path.expanduser("~"), "Desktop", "뚱힐러_github", "flash_arduino.py"))
    cands.append(tmp)
    for path in cands:
        if path and os.path.isfile(path):
            mod = _load_path(path)
            if mod:
                return mod
    return None

def _call_flash(mod, callback, port, ask_manual_reset=None):
    """flash() 시그니처에 맞게 인자 전달 — 구버전 모듈이어도 TypeError 안 나게."""
    import inspect
    kwargs = {}
    try:
        params = inspect.signature(mod.flash).parameters
    except Exception:
        params = {}
    if "callback" in params:
        kwargs["callback"] = callback
    if "port" in params:
        kwargs["port"] = port
    if "ask_manual_reset" in params and ask_manual_reset is not None:
        kwargs["ask_manual_reset"] = ask_manual_reset
    return mod.flash(**kwargs)

def probe_arduino_fw(ser_obj=None, timeout=2.5):
    """시리얼로 'V'를 보내 펌웨어 식별 문자열을 읽음.
    워치독 펌이면 'DDONG-WDT' 응답. 옛 펌/무응답이면 ''."""
    s = ser_obj if ser_obj is not None else ser
    if not s or not getattr(s, "is_open", False):
        return ""
    # 뚱박스는 시리얼 프로토콜 다름
    if s.__class__.__name__ == "KmBox":
        return ""
    try:
        try:
            s.reset_input_buffer()
        except Exception:
            while getattr(s, "in_waiting", 0):
                s.read(s.in_waiting)
        s.write(b"V")
        try:
            s.flush()
        except Exception:
            pass
        buf = b""
        t0 = time.time()
        while time.time() - t0 < timeout:
            n = getattr(s, "in_waiting", 0) or 0
            if n:
                buf += s.read(n)
                if b"DDONG" in buf or b"\n" in buf:
                    break
            time.sleep(0.05)
        return buf.decode("ascii", errors="ignore").strip()
    except Exception:
        return ""

def check_fw_wdt(ser_obj=None):
    """(ok, detail) — ok=True 이면 최신 펌(DDONG-V / DDONG-WDT) 확인."""
    ver = refresh_fw_version(ser_obj, log=False, retries=7)
    u = (ver or "").upper().replace(" ", "")
    if ver and ("DDONG-V" in u or "DDONG-WDT" in u):
        return True, ver
    if ver:
        return False, ver
    return False, ""

def _fw_is_wdt4(ver=None):
    v = (ver if ver is not None else _fw_version_str) or ""
    u = v.upper().replace(" ", "")
    return "DDONG-V4" in u or "DDONG-WDT4" in u

def refresh_fw_version(ser_obj=None, log=False, retries=6):
    """연결·펌확인·펌업 후 펌 버전 캐시 갱신.
    옛 펌은 setup()에 delay(3초) 있어서 첫 V 조회가 빈칸일 수 있음 → 재시도."""
    global _fw_version_str, _fw_wdt4
    s = ser_obj if ser_obj is not None else ser
    ver = ""
    for i in range(max(1, retries)):
        if i > 0:
            time.sleep(0.55)
        if not s or not getattr(s, "is_open", False):
            break
        ver = probe_arduino_fw(s, timeout=2.0 if i == 0 else 2.5)
        if ver and "DDONG" in ver.upper():
            break
    _fw_version_str = ver
    _fw_wdt4 = _fw_is_wdt4(ver)
    if root:
        try:
            root.after(0, _apply_wheel_heal_ui)
        except Exception:
            pass
    if log and ver:
        extra = " (휠힐 가능)" if _fw_wdt4 else ""
        log_event(f"🔌 펌 {ver}{extra}")
        if _fw_wdt4:
            try:
                root.after(0, lambda: lbl_ard.configure(text="● 펌 OK", text_color="#3fb950"))
            except Exception:
                pass
    return ver

def _apply_wheel_heal_ui():
    """WDT4면 휠힐 항상 ON 표시."""
    tw = globals().get("toggle_wheel_heal")
    cw = globals().get("chk_wheel_heal")
    if not tw or not cw:
        return
    if _fw_wdt4:
        cw.set(True)
        tw.lbl.configure(text="휠힐(항상ON)", text_color="#a6e3a1")
    else:
        cw.set(False)
        tw.lbl.configure(text="휠힐(WDT4필요)", text_color="#6c7086")

def wheel_heal_enabled():
    """최신 펌웨어(WDT4)면 일반 힐은 가운데 휠클릭. 상위힐은 별도(좌클릭)."""
    return bool(_fw_wdt4)


def heal_target_click():
    """힐 대상 지정 클릭만. 휠힐 ON→M, OFF→K. 버프·해독 등은 항상 K."""
    return 'M' if wheel_heal_enabled() else 'K'


def run_target_heal(hotbar, slot, end_delay=0.08, use_wheel=None):
    """타겟 힐 — ① 핫바+힐슬롯 ② 대상 클릭(휠 또는 좌클릭).
    use_wheel=None이면 휠힐 설정 따름. 상위힐은 use_wheel=False(좌클릭)."""
    global ser, running
    if not running or not ser or not getattr(ser, "is_open", False):
        return False
    if use_wheel is None:
        use_wheel = wheel_heal_enabled()
    click = 'M' if use_wheel else 'K'
    keys = heal_action_keys(hotbar, slot)
    execute_keys(keys, max(0.10, end_delay * 0.35), skip_follow_toggle=True, key_gap=(0.09, 0.16))
    if not running or not ser or not getattr(ser, "is_open", False):
        return False
    focus_lineage_window()
    time.sleep(0.02)
    ser.write(click.encode())
    time.sleep(random.uniform(max(0.05, end_delay * 0.55), max(end_delay, end_delay * 1.1)))
    return True

def on_fw_check_click():
    """제어판 [확인] — 연결된 뚱USB 펌 버전 조회 (V 명령)."""
    if hw_var.get() in ("뚱박스", "KMBox"):
        log_event("⚠️ 펌 확인은 뚱USB 전용")
        _ui_alert("펌 확인", "뚱USB(아두이노) 연결 상태에서만 확인할 수 있습니다.")
        return
    if not ser or not getattr(ser, "is_open", False):
        # 연결 안 되어 있으면 한번 시도
        try:
            connect_hardware()
        except Exception:
            pass
    if not ser or not getattr(ser, "is_open", False):
        log_event("❌ 펌 확인 실패 — 장치 미연결")
        _ui_alert("펌 확인", "뚱USB가 연결되지 않았습니다.", "error")
        return
    ok, detail = check_fw_wdt()
    if ok:
        log_event(f"✅ 펌 확인 OK — {detail}" + (" · 휠힐 가능" if _fw_wdt4 else ""))
        try:
            lbl_ard.configure(text="● 펌 OK", text_color="#3fb950")
        except Exception:
            pass
        _ui_alert("펌 확인", f"펌웨어 확인됨.\n응답: {detail}")
    else:
        msg = detail if detail else "(응답 없음)"
        log_event(f"⚠️ 펌 확인 실패 — {msg}")
        _ui_alert(
            "펌 확인",
            "펌 버전 응답이 없습니다.\n\n"
            "· Insert로 연결한 뒤 3~4초 기다렸다가 다시 [확인]\n"
            "· IDE로 올린 코드에 V(버전조회) 명령이 있는지 확인\n"
            "  (뚱힐러_github firmware/cs_firmware.ino 또는 최신 아두이노코드.txt)\n"
            "· [펌업]으로 최신 hex 올리면 해결되는 경우가 많습니다.",
            "warning",
        )

def on_fw_flash_click():
    """제어판 [펌업] — 시리얼 닫고 아두이노에 최신 hex 업로드."""
    global ser, running, SERIAL_PORT, _fw_flash_busy
    if _fw_flash_busy:
        log_event("⏳ 펌업 진행 중…")
        return
    if hw_var.get() in ("뚱박스", "KMBox"):
        log_event("⚠️ 펌업은 뚱USB(아두이노) 전용입니다")
        _ui_alert("펌업", "펌업은 뚱USB(아두이노) 전용입니다.\n장치를 뚱USB로 바꾼 뒤 다시 눌러주세요.")
        return
    if running:
        def _go():
            stop_everything("펌업 전 정지")
            _begin_fw_flash()
        _ui_yesno("펌업", "사냥 중입니다.\n정지한 뒤 펌웨어를 업로드할까요?", _go)
        return
    _ui_yesno(
        "펌업",
        "뚱USB(아두이노)에 최신 펌웨어를 구워 넣을까요?\n업로드 중엔 USB를 뽑지 마세요.",
        _begin_fw_flash,
    )

def _begin_fw_flash():
    global ser, running, SERIAL_PORT, _fw_flash_busy
    if _fw_flash_busy:
        log_event("⏳ 펌업 진행 중…")
        return

    globals()['_fw_flash_busy'] = True
    try:
        lbl_ard.configure(text="⏳ 펌업 준비…", text_color="#f9e2af")
    except Exception:
        pass
    log_event("🔌 펌업 시작 — 장치 연결 해제 중")

    def _progress(pct, msg):
        def _ui():
            try:
                lbl_ard.configure(text=f"⏳ 펌업 {pct}%", text_color="#f9e2af")
            except Exception:
                pass
            log_event(f"🔌 {msg}")
        try:
            root.after(0, _ui)
        except Exception:
            pass

    def _worker():
        global ser, SERIAL_PORT
        ok, msg = False, "실패"
        wdt_ok, wdt_detail = False, ""
        try:
            # 연결에 이미 쓰던 COM을 펌업에도 그대로 사용 (검색 조건 불일치 방지)
            preferred = SERIAL_PORT
            with _hw_lock:
                try:
                    if ser:
                        ser.close()
                except Exception:
                    pass
                ser = None
            # Windows 시리얼 핸들 완전 해제 + 좀비 avrdude 정리 시간
            time.sleep(2.0)
            alive = {p.device for p in serial.tools.list_ports.comports()}
            found = auto_find_arduino()
            use_port = preferred if preferred in alive else (found or preferred)
            if use_port:
                log_event(f"🔌 펌업 포트: {use_port}")
            mod = _load_flash_module()
            if mod is None:
                ok, msg = False, "flash_arduino 로드 실패 (인터넷/파일 확인)"
            else:
                try:
                    if hasattr(mod, "_kill_stray_avrdude"):
                        mod._kill_stray_avrdude()
                except Exception:
                    pass

                # 워커 스레드에서 UI 확인창 — 메인스레드로 물어보고 기다림
                def _ask_manual_reset():
                    box = {"ok": False}
                    ev = _threading.Event()

                    def _ask():
                        def _yes():
                            box["ok"] = True
                            ev.set()
                        def _no():
                            box["ok"] = False
                            ev.set()
                        try:
                            _ui_yesno(
                                "펌업 재시도",
                                "자동 펌업이 실패했습니다.\n\n"
                                "【옛 워치독 WDT1/2 펌】이면 1200 자동리셋이 안 됩니다.\n"
                                "USB 케이블을 뽑았다 다시 꽂은 뒤 【예】를 눌러주세요.\n"
                                "(리셋 버튼 없어도 됩니다 · 20초 안에 재시도)\n\n"
                                "WDT3/4 또는 새 펌이면 위만으로 됩니다.",
                                _yes,
                                _no,
                            )
                        except Exception:
                            box["ok"] = True
                            ev.set()

                    try:
                        root.after(0, _ask)
                    except Exception:
                        box["ok"] = True
                        ev.set()
                    ev.wait(timeout=120)
                    return box["ok"]

                ret = _call_flash(
                    mod,
                    callback=_progress,
                    port=use_port or None,
                    ask_manual_reset=_ask_manual_reset,
                )
                if isinstance(ret, tuple) and len(ret) >= 2:
                    ok, msg = ret[0], ret[1]
                else:
                    ok, msg = bool(ret), str(ret)
            if ok:
                # 업로드 성공이면 워치독 hex가 들어간 것. 확인응답(V)은 보너스.
                time.sleep(3.5)
                found = auto_find_arduino()
                if found:
                    SERIAL_PORT = found
                try:
                    connect_hardware()
                except Exception:
                    pass
                time.sleep(0.5)
                wdt_ok, wdt_detail = check_fw_wdt()
                refresh_fw_version(ser, log=False)
        except Exception as e:
            ok, msg = False, str(e)
        def _done():
            globals()['_fw_flash_busy'] = False
            if ok:
                if wdt_ok:
                    log_event(f"✅ 펌업+확인 OK — {wdt_detail}")
                    try:
                        lbl_ard.configure(text="● 펌 OK", text_color="#3fb950")
                    except Exception:
                        pass
                    _ui_alert(
                        "펌업 완료",
                        f"업로드 성공 + 펌 확인됨.\n응답: {wdt_detail}",
                    )
                else:
                    # avrdude 성공이면 펌은 들어간 것 — V응답은 없어도 실패로 치지 않음
                    log_event(f"✅ 펌업 완료 — {msg} (확인응답은 나중에 [확인]으로)")
                    _ui_alert(
                        "펌업 완료",
                        "업로드 성공했습니다.\n"
                        "원하면 몇 초 뒤 [확인]을 눌러 펌 버전을 보세요.",
                    )
            else:
                log_event(f"❌ 펌업 실패 — {msg}")
                try:
                    lbl_ard.configure(text="○ 펌업실패", text_color="#f85149")
                except Exception:
                    pass
                try:
                    _ui_alert("펌업 실패", msg, "error")
                except Exception:
                    pass
        try:
            root.after(0, _done)
        except Exception:
            globals()['_fw_flash_busy'] = False

    Thread(target=_worker, daemon=True).start()

def refresh_device_status():
    """대기 중 장치 라벨 갱신. 뚱USB는 포트 탐색만(연결은 Insert), 뚱박스는 Insert 안내.
    드롭다운 변경으로 kmNet.init 하지 않음(응답없음 방지)."""
    global SERIAL_PORT
    if globals().get('_fw_flash_busy'):
        return
    globals()['_hw_status_gen'] = int(globals().get('_hw_status_gen', 0)) + 1
    gen = globals()['_hw_status_gen']
    try:
        _hw = hw_var.get() if ('hw_var' in globals() and hw_var) else HW_MODE
    except Exception:
        _hw = HW_MODE
    if _hw in ("뚱박스", "KMBox"):
        if ser is not None and getattr(ser, "is_open", False) and ser.__class__.__name__ == "KmBox":
            _set_hw_label("● 박스OK", '#3fb950', gen)
        else:
            _set_hw_label("○ 박스대기", '#f9e2af', gen)
        return
    # 뚱USB: 포트 다시 찾기 → 라벨 표시 (시리얼 open은 Insert 때)
    found = auto_find_arduino()
    if found:
        SERIAL_PORT = found
        _set_hw_label(f"● {found}", '#3fb950', gen)
    else:
        _set_hw_label("○ USB없음", '#f85149', gen)

def connect_hardware():
    """하드웨어 연결 (드롭다운 선택에 따라 아두이노/KMBox). 재연결에도 재사용.
    시작버튼과 워커가 동시에 부르면 COM포트 충돌로 한쪽만 실패→라벨만 실패로 남는
    문제가 있어서 Lock으로 직렬화하고, 라벨은 세대번호로 최신 결과만 반영."""
    global ser, SERIAL_PORT
    # 펌업 중엔 COM을 절대 다시 열지 않음 (부트로더 가로채기 방지)
    if globals().get('_fw_flash_busy'):
        return False
    with _hw_lock:
        globals()['_hw_status_gen'] = int(globals().get('_hw_status_gen', 0)) + 1
        gen = globals()['_hw_status_gen']
        try:
            if ser: ser.close()
        except Exception:
            pass
        ser = None
        try:
            _hw = hw_var.get() if ('hw_var' in globals() and hw_var) else HW_MODE
            if _hw in ("뚱박스", "KMBox"):
                if kmNet is None or not hasattr(kmNet, "lcd_picture"):
                    _set_hw_label("⬇ 뚱박스 드라이버 받는중", '#f9e2af', gen)
                    if not ensure_kmnet():
                        _set_hw_label("○ kmNet 없음", '#f85149', gen)
                        return False
                _kip = ent_km_ip.get().strip() if ('ent_km_ip' in globals() and ent_km_ip and ent_km_ip.get().strip()) else KM_IP
                _kport = ent_km_port.get().strip() if ('ent_km_port' in globals() and ent_km_port and ent_km_port.get().strip()) else KM_PORT
                _kmac = ent_km_mac.get().strip() if ('ent_km_mac' in globals() and ent_km_mac and ent_km_mac.get().strip()) else KM_MAC
                globals()['KM_IP'] = _kip; globals()['KM_PORT'] = _kport; globals()['KM_MAC'] = _kmac
                ser = KmBox(_kip, _kport, _kmac)
                try: ensure_logo()
                except Exception: pass
                _set_hw_label(f"● 뚱박스 {_kip}", '#3fb950', gen)
            else:
                found = auto_find_arduino()
                if found:
                    globals()['SERIAL_PORT'] = found
                    SERIAL_PORT = found
                ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0)
                _set_hw_label(f"● {SERIAL_PORT}", '#3fb950', gen)
            connected = bool(ser and getattr(ser, "is_open", False))
            if connected:
                if _hw in ("뚱박스", "KMBox"):
                    globals()["_fw_version_str"] = ""
                    globals()["_fw_wdt4"] = False
                    if root:
                        try:
                            root.after(0, _apply_wheel_heal_ui)
                        except Exception:
                            pass
                else:
                    Thread(target=lambda s=ser: refresh_fw_version(s, log=True), daemon=True).start()
            return connected
        except Exception:
            ser = None
            _set_hw_label("○ 연결실패", '#f85149', gen)
            return False

def expert_logic():
    global ser, running, last_buff_seq, BUFF_SEQ_GAP
    global last_loot, last_loot_sent_time, loot_interval
    global camera, root, lbl_ard, mode_var, chk_follow
    global chk_loot, chk_poison, chk_target_poison, chk_party_poison, chk_buff_on
    global SELF_HP_COORD, SELF_HP_RGB, NOPARTY_HP_COORD, NOPARTY_RGB, PARTY_COORDS, MAIN_ATTACKER_COORD
    global DANGER_HP_COORD, DANGER_HP_RGB, SELF_POISON_COORD, SELF_POISON_RGB, TARGET_POISON_COORD, TARGET_POISON_RGB
    global last_self_heal, last_party_heal, last_party_cure, last_noparty_heal
    global party_mode_flags, selected_party_flags
    global SELF_HP_ROI, SELF_HP_100_REF, DANGER_HP_ROI, DANGER_HP_100_REF
    global self_hp_threshold, danger_hp_threshold, attacker_hp_threshold, mna_threshold, strong_heal_pct, self_strong_heal_pct, chk_strong_heal, chk_self_strong_heal
    global attacker_hp_udp, attacker_poisoned, attacker_petrified
    global MNA_ROI, MNA_100_REF, last_mna_potion, chk_mna, chk_self_heal_sw, chk_danger_sw, chk_attacker_sw
    global buff_next_due, last_buff_global, _buff_cfg, _self_buff_cfg
    
    load_buff_templates()

    while True:
        now = time.time()
        if _reconnect_req and not running and not globals().get('_fw_flash_busy'):
            globals()['_reconnect_req'] = False
            connect_hardware()
        if running and ser and getattr(ser, 'is_open', False):
            frame = camera.get_latest_frame() if camera else None
            if frame is None: time.sleep(0.01); continue
            _offer_stream_frame(frame)

            if remote_control_active():
                time.sleep(0.03)
                continue

            # 석화(회색 피바): 일반/독은 빨강+초록, 석화일 때만 어두운 회색 열=채움 (빈칸=밝은 은색)
            _self_petrified = is_gray_bar(frame, SELF_HP_ROI) if SELF_HP_ROI[0] != 0 else False

            # 위험베르 — 최우선 (HP%만 판정, 빨강/초록 독·석화 각각 채움 인식)
            danger_roi = DANGER_HP_ROI if DANGER_HP_ROI[0] != 0 else SELF_HP_ROI
            danger_ref = DANGER_HP_100_REF if DANGER_HP_ROI[0] != 0 else SELF_HP_100_REF
            _danger_petrified = is_gray_bar(frame, danger_roi) if danger_roi[0] != 0 else False
            if danger_roi[0] != 0:
                danger_pct = self_hp_pct(frame, danger_roi, danger_ref, petrified=_danger_petrified)
                # 예전엔 "연속 2프레임 모두 낮아야 발동"이라 전투 이펙트로 한 프레임만 튀어도
                # 진짜 위험할 때조차 발동을 놓치는 치명적 문제가 있어서 뺐었음. 지금은 그 대신
                # "3번 중 2번 이상 낮으면 발동"(다수결) — 순간 캡처오독 1번은 걸러내면서도,
                # 진짜 위험하면 3개 중 대부분이 낮게 나오므로 실발동엔 거의 영향 없음.
                if chk_danger_sw.get() and danger_pct < danger_hp_threshold:
                    _confirmed, _samples = _danger_confirm_majority(danger_roi, danger_ref, danger_pct, danger_hp_threshold, petrified=_danger_petrified)
                    _samp_str = ",".join("?" if s is None else f"{s:.0f}" for s in _samples)
                    if _confirmed:
                        focus_lineage_window()
                        _cap = 'dx' if getattr(camera, '_dx_ok', False) else 'mss'   # 다음에 또 오작동하면 캡처백엔드까지 로그로 바로 확인 가능
                        ser.write(b'C')
                        _save_danger_debug(frame, danger_roi, danger_pct)
                        log_event(f"🛡️ 위험베르 (HP:{danger_pct:.0f}%, 확인:{_samp_str}, cap:{_cap})"); stop_everything(f"🚨 위기 베르 감지 (HP:{danger_pct:.0f}%)"); continue
                    else:
                        log_event(f"🛡️ 위기베르 오독걸러짐 (확인:{_samp_str})")

            # 채팅 등 실제 타이핑 중엔 "생명과 무관한" 동작(버프·줍기·해독·파랭이)만 일시정지.
            # 자힐·파티힐(A/7)·위기베르는 절대 여기서 안 막음 — 채팅 중이라도 실제로
            # 힐이 필요하면 그대로 나가야 함(안 그러면 채팅 중 맞아죽을 위험).
            _typing_now = (time.time() - last_typing_time) < TYPING_PAUSE_SEC

            # 줍기
            if not _typing_now and chk_loot and chk_loot.get() and (now - last_loot >= loot_interval):
                last_loot_sent_time = now; ser.write(b'4'); last_loot = now; loot_interval = random.uniform(4.0, 7.0); log_event('🎒 줍기') 

            # 파랭이 (마나 물약)
            if not _typing_now and chk_mna and chk_mna.get() and MNA_ROI[0] != 0 and (now - last_mna_potion >= 600):
                mna_pct = roi_mna_pct(frame, MNA_ROI, MNA_100_REF)
                if mna_pct < mna_threshold:
                    execute_keys(mna_potion_keys(), 0.5); last_mna_potion = now
                    log_event(f"💙 파랭이 (MP:{mna_pct:.0f}%)")
                    continue

            m = mode_var.get() if mode_var else "노파티"

            # 파티 해독 반응지연 진단용 — 초록(독)바가 화면에 실제로 처음 보인 시각을 기록.
            # 게이트(쿨다운·타이핑중·party_window_alive)와 무관하게 매 프레임 스캔해서,
            # 나중에 실제 해독키가 나갈 때 "감지~해독" 걸린 시간을 로그로 남기기 위함.
            if chk_party_poison and chk_party_poison.get():
                _diag_flags = party_mode_flags if m == "파티" else selected_party_flags
                for _pi in range(1, 8):
                    if not _diag_flags[_pi] or PARTY_ROIS[_pi][0] <= 0:
                        _party_poison_first_seen.pop(_pi, None); continue
                    if party_slot_active(frame, PARTY_ROIS[_pi], _pi) and is_green_bar(frame, PARTY_ROIS[_pi]):
                        if _pi not in _party_poison_first_seen:
                            _party_poison_first_seen[_pi] = now
                            log_event(f'🟢 파티독 감지 P{_pi + 1} (해독 대기중)')
                    else:
                        _party_poison_first_seen.pop(_pi, None)

            # ── 해독 ──────────────────────────────────────
            # 쫄법 독:   F2→F9(엔줄고정)→F1
            # 격수 독:   F2→F10(큐어포이즌)→F1 (UDP)
            # 파티 독:   마우스이동 → F2→F10(큐어포이즌)→클릭(대상)→F1
            # 쫄법 석화: F2→F12(리무브커스)→F1 (ROI)
            # 격수 석화: F2→F12(리무브커스)→F1 (UDP)
            # (해독도 죽지는 않는 동작이라 타이핑 중엔 대기 — 힐은 아래에서 그대로 계속 작동함)
            if not _typing_now and chk_poison and chk_poison.get() and is_green_bar(frame, SELF_HP_ROI):
                fix_mode_keys(['2', '9', '1'], 0.5); log_event('🟢 독해독'); continue
            if not _typing_now and chk_target_poison and chk_target_poison.get() and attacker_poisoned:
                # 노파티: HP 임계값 미만이면 해독보다 힐 우선 (독이어도 HP%만 본다)
                udp_fresh = (time.time() - last_udp_time) < 5
                atk_hp = attacker_hp_udp
                hp_need_heal = udp_fresh and atk_hp < attacker_hp_threshold
                if not (m == "노파티" and hp_need_heal):
                    fix_mode_keys(['2', 'X', '1'], 0.45); attacker_poisoned = False; log_event('🟢 격수 독해독'); continue
            if not _typing_now and chk_party_poison and chk_party_poison.get() and (now - last_party_cure >= 0.5):
                party_flags = party_mode_flags if m == "파티" else selected_party_flags
                if party_window_alive(frame, party_flags):
                    cure_pi = -1; cure_tx = 0; cure_ty = 0
                    for pi in range(1, 8):
                        if not party_flags[pi]: continue
                        if PARTY_ROIS[pi][0] <= 0: continue
                        if not party_slot_active(frame, PARTY_ROIS[pi], pi): continue
                        if is_green_bar(frame, PARTY_ROIS[pi]):
                            x1, y1, x2, y2 = PARTY_ROIS[pi]
                            cure_pi = pi; cure_tx, cure_ty = (x1 + x2) // 2, (y1 + y2) // 2
                            break
                    if cure_pi >= 0:
                        if m == "파티":
                            pt_orig = POINT(); ctypes.windll.user32.GetCursorPos(ctypes.byref(pt_orig))
                            orig_x, orig_y = pt_orig.x, pt_orig.y
                            was_fixed, was_follow = _pause_attack_click()
                            focus_lineage_window()
                            human_mouse_move(cure_tx, cure_ty, roi=PARTY_ROIS[cure_pi]); time.sleep(0.02)
                            # F2→F10(큐어포이즌)→클릭(대상지정)→F1 — 이미 pause됨, 키만 전송
                            execute_keys(['2', 'X', 'K', '1'], 0.45, skip_follow_toggle=True)
                            human_mouse_move(orig_x, orig_y)
                            _resume_attack_click(was_fixed, was_follow)
                        else:
                            fix_mode_keys(['2', 'X', '1'], 0.45)
                        _seen_at = _party_poison_first_seen.pop(cure_pi, now)
                        last_party_cure = now; log_event(f'🟢 파티해독 P{cure_pi + 1} (감지후 {now - _seen_at:.1f}초)'); continue

            # 버프 (F1/F2/F3 × F5~F12 그리드) — 타이핑 중엔 대기(생명과 무관)
            if not _typing_now and chk_buff_on and chk_buff_on.get() and (now - last_buff_global >= 1.0) and (now - last_buff_seq >= BUFF_SEQ_GAP):
                buff_cast = False
                for idx, (cb_sb, hb_var, slot_var, sec_var) in enumerate(_self_buff_cfg, 1):
                    if not cb_sb.get():
                        continue
                    tk_sb = self_buff_time_key(idx)
                    iv_sb = get_safe_int(sec_var, int(saved_self_buff_sec or 1200))
                    if now >= buff_next_due.get(tk_sb, 0):
                        hb_sb = hb_var.get()
                        slot_sb = slot_var.get()
                        cast_self_buff(hb_sb, slot_sb)
                        schedule_buff(tk_sb, iv_sb, soon=False)
                        last_buff_seq = now
                        last_buff_global = now
                        log_event(f"⚡ 자기버프{idx} {hb_sb}-{slot_sb}")
                        buff_cast = True
                        break
                if not buff_cast:
                    for hb in BUFF_HOTBARS:
                        for slot, cb, iv in _buff_cfg.get(hb, []):
                            if not cb.get():
                                continue
                            tk = buff_time_key(hb, slot)
                            iv_sec = get_safe_int(iv, BASE_BUFF_INTERVAL)
                            if now >= buff_next_due.get(tk, 0):
                                cast_buff(hb, slot)
                                schedule_buff(tk, iv_sec, soon=False)
                                last_buff_seq = now
                                last_buff_global = now
                                tag = f"{hb}-{slot}" if hb != "F1" else slot
                                log_event(f"✨ 버프 {tag}")
                                buff_cast = True
                                break
                        if buff_cast:
                            break
                if buff_cast:
                    continue

            # MP% 체크 (자힐 제한)
            _mp_low = False
            if chk_mna and chk_mna.get() and MNA_ROI[0] != 0:
                _mp_low = roi_mna_pct(frame, MNA_ROI, MNA_100_REF) < mna_threshold

            # 솔로(파티)
            if m == "솔로(파티)":
                healed = False
                if SELF_HP_ROI[0] != 0:
                    self_hp = roi_hp_pct(frame, SELF_HP_ROI, SELF_HP_100_REF, petrified=_self_petrified)
                    if chk_self_heal_sw.get() and self_hp < self_hp_threshold and (now - last_self_heal >= 0.3):
                        use_strong = chk_self_strong_heal and chk_self_strong_heal.get() and self_hp < self_strong_heal_pct
                        tag = do_self_heal(self_hp, end_delay=1.0, mp_low=_mp_low, use_strong=use_strong)
                        last_self_heal = now; healed = True; log_event(f'🔴 자힐 {tag} ({int(self_hp)}%)')
                elif chk_self_heal_sw.get() and chk_color(frame, SELF_HP_COORD, SELF_HP_RGB, 18) and (now - last_self_heal >= 0.3):
                    tag = do_self_heal(None, end_delay=1.0, mp_low=_mp_low)
                    last_self_heal = now; healed = True; log_event(f'🔴 자힐 {tag}')

                if not healed:
                    # 파티창이 실제로 떠 있을 때만 파티원 힐 (미파티/창닫힘 → 마우스 유령이동 차단)
                    if party_window_alive(frame, selected_party_flags):
                        best_i = -1; best_hp = 999
                        for i in range(8):
                            if selected_party_flags[i] and PARTY_ROIS[i][0] != 0:
                                # 힐 타겟: 짧은 홀드(0.4초) — 깜빡임에 놓치지 않되 빈곳 유령클릭은 짧게만
                                hp_pct = scan_party_hp(frame, i, hold_sec=PARTY_HEAL_HOLD_SEC)
                                if hp_pct is not None and hp_pct > 1.0 and hp_pct < PARTY_HP_THRESHOLDS[i]:
                                    if hp_pct < best_hp:
                                        best_hp = hp_pct; best_i = i
                        if best_i >= 0:
                            focus_lineage_window()
                            was_fixed, was_follow = _pause_attack_click()
                            try:
                                use_strong = chk_strong_heal and chk_strong_heal.get() and best_hp < strong_heal_pct
                                hb_h, sl_h = get_heal_hotbar_slot(use_strong)
                                run_target_heal(hb_h, sl_h, end_delay=0.45, use_wheel=wheel_heal_enabled() and not use_strong)
                                if use_strong:
                                    log_event(f"⚡ 상위힐 P{best_i+1} HP{best_hp:.0f}% ({heal_slot_label(hb_h, sl_h)})")
                                else:
                                    tag = "휠" if wheel_heal_enabled() else None
                                    log_event(f"💚 파티힐 P{best_i+1} HP{best_hp:.0f}% ({heal_slot_label(hb_h, sl_h)})" + (f" {tag}" if tag else ""))
                                healed = True
                            finally:
                                _resume_attack_click(was_fixed, was_follow)
                    if healed: continue

            # 파티
            elif m == "파티":
                healed = False
                if SELF_HP_ROI[0] != 0:
                    self_hp = roi_hp_pct(frame, SELF_HP_ROI, SELF_HP_100_REF, petrified=_self_petrified)
                    if chk_self_heal_sw.get() and self_hp < self_hp_threshold and (now - last_self_heal >= 0.3):
                        use_strong = chk_self_strong_heal and chk_self_strong_heal.get() and self_hp < self_strong_heal_pct
                        tag = do_self_heal(self_hp, end_delay=0.8, mp_low=_mp_low, use_strong=use_strong)
                        last_self_heal = now; healed = True; log_event(f'🔴 자힐 {tag} ({int(self_hp)}%)')
                elif chk_self_heal_sw.get() and chk_color(frame, SELF_HP_COORD, SELF_HP_RGB, 18) and (now - last_self_heal >= 0.3):
                    tag = do_self_heal(None, end_delay=0.8, mp_low=_mp_low)
                    last_self_heal = now; healed = True; log_event(f'🔴 자힐 {tag}')

                if not healed:
                    # 파티창 없음/미파티면 파티힐 자체 스킵 (ROI 배경 오탐·홀드값 유령이동 방지)
                    if party_window_alive(frame, party_mode_flags):
                        pt_orig = POINT(); ctypes.windll.user32.GetCursorPos(ctypes.byref(pt_orig))
                        orig_x, orig_y = pt_orig.x, pt_orig.y
                        best_pi = -1; best_hp = 999; best_tx = 0; best_ty = 0
                        for pi in range(1, 8):
                            if not party_mode_flags[pi]: continue
                            if PARTY_ROIS[pi][0] > 0:
                                # 힐 타겟: 짧은 홀드(0.4초) — 깜빡임에 놓치지 않되 빈곳 유령클릭은 짧게만
                                hp_pct = scan_party_hp(frame, pi, hold_sec=PARTY_HEAL_HOLD_SEC)
                                if hp_pct is not None and hp_pct > 1.0 and hp_pct < PARTY_HP_THRESHOLDS[pi]:
                                    if hp_pct < best_hp:
                                        best_hp = hp_pct; best_pi = pi
                                        x1,y1,x2,y2 = PARTY_ROIS[pi]
                                        best_tx, best_ty = (x1+x2)//2, (y1+y2)//2
                        if best_pi >= 0:
                            was_fixed, was_follow = _pause_attack_click()
                            focus_lineage_window()
                            heal_roi = PARTY_ROIS[best_pi]
                            human_mouse_move((heal_roi[0] + heal_roi[2]) // 2, (heal_roi[1] + heal_roi[3]) // 2, fast=True, roi=heal_roi); time.sleep(0.02)
                            use_strong = chk_strong_heal and chk_strong_heal.get() and best_hp < strong_heal_pct
                            hb_h, sl_h = get_heal_hotbar_slot(use_strong)
                            run_target_heal(hb_h, sl_h, end_delay=0.08, use_wheel=wheel_heal_enabled() and not use_strong)
                            if use_strong:
                                log_event(f"⚡ 상위힐 P{best_pi + 1} HP{best_hp:.0f}% ({heal_slot_label(hb_h, sl_h)})")
                            else:
                                log_event(f"💚 파티힐 P{best_pi + 1} HP{best_hp:.0f}% ({heal_slot_label(hb_h, sl_h)})" + (" 휠" if wheel_heal_enabled() else ""))
                            human_mouse_move(orig_x, orig_y, fast=True)
                            _resume_attack_click(was_fixed, was_follow)
                            last_party_heal = now; healed = True

            # 노파티 — 격수힐: 독 여부와 무관, UDP HP% vs 격수% 임계값만 판단
            elif m == "노파티":
                action_taken = False
                if SELF_HP_ROI[0] != 0:
                    self_hp = roi_hp_pct(frame, SELF_HP_ROI, SELF_HP_100_REF, petrified=_self_petrified)
                    if chk_self_heal_sw.get() and self_hp < self_hp_threshold and (now - last_self_heal >= 0.2):
                        use_strong = chk_self_strong_heal and chk_self_strong_heal.get() and self_hp < self_strong_heal_pct
                        tag = do_self_heal(self_hp, end_delay=0.8, mp_low=_mp_low, use_strong=use_strong)
                        last_self_heal = now; action_taken = True
                        log_event(f'🔴 자힐 {tag} ({int(self_hp)}%)')
                elif chk_self_heal_sw.get() and chk_color(frame, SELF_HP_COORD, SELF_HP_RGB, 20) and (now - last_self_heal >= 0.2):
                    tag = do_self_heal(None, end_delay=0.8, mp_low=_mp_low)
                    last_self_heal = now; action_taken = True
                    log_event(f'🔴 자힐 {tag}')
                
                if not action_taken and (now - last_noparty_heal >= 0.2):
                    udp_ok = (time.time() - last_udp_time) < 5
                    atk_hp = attacker_hp_udp
                    if chk_attacker_sw.get() and udp_ok and atk_hp < attacker_hp_threshold:
                        focus_lineage_window()
                        use_strong = chk_strong_heal and chk_strong_heal.get() and atk_hp < strong_heal_pct
                        hb_h, sl_h = get_heal_hotbar_slot(use_strong)
                        was_fixed, was_follow = _pause_attack_click()
                        try:
                            if wheel_heal_enabled() and not use_strong:
                                run_target_heal(hb_h, sl_h, end_delay=0.45, use_wheel=True)
                                log_event(f"💚 격수힐 HP{atk_hp:.0f}% ({heal_slot_label(hb_h, sl_h)} 휠)")
                            elif wheel_heal_enabled() and use_strong:
                                run_target_heal(hb_h, sl_h, end_delay=0.45, use_wheel=False)
                                log_event(f"⚡ 상위힐 격수 HP{atk_hp:.0f}% ({heal_slot_label(hb_h, sl_h)})")
                            else:
                                execute_keys(heal_action_keys(hb_h, sl_h), 0.45, skip_follow_toggle=True, key_gap=(0.09, 0.16))
                                if use_strong:
                                    log_event(f"⚡ 상위힐 격수 HP{atk_hp:.0f}% ({heal_slot_label(hb_h, sl_h)})")
                                elif random.randint(1, 100) <= 85:
                                    log_event(f"💚 격수힐 HP{atk_hp:.0f}% ({heal_slot_label(hb_h, sl_h)})")
                                else:
                                    time.sleep(human_delay(0.2, 0.3))
                        finally:
                            _resume_attack_click(was_fixed, was_follow)
                        last_noparty_heal = now

                
        if not running: time.sleep(0.2)
        else:
            if random.randint(1, 100) <= 2:
                try: time.sleep(0.02)
                except: pass
            time.sleep(0.002)

# =======================================================
# 🚨 메인 구동
# =======================================================
_WIN_MIN_W, _WIN_MAX_W = 158, 420
_WIN_MIN_H, _WIN_MAX_H = 180, 900
_sync_height_job = None

def sync_window_height():
    global _sync_height_job
    if not root or not root.winfo_exists():
        return
    if _sync_height_job:
        try:
            root.after_cancel(_sync_height_job)
        except Exception:
            pass
    _sync_height_job = root.after(50, _apply_window_height)

def _apply_window_height():
    """접으면 창을 줄이고, 펼치면 내용만큼 늘린다."""
    global _sync_height_job
    _sync_height_job = None
    try:
        if not root or not root.winfo_exists() or _ui_busy():
            return
        try:
            import imgui_ui
            if imgui_ui.is_active():
                return
        except Exception:
            pass
        root.update_idletasks()
        w = root.winfo_width()
        if w < 120:
            w = saved_win_w
        cap = int(root.winfo_screenheight() * 0.88)
        req_h = root.winfo_reqheight()
        nh = max(_WIN_MIN_H, min(_WIN_MAX_H, cap, req_h))
        root.geometry(f"{int(w)}x{int(nh)}+{root.winfo_x()}+{root.winfo_y()}")
    except Exception:
        pass

def _start_resize(event):
    root._rs_x = event.x_root
    root._rs_y = event.y_root
    root._rs_w = root.winfo_width()
    root._rs_h = root.winfo_height()

def _do_resize(event):
    dw = event.x_root - root._rs_x
    dh = event.y_root - root._rs_y
    nw = max(_WIN_MIN_W, min(_WIN_MAX_W, root._rs_w + dw))
    nh = max(_WIN_MIN_H, min(_WIN_MAX_H, root._rs_h + dh))
    root.geometry(f"{int(nw)}x{int(nh)}+{root.winfo_x()}+{root.winfo_y()}")

def _end_resize(event):
    global saved_win_w
    try:
        saved_win_w = root.winfo_width()
        if loaded_pwd:
            save_hidden_config(loaded_pwd)
    except Exception:
        pass

def _set_taskmgr_title(win, title):
    """작업관리자·Alt+Tab 표시용 창 제목 (UI 뚱힐러 텍스트와 별개)."""
    try:
        win.title(title)
        def _apply():
            try:
                hid = win.winfo_id()
                hwnd = ctypes.windll.user32.GetParent(hid) or hid
                ctypes.windll.user32.SetWindowTextW(int(hwnd), title)
            except Exception:
                pass
        win.after(50, _apply)
    except Exception:
        pass

root = ctk.CTk()
root.withdraw()
root.geometry("1x1+-32000+-32000")
root.attributes("-topmost", False)
root.after(400, sync_window_height)
root.configure(fg_color="#141420")
root.overrideredirect(True)
try:
    import imgui_ui
    imgui_ui._cloak_stray_windows()
except Exception:
    pass
_set_taskmgr_title(root, SOOPLIVE_CLIENT_TITLE)

title_bar = ctk.CTkFrame(root, height=24, corner_radius=0, fg_color="#141420")
title_bar.pack(fill="x")
try:
    title_text = " 뚱힐러"
    if os.path.exists("logo.png"):
        logo_img = ctk.CTkImage(light_image=Image.open("logo.png"), size=(18, 18))
        title_lbl = ctk.CTkLabel(title_bar, text=title_text, image=logo_img, compound="left", font=("Malgun Gothic", 12, "bold"), text_color="#cba6f7")
    else: title_lbl = ctk.CTkLabel(title_bar, text="❖ 뚱힐러 ❖", font=("Malgun Gothic", 12, "bold"), text_color="#cba6f7")
except: title_lbl = ctk.CTkLabel(title_bar, text="❖ 뚱힐러 ❖", font=("Malgun Gothic", 12, "bold"), text_color="#cba6f7")
title_lbl.place(relx=0.5, rely=0.5, anchor="center") 

def exit_app():
    global timer_thread_active, loaded_pwd, ser
    timer_thread_active = False
    try: save_hidden_config(loaded_pwd if loaded_pwd else "")
    except: pass
    try:
        stop_stream_server()
    except Exception:
        pass
    try:
        if camera: camera.stop(); camera.release()
    except: pass
    try:
        if ser:
            ser.close()
            ser = None
    except Exception:
        pass
    try:
        keyboard.unhook_all()
    except Exception:
        pass
    time.sleep(0.5)
    os._exit(0)

exit_btn = ctk.CTkButton(title_bar, text="✖", width=24, height=20, fg_color="#800020", hover_color="#9e1a3a", border_width=1, border_color="#4a0010", command=exit_app)
exit_btn.pack(side="right", padx=5, pady=2)

def start_move(event): root.x = event.x; root.y = event.y
def stop_move(event): root.x = None; root.y = None
def do_move(event):
    x = root.winfo_x() + (event.x - root.x); y = root.winfo_y() + (event.y - root.y)
    root.geometry(f"+{x}+{y}")
title_bar.bind("<ButtonPress-1>", start_move); title_bar.bind("<ButtonRelease-1>", stop_move); title_bar.bind("<B1-Motion>", do_move)
title_lbl.bind("<ButtonPress-1>", start_move); title_lbl.bind("<ButtonRelease-1>", stop_move); title_lbl.bind("<B1-Motion>", do_move)

def keep_on_top():
    try:
        import imgui_ui
        if imgui_ui.is_active():
            try:
                imgui_ui._cloak_tk_root(root)
            except Exception:
                pass
            if root:
                root.after(2000, keep_on_top)
            return
    except Exception:
        pass
    try:
        if root and root.winfo_exists() and not _ui_busy():
            root.attributes("-topmost", True)  # lift() 제거: 드롭다운 포커스 뺏김 방지
    except Exception:
        pass
    if root:
        root.after(2000, keep_on_top)
keep_on_top()

chk_fix = ctk.BooleanVar(value=False)
chk_follow = ctk.BooleanVar(value=False)
chk_force_fix = ctk.BooleanVar(value=False)
chk_space_save = ctk.BooleanVar(value=False) 
mode_var = ctk.StringVar(value="노파티")
_preset_data = _read_presets_file()
_preset_var = ctk.StringVar(value=_preset_data.get("last") or "파티")
chk_buff_on = ctk.BooleanVar(value=saved_buff_on in ("1", "true", "True"))
chk_poison = ctk.BooleanVar(value=False)
chk_target_poison = ctk.BooleanVar(value=False)
chk_party_poison = ctk.BooleanVar(value=False)
chk_loot = ctk.BooleanVar(value=False) 

# ─── 상단 헤더바 (업데이트 + 장치상태) ───
header = ctk.CTkFrame(root, fg_color="#161b22", corner_radius=8, height=24)
header.pack(pady=(2,1), padx=2, fill='x')
header.grid_columnconfigure(1, weight=1)
_upd_short = PATCH_UPDATED_AT[5:] if len(PATCH_UPDATED_AT) > 5 else PATCH_UPDATED_AT  # "08-04 18:30"
lbl_update = ctk.CTkButton(
    header, text=f"업데이트 {_upd_short}", command=on_update_check_click,
    fg_color="#21262d", hover_color="#30363d", border_width=1, border_color="#30363d",
    text_color="#e2e8f0", font=("Malgun Gothic", 8, "bold"),
    height=20, width=118, corner_radius=6,
)
lbl_update.grid(row=0, column=0, padx=(4,2), pady=2, sticky="w")
lbl_ard = ctk.CTkLabel(header, text="확인중", text_color="#a6adc8",
                        font=("Malgun Gothic", 8, "bold"))
lbl_ard.grid(row=0, column=2, padx=(2,6), pady=2, sticky="e")

# ─── 하드웨어 선택 (아두이노/KMBox) + KMBox 접속입력 ───
frame_hw = ctk.CTkFrame(root, fg_color="#161b22", corner_radius=6)
frame_hw.pack(pady=(1,1), padx=2, fill='x')
frame_hw.grid_columnconfigure(1, weight=1)
ctk.CTkLabel(frame_hw, text="장치", text_color="#f9e2af", font=("Malgun Gothic", 8, "bold"), width=28).grid(row=0, column=0, padx=(4,2), pady=4, sticky="w")
hw_var = tk.StringVar(value=HW_MODE)
hw_combo = make_pick_btn(
    frame_hw, ["뚱USB", "뚱박스"], hw_var, command=lambda v: _on_hw_mode_change(v),
    width=100, height=26, premium=True,
)
hw_combo.configure(font=("Malgun Gothic", 9, "bold"))
hw_combo.grid(row=0, column=1, padx=(1, 4), pady=3, sticky="ew")
btn_fw_flash = ctk.CTkButton(
    frame_hw, text="펌업", width=42, height=26,
    font=("Malgun Gothic", 9, "bold"),
    fg_color="#1f6feb", hover_color="#388bfd", corner_radius=8,
    command=on_fw_flash_click,
)
btn_fw_flash.grid(row=0, column=2, padx=(0, 2), pady=3, sticky="e")
btn_fw_check = ctk.CTkButton(
    frame_hw, text="확인", width=36, height=26,
    font=("Malgun Gothic", 8, "bold"),
    fg_color="#238636", hover_color="#2ea043", corner_radius=8,
    command=on_fw_check_click,
)
btn_fw_check.grid(row=0, column=3, padx=(0, 4), pady=3, sticky="e")

frame_kmfields = ctk.CTkFrame(root, fg_color="#161b22", corner_radius=6)
_kmr1 = ctk.CTkFrame(frame_kmfields, fg_color="transparent"); _kmr1.pack(fill='x', pady=1)
ctk.CTkLabel(_kmr1, text="IP", width=34, anchor="w", text_color="#a6adc8", font=("Malgun Gothic", 8, "bold")).pack(side="left", padx=(6,2))
ent_km_ip = ctk.CTkEntry(_kmr1, width=132, height=20, font=("Malgun Gothic", 9))
ent_km_ip.pack(side="left"); ent_km_ip.insert(0, KM_IP)
_kmr2 = ctk.CTkFrame(frame_kmfields, fg_color="transparent"); _kmr2.pack(fill='x', pady=1)
ctk.CTkLabel(_kmr2, text="포트", width=34, anchor="w", text_color="#a6adc8", font=("Malgun Gothic", 8, "bold")).pack(side="left", padx=(6,2))
ent_km_port = ctk.CTkEntry(_kmr2, width=132, height=20, font=("Malgun Gothic", 9))
ent_km_port.pack(side="left"); ent_km_port.insert(0, KM_PORT)
_kmr3 = ctk.CTkFrame(frame_kmfields, fg_color="transparent"); _kmr3.pack(fill='x', pady=1)
ctk.CTkLabel(_kmr3, text="UUID", width=34, anchor="w", text_color="#a6adc8", font=("Malgun Gothic", 8, "bold")).pack(side="left", padx=(6,2))
ent_km_mac = ctk.CTkEntry(_kmr3, width=132, height=20, font=("Malgun Gothic", 9))
ent_km_mac.pack(side="left"); ent_km_mac.insert(0, KM_MAC)
# 뚱헌터와 동일 셋팅 버튼 — 한 줄, 폼 폭에 맞게 균등 확장
_kmr_tools = ctk.CTkFrame(frame_kmfields, fg_color="transparent")
_kmr_tools.pack(fill='x', pady=(2, 3), padx=2)
_kmr_tools.grid_columnconfigure(0, weight=1)
_kmr_tools.grid_columnconfigure(1, weight=1)
_kmr_tools.grid_columnconfigure(2, weight=1)
_km_btn_kw = dict(
    height=22, font=("Malgun Gothic", 8, "bold"), corner_radius=6,
    fg_color="#21262d", hover_color="#30363d", border_width=1, border_color="#30363d",
    text_color="#e2e8f0",
)
ctk.CTkButton(_kmr_tools, text="드라이버", command=on_kmbox_driver_click, **_km_btn_kw).grid(row=0, column=0, padx=(2, 1), sticky="ew")
ctk.CTkButton(_kmr_tools, text="IP설정", command=on_kmbox_setup_click, **_km_btn_kw).grid(row=0, column=1, padx=1, sticky="ew")
ctk.CTkButton(_kmr_tools, text="설정도구", command=on_kmbox_net_setup_click, **_km_btn_kw).grid(row=0, column=2, padx=(1, 2), sticky="ew")

def _toggle_km_fields():
    """뚱박스 입력칸 보이기/숨기기만 — 재연결 요청은 여기서 안 함."""
    if hw_var.get() in ("뚱박스", "KMBox"):
        frame_kmfields.pack(pady=(0,1), padx=2, fill='x', after=frame_hw)
    else:
        frame_kmfields.pack_forget()
    # 높이 다시 맞춤 (버튼 줄 가려지지 않게)
    try:
        root.update_idletasks()
        sync_window_height()
    except Exception:
        pass

def _on_hw_mode_change(v=None):
    """장치 드롭다운 변경 — 입력칸 토글 + 상태 라벨 갱신.
    뚱박스 kmNet.init 는 여기서 안 함(없는 박스로 고르면 UI 응답없음).
    실제 연결은 Insert 시작 시에만."""
    try:
        globals()['HW_MODE'] = hw_var.get() if hw_var else HW_MODE
    except Exception:
        pass
    _toggle_km_fields()
    try:
        refresh_device_status()
    except Exception:
        pass

_toggle_km_fields()
globals()['_hw_ui_ready'] = True
try:
    root.after(200, refresh_device_status)
except Exception:
    pass

frame_mode = ctk.CTkFrame(root, fg_color="#313244", corner_radius=6)
frame_mode.pack(pady=(2,1), padx=2, fill='x')
frame_mode.grid_columnconfigure(0, weight=1)
_pick_sel = dict(width=72, height=26, premium=True)
mode_seg = make_pick_btn(
    frame_mode, ["파티", "솔로(파티)", "노파티"], mode_var, **_pick_sel,
)
mode_seg.grid(row=0, column=0, padx=4, pady=3, sticky="ew")

main_body = ctk.CTkFrame(root, fg_color="transparent")
main_body.pack(fill="x", padx=2, pady=1)

# ─── 접이식: 옵션 ───
coll_opt = Collapsible(main_body, "옵션", start_open=False)
coll_opt.pack(pady=1, padx=2, fill="x")
frame_opt = coll_opt.body
frame_opt.grid_columnconfigure(0, weight=1)
frame_opt.grid_columnconfigure(1, weight=1)
sw_w, sw_h = 28, 14; ft = ('Malgun Gothic', 8, 'bold')

def _on_fix_sw():
    if not running:
        return
    if chk_fix.get():
        _apply_attack_mode('fix')
        log_event("📌 고정 (클릭 OFF)")
    else:
        _apply_attack_mode('follow')
        log_event("🖱️ 따라가기 ON")

def _on_follow_sw():
    if not running:
        return
    if chk_follow.get():
        _apply_attack_mode('follow')
        log_event("🖱️ 따라가기 ON")
    else:
        _apply_attack_mode('fix')
        log_event("📌 고정 (클릭 OFF)")

def _on_force_fix_sw():
    if not running:
        return
    if chk_force_fix.get():
        _apply_force_fix(True)
        log_event("📌 강제고정 ON (시프트 제자리)")
    else:
        _apply_force_fix(False)
        log_event("📌 강제고정 OFF")

RoundedToggle(frame_opt, "고정(Home)", "#a371f7", var=chk_fix, cmd=_on_fix_sw).grid(row=0, column=0, padx=3, pady=2, sticky="w")
RoundedToggle(frame_opt, "따라가기(Home)", "#a371f7", var=chk_follow, cmd=_on_follow_sw).grid(row=0, column=1, padx=3, pady=2, sticky="w")
RoundedToggle(frame_opt, "강제고정(PageUp)", "#a371f7", var=chk_force_fix, cmd=_on_force_fix_sw).grid(row=1, column=0, padx=3, pady=2, sticky="w")
RoundedToggle(frame_opt, "독 해독", "#a371f7", var=chk_poison, cmd=lambda: log_event(f"☠️ 독해독 {'ON' if chk_poison.get() else 'OFF'}")).grid(row=1, column=1, padx=3, pady=2, sticky="w")
RoundedToggle(frame_opt, "격수 해독", "#a371f7", var=chk_target_poison, cmd=lambda: log_event(f"⚔️ 격수해독 {'ON' if chk_target_poison.get() else 'OFF'}")).grid(row=2, column=0, padx=3, pady=2, sticky="w")
RoundedToggle(frame_opt, "파티 해독", "#a371f7", var=chk_party_poison, cmd=lambda: log_event(f"💚 파티해독 {'ON' if chk_party_poison.get() else 'OFF'}")).grid(row=2, column=1, padx=3, pady=2, sticky="w")
RoundedToggle(frame_opt, "줍기(F4)", "#a371f7", var=chk_loot, cmd=lambda: log_event(f"🎒 줍기 {'ON' if chk_loot.get() else 'OFF'}")).grid(row=3, column=0, padx=3, pady=2, sticky="w")
chk_end_bert = ctk.BooleanVar(value=saved_chk_end_bert in ("1", "true", "True"))
def _on_end_bert_sw():
    log_event(f"🏃 강제베르 {'ON' if chk_end_bert.get() else 'OFF'}")
    try:
        save_hidden_config(loaded_pwd if loaded_pwd else "")
    except Exception:
        pass
RoundedToggle(frame_opt, "강제베르(end)", "#f9e2af", var=chk_end_bert, cmd=_on_end_bert_sw).grid(row=3, column=1, padx=3, pady=2, sticky="w")
chk_wheel_heal = ctk.BooleanVar(value=saved_chk_wheel_heal in ("1", "true", "True"))
def _on_wheel_heal_sw():
    if not _fw_wdt4:
        chk_wheel_heal.set(False)
        log_event("⚠️ 휠힐 — WDT4 펌 필요 (Insert 연결 시 자동 확인)")
        return
    chk_wheel_heal.set(True)
    log_event("🖱️ 휠힐 — 최신 펌웨어에서 항상 켜짐 (일반힐=휠, 상위힐=좌클릭)")
    try:
        save_hidden_config(loaded_pwd if loaded_pwd else "")
    except Exception:
        pass
toggle_wheel_heal = RoundedToggle(frame_opt, "휠힐(항상ON)", "#a371f7", var=chk_wheel_heal, cmd=_on_wheel_heal_sw)
toggle_wheel_heal.grid(row=4, column=0, padx=3, pady=2, sticky="w")
try:
    root.after(200, _apply_wheel_heal_ui)
except Exception:
    pass

# ─── 접이식: 버프 그리드 ───
coll_buff = Collapsible(main_body, "버프", start_open=True)
coll_buff.pack(pady=1, padx=2, fill="x")
buff_body = coll_buff.body
def _on_buff_on():
    log_event(f"✨ 버프 {'ON' if chk_buff_on.get() else 'OFF'}")
    try:
        globals()["saved_buff_on"] = "1" if chk_buff_on.get() else "0"
        save_hidden_config(loaded_pwd if loaded_pwd else "")
    except Exception:
        pass
_buff_card_kw = dict(fg_color="#1e1e2e", corner_radius=6, border_width=1, border_color="#45475a")
_buff_pk = dict(premium=True, width=28, height=16, font=("Malgun Gothic", 8, "bold"), arrow=False)
_buff_sec_entry = dict(width=36, height=16, font=("Malgun Gothic", 7), text_color="#ffffff",
                       fg_color="#1e1e2e", border_color="#45475a", justify="center")

frame_buff_card = ctk.CTkFrame(buff_body, **_buff_card_kw)
frame_buff_card.pack(pady=(1, 2), padx=2, fill="x")
buff_top = ctk.CTkFrame(frame_buff_card, fg_color="transparent")
buff_top.pack(fill="x", padx=4, pady=(3, 2))
buff_mode_var = tk.StringVar(value="일반")
ctk.CTkLabel(buff_top, text="✨", text_color="#cba6f7", font=("Malgun Gothic", 8, "bold")).pack(side="left")
buff_mode_btn = make_pick_btn(buff_top, ["일반", "자기"], buff_mode_var, width=36, height=16, font=("Malgun Gothic", 8, "bold"), premium=True, arrow=False)
buff_mode_btn.pack(side="left", padx=(2, 4))
buff_general_top = ctk.CTkFrame(buff_top, fg_color="transparent")
buff_general_top.pack(side="left")
RoundedToggle(buff_general_top, "자동", "#a371f7", var=chk_buff_on, cmd=_on_buff_on).pack(side="left", padx=(0, 4))
ctk.CTkLabel(buff_general_top, text="창", text_color="#6c7086", font=("Malgun Gothic", 8)).pack(side="left", padx=(0, 2))
buff_hotbar_var = tk.StringVar(value="F1")
buff_hotbar_combo = make_pick_btn(buff_general_top, BUFF_HOTBARS, buff_hotbar_var, **_buff_pk)
buff_hotbar_combo.pack(side="left")

buff_general_host = ctk.CTkFrame(frame_buff_card, fg_color="transparent")
buff_general_host.pack(fill="x", padx=2, pady=(0, 3))
buff_page_host = ctk.CTkFrame(buff_general_host, fg_color="transparent")
buff_page_host.pack(fill="x")
_buff_pages = {}

def _parse_buff_saved(hb, slot):
    raw = saved_buff_grid.get(buff_grid_key(hb, slot), f"0:{BASE_BUFF_INTERVAL}")
    parts = raw.split(":", 1)
    on = parts[0] in ("1", "true", "True") if parts else False
    sec = parts[1] if len(parts) > 1 else str(BASE_BUFF_INTERVAL)
    return on, sec

for hb in BUFF_HOTBARS:
    page = ctk.CTkFrame(buff_page_host, fg_color="transparent")
    _buff_pages[hb] = page
    left_col = ctk.CTkFrame(page, fg_color="transparent")
    right_col = ctk.CTkFrame(page, fg_color="transparent")
    left_col.pack(side="left", fill="x", expand=True, anchor="n")
    right_col.pack(side="left", fill="x", expand=True, anchor="n")
    rows = []
    for idx, slot in enumerate(BUFF_SLOT_LABELS):
        parent = left_col if idx < 4 else right_col
        cell = ctk.CTkFrame(parent, fg_color="transparent")
        cell.pack(anchor="w", pady=0)
        on_def, sec_def = _parse_buff_saved(hb, slot)
        cb = ctk.BooleanVar(value=on_def)
        iv = tk.StringVar(value=sec_def)
        def _on_buff_slot(_hb=hb, _slot=slot):
            try:
                save_hidden_config(loaded_pwd if loaded_pwd else "")
            except Exception:
                pass
        ctk.CTkCheckBox(cell, text=slot, variable=cb, width=32, checkbox_width=12, checkbox_height=12,
                        font=("Malgun Gothic", 7, "bold"), text_color="#f0d9a8",
                        fg_color="#800020", hover_color="#9e1a3a",
                        command=_on_buff_slot).pack(side="left")
        ctk.CTkEntry(cell, textvariable=iv, **_buff_sec_entry).pack(side="left", padx=(1, 0))
        iv.trace_add("write", lambda *a: _schedule_buff_cfg_save())
        rows.append((slot, cb, iv))
    _buff_cfg[hb] = rows

def _show_buff_page(choice=None):
    hb = choice or buff_hotbar_var.get()
    for name, page in _buff_pages.items():
        if name == hb:
            page.pack(fill="x")
        else:
            page.pack_forget()

buff_hotbar_combo.set_pick_command(_show_buff_page)
_show_buff_page("F1")

buff_self_host = ctk.CTkFrame(frame_buff_card, fg_color="transparent")
_self_left = ctk.CTkFrame(buff_self_host, fg_color="transparent")
_self_right = ctk.CTkFrame(buff_self_host, fg_color="transparent")
_self_left.pack(side="left", fill="x", expand=True, anchor="n")
_self_right.pack(side="left", fill="x", expand=True, anchor="n")
_self_buff_cfg = []
for _sb_idx in range(1, SELF_BUFF_COUNT + 1):
    _sb_on, _sb_hb, _sb_slot, _sb_sec = _parse_self_buff_saved(_sb_idx)
    _sb_parent = _self_left if _sb_idx <= 2 else _self_right
    _sb_cell = ctk.CTkFrame(_sb_parent, fg_color="transparent")
    _sb_cell.pack(anchor="w", pady=0)
    _sb_cb = ctk.BooleanVar(value=_sb_on)
    _sb_hb_var = tk.StringVar(value=_sb_hb if _sb_hb in BUFF_HOTBARS else "F1")
    _sb_slot_var = tk.StringVar(value=_sb_slot if _sb_slot in BUFF_SLOT_LABELS else "F5")
    _sb_sec_var = tk.StringVar(value=str(_sb_sec or "1200"))
    def _on_self_buff_row(_i=_sb_idx, _c=_sb_cb):
        log_event(f"⚡ 자기버프{_i} {'ON' if _c.get() else 'OFF'}")
        try:
            save_hidden_config(loaded_pwd if loaded_pwd else "")
        except Exception:
            pass
    ctk.CTkCheckBox(_sb_cell, text=str(_sb_idx), variable=_sb_cb, width=16, checkbox_width=12, checkbox_height=12,
                    font=("Malgun Gothic", 7, "bold"), text_color="#f9e2af",
                    fg_color="#800020", hover_color="#9e1a3a", command=_on_self_buff_row).pack(side="left")
    _sb_hb_btn = make_pick_btn(_sb_cell, BUFF_HOTBARS, _sb_hb_var, width=26, height=16, font=("Malgun Gothic", 7, "bold"), premium=True, arrow=False)
    _sb_hb_btn.pack(side="left", padx=1)
    _sb_hb_btn.set_pick_command(lambda *a: _schedule_buff_cfg_save())
    _sb_slot_btn = make_pick_btn(_sb_cell, BUFF_SLOT_LABELS, _sb_slot_var, width=28, height=16, font=("Malgun Gothic", 7, "bold"), premium=True, arrow=False)
    _sb_slot_btn.pack(side="left", padx=1)
    _sb_slot_btn.set_pick_command(lambda *a: _schedule_buff_cfg_save())
    ctk.CTkEntry(_sb_cell, textvariable=_sb_sec_var, **_buff_sec_entry).pack(side="left", padx=1)
    _sb_sec_var.trace_add("write", lambda *a: _schedule_buff_cfg_save())
    _self_buff_cfg.append((_sb_cb, _sb_hb_var, _sb_slot_var, _sb_sec_var))

def _show_buff_mode(choice=None):
    mode = choice or buff_mode_var.get()
    if mode == "자기":
        buff_general_top.pack_forget()
        buff_general_host.pack_forget()
        buff_self_host.pack(fill="x", padx=2, pady=(0, 3))
    else:
        buff_self_host.pack_forget()
        buff_general_top.pack(side="left")
        buff_general_host.pack(fill="x", padx=2, pady=(0, 3))
        _show_buff_page()
    try:
        sync_window_height()
    except Exception:
        pass

buff_mode_btn.set_pick_command(_show_buff_mode)
_show_buff_mode("일반")

# ─── 접이식: 힐·물약 ───
coll_heal = Collapsible(main_body, "힐·물약", start_open=False)
coll_heal.pack(pady=1, padx=2, fill="x")
heal_body = coll_heal.body

frame_heal_slot = ctk.CTkFrame(heal_body, fg_color="#1e1e2e", corner_radius=8, border_width=1, border_color="#45475a")
frame_heal_slot.pack(pady=(2, 4), padx=2, fill="x")
ctk.CTkLabel(frame_heal_slot, text="⌨ 힐 단축키", text_color="#cba6f7", font=("Malgun Gothic", 9, "bold")).pack(anchor="w", padx=6, pady=(5, 2))
_row_hk = dict(premium=True, width=28, height=18, font=("Malgun Gothic", 8, "bold"), arrow=False)
_hk_split = ctk.CTkFrame(frame_heal_slot, fg_color="transparent")
_hk_split.pack(fill="x", padx=4, pady=(0, 5))
_row_n = ctk.CTkFrame(_hk_split, fg_color="transparent")
_row_n.pack(side="left", fill="x", expand=True, padx=(0, 2))
ctk.CTkLabel(_row_n, text="💚 일반", text_color="#a6e3a1", font=("Malgun Gothic", 8, "bold")).pack(side="left")
heal_hotbar_var = tk.StringVar(value=HEAL_HOTBAR)
heal_slot_var = tk.StringVar(value=HEAL_SLOT)
heal_hb_btn = make_pick_btn(_row_n, BUFF_HOTBARS, heal_hotbar_var, **_row_hk)
heal_hb_btn.pack(side="left", padx=(2, 1))
ctk.CTkLabel(_row_n, text="+", text_color="#6c7086", font=("Malgun Gothic", 8)).pack(side="left")
heal_sl_btn = make_pick_btn(_row_n, BUFF_SLOT_LABELS, heal_slot_var, width=30, height=18, font=("Malgun Gothic", 8, "bold"), premium=True, arrow=False)
heal_sl_btn.pack(side="left", padx=1)
_row_s = ctk.CTkFrame(_hk_split, fg_color="transparent")
_row_s.pack(side="left", fill="x", expand=True, padx=(2, 0))
ctk.CTkLabel(_row_s, text="⚡ 상위", text_color="#89b4fa", font=("Malgun Gothic", 8, "bold")).pack(side="left")
strong_heal_hotbar_var = tk.StringVar(value=STRONG_HEAL_HOTBAR)
strong_heal_slot_var = tk.StringVar(value=STRONG_HEAL_SLOT)
str_hb_btn = make_pick_btn(_row_s, BUFF_HOTBARS, strong_heal_hotbar_var, **_row_hk)
str_hb_btn.pack(side="left", padx=(2, 1))
ctk.CTkLabel(_row_s, text="+", text_color="#6c7086", font=("Malgun Gothic", 8)).pack(side="left")
str_sl_btn = make_pick_btn(_row_s, BUFF_SLOT_LABELS, strong_heal_slot_var, width=30, height=18, font=("Malgun Gothic", 8, "bold"), premium=True, arrow=False)
str_sl_btn.pack(side="left", padx=1)
def update_heal_slots(*a):
    global HEAL_HOTBAR, HEAL_SLOT, STRONG_HEAL_HOTBAR, STRONG_HEAL_SLOT
    HEAL_HOTBAR = heal_hotbar_var.get()
    HEAL_SLOT = heal_slot_var.get()
    STRONG_HEAL_HOTBAR = strong_heal_hotbar_var.get()
    STRONG_HEAL_SLOT = strong_heal_slot_var.get()
    log_event(f"⌨ 힐키 → 일반 {heal_slot_label(HEAL_HOTBAR, HEAL_SLOT)} / 상위 {heal_slot_label(STRONG_HEAL_HOTBAR, STRONG_HEAL_SLOT)}")
    if loaded_pwd:
        save_hidden_config(loaded_pwd)
for _b in (heal_hb_btn, heal_sl_btn, str_hb_btn, str_sl_btn):
    _b.set_pick_command(update_heal_slots)

frame_selfhp = ctk.CTkFrame(heal_body, fg_color="transparent")
frame_selfhp.pack(pady=1, padx=2, fill='x')
frame_selfhp.grid_columnconfigure(1, weight=1)
chk_self_heal_sw = ctk.BooleanVar(value=saved_chk_self_heal in ("1", "true", "True"))
def _on_self_heal_sw():
    log_event(f"🔴 자힐 {'ON' if chk_self_heal_sw.get() else 'OFF'}")
    try: save_hidden_config(loaded_pwd if loaded_pwd else "")
    except Exception: pass
_tg_self = RoundedToggle(frame_selfhp, "🔴 자힐", "#58a6ff", var=chk_self_heal_sw, cmd=_on_self_heal_sw)
_tg_self.grid(row=0, column=0, sticky="w", padx=2)
self_hp_var = ctk.IntVar(value=self_hp_threshold)
self_hp_sld = make_pct_slider(frame_selfhp, 10, 90, self_hp_var)
self_hp_sld.grid(row=0, column=1, sticky="ew", padx=2)
self_hp_lbl = ctk.CTkLabel(frame_selfhp, text=f"{self_hp_threshold}%", text_color="#f38ba8", font=('Malgun Gothic', 10, 'bold'), width=28)
self_hp_lbl.grid(row=0, column=2, sticky="e")
def update_self_hp_thr(*a):
    global self_hp_threshold
    self_hp_threshold = self_hp_var.get(); self_hp_lbl.configure(text=f"{self_hp_threshold}%")
    save_hidden_config(loaded_pwd)
self_hp_var.trace_add("write", update_self_hp_thr)

frame_self_strong = ctk.CTkFrame(heal_body, fg_color="transparent")
frame_self_strong.pack(pady=1, padx=2, fill='x')
frame_self_strong.grid_columnconfigure(1, weight=1)
chk_self_strong_heal = ctk.BooleanVar(value=saved_chk_self_strong_heal in ("1", "true", "True"))
def _on_self_strong_heal():
    log_event(f"⚡ 자힐상위 {'ON' if chk_self_strong_heal.get() else 'OFF'}")
    try: save_hidden_config(loaded_pwd if loaded_pwd else "")
    except Exception: pass
_tg_self_s = RoundedToggle(frame_self_strong, "⚡ 자힐상위", "#58a6ff", var=chk_self_strong_heal, cmd=_on_self_strong_heal)
_tg_self_s.grid(row=0, column=0, sticky="w", padx=2)
self_strong_var = ctk.IntVar(value=self_strong_heal_pct)
self_strong_sld = make_pct_slider(frame_self_strong, 5, 70, self_strong_var)
self_strong_sld.grid(row=0, column=1, sticky="ew", padx=2)
self_strong_lbl = ctk.CTkLabel(frame_self_strong, text=f"{self_strong_heal_pct}%", text_color="#f38ba8", font=('Malgun Gothic', 10, 'bold'), width=28)
self_strong_lbl.grid(row=0, column=2, sticky="e")
def update_self_strong_thr(*a):
    global self_strong_heal_pct
    self_strong_heal_pct = self_strong_var.get()
    self_strong_lbl.configure(text=f"{self_strong_heal_pct}%")
    save_hidden_config(loaded_pwd)
self_strong_var.trace_add("write", update_self_strong_thr)

frame_dangerhp = ctk.CTkFrame(heal_body, fg_color="transparent")
frame_dangerhp.pack(pady=1, padx=2, fill='x')
frame_dangerhp.grid_columnconfigure(1, weight=1)
chk_danger_sw = ctk.BooleanVar(value=saved_chk_danger in ("1", "true", "True"))
def _on_danger_sw():
    log_event(f"🛡️ 위기 {'ON' if chk_danger_sw.get() else 'OFF'}")
    try: save_hidden_config(loaded_pwd if loaded_pwd else "")
    except Exception: pass
_tg_danger = RoundedToggle(frame_dangerhp, "🛡️ 위기", "#58a6ff", var=chk_danger_sw, cmd=_on_danger_sw)
_tg_danger.grid(row=0, column=0, sticky="w", padx=2)
danger_hp_var = ctk.IntVar(value=danger_hp_threshold)
danger_hp_sld = make_pct_slider(frame_dangerhp, 5, 50, danger_hp_var)
danger_hp_sld.grid(row=0, column=1, sticky="ew", padx=2)
danger_hp_lbl = ctk.CTkLabel(frame_dangerhp, text=f"{danger_hp_threshold}%", text_color=SLIDER_PROGRESS_DEFAULT, font=('Malgun Gothic', 10, 'bold'), width=28)
danger_hp_lbl.grid(row=0, column=2, sticky="e")
def update_danger_hp_thr(*a):
    global danger_hp_threshold
    danger_hp_threshold = danger_hp_var.get(); danger_hp_lbl.configure(text=f"{danger_hp_threshold}%")
    save_hidden_config(loaded_pwd)
danger_hp_var.trace_add("write", update_danger_hp_thr)

frame_strong = ctk.CTkFrame(heal_body, fg_color="transparent")
frame_strong.pack(pady=1, padx=2, fill="x")
frame_strong.grid_columnconfigure(1, weight=1)
chk_strong_heal = ctk.BooleanVar(value=saved_chk_strong_heal in ("1", "true", "True"))
def _on_strong_heal():
    log_event(f"⚡ 상위힐 {'ON' if chk_strong_heal.get() else 'OFF'}")
    try: save_hidden_config(loaded_pwd if loaded_pwd else "")
    except Exception: pass
_tg_strong = RoundedToggle(frame_strong, "⚡ 상위힐", "#58a6ff", var=chk_strong_heal, cmd=_on_strong_heal)
_tg_strong.grid(row=0, column=0, sticky="w", padx=2)
sv = ctk.IntVar(value=strong_heal_pct)
_strong_sld = make_pct_slider(frame_strong, 5, 70, sv)
_strong_sld.grid(row=0, column=1, sticky="ew", padx=2)
s_lbl = ctk.CTkLabel(frame_strong, text=f"{strong_heal_pct}%", text_color="#f38ba8", font=("Malgun Gothic",10,"bold"), width=28)
s_lbl.grid(row=0, column=2, sticky="e")
def update_strong_thr(v, lbl=s_lbl):
    global strong_heal_pct
    strong_heal_pct = sv.get(); lbl.configure(text=f"{strong_heal_pct}%")
    save_hidden_config(loaded_pwd if loaded_pwd else "")

sv.trace_add("write", lambda *a: update_strong_thr(sv, s_lbl))

frame_atkhp = ctk.CTkFrame(heal_body, fg_color="transparent")
frame_atkhp.pack(pady=1, padx=2, fill='x')
frame_atkhp.grid_columnconfigure(1, weight=1)
chk_attacker_sw = ctk.BooleanVar(value=saved_chk_attacker in ("1", "true", "True"))
def _on_attacker_sw():
    log_event(f"⚔️ 격수 {'ON' if chk_attacker_sw.get() else 'OFF'}")
    try: save_hidden_config(loaded_pwd if loaded_pwd else "")
    except Exception: pass
_tg_atk = RoundedToggle(frame_atkhp, "⚔️ 격수", "#58a6ff", var=chk_attacker_sw, cmd=_on_attacker_sw)
_tg_atk.grid(row=0, column=0, sticky="w", padx=2)
atkhp_var = ctk.IntVar(value=int(attacker_hp_threshold))
atkhp_sld = make_pct_slider(frame_atkhp, 10, 99, atkhp_var)
atkhp_sld.grid(row=0, column=1, sticky="ew", padx=2)
atkhp_lbl = ctk.CTkLabel(frame_atkhp, text=f"{int(attacker_hp_threshold)}%", text_color=SLIDER_PROGRESS_DEFAULT, font=('Malgun Gothic', 10, 'bold'), width=28)
atkhp_lbl.grid(row=0, column=2, sticky="e")
def update_atkhp_thr(*a):
    global attacker_hp_threshold
    attacker_hp_threshold = atkhp_var.get(); atkhp_lbl.configure(text=f"{int(attacker_hp_threshold)}%")
    save_hidden_config(loaded_pwd)
atkhp_var.trace_add("write", update_atkhp_thr)

# 마나 물약 (맨 밑)
frame_mna = ctk.CTkFrame(heal_body, fg_color="transparent")
frame_mna.pack(pady=1, padx=2, fill='x')
frame_mna.grid_columnconfigure(1, weight=1)
chk_mna = ctk.BooleanVar(value=saved_chk_mna in ("1", "true", "True"))
def _on_mna_sw():
    log_event(f"💙 파랭이 {'ON' if chk_mna.get() else 'OFF'}")
    try: save_hidden_config(loaded_pwd if loaded_pwd else "")
    except Exception: pass
_tg_mna = RoundedToggle(frame_mna, "💙 파랭이", "#58a6ff", var=chk_mna, cmd=_on_mna_sw)
_tg_mna.grid(row=0, column=0, sticky="w", padx=2)
mna_var = ctk.IntVar(value=mna_threshold)
mna_sld = make_pct_slider(frame_mna, 10, 80, mna_var, progress_color=SLIDER_PROGRESS_MNA)
mna_sld.grid(row=0, column=1, sticky="ew", padx=2)
mna_lbl = ctk.CTkLabel(frame_mna, text=f"{mna_threshold}%", text_color=SLIDER_PROGRESS_MNA, font=('Malgun Gothic', 10, 'bold'), width=28)
mna_lbl.grid(row=0, column=2, sticky="e")
def update_mna_thr(*a):
    global mna_threshold
    mna_threshold = mna_var.get(); mna_lbl.configure(text=f"{mna_threshold}%")
    if loaded_pwd: save_hidden_config(loaded_pwd)
mna_var.trace_add("write", update_mna_thr)

# 파랭이 위치(핫바+슬롯) — 잘못된 슬롯(예: F1의 F8=귀환주문서)이 실수로 눌리는 사고 방지용.
# 실제 파랭이가 있는 핫바/슬롯으로 맞춰두면 그 자리가 그대로 눌림.
frame_mna_slot = ctk.CTkFrame(heal_body, fg_color="transparent")
frame_mna_slot.pack(pady=(0, 1), padx=2, fill='x')
frame_mna_slot.grid_columnconfigure(3, weight=1)
ctk.CTkLabel(frame_mna_slot, text="위치", text_color="#89b4fa", font=('Malgun Gothic', 9)).grid(row=0, column=0, sticky="w", padx=(4, 0))
mna_hotbar_var = ctk.StringVar(value=MNA_HOTBAR)
mna_hotbar_combo = make_pick_btn(frame_mna_slot, BUFF_HOTBARS, mna_hotbar_var, width=32, height=18, font=('Malgun Gothic', 9))
mna_hotbar_combo.grid(row=0, column=1, padx=2, sticky="w")
mna_slot_var = ctk.StringVar(value=MNA_SLOT)
mna_slot_combo = make_pick_btn(frame_mna_slot, BUFF_SLOT_LABELS, mna_slot_var, width=36, height=18, font=('Malgun Gothic', 9))
mna_slot_combo.grid(row=0, column=2, padx=2, sticky="w")
def update_mna_slot(*a):
    global MNA_HOTBAR, MNA_SLOT
    MNA_HOTBAR = mna_hotbar_var.get(); MNA_SLOT = mna_slot_var.get()
    log_event(f"💙 파랭이 위치 변경 → {MNA_HOTBAR}+{MNA_SLOT}")
    if loaded_pwd: save_hidden_config(loaded_pwd)
mna_hotbar_combo.set_pick_command(update_mna_slot)
mna_slot_combo.set_pick_command(update_mna_slot)



frame_timer_mini = ctk.CTkFrame(root, fg_color="#313244")
frame_timer_mini.pack(pady=1, padx=2, fill='x')
ctk.CTkLabel(frame_timer_mini, text="⏰ 예약종료:", text_color="#ffffff", font=('Malgun Gothic', 10, 'bold')).pack(side="left", padx=4)
_timer_var = ctk.StringVar(value="예약OFF")
combo_timer = make_pick_btn(frame_timer_mini, ["예약OFF", "1시간", "2시간", "3시간", "5시간", "10시간"], _timer_var, command=set_shutdown_timer, width=84, height=19, font=('Malgun Gothic', 10))
combo_timer.pack(side="right", padx=4, pady=2)

btn_frame = ctk.CTkFrame(root, fg_color="transparent")
btn_frame.pack(fill='x', padx=2, pady=1)
btn_frame.grid_columnconfigure(0, weight=1, uniform="btn"); btn_frame.grid_columnconfigure(1, weight=1, uniform="btn"); btn_frame.grid_columnconfigure(2, weight=1, uniform="btn") 
ctk.CTkButton(btn_frame, text="⚙️ 제어판", command=ask_admin_pw, fg_color="#800020", hover_color="#9e1a3a", border_width=1, border_color="#4a0010", text_color="#ffffff", font=('Malgun Gothic', 10, 'bold'), height=26).grid(row=0, column=0)
ctk.CTkButton(btn_frame, text="📜 패치", command=open_patch_notes_panel, fg_color="#1f538d", hover_color="#14375e", border_width=1, border_color="#061220", text_color="#ffffff", font=('Malgun Gothic', 10, 'bold'), height=26).grid(row=0, column=1)
ctk.CTkButton(btn_frame, text="📖 가이드", command=open_guide_panel, fg_color="#313244", hover_color="#45475a", border_width=1, border_color="#1a1b26", text_color="#ffffff", font=('Malgun Gothic', 10, 'bold'), height=26).grid(row=0, column=2)

lbl_auth = ctk.CTkLabel(root, text="", text_color="#89b4fa", font=('Malgun Gothic', 10, 'bold'), height=18)
lbl_auth.pack(pady=(2,0), ipady=0)
lbl_status = ctk.CTkLabel(root, text="💤 대기 중", text_color="#f38ba8", font=('Malgun Gothic', 13, 'bold'), height=22)
lbl_status.pack(pady=0, ipady=0)
frame_buff = ctk.CTkFrame(root, fg_color="#181825", corner_radius=5)
frame_buff.pack(pady=0, padx=2, fill='x')
lbl_buff = ctk.CTkLabel(frame_buff, text="", text_color="#6c7086", font=('Malgun Gothic', 11, 'bold'))
lbl_buff.pack(pady=0)
lbl_saved_coord = ctk.CTkLabel(root, text="", text_color="#a6e3a1", font=('Malgun Gothic', 10, 'bold'))

# UDP 모듈
UDP_CONFIG_FILE = "udp_config.json"
UDP_DISCOVER_PORT = 9998
udp_target_ip = "192.168.0.100"
if os.path.exists(UDP_CONFIG_FILE):
    try:
        with open(UDP_CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        udp_target_ip = cfg.get("target_ip", udp_target_ip)
    except: pass

def save_udp_config():
    with open(UDP_CONFIG_FILE, "w", encoding="utf-8") as f: json.dump({"target_ip": udp_ip_var.get()}, f)

def _local_ipv4_addrs():
    addrs = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip and not ip.startswith("127."):
                addrs.add(ip)
    except Exception:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            addrs.add(ip)
    except Exception:
        pass
    return sorted(addrs)

def get_my_ip():
    ips = _local_ipv4_addrs()
    return ips[0] if ips else "..."

def broadcast_healer_ip():
    """같은 공유기 안 격수에 힐러 IP 알려줌."""
    ips = _local_ipv4_addrs()
    if not ips:
        log_event("📡 격수연결 실패 — 내IP 없음")
        return
    ip = ips[0]
    msg = json.dumps({"t": "ddong_healer", "ip": ip, "ips": ips}, ensure_ascii=False).encode("utf-8")
    targets = {"255.255.255.255", "127.0.0.1"}
    for one in ips:
        targets.add(one)
        parts = str(one).split(".")
        if len(parts) == 4 and all(p.isdigit() for p in parts):
            targets.add(".".join(parts[:3] + ["255"]))
    ok = 0
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try:
            s.bind((ip, 0))
        except Exception:
            try:
                s.bind(("", 0))
            except Exception:
                pass
        s.settimeout(0.5)
        for _ in range(3):
            for t in targets:
                try:
                    s.sendto(msg, (t, UDP_DISCOVER_PORT))
                    ok += 1
                except Exception:
                    pass
            time.sleep(0.05)
        s.close()
    except Exception as e:
        log_event("📡 격수연결 실패 — %s" % e)
        return
    if ok:
        log_event("📡 격수연결 신호 보냄 (%s)" % ", ".join(ips))
    else:
        log_event("📡 격수연결 전송 실패")

frame_ontop_ctrl = ctk.CTkFrame(root, fg_color="#313244", corner_radius=6)
frame_ontop_ctrl.pack(pady=1, padx=2, fill='x')

row1 = ctk.CTkFrame(frame_ontop_ctrl, fg_color="transparent"); row1.pack(fill='x', padx=2, pady=(3,0))
ctk.CTkLabel(row1, text="📡", text_color="#f9e2af", font=('', 9)).pack(side='left')
udp_ip_var = ctk.StringVar(value=udp_target_ip)
udp_ip_entry = ctk.CTkEntry(row1, textvariable=udp_ip_var, width=78, height=22, fg_color="#1e1e2e", text_color="#cdd6f4", font=('Consolas', 9))
# ImGui 메인에선 안 씀 — 숨김 유지용 변수만 남김
udp_ip_entry.pack_forget()
ctk.CTkButton(row1, text="격수연결", width=64, height=22, fg_color="#238636", hover_color="#2ea043", font=('Malgun Gothic', 8, 'bold'), command=broadcast_healer_ip).pack(side='left', padx=1)

row2 = ctk.CTkFrame(frame_ontop_ctrl, fg_color="transparent"); row2.pack(fill='x', padx=2, pady=(0,3))
lbl_my_ip = ctk.CTkLabel(row2, text=f"내IP:{get_my_ip()}", text_color="#a6e3a1", font=('Consolas', 8, 'bold'))
lbl_my_ip.pack(side='left', padx=4)
udp_hp_lbl = ctk.CTkLabel(row2, text="격수: --", text_color="#ef4444", font=('Malgun Gothic', 10, 'bold'))
udp_hp_lbl.pack(side='right', padx=4)
lbl_ontop_status = ctk.CTkLabel(row2, text="○ 대기", text_color="#6c7086", font=('Malgun Gothic', 9, 'bold'))
lbl_ontop_status.pack(side="right", padx=2)

udp_listen_ok = False          # 포트 9999 바인드 성공 여부
udp_last_from = ""             # 마지막 송신측 IP (진단용)

def _attacker_stream_connected():
    global _stream_active, _stream_client
    if not _stream_active:
        return False
    try:
        with _stream_client_lock:
            return _stream_client is not None
    except Exception:
        return False

def _attacker_link_ui():
    """격수 연결 표시 — UDP HP 또는 쫄화면(TCP) 둘 중 하나만 되어도 연결."""
    if not udp_listen_ok:
        return "격수: 오류", "#ef4444", "○ 대기", "#f38ba8"
    udp_fresh = last_udp_time > 0 and (time.time() - last_udp_time) <= 2.0
    if udp_fresh:
        return "격수: %.0f%%" % attacker_hp_udp, "#ef4444", "✅ 연결", "#a6e3a1"
    if _attacker_stream_connected():
        return "격수: 연결", "#a6e3a1", "✅ 연결", "#a6e3a1"
    return "격수: 끊김", "#ef4444", "○ 대기", "#f9e2af"

def update_udp_hp_label():
    try:
        if root and root.winfo_exists():
            atk, atk_c, ontop, ontop_c = _attacker_link_ui()
            udp_hp_lbl.configure(text=atk, text_color=atk_c)
            lbl_ontop_status.configure(text=ontop, text_color=ontop_c)
    except: pass
    try:
        if root and root.winfo_exists():
            root.after(300, update_udp_hp_label)
    except: pass

# UDP 원격 명령 매핑
def _get_stream_rect():
    """스트림 캡처 영역 (left, top, width, height)."""
    global _stream_roi
    if _stream_roi[2] > _stream_roi[0] and _stream_roi[3] > _stream_roi[1]:
        x1, y1, x2, y2 = _stream_roi
        return x1, y1, max(1, x2 - x1), max(1, y2 - y1)
    try:
        import mss as _mss
        mon = _mss.mss().monitors[1]
        return mon["left"], mon["top"], mon["width"], mon["height"]
    except Exception:
        return 0, 0, 1920, 1080

def _stream_point_from_frac(fx, fy):
    """격수 미리보기 0~1 좌표 → 쫄 화면 절대 좌표."""
    sx, sy, sw, sh = _get_stream_rect()
    fx = max(0.0, min(1.0, float(fx)))
    fy = max(0.0, min(1.0, float(fy)))
    return int(sx + fx * sw), int(sy + fy * sh)

def _touch_remote_control():
    global _remote_control_until
    _remote_control_until = time.time() + 1.5

def remote_control_active():
    return time.time() < globals().get("_remote_control_until", 0)

def _remote_mouse_move(fx, fy):
    global ser
    _touch_remote_control()
    if not ser or not getattr(ser, "is_open", False):
        return
    tx, ty = _stream_point_from_frac(fx, fy)
    with _remote_mouse_lock:
        _remote_mouse_move_fast(tx, ty)

def _remote_mouse_move_fast(tx, ty):
    """원격 조종용 빠른 이동 — human_mouse_move(다단계) 대신 1패킷."""
    global ser
    if not ser or not getattr(ser, "is_open", False):
        return
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    cx, cy = pt.x, pt.y
    tx, ty = _clamp_to_screen(int(tx), int(ty))
    dx, dy = tx - cx, ty - cy
    if abs(dx) < 2 and abs(dy) < 2:
        return
    _km = (hw_var.get() in ("뚱박스", "KMBox")) if ('hw_var' in globals() and hw_var) else (HW_MODE in ("뚱박스", "KMBox"))
    try:
        if _km and hasattr(ser, "move_smooth"):
            dist = (dx * dx + dy * dy) ** 0.5
            ms = int(max(20, min(90, dist * 0.35)))
            ser.move_smooth(int(dx), int(dy), ms)
            return
        while abs(dx) > 100 or abs(dy) > 100:
            sx, sy = max(-100, min(100, dx)), max(-100, min(100, dy))
            ser.write(f"<{sx},{sy}>".encode())
            dx -= sx
            dy -= sy
        if dx or dy:
            ser.write(f"<{dx},{dy}>".encode())
    except Exception:
        pass

def _remote_mouse_click(fx, fy, button="left", down=True):
    global ser
    _touch_remote_control()
    if not ser or not getattr(ser, "is_open", False):
        return
    tx, ty = _stream_point_from_frac(fx, fy)
    with _remote_mouse_lock:
        _remote_mouse_move_fast(tx, ty)
        time.sleep(0.02)
        btn = (button or "left").lower()
        if btn == "middle":
            if down:
                ser.write(b'M')
            return
        if btn == "left" and down:
            ser.write(b'K')

def _remote_mouse_scroll(delta):
    global ser
    _touch_remote_control()
    if not ser or not getattr(ser, "is_open", False):
        return
    with _remote_mouse_lock:
        if hasattr(ser, "wheel"):
            ser.wheel(delta)
            return
    # 뚱USB: 스크롤 미지원

def _handle_remote_udp_json(msg):
    if not isinstance(msg, dict):
        return
    t = msg.get("t")
    if t == "mm":
        _remote_mouse_move(msg.get("fx", 0.5), msg.get("fy", 0.5))
    elif t == "mc":
        _remote_mouse_click(msg.get("fx", 0.5), msg.get("fy", 0.5), msg.get("btn", "left"), bool(msg.get("down", True)))
    elif t == "ms":
        _remote_mouse_scroll(int(msg.get("d", 0)))

def _enqueue_remote_udp_json(msg):
    """UDP 수신 스레드에서 바로 ser/kmNet 건드리지 않게 큐로 넘김."""
    if not isinstance(msg, dict):
        return
    t = msg.get("t")
    if t == "mm":
        try:
            while True:
                old = _remote_mouse_queue.get_nowait()
                if not isinstance(old, dict) or old.get("t") != "mm":
                    _remote_mouse_queue.put_nowait(old)
                    break
        except Empty:
            pass
    try:
        _remote_mouse_queue.put_nowait(msg)
    except Exception:
        try:
            _remote_mouse_queue.get_nowait()
            _remote_mouse_queue.put_nowait(msg)
        except Exception:
            pass

def _remote_mouse_worker():
    while timer_thread_active:
        try:
            msg = _remote_mouse_queue.get(timeout=0.25)
        except Empty:
            continue
        try:
            _handle_remote_udp_json(msg)
        except Exception:
            pass

def _offer_stream_frame(rgb):
    """힐 스레드가 이미 잡은 프레임만 복사 — 송출이 dxcam/mss를 따로 찍지 않게."""
    global _stream_frame_bgr, _stream_offer_ts
    if not _stream_active or rgb is None:
        return
    now = time.time()
    if now - _stream_offer_ts < 0.09:
        return
    try:
        sx, sy, sw, sh = _get_stream_rect()
        fh, fw = rgb.shape[:2]
        x1 = max(0, min(int(sx), fw - 1))
        y1 = max(0, min(int(sy), fh - 1))
        x2 = max(x1 + 1, min(int(sx + sw), fw))
        y2 = max(y1 + 1, min(int(sy + sh), fh))
        crop = rgb[y1:y2, x1:x2]
        if crop.size == 0:
            return
        bgr = cv2.cvtColor(crop, cv2.COLOR_RGB2BGR)
        _stream_offer_ts = now
        with _stream_frame_lock:
            _stream_frame_bgr = bgr
    except Exception:
        pass

def _stream_feed_loop():
    """사냥 중이 아닐 때만 프레임 공급. 사냥 중엔 expert_logic 이 이미 캡처함."""
    while _stream_active:
        try:
            if not running:
                f = camera.get_latest_frame() if camera else None
                if f is not None:
                    _offer_stream_frame(f)
        except Exception:
            pass
        time.sleep(0.1)

def _stream_capture_bgr():
    with _stream_frame_lock:
        src = _stream_frame_bgr
    if src is None:
        return None
    return src.copy()

def _stream_send_loop():
    """JPEG 프레임 송출 — 격수 TCP 연결 시에만. 캡처는 하지 않음."""
    global _stream_active, _stream_client
    while _stream_active:
        with _stream_client_lock:
            conn = _stream_client
        if not conn:
            time.sleep(0.05)
            continue
        try:
            frame = _stream_capture_bgr()
            if frame is None or frame.size == 0:
                time.sleep(0.05)
                continue
            sx, sy, sw, sh = _get_stream_rect()
            pt = POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            lcx, lcy = pt.x - sx, pt.y - sy
            if 0 <= lcx < frame.shape[1] and 0 <= lcy < frame.shape[0]:
                cv2.circle(frame, (int(lcx), int(lcy)), 6, (0, 255, 255), -1)
            max_w, max_h = 1280, 720
            h, w = frame.shape[:2]
            scale = min(max_w / max(w, 1), max_h / max(h, 1), 1.0)
            if scale < 1.0:
                frame = cv2.resize(frame, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
            ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 65])
            if not ok:
                time.sleep(0.02)
                continue
            raw = buf.tobytes()
            conn.sendall(len(raw).to_bytes(4, "big") + raw)
            global last_udp_time
            last_udp_time = time.time()
        except Exception:
            with _stream_client_lock:
                try:
                    if _stream_client is conn:
                        _stream_client.close()
                        _stream_client = None
                except Exception:
                    _stream_client = None
        time.sleep(0.04)

def _stream_accept_loop():
    global _stream_active, _stream_client
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        srv.bind(("0.0.0.0", STREAM_TCP_PORT))
        srv.listen(1)
        srv.settimeout(1.0)
    except Exception:
        try:
            srv.close()
        except Exception:
            pass
        return
    while _stream_active:
        try:
            conn, _addr = srv.accept()
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            global last_udp_time
            last_udp_time = time.time()
            with _stream_client_lock:
                old = _stream_client
                _stream_client = conn
            if old:
                try:
                    old.close()
                except Exception:
                    pass
        except socket.timeout:
            continue
        except Exception:
            break
    try:
        srv.close()
    except Exception:
        pass

def start_stream_server():
    global _stream_active
    if _stream_active:
        return
    _stream_active = True
    Thread(target=_stream_accept_loop, daemon=True).start()
    Thread(target=_stream_send_loop, daemon=True).start()
    Thread(target=_stream_feed_loop, daemon=True).start()
    log_event("📡 쫄화면 송출 시작")

def stop_stream_server():
    global _stream_active, _stream_client, _stream_frame_bgr
    _stream_active = False
    with _stream_client_lock:
        try:
            if _stream_client:
                _stream_client.close()
        except Exception:
            pass
        _stream_client = None
    with _stream_frame_lock:
        _stream_frame_bgr = None
    log_event("📡 쫄화면 송출 정지")

UDP_CMD_MAP = {
    b'I': 'on_main_toggle',    # Insert → 시작/종료
    b'H': 'on_home_click_toggle',  # Home   → 클릭 ON/OFF
    b'P': 'on_home_click_toggle',  # 격수모니터 [고정] 버튼 (Home과 동일 토글)
    b'L': 'on_f4_toggle',      # F4     → 줍기 토글
    b'G': 'on_pageup_force_fix',  # 격수 PageUp → 강제고정
}
# Alt+숫자 → F3→F키→F1 매크로 (슬롯 1~8 → F5~F12)
UDP_SLOT_KEYS = {1: '5', 2: '6', 3: '7', 4: '8', 5: '9', 6: 'X', 7: 'Y', 8: 'Z'}  # F5~F12
def udp_macro_slot(n):
    """Alt+숫자: F3→F키→K→F1."""
    global ser, running
    if not running or not ser or not ser.is_open: return
    try:
        key = UDP_SLOT_KEYS.get(n, '5')
        time.sleep(0.02)
        ser.write(b'3'); time.sleep(random.uniform(0.30, 0.45))
        ser.write(key.encode()); time.sleep(0.15)
        ser.write(b'K'); time.sleep(0.10)
        ser.write(b'1'); time.sleep(random.uniform(0.25, 0.40))
    except: pass
def udp_listener():
    """격수모니터 → 뚱힐러 UDP 수신 (포트 9999).
    예전엔 bind 실패/예외 1번에 스레드가 바로 죽어서 영원히 '수신안됨'만 떴음."""
    global attacker_hp_udp, attacker_poisoned, attacker_petrified, last_udp_time
    global udp_listen_ok, udp_last_from
    sock = None
    while timer_thread_active:
        try:
            if sock is None:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(("0.0.0.0", UDP_ATTACKER_PORT))
                sock.settimeout(1.0)
                udp_listen_ok = True
                _ensure_udp_firewall(UDP_ATTACKER_PORT, "DDONG Healer UDP 9999")
            data, addr = sock.recvfrom(1024)
            udp_last_from = addr[0] if addr else ""
            if data and data != b'v':
                last_udp_time = time.time()
            if len(data) == 1:
                if data == b'V':
                    Thread(target=start_stream_server, daemon=True).start()
                elif data == b'v':
                    Thread(target=stop_stream_server, daemon=True).start()
                elif data in UDP_CMD_MAP:
                    # UI after 대기 없이 수신 스레드에서 즉시 처리.
                    # (힐 중 ser 사용 중에도 after 큐에 안 쌓이게 — 따라/고정/시작 반응 개선)
                    # 체크박스 갱신은 각 핸들러가 이미 root.after 로 넘김.
                    func_name = UDP_CMD_MAP[data]
                    f = globals().get(func_name)
                    if f:
                        try:
                            f()
                        except Exception:
                            pass
                elif data in (b'1',b'2',b'3',b'4',b'5',b'6',b'7',b'8'):
                    n = int(data.decode())
                    Thread(target=lambda s=n: udp_macro_slot(s), daemon=True).start()
                elif data == b'C':
                    Thread(target=do_manual_bert, daemon=True).start()
            elif len(data) >= 2 and data[0:1] == b'{':
                try:
                    msg = json.loads(data.decode("utf-8"))
                    _enqueue_remote_udp_json(msg)
                except Exception:
                    pass
            elif len(data) == 4:
                attacker_hp_udp = struct.unpack('f', data)[0]; last_udp_time = time.time()
            elif len(data) == 5:
                attacker_hp_udp, poison_byte = struct.unpack('fB', data)
                attacker_poisoned = bool(poison_byte); last_udp_time = time.time()
            elif len(data) == 6:
                attacker_hp_udp, poison_byte, petrify_byte = struct.unpack('fBB', data)
                attacker_poisoned = bool(poison_byte); attacker_petrified = bool(petrify_byte); last_udp_time = time.time()
        except socket.timeout:
            continue
        except OSError as e:
            # 포트 점유/방화벽 등으로 bind·수신 실패 → 죽지 말고 재시도
            udp_listen_ok = False
            try:
                if sock: sock.close()
            except Exception: pass
            sock = None
            time.sleep(2.0)
        except Exception:
            # 패킷 파싱 등 기타 오류 — 리스너 유지
            time.sleep(0.05)
    try:
        if sock: sock.close()
    except Exception: pass
    udp_listen_ok = False

is_gui_hidden = False
def toggle_gui(e=None):
    global is_gui_hidden
    is_gui_hidden = not is_gui_hidden
    try:
        import imgui_ui
        imgui_ui.set_hidden(is_gui_hidden)
    except Exception:
        if is_gui_hidden:
            root.withdraw()
        else:
            root.deiconify()

def _install_hotkeys():
    """창이 뜬 뒤에 훅 등록. 게임 켜진 채로 훅이 막히면 mainloop 전에 멈추던 문제 방지."""
    def _hook(name, fn):
        try:
            keyboard.on_release_key(name, fn)
        except Exception:
            pass
    _hook('delete', toggle_gui)
    _hook('space', on_space_save)
    _hook('home', on_home_click_toggle)
    for pg in ('page up', 'page_up', 'pageup'):
        try:
            keyboard.on_release_key(pg, on_pageup_force_fix)
            break
        except Exception:
            continue
    _hook('insert', on_main_toggle)
    _hook('end', on_end_bert)
    _hook('f4', on_f4_toggle)

timer_thread_active = True
_ensure_udp_firewall(UDP_ATTACKER_PORT, "DDONG Healer UDP 9999")
Thread(target=reserve_shutdown_worker, daemon=True).start()
Thread(target=expert_logic, daemon=True).start()
Thread(target=lcd_logo_worker, daemon=True).start()
Thread(target=update_ui_timer, daemon=True).start()
Thread(target=udp_listener, daemon=True).start()
Thread(target=_remote_mouse_worker, daemon=True).start()
Thread(target=_typing_poll_worker, daemon=True).start()
Thread(target=_user_keys_passthrough_worker, daemon=True).start()
update_udp_hp_label()

lbl_log = ctk.CTkTextbox(root, height=55, fg_color="#0d1117", text_color="#a6e3a1",
                          font=("Consolas", 9), border_width=1, border_color="#262a33",
                          corner_radius=6, activate_scrollbars=False)
lbl_log.pack(fill="x", padx=6, pady=(4,2))
lbl_log.insert("1.0", "🟢 시스템 시작")
lbl_log.configure(state="disabled")
resize_grip = ctk.CTkLabel(root, text="◢", width=16, height=16, fg_color="#313244", text_color="#6c7086",
                           font=("Malgun Gothic", 10, "bold"), corner_radius=0)
resize_grip.place(relx=1.0, rely=1.0, anchor="se")
resize_grip.bind("<ButtonPress-1>", _start_resize)
resize_grip.bind("<B1-Motion>", _do_resize)
resize_grip.bind("<ButtonRelease-1>", _end_resize)
root.after(50, _install_hotkeys)
root.after(300, sync_window_height)
try:
    import imgui_ui
    imgui_ui.run_main(globals())
except Exception:
    import traceback
    traceback.print_exc()
    try:
        root.deiconify()
    except Exception:
        pass
    root.mainloop()