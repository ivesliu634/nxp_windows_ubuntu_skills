# local

本目录集中保存当前机器的具体配置，不承载通用工程规则。
可公开的本机配置随 Git 提交；含私有信息的补充单独排除，不忽略整个目录。

## 目录内容

| 项目 | 用途 |
|---|---|
| [README.md](README.md) | 当前目录及各项用途的说明 |
| [ENVIRONMENT.md](ENVIRONMENT.md) | 当前机器可公开的路径、工具位置和资源状态说明 |
| `ENVIRONMENT.private.md`（可选，不发布） | 私有机器值和原有环境便笺；存在时与公开配置一并读取 |

模板与迁移方法位于 [porting](../docs/porting/README.md)。
凭据仍由凭据存储管理，不因本目录存在而把密码、token 或私钥写入配置。
