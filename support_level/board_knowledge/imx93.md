# i.MX93

实物板型尚未确定。现有 [串口参考](../tools/serial-console/scripts/profiles/imx93evk14/README.md) 针对 14x14 EVK；Windows role 状态待验证。
原理图放 `SoC_material/imx93/hardware/<实际板型>/<revision>/`。
先根据 EEPROM / 丝印核对板型，再选择 profile、BCU 型号与镜像。确认过的接口角色写回 profile，保留实际日志依据。

整盘 SD 映像写入与 boot 分区的文件更新分别处理。已有镜像文件名不能单独证明适合当前板和当前介质。
M33 SDK、Linux 驱动、U-Boot 分别去对应模块说明，源码在 server 上查。
