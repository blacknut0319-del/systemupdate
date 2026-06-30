# -*- coding: utf-8 -*-
"""
격수 HP 전송기 v7 — HP 전송 + 쫄법PC 원격 키보드 제어 통합
"""
import numpy as np
import sys, subprocess
for mod, pkg in [("numpy","numpy"),("PIL","pillow"),("mss","mss"),("keyboard","keyboard")]:
    try: __import__(mod)
    except: subprocess.check_call([sys.executable,"-m","pip","install",pkg,"--quiet"])

import socket, struct, json, os, threading, time
import tkinter as tk
from PIL import Image, ImageTk
import mss
import keyboard
import ctypes
import win32gui

PATCH_UPDATED_AT = "2026-06-18 13:32"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "udp_config.json")

TARGET_IP = "192.168.0.100"
TARGET_PORT = 9999
HP_ROI = (558, 878, 304, 5)
HP_100_REF = None

if os.path.exists(CONFIG_FILE):
    try:
        ctypes.windll.kernel32.SetFileAttributesW(CONFIG_FILE, 128)
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        TARGET_IP = cfg.get("target_ip", TARGET_IP)
        if "hp_roi" in cfg: HP_ROI = tuple(int(v) for v in cfg["hp_roi"])
        if "hp_100_ref" in cfg: HP_100_REF = cfg["hp_100_ref"]
    except: pass

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
DEBOUNCE = {'insert': 0, 'home': 0, 'page up': 0, 'f4': 0}
CMD_MAP = {'insert': b'I', 'home': b'H', 'page up': b'P', 'f4': b'L'}
CMD_NAMES = {b'I':'시작', b'H':'따라', b'P':'고정', b'L':'줍기'}

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

for key_name in ['insert', 'home', 'page up', 'f4']:
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

# ============================================================
# 메인 GUI
# ============================================================
root = tk.Tk()
root.overrideredirect(True)
root.geometry("250x100+0+0")
root.attributes("-topmost", True)
root.configure(bg="#0d0f14")  # header UI v2

# ── 헤더바 ──
header = tk.Frame(root, bg="#141420", height=24)
header.pack(fill="x")
header.pack_propagate(False)
tk.Label(header, text=PATCH_UPDATED_AT, bg="#141420", fg="#ffffff", font=("Consolas", 7)).place(x=8, rely=0.5, anchor="w")
tk.Label(header, text="격수 HP 전송기", bg="#141420", fg="#cba6f7", font=("Malgun Gothic", 10, "bold")).place(relx=0.5, rely=0.5, anchor="center")
# 닫기
close_btn = tk.Label(header, text="✕", bg="#141420", fg="#f38ba8", font=("", 11))
close_btn.place(relx=1.0, x=-10, rely=0.5, anchor="e")
close_btn.bind("<Button-1>", lambda e: root.destroy())

# 드래그 이동
def start_move(e): root.start_x, root.start_y = e.x, e.y
def do_move(e): root.geometry(f"+{e.x_root - root.start_x}+{e.y_root - root.start_y}")
header.bind("<Button-1>", start_move)
header.bind("<B1-Motion>", do_move)
header.bind("<Button-3>", start_move)
header.bind("<B3-Motion>", do_move)

def auto_resize_height():
    if root and root.winfo_exists():
        h = root.winfo_reqheight()
        if h > 100:
            x = root.winfo_x(); y = root.winfo_y()
            root.geometry("225x%d+%d+%d" % (h, x, y))
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
            raw = int(np.sum(red))
            green = (arr[:,:,1]>80)&(arr[:,:,1]>arr[:,:,0]*1.2)&(arr[:,:,1]>arr[:,:,2]*1.2)
            poisoned = int(np.sum(green)) > (w*h*0.08)
            gray = (abs(arr[:,:,0]-arr[:,:,1])<25)&(abs(arr[:,:,1]-arr[:,:,2])<25)&(abs(arr[:,:,0]-arr[:,:,2])<25)&(arr[:,:,0]>30)
            petrified = int(np.sum(gray)) > (w*h*0.12)
            hp_pct = round(raw/HP_100_REF*100,1) if (HP_100_REF and HP_100_REF>0) else round(raw/max(w*h,1)*100,1)
            sock.sendto(struct.pack('fBB', hp_pct, 1 if poisoned else 0, 1 if petrified else 0), (ip_var.get(), TARGET_PORT))
            root.after(0, update_bar)
            root.after(0, lambda v=hp_pct: lbl_status.config(text="HP:%.0f%%" % v, fg="#10b981"))
            root.after(0, lambda p=poisoned, s=petrified: lbl_poison.config(
                text="중독!" if p else ("석화!" if s else ""), fg="#ef4444" if p else ("#8b5cf6" if s else "#10b981")))
            root.after(0, update_preview, arr.copy())
            time.sleep(0.3)
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
try:
    root.mainloop()
except Exception as e:
    print("GUI error: %s" % e)
    traceback.print_exc()
running = False; sock.close()
keyboard.unhook_all()