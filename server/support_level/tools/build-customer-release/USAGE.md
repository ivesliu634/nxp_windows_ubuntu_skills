# server 客户包校验器

此处只部署校验脚本；AI 的 `build-customer-release` skill、模板和主 case 在 Windows。
脚本沿用 Windows skill 下的 `scripts/validate_release.py`，其部署副本在 Windows
工作流的 `server/support_level/tools/build-customer-release/scripts`，不需要远端 AI 工作区。

在 Linux shell 中，用本次真实路径替换下面的占位参数：

```bash
python3 <server-support-level>/tools/build-customer-release/scripts/validate_release.py \
  <server-release-dir> --spec <server-case>/records/release/customer-release.yaml
```

依赖 Python 和 PyYAML。spec、源码 baseline、补丁和 release 输入均使用 server 路径；
需要的内容通过 SSH/SCP 准备，不把 Windows 路径直接传入校验器。
补丁应用和 shell 脚本语义检查在 server 完成，不能以 Windows 的静态检查替代。
release 内容定稿后先生成覆盖全部文件（除自身）的 `SHA256SUMS`，再验证目录；
内容改变必须重新生成。通过后打包，再校验压缩包，不把缺失 checksum 当作通过。
校验日志和所需 release 产物按需取回 Windows 主 case，并核对校验和。
仅查看帮助可执行同一脚本的 `--help`，不会编译或操作板子。
