"""
Consolidador de Bancos - Ferramenta para Consolidação Mensal
Une múltiplos arquivos .db de diferentes cabines em um único banco mestre
"""
import sqlite3
import os
import argparse
from datetime import datetime
import sys
import os

# Adiciona o diretório 'centaurus' ao path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'centaurus'))

from database_manager import DatabaseManager
import shutil

class ConsolidadorDB:
    def __init__(self, pasta_origem, arquivo_destino):
        """
        Inicializa o consolidador
        
        Args:
            pasta_origem: Pasta contendo os arquivos .db das cabines
            arquivo_destino: Caminho para o arquivo .db consolidado
        """
        self.pasta_origem = pasta_origem
        self.arquivo_destino = arquivo_destino
        self.conn_dest = None
        
    def consolidar(self):
        """Executa a consolidação dos bancos"""
        print(f"\n{'='*60}")
        print(f"Consolidador de Bancos - Centaurus")
        print(f"{'='*60}\n")
        
        # Verificar pasta de origem
        if not os.path.exists(self.pasta_origem):
            print(f"❌ Erro: Pasta '{self.pasta_origem}' não existe")
            return False
        
        # Encontrar arquivos .db
        db_files = [f for f in os.listdir(self.pasta_origem) if f.endswith('.db')]
        
        if not db_files:
            print(f"❌ Erro: Nenhum arquivo .db encontrado em '{self.pasta_origem}'")
            return False
        
        print(f"📁 Pasta de origem: {self.pasta_origem}")
        print(f"📊 Encontrados {len(db_files)} arquivo(s) .db")
        print(f"💾 Arquivo destino: {self.arquivo_destino}\n")
        
        # Criar banco de destino
        print("🔧 Criando banco de dados consolidado...")
        self._criar_banco_destino()
        
        # Consolidar cada banco
        total_verificacoes = 0
        total_imagens = 0
        cabines = set()
        
        for db_file in db_files:
            db_path = os.path.join(self.pasta_origem, db_file)
            print(f"\n📥 Processando: {db_file}")
            
            try:
                verif_count, img_count, cab_set = self._copiar_dados(db_path)
                total_verificacoes += verif_count
                total_imagens += img_count
                cabines.update(cab_set)
                
                print(f"   ✓ {verif_count} verificações copiadas")
                print(f"   ✓ {img_count} imagens copiadas")
                
            except Exception as e:
                print(f"   ❌ Erro ao processar {db_file}: {e}")
        
        # Fechar conexão
        if self.conn_dest:
            self.conn_dest.commit()
            self.conn_dest.close()
        
        # Resumo final
        print(f"\n{'='*60}")
        print(f"✅ Consolidação concluída!")
        print(f"{'='*60}")
        print(f"📊 Total de verificações: {total_verificacoes}")
        print(f"🖼️  Total de imagens: {total_imagens}")
        print(f"🏢 Cabines encontradas: {', '.join(sorted(cabines)) if cabines else 'Nenhuma'}")
        print(f"💾 Arquivo gerado: {self.arquivo_destino}")
        print(f"📏 Tamanho: {self._get_file_size(self.arquivo_destino)}\n")
        
        return True
    
    def _criar_banco_destino(self):
        """Cria o banco de dados de destino com a estrutura necessária"""
        # Se já existe, fazer backup
        if os.path.exists(self.arquivo_destino):
            backup = f"{self.arquivo_destino}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(self.arquivo_destino, backup)
            print(f"⚠️  Backup do arquivo existente criado: {backup}")
            os.remove(self.arquivo_destino)
        
        # Criar nova conexão
        self.conn_dest = sqlite3.connect(self.arquivo_destino)
        
        # Criar estrutura usando a mesma do DatabaseManager
        # Como não podemos instanciar DatabaseManager diretamente, vamos copiar a estrutura
        cursor = self.conn_dest.cursor()
        
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
        
        # Tabela de verificações
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS verificacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cabine_id TEXT,
                usuario_windows TEXT,
                timestamp DATETIME NOT NULL,
                similaridade REAL NOT NULL,
                status TEXT NOT NULL,
                modo_verificacao TEXT NOT NULL,
                camera_index INTEGER,
                maquina_id INTEGER NOT NULL,
                FOREIGN KEY (maquina_id) REFERENCES maquinas(id)
            )
        """)
        
        # Tabela de imagens
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
        
        # Tabela de casos suspeitos
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
        
        self.conn_dest.commit()
    
    def _copiar_dados(self, db_path):
        """Copia dados de um banco de origem para o banco destino"""
        conn_orig = sqlite3.connect(db_path)
        cursor_orig = conn_orig.cursor()
        cursor_dest = self.conn_dest.cursor()
        
        verif_count = 0
        img_count = 0
        cabines = set()
        
        # Mapeamento de IDs antigos para novos
        maquina_map = {}
        verif_map = {}
        
        # 1. Copiar máquinas
        cursor_orig.execute("SELECT * FROM maquinas")
        for row in cursor_orig.fetchall():
            old_id = row[0]
            # Verificar se já existe
            cursor_dest.execute(
                "SELECT id FROM maquinas WHERE hostname = ? AND username = ?",
                (row[1], row[2])
            )
            existing = cursor_dest.fetchone()
            
            if existing:
                maquina_map[old_id] = existing[0]
            else:
                cursor_dest.execute("""
                    INSERT INTO maquinas (hostname, username, sistema_operacional, versao_so,
                                         processador, memoria_ram, endereco_mac,
                                         primeira_execucao, ultima_execucao)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, row[1:])
                maquina_map[old_id] = cursor_dest.lastrowid
        
        # 2. Copiar verificações
        cursor_orig.execute("SELECT * FROM verificacoes")
        # Obter nomes das colunas para mapear corretamente
        col_names = [description[0] for description in cursor_orig.description]
        
        for row in cursor_orig.fetchall():
            row_dict = dict(zip(col_names, row))
            
            old_id = row_dict['id']
            cabine_id = row_dict.get('cabine_id')
            usuario_windows = row_dict.get('usuario_windows')
            timestamp = row_dict['timestamp']
            similaridade = row_dict['similaridade']
            status = row_dict['status']
            modo_verif = row_dict['modo_verificacao']
            camera_idx = row_dict.get('camera_index')
            maquina_id = row_dict['maquina_id']
            
            new_maquina_id = maquina_map.get(maquina_id, maquina_id)
            
            cursor_dest.execute("""
                INSERT INTO verificacoes (cabine_id, usuario_windows, timestamp, similaridade, status,
                                         modo_verificacao, camera_index, maquina_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (cabine_id, usuario_windows, timestamp, similaridade, status, modo_verif, camera_idx, new_maquina_id))
            
            verif_map[old_id] = cursor_dest.lastrowid
            verif_count += 1
            
            if cabine_id:
                cabines.add(cabine_id)
        
        # 3. Copiar imagens
        cursor_orig.execute("SELECT * FROM imagens")
        for row in cursor_orig.fetchall():
            # Assumindo ordem fixa pois schema de imagens não mudou
            old_id, old_verif_id, tipo, blob, largura, altura, tamanho = row
            new_verif_id = verif_map.get(old_verif_id)
            
            if new_verif_id:
                cursor_dest.execute("""
                    INSERT INTO imagens (verificacao_id, tipo_imagem, imagem_blob_encrypted,
                                        largura, altura, tamanho_bytes)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (new_verif_id, tipo, blob, largura, altura, tamanho))
                img_count += 1
        
        # 4. Copiar casos positivos
        try:
            cursor_orig.execute("SELECT * FROM casos_positivos")
            col_names = [description[0] for description in cursor_orig.description]
            
            for row in cursor_orig.fetchall():
                row_dict = dict(zip(col_names, row))
                old_verif_id = row_dict['verificacao_id']
                new_verif_id = verif_map.get(old_verif_id)
                
                if new_verif_id:
                    cursor_dest.execute("""
                        INSERT INTO casos_positivos (verificacao_id, cabine_id, usuario_windows, similaridade, timestamp)
                        VALUES (?, ?, ?, ?, ?)
                    """, (new_verif_id, row_dict.get('cabine_id'), row_dict.get('usuario_windows'), 
                          row_dict.get('similaridade'), row_dict.get('timestamp')))
        except sqlite3.OperationalError:
            pass  # Tabela pode não existir em bancos antigos
        
        # 5. Copiar casos suspeitos
        try:
            cursor_orig.execute("SELECT * FROM casos_suspeitos")
            col_names = [description[0] for description in cursor_orig.description]
            
            for row in cursor_orig.fetchall():
                row_dict = dict(zip(col_names, row))
                old_verif_id = row_dict['verificacao_id']
                new_verif_id = verif_map.get(old_verif_id)
                
                if new_verif_id:
                    cursor_dest.execute("""
                        INSERT INTO casos_suspeitos (verificacao_id, screenshot_encrypted, cabine_id, 
                                                   usuario_windows, similaridade, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (new_verif_id, row_dict.get('screenshot_encrypted'), row_dict.get('cabine_id'),
                          row_dict.get('usuario_windows'), row_dict.get('similaridade'), row_dict.get('timestamp')))
        except sqlite3.OperationalError:
            pass
        
        # 6. Copiar auditoria
        try:
            cursor_orig.execute("SELECT * FROM auditoria_documentos")
            for row in cursor_orig.fetchall():
                old_verif_id = row[1]
                new_verif_id = verif_map.get(old_verif_id)
                if new_verif_id:
                    cursor_dest.execute(
                        "INSERT INTO auditoria_documentos (verificacao_id) VALUES (?)",
                        (new_verif_id,)
                    )
        except sqlite3.OperationalError:
            pass
        
        conn_orig.close()
        return verif_count, img_count, cabines
    
    def _get_file_size(self, filepath):
        """Retorna tamanho do arquivo formatado"""
        size = os.path.getsize(filepath)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} TB"


def main():
    parser = argparse.ArgumentParser(description="Consolidador de Bancos de Dados - Centaurus")
    parser.add_argument("--pasta", "-p", required=True, help="Pasta contendo os arquivos .db")
    parser.add_argument("--saida", "-s", required=True, help="Arquivo .db de saída (consolidado)")
    
    args = parser.parse_args()
    
    consolidador = ConsolidadorDB(args.pasta, args.saida)
    success = consolidador.consolidar()
    
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
