# Windows 工具

| 工具 | 入口 | 操作说明 |
|---|---|---|
| BCU | `bcu\bin\bcu.exe` | [USAGE](bcu/USAGE.md) |
| 串口 | `serial-console\scripts\serial_console.py` | [USAGE](serial-console/USAGE.md) |
| UUU | `uuu\uuu.exe` | [USAGE](uuu/USAGE.md) |
| cfimager | `cfimager.exe` | 仅用户明确要求且确认目标盘后使用，先查程序帮助 |

BCU 与串口工具保留 Vero 原实现和 profile，整体迁入本目录。
Windows 不使用 Linux sudo、udev、sysfs 或 `/dev/ttyUSB*` 操作硬件。
具体参数以本目录中的 Windows 工具说明及帮助为准。

`compile-tool` 等构建工具只在 server 使用，不能在本目录假装已有可执行文件。
它们的 Windows 维护/部署源见 [server](../../server/README.md)，不是本地执行工具。
RM 章节工具的参考说明见 [上游 imx-rm](https://github.com/lbwlele-bot/nxp_ivesliu_skill/tree/02c4fbf16ee80a5c1732a080facacc855a588231/support_level/tools/imx-rm)；
该参考目录未包含程序入口，当前未部署 Windows 版本，查询时明确这一限制并使用原始本地 PDF。
