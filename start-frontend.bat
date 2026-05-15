@echo off
REM Script de inicialização do frontend (Windows)
cd /d "%~dp0frontend"
if not exist node_modules (
    echo Instalando dependencias...
    npm install
)
npm run dev
