# Hermes Alive

Hermes 的克制型主动陪伴插件。它根据最近对话、安静时段、发送积压和互动频率，决定是否主动发起一条消息。

## 功能

- 活跃对话或待发送队列存在时不打扰。
- 支持安静时段和最小主动消息间隔。
- 对重复、施压、无依据的任务声明和低质量草稿做拦截。
- 人格、关系和记忆更新有界、可追踪、可关闭。
- 使用 Hermes 已配置的模型与消息通道，不维护第二套密钥。
- 默认关闭；必须由使用者明确启用。

Hermes Alive 不负责普通入站回复、微信队列、邮件监控或学术周报。

## 要求

- Hermes `>=0.21.3,<0.22`
- Python 3.11+
- Hermes 中已有可用模型和目标消息通道

## 安装

```bash
hermes plugins install Awenforever/hermes-alive
hermes plugins enable hermes-alive
hermes alive install-runtime
```

确认状态后再启用主动消息：

```bash
hermes alive status
hermes alive enable
```

暂停时无需卸载：

```bash
hermes alive disable
```

## 默认策略

| 选项 | 默认值 | 作用 |
|---|---:|---|
| `enabled` | `false` | 是否允许主动发送 |
| `delivery_platform` | `weixin` | 主动消息通道 |
| `min_interval_seconds` | `21600` | 两次主动消息的最短间隔 |
| `quiet_hours_start` | `23:00` | 安静时段开始 |
| `quiet_hours_end` | `08:00` | 安静时段结束 |

运行状态保存在当前 Hermes profile 的 `plugin-data/hermes-alive/`，Gateway hook 位于 `hooks/hermes-alive/`。插件不修改 Hermes Core。

## 安全与隐私

插件只应使用当前会话和本地状态中确有依据的信息。发现、记忆或主动发送功能均不得绕过 Hermes 的通道权限与队列规则。建议先在备用账号观察数天，再逐步缩短主动间隔。

## License

[MIT](LICENSE)
