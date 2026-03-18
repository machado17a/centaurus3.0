"""
QualityValidator - Validação de Qualidade de Imagem
Valida nitidez (blur) e pose frontal
"""
import cv2
import numpy as np
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class QualityResult:
    """Resultado da validação de qualidade"""
    is_valid: bool
    blur_score: float
    blur_passed: bool
    pose_angle: Optional[float]
    pose_passed: bool
    message: str


class QualityValidator:
    """Valida qualidade de imagem facial"""
    
    def __init__(self, blur_threshold: float = 50, pose_threshold: float = 40):
        """
        Inicializa o validador de qualidade
        
        Args:
            blur_threshold: Threshold mínimo de nitidez (maior = mais nítido)
            pose_threshold: Ângulo máximo permitido para pose frontal (graus)
        """
        self.blur_threshold = blur_threshold
        self.pose_threshold = pose_threshold
    
    def validate_blur(self, image: np.ndarray) -> Tuple[bool, float]:
        """
        Valida nitidez da imagem usando Laplacian
        
        Args:
            image: Imagem numpy array (BGR)
            
        Returns:
            tuple: (passou, score)
        """
        if image is None or not isinstance(image, np.ndarray) or image.size == 0:
            return False, 0.0
        
        # Converte para grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Calcula variância do Laplacian
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        passed = laplacian_var >= self.blur_threshold
        return passed, laplacian_var
    
    def validate_pose(self, face_obj) -> Tuple[bool, Optional[float]]:
        """
        Valida se a pose está frontal usando dados do InsightFace
        
        Args:
            face_obj: Objeto face do InsightFace com atributo pose
            
        Returns:
            tuple: (passou, ângulo) ou (False, None) se não disponível
        """
        if not hasattr(face_obj, 'pose') or face_obj.pose is None:
            # Se não tem pose, aceita (para compatibilidade)
            return True, None
        
        # Calcula ângulo total (pitch, yaw, roll)
        try:
            pose = face_obj.pose
            # pose é um array [pitch, yaw, roll] em graus
            total_angle = np.sqrt(np.sum(np.array(pose) ** 2))
            
            passed = total_angle <= self.pose_threshold
            return passed, total_angle
        except Exception as e:
            print(f"Erro ao validar pose: {e}")
            return True, None  # Aceita em caso de erro
    
    def validate_face_image(
        self,
        image: np.ndarray,
        face_obj=None
    ) -> QualityResult:
        """
        Valida qualidade completa da imagem facial
        
        Args:
            image: Imagem da face (BGR)
            face_obj: Objeto face do InsightFace (opcional, para pose)
            
        Returns:
            QualityResult: Resultado completo da validação
        """
        # Valida blur
        blur_passed, blur_score = self.validate_blur(image)
        
        # Valida pose (se disponível)
        pose_passed = True
        pose_angle = None
        if face_obj is not None:
            pose_passed, pose_angle = self.validate_pose(face_obj)
        
        # Determina se passou
        is_valid = blur_passed and pose_passed
        
        # Monta mensagem
        messages = []
        if not blur_passed:
            messages.append(f"Imagem desfocada (score: {blur_score:.1f}, mínimo: {self.blur_threshold})")
        if not pose_passed:
            messages.append(f"Pose não frontal (ângulo: {pose_angle:.1f}°, máximo: {self.pose_threshold}°)")
        
        if is_valid:
            message = "Qualidade OK"
        else:
            message = " | ".join(messages)
        
        return QualityResult(
            is_valid=is_valid,
            blur_score=blur_score,
            blur_passed=blur_passed,
            pose_angle=pose_angle,
            pose_passed=pose_passed,
            message=message
        )
    
    def get_blur_level_description(self, score: float) -> str:
        """
        Retorna descrição do nível de blur
        
        Args:
            score: Score de blur
            
        Returns:
            str: Descrição textual
        """
        if score >= self.blur_threshold * 2:
            return "Excelente"
        elif score >= self.blur_threshold * 1.5:
            return "Boa"
        elif score >= self.blur_threshold:
            return "Aceitável"
        elif score >= self.blur_threshold * 0.7:
            return "Regular"
        else:
            return "Ruim"
    
    def suggest_improvement(self, result: QualityResult) -> str:
        """
        Sugere melhorias baseado no resultado
        
        Args:
            result: Resultado da validação
            
        Returns:
            str: Sugestão de melhoria
        """
        if result.is_valid:
            return "Imagem com qualidade adequada"
        
        suggestions = []
        
        if not result.blur_passed:
            suggestions.append("• Aproxime mais a câmera ou melhore a iluminação")
            suggestions.append("• Mantenha o documento ou rosto mais estático")
        
        if not result.pose_passed:
            suggestions.append("• Mantenha o rosto frontal à câmera")
            suggestions.append("• Evite inclinar ou girar a cabeça")
        
        return "\n".join(suggestions)
