#!/bin/bash
set -e

echo "===== 1/5 检查 Node.js ====="
if ! command -v node &>/dev/null; then
    echo "Node.js 未安装，正在通过 Homebrew 安装..."
    if ! command -v brew &>/dev/null; then
        echo "请先安装 Homebrew: https://brew.sh"
        exit 1
    fi
    brew install node
else
    echo "Node.js 已安装: $(node -v)"
fi

echo ""
echo "===== 2/5 安装 Claude Code ====="
npm install -g @anthropic-ai/claude-code
echo "Claude Code 已安装: $(claude --version)"

echo ""
echo "===== 3/5 配置 DeepSeek API ====="
cat >> ~/.zshrc << 'ENVEOF'

# === Claude Code / DeepSeek API ===
export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
export ANTHROPIC_AUTH_TOKEN="sk-dc781f99cf814e63868e4a8cd6d04f58"
export ANTHROPIC_MODEL="deepseek-v4-pro[1m]"
export ANTHROPIC_DEFAULT_OPUS_MODEL="deepseek-v4-pro[1m]"
export ANTHROPIC_DEFAULT_SONNET_MODEL="deepseek-v4-pro[1m]"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="deepseek-v4-flash"
export CLAUDE_CODE_SUBAGENT_MODEL="deepseek-v4-flash"
export CLAUDE_CODE_EFFORT_LEVEL="max"
ENVEOF

# 也加到 ~/.bashrc 以防万一
cat >> ~/.bashrc << 'ENVEOF'

# === Claude Code / DeepSeek API ===
export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
export ANTHROPIC_AUTH_TOKEN="sk-dc781f99cf814e63868e4a8cd6d04f58"
export ANTHROPIC_MODEL="deepseek-v4-pro[1m]"
export ANTHROPIC_DEFAULT_OPUS_MODEL="deepseek-v4-pro[1m]"
export ANTHROPIC_DEFAULT_SONNET_MODEL="deepseek-v4-pro[1m]"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="deepseek-v4-flash"
export CLAUDE_CODE_SUBAGENT_MODEL="deepseek-v4-flash"
export CLAUDE_CODE_EFFORT_LEVEL="max"
ENVEOF

export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
export ANTHROPIC_AUTH_TOKEN="sk-dc781f99cf814e63868e4a8cd6d04f58"
export ANTHROPIC_MODEL="deepseek-v4-pro[1m]"
export ANTHROPIC_DEFAULT_OPUS_MODEL="deepseek-v4-pro[1m]"
export ANTHROPIC_DEFAULT_SONNET_MODEL="deepseek-v4-pro[1m]"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="deepseek-v4-flash"
export CLAUDE_CODE_SUBAGENT_MODEL="deepseek-v4-flash"
export CLAUDE_CODE_EFFORT_LEVEL="max"
echo "环境变量已写入 ~/.zshrc 和 ~/.bashrc"

echo ""
echo "===== 4/5 创建 settings.json ====="
mkdir -p ~/.claude
cat > ~/.claude/settings.json << 'EOF'
{
  "env": {
    "CLAUDE_CODE_EFFORT_LEVEL": "max"
  },
  "autoCompactEnabled": true
}
EOF
echo "settings.json 已创建"

echo ""
echo "===== 5/5 Clone 项目 ====="
mkdir -p ~/code/self
if [ -d ~/code/self/dfw ]; then
    echo "目录已存在，跳过 clone"
else
    git clone https://github.com/dlni/dfw.git ~/code/self/dfw
fi

echo ""
echo "===== 全部完成! ====="
echo "执行以下命令生效环境变量:"
echo "  source ~/.zshrc"
echo "然后进入项目:"
echo "  cd ~/code/self/dfw"
echo "  claude"
