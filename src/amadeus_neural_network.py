import discord
from discord.ext import commands
import sys
import os
import asyncio

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.classes.music_manager import MusicManager
from src.config.config import BOT_TOKEN, YTDL_OPTIONS, MESSAGE_DELETE_TIMES

# Configuração do bot
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix='/', intents=intents)

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.music = MusicManager(bot)

    async def send_and_delete(self, ctx, message, success=True):
        """Envia uma mensagem e a deleta após um tempo"""
        try:
            # Deleta a mensagem do comando imediatamente
            try:
                await ctx.message.delete()
            except Exception as e:
                print(f"Erro ao deletar comando: {e}")
            
            # Envia a resposta
            response = await ctx.send(message)
            
            # Define o tempo de espera (1 minuto para sucesso, 3 para erro)
            wait_time = MESSAGE_DELETE_TIMES['success'] if success else MESSAGE_DELETE_TIMES['error']
            
            # Espera e deleta a resposta em uma task separada
            async def delete_response():
                try:
                    await asyncio.sleep(wait_time)
                    await response.delete()
                except Exception as e:
                    print(f"Erro ao deletar resposta: {e}")
            
            # Cria uma task separada para deletar a resposta
            asyncio.create_task(delete_response())
            
        except Exception as e:
            print(f"Erro ao gerenciar mensagens: {e}")

    @commands.command(name='music')
    async def music(self, ctx, *, search):
        """Toca uma música do YouTube"""
        try:
            # Verifica se o usuário está em um canal de voz
            if not ctx.author.voice:
                await ctx.send("❌ Você precisa estar em um canal de voz para usar este comando!")
                return

            # Conecta ao canal de voz
            voice_client = await self.music.join_voice(ctx.author.voice.channel)
            if not voice_client:
                await ctx.send("❌ Não foi possível conectar ao canal de voz!")
                return

            # Toca a música
            result = await self.music.play_audio(voice_client, search, ctx.channel)
            
            if result['success']:
                # Se a música foi adicionada com sucesso, apaga a mensagem do comando
                await ctx.message.delete()
                
                # Envia a mensagem de resposta
                bot_message = await ctx.send(result['message'])
                
                # Se a música não estiver tocando (está na fila), apaga a mensagem após 1 minuto
                if not result['is_playing']:
                    await asyncio.sleep(60)
                    try:
                        await bot_message.delete()
                    except:
                        pass
            else:
                # Se houve erro, envia mensagem de erro e apaga ambas as mensagens após 1 minuto
                error_message = await ctx.send(f"❌ Erro ao tocar música: {result['error']}")
                await asyncio.sleep(60)
                try:
                    await ctx.message.delete()
                    await error_message.delete()
                except:
                    pass

        except Exception as e:
            print(f"Erro no comando music: {e}")
            error_message = await ctx.send(f"❌ Ocorreu um erro: {str(e)}")
            await asyncio.sleep(60)
            try:
                await ctx.message.delete()
                await error_message.delete()
            except:
                pass

    @commands.command(name='stop')
    async def stop(self, ctx):
        """Para a reprodução e limpa a fila"""
        try:
            if not ctx.author.voice:
                await ctx.send("❌ Você precisa estar em um canal de voz para usar este comando!")
                return

            voice_client = ctx.guild.voice_client
            if not voice_client:
                await ctx.send("❌ Não estou tocando música no momento!")
                return

            await self.music.stop(voice_client, ctx.guild.id)
            await ctx.send("⏹️ Reprodução parada e fila limpa!")

        except Exception as e:
            print(f"Erro no comando stop: {e}")
            await ctx.send(f"❌ Erro ao parar música: {str(e)}")

    @commands.command(name='pause')
    async def pause(self, ctx):
        """Pausa a música atual"""
        try:
            if not ctx.author.voice:
                await ctx.send("❌ Você precisa estar em um canal de voz para usar este comando!")
                return

            voice_client = ctx.guild.voice_client
            if not voice_client or not voice_client.is_playing():
                await ctx.send("❌ Não estou tocando música no momento!")
                return

            voice_client.pause()
            await ctx.send("⏸️ Música pausada!")

        except Exception as e:
            print(f"Erro no comando pause: {e}")
            await ctx.send(f"❌ Erro ao pausar música: {str(e)}")

    @commands.command(name='resume')
    async def resume(self, ctx):
        """Retoma a música pausada"""
        try:
            if not ctx.author.voice:
                await ctx.send("❌ Você precisa estar em um canal de voz para usar este comando!")
                return

            voice_client = ctx.guild.voice_client
            if not voice_client or not voice_client.is_paused():
                await ctx.send("❌ Não há música pausada no momento!")
                return

            voice_client.resume()
            await ctx.send("▶️ Música retomada!")

        except Exception as e:
            print(f"Erro no comando resume: {e}")
            await ctx.send(f"❌ Erro ao retomar música: {str(e)}")

    @commands.command(name='skip')
    async def skip(self, ctx):
        """Pula para a próxima música na fila"""
        try:
            if not ctx.author.voice:
                await ctx.send("❌ Você precisa estar em um canal de voz para usar este comando!")
                return

            voice_client = ctx.guild.voice_client
            if not voice_client:
                await ctx.send("❌ Não estou tocando música no momento!")
                return

            # Verifica se já existe uma votação em andamento
            if not self.music.can_start_skip_vote(ctx.guild.id):
                await ctx.send("❌ Já existe uma votação de skip em andamento!")
                return

            # Conta apenas usuários reais (não bots) no canal de voz
            real_users = [m for m in ctx.author.voice.channel.members if not m.bot]
            total_users = len(real_users)
            
            # Se só tiver uma pessoa, pula direto
            if total_users == 1:
                await ctx.message.delete()
                if await self.music.skip(voice_client, ctx.guild.id):
                    await ctx.send("⏭️ Música pulada!")
                return

            # Inicia a votação
            self.music.start_skip_vote(ctx.guild.id)
            
            # Calcula votos necessários (metade + 1 dos usuários)
            required_votes = (total_users // 2) + 1
            
            # Cria mensagem de votação
            vote_msg = await ctx.send(
                f"⏭️ Votação para pular música\n"
                f"Reaja com ✅ para votar\n"
                f"Votos necessários: {required_votes}/{total_users}"
            )
            await vote_msg.add_reaction("✅")
            
            # Espera 30 segundos pelos votos
            def check(reaction, user):
                return (
                    str(reaction.emoji) == "✅" and
                    not user.bot and
                    user in ctx.author.voice.channel.members
                )
            
            try:
                while True:
                    reaction, user = await self.bot.wait_for(
                        'reaction_add',
                        timeout=30.0,
                        check=check
                    )
                    
                    # Adiciona o voto
                    current_votes = self.music.add_skip_vote(ctx.guild.id, user.id)
                    
                    # Atualiza mensagem com contagem
                    await vote_msg.edit(content=(
                        f"⏭️ Votação para pular música\n"
                        f"Reaja com ✅ para votar\n"
                        f"Votos: {current_votes}/{required_votes}"
                    ))
                    
                    # Se atingiu os votos necessários, pula a música
                    if current_votes >= required_votes:
                        if await self.music.skip(voice_client, ctx.guild.id):
                            await vote_msg.edit(content="⏭️ Música pulada!")
                        break
                    
            except asyncio.TimeoutError:
                await vote_msg.edit(content="❌ Tempo de votação expirado!")
                self.music.end_skip_vote(ctx.guild.id)
            
        except Exception as e:
            print(f"Erro no comando skip: {e}")
            await ctx.send(f"❌ Erro ao pular música: {str(e)}")
            self.music.end_skip_vote(ctx.guild.id)

    @commands.command(name='queue')
    async def queue(self, ctx):
        """Mostra a fila de músicas"""
        try:
            if not ctx.guild.voice_client:
                await ctx.send("❌ Não estou tocando música no momento!")
                return

            queue_list = self.music.get_queue_list(ctx.guild.id)
            if not queue_list:
                await ctx.send("📋 A fila está vazia!")
                return

            # Apaga a mensagem do usuário
            await ctx.message.delete()

            # Divide a mensagem em chunks se necessário
            chunks = [queue_list[i:i+1900] for i in range(0, len(queue_list), 1900)]
            for i, chunk in enumerate(chunks):
                # Adiciona o título apenas no primeiro chunk
                if i == 0:
                    message = await ctx.send(f"📋 **Fila de Músicas:**\n{chunk}")
                else:
                    message = await ctx.send(chunk)
                
                # Apaga a mensagem após 1 minuto
                await asyncio.sleep(60)
                try:
                    await message.delete()
                except:
                    pass

        except Exception as e:
            print(f"Erro no comando queue: {e}")
            error_msg = await ctx.send(f"❌ Erro ao mostrar fila: {str(e)}")
            await asyncio.sleep(60)
            try:
                await error_msg.delete()
            except:
                pass

    @commands.command(name='now')
    async def now(self, ctx):
        """Mostra a música atual"""
        try:
            if not ctx.guild.voice_client or not ctx.guild.voice_client.is_playing():
                await ctx.send("❌ Não estou tocando música no momento!")
                return

            current_song = self.music.get_current_song(ctx.guild.id)
            if current_song:
                # Apaga a mensagem do usuário
                await ctx.message.delete()
                
                # Envia a mensagem e a apaga após 1 minuto
                message = await ctx.send(f"🎵 Tocando agora: **{current_song}**")
                await asyncio.sleep(60)
                try:
                    await message.delete()
                except:
                    pass
            else:
                await ctx.send("❌ Não consigo identificar a música atual!")

        except Exception as e:
            print(f"Erro no comando now: {e}")
            error_msg = await ctx.send(f"❌ Erro ao mostrar música atual: {str(e)}")
            await asyncio.sleep(60)
            try:
                await error_msg.delete()
            except:
                pass

@bot.event
async def on_ready():
    print(f'Ready to search the leylines!')
    await bot.add_cog(Music(bot))

bot.run(BOT_TOKEN) 