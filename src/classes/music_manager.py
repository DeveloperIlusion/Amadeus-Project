import discord
from discord.ext import commands
import asyncio
import yt_dlp
import subprocess
import os
from collections import deque
import time

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
        if os.name == 'nt':  # Windows
            self.ffmpeg_path = r"D:\Backup\Biblioteca\Projetos\Programming\Ilusory Land Maid\libraries\ffmpeg-master-latest-win64-gpl-shared\bin\ffmpeg.exe"
        else:  # Linux/Mac
            self.ffmpeg_path = 'ffmpeg'
        
        # Verifica se o FFmpeg existe
        if not os.path.exists(self.ffmpeg_path):
            print(f"[ERRO] FFmpeg não encontrado em: {self.ffmpeg_path}")
            print("[ERRO] Por favor, verifique se o FFmpeg está instalado e o caminho está correto.")
            raise FileNotFoundError(f"FFmpeg não encontrado em: {self.ffmpeg_path}")
        
        # Inicia a task de verificação de usuários
        self.bot.loop.create_task(self.check_empty_channels())
        
        # Configurações do yt-dlp
        self.ytdl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'default_search': 'auto',
            'source_address': '0.0.0.0',
            'force-ipv4': True,
            'cachedir': False,
            'no_cache': True,
            'rm_cachedir': True,
            'ignoreerrors': True,
            'logtostderr': False,
            'no_warnings': True,
            'quiet': True,
            'no_color': True,
            'socket_timeout': 30,
            'retries': 10,
            'file_access_retries': 10,
            'fragment_retries': 10,
            'extractor_retries': 10,
            'skip_download': True,
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'postprocessor_args': [
                '-ar', '48000',
                '-ac', '2',
                '-b:a', '192k'
            ],
            'cookiefile': 'cookies.txt'
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
        if guild_id not in self.queues:
            self.queues[guild_id] = deque()
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
        queue = self.get_queue(guild_id)
        print(f"[DEBUG] play_next chamado. Tamanho da fila: {len(queue)}")
        
        if not queue:
            print("[DEBUG] Fila vazia, retornando")
            return

        try:
            # Verifica se já está tocando
            if voice_client.is_playing():
                print("[DEBUG] Já está tocando, aguardando...")
                return

            # Pega a próxima música da fila
            next_song = queue[0]
            info = next_song['info']
            title = info.get('title', 'Música desconhecida')
            url = info['url']
            print(f"[DEBUG] Próxima música: {title}")
            print(f"[DEBUG] URL: {url}")

            # Atualiza a música atual
            self.current_songs[guild_id] = title
            # Reseta o estado de votação de skip
            self.end_skip_vote(guild_id)

            # Configurações do FFmpeg para evitar cortes
            ffmpeg_options = {
                'options': '-vn -b:a 192k -ar 48000 -ac 2',
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -analyzeduration 0 -loglevel 0'
            }

            # Função para tocar a próxima música
            def after_playing(error):
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

            print("[DEBUG] Iniciando FFmpegPCMAudio")
            
            # Tenta baixar o áudio primeiro
            with yt_dlp.YoutubeDL(self.ytdl_opts) as ydl:
                try:
                    print("[DEBUG] Baixando áudio...")
                    info = ydl.extract_info(url, download=False)
                    audio_url = info['url']
                    print("[DEBUG] Áudio baixado com sucesso")
                except Exception as e:
                    print(f"[DEBUG] Erro ao baixar áudio: {e}")
                    raise e

            # Toca a música
            voice_client.play(
                discord.FFmpegPCMAudio(
                    audio_url,
                    executable=self.ffmpeg_path,
                    **ffmpeg_options
                ),
                after=after_playing
            )
            print("[DEBUG] FFmpegPCMAudio iniciado")

            # Envia mensagem no canal de texto apenas quando uma nova música começa a tocar
            if guild_id in self.text_channels:
                channel = self.text_channels[guild_id]
                try:
                    await channel.send(f"🎵 Tocando agora: **{title}**")
                    print("[DEBUG] Mensagem de reprodução enviada")
                except Exception as e:
                    print(f"[DEBUG] Erro ao enviar mensagem de reprodução: {e}")

        except Exception as e:
            print(f"[DEBUG] Erro detalhado ao tocar próxima música: {str(e)}")
            print(f"[DEBUG] Tipo do erro: {type(e)}")
            import traceback
            print(f"[DEBUG] Stack trace: {traceback.format_exc()}")
            # Se der erro, tenta tocar a próxima
            if queue:
                queue.popleft()  # Remove a música que falhou
            await self.play_next(voice_client, guild_id)

    async def play_audio(self, voice_client, search, text_channel=None):
        try:
            # Atualiza o timestamp de verificação de usuários
            self.last_user_check[voice_client.guild.id] = time.time()
            
            print(f"[DEBUG] Iniciando busca por: {search}")
            with yt_dlp.YoutubeDL(self.ytdl_opts) as ydl:
                # Se não for uma URL, adiciona o prefixo de busca
                if not search.startswith(('http://', 'https://')):
                    search = f"ytsearch:{search}"
                print(f"[DEBUG] Buscando com yt-dlp: {search}")
                
                info = ydl.extract_info(search, download=False)
                print(f"[DEBUG] Informações obtidas: {info.get('title', 'Sem título')}")
                
                # Se for uma busca, pega o primeiro resultado
                if 'entries' in info:
                    info = info['entries'][0]
                    print(f"[DEBUG] Primeiro resultado da busca: {info.get('title', 'Sem título')}")
                
                title = info.get('title', 'Música desconhecida')
                print(f"[DEBUG] Título final: {title}")
                
                # Armazena o canal de texto para mensagens
                if text_channel:
                    self.text_channels[voice_client.guild.id] = text_channel
                    print(f"[DEBUG] Canal de texto armazenado para guild {voice_client.guild.id}")

                # Adiciona à fila
                queue = self.get_queue(voice_client.guild.id)
                queue.append({'info': info})
                print(f"[DEBUG] Música adicionada à fila. Tamanho atual: {len(queue)}")

                # Se não estiver tocando nada, começa a tocar
                if not voice_client.is_playing():
                    print("[DEBUG] Iniciando reprodução...")
                    # Cria uma task separada para iniciar a reprodução
                    asyncio.create_task(self.play_next(voice_client, voice_client.guild.id))
                    return {
                        'success': True,
                        'title': title,
                        'message': f"🎵 Adicionado à fila: **{title}**",
                        'is_playing': True
                    }
                else:
                    print("[DEBUG] Música adicionada à fila (já está tocando)")
                    return {
                        'success': True,
                        'title': title,
                        'message': f"🎵 Adicionado à fila: **{title}**",
                        'is_playing': False
                    }

        except Exception as e:
            print(f"[DEBUG] Erro detalhado ao tocar áudio: {str(e)}")
            print(f"[DEBUG] Tipo do erro: {type(e)}")
            import traceback
            print(f"[DEBUG] Stack trace: {traceback.format_exc()}")
            return {
                'success': False,
                'error': str(e)
            }

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