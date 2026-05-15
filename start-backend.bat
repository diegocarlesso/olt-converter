@echo off
REM ============================================================
REM  OLT Config Converter Engine — Backend (Windows)
REM ============================================================
REM  - Tenta primeiro Python 3.13 (mais estavel), depois 3.12, e
REM    apenas como ultimo recurso 3.14 (que ainda quebra alguns
REM    pacotes que dependem de PyO3/Rust).
REM  - Recria a venv automaticamente se o python associado a ela
REM    nao for mais o desejado.
REM ============================================================
cd /d "%~dp0backend"

set "PYTHON_CMD="
for %%V in (3.13 3.12 3.14 3) do (
    if not defined PYTHON_CMD (
        py -%%V -c "import sys; sys.exit(0)" >nul 2>&1
        if not errorlevel 1 set "PYTHON_CMD=py -%%V"
    )
)
if not defined PYTHON_CMD set "PYTHON_CMD=python"

echo Usando interpretador: %PYTHON_CMD%

REM Habilita compatibilidade futura do PyO3 caso o pip caia em build local
set PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1

if not exist .venv (
    echo Criando virtualenv...
    %PYTHON_CMD% -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
