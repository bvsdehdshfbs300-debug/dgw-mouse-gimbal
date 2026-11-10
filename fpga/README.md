## FPGA 版文件对照

| 位置 | 对应部分 | 看什么 |
| --- | --- | --- |
| [src/mouse_gimbal_top.v](src/mouse_gimbal_top.v) | 顶层控制逻辑 | 串口帧校验、两轴使能、方向与周期设置 |
| [src/uart_rx.v](src/uart_rx.v) | UART 接收器 | 将串口位流还原为字节 |
| [src/stepper_axis.v](src/stepper_axis.v) | 单轴脉冲发生器 | 按半周期输出 STEP 与方向 |
| [pc/mouse_gimbal_control.py](pc/mouse_gimbal_control.py) | 电脑控制界面 | 把鼠标变化编码为 FPGA 串口帧 |
| [mouse_gimbal.qsf](mouse_gimbal.qsf) | 器件与引脚 | Cyclone IV 器件、顶层和引脚映射 |
| [constraints.sdc](constraints.sdc) | 时钟约束 | 工程时钟约束 |
| [build.ps1](build.ps1) | 编译脚本 | 调用 Quartus 构建工程 |
| [program.ps1](program.ps1) | 下载脚本 | 手动将生成的 SOF 下载到板卡 |

这一路线使用二进制串口帧。原接线与编译说明继续保留在下面。

---

# FPGA mouse gimbal control

This project controls two ZDT X42S stepper motors in pulse mode.

PC mouse movement is converted to serial frames. The FPGA receives those frames
and generates two STEP/DIR outputs.

## FPGA pins

```text
clk       PIN_25  50 MHz board clock
uart_rx   PIN_23  connect USB-TTL TX here, or use the board CH340 path
uart_tx   PIN_10  optional, idle high

m1_step   PIN_39
m1_dir    PIN_42
m1_en     PIN_38
m2_step   PIN_43
m2_dir    PIN_44
m2_en     PIN_41
status    PIN_11  toggles when a valid serial frame is received
```

## Wiring

```text
USB-TTL TX  -> FPGA uart_rx / PIN_23
USB-TTL RX  -> FPGA uart_tx / PIN_10, optional
USB-TTL GND -> FPGA GND

FPGA PIN_39 -> X motor Stp
FPGA PIN_42 -> X motor Dir
FPGA PIN_38 -> X motor En
FPGA PIN_43 -> Y motor Stp
FPGA PIN_44 -> Y motor Dir
FPGA PIN_41 -> Y motor En
FPGA GND    -> both motor Gnd
```

Power the motors from their own 10-29 V supply. Do not power motors from the
FPGA board. Keep all grounds common.

## Build and program

```powershell
cd .
.\build.ps1
.\program.ps1
```

## PC control

Install pyserial if needed:

```powershell
pip install pyserial
```

Run the GUI:

```powershell
python .\pc\mouse_gimbal_control.py --port COM5
```

Move the mouse inside the window. Mouse stops for 150 ms will command both
motors to stop.
