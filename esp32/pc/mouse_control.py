import argparse
import signal
import sys
import time

import serial
from pynput import mouse


def clamp(value, limit):
    if value > limit:
        return limit
    if value < -limit:
        return -limit
    return value


class MouseStepperBridge:
    def __init__(self, port, baud, gain, deadzone, max_steps, interval):
        self.ser = serial.Serial(port, baudrate=baud, timeout=0.02)
        self.gain = gain
        self.deadzone = deadzone
        self.max_steps = max_steps
        self.interval = interval
        self.last_x = None
        self.last_y = None
        self.accum_x = 0.0
        self.accum_y = 0.0
        self.running = True

    def on_move(self, x, y):
        if self.last_x is None:
            self.last_x = x
            self.last_y = y
            return

        dx = x - self.last_x
        dy = y - self.last_y
        self.last_x = x
        self.last_y = y

        if abs(dx) >= self.deadzone:
            self.accum_x += dx * self.gain
        if abs(dy) >= self.deadzone:
            self.accum_y += -dy * self.gain

    def send_loop(self):
        print("Mouse control running. Press Ctrl+C to stop.")
        print("Move mouse horizontally for X, vertically for Y.")

        while self.running:
            x_steps = int(self.accum_x)
            y_steps = int(self.accum_y)

            if x_steps or y_steps:
                x_steps = clamp(x_steps, self.max_steps)
                y_steps = clamp(y_steps, self.max_steps)
                self.accum_x -= x_steps
                self.accum_y -= y_steps

                cmd = f"M {x_steps} {y_steps}\n".encode("ascii")
                self.ser.write(cmd)

            time.sleep(self.interval)

    def close(self):
        self.running = False
        self.ser.close()


def main():
    parser = argparse.ArgumentParser(description="PC mouse to ESP32-S3 two-axis stepper bridge")
    parser.add_argument("--port", default="COM3", help="ESP32 serial port, default COM3")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--gain", type=float, default=1.0, help="step pulses per mouse pixel")
    parser.add_argument("--deadzone", type=float, default=0.0, help="ignore smaller mouse deltas")
    parser.add_argument("--max-steps", type=int, default=40, help="max pulses per serial packet")
    parser.add_argument("--interval", type=float, default=0.02, help="send interval in seconds")
    args = parser.parse_args()

    bridge = MouseStepperBridge(
        port=args.port,
        baud=args.baud,
        gain=args.gain,
        deadzone=args.deadzone,
        max_steps=args.max_steps,
        interval=args.interval,
    )

    def stop(_signum=None, _frame=None):
        bridge.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, stop)

    listener = mouse.Listener(on_move=bridge.on_move)
    listener.start()

    try:
      bridge.send_loop()
    finally:
      listener.stop()
      bridge.close()


if __name__ == "__main__":
    main()
