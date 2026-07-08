---
name: api-backend
description: This project uses DeepSeek API as the Claude-compatible backend, not official Anthropic
metadata:
  type: project
---

DFW 项目使用 DeepSeek API 作为后端，通过 Anthropic 兼容协议访问。

- Base URL: `https://api.deepseek.com/anthropic`
- Auth Token: `sk-dc781f99cf814e63868e4a8cd6d04f58`
- 主力模型: `deepseek-v4-pro[1m]`（配置为所有 default model）
- 子 agent 模型: `deepseek-v4-flash`
- Effort level: `max`

这些配置通过环境变量注入，不要把 token 硬编码到 settings.json 里（会随 git 泄露）。详细配置步骤见 [[setup-claude]]。
