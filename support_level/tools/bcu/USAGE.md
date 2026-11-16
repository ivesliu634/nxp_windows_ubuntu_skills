# Windows BCU

本工具内 `bin/bcu.exe` 是用户提供的 `bcu_1.1.128-0-ge7027dc`。调用前把路径展开成绝对路径，PowerShell 用 `&` 调用 EXE。
板子通过 Windows 的 FTDI 调试口连接；烧写 USB 口可能是另一个接口。
本说明保留原 Vero 的 Windows 方法；写 EEPROM、复位和切模式需要在用户授权范围内执行，
身份体检异常本身不构成写 EEPROM 的授权。

## 先识别，再操作

下面在 `workspace` 目录的 PowerShell 执行；在其他目录时改用绝对路径：

```powershell
$bcuExe = (Resolve-Path '..\support_level\tools\bcu\bin\bcu.exe').Path
& $bcuExe version
& $bcuExe lsftdi
& $bcuExe lsboard
```

`lsboard` 只列工具支持的板型。i.MX943 B1 已有 [板级说明](profiles/imx943evk19b1/README.md)。i.MX95/i.MX93 先结合 EEPROM、丝印核对板型，不能套最近似的名称。

已知候选型号后核对身份，但要注意 bcu 的输出陷阱（实测确认）：

- `eeprom -r -board=<model>` 输出里的 `board model is <model>` **只是回显你在 `-board=` 里传入的名字，不是从板上读出来的**，不能当作身份已核对。实测传一个明显不符的板型也会照样回显该名字。
- 真正判断 FTDI EEPROM 是否已写，看这行后面的内容：空片会打印 `Registered FTDI EEPROM on board` + `Invalid EEPROM context, use -w option to write the default values.`；已写的板会打印真实的 `FTDI EEPROM SN / Board Info / SoC Info`。
- `-auto` 才是真识别：空片会对所有板型逐一报 `Invalid EEPROM context`，最后 `Can't auto recognize the board`；只有已写身份的板 `-auto` 才能认出来。
- 还有一种更省事的空片输出（实测 imx8mpevk）：`eeprom -r -board=<model>` 只打印 `board model is <model>` + `done`，连 `Invalid EEPROM context` 都没有。这时 bcu 什么都没回读到，无法据此判断空/已写；以适配器身份体检为准（串口侧裸序列号 `5`、四口无 A/B/C/D 尾字母即身份未写）。
- 因此空片无法靠 bcu 读回板型，必须靠丝印 / RM / 原理图确认型号，再 `-w` 写入。
- 串口工具 `serial_console.py doctor --board <model> --verify-eeprom <bcu路径>` 已把上述判读固化：它跑 `eeprom -r`，用 `classify_bcu_eeprom_output` 越过回显看真实状态，回读不到内容时明确提示以适配器体检为准。
- 写入空操作还有第三种可能：**FTDI 桥的串行 EEPROM 根本没贴片（DNP）**，此时 `-w` 报成功却永远写不进去，拔插多少次都没用。用原理图核对工具一条命令定论（见下）。

## 判断 EEPROM 是"空白"还是"根本没贴片"

`eeprom -w` 空操作有两种根因，处理相反：白片（有芯片、可写）vs DNP（没芯片、永远写不进）。
证据分三层，**优先用不依赖原理图、可移植到任意板载 FTDI 桥板卡（含客户板）的行为判据**；
原理图只是当你想在上板/拔插前先离线确认时的可选佐证：

1. 主判据（行为体检，板无关，不需原理图）：`serial_console.py doctor`。裸序列号、四口无
   A/B/C/D 尾字母、都塌到 if00 => 身份没写。这套判据对任何用板载 FTDI 桥的板都成立。
2. 行为闭环（区分白片 vs DNP，仍不需原理图）：`eeprom -w` 后拔插再体检。序列号变了、四口出现
   A/B/C/D => 是白片、写成功；反复写+拔插后永远裸序列号、且 bcu 从不打印
   `Registered FTDI EEPROM on board` => 极可能没芯片（DNP）。这是判"能不能写"的可移植闭环。
3. 可选离线佐证（**需要原理图，客户不一定提供**）：`scripts/schematic_eeprom_check.py`。
   有原理图时它把"手翻 PDF 找 EECS/EECLK/EEDATA 看有无 EEPROM 型号"固化成一条命令；没有
   原理图就跳过这层，直接用上面 1/2 定论。

有原理图时的可选佐证命令：

```powershell
python ..\support_level\tools\bcu\scripts\schematic_eeprom_check.py --board imx8mpevk --material ..\support_level\SoC_material
python ..\support_level\tools\bcu\scripts\schematic_eeprom_check.py --pdf '<schematic.pdf>'
```

它在 `support_level/SoC_material/<soc>/hardware/*.pdf` 里定位 FT4232H 桥的串行 EEPROM 接口页（EECS/EECLK/EEDATA），判据是**该页有没有 EEPROM 芯片型号（93LC56/93C46 等）**：

- 有型号 -> `POPULATED`（退出码 0）：芯片在 BOM 里，若空片则 `-w` + 拔插可写入；旁边的 DNP 是相邻跳线电阻，工具已忽略。
- 无型号、只有 DNP 占位 -> `DNP`（退出码 3）：EEPROM 未贴片，`-w` 永远写不进，改用串口注册表兜底口直接找控制台。
- 找不到 EEPROM 引脚 -> `UNKNOWN`（退出码 2）：手工核对该 PDF。

工具总会打印命中页和证据行供人复核。**实测**：imx8mpevk 底板第 19 页 EECS/EECLK/EEDATA 无型号全 DNP -> DNP（正是 8MP `-w` 空操作的根因）；imx93evk14 的 EEPROM 页标 `93LC56BT` -> POPULATED（与实测贴片、bcu 写入 SN E10092 一致）。
无硬件单元测试见 `scripts/test_schematic_eeprom_check.py`。

多板通过 `lsftdi` 和工具帮助选实际设备 `-id=`。注意板上通常有两颗不同的 EEPROM：bcu `eeprom -r/-w` 操作的是 **FT4232H 桥的 USB 配置 EEPROM**（决定串口序列号/接口区分），与 U-Boot 读的**板载 I2C board-ID EEPROM** 是不同器件；bcu 这里不读后者。


## 空 EEPROM 板卡：先写身份，再拔插（串口接入的通用前置）

这是所有用板载 FTDI 桥的 EVK 的通用步骤，不是某块板的特例。串口技能的
`doctor` 报 blank/degraded、或"读不到串口/四口塌到 if00"时，都走这里。

新板 / 白片 EVK 的板载 FT4232H EEPROM 可能是空的。表现（实测 imx8mpevk）：
`eeprom -r -board=<任意名>` 会先回显 `board model is <任意名>`（仅回显参数，见上），
随后报 `Registered FTDI EEPROM on board` + `Invalid EEPROM context, use -w option
to write the default values.`；`eeprom -r -auto` 遍历所有板型全部 `Invalid EEPROM
context` 并 `Can't auto recognize the board`；`get_boot_mode` 报 `remote_en is
disabled`；串口侧 pyserial 只读到裸序列号（如 `5`）、四个口塌到 if00 无法区分角色。
注意"能显示板型"是假象，那是命令行参数回显，不代表读到了身份。



确认板型后（`lsboard` 里的确切名字），一次性写入默认身份：

```powershell
& $bcuExe eeprom -w -board=<实际model>   # 例 imx93evk14
```

写成功会打印 `... default values to FTDI EEPROM successfully` 和
`FTDI EEPROM SN / Board Info / SoC Info`。**写完必须拔插一次调试 USB 线**（或在设备
管理器禁用/启用），Windows 才会用新序列号重新枚举；这时四个口才带 A/B/C/D 尾字母，
串口工具原生就能区分 if00-if03。实测 imx93evk14：写入后 SN 变为 `E10092`，四口
`E10092A..D -> if00..if03`。写 EEPROM 需要独占 FTDI，先关掉占用串口的捕获/终端再执行。
`eeprom -w` 只写工具内置默认身份，不动 boot fuse。

## 常用独立命令

`<实际model>` / `<mode>` 先换成当前板的真实参数，支持的模式用 `lsbootmode` 查。

```text
bcu.exe eeprom -r -board=<实际model>
bcu.exe lsbootmode -board=<实际model>
bcu.exe reset <mode> -board=<实际model>
bcu.exe get_boot_mode -board=<实际model>
bcu.exe onoff -hold=500 -board=<实际model>
```

i.MX943 B1 历史板的 reset 示例为 `reset sd -board=imx943evk19b1`；USB 下载模式为 `reset usb -board=imx943evk19b1`。模式与任务目标对应后再执行。
需要 GPIO 时先查工具 `help` / `lsgpio` 及板级原理图。读 EEPROM 不需要写入或擦除身份信息。

## 串口与收尾

- 要抓完整启动：先启动串口捕获，看到 `ALL PORTS READY`，再复位，复位时捕获仍须保持运行。
- 历史 i.MX943 B1 的 BCU 使用 if01，日志在 if02/if03，可配合捕获；其他板按自身 profile/实测确定。抓取通道与板控冲突时选物理复位等合适方式。
- `reset` 默认结束会 deinit。用过 `init`、`set_boot_mode` 或 `-keep` 时，工作结束执行 `deinit -board=<model>`，再用 `get_boot_mode` 确认控制权交还拨码开关。
- 具体板控前提和拨码要求看 profile；历史 B1 的 SW7-1 为 OFF，不能套到 A0 板卡。

首次迁移可执行本目录 `selfcheck.cmd`，仅检查工具能运行。板上日志与运行情况仍需现场确认。
