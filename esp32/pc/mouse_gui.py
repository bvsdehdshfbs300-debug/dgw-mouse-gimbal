import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import serial
import serial.tools.list_ports


class SerialWorker:
    def __init__(self):
        self.ser = None
        self.commands = queue.Queue()
        self.running = False
        self.thread = None

    def connect(self, port, baud):
        self.disconnect()
        self.ser = serial.Serial(port, baudrate=baud, timeout=0.02)
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def disconnect(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=0.5)
        self.thread = None
        if self.ser:
            self.ser.close()
        self.ser = None

    def send(self, command):
        if self.ser and self.ser.is_open:
            self.commands.put(command)
            return True
        return False

    def _loop(self):
        while self.running:
            try:
                command = self.commands.get(timeout=0.05)
            except queue.Empty:
                continue

            try:
                self.ser.write(command.encode("ascii"))
            except serial.SerialException:
                self.running = False


class MouseGimbalGui(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ESP32-S3 双轴鼠标云台")
        self.geometry("1080x720")
        self.minsize(900, 620)

        self.serial_worker = SerialWorker()
        self.last_x = None
        self.last_y = None
        self.dot_id = None
        self.jog_after_id = None
        self.jog_vector = (0, 0)
        self.accum_x = 0.0
        self.accum_y = 0.0
        self.sent_x = 0
        self.sent_y = 0

        self.connected = tk.BooleanVar(value=False)
        self.mouse_enabled = tk.BooleanVar(value=False)
        self.laser_enabled = tk.BooleanVar(value=False)

        self.port_var = tk.StringVar(value="COM3")
        self.baud_var = tk.IntVar(value=115200)
        self.gain_var = tk.DoubleVar(value=0.2)
        self.deadzone_var = tk.DoubleVar(value=0.0)
        self.max_steps_var = tk.IntVar(value=40)
        self.period_var = tk.IntVar(value=500)
        self.jog_steps_var = tk.IntVar(value=100)
        self.invert_x_var = tk.BooleanVar(value=False)
        self.invert_y_var = tk.BooleanVar(value=False)

        self.status_var = tk.StringVar(value="未连接")
        self.motion_var = tk.StringVar(value="X: 0    Y: 0")
        self.last_cmd_var = tk.StringVar(value="最近命令：无")

        self._configure_style()
        self._build_ui()
        self._refresh_ports()
        self.after(20, self._send_loop)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _configure_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#f4f6f8")
        style.configure("Panel.TFrame", background="#ffffff")
        style.configure("TLabel", background="#f4f6f8", foreground="#1f2933", font=("Microsoft YaHei UI", 10))
        style.configure("Panel.TLabel", background="#ffffff")
        style.configure("Title.TLabel", background="#ffffff", foreground="#111827", font=("Microsoft YaHei UI", 13, "bold"))
        style.configure("Status.TLabel", background="#ffffff", foreground="#475569")
        style.configure("TButton", font=("Microsoft YaHei UI", 10), padding=(8, 5))
        style.configure("Accent.TButton", font=("Microsoft YaHei UI", 10, "bold"), padding=(10, 6))
        style.configure("Danger.TButton", foreground="#b91c1c", font=("Microsoft YaHei UI", 10, "bold"))
        style.configure("TCheckbutton", background="#ffffff", foreground="#1f2933", font=("Microsoft YaHei UI", 10))
        style.configure("TLabelframe", background="#ffffff")
        style.configure("TLabelframe.Label", background="#ffffff", foreground="#334155", font=("Microsoft YaHei UI", 10, "bold"))

    def _build_ui(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill=tk.BOTH, expand=True)

        controls = ttk.Frame(root, style="Panel.TFrame", padding=12, width=300)
        controls.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))
        controls.pack_propagate(False)

        canvas_panel = ttk.Frame(root, style="Panel.TFrame", padding=10)
        canvas_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        ttk.Label(controls, text="双轴控制台", style="Title.TLabel").pack(anchor=tk.W, pady=(0, 10))
        self._build_serial_panel(controls)
        self._build_laser_panel(controls)
        self._build_motion_panel(controls)
        self._build_jog_panel(controls)

        ttk.Label(controls, textvariable=self.status_var, style="Status.TLabel", wraplength=260).pack(anchor=tk.W, pady=(12, 4))
        ttk.Label(controls, textvariable=self.last_cmd_var, style="Status.TLabel", wraplength=260).pack(anchor=tk.W)

        toolbar = ttk.Frame(canvas_panel, style="Panel.TFrame")
        toolbar.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(toolbar, text="鼠标轨迹", style="Title.TLabel").pack(side=tk.LEFT)
        ttk.Label(toolbar, textvariable=self.motion_var, style="Panel.TLabel").pack(side=tk.RIGHT)

        self.canvas = tk.Canvas(canvas_panel, bg="#0f1720", highlightthickness=1, highlightbackground="#9aa7b2")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Motion>", self._on_mouse_move)
        self.canvas.bind("<Enter>", self._on_mouse_enter)
        self.canvas.bind("<Leave>", self._on_mouse_leave)
        self.canvas.bind("<Button-3>", lambda _event: self._clear_track())
        self.canvas.bind("<Configure>", lambda _event: self._redraw_canvas_guides())
        self.bind("<KeyPress-l>", lambda _event: self._toggle_laser())
        self.bind("<KeyPress-L>", lambda _event: self._toggle_laser())
        self._redraw_canvas_guides()

    def _build_serial_panel(self, parent):
        panel = ttk.LabelFrame(parent, text="连接")
        panel.pack(fill=tk.X, pady=(0, 10))

        row = ttk.Frame(panel, style="Panel.TFrame")
        row.pack(fill=tk.X, padx=8, pady=(8, 6))
        self.port_combo = ttk.Combobox(row, textvariable=self.port_var, width=12, state="readonly")
        self.port_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(row, text="刷新", width=6, command=self._refresh_ports).pack(side=tk.LEFT, padx=(6, 0))

        row = ttk.Frame(panel, style="Panel.TFrame")
        row.pack(fill=tk.X, padx=8, pady=(0, 8))
        ttk.Label(row, text="波特率", style="Panel.TLabel").pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=self.baud_var, width=10).pack(side=tk.RIGHT)

        row = ttk.Frame(panel, style="Panel.TFrame")
        row.pack(fill=tk.X, padx=8, pady=(0, 8))
        self.connect_button = ttk.Button(row, text="连接", style="Accent.TButton", command=self._connect)
        self.connect_button.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.disconnect_button = ttk.Button(row, text="断开", command=self._disconnect)
        self.disconnect_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))

    def _build_motion_panel(self, parent):
        panel = ttk.LabelFrame(parent, text="鼠标控制")
        panel.pack(fill=tk.X, pady=(0, 10))

        ttk.Checkbutton(panel, text="启用鼠标输出", variable=self.mouse_enabled, command=self._update_mouse_state).pack(anchor=tk.W, padx=8, pady=(8, 6))
        self._spin(panel, "灵敏度 步/像素", self.gain_var, 0.01, 20.0, 0.05)
        self._spin(panel, "死区 像素", self.deadzone_var, 0.0, 20.0, 0.5)
        self._spin(panel, "单包最大步数", self.max_steps_var, 1, 1000, 1)

        row = ttk.Frame(panel, style="Panel.TFrame")
        row.pack(fill=tk.X, padx=8, pady=(4, 8))
        ttk.Label(row, text="脉冲半周期 us", style="Panel.TLabel").pack(side=tk.LEFT)
        ttk.Spinbox(row, textvariable=self.period_var, from_=80, to=10000, increment=50, width=8).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(row, text="设置", command=self._set_period).pack(side=tk.RIGHT)

        row = ttk.Frame(panel, style="Panel.TFrame")
        row.pack(fill=tk.X, padx=8, pady=(0, 8))
        ttk.Checkbutton(row, text="X 反向", variable=self.invert_x_var).pack(side=tk.LEFT)
        ttk.Checkbutton(row, text="Y 反向", variable=self.invert_y_var).pack(side=tk.LEFT, padx=(18, 0))

    def _build_jog_panel(self, parent):
        panel = ttk.LabelFrame(parent, text="点动")
        panel.pack(fill=tk.X, pady=(0, 10))

        self._spin(panel, "点动步数", self.jog_steps_var, 1, 5000, 10)

        grid = ttk.Frame(panel, style="Panel.TFrame")
        grid.pack(pady=(0, 8))
        self._jog_button(grid, "Y+", 0, 1, 0, 1)
        self._jog_button(grid, "X-", 1, 0, -1, 0)
        ttk.Button(grid, text="停止", width=8, style="Danger.TButton", command=self._stop_motion).grid(row=1, column=1, padx=4, pady=4)
        self._jog_button(grid, "X+", 1, 2, 1, 0)
        self._jog_button(grid, "Y-", 2, 1, 0, -1)

    def _build_laser_panel(self, parent):
        panel = ttk.LabelFrame(parent, text="激光")
        panel.pack(fill=tk.X, pady=(0, 10))

        self.laser_button = ttk.Button(panel, text="激光开关：关", style="Accent.TButton", command=self._toggle_laser)
        self.laser_button.pack(fill=tk.X, padx=8, pady=(8, 6), ipady=8)

        row = ttk.Frame(panel, style="Panel.TFrame")
        row.pack(fill=tk.X, padx=8, pady=(0, 8))
        ttk.Label(row, text="快捷键：L", style="Panel.TLabel").pack(side=tk.LEFT)
        ttk.Button(row, text="清除轨迹", command=self._clear_track).pack(side=tk.RIGHT)

    def _spin(self, parent, label, variable, from_, to, increment):
        row = ttk.Frame(parent, style="Panel.TFrame")
        row.pack(fill=tk.X, padx=8, pady=(4, 6))
        ttk.Label(row, text=label, style="Panel.TLabel").pack(side=tk.LEFT)
        ttk.Spinbox(row, textvariable=variable, from_=from_, to=to, increment=increment, width=8).pack(side=tk.RIGHT)

    def _jog_button(self, parent, text, row, column, x_dir, y_dir):
        button = ttk.Button(parent, text=text, width=8)
        button.grid(row=row, column=column, padx=4, pady=4)
        button.bind("<ButtonPress-1>", lambda _event: self._start_jog(x_dir, y_dir))
        button.bind("<ButtonRelease-1>", lambda _event: self._stop_jog())

    def _refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_combo["values"] = ports
        if ports and self.port_var.get() not in ports:
            self.port_var.set(ports[0])
        self.status_var.set(f"发现串口：{', '.join(ports) if ports else '无'}")

    def _connect(self):
        try:
            self.serial_worker.connect(self.port_var.get(), self.baud_var.get())
        except serial.SerialException as exc:
            messagebox.showerror("串口错误", str(exc))
            self.status_var.set("连接失败")
            return

        self.connected.set(True)
        self.status_var.set(f"已连接：{self.port_var.get()}")
        self._set_period()
        self._send_laser(False)

    def _disconnect(self):
        self.mouse_enabled.set(False)
        self._send_laser(False)
        self.serial_worker.disconnect()
        self.connected.set(False)
        self.status_var.set("已断开")

    def _send_command(self, command):
        ok = self.serial_worker.send(command)
        if ok:
            self.last_cmd_var.set(f"最近命令：{command.strip()}")
        else:
            self.status_var.set("未连接，命令未发送")
        return ok

    def _set_period(self):
        self._send_command(f"P {self.period_var.get()}\n")

    def _send_laser(self, enabled):
        self.laser_enabled.set(enabled)
        self.laser_button.configure(text=f"激光开关：{'开' if enabled else '关'}")
        self._send_command(f"L {1 if enabled else 0}\n")

    def _toggle_laser(self):
        self._send_laser(not self.laser_enabled.get())

    def _send_move(self, x_steps, y_steps):
        if x_steps == 0 and y_steps == 0:
            return
        if self._send_command(f"M {x_steps} {y_steps}\n"):
            self.sent_x += x_steps
            self.sent_y += y_steps
            self.motion_var.set(f"X: {self.sent_x}    Y: {self.sent_y}")

    def _start_jog(self, x_dir, y_dir):
        self.jog_vector = (x_dir, y_dir)
        self._jog_once()

    def _jog_once(self):
        x_dir, y_dir = self.jog_vector
        steps = self.jog_steps_var.get()
        self._send_move(x_dir * steps, y_dir * steps)
        self.jog_after_id = self.after(120, self._jog_once)

    def _stop_jog(self):
        if self.jog_after_id is not None:
            self.after_cancel(self.jog_after_id)
            self.jog_after_id = None

    def _stop_motion(self):
        self._stop_jog()
        self.accum_x = 0.0
        self.accum_y = 0.0
        self.mouse_enabled.set(False)
        self.status_var.set("已停止输出")

    def _update_mouse_state(self):
        self.status_var.set("鼠标输出已启用" if self.mouse_enabled.get() else "鼠标输出已关闭")

    def _on_mouse_enter(self, event):
        self.last_x = event.x
        self.last_y = event.y

    def _on_mouse_leave(self, _event):
        self.last_x = None
        self.last_y = None

    def _on_mouse_move(self, event):
        if self.last_x is None:
            self.last_x = event.x
            self.last_y = event.y
            return

        dx = event.x - self.last_x
        dy = event.y - self.last_y
        old_x = self.last_x
        old_y = self.last_y
        self.last_x = event.x
        self.last_y = event.y

        self.canvas.create_line(old_x, old_y, event.x, event.y, fill="#38d9a9", width=2, tags="track")
        self._draw_dot(event.x, event.y)

        if not self.mouse_enabled.get():
            return

        deadzone = self.deadzone_var.get()
        if abs(dx) >= deadzone:
            value = dx * self.gain_var.get()
            self.accum_x += -value if self.invert_x_var.get() else value
        if abs(dy) >= deadzone:
            value = -dy * self.gain_var.get()
            self.accum_y += -value if self.invert_y_var.get() else value

    def _send_loop(self):
        if self.mouse_enabled.get():
            max_steps = max(1, self.max_steps_var.get())
            x_steps = int(self.accum_x)
            y_steps = int(self.accum_y)

            if x_steps or y_steps:
                x_steps = max(-max_steps, min(max_steps, x_steps))
                y_steps = max(-max_steps, min(max_steps, y_steps))
                self.accum_x -= x_steps
                self.accum_y -= y_steps
                self._send_move(x_steps, y_steps)

        self.after(20, self._send_loop)

    def _draw_dot(self, x, y):
        if self.dot_id is not None:
            self.canvas.delete(self.dot_id)
        self.dot_id = self.canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill="#f8fafc", outline="#38d9a9", width=2, tags="dot")

    def _clear_track(self):
        self.canvas.delete("track")
        if self.dot_id is not None:
            self.canvas.delete(self.dot_id)
            self.dot_id = None
        self._redraw_canvas_guides()

    def _redraw_canvas_guides(self):
        self.canvas.delete("guide")
        width = max(self.canvas.winfo_width(), 1)
        height = max(self.canvas.winfo_height(), 1)
        cx = width // 2
        cy = height // 2
        self.canvas.create_line(cx, 0, cx, height, fill="#334155", dash=(5, 5), tags="guide")
        self.canvas.create_line(0, cy, width, cy, fill="#334155", dash=(5, 5), tags="guide")
        self.canvas.create_oval(cx - 6, cy - 6, cx + 6, cy + 6, outline="#94a3b8", width=2, tags="guide")
        self.canvas.tag_lower("guide")

    def _on_close(self):
        self._stop_jog()
        self._send_laser(False)
        self.serial_worker.disconnect()
        self.destroy()


if __name__ == "__main__":
    MouseGimbalGui().mainloop()
