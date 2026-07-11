# Hermes Alive 技能包

本目录是 GitHub 仓库 `Awenforever/hermes-alive` 中的完整多文件技能，不是单独的
`SKILL.md`。正式分发和验收对象是完整 GitHub 仓库。

## Hermes 自安装

```bash
git clone --depth 1 \
  https://github.com/Awenforever/hermes-alive.git \
  /tmp/hermes-alive

bash /tmp/hermes-alive/bootstrap.sh \
  --hermes-home /opt/data
```

也可以使用 Hermes 官方 GitHub 技能标识符：

```bash
/opt/hermes/.venv/bin/hermes skills install \
  Awenforever/hermes-alive/skills/hermes-alive \
  --category hermes --yes

cd /opt/data/skills/hermes/hermes-alive
scripts/hermes-alive-lifecycle install
```

bootstrap 会原子安装 source skill 和 active hook、编译全部 Python、生成 manifest、
规范权限，并在升级失败时恢复上一可用版本。测试工具不得预先把源码复制到最终
skill/hook 目录。

## Provider 与个性化

Provider 密钥和模型配置始终由 Hermes 管理：

```bash
LIFECYCLE=/opt/data/skills/hermes/hermes-alive/scripts/hermes-alive-lifecycle

"$LIFECYCLE" configure --provider-check-only
/opt/hermes/.venv/bin/hermes setup model
```

Hermes Alive 只保存非敏感个性化配置：

```bash
"$LIFECYCLE" configure \
  --enable \
  --weixin-chat-id '<chat-id>' \
  --timezone Asia/Singapore \
  --quiet-start 23:00 \
  --quiet-end 08:00 \
  --emoji-policy contextual

"$LIFECYCLE" verify
"$LIFECYCLE" status
```

显式环境变量优先于 managed config。不得把 API Key 写入 Hermes Alive 配置。

## 卸载

默认卸载删除 source、active hook 和 managed config，但保留学习/运行状态：

```bash
"$LIFECYCLE" uninstall
```

彻底清理会删除全部 Hermes Alive 共享状态：

```bash
"$LIFECYCLE" purge
```

生产 Gateway 重启和真实消息发送必须取得明确许可。

## Phase H 测试套件

```bash
python3 /opt/data/skills/hermes/hermes-alive/tests/run_matrix.py
python3 /opt/data/skills/hermes/hermes-alive/tests/run_stress.py
```

最终验收必须使用默认满负载压力规模；缩放模式仅用于开发烟测。
