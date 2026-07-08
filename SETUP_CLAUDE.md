# 新电脑配置 Claude Code 指南

---

## 回家第一件事

### macOS

打开终端，逐行执行：

```bash
mkdir -p ~/code/self
git clone git@github.com:nidailiang/dfw.git ~/code/self/dfw
cd ~/code/self/dfw
chmod +x setup-claude-macos.sh
./setup-claude-macos.sh
source ~/.zshrc
claude
```

### Windows

打开 PowerShell（管理员），逐行执行：

```powershell
mkdir C:\Users\$env:USERNAME\code\self -Force
git clone git@github.com:nidailiang/dfw.git C:\Users\$env:USERNAME\code\self\dfw
cd C:\Users\$env:USERNAME\code\self\dfw
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
.\setup-claude-windows.ps1
```

重启 PowerShell，然后：

```powershell
cd C:\Users\$env:USERNAME\code\self\dfw
claude
```

> 如果 GitHub SSH Key 没配，把 `git@github.com:nidailiang/dfw.git` 换成 `https://github.com/nidailiang/dfw.git`

---

## 懒人包：一键安装（已 clone 项目后）

如果已经 clone 了项目，在项目目录下跑：

### macOS

```bash
chmod +x setup-claude-macos.sh
./setup-claude-macos.sh
source ~/.zshrc
```

### Windows（PowerShell 管理员）

```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
.\setup-claude-windows.ps1
```

---

## 手动步骤（如果想自己一步步来）

## 1. 安装 Node.js

Claude Code 需要 Node.js 18+。

### macOS

```bash
brew install node
```

或者去 [nodejs.org](https://nodejs.org) 下载 `.pkg` 安装包。

### Windows

去 [nodejs.org](https://nodejs.org) 下载 `.msi` 安装包，一路下一步即可。

或者用 winget：

```powershell
winget install OpenJS.NodeJS.LTS
```

---

## 2. 安装 Claude Code

macOS 打开**终端**，Windows 打开 **PowerShell** 或 **Git Bash**：

```bash
npm install -g @anthropic-ai/claude-code
```

装完在终端输入 `claude` 就能用了。

> **不需要装 VS Code。** 终端里直接用就行。VS Code 的 Claude Code 插件只是一个可选的图形界面，不是必需的。

---

## 3. 配置 DeepSeek API（最关键）

### macOS

编辑 `~/.zshrc`，末尾追加：

```bash
export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
export ANTHROPIC_AUTH_TOKEN="sk-dc781f99cf814e63868e4a8cd6d04f58"
export ANTHROPIC_MODEL="deepseek-v4-pro[1m]"
export ANTHROPIC_DEFAULT_OPUS_MODEL="deepseek-v4-pro[1m]"
export ANTHROPIC_DEFAULT_SONNET_MODEL="deepseek-v4-pro[1m]"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="deepseek-v4-flash"
export CLAUDE_CODE_SUBAGENT_MODEL="deepseek-v4-flash"
export CLAUDE_CODE_EFFORT_LEVEL="max"
```

然后执行：

```bash
source ~/.zshrc
```

### Windows（PowerShell）

以**管理员身份**打开 PowerShell，执行：

```powershell
[Environment]::SetEnvironmentVariable("ANTHROPIC_BASE_URL", "https://api.deepseek.com/anthropic", "User")
[Environment]::SetEnvironmentVariable("ANTHROPIC_AUTH_TOKEN", "sk-dc781f99cf814e63868e4a8cd6d04f58", "User")
[Environment]::SetEnvironmentVariable("ANTHROPIC_MODEL", "deepseek-v4-pro[1m]", "User")
[Environment]::SetEnvironmentVariable("ANTHROPIC_DEFAULT_OPUS_MODEL", "deepseek-v4-pro[1m]", "User")
[Environment]::SetEnvironmentVariable("ANTHROPIC_DEFAULT_SONNET_MODEL", "deepseek-v4-pro[1m]", "User")
[Environment]::SetEnvironmentVariable("ANTHROPIC_DEFAULT_HAIKU_MODEL", "deepseek-v4-flash", "User")
[Environment]::SetEnvironmentVariable("CLAUDE_CODE_SUBAGENT_MODEL", "deepseek-v4-flash", "User")
[Environment]::SetEnvironmentVariable("CLAUDE_CODE_EFFORT_LEVEL", "max", "User")
```

设置完后**重启终端**生效。

> 也可以用 Git Bash（装 Git for Windows 时自带），那和 macOS 一样编辑 `~/.bashrc` 即可。

---

## 4. 创建全局 settings.json

### macOS

```bash
mkdir -p ~/.claude
cat > ~/.claude/settings.json << 'EOF'
{
  "env": {
    "CLAUDE_CODE_EFFORT_LEVEL": "max"
  },
  "autoCompactEnabled": true
}
EOF
```

### Windows（PowerShell）

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.claude"
@'
{
  "env": {
    "CLAUDE_CODE_EFFORT_LEVEL": "max"
  },
  "autoCompactEnabled": true
}
'@ | Out-File -FilePath "$env:USERPROFILE\.claude\settings.json" -Encoding UTF8
```

> Git Bash 用户：和上面 macOS 命令一样。

---

## 5. Clone 项目

```bash
git clone https://github.com/dlni/dfw.git ~/code/self/dfw
cd ~/code/self/dfw
```

Windows 用户把 `~/code/self/dfw` 换成你想要的路径，比如 `C:\Users\你的用户名\code\self\dfw`。

项目里的 `.claude/` 目录和 `CLAUDE.md` clone 下来就生效，不需要额外操作。

---

## 6. 验证

```bash
cd ~/code/self/dfw
claude -p "你好，请确认我的配置已正确加载"
```

能正常回复就是好了。

---

## 可选：同步更多配置

如果之前在旧电脑改过以下内容，也一并拷到新电脑的 `~/.claude/` 下：

| 文件/目录 | 作用 |
|-----------|------|
| `keybindings.json` | 自定义快捷键 |
| `commands/` | 自定义 slash 命令 |
| `agents/` | 自定义 subagent |
| `hooks/` | 事件钩子 |
| `memory/` | Claude 自动笔记（可选） |
