# Windows BCU 包

本机 `bin/bcu.exe` 版本为 `bcu_1.1.128-0-ge7027dc`。
Windows 需要目标机器可用的 FTDI 驱动、调试 USB 连接。命令见 [USAGE.md](USAGE.md)。

- `bin/bcu.exe`：工具本体。
- `selfcheck.cmd`：无板 version / lsboard 检查。
- `profiles/imx943evk19b1/README.md`：Windows 板卡历史实测记录。
- `bin/fetch-bcu.cmd`：可选下载脚本，缺少工具或需更换版本时使用。

第三方来源：[NXP BCU](https://github.com/nxp-imx/bcu)。已有工具可正常使用时无需更新；升级后核对版本及板型支持。
可执行文件不随 Git 仓库发布，缺失时须另行取得；安装后核对实际版本。

历史 profile 中的“本机”指原验证电脑，并不代表新目标电脑。i.MX95 / i.MX93 的具体板型仍待现场确认。
