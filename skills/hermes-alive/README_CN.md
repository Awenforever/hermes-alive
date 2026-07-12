# Hermes Alive 技能包

本目录是 GitHub 仓库 `Awenforever/hermes-alive` 中的完整多文件技能，不是单独的
`SKILL.md`。正式分发和验收对象是完整 GitHub 仓库。

### 位置与天气（轻量引导）

`configure` 会在现有个性化流程中附带一次简短的位置确认：可使用系统时区与网络出口做粗定位，再尽可能细化到区、县、规划区或同等级别；也可直接输入地区或跳过。网络定位仅在用户选择后执行，原始公网 IP 与原始响应不会保存，最终确认的位置只写入本地 managed config。天气上下文没有默认坐标，未确认位置时不会查询。


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

## 作息联合 Shadow 回放

`tests/run_joint_shadow_replay.py` 会把用户作息意图、Circadian 状态机、动态 Sleep / Quiet 比较、主动搭话质量治理和已确认的区／县级天气上下文放在同一条确定性回放链中验证。同时确认所有拒绝结论仍然只观察、不改变现有 watcher 发送路径。本阶段不启用 enforcement。

## 隔离投递 Enforcement v1

联合 Shadow Replay 通过后，已验证的作息、睡眠/静默和主动质量决策只会在
“双重隔离开关”同时满足时真正控制投递。该阶段覆盖动态睡眠保护、被叫醒后
对旧固定静默期的隔离覆盖、无回应沉默锁、候选消息过滤，以及情绪脉冲仅在
成功发送后提交。生产托管配置不暴露这两个 enforcement 开关。
