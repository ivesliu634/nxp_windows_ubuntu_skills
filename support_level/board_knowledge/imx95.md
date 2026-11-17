# i.MX95

实物板型尚未确定。现有 [串口参考](../tools/serial-console/scripts/profiles/imx95evk19/README.md) 针对 19x19 EVK，Windows role 状态均待验证；不覆盖 15x15、FRDM 等板型。
原理图放 `SoC_material/imx95/hardware/<实际板型>/<revision>/`，确认前不按 19x19 给整块实物定型。

从 EEPROM / 丝印确认板型、板卡 revision；SoC revision 和 DDR 再分别核对。随后选择 BCU 型号与 serial profile。
历史经验：BCU `-keep` 可能让 `ft_fta_sel` 保持 HIGH，导致 first-runtime(if00) 静音。遇到空日志先检查控制状态和 mux，不直接认定固件没启动。具体恢复按已确认板型的控制定义操作，不盲写 GPIO。
RTE 与普通 LF 的源码/配置差异经 `myserver` 查 server 的
`support_level/software_stacks/rte.md`；其 Git 维护源见
[RTE 软件线说明](../../server/support_level/software_stacks/rte.md)。
