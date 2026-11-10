from maix import camera, display, image, nn, app
import os

MODEL_PATH = "/root/models/model_276234.mud"
CONF_TH = 0.5
IOU_TH = 0.45

print("model exists:", os.path.exists(MODEL_PATH))

detector = nn.YOLOv5(model=MODEL_PATH)

cam = camera.Camera(
    detector.input_width(),
    detector.input_height(),
    detector.input_format()
)
disp = display.Display()

while not app.need_exit():
    img = cam.read()
    objs = detector.detect(img, conf_th=CONF_TH, iou_th=IOU_TH)

    img_cx = img.width() // 2
    img_cy = img.height() // 2
    img.draw_cross(img_cx, img_cy, color=image.COLOR_BLUE, size=12)

    for obj in objs:
        img.draw_rect(obj.x, obj.y, obj.w, obj.h, color=image.COLOR_RED)

        cx = obj.x + obj.w // 2
        cy = obj.y + obj.h // 2
        dx = cx - img_cx
        dy = cy - img_cy

        img.draw_cross(cx, cy, color=image.COLOR_GREEN, size=12)

        msg = f"{detector.labels[obj.class_id]} {obj.score:.2f}"
        img.draw_string(obj.x, obj.y, msg, color=image.COLOR_RED)
        img.draw_string(obj.x, obj.y + 18, f"dx={dx}, dy={dy}", color=image.COLOR_GREEN)

    disp.show(img)
