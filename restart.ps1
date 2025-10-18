# 自动重启Flask应用脚本
# 每次启动前会先停止所有Python进程

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Flask 应用自动重启脚本" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# 1. 停止所有Python进程
Write-Host "正在停止所有Python进程..." -ForegroundColor Yellow
Get-Process python* -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

# 2. 验证进程已停止
$pythonProcesses = Get-Process python* -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    Write-Host "警告: 仍有Python进程在运行" -ForegroundColor Red
} else {
    Write-Host "✅ 所有Python进程已停止" -ForegroundColor Green
}

Write-Host ""

# 3. 启动Flask应用
Write-Host "正在启动Flask应用..." -ForegroundColor Yellow
Start-Process python -ArgumentList "app.py" -WindowStyle Normal

Start-Sleep -Seconds 3

# 4. 验证应用启动
$listening = netstat -ano | findstr :5000 | findstr LISTENING
if ($listening) {
    Write-Host "✅ Flask应用已成功启动！" -ForegroundColor Green
    Write-Host ""
    Write-Host "访问地址: http://localhost:5000" -ForegroundColor Cyan
} else {
    Write-Host "❌ Flask应用启动失败，请检查错误" -ForegroundColor Red
}

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan

