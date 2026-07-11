# Hermes Alive

这是 Hermes Alive 的完整 GitHub 分发仓库，不是单独的 `SKILL.md`。

## Hermes 自安装

在全新 Hermes 容器中，只需要提供仓库地址：

```bash
git clone --depth 1 https://github.com/Awenforever/hermes-alive.git /tmp/hermes-alive
bash /tmp/hermes-alive/bootstrap.sh --hermes-home /opt/data
```

也可以使用 Hermes 官方 GitHub 技能安装：

```bash
/opt/hermes/.venv/bin/hermes skills install \
  Awenforever/hermes-alive/skills/hermes-alive \
  --category hermes --yes

cd /opt/data/skills/hermes/hermes-alive
scripts/hermes-alive-lifecycle install
```

仓库 bootstrap 会自行安装 source skill、激活 hook、编译全部模块、生成 manifest、
规范权限并保留升级前的学习状态。Provider 密钥始终由 Hermes 管理；没有模型时应引导
用户运行 `hermes setup model`。

只有全新容器矩阵、压力、备用微信真实验收和干净卸载全部通过后，才考虑生产替换。

## Phase H 测试套件

标记：`HERMES_ALIVE_MATRIX_SUITE_V1`、`HERMES_ALIVE_STRESS_SUITE_V1`。

```bash
python3 skills/hermes-alive/tests/run_matrix.py
python3 skills/hermes-alive/tests/run_stress.py
```

最终验收必须以默认压力规模运行；缩放模式仅用于开发烟测。

## 生命周期命令

```bash
LIFECYCLE=/opt/data/skills/hermes/hermes-alive/scripts/hermes-alive-lifecycle

"$LIFECYCLE" configure --provider-check-only
"$LIFECYCLE" configure
"$LIFECYCLE" verify
"$LIFECYCLE" status
"$LIFECYCLE" uninstall
"$LIFECYCLE" purge
```

默认卸载保留学习和运行状态；`purge` 删除全部 Hermes Alive 共享状态。生产
Gateway 重启和真实消息测试必须取得明确许可。

## 公共仓库契约

公开说明只使用完整 GitHub 仓库、根目录 bootstrap 和 lifecycle CLI，不依赖未发布
分支、手动复制 hook 或旧部署流程。

标记：`HERMES_ALIVE_PUBLIC_DOCUMENTATION_CONTRACT_V1`。
