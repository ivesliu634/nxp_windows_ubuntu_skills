# i.MX943 19x19 EVK - bcu Board Profile

本目录是 **bcu 技能的板级 profile**（board control 专属）。凡是和这块具体板子相关的
bcu 事实——板型字符串、启动模式名、拨码开关前提、EEPROM 认板、FTDI channel 占用、实测
证据——都记在**这一个文件**里，不写进通用的 `SKILL.md`。串口口分配 / 抓 log 的板级细节在
`serial-console` 技能的同名 profile 里，两边各管一段，不重复。

- **profile id / bcu 板型参数**：`imx943evk19b1`（`-board=imx943evk19b1`）
- **板上 FTDI**：FT4232H，USB id `0403:6011`，4 个 channel；bcu 板控走 channel 1(`if01`)。

## 这块板是什么

- EVK **板卡 revision B1** + i.MX943 **芯片 silicon A0**（soc revision 1.0）+ LPDDR4。
- 后缀 `a0/b1` 指 **EVK 板卡 revision**，不是芯片 silicon rev。本机是板卡 B1（EEPROM 存 B1），
  芯片 silicon 是 A0。**bcu 必须用 `imx943evk19b1`**；用 a0 会报 `board rev ... MISMATCH`
  且不动作。

## 认板（别在 lsboard 列表里猜）

直接读板载 EEPROM：
```
bcu.exe eeprom -r -board=imx943evk19b1
```
本板输出：
```
Board Info: NXP i.MX943 19x19 EVK Board Rev B1
  SoC Info: i.MX943 Rev A0
 PMIC Info: MFS5600
FTDI EEPROM SN: 0C1819
```
> 注意：某些 bcu 命令（如 reset）会打印 "EEPROM is EMPTY"，那指的是 bcu 的**板卡配置区**
> 未写，**不代表** FTDI 的**板卡身份块**为空——身份块是有的，`eeprom -r` 能读出来。

## 前提

- bcu 复位时会提示 **"Please set SW7-1 as OFF"**——把拨码 **SW7-1 拨到 OFF** 才能正常板控。
- Windows 需装 FTDI 驱动，调试 USB 线接板子 FTDI/调试口。

## 支持的启动模式（`lsbootmode` 实测）

`a_usb a_emmc a_sd a_nor a_nand_2k a_nand_4k usb emmc sd nor nand_2k nand_4k`

## 常用操作

```bat
:: 烧写前：切 USB 下载模式 + 复位，再跑 uuu
bcu.exe reset usb -board=imx943evk19b1

:: 烧写后：切回 SD 启动 + 复位
bcu.exe reset sd -board=imx943evk19b1

:: 认板 / 读板卡 revision
bcu.exe eeprom -r -board=imx943evk19b1
```
`reset` 默认结尾自带 deinit（把 boot mode 交还拨码开关），不加 `-keep` 就已交还。

## 实测证据（2026-08-20，本机 Windows）

- **认板**：`eeprom -r` 直接报出 Board Rev B1 / SoC A0 / SN 0C1819（见上）。
- **reset sd**：`bcu reset sd -board=imx943evk19b1` 返回 `reset successfully`，并自动
  `deinitialized ... BOOTMODE returns to BOOT SWITCH.`（未加 `-keep`）。同时打印
  `Please set SW7-1 as OFF`。
- **FTDI channel（重要纠正）**：**bcu 板控只占 FT4232H 的 channel 1（if01）**。在 `bcu reset sd`
  **之前**先开着串口 capture-set 抓 a-core(if02) 和 sm(if03)，两个口**没有被踢掉**，bcu 照常
  `reset successfully`，两口都从最早 banner 抓到了启动（SM 的 `DDR OEI` / `Hello from SM`、
  A-core 的 U-Boot SPL）。

## 纠正的旧说法

之前的 bcu 文档有两处与本板实测不符，已在本 profile 更正：
1. ~~"bcu reset 会独占整颗 FT4232H，复位瞬间的 SM/OEI 早期 banner 抓不到"~~ —— 错。bcu 只占
   if01；串口抓 if02/if03 时先开口再 reset 完全能抓到早期 banner。抓启动 log 就用通用姿势
   **"先开串口捕获、再 bcu reset"**（详见 `serial-console` 技能）。
2. ~~"拨码 SW7-1 拨到 ON"~~ —— 错。bcu 在本板提示的是 **SW7-1 设为 OFF**。

## 协作边界

- 本 profile 只管**板控（bcu）** 侧的板子事实。串口口分配、role<->ifNN、抓 log 的证据在
  `serial-console` 技能的 `scripts/profiles/imx943evk19b1/`。
- 通用 bcu 用法、命令语义、铁律看 bcu 技能的 `SKILL.md`；本文件只放板子专属内容。
