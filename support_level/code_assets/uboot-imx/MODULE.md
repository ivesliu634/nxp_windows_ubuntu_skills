# uboot-imx

来源：[NXP U-Boot](https://github.com/nxp-imx/uboot-imx)，clone URL 为 `https://github.com/nxp-imx/uboot-imx.git`。
Ubuntu 资料记录过 `lf_v2025.04` / `lf-6.18.2-1.0.0`；按任务 release 选 ref。

查代码：`configs/`、`board/freescale/`、`arch/arm/dts/`、`include/configs/`；部分版本也从 `dts/upstream/` 取 DTS。
配置线索：`imx943_evk_defconfig`、`imx95_19x19_evk_defconfig`、`imx95_15x15_evk_defconfig`、`imx93_14x14_evk_defconfig`。不能由 SoC 名直接推定板型配置。

需要编译时，在工作副本分开执行：

```bash
export CROSS_COMPILE=/absolute/toolchain/bin/aarch64-none-linux-gnu-
make O=build <实际defconfig>
make O=build -j4
```

典型输出 `build/u-boot.bin`、`build/u-boot-nodtb.bin`、`build/u-boot.dtb`、`build/spl/u-boot-spl.bin`，取决于配置。
若软件线选中 RTE U-Boot，转 [real-time-edge-uboot](../real-time-edge-uboot/MODULE.md)。构建 U-Boot 本身完成后，是否打包 flash.bin 由用户目标决定。
