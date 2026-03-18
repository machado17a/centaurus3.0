"""
Centaurus - Sistema de Verificação Facial
Entry Point Principal da Aplicação
Versão 3.0 - AuraFace (Apache 2.0)
"""
import sys
import os
import logging
from pathlib import Path

# Adiciona o diretório centaurus ao path se necessário
if getattr(sys, 'frozen', False):
    # Executando como .exe
    BASE_DIR = Path(sys.executable).parent
else:
    # Executando como script
    BASE_DIR = Path(__file__).parent
    sys.path.insert(0, str(BASE_DIR))

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def check_dependencies():
    """Verifica dependências críticas"""
    # Em executável empacotado, pula verificação (já está tudo incluído)
    if getattr(sys, 'frozen', False):
        return True
    
    # Em modo desenvolvimento, verifica dependências
    try:
        import cv2
        import numpy
        import PIL
        import ttkbootstrap
        import insightface
        import onnxruntime
        import cryptography
        return True
    except ImportError as e:
        logger.error(f"Dependência faltando: {e}")
        return False


def main():
    """Entry point principal"""
    try:
        logger.info("="*70)
        logger.info("🚀 Centaurus - Sistema de Verificação Facial")
        logger.info("   Versão 3.0 - AuraFace (Apache 2.0)")
        logger.info("="*70)
        
        # Verifica dependências
        if not check_dependencies():
            logger.error("❌ Erro: Dependências não instaladas")
            logger.error("Execute: pip install -r requirements.txt")
            sys.exit(1)
        
        # Importações tardias para performance
        from config.settings import AppConfig
        from config.paths import PathManager
        from ui.main_window import CentaurusApp
        import ttkbootstrap as ttk
        
        logger.info(f"📂 Diretório base: {AppConfig.get_base_dir()}")
        logger.info(f"📂 Diretório de dados: {AppConfig.get_data_dir()}")
        
        # Inicializa caminhos
        if not PathManager.initialize_all_paths():
            logger.error("❌ Erro ao criar diretórios necessários")
            sys.exit(1)
        
        # Valida modelos
        models_ok, models_msg = PathManager.validate_models_dir()
        if not models_ok:
            logger.error(f"❌ {models_msg}")
            import tkinter.messagebox as mb
            mb.showerror(
                "Modelos não encontrados",
                f"{models_msg}\n\n"
                "Por favor, certifique-se de que a pasta 'models' está presente."
            )
            sys.exit(1)
        
        logger.info("✅ Modelos validados")
        logger.info("✅ Iniciando interface...")
        
        # Cria aplicação
        root = ttk.Window(themename=AppConfig.DEFAULT_THEME)
        app = CentaurusApp(root)
        
        logger.info("✅ Aplicação iniciada com sucesso!")
        root.mainloop()
        
        logger.info("👋 Aplicação encerrada")
        
    except KeyboardInterrupt:
        logger.info("\n👋 Aplicação interrompida pelo usuário")
        sys.exit(0)
        
    except Exception as e:
        logger.exception("❌ Erro crítico ao iniciar aplicação")
        
        try:
            import tkinter.messagebox as mb
            mb.showerror(
                "Erro Fatal",
                f"Não foi possível iniciar o Centaurus:\n\n{e}\n\n"
                f"Verifique os logs para mais detalhes."
            )
        except:
            pass
        
        sys.exit(1)


if __name__ == "__main__":
    main()
