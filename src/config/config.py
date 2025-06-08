"""
Arquivo de configuração do bot.
Aqui ficam todas as constantes e configurações do sistema.
"""
from ..functions import get_ffmpeg_path

# Token do bot
BOT_TOKEN = 'MTM4MDg3NDU1NTIwNzMyMzY1OQ.Ge7AJ5.sSx2WjIi-ZJlwLlge8sOjpOzhxdIdSV-n3KJI8'

# Configurações do FFmpeg
FFMPEG_PATH = get_ffmpeg_path()

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
    'no_warnings': True
}

# Configurações de mensagens
MESSAGE_DELETE_TIMES = {
    'success': 60,  # 1 minuto
    'error': 180    # 3 minutos
} 