<div align="center">

# Hermes Alive

**面向 Hermes 与微信网关的主动陪伴能力。**

在不修改 Hermes Core 和微信适配器的前提下，提供上下文感知、主动搭话、外部发现、
兴趣学习、真实模型归属和可回滚的生命周期管理。

[English](README.md) · [架构](docs/ARCHITECTURE.md) · [测试与验收](docs/TESTING_AND_ACCEPTANCE.md)

</div>

## 安装后会有什么变化

Hermes Alive 为 Hermes 增加主动交互层。安装后，Hermes 可以：

- 读取有限且新鲜的上下文，避免打断正在进行的任务；
- 在旧话题失去价值后，基于真实的新内容转向新话题；
- 一次采集多个 Discovery 候选，并逐次分享不同的未投递候选；
- 根据语义需要、关系状态和上下文选择表达方式与气泡数量；
- 在投递前拦截重复、无证据或带有施压倾向的主动草稿；
- 在消息 footer 中保留真实路由模型；
- 将可替换源码与用户学习、运行状态分开保存。

Circadian 当前用于学习和观测，保持 `shadow`。固定静默时间仍然具有实际约束力，
动态睡眠/静默策略尚不宣称为生产强制模式。

## 快速开始

在完整仓库中进入技能目录：

```bash
cd skills/hermes-alive

bash scripts/install.sh

scripts/hermes-alive-lifecycle configure \
  --non-interactive \
  --enable \
  --skip-weather

bash scripts/verify.sh
```

成功时会出现：

```text
HERMES_ALIVE_LIFECYCLE_INSTALL_OK
HERMES_ALIVE_ZERO_TOUCH_CONFIG_OK
HERMES_ALIVE_LIFECYCLE_VERIFY_RESULT=PASS
```

Provider 和模型继续由 Hermes 管理。Hermes Alive 只检查是否可用，不会开启第二套
Provider 问卷，也不会保存 API Key。

## 首次运行

非交互式配置会：

1. 自动识别本地时区；
2. 使用默认静默时间 `23:00`–`08:00`；
3. 启用实时主动质量治理；
4. 将 Circadian 保持为 `shadow`；
5. 使用 `--skip-weather` 时保持天气关闭；
6. 将非敏感托管配置写入共享状态目录。

天气是可选能力。只有明确允许网络位置发现时，Hermes 才可能在原聊天中自然确认一次
区域信息；用户可以确认、更正或拒绝。安装过程不会在终端等待回答。

## 主要能力

### 基于上下文决定是否主动说话

Hermes Alive 会在生成前和每次发送前检查用户活动、上下文新鲜度、冷却时间、
打断策略和投递证据。气泡数量由独立语义动作规划，范围为 1–5 条，并非固定数量。

### Discovery 缓存轮换与话题去重

一次采集可以缓存多个排序后的候选。每次主动分享只消费一个当前可投递候选；
后续 tick 可以复用同一缓存，但会选择另一个未投递候选。已经投递、正在保留或
属于重复话题的候选会被抑制。只有可验证的实质更新指纹发生变化时，旧话题才可重新进入。

### 实时质量治理

生命周期托管配置默认将主动质量治理设为 `enforce`。它可以阻止重复开头、语义近似重复、
缺少结构化证据的任务状态、同一未回应事件的重复情绪，以及虚构机器人位置或身体感受的
天气表述。`off` 与 `shadow` 仍是明确可选模式。

### 兴趣和表达风格学习

兴趣变化必须可归因、可逆。明确反馈强于弱对话信号，不推断敏感身份属性。
表达风格可以逐步适应，但始终受安全、上下文和投递约束。

### 真实模型归属

模型生成的主动消息会携带真实路由模型信息。生命周期、控制和确定性系统消息使用
Hermes 系统元数据。

## 环境要求

Hermes Alive 需要：

- 已安装并可用的 Hermes；
- 已配置的 Provider；
- 可写的 `HERMES_HOME`；
- 可加载 gateway hook 的运行环境。

Docker 不是必需条件。容器环境应持久化挂载 `HERMES_HOME`；普通 Linux 或 WSL
使用本地文件系统持久化即可。

## 路径与数据

生命周期默认使用：

```text
$HERMES_HOME/skills/hermes/hermes-alive
$HERMES_HOME/hooks/hermes-alive
$HERMES_HOME/hermes_alive_shared
```

共享目录必须位于 `HERMES_HOME` 内部。

持久化内容可能包括托管配置、有限上下文、兴趣与表达档案、Discovery 证据、
话题投递哈希、主动日志和 Circadian 观测状态。Provider 凭据仍保存在 Hermes 配置中。

详见[数据与隐私](docs/DATA_AND_PRIVACY.md)。

## 状态、验证与排障

在已安装技能目录执行：

```bash
scripts/hermes-alive-lifecycle status
bash scripts/verify.sh
python3 hooks/alive_control.py status
python3 scripts/logs.py --tail 20
```

需要暂时关闭或重新启用主动投递时：

```bash
python3 hooks/alive_control.py disable
python3 hooks/alive_control.py enable
```

不要通过直接修改运行时 JSON 来“清零”静默状态。未回应数量是互动证据，不是固定的
开关条件。应使用状态、日志和受控命令定位原因。

详见[主动静默排障](references/troubleshooting-silent-mode.md)。

## 卸载与数据保留

默认卸载会移除安装源码、active hook 和托管配置，但保留学习与运行状态：

```bash
bash scripts/uninstall.sh
```

彻底删除 Hermes Alive 所有共享状态：

```bash
bash scripts/uninstall.sh --purge
```

`purge` 具有破坏性。生产重启、生产源码或配置修改、真实消息发送仍然必须单独明确执行。

## 当前验收边界

当前源码已经通过隔离 hardening、完整回归、全新安装、幂等安装、容器重建持久化、
卸载、重装、purge 和零残留生命周期验收。后续发布路径见
[测试与验收](docs/TESTING_AND_ACCEPTANCE.md)，其中包括完整仓库 transport、
真实 GitHub URL 安装、备用微信 E2E 和受控生产验收。

## 深入文档

- [架构](docs/ARCHITECTURE.md)
- [运行策略](docs/RUNTIME_POLICIES.md)
- [生命周期与持久化](docs/LIFECYCLE_AND_PERSISTENCE.md)
- [数据与隐私](docs/DATA_AND_PRIVACY.md)
- [测试与验收](docs/TESTING_AND_ACCEPTANCE.md)
- [Discovery 开发](docs/DISCOVERY_DEVELOPMENT.md)
- [测试指南](tests/TESTING.md)

## License

见 [LICENSE](LICENSE)。
