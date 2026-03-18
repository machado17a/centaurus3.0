"""
ModelsLoader - Carregador de Modelos ML
Gerencia carregamento do InsightFace (AuraFace v1) e validações
Versão 3.0 - Migrado de antelopev2 para AuraFace
"""
import os
from pathlib import Path
from typing import Optional
from insightface.app import FaceAnalysis


class ModelsLoader:
    """Gerencia carregamento de modelos de ML (AuraFace v1)"""
    
    def __init__(self, models_dir: Path):
        """
        Inicializa o loader
        
        Args:
            models_dir: Diretório contendo os modelos (ex: .../models/)
        """
        self.models_dir = Path(models_dir).absolute()
        self.model: Optional[FaceAnalysis] = None
    
    def load_model(self, model_name: str = 'auraface') -> FaceAnalysis:
        """
        Carrega modelo AuraFace via InsightFace FaceAnalysis.
        
        O AuraFace usa a mesma API do InsightFace (FaceAnalysis) e produz
        embeddings via face.normed_embedding, compatível com o restante do sistema.
        
        Args:
            model_name: Nome do modelo a carregar ('auraface')
            
        Returns:
            FaceAnalysis: Modelo carregado
            
        Raises:
            FileNotFoundError: Se modelos não encontrados
            RuntimeError: Se erro ao carregar
        """
        model_path = self.models_dir / model_name
        
        # Valida existência do diretório
        if not model_path.exists():
            raise FileNotFoundError(
                f"Diretório de modelos não encontrado: {model_path}\n"
                f"Execute 'python download_model.py' para baixar o modelo AuraFace.\n"
                f"Ou certifique-se de que a pasta 'models/{model_name}' está presente."
            )
        
        # Verifica se arquivos estão em subpasta duplicada (ex: auraface/auraface/)
        model_subpath = model_path / model_name
        if model_subpath.exists():
            check_path = model_subpath
        else:
            check_path = model_path
        
        # Verifica arquivos .onnx (AuraFace precisa de pelo menos 2: detecção + reconhecimento)
        onnx_files = list(check_path.glob('*.onnx'))
        if len(onnx_files) < 2:
            raise FileNotFoundError(
                f"Modelos incompletos em {check_path}\n"
                f"Encontrados {len(onnx_files)} arquivos .onnx, esperado: 2+\n"
                f"Arquivos encontrados: {[f.name for f in onnx_files]}\n"
                f"Execute 'python download_model.py' para baixar o modelo AuraFace."
            )
        
        try:
            # root deve apontar para o parent de models/
            # InsightFace procura em {root}/models/{model_name}/
            root_path = self.models_dir.parent
            
            print(f"[ModelsLoader] Carregando modelo '{model_name}' (AuraFace v1)")
            print(f"[ModelsLoader] Root path: {root_path}")
            print(f"[ModelsLoader] Models dir: {self.models_dir}")
            print(f"[ModelsLoader] Model path: {model_path}")
            print(f"[ModelsLoader] Arquivos .onnx: {[f.name for f in onnx_files]}")
            
            model = FaceAnalysis(
                name=model_name,
                root=str(root_path),
                providers=['CPUExecutionProvider'],
                allowed_modules=['detection', 'recognition']
            )
            
            print(f"[ModelsLoader] FaceAnalysis criado, preparando modelo...")
            
            # ctx_id=-1 força CPU; det_thresh=0.5 é sensibilidade padrão
            model.prepare(ctx_id=-1, det_thresh=0.5, det_size=(640, 640))
            
            print(f"[ModelsLoader] Modelo AuraFace preparado com sucesso!")
            if hasattr(model, 'models'):
                print(f"[ModelsLoader] Módulos carregados: {list(model.models.keys())}")
            
            self.model = model
            return model
            
        except Exception as e:
            raise RuntimeError(
                f"Erro ao carregar modelo AuraFace: {e}\n"
                f"Root: {root_path}\n"
                f"Models dir: {self.models_dir}\n"
                f"Model path: {model_path}"
            )
    
    def get_model(self) -> Optional[FaceAnalysis]:
        """Retorna modelo carregado ou None"""
        return self.model
    
    def is_loaded(self) -> bool:
        """Verifica se modelo está carregado"""
        return self.model is not None
    
    @staticmethod
    def validate_onnx_runtime():
        """
        Valida se ONNX Runtime está funcionando
        
        Raises:
            ImportError: Se ONNX Runtime não disponível
        """
        try:
            import onnxruntime as ort
            # Testa criação de sessão simples
            _ = ort.get_available_providers()
        except Exception as e:
            raise ImportError(
                f"ONNX Runtime não disponível ou com problemas: {e}\n"
                "Instale com: pip install onnxruntime"
            )
    
    @staticmethod
    def get_providers_info() -> dict:
        """
        Retorna informações sobre providers disponíveis
        
        Returns:
            dict: Informações dos providers
        """
        try:
            import onnxruntime as ort
            available = ort.get_available_providers()
            
            return {
                'available': available,
                'has_cuda': 'CUDAExecutionProvider' in available,
                'has_cpu': 'CPUExecutionProvider' in available,
            }
        except:
            return {
                'available': [],
                'has_cuda': False,
                'has_cpu': False,
            }
