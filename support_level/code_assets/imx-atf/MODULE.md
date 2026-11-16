# imx-atf

来源：[NXP ATF](https://github.com/nxp-imx/imx-atf)，clone URL 为 `https://github.com/nxp-imx/imx-atf.git`。
Ubuntu 资料记录过 `lf_v2.12` / `lf-6.18.2-1.0.0`。
查平台实现从 `plat/imx/` 和仓库 README 开始。i.MX943 的平台名是线索 `imx94`，i.MX95 为 `imx95`；在所选源码确认。

工作副本构建形态：

```bash
export CROSS_COMPILE=/absolute/toolchain/bin/aarch64-none-linux-gnu-
unset LDFLAGS AS
make PLAT=<实际平台> bl31
```

所选软件线需要 OP-TEE 时，构建命令加 `SPD=opteed`。RTE patch 只取 ATF 对应部分。
典型输出 `build/<plat>/release/bl31.bin`。构建前清除 `LDFLAGS` / `AS` 来自原工作区排除宿主环境干扰的经验，局限于当前 shell。
