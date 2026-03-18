"""
Core - Módulo principal com lógica de negócio
Contém verificação facial, câmera e validação de qualidade
"""
from .face_verifier import FaceVerifier, VerificationResult
from .camera_handler import CameraHandler
from .quality_validator import QualityValidator
from .models_loader import ModelsLoader

__all__ = [
    'FaceVerifier',
    'VerificationResult',
    'CameraHandler',
    'QualityValidator',
    'ModelsLoader',
]
