<div align="center">

# Hermes Alive

**Hermes Agent 的 gateway-native 主动陪伴能力。**

让 Hermes 拥有在场感、性格、记忆与作息，但不把每一次沉默都变成通知。

![version](https://img.shields.io/badge/version-2.8.12-blue)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB)
![Hermes](https://img.shields.io/badge/Hermes-gateway--native-6f42c1)
![license](https://img.shields.io/badge/license-MIT-green)

[English](README.md) · [安全说明](SECURITY.md) · [参与贡献](CONTRIBUTING.md)

</div>

---

## 这是什么

[Hermes Alive](https://github.com/Awenforever/hermes-alive) 是 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 的主动交互层。它随 Hermes Gateway 运行，理解近期微信上下文，并在时机和内容都合适时偶尔主动开口。

> **有在场感，但不制造回应义务。** Hermes 可以注意、记住、反应、沉默、入睡、醒来和主动搭话，但不应索取注意力。

Hermes Alive 复用 Hermes 已有的 Provider、模型配置、Gateway 和微信适配器，不替代 Hermes，也不维护第二套凭据系统。

## 核心能力

| 能力 | 作用 |
|---|---|
| 上下文感知 | Hermes 正在工作、仍需回复或对话仍新鲜时避免插话。 |
| 性格与关系状态 | 通过有边界、可逆的学习调整表达和主动倾向。 |
| 拟人作息 | 建模入睡、清醒、延迟入睡、睡眠债与恢复。 |
| 打断与质量策略 | 拦截重复、施压、无依据的任务判断和不安全草稿。 |
| Discovery | 在时事、合肥本地、人物文化、轻松趣闻、社区、技术与学术栏目间发现并轮换内容。 |
| 证据化编辑 | 先读取候选正文，再按事实、价值、时效、自然度、最少气泡和整体连贯性独立审查；不合格内容不会发送。 |
| Dream 记忆整合 | 可选地把高置信度对话证据转化为有边界的记忆更新。 |
| 可追踪投递 | 保留真实路由模型，并用统一 `tick_id` 串联决策。 |
| 安全生命周期 | 支持原子安装、验证、回滚、保留状态卸载和彻底清理。 |

## 工作方式

```text
Hermes Gateway
  → 近期上下文与活动检查
  → 作息与打断策略
  → 性格、记忆与可选 Discovery
  → 来源正文取证与模型生成
  → 独立编辑审查，必要时整稿重写
  → 质量与重复检查
  → 微信投递
```

系统和安全消息保持独立优先级，不按普通社交打扰处理。

## 快速开始

运行要求：

- 已安装且可用的 Hermes；
- Python 3.11 或更高版本；
- 已在 Hermes 中配置可用的 Provider 与模型；
- 可写的 `HERMES_HOME`，通常为 `/opt/data`。

### 让 Hermes 代为安装（推荐）

把本仓库链接发给 Hermes，并让它“阅读 `README_CN.md` 与
`skills/hermes-alive/SKILL.md` 后安装”。Hermes 会先在当前对话中确认接收
消息的会话、地区、作息与内容偏好，再把自然语言偏好转换成配置；用户不需要
填写 API Key、模型别名、时区字符串或经纬度。确认后才会启用并提示重启。

模型和凭据继承当前 Hermes 配置。仓库不会把作者设备上的 USTC 模型、微信
账号、代理或私人偏好写成公共默认值，因此新设备得到的是一致的功能和引导，
而不是错误复制另一位用户的身份与凭据。

### 命令行安装

从完整仓库安装：

```bash
git clone --depth 1 \
  https://github.com/Awenforever/hermes-alive.git \
  /tmp/hermes-alive

cd /tmp/hermes-alive
HERMES_HOME=/opt/data bash scripts/bootstrap.sh
```

bootstrap 会安装技能源码和 Gateway Hook、继承 Hermes 当前模型、写入非敏感
默认配置并执行验证，但不会重启 Gateway。命令行路径适合已有明确配置的运维者；
普通用户应优先采用上面的 Hermes 引导安装。确认结果后，请按当前部署方式正常
重启 Hermes。

## 配置与运行

```bash
export HERMES_HOME=/opt/data
LIFECYCLE="$HERMES_HOME/skills/hermes-alive/scripts/hermes-alive-lifecycle"

"$LIFECYCLE" configure
"$LIFECYCLE" verify
"$LIFECYCLE" status
```

Provider 凭据始终由 Hermes 管理。如果 Hermes 尚无可用模型，请运行：

```bash
/opt/hermes/.venv/bin/hermes setup model
```

无需卸载即可暂停或恢复主动投递：

```bash
python3 "$HERMES_HOME/hooks/hermes-alive/alive_control.py" disable
python3 "$HERMES_HOME/hooks/hermes-alive/alive_control.py" enable
python3 "$HERMES_HOME/hooks/hermes-alive/alive_control.py" status
```

## 数据与卸载

```text
$HERMES_HOME/skills/hermes-alive         已安装源码
$HERMES_HOME/hooks/hermes-alive          生效中的 Gateway Hook
$HERMES_HOME/plugin-data/hermes-alive/runtime  配置与持久化状态
```

Provider 密钥仍保存在 Hermes 配置中。Hermes Alive 不修改 Hermes Core 或 `weixin.py`。

默认卸载会删除已安装源码、Hook 和托管配置，同时保留学习与运行状态：

```bash
bash "$HERMES_HOME/skills/hermes-alive/scripts/uninstall.sh"
```

同时删除全部 Hermes Alive 状态：

```bash
bash "$HERMES_HOME/skills/hermes-alive/scripts/uninstall.sh" --purge
```

`--purge` 具有破坏性。生产重启和真实消息测试始终应当是明确的运维决定。

## 文档

- [架构](skills/hermes-alive/docs/ARCHITECTURE.md)
- [运行策略](skills/hermes-alive/docs/RUNTIME_POLICIES.md)
- [生命周期与持久化](skills/hermes-alive/docs/LIFECYCLE_AND_PERSISTENCE.md)
- [数据与隐私](skills/hermes-alive/docs/DATA_AND_PRIVACY.md)
- [测试指南](skills/hermes-alive/tests/TESTING.md)

## 许可证

[MIT](LICENSE)
