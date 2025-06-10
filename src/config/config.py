"""
Arquivo de configuração do bot.
Aqui ficam todas as constantes e configurações do sistema.
"""
import os
from pathlib import Path
from ..functions import get_ffmpeg_path, get_resource_path

# Obtém o diretório raiz do projeto
ROOT_DIR = Path(__file__).parent.parent.parent

# Token do bot
BOT_TOKEN = 'MTM4MDg3NDU1NTIwNzMyMzY1OQ.Ge7AJ5.sSx2WjIi-ZJlwLlge8sOjpOzhxdIdSV-n3KJI8'

# Configurações do FFmpeg
FFMPEG_PATH = os.path.join(ROOT_DIR, "ffmpeg", "bin", "ffmpeg.exe")

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