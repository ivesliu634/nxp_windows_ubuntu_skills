# linux-imx

来源：[NXP i.MX Linux](https://github.com/nxp-imx/linux-imx)，clone URL 为 `https://github.com/nxp-imx/linux-imx.git`。
Ubuntu 资料记录过 `lf-6.12.y` / `lf-6.12.49-2.2.0`；按任务 release 选 ref。RTE 内核另看 [real-time-edge-linux](../real-time-edge-linux/MODULE.md)。

查代码：`drivers/`、`Documentation/devicetree/bindings/`、`arch/arm64/boot/dts/freescale/`。
候选 DTS：`imx943-evk.dts`、`imx95-19x19-evk.dts`、`imx93-14x14-evk.dts`；先确认目标版本和板型。

需要编译时，在 server 的工作副本中逐步执行；prefix 必须替换：

```bash
export ARCH=arm64
export CROSS_COMPILE=/absolute/toolchain/bin/aarch64-none-linux-gnu-
make O=build imx_v8_defconfig
make O=build -j4 Image dtbs modules
```

只改 DTB 时可将构建目标换为 `freescale/<board>.dtb`。
输出：`build/arch/arm64/boot/Image`、`build/arch/arm64/boot/dts/freescale/`。
需要模块目录时再运行 `make O=build INSTALL_MOD_PATH="$PWD/modules-out" modules_install`。
