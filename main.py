import sys
import os

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importa e executa o bot
from src.bot.commands.music import bot, BOT_TOKEN

if __name__ == "__main__":
    print("Iniciando Amadeus Neural Network...")
    bot.run(BOT_TOKEN)