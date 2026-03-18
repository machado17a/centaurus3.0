"""
EncryptionHelper - Utilitários de Criptografia
Funções centralizadas para criptografia de dados sensíveis
"""
import hashlib
import base64
from cryptography.fernet import Fernet
from typing import Optional


class EncryptionHelper:
    """Helper para criptografia AES-256 usando Fernet"""
    
    def __init__(self, password: str):
        """
        Inicializa o helper de criptografia
        
        Args:
            password: Senha para derivar a chave de criptografia
        """
        self.cipher = self._create_cipher(password)
    
    @staticmethod
    def _create_cipher(password: str) -> Fernet:
        """
        Cria cipher Fernet a partir da senha
        
        Args:
            password: Senha em texto
            
        Returns:
            Fernet: Cipher pronto para uso
        """
        # Deriva uma chave de 32 bytes da senha usando SHA-256
        key_bytes = hashlib.sha256(password.encode()).digest()
        # Converte para formato base64 URL-safe (necessário para Fernet)
        key_b64 = base64.urlsafe_b64encode(key_bytes)
        return Fernet(key_b64)
    
    def encrypt_bytes(self, data: bytes) -> Optional[bytes]:
        """
        Criptografa dados em bytes
        
        Args:
            data: Dados para criptografar
            
        Returns:
            bytes: Dados criptografados ou None
        """
        if data is None:
            return None
        
        try:
            return self.cipher.encrypt(data)
        except Exception as e:
            print(f"Erro ao criptografar: {e}")
            return None
    
    def decrypt_bytes(self, encrypted_data: bytes) -> Optional[bytes]:
        """
        Descriptografa dados em bytes
        
        Args:
            encrypted_data: Dados criptografados
            
        Returns:
            bytes: Dados descriptografados ou None
        """
        if encrypted_data is None:
            return None
        
        try:
            return self.cipher.decrypt(encrypted_data)
        except Exception as e:
            print(f"Erro ao descriptografar: {e}")
            return None
    
    def encrypt_text(self, text: str) -> Optional[str]:
        """
        Criptografa texto e retorna como string base64
        
        Args:
            text: Texto para criptografar
            
        Returns:
            str: Texto criptografado em base64 ou None
        """
        if text is None:
            return None
        
        encrypted = self.encrypt_bytes(text.encode('utf-8'))
        return base64.b64encode(encrypted).decode('utf-8') if encrypted else None
    
    def decrypt_text(self, encrypted_text: str) -> Optional[str]:
        """
        Descriptografa texto de string base64
        
        Args:
            encrypted_text: Texto criptografado em base64
            
        Returns:
            str: Texto descriptografado ou None
        """
        if encrypted_text is None:
            return None
        
        try:
            encrypted_bytes = base64.b64decode(encrypted_text.encode('utf-8'))
            decrypted = self.decrypt_bytes(encrypted_bytes)
            return decrypted.decode('utf-8') if decrypted else None
        except Exception as e:
            print(f"Erro ao descriptografar texto: {e}")
            return None
