# Script de Teste do Sistema de Banco de Dados
# Versão 1.0 - Testa todas as funcionalidades do database_manager

import os
import sys
import cv2
import numpy as np
from datetime import datetime

# Importa o gerenciador
from database_manager import DatabaseManager

def criar_imagem_teste(texto, cor=(255, 0, 0)):
    """Cria uma imagem de teste simples"""
    img = np.zeros((200, 300, 3), dtype=np.uint8)
    cv2.putText(img, texto, (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, cor, 2)
    return img

def teste_database_manager():
    """Testa todas as funcionalidades do DatabaseManager"""
    
    print("=" * 70)
    print("TESTE DO SISTEMA DE BANCO DE DADOS - CENTAURUS")
    print("=" * 70)
    
    # 1. Inicialização
    print("\n[1/6] Inicializando banco de dados...")
    test_dir = os.path.join(os.getcwd(), "test_database")
    os.makedirs(test_dir, exist_ok=True)
    
    try:
        db = DatabaseManager(test_dir)
        print("✓ Banco de dados inicializado com sucesso")
        print(f"  Localização: {db.db_path}")
        print(f"  Máquina ID: {db.maquina_id}")
    except Exception as e:
        print(f"✗ ERRO ao inicializar: {e}")
        return False
    
    # 2. Teste de salvamento - Caso Positivo
    print("\n[2/6] Testando salvamento de caso POSITIVO (>70%)...")
    try:
        img_doc = criar_imagem_teste("DOCUMENTO", (0, 255, 0))
        img_web = criar_imagem_teste("WEBCAM", (255, 0, 0))
        
        verificacao_id = db.salvar_verificacao(
            similaridade=85.5,
            status="Verificado com sucesso",
            modo_verificacao="screenshot",
            camera_index=0,
            img_documento=img_doc,
            img_webcam=img_web,
            screenshot_resultado=None
        )
        print(f"✓ Caso positivo salvo com ID: {verificacao_id}")
    except Exception as e:
        print(f"✗ ERRO ao salvar caso positivo: {e}")
        return False
    
    # 3. Teste de salvamento - Caso Suspeito
    print("\n[3/6] Testando salvamento de caso SUSPEITO (<70%)...")
    try:
        img_doc2 = criar_imagem_teste("DOC2", (0, 0, 255))
        img_web2 = criar_imagem_teste("CAM2", (255, 255, 0))
        img_screenshot = criar_imagem_teste("SCREENSHOT", (128, 128, 128))
        
        verificacao_id2 = db.salvar_verificacao(
            similaridade=55.3,
            status="Chamar especialista",
            modo_verificacao="documento",
            camera_index=1,
            img_documento=img_doc2,
            img_webcam=img_web2,
            screenshot_resultado=img_screenshot
        )
        print(f"✓ Caso suspeito salvo com ID: {verificacao_id2}")
    except Exception as e:
        print(f"✗ ERRO ao salvar caso suspeito: {e}")
        return False
    
    # 4. Teste de contagem
    print("\n[4/6] Testando contagem de verificações...")
    try:
        count = db.contar_verificacoes_hoje()
        print(f"✓ Total de verificações hoje: {count}")
        if count != 2:
            print("⚠ AVISO: Esperado 2 verificações, obtido", count)
    except Exception as e:
        print(f"✗ ERRO ao contar verificações: {e}")
        return False
    
    # 5. Teste de estatísticas
    print("\n[5/6] Testando estatísticas...")
    try:
        stats = db.get_estatisticas()
        print(f"✓ Estatísticas obtidas:")
        print(f"  - Total de verificações: {stats['total_verificacoes']}")
        print(f"  - Verificações hoje: {stats['verificacoes_hoje']}")
        print(f"  - Por status:")
        for status, total in stats['por_status'].items():
            print(f"    • {status}: {total}")
    except Exception as e:
        print(f"✗ ERRO ao obter estatísticas: {e}")
        return False
    
    # 6. Teste de consulta SQL direta
    print("\n[6/6] Testando consultas SQL diretas...")
    try:
        cursor = db.conn.cursor()
        
        # Verifica tabelas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tabelas = [row[0] for row in cursor.fetchall()]
        print(f"✓ Tabelas criadas: {', '.join(tabelas)}")
        
        # Verifica casos positivos
        cursor.execute("SELECT COUNT(*) FROM casos_positivos")
        casos_pos = cursor.fetchone()[0]
        print(f"✓ Casos positivos: {casos_pos}")
        
        # Verifica casos suspeitos
        cursor.execute("SELECT COUNT(*) FROM casos_suspeitos")
        casos_susp = cursor.fetchone()[0]
        print(f"✓ Casos suspeitos: {casos_susp}")
        
        # Verifica imagens
        cursor.execute("SELECT COUNT(*) FROM imagens")
        total_imgs = cursor.fetchone()[0]
        print(f"✓ Total de imagens salvas: {total_imgs}")
        
    except Exception as e:
        print(f"✗ ERRO nas consultas SQL: {e}")
        return False
    
    # Fecha conexão
    db.close()
    
    print("\n" + "=" * 70)
    print("✅ TODOS OS TESTES PASSARAM COM SUCESSO!")
    print("=" * 70)
    print(f"\n📁 Arquivo de teste criado: {db.db_path}")
    print("📝 Tamanho do arquivo:", os.path.getsize(db.db_path) / 1024, "KB")
    print("\n💡 Próximos passos:")
    print("   1. Teste descriptografar o arquivo com: python descriptografar_db.py")
    print("   2. Abra o arquivo descriptografado no DBeaver")
    print("   3. Delete a pasta 'test_database' após os testes")
    
    return True

if __name__ == "__main__":
    sucesso = teste_database_manager()
    sys.exit(0 if sucesso else 1)
