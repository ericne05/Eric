$dirs = @(
  "apps\desktop", "apps\brain", "apps\launcher", "apps\server",
  "core\brain", "core\planner", "core\reasoner", "core\dispatcher", "core\memory", "core\context", "core\scheduler", "core\events",
  "packages\shared", "packages\browser", "packages\windows", "packages\memory", "packages\automation", "packages\mcp",
  "tools\file-agent", "tools\terminal-agent", "tools\vscode-agent", "tools\database-agent",
  "tools\browser-agent\browser", "tools\browser-agent\tabs", "tools\browser-agent\dom", "tools\browser-agent\network", "tools\browser-agent\cookies", "tools\browser-agent\download", "tools\browser-agent\upload", "tools\browser-agent\cdp", "tools\browser-agent\screenshot",
  "plugins\browser", "plugins\discord", "plugins\github", "plugins\spotify", "plugins\custom",
  "storage\memory", "storage\vector", "storage\cache", "storage\logs", "storage\profiles", "storage\tasks", "storage\models", "storage\downloads", "storage\database",
  "resources\prompts", "resources\templates", "resources\icons", "resources\voices", "resources\ocr",
  "tests\unit", "tests\integration", "tests\agent",
  "scripts", "assets"
)

foreach ($dir in $dirs) {
  $path = Join-Path "D:\Projects\Eric" $dir
  if (-not (Test-Path $path)) {
    New-Item -ItemType Directory -Force -Path $path | Out-Null
  }
  $gitkeep = Join-Path $path ".gitkeep"
  if (-not (Test-Path $gitkeep)) {
    New-Item -ItemType File -Force -Path $gitkeep | Out-Null
  }
}
Write-Host "Success: All directories and .gitkeep files initialized."
