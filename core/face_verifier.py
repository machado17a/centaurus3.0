"""
FaceVerifier - Lógica de Verificação Facial Pura (sem UI)
Responsável por captura e comparação de faces
"""
from dataclasses import dataclass
from typing import Optional, Tuple
import numpy as np
import cv2


@dataclass
class VerificationResult:
    """Resultado da verificação facial"""
    similarity: float
    status: str
    color: str
    icon: str
    doc_image: Optional[np.ndarray] = None
    webcam_image: Optional[np.ndarray] = None
    embedding_doc: Optional[np.ndarray] = None
    embedding_webcam: Optional[np.ndarray] = None


class FaceVerifier:
    """Lógica de verificação facial pura (sem dependência de UI)"""
    
    def __init__(self, model, config):
        """
        Inicializa o verificador facial
        
        Args:
            model: Modelo InsightFace (FaceAnalysis)
            config: Objeto AppConfig com parâmetros
        """
        self.model = model
        self.config = config
    
    def capture_face(self, image: np.ndarray) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Captura face de uma imagem
        
        Args:
            image: Imagem numpy array (BGR)
            
        Returns:
            tuple: (face_image, embedding) ou (None, None) se não detectar
        """
        if image is None:
            return None, None
        
        # Detecta faces
        faces = self.model.get(image)
        if not faces:
            return None, None
        
        # Pega a primeira face (mais à esquerda)
        face = sorted(faces, key=lambda f: f.bbox[0])[0]
        
        # Extrai região da face com margem
        face_img = self._extract_face_with_margin(image, face.bbox)
        
        return face_img, face.normed_embedding
    
    def verify_faces(
        self,
        emb1: np.ndarray,
        emb2: np.ndarray,
        img1: Optional[np.ndarray] = None,
        img2: Optional[np.ndarray] = None
    ) -> VerificationResult:
        """
        Compara duas embeddings e retorna resultado
        
        Args:
            emb1: Embedding da primeira face (documento)
            emb2: Embedding da segunda face (webcam)
            img1: Imagem opcional do documento
            img2: Imagem opcional da webcam
            
        Returns:
            VerificationResult: Resultado da verificação
        """
        # Calcula similaridade de cosseno
        cos_sim = np.dot(emb1, emb2)
        cos_sim = np.clip(cos_sim, -1.0, 1.0)
        sim_percent = ((cos_sim + 1) / 2) * 100
        
        # Determina status baseado nos thresholds
        if sim_percent > self.config.SIMILARITY_THRESHOLD_VERIFIED:
            status = "Verificado"
            color = "#2ea628"
            icon = "✓"
        elif sim_percent >= self.config.SIMILARITY_THRESHOLD_WARNING:
            status = "Atenção durante a captura"
            color = "#dede33"
            icon = "⚠"
        else:
            status = "Chamar Policial Federal"
            color = "#cf2929"
            icon = "✗"
        
        return VerificationResult(
            similarity=sim_percent,
            status=status,
            color=color,
            icon=icon,
            doc_image=img1,
            webcam_image=img2,
            embedding_doc=emb1,
            embedding_webcam=emb2
        )
    
    def _extract_face_with_margin(
        self,
        image: np.ndarray,
        bbox: Tuple[float, float, float, float],
        margin: float = 0.2
    ) -> np.ndarray:
        """
        Extrai face com margem ao redor
        
        Args:
            image: Imagem original
            bbox: Bounding box (x1, y1, x2, y2)
            margin: Margem percentual a adicionar
            
        Returns:
            np.ndarray: Região da face extraída
        """
        # Validação de imagem
        if image is None or not isinstance(image, np.ndarray) or image.size == 0:
            return np.array([])  # Retorna array vazio
        
        x1, y1, x2, y2 = [int(v) for v in bbox]
        
        # Calcula margem
        margem_x = int((x2 - x1) * margin)
        margem_y = int((y2 - y1) * margin)
        
        # Aplica margem respeitando limites da imagem
        h, w = image.shape[:2]
        x1 = max(0, x1 - margem_x)
        y1 = max(0, y1 - margem_y)
        x2 = min(w, x2 + margem_x)
        y2 = min(h, y2 + margem_y)
        
        return image[y1:y2, x1:x2].copy()
    
    def count_faces(self, image: np.ndarray) -> int:
        """
        Conta número de faces em uma imagem
        
        Args:
            image: Imagem numpy array (BGR)
            
        Returns:
            int: Número de faces detectadas
        """
        if image is None:
            return 0
        
        faces = self.model.get(image)
        return len(faces) if faces else 0
    
    def get_largest_face(self, image: np.ndarray) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """
        Pega a maior face em uma imagem
        
        Args:
            image: Imagem numpy array (BGR)
            
        Returns:
            tuple: (face_image, embedding) ou None
        """
        if image is None:
            return None
        
        faces = self.model.get(image)
        if not faces:
            return None
        
        # Ordena por área do bbox (maior primeiro)
        largest = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        
        face_img = self._extract_face_with_margin(image, largest.bbox)
        return face_img, largest.normed_embedding
