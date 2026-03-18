"""
AppConfig - Configuração Centralizada do Centaurus
Todas as configurações da aplicação em um único lugar
"""
import os
import sys
from pathlib import Path
from typing import Optional


class AppConfig:
    """Configuração centralizada da aplicação"""
    
    # ==================== INFORMAÇÕES DO APP ====================
    VERSION = "3.0.0"
    APP_NAME = "Centaurus"
    APP_DISPLAY_NAME = "Centaurus 3.0 - Sistema de Verificação Facial (AuraFace)"
    
    # ==================== MODELO DE RECONHECIMENTO ====================
    MODEL_NAME = "auraface"  # AuraFace v1 (Apache 2.0 - uso comercial permitido)
    MODEL_ONNX_MIN_FILES = 2  # AuraFace usa 2 arquivos ONNX (detecção + reconhecimento)
    
    # ==================== CAMINHOS BASE ====================
    
    @staticmethod
    def get_base_dir() -> Path:
        """
        Retorna diretório base da aplicação (funciona em .exe e script)
        
        Returns:
            Path: Diretório onde está o executável ou script principal
        """
        if getattr(sys, 'frozen', False):
            # Executando como .exe compilado pelo PyInstaller
            # sys.executable aponta para o .exe
            # sys._MEIPASS é o diretório temporário interno (se onefile)
            # Usamos o diretório do executável para acessar arquivos externos (models)
            return Path(sys.executable).parent
        else:
            # Executando como script Python
            return Path(__file__).parent.parent
    
    @staticmethod
    def get_data_dir() -> Path:
        """
        Retorna diretório de dados do usuário (ProgramData no Windows)
        Cria o diretório se não existir
        
        Returns:
            Path: Diretório de dados da aplicação
        """
        if os.name == 'nt':  # Windows
            base = Path(os.environ.get('PROGRAMDATA', 'C:/ProgramData'))
        else:  # Linux/Mac
            base = Path.home() / '.local' / 'share'
        
        data_dir = base / 'Centaurus'
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir
    
    @staticmethod
    def get_verificacoes_dir() -> Path:
        """
        Retorna diretório de verificações (onde fica o banco de dados)
        
        Returns:
            Path: Diretório de verificações
        """
        verif_dir = AppConfig.get_data_dir() / 'verificacoes'
        verif_dir.mkdir(parents=True, exist_ok=True)
        return verif_dir
    
    # ==================== CAMINHOS ESPECÍFICOS ====================
    
    @staticmethod
    def get_models_dir() -> Path:
        """Retorna diretório dos modelos ML"""
        return AppConfig.get_base_dir() / 'models'
    
    @staticmethod
    def get_auraface_dir() -> Path:
        """Retorna diretório específico do modelo AuraFace"""
        return AppConfig.get_models_dir() / 'auraface'
    
    @staticmethod
    def get_model_dir() -> Path:
        """Retorna diretório do modelo configurado (alias genérico)"""
        return AppConfig.get_models_dir() / AppConfig.MODEL_NAME
    
    @staticmethod
    def get_db_path() -> Path:
        """Retorna caminho do banco de dados"""
        return AppConfig.get_verificacoes_dir() / 'verificacoes.db'
    
    @staticmethod
    def get_config_path() -> Path:
        """Retorna caminho do arquivo de configuração"""
        return AppConfig.get_data_dir() / 'config.json'
    
    @staticmethod
    def get_icon_path() -> Optional[Path]:
        """Retorna caminho do ícone se existir"""
        icon = AppConfig.get_base_dir() / 'icone.ico'
        return icon if icon.exists() else None
    
    # ==================== PARÂMETROS DE QUALIDADE ====================
    
    # Validação de nitidez (blur)
    BLUR_THRESHOLD = 50  # Quanto maior, mais nítida deve ser a imagem
    
    # Validação de pose frontal
    POSE_ANGLE_THRESHOLD = 40  # Ângulo máximo permitido (graus)
    
    # Tentativas de captura
    MAX_TENTATIVAS = 2  # Número máximo de tentativas
    
    # ==================== PARÂMETROS DE SIMILARIDADE ====================
    
    # Thresholds para verificação facial
    SIMILARITY_THRESHOLD_VERIFIED = 70  # Acima disto: Verificado
    SIMILARITY_THRESHOLD_WARNING = 65   # Entre 65-70: Atenção
    # Abaixo de 65: Chamar Policial Federal
    
    # ==================== PARÂMETROS DE CÂMERA ====================
    
    # Número máximo de câmeras a testar
    MAX_CAMERAS_TO_TEST = 10
    
    # Usar DirectShow no Windows (mais rápido)
    USE_DSHOW = os.name == 'nt'
    
    # ==================== PARÂMETROS DE INTERFACE ====================
    
    # Tema padrão do ttkbootstrap
    DEFAULT_THEME = "darkly"
    
    # Dimensões da janela principal
    WINDOW_WIDTH = 800
    WINDOW_HEIGHT = 900
    
    # Tamanho inicial das imagens no zoom/pan
    INITIAL_IMAGE_SIZE = (900, 900)
    
    # ==================== PARÂMETROS DE SEGURANÇA ====================
    
    # Senha para criptografia do banco de dados
    DB_PASSWORD = "Centaurus@PF2025!SecureDB#RFH"
    
    # ==================== VALIDAÇÕES DE CABINE ====================
    
    # Padrão de ID de cabine válido (E1-E20 ou D1-D20)
    CABINE_PATTERN = r'^[ED]([1-9]|1[0-9]|20)$'
    
    # Lados válidos
    CABINE_SIDES = ['E', 'D']
    
    # Números válidos (1-20)
    CABINE_MIN_NUM = 1
    CABINE_MAX_NUM = 20
    
    # ==================== CONFIGURAÇÕES DE BUILD ====================
    
    @staticmethod
    def is_frozen() -> bool:
        """Verifica se está executando como .exe"""
        return getattr(sys, 'frozen', False)
    
    @staticmethod
    def get_resource_path(relative_path: str) -> Path:
        """
        Obtém caminho para recurso (funciona em .exe e script)
        
        Args:
            relative_path: Caminho relativo ao diretório base
            
        Returns:
            Path: Caminho absoluto para o recurso
        """
        base = AppConfig.get_base_dir()
        return base / relative_path


# ==================== CONSTANTES DE STATUS ====================

class VerificationStatus:
    """Status possíveis de verificação"""
    VERIFIED = "Verificado"
    WARNING = "Atenção durante a captura"
    ALERT = "Chamar Policial Federal"


class VerificationColors:
    """Cores para cada status"""
    VERIFIED = "#2ea628"  # Verde
    WARNING = "#dede33"   # Amarelo
    ALERT = "#cf2929"     # Vermelho


class VerificationIcons:
    """Ícones para cada status"""
    VERIFIED = "✓"
    WARNING = "⚠"
    ALERT = "✗"
