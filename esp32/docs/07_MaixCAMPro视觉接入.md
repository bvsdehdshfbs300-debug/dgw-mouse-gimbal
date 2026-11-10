# 07 MaixCAM Pro 视觉接入

本项目可以加入 MaixCAM Pro 作为视觉识别端。推荐分工如下：

```text
MaixCAM Pro：摄像头取图、运行模型、识别目标、计算目标中心偏差
ESP32-S3：接收串口指令、输出 Stp/Dir 脉冲、控制双轴电机和激光
```

这样比直接用 MaixCAM Pro 发电机脉冲更稳定，因为 ESP32-S3 更适合产生稳定的 `Stp/Dir` 脉冲。

## 当前皮卡丘识别脚本

脚本位置：

```text
maixcam/pikachu_detect.py
```

用途：

```text
1. 加载训练好的 YOLOv5 模型
2. 识别皮卡丘
3. 画出检测框
4. 画出目标中心
5. 显示目标中心相对画面中心的 dx/dy
```

## 模型文件放置

当前脚本默认模型路径：

```text
/root/models/model_276234.mud
```

板子上需要同时存在：

```text
/root/models/model_276234.mud
/root/models/model_276234.cvimodel
```

`.mud` 和 `.cvimodel` 必须在同一个目录，因为 `.mud` 会按相对路径寻找 `.cvimodel`。

## MaixVision 运行方式

1. 打开 MaixVision。
2. 连接 MaixCAM Pro。
3. 把 `maixcam/pikachu_detect.py` 复制到编辑器。
4. 确认模型文件已经上传到 `/root/models/`。
5. 点击运行。

## 顶格可复制代码

```python
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
```

## 后续接入 ESP32

识别脚本里已经计算了：

```text
dx = 目标中心 x - 画面中心 x
dy = 目标中心 y - 画面中心 y
```

后续可以把 `dx/dy` 转成 ESP32 串口协议：

```text
M x_steps y_steps
```

例如：

```text
M 10 -5
```

ESP32-S3 收到后会控制双轴云台移动。

## 注意

当前脚本只是视觉识别和偏差显示，还没有自动控制云台。建议先把识别稳定跑通，再接串口控制。
