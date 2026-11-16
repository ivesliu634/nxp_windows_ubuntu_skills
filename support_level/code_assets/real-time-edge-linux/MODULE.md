# real-time-edge-linux

来源：[Real-Time Edge Linux](https://github.com/nxp-real-time-edge-sw/real-time-edge-linux)，clone URL 为 `https://github.com/nxp-real-time-edge-sw/real-time-edge-linux.git`。

用于 RTE 内核代码。先确定 RTE release，再由该 release 的文档或 Yocto recipe 找 ref、defconfig、补丁和 DTB。
查代码目录与 [linux-imx](../linux-imx/MODULE.md) 类似；构建也可使用普通 kernel make，但不能直接套通用 BSP 的配置。
用户只要求修改驱动时，定位并修改相应模块即可，无需同时准备 Yocto 镜像构建。
