# i.MX8DXL EVK Serial Profile (Windows)

> 迁移自 Ubuntu 侧 Linux serial-console profile（2026-07-24 在 Linux 上 verified，实物为
> B0 LPDDR4）。接口布局、role 分配照搬；**Windows 上的 COM 枚举与 role 映射尚未实测**，
> 所以本 profile 标 `partial`，各口 status=unknown，抓过一次启动 session 再升 verified。

## Onboard FT4232H 映射

| 顺序 | Interface | serial 尾字母 | 默认 role | Linux 已验证输出 |
|---|---|---|---|---|
| 第 1 个 COM | `if00` | A | `first-com` | 无默认运行日志角色 |
| 第 2 个 COM | `if01` | B | `m4` | M4 console |
| 第 3 个 COM | `if02` | C | `a-core` | SPL、U-Boot、Fastboot、Linux |
| 第 4 个 COM | `if03` | D | `scfw` | SCFW |

默认同时捕获 `m4`、`a-core`、`scfw`，参数 `115200 8N1`。interface 顺序是稳定身份；
COM 号只作现场兜底提示，工具用 `VID:PID`(0403:6011) + 基础序列号 + 尾字母(A/B/C/D) 定位。

## BCU channel 1 冲突（关键坑）

BCU 板控固定用 FT4232H channel 1 = `if01`，而 DXL 的 **M4 console 也是 if01**（同一个口）。
所以：
- **要抓 M4 早期日志时：绝不能跑 BCU，也不能用 BCU reset**（BCU 会占走 if01，M4 早期字节
  直接丢失，`--reconnect` 也找不回 BCU 占用期间已输出的字节）。用板上物理 RESET 键触发。
- **只抓 A-core + SCFW 时**：Linux 上 B0 LPDDR4 实物已验证，可在这两路 READY 后用 BCU reset。

### 需要 M4 早期日志（用物理 RESET，不用 BCU）
```bat
python serial_console.py recover --board imx8dxlevk
python serial_console.py probe --board imx8dxlevk
python serial_console.py capture-set --board imx8dxlevk --log-dir logs --name sd-boot --timeout 600 --prepare
```
看到 `ALL PORTS READY` 后由人手动按板上 RESET。

### 不需要 M4 早期日志（可配合 BCU reset）
```bat
python serial_console.py capture-set --board imx8dxlevk --role a-core --role scfw --log-dir logs --name bcu-reset --timeout 90 --prepare
```
看到 `ALL PORTS READY` 后，另开一条命令跑 bcu reset（bcu -board 名以 `bcu.exe lsboard` 为准）。

Linux 上 2026-07-24 连续 3 次普通 reset 均抓到 a-core(SPL/U-Boot/Linux 到 login) 和
scfw(SCFW banner)，两路 0 reconnect。该结果不证明 M4 早期日志完整，也不覆盖其它 revision。

## 主机侧注意事项

- BCU 退出后 `if01` 可能掉线；Windows 不能命令行重绑驱动，关掉 BCU 后重新插拔适配器
  （或设备管理器禁用/启用）再 `probe`。`recover` 只报告缺失接口。
- Linux 上 if00/if01 曾静默回落 9600，抓前 prepare；Windows 上留意乱码，必要时重开 115200。
- 串口静默不能单独证明板子/固件没运行。
- `--stop-modemmanager` 是 Linux 专属，Windows 上工具会 no-op（无此服务），可不管。

## 证据

- 上游 Linux verified 日期：2026-07-24；来源 case `2026-07-23-imx8dxl-power-mode-ocram-suspend`。
- BCU reset 串口范围 case：`2026-07-24-imx8dxl-bcu-reset-serial-scope`。
- 本地 Windows：2026-08-24 实测（Orange Box Rev A0 / SoC i.MX8DXL Rev A1）。
  BCU 与串口两条通道均正常：
  - `bcu.exe eeprom -r` 正常认板；`get_boot_mode` = boot from BOOT SWITCH；
    `bcu.exe reset sd` 全流程 OK（reset successfully，自动 deinit 交还拨码开关）。
  - 串口 a-core（第 3 个 COM）抓到完整 SD 启动 log（U-Boot 到 Linux login），48556 bytes，
    state=data。BCU 占 if01、串口抓 a-core 不冲突（铁律二），reset + capture 串起来即可。

## Windows 上 role 映射失效的坑（重要）

本板载 FT4232H 的 **FTDI 序列号是纯数字（实测 "7"），尾部没有 A/B/C/D 接口字母**，
所以 `serial_console.py` 的 ifNN 解析拿不到接口字母，`probe`/`--role` 全部把 4 个口
识别成 if00，`probe --board imx8dxlevk` 会报 `required role 'm4'/'a-core'/'scfw' is
missing` 且 profile_status=partial。**结论：这块板暂时不能用 `--role` 定位，必须用
`--device COMxx` 直连。**

按枚举顺序映射（实测 COM42-45 连号）：
- 第 1 个 COM = if00 = first-com
- 第 2 个 COM = if01 = m4（也是 BCU 板控占用的 channel）
- 第 3 个 COM = if02 = a-core（U-Boot / Linux console）
- 第 4 个 COM = if03 = scfw

用 `serial_console.py list` 看当前这颗适配器枚举出的 4 个 COM 号，按上面顺序对号入座。
COM 号易变，每次以 `list` 输出为准。
