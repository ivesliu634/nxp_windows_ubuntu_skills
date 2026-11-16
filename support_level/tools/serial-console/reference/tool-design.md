# serial (serial_console.py)


i.MX 板卡串口探测 / 捕获 / 交互工具的 **Windows 原生版本**。

参考自 Linux 版 `nxp_ivesliu_skill/support_level/tools/serial-console`，保留了完全相同的
**命令接口、board profile 概念、session summary 格式和退出码约定**，只把平台相关的
两层（设备发现、交互终端）按 Windows 重写。目标是让 Windows 侧和 Linux 侧行为一致、
profile 可以对照共享。

- 程序入口：`python serial_console.py <command>`
- 底层实现：`python3 + pyserial + PyYAML`
- 板型事实：`profiles/<board>/serial.yaml`

## 依赖

```bat
python -m pip install pyserial pyyaml
```

已在 Python 3.13 + pyserial 3.5 上实机验证（FT4232H 四口适配器）。

## Windows 与 Linux 的差异

| 能力 | Linux 版 | 本 Windows 版 |
|------|---------|--------------|
| 设备发现 | 扫 `/dev/ttyUSB*`、`/dev/serial/by-id`、读 sysfs `bInterfaceNumber` | `serial.tools.list_ports`，用 FTDI 序列号尾字母定位接口 |
| 接口身份 | `by_id` / `ifNN` | `usb_id` + 基础序列号 + 尾字母（A->if00, B->if01, ...） |
| 设备名 | `/dev/ttyUSBn` | `COMxxx`（会变，仅作 fallback 提示） |
| `prepare` | 调用 `stty` 配串口 | 只验证每个 role 能被打开（pyserial 打开时已设 8N1） |
| `recover` | 写 sysfs `driver/bind` 重绑驱动 | 无法命令行重绑，报告缺失接口并提示重新插拔 |
| `stop-modemmanager` | `systemctl stop ModemManager` | no-op（Windows 无此服务） |
| `shell` | `termios` + `select` raw 终端 | `msvcrt` 键盘轮询 + 读线程 |

其余（capture / capture-set / send / uboot-stop 的串口读写逻辑、断线重连、
session summary、READY 文件、退出码）与 Linux 版完全一致。

## 设备识别模型（Windows）

pyserial 在 Windows 上拿不到 `location` / `interface`，但 FTDI 多口适配器会给每个
接口的 USB 序列号追加尾字母。因此：

- **适配器身份** = `VID:PID` + 基础序列号（去掉尾字母），例如 `0403:6011` + `0C1819`
- **接口号** = 序列号尾字母：`A->if00`、`B->if01`、`C->if02`、`D->if03`
- **role -> COM** 由 profile 的 `interface` 字段动态解析，不依赖会变的 COM 号

实测枚举示例：

```
[1] 0403:6011 USB Serial Port interfaces=4 id=0C1819
      order=1 if00 COM153 serial=0C1819A
      order=2 if01 COM154 serial=0C1819B
      order=3 if02 COM155 serial=0C1819C
      order=4 if03 COM156 serial=0C1819D
```

## 常用命令

枚举当前所有串口适配器：

```bat
python serial_console.py list
```

按板型 profile 校验（检查适配器 VID:PID、接口数量、必要 role 是否在位）：

```bat
python serial_console.py probe --board imx93evk14
```

验证板型所有 role 都能打开：

```bat
python serial_console.py prepare --board imx93evk14
```

抓单路日志：

```bat
python serial_console.py capture --board imx93evk14 --role a-core ^
  --log logs\a-core.log --timeout 30
```

同时抓多路（默认抓 profile 中 `default_capture: true` 的 role）：

```bat
python serial_console.py capture-set --board imx93evk14 ^
  --log-dir logs --name sd-boot --timeout 90
```

要求某些 / 全部 role 必须收到数据（否则退出码 2）：

```bat
python serial_console.py capture-set --board imx93evk14 --log-dir logs ^
  --expect-data a-core
python serial_console.py capture-set --board imx93evk14 --log-dir logs --require-data
```

发命令：

```bat
python serial_console.py send --board imx93evk14 --role a-core --cmd "printenv"
```

等 U-Boot autoboot 提示并打断：

```bat
python serial_console.py uboot-stop --board imx93evk14 --role a-core --timeout 10
```

交互式串口终端（`Ctrl-]` 退出）：

```bat
python serial_console.py shell --board imx93evk14 --role a-core
```

也可以不带 `--board`、直接对某个 COM 口操作：

```bat
python serial_console.py capture --device COM155 --timeout 10
```

## 退出码

- `0`：所有端口完成捕获；未声明数据期望的端口可以是 `empty`
- `1`：探测、打开、配置或必要端口检查失败
- `2`：声明必须有数据的 role 最终是 `empty`

## capture-set 输出

每次生成：

```
logs\<name>-<role>.log            每路原始串口数据
logs\<name>-serial-session.txt    人读 session summary
logs\<name>-serial-session.yaml   机读 session summary
```

`--ready-file` 可写一个活动状态标记文件：所有端口打开后创建，捕获结束时删除，
供自动化流程等待"就绪"。

## Profile schema（v3）

```yaml
schema_version: 3
board: imx93evk14
profile_status: verified   # verified | partial | unknown
adapter:
  name: FT4232H Quad HS USB-UART/FIFO IC
  usb_id: "0403:6011"
  interface_count: 4
baudrate: 115200
format: 8N1
ports:
  a-core:
    order: 3
    interface: if02          # 主身份；对应 FTDI 序列号尾字母 C
    description: SPL, U-Boot and Linux console
    log_sources: [spl, u-boot, linux]
    default_capture: true
    required: true
    status: verified         # verified | partial | unknown
```

相比 Linux 版 schema 2，去掉了 `by_id` 和 `tty(/dev/...)`（Linux 专属身份），
其余字段语义一致。工具同时兼容读取 schema 1 / 2 的 `interface` 字段。

## 已知边界

- `recover` 在 Windows 上只能报告缺失接口，不能命令行重绑驱动。若板控工具（BCU）
  占用了某个 FTDI 通道，需关闭它后重新插拔适配器或在设备管理器里禁用/启用。
- COM 号是易变的，任何情况下都不要把 `COMxxx` 当稳定身份。
- profile 的 `status` 只有拿到实机 case 证据后才能升级为 `verified`；随附的
  `imx93evk14` profile 目前是 `partial`（接口布局沿用 Linux 版，Windows role 映射待现场确认）。
