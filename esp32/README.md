## ESP32-S3 版文件对照

| 位置 | 对应部分 | 看什么 |
| --- | --- | --- |
| [pc/mouse_gui.py](pc/mouse_gui.py) | 中文电脑控制界面 | 鼠标轨迹、点动、灵敏度、死区与串口 |
| [pc/mouse_control.py](pc/mouse_control.py) | 命令行控制 | 从电脑发送串口控制命令 |
| [firmware_idf/main/main.c](firmware_idf/main/main.c) | ESP-IDF 主固件 | 解释命令，产生两轴 STEP/DIR 与激光控制 |
| [firmware/mouse_gimbal/mouse_gimbal.ino](firmware/mouse_gimbal/mouse_gimbal.ino) | Arduino 备份固件 | 另一套构建入口，按对应说明选用 |
| [docs/05_串口协议.md](docs/05_%E4%B8%B2%E5%8F%A3%E5%8D%8F%E8%AE%AE.md) | 两端通信约定 | PC 发什么、固件如何解释 |
| [maixcam/capture_dataset.py](maixcam/capture_dataset.py) | 采集脚本备份 | MaixCAM 触屏拍照 |

此目录对应 ESP32-S3 路线，串口命令与 FPGA 版分别查看。下方保留原完整教程。

---

# ESP32-S3 双轴鼠标云台

这是一个面向入门者的 ESP32-S3 双轴云台项目。电脑端用中文 GUI 控制，ESP32-S3 输出 `Stp/Dir` 脉冲，驱动两台张大头/ZDT X42S 闭环步进电机，实现鼠标控制、点动控制和激光开关。

如果你是第一次打开这个项目，请先看：

[START_HERE_先看我.md](START_HERE_先看我.md)

## 项目能做什么

```text
1. 用鼠标控制 X/Y 双轴云台
2. 用中文 GUI 调节灵敏度、速度、死区等参数
3. 用按钮点动 X/Y 轴，适合调试
4. 控制一路激光灯开关
5. 通过简单串口命令二次开发
```

## 项目结构

```text
START_HERE_先看我.md        新手入口
README.md                   项目总览
requirements.txt            Python 依赖
LICENSE                     MIT 开源协议

firmware_idf/               ESP-IDF 固件，推荐使用
firmware/                   Arduino 版本固件备份
pc/                         Python 中文 GUI 和命令行脚本
docs/                       中文接线、烧录、协议、排错文档
maixcam/                    MaixCAM 采图脚本备份
```

## 推荐阅读顺序

```text
1. START_HERE_先看我.md
2. docs/01_硬件清单和安全注意.md
3. docs/02_接线说明.md
4. docs/03_烧录ESP32固件.md
5. docs/04_运行中文GUI.md
6. docs/05_串口协议.md
7. docs/06_常见问题.md
8. docs/07_MaixCAMPro视觉接入.md
```

## 当前默认接线

```text
X轴：
ESP32 GPIO7  -> X 电机 Stp
ESP32 GPIO15 -> X 电机 Dir

Y轴：
ESP32 GPIO4 -> Y 电机 Stp
ESP32 GPIO5 -> Y 电机 Dir

激光：
ESP32 GPIO6 -> 激光模块 Signal / IN / S

共地：
ESP32 GND -> 两个电机 Gnd -> 电源 -
```

电机供电：

```text
外部电源 + -> 两个电机 V+
外部电源 - -> 两个电机 Gnd
```

当前方案中：

```text
电机 Com 不接
电机 En  不接
```

## 快速运行

安装 Python 依赖：

```powershell
pip install -r requirements.txt
```

运行中文 GUI：

```powershell
python pc\mouse_gui.py
```

ESP-IDF 烧录：

```powershell
cd firmware_idf
idf.py set-target esp32s3
idf.py -p COM3 build flash monitor
```

如果 `COM3` 不对，换成设备管理器里的实际串口，例如 `COM8`。

## 开源协议

本项目使用 MIT License，见 [LICENSE](LICENSE)。
