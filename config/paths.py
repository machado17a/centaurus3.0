"""
PathManager - Gerenciador de Caminhos do Sistema
Garante que todos os diretórios necessários existam
"""
from pathlib import Path
from typing import Optional
import os
from .settings import AppConfig


class PathManager:
    """Gerencia criação e validação de caminhos"""
    
    @staticmethod
    def initialize_all_paths() -> bool:
        """
        Inicializa todos os diretórios necessários
        
        Returns:
            bool: True se sucesso, False se erro
        """
        try:
            # Diretórios principais
            AppConfig.get_data_dir().mkdir(parents=True, exist_ok=True)
            AppConfig.get_verificacoes_dir().mkdir(parents=True, exist_ok=True)
            
            # Subdiretórios de verificações (legado - pode ser removido)
            # resultados_dir = AppConfig.get_verificacoes_dir() / 'resultados_suspeitos'
            # resultados_dir.mkdir(parents=True, exist_ok=True)
            
            return True
            
        except (OSError, PermissionError) as e:
            print(f"Erro ao criar diretórios: {e}")
            return False
    
    @staticmethod
    def validate_models_dir() -> tuple[bool, Optional[str]]:
        """
        Valida se o diretório de modelos existe e contém arquivos necessários
        
        Returns:
            tuple: (sucesso, mensagem de erro)
        """
        models_dir = AppConfig.get_model_dir()
        
        if not models_dir.exists():
            return False, (
                f"Diretório de modelos não encontrado: {models_dir}\n"
                f"Execute 'python download_model.py' para baixar o modelo AuraFace."
            )
        
        # Verifica arquivos .onnx necessários (AuraFace usa 2, antelopev2 usava 5)
        onnx_files = list(models_dir.glob('*.onnx'))
        min_files = AppConfig.MODEL_ONNX_MIN_FILES
        if len(onnx_files) < min_files:
            return False, f"Modelos insuficientes em {models_dir}. Esperado: {min_files}+ arquivos .onnx, encontrados: {len(onnx_files)}"
        
        return True, None
    
    @staticmethod
    def validate_icon() -> tuple[bool, Optional[Path]]:
        """
        Valida se o ícone existe
        
        Returns:
            tuple: (existe, caminho ou None)
        """
        icon_path = AppConfig.get_icon_path()
        if icon_path and icon_path.exists():
            return True, icon_path
        return False, None
    
    @staticmethod
    def get_temp_dir() -> Path:
        """
        Retorna diretório temporário da aplicação
        
        Returns:
            Path: Diretório temporário
        """
        import tempfile
        temp = Path(tempfile.gettempdir()) / 'Centaurus'
        temp.mkdir(parents=True, exist_ok=True)
        return temp
    
    @staticmethod
    def ensure_writable(path: Path) -> bool:
        """
        Verifica se um caminho é gravável
        
        Args:
            path: Caminho para verificar
            
        Returns:
            bool: True se gravável
        """
        try:
            if path.is_file():
                path = path.parent
            
            # Tenta criar arquivo de teste
            test_file = path / '.write_test'
            test_file.touch()
            test_file.unlink()
            return True
            
        except (OSError, PermissionError):
            return False
