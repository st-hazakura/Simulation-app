@echo off
REM Load .env from repo root (KEY=VALUE; lines starting with # are ignored)
set "ENV_FILE=%~dp0..\..\.env"
if exist "%ENV_FILE%" (
  for /f "usebackq eol=# delims=" %%L in ("%ENV_FILE%") do set "%%L"
) else (
  echo Warn: .env not found at "%ENV_FILE%"
)
