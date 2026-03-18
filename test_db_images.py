"""
Script de teste para diagnosticar problema de salvamento de imagens no banco
"""
import sys
import cv2
import numpy as np
from pathlib import Path

# Adiciona o diretório ao path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from database.db_manager import DatabaseManager
from config.settings import AppConfig

def criar_imagem_teste(cor, texto):
    """Cria uma imagem de teste"""
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    img[:] = cor  # Cor de fundo
    
    # Adiciona texto
    cv2.putText(img, texto, (150, 240), 
                cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
    
    return img

def main():
    print("="*70)
    print("TESTE DE SALVAMENTO DE IMAGENS NO BANCO DE DADOS")
    print("="*70)
    
    # Cria imagens de teste
    print("\n1. Criando imagens de teste...")
    img_doc = criar_imagem_teste((0, 0, 255), "DOCUMENTO")  # Vermelho
    img_webcam = criar_imagem_teste((0, 255, 0), "WEBCAM")  # Verde
    
    print(f"   - img_doc: shape={img_doc.shape}, dtype={img_doc.dtype}")
    print(f"   - img_webcam: shape={img_webcam.shape}, dtype={img_webcam.dtype}")
    
    # Conecta ao banco
    print("\n2. Conectando ao banco de dados...")
    db_path = AppConfig.get_db_path()
    print(f"   DB Path: {db_path}")
    
    db = DatabaseManager(str(db_path))
    print("   ✓ Conectado!")
    
    # Salva verificação com imagens
    print("\n3. Salvando verificação com imagens...")
    try:
        verificacao_id = db.salvar_verificacao(
            similaridade=85.5,
            status="Teste",
            modo_verificacao="documento",
            camera_index=0,
            cabine_id="TEST",
            img_documento=img_doc,
            img_webcam=img_webcam,
            screenshot_resultado=None
        )
        print(f"   ✓ Verificação salva! ID: {verificacao_id}")
    except Exception as e:
        print(f"   ✗ ERRO ao salvar: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Verifica se imagens foram salvas
    print("\n4. Verificando imagens no banco...")
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT id, tipo_imagem, largura, altura, tamanho_bytes 
        FROM imagens 
        WHERE verificacao_id = ?
    """, (verificacao_id,))
    
    imagens = cursor.fetchall()
    print(f"   Encontradas {len(imagens)} imagens:")
    for img_id, tipo, largura, altura, tamanho in imagens:
        print(f"   - ID {img_id}: {tipo} ({largura}x{altura}, {tamanho} bytes)")
    
    if len(imagens) == 0:
        print("\n   ⚠️  PROBLEMA: Nenhuma imagem foi salva no banco!")
    elif len(imagens) != 2:
        print(f"\n   ⚠️  PROBLEMA: Esperadas 2 imagens, encontradas {len(imagens)}")
    else:
        print("\n   ✓ Imagens salvas corretamente!")
    
    # Tenta recuperar as imagens
    print("\n5. Testando recuperação das imagens...")
    for tipo in ['documento', 'webcam']:
        try:
            img_recuperada = db.carregar_imagem(verificacao_id, tipo)
            if img_recuperada is not None:
                print(f"   ✓ {tipo}: recuperada com sucesso! Shape: {img_recuperada.shape}")
            else:
                print(f"   ✗ {tipo}: retornou None")
        except Exception as e:
            print(f"   ✗ {tipo}: erro ao recuperar - {e}")
    
    print("\n" + "="*70)
    print("TESTE CONCLUÍDO")
    print("="*70)
    
    db.close()

if __name__ == "__main__":
    main()
