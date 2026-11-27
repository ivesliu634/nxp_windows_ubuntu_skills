# Windows 工具

| 工具 | 入口 | 操作说明 |
|---|---|---|
| BCU | `bcu\bin\bcu.exe` | [USAGE](bcu/USAGE.md) |
| 串口 | `serial-console\scripts\serial_console.py` | [USAGE](serial-console/USAGE.md) |
| UUU | `uuu\uuu.exe` | [USAGE](uuu/USAGE.md) |
| imx-rm | `imx-rm\imx_rm.py` | [USAGE](imx-rm/USAGE.md) |
| cfimager | `cfimager.exe` | 仅用户明确要求且确认目标盘后使用，先查程序帮助 |

Windows 不使用 Linux sudo、udev、sysfs 或 `/dev/ttyUSB*` 操作硬件。
具体参数以本目录中的 Windows 工具说明及帮助为准。

`compile-tool` 等构建工具只在 server 使用，不能在本目录假装已有可执行文件。
它们的 Windows 维护/部署源见 [server](../../server/README.md)，不是本地执行工具。
RM 章节定位、范围搜索和摘录使用 Windows [imx-rm](imx-rm/USAGE.md)；
先定位再读取有界页面，图表和复杂版面仍以原始 PDF 为准。
PDF、生成索引和摘录缓存不随工具发布。
