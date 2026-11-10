import argparse
import struct
import time
import tkinter as tk

try:
    import serial
except ImportError as exc:
    raise SystemExit("Install pyserial first: pip install pyserial") from exc


CLK_HZ = 50_000_000
FRAME_HEADER = 0xA5


def clamp(value, low, high):
    return max(low, min(high, value))


def rate_to_half_period(rate_hz):
    if rate_hz <= 0:
        return 0
    return int(CLK_HZ // (2 * rate_hz))


def make_frame(x_rate, x_dir, y_rate, y_dir):
    flags = 0
    if x_rate > 0:
        flags |= 0x01
    if x_dir:
        flags |= 0x02
    if y_rate > 0:
        flags |= 0x04
    if y_dir:
        flags |= 0x08

    payload = bytearray()
    payload.append(FRAME_HEADER)
    payload.append(flags)
    payload.extend(struct.pack(">I", rate_to_half_period(x_rate)))
    payload.extend(struct.pack(">I", rate_to_half_period(y_rate)))

    checksum = 0
    for byte in payload:
        checksum ^= byte
    payload.append(checksum)
    return bytes(payload)


class MouseGimbalApp:
    def __init__(self, root, port, baud):
        self.root = root
        self.ser = serial.Serial(port, baudrate=baud, timeout=0)

        self.last_x = None
        self.last_y = None
        self.dx_acc = 0
        self.dy_acc = 0
        self.last_motion_time = time.monotonic()

        root.title("FPGA mouse gimbal control")
        root.geometry("620x420")

        self.canvas = tk.Canvas(root, bg="#20242a", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.create_text(
            310,
            160,
            fill="#e8edf2",
            text="Move mouse in this window to control the gimbal",
            font=("Segoe UI", 14),
        )

        panel = tk.Frame(root)
        panel.pack(fill=tk.X)

        self.max_rate = tk.IntVar(value=600)
        self.sensitivity = tk.DoubleVar(value=30.0)
        self.deadzone = tk.IntVar(value=2)
        self.invert_x = tk.BooleanVar(value=False)
        self.invert_y = tk.BooleanVar(value=True)

        self._add_slider(panel, "max step/s", self.max_rate, 50, 3000)
        self._add_slider(panel, "sensitivity", self.sensitivity, 1, 100)
        self._add_slider(panel, "deadzone px", self.deadzone, 0, 20)
        tk.Checkbutton(panel, text="invert X", variable=self.invert_x).pack(side=tk.LEFT)
        tk.Checkbutton(panel, text="invert Y", variable=self.invert_y).pack(side=tk.LEFT)

        self.status = tk.Label(root, text="", anchor="w")
        self.status.pack(fill=tk.X)

        self.canvas.bind("<Motion>", self.on_motion)
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.after(20, self.update_motor)

    def _add_slider(self, parent, label, variable, low, high):
        frame = tk.Frame(parent)
        frame.pack(side=tk.LEFT, padx=6)
        tk.Label(frame, text=label).pack()
        tk.Scale(
            frame,
            from_=low,
            to=high,
            orient=tk.HORIZONTAL,
            variable=variable,
            length=150,
            showvalue=True,
        ).pack()

    def on_motion(self, event):
        if self.last_x is not None:
            self.dx_acc += event.x - self.last_x
            self.dy_acc += event.y - self.last_y
        self.last_x = event.x
        self.last_y = event.y
        self.last_motion_time = time.monotonic()

    def update_motor(self):
        now = time.monotonic()
        dx = self.dx_acc
        dy = self.dy_acc
        self.dx_acc = 0
        self.dy_acc = 0

        if now - self.last_motion_time > 0.15:
            dx = 0
            dy = 0

        if abs(dx) <= self.deadzone.get():
            dx = 0
        if abs(dy) <= self.deadzone.get():
            dy = 0

        if self.invert_x.get():
            dx = -dx
        if self.invert_y.get():
            dy = -dy

        x_dir = dx >= 0
        y_dir = dy >= 0
        max_rate = self.max_rate.get()
        sensitivity = self.sensitivity.get()

        x_rate = int(clamp(abs(dx) * sensitivity, 0, max_rate))
        y_rate = int(clamp(abs(dy) * sensitivity, 0, max_rate))

        self.ser.write(make_frame(x_rate, x_dir, y_rate, y_dir))
        self.status.config(text=f"x={x_rate:4d} step/s y={y_rate:4d} step/s")

        self.root.after(20, self.update_motor)

    def on_close(self):
        self.ser.write(make_frame(0, 0, 0, 0))
        time.sleep(0.05)
        self.ser.close()
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", required=True, help="Serial port, for example COM5")
    parser.add_argument("--baud", type=int, default=115200)
    args = parser.parse_args()

    root = tk.Tk()
    MouseGimbalApp(root, args.port, args.baud)
    root.mainloop()


if __name__ == "__main__":
    main()
