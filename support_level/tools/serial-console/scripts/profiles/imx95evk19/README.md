# i.MX95 19x19 EVK Serial Profile (Windows)

> 迁移自 Ubuntu 侧 Linux serial-console profile（在 Linux 上就是 `partial`）。接口布局照搬；
> **Windows 上的 COM 枚举与 role 映射尚未实测**，各口 status=unknown，抓过一次启动 session
> 再升 verified。`imx95evk19` 是 19x19 封装（区别于 15x15 的 `imx95evk15`）。

## 当前映射

| 顺序 | Interface | serial 尾字母 | 默认 role | Linux 状态 |
|---|---|---|---|---|
| 第 1 个 COM | `if00` | A | `first-runtime` | 已验证（Linux）|
| 第 2 个 COM | `if01` | B | `second-com` | **role 未确认，不猜测** |
| 第 3 个 COM | `if02` | C | `a55-rtos` | 已验证（Linux）|
| 第 4 个 COM | `if03` | D | `cm33-smfw` | 已验证（Linux）|

参数 `115200 8N1`。**未确认 `if01` 前，不得自动给它分配 Linux / M 核 / 系统管理固件 role。**
COM 号只作现场兜底提示，工具用 `VID:PID`(0403:6011) + 基础序列号 + 尾字母(A/B/C/D) 定位。

## BCU UART Mux 风险

`bcu reset ... -keep` 可能把 `ft_fta_sel` 留在 HIGH，从而抑制 `first-runtime`(if00) 输出。
出现第一路假静音时，先按板级规则恢复 `ft_fta_sel`，**不要**直接判断对应固件/系统没启动。

## 常用命令

```bat
python serial_console.py probe --board imx95evk19
python serial_console.py capture-set --board imx95evk19 --log-dir logs --name boot --timeout 120
```

## 证据

- 上游 Linux profile 就是 partial：first-runtime / a55-rtos / cm33-smfw 已验证，if01 role 未确认。
- 本地 Windows：待抓一次启动 session，确认 COM 映射与 if01 role 后再升 verified。
