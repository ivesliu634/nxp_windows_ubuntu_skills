# Windows UUU

把已有 `uuu.exe` 放在这里，或在 [本机环境配置](../../../workspace/local/ENVIRONMENT.md)写明外部位置。本包未附带 UUU。
来源入口：[NXP mfgtools / UUU](https://github.com/nxp-imx/mfgtools)。

在 Windows PowerShell，设 `$uuuExe` 为实际绝对路径：

```powershell
& $uuuExe -h
& $uuuExe -lsusb
```

`-lsusb` 可查看下载 USB 枚举。FTDI 调试 USB 与 ROM 下载 USB 可能不同。
需要写入时先查该 release 随包的 `.uuu` 脚本、Release Notes 与工具帮助。命令应说明输入文件、写入哪个介质、是否覆盖整个盘。
`sd_all` / `emmc_all` 这类整盘动作与启动镜像更新、FAT 分区文件更新不同；不要把任意 `.bin` 当成整盘镜像。

UUU 是普通原生命令，不需要额外桥接工具。涉及写入的具体参数在现场确定，避免给未知板型一个能直接误烧的默认命令。
完成后按本次目标核对串口输出。ROM 下载阶段枚举成功不等于 U-Boot fastboot 或 Linux 已启动。
