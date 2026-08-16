# -*- coding: utf-8 -*-
"""격수 메인 UI — Dear ImGui. 로직·변수는 attacker_hp.pyw 를 그대로 쓴다.
창 제목: sooplive service / 쫄화면은 Tk 그대로 sooplive-미리보기."""
import ctypes
import tkinter as tk

import imgui_ui as _ui

_glfw_window = None
_impl = None
_main_ctx = None
_win_w = 340
_win_h = 0
_tex = {}
_last_arr = None


def is_active():
    return _glfw_window is not None


def _cloak_tk_root(root):
    _ui._cloak_tk_root(root)


def _hex(*a, **k):
    return _ui._hex(*a, **k)


def _text_c(*a, **k):
    return _ui._text_c(*a, **k)


def _center_text(*a, **k):
    return _ui._center_text(*a, **k)


def _btn(*a, **k):
    return _ui._btn(*a, **k)


def _left_down():
    return _ui._left_down()


def _widget_text(w, default=""):
    try:
        t = w.cget("text")
        return t if t is not None else default
    except Exception:
        return default


def _widget_fg(w, default="#cdd6f4"):
    try:
        return w.cget("fg") or w.cget("foreground") or default
    except Exception:
        return default


def _stream_interacting(g):
    stream = g.get("stream_view_win")
    if stream is None or not _left_down():
        return False
    try:
        if not stream.winfo_exists():
            return False
        user32 = ctypes.windll.user32
        hid = int(stream.winfo_id())
        hwnd = int(user32.GetParent(hid) or hid)
        rect = ctypes.wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return False
        x, y = _ui._cursor_screen()
        return rect.left <= x <= rect.right and rect.top <= y <= rect.bottom
    except Exception:
        return False


def _should_pause(g):
    root = g.get("root")
    if root is None:
        return False
    if _stream_interacting(g):
        return True
    stream = g.get("stream_view_win")
    try:
        for w in root.winfo_children():
            try:
                if not isinstance(w, tk.Toplevel) or not w.winfo_exists():
                    continue
                try:
                    if str(w.state()) == "withdrawn":
                        continue
                except Exception:
                    pass
                if stream is not None and w == stream:
                    continue
                return True
            except Exception:
                pass
    except Exception:
        pass
    return False


def _upload_preview(arr):
    global _last_arr
    if arr is None:
        return None
    _last_arr = arr
    return _ui._upload_tex("atk_prev", arr, 220)


def _draw_hp_bar(hp):
    import imgui
    hp = max(0.0, min(100.0, float(hp)))
    if hp > 50:
        col = "#10b981"
    elif hp > 25:
        col = "#fbbf24"
    else:
        col = "#ef4444"
    imgui.push_style_color(imgui.COLOR_PLOT_HISTOGRAM, *_hex(col))
    imgui.progress_bar(hp / 100.0, (-1, 22), "HP:%.0f%%" % hp)
    imgui.pop_style_color(1)


def _draw_main(g):
    import imgui

    global _win_w, _win_h
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
    imgui.begin("##attacker", flags=flags)

    _center_text("뚱격수", "#cba6f7")
    imgui.same_line(_win_w - 26)
    if _btn("✖", "#800020", "#9e1a3a", width=18, height=18):
        g["close_app"]()
    title_hovered = _ui._title_row_hovered()
    imgui.separator()

    upd = _widget_text(g["lbl_update"], "업데이트")
    uc = _widget_fg(g["lbl_update"], "#e2e8f0")
    if "a6e3a1" in str(uc).lower() or "10b981" in str(uc).lower():
        ufg, uhv, utc = "#238636", "#2ea043", "#ffffff"
    else:
        ufg, uhv, utc = "#21262d", "#30363d", uc
    if _btn(upd, ufg, uhv, text_color=utc):
        g["on_update_check_click"]()

    imgui.align_text_to_frame_padding()
    _text_c("📡", "#f9e2af")
    imgui.same_line()
    imgui.set_next_item_width(-44)
    changed, ip = imgui.input_text("##ip", g["ip_var"].get(), 64)
    if changed:
        g["ip_var"].set(ip)
    imgui.same_line()
    if _btn("저장", "#800020", "#9e1a3a", width=36):
        g["save_cfg"]()

    try:
        hp_now = float(g["hp_pct"])
    except Exception:
        hp_now = 0.0
    _draw_hp_bar(hp_now)

    st = _widget_text(g["lbl_status"], "")
    imgui.align_text_to_frame_padding()
    _text_c(st, _widget_fg(g["lbl_status"], "#10b981"))
    myip = "내아이피:%s" % (g.get("MY_IP") or "")
    imgui.same_line()
    imgui.set_cursor_pos_x(
        imgui.get_cursor_pos_x() + max(0.0, imgui.get_content_region_available().x - imgui.calc_text_size(myip).x)
    )
    _text_c(myip, "#a6e3a1")

    changed, on = imgui.checkbox("강제베르(end)", bool(g["end_bert_var"].get()))
    if changed:
        g["end_bert_var"].set(bool(on))
        g["save_cfg"]()

    _text_c(_widget_text(g["lbl_roi"], ""), "#45475a")
    arr = g.get("LAST_PREVIEW_ARR")
    tex = _upload_preview(arr) if arr is not None else None
    if tex:
        imgui.image(tex["id"], float(tex["w"]), float(tex["h"]))
    poison = _widget_text(g["lbl_poison"], "")
    if poison:
        _center_text(poison, _widget_fg(g["lbl_poison"], "#ef4444"))

    bw = max(60, (_win_w - 20) / 2)
    if _btn("🎯 피통", "#1f538d", "#14375e", width=bw, height=24):
        g["open_overlay"]()
    imgui.same_line()
    if _btn("💯 100%", "#fbbf24", "#f59e0b", width=bw, height=24, text_color="#1e1e2e"):
        g["set_100ref"]()

    imgui.separator()
    _center_text("쫄법PC 제어", "#f9e2af")
    ctl = [
        ("▶ 시작", b"I", "#10b981"),
        ("👣 따라가기", b"H", "#3b82f6"),
        ("📌 고정", b"P", "#f59e0b"),
        ("🎒 줍기", b"L", "#8b5cf6"),
    ]
    for i, (text, cmd, color) in enumerate(ctl):
        if i % 2 == 1:
            imgui.same_line()
        if _btn(text, color, color, width=bw, height=24):
            g["send_remote_cmd"](cmd)

    imgui.separator()
    _center_text("쫄화면 (Alt+마우스 조종)", "#f9e2af")
    send_t = _widget_text(g["btn_stream_send"], "📡 전송 OFF")
    view_t = _widget_text(g["btn_stream_view"], "📺 쫄화면")
    send_on = "ON" in send_t
    if _btn(send_t, "#10b981" if send_on else "#374151", "#059669" if send_on else "#4b5563", width=bw, height=24):
        g["toggle_stream_send"]()
    imgui.same_line()
    view_on = "닫기" in view_t
    if _btn(view_t, "#ef4444" if view_on else "#6366f1", "#dc2626" if view_on else "#4f46e5", width=bw, height=24):
        g["toggle_stream_view"]()

    imgui.separator()
    _center_text("쫄법PC 연동 단축키", "#f9e2af")
    sock = g["sock"]
    port = g["TARGET_PORT"]
    for n in range(1, 9):
        if (n - 1) % 2 == 1:
            imgui.same_line()
        if _btn("Alt+%d F3>F%d" % (n, n + 4), "#313244", "#45475a", width=bw, height=22):
            try:
                sock.sendto(bytes([n + 48]), (g["ip_var"].get(), port))
            except Exception:
                pass

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
        _win_w = max(240, min(520, int(_win_w + dx)))
        if _win_h > 0:
            _win_h = max(220, min(900, int(_win_h + dy)))
        g["WIN_W"] = _win_w
        g["WIN_H"] = _win_h
    elif imgui.is_item_deactivated():
        try:
            g["save_cfg"]()
        except Exception:
            pass

    imgui.end()
    return content_h, title_hovered


def run_main(g):
    import glfw
    from OpenGL import GL as gl
    import imgui

    global _glfw_window, _impl, _win_w, _win_h, _main_ctx

    root = g["root"]
    _cloak_tk_root(root)
    try:
        _win_w = max(240, min(520, int(g.get("WIN_W") or 340)))
    except Exception:
        _win_w = 340
    try:
        _win_h = max(0, int(g.get("WIN_H") or 0))
    except Exception:
        _win_h = 0

    window, impl = _ui._init_glfw_window("sooplive service", _win_w, 520, 80, 80)
    _glfw_window = window
    _ui._glfw_window = window
    _impl = impl
    _main_ctx = imgui.get_current_context()

    drag = {"on": False, "mx": 0, "my": 0, "wx": 0, "wy": 0}
    ov_drag = {"on": False, "mx": 0, "my": 0, "wx": 0, "wy": 0}
    draw_err = [0]

    def _tick():
        global _win_w, _win_h
        if _glfw_window is None:
            return
        try:
            if glfw.window_should_close(window):
                g["close_app"]()
                return
            if _should_pause(g):
                root.after(50, _tick)
                return
            glfw.poll_events()
            glfw.make_context_current(window)
            if _main_ctx is not None:
                imgui.set_current_context(_main_ctx)
            impl.process_inputs()
            imgui.new_frame()
            g["hp_pct"] = g.get("hp_pct")
            try:
                g["hp_pct"] = float(g["hp_pct"])
            except Exception:
                pass
            content_h, title_hovered = _draw_main(g)

            if title_hovered and imgui.is_mouse_clicked(0) and _left_down():
                drag["on"] = True
                drag["mx"], drag["my"] = _ui._cursor_screen()
                drag["wx"], drag["wy"] = glfw.get_window_pos(window)
            if drag["on"]:
                if _left_down():
                    cx, cy = _ui._cursor_screen()
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
                cw, ch = glfw.get_window_size(window)
                if cw != int(_win_w) or abs(ch - nh) > 2:
                    glfw.set_window_size(window, int(_win_w), int(nh))
                    g["WIN_W"] = int(_win_w)
                    g["WIN_H"] = int(nh)

            imgui.render()
            fb_w, fb_h = glfw.get_framebuffer_size(window)
            gl.glViewport(0, 0, int(fb_w), int(fb_h))
            gl.glClear(gl.GL_COLOR_BUFFER_BIT)
            impl.render(imgui.get_draw_data())
            glfw.swap_buffers(window)
            _ui.tick_overlay(g, window, _main_ctx, ov_drag)
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
