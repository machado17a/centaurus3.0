"""
Extrator STANDALONE de imagens do banco de dados
Não depende de nenhum módulo da aplicação - apenas cryptography
"""
import sqlite3
import os
from pathlib import Path
from cryptography.fernet import Fernet

# Chave de criptografia (mesma usada na aplicação)
ENCRYPTION_KEY = b'2r5u8x/A?D(G+KbPeShVmYq3t6w9z$C&'


def get_cipher():
    """Cria o cipher Fernet"""
    # Deriva chave de 32 bytes para base64 de 44 bytes
    import base64
    import hashlib
    derived_key = hashlib.sha256(ENCRYPTION_KEY).digest()
    b64_key = base64.urlsafe_b64encode(derived_key)
    return Fernet(b64_key)


def decrypt_blob(encrypted_blob):
    """Descriptografa um blob"""
    cipher = get_cipher()
    return cipher.decrypt(bytes(encrypted_blob))


def encontrar_banco():
    """Encontra o banco de dados"""
    locais = [
        Path(os.environ.get('PROGRAMDATA', 'C:/ProgramData')) / 'Centaurus' / 'verificacoes' / 'verificacoes.db',
        Path(__file__).parent / 'verificacoes.db',
    ]
    
    for local in locais:
        if local.exists():
            return local
    return None


def extrair_imagens_verificacao(db_path, verificacao_id, pasta_saida):
    """Extrai e salva as imagens de uma verificação como arquivos PNG"""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Busca informações da verificação
    cursor.execute("""
        SELECT timestamp, similaridade, status, modo_verificacao, cabine_id, usuario_windows
        FROM verificacoes
        WHERE id = ?
    """, (verificacao_id,))
    
    verif = cursor.fetchone()
    if not verif:
        print(f"Verificação {verificacao_id} não encontrada!")
        conn.close()
        return 0
    
    timestamp, similaridade, status, modo, cabine, usuario = verif
    
    # Cria pasta de saída
    pasta_verif = pasta_saida / f"verificacao_{verificacao_id:04d}"
    pasta_verif.mkdir(parents=True, exist_ok=True)
    
    # Salva info em txt
    info_file = pasta_verif / "info.txt"
    with open(info_file, 'w', encoding='utf-8') as f:
        f.write(f"Verificação #{verificacao_id}\n")
        f.write(f"Data/Hora: {timestamp}\n")
        f.write(f"Similaridade: {similaridade:.2f}%\n")
        f.write(f"Status: {status}\n")
        f.write(f"Modo: {modo}\n")
        f.write(f"Cabine: {cabine or 'N/A'}\n")
        f.write(f"Usuário: {usuario or 'N/A'}\n")
    
    print(f"\n{'='*70}")
    print(f"VERIFICAÇÃO #{verificacao_id}")
    print(f"{'='*70}")
    print(f"Data/Hora: {timestamp}")
    print(f"Similaridade: {similaridade:.2f}%")
    print(f"Status: {status}")
    print(f"Cabine: {cabine or 'N/A'}")
    
    # Busca as imagens
    cursor.execute("""
        SELECT tipo_imagem, imagem_blob_encrypted, largura, altura, tamanho_bytes
        FROM imagens
        WHERE verificacao_id = ?
        ORDER BY tipo_imagem
    """, (verificacao_id,))
    
    imagens = cursor.fetchall()
    conn.close()
    
    if not imagens:
        print("Nenhuma imagem encontrada!")
        return 0
    
    print(f"\nExtraindo {len(imagens)} imagens...\n")
    
    # Processa cada imagem
    count = 0
    for tipo, blob_encrypted, largura, altura, tamanho in imagens:
        try:
            # Descriptografa
            blob_decrypted = decrypt_blob(blob_encrypted)
            
            # Salva como PNG
            filename = f"{tipo}.png"
            filepath = pasta_verif / filename
            
            with open(filepath, 'wb') as f:
                f.write(blob_decrypted)
            
            # Verifica se o arquivo foi criado
            if filepath.exists():
                tamanho_arquivo = filepath.stat().st_size
                print(f"  ✓ {filename:<15} ({largura}x{altura}) → {tamanho_arquivo:,} bytes")
                count += 1
            else:
                print(f"  ✗ Falha ao salvar {filename}")
            
        except Exception as e:
            print(f"  ✗ Erro ao extrair {tipo}: {e}")
    
    print(f"\n✓ {count} imagens extraídas para: {pasta_verif}")
    print(f"{'='*70}\n")
    
    return count


def listar_verificacoes(db_path, limit=15):
    """Lista as verificações disponíveis"""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    cursor.execute(f"""
        SELECT v.id, v.timestamp, v.similaridade, v.status, COUNT(i.id) as num_imgs
        FROM verificacoes v
        LEFT JOIN imagens i ON v.id = i.verificacao_id
        GROUP BY v.id
        ORDER BY v.id DESC
        LIMIT {limit}
    """)
    
    verificacoes = cursor.fetchall()
    conn.close()
    
    print("="*70)
    print(f"ÚLTIMAS {limit} VERIFICAÇÕES")
    print("="*70)
    print(f"{'ID':<5} {'Data/Hora':<20} {'Sim%':<7} {'Status':<25} {'Imgs':<5}")
    print("-"*70)
    
    for row in verificacoes:
        vid, timestamp, sim, status, num_imgs = row
        print(f"{vid:<5} {timestamp:<20} {sim:>6.1f} {status:<25} {num_imgs:<5}")
    
    print("="*70)
    return [v[0] for v in verificacoes]


def extrair_todas(db_path, pasta_saida, limit=None):
    """Extrai imagens de todas as verificações"""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    query = """
        SELECT DISTINCT v.id
        FROM verificacoes v
        INNER JOIN imagens i ON v.id = i.verificacao_id
        ORDER BY v.id DESC
    """
    
    if limit:
        query += f" LIMIT {limit}"
    
    cursor.execute(query)
    ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    print(f"\nExtraindo imagens de {len(ids)} verificações...\n")
    
    total_imgs = 0
    for i, vid in enumerate(ids, 1):
        print(f"[{i}/{len(ids)}] ", end='')
        count = extrair_imagens_verificacao(db_path, vid, pasta_saida)
        total_imgs += count
    
    print(f"\n{'='*70}")
    print(f"✓ CONCLUÍDO: {total_imgs} imagens extraídas de {len(ids)} verificações")
    print(f"  Localização: {pasta_saida.absolute()}")
    print(f"{'='*70}\n")
    
    # Abre a pasta no Explorer
    import subprocess
    subprocess.Popen(f'explorer "{pasta_saida.absolute()}"')


def main():
    print("\n" + "="*70)
    print("EXTRATOR DE IMAGENS DO BANCO DE DADOS CENTAURUS")
    print("="*70 + "\n")
    
    # Encontra o banco
    db_path = encontrar_banco()
    if not db_path:
        print("✗ Banco de dados não encontrado!")
        input("\nPressione Enter para sair...")
        return
    
    print(f"✓ Banco encontrado: {db_path}\n")
    
    # Define pasta de saída
    pasta_saida = Path(__file__).parent / "imagens_extraidas"
    pasta_saida.mkdir(exist_ok=True)
    
    # Lista verificações disponíveis
    ids_disponiveis = listar_verificacoes(db_path, limit=15)
    
    if not ids_disponiveis:
        print("\nNenhuma verificação encontrada no banco.")
        input("\nPressione Enter para sair...")
        return
    
    # Menu
    print("\nOpções:")
    print("  [1] Extrair imagens de UMA verificação específica")
    print("  [2] Extrair imagens de TODAS as verificações")
    print("  [q] Sair")
    
    escolha = input("\n> ").strip()
    
    if escolha == '1':
        vid = input("Digite o ID da verificação: ").strip()
        try:
            verificacao_id = int(vid)
            if verificacao_id in ids_disponiveis:
                extrair_imagens_verificacao(db_path, verificacao_id, pasta_saida)
                print(f"\n✓ Abrindo pasta: {pasta_saida.absolute()}")
                import subprocess
                subprocess.Popen(f'explorer "{pasta_saida.absolute()}"')
            else:
                print(f"⚠️  ID {verificacao_id} não encontrado.")
        except ValueError:
            print("⚠️  ID inválido.")
        
        input("\nPressione Enter para sair...")
    
    elif escolha == '2':
        confirma = input("Extrair TODAS as imagens? (s/n): ").strip().lower()
        if confirma == 's':
            extrair_todas(db_path, pasta_saida)
        else:
            print("Cancelado.")
        
        input("\nPressione Enter para sair...")
    
    elif escolha.lower() == 'q':
        print("Encerrando...")
    
    else:
        print("Opção inválida.")
        input("\nPressione Enter para sair...")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n✗ ERRO: {e}")
        import traceback
        traceback.print_exc()
        input("\nPressione Enter para sair...")
