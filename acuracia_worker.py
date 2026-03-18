"""
Workers de multiprocessing para teste_acuracia.py
Arquivo separado: não importa tkinter/ttkbootstrap, evitando falhas no spawn do Windows.
"""
import sys
from pathlib import Path

import cv2
import numpy as np

# Garante que o projeto está no path do worker
sys.path.insert(0, str(Path(__file__).parent))

_worker_model = None


def worker_init(models_dir_str: str, model_name: str):
    """Carrega o modelo AuraFace uma vez por processo worker (com retry)."""
    global _worker_model
    import time
    import random
    from core.models_loader import ModelsLoader
    from core.face_verifier import FaceVerifier
    from config.settings import AppConfig

    # Jitter inicial para evitar que todos os workers acessem os arquivos ONNX
    # exatamente ao mesmo tempo (pode gerar "Error parsing message" no Windows)
    time.sleep(random.uniform(0.0, 1.5))

    last_error = None
    for attempt in range(3):          # até 3 tentativas
        try:
            loader = ModelsLoader(Path(models_dir_str))
            model = loader.load_model(model_name)
            _worker_model = FaceVerifier(model, AppConfig)
            return                    # sucesso — sai da função
        except Exception as e:
            last_error = e
            if attempt < 2:
                time.sleep(random.uniform(1.0, 3.0))  # backoff antes de tentar de novo

    # Todas as tentativas falharam — salva o erro para worker_task reportar
    _worker_model = f"INIT_ERROR:{last_error}"


def worker_task(args: tuple) -> dict:
    """Processa um único par de imagens num processo worker."""
    global _worker_model
    idx, doc_path, webcam_path, esperado = args

    result = {
        "idx": idx,
        "doc": doc_path,
        "webcam": webcam_path,
        "esperado": esperado,
        "erro": "",
        "faces_doc": 0,
        "faces_webcam": 0,
        "similaridade_pct": None,
        "cosseno": None,
        "status": "",
    }

    # Verifica se o modelo foi inicializado com sucesso
    if _worker_model is None:
        result["erro"] = "Modelo não inicializado (worker_init não foi chamado)"
        result["status"] = "Erro"
        return result

    if isinstance(_worker_model, str) and _worker_model.startswith("INIT_ERROR:"):
        result["erro"] = _worker_model[len("INIT_ERROR:"):]
        result["status"] = "Erro"
        return result

    try:
        img_doc = cv2.imread(doc_path)
        img_web = cv2.imread(webcam_path)

        if img_doc is None:
            raise FileNotFoundError(f"Não foi possível abrir: {Path(doc_path).name}")
        if img_web is None:
            raise FileNotFoundError(f"Não foi possível abrir: {Path(webcam_path).name}")

        _, emb_doc = _worker_model.capture_face(img_doc)
        _, emb_web = _worker_model.capture_face(img_web)

        result["faces_doc"]    = _worker_model.count_faces(img_doc)
        result["faces_webcam"] = _worker_model.count_faces(img_web)

        if emb_doc is None:
            raise ValueError("Sem face detectada na imagem do documento")
        if emb_web is None:
            raise ValueError("Sem face detectada na imagem da câmera")

        vr  = _worker_model.verify_faces(emb_doc, emb_web)
        cos = float(np.clip(np.dot(emb_doc, emb_web), -1.0, 1.0))

        result["similaridade_pct"] = round(float(vr.similarity), 4)
        result["cosseno"]          = round(cos, 6)
        result["status"]           = vr.status

    except Exception as e:
        result["erro"]   = str(e)
        result["status"] = "Erro"

    return result
