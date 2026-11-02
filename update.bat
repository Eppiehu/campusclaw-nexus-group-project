@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy\nexus-deploy.ps1" -Update %*
set "nexus_exit=%errorlevel%"
if not "%nexus_exit%"=="0" (
  echo.
  echo Nexus update failed. See the error above.
  if not defined NEXUS_NO_PAUSE pause
)
exit /b %nexus_exit%
