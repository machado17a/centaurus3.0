# Versão 1.6 - Integração com banco de dados criptografado
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import tkinter as tk
from tkinter import messagebox, filedialog
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
from database_manager import DatabaseManager

def get_base_path():
    """ Retorna o caminho base para encontrar arquivos, funcionando tanto em modo script quanto em .exe. """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

class ZoomPanCanvas(tk.Canvas):
    """ Uma classe de Canvas que implementa funcionalidades de zoom e arraste (pan). """
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.image_item, self.pil_image, self.zoom_level = None, None, 1.0
        self.initial_target_size = (900, 900)
        self.bind("<MouseWheel>", self.zoom)
        self.bind("<ButtonPress-1>", self.start_pan)
        self.bind("<B1-Motion>", self.pan)
        self.bind("<Configure>", self.center_image)

    def set_image(self, pil_image):
        self.pil_image, self.zoom_level = pil_image, 1.0
        self.update_image()

    def update_image(self):
        if self.pil_image is None: return
        w, h = self.pil_image.size
        initial_scale = min(self.initial_target_size[0] / w, self.initial_target_size[1] / h) if w > 0 and h > 0 else 1.0
        final_scale = initial_scale * self.zoom_level
        new_size = (int(w * final_scale), int(h * final_scale))
        if new_size[0] < 1 or new_size[1] < 1: return
        resized_pil = self.pil_image.resize(new_size, Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(resized_pil)
        if self.image_item is None:
            self.image_item = self.create_image(0, 0, image=self.tk_image, anchor="nw")
        else:
            self.itemconfig(self.image_item, image=self.tk_image)
        self.center_image()

    def center_image(self, event=None):
        if self.image_item is None or not hasattr(self, 'tk_image'): return
        canvas_w, canvas_h = self.winfo_width(), self.winfo_height()
        img_w, img_h = self.tk_image.width(), self.tk_image.height()
        x, y = (canvas_w - img_w) // 2, (canvas_h - img_h) // 2
        self.coords(self.image_item, x, y)

    def zoom(self, event):
        self.zoom_level *= 1.1 if event.delta > 0 else 0.9
        self.zoom_level = max(0.1, min(self.zoom_level, 10.0))
        self.update_image()

    def start_pan(self, event):
        self.scan_mark(event.x, event.y)

    def pan(self, event):
        self.scan_dragto(event.x, event.y, gain=1)

class FaceVerifierApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Centaurus - Verificador")
        try:
            base_path = get_base_path()
            icon_path = os.path.join(base_path, "icone.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except tk.TclError:
            print("Aviso: Erro ao carregar o 'icone.ico'.")

        window_width, window_height = 800, 900
        screen_width = self.root.winfo_screenwidth()
        x_offset = screen_width - window_width
        self.root.geometry(f"{window_width}x{window_height}+{x_offset}+0")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.camera, self.frame_atual, self.model = None, None, None
        self.verificacoes_realizadas, self.capture_step = 0, None
        self.doc_img, self.doc_emb = None, None
        self.cameras_disponiveis = []
        self.modo_verificacao = None
        self.modelo_selecionado = "antelopev2"

        APP_DATA_DIR = os.path.join(os.environ['PROGRAMDATA'], 'Centaurus')
        self.BASE_DIR = os.path.join(APP_DATA_DIR, 'verificacoes')
        try:
            os.makedirs(self.BASE_DIR, exist_ok=True)
            # Inicializa o gerenciador de banco de dados
            self.db = DatabaseManager(self.BASE_DIR)
        except OSError as e:
            messagebox.showerror("Erro de Permissão", f"Não foi possível criar diretórios de dados em {APP_DATA_DIR}.\nErro: {e}")

        self.create_widgets()
        threading.Thread(target=self.initialize_systems, daemon=True).start()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=BOTH, expand=True)
        ttk.Label(main_frame, text="Centaurus", font=("Segoe UI Semibold", 24, "bold"), foreground="gold").pack(pady=(0, 10), anchor="center")
        ttk.Separator(main_frame, orient=HORIZONTAL).pack(fill=X, pady=5)
        ttk.Label(main_frame, text="Desenvolvido por RFH/DCRIM/INI/DPA/PF", font=("Segoe UI", 7)).pack(side=BOTTOM, anchor="e", padx=5)
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=BOTH, expand=True)
        content_frame.grid_columnconfigure(0, weight=3); content_frame.grid_columnconfigure(1, weight=1)
        content_frame.grid_rowconfigure(0, weight=1)
        webcam_frame = ttk.Frame(content_frame, padding=10)
        webcam_frame.grid(row=0, column=0, sticky="nsew")
        ttk.Label(webcam_frame, text="Pré-visualização da Webcam", font=("Segoe UI", 14, "bold")).pack(pady=(0, 10))
        self.webcam_label = ttk.Label(webcam_frame, bootstyle="dark")
        self.webcam_label.pack(fill=tk.BOTH, expand=True)
        control_frame = ttk.Frame(content_frame, padding=20)
        control_frame.grid(row=0, column=1, sticky="nsew")
        self.contador_label = ttk.Label(control_frame, text="Verificações: 0", font=("Segoe UI", 12))
        self.contador_label.pack(pady=(0, 20), anchor="w")
        ttk.Label(control_frame, text="SELECIONAR CÂMERA:", font=("Segoe UI", 10, "bold")).pack(pady=(10, 0), anchor='w')
        self.camera_combobox = ttk.Combobox(control_frame, state="readonly")
        self.camera_combobox.pack(fill=X, pady=5)
        self.camera_combobox.bind("<<ComboboxSelected>>", self.trocar_camera)

        ttk.Separator(control_frame, orient=HORIZONTAL).pack(fill=X, pady=10)
        ttk.Label(control_frame, text="MODOS DE VERIFICAÇÃO", font=("Segoe UI", 10, "bold")).pack(pady=10, anchor='w')
        
        self.verify_button = ttk.Button(control_frame, text="Verificação de faces STI", width=30, bootstyle="warning", command=self.iniciar_verificacao_screenshot)
        self.verify_button.pack(fill=X, pady=5)
        self.doc_button = ttk.Button(control_frame, text="Documento de identidade", width=30, bootstyle="secondary", command=self.iniciar_verificacao_documento)
        self.doc_button.pack(fill=X, pady=5)

        ttk.Separator(control_frame, orient=HORIZONTAL).pack(fill=X, pady=20)
        self.status_label = ttk.Label(control_frame, text="Status: Inicializando...", font=("Segoe UI", 12, "italic"), bootstyle="warning", wraplength=250)
        self.status_label.pack(pady=10, anchor='w', fill=X)
        self.capture_button = ttk.Button(control_frame, text="CAPTURAR IMAGEM", bootstyle="success", command=self.processar_captura, state=tk.DISABLED)
        self.capture_button.pack(fill=X, ipady=10, pady=10)
        self.cancel_button = ttk.Button(control_frame, text="Cancelar Operação", bootstyle="danger-outline", command=self.cancelar_operacao, state=tk.DISABLED)
        self.cancel_button.pack(fill=X, pady=5)

    def initialize_systems(self):
        self.status_label.config(text="Status: Carregando modelo de IA...")
        try:
            base_path = get_base_path()
            self.model = FaceAnalysis(name=self.modelo_selecionado, root=base_path, providers=["CPUExecutionProvider"])
            self.model.prepare(ctx_id=0)
        except Exception as e:
            messagebox.showerror("Erro Crítico", f"Falha ao carregar o modelo de IA.\n\nErro: {e}")
            self.root.destroy(); return
        self.status_label.config(text="Status: Modelo carregado. Verificando câmeras...")
        self.cameras_disponiveis = self.detectar_cameras()
        if not self.cameras_disponiveis:
            messagebox.showerror("Erro Crítico", "Nenhuma câmera foi encontrada. O programa será fechado.")
            self.root.destroy(); return
        self.camera_combobox['values'] = [f"Câmera {i}" for i in self.cameras_disponiveis]
        self.camera_combobox.current(0)
        self.trocar_camera()
        self.inicializar_contador_do_dia()
        self.root.after(0, self.update_webcam)

    def get_camera_index(self):
        """Retorna o índice da câmera atualmente selecionada"""
        try:
            return int(self.camera_combobox.get().split()[-1])
        except:
            return 0

    def detectar_cameras(self):
        arr = []
        for index in range(10):
            cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            if cap.isOpened(): arr.append(index); cap.release()
        return arr

    def trocar_camera(self, event=None):
        if self.camera and self.camera.isOpened(): self.camera.release()
        try:
            camera_index = int(self.camera_combobox.get().split()[-1])
            self.camera = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
            if not self.camera.isOpened(): messagebox.showerror("Erro de Câmera", f"Não foi possível abrir a Câmera {camera_index}."); self.camera = None
            else: self.status_label.config(text=f"Status: Câmera {camera_index} selecionada.")
        except (ValueError, IndexError): messagebox.showerror("Erro de Seleção", "Seleção de câmera inválida."); self.camera = None

    def update_webcam(self):
        if self.camera and self.camera.isOpened():
            ret, frame = self.camera.read()
            if ret:
                self.frame_atual = frame.copy()
                img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, _ = img_rgb.shape
                label_w, label_h = self.webcam_label.winfo_width(), self.webcam_label.winfo_height()
                if label_w > 10 and label_h > 10:
                    scale = min(label_w / w, label_h / h)
                    new_size = (int(w * scale), int(h * scale))
                    resized_img = cv2.resize(img_rgb, new_size, interpolation=cv2.INTER_AREA)
                    pil_image = Image.fromarray(resized_img)
                    tk_image = ImageTk.PhotoImage(image=pil_image)
                    self.webcam_label.config(image=tk_image)
                    self.webcam_label.image = tk_image
        self.root.after(20, self.update_webcam)

    def capturar_face(self, image, source_type):
        """
        Captura um rosto de uma imagem usando uma lógica de seleção diferente
        baseada na origem da imagem (screenshot ou webcam).
        """
        if image is None: return None, None
        faces = self.model.get(image)
        if not faces: return None, None
        
        if source_type == 'screenshot':
            # Para screenshots, usa o critério de 'rosto mais à esquerda'.
            face = sorted(faces, key=lambda f: f.bbox[0])[0]
        else: # Para 'webcam'
            # Para a webcam, usa o critério de 'maior área' (rosto mais próximo).
            face = sorted(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True)[0]
        
        x1, y1, x2, y2 = [int(v) for v in face.bbox]
        margem_x, margem_y = int((x2 - x1) * 0.2), int((y2 - y1) * 0.2)
        h_img, w_img = image.shape[:2]
        x1, y1, x2, y2 = max(0, x1 - margem_x), max(0, y1 - margem_y), min(w_img, x2 + margem_x), min(h_img, y2 + margem_y)
        face_img = image[y1:y2, x1:x2]
        return face_img, face.normed_embedding

    def iniciar_verificacao_screenshot(self):
        self.modo_verificacao = 'screenshot'
        self.verify_button.config(state=tk.DISABLED); self.doc_button.config(state=tk.DISABLED)
        self.status_label.config(text="Status: Capturando e processando screenshot...")
        threading.Thread(target=self._worker_verificacao_screenshot, daemon=True).start()
    
    def _worker_verificacao_screenshot(self):
        try:
            self.root.withdraw()
            time.sleep(0.3)
            screenshot = pyautogui.screenshot()
            self.root.deiconify()
            img_bgr = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            self.doc_img, self.doc_emb = self.capturar_face(img_bgr, source_type='screenshot')
            if self.doc_img is None: messagebox.showerror("Erro na Captura", "Nenhuma face foi detectada no screenshot."); self.cancelar_operacao(); return
            self.status_label.config(text="Status: Posicione o ROSTO e clique em CAPTURAR")
            self.capture_step = 'webcam'
            self.capture_button.config(state=tk.NORMAL); self.cancel_button.config(state=tk.NORMAL)
        except Exception as e:
            self.root.deiconify()
            messagebox.showerror("Erro no Screenshot", f"Falha ao processar o screenshot: {e}"); self.cancelar_operacao()

    def iniciar_verificacao_documento(self):
        self.modo_verificacao = 'documento'
        self.status_label.config(text="Status: Posicione o DOCUMENTO e clique em CAPTURAR")
        self.capture_step = 'documento'
        self.capture_button.config(state=tk.NORMAL); self.cancel_button.config(state=tk.NORMAL)

    def processar_captura(self):
        try:
            if self.frame_atual is None: raise ValueError("Imagem da webcam não disponível.")
            if self.capture_step == 'documento':
                self.doc_img, self.doc_emb = self.capturar_face(self.frame_atual, source_type='webcam')
                if self.doc_img is None: messagebox.showerror("Erro na Captura", "Nenhuma face foi detectada na imagem do documento."); self.cancelar_operacao(); return
                messagebox.showinfo("Sucesso", "Face do documento capturada! Agora posicione o rosto para a captura da webcam.")
                self.status_label.config(text="Status: Posicione o ROSTO e clique em CAPTURAR"); self.capture_step = 'webcam'
            elif self.capture_step == 'webcam':
                webcam_img, webcam_emb = self.capturar_face(self.frame_atual, source_type='webcam')
                if webcam_img is None: messagebox.showerror("Erro na Captura", "Nenhuma face foi detectada na imagem da webcam."); self.cancelar_operacao(); return
                
                self.finalizar_comparacao(self.doc_img, webcam_img, self.doc_emb, webcam_emb)
                self.cancelar_operacao()
        except Exception as e:
            messagebox.showerror("Erro na Captura", str(e)); self.cancelar_operacao()

    def finalizar_comparacao(self, img1, img2, emb1, emb2):
        cos_sim = np.dot(emb1, emb2)
        cos_sim = np.clip(cos_sim, -1.0, 1.0)
        sim_percent = ((cos_sim + 1) / 2) * 100

        if sim_percent > 70:
            status = "Verificado"
            cor_hex, icone = "#2ea628", "✓"
        elif sim_percent >= 65:
            status = "Atenção durante a captura"
            cor_hex, icone = "#dede33", "⚠"
        else:
            status = "Chamar Policial Federal para conferência"
            cor_hex, icone = "#cf2929", "✗"

        camera_idx = self.get_camera_index()
        screenshot_janela = None

        verificacao_id = self.db.salvar_verificacao(
            similaridade=sim_percent,
            status=status,
            modo_verificacao=self.modo_verificacao,
            camera_index=camera_idx,
            img_documento=img1,
            img_webcam=img2,
            screenshot_resultado=screenshot_janela
        )

        self.atualizar_contador()
        self.mostrar_comparacao(img1, img2, sim_percent, status, cor_hex, icone, verificacao_id)

    def mostrar_comparacao(self, img1, img2, similaridade, status, cor, icone, verificacao_id):
        janela = tk.Toplevel(self.root)
        janela.title("Resultado da Comparação")
        janela.configure(background=cor)
        janela.geometry("+0+0")
        janela.update_idletasks()
        janela.state('zoomed')
        
        # Armazena referência para capturar screenshot se necessário
        self.janela_resultado = janela
        self.verificacao_id_atual = verificacao_id
        
        style = ttk.Style()
        style_frame_colorido = f"Color.{cor}.TFrame"
        style.configure(style_frame_colorido, background=cor)
        style_titulo_colorido = f"Title.{cor}.TLabel"
        style.configure(style_titulo_colorido, background=cor, foreground="white", font=("Segoe UI", 16, "bold"))
        style_icone_colorido = f"Icon.{cor}.TLabel"
        style.configure(style_icone_colorido, background=cor, foreground="white", font=("Segoe UI Symbol", 48))
        style_status_colorido = f"Status.{cor}.TLabel"
        style.configure(style_status_colorido, background=cor, foreground="white", font=("Segoe UI", 22, "bold"))

        frame_externo = ttk.Frame(janela, style=style_frame_colorido)
        frame_externo.pack(expand=True, fill="both", padx=25, pady=25)
        frame_externo.grid_columnconfigure((0, 1), weight=1)
        frame_externo.grid_rowconfigure(0, weight=0); frame_externo.grid_rowconfigure(1, weight=1); frame_externo.grid_rowconfigure(2, weight=0)
        
        titulo_doc = ttk.Label(frame_externo, text="Documento de Referência", style=style_titulo_colorido)
        titulo_doc.grid(row=0, column=0, pady=(0, 10))
        titulo_webcam = ttk.Label(frame_externo, text="Captura da Webcam", style=style_titulo_colorido)
        titulo_webcam.grid(row=0, column=1, pady=(0, 10))

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
                
        resultado_frame = ttk.Frame(frame_externo, style=style_frame_colorido)
        resultado_frame.grid(row=2, column=0, columnspan=2, pady=(20, 0), sticky="ew")
        
        resultado_frame.columnconfigure(0, weight=1)
        resultado_frame.columnconfigure(1, weight=0)
        resultado_frame.columnconfigure(2, weight=1)

        center_sub_frame = ttk.Frame(resultado_frame, style=style_frame_colorido)
        center_sub_frame.grid(row=0, column=1)

        icone_label = ttk.Label(center_sub_frame, text=icone, style=style_icone_colorido)
        icone_label.pack(side="left", padx=(0, 20))
        status_label = ttk.Label(center_sub_frame, text=status, style=style_status_colorido, anchor="w")
        status_label.pack(side="left")

        # Salva screenshot para casos suspeitos
        if similaridade <= 70:
            janela.after(1000, lambda: self.salvar_janela_resultado_db(janela, verificacao_id))

    def salvar_janela_resultado_db(self, janela, verificacao_id):
        """Salva screenshot da janela de resultado no banco de dados"""
        try:
            janela.update()
            time.sleep(0.3)
            x, y = janela.winfo_rootx(), janela.winfo_rooty()
            w, h = janela.winfo_width(), janela.winfo_height()
            img_pil = pyautogui.screenshot(region=(x, y, w, h))

            img_cv = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

            cursor = self.db.conn.cursor()
            screenshot_bytes = self.db._image_to_bytes(img_cv)
            screenshot_encrypted = self.db._encrypt_blob(screenshot_bytes)
            cursor.execute("""
                UPDATE casos_suspeitos
                SET screenshot_encrypted = ?
                WHERE verificacao_id = ?
            """, (screenshot_encrypted, verificacao_id))
            self.db.conn.commit()

        except Exception as e:
            print(f"Erro ao salvar screenshot do resultado: {e}")

    def salvar_faces_positivas(self, doc_img, webcam_img):
        """Método mantido para compatibilidade - agora salva no banco"""
        pass

    def salvar_faces_de_auditoria(self, doc_img, webcam_img):
        """Método mantido para compatibilidade - agora salva no banco"""
        pass

    def salvar_janela_resultado(self, janela):
        """Método mantido para compatibilidade - agora salva no banco"""
        pass

    def cancelar_operacao(self):
        self.capture_step, self.doc_img, self.doc_emb = None, None, None
        self.modo_verificacao = None
        self.status_label.config(text="Status: Operação cancelada. Pronto.")
        self.capture_button.config(state=tk.DISABLED); self.cancel_button.config(state=tk.DISABLED)
        self.verify_button.config(state=tk.NORMAL); self.doc_button.config(state=tk.NORMAL)

    def registrar_verificacao(self, similaridade, status):
        """Método mantido para compatibilidade - não usado mais (salva no banco)"""
        pass

    def atualizar_contador(self):
        # Busca contagem do banco de dados
        self.verificacoes_realizadas = self.db.contar_verificacoes_hoje()
        self.contador_label.config(text=f"Verificações: {self.verificacoes_realizadas}")

    def inicializar_contador_do_dia(self):
        # Busca contagem do banco de dados
        self.verificacoes_realizadas = self.db.contar_verificacoes_hoje()
        self.contador_label.config(text=f"Verificações: {self.verificacoes_realizadas}")

    def on_closing(self):
        if self.camera and self.camera.isOpened(): self.camera.release()
        if hasattr(self, 'db'):
            self.db.close()
        self.root.destroy()

if __name__ == "__main__":
    app = ttk.Window(themename="darkly")
    face_verifier = FaceVerifierApp(app)
    app.mainloop()