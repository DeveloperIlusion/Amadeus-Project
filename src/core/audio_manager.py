import discord
from discord.ext import commands
import asyncio
import yt_dlp
import subprocess
import os
from collections import deque
import time
from ..utils.functions import get_ffmpeg_path, get_resource_path
from ..config.settings import YTDL_OPTIONS, COOKIES_PATH
import certifi
import ssl

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
        
        # Inicia a task de verificação de usuários
        self.bot.loop.create_task(self.check_empty_channels())
        
        # Configura o caminho do arquivo de cookies
        self.cookies_path = COOKIES_PATH
        print(f"[DEBUG] Caminho do cookies.txt: {self.cookies_path}")
        
        # Configura o certificado SSL
        os.environ['SSL_CERT_FILE'] = certifi.where()
        
        # Configurações do yt-dlp
        self.ytdl_opts = YTDL_OPTIONS.copy()

    async def check_empty_channels(self):
        """Verifica periodicamente se há canais vazios e desconecta o bot"""
        while True:
            try:
                # Obtém todos os voice clients ativos
                voice_clients = [vc for vc in self.bot.voice_clients if vc and vc.is_connected()]
                
                for voice_client in voice_clients:
                    guild_id = voice_client.guild.id
                    current_time = time.time()  # Define current_time aqui
                    
                    # Conta apenas usuários reais (não bots) no canal
                    real_users = [m for m in voice_client.channel.members if not m.bot]
                    
                    if not real_users:
                        # Se não houver usuários, verifica se já passou 3 minutos
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
                        # Se houver usuários, reseta o último check
                        self.last_user_check[guild_id] = current_time
                
                # Espera 30 segundos antes da próxima verificação
                await asyncio.sleep(30)
                
            except Exception as e:
                print(f"[ERRO] Erro ao verificar canais vazios: {e}")
                await asyncio.sleep(30)  # Espera 30 segundos mesmo em caso de erro

    async def join_voice(self, channel):
        """Conecta ao canal de voz"""
        try:
            # Verifica se já está conectado a algum canal
            if channel.guild.voice_client:
                # Se estiver em outro canal, move para o novo
                if channel.guild.voice_client.channel != channel:
                    await channel.guild.voice_client.move_to(channel)
                return channel.guild.voice_client
            
            # Se não estiver conectado, conecta ao novo canal
            return await channel.connect()
            
        except Exception as e:
            print(f"[ERRO] Erro ao conectar ao canal de voz: {e}")
            return None

    def get_queue(self, guild_id):
        """Retorna a fila de músicas do servidor"""
        if guild_id not in self.queues:
            self.queues[guild_id] = deque()
        return self.queues[guild_id]

    async def play_next(self, voice_client, guild_id):
        """Toca a próxima música da fila"""
        try:
            # Verifica se o FFmpeg está funcionando
            try:
                ffmpeg_version = subprocess.check_output([str(self.ffmpeg_path), '-version']).decode()
                print(f"[DEBUG] FFmpeg versão: {ffmpeg_version.split()[2]}")
            except Exception as e:
                print(f"[ERRO] FFmpeg não está funcionando corretamente: {e}")
                return

            queue = self.get_queue(guild_id)
            if not queue:
                print("[DEBUG] Fila vazia, nada para tocar")
                return

            # Pega a próxima música da fila
            song = queue[0]
            url = song['url']
            title = song['title']

            print(f"[DEBUG] Preparando para tocar: {title}")
            print(f"[DEBUG] URL: {url}")

            def after_playing(error):
                """Callback após a música terminar"""
                if error:
                    print(f"[DEBUG] Erro na reprodução: {error}")
                print("[DEBUG] Música terminou, chamando play_next")
                # Remove a música da fila apenas quando terminar de tocar
                if queue:
                    queue.popleft()
                    print(f"[DEBUG] Música removida da fila após terminar. Tamanho atual: {len(queue)}")
                # Cria uma nova task para tocar a próxima música
                asyncio.run_coroutine_threadsafe(
                    self.play_next(voice_client, guild_id),
                    self.bot.loop
                )

            try:
                # Configurações do FFmpeg para evitar cortes
                ffmpeg_options = {
                    'options': '-vn -b:a 192k -ar 48000 -ac 2 -loglevel error',
                    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
                }

                # Toca a música
                print("[DEBUG] Iniciando FFmpegPCMAudio")
                print(f"[DEBUG] Caminho do FFmpeg: {self.ffmpeg_path}")
                print(f"[DEBUG] Opções do FFmpeg: {ffmpeg_options}")
                
                # Verifica se a URL é válida
                try:
                    response = subprocess.run(
                        [str(self.ffmpeg_path), '-i', url, '-f', 'null', '-'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    print(f"[DEBUG] Teste de URL: {response.stderr}")
                except Exception as e:
                    print(f"[DEBUG] Erro ao testar URL: {e}")
                
                voice_client.play(
                    discord.FFmpegPCMAudio(
                        url,
                        executable=str(self.ffmpeg_path),
                        **ffmpeg_options
                    ),
                    after=after_playing
                )
                print("[DEBUG] FFmpegPCMAudio iniciado com sucesso")

                # Envia mensagem no canal de texto apenas quando uma nova música começa a tocar
                if guild_id in self.text_channels:
                    channel = self.text_channels[guild_id]
                    try:
                        await channel.send(f"🎵 Tocando agora: **{title}**")
                        print("[DEBUG] Mensagem de reprodução enviada")
                    except Exception as e:
                        print(f"[DEBUG] Erro ao enviar mensagem de reprodução: {e}")

            except Exception as e:
                print(f"[ERRO] Erro ao tocar música: {e}")
                import traceback
                print(f"[DEBUG] Stack trace: {traceback.format_exc()}")
                # Se der erro, tenta tocar a próxima
                if queue:
                    queue.popleft()  # Remove a música que falhou
                await self.play_next(voice_client, guild_id)

        except Exception as e:
            print(f"[ERRO] Erro em play_next: {e}")
            import traceback
            print(f"[DEBUG] Stack trace: {traceback.format_exc()}")

    async def play_audio(self, voice_client, text_channel, search):
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

            # Verifica se é uma URL do YouTube
            if not search.startswith(('http://', 'https://')):
                search = f"ytsearch:{search}"

            print(f"[DEBUG] Buscando com yt-dlp: {search}")
            
            # Tenta extrair informações do vídeo
            try:
                with yt_dlp.YoutubeDL(self.ytdl_opts) as ydl:
                    print("[DEBUG] Iniciando extração de informações...")
                    info = ydl.extract_info(search, download=False)
                    print(f"[DEBUG] Informações extraídas: {info is not None}")
                    
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
                'quiet': True,
                'no_warnings': True,
                'cookiefile': self.cookies_path,
                'cookiesfrombrowser': ('chrome',),  # Tenta pegar cookies do Chrome
                'cookiesfrombrowserargs': ['--user-data-dir=Default']  # Perfil padrão do Chrome
            }
            
            # Tenta gerar o arquivo de cookies
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download(['https://www.youtube.com/watch?v=dQw4w9WgXcQ'])  # Vídeo de teste
                
            print("[DEBUG] Arquivo de cookies gerado com sucesso!")
            return True
            
        except Exception as e:
            print(f"[ERRO] Erro ao gerar cookies: {e}")
            return False