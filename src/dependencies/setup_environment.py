import os
import sys
import subprocess
import urllib.request
import zipfile
import shutil
from pathlib import Path

# Instala o tqdm se não estiver instalado
subprocess.check_call([sys.executable, "-m", "pip", "install", "tqdm"])

from tqdm import tqdm

def get_project_root():
    """Retorna o diretório raiz do projeto"""
    # Como agora estamos em src/dependencies, precisamos subir 3 níveis
    return Path(__file__).parent.parent.parent

class DownloadProgressBar(tqdm):
    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)

def download_ffmpeg():
    """Baixa e configura o FFmpeg"""
    print("Verificando FFmpeg...")
    
    # Define o caminho correto para o FFmpeg
    ffmpeg_dir = get_project_root() / "libraries" / "ffmpeg"
    ffmpeg_bin = ffmpeg_dir / "bin"
    
    # Verifica se o FFmpeg já existe
    if ffmpeg_bin.exists() and any(ffmpeg_bin.glob("ffmpeg.exe")):
        print("FFmpeg já está instalado!")
        return str(ffmpeg_bin / "ffmpeg.exe")
    
    # Cria diretórios necessários
    ffmpeg_dir.mkdir(parents=True, exist_ok=True)
    
    # URL do FFmpeg para Windows (versão minimal com apenas os arquivos necessários)
    ffmpeg_url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl-shared.zip"
    zip_path = ffmpeg_dir / "ffmpeg.zip"
    
    try:
        # Baixa o FFmpeg com barra de progresso
        print("Baixando FFmpeg...")
        with DownloadProgressBar(unit='B', unit_scale=True, miniters=1, desc="Download FFmpeg") as t:
            urllib.request.urlretrieve(ffmpeg_url, zip_path, reporthook=t.update_to)
        
        # Extrai o arquivo com barra de progresso
        print("Extraindo FFmpeg...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Obtém o tamanho total dos arquivos
            total_size = sum(info.file_size for info in zip_ref.filelist)
            with tqdm(total=total_size, unit='B', unit_scale=True, desc="Extraindo") as pbar:
                for file in zip_ref.filelist:
                    zip_ref.extract(file, ffmpeg_dir / "temp")
                    pbar.update(file.file_size)
        
        # Move a pasta bin inteira
        temp_bin = next((ffmpeg_dir / "temp").glob("**/bin"))
        if temp_bin.exists():
            # Remove a pasta bin existente se houver
            if ffmpeg_bin.exists():
                shutil.rmtree(ffmpeg_bin)
            # Move a pasta bin inteira
            shutil.move(str(temp_bin), str(ffmpeg_dir))
            print("Pasta bin movida com sucesso!")
            
            # Verifica se todos os arquivos necessários estão presentes
            required_files = [
                "avcodec-62.dll",
                "avdevice-62.dll",
                "avfilter-11.dll",
                "avformat-62.dll",
                "avutil-60.dll",
                "ffmpeg.exe",
                "swresample-6.dll",
                "swscale-9.dll"
            ]
            
            missing_files = [f for f in required_files if not (ffmpeg_bin / f).exists()]
            if missing_files:
                print(f"Erro: Arquivos faltando na pasta bin: {', '.join(missing_files)}")
                return None
            else:
                print("Todos os arquivos necessários foram encontrados!")
        else:
            print("Erro: Pasta bin não encontrada no arquivo extraído!")
            return None
        
        # Limpa arquivos temporários
        shutil.rmtree(ffmpeg_dir / "temp")
        zip_path.unlink()
        
        print("FFmpeg configurado com sucesso!")
        return str(ffmpeg_bin / "ffmpeg.exe")
        
    except Exception as e:
        print(f"Erro ao configurar FFmpeg: {e}")
        return None

def setup_environment():
    """Configura todo o ambiente necessário"""
    print("Configurando ambiente...")
    
    # Instala dependências do requirements.txt
    print("Instalando dependências...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(get_project_root() / "src" / "dependencies" / "requirements.txt")])
    
    # Configura FFmpeg
    ffmpeg_path = download_ffmpeg()
    if ffmpeg_path:
        print(f"FFmpeg instalado em: {ffmpeg_path}")
    else:
        print("Aviso: FFmpeg não foi instalado automaticamente.")
        print("Por favor, instale o FFmpeg manualmente e configure o caminho no config.py")
    
    print("Configuração concluída!")

if __name__ == "__main__":
    setup_environment()