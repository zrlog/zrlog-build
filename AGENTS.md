# AGENTS.md

本仓库维护插件共用构建脚本和 Native 制品处理客户端。先读 `README.md` 与 `action.yml`。
插件构建脚本在 `scripts/plugin/`，制品处理命令在 `scripts/process-artifact.sh`，回归测试在 `tests/`。

- Action 和命令行共用同一实现。保持现有输入、环境变量与四个位置参数兼容。
- 从插件仓库根目录调用共享脚本，沿用插件的 POM、制品名称、版本和校验文件。发布触发条件、构建平台和发布目标由调用仓库配置。
- 下载结果必须同时通过 SHA-256 和大小校验，成功后才能替换输入文件并确认服务端清理。
- 上传、轮询、下载和校验失败必须保留原文件；替换成功后的服务端清理失败保持非致命。
- JSON 响应通过临时文件接收，不能让 curl 重试把失败响应与成功 JSON 串接。
- 不写入服务 token，不在日志输出凭据，不为连通性检查绕过 TLS 验证。
- 默认验证使用本机 HTTP 夹具；HTTPS 探测只由手动工作流执行。
- 修改客户端后运行 `bash -n scripts/process-artifact.sh` 和
  `python3 -m unittest discover -s tests -v`；修改工作流同时运行 actionlint。
- 消费者包括主工程 FaaS、plugin-core 的 Linux Native/FaaS 和 backup-sql-file 的
  Linux Native。消费者使用完整提交 SHA；更新时核对处理发生在最终摘要与组包之前。
