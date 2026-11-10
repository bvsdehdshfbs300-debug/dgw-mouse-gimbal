# 先看我：从零跑起来

这个文档给第一次使用本项目的人看。按顺序做，不要跳步。

## 你最终会得到什么

你会得到一个可以用电脑 GUI 控制的双轴云台：

```text
电脑 GUI
  -> USB 串口
  -> ESP32-S3
  -> Stp/Dir 脉冲
  -> 两台闭环步进电机
```

## 第 0 步：确认你有这些东西

```text
1. ESP32-S3 开发板
2. 两台 ZDT X42S 闭环步进电机
3. 10-29V 电机电源，建议两台电机 >= 6A
4. 杜邦线
5. USB 数据线
6. Windows 电脑
7. 已安装 ESP-IDF
8. 已安装 Python
```

可选：

```text
1. 激光模块
2. 万用表
```

## 第 1 步：先接电机电源

```text
电源 + -> 两个电机 V+
电源 - -> 两个电机 Gnd
```

注意：

```text
不要把电机 V+ 接到 ESP32
不要用 ESP32 给电机供电
```

## 第 2 步：接 ESP32 控制线

X 轴：

```text
ESP32 GPIO7  -> X 电机 Stp
ESP32 GPIO15 -> X 电机 Dir
ESP32 GND    -> X 电机 Gnd
```

Y 轴：

```text
ESP32 GPIO4 -> Y 电机 Stp
ESP32 GPIO5 -> Y 电机 Dir
ESP32 GND   -> Y 电机 Gnd
```

两个电机的 `Gnd`、电源负极、ESP32 的 `GND` 必须连在一起。

当前方案先不要接：

```text
Com
En
```

## 第 3 步：烧录 ESP32 固件

打开 ESP-IDF PowerShell，进入项目：

```powershell
cd esp32
```

如果你把项目放到了其他位置，就进入你实际的 `firmware_idf` 目录。

设置芯片：

```powershell
idf.py set-target esp32s3
```

烧录：

```powershell
idf.py -p COM3 build flash monitor
```

如果 `COM3` 不对，换成实际串口：

```powershell
idf.py -p COM8 build flash monitor
```

## 第 4 步：手动测试电机

烧录后在 monitor 里输入：

```text
T X 50
T Y 50
```

如果电机能动，说明接线和固件基本正确。

再试：

```text
M 100 -100
```

退出 monitor：

```text
Ctrl + ]
```

## 第 5 步：运行中文 GUI

安装依赖：

```powershell
pip install -r requirements.txt
```

运行：

```powershell
python pc\mouse_gui.py
```

在 GUI 里：

```text
1. 选择 COM 口
2. 点击“连接”
3. 用 X+/X-/Y+/Y- 点动测试
4. 勾选“启用鼠标输出”
5. 在右侧轨迹区域移动鼠标
```

## 最容易错的地方

```text
1. ESP32 GND 没有和电机 Gnd 共地
2. Stp / Dir 接反
3. COM 被误接
4. En 被误接导致电机禁用
5. GUI 和 idf.py monitor 同时占用同一个 COM 口
6. 电机电源电流不够
```

遇到问题先看：

[docs/06_常见问题.md](docs/06_常见问题.md)

## 可选：加入 MaixCAM Pro 视觉

如果你要让项目加入视觉识别，先看：

[docs/07_MaixCAMPro视觉接入.md](docs/07_MaixCAMPro视觉接入.md)

建议先让 MaixCAM Pro 独立识别目标并显示 `dx/dy`，确认识别稳定后，再接入 ESP32 云台控制。
