# quiron.py
# Versão final com limpeza automática dos campos após a comparação.
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import tkinter as tk
from tkinter import messagebox, filedialog
from tkinterdnd2 import DND_FILES, TkinterDnD
import cv2
import numpy as np
from PIL import Image, ImageTk
from insightface.app import FaceAnalysis
import pyautogui
import os
from datetime import datetime
import threading
import sys
import time

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

class ZoomPanCanvas(tk.Canvas):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.pil_image = None
        self.tk_image = None
        self.image_item = None
        self.zoom_level = 1.0
        
        self.bind("<Configure>", self.on_configure)
        self.bind("<MouseWheel>", self.on_mouse_wheel)
        self.bind("<ButtonPress-1>", self.on_button_press)
        self.bind("<B1-Motion>", self.on_mouse_drag)

    def set_image(self, pil_image):
        self.pil_image = pil_image
        self.tk_image = None 
        self.zoom_level = 1.0
        self.event_generate("<Configure>")

    def on_configure(self, event=None):
        if self.pil_image and not self.tk_image:
            self.update_display()
        
        self.center_image()

    def update_display(self):
        if self.pil_image is None:
            return

        canvas_w = self.winfo_width()
        canvas_h = self.winfo_height()

        if canvas_w < 2 or canvas_h < 2:
            return 

        img_w, img_h = self.pil_image.size
        
        scale = min(canvas_w / img_w, canvas_h / img_h)
        self.final_scale = scale * self.zoom_level
        
        new_size = (int(img_w * self.final_scale), int(img_h * self.final_scale))
        if new_size[0] < 1 or new_size[1] < 1:
            return

        resized_pil = self.pil_image.resize(new_size, Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(resized_pil)

        if self.image_item is None:
            self.image_item = self.create_image(0, 0, image=self.tk_image, anchor="nw")
        else:
            self.itemconfig(self.image_item, image=self.tk_image)

    def center_image(self):
        if self.image_item is None or not hasattr(self, 'tk_image') or not self.tk_image:
            return
        canvas_w = self.winfo_width()
        canvas_h = self.winfo_height()
        img_w = self.tk_image.width()
        img_h = self.tk_image.height()
        
        x = (canvas_w - img_w) // 2
        y = (canvas_h - img_h) // 2
        self.coords(self.image_item, x, y)

    def on_mouse_wheel(self, event):
        if event.delta > 0:
            self.zoom_level *= 1.1
        else:
            self.zoom_level *= 0.9
        self.zoom_level = max(0.1, min(self.zoom_level, 10.0))
        self.update_display()
        self.center_image() 

    def on_button_press(self, event):
        self.scan_mark(event.x, event.y)

    def on_mouse_drag(self, event):
        self.scan_dragto(event.x, event.y, gain=1)


class QuironApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Quiron - Módulo de Comparação")
        try:
            base_path = get_base_path()
            icon_path = os.path.join(base_path, "icone.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except tk.TclError:
            print("Aviso: Erro ao carregar o 'icone.ico'.")
            
        window_width, window_height = 800, 700
        screen_width = self.root.winfo_screenwidth()
        x_offset = screen_width - window_width
        self.root.geometry(f"{window_width}x{window_height}+{x_offset}+0")
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.model = None
        self.img1_data, self.img2_data = None, None
        self.full_img1, self.full_img2 = None, None
        self.emb1, self.emb2 = None, None

        APP_DATA_DIR = os.path.join(os.environ['PROGRAMDATA'], 'Centaurus')
        self.COMPARISON_DIR = os.path.join(APP_DATA_DIR, 'testes de comparação')
        try:
            os.makedirs(self.COMPARISON_DIR, exist_ok=True)
        except OSError as e:
            messagebox.showerror("Erro de Permissão", f"Não foi possível criar diretório de dados.\nErro: {e}")
        
        self.create_widgets()
        threading.Thread(target=self.initialize_systems, daemon=True).start()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=BOTH, expand=True)

        ttk.Label(main_frame, text="Quiron", font=("Segoe UI Semibold", 24, "bold"), foreground="gold").pack(pady=(0, 10), anchor="center")
        ttk.Separator(main_frame, orient=HORIZONTAL).pack(fill=X, pady=5)
        
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=BOTH, expand=True, pady=10)
        content_frame.grid_columnconfigure((0, 2), weight=1)
        content_frame.grid_columnconfigure(1, weight=0)
        content_frame.grid_rowconfigure(0, weight=1)

        frame1 = ttk.Labelframe(content_frame, text=" Imagem de Referência 1 ", padding=10)
        frame1.grid(row=0, column=0, sticky="nsew", padx=10)
        self.thumb1_label = ttk.Label(frame1, text="Arraste um arquivo aqui\nou clique para procurar", anchor="center", bootstyle="dark", justify="center")
        self.thumb1_label.pack(fill=BOTH, expand=True, pady=5)
        self.status1_label = ttk.Label(frame1, text="Nenhuma face selecionada", anchor="center", font=("Segoe UI", 9, "italic"))
        self.status1_label.pack(fill=X, pady=(5,0))
        ttk.Button(frame1, text="Procurar Arquivo 1", command=lambda: self.browse_file(1), bootstyle="secondary").pack(fill=X, pady=10)

        frame2 = ttk.Labelframe(content_frame, text=" Imagem de Referência 2 ", padding=10)
        frame2.grid(row=0, column=2, sticky="nsew", padx=10)
        self.thumb2_label = ttk.Label(frame2, text="Arraste um arquivo aqui\nou clique para procurar", anchor="center", bootstyle="dark", justify="center")
        self.thumb2_label.pack(fill=BOTH, expand=True, pady=5)
        self.status2_label = ttk.Label(frame2, text="Nenhuma face selecionada", anchor="center", font=("Segoe UI", 9, "italic"))
        self.status2_label.pack(fill=X, pady=(5,0))
        ttk.Button(frame2, text="Procurar Arquivo 2", command=lambda: self.browse_file(2), bootstyle="secondary").pack(fill=X, pady=10)
        
        self.thumb1_label.drop_target_register(DND_FILES)
        self.thumb1_label.dnd_bind('<<Drop>>', lambda e: self.handle_drop(e, 1))
        self.thumb2_label.drop_target_register(DND_FILES)
        self.thumb2_label.dnd_bind('<<Drop>>', lambda e: self.handle_drop(e, 2))
        
        self.compare_button = ttk.Button(main_frame, text="Comparar Faces", command=self.compare_faces, state=tk.DISABLED, bootstyle="success")
        self.compare_button.pack(fill=X, ipady=10, pady=10, padx=10)

        self.status_label = ttk.Label(main_frame, text="Status: Inicializando...", font=("Segoe UI", 10, "italic"), bootstyle="warning")
        self.status_label.pack(side=LEFT, padx=10, pady=5)
        ttk.Label(main_frame, text="Desenvolvido por RFH/DCRIM/INI/DPA/PF", font=("Segoe UI", 7)).pack(side=RIGHT, padx=10, pady=5)

    def initialize_systems(self):
        self.status_label.config(text="Status: Carregando modelo de IA...")
        try:
            base_path = get_base_path()
            self.model = FaceAnalysis(name="buffalo_sc", root=base_path, providers=["CPUExecutionProvider"])
            self.model.prepare(ctx_id=0)
            self.status_label.config(text="Status: Pronto. Carregue duas imagens para comparar.")
        except Exception as e:
            messagebox.showerror("Erro Crítico", f"Falha ao carregar o modelo de IA.\n\nErro: {e}")
            self.root.destroy()

    def handle_drop(self, event, image_slot):
        filepath = event.data.strip('{}')
        if os.path.exists(filepath):
            self.process_new_image(filepath, image_slot)
        else:
            messagebox.showerror("Erro", f"Caminho inválido ou arquivo não encontrado:\n{filepath}")

    def browse_file(self, image_slot):
        filepath = filedialog.askopenfilename(title=f"Selecione a Imagem {image_slot}", filetypes=[("Imagens", "*.jpg *.jpeg *.png *.bmp")])
        if filepath:
            self.process_new_image(filepath, image_slot)
    
    def process_new_image(self, filepath, image_slot):
        try:
            n = np.fromfile(filepath, np.uint8)
            image = cv2.imdecode(n, cv2.IMREAD_COLOR)
            
            if image is None:
                messagebox.showerror("Erro de Leitura", "Não foi possível ler o arquivo de imagem. Verifique a integridade do arquivo.")
                return
            
            faces = self.model.get(image)
            
            if not faces:
                messagebox.showerror("Nenhuma Face", "Nenhuma face foi detectada na imagem selecionada.")
                return

            if len(faces) == 1:
                self.finalize_face_selection(image, faces[0], image_slot)
            else:
                self.open_face_selector(image, faces, image_slot)
        except Exception as e:
            messagebox.showerror("Erro no Processamento", f"Ocorreu um erro ao processar a imagem:\n{e}")

    def open_face_selector(self, image, faces, image_slot):
        selector_win = tk.Toplevel(self.root)
        selector_win.title("Selecione uma Face")
        selector_win.transient(self.root)
        selector_win.grab_set()

        canvas = tk.Canvas(selector_win)
        canvas.pack(fill="both", expand=True)

        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)
        
        max_w, max_h = self.root.winfo_screenwidth() * 0.7, self.root.winfo_screenheight() * 0.7
        pil_img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        
        tk_img = ImageTk.PhotoImage(pil_img)
        canvas.config(width=tk_img.width(), height=tk_img.height())
        canvas.create_image(0, 0, anchor="nw", image=tk_img)
        canvas.image = tk_img
        
        self.root.update_idletasks()
        main_win_x = self.root.winfo_x()
        main_win_y = self.root.winfo_y()
        main_win_w = self.root.winfo_width()
        main_win_h = self.root.winfo_height()
        popup_w = tk_img.width()
        popup_h = tk_img.height()
        popup_x = main_win_x + (main_win_w - popup_w) // 2
        popup_y = main_win_y + (main_win_h - popup_h) // 2
        selector_win.geometry(f"{popup_w}x{popup_h}+{popup_x}+{popup_y}")
        
        scale_factor = tk_img.width() / image.shape[1]
        for i, face in enumerate(faces):
            x1, y1, x2, y2 = [int(v * scale_factor) for v in face.bbox]
            canvas.create_rectangle(x1, y1, x2, y2, outline="lime", width=3)
            text_x, text_y = x1, y1 - 12 if y1 > 20 else y1 + 12
            canvas.create_oval(text_x - 12, text_y - 12, text_x + 12, text_y + 12, fill="black", outline="lime")
            canvas.create_text(text_x, text_y, text=str(i + 1), fill="lime", font=("Segoe UI", 10, "bold"))

        def on_canvas_click(event):
            for i, face in enumerate(faces):
                x1_box, y1_box, x2_box, y2_box = [int(v * scale_factor) for v in face.bbox]
                if x1_box <= event.x <= x2_box and y1_box <= event.y <= y2_box:
                    self.finalize_face_selection(image, faces[i], image_slot)
                    selector_win.destroy()
                    return
        
        canvas.bind("<Button-1>", on_canvas_click)

    def finalize_face_selection(self, original_image, selected_face, image_slot):
        x1, y1, x2, y2 = [int(v) for v in selected_face.bbox]
        face_img_crop = original_image[y1:y2, x1:x2]
        
        if image_slot == 1:
            self.img1_data = face_img_crop
            self.full_img1 = original_image
            self.emb1 = selected_face.normed_embedding
            self.update_thumbnail(self.thumb1_label, face_img_crop)
            self.status1_label.config(text="Face selecionada com sucesso!", bootstyle="success")
        else:
            self.img2_data = face_img_crop
            self.full_img2 = original_image
            self.emb2 = selected_face.normed_embedding
            self.update_thumbnail(self.thumb2_label, face_img_crop)
            self.status2_label.config(text="Face selecionada com sucesso!", bootstyle="success")

        if self.emb1 is not None and self.emb2 is not None:
            self.compare_button.config(state=tk.NORMAL)

    def update_thumbnail(self, thumb_label, cv2_img):
        img_rgb = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)
        
        thumb_label.update_idletasks()
        w, h = thumb_label.winfo_width(), thumb_label.winfo_height()
        if w < 10 or h < 10: w, h = 150, 150
        
        pil_img.thumbnail((w - 10, h - 10), Image.Resampling.LANCZOS)
        
        final_img = Image.new("RGBA", (w, h)) 
        paste_x = (w - pil_img.width) // 2
        paste_y = (h - pil_img.height) // 2
        final_img.paste(pil_img, (paste_x, paste_y))
        
        tk_img = ImageTk.PhotoImage(final_img)

        thumb_label.config(image=tk_img, text="")
        thumb_label.image = tk_img
        
    def compare_faces(self):
        if self.emb1 is None or self.emb2 is None:
            messagebox.showwarning("Faltam Dados", "É preciso selecionar uma face para cada imagem antes de comparar.")
            return

        cos_sim = np.dot(self.emb1, self.emb2)
        cos_sim = np.clip(cos_sim, -1.0, 1.0)
        sim_percent = ((cos_sim + 1) / 2) * 100
        
        if sim_percent > 70:
            status, cor_hex, icone = "Verificado com sucesso", "#2ea628", "✅"
        elif sim_percent >= 65:
            status, cor_hex, icone = "Análise recomendada", "#dede33", "⚠️"
        elif sim_percent >= 60:
            status, cor_hex, icone = "Baixa similaridade", "#ed8d0e", "⚠️"
        else:
            status, cor_hex, icone = "Faces não correspondentes", "#cf2929", "❌"
        
        self.mostrar_comparacao(self.full_img1, self.full_img2, sim_percent, status, cor_hex, icone)
        
        # --- AJUSTE FINAL: Limpa os campos após a comparação ---
        self.reset_comparison_fields()

    def reset_comparison_fields(self):
        """Reseta todos os dados e widgets da tela principal para um novo ciclo."""
        # Reseta as variáveis de dados
        self.img1_data, self.img2_data = None, None
        self.full_img1, self.full_img2 = None, None
        self.emb1, self.emb2 = None, None
        
        # Reseta a aparência dos widgets da Imagem 1
        self.thumb1_label.config(image='', text="Arraste um arquivo aqui\nou clique para procurar")
        self.thumb1_label.image = None
        self.status1_label.config(text="Nenhuma face selecionada", bootstyle="secondary")
        
        # Reseta a aparência dos widgets da Imagem 2
        self.thumb2_label.config(image='', text="Arraste um arquivo aqui\nou clique para procurar")
        self.thumb2_label.image = None
        self.status2_label.config(text="Nenhuma face selecionada", bootstyle="secondary")
        
        # Desabilita o botão de comparação
        self.compare_button.config(state=tk.DISABLED)
        self.status_label.config(text="Status: Pronto para nova comparação.")


    def mostrar_comparacao(self, img1, img2, similaridade, status, cor, icone):
        janela = tk.Toplevel(self.root)
        janela.title("Resultado da Comparação")
        janela.configure(background=cor)
        janela.state('zoomed')
        janela.update_idletasks()
        
        style = ttk.Style()
        style.configure(f"Color.{cor}.TFrame", background=cor)
        style.configure(f"Title.{cor}.TLabel", background=cor, foreground="white", font=("Segoe UI", 16, "bold"))
        style.configure(f"Icon.{cor}.TLabel", background=cor, foreground="white", font=("Segoe UI Symbol", 48))
        style.configure(f"Status.{cor}.TLabel", background=cor, foreground="white", font=("Segoe UI", 22, "bold"))

        frame_externo = ttk.Frame(janela, style=f"Color.{cor}.TFrame")
        frame_externo.pack(expand=True, fill="both", padx=25, pady=25)
        frame_externo.grid_columnconfigure((0, 1), weight=1)
        frame_externo.grid_rowconfigure(0, weight=0); frame_externo.grid_rowconfigure(1, weight=1); frame_externo.grid_rowconfigure(2, weight=0)
        
        ttk.Label(frame_externo, text="Imagem 1", style=f"Title.{cor}.TLabel").grid(row=0, column=0, pady=(0, 10))
        ttk.Label(frame_externo, text="Imagem 2", style=f"Title.{cor}.TLabel").grid(row=0, column=1, pady=(0, 10))

        for i, imagem_cv in enumerate([img1, img2]):
            frame_img = ttk.Frame(frame_externo, bootstyle="light", padding=5)
            frame_img.grid(row=1, column=i, sticky="nsew", padx=20, pady=10)
            frame_img.grid_rowconfigure(0, weight=1); frame_img.grid_columnconfigure(0, weight=1)
            
            canvas = ZoomPanCanvas(frame_img, highlightthickness=0)
            canvas.pack(fill="both", expand=True)

            if imagem_cv is not None:
                img_rgb = cv2.cvtColor(imagem_cv, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(img_rgb)
                canvas.set_image(pil_img)
                
        resultado_frame = ttk.Frame(frame_externo, style=f"Color.{cor}.TFrame")
        resultado_frame.grid(row=2, column=0, columnspan=2, pady=(20, 0), sticky="ew")
        resultado_frame.columnconfigure((0, 2), weight=1)
        resultado_frame.columnconfigure(1, weight=0)

        center_sub_frame = ttk.Frame(resultado_frame, style=f"Color.{cor}.TFrame")
        center_sub_frame.grid(row=0, column=1)

        ttk.Label(center_sub_frame, text=icone, style=f"Icon.{cor}.TLabel").pack(side="left", padx=(0, 20))
        
        texto_resultado = f"{status}\nSimilaridade: {similaridade:.2f}%"
        ttk.Label(center_sub_frame, text=texto_resultado, style=f"Status.{cor}.TLabel", anchor="w").pack(side="left")
        
        self.salvar_janela_resultado(janela)

    def salvar_janela_resultado(self, janela):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            janela.update()
            time.sleep(0.5)
            x, y = janela.winfo_rootx(), janela.winfo_rooty()
            w, h = janela.winfo_width(), janela.winfo_height()
            img = pyautogui.screenshot(region=(x, y, w, h))
            path_suspeito = os.path.join(self.COMPARISON_DIR, f"comparacao_{timestamp}.png")
            img.save(path_suspeito)
            self.status_label.config(text=f"Resultado salvo.", bootstyle="info")
        except Exception as e:
            self.status_label.config(text=f"Erro ao salvar resultado: {e}", bootstyle="danger")

    def on_closing(self):
        self.root.destroy()

if __name__ == "__main__":
    app = TkinterDnD.Tk()
    style = ttk.Style(theme="darkly")
    
    face_verifier = QuironApp(app)
    app.mainloop()