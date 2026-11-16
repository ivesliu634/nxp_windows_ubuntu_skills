# i.MX93 14x14 LPDDR4x EVK Serial Profile (Windows)

> 迁移自 Ubuntu 侧 Linux serial-console profile（2026-07-24 在 Linux 上 verified）。接口布局、
> role 分配照搬；**Windows 上的 COM 枚举与 role 映射尚未实测**，本地 serial.yaml 标 `partial`、
> 各口 status=unknown，抓过一次启动 session 再升 verified。

## Onboard FT4232H 映射

| 顺序 | Interface | serial 尾字母 | 默认 role | Linux 已验证输出 |
|---|---|---|---|---|
| 第 1 个 COM | `if00` | A | `first-com` | 无默认运行日志角色 |
| 第 2 个 COM | `if01` | B | `second-com` | BCU 板控，无默认运行日志 |
| 第 3 个 COM | `if02` | C | `a-core` | SPL、U-Boot、Linux |
| 第 4 个 COM | `if03` | D | `m33` | M33 |

默认同时捕获 `a-core` 和 `m33`，参数 `115200 8N1`。COM 号只作现场兜底提示，工具用
`VID:PID`(0403:6011) + 基础序列号 + 尾字母(A/B/C/D) 定位接口。

## BCU 影响

BCU 板控固定用 FT4232H channel 1 = `if01`。Linux 上实测 `get_boot_mode`/reset 退出后可能
留下未绑定的 `if01`（不访问板卡的 `bcu version` 不影响绑定）。这不会移除 `if02` 的 a-core
或 `if03` 的 m33 日志，所以可在允许的 BCU reset 流程里先抓这两路。BCU 退出后恢复 if01：

```bat
python serial_console.py recover --board imx93evk14
python serial_console.py probe --board imx93evk14
```

Windows 不能命令行重绑驱动，if01 掉了就关掉 BCU 后重新插拔适配器再 `probe`。
reset 是否允许由板级执行规则决定，不由本工具/profile 自动决定。

## 证据

- 上游 Linux verified 日期：2026-07-24；来源 case `2026-07-24-imx93evk14-serial-console-validation`
  （Linux 上 a-core 抓到 Linux login、M33 端口映射已确认）。
- 本地 Windows：待抓一次启动 session 后升 verified。
