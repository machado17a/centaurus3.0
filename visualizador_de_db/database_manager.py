# Database Manager - Gerenciador de Banco de Dados com Criptografia AES-256
# Versão 2.0 - Sistema com criptografia via cryptography (compatível Windows)

import sqlite3
import os
import platform
import socket
import psutil
from datetime import datetime
import cv2
import uuid
import numpy as np
from cryptography.fernet import Fernet
import hashlib
import base64
import threading

# Senha hardcoded para criptografia dos dados sensíveis
DB_PASSWORD = "Centaurus@PF2025!SecureDB#RFH"

class DatabaseManager:
    """Gerenciador de banco de dados SQLite com criptografia AES-256 nos BLOBs"""
    
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.db_path = os.path.join(base_dir, "verificacoes.db")
        self.conn = None
        self.maquina_id = None
        self.cipher = self._create_cipher()
        self._lock = threading.Lock()  # Lock para thread-safety
        self._initialize_database()
    
    def _create_cipher(self):
        """Cria o cipher Fernet a partir da senha"""
        # Deriva uma chave de 32 bytes da senha usando SHA-256
        key_bytes = hashlib.sha256(DB_PASSWORD.encode()).digest()
        # Converte para formato base64 URL-safe (necessário para Fernet)
        key_b64 = base64.urlsafe_b64encode(key_bytes)
        return Fernet(key_b64)
    
    def _encrypt_blob(self, data_bytes):
        """Criptografa bytes"""
        if data_bytes is None:
            return None
        return self.cipher.encrypt(data_bytes)
    
    def _decrypt_blob(self, encrypted_bytes):
        """Descriptografa bytes"""
        if encrypted_bytes is None:
            return None
        return self.cipher.decrypt(encrypted_bytes)
    
    def _initialize_database(self):
        """Inicializa o banco de dados"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        print(f"✓ Banco de dados: {self.db_path}")
        print(f"✓ Criptografia AES-256 ativada para imagens")
        self._create_tables()
        self.maquina_id = self._register_machine()
    
    def _create_tables(self):
        """Cria todas as tabelas do banco de dados"""
        cursor = self.conn.cursor()
        
        # Tabela de máquinas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS maquinas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hostname TEXT NOT NULL,
                username TEXT NOT NULL,
                sistema_operacional TEXT,
                versao_so TEXT,
                processador TEXT,
                memoria_ram TEXT,
                endereco_mac TEXT,
                primeira_execucao DATETIME NOT NULL,
                ultima_execucao DATETIME,
                UNIQUE(hostname, username)
            )
        """)
        
        # Tabela principal de verificações
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS verificacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cabine_id TEXT,
                timestamp DATETIME NOT NULL,
                similaridade REAL NOT NULL,
                status TEXT NOT NULL,
                modo_verificacao TEXT NOT NULL,
                camera_index INTEGER,
                maquina_id INTEGER NOT NULL,
                FOREIGN KEY (maquina_id) REFERENCES maquinas(id)
            )
        """)
        
        # Migration: Adicionar cabine_id se não existir
        try:
            cursor.execute("PRAGMA table_info(verificacoes)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'cabine_id' not in columns:
                print("⚠ Migrando banco: adicionando coluna cabine_id")
                cursor.execute("ALTER TABLE verificacoes ADD COLUMN cabine_id TEXT")
                print("✓ Coluna cabine_id adicionada")
            if 'usuario_windows' not in columns:
                print("⚠ Migrando banco: adicionando coluna usuario_windows")
                cursor.execute("ALTER TABLE verificacoes ADD COLUMN usuario_windows TEXT")
                print("✓ Coluna usuario_windows adicionada")
        except Exception as e:
            print(f"Erro na migration: {e}")
        
        # Tabela de imagens (BLOBs CRIPTOGRAFADOS)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS imagens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                verificacao_id INTEGER NOT NULL,
                tipo_imagem TEXT NOT NULL,
                imagem_blob_encrypted BLOB NOT NULL,
                largura INTEGER,
                altura INTEGER,
                tamanho_bytes INTEGER,
                FOREIGN KEY (verificacao_id) REFERENCES verificacoes(id) ON DELETE CASCADE
            )
        """)
        
        # Tabela de casos positivos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS casos_positivos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                verificacao_id INTEGER NOT NULL UNIQUE,
                cabine_id TEXT,
                usuario_windows TEXT,
                similaridade REAL,
                timestamp DATETIME,
                FOREIGN KEY (verificacao_id) REFERENCES verificacoes(id) ON DELETE CASCADE
            )
        """)
        
        # Tabela de casos suspeitos (screenshot CRIPTOGRAFADO)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS casos_suspeitos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                verificacao_id INTEGER NOT NULL UNIQUE,
                screenshot_encrypted BLOB,
                cabine_id TEXT,
                usuario_windows TEXT,
                similaridade REAL,
                timestamp DATETIME,
                FOREIGN KEY (verificacao_id) REFERENCES verificacoes(id) ON DELETE CASCADE
            )
        """)

        # Migration: Adicionar colunas de auditoria em tabelas existentes
        try:
            # Casos Positivos
            cursor.execute("PRAGMA table_info(casos_positivos)")
            cols_pos = [row[1] for row in cursor.fetchall()]
            if 'cabine_id' not in cols_pos:
                cursor.execute("ALTER TABLE casos_positivos ADD COLUMN cabine_id TEXT")
                cursor.execute("ALTER TABLE casos_positivos ADD COLUMN usuario_windows TEXT")
                cursor.execute("ALTER TABLE casos_positivos ADD COLUMN similaridade REAL")
                cursor.execute("ALTER TABLE casos_positivos ADD COLUMN timestamp DATETIME")
                print("✓ Colunas de auditoria adicionadas em casos_positivos")

            # Casos Suspeitos
            cursor.execute("PRAGMA table_info(casos_suspeitos)")
            cols_susp = [row[1] for row in cursor.fetchall()]
            if 'cabine_id' not in cols_susp:
                cursor.execute("ALTER TABLE casos_suspeitos ADD COLUMN cabine_id TEXT")
                cursor.execute("ALTER TABLE casos_suspeitos ADD COLUMN usuario_windows TEXT")
                cursor.execute("ALTER TABLE casos_suspeitos ADD COLUMN similaridade REAL")
                cursor.execute("ALTER TABLE casos_suspeitos ADD COLUMN timestamp DATETIME")
                print("✓ Colunas de auditoria adicionadas em casos_suspeitos")
        except Exception as e:
            print(f"Erro na migration de auditoria: {e}")
        
        # Tabela de auditoria
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auditoria_documentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                verificacao_id INTEGER NOT NULL UNIQUE,
                FOREIGN KEY (verificacao_id) REFERENCES verificacoes(id) ON DELETE CASCADE
            )
        """)
        
        # Índices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_verificacoes_cabine ON verificacoes(cabine_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_verificacoes_timestamp ON verificacoes(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_verificacoes_status ON verificacoes(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_verificacoes_maquina ON verificacoes(maquina_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_imagens_verificacao ON imagens(verificacao_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_maquinas_hostname_username ON maquinas(hostname, username)")
        
        self.conn.commit()
    
    def _get_machine_info(self):
        """Coleta informações da máquina"""
        try:
            hostname = socket.gethostname()
            username = os.getenv('USERNAME') or os.getenv('USER') or 'unknown'
            sistema_operacional = platform.system()
            versao_so = platform.version()
            processador = platform.processor()
            
            # Memória RAM
            mem = psutil.virtual_memory()
            memoria_ram = f"{mem.total / (1024**3):.2f} GB"
            
            # Endereço MAC
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                           for elements in range(0, 2*6, 2)][::-1])
            
            return {
                'hostname': hostname,
                'username': username,
                'sistema_operacional': sistema_operacional,
                'versao_so': versao_so,
                'processador': processador,
                'memoria_ram': memoria_ram,
                'endereco_mac': mac
            }
        except Exception as e:
            print(f"Erro ao coletar informações da máquina: {e}")
            return {
                'hostname': 'unknown',
                'username': 'unknown',
                'sistema_operacional': 'unknown',
                'versao_so': 'unknown',
                'processador': 'unknown',
                'memoria_ram': 'unknown',
                'endereco_mac': 'unknown'
            }
    
    def _register_machine(self):
        """Registra ou atualiza informações da máquina atual"""
        machine_info = self._get_machine_info()
        cursor = self.conn.cursor()
        
        # Verifica se a combinação hostname+username já existe
        cursor.execute(
            "SELECT id FROM maquinas WHERE hostname = ? AND username = ?", 
            (machine_info['hostname'], machine_info['username'])
        )
        row = cursor.fetchone()
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if row:
            # Atualiza última execução
            maquina_id = row[0]
            cursor.execute("UPDATE maquinas SET ultima_execucao = ? WHERE id = ?", (now, maquina_id))
        else:
            # Registra nova máquina (ou novo usuário na mesma máquina)
            cursor.execute("""
                INSERT INTO maquinas (hostname, username, sistema_operacional, versao_so, 
                                     processador, memoria_ram, endereco_mac, 
                                     primeira_execucao, ultima_execucao)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                machine_info['hostname'],
                machine_info['username'],
                machine_info['sistema_operacional'],
                machine_info['versao_so'],
                machine_info['processador'],
                machine_info['memoria_ram'],
                machine_info['endereco_mac'],
                now,
                now
            ))
            maquina_id = cursor.lastrowid
        
        self.conn.commit()
        return maquina_id
    
    def salvar_verificacao(self, similaridade, status, modo_verificacao, camera_index, 
                          cabine_id=None, img_documento=None, img_webcam=None, screenshot_resultado=None):
        """
        Salva uma verificação completa no banco de dados
        
        Args:
            similaridade: Percentual de similaridade
            status: Status da verificação
            modo_verificacao: 'screenshot' ou 'documento'
            camera_index: Índice da câmera usada
            cabine_id: ID da cabine (ex: "E4", "D12")
            img_documento: Imagem OpenCV do documento/screenshot
            img_webcam: Imagem OpenCV da webcam
            screenshot_resultado: Screenshot da janela de resultado (para casos suspeitos)
        
        Returns:
            verificacao_id: ID da verificação salva
        """
        with self._lock:
            cursor = self.conn.cursor()
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Obter usuário Windows atual
            import os
            usuario_windows = os.getenv('USERNAME', 'Desconhecido')
            
            # 1. Inserir verificação
            cursor.execute("""
                INSERT INTO verificacoes (cabine_id, usuario_windows, timestamp, similaridade, status, modo_verificacao, 
                                         camera_index, maquina_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (cabine_id, usuario_windows, timestamp, similaridade, status, modo_verificacao, camera_index, self.maquina_id))
            
            verificacao_id = cursor.lastrowid
            
            # 2. Salvar imagens CRIPTOGRAFADAS
            if img_documento is not None:
                self._salvar_imagem_encrypted(verificacao_id, 'documento', img_documento)
            
            if img_webcam is not None:
                self._salvar_imagem_encrypted(verificacao_id, 'webcam', img_webcam)
            
            # 3. Registrar em tabelas específicas
            if similaridade > 70:
                # Caso positivo
                cursor.execute("""
                    INSERT INTO casos_positivos (verificacao_id, cabine_id, usuario_windows, similaridade, timestamp) 
                    VALUES (?, ?, ?, ?, ?)
                """, (verificacao_id, cabine_id, usuario_windows, similaridade, timestamp))
            else:
                # Caso suspeito (screenshot será atualizado depois se fornecido)
                screenshot_encrypted = None
                if screenshot_resultado is not None:
                    screenshot_encrypted = self._encrypt_blob(self._image_to_bytes(screenshot_resultado))
                
                cursor.execute("""
                    INSERT INTO casos_suspeitos (verificacao_id, screenshot_encrypted, cabine_id, usuario_windows, similaridade, timestamp) 
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (verificacao_id, screenshot_encrypted, cabine_id, usuario_windows, similaridade, timestamp))
            
            # 4. Auditoria para modo documento
            if modo_verificacao == 'documento':
                cursor.execute("INSERT INTO auditoria_documentos (verificacao_id) VALUES (?)", (verificacao_id,))
            
            self.conn.commit()
            return verificacao_id

    def atualizar_screenshot_suspeito(self, verificacao_id, screenshot_img):
        """
        Atualiza o screenshot de um caso suspeito existente
        Args:
            verificacao_id: ID da verificação
            screenshot_img: Imagem PIL ou bytes do screenshot
        """
        with self._lock:
            cursor = self.conn.cursor()
            
            # Converte para bytes se necessário
            if hasattr(screenshot_img, 'save'):  # É imagem PIL
                import io
                img_byte_arr = io.BytesIO()
                screenshot_img.save(img_byte_arr, format='PNG')
                screenshot_bytes = img_byte_arr.getvalue()
            elif isinstance(screenshot_img, bytes):
                screenshot_bytes = screenshot_img
            else:
                return # Formato inválido
            
            # Criptografa
            screenshot_encrypted = self._encrypt_blob(screenshot_bytes)
            
            # Atualiza no banco
            cursor.execute("""
                UPDATE casos_suspeitos 
                SET screenshot_encrypted = ? 
                WHERE verificacao_id = ?
            """, (screenshot_encrypted, verificacao_id))
            
            self.conn.commit()
    
    def _salvar_imagem_encrypted(self, verificacao_id, tipo_imagem, img_cv):
        """Salva uma imagem CRIPTOGRAFADA como BLOB no banco"""
        if img_cv is None:
            return
        
        cursor = self.conn.cursor()
        
        # Converter imagem para bytes
        img_bytes = self._image_to_bytes(img_cv)
        if img_bytes is None:
            return
        
        # CRIPTOGRAFAR
        encrypted_blob = self._encrypt_blob(img_bytes)
        
        h, w = img_cv.shape[:2]
        tamanho = len(img_bytes)
        
        cursor.execute("""
            INSERT INTO imagens (verificacao_id, tipo_imagem, imagem_blob_encrypted, largura, altura, tamanho_bytes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (verificacao_id, tipo_imagem, encrypted_blob, w, h, tamanho))
    
    def _image_to_bytes(self, img_cv):
        """Converte imagem OpenCV para bytes (PNG)"""
        if img_cv is None:
            return None
        
        # Codificar imagem como PNG
        success, encoded = cv2.imencode('.png', img_cv)
        if success:
            return encoded.tobytes()
        return None
    
    def _bytes_to_image(self, img_bytes):
        """Converte bytes para imagem OpenCV"""
        if img_bytes is None:
            return None
        
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img
    
    def contar_verificacoes_hoje(self):
        """Retorna o número de verificações realizadas hoje"""
        with self._lock:
            cursor = self.conn.cursor()
            hoje = datetime.now().strftime('%Y-%m-%d')
            
            cursor.execute("""
                SELECT COUNT(*) FROM verificacoes 
                WHERE DATE(timestamp) = ?
            """, (hoje,))
            
            return cursor.fetchone()[0]
    
    def get_estatisticas(self):
        """Retorna estatísticas gerais do banco"""
        with self._lock:
            cursor = self.conn.cursor()
            
            stats = {}
            
            # Total de verificações
            cursor.execute("SELECT COUNT(*) FROM verificacoes")
            stats['total_verificacoes'] = cursor.fetchone()[0]
            
            # Total hoje (sem chamar o método para evitar deadlock)
            hoje = datetime.now().strftime('%Y-%m-%d')
            cursor.execute("SELECT COUNT(*) FROM verificacoes WHERE DATE(timestamp) = ?", (hoje,))
            stats['verificacoes_hoje'] = cursor.fetchone()[0]
            
            # Por status
            cursor.execute("SELECT status, COUNT(*) FROM verificacoes GROUP BY status")
            stats['por_status'] = {row[0]: row[1] for row in cursor.fetchall()}
            
            return stats
    
    def close(self):
        """Fecha a conexão com o banco"""
        if self.conn:
            self.conn.close()
