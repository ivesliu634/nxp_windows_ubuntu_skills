# Windows 串口工具

Windows 串口工具，需要 Python 3.10+、pyserial、PyYAML 和目标机可用的串口驱动。
在此工具目录安装依赖：`python -m pip install -r requirements.txt`。
操作入口见 [USAGE.md](USAGE.md)；参数用脚本 `--help` 查询；profile 字段详见 [tool-design.md](reference/tool-design.md)。

capture-set 等各读取线程完成首次定时 read 后才报告 READY；自检导入失败会返回失败。

profile 保留原来源与验证状态：B1 部分角色有历史 Windows 证据，95/93 Windows 映射待确认，8DXL 为附带历史参考。
这里的 verified 指原 profile 记录过的板卡/环境，并不保证新电脑连接的实物相同。
