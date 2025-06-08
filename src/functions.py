"""
Arquivo contendo funções utilitárias para o projeto.
"""
import os
from pathlib import Path

def get_project_root() -> Path:
    """
    Retorna o caminho raiz do projeto.
    """
    return Path(__file__).parent.parent

def get_resource_path(relative_path: str) -> str:
    """
    Retorna o caminho absoluto para um recurso do projeto.
    
    Args:
        relative_path (str): Caminho relativo ao diretório raiz do projeto
        
    Returns:
        str: Caminho absoluto do recurso
    """
    return str(get_project_root() / relative_path)

def get_ffmpeg_path() -> str:
    """
    Retorna o caminho para o executável do FFmpeg.
    """
    return get_resource_path("libraries/ffmpeg/bin/ffmpeg.exe")

def ensure_directory_exists(path: str) -> None:
    """
    Garante que um diretório existe, criando-o se necessário.
    
    Args:
        path (str): Caminho do diretório
    """
    os.makedirs(path, exist_ok=True) 