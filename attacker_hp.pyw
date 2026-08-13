# -*- coding: utf-8 -*-
"""
격수 HP 전송기 v7 — HP 전송 + 쫄법PC 원격 키보드 제어 통합
"""
import numpy as np
import sys, subprocess
for mod, pkg in [("numpy","numpy"),("PIL","pillow"),("mss","mss"),("keyboard","keyboard")]:
    try: __import__(mod)
    except: subprocess.check_call([sys.executable,"-m","pip","install",pkg,"--quiet"])

import socket, struct, json, os, threading, time, re
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import mss
import keyboard
import ctypes
import win32gui

PATCH_UPDATED_AT = "2026-08-14 02:55"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ATTACKER_MAIN = os.path.join(SCRIPT_DIR, "attacker_hp.pyw")
CONFIG_FILE = os.path.join(SCRIPT_DIR, "udp_config.json")

def _read_patch_ver(source):
    try:
        if isinstance(source, bytes):
            text = source.decode("utf-8", errors="replace")
        elif isinstance(source, str) and os.path.isfile(source):
            with open(source, encoding="utf-8") as f:
                text = f.read()
        else:
            text = str(source)
        m = re.search(r'PATCH_UPDATED_AT\s*=\s*"([^"]+)"', text)
        return m.group(1).strip() if m else ""
    except Exception:
        return ""

def _cleanup_stale_new(expected_patch=None):
    """구버전 .new 가 main 을 덮어써서 업데이트 무한루프 나는 것 방지."""
    new_path = ATTACKER_MAIN + ".new"
    if not os.path.isfile(new_path):
        return
    exp = (expected_patch or PATCH_UPDATED_AT or "").strip()
    if _read_patch_ver(new_path) != exp:
        try:
            os.remove(new_path)
        except Exception:
            pass

def _sync_attacker_from_new():
    """업데이트 .new → main (서버 버전과 일치할 때만)."""
    new_path = ATTACKER_MAIN + ".new"
    if not os.path.isfile(new_path):
        return
    remote = fetch_remote_version()
    if not remote or _read_patch_ver(new_path) != remote:
        _cleanup_stale_new(remote)
        return
    try:
        import shutil
        shutil.copy2(new_path, ATTACKER_MAIN)
    except Exception:
        pass
    try:
        os.remove(new_path)
    except Exception:
        pass

if __file__.lower().endswith(".new"):
    _sync_attacker_from_new()
elif os.path.isfile(ATTACKER_MAIN + ".new"):
    _cleanup_stale_new(PATCH_UPDATED_AT)

TARGET_IP = "192.168.0.100"
TARGET_PORT = 9999
HP_ROI = (558, 878, 304, 5)
HP_100_REF = None
WIN_W = 340
WIN_H = 420
_WIN_MIN_W, _WIN_MAX_W = 240, 520
_WIN_MIN_H, _WIN_MAX_H = 120, 900
END_BERT_ON = False

if os.path.exists(CONFIG_FILE):
    try:
        ctypes.windll.kernel32.SetFileAttributesW(CONFIG_FILE, 128)
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        TARGET_IP = cfg.get("target_ip", TARGET_IP)
        if "hp_roi" in cfg: HP_ROI = tuple(int(v) for v in cfg["hp_roi"])
        if "hp_100_ref" in cfg: HP_100_REF = cfg["hp_100_ref"]
        if "win_w" in cfg:
            try: WIN_W = max(_WIN_MIN_W, min(_WIN_MAX_W, int(cfg["win_w"])))
            except Exception: pass
        if "win_h" in cfg:
            try: WIN_H = max(_WIN_MIN_H, min(_WIN_MAX_H, int(cfg["win_h"])))
            except Exception: pass
        if "end_bert" in cfg:
            END_BERT_ON = bool(cfg.get("end_bert"))
    except: pass

_VERSION_URL = "https://raw.githubusercontent.com/blacknut0319-del/systemupdate/main/attacker_version.txt"
_ATTACKER_URL = "https://raw.githubusercontent.com/blacknut0319-del/systemupdate/main/attacker_hp.pyw"
UPDATE_SKIP_FILE = os.path.join(SCRIPT_DIR, "attacker_update_skip.txt")
UPDATE_ATTEMPT_FILE = os.path.join(SCRIPT_DIR, "attacker_update_attempt.flag")
_last_update_check = 0.0
_update_available = False
_update_notified = False
lbl_update = None

# Windows 네이티브 알림 — borderless topmost 창에서 tkinter messagebox가 안 보임
_MB_ICONINFORMATION = 0x00000040
_MB_ICONWARNING = 0x00000030
_MB_ICONERROR = 0x00000010
_MB_YESNO = 0x00000004
_MB_TOPMOST = 0x00040000
_IDYES = 6

def _show_msgbox(kind, title, message):
    try:
        style = _MB_TOPMOST
        if kind == "info":
            style |= _MB_ICONINFORMATION
        elif kind == "warning":
            style |= _MB_ICONWARNING
        elif kind == "error":
            style |= _MB_ICONERROR
        elif kind == "yesno":
            style |= _MB_YESNO | _MB_ICONINFORMATION
        ret = ctypes.windll.user32.MessageBoxW(0, str(message), str(title), style)
        if kind == "yesno":
            return ret == _IDYES
        return None
    except Exception:
        return None

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

def fetch_remote_version():
    try:
        import ssl
        import urllib.request
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(
            _VERSION_URL + "?t=%d" % int(time.time()),
            headers={
                "User-Agent": "ddong-attacker",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
            },
        )
        with urllib.request.urlopen(req, timeout=8, context=ctx) as r:
            return r.read().decode("utf-8", errors="replace").strip().splitlines()[0].strip()
    except Exception:
        return None

def _mark_update_attempt(remote_ver):
    try:
        with open(UPDATE_ATTEMPT_FILE, "w", encoding="utf-8") as f:
            f.write("%f|%s" % (time.time(), remote_ver or ""))
    except Exception:
        pass

def _resolve_pythonw():
    exe = sys.executable
    if exe.lower().endswith("python.exe"):
        pyw = os.path.join(os.path.dirname(exe), "pythonw.exe")
        if os.path.isfile(pyw):
            return pyw
    return exe

def _spawn_attacker(script_path):
    """뚱힐러 dloader 실행과 같이 — 새 pythonw 프로세스를 먼저 띄움."""
    exe = _resolve_pythonw()
    script_path = os.path.abspath(script_path)
    flags = getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
    flags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
    subprocess.Popen(
        [exe, script_path],
        cwd=SCRIPT_DIR,
        close_fds=True,
        creationflags=flags,
    )

def _exit_attacker():
    global running
    running = False
    try:
        keyboard.unhook_all()
        sock.close()
    except Exception:
        pass
    try:
        root.destroy()
    except Exception:
        pass
    os._exit(0)

def restart_app():
    """다운로드 없이 격수만 다시 켜기."""
    script = os.path.abspath(__file__)
    if not os.path.isfile(script):
        script = ATTACKER_MAIN
    _spawn_attacker(script)
    time.sleep(0.45)
    _exit_attacker()

def restart_with_update():
    """최신 attacker_hp.pyw 받은 뒤 .new로 새 프로세스 실행 → 지금 창 종료."""
    global running
    remote = fetch_remote_version()
    if remote:
        _mark_update_attempt(remote)
    try:
        import ssl
        import urllib.request
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(
            _ATTACKER_URL + "?t=%d" % int(time.time()),
            headers={
                "User-Agent": "ddong-attacker",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
            },
        )
        with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
            data = r.read()
        if not data or b"PATCH_UPDATED_AT" not in data:
            raise RuntimeError("다운로드한 파일이 올바르지 않습니다.")
        new_path = ATTACKER_MAIN + ".new"
        with open(new_path, "wb") as f:
            f.write(data)
        _spawn_attacker(new_path)
        time.sleep(0.45)
    except Exception as e:
        _show_msgbox(
            "error",
            "업데이트 실패",
            "다시 받기에 실패했어요.\nhp_start.bat 으로 실행해 주세요.\n\n%s" % e,
        )
        return
    _exit_attacker()

def check_for_update(force=False, manual=False):
    global _last_update_check, _update_available, _update_notified
    now = time.time()
    if not force and not manual and (now - _last_update_check) < 600:
        return
    _last_update_check = now
    remote = fetch_remote_version()
    _short = PATCH_UPDATED_AT[5:] if len(PATCH_UPDATED_AT) > 5 else PATCH_UPDATED_AT

    def _set_lbl(text, color="#e2e8f0"):
        try:
            if lbl_update:
                lbl_update.config(text=text, fg=color)
        except Exception:
            pass

    if not remote:
        if manual:
            def _fail():
                _set_lbl("업데이트 %s" % _short, "#e2e8f0")
                _show_msgbox("warning", "업데이트 확인", "확인 실패.\n인터넷 연결을 확인해 주세요.")
            try:
                if root:
                    root.after(0, _fail)
            except Exception:
                pass
        return
    if remote == PATCH_UPDATED_AT:
        _update_available = False
        _save_update_skip("")
        try:
            if os.path.isfile(UPDATE_ATTEMPT_FILE):
                os.remove(UPDATE_ATTEMPT_FILE)
        except Exception:
            pass
        if manual:
            def _ok():
                _set_lbl("업데이트 %s" % _short, "#a6e3a1")
                _show_msgbox(
                    "info",
                    "업데이트 확인",
                    "최신이에요.\n다시 받을 필요 없어요.\n\n실행: %s\n서버: %s" % (PATCH_UPDATED_AT, remote),
                )
            try:
                if root:
                    root.after(0, _ok)
            except Exception:
                pass
        return
    _update_available = True
    if manual:
        _update_notified = False
    elif _load_update_skip() == remote:
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
        if manual or not _update_notified:
            _update_notified = True
            try:
                if _show_msgbox(
                    "yesno",
                    "업데이트",
                    "업데이트가 있습니다.\n\n서버: %s\n현재: %s\n\n업데이트하시겠습니까?"
                    % (remote, PATCH_UPDATED_AT),
                ):
                    _save_update_skip("")
                    restart_with_update()
                else:
                    _save_update_skip(remote)
            except Exception:
                pass
    try:
        if root:
            root.after(0, _ui)
    except Exception:
        pass

def on_update_check_click():
    try:
        if lbl_update:
            lbl_update.config(text="확인중...", fg="#f9e2af")
    except Exception:
        pass
    threading.Thread(target=lambda: check_for_update(force=True, manual=True), daemon=True).start()

def my_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close()
        return ip
    except: return "???"

MY_IP = my_ip()
sct = mss.MSS()
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
running = True; hp_pct = 0.0

# ============================================================
# 원격 제어 (UDP 1byte)
# ============================================================
DEBOUNCE = {'insert': 0, 'home': 0, 'f4': 0, 'end': 0}
CMD_MAP = {'insert': b'I', 'home': b'H', 'f4': b'L'}
CMD_NAMES = {b'I':'시작', b'H':'클릭', b'P':'고정', b'L':'줍기'}

def send_remote_cmd(cmd_byte):
    try:
        sock.sendto(cmd_byte, (ip_var.get(), TARGET_PORT))
        lbl_status.config(text="%s 전송됨" % CMD_NAMES.get(cmd_byte,'?'), fg="#10b981")
    except:
        lbl_status.config(text="전송 실패", fg="#ef4444")

def on_remote_key(name):
    def handler(e=None):
        now = time.time()
        if now - DEBOUNCE[name] < 0.3: return
        DEBOUNCE[name] = now
        send_remote_cmd(CMD_MAP[name])
    return handler

for key_name in ['insert', 'home', 'f4']:
    keyboard.on_release_key(key_name, on_remote_key(key_name))

SLOT_NAMES = {1:'F5',2:'F6',3:'F7',4:'F8',5:'F9',6:'F10',7:'F11',8:'F12'}
DEBOUNCE['slot'] = 0

def on_slot_hotkey(n):
    def handler():
        now = time.time()
        if now - DEBOUNCE.get('slot',0) < 0.5: return
        DEBOUNCE['slot'] = now
        try:
            sock.sendto(bytes([n+48]), (ip_var.get(), TARGET_PORT))
            lbl_status.config(text="슬롯%d F3>%s>F1" % (n, SLOT_NAMES[n]), fg="#10b981")
        except:
            lbl_status.config(text="전송 실패", fg="#ef4444")
    return handler

for i in range(1, 9):
    keyboard.add_hotkey('alt+%d' % i, on_slot_hotkey(i))

def on_end_bert_key(e=None):
    now = time.time()
    if now - DEBOUNCE.get('end', 0) < 0.5:
        return
    if not end_bert_var.get():
        return
    DEBOUNCE['end'] = now
    try:
        sock.sendto(b'C', (ip_var.get(), TARGET_PORT))
        lbl_status.config(text="베르 전송", fg="#f9e2af")
    except Exception:
        lbl_status.config(text="베르 실패", fg="#ef4444")

keyboard.on_release_key('end', on_end_bert_key)

# ============================================================
# 메인 GUI
# ============================================================
root = tk.Tk()
root.overrideredirect(True)
root.geometry("%dx%d+80+80" % (WIN_W, WIN_H))
root.attributes("-topmost", True)
root.configure(bg="#0d0f14")  # header UI v14 - final - CDN refresh

# ── 헤더바 ──
header = tk.Frame(root, bg="#141420", height=24)
header.pack(fill="x")
header.pack_propagate(False)
_upd_short = PATCH_UPDATED_AT[5:] if len(PATCH_UPDATED_AT) > 5 else PATCH_UPDATED_AT
lbl_update = tk.Button(
    header, text="업데이트 %s" % _upd_short, bg="#21262d", fg="#e2e8f0",
    font=("Malgun Gothic", 7, "bold"), padx=4, pady=0, bd=0, highlightthickness=0,
    activebackground="#30363d", activeforeground="#e2e8f0", cursor="hand2",
    command=on_update_check_click,
)
lbl_update.pack(side="left", padx=4, pady=2)
title_lbl = tk.Label(header, text="격수", bg="#141420", fg="#cba6f7", font=("Malgun Gothic", 8, "bold"))
title_lbl.place(relx=0.5, rely=0.5, anchor="center")
# 닫기
close_btn = tk.Label(header, text="✕", bg="#141420", fg="#f38ba8", font=("", 11))
close_btn.place(relx=1.0, x=-10, rely=0.5, anchor="e")
def close_app():
    global running, sock
    running = False
    try: sock.close()
    except: pass
    root.destroy()

# 드래그 이동 (뚱힐러와 동일)
def start_move(e):
    root._dx = e.x
    root._dy = e.y
def do_move(e):
    if hasattr(root, "_dx"):
        root.geometry("+%d+%d" % (root.winfo_x() + e.x - root._dx, root.winfo_y() + e.y - root._dy))
for _w in (header, title_lbl):
    _w.bind("<ButtonPress-1>", start_move)
    _w.bind("<B1-Motion>", do_move)

# 닫기
close_btn.bind("<Button-1>", lambda e: close_app())

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
    root.geometry("%dx%d+%d+%d" % (int(nw), int(nh), root.winfo_x(), root.winfo_y()))

def _end_resize(event):
    global WIN_W, WIN_H
    WIN_W = root.winfo_width()
    WIN_H = root.winfo_height()
    save_cfg()

def auto_resize_height():
    if root and root.winfo_exists():
        req = root.winfo_reqheight()
        cur = root.winfo_height()
        if req > cur + 4:
            root.geometry("%dx%d+%d+%d" % (root.winfo_width(), req, root.winfo_x(), root.winfo_y()))
    if root:
        root.after(500, auto_resize_height)
root.after(300, auto_resize_height)

# --- IP 행 ---
frm = tk.Frame(root, bg="#0d0f14")
frm.pack(fill='x', padx=6, pady=(6,1))
tk.Label(frm, text="📡", bg="#0d0f14", fg="#f9e2af", font=('',8)).pack(side='left')
ip_var = tk.StringVar(value=TARGET_IP)
tk.Entry(frm, textvariable=ip_var, width=13, bg="#1e1e2e", fg="#cdd6f4",
         insertbackground="#cdd6f4", font=('Consolas',9), justify='center',
         relief='flat', bd=1).pack(side='left', padx=3, fill='x', expand=True)
tk.Button(frm, text="저장", command=lambda: save_cfg(),
          bg="#800020", fg="#fff", font=('',7,'bold'), relief='flat',
          padx=5, cursor="hand2").pack(side='right')

# --- HP바 ---
canvas = tk.Canvas(root, bg="#0d0f14", height=40, highlightthickness=0)
canvas.pack(fill='x', padx=6, pady=(4,1))

# --- 상태 행 ---
frm2 = tk.Frame(root, bg="#0d0f14")
frm2.pack(fill='x', padx=6, pady=(0,2))
lbl_status = tk.Label(frm2, text="● 전송중", bg="#0d0f14", fg="#10b981", font=('',8))
lbl_status.pack(side='left')
tk.Label(frm2, text="IP:%s" % MY_IP, bg="#0d0f14", fg="#6c7086", font=('Consolas',7)).pack(side='right')

opt_frm = tk.Frame(root, bg="#0d0f14")
opt_frm.pack(fill='x', padx=6, pady=(0, 2))
end_bert_var = tk.BooleanVar(value=END_BERT_ON)
tk.Checkbutton(opt_frm, text="강제베르(end)", variable=end_bert_var, bg="#0d0f14", fg="#f9e2af",
               selectcolor="#313244", activebackground="#0d0f14", activeforeground="#f9e2af",
               font=("Malgun Gothic", 8), command=lambda: save_cfg()).pack(side='left')

# --- ROI + 미리보기 + 중독 ---
lbl_roi = tk.Label(root, text="ROI=%s" % str(HP_ROI), bg="#0d0f14", fg="#45475a", font=('Consolas',7))
lbl_roi.pack(pady=(0,1))
roi_preview = tk.Label(root, bg="black")
roi_preview.pack(pady=1)
lbl_poison = tk.Label(root, text="", bg="#0d0f14", fg="#10b981", font=("Malgun Gothic",8,"bold"))
lbl_poison.pack()

# --- 콜백 함수 ---
def save_cfg():
    cfg = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f: cfg = json.load(f)
        except: pass
        ctypes.windll.kernel32.SetFileAttributesW(CONFIG_FILE, 2)
    cfg["target_ip"] = ip_var.get()
    cfg["hp_roi"] = tuple(int(v) for v in HP_ROI)
    cfg["win_w"] = WIN_W
    cfg["win_h"] = WIN_H
    cfg["end_bert"] = bool(end_bert_var.get())
    if HP_100_REF is not None:
        cfg["hp_100_ref"] = HP_100_REF
    if os.path.exists(CONFIG_FILE): ctypes.windll.kernel32.SetFileAttributesW(CONFIG_FILE, 128)
    tmp = CONFIG_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(cfg, f, indent=2)
    os.replace(tmp, CONFIG_FILE)
    ctypes.windll.kernel32.SetFileAttributesW(CONFIG_FILE, 2)
    lbl_status.config(text="저장됨", fg="#10b981")

def set_100ref():
    global HP_100_REF
    x,y,w,h = HP_ROI
    img = sct.grab({"left":x,"top":y,"width":max(w,1),"height":max(h,1)})
    arr = np.array(img, dtype=np.uint8)[:,:,:3][:,:,::-1]
    red = (arr[:,:,0]>80)&(arr[:,:,0]>arr[:,:,1]*1.2)&(arr[:,:,0]>arr[:,:,2]*1.2)
    HP_100_REF = int(np.sum(red))
    save_cfg()
    lbl_status.config(text="100%%=%dpx" % HP_100_REF, fg="#10b981")

# --- 설정 버튼 행 ---
btn_row = tk.Frame(root, bg="#0d0f14")
btn_row.pack(fill='x', padx=6, pady=(2,1))
tk.Button(btn_row, text="🎯 피통", command=lambda: open_overlay(),
          bg="#1f538d", fg="#fff", font=('',7,'bold'), relief='flat',
          padx=4, cursor="hand2").pack(side='left', padx=1, fill='x', expand=True)
tk.Button(btn_row, text="💯 100%", command=set_100ref,
          bg="#fbbf24", fg="#000", font=('',7,'bold'), relief='flat',
          padx=4, cursor="hand2").pack(side='left', padx=1, fill='x', expand=True)

def update_bar():
    canvas.delete("all")
    w = canvas.winfo_width() or 200; h = canvas.winfo_height() or 34
    hp = max(0, min(100, hp_pct)); fw = int(w*hp/100)
    canvas.create_rectangle(0,0,w,h, fill="#1a1a2e", outline="#2a2a3e", width=1)
    c = "#10b981" if hp>50 else ("#fbbf24" if hp>25 else "#ef4444")
    canvas.create_rectangle(1,1,fw-1,h-1, fill=c, outline="")
    canvas.create_text(w//2,h//2, text="HP:%.0f%%" % hp,
                       fill="#fff", font=("Malgun Gothic",11,"bold"))

# ============================================================
# 원격 제어 버튼 (2x2 그리드)
# ============================================================
tk.Label(root, text="─"*28, bg="#0d0f14", fg="#2a2a3e", font=('',6)).pack(pady=(6,0))
tk.Label(root, text="쫄법PC 제어", bg="#0d0f14", fg="#f9e2af", font=("Malgun Gothic",8,"bold")).pack(pady=(0,2))

ctl_frame = tk.Frame(root, bg="#0d0f14")
ctl_frame.pack(fill='x', padx=6)
ctl_btns = [
    ("▶ 시작", b'I', "#10b981"),
    ("👣 클릭", b'H', "#3b82f6"),
    ("📌 고정", b'P', "#f59e0b"),
    ("🎒 줍기", b'L', "#8b5cf6"),
]
for i, (text, cmd, color) in enumerate(ctl_btns):
    row, col = i//2, i%2
    f = tk.Frame(ctl_frame, bg="#0d0f14")
    f.grid(row=row, column=col, padx=1, pady=1, sticky="ew")
    ctl_frame.grid_columnconfigure(col, weight=1)
    tk.Button(f, text=text, bg=color, fg="#fff", font=('',8,'bold'),
              relief='flat', padx=2, cursor="hand2",
              command=lambda c=cmd: send_remote_cmd(c)).pack(fill='x', pady=0)

# ============================================================
# Alt+숫자 매크로 (4x2 그리드)
# ============================================================
tk.Label(root, text="─"*28, bg="#0d0f14", fg="#2a2a3e", font=('',6)).pack(pady=(6,0))
tk.Label(root, text="쫄법PC 연동 단축키", bg="#0d0f14", fg="#f9e2af", font=("Malgun Gothic",8,"bold")).pack(pady=(0,2))

slot_colors = {1:"#313244",2:"#313244",3:"#313244",4:"#313244",
               5:"#313244",6:"#313244",7:"#313244",8:"#313244"}
slot_frame = tk.Frame(root, bg="#0d0f14")
slot_frame.pack(fill='x', padx=6)
for n in range(1,9):
    row = (n-1)//2; col = (n-1)%2
    f = tk.Frame(slot_frame, bg="#0d0f14")
    f.grid(row=row, column=col, padx=1, pady=1, sticky="ew")
    slot_frame.grid_columnconfigure(col, weight=1)
    tk.Button(f, text="Alt+%d F3>F%d" % (n, n+4), bg=slot_colors[n],
              fg="#fff", font=('',7,'bold'), relief='flat', padx=1, cursor="hand2",
              command=lambda s=n: sock.sendto(bytes([s+48]), (ip_var.get(), TARGET_PORT))
              ).pack(fill='x')

# ============================================================
# 드래그 오버레이
# ============================================================
def open_overlay():
    ov = tk.Toplevel(root)
    # 듀얼모니터 전체화면
    ov.overrideredirect(True)
    sx = ctypes.windll.user32.GetSystemMetrics(76)
    sy = ctypes.windll.user32.GetSystemMetrics(77)
    sw = ctypes.windll.user32.GetSystemMetrics(78)
    sh = ctypes.windll.user32.GetSystemMetrics(79)
    ov.geometry(f"{sw}x{sh}+{sx}+{sy}")
    ov.attributes("-topmost", True)
    ov.attributes("-alpha", 0.35)
    ov.configure(bg="black")

    cv = tk.Canvas(ov, bg="black", highlightthickness=0)
    cv.pack(fill="both", expand=True)

    drag = {"x1":0,"y1":0,"x2":0,"y2":0,"rect":None}

    def on_down(e):
        drag["x1"],drag["y1"] = e.x_root, e.y_root
        drag["rect"] = cv.create_rectangle(e.x_root-sx,e.y_root-sy,e.x_root-sx,e.y_root-sy,
                        outline="#10b981", width=4)

    def on_move(e):
        if drag["rect"]:
            cv.coords(drag["rect"], drag["x1"]-sx, drag["y1"]-sy, e.x_root-sx, e.y_root-sy)

    def on_up(e):
        drag["x2"],drag["y2"] = e.x_root, e.y_root
        x1 = min(drag["x1"],drag["x2"])
        y1 = min(drag["y1"],drag["y2"])
        x2 = max(drag["x1"],drag["x2"])
        y2 = max(drag["y1"],drag["y2"])
        w = x2-x1; h = y2-y1
        ov.destroy()
        if w < 10 or h < 2:
            lbl_status.config(text="너무 작음", fg="#fbbf24")
            return
        global HP_ROI
        HP_ROI = (x1, y1, w, h)
        lbl_roi.config(text="ROI=%s" % str(HP_ROI))
        save_cfg()
        lbl_status.config(text="저장됨!", fg="#10b981")

    cv.bind("<ButtonPress-1>", on_down)
    cv.bind("<B1-Motion>", on_move)
    cv.bind("<ButtonRelease-1>", on_up)

    tk.Label(ov, text="HP바 드래그 (ESC=취소)", fg="#10b981", bg="black",
             font=("Malgun Gothic",13,"bold")).place(x=sw//2, y=20, anchor="n")
    ov.bind("<Escape>", lambda e: ov.destroy())

def update_preview(arr):
    try:
        h, w = arr.shape[:2]
        pw = min(w*2, 200)
        ph = max(h*2, 6)
        img = Image.fromarray(arr).resize((pw, ph), Image.NEAREST)
        photo = ImageTk.PhotoImage(img)
        roi_preview.config(image=photo)
        roi_preview.image = photo
    except: pass

# ============================================================
# 전송 루프
# ============================================================
def _hp_bar_poisoned(red_cnt, green_cnt, total_px):
    return green_cnt > total_px * 0.05 or (green_cnt > red_cnt and green_cnt > total_px * 0.02)

def _is_petrified_bar(arr, red_cnt, total_px):
    """석화 판정 — 뚱힐러 is_gray_bar와 동일.
    금색 테두리가 빨강으로 조금 잡혀도, 평균색이 중성 회색이면 석화로 인정."""
    r = arr[:, :, 0].astype(int); g = arr[:, :, 1].astype(int); b = arr[:, :, 2].astype(int)
    gray = (abs(r - g) < 35) & (abs(g - b) < 35) & (abs(r - b) < 35) & (r > 20) & (r < 170)
    gray_cnt = int(np.sum(gray))
    if gray_cnt > total_px * 0.15 and red_cnt < total_px * 0.03:
        return True
    avg_r, avg_g, avg_b = float(np.mean(r)), float(np.mean(g)), float(np.mean(b))
    return abs(avg_r - avg_g) < 25 and abs(avg_g - avg_b) < 25 and abs(avg_r - avg_b) < 25 and avg_r > 50 and avg_r < 180

def hp_pct_from_bar(arr, w, h, petrified=False):
    """HP바 채움% — ROI 가로폭(열 수) 기준.
    평소: 빨강+초록(독). 석화일 때만 어두운 회색 열=채움(빈칸=밝은 은색 제외).
    석화%는 상·하 장식(금테/갈색)을 피하려고 ROI 세로 중앙 50%만 사용."""
    if petrified and w >= 2:
        # 석화: 고정밝기 임계 대신 채움|빈칸 경계 분할 (64%→85% 부풀림 방지)
        hh = arr.shape[0]
        y1, y2 = max(0, hh // 4), max(1, (3 * hh) // 4)
        if y2 <= y1:
            y1, y2 = 0, hh
        band = arr[y1:y2]
        R = band[:, :, 0].astype(np.float32)
        G = band[:, :, 1].astype(np.float32)
        B = band[:, :, 2].astype(np.float32)
        text = (R >= 190) & (G >= 190) & (B >= 190)
        R2 = R.copy(); R2[text] = np.nan
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
        best_l = (-1e9, None); best_r = (-1e9, None)
        lo, hi = max(1, ww // 20), min(ww, ww - ww // 20)
        for k in range(lo, hi):
            left = float(sm[:k].mean()); right = float(sm[k:].mean())
            if right - left > best_l[0]: best_l = (right - left, k)
            if left - right > best_r[0]: best_r = (left - right, k)
        cands = []
        if best_l[1] is not None:
            k = best_l[1]; cands.append((best_l[0], sm[:k], sm[k:], 100.0 * k / ww))
        if best_r[1] is not None:
            k = best_r[1]; cands.append((best_r[0], sm[k:], sm[:k], 100.0 * (ww - k) / ww))
        best = None
        for diff, fill_side, empty_side, pct in cands:
            fill_m = float(np.mean(fill_side)); empty_m = float(np.mean(empty_side))
            empty_p30 = float(np.percentile(empty_side, 30))
            if diff >= 12 and empty_p30 >= fill_m + 20 and empty_m >= fill_m + 15:
                if best is None or diff > best[0]:
                    best = (diff, pct)
        if best is None:
            return 100.0 if float(np.median(col)) <= 120 else round(100.0 * float(np.mean(col <= 105)), 1)
        return round(best[1], 1)
    red = (arr[:,:,0]>80)&(arr[:,:,0]>arr[:,:,1]*1.2)&(arr[:,:,0]>arr[:,:,2]*1.2)
    green = (arr[:,:,1]>15)&(arr[:,:,1]>arr[:,:,0]*1.03)&(arr[:,:,1]>arr[:,:,2]*1.03)
    bar_px = red | green
    if w >= 2:
        filled_cols = int(np.sum(np.any(bar_px, axis=0)))
        return round(filled_cols / w * 100, 1)
    red_cnt = int(np.sum(bar_px))
    total_px = max(w * h, 1)
    if HP_100_REF and HP_100_REF > 0:
        return round(red_cnt / HP_100_REF * 100, 1)
    return round(red_cnt / total_px * 100, 1)

def sender():
    global hp_pct
    while running:
        try:
            # 리니지 창이 맨 위에 있는지 확인
            # Alt+Tab 감지 제거됨
            x,y,w,h = HP_ROI
            if w < 5 or h < 1: time.sleep(0.1); continue
            img = sct.grab({"left":x,"top":y,"width":max(w,1),"height":max(h,1)})
            arr = np.array(img, dtype=np.uint8)[:,:,:3][:,:,::-1]
            red = (arr[:,:,0]>80)&(arr[:,:,0]>arr[:,:,1]*1.2)&(arr[:,:,0]>arr[:,:,2]*1.2)
            green = (arr[:,:,1]>15)&(arr[:,:,1]>arr[:,:,0]*1.03)&(arr[:,:,1]>arr[:,:,2]*1.03)
            green_cnt = int(np.sum(green))
            red_cnt = int(np.sum(red))
            total_px = max(w * h, 1)
            poisoned = _hp_bar_poisoned(red_cnt, green_cnt, total_px)
            petrified = _is_petrified_bar(arr, red_cnt, total_px)
            hp_pct = hp_pct_from_bar(arr, w, h, petrified=petrified)
            sock.sendto(struct.pack('fBB', hp_pct, 1 if poisoned else 0, 1 if petrified else 0), (ip_var.get(), TARGET_PORT))
            root.after(0, update_bar)
            root.after(0, lambda v=hp_pct: lbl_status.config(text="HP:%.0f%%" % v, fg="#10b981"))
            root.after(0, lambda p=poisoned, s=petrified: lbl_poison.config(
                text="중독!" if p else ("석화!" if s else ""), fg="#ef4444" if p else ("#8b5cf6" if s else "#10b981")))
            root.after(0, update_preview, arr.copy())
            time.sleep(0.1)
        except Exception as e:
            import traceback; traceback.print_exc()
            time.sleep(0.5)

threading.Thread(target=sender, daemon=True).start()

import traceback
def on_close():
    global running
    running = False
    keyboard.unhook_all()
    sock.close()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)
resize_grip = tk.Label(root, text="◢", bg="#313244", fg="#6c7086", font=("Malgun Gothic", 9, "bold"), cursor="sizing")
resize_grip.place(relx=1.0, rely=1.0, anchor="se")
resize_grip.bind("<ButtonPress-1>", _start_resize)
resize_grip.bind("<B1-Motion>", _do_resize)
resize_grip.bind("<ButtonRelease-1>", _end_resize)

def _upd_periodic():
    threading.Thread(target=lambda: check_for_update(force=False), daemon=True).start()
    root.after(600000, _upd_periodic)

root.after(15000, lambda: threading.Thread(target=lambda: check_for_update(force=True), daemon=True).start())
root.after(615000, _upd_periodic)

try:
    root.mainloop()
except Exception as e:
    print("GUI error: %s" % e)
    traceback.print_exc()
running = False; sock.close()
keyboard.unhook_all()