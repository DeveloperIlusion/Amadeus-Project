"""
Arquivo de configuração do bot.
Aqui ficam todas as constantes e configurações do sistema.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from ..utils.functions import get_ffmpeg_path, get_resource_path, get_project_root

# Obtém o diretório raiz do projeto
ROOT_DIR = get_project_root()

# Carrega as variáveis de ambiente do arquivo .env
env_path = ROOT_DIR / "src" / "config" / ".env"
load_dotenv(dotenv_path=env_path)

# Token do bot
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("Token do bot não encontrado! Verifique se o arquivo .env existe em src/config/ e contém BOT_TOKEN.")

# Configurações do FFmpeg
FFMPEG_PATH = get_ffmpeg_path()

# Configurações do arquivo de cookies
COOKIES_PATH = get_resource_path("src/config/cookies.txt")

# Configurações do bot
COMMAND_PREFIX = "!"  # Prefixo para comandos do bot

# Configurações do YouTube
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': False,
    'no_warnings': False,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'cookiefile': COOKIES_PATH
}

# Configurações de mensagens
MESSAGE_DELETE_TIMES = {
    'success': 60,  # 1 minuto
    'error': 180    # 3 minutos
} 