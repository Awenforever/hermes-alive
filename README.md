<div align="center">

# Hermes Alive

**让 Hermes 偶尔主动开口，同时知道何时保持安静。**

![version](https://img.shields.io/badge/version-2.8.11-blue)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB)
![Hermes](https://img.shields.io/badge/Hermes-gateway--native-6f42c1)
![license](https://img.shields.io/badge/license-MIT-green)

[详细说明](README_CN.md) · [安全](SECURITY.md) · [贡献](CONTRIBUTING.md)

</div>

Hermes Alive 是独立的 Gateway 主动陪伴插件。它结合近期对话、互动压力、
作息、兴趣和外部内容，决定是否发起自然消息；不会接管普通回复、微信队列、
邮件监控或周报。

## 主要能力

- 对话活跃、仍有待回复内容或用户连续未回应时主动克制；
- 在时事、本地动态、人物文化、轻松趣闻、社区、技术与学术内容间轮换；
- 先读取来源正文，再按事实、价值、时效、自然度、最少气泡与整体连贯性独立审查；
- 以语义气泡表达，不把长段文字机械切片；来源链接以内联 Markdown 呈现；
- 有边界地学习性格、兴趣和作息，并支持暂停、验证与回滚；
- 复用 Hermes 当前模型、消息通道和认证，不维护第二套密钥。

## 让 Hermes 安装（推荐）

把仓库地址发给 Hermes，并告诉它：

> 阅读本仓库的 `README.md` 与 `skills/hermes-alive/SKILL.md`，引导我完成
> 个性化配置，确认后安装 Hermes Alive。

Hermes 会用自然语言确认目标会话、地区、作息和内容偏好，再转换成安装参数。
用户无需填写 API Key、模型别名、时区字符串或经纬度。首次安装继承当前设备
已配置的 Hermes 模型；升级保留已有 Alive 配置和学习状态。

仓库不会复制作者的微信身份、USTC 模型、代理或私人偏好。所谓“一致体验”是
相同的功能、引导、目录结构和安全边界，而不是复制另一位用户的凭据。

## 命令行安装

要求 Hermes `>=0.21.3,<0.22`、Python 3.11+，以及已经可用的模型和消息通道。

```bash
git clone --depth 1 https://github.com/Awenforever/hermes-alive.git /tmp/hermes-alive
cd /tmp/hermes-alive
HERMES_HOME=/opt/data bash scripts/bootstrap.sh
```

安装脚本会写入标准 Hermes 数据目录并完成验证，但不会重启 Gateway：

```text
$HERMES_HOME/skills/hermes-alive
$HERMES_HOME/hooks/hermes-alive
$HERMES_HOME/plugin-data/hermes-alive/runtime
```

它不使用 `personal_folder`、工作目录或仓库目录保存运行数据。

## 控制与卸载

```bash
export HERMES_HOME=/opt/data
LIFECYCLE="$HERMES_HOME/skills/hermes-alive/scripts/hermes-alive-lifecycle"

"$LIFECYCLE" status
python3 "$HERMES_HOME/hooks/hermes-alive/alive_control.py" disable
python3 "$HERMES_HOME/hooks/hermes-alive/alive_control.py" enable
bash "$HERMES_HOME/skills/hermes-alive/scripts/verify.sh"
```

普通卸载保留学习与运行状态；`--purge` 才会删除全部 Alive 状态：

```bash
bash "$HERMES_HOME/skills/hermes-alive/scripts/uninstall.sh"
bash "$HERMES_HOME/skills/hermes-alive/scripts/uninstall.sh" --purge
```

## 安全边界

- 不修改 Hermes Core 或 `weixin.py`；
- 不把 Provider 密钥写入插件仓库或 Alive 配置；
- 不在未经确认时发送测试消息或重启生产 Gateway；
- 安装、更新与卸载均保留可验证的回滚路径。

## 文档

- [架构](skills/hermes-alive/docs/ARCHITECTURE.md)
- [运行策略](skills/hermes-alive/docs/RUNTIME_POLICIES.md)
- [生命周期与持久化](skills/hermes-alive/docs/LIFECYCLE_AND_PERSISTENCE.md)
- [数据与隐私](skills/hermes-alive/docs/DATA_AND_PRIVACY.md)
- [测试](skills/hermes-alive/tests/TESTING.md)

## License

[MIT](LICENSE)
