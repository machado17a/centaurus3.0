# -*- mode: python ; coding: utf-8 -*-
"""
Centaurus.spec - Arquivo de Configuração PyInstaller
Versão 2.0 - Arquitetura Modular Otimizada
"""

import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# ==================== CONFIGURAÇÕES ====================
APP_NAME = "Centaurus"
APP_VERSION = "2.0.0"
MAIN_SCRIPT = "app.py"

# Paths
BASE_DIR = Path(SPECPATH)
MODELS_DIR = BASE_DIR / "models" / "antelopev2"
ICON_PATH = BASE_DIR / "icone.ico"

block_cipher = None

# ==================== HIDDEN IMPORTS ====================
hiddenimports = [
    # Core Python
    'sqlite3',
    'threading',
    'datetime',
    'pathlib',
    'logging',
    'json',
    're',
    'uuid',
    'base64',
    'hashlib',
    
    # Interface
    'tkinter',
    'tkinter.messagebox',
    'tkinter.filedialog',
    'ttkbootstrap',
    'ttkbootstrap.constants',
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'PIL._tkinter_finder',
    
    # Computer Vision
    'cv2',
    'cv2.cv2',
    'cv2.data',
    'numpy',
    'numpy.core',
    'numpy.core._methods',
    'numpy.core._dtype_ctypes',
    'numpy.lib',
    'numpy.lib.format',
    
    # PIL/Pillow - crítico para screenshot
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'PIL.ImageGrab',
    'PIL._tkinter_finder',
    'PIL._imaging',
    
    # Face Recognition
    'insightface',
    'insightface.app',
    'insightface.app.face_analysis',
    'insightface.app.mask_renderer',
    'insightface.model_zoo',
    'insightface.utils',
    'insightface.thirdparty',
    'insightface.thirdparty.face3d',
    'insightface.thirdparty.face3d.mesh',
    'insightface.thirdparty.face3d.mesh.vis',
    
    # Matplotlib (necessário para insightface)
    'matplotlib',
    'matplotlib.pyplot',
    'matplotlib.backends',
    'matplotlib.backends.backend_agg',
    
    # ONNX Runtime
    'onnxruntime',
    'onnxruntime.capi',
    'onnxruntime.capi.onnxruntime_pybind11_state',
    
    # SciPy - correção para scipy.linalg.inv
    'scipy',
    'scipy.linalg',
    'scipy.linalg.blas',
    'scipy.linalg.lapack',
    'scipy.linalg._fblas',
    'scipy.linalg._flapack',
    'scipy.special',
    'scipy.special._ufuncs_cxx',
    'scipy.sparse',
    'scipy.sparse.csgraph',
    'scipy.sparse.csgraph._validation',
    
    # Criptografia
    'cryptography',
    'cryptography.fernet',
    
    # Sistema
    'psutil',
    'pyautogui',
    'pyautogui._pyautogui_win',
    'pyscreeze',
    'PIL.ImageGrab',
    'pygetwindow',
    'pyrect',
    'pymsgbox',
    'pytweening',
    'mouseinfo',
    'platform',
    'socket',
    
    # Setuptools e pkg_resources (necessário para alguns pacotes)
    'pkg_resources',
    'jaraco',
    'jaraco.text',
    'jaraco.functools',
    'jaraco.context',
    
    # Windows
    'pywin32',
    'win32api',
    'win32gui',
    'win32con',
    
    # Módulos do app
    'config',
    'config.settings',
    'config.paths',
    'config.cabine_config',
    'core',
    'core.face_verifier',
    'core.camera_handler',
    'core.quality_validator',
    'core.models_loader',
    'database',
    'database.db_manager',
    'database.encryption',
    'ui',
    'ui.main_window',
    'ui.widgets',
    'ui.dialogs',
    
    # Mantém compatibilidade com scripts antigos
    'main',
    'database_manager',
    'config_manager',
]

# ==================== DATA FILES ====================
datas = []

# Ícone
if ICON_PATH.exists():
    datas.append((str(ICON_PATH), '.'))

# Modelos ML - APENAS antelopev2 (evita duplicatas e buffalo)
models_source = BASE_DIR / 'models' / 'antelopev2'
if models_source.exists():
    for onnx_file in models_source.glob('*.onnx'):
        datas.append((str(onnx_file), 'models/antelopev2'))

# Coleta dados das bibliotecas (SEM insightface para evitar buffalo)
datas += collect_data_files('ttkbootstrap')

# Coleta dados do matplotlib (necessário para insightface)
try:
    datas += collect_data_files('matplotlib', include_py_files=False)
except Exception as e:
    print(f"⚠ Aviso ao coletar dados matplotlib: {e}")

# Coleta submódulos do scipy
hiddenimports += collect_submodules('scipy.linalg')
hiddenimports += collect_submodules('scipy.sparse.csgraph')

# Coleta submódulos do jaraco para evitar erros de pkg_resources
hiddenimports += collect_submodules('jaraco')

# ==================== BINARIES ====================
binaries = []

# DLLs do ONNX Runtime
try:
    import onnxruntime
    onnx_path = Path(onnxruntime.__file__).parent
    
    # DLL providers
    onnx_dll = onnx_path / 'capi' / 'onnxruntime_providers_shared.dll'
    if onnx_dll.exists():
        binaries.append((str(onnx_dll), 'onnxruntime/capi'))
    
    # Pyd file
    onnx_pyd = onnx_path / 'capi' / 'onnxruntime_pybind11_state.pyd'
    if onnx_pyd.exists():
        binaries.append((str(onnx_pyd), 'onnxruntime/capi'))
        
except Exception as e:
    print(f"⚠ Aviso ao coletar binários ONNX Runtime: {e}")

# DLLs do OpenCV
try:
    import cv2
    cv2_path = Path(cv2.__file__).parent
    
    # Todas as DLLs
    for dll in cv2_path.glob('*.dll'):
        binaries.append((str(dll), 'cv2'))
    
    # Arquivos de cascade (se existirem)
    cv2_data = cv2_path / 'data'
    if cv2_data.exists():
        datas.append((str(cv2_data), 'cv2/data'))
        
except Exception as e:
    print(f"⚠ Aviso ao coletar binários OpenCV: {e}")

# ==================== ANÁLISE ====================
a = Analysis(
    [MAIN_SCRIPT],
    pathex=[str(BASE_DIR)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclui pacotes desnecessários
        'pandas',
        'jupyter',
        'notebook',
        'IPython',
        'pytest',
        'test',
        'tests',
        'unittest',
        'doctest',
        # Excluir pacotes pesados não utilizados
        'torch',
        'tensorflow',
        'keras',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ==================== PYZ ====================
pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

# ==================== EXE ====================
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON_PATH) if ICON_PATH.exists() else None,
)

# ==================== COLLECT ====================
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)
