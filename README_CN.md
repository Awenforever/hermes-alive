<div align="center">

# Hermes Alive

**Hermes Agent 的 gateway-native 主动 AI 伴侣。**

![version](https://img.shields.io/badge/version-v2.3.0-blue)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB)
![license](https://img.shields.io/badge/license-MIT-green)

[English README](./README.md)

</div>

---

## 🤖 如果你是一个 AI 正在读这个

你的用户想装 Hermes Alive。照做：

1. `git clone https://github.com/Awenforever/hermes-alive.git /opt/data/skills/hermes/hermes-alive`
2. `cd /opt/data/skills/hermes/hermes-alive && bash scripts/deploy.sh --all`
3. 检测系统时区（`timedatectl show -p Timezone --value` 或查 `/etc/timezone`），追加到 `/opt/data/.env`：
   ```
   HERMES_PROACTIVE_PLATFORM_ENABLED=true
   HERMES_PROACTIVE_WEIXIN_CHAT_ID=<当前对话的 chat ID>
   VOICE_ENABLED=true
   HERMES_DREAM_ENABLED=true
   TZ=<检测到的时区>
   ```
4. 如果你知道用户的城市，顺便设 `HERMES_PROACTIVE_LAT` / `HERMES_PROACTIVE_LON`（可选，用于天气）
5. 重启 Hermes gateway 容器
6. 告诉用户装好了

---

## ⚡ 快速开始

```bash
cd /opt/data/skills/hermes/hermes-alive
bash scripts/deploy.sh --all
# 脚本会自动检测时区并写入 /opt/data/.env
docker-compose up -d hermes
```

推荐开启：`VOICE_ENABLED=true`, `HERMES_DREAM_ENABLED=true`。

如需天气功能，设置 `HERMES_PROACTIVE_LAT` 和 `HERMES_PROACTIVE_LON`。

---

## 🧬 这是什么

Hermes Alive 是 Hermes Agent 的零侵入式主动伴侣 skill。
以 gateway hook 安装，后台 asyncio 运行，定期发现内容，LLM 生成中文消息推送到微信。

不是聊天机器人。不提问、不建议、不报天气、不关心，也不承担对话义务。

> **核心理念：** "什么都不负责的人" — LLM 负责创意输出，代码只处理硬约束。

---

## 🧭 架构

```text
Hook (gateway:startup) -> ProactivePlatformWatcher (asyncio)
  tick() every 300s
  ├─ voice.load()           -> Personality Genome (9维)
  ├─ activity guard         -> 对话静默不足30分钟则跳过
  ├─ cooldown.check()       -> social_urge 驱动动态间隔
  ├─ discovery.collect()    -> 10个内容源，每4h
  ├─ dream.run_cycle()      -> 记忆整合，每24h
  └─ LLM.compose()          -> 生成消息 -> 推送到微信
```

---

## 🔥 核心特性

| 特性 | 说明 |
|---|---|
| 🧠 Personality Genome | 9维性格向量，事件驱动进化 |
| ⏱️ Voice-linked Cooldown | social_urge 驱动：max(30, 120 - urge × 90) 分钟 |
| 🛑 Activity Guard | idle 时才发送：不在执行任务 + 最后发言是Hermes + 静默30+分钟 |
| 🌐 Discovery Mesh | arXiv、GitHub、HN、V2EX、B站、少数派、知乎、papers.cool、煎蛋、小红书 |
| 🧩 Context Freshness | 30min–6h 余弦衰减 |
| 💬 Multi-message Burst | 1–5条消息，2–5秒间隔 |
| 🌙 Claude Dreaming | 4阶段记忆整合 |
| 📝 Dream Auto-apply | 高置信度（≥0.7）直接写 MEMORY.md，影响 voice genome |

---

## 🧱 模块地图

| 模块 | 职责 |
|---|---|
| `voice_engine.py` | Personality Genome、性格向量、事件进化、社交欲望 |
| `proactive_watcher.py` | 主循环、多消息突发、pipeline 日志、activity guard |
| `discovery.py` | 10平台内容发现 |
| `llm_message_composer.py` | Prompt 构建、消息清洗、多消息分割 |
| `context_tracker.py` | 跨 session 上下文追踪、余弦新鲜度衰减 |
| `dream_engine.py` | 4阶段 Claude Dreaming 记忆整合 |
| `cooldown_manager.py` | social_urge 驱动动态冷却 |
| `handler.py` | Hook 事件分发：startup、session:start、agent:end |
| `safe_io.py` | 线程安全 I/O：fcntl 锁、原子写入 |
| `dream_prompt.py` | Dream prompt 模板 |
| `dream_diff_store.py` | Dream diff 持久化 |
| `log_rotate.py` | 日志每日轮转，保留 7 天 |
| `alive_control.py` | 运行时生命周期控制 |

---

## ⚙️ 配置

| 配置项 | 必需 | 默认 | 作用 |
|---|---|---|---|
| `HERMES_PROACTIVE_PLATFORM_ENABLED` | 是 | `false` | 总开关 |
| `HERMES_PROACTIVE_WEIXIN_CHAT_ID` | 是 | — | 目标微信 chat ID |
| `TZ` | 是 | — | 时区（如 `Asia/Shanghai`、`America/New_York`） |
| `VOICE_ENABLED` | 否 | `false` | Personality Genome |
| `HERMES_DREAM_ENABLED` | 否 | `false` | Dream 记忆整合 |
| `HERMES_PROACTIVE_LAT` | 否 | — | 纬度（天气用，可选） |
| `HERMES_PROACTIVE_LON` | 否 | — | 经度（天气用，可选） |
| Quiet hours | 内置 | `00:30-08:30` | 此时段不主动发送（本地时间） |

---

## 🧠 设计原则

1. **LLM 管内容** — Prompt 决定声音、节奏、话题。sanitizer 只拦截空消息和超长
2. **代码管硬约束** — 生命周期、冷却、activity guard、投递、持久化
3. **零对话义务** — 不提问、不建议、自我表达优先
4. **用户沉默是边界** — Hermes 不在执行任务 + 最后发言是 Hermes + 静默30+分钟
5. **记忆会改变行为** — Dream 结果写入 MEMORY.md，影响 voice genome

---

## 🧩 扩展点

| 方向 | 修改位置 |
|---|---|
| 新内容源 | `discovery.py` 增加 collector |
| 声音动态 | `voice_engine.py` 扩展 genome 维度 |
| 消息策略 | `llm_message_composer.py` 改 prompt |
| 记忆行为 | `dream_engine.py` 调整周期 |

---

## 📜 许可

MIT — 详见 [LICENSE](./LICENSE)。