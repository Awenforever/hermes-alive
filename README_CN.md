<div align="center">

# Hermes Alive

**Hermes Agent 的 gateway-native 主动 AI 伴侣。**

性格、上下文、记忆、拟人作息与安全生命周期管理——让 Hermes 有“在场感”，但不会把每一次沉默都变成通知。

![version](https://img.shields.io/badge/version-v2.4.0-blue)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB)
![Hermes](https://img.shields.io/badge/Hermes-gateway--native-6f42c1)
![status](https://img.shields.io/badge/status-acceptance%20candidate-orange)
![license](https://img.shields.io/badge/license-MIT-green)

[English README](./README.md) · [安全说明](./SECURITY.md) · [参与贡献](./CONTRIBUTING.md)

</div>

---

## 🧬 Hermes Alive 是什么

Hermes Alive 是 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 的主动陪伴层。

它以 gateway hook 的形式安装，作为持久化 `asyncio` 任务运行，理解当前微信对话，维护有边界的性格画像，发现可能值得分享的内容，并通过 Hermes 已配置的真实模型偶尔主动开口。

它围绕一个核心理念设计：

> **有在场感，但不制造回应义务。**
> Hermes 可以注意、记住、反应、沉默、入睡、醒来，也可以偶尔主动搭话；但它不应索取注意力，更不能虚构自己并不存在的物理体验。

Hermes Alive 不是一个替代式聊天机器人，也不接管 Provider 密钥。模型配置、平台适配和最终消息发送仍由 Hermes 管理。

---

## ✨ 核心能力

| 能力 | 行为 | 当前状态 |
|---|---|---|
| 🫀 Gateway 原生 watcher | 随 Hermes Gateway 运行，周期性评估是否适合主动开口。 | 已启用 |
| 🛑 Activity Guard | Hermes 正在工作、用户还在等回复或对话仍很新鲜时，禁止主动插话。 | 已启用 |
| 🧩 Context Queue | 从 `state.db` 刷新近期微信上下文，并持久化有上限的崩溃恢复队列。 | 已启用 |
| 🧠 Personality Genome | 维护有边界的用户级性格向量，并以独立 `social_urge` 控制主动节奏。 | 已启用 |
| 🌙 Circadian Engine | 建模清醒、困倦、延迟入睡、睡眠、浅睡、被叫醒、赖床、睡眠债与恢复。 | 默认 Shadow |
| 🤫 Sleep / Quiet Policy | 比较动态作息与旧固定静默期，同时保留系统消息硬豁免。 | 默认 Shadow |
| 💬 Proactive Quality Governor | 识别语义重复、无证据任务推断、speech-act 过度复用和虚假天气视角。 | 默认 Shadow |
| 😒 情绪脉冲 | 日常聊天突然中断时，可低概率出现一次轻微短暂情绪；同一沉默事件绝不重复或升级。 | 默认 Shadow |
| 🌦️ 精细位置与天气 | 使用天气前确认区、县、规划区或同等级别位置。 | 引导已接入 |
| 🌐 Discovery Mesh | 以缓存和预算约束收集论文、开发、资讯、视频及生活内容。 | 已启用 |
| 🌙 Dream 记忆整合 | 读取真实会话上下文，提出有边界的记忆变更，并可影响性格画像。 | 可选 |
| 🖼️ 富内容投递 | 通过经过验证的内容引用和平台能力安全发送链接、图片等内容。 | 已启用 |
| 🔎 Pipeline Trace | 使用同一 `tick_id` 串联发现、生成、策略判断和发送。 | 已启用 |
| 🧰 生命周期管理 | 原子安装、失败回滚、验证、保留状态卸载和彻底清理。 | 已启用 |

> **为什么默认使用 Shadow？**
> v2.4.0 候选版会记录 Circadian 与 Quality 判断，但不会直接改变生产投递。真正拦截消息需要两个仅用于隔离测试的开关，必须在全新容器和备用微信真实验收通过后，才会考虑生产启用。

---

## 🧭 一条主动消息如何产生

```text
Gateway 控制队列
  └─ 系统 / 安全 / 提醒 / 生命周期消息保持最高优先级

近期微信上下文
  ├─ Hermes 是否仍在执行任务？
  ├─ 用户是否还在等待 Hermes 回复？
  └─ 对话是否已经安静足够长时间？

Circadian Engine
  ├─ awake / drowsy / delayed_sleep
  ├─ sleeping / light_sleep / awakened / snoozing
  └─ sleep_deprived / recovering

Sleep & Quiet Policy
  ├─ 动态睡眠建议
  ├─ 与旧固定静默期比较
  └─ 保留系统硬豁免

Proactive Quality Governor
  ├─ 未回应消息预算
  ├─ 一次性情绪脉冲
  ├─ 语义新颖度和模板族冷却
  ├─ 任务状态证据门
  └─ 天气视角检查

上下文提供器
  ├─ Personality Genome
  ├─ 近期对话
  ├─ 发现内容
  ├─ 已确认的当地天气
  └─ 兴趣与记忆

LLM Composer
  └─ 候选消息

生成后检查
  └─ 安全、非重复、有证据的输出

微信适配器
  └─ 真实模型 metadata 与可追踪发送
```

控制、安全、提醒、生命周期等系统消息不作为普通社交打扰处理。

---

## 🌙 拟人作息、睡眠与静默

Circadian Engine 不只是固定的“勿扰时间”。它维护确定性的日计划和持久化作息状态，并能理解用户明确表达的作息意图。

意图桥可以区分：

| 用户表达 | 系统理解 |
|---|---|
| “晚安”“你先睡吧” | Hermes 可以提前进入睡眠倾向。 |
| “再陪我一会儿” | 在有上限的范围内临时延迟入睡。 |
| “醒醒”“起床了” | 提前醒来或离开睡眠状态。 |
| “你睡了吗” | 只是询问状态，不会自动改写作息。 |
| “我今晚熬夜”“我还在忙” | 这是用户上下文，不等于 Hermes 必须陪着熬夜。 |

作息模型支持：

- 可配置的基础入睡和起床时间；
- 有上限的每日自然波动；
- 深睡核心时段；
- 最低与理想睡眠时长；
- 睡眠债与恢复；
- 从重复行为中缓慢、限幅学习；
- 旧学习偏移逐步衰减；
- 明确用户偏好高于单次晚间互动；
- 可配置概率的入睡和醒来过渡表达。

一次熬夜不能永久改变作息。重复行为可以缓慢推动调整，旧偏移也可以逐步回归明确偏好。

---

## 💬 可以有情绪，但不能循环施压

Hermes Alive 可以在活跃闲聊突然中断时偶尔产生一点情绪。完全没有情绪会显得机械，这种拟人表现是有意保留的。

正确规则是：

```text
一个沉默事件
→ 可能产生一次轻微情绪脉冲
→ 情绪自然衰减
→ 安静等待
```

对于同一个沉默事件，Hermes 不得：

- 再发第二次抱怨；
- 从轻微不满持续升级；
- 通过改写反复发送“人呢 / 又消失 / 呵”；
- 因用户没有回应而持续数小时；
- 把运行脚本、审计或 debug 时的沉默解释为冷落。

Quality Governor 还会拒绝“还没跑完？”之类没有新鲜结构化证据的任务状态判断。

---

## 🌦️ 位置与天气：精细，但不虚构

天气只是轻量上下文能力，不是安装引导的主角。

首次 `configure` 且尚无已确认位置时，Hermes Alive 只提出一次简短位置确认。它可以参考：

- 系统时区和区域；
- 已有确认位置；
- 用户允许后的网络粗定位；
- 用户直接输入的区、县、规划区、borough 或同等级别区域。

所有推断都允许确认和修正。VPN、代理、移动网络或远程服务器都可能让网络位置判断失真。

隐私边界：

- 最终确认位置保存在本机；
- 不长期保存公网 IP 和原始定位响应；
- 不向天气服务发送 Provider 密钥和聊天内容；
- 天气查询只发送服务所需的最小地区或坐标；
- 网络出口变化不会静默覆盖用户已经确认的位置。

Hermes 可以说：

> “接下来一周好像都有雨。”
> “下午可能有阵雨，出门的话带把伞。”

Hermes 不能假装：

> “我这里在下雨。”
> “雷暴让我喘不过气。”

人格化表达可以存在，虚构物理体验不可以。

---

## ⚡ 快速开始

正式分发对象是完整 GitHub 仓库，不是单独的 `SKILL.md`。

### 方式 A：克隆并执行 bootstrap

```bash
git clone --depth 1 \
  https://github.com/Awenforever/hermes-alive.git \
  /tmp/hermes-alive

bash /tmp/hermes-alive/bootstrap.sh \
  --hermes-home /opt/data
```

### 方式 B：Hermes 官方 GitHub Skill Transport

```bash
/opt/hermes/.venv/bin/hermes skills install \
  Awenforever/hermes-alive/skills/hermes-alive \
  --category hermes \
  --yes

cd /opt/data/skills/hermes/hermes-alive
scripts/hermes-alive-lifecycle install
```

### 配置 Provider 与个性化

Provider 凭据归 Hermes 管理。Hermes Alive 只保存非敏感个性化配置。

```bash
LIFECYCLE=/opt/data/skills/hermes/hermes-alive/scripts/hermes-alive-lifecycle

"$LIFECYCLE" configure --provider-check-only

# 仅当 Hermes 报告没有可用模型时执行：
/opt/hermes/.venv/bin/hermes setup model

# 交互式个性化配置，其中包含一次简短位置确认：
"$LIFECYCLE" configure

"$LIFECYCLE" verify
"$LIFECYCLE" status
```

active hook 发生变化后可能需要重启 Gateway。生产 Gateway 重启和真实消息发送必须是明确的运维决策，不能作为安装脚本的隐式副作用。

---

## ⚙️ 配置

交互式配置会尽量保持简洁。多数用户只需要确认：

- 是否启用 Hermes Alive；
- 目标微信会话；
- 时区与静默偏好；
- 是否使用模型生成；
- 内容发现与 Dream 偏好；
- 一次简短的位置和天气确认。

高级非敏感配置可以通过生命周期 CLI 传入：

```bash
"$LIFECYCLE" configure \
  --enable \
  --weixin-chat-id '<chat-id>' \
  --timezone Asia/Singapore \
  --quiet-start 23:00 \
  --quiet-end 08:00 \
  --emoji-policy contextual \
  --circadian-enabled \
  --circadian-mode shadow \
  --base-sleep-time 23:00 \
  --base-wake-time 07:00
```

常用配置组：

| 配置组 | 示例 |
|---|---|
| 平台 | 总开关、微信 peer、tick 间隔、冷却时间 |
| 模型 | LLM 开关、主模型、回退模型、超时 |
| 内容 | Discovery 开关与间隔、Dream 开关 |
| 表达 | emoji 策略、多消息生成、性格画像 |
| 作息 | chronotype、睡眠偏好、学习限幅、睡眠债 |
| 天气 | 已确认位置、行政区层级、坐标、时区 |
| 生命周期 | 安装路径、验证、保留状态卸载、彻底清理 |

显式进程环境变量优先于 managed config。API Key、Token、密码和 Provider 凭据必须继续保存在 Hermes 配置中，不得写入 Hermes Alive 的 managed JSON。

---

## 🏗️ 架构

```text
Hermes gateway
└── hooks/hermes-alive
    ├── handler.py
    │   ├── gateway:startup
    │   ├── session:start
    │   └── agent:end
    │
    ├── proactive_watcher.py
    │   ├── 上下文 / Activity Guard
    │   ├── Circadian Shadow 判断
    │   ├── Sleep / Quiet Shadow 比较
    │   ├── Quality Governor Shadow 判断
    │   ├── Discovery 与 Dream 周期
    │   └── 生成与发送
    │
    ├── context_tracker.py
    ├── voice_engine.py
    ├── circadian_engine.py
    ├── circadian_intent_bridge.py
    ├── circadian_sleep_quiet_policy.py
    ├── proactive_quality_governor.py
    ├── location_weather_profile.py
    ├── discovery.py
    ├── dream_engine.py
    ├── llm_message_composer.py
    ├── content_delivery.py
    ├── interest_learning.py
    ├── interruption_policy.py
    └── safe_io.py
```

持久化数据与可替换源码分离：

```text
/opt/data/skills/hermes/hermes-alive   # source skill
/opt/data/hooks/hermes-alive           # active hook
/opt/data/hermes_alive_shared          # managed config、运行状态和学习数据
```

这样升级可以替换代码，而不会丢弃已经积累的用户状态。

---

## 🧱 模块地图

| 模块 | 职责 |
|---|---|
| `proactive_watcher.py` | 周期主循环、策略编排、生成、发送和 trace 日志 |
| `context_tracker.py` | 近期消息队列、`state.db` 刷新、角色与活跃语义 |
| `voice_engine.py` | Personality Genome 与 social urge |
| `circadian_engine.py` | 日计划、持久化睡眠状态、睡眠债、恢复和限幅学习 |
| `circadian_intent_bridge.py` | 确定性作息意图解析、去重和过期保护 |
| `circadian_sleep_quiet_policy.py` | 动态作息建议、固定静默比较和硬豁免 |
| `proactive_quality_governor.py` | 情绪脉冲、语义新颖度、状态证据与视角检查 |
| `location_weather_profile.py` | 精细位置确认和隐私最小化天气上下文 |
| `interruption_policy.py` | 主动打扰级别与消息气泡数量 |
| `interest_learning.py` | 有边界、可归因的兴趣反馈学习 |
| `discovery.py` | 内容收集、规范化、缓存和预算 |
| `dream_engine.py` | 记忆整合与高置信度更新 |
| `llm_message_composer.py` | Prompt、模型调用、回退、清洗和消息分割 |
| `content_delivery.py` | 已验证链接、媒体引用和平台能力适配 |
| `managed_config.py` | 非敏感 managed config 加载 |
| `safe_io.py` | 原子写入、文件锁和有上限 JSON/JSONL 持久化 |
| `alive_control.py` | 运行时启动与停止控制 |
| `log_rotate.py` | 日志轮转和保留 |

---

## 🔎 日志与诊断

每次主动 tick 都会在共享运行日志中记录 decision、reason 和 `tick_id`。

```bash
cd /opt/data/skills/hermes/hermes-alive

# 最近事件和消息预览
python3 scripts/logs.py --tail 5 --preview

# 某日期以来已发送的消息
python3 scripts/logs.py --decision sent --since 2026-07-01 --preview

# 决策统计
python3 scripts/logs.py --stats

# 原始 JSON 错误记录
python3 scripts/logs.py --decision error --json
```

生命周期诊断：

```bash
scripts/hermes-alive-lifecycle status
scripts/hermes-alive-lifecycle verify
```

---

## 🧪 验证与验收

开发回归：

```bash
cd /opt/data/skills/hermes/hermes-alive
bash tests/run_all.sh
```

专项测试：

```bash
python3 tests/run_matrix.py
python3 tests/run_stress.py
python3 tests/run_joint_shadow_replay.py
python3 tests/run_isolated_enforcement.py
```

最终验收比单元测试更严格：

1. 从全新容器开始；
2. 从真实 GitHub 仓库克隆或安装；
3. 完成 Provider 与个性化引导；
4. 运行完整 matrix 和默认规模 stress；
5. 验证安装、verify、卸载、重装和 purge；
6. 经明确批准后使用备用微信账号完成真实端到端消息验证；
7. 确认安全干净卸载，且生产环境没有副作用。

在该流程全部通过前，候选代码不能被视为生产就绪。

---

## ♻️ 生命周期与数据保留

```bash
LIFECYCLE=/opt/data/skills/hermes/hermes-alive/scripts/hermes-alive-lifecycle

"$LIFECYCLE" install
"$LIFECYCLE" configure
"$LIFECYCLE" verify
"$LIFECYCLE" status
"$LIFECYCLE" uninstall
"$LIFECYCLE" purge
```

- `install` 原子替换 source 和 active hook，失败时回滚。
- `verify` 检查 manifest、source/hook 一致性、Python 编译和配置。
- `uninstall` 删除 source、active hook 与 managed config，但保留学习和运行状态。
- `purge` 删除全部 Hermes Alive 共享状态，是有意设计的破坏性操作。

---

## 📚 深入文档

- [架构](skills/hermes-alive/docs/ARCHITECTURE.md)
- [运行策略](skills/hermes-alive/docs/RUNTIME_POLICIES.md)
- [生命周期与持久化](skills/hermes-alive/docs/LIFECYCLE_AND_PERSISTENCE.md)
- [数据与隐私](skills/hermes-alive/docs/DATA_AND_PRIVACY.md)
- [测试与验收](skills/hermes-alive/docs/TESTING_AND_ACCEPTANCE.md)
- [内容发现开发](skills/hermes-alive/docs/DISCOVERY_DEVELOPMENT.md)

---

## 🛡️ 设计原则

1. **模型负责表达，代码负责安全边界。**
2. **用户沉默可以带来短暂情绪，但不能演变成持续施压。**
3. **没有新鲜证据，就不推断任务状态。**
4. **不虚构所在地、天气体验和身体感受。**
5. **明确用户偏好高于单次行为推断。**
6. **学习必须有边界、可归因、可逆且尊重隐私。**
7. **可替换源码与持久化用户状态分离。**
8. **Provider 密钥继续归 Hermes 管理。**
9. **生产修改不得隐藏在普通测试步骤中。**
10. **全新容器验收先于生产替换。**

---

## 📜 许可证

MIT — 参见 [LICENSE](./LICENSE)。
