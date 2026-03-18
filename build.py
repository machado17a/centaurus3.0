"""
Build script para o Centaurus (modo pasta, sem onefile).
Requisitos:
- PyInstaller disponível no Python atual
- `centaurus.spec` presente na raiz do projeto
- Modelos em `models/antelopev2` antes do build
"""

from pathlib import Path
import shutil
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parent
SPEC_FILE = PROJECT_ROOT / "centaurus.spec"
BUILD_DIR = PROJECT_ROOT / "build"
DIST_DIR = PROJECT_ROOT / "dist"
DIST_NAME = "Centaurus"
DIST_BUNDLE = DIST_DIR / DIST_NAME
EXECUTABLE = DIST_BUNDLE / f"{DIST_NAME}.exe"
MODELS_SOURCE = PROJECT_ROOT / "models" / "antelopev2"
MODELS_TARGET = DIST_BUNDLE / "models" / "antelopev2"


def fail(message: str) -> None:
    print(f"[ERRO] {message}")
    sys.exit(1)


def check_prereqs() -> None:
    if not SPEC_FILE.exists():
        fail(f"Spec nao encontrado: {SPEC_FILE}")

    try:
        import PyInstaller  # type: ignore
        print(f"[OK] PyInstaller importado - versao {PyInstaller.__version__}")
    except ImportError:
        fail("PyInstaller nao encontrado. Instale com: pip install pyinstaller")

    # Checa versao via CLI apenas para log; nao aborta em caso de codigo != 0
    try:
        result = subprocess.run(
            [sys.executable, "-m", "PyInstaller", "--version"],
            capture_output=True,
            text=True,
        )
        if result.stdout:
            print(f"[PyInstaller] {result.stdout.strip()}")
        if result.returncode != 0:
            print(
                f"[AVISO] pyinstaller --version retornou codigo {result.returncode}\n{result.stderr.strip()}"
            )
    except Exception as exc:
        print(f"[AVISO] Nao foi possivel checar versao via CLI: {exc}")


def check_models() -> None:
    if not MODELS_SOURCE.exists():
        fail(f"Modelos ausentes: {MODELS_SOURCE}")

    onnx_files = list(MODELS_SOURCE.glob("*.onnx"))
    if len(onnx_files) < 5:
        print(f"[AVISO] Modelos encontrados: {len(onnx_files)} (esperado >= 5)")
    else:
        print(f"[OK] Modelos prontos: {len(onnx_files)} arquivos")


def clean_previous() -> None:
    for path in (BUILD_DIR, DIST_DIR):
        if path.exists():
            print(f"Removendo {path}")
            shutil.rmtree(path, ignore_errors=True)


def run_pyinstaller() -> None:
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(SPEC_FILE),
        "--clean",
        "--noconfirm",
    ]
    print("Executando PyInstaller...")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        fail(f"PyInstaller retornou codigo {result.returncode}")


def validate_output() -> None:
    missing = []
    if not EXECUTABLE.exists():
        missing.append(str(EXECUTABLE))
    if not MODELS_TARGET.exists():
        missing.append(str(MODELS_TARGET))
    else:
        onnx_files = list(MODELS_TARGET.glob("*.onnx"))
        if not onnx_files:
            missing.append(f"Nenhum .onnx em {MODELS_TARGET}")

    if missing:
        details = "\n - ".join(missing)
        fail(f"Saida incompleta:\n - {details}")

    print("Build concluido.")
    print(f"Executavel: {EXECUTABLE}")
    print(f"Modelos: {MODELS_TARGET}")


def main() -> None:
    print("== Centaurus Build (modo pasta) ==")
    check_prereqs()
    check_models()
    clean_previous()
    run_pyinstaller()
    validate_output()


if __name__ == "__main__":
    main()
