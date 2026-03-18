"""
CameraHandler - Gerenciamento Robusto de Câmera
Context manager para abertura/fechamento seguro de câmera
"""
import cv2
from typing import Optional, List
import numpy as np


class CameraHandler:
    """Gerenciamento seguro de câmera com context manager"""
    
    def __init__(self, use_dshow: bool = True):
        """
        Inicializa o handler de câmera
        
        Args:
            use_dshow: Usar DirectShow no Windows (mais rápido)
        """
        self.camera: Optional[cv2.VideoCapture] = None
        self.camera_index: Optional[int] = None
        self.use_dshow = use_dshow
    
    @staticmethod
    def list_available_cameras(max_test: int = 10, use_dshow: bool = True) -> List[int]:
        """
        Lista câmeras disponíveis
        
        Args:
            max_test: Número máximo de índices a testar
            use_dshow: Usar DirectShow (Windows)
            
        Returns:
            list: Índices de câmeras disponíveis
        """
        available = []
        backend = cv2.CAP_DSHOW if use_dshow else cv2.CAP_ANY
        
        for i in range(max_test):
            cap = cv2.VideoCapture(i, backend)
            if cap.isOpened():
                # Verifica se consegue ler pelo menos um frame
                ret, _ = cap.read()
                if ret:
                    available.append(i)
                cap.release()
        
        return available
    
    def open_camera(self, index: int) -> bool:
        """
        Abre câmera com tratamento de erro
        
        Args:
            index: Índice da câmera
            
        Returns:
            bool: True se abriu com sucesso
        """
        self.close_camera()  # Fecha anterior se existir
        
        backend = cv2.CAP_DSHOW if self.use_dshow else cv2.CAP_ANY
        self.camera = cv2.VideoCapture(index, backend)
        
        if not self.camera.isOpened():
            self.camera = None
            return False
        
        # Configura propriedades para máxima qualidade (Full HD)
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        self.camera.set(cv2.CAP_PROP_FPS, 30)
        
        self.camera_index = index
        return True
    
    def read_frame(self) -> Optional[np.ndarray]:
        """
        Lê frame da câmera
        
        Returns:
            np.ndarray: Frame BGR ou None se erro
        """
        if self.camera is None or not self.camera.isOpened():
            return None
        
        ret, frame = self.camera.read()
        return frame if ret else None
    
    def is_opened(self) -> bool:
        """Verifica se câmera está aberta"""
        return self.camera is not None and self.camera.isOpened()
    
    def get_camera_info(self) -> dict:
        """
        Retorna informações da câmera atual
        
        Returns:
            dict: Informações da câmera
        """
        if not self.is_opened():
            return {}
        
        return {
            'index': self.camera_index,
            'width': int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'height': int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'fps': int(self.camera.get(cv2.CAP_PROP_FPS)),
            'backend': 'DirectShow' if self.use_dshow else 'Default'
        }
    
    def close_camera(self):
        """Fecha câmera com segurança"""
        if self.camera is not None:
            try:
                if self.camera.isOpened():
                    self.camera.release()
            except Exception as e:
                print(f"Erro ao fechar câmera: {e}")
            finally:
                self.camera = None
                self.camera_index = None
    
    def restart_camera(self) -> bool:
        """
        Reinicia a câmera atual
        
        Returns:
            bool: True se reiniciou com sucesso
        """
        if self.camera_index is None:
            return False
        
        index = self.camera_index
        self.close_camera()
        return self.open_camera(index)
    
    # Context manager protocol
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_camera()
        return False
    
    def __del__(self):
        """Garante fechamento ao destruir objeto"""
        self.close_camera()


class CameraError(Exception):
    """Exceção customizada para erros de câmera"""
    pass
