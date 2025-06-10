"""
Script para configurar o ambiente do bot.
Responsável por baixar e configurar o FFmpeg.
"""
import os
import sys
import zipfile
import requests
from pathlib import Path
from tqdm import tqdm

def download_file(url: str, destination: str) -> None:
    """
    Baixa um arquivo com barra de progresso.
    
    Args:
        url (str): URL do arquivo
        destination (str): Caminho de destino
    """
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    block_size = 1024
    
    with open(destination, 'wb') as file, tqdm(
        desc=os.path.basename(destination),
        total=total_size,
        unit='iB',
        unit_scale=True,
        unit_divisor=1024,
    ) as bar:
        for data in response.iter_content(block_size):
            size = file.write(data)
            bar.update(size)

def setup_ffmpeg() -> None:
    """
    Baixa e configura o FFmpeg.
    """
    # URL do FFmpeg para Windows
    ffmpeg_url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
    
    # Cria os diretórios necessários
    ffmpeg_dir = Path("libraries/ffmpeg")
    ffmpeg_dir.mkdir(parents=True, exist_ok=True)
    
    # Caminho do arquivo zip
    zip_path = ffmpeg_dir / "ffmpeg.zip"
    
    print("Baixando FFmpeg...")
    download_file(ffmpeg_url, str(zip_path))
    
    print("Extraindo FFmpeg...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        # Extrai apenas os arquivos necessários
        for file in zip_ref.namelist():
            if file.endswith(('ffmpeg.exe', 'ffprobe.exe')):
                zip_ref.extract(file, ffmpeg_dir)
    
    # Move os arquivos para o local correto
    bin_dir = ffmpeg_dir / "bin"
    bin_dir.mkdir(exist_ok=True)
    
    # Move os executáveis para a pasta bin
    for exe in ffmpeg_dir.glob("**/*.exe"):
        exe.rename(bin_dir / exe.name)
    
    # Remove o arquivo zip
    zip_path.unlink()
    
    print("FFmpeg instalado com sucesso!")

def main() -> None:
    """
    Função principal do script.
    """
    try:
        setup_ffmpeg()
    except Exception as e:
        print(f"Erro ao configurar o ambiente: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 