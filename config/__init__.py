"""
Config - Módulo de configuração
Contém configurações centralizadas e gerenciamento de caminhos
"""
from .settings import AppConfig
from .paths import PathManager
from .cabine_config import CabineConfigManager

__all__ = [
    'AppConfig',
    'PathManager',
    'CabineConfigManager',
]
