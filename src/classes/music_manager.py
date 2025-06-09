import discord
from discord.ext import commands
import asyncio
import yt_dlp
import subprocess
import os
from collections import deque
import time
from ..functions import get_ffmpeg_path, get_resource_path

class MusicManager:
    """
    Classe responsável por gerenciar a reprodução de música no Discord.
    Utiliza discord.py[voice] e yt-dlp para streaming de áudio.
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.queues = {}
        self.text_channels = {}
        self.current_songs = {}
        self.skip_votes = {}  # Armazena os votos de skip por servidor
        self.skip_in_progress = {}  # Controla se há uma votação em andamento
        self.last_user_check = {}  # Armazena o último momento em que havia usuários
        
        # Configura o caminho do FFmpeg
        self.ffmpeg_path = get_ffmpeg_path()
        
        # Verifica se o FFmpeg existe
        if not os.path.exists(self.ffmpeg_path):
            print(f"[ERRO] FFmpeg não encontrado em: {self.ffmpeg_path}")
            print("[ERRO] Por favor, verifique se o FFmpeg está instalado e o caminho está correto.")
            raise FileNotFoundError(f"FFmpeg não encontrado em: {self.ffmpeg_path}")
        
        # Inicia a task de verificação de usuários
        self.bot.loop.create_task(self.check_empty_channels())
        
        # Configura o caminho do arquivo de cookies
        self.cookies_path = get_resource_path("src/config/cookies.txt")
        print(f"[DEBUG] Caminho do cookies.txt: {self.cookies_path}")
        
        # Gera o arquivo de cookies se não existir
        if not os.path.exists(self.cookies_path):
            print("[DEBUG] Arquivo de cookies não encontrado, gerando novo arquivo...")
            self.generate_cookies()
        
        # Verifica se o arquivo de cookies existe e está no formato correto
        if os.path.exists(self.cookies_path):
            print(f"[DEBUG] Arquivo de cookies encontrado em: {self.cookies_path}")
            try:
                with open(self.cookies_path, 'r') as f:
                    first_line = f.readline().strip()
                    if first_line.startswith('# Netscape HTTP Cookie File'):
                        print("[DEBUG] Arquivo de cookies está no formato correto")
                    else:
                        print(f"[AVISO] Arquivo de cookies em formato inválido: {self.cookies_path}")
                        print("[AVISO] Gerando novo arquivo de cookies...")
                        self.generate_cookies()
            except Exception as e:
                print(f"[AVISO] Erro ao verificar arquivo de cookies: {str(e)}")
                print("[AVISO] Gerando novo arquivo de cookies...")
                self.generate_cookies()
        else:
            print(f"[AVISO] Arquivo de cookies não encontrado em: {self.cookies_path}")
            print("[AVISO] O bot pode ter problemas para acessar alguns vídeos.")
            print("[AVISO] Gerando novo arquivo de cookies...")
            self.generate_cookies()
        
        # Configurações do yt-dlp
        self.ytdl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'default_search': 'auto',
            'nocheckcertificate': True,
            'prefer_insecure': True,
            'geo_bypass': True,
            'geo_bypass_country': 'BR',
            'cookiefile': self.cookies_path,  # Usa apenas o arquivo de cookies
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Sec-Fetch-Mode': 'navigate',
            }
        }

    async def check_empty_channels(self):
        """Verifica periodicamente se há canais vazios e desconecta o bot"""
        while True:
            try:
                # Obtém todos os voice clients ativos
                voice_clients = [vc for vc in self.bot.voice_clients if vc and vc.is_connected()]
                
                for voice_client in voice_clients:
                    guild_id = voice_client.guild.id
                    
                    # Conta apenas usuários reais (não bots) no canal
                    real_users = [m for m in voice_client.channel.members if not m.bot]
                    
                    if not real_users:
                        # Se não houver usuários, verifica se já passou 3 minutos
                        current_time = time.time()
                        last_check = self.last_user_check.get(guild_id, current_time)
                        
                        if current_time - last_check >= 180:  # 3 minutos = 180 segundos
                            print(f"[DEBUG] Desconectando do canal vazio em {guild_id}")
                            # Limpa a fila e o estado
                            if guild_id in self.queues:
                                self.queues[guild_id].clear()
                            self.end_skip_vote(guild_id)
                            # Desconecta o bot
                            await voice_client.disconnect()
                            # Envia mensagem no canal de texto se disponível
                            if guild_id in self.text_channels:
                                try:
                                    await self.text_channels[guild_id].send(
                                        "👋 Desconectei do canal de voz por inatividade."
                                    )
                                except:
                                    pass
                    else:
                        # Se houver usuários, atualiza o timestamp
                        self.last_user_check[guild_id] = time.time()

            except Exception as e:
                print(f"[DEBUG] Erro ao verificar canais vazios: {e}")
                import traceback
                print(f"[DEBUG] Stack trace: {traceback.format_exc()}")

            # Verifica a cada 30 segundos
            await asyncio.sleep(30)

    async def send_and_delete(self, channel, message, success=True):
        """Envia uma mensagem e a deleta após um tempo"""
        try:
            # Envia a mensagem
            response = await channel.send(message)
            
            # Define o tempo de espera (1 minuto para sucesso, 3 para erro)
            wait_time = 60 if success else 180
            
            # Espera e deleta a resposta em uma task separada
            async def delete_message():
                try:
                    await asyncio.sleep(wait_time)
                    await response.delete()
                except Exception as e:
                    print(f"Erro ao deletar mensagem: {e}")
            
            # Cria uma task separada para deletar a mensagem
            asyncio.create_task(delete_message())
            
        except Exception as e:
            print(f"Erro ao gerenciar mensagens: {e}")

    def get_queue(self, guild_id):
        """Retorna a fila de músicas do servidor"""
        if guild_id not in self.queues:
            self.queues[guild_id] = deque()
        elif not isinstance(self.queues[guild_id], deque):
            # Se por algum motivo a fila não for um deque, converte para deque
            self.queues[guild_id] = deque(self.queues[guild_id])
        return self.queues[guild_id]

    async def join_voice(self, channel):
        try:
            # Se já estiver conectado no mesmo canal, retorna o voice_client
            if channel.guild.voice_client and channel.guild.voice_client.channel == channel:
                return channel.guild.voice_client
            
            # Se estiver em outro canal, desconecta
            if channel.guild.voice_client:
                await channel.guild.voice_client.disconnect()
            
            # Conecta ao novo canal
            voice_client = await channel.connect()
            return voice_client
        except Exception as e:
            print(f"Erro ao conectar ao canal de voz: {e}")
            return None

    async def leave_voice(self, guild_id):
        try:
            guild = self.bot.get_guild(guild_id)
            if guild and guild.voice_client:
                await guild.voice_client.disconnect()
                # Limpa a fila ao sair
                if guild_id in self.queues:
                    self.queues[guild_id].clear()
        except Exception as e:
            print(f"Erro ao desconectar do canal de voz: {e}")

    async def play_next(self, voice_client, guild_id):
        """Toca a próxima música da fila"""
        if not self.queue:
            print("[DEBUG] Fila vazia, retornando")
            return

        # Verifica se o FFmpeg está funcionando
        try:
            result = subprocess.run(
                [str(self.ffmpeg_path), "-version"],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"[DEBUG] FFmpeg versão: {result.stdout.splitlines()[0]}")
        except Exception as e:
            print(f"[DEBUG] Erro ao verificar FFmpeg: {e}")
            return

        # Verifica se já está tocando
        if voice_client.is_playing():
            return

        # Pega a próxima música da fila
        queue = self.queue[guild_id]
        if not queue:
            return

        next_song = queue[0]
        print(f"[DEBUG] Próxima música: {next_song['title']}")
        print(f"[DEBUG] URL: {next_song['url']}")

        def after_playing(error):
            """Callback após a música terminar"""
            print("[DEBUG] Música terminou, chamando play_next")
            if queue:
                queue.popleft()  # Remove a música que acabou de tocar
                print(f"[DEBUG] Música removida da fila após terminar. Tamanho atual: {len(queue)}")
            asyncio.run_coroutine_threadsafe(self.play_next(voice_client, guild_id), self.bot.loop)

        try:
            # Configurações do FFmpeg para melhor qualidade e estabilidade
            ffmpeg_options = {
                'options': '-vn -b:a 192k -ar 48000 -ac 2 -loglevel error',
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
            }

            # Toca a música
            print("[DEBUG] Iniciando FFmpegPCMAudio")
            print(f"[DEBUG] Caminho do FFmpeg: {self.ffmpeg_path}")
            print(f"[DEBUG] Opções do FFmpeg: {ffmpeg_options}")
            
            voice_client.play(
                discord.FFmpegPCMAudio(
                    next_song['url'],
                    executable=str(self.ffmpeg_path),
                    **ffmpeg_options
                ),
                after=after_playing
            )
            print("[DEBUG] FFmpegPCMAudio iniciado com sucesso")

            # Envia mensagem no canal de texto apenas quando uma nova música começa a tocar
            if hasattr(voice_client, 'channel') and voice_client.channel:
                try:
                    await voice_client.channel.send(f"🎵 Tocando agora: **{next_song['title']}**")
                    print("[DEBUG] Mensagem de reprodução enviada")
                except Exception as e:
                    print(f"[DEBUG] Erro ao enviar mensagem de reprodução: {e}")

        except Exception as e:
            print(f"[DEBUG] Erro ao tocar música: {e}")
            import traceback
            print(f"[DEBUG] Stack trace: {traceback.format_exc()}")
            # Se der erro, tenta tocar a próxima
            if queue:
                queue.popleft()  # Remove a música que falhou
            await self.play_next(voice_client, guild_id)

    async def play_audio(self, voice_client, search: str, text_channel=None):
        """Reproduz áudio do YouTube"""
        try:
            # Verifica se o usuário está em um canal de voz
            if not voice_client.is_connected():
                await text_channel.send("❌ Você precisa estar em um canal de voz para usar este comando!")
                return {'success': False, 'error': 'Você precisa estar em um canal de voz!'}

            # Conecta ao canal de voz se não estiver conectado
            if not voice_client.is_connected():
                await voice_client.connect()
            # Se estiver em outro canal, move para o canal do usuário
            elif voice_client.channel != voice_client.channel:
                await voice_client.move_to(voice_client.channel)

            # Configurações do yt-dlp
            ydl_opts = {
                'format': 'bestaudio/best',
                'noplaylist': True,
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'default_search': 'auto',
                'nocheckcertificate': True,
                'prefer_insecure': True,
                'geo_bypass': True,
                'geo_bypass_country': 'BR',
                'cookiefile': self.cookies_path,  # Usa apenas o arquivo de cookies
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-us,en;q=0.5',
                    'Sec-Fetch-Mode': 'navigate',
                }
            }

            # Verifica se é uma URL do YouTube
            if not search.startswith(('http://', 'https://')):
                search = f"ytsearch:{search}"

            print(f"[DEBUG] Buscando com yt-dlp: {search}")
            
            # Tenta extrair informações do vídeo
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    print("[DEBUG] Iniciando extração de informações...")
                    try:
                        info = ydl.extract_info(search, download=False)
                        print(f"[DEBUG] Informações extraídas: {info is not None}")
                    except Exception as e:
                        print(f"[DEBUG] Erro na extração: {str(e)}")
                        # Tenta novamente com configurações mais básicas
                        ydl_opts['nocheckcertificate'] = True
                        ydl_opts['prefer_insecure'] = True
                        info = ydl.extract_info(search, download=False)
                    
                    if not info:
                        print("[DEBUG] Nenhuma informação retornada pelo yt-dlp")
                        await text_channel.send("❌ Não foi possível encontrar o vídeo. Por favor, tente novamente.")
                        return {'success': False, 'error': 'Não foi possível encontrar o vídeo.'}
                        
                    if 'entries' in info:
                        if not info['entries']:
                            print("[DEBUG] Lista de resultados vazia")
                            await text_channel.send("❌ Nenhum resultado encontrado para sua busca!")
                            return {'success': False, 'error': 'Nenhum resultado encontrado!'}
                        info = info['entries'][0]
                        print(f"[DEBUG] Primeiro resultado encontrado: {info.get('title', 'Sem título')}")
                        
                    if not info or not info.get('url'):
                        print("[DEBUG] URL não encontrada nas informações do vídeo")
                        await text_channel.send("❌ Não foi possível obter a URL do áudio!")
                        return {'success': False, 'error': 'Não foi possível obter a URL do áudio.'}
                        
                    # Adiciona à fila
                    guild_id = voice_client.guild.id
                    if guild_id not in self.queues:
                        self.queues[guild_id] = deque()
                        self.text_channels[guild_id] = text_channel
                        
                    self.queues[guild_id].append({
                        'url': info['url'],
                        'title': info.get('title', 'Título desconhecido'),
                        'duration': info.get('duration', 0),
                        'info': {
                            'title': info.get('title', 'Título desconhecido'),
                            'url': info['url']
                        }
                    })
                    
                    # Se não estiver tocando nada, inicia a reprodução
                    if not voice_client.is_playing():
                        await self.play_next(voice_client, guild_id)
                        return {
                            'success': True,
                            'message': f"🎵 Tocando agora: **{info.get('title', 'Título desconhecido')}**",
                            'is_playing': True
                        }
                    else:
                        return {
                            'success': True,
                            'message': f"🎵 Adicionado à fila: **{info.get('title', 'Título desconhecido')}**",
                            'is_playing': False
                        }
                        
            except Exception as e:
                print(f"[DEBUG] Erro na busca: {str(e)}")
                print(f"[DEBUG] Tipo do erro: {type(e)}")
                import traceback
                print(f"[DEBUG] Stack trace: {traceback.format_exc()}")
                return {'success': False, 'error': str(e)}
                
        except Exception as e:
            print(f"[DEBUG] Erro geral: {str(e)}")
            return {'success': False, 'error': str(e)}

    async def skip(self, voice_client, guild_id):
        """Pula para a próxima música"""
        if voice_client.is_playing():
            voice_client.stop()
            # Reseta o estado de votação de skip
            self.end_skip_vote(guild_id)
            return True
        return False

    async def stop(self, voice_client, guild_id):
        """Para a reprodução e limpa a fila"""
        if voice_client.is_playing():
            voice_client.stop()
        queue = self.get_queue(guild_id)
        queue.clear()
        # Limpa o estado de votação de skip
        self.end_skip_vote(guild_id)
        return True

    def get_queue_list(self, guild_id):
        """Retorna uma string formatada com a lista de músicas na fila"""
        queue = self.get_queue(guild_id)
        if not queue:
            return "A fila está vazia!"
        
        queue_list = ""
        for i, song in enumerate(queue, 1):
            title = song['info'].get('title', 'Música desconhecida')
            queue_list += f"{i}. {title}\n"
        return queue_list

    def get_current_song(self, guild_id):
        """Retorna a música atual que está tocando"""
        queue = self.get_queue(guild_id)
        if queue:
            return queue[0]['info'].get('title', 'Música desconhecida')
        return None 

    def can_start_skip_vote(self, guild_id):
        """Verifica se uma nova votação de skip pode ser iniciada"""
        return not self.skip_in_progress.get(guild_id, False)

    def start_skip_vote(self, guild_id):
        """Inicia uma nova votação de skip"""
        self.skip_in_progress[guild_id] = True
        self.skip_votes[guild_id] = set()

    def end_skip_vote(self, guild_id):
        """Finaliza a votação de skip atual"""
        self.skip_in_progress[guild_id] = False
        self.skip_votes[guild_id] = set()

    def add_skip_vote(self, guild_id, user_id):
        """Adiciona um voto de skip"""
        if guild_id in self.skip_votes:
            self.skip_votes[guild_id].add(user_id)
            return len(self.skip_votes[guild_id])
        return 0

    def get_skip_votes(self, guild_id):
        """Retorna o número de votos atuais"""
        return len(self.skip_votes.get(guild_id, set()))

    def generate_cookies(self):
        """Gera um novo arquivo de cookies usando o yt-dlp"""
        try:
            print("[DEBUG] Iniciando geração de cookies...")
            # Configurações para gerar cookies
            ydl_opts = {
                'cookiefile': self.cookies_path,
                'cookiesfrombrowser': None,
                'quiet': True,
                'no_warnings': True,
                'nocheckcertificate': True,
                'prefer_insecure': True,
                'geo_bypass': True,
                'geo_bypass_country': 'BR',
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                }
            }
            
            # Tenta acessar o YouTube para gerar cookies
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info('https://www.youtube.com/watch?v=dQw4w9WgXcQ', download=False)
            
            print("[DEBUG] Arquivo de cookies gerado com sucesso!")
        except Exception as e:
            print(f"[ERRO] Falha ao gerar arquivo de cookies: {str(e)}")
            print("[ERRO] O bot pode ter problemas para acessar alguns vídeos.")