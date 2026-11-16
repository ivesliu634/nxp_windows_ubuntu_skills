# imx-mkimage

来源：[NXP mkimage](https://github.com/nxp-imx/imx-mkimage)，clone URL 为 `https://github.com/nxp-imx/imx-mkimage.git`。
Ubuntu 资料记录过 `lf-6.12.49_2.2.0` 分支、`lf-6.12.49-2.2.0` 版本。分支和 tag 拼写要实际核对。

先读所选 SoC 目录的 `soc.mak` 与 README，确认 recipe 的输入和文件名。i.MX943 在原资料中使用 `SOC=iMX94`。
常见输入包括 BL31、U-Boot / SPL、OEI、SMFW、DDR / AHAB firmware；OP-TEE 与 M 核 payload 是否加入由软件线和 recipe 决定。

仅用户需要打包时，在任务副本准备对应输入，再执行实际参数：

```bash
make SOC=<iMX94或iMX95等> REV=<实际芯片rev> \
  OEI=<YES或NO> LPDDR_TYPE=<实际类型> <实际recipe>
```

原资料的 `flash_a55` / `flash_all` 是 recipe 候选，不是可套全部板子的预设。`REV`、OEI 与 DDR 参数按当前 Makefile 和 release 确认。
`iMX94/flash_all` 在原版本需要 m33s/m70/m71 输入；`iMX95/flash_all` 需要 m7 输入。以当前 `soc.mak` 的实际依赖为准。
输出通常在 SoC 目录内为 `flash.bin`，用实际命令输出定位。这只是启动镜像，不等于整盘 `.wic`，也不证明板子已运行。
