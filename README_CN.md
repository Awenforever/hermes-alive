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
- 启用生产 Circadian `live` enforcement；
- 在 watcher pre-compose 边界启用动态 Sleep/Quiet live enforcement；
- 保持 isolated 双 key delivery-enforcement helper 仅用于测试；
- 在位置未明确确认前关闭天气；
- 将共享状态保存到 `$HERMES_HOME/hermes_alive_shared`。

## 验证

```bash
bash scripts/portable-ci.sh
```

便携 CI 检查仓库结构、清单、文档链接、Python 编译和可使用确定性测试替身运行的
测试。完整 Hermes 运行时归属与生命周期验收仍是独立发布门禁。

## 当前边界

这是 **v2.4.3-rc.1 仓库候选**，不是已经部署到生产的最终版本。
Circadian + Dynamic Sleep/Quiet production-enforcement 补丁已经在当前生产
镜像的全新隔离容器中通过精确基线验收，包括完整回归、默认规模 stress、
容器重建持久化、卸载/重装以及 purge/重装。

后续发布路径仍严格分离：

1. 验证本仓库候选与 Git bundle transport；
2. 只有在明确批准后才受控发布 `v2.4.3-rc.1`；
3. 从真实 GitHub URL 在全新隔离容器安装；
4. 经明确批准后使用备用微信做端到端验收；
5. 受控生产升级、回滚验证以及 restart/persistence/real-path 验收。

当前线上生产仍保持此前已经验收通过的 v2.4.2，直到上述升级链全部完成。

## License

[MIT](LICENSE)
