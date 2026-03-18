"""
UI - Módulo de interface gráfica
Contém janela principal, widgets e diálogos
"""
from .main_window import CentaurusApp
from .widgets import ZoomPanCanvas
from .dialogs import ConfiguradorCabineDialog

__all__ = [
    'CentaurusApp',
    'ZoomPanCanvas', 
    'ConfiguradorCabineDialog',
]
