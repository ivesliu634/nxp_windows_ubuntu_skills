# Windows BCU 包

本版已包含从用户 `vero_release` 复制的 `bin/bcu.exe`，版本 `bcu_1.1.128-0-ge7027dc`。
Windows 需要目标机器可用的 FTDI 驱动、调试 USB 连接。命令见 [USAGE.md](USAGE.md)。

- `bin/bcu.exe`：工具本体。
- `selfcheck.cmd`：无板 version / lsboard 检查。
- `profiles/imx943evk19b1/README.md`：原 Windows 板卡历史实测记录。
- `bin/fetch-bcu.cmd`：原包的可选下载脚本，仅需更换版本时使用。

第三方来源：[NXP BCU](https://github.com/nxp-imx/bcu)。已有工具可正常使用时无需更新；升级后核对版本及板型支持。
本目录 `.gitignore` 沿用原包，会忽略 EXE；本次 ZIP 显式包含 EXE。以后通过 Git 分发时需要另行携带或取得该可执行文件。

历史 profile 中的“本机”指原验证电脑，并不代表新目标电脑。i.MX95 / i.MX93 的具体板型仍待现场确认。
