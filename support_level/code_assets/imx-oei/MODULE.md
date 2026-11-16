# imx-oei

来源：[NXP OEI](https://github.com/nxp-imx/imx-oei)，clone URL 为 `https://github.com/nxp-imx/imx-oei.git`。
Ubuntu 资料记录过 `lf-6.18.2-1.0.0`。
查 DDR / TCM 配置从 `boards/` 开始，目录中的 LPDDR4/LPDDR5、板型、revision 要与实物相符。

使用 `arm-none-eabi` 工具链，按当前版本 README 设置 prefix/PATH。在工作副本中运行的模板：

```bash
export OEI_CROSS_COMPILE=/absolute/toolchain/bin/arm-none-eabi-
make board=<实际board> oei=ddr R=<silicon-rev> REV=<silicon-rev> DEBUG=1
```

R 与 REV 的传参来自原工作区的版本控制经验，两者填同一个实际芯片 revision，并查看当前 Makefile 对它们的定义。B1 板卡不能直接推导 silicon revision 为 B1。
候选 board 在原资料中包括 `mx95lp5`、`mx943lp5-19`；i.MX943 B1 历史实物为 LPDDR4，不能套 LPDDR5 配置。
典型输出 `build/<board>/ddr/oei-m33-ddr.bin`；如生成 `build_info.h`，可核对实际 board/revision。需要 TCM OEI 时按当前 README 改用 `oei=tcm`。
