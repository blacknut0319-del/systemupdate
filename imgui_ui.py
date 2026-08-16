# -*- coding: utf-8 -*-
"""뚱힐러 메인/인증 UI — Dear ImGui. 로직·변수는 _decrypted 쪽을 그대로 쓴다."""
import os
import sys
import time
import ctypes
import json
import urllib.request

_glfw_window = None
_gui_hidden = False
_win_w = 220
_win_h = 0
_impl = None
_main_ctx = None
_ov_win = None
_ov_impl = None
_ov_ctx = None
_ui_dpi = 1.0
# 예전 CTk Collapsible 과 동일: 옵션/힐 접힘, 버프만 펼침
_sections = {"opt": False, "buff": True, "heal": False}
_log_follow = True

_overlay = {
    "kind": None,
    "title": "",
    "body": "",
    "yes_fn": None,
    "no_fn": None,
    "ow": 460,
    "oh": 400,
}
_pending_overlay = None
_saved_geom = None


def is_active():
    return _glfw_window is not None


def _cloak_hwnd(hwnd):
    """해당 윈도우가 클릭을 먹지 않게 숨김."""
    try:
        user32 = ctypes.windll.user32
        hwnd = int(hwnd)
        gwl = -20
        ex_add = 0x00080000 | 0x00000020 | 0x00000080 | 0x08000000
        if hasattr(user32, "GetWindowLongPtrW"):
            ex = user32.GetWindowLongPtrW(hwnd, gwl)
            user32.SetWindowLongPtrW(hwnd, gwl, int(ex) | ex_add)
        else:
            ex = user32.GetWindowLongW(hwnd, gwl)
            user32.SetWindowLongW(hwnd, gwl, int(ex) | ex_add)
        user32.ShowWindow(hwnd, 0)
        user32.SetWindowPos(hwnd, 1, -32000, -32000, 1, 1, 0x0010)
    except Exception:
        pass


def _cloak_stray_windows():
    """CTk TtkMonitor 등 아래 모니터를 덮는 숨은 창 클릭 통과."""
    try:
        user32 = ctypes.windll.user32
        pid_me = os.getpid()
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        def _enum(hwnd, _l):
            proc = ctypes.c_uint(0)
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(proc))
            if int(proc.value) != pid_me:
                return True
            buf = ctypes.create_unicode_buffer(128)
            user32.GetClassNameW(hwnd, buf, 128)
            if buf.value == "TtkMonitorClass":
                _cloak_hwnd(hwnd)
            return True

        user32.EnumWindows(WNDENUMPROC(_enum), 0)
    except Exception:
        pass


def _detach_tk_toplevel(win):
    """숨긴 루트에 묶인 Toplevel 을 떼서 옮길 때 튕기지 않게 함."""
    try:
        win.update_idletasks()
        user32 = ctypes.windll.user32
        hid = int(win.winfo_id())
        hwnd = int(user32.GetParent(hid) or hid)
        gwl_hwndparent = -8
        if hasattr(user32, "SetWindowLongPtrW"):
            user32.SetWindowLongPtrW(hwnd, gwl_hwndparent, 0)
        else:
            user32.SetWindowLongW(hwnd, gwl_hwndparent, 0)
    except Exception:
        pass


def _cloak_tk_root(root):
    """숨긴 CTk 루트·모니터창이 클릭을 먹지 않게 완전히 숨김."""
    if root is not None:
        try:
            root.withdraw()
            root.attributes("-topmost", False)
            root.geometry("1x1+-32000+-32000")
        except Exception:
            pass
        try:
            user32 = ctypes.windll.user32
            hid = int(root.winfo_id())
            hwnd = int(user32.GetParent(hid) or hid)
            _cloak_hwnd(hwnd)
        except Exception:
            pass
    _cloak_stray_windows()


def _left_down():
    try:
        return bool(ctypes.windll.user32.GetAsyncKeyState(0x01) & 0x8000)
    except Exception:
        return False


def set_hidden(hidden):
    global _gui_hidden
    _gui_hidden = bool(hidden)
    if _glfw_window is None:
        return
    import glfw
    if _gui_hidden:
        glfw.hide_window(_glfw_window)
    else:
        glfw.show_window(_glfw_window)


def _cap_overlay_h(h, min_h=180):
    try:
        import glfw
        mon = glfw.get_primary_monitor()
        cap = int(glfw.get_video_mode(mon).size.height * 0.88) if mon else 900
        return max(int(min_h), min(int(h), cap))
    except Exception:
        return max(int(min_h), int(h))


def _center_glfw(win, w, h):
    import glfw
    try:
        mon = glfw.get_primary_monitor()
        mode = glfw.get_video_mode(mon)
        sw, sh = mode.size.width, mode.size.height
        glfw.set_window_pos(win, max(0, int((sw - w) / 2)), max(0, int((sh - h) / 2)))
    except Exception:
        pass


def _present_glfw_window(win, w, h, title=None):
    """작업표시줄만 보이고 폼이 안 뜨는 경우 방지."""
    import glfw
    try:
        _center_glfw(win, int(w), int(h))
        glfw.show_window(win)
        glfw.focus_window(win)
        hwnd = glfw.get_win32_window(win)
        if hwnd:
            user32 = ctypes.windll.user32
            user32.ShowWindow(int(hwnd), 9)
            user32.SetForegroundWindow(int(hwnd))
        if title:
            _set_hwnd_title(win, title)
    except Exception:
        pass


def _ensure_popup_window(title, w, h):
    """메인과 별도 glfw 창. 확인/제어판/패치/가이드 전부 여기."""
    global _ov_win, _ov_impl, _ov_ctx
    import glfw
    from OpenGL import GL as gl
    import imgui
    from imgui.integrations.glfw import GlfwRenderer

    w = int(w)
    min_h = 64 if _overlay.get("kind") in ("alert", "yesno") else 180
    h = _cap_overlay_h(h, min_h)
    _overlay["ow"] = w
    _overlay["oh"] = h
    if _ov_win is not None:
        try:
            glfw.set_window_size(_ov_win, w, h)
            _center_glfw(_ov_win, w, h)
            glfw.show_window(_ov_win)
            glfw.focus_window(_ov_win)
            glfw.set_window_should_close(_ov_win, False)
            _set_hwnd_title(_ov_win, title)
        except Exception:
            pass
        return True
    if _glfw_window is None:
        return False
    glfw.window_hint(glfw.FLOATING, glfw.TRUE)
    glfw.window_hint(glfw.DECORATED, glfw.FALSE)
    glfw.window_hint(glfw.RESIZABLE, glfw.FALSE)
    glfw.window_hint(glfw.VISIBLE, glfw.TRUE)
    win = glfw.create_window(w, h, title, None, _glfw_window)
    if not win:
        return False
    _center_glfw(win, w, h)
    main_ctx = imgui.get_current_context()
    glfw.make_context_current(win)
    glfw.swap_interval(0)
    _ov_ctx = imgui.create_context()
    imgui.set_current_context(_ov_ctx)
    io = imgui.get_io()
    io.ini_file_name = None
    _load_korean_font(io, 14.0 * _ui_dpi)
    io.font_global_scale = 1.0 / max(_ui_dpi, 1.0)
    _ov_impl = GlfwRenderer(win)
    _apply_theme()
    gl.glClearColor(0.078, 0.078, 0.125, 1.0)
    _ov_win = win
    _set_hwnd_title(win, title)
    imgui.set_current_context(main_ctx)
    glfw.make_context_current(_glfw_window)
    return True


def close_overlay():
    _overlay["kind"] = None
    _overlay["title"] = ""
    _overlay["body"] = ""
    _overlay["yes_fn"] = None
    _overlay["no_fn"] = None
    _modal["open"] = False
    if _ov_win is not None:
        import glfw
        try:
            glfw.hide_window(_ov_win)
        except Exception:
            pass


def _begin_overlay(kind, title, w, h, body="", yes_fn=None, no_fn=None):
    if _glfw_window is None:
        return False
    _overlay["kind"] = kind
    _overlay["title"] = title
    _overlay["body"] = body
    _overlay["yes_fn"] = yes_fn
    _overlay["no_fn"] = no_fn
    _overlay["ow"] = int(w)
    _overlay["oh"] = int(h)
    return _ensure_popup_window(title, w, h)


def _schedule_overlay(kind, title, w, h, body="", yes_fn=None, no_fn=None, **extra):
    """ImGui 프레임 도중 GLFW 창을 만들면 멈춤/크래시 → 다음 tick 에서 연다."""
    global _pending_overlay
    job = {
        "kind": kind,
        "title": title,
        "w": int(w),
        "h": int(h),
        "body": body,
        "yes_fn": yes_fn,
        "no_fn": no_fn,
    }
    job.update(extra)
    _pending_overlay = job
    return True


def _flush_pending_overlay():
    global _pending_overlay
    job = _pending_overlay
    if not job:
        return
    _pending_overlay = None
    try:
        kind = job.get("kind")
        if kind == "km_ip":
            _overlay["box_ip"] = job.get("box_ip")
            _overlay["pc_ip"] = job.get("pc_ip")
        _begin_overlay(
            kind,
            job.get("title") or "",
            job.get("w") or 460,
            job.get("h") or 400,
            body=job.get("body") or "",
            yes_fn=job.get("yes_fn"),
            no_fn=job.get("no_fn"),
        )
    except Exception:
        import traceback
        traceback.print_exc()


def open_guide():
    return _schedule_overlay("guide", "📖 뚱힐러 가이드", 460, 680)


def open_patch():
    return _schedule_overlay("patch", "패치노트", 480, 580)


_modal = {
    "open": False,
    "kind": "alert",
    "title": "",
    "body": "",
    "yes_fn": None,
    "no_fn": None,
}

_admin = {
    "dirty": True,
    "last_prev": 0.0,
    "last_live": 0.0,
    "self_txt": "",
    "self_col": "#f0f0f0",
    "mna_txt": "",
    "mna_col": "#f0f0f0",
    "stream_txt": "미설정 → 격수 쫄화면에 주 모니터 전체 송출",
    "stream_col": "#6c7086",
    "party": [{"pct": None, "status": "", "diag": ""} for _ in range(8)],
}
_tex = {}


def admin_mark_dirty():
    _admin["dirty"] = True


def _fit_alert_wh(title, body, min_w, extra_h):
    parts = [str(title or "")]
    parts.extend(str(body or "").replace("\r", "").split("\n"))
    longest = 0
    for ln in parts:
        n = 0
        for ch in ln:
            n += 13 if ord(ch) > 0x2FF else 7
        if n > longest:
            longest = n
    w = max(int(min_w), min(360, longest + 20))
    lines = max(1, str(body or "").count("\n") + 1)
    h = max(64, 32 + lines * 16 + extra_h)
    return w, h


def show_alert(title, body):
    if _glfw_window is None:
        return False
    if _overlay.get("kind") and _overlay["kind"] not in ("alert", "yesno"):
        _modal.update(open=True, kind="alert", title=title, body=body, yes_fn=None, no_fn=None)
        return True
    w, h = _fit_alert_wh(title, body, 160, 24)
    return _schedule_overlay("alert", title, w, h, body=body)


def show_yesno(title, body, on_yes, on_no=None):
    if _glfw_window is None:
        return False
    if _overlay.get("kind") and _overlay["kind"] not in ("alert", "yesno"):
        _modal.update(open=True, kind="yesno", title=title, body=body, yes_fn=on_yes, no_fn=on_no)
        return True
    w, h = _fit_alert_wh(title, body, 180, 28)
    return _schedule_overlay("yesno", title, w, h, body=body, yes_fn=on_yes, no_fn=on_no)


def open_admin():
    _admin["dirty"] = True
    return _schedule_overlay("admin", "실시간 제어판", 540, 640)


def open_km_trans():
    return _schedule_overlay("km_trans", "설정도구 한글 통역", 440, 560)


def open_km_ip(box_ip, pc_ip):
    return _schedule_overlay(
        "km_ip", "뚱박스 랜(IP) 설정", 420, 520, box_ip=box_ip, pc_ip=pc_ip
    )


def _ctk_toplevel_open(root):
    if root is None:
        return False
    try:
        import tkinter as tk
        for w in root.winfo_children():
            try:
                if isinstance(w, tk.Toplevel) and w.winfo_exists():
                    try:
                        if str(w.state()) == "withdrawn":
                            continue
                    except Exception:
                        pass
                    return True
            except Exception:
                pass
    except Exception:
        pass
    return False


def _should_pause_glfw(g):
    try:
        busy = g.get("_ui_busy")
        if callable(busy) and busy():
            return True
    except Exception:
        pass
    return _ctk_toplevel_open(g.get("root"))


def _hex(c, a=1.0):
    if not c:
        return (1.0, 1.0, 1.0, a)
    if isinstance(c, (tuple, list)):
        if len(c) >= 3 and float(c[0]) <= 1.0:
            return (float(c[0]), float(c[1]), float(c[2]), float(c[3]) if len(c) > 3 else a)
        return (float(c[0]) / 255.0, float(c[1]) / 255.0, float(c[2]) / 255.0, a)
    s = str(c).strip()
    if s.startswith("#"):
        s = s[1:]
    if len(s) == 6:
        return (int(s[0:2], 16) / 255.0, int(s[2:4], 16) / 255.0, int(s[4:6], 16) / 255.0, a)
    return (1.0, 1.0, 1.0, a)


def _text_c(text, color="#ffffff"):
    import imgui
    r, g, b, a = _hex(color)
    imgui.text_colored(str(text), r, g, b, a)


def _center_text(text, color="#ffffff"):
    import imgui
    s = str(text)
    if not s:
        return
    tw = imgui.calc_text_size(s).x
    win_w = imgui.get_window_width()
    pad = imgui.get_style().window_padding.x
    imgui.set_cursor_pos_x(max(pad, (win_w - tw) * 0.5))
    _text_c(s, color)


def _title_row_hovered(close_w=26):
    """타이틀 줄 전체(닫기 버튼 제외)에서 창 이동."""
    import imgui
    io = imgui.get_io()
    wx, wy = imgui.get_window_position()
    ww = imgui.get_window_width()
    pad_y = imgui.get_style().window_padding.y
    th = pad_y + max(18, imgui.get_text_line_height_with_spacing())
    mx, my = io.mouse_pos
    return (wx <= mx < wx + ww - close_w) and (wy <= my < wy + th)


def _lbl_text(w, default=""):
    try:
        t = w.cget("text")
        return t if t is not None else default
    except Exception:
        return default


def _lbl_color(w, default="#cdd6f4"):
    try:
        return w.cget("text_color") or default
    except Exception:
        return default


def _attacker_udp_ui(g):
    """ImGui는 숨긴 CTkLabel 갱신을 못 읽는 경우가 있어 전역값을 직접 본다."""
    fn = g.get("_attacker_link_ui")
    if callable(fn):
        try:
            return fn()
        except Exception:
            pass
    import time
    listen_ok = bool(g.get("udp_listen_ok"))
    try:
        last_t = float(g.get("last_udp_time") or 0)
    except Exception:
        last_t = 0.0
    try:
        hp = float(g.get("attacker_hp_udp") or 0)
    except Exception:
        hp = 0.0
    if not listen_ok:
        return "격수: 오류", "#ef4444", "○ 대기", "#f38ba8"
    if last_t <= 0 or (time.time() - last_t) > 5.0:
        return "격수: 끊김", "#ef4444", "○ 대기", "#f9e2af"
    return "격수: %.0f%%" % hp, "#ef4444", "✅ 연결", "#a6e3a1"


def _bool_cb(label, var, cmd=None):
    import imgui
    cur = bool(var.get())
    clicked, val = imgui.checkbox(label, cur)
    if clicked and val != cur:
        var.set(val)
        if cmd:
            try:
                cmd()
            except Exception:
                pass
    return val


HB_W = 28
SL_W = 32


def _center_width(w):
    import imgui
    x = imgui.get_cursor_pos_x()
    avail = imgui.get_content_region_available().x
    imgui.set_cursor_pos_x(x + max(0.0, (avail - w) * 0.5))


def _combo(label, items, var, cmd=None, width=0, arrow=True):
    import imgui
    items = list(items)
    cur = var.get()
    if cur not in items:
        items = ([cur] + items) if cur else items
    idx = items.index(cur) if cur in items else 0
    preview = items[idx] if items else ""
    if width:
        imgui.set_next_item_width(width)
    flags = 0 if arrow else imgui.COMBO_NO_ARROW_BUTTON
    opened = imgui.begin_combo(label, preview, flags)
    if opened:
        for i, it in enumerate(items):
            clicked, _sel = imgui.selectable(str(it), i == idx)
            if clicked:
                var.set(it)
                if cmd:
                    try:
                        cmd(it)
                    except TypeError:
                        try:
                            cmd()
                        except Exception:
                            pass
                    except Exception:
                        pass
        imgui.end_combo()


def _gold_combo(label, items, var, cmd=None, width=0, arrow=True, height=18):
    """골드 테두리 픽버튼. 글자는 가운데. 목록은 골드 선택."""
    import imgui
    items = list(items)
    cur = var.get()
    if cur not in items:
        items = ([cur] + items) if cur else items
    preview = cur if cur in items else (items[0] if items else "")
    shown = ("%s ▾" % preview) if arrow else preview
    imgui.push_style_color(imgui.COLOR_BUTTON, *_hex("#16161f"))
    imgui.push_style_color(imgui.COLOR_BUTTON_HOVERED, *_hex("#22222c"))
    imgui.push_style_color(imgui.COLOR_BUTTON_ACTIVE, *_hex("#22222c"))
    imgui.push_style_color(imgui.COLOR_BORDER, *_hex("#c9a84c"))
    imgui.push_style_color(imgui.COLOR_TEXT, *_hex("#f0d9a8"))
    imgui.push_style_var(imgui.STYLE_FRAME_BORDERSIZE, 1)
    imgui.push_style_var(imgui.STYLE_FRAME_ROUNDING, 6)
    imgui.push_style_var(imgui.STYLE_BUTTON_TEXT_ALIGN, (0.5, 0.5))
    vid = "%s###%s" % (shown, label)
    clicked = imgui.button(vid, width, height) if width else imgui.button(vid)
    imgui.pop_style_var(3)
    imgui.pop_style_color(5)
    pop = str(label) + "_pop"
    if clicked:
        imgui.open_popup(pop)
    pw = width if (width and width > 40) else 120
    imgui.set_next_window_size_constraints((80, 36), (min(240, max(80, pw + 24)), 280))
    imgui.push_style_color(imgui.COLOR_POPUP_BACKGROUND, *_hex("#14141c"))
    imgui.push_style_color(imgui.COLOR_BORDER, *_hex("#3d3a2f"))
    imgui.push_style_color(imgui.COLOR_HEADER, *_hex("#2a2118"))
    imgui.push_style_color(imgui.COLOR_HEADER_HOVERED, *_hex("#3d2e1f"))
    imgui.push_style_color(imgui.COLOR_HEADER_ACTIVE, *_hex("#3d2e1f"))
    imgui.push_style_color(imgui.COLOR_TEXT, *_hex("#f0d9a8"))
    imgui.push_style_var(imgui.STYLE_POPUP_ROUNDING, 10)
    imgui.push_style_var(imgui.STYLE_POPUP_BORDERSIZE, 1)
    imgui.push_style_var(imgui.STYLE_WINDOW_PADDING, (6, 6))
    opened = False
    try:
        opened = imgui.begin_popup(pop)
        if opened:
            for it in items:
                hit, _sel = imgui.selectable("  %s" % it, str(it) == preview)
                if hit:
                    var.set(it)
                    if cmd:
                        try:
                            cmd(it)
                        except TypeError:
                            try:
                                cmd()
                            except Exception:
                                pass
                        except Exception:
                            pass
                    imgui.close_current_popup()
            imgui.end_popup()
    finally:
        imgui.pop_style_var(3)
        imgui.pop_style_color(6)


def _input_var(label, var, width=0):
    import imgui
    if width:
        imgui.set_next_item_width(width)
    changed, text = imgui.input_text(label, var.get(), -1)
    if changed:
        var.set(text)
    return text


def _input_entry(label, entry, width=0):
    import imgui
    if width:
        imgui.set_next_item_width(width)
    changed, text = imgui.input_text(label, entry.get(), -1)
    if changed:
        try:
            entry.delete(0, "end")
            entry.insert(0, text)
        except Exception:
            pass
    return text


def _slider_int(label, var, vmin, vmax, fill="#f38ba8"):
    import imgui
    imgui.push_style_color(imgui.COLOR_SLIDER_GRAB, *_hex("#d4af37"))
    imgui.push_style_color(imgui.COLOR_SLIDER_GRAB_ACTIVE, *_hex("#f0d878"))
    imgui.push_style_color(imgui.COLOR_FRAME_BACKGROUND, *_hex("#1e1e2e"))
    imgui.push_style_color(imgui.COLOR_FRAME_BACKGROUND_ACTIVE, *_hex(fill, 0.35))
    imgui.push_style_color(imgui.COLOR_FRAME_BACKGROUND_HOVERED, *_hex(fill, 0.22))
    imgui.set_next_item_width(-36)
    changed, val = imgui.slider_int(label, int(var.get()), int(vmin), int(vmax), "%d%%")
    imgui.pop_style_color(5)
    if changed:
        var.set(int(val))
    imgui.same_line()
    _text_c("%d%%" % int(var.get()), fill)


def _btn(label, fg, hover, width=0, height=0, text_color=None):
    import imgui
    n = 3
    imgui.push_style_color(imgui.COLOR_BUTTON, *_hex(fg))
    imgui.push_style_color(imgui.COLOR_BUTTON_HOVERED, *_hex(hover))
    imgui.push_style_color(imgui.COLOR_BUTTON_ACTIVE, *_hex(hover))
    if text_color:
        imgui.push_style_color(imgui.COLOR_TEXT, *_hex(text_color))
        n += 1
    clicked = imgui.button(label, width, height) if width else imgui.button(label)
    imgui.pop_style_color(n)
    return clicked


def _apply_theme():
    import imgui
    st = imgui.get_style()
    st.window_rounding = 8
    st.frame_rounding = 5
    st.grab_rounding = 10
    st.grab_min_size = 11
    st.window_padding = (5, 4)
    st.frame_padding = (4, 2)
    st.item_spacing = (4, 3)
    st.item_inner_spacing = (3, 2)
    st.window_border_size = 1
    st.frame_border_size = 0
    st.child_rounding = 6
    st.button_text_align = (0.5, 0.5)
    colors = st.colors
    colors[imgui.COLOR_WINDOW_BACKGROUND] = _hex("#141420")
    colors[imgui.COLOR_CHILD_BACKGROUND] = _hex("#181825")
    colors[imgui.COLOR_BORDER] = _hex("#313244")
    colors[imgui.COLOR_TEXT] = _hex("#ffffff")
    colors[imgui.COLOR_TEXT_DISABLED] = _hex("#d0d0d0")
    colors[imgui.COLOR_FRAME_BACKGROUND] = _hex("#1e1e2e")
    colors[imgui.COLOR_FRAME_BACKGROUND_HOVERED] = _hex("#313244")
    colors[imgui.COLOR_FRAME_BACKGROUND_ACTIVE] = _hex("#45475a")
    colors[imgui.COLOR_BUTTON] = _hex("#313244")
    colors[imgui.COLOR_BUTTON_HOVERED] = _hex("#45475a")
    colors[imgui.COLOR_BUTTON_ACTIVE] = _hex("#585b70")
    colors[imgui.COLOR_HEADER] = _hex("#313244")
    colors[imgui.COLOR_HEADER_HOVERED] = _hex("#45475a")
    colors[imgui.COLOR_HEADER_ACTIVE] = _hex("#585b70")
    colors[imgui.COLOR_CHECK_MARK] = _hex("#f38ba8")
    colors[imgui.COLOR_SLIDER_GRAB] = _hex("#d4af37")
    colors[imgui.COLOR_SLIDER_GRAB_ACTIVE] = _hex("#f0d878")
    colors[imgui.COLOR_POPUP_BACKGROUND] = _hex("#1e1e2e")
    colors[imgui.COLOR_TITLE_BACKGROUND] = _hex("#141420")
    colors[imgui.COLOR_TITLE_BACKGROUND_ACTIVE] = _hex("#141420")
    colors[imgui.COLOR_SEPARATOR] = _hex("#313244")
    colors[imgui.COLOR_RESIZE_GRIP] = _hex("#313244")
    colors[imgui.COLOR_RESIZE_GRIP_HOVERED] = _hex("#45475a")


def _load_korean_font(io, size=13.0):
    import imgui
    candidates = [
        r"C:\Windows\Fonts\malgunbd.ttf",
        r"C:\Windows\Fonts\malgun.ttf",
        r"C:\Windows\Fonts\gulim.ttc",
        r"C:\Windows\Fonts\msgothic.ttc",
    ]
    font = None
    used = None
    kr = io.fonts.get_glyph_ranges_korean()
    for path in candidates:
        if os.path.isfile(path):
            font = io.fonts.add_font_from_file_ttf(path, size, glyph_ranges=kr)
            if font:
                used = path
                break
    if not font:
        return None
    # 뚱박스 통역 한자(连接盒子 등). 한글 레인지만 쓰면 ??? 로 나옴
    if used:
        cfg = imgui.FontConfig(merge_mode=True, pixel_snap_h=True)
        cn = None
        for name in ("get_glyph_ranges_chinese_simplified_common", "get_glyph_ranges_chinese_full"):
            fn = getattr(io.fonts, name, None)
            if callable(fn):
                try:
                    cn = fn()
                    break
                except Exception:
                    cn = None
        if cn is None:
            cn = imgui.GlyphRanges([0x4E00, 0x9FFF, 0])
        io.fonts.add_font_from_file_ttf(used, size, font_config=cfg, glyph_ranges=cn)
    # 맑은고딕엔 이모지가 없어서 ?? 로 나옴 → Segoe 심볼/이모지 합치기
    icon_ranges = imgui.GlyphRanges([
        0x2000, 0x206F,
        0x2190, 0x21FF,
        0x2300, 0x23FF,
        0x2460, 0x24FF,
        0x2500, 0x27BF,
        0x2B00, 0x2BFF,
        0xFE00, 0xFE0F,
        0x1F300, 0x1FAFF,
        0,
    ])
    for icon_path in (r"C:\Windows\Fonts\seguisym.ttf", r"C:\Windows\Fonts\seguiemj.ttf"):
        if not os.path.isfile(icon_path):
            continue
        cfg = imgui.FontConfig(merge_mode=True, pixel_snap_h=True)
        io.fonts.add_font_from_file_ttf(icon_path, size, font_config=cfg, glyph_ranges=icon_ranges)
    return font


def _draw_log_panel(log):
    """로그: 새 줄 오면 맨 아래 따라가되, 위로 스크롤하면 멈춤."""
    import imgui

    global _log_follow
    text = str(log or "시스템 시작")
    imgui.begin_child("##logscroll", width=-1, height=56, border=True)
    prev_y = imgui.get_scroll_y()
    prev_max = imgui.get_scroll_max_y()
    at_bottom = prev_y >= max(0.0, prev_max - 2.0)
    io = imgui.get_io()
    if imgui.is_window_hovered():
        if io.mouse_wheel > 0:
            _log_follow = False
        elif at_bottom or io.mouse_wheel < 0:
            _log_follow = True
    for ln in text.split("\n"):
        if ln:
            imgui.text_wrapped(ln)
    max_y = imgui.get_scroll_max_y()
    if _log_follow and max_y > 0:
        imgui.set_scroll_y(max_y)
    elif at_bottom:
        _log_follow = True
    imgui.end_child()


def _collapsible(title, key):
    """CTk Collapsible 과 같은 ▶/▼ 헤더. 눌러야 접히고 펼쳐짐."""
    global _win_h
    open_ = bool(_sections.get(key))
    arrow = "▼" if open_ else "▶"
    if _btn("%s  %s" % (arrow, title), "#313244", "#45475a", width=-1, height=22):
        open_ = not open_
        _sections[key] = open_
        _win_h = 0
    return open_


def _set_hwnd_title(window, title):
    try:
        import glfw
        hwnd = glfw.get_win32_window(window)
        if hwnd:
            ctypes.windll.user32.SetWindowTextW(int(hwnd), title)
    except Exception:
        pass


def _cursor_screen():
    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
    p = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(p))
    return p.x, p.y


def _init_glfw_window(title, w, h, x=0, y=0):
    import glfw
    from OpenGL import GL as gl
    import imgui
    from imgui.integrations.glfw import GlfwRenderer

    os.environ.setdefault("DISCORD_DISABLE_OVERLAY", "1")
    os.environ.setdefault("DISABLE_DISCORD_OVERLAY", "1")
    if not glfw.init():
        raise RuntimeError("glfw init failed")
    glfw.window_hint(glfw.FLOATING, glfw.TRUE)
    glfw.window_hint(glfw.DECORATED, glfw.FALSE)
    glfw.window_hint(glfw.RESIZABLE, glfw.FALSE)
    glfw.window_hint(glfw.VISIBLE, glfw.TRUE)
    window = glfw.create_window(int(w), int(h), title, None, None)
    if not window:
        glfw.terminate()
        raise RuntimeError("glfw window failed")
    glfw.set_window_pos(window, int(x), int(y))
    glfw.make_context_current(window)
    glfw.swap_interval(0)
    try:
        glfw.set_input_mode(window, glfw.CURSOR, glfw.CURSOR_NORMAL)
    except Exception:
        pass
    try:
        sx, sy = glfw.get_window_content_scale(window)
        dpi = max(float(sx or 1.0), float(sy or 1.0), 1.0)
    except Exception:
        dpi = 1.0
    imgui.create_context()
    io = imgui.get_io()
    io.ini_file_name = None
    global _ui_dpi
    _ui_dpi = dpi
    _load_korean_font(io, 14.0 * dpi)
    io.font_global_scale = 1.0 / dpi
    impl = GlfwRenderer(window)
    _apply_theme()
    gl.glClearColor(0.078, 0.078, 0.125, 1.0)
    _set_hwnd_title(window, title)
    return window, impl


def _shutdown_glfw(window, impl):
    import glfw
    import imgui
    try:
        if impl:
            impl.shutdown()
    except Exception:
        pass
    try:
        if window:
            glfw.destroy_window(window)
    except Exception:
        pass
    try:
        imgui.destroy_context()
    except Exception:
        pass
    try:
        glfw.terminate()
    except Exception:
        pass


def run_auth(g):
    """저장된 코드가 없을 때 ImGui 인증창. 성공하면 True."""
    import glfw
    from OpenGL import GL as gl
    import imgui

    pw = ""
    com = str(g.get("SERIAL_PORT") or "")
    err = ""
    ok = {"v": False}

    def check_login():
        nonlocal pw, com, err
        pwd = (pw or "").strip()
        user_com = (com or "").strip().upper()
        if not pwd:
            return
        if user_com:
            g["SERIAL_PORT"] = user_com
        server_result, server_info, server_start = g["check_google_sheet"](pwd)
        if server_result == "PASS":
            if server_info == "0":
                err = "만료된 코드입니다"
                return
            g["_sync_expire_cache"](server_info, server_start)
            g["save_hidden_config"](pwd)
            g["loaded_pwd"] = pwd
            g["authenticated"] = True
            ok["v"] = True
        elif server_result == "REGISTER":
            gas = g.get("GAS_API_URL")
            if gas:
                try:
                    reg_data = json.dumps({"code": pwd, "hwid": g["MY_HWID"]}).encode()
                    reg_req = urllib.request.Request(
                        gas, data=reg_data, headers={"Content-Type": "application/json"}
                    )
                    reg_resp = json.loads(urllib.request.urlopen(reg_req, timeout=8).read())
                    if reg_resp.get("result") == "OK":
                        _r, _i, _s = g["check_google_sheet"](pwd)
                        if _r not in ("ERROR",):
                            g["_sync_expire_cache"](_i, _s)
                        g["save_hidden_config"](pwd)
                        g["loaded_pwd"] = pwd
                        g["authenticated"] = True
                        ok["v"] = True
                    else:
                        err = "이미 다른 PC에서 등록된 코드입니다"
                except Exception:
                    err = "인증 서버 연결 실패"
            else:
                err = "API 설정이 필요합니다"
        elif server_result == "ALREADY_IN_USE":
            err = "다른 PC에서 사용 중인 코드입니다"
        elif server_result == "NOT_FOUND":
            err = "등록되지 않은 코드입니다"
        else:
            err = "인증에 실패했습니다"

    aw = 220
    window, impl = _init_glfw_window("뚱시스템 VIP 인증", aw, 160, 200, 160)
    _present_glfw_window(window, aw, 160)
    drag = {"on": False, "mx": 0, "my": 0, "wx": 0, "wy": 0}
    try:
        while not glfw.window_should_close(window) and not ok["v"]:
            glfw.poll_events()
            impl.process_inputs()
            imgui.new_frame()
            imgui.set_next_window_position(0, 0)
            imgui.set_next_window_size(aw, imgui.get_io().display_size.y)
            flags = (
                imgui.WINDOW_NO_TITLE_BAR
                | imgui.WINDOW_NO_RESIZE
                | imgui.WINDOW_NO_MOVE
                | imgui.WINDOW_NO_COLLAPSE
                | imgui.WINDOW_NO_SAVED_SETTINGS
                | imgui.WINDOW_NO_SCROLLBAR
            )
            imgui.push_style_var(imgui.STYLE_WINDOW_PADDING, (8, 5))
            imgui.push_style_var(imgui.STYLE_ITEM_SPACING, (4, 3))
            imgui.push_style_color(imgui.COLOR_BORDER, *_hex("#c9a84c"))
            imgui.begin("##auth", flags=flags)
            _center_text("뚱시스템 VIP 인증", "#f0d9a8")
            title_hovered = _title_row_hovered()
            imgui.separator()
            _text_c("인증 코드를 입력하세요", "#cba6f7")
            imgui.set_next_item_width(-1)
            changed, pw = imgui.input_text("##pw", pw, -1, imgui.INPUT_TEXT_PASSWORD)
            if imgui.is_item_focused() and imgui.is_key_pressed(imgui.KEY_ENTER):
                check_login()
            _text_c("포트 번호", "#a6adc8")
            imgui.set_next_item_width(-1)
            changed, com = imgui.input_text("##com", com, -1)
            if err:
                _text_c(err, "#ef4444")
            _text_c("PC ID: %s" % g.get("MY_HWID", ""), "#6c7086")
            if _btn("시스템 잠금 해제", "#89b4fa", "#74c7ec", width=-1, height=28):
                check_login()
            content_h = imgui.get_cursor_pos_y() + 8
            imgui.end()
            imgui.pop_style_color(1)
            imgui.pop_style_var(2)

            if title_hovered and imgui.is_mouse_clicked(0) and _left_down():
                drag["on"] = True
                drag["mx"], drag["my"] = _cursor_screen()
                drag["wx"], drag["wy"] = glfw.get_window_pos(window)
            if drag["on"]:
                if _left_down():
                    cx, cy = _cursor_screen()
                    glfw.set_window_pos(
                        window, drag["wx"] + (cx - drag["mx"]), drag["wy"] + (cy - drag["my"])
                    )
                else:
                    drag["on"] = False

            nh = max(120, int(content_h) + 4)
            cw, ch = glfw.get_window_size(window)
            if cw != aw or abs(ch - nh) > 2:
                glfw.set_window_size(window, aw, nh)

            imgui.render()
            gl.glClear(gl.GL_COLOR_BUFFER_BIT)
            impl.render(imgui.get_draw_data())
            glfw.swap_buffers(window)
            if ok["v"]:
                break
    finally:
        _shutdown_glfw(window, impl)
    return bool(ok["v"] or g.get("authenticated"))


_GUIDE = [
    ("t", "🚀 시작하기", "#a6e3a1"),
    ("w", "리니지 클래식 — 휠고정 무조건 하세요 (게임 설정에서 마우스 휠 고정)"),
    ("w", "Insert 로 시작 · 다시 누르면 정지 (시작할 때 자동클릭은 안 켜짐)"),
    ("w", "시작 전 제어판에서 파티원 HP바·100% 기준 저장 필수"),
    ("s",),
    ("t", "⌨️ 단축키", "#89b4fa"),
    ("d", "Insert", "시작 / 정지"),
    ("d", "Home", "따라가기 ON ↔ 전부 끄기 (사냥 중에만)"),
    ("d", "PageUp", "강제고정 — 시프트 제자리공격 ON/OFF (격수도 동일)"),
    ("d", "Delete", "창 숨기기 / 다시 보이기"),
    ("d", "F4", "주변 줍기 켜기 / 끄기"),
    ("s",),
    ("t", "🖱️ Home — 따라가기 / 고정", "#cba6f7"),
    ("d", "1번 누름", "따라가기 ON — 몹 따라가며 자동 공격"),
    ("d", "2번 누름", "전부 끄기 — 클릭·시프트 없음 (F1~F3 단축창 이동 가능)"),
    ("d", "다시 Home", "따라가기로 복귀"),
    ("w", "옵션 칸의 [따라가기(Home)]·[고정(Home)] 스위치로도 같은 동작"),
    ("w", "격수 모니터 [따라가기]·[고정] 버튼도 동일"),
    ("w", "[강제고정(PageUp)] — 시프트로 제자리 공격. 켜 두면 F1~F3 단축창이 안 바뀜"),
    ("s",),
    ("t", "💚 힐 · 휠힐 설정", "#94e2d5"),
    ("w", "게임 단축창: 힐·물약 섹션에서 F1~F3 + F5~F12 슬롯 지정 (기본 일반 F9 / 상위 F7)"),
    ("w", "WDT4 펌이면 Insert 연결 시 휠힐 자동 ON (별도 펌업 불필요)"),
    ("w", "최신 펌웨어: 일반 파티힐·격수힐 → 가운데 휠클릭으로 대상 지정 (항상 켜짐)"),
    ("w", "상위힐은 휠이 아니라 좌클릭으로 대상 지정 — 슬롯은 힐·물약에서 변경"),
    ("w", "버프·해독·줍기는 항상 좌클릭"),
    ("s",),
    ("t", "🛡️ 옵션 설명", "#89b4fa"),
    ("d", "버프", "▶ 버프 펼침 → 단축창(F1~F3) · 슬롯(F5~F12) 체크·초 설정"),
    ("d", "자힐", "평소 힐만 · 50% 이하 물약+힐 · 자힐 상위% 이하면 F7"),
    ("d", "상위힐", "파티·격수용 % (자힐 상위%는 자힐 슬라이더 옆)"),
    ("d", "독 해독", "본인 독 → F2단축창 엔줄복용(F9) 자동"),
    ("d", "격수 해독", "격수 독 → F2단축창 큐어포이즌(F10) 자동"),
    ("d", "파티 해독", "파티원 HP바 초록(독) → 큐어포이즌+대상 클릭"),
    ("d", "파랭이", "엠통% 이하 시 10분마다 파란물약"),
    ("d", "격수 HP", "격수 모니터 연결 시 체력% 표시"),
    ("s",),
    ("t", "📡 쫄화면 송출 (격수 ↔ 쫄)", "#89b4fa"),
    ("w", "쫄 PC 제어판 → [📡 송출 영역 드래그]로 게임 화면만 지정 (미설정이면 주 모니터 전체)"),
    ("w", "격수 PC: IP 맞춘 뒤 [📡 전송 ON] → [📺 쫄화면] 창 열기"),
    ("w", "쫄화면에서 Alt 누른 채 마우스 이동·클릭 → 쫄 PC 마우스 원격 조종"),
    ("w", "[📡 전송 OFF] 또는 격수 종료 시 송출 정지"),
    ("s",),
    ("t", "🚨 주의사항", "#89b4fa"),
    ("w", "파티창 UI를 켜 두지 않아도 파티힐 됩니다 (제어판 HP바 ROI만 맞으면 됨)"),
    ("w", "노파티: 배경 오탐 방지용 아이콘 ROI 설정 권장"),
    ("w", "채팅 중: 힐·귀환은 계속, 버프·줍기·해독만 잠깐 쉼"),
    ("s",),
    ("t", "🕹️ 뚱USB", "#f9e2af"),
    ("w", "상단 [장치] → 뚱USB 선택"),
    ("w", "USB 꽂으면 COM 포트 자동 표시 (대기 중에도 확인 가능)"),
    ("w", "Insert 로 시작 · 정지할 때도 Insert"),
    ("w", "[펌업] — 옛 펌일 때만 (이미 WDT4면 불필요)"),
    ("w", "Insert 연결 시 펌 자동 확인 → WDT4면 휠힐 바로 사용"),
    ("w", "[확인] — 펌 버전 수동 조회"),
    ("s",),
    ("t", "🕹️ 뚱박스 — 처음 세팅", "#cba6f7"),
    ("w", "① [장치] → 뚱박스 선택 → IP·포트·UUID 칸이 나타남"),
    ("w", "② [드라이버] — 랜드라이버 설치 (처음 1회, 재부팅 권장)"),
    ("w", "③ [IP설정] — PC 랜 IP 맞추기 (박스와 같은 대역, 예: 192.168.2.x)"),
    ("w", "   · 네트워크 어댑터 열기 → USB 이더넷 → IPv4 수동 입력"),
    ("w", "   · Wi-Fi/인터넷 어댑터는 건드리지 않기"),
    ("w", "④ [설정도구] — 중국어 프로그램 + 한글 통역 창"),
    ("w", "   · 连接盒子(연결) 클릭 · 박스 LCD의 IP/포트/UUID 입력"),
    ("w", "   · 禁用Bypass 체크 (Bypass 끄기) ← 필수"),
    ("w", "⑤ 뚱힐러 폼에 IP·포트·UUID 입력 → [설정저장]"),
    ("w", "⑥ Insert 로 연결 · 사냥 중 박스 LCD에 로고 표시"),
    ("w", "※ 연결 안 되면: ping 테스트 · 드라이버 · Bypass · IP 대역 재확인"),
]


def _draw_guide_body():
    import imgui
    _center_text("⚠️ 사용 책임은 사용자에게 있습니다 · 항상 후원 감사합니다 ❤️", "#a6adc8")
    imgui.begin_child("##gscroll", 0, -40, True)
    imgui.push_text_wrap_pos(0)
    for item in _GUIDE:
        kind = item[0]
        if kind == "s":
            imgui.separator()
        elif kind == "t":
            imgui.dummy(0, 4)
            _text_c(item[1], item[2] if len(item) > 2 else "#89b4fa")
        elif kind == "w":
            imgui.text_wrapped("• " + item[1])
        elif kind == "d":
            _text_c(item[1], "#f9e2af")
            imgui.same_line(86)
            imgui.text_wrapped(item[2])
    imgui.pop_text_wrap_pos()
    imgui.end_child()
    if _btn("닫기", "#313244", "#45475a", width=-1, height=32):
        close_overlay()


def _draw_patch_body(g):
    import imgui
    stamp = g.get("PATCH_UPDATED_AT") or ""
    _center_text("최신 업데이트", "#f9e2af")
    _center_text(str(stamp), "#a6e3a1")
    imgui.dummy(0, 4)
    imgui.begin_child("##pwarn", 0, 62, True)
    imgui.push_text_wrap_pos(0)
    _text_c("⚠️ 본 프로그램 사용 시 책임은 사용자에게 있습니다.", "#f38ba8")
    _text_c("감수하시고 사용하시고 6개월째 제것만 정지 없습니다.", "#a6adc8")
    _text_c("항상 후원 감사합니다. ❤️", "#f9e2af")
    imgui.pop_text_wrap_pos()
    imgui.end_child()
    imgui.dummy(0, 4)
    imgui.begin_child("##pscroll", 0, -40, True)
    imgui.push_text_wrap_pos(0)
    _text_c("NEW", "#a6e3a1")
    imgui.separator()
    for item in g.get("LATEST_PATCH") or []:
        imgui.bullet()
        imgui.same_line()
        _text_c(str(item), "#a6e3a1")
    imgui.dummy(0, 8)
    _text_c("지난 업데이트", "#89b4fa")
    imgui.separator()
    for item in g.get("PAST_PATCHES") or []:
        imgui.bullet()
        imgui.same_line()
        imgui.text_wrapped(str(item))
    imgui.pop_text_wrap_pos()
    imgui.end_child()
    if _btn("닫기", "#800020", "#9e1a3a", width=-1, height=32, text_color="#ffffff"):
        close_overlay()


_KM_TRANS = (
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
    "  게임기口 ✓  =  게임 PC 연결됨\n"
    "  网口 ✓      =  뚱힐러/설정도구 연결됨\n"
    "  打叉 ✗      =  끊김\n\n"
    "뚱힐러만 쓸 때: 연결 + 禁用Bypass 후\n"
    "뚱힐러 IP/포트/UUID 입력 → 설정저장 → 시작"
)


def _draw_km_trans_body(g):
    import imgui
    _center_text("옆 중국어 프로그램 보면서 이 창만 보세요", "#a6adc8")
    imgui.begin_child("##kmts", 0, -40, True)
    imgui.push_text_wrap_pos(0)
    imgui.text_unformatted(_KM_TRANS)
    imgui.pop_text_wrap_pos()
    imgui.end_child()
    bw = max(80.0, (imgui.get_content_region_available().x - 8) / 2)
    if _btn("상세 통역(브라우저)", "#313244", "#45475a", width=bw, height=28):
        try:
            g["_kmbox_open_html_guide"]()
        except Exception:
            pass
    imgui.same_line()
    if _btn("닫기", "#45475a", "#585b70", width=bw, height=28):
        close_overlay()


def _draw_km_ip_body(g):
    import imgui
    box_ip = _overlay.get("box_ip") or "192.168.2.188"
    pc_ip = _overlay.get("pc_ip") or "192.168.2.100"
    _center_text("박스 화면 IP와 PC가 같은 대역이어야 연결됩니다.", "#a6adc8")
    imgui.begin_child("##kmipinfo", 0, 52, True)
    _text_c("박스 IP (위 입력칸):  %s" % box_ip, "#a6e3a1")
    _text_c("PC에 넣을 IP 예시:  %s" % pc_ip, "#89b4fa")
    imgui.end_child()
    guide = (
        "【설정 순서】\n"
        "1. [드라이버] 버튼으로 랜드라이버 설치 (처음 1회)\n"
        "2. 아래 [네트워크 어댑터 열기] 클릭\n"
        "3. 새로 생긴 이더넷(USB/WCH 등) 우클릭 → 속성\n"
        "4. IPv4 → 다음 IP 주소 사용\n"
        "     IP: %s\n"
        "     서브넷: 255.255.255.0\n"
        "     게이트웨이·DNS: 비워둠\n"
        "5. 위 폼에 박스 IP·포트·UUID 입력 후 [설정저장]\n\n"
        "※ Wi-Fi/인터넷 쓰는 어댑터는 건드리지 마세요.\n"
        "※ ping 테스트: cmd → ping %s\n"
    ) % (pc_ip, box_ip)
    imgui.begin_child("##kmipg", 0, -72, True)
    imgui.push_text_wrap_pos(0)
    imgui.text_unformatted(guide)
    imgui.pop_text_wrap_pos()
    imgui.end_child()
    bw = max(80.0, (imgui.get_content_region_available().x - 8) / 2)
    if _btn("네트워크 어댑터 열기", "#89b4fa", "#74c7ec", width=bw, height=28, text_color="#1e1e2e"):
        try:
            g["_kmbox_open_adapters"]()
        except Exception:
            pass
    imgui.same_line()
    if _btn("한글 메뉴얼", "#313244", "#45475a", width=bw, height=28):
        try:
            g["_kmbox_open_manual"]()
        except Exception:
            pass
    if _btn("공식 설정도구 + 한글통역", "#a6e3a1", "#7bd88f", width=-1, height=26, text_color="#1e1e2e"):
        try:
            g["_kmbox_open_chinese_tool"]()
        except Exception:
            pass
    if _btn("닫기", "#45475a", "#585b70", width=-1, height=26):
        close_overlay()


def _upload_tex(key, arr, max_w=180):
    if arr is None:
        return None
    try:
        from PIL import Image
        from OpenGL import GL as gl
        h, w = arr.shape[:2]
        pw = min(max(w * 2, 8), max_w)
        ph = max(int(h * pw / max(w, 1)), 3)
        img = Image.fromarray(arr).resize((pw, ph), Image.LANCZOS).convert("RGBA")
        data = img.tobytes()
        if key not in _tex:
            tid = int(gl.glGenTextures(1))
            _tex[key] = {"id": tid, "w": pw, "h": ph}
        else:
            tid = _tex[key]["id"]
            _tex[key]["w"] = pw
            _tex[key]["h"] = ph
        gl.glBindTexture(gl.GL_TEXTURE_2D, tid)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexImage2D(
            gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, pw, ph, 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, data
        )
        return _tex[key]
    except Exception:
        return None


def _admin_refresh_previews(g):
    grab = g.get("_admin_grab_rgb")
    lab = g.get("_admin_preview_label")
    if not grab or not lab:
        return
    roi = g.get("SELF_HP_ROI") or (0, 0, 0, 0)
    if roi[0] != 0:
        txt, col = lab(roi, g.get("SELF_HP_100_REF"), False, False)
        _admin["self_txt"], _admin["self_col"] = txt, col
        _upload_tex("self", grab(roi))
    roi = g.get("MNA_ROI") or (0, 0, 0, 0)
    if roi[0] != 0:
        txt, col = lab(roi, g.get("MNA_100_REF"), True, True)
        _admin["mna_txt"], _admin["mna_col"] = txt, col
        _upload_tex("mna", grab(roi))
    sl = g.get("_admin_stream_label")
    if sl:
        txt, col = sl()
        _admin["stream_txt"], _admin["stream_col"] = txt, col
    sroi = g.get("_stream_roi") or (0, 0, 0, 0)
    if sroi[2] > sroi[0] and sroi[3] > sroi[1]:
        _upload_tex("stream", grab(sroi), 220)
    rois = g.get("PARTY_ROIS") or []
    refs = g.get("PARTY_HP_100_REF") or []
    for pi in range(8):
        if pi < len(rois) and rois[pi][0] != 0:
            _upload_tex("p%d" % pi, grab(rois[pi]), 120)
    nrois = g.get("PARTY_NAME_ROIS") or []
    for pi in range(8):
        if pi < len(nrois) and nrois[pi][0] != 0:
            _upload_tex("icon%d" % pi, grab(nrois[pi]), 48)


def _admin_refresh_live(g):
    camera = g.get("camera")
    scan = g.get("scan_party_hp")
    rois = g.get("PARTY_ROIS") or []
    ths = g.get("PARTY_HP_THRESHOLDS") or [50] * 8
    nrois = g.get("PARTY_NAME_ROIS") or []
    stats_fn = g.get("_party_name_tag_stats")
    thr = g.get("ICON_BLACK_PCT_THRESHOLD") or 0
    frame = None
    if camera:
        try:
            frame = camera.get_latest_frame()
        except Exception:
            frame = None
    if frame is None:
        return
    for pi in range(8):
        st = _admin["party"][pi]
        if pi < len(rois) and rois[pi][0] > 0 and scan:
            try:
                hp = scan(frame, pi)
            except Exception:
                hp = None
            st["pct"] = hp
        if stats_fn and pi < len(nrois) and nrois[pi][0] > 0:
            try:
                stats = stats_fn(frame, nrois[pi])
            except Exception:
                stats = None
            if stats is not None:
                black, t, ar, ag, ab = stats
                black_pct = (black / t * 100) if t else 0
                present = t > 0 and (black / t) >= thr
                st["status"] = "🖼️있음" if present else "🖼️없음"
                st["status_col"] = "#a6e3a1" if present else "#6c7086"
                st["diag"] = "검정%.0f%% B%s/T%s RGB%s,%s,%s" % (black_pct, black, t, ar, ag, ab)


def _draw_admin_body(g):
    import imgui
    now = time.time()
    if _admin["dirty"] or (now - _admin["last_prev"] > 3.0):
        _admin_refresh_previews(g)
        _admin["last_prev"] = now
        _admin["dirty"] = False
    if now - _admin["last_live"] > 2.0:
        _admin_refresh_live(g)
        _admin["last_live"] = now

    imgui.begin_child("##ascroll", 0, -40, False)
    if _btn("🖱️ 쫄법 피통 셋팅", "#1f538d", "#14375e", height=22):
        g["open_self_hp_overlay"]()
    imgui.same_line()
    if _btn("💯 100% 기준", "#fbbf24", "#d97706", height=22, text_color="#000000"):
        g["set_self_100ref"]()
    tex = _tex.get("self")
    if tex:
        imgui.image(tex["id"], float(tex["w"]), float(tex["h"]))
    if _admin["self_txt"]:
        _text_c(_admin["self_txt"], _admin["self_col"])
    imgui.separator()

    if _btn("💙 마나 엠통 셋팅", "#1e40af", "#2563eb", height=22):
        g["open_mna_roi_overlay"]()
    imgui.same_line()
    if _btn("💯 100% 기준##mna", "#fbbf24", "#d97706", height=22, text_color="#000000"):
        g["set_mna_100ref"]()
    tex = _tex.get("mna")
    if tex:
        imgui.image(tex["id"], float(tex["w"]), float(tex["h"]))
    if _admin["mna_txt"]:
        _text_c(_admin["mna_txt"], _admin["mna_col"])
    imgui.separator()

    _text_c("📡 격수 쫄화면 송출 영역", "#bac2de")
    if _btn("📡 송출 영역 드래그", "#166534", "#15803d", height=22):
        g["open_stream_roi_overlay"]()
    imgui.same_line()
    if _btn("전체화면", "#374151", "#4b5563", height=22):
        g["clear_stream_roi"]()
    tex = _tex.get("stream")
    if tex:
        imgui.image(tex["id"], float(tex["w"]), float(tex["h"]))
    _text_c(_admin["stream_txt"], _admin["stream_col"])
    imgui.separator()

    _text_c("👥 파티원 좌표 / HP바 / 힐% (HP바 드래그로 설정)", "#bac2de")
    flags = g["party_mode_flags"]
    rois = g["PARTY_ROIS"]
    nrois = g["PARTY_NAME_ROIS"]
    ths = g["PARTY_HP_THRESHOLDS"]
    for i in range(8):
        imgui.push_id("p%d" % i)
        imgui.begin_child("##pc%d" % i, 0, 158, True)
        cur = bool(flags[i])
        clicked, val = imgui.checkbox("##on", cur)
        if clicked and val != cur:
            flags[i] = 1 if val else 0
            g["saved_party_mode_flags"] = ",".join(str(f) for f in flags)
            try:
                g["save_hidden_config"](g["loaded_pwd"] if g.get("loaded_pwd") else "")
            except Exception:
                pass
        imgui.same_line()
        if i == 0:
            lbl = "P1(본인)"
        elif i == 1:
            lbl = "P2(격수)"
        else:
            lbl = "P%d" % (i + 1)
        _text_c(lbl, "#cba6f7")
        r = rois[i]
        imgui.same_line()
        if r[0] != 0:
            _text_c("(%s,%s) %sx%s" % (r[0], r[1], r[2] - r[0], r[3] - r[1]), "#ffffff")
        else:
            _text_c("HP바 미설정", "#6c7086")
        if _btn("HP바", "#1f538d", "#14375e", width=46, height=20):
            g["open_party_roi_overlay"](i)
        imgui.same_line()
        st = _admin["party"][i]
        hp = st.get("pct")
        thr = int(ths[i])
        if hp is None:
            frac, bar_c, pct_t, pct_c = 0.0, "#45475a", "--%", "#6c7086"
        else:
            frac = max(0.0, min(1.0, float(hp) / 100.0))
            low = hp < thr
            bar_c = "#ef4444" if low else "#10b981"
            pct_t = "%d%%" % int(hp)
            pct_c = "#ef4444" if low else "#10b981"
        imgui.push_style_color(imgui.COLOR_PLOT_HISTOGRAM, *_hex(bar_c))
        imgui.progress_bar(frac, (50, 10), "")
        imgui.pop_style_color()
        imgui.same_line()
        _text_c(pct_t, pct_c)
        imgui.same_line()
        _text_c("힐↓", "#f38ba8")
        imgui.same_line()
        imgui.set_next_item_width(64)
        imgui.push_style_color(imgui.COLOR_SLIDER_GRAB, *_hex("#d4af37"))
        changed, nval = imgui.slider_int("##thr", thr, 10, 90, "%d%%")
        imgui.pop_style_color()
        if changed:
            ths[i] = int(nval)
            try:
                g["save_hidden_config"](g["loaded_pwd"] if g.get("loaded_pwd") else "")
            except Exception:
                pass
        tex = _tex.get("p%d" % i)
        if tex:
            imgui.image(tex["id"], float(min(tex["w"], 100)), float(min(tex["h"], 18)))
            imgui.same_line()
        if _btn("💯", "#fbbf24", "#d97706", width=22, height=20, text_color="#000000"):
            g["set_party_100ref"](i)
        imgui.same_line()
        if _btn("아이콘", "#8a6d1f", "#6b5417", width=48, height=20):
            g["open_party_name_roi_overlay"](i)
        itex = _tex.get("icon%d" % i)
        if itex:
            imgui.image(itex["id"], 36.0, 36.0)
            imgui.same_line()
        imgui.begin_group()
        nr = nrois[i]
        if nr[0] != 0:
            imgui.push_text_wrap_pos(0)
            _text_c("아이콘 (%s,%s) %sx%s" % (nr[0], nr[1], nr[2] - nr[0], nr[3] - nr[1]), "#9399b2")
            imgui.pop_text_wrap_pos()
        else:
            imgui.push_text_wrap_pos(0)
            _text_c("아이콘 미설정 (HP바만 판정)", "#9399b2")
            imgui.pop_text_wrap_pos()
        if st.get("status"):
            _text_c(st["status"], st.get("status_col") or "#6c7086")
        if st.get("diag"):
            imgui.push_text_wrap_pos(0)
            imgui.text_wrapped(st["diag"])
            imgui.pop_text_wrap_pos()
        imgui.end_group()
        imgui.end_child()
        imgui.pop_id()
    imgui.end_child()
    if _btn("💾 실시간 저장 및 닫기", "#800020", "#9e1a3a", width=-1, height=32, text_color="#ffffff"):
        try:
            key = g["loaded_pwd"] if g.get("loaded_pwd") else ""
            g["save_hidden_config"](key)
        except Exception:
            pass
        close_overlay()
        show_alert("저장 완료", "✨ 설정이 저장되었습니다!")


def _draw_modal():
    import imgui
    if not _modal.get("open"):
        return
    mw = 200.0
    imgui.set_next_window_size(mw, 0)
    ds = imgui.get_io().display_size
    imgui.set_next_window_position(max(6.0, (ds.x - mw) * 0.5), max(6.0, ds.y * 0.28))
    imgui.push_style_var(imgui.STYLE_WINDOW_PADDING, (8, 6))
    imgui.push_style_var(imgui.STYLE_WINDOW_ROUNDING, 8)
    imgui.push_style_color(imgui.COLOR_TITLE_BACKGROUND, *_hex("#1e1e2e"))
    imgui.push_style_color(imgui.COLOR_TITLE_BACKGROUND_ACTIVE, *_hex("#1e1e2e"))
    imgui.push_style_color(imgui.COLOR_BORDER, *_hex("#c9a84c"))
    flags = imgui.WINDOW_NO_COLLAPSE | imgui.WINDOW_NO_SAVED_SETTINGS | imgui.WINDOW_ALWAYS_AUTO_RESIZE
    _expanded, opened = imgui.begin(_modal.get("title") or "알림", True, flags)
    if not opened:
        _modal["open"] = False
        imgui.end()
        imgui.pop_style_color(3)
        imgui.pop_style_var(2)
        return
    imgui.push_text_wrap_pos(0)
    imgui.text_wrapped(_modal.get("body") or "")
    imgui.pop_text_wrap_pos()
    imgui.dummy(0, 3)
    if _modal.get("kind") == "yesno":
        bw = 72.0
        _center_width(bw * 2 + 8)
        if _btn("예", "#238636", "#2ea043", width=bw, height=22):
            fn = _modal.get("yes_fn")
            _modal["open"] = False
            if fn:
                try:
                    fn()
                except Exception:
                    pass
        imgui.same_line()
        if _btn("아니요", "#800020", "#9e1a3a", width=bw, height=22):
            fn = _modal.get("no_fn")
            _modal["open"] = False
            if fn:
                try:
                    fn()
                except Exception:
                    pass
    else:
        _center_width(64)
        if _btn("확인", "#2a2118", "#3d2e1f", width=64, height=20, text_color="#f0d9a8"):
            _modal["open"] = False
    imgui.end()
    imgui.pop_style_color(3)
    imgui.pop_style_var(2)


def _draw_overlay(g):
    import imgui
    kind = _overlay.get("kind")
    ow = int(_overlay.get("ow") or 460)
    oh = int(_overlay.get("oh") or 400)
    flags = (
        imgui.WINDOW_NO_TITLE_BAR
        | imgui.WINDOW_NO_RESIZE
        | imgui.WINDOW_NO_MOVE
        | imgui.WINDOW_NO_COLLAPSE
        | imgui.WINDOW_NO_SAVED_SETTINGS
        | imgui.WINDOW_NO_SCROLLBAR
    )
    imgui.set_next_window_position(0, 0)
    extra_pad = kind in ("alert", "yesno")
    if extra_pad:
        imgui.set_next_window_size(ow, oh)
        imgui.push_style_var(imgui.STYLE_WINDOW_PADDING, (8, 5))
        imgui.push_style_var(imgui.STYLE_ITEM_SPACING, (4, 2))
        imgui.push_style_color(imgui.COLOR_BORDER, *_hex("#c9a84c"))
        imgui.push_style_var(imgui.STYLE_WINDOW_BORDERSIZE, 1)
    else:
        imgui.set_next_window_size(ow, oh)
    imgui.begin("##overlay", flags=flags)
    title = _overlay.get("title") or ""
    _center_text(title, "#f0d9a8")
    imgui.same_line(max(24, ow - 26))
    if _btn("✖", "#800020", "#9e1a3a", width=18, height=18):
        close_overlay()
        imgui.end()
        if extra_pad:
            imgui.pop_style_color(1)
            imgui.pop_style_var(3)
        return False
    title_hovered = _title_row_hovered()
    imgui.separator()
    if kind == "guide":
        _draw_guide_body()
    elif kind == "patch":
        _draw_patch_body(g)
    elif kind == "admin":
        _draw_admin_body(g)
    elif kind == "km_trans":
        _draw_km_trans_body(g)
    elif kind == "km_ip":
        _draw_km_ip_body(g)
    elif kind == "alert":
        imgui.push_text_wrap_pos(0)
        imgui.text_wrapped(_overlay.get("body") or "")
        imgui.pop_text_wrap_pos()
        imgui.dummy(0, 2)
        _center_width(64)
        if _btn("확인", "#2a2118", "#3d2e1f", width=64, height=20, text_color="#f0d9a8"):
            close_overlay()
    elif kind == "yesno":
        imgui.push_text_wrap_pos(0)
        imgui.text_wrapped(_overlay.get("body") or "")
        imgui.pop_text_wrap_pos()
        imgui.dummy(0, 2)
        bw = 64.0
        _center_width(bw * 2 + 8)
        if _btn("예", "#238636", "#2ea043", width=bw, height=20):
            fn = _overlay.get("yes_fn")
            close_overlay()
            if fn:
                try:
                    fn()
                except Exception:
                    pass
        imgui.same_line()
        if _btn("아니요", "#800020", "#9e1a3a", width=bw, height=20):
            fn = _overlay.get("no_fn")
            close_overlay()
            if fn:
                try:
                    fn()
                except Exception:
                    pass
    if extra_pad:
        pad_y = imgui.get_style().window_padding.y
        _overlay["oh"] = max(64, int(imgui.get_cursor_pos_y() + pad_y))
    imgui.end()
    if extra_pad:
        imgui.pop_style_color(1)
        imgui.pop_style_var(3)
    return title_hovered


def _draw_status_chips(g):
    """끊김·미설정 등 이상 상태 한눈에."""
    import imgui

    fn = g.get("collect_status_chips")
    if not fn:
        return
    try:
        chips = fn()
    except Exception:
        return
    if not chips:
        return
    imgui.push_style_var(imgui.STYLE_ITEM_SPACING, (4, 2))
    x0 = imgui.get_cursor_pos_x()
    total_w = imgui.get_content_region_available().x
    used = 0.0
    for i, (txt, col) in enumerate(chips):
        tw = imgui.calc_text_size(txt).x + 6
        if used + tw > total_w and i > 0:
            break
        if i > 0:
            imgui.same_line(spacing=4)
        imgui.push_style_color(imgui.COLOR_TEXT, *_hex(col))
        imgui.text(txt)
        imgui.pop_style_color(1)
        used += tw + 4
    imgui.pop_style_var(1)


def _draw_labeled_row(label, label_color, combo_id, items, var, btn1, btn1_fg, btn1_hv, btn1_fn, btn2, btn2_fg, btn2_hv, btn2_fn, combo_w, combo_x, btn1_x, btn2_x, btn1_w, btn2_w, combo_cmd=None, label_x=6):
    """장치/프리셋 — 라벨·드롭다운·버튼2개 열 맞춤."""
    import imgui
    row_y = imgui.get_cursor_pos_y()
    imgui.set_cursor_pos((label_x, row_y))
    imgui.align_text_to_frame_padding()
    _text_c(label, label_color)
    imgui.set_cursor_pos((combo_x, row_y))
    _gold_combo(combo_id, items, var, cmd=combo_cmd, width=combo_w, height=20)
    imgui.set_cursor_pos((btn1_x, row_y))
    if _btn(btn1, btn1_fg, btn1_hv, width=btn1_w, height=20):
        if btn1_fn:
            btn1_fn()
    imgui.set_cursor_pos((btn2_x, row_y))
    if _btn(btn2, btn2_fg, btn2_hv, width=btn2_w, height=20):
        if btn2_fn:
            btn2_fn()
    imgui.set_cursor_pos_y(row_y + 22)


def _draw_main(g):
    import imgui
    import glfw

    global _win_w, _win_h
    hw_var = g["hw_var"]
    root = g["root"]

    flags = (
        imgui.WINDOW_NO_TITLE_BAR
        | imgui.WINDOW_NO_RESIZE
        | imgui.WINDOW_NO_MOVE
        | imgui.WINDOW_NO_COLLAPSE
        | imgui.WINDOW_NO_SAVED_SETTINGS
        | imgui.WINDOW_NO_SCROLLBAR
    )
    imgui.set_next_window_position(0, 0)
    imgui.set_next_window_size(_win_w, imgui.get_io().display_size.y)
    imgui.begin("##healer", flags=flags)

    # 타이틀 (드래그, 가운데)
    title = "❖ 뚱힐러 ❖"
    _center_text(title, "#f0d9a8")
    imgui.same_line(_win_w - 26)
    if _btn("✖", "#800020", "#9e1a3a", width=18, height=18):
        g["exit_app"]()
    title_hovered = _title_row_hovered()
    imgui.separator()

    # 헤더: 업데이트 왼쪽, 장치상태 오른쪽. 최신이면 초록 버튼.
    upd = _lbl_text(g["lbl_update"], "업데이트")
    uc = _lbl_color(g["lbl_update"], "#e2e8f0")
    if "a6e3a1" in str(uc).lower():
        upd_fg, upd_hv, upd_tc = "#238636", "#2ea043", "#ffffff"
    else:
        upd_fg, upd_hv, upd_tc = "#21262d", "#30363d", uc
    if _btn(upd, upd_fg, upd_hv, text_color=upd_tc):
        g["on_update_check_click"]()
    imgui.same_line()
    if _btn("뚱usb수동펌업", "#1f6feb", "#388bfd", text_color="#ffffff"):
        g["on_manual_ide_flash"]()
    ard = _lbl_text(g["lbl_ard"], "확인중")
    imgui.same_line()
    imgui.set_cursor_pos_x(
        imgui.get_cursor_pos_x() + max(0.0, imgui.get_content_region_available().x - imgui.calc_text_size(ard).x)
    )
    _text_c(ard, _lbl_color(g["lbl_ard"], "#a6adc8"))

    _draw_status_chips(g)

    # 장치 / 프리셋 — 라벨·드롭다운·버튼 열 동일
    import imgui as _im
    combo_x = int(max(_im.calc_text_size("프리셋").x, _im.calc_text_size("장  치").x)) + 14
    btn1_w, btn2_w, gap = 36, 36, 4
    combo_w = max(48, int(_win_w) - combo_x - btn1_w - btn2_w - gap * 2 - 8)
    btn1_x = combo_x + combo_w + gap
    btn2_x = btn1_x + btn1_w + gap

    _draw_labeled_row(
        "장  치", "#f9e2af", "##hw", ["뚱USB", "뚱박스"], hw_var,
        "펌업", "#1f6feb", "#388bfd", g["on_fw_flash_click"],
        "확인", "#238636", "#2ea043", g["on_fw_check_click"],
        combo_w, combo_x, btn1_x, btn2_x, btn1_w, btn2_w,
        combo_cmd=g["_on_hw_mode_change"],
    )

    if hw_var.get() in ("뚱박스", "KMBox"):
        imgui.align_text_to_frame_padding()
        imgui.text_disabled("IP")
        imgui.same_line(40)
        _input_entry("##kmip", g["ent_km_ip"], width=-1)
        imgui.align_text_to_frame_padding()
        imgui.text_disabled("포트")
        imgui.same_line(40)
        _input_entry("##kmport", g["ent_km_port"], width=-1)
        imgui.align_text_to_frame_padding()
        imgui.text_disabled("UUID")
        imgui.same_line(40)
        _input_entry("##kmmac", g["ent_km_mac"], width=-1)
        bw = max(40, (_win_w - 20) / 3)
        if _btn("드라이버", "#21262d", "#30363d", width=bw):
            g["on_kmbox_driver_click"]()
        imgui.same_line()
        if _btn("IP설정", "#21262d", "#30363d", width=bw):
            g["on_kmbox_setup_click"]()
        imgui.same_line()
        if _btn("설정도구", "#21262d", "#30363d", width=bw):
            g["on_kmbox_net_setup_click"]()

    preset_names = []
    try:
        preset_names = g.get("list_preset_names", lambda: [])() or []
    except Exception:
        preset_names = ["파티", "솔로", "노파티"]
    if not preset_names:
        preset_names = ["파티", "솔로", "노파티"]
    pvar = g.get("_preset_var")
    if pvar is not None:
        _draw_labeled_row(
            "프리셋", "#cba6f7", "##preset", preset_names, pvar,
            "저장", "#1f6feb", "#388bfd", lambda: g["save_named_preset"](pvar.get()),
            "적용", "#238636", "#2ea043", lambda: g["load_named_preset"](pvar.get()),
            combo_w, combo_x, btn1_x, btn2_x, btn1_w, btn2_w,
        )

    mode_w = max(158, int(_win_w) - 8)
    _center_width(mode_w)
    _gold_combo("##mode", ["파티", "솔로(파티)", "노파티"], g["mode_var"], width=mode_w, height=20)

    # 옵션 (기본 접힘)
    if _collapsible("옵션", "opt"):
        imgui.indent(3)
        imgui.columns(2, "optcols", False)
        _bool_cb("고정(Home)", g["chk_fix"], g["_on_fix_sw"])
        imgui.next_column()
        _bool_cb("따라가기(Home)", g["chk_follow"], g["_on_follow_sw"])
        imgui.next_column()
        _bool_cb("강제고정(PageUp)", g["chk_force_fix"], g["_on_force_fix_sw"])
        imgui.next_column()
        _bool_cb("독 해독", g["chk_poison"], lambda: g["log_event"]("☠️ 독해독 %s" % ("ON" if g["chk_poison"].get() else "OFF")))
        imgui.next_column()
        _bool_cb("격수 해독", g["chk_target_poison"], lambda: g["log_event"]("⚔️ 격수해독 %s" % ("ON" if g["chk_target_poison"].get() else "OFF")))
        imgui.next_column()
        _bool_cb("파티 해독", g["chk_party_poison"], lambda: g["log_event"]("💚 파티해독 %s" % ("ON" if g["chk_party_poison"].get() else "OFF")))
        imgui.next_column()
        _bool_cb("줍기(F4)", g["chk_loot"], lambda: g["log_event"]("🎒 줍기 %s" % ("ON" if g["chk_loot"].get() else "OFF")))
        imgui.next_column()
        _bool_cb("강제베르(end)", g["chk_end_bert"], g["_on_end_bert_sw"])
        imgui.next_column()
        _bool_cb("휠힐(항상ON)", g["chk_wheel_heal"], g["_on_wheel_heal_sw"])
        imgui.columns(1)
        imgui.unindent(3)

    # 버프 (기본 펼침)
    if _collapsible("버프", "buff"):
        imgui.indent(3)
        _gold_combo("##buffmode", ["일반", "자기"], g["buff_mode_var"], cmd=g["_show_buff_mode"], width=72)
        mode = g["buff_mode_var"].get()
        if mode != "자기":
            imgui.same_line()
            _bool_cb("자동", g["chk_buff_on"], g["_on_buff_on"])
            imgui.same_line()
            imgui.text_disabled("창")
            imgui.same_line()
            _gold_combo("##buffhb", g["BUFF_HOTBARS"], g["buff_hotbar_var"], cmd=g["_show_buff_page"], width=HB_W, arrow=False)
            hb = g["buff_hotbar_var"].get()
            rows = g["_buff_cfg"].get(hb, [])
            imgui.columns(2, "buffcols", False)
            for idx, (slot, cb, iv) in enumerate(rows):
                if idx == 4:
                    imgui.next_column()
                imgui.push_id("b%s%s" % (hb, slot))
                _bool_cb(slot, cb, lambda: g["save_hidden_config"](g["loaded_pwd"] if g["loaded_pwd"] else ""))
                imgui.same_line()
                _input_var("##sec", iv, width=36)
                imgui.pop_id()
            imgui.columns(1)
        else:
            imgui.columns(2, "selfbuff", False)
            for i, (cb, hb_var, slot_var, sec_var) in enumerate(g["_self_buff_cfg"], start=1):
                if i == 3:
                    imgui.next_column()
                imgui.push_id("sb%d" % i)

                def _on_sb(_i=i, _c=cb):
                    g["log_event"]("⚡ 자기버프%d %s" % (_i, "ON" if _c.get() else "OFF"))
                    try:
                        g["save_hidden_config"](g["loaded_pwd"] if g["loaded_pwd"] else "")
                    except Exception:
                        pass

                _bool_cb(str(i), cb, _on_sb)
                imgui.same_line()
                _gold_combo("##hb", g["BUFF_HOTBARS"], hb_var, cmd=lambda *_: g["_schedule_buff_cfg_save"](), width=38)
                imgui.same_line()
                _gold_combo("##sl", g["BUFF_SLOT_LABELS"], slot_var, cmd=lambda *_: g["_schedule_buff_cfg_save"](), width=42)
                _input_var("##sec", sec_var, width=-1)
                imgui.pop_id()
            imgui.columns(1)
        imgui.unindent(3)

    # 힐·물약 (기본 접힘)
    if _collapsible("힐·물약", "heal"):
        imgui.indent(3)
        _center_text("⌨ 힐 단축키", "#cba6f7")
        imgui.columns(2, "healkeys", False)
        _center_text("💚 일반", "#a6e3a1")
        _center_width(HB_W + SL_W + 4)
        _gold_combo("##hhb", g["BUFF_HOTBARS"], g["heal_hotbar_var"], cmd=g["update_heal_slots"], width=HB_W, arrow=False)
        imgui.same_line()
        _gold_combo("##hsl", g["BUFF_SLOT_LABELS"], g["heal_slot_var"], cmd=g["update_heal_slots"], width=SL_W, arrow=False)
        imgui.next_column()
        _center_text("⚡ 상위", "#89b4fa")
        _center_width(HB_W + SL_W + 4)
        _gold_combo("##shb", g["BUFF_HOTBARS"], g["strong_heal_hotbar_var"], cmd=g["update_heal_slots"], width=HB_W, arrow=False)
        imgui.same_line()
        _gold_combo("##ssl", g["BUFF_SLOT_LABELS"], g["strong_heal_slot_var"], cmd=g["update_heal_slots"], width=SL_W, arrow=False)
        imgui.columns(1)
        _center_text("파란물약 단축키", "#89b4fa")
        _center_width(HB_W + SL_W + 4)
        _gold_combo("##mhb", g["BUFF_HOTBARS"], g["mna_hotbar_var"], cmd=g["update_mna_slot"], width=HB_W, arrow=False)
        imgui.same_line()
        _gold_combo("##msl", g["BUFF_SLOT_LABELS"], g["mna_slot_var"], cmd=g["update_mna_slot"], width=SL_W, arrow=False)

        def _heal_row(label, chk, cmd, svar, vmin, vmax, fill="#f38ba8"):
            _bool_cb(label, chk, cmd)
            x = imgui.get_item_rect_max().x - imgui.get_window_position().x + 6
            imgui.same_line(max(92, x))
            _slider_int("##" + label, svar, vmin, vmax, fill)

        _heal_row("🔴 자힐", g["chk_self_heal_sw"], g["_on_self_heal_sw"], g["self_hp_var"], 10, 90)
        _heal_row("⚡ 자힐상위", g["chk_self_strong_heal"], g["_on_self_strong_heal"], g["self_strong_var"], 5, 70)
        _heal_row("🔴 위기베르", g["chk_danger_sw"], g["_on_danger_sw"], g["danger_hp_var"], 5, 50)
        _heal_row("⚡ 상위힐", g["chk_strong_heal"], g["_on_strong_heal"], g["sv"], 5, 70)
        _heal_row("⚡ 노파티격수", g["chk_attacker_sw"], g["_on_attacker_sw"], g["atkhp_var"], 10, 99)
        _heal_row("💙 파랭이", g["chk_mna"], g["_on_mna_sw"], g["mna_var"], 10, 80, "#89b4fa")
        imgui.unindent(3)

    imgui.align_text_to_frame_padding()
    imgui.text("⏰ 예약종료")
    imgui.same_line()
    _gold_combo(
        "##timer",
        ["예약OFF", "1시간", "2시간", "3시간", "5시간", "10시간"],
        g["_timer_var"],
        cmd=g["set_shutdown_timer"],
        width=-1,
    )

    bw = max(48, (_win_w - 20) / 3)
    if _btn("⚙ 제어판", "#800020", "#9e1a3a", width=bw, height=24):
        g["ask_admin_pw"]()
    imgui.same_line()
    if _btn("📜 패치", "#1f538d", "#14375e", width=bw, height=24):
        g["open_patch_notes_panel"]()
    imgui.same_line()
    if _btn("📖 가이드", "#313244", "#45475a", width=bw, height=24):
        g["open_guide_panel"]()

    auth_t = _lbl_text(g["lbl_auth"], "")
    if auth_t:
        _center_text(auth_t, "#89b4fa")
    st = _lbl_text(g["lbl_status"], "대기 중")
    _center_text(st, _lbl_color(g["lbl_status"], "#f38ba8"))
    buff_t = _lbl_text(g["lbl_buff"], "")
    buff_lines = []
    for line in str(buff_t).split("\n"):
        s = line.strip()
        if not s or s == "대기중":
            continue
        buff_lines.append(s)
    if buff_lines == ["✨ 버프 대기 ✨"]:
        buff_lines = []
    for line in buff_lines:
        _center_text(line, "#a6e3a1")

    imgui.dummy(0, 2)
    imgui.align_text_to_frame_padding()
    myip = _lbl_text(g["lbl_my_ip"], "")
    _text_c(myip or "내IP:...", "#a6e3a1")
    imgui.same_line()
    if _btn("격수연결", "#238636", "#2ea043", width=64, height=20):
        try:
            g["broadcast_healer_ip"]()
        except Exception:
            pass
    ontop = _lbl_text(g["lbl_ontop_status"], "")
    atkhp, atk_c, ontop_t, ontop_c = _attacker_udp_ui(g)
    if ontop or ontop_t:
        ow = imgui.calc_text_size(ontop_t or ontop).x
        imgui.same_line()
        imgui.set_cursor_pos_x(
            imgui.get_cursor_pos_x() + max(4.0, imgui.get_content_region_available().x - ow)
        )
        _text_c(ontop_t or ontop, ontop_c if ontop_t else _lbl_color(g["lbl_ontop_status"], "#f0d9a8"))
    if atkhp:
        aw = imgui.calc_text_size(atkhp).x
        imgui.set_cursor_pos_x(
            imgui.get_cursor_pos_x() + max(0.0, imgui.get_content_region_available().x - aw)
        )
        _text_c(atkhp, atk_c)

    _draw_log_panel(g.get("last_log") or "시스템 시작")

    content_h = imgui.get_cursor_pos_y() + 24
    avail = imgui.get_content_region_available()
    if avail.y > 22:
        imgui.dummy(1, avail.y - 20)
    imgui.dummy(max(1, imgui.get_content_region_available().x - 18), 1)
    imgui.same_line()
    _btn("◢", "#313244", "#45475a", width=16, height=16)
    if imgui.is_item_active():
        dx = imgui.get_io().mouse_delta.x
        dy = imgui.get_io().mouse_delta.y
        _win_w = max(165, min(420, int(_win_w + dx)))
        if _win_h > 0:
            _win_h = max(220, min(900, int(_win_h + dy)))
        g["saved_win_w"] = _win_w
    elif imgui.is_item_deactivated():
        try:
            if g.get("loaded_pwd"):
                g["save_hidden_config"](g["loaded_pwd"])
        except Exception:
            pass

    imgui.end()
    return content_h, title_hovered


def tick_overlay(g, main_window, main_ctx, ov_drag):
    """확인/예아니오 등 별도 glfw 팝업. 힐러·격수 공통."""
    import glfw
    from OpenGL import GL as gl
    import imgui

    if not _overlay.get("kind") or _ov_win is None or _ov_impl is None:
        return
    if glfw.window_should_close(_ov_win):
        close_overlay()
        try:
            glfw.set_window_should_close(_ov_win, False)
        except Exception:
            pass
        return
    glfw.make_context_current(_ov_win)
    if _ov_ctx is not None:
        imgui.set_current_context(_ov_ctx)
    ow = int(_overlay.get("ow") or 460)
    kind = _overlay.get("kind")
    min_h = 64 if kind in ("alert", "yesno") else 180
    oh = _cap_overlay_h(_overlay.get("oh") or 400, min_h)
    cw, ch = glfw.get_window_size(_ov_win)
    if cw != ow or abs(ch - oh) > 2:
        glfw.set_window_size(_ov_win, ow, oh)
    _ov_impl.process_inputs()
    imgui.new_frame()
    ov_hover = _draw_overlay(g)
    _draw_modal()
    if ov_hover and imgui.is_mouse_clicked(0) and _left_down():
        ov_drag["on"] = True
        ov_drag["mx"], ov_drag["my"] = _cursor_screen()
        ov_drag["wx"], ov_drag["wy"] = glfw.get_window_pos(_ov_win)
    if ov_drag["on"]:
        if _left_down():
            cx, cy = _cursor_screen()
            glfw.set_window_pos(
                _ov_win,
                ov_drag["wx"] + (cx - ov_drag["mx"]),
                ov_drag["wy"] + (cy - ov_drag["my"]),
            )
        else:
            ov_drag["on"] = False
    imgui.render()
    fb_w, fb_h = glfw.get_framebuffer_size(_ov_win)
    gl.glViewport(0, 0, int(fb_w), int(fb_h))
    gl.glClear(gl.GL_COLOR_BUFFER_BIT)
    _ov_impl.render(imgui.get_draw_data())
    glfw.swap_buffers(_ov_win)
    glfw.make_context_current(main_window)
    if main_ctx is not None:
        imgui.set_current_context(main_ctx)


def run_main(g):
    """보이는 창은 ImGui, Tk mainloop 는 숨긴 채로 유지(스레드 after 동작)."""
    import glfw
    from OpenGL import GL as gl
    import imgui

    global _glfw_window, _impl, _win_w, _win_h, _gui_hidden, _main_ctx

    root = g["root"]
    _cloak_tk_root(root)

    _win_w = 220
    try:
        sw = int(g.get("saved_win_w") or 220)
        if sw >= 220:
            _win_w = min(420, sw)
        else:
            _win_w = 220
    except Exception:
        _win_w = 220
    _win_title = g.get("SOOPLIVE_CLIENT_TITLE") or "soop client"
    window, impl = _init_glfw_window(_win_title, _win_w, 520, 0, 0)
    _present_glfw_window(window, _win_w, 520, _win_title)
    _glfw_window = window
    _impl = impl
    _gui_hidden = False
    _main_ctx = imgui.get_current_context()

    drag = {"on": False, "mx": 0, "my": 0, "wx": 0, "wy": 0}
    ov_drag = {"on": False, "mx": 0, "my": 0, "wx": 0, "wy": 0}
    last_h = [520]
    draw_err = [0]

    def _tick():
        global _win_w, _win_h
        if _glfw_window is None:
            return
        try:
            if glfw.window_should_close(window):
                g["exit_app"]()
                return
            _flush_pending_overlay()
            if _should_pause_glfw(g):
                root.after(50, _tick)
                return
            glfw.poll_events()
            if _gui_hidden:
                root.after(50, _tick)
                return

            glfw.make_context_current(window)
            if _main_ctx is not None:
                imgui.set_current_context(_main_ctx)
            impl.process_inputs()
            imgui.new_frame()
            content_h, title_hovered = _draw_main(g)

            if title_hovered and imgui.is_mouse_clicked(0) and _left_down():
                drag["on"] = True
                drag["mx"], drag["my"] = _cursor_screen()
                drag["wx"], drag["wy"] = glfw.get_window_pos(window)
            if drag["on"]:
                if _left_down():
                    cx, cy = _cursor_screen()
                    glfw.set_window_pos(
                        window, drag["wx"] + (cx - drag["mx"]), drag["wy"] + (cy - drag["my"])
                    )
                else:
                    drag["on"] = False

            if content_h is not None:
                try:
                    mon = glfw.get_primary_monitor()
                    cap = int(glfw.get_video_mode(mon).size.height * 0.88) if mon else 900
                except Exception:
                    cap = 900
                need = int(content_h) + 4
                if _win_h <= 0:
                    _win_h = need
                elif need > _win_h:
                    _win_h = need
                nh = max(220, min(int(_win_h), cap))
                last_h[0] = nh
                cw, ch = glfw.get_window_size(window)
                if cw != int(_win_w) or abs(ch - nh) > 2:
                    glfw.set_window_size(window, int(_win_w), int(nh))

            imgui.render()
            fb_w, fb_h = glfw.get_framebuffer_size(window)
            gl.glViewport(0, 0, int(fb_w), int(fb_h))
            gl.glClear(gl.GL_COLOR_BUFFER_BIT)
            impl.render(imgui.get_draw_data())
            glfw.swap_buffers(window)

            tick_overlay(g, window, _main_ctx, ov_drag)

            draw_err[0] = 0
        except Exception:
            import traceback
            traceback.print_exc()
            draw_err[0] += 1
            if draw_err[0] >= 8:
                _cloak_tk_root(root)
                return
        try:
            root.after(16, _tick)
        except Exception:
            pass

    root.after(16, _tick)
    root.mainloop()
