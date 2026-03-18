"""
Script para verificar o conteúdo do banco de dados de produção
"""
import sqlite3
from pathlib import Path
import os

def verificar_banco():
    # Possíveis locais do banco
    locais = [
        Path(os.environ.get('PROGRAMDATA', 'C:/ProgramData')) / 'Centaurus' / 'verificacoes' / 'verificacoes.db',
        Path(__file__).parent / 'verificacoes.db',
        Path(os.environ.get('USERPROFILE', '')) / 'AppData' / 'Local' / 'Centaurus' / 'verificacoes.db'
    ]
    
    print("="*70)
    print("VERIFICAÇÃO DO BANCO DE DADOS")
    print("="*70)
    
    db_path = None
    for local in locais:
        if local.exists():
            print(f"\n✓ Banco encontrado em: {local}")
            db_path = local
            break
    
    if not db_path:
        print("\n✗ Banco de dados não encontrado em nenhum local esperado:")
        for local in locais:
            print(f"  - {local}")
        return
    
    # Conecta ao banco
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Verifica verificações
    print("\n" + "="*70)
    print("VERIFICAÇÕES")
    print("="*70)
    cursor.execute("SELECT COUNT(*) FROM verificacoes")
    total = cursor.fetchone()[0]
    print(f"Total de verificações: {total}")
    
    if total > 0:
        cursor.execute("""
            SELECT id, timestamp, similaridade, status, modo_verificacao 
            FROM verificacoes 
            ORDER BY id DESC 
            LIMIT 5
        """)
        print("\nÚltimas 5 verificações:")
        for row in cursor.fetchall():
            print(f"  ID: {row[0]} | {row[1]} | {row[2]:.1f}% | {row[3]} | {row[4]}")
    
    # Verifica imagens
    print("\n" + "="*70)
    print("IMAGENS")
    print("="*70)
    cursor.execute("SELECT COUNT(*) FROM imagens")
    total_imgs = cursor.fetchone()[0]
    print(f"Total de imagens: {total_imgs}")
    
    if total_imgs > 0:
        cursor.execute("""
            SELECT verificacao_id, tipo_imagem, largura, altura, tamanho_bytes 
            FROM imagens 
            ORDER BY id DESC 
            LIMIT 10
        """)
        print("\nÚltimas 10 imagens:")
        for row in cursor.fetchall():
            print(f"  Verif ID: {row[0]} | {row[1]:10s} | {row[2]}x{row[3]} | {row[4]:,} bytes")
    else:
        print("\n⚠️  PROBLEMA CONFIRMADO: Nenhuma imagem no banco!")
        print("\nVerificando se há verificações sem imagens:")
        cursor.execute("""
            SELECT v.id, v.timestamp, v.similaridade, v.status
            FROM verificacoes v
            LEFT JOIN imagens i ON v.id = i.verificacao_id
            WHERE i.id IS NULL
            ORDER BY v.id DESC
            LIMIT 10
        """)
        sem_imgs = cursor.fetchall()
        if sem_imgs:
            print(f"\n{len(sem_imgs)} verificações SEM imagens associadas:")
            for row in sem_imgs:
                print(f"  ID: {row[0]} | {row[1]} | {row[2]:.1f}% | {row[3]}")
    
    # Verifica casos positivos e suspeitos
    print("\n" + "="*70)
    print("CASOS POSITIVOS E SUSPEITOS")
    print("="*70)
    cursor.execute("SELECT COUNT(*) FROM casos_positivos")
    positivos = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM casos_suspeitos")
    suspeitos = cursor.fetchone()[0]
    print(f"Casos positivos: {positivos}")
    print(f"Casos suspeitos: {suspeitos}")
    
    conn.close()
    print("\n" + "="*70)

if __name__ == "__main__":
    verificar_banco()
