# meta-real-time-edge

来源：[Real-Time Edge Yocto layer](https://github.com/nxp-real-time-edge-sw/meta-real-time-edge)，clone URL 为 `https://github.com/nxp-real-time-edge-sw/meta-real-time-edge.git`。

常查：

- `conf/layer.conf`、`conf/distro/`、`conf/machine/`：layer、发行版和机器配置。
- `recipes-nxp/images/`、`recipes-nxp/packagegroups/`：镜像和包组合。
- `dynamic-layers/imx-layer/recipes-bsp/`：ATF、SMFW、U-Boot 的 patch 和 bbappend 线索。

这些位置来自原 Ubuntu 说明，在当前 ref 中检查是否存在。查 `SRC_URI`、`SRCREV` 和分支变量定位组件来源；每个 patch 跟随自己的 recipe 使用。
它是 layer，不是可在仓库根直接 make 的单一固件。需要完整 Yocto 构建时，按所选 RTE 的 README 设置 manifest/layers 和环境；本版不假定固定 distro/machine 或后台构建流程。
