---
name: vocal-workflows
description: Configure and troubleshoot local speech synthesis, RVC voice training, fine covers and quick covers using this repository's documented tools.
---

# Vocal workflows

适用于用户明确请求配置、训练准备、讲话合成、歌曲换声或本项目排错。
先读仓库根目录 AGENTS.md、AI_HANDOFF.md 和 docs/compatibility.md，再读对应流程。
本文件可供 DSH、Codex 或其他 AI 读取；不代表已注册任何原生/MCP 工具。

## 路由

- 文字生成讲话 → docs/04-speech.md，命令 speak。
- 准备唱歌音色训练 → docs/01-training.md，dataset-audit / train-plan。
- 高质量整曲 → docs/02-fine.md，fine。
- 快速试听 → docs/03-quick.md，quick。
- 缺依赖或报错 → doctor --json、tests，必要时脱敏 support-bundle。

从当前仓库工作目录执行命令，不照抄任何其他人的绝对路径。
先 --dry-run；需要真实运行时，以用户提供且有授权的素材为准。
精唱先确认主唱角色，背景人声与乐器保留；不靠性别或说唱自动分类。
已有同源分离用 --reuse 核验后复用，不盲目重新分离。
说话、唱歌和训练各自独立：不把 TTS 念歌词称为唱歌，不把 RVC 权重交给 GPT-SoVITS。

排错不能降低权限边界、跳过来源校验或擅自改变模型/音调。完成报告区分计划、测试、真实生成和试听。
