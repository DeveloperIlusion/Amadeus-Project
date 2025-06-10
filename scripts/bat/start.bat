@echo off
echo Configurando ambiente do Amadeus Neural Network...

REM Muda para o diretório raiz do projeto
cd /d "%~dp0\..\.."

REM Verifica se o Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo Python nao encontrado! Por favor, instale o Python 3.8 ou superior.
    pause
    exit /b 1
)

REM Cria o ambiente virtual se não existir
if not exist .venv (
    echo Criando ambiente virtual...
    python -m venv .venv
)

REM Ativa o ambiente virtual
echo Ativando ambiente virtual...
call .\.venv\Scripts\activate.bat

REM Instala as dependências
echo Instalando dependências...
pip install -r requirements.txt

REM Verifica se o FFmpeg está instalado
if not exist libraries\ffmpeg\bin\ffmpeg.exe (
    echo FFmpeg nao encontrado! Baixando FFmpeg...
    python src\config\setup.py
)

REM Inicia o bot
echo Iniciando Amadeus Neural Network...
python main.py

REM Mantém a janela aberta em caso de erro
pause 