@echo off
setlocal
rem Manual diagnostic only: keep the existing Edge profile and protection settings.
set "KO_EDGE=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if not exist "%KO_EDGE%" set "KO_EDGE=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
if not exist "%KO_EDGE%" (
  echo Microsoft Edge was not found.
  pause
  exit /b 1
)
start "" "%KO_EDGE%" "--user-data-dir=%~dp0..\artifacts\edge-check-profile" --no-first-run --no-default-browser-check http://127.0.0.1:8081/stage
endlocal
