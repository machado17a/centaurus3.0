"""
Download do modelo AuraFace v1 do HuggingFace Hub
Executa uma vez para baixar os arquivos ONNX necessários.

Uso:
    python download_model.py

Após a execução, a pasta models/auraface/ conterá os modelos prontos.
Licença do modelo: Apache 2.0 (uso comercial permitido)
"""
import sys
from pathlib import Path


def main():
    print("=" * 60)
    print("  Centaurus 3.0 - Download do Modelo AuraFace v1")
    print("  Licença: Apache 2.0 (uso comercial permitido)")
    print("=" * 60)
    
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("\n❌ Pacote 'huggingface_hub' não encontrado.")
        print("   Instale com: pip install huggingface_hub")
        sys.exit(1)
    
    # Diretório de destino: models/auraface/
    base_dir = Path(__file__).parent
    models_dir = base_dir / "models"
    auraface_dir = models_dir / "auraface"
    
    print(f"\n📂 Diretório de destino: {auraface_dir}")
    
    # Verifica se já existe
    if auraface_dir.exists():
        onnx_files = list(auraface_dir.glob("*.onnx"))
        if len(onnx_files) >= 2:
            print(f"\n✅ Modelo AuraFace já existe com {len(onnx_files)} arquivos .onnx:")
            for f in onnx_files:
                print(f"   - {f.name} ({f.stat().st_size / 1024 / 1024:.1f} MB)")
            
            resp = input("\n🔄 Deseja baixar novamente? (s/N): ").strip().lower()
            if resp != 's':
                print("Download cancelado.")
                return
    
    print("\n⬇️  Baixando modelo AuraFace v1 do HuggingFace...")
    print("   Repositório: fal/AuraFace-v1")
    print("   Isso pode levar alguns minutos...\n")
    
    try:
        snapshot_download(
            repo_id="fal/AuraFace-v1",
            local_dir=str(auraface_dir),
        )
        
        # Verifica resultado
        onnx_files = list(auraface_dir.glob("*.onnx"))
        if len(onnx_files) >= 2:
            print(f"\n✅ Download concluído com sucesso!")
            print(f"   {len(onnx_files)} arquivos .onnx baixados:")
            for f in sorted(onnx_files):
                size_mb = f.stat().st_size / 1024 / 1024
                print(f"   - {f.name} ({size_mb:.1f} MB)")
            print(f"\n📂 Modelos salvos em: {auraface_dir}")
            print("\n🚀 Agora execute: python app.py")
        else:
            # Pode ser que os .onnx estejam em subpasta
            all_onnx = list(auraface_dir.rglob("*.onnx"))
            if all_onnx:
                print(f"\n⚠️  Arquivos .onnx encontrados em subpastas:")
                for f in all_onnx:
                    print(f"   - {f.relative_to(auraface_dir)}")
                print("\n   O sistema detecta subpastas automaticamente.")
            else:
                print("\n❌ Nenhum arquivo .onnx encontrado após download!")
                print("   Verifique sua conexão com a internet.")
                sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Erro durante o download: {e}")
        print("\nTente novamente ou baixe manualmente de:")
        print("   https://huggingface.co/fal/AuraFace-v1")
        sys.exit(1)


if __name__ == "__main__":
    main()
