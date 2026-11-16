# 板卡资料入口

| 优先级 | 实物信息 | 本版入口 |
|---|---|---|
| 1 | i.MX943 EVK B1 | [imx943-b1](imx943-b1.md) |
| 2 | i.MX95，具体板型待 EEPROM 核对 | [imx95](imx95.md) |
| 3 | i.MX93，具体板型待 EEPROM 核对 | [imx93](imx93.md) |

BCU profile 记板控事实，serial profile 记口映射；本目录连接硬件资料和这些记录。
新电脑的 COM、适配器序列号、驱动和实际板型需要现场识别。不要把原记录的“本机”理解为当前电脑。

## Ubuntu 历史板级参考

以下资料从原 Ubuntu 支撑层归并到 Windows，保留原板型和版本边界：

| 历史板型 | 参考入口 |
|---|---|
| i.MX8DXL EVK | [imx8dxlevk](imx8dxlevk/README.md) |
| i.MX93 14x14 EVK | [imx93evk14](imx93evk14/README.md) |
| i.MX943 19x19 A0 EVK | [imx943evk19a0](imx943evk19a0/README.md) |
| i.MX95 19x19 EVK | [imx95evk19](imx95evk19/README.md) |

其中的“本机”、镜像相对路径、命令和实测均属于原 Ubuntu 环境，
不是当前 Windows 部署清单，也不代表当前连接了该实物。
当前操作优先使用上方本版入口和 Windows 工具的 profile；历史 Linux 命令不直接执行。
A0 串口 profile 未部署到 Windows，不得以 B1 profile 替代。
