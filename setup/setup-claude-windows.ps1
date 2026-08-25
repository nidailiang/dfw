# Claude Code 一键安装脚本 (Windows PowerShell)
# 以管理员身份运行 PowerShell，执行:
#   Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
#   .\setup-claude-windows.ps1

$ErrorActionPreference = "Stop"

Write-Host "===== 1/5 检查 Node.js =====" -ForegroundColor Cyan
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "Node.js 未安装，正在通过 winget 安装..."
    winget install OpenJS.NodeJS.LTS --accept-package-agreements
    Write-Host "请重启 PowerShell 后重新运行此脚本"
    exit 0
} else {
    Write-Host "Node.js 已安装: $(node -v)"
}

Write-Host ""
Write-Host "===== 2/5 安装 Claude Code =====" -ForegroundColor Cyan
npm install -g @anthropic-ai/claude-code
Write-Host "Claude Code 已安装"

Write-Host ""
Write-Host "===== 3/5 配置 DeepSeek API =====" -ForegroundColor Cyan
$envVars = @{
    "ANTHROPIC_BASE_URL"              = "https://api.deepseek.com/anthropic"
    "ANTHROPIC_AUTH_TOKEN"            = "sk-dc781f99cf814e63868e4a8cd6d04f58"
    "ANTHROPIC_MODEL"                 = "deepseek-v4-pro[1m]"
    "ANTHROPIC_DEFAULT_OPUS_MODEL"    = "deepseek-v4-pro[1m]"
    "ANTHROPIC_DEFAULT_SONNET_MODEL"  = "deepseek-v4-pro[1m]"
    "ANTHROPIC_DEFAULT_HAIKU_MODEL"   = "deepseek-v4-flash"
    "CLAUDE_CODE_SUBAGENT_MODEL"      = "deepseek-v4-flash"
    "CLAUDE_CODE_EFFORT_LEVEL"        = "max"
}

foreach ($key in $envVars.Keys) {
    [Environment]::SetEnvironmentVariable($key, $envVars[$key], "User")
    # 同时设到当前进程
    Set-Item -Path "env:$key" -Value $envVars[$key]
}
Write-Host "环境变量已配置（用户级别）"

Write-Host ""
Write-Host "===== 4/5 创建 settings.json =====" -ForegroundColor Cyan
$claudeDir = "$env:USERPROFILE\.claude"
New-Item -ItemType Directory -Force -Path $claudeDir | Out-Null
@'
{
  "env": {
    "CLAUDE_CODE_EFFORT_LEVEL": "max"
  },
  "autoCompactEnabled": true
}
'@ | Out-File -FilePath "$claudeDir\settings.json" -Encoding UTF8
Write-Host "settings.json 已创建"

Write-Host ""
Write-Host "===== 5/5 Clone 项目 =====" -ForegroundColor Cyan
$projectDir = "$env:USERPROFILE\code\self\dfw"
if (Test-Path $projectDir) {
    Write-Host "目录已存在，跳过 clone"
} else {
    New-Item -ItemType Directory -Force -Path (Split-Path $projectDir) | Out-Null
    git clone https://github.com/dlni/dfw.git $projectDir
}

Write-Host ""
Write-Host "===== 全部完成! =====" -ForegroundColor Green
Write-Host "重启 PowerShell 后进入项目:"
Write-Host "  cd $projectDir"
Write-Host "  claude"
