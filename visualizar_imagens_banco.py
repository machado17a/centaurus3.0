"""
Script para visualizar imagens salvas no banco de dados
"""
import sys
from pathlib import Path
import sqlite3
import os

# Adiciona o diretório ao path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

try:
    import cv2
    import numpy as np
    from database.encryption import decrypt_blob
except ImportError as e:
    print(f"Erro ao importar dependências: {e}")
    print("Execute: pip install opencv-python numpy cryptography")
    sys.exit(1)


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


def bytes_to_image(img_bytes):
    """Converte bytes para imagem OpenCV"""
    if img_bytes is None:
        return None
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img


def visualizar_verificacao(db_path, verificacao_id):
    """Visualiza as imagens de uma verificação específica"""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Busca informações da verificação
    cursor.execute("""
        SELECT timestamp, similaridade, status, modo_verificacao, cabine_id
        FROM verificacoes
        WHERE id = ?
    """, (verificacao_id,))
    
    verif = cursor.fetchone()
    if not verif:
        print(f"Verificação {verificacao_id} não encontrada!")
        conn.close()
        return
    
    timestamp, similaridade, status, modo, cabine = verif
    
    print("="*70)
    print(f"VERIFICAÇÃO #{verificacao_id}")
    print("="*70)
    print(f"Data/Hora: {timestamp}")
    print(f"Similaridade: {similaridade:.2f}%")
    print(f"Status: {status}")
    print(f"Modo: {modo}")
    print(f"Cabine: {cabine or 'N/A'}")
    print("="*70)
    
    # Busca as imagens
    cursor.execute("""
        SELECT tipo_imagem, imagem_blob_encrypted, largura, altura, tamanho_bytes
        FROM imagens
        WHERE verificacao_id = ?
        ORDER BY tipo_imagem
    """, (verificacao_id,))
    
    imagens = cursor.fetchall()
    
    if not imagens:
        print("Nenhuma imagem encontrada para esta verificação!")
        conn.close()
        return
    
    print(f"\nEncontradas {len(imagens)} imagens. Descriptografando e exibindo...\n")
    
    # Processa cada imagem
    imgs_para_mostrar = []
    for tipo, blob_encrypted, largura, altura, tamanho in imagens:
        print(f"[{tipo.upper()}] {largura}x{altura}, {tamanho:,} bytes")
        
        try:
            # Descriptografa
            blob_decrypted = decrypt_blob(blob_encrypted)
            
            # Converte para imagem
            img = bytes_to_image(blob_decrypted)
            
            if img is not None:
                # Adiciona texto
                label = "DOCUMENTO" if tipo == "documento" else "WEBCAM"
                img_com_label = img.copy()
                cv2.putText(img_com_label, label, (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                imgs_para_mostrar.append((label, img_com_label))
                print(f"  ✓ Descriptografada e decodificada: {img.shape}")
            else:
                print(f"  ✗ Erro ao decodificar imagem")
                
        except Exception as e:
            print(f"  ✗ Erro ao processar: {e}")
    
    conn.close()
    
    # Exibe as imagens
    if imgs_para_mostrar:
        print(f"\n{'='*70}")
        print("Exibindo imagens... (Pressione qualquer tecla para fechar)")
        print(f"{'='*70}\n")
        
        for label, img in imgs_para_mostrar:
            cv2.imshow(f"Verificacao #{verificacao_id} - {label}", img)
        
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    else:
        print("\nNenhuma imagem pôde ser carregada.")


def listar_verificacoes(db_path, limit=10):
    """Lista as verificações disponíveis"""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    cursor.execute(f"""
        SELECT v.id, v.timestamp, v.similaridade, v.status, v.modo_verificacao,
               COUNT(i.id) as num_imgs
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
        vid, timestamp, sim, status, modo, num_imgs = row
        print(f"{vid:<5} {timestamp:<20} {sim:>6.1f} {status:<25} {num_imgs:<5}")
    
    print("="*70)
    return [v[0] for v in verificacoes]


def main():
    print("\n" + "="*70)
    print("VISUALIZADOR DE IMAGENS DO BANCO DE DADOS")
    print("="*70 + "\n")
    
    # Encontra o banco
    db_path = encontrar_banco()
    if not db_path:
        print("✗ Banco de dados não encontrado!")
        return
    
    print(f"✓ Banco encontrado: {db_path}\n")
    
    # Lista verificações disponíveis
    ids_disponiveis = listar_verificacoes(db_path, limit=15)
    
    if not ids_disponiveis:
        print("\nNenhuma verificação encontrada no banco.")
        return
    
    # Menu interativo
    print("\nOpções:")
    print("  - Digite o ID da verificação para visualizar")
    print("  - Digite 'q' para sair")
    
    while True:
        try:
            escolha = input("\n> ").strip()
            
            if escolha.lower() == 'q':
                print("\nEncerrando...")
                break
            
            verificacao_id = int(escolha)
            
            if verificacao_id not in ids_disponiveis:
                print(f"⚠️  ID {verificacao_id} não está na lista. Tente outro.")
                continue
            
            visualizar_verificacao(db_path, verificacao_id)
            
        except ValueError:
            print("⚠️  Digite um número válido ou 'q' para sair")
        except KeyboardInterrupt:
            print("\n\nEncerrando...")
            break
        except Exception as e:
            print(f"✗ Erro: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
