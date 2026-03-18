"""
Widgets - Componentes Reutilizáveis da Interface
Contém ZoomPanCanvas e outros widgets customizados
"""
import tkinter as tk
from PIL import Image, ImageTk


class ZoomPanCanvas(tk.Canvas):
    """Canvas com funcionalidades de zoom e arraste (pan)"""
    
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.image_item = None
        self.pil_image = None
        self.zoom_level = 1.0
        self.initial_target_size = (900, 900)
        
        # Binds para zoom e pan
        self.bind("<MouseWheel>", self.zoom)
        self.bind("<ButtonPress-1>", self.start_pan)
        self.bind("<B1-Motion>", self.pan)
        self.bind("<Configure>", self.center_image)

    def set_image(self, pil_image):
        """Define a imagem a ser exibida"""
        self.pil_image = pil_image
        self.zoom_level = 1.0
        self.update_image()

    def update_image(self):
        """Atualiza a visualização da imagem com o zoom atual"""
        if self.pil_image is None:
            return
        
        w, h = self.pil_image.size
        
        # Calcula escala inicial
        if w > 0 and h > 0:
            initial_scale = min(
                self.initial_target_size[0] / w,
                self.initial_target_size[1] / h
            )
        else:
            initial_scale = 1.0
        
        # Aplica zoom
        final_scale = initial_scale * self.zoom_level
        new_size = (int(w * final_scale), int(h * final_scale))
        
        if new_size[0] < 1 or new_size[1] < 1:
            return
        
        # Redimensiona imagem
        resized_pil = self.pil_image.resize(new_size, Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(resized_pil)
        
        # Atualiza canvas
        if self.image_item is None:
            self.image_item = self.create_image(0, 0, image=self.tk_image, anchor="nw")
        else:
            self.itemconfig(self.image_item, image=self.tk_image)
        
        self.center_image()

    def center_image(self, event=None):
        """Centraliza a imagem no canvas"""
        if self.image_item is None or not hasattr(self, 'tk_image'):
            return
        
        canvas_w = self.winfo_width()
        canvas_h = self.winfo_height()
        img_w = self.tk_image.width()
        img_h = self.tk_image.height()
        
        x = (canvas_w - img_w) // 2
        y = (canvas_h - img_h) // 2
        
        self.coords(self.image_item, x, y)

    def zoom(self, event):
        """Handler para zoom com scroll do mouse"""
        if event.delta > 0:
            self.zoom_level *= 1.1
        else:
            self.zoom_level *= 0.9
        
        # Limita zoom
        self.zoom_level = max(0.1, min(self.zoom_level, 10.0))
        self.update_image()

    def start_pan(self, event):
        """Inicia arraste da imagem"""
        self.scan_mark(event.x, event.y)

    def pan(self, event):
        """Realiza arraste da imagem"""
        self.scan_dragto(event.x, event.y, gain=1)
