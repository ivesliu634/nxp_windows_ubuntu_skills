# i.MX943 19x19 EVK Serial Profile (Windows)

目标板：**EVK 板卡 REV B1** + i.MX943 A0 芯片（SoC revision 1.0）+ LPDDR4。

> 命名说明（2026-08-17 统一为 b1）：`imx943evk19` 后缀的 `a0/b1` 指的是 **EVK 板卡的
> revision**，不是芯片 silicon rev。本机是**板卡 B1**（bcu EEPROM 存 B1），芯片 silicon
> 是 A0。所以本 profile 按板卡命名为 `imx943evk19b1`，串口工具和 bcu **统一都用 b1**：
> - 串口工具（本工具）：`--board imx943evk19b1`
> - bcu 板控/复位：`-board=imx943evk19b1`
>
> （历史：本 profile 早期沿用上游 Linux 的 `imx943evk19a0` 名，导致 serial 用 a0、bcu 用
> b1 两个名字不一致；2026-08-17 统一改为 b1，消除这个坑。bcu 用 a0 会报
> `board rev ... MISMATCH` 且不动作。）

## 当前接口语义（2026-11-10 用户确认）

同一块 943 的四口通常按 COM 号从小到大对应：
`if00=CM33S`、`if01=空/BCU`、`if02=U-Boot/Linux`、`if03=OEI/SMFW`。
工具 role 分别为 `cm33s`、`second-com`、`a-core`、`sm`。
默认捕获三个日志口，不打开 BCU 保留口；CM33S 是否有输出取决于当前固件。
优先用 A/B/C/D 或注册表定位固定接口；缺口不重新编号，不跨适配器排序。
此处确认的是角色约定，不是新一次硬件验证。

## 历史 FT4232H 映射（2026-08-11 Windows 实测）

| 顺序 | Interface | serial 尾字母 | 本次 COM（易变） | 默认 role | 实测结果 |
|---|---|---|---|---|---|
| 第 1 个 COM | `if00` | A | COM153 | `first-com` | 0 字节（无默认日志角色）|
| 第 2 个 COM | `if01` | B | COM154 | `second-com` | 0 字节（BCU 板控口）|
| 第 3 个 COM | `if02` | C | COM155 | `a-core` | **verified**：完整启动到 login + 双向交互 |
| 第 4 个 COM | `if03` | D | COM156 | `sm` | **verified**：先开口再 reset，抓到 DDR OEI + "Hello from SM" banner |


当时同时捕获 `a-core` 和 `sm`，参数 `115200 8N1`。Linux shell 和 U-Boot
操作默认使用 `a-core`，不要把 `if03` 当作 Linux console。

COM 口号是易变的、仅作兜底提示；工具用 `VID:PID`(0403:6011) + 基础序列号(本板 `0C1819`)
定位适配器，用序列号尾字母（A/B/C/D）定位接口，不硬编码 COM 号或完整序列号。

## 实测证据（2026-08-11，本机 Windows）

用 bcu 复位从 SD 启动（`bcu reset sd -board=imx943evk19b1`，bcu 用完自动 deinit 交还拨码），
再用本工具 `capture-set` 四口同抓：

- **a-core (if02/COM155)：verified**。抓到完整启动：
  `U-Boot SPL -> BL31 -> U-Boot 2025.04 -> Starting kernel -> Linux 6.18.2-rt3 ->
  NXP Real-time Edge Distro 3.4 -> login`。`send` 登录后跑命令确认双向可用：
  `uname -r=6.18.2-rt3-1.0.0-1.0.0`、`soc_id=i.MX943`、`revision=1.0`（即 SoC A0）。
- **sm (if03/COM156)：verified**（2026-08-20 更新）。**先起 capture-set、再 `bcu reset sd`**，
  抓到 SM 口 banner：`DDR OEI: ... SOC MIMX94(A0), Board mx943lp4-19` +
  `Hello from SM (Build ...)` + `Press key to enter monitor mode.`。
  订正旧结论：此前记录的"sm 0 字节 / warm reboot 不重启 SM 所以不打 banner"是**采集时机造成
  的假象**——旧做法是"先 reset 后抓"，复位瞬间喷出的 OEI/SM banner 早已过去才开口。**bcu 只
  占 if01，sm 在 if03，先开口再 reset 完全不冲突**，banner 就抓到了，不需要冷上电。
- **当时命名 first-com / second-com：0 字节**。空日志不能否认 if00 的 CM33S 角色。

板型认定证据（`bcu eeprom -r`）：`Board Info: NXP i.MX943 19x19 EVK Board Rev B1` /
`SoC Info: i.MX943 Rev A0` / `FTDI EEPROM SN: 0C1819`——直接读板载 EEPROM 认板，别在 lsboard
列表里靠序列号猜。

profile 保持 `partial`：a-core、sm 有历史实测，CM33S 尚未重新验证；if01 保留给 BCU。

## 常用命令

```bat
python serial_console.py probe --board imx943evk19b1
python serial_console.py capture-set --board imx943evk19b1 --log-dir logs --name boot --timeout 120
python serial_console.py uboot-stop --board imx943evk19b1 --role a-core --timeout 15
python serial_console.py shell --board imx943evk19b1 --role a-core
```

触发一次启动（本工具自身不复位板子）：
- bcu 复位到 SD：`bcu.exe reset sd -board=imx943evk19b1`（用完会自动交还 boot mode 给拨码）。
- 或已进 Linux 时从 a-core 发 `reboot`。要抓复位瞬间的 SM/OEI banner，务必**先开 capture-set
  再触发**（见文末 BCU 影响一节）。

## Profile 边界

- 当前未连接外部 application M-core UART 转接板；那些 UART 不属于主板四口 profile，
  不能根据主板四个 COM 的内容推测其 role。
- 板 revision（B1 板卡 / A0 芯片）必须由 BCU EEPROM 等现场证据确认，PCB 颜色不能替代识别。
- 本 profile 只适用于这块 i.MX943 EVK，不得传播到其它 SoC 或 EVK。

## BCU 影响（Windows）

BCU 实际板控访问使用 FT4232H channel 1，即 `if01`，退出后该 COM 口可能掉线。
Windows 上无法命令行重绑驱动，BCU 操作结束后：

```bat
python serial_console.py recover --board imx943evk19b1
```

`recover` 只报告缺失接口——若 if01 掉了，关闭 BCU 后重新插拔适配器（或在设备管理器
禁用/启用）再 `probe`。串口工具本身不 reset 板子、不改 boot mode。

> bcu 与串口共用同一颗 FT4232H，但**按 channel 独立**：bcu 只占 if01，串口抓 a-core(if02)/
> sm(if03) 不受影响。所以看正常启动 log 用**通用姿势"先开串口捕获、等 ALL PORTS READY、
> 再 bcu reset"**，连复位瞬间的 OEI/SM banner 都能抓到（2026-08-20 实测）。仅当串口要抓 if01
> 时才需先 reset 再抓。看 uuu 烧写期 log 同样"先开串口捕获、再跑 uuu"（uuu 走 USB 下载口不占 FTDI）。

## 参考

- 上游 Linux verified profile（同一颗板载 FT4232H）：case `2026-07-24-imx943evk19a0-serial-console-validation`（上游按 a0 板卡命名）。
- 本次 Windows 验证 case：`2026-08-11-imx943evk19a0-serial-win-validation`。
