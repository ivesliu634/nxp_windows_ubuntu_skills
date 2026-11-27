# Windows 串口

工具为本目录 `scripts/serial_console.py`；依赖见 `requirements.txt`。调用时展开绝对路径。
配置在 `scripts/profiles/<board>/serial.yaml` 与 README；只读本次相关板型。
写 EEPROM、复位和驱动调整需另有相应授权，
不要把体检提示当成自动执行整改的许可。

## 独立动作（PowerShell）

在 `workspace` 目录定义脚本路径；运行器不保留变量时每条直接写实际绝对路径。

```powershell
$serialScript = (Resolve-Path '..\support_level\tools\serial-console\scripts\serial_console.py').Path
python $serialScript doctor
python $serialScript list
python $serialScript probe --board imx943evk19b1
```

`probe` 展示 profile 和当前接口映射，不代表所有 role 已在这台电脑实测。
板型尚不确定时先 `list`，可以对已识别的 COM 单口捕获；不要为了使用 profile 猜板型。

## Windows 接板与可选诊断

通常先 `list` 查看 COM 和适配器，再按已知板型 `probe` 确认角色。身份异常时可用 `doctor` 辅助定位：

```powershell
python $serialScript doctor --board <profile-id>   # --board 可省，仅在可选 BCU 回读时使用
```

`doctor` 对每个适配器判定身份健康度，退出码即结论：

- `0` ok：每个接口都有稳定身份（FTDI 尾字母 A/B/C/D、CH9114 固定 USB location，或单口适配器），可直接 list/probe/capture。
- `1` blank 或诊断失败：接口身份未能区分时，禁止按 role 猜口。可用独立确认的 `--device COMn` 抓原始日志；此结果本身不能证明 EEPROM 空白或要求写入。未发现适配器、BCU 回读失败或回读目标不明确也返回 1。
- `2` degraded：工具通过 Windows 注册表恢复了顺序，当前可按该映射使用；这不是自动写 EEPROM 的理由。

`doctor`、`list` 和 `probe` 的身份提示都不推断 EEPROM 内容，也不建议直接写默认值。
显式指定 `--verify-eeprom <bcu绝对路径>` 时，必须同时指定 `--board <已确认model>`，
且当前只能有一个 FT4232H 适配器；非 FTDI 桥或多适配器连接时拒绝调用 BCU。
BCU 只做 `eeprom -r`：未读回上下文时保留 `unknown`，不改用串口序列号断言 EEPROM 空白。
读回身份或无效上下文也不改变接口是否可区分的结论；无效上下文不能证明芯片已贴片或可写，
更不构成写入授权。

只有独立确认 EEPROM 可写、确实需要初始化且获授权后，才考虑以下动作；DNP EEPROM 和 CH9114 不适用：

```powershell
# 确认板型后，用 bcu 把默认身份写进 FTDI EEPROM，然后拔插调试 USB 线
bcu eeprom -w -board=<实际model>
# 拔插后重新体检，应变为 ok
python $serialScript doctor --board <profile-id>
```

写 EEPROM 需要独占 FTDI，先关掉自己启动的捕获/终端；细节见 [BCU USAGE](../bcu/USAGE.md)。
list 和 probe 也会在顶部打印同样的身份体检行，无需单独记忆。


```powershell
# 示例 COM12 必须改成刚检测出的口；日志路径改成当前任务目录
python $serialScript capture --device COM12 --baud 115200 --timeout 30 --log 'C:\actual-workspace\support_level\work\task\logs\one.log'

# 仅在已确认匹配 B1 profile 时使用；默认抓 cm33s、a-core 与 sm，保留 if01 给 BCU
python $serialScript capture-set --board imx943evk19b1 --log-dir 'C:\actual-workspace\support_level\work\task\logs' --name boot --timeout 60
```

要抓 reset 瞬间的日志，保持捕获运行，看到 `ALL PORTS READY` 后再从另一个动作触发复位。普通查看正在输出的日志无需复位。
若运行器等待命令结束才允许下一个操作，让它在后台保持捕获或让用户用独立终端启动捕获；不能等捕获退出后才复位。
多板时用 `--adapter <当前基础序列号>` 选设备；同一个 COM 同一时刻只由一个程序占用。

## 发送命令 / 打断启动

先确认串口当前是在 U-Boot、登录提示还是 Linux shell，再发送相应命令。

```powershell
python $serialScript send --board imx943evk19b1 --role a-core --cmd 'uname -a' --capture-after 5
python $serialScript uboot-stop --board imx943evk19b1 --role a-core --timeout 15
python $serialScript shell --board imx943evk19b1 --role a-core
```

`uboot-stop` 要在 autoboot 提示出现前运行；它不会复位板子。`shell` 供交互终端使用，Ctrl-] 退出。
登录和后续命令分开发，避免登录过程中吞掉字符。不要通过另开 `send` 去抢一个正在 capture 的口。

## 角色、日志与异常

- `--board` 是 profile id，板卡 revision 与 silicon revision 分开。i.MX95 / i.MX93 当前 profile 是待验证参考。
- FTDI 多口适配器按 VID:PID、基础序列号、接口尾字母 A/B/C/D 定位 if00..03；COM 号会变化。
- B1 历史 BCU 控制为 if01，日志为 if02/if03；其他板控制通道依 profile/实物核对。
- capture-set 输出分口日志和 session 摘要；打开成功、收到字节、启动成功是不同结论。空日志先查捕获时机、串口角色和 mux 状态。
- `recover` 只报告缺失接口，不重绑 Windows 驱动。先关闭占用程序，必要时由用户重插适配器。
- 943 四口语义继承用户确认：CM33S、空/BCU、U-Boot/Linux、OEI/SMFW。COM 号易变，按同一适配器的固定接口定位，缺口不补位。
- Windows 不执行 Linux 的 sysfs/udev/stty/驱动重绑操作；只处理 COM 枚举、角色确认、捕获、交互及占用提示。

## 非 FTDI 调试桥（FRDM 板：WCH CH9114）

不是所有板都用 FTDI FT4232H。部分 FRDM 板（实测 FRDM i.MX95）用 **WCH CH9114** 四口 USB 串口桥（VID:PID=1A86:55E8）。它和 FTDI 有两点本质区别，判读方式不同：

- **bcu 管不了这类板**：bcu 靠 FT4232H 的 GPIO/I2C 做 onoff/reset/eeprom，对 CH9114 只会报 `failed to open ftdi device`。这类板没有 bcu 板控通道，电源/复位靠物理开关、复位键或独立 SWD/JTAG 探针。profile 里用 `adapter.bcu_capable: false` 标注。
- **接口区分模型不同**：FTDI 优先用尾字母 A/B/C/D，缺失时可用 Windows 注册表；CH9114 共用序列号，按固定 USB location `.0/.2/.4/.6` 映射 if00..03。缺少接口时保留缺口，绝不按当前可见口重新编号。无法证明接口身份时拒绝按 role 操作，不猜测控制台。这类板没有可写的 EEPROM 身份，**不要**套“写 EEPROM 再拔插”的流程。

FRDM i.MX95 的 profile 见 `scripts/profiles/frdmimx95/serial.yaml`（实测 if00=A55 Linux 登录、if01=SM Debug Monitor）。



- 退出码 0 为完成；1 为失败；2 常为要求有数据但没有数据或未等到打断触发。看输出细节判断。

需要不常用参数时执行 `python <绝对脚本路径> <子命令> --help`。首次环境确认可运行同目录 `scripts/selfcheck.py`，不必每次重复。
