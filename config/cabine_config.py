"""
CabineConfigManager - Gerenciador de Configuração de Cabine
Gerencia a identificação da cabine (E1-E20 ou D1-D20) via config.json
Versão refatorada usando AppConfig
"""
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from .settings import AppConfig


class CabineConfigManager:
    """Gerencia a configuração da cabine em config.json"""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Inicializa o gerenciador de configuração.
        
        Args:
            config_path: Caminho para o arquivo de configuração.
                        Se None, usa AppConfig.get_config_path()
        """
        self.config_path = config_path or AppConfig.get_config_path()
        
        # Garante que o diretório existe
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"Aviso: Não foi possível criar diretório {self.config_path.parent}: {e}")
    
    def config_exists(self) -> bool:
        """Verifica se o arquivo de configuração existe"""
        return self.config_path.exists()
    
    def get_cabine_id(self) -> Optional[str]:
        """
        Retorna o ID da cabine configurada.
        
        Returns:
            str: ID da cabine (ex: "E4", "D12") ou None se não configurado
        """
        if not self.config_exists():
            return None
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('cabine_id')
        except (json.JSONDecodeError, IOError) as e:
            print(f"Erro ao ler configuração: {e}")
            return None
    
    def set_cabine_id(self, cabine_id: str) -> bool:
        """
        Define o ID da cabine e salva no arquivo de configuração.
        
        Args:
            cabine_id: ID da cabine (ex: "E4", "D12")
            
        Returns:
            bool: True se salvou com sucesso, False caso contrário
        """
        if not self.validar_cabine_id(cabine_id):
            print(f"Erro: ID de cabine inválido: {cabine_id}")
            return False
        
        config = {
            'cabine_id': cabine_id.upper(),
            'instalacao_data': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'versao': AppConfig.VERSION
        }
        
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            print(f"Erro ao salvar configuração: {e}")
            return False
    
    def get_config(self) -> dict:
        """
        Retorna toda a configuração.
        
        Returns:
            dict: Configuração completa ou dict vazio se não existe
        """
        if not self.config_exists():
            return {}
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Erro ao ler configuração: {e}")
            return {}
    
    @staticmethod
    def validar_cabine_id(cabine_id: str) -> bool:
        """
        Valida se o ID da cabine está no formato correto.
        
        Args:
            cabine_id: ID para validar (ex: "E4", "d12")
            
        Returns:
            bool: True se válido (E1-E20 ou D1-D20)
        """
        if not cabine_id or not isinstance(cabine_id, str):
            return False
        
        # Usa o padrão de AppConfig
        return bool(re.match(AppConfig.CABINE_PATTERN, cabine_id.upper()))
    
    @staticmethod
    def get_todas_cabines() -> List[str]:
        """
        Retorna lista de todas as cabines possíveis.
        
        Returns:
            list: Lista com todos os IDs possíveis (E1-E20, D1-D20)
        """
        cabines = []
        for letra in AppConfig.CABINE_SIDES:
            for numero in range(AppConfig.CABINE_MIN_NUM, AppConfig.CABINE_MAX_NUM + 1):
                cabines.append(f"{letra}{numero}")
        return cabines
    
    def delete_config(self) -> bool:
        """Remove o arquivo de configuração (útil para testes)"""
        if self.config_exists():
            try:
                self.config_path.unlink()
                return True
            except OSError as e:
                print(f"Erro ao remover configuração: {e}")
                return False
        return True
    
    def update_version(self) -> bool:
        """
        Atualiza a versão no arquivo de configuração
        
        Returns:
            bool: True se atualizou com sucesso
        """
        config = self.get_config()
        if not config:
            return False
        
        config['versao'] = AppConfig.VERSION
        config['ultima_atualizacao'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            print(f"Erro ao atualizar configuração: {e}")
            return False
