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
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'default_search': 'ytsearch',
    'quiet': True,
    'no_warnings': True,
    'nocheckcertificate': True,
    'prefer_insecure': True,
    'geo_bypass': True,
    'geo_bypass_country': 'BR',
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-us,en;q=0.5',
        'Sec-Fetch-Mode': 'navigate',
    },
    'extractor_args': {
        'youtube': {
            'skip': ['dash', 'hls'],
            'player_skip': ['js', 'configs', 'webpage']
        }
    }
}

# Configurações de mensagens
MESSAGE_DELETE_TIMES = {
    'success': 60,  # 1 minuto
    'error': 180    # 3 minutos
} 