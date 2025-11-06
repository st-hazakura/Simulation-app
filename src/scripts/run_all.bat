@echo off
setlocal

REM ======= Nastaveni ========
REM Normalizace cesty ke korenu pojektu bez \..\..
for %%I in ("%~dp0..\..") do set "ROOT=%%~fI"

REM cesta g generatoru vstupnich souboru a souboru s privanti data
set "GEN_PY=%ROOT%\src\simapp\generate_input.py"
set "ENV_FILE=%ROOT%\.env"


if not exist "%GEN_PY%" (
  echo [ERR] Nenalezen generate_input.py: "%GEN_PY%"
  popd & exit /b 1
)

REM Cteme promene z .env (radky s # ignorujeme)
if exist "%ENV_FILE%" (
  for /f "usebackq eol=# delims=" %%L in ("%ENV_FILE%") do set "%%L"
) else (
  echo [WARN] .env neexistuje: "%ENV_FILE%"
)


REM ======= Krok 1: Generuju vystupni soubory... ========
echo [1/3] Generuju vystupni soubory...
for /f "usebackq delims=" %%i in (`python "%GEN_PY%"`) do set "SIM_FOLDER=%%i"


REM Overeni: jestli se nevratila slozka simulace - vratit se
if "%SIM_FOLDER%"=="" (
    echo Chyba: Jmeno slozky simulace nebylo nalezene
    pause
    exit /b
)

echo Vytvorena slozka: %SIM_FOLDER%

REM ======= Krok 2: Kopirovani  ========
echo [2/3] Kopiruju slozku na kluster...
pscp -i "%CLUSTER_KEY_PATH%" -r "%SIM_FOLDER%" %CLUSTER_USERNAME%@%CLUSTER_HOST%:"%CLUSTER_SIMULATION_DIR%"


REM ======= Krok 3: Spousteni na klusteru ========
echo [3/3] Spoustim simulace...
plink -batch -i "%CLUSTER_KEY_PATH%" %CLUSTER_USERNAME%@%CLUSTER_HOST% "cd %CLUSTER_SIMULATION_DIR%/%SIM_FOLDER% && bash submit_job.sh"

echo ---------------------------------------
echo Hotovo, simulace spustena na clusteru.



rmdir /s /q "%SIM_FOLDER%"