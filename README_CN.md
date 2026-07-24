# Hermes Alive

Hermes Alive 是面向 Hermes 与微信网关的主动陪伴能力。本仓库包含完整技能源码、
生命周期工具、测试、文档、仓库元数据和便携 CI，不是单独的 `SKILL.md`。

- 英文技能说明：[`skills/hermes-alive/README.md`](skills/hermes-alive/README.md)
- 中文技能说明：[`skills/hermes-alive/README_CN.md`](skills/hermes-alive/README_CN.md)
- 架构：[`skills/hermes-alive/docs/ARCHITECTURE.md`](skills/hermes-alive/docs/ARCHITECTURE.md)
- 测试与验收：[`skills/hermes-alive/docs/TESTING_AND_ACCEPTANCE.md`](skills/hermes-alive/docs/TESTING_AND_ACCEPTANCE.md)

## 仓库结构

```text
skills/hermes-alive/       完整可安装技能
scripts/bootstrap.sh       仓库级安装、配置和验证入口
scripts/portable-ci.sh     公共 CI 与仓库完整性检查
scripts/verify-repository.py
metadata/                  版本、源码清单和发布阶段事实
.github/workflows/ci.yml   GitHub Actions 便携检查
```

## 安全安装

克隆完整仓库后执行：

```bash
bash scripts/bootstrap.sh
```

bootstrap 只调用技能生命周期，不修改 Hermes Core 或 `weixin.py`，不重启生产，
也不会发送真实微信消息。

默认配置会：

- 启用实时主动质量治理；
- 将 Circadian 保持为 `shadow`；
- 将动态 Sleep/Quiet 保持为 `observe_only`；
- 在位置未明确确认前关闭天气；
- 将共享状态保存到 `$HERMES_HOME/hermes_alive_shared`。

## 验证

```bash
bash scripts/portable-ci.sh
```

便携 CI 检查仓库结构、清单、文档链接、Python 编译和可使用确定性测试替身运行的
测试。完整 Hermes 运行时归属与生命周期验收仍是独立发布门禁。

## 当前边界

这是**仓库候选**，不是最终生产发布。后续仍需完成：

1. bare repository 与 Git bundle transport 验证；
2. 从真实 GitHub URL 在全新容器安装；
3. 经明确批准后使用备用微信做端到端验证；
4. 受控生产部署与回滚；
5. 重启、持久化和稳定运行观察。

Circadian 与动态 Sleep/Quiet 的 shadow 组件不能计为生产强制功能。

## License

[MIT](LICENSE)
