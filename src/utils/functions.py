"""
Arquivo contendo funções utilitárias para o projeto.
"""
import os
from pathlib import Path

def get_project_root() -> Path:
    """
    Retorna o caminho raiz do projeto.
    """
    return Path(__file__).parent.parent.parent

def get_resource_path(relative_path: str) -> str:
    """
    Retorna o caminho absoluto para um recurso do projeto.
    
    Args:
        relative_path (str): Caminho relativo ao diretório raiz do projeto
        
    Returns:
        str: Caminho absoluto do recurso
    """
    path = get_project_root() / relative_path
    return str(path)

def get_ffmpeg_path() -> str:
    """
    Retorna o caminho para o executável do FFmpeg.
    """
    path = get_resource_path("libraries/ffmpeg/bin/ffmpeg.exe")
    if not os.path.exists(path):
        raise FileNotFoundError(f"FFmpeg não encontrado em: {path}")
    return path

def ensure_directory_exists(path: str) -> None:
    """
    Garante que um diretório existe, criando-o se necessário.
    
    Args:
        path (str): Caminho do diretório
    """
    os.makedirs(path, exist_ok=True) 