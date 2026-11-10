import os

from maix import app, camera, display, image, touchscreen, time


# Change this name for different datasets/classes.
DATASET_NAME = "target"

# Images will be saved on MaixCAM Pro here.
SAVE_DIR = f"/root/datasets/{DATASET_NAME}"

# Use a normal training-friendly resolution.
CAM_W = 640
CAM_H = 480


def next_index(save_dir):
    max_idx = -1
    for name in os.listdir(save_dir):
        if not name.lower().endswith(".jpg"):
            continue
        stem = name[:-4]
        if stem.startswith(DATASET_NAME + "_"):
            num = stem[len(DATASET_NAME) + 1:]
            if num.isdigit():
                max_idx = max(max_idx, int(num))
    return max_idx + 1


def draw_hud(img, count, last_file):
    img.draw_string(8, 8, "Touch screen: capture", color=image.COLOR_GREEN)
    img.draw_string(8, 30, f"Saved: {count}", color=image.COLOR_GREEN)
    img.draw_string(8, 52, f"Dir: {SAVE_DIR}", color=image.COLOR_GREEN)
    if last_file:
        img.draw_string(8, 74, f"Last: {last_file}", color=image.COLOR_GREEN)

    w = img.width()
    h = img.height()
    img.draw_cross(w // 2, h // 2, color=image.COLOR_RED, size=18)


def main():
    os.makedirs(SAVE_DIR, exist_ok=True)

    cam = camera.Camera(CAM_W, CAM_H)
    disp = display.Display()
    ts = touchscreen.TouchScreen()

    # Let auto exposure / white balance settle.
    cam.skip_frames(20)

    idx = next_index(SAVE_DIR)
    saved_count = idx
    last_file = ""
    was_pressed = False
    flash_until_ms = 0

    while not app.need_exit():
        try:
            img = cam.read()
        except Exception:
            time.sleep_ms(10)
            continue

        x, y, pressed = ts.read()

        # Save one image on touch release, avoiding multiple saves while pressed.
        if was_pressed and not pressed:
            filename = f"{DATASET_NAME}_{idx:05d}.jpg"
            path = f"{SAVE_DIR}/{filename}"
            img.save(path)
            print(f"saved: {path}")
            idx += 1
            saved_count += 1
            last_file = filename
            flash_until_ms = time.ticks_ms() + 350

        was_pressed = pressed

        draw_hud(img, saved_count, last_file)
        if pressed:
            img.draw_circle(x, y, 8, color=image.COLOR_YELLOW, thickness=2)

        if time.ticks_ms() < flash_until_ms:
            img.draw_rect(0, 0, img.width(), img.height(), color=image.COLOR_GREEN, thickness=5)

        disp.show(img)


if __name__ == "__main__":
    main()
