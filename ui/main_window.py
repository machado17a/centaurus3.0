"""
MainWindow - Interface Principal do Centaurus
Versão refatorada standalone usando arquitetura modular
"""
import sys
import os
from pathlib import Path
import threading
import time

# Adiciona o diretório pai ao path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import tkinter as tk
from tkinter import messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk, ImageGrab
import pyautogui
from datetime import datetime

# Importa novos módulos
from config.settings import AppConfig
from config.cabine_config import CabineConfigManager
from database.db_manager import DatabaseManager
from core.models_loader import ModelsLoader
from core.camera_handler import CameraHandler
from ui.widgets import ZoomPanCanvas


class CentaurusApp:
    """
    Aplicação principal do Centaurus com:
    - Sistema de cabines
    - Banco de dados criptografado
    - Arquitetura modular
    """
    
    def __init__(self, root):
        self.root = root
        self.root.title(AppConfig.APP_DISPLAY_NAME)
        
        # Configuração de ícone
        icon_path = AppConfig.get_icon_path()
        if icon_path:
            try:
                self.root.iconbitmap(str(icon_path))
            except tk.TclError:
                print("Aviso: Erro ao carregar o ícone")
        
        # Configuração da janela
        window_width, window_height = AppConfig.WINDOW_WIDTH, AppConfig.WINDOW_HEIGHT
        
        # Define tamanho inicial da janela
        self.root.geometry(f"{window_width}x{window_height}")
        
        # Agenda posicionamento no canto superior direito após janela estar pronta
        self.root.after(10, lambda: self._posicionar_janela_direita(window_width, window_height))
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Variáveis de estado
        self.camera_handler = CameraHandler(use_dshow=AppConfig.USE_DSHOW)
        self.frame_atual = None
        self.model = None
        self.verificacoes_realizadas = 0
        self.capture_step = None
        self.doc_img, self.doc_emb = None, None
        self.cameras_disponiveis = []
        self.modo_verificacao = None
        self.ultimo_verificacao_id = None
        
        # Configuração de cabine
        self.config_manager = CabineConfigManager()
        self.cabine_id = self._verificar_configuracao_cabine()
        
        # Database
        try:
            self.db = DatabaseManager()
            print(f"✅ Database Manager inicializado: {self.db.db_path}")
        except Exception as e:
            print(f"⚠ Erro ao inicializar DatabaseManager: {e}")
            self.db = None
        
        # Cria interface
        self.create_widgets()
        
        # Inicializa sistemas em thread
        threading.Thread(target=self.initialize_systems, daemon=True).start()
    
    def _posicionar_janela_direita(self, window_width, window_height):
        """Posiciona janela no canto superior direito da tela"""
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Calcula posição no canto superior direito
        x_position = screen_width - window_width
        y_position = 0
        
        # Aplica nova geometria com posição
        self.root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
    
    def _verificar_configuracao_cabine(self):
        """Verifica configuração de cabine"""
        if not self.config_manager.config_exists():
            messagebox.showinfo(
                "Configuração Inicial",
                "Este é o primeiro acesso ao sistema.\n"
                "Por favor, configure a identificação da cabine."
            )
            try:
                from ui.dialogs import ConfiguradorCabineDialog
                ConfiguradorCabineDialog(self.root, is_dialog=True)
            except Exception as e:
                messagebox.showerror(
                    "Erro de Configuração",
                    f"Não foi possível abrir o configurador.\n\nErro: {e}"
                )
                return None
        
        cabine_id = self.config_manager.get_cabine_id()
        if cabine_id is None:
            messagebox.showwarning(
                "Cabine Não Configurada",
                "O sistema não possui uma cabine configurada.\n"
                "Os dados serão salvos sem identificação de cabine."
            )
        return cabine_id
    
    def create_widgets(self):
        """Cria interface gráfica"""
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=BOTH, expand=True)
        
        # Header com cabine
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=X, pady=(0, 10))
        
        ttk.Label(
            header_frame,
            text="Centaurus 3.0",
            font=("Segoe UI Semibold", 24, "bold"),
            foreground="gold"
        ).pack(side=LEFT)
        
        if self.cabine_id:
            ttk.Label(
                header_frame,
                text=f"📍 Cabine: {self.cabine_id}",
                font=("Segoe UI", 12, "bold"),
                foreground="gold"
            ).pack(side=RIGHT, padx=10)
        
        ttk.Separator(main_frame, orient=HORIZONTAL).pack(fill=X, pady=5)
        
        # Rodapé
        ttk.Label(
            main_frame,
            text="Desenvolvido por RFH/DCRIM/INI/DPA/PF",
            font=("Segoe UI", 7)
        ).pack(side=BOTTOM, anchor="e", padx=5)
        
        # Content frame
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=BOTH, expand=True)
        content_frame.grid_columnconfigure(0, weight=3)
        content_frame.grid_columnconfigure(1, weight=1)
        content_frame.grid_rowconfigure(0, weight=1)
        
        # Webcam frame
        webcam_frame = ttk.Frame(content_frame, padding=10)
        webcam_frame.grid(row=0, column=0, sticky="nsew")
        
        ttk.Label(
            webcam_frame,
            text="Pré-visualização da Webcam",
            font=("Segoe UI", 14, "bold")
        ).pack(pady=(0, 10))
        
        self.webcam_label = ttk.Label(webcam_frame, bootstyle="dark")
        self.webcam_label.pack(fill=BOTH, expand=True)
        
        # Control frame
        control_frame = ttk.Frame(content_frame, padding=20)
        control_frame.grid(row=0, column=1, sticky="nsew")
        
        # Contador
        self.contador_label = ttk.Label(
            control_frame,
            text="Verificações: 0",
            font=("Segoe UI", 12)
        )
        self.contador_label.pack(pady=(0, 20), anchor="w")
        
        # Seleção de câmera
        ttk.Label(
            control_frame,
            text="SELECIONAR CÂMERA:",
            font=("Segoe UI", 10, "bold")
        ).pack(pady=(10, 0), anchor='w')
        
        self.camera_combobox = ttk.Combobox(control_frame, state="readonly")
        self.camera_combobox.pack(fill=X, pady=5)
        self.camera_combobox.bind("<<ComboboxSelected>>", self.trocar_camera)
        
        ttk.Separator(control_frame, orient=HORIZONTAL).pack(fill=X, pady=10)
        
        # Modos de verificação
        ttk.Label(
            control_frame,
            text="MODOS DE VERIFICAÇÃO",
            font=("Segoe UI", 10, "bold")
        ).pack(pady=10, anchor='w')
        
        self.verify_button = ttk.Button(
            control_frame,
            text="Verificação de Passaporte",
            width=30,
            bootstyle="warning",
            command=self.iniciar_verificacao_passaporte
        )
        self.verify_button.pack(fill=X, pady=5)
        
        self.doc_button = ttk.Button(
            control_frame,
            text="Documento de identidade",
            width=30,
            bootstyle="secondary",
            command=self.iniciar_verificacao_documento
        )
        self.doc_button.pack(fill=X, pady=5)
        
        ttk.Separator(control_frame, orient=HORIZONTAL).pack(fill=X, pady=20)
        
        # Status
        self.status_label = ttk.Label(
            control_frame,
            text="Status: Inicializando...",
            font=("Segoe UI", 12, "italic"),
            bootstyle="warning",
            wraplength=250
        )
        self.status_label.pack(pady=10, anchor='w', fill=X)
        
        # Botões de ação
        self.capture_button = ttk.Button(
            control_frame,
            text="CAPTURAR IMAGEM",
            bootstyle="success",
            command=self.processar_captura,
            state=tk.DISABLED
        )
        self.capture_button.pack(fill=X, ipady=10, pady=10)
        
        self.cancel_button = ttk.Button(
            control_frame,
            text="Cancelar Operação",
            bootstyle="danger-outline",
            command=self.cancelar_operacao,
            state=tk.DISABLED
        )
        self.cancel_button.pack(fill=X, pady=5)
    
    def initialize_systems(self):
        """Inicializa modelo e câmeras"""
        self.status_label.config(text="Status: Carregando modelo de IA...")
        
        try:
            # Carrega modelo
            models_dir = AppConfig.get_models_dir()
            print(f"🔍 Diretório de modelos: {models_dir}")
            print(f"🔍 Diretório base: {AppConfig.get_base_dir()}")
            print(f"🔍 Executando como .exe: {getattr(sys, 'frozen', False)}")
            
            if not models_dir.exists():
                raise FileNotFoundError(
                    f"Diretório de modelos não encontrado: {models_dir}\n"
                    f"Verifique se a pasta 'models' está no mesmo diretório do executável."
                )
            
            loader = ModelsLoader(models_dir)
            self.model = loader.load_model(AppConfig.MODEL_NAME)
            print(f"✅ Modelo '{AppConfig.MODEL_NAME}' carregado com sucesso")
        except Exception as e:
            messagebox.showerror(
                "Erro Crítico",
                f"Falha ao carregar o modelo de IA.\n\nErro: {e}"
            )
            self.root.destroy()
            return
        
        self.status_label.config(text="Status: Modelo carregado. Verificando câmeras...")
        
        # Detecta câmeras
        self.cameras_disponiveis = CameraHandler.list_available_cameras(
            max_test=AppConfig.MAX_CAMERAS_TO_TEST,
            use_dshow=AppConfig.USE_DSHOW
        )
        
        if not self.cameras_disponiveis:
            messagebox.showerror(
                "Erro Crítico",
                "Nenhuma câmera foi encontrada. O programa será fechado."
            )
            self.root.destroy()
            return
        
        # Configura combo de câmeras
        self.camera_combobox['values'] = [f"Câmera {i}" for i in self.cameras_disponiveis]
        self.camera_combobox.current(0)
        self.trocar_camera()
        
        # Inicializa contador
        self.inicializar_contador_do_dia()
        
        # Inicia atualização da webcam
        self.root.after(0, self.update_webcam)
    
    def trocar_camera(self, event=None):
        """Troca câmera selecionada"""
        try:
            camera_index = int(self.camera_combobox.get().split()[-1])
            
            if self.camera_handler.open_camera(camera_index):
                self.status_label.config(text=f"Status: Câmera {camera_index} selecionada.")
            else:
                messagebox.showerror(
                    "Erro de Câmera",
                    f"Não foi possível abrir a Câmera {camera_index}."
                )
        except (ValueError, IndexError):
            messagebox.showerror("Erro de Seleção", "Seleção de câmera inválida.")
    
    def update_webcam(self):
        """Atualiza preview da webcam"""
        try:
            frame = self.camera_handler.read_frame()
            
            if frame is not None and isinstance(frame, np.ndarray) and frame.size > 0:
                self.frame_atual = frame.copy()
                img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                h, w, _ = img_rgb.shape
                label_w = self.webcam_label.winfo_width()
                label_h = self.webcam_label.winfo_height()
                
                if label_w > 10 and label_h > 10:
                    scale = min(label_w / w, label_h / h)
                    new_size = (int(w * scale), int(h * scale))
                    resized_img = cv2.resize(img_rgb, new_size, interpolation=cv2.INTER_AREA)
                    
                    pil_image = Image.fromarray(resized_img)
                    tk_image = ImageTk.PhotoImage(image=pil_image)
                    
                    self.webcam_label.config(image=tk_image)
                    self.webcam_label.image = tk_image
        except Exception as e:
            print(f"Erro no update_webcam: {e}")
            # Continua mesmo com erro para não travar a aplicação
        
        # Agenda próxima atualização
        if hasattr(self, 'root') and self.root.winfo_exists():
            self.root.after(20, self.update_webcam)
    
    def capturar_face(self, image, criterio='maior'):
        """Captura face de uma imagem
        
        Args:
            image: Imagem numpy array (BGR)
            criterio: 'maior' para maior área ou 'esquerda' para mais à esquerda
        """
        print(f"[DEBUG capturar_face] Iniciando...")
        print(f"[DEBUG capturar_face] image type: {type(image)}")
        print(f"[DEBUG capturar_face] critério de seleção: {criterio}")
        
        if image is None:
            print("[DEBUG capturar_face] ERRO: image é None!")
            return None, None
        
        # Validação adicional para PyInstaller
        if not isinstance(image, np.ndarray):
            print(f"[DEBUG capturar_face] ERRO: image não é ndarray! Tipo: {type(image)}")
            return None, None
            
        if image.size == 0:
            print("[DEBUG capturar_face] ERRO: image está vazio!")
            return None, None
        
        print(f"[DEBUG capturar_face] image shape: {image.shape}, dtype: {image.dtype}")
        print(f"[DEBUG capturar_face] model existe: {self.model is not None}")
        
        try:
            print("[DEBUG capturar_face] Chamando self.model.get(image)...")
            faces = self.model.get(image)
            print(f"[DEBUG capturar_face] Faces encontradas: {len(faces) if faces else 0}")
        except Exception as e:
            import traceback
            print(f"[DEBUG capturar_face] EXCEÇÃO em model.get(): {e}")
            traceback.print_exc()
            return None, None
        
        if not faces:
            print("[DEBUG capturar_face] Nenhuma face encontrada!")
            return None, None
        
        # Seleciona face baseado no critério
        if criterio == 'esquerda':
            # Seleciona a face mais à esquerda (menor valor de x1)
            face = min(faces, key=lambda f: f.bbox[0])
            print("[DEBUG capturar_face] Critério: Face mais à ESQUERDA")
        else:
            # Seleciona o maior rosto por área (largura * altura)
            def calcular_area(f):
                x1, y1, x2, y2 = f.bbox
                return (x2 - x1) * (y2 - y1)
            
            face = max(faces, key=calcular_area)
            print("[DEBUG capturar_face] Critério: Face de MAIOR área")
        
        x1, y1, x2, y2 = [int(v) for v in face.bbox]
        print(f"[DEBUG capturar_face] Face selecionada bbox: ({x1}, {y1}, {x2}, {y2})")
        
        # Adiciona margem
        margem_x = int((x2 - x1) * 0.2)
        margem_y = int((y2 - y1) * 0.2)
        
        h_img, w_img = image.shape[:2]
        x1 = max(0, x1 - margem_x)
        y1 = max(0, y1 - margem_y)
        x2 = min(w_img, x2 + margem_x)
        y2 = min(h_img, y2 + margem_y)
        
        face_img = image[y1:y2, x1:x2]
        print(f"[DEBUG capturar_face] face_img shape: {face_img.shape if face_img is not None else 'None'}")
        print(f"[DEBUG capturar_face] embedding shape: {face.normed_embedding.shape if hasattr(face, 'normed_embedding') and face.normed_embedding is not None else 'None'}")
        
        return face_img, face.normed_embedding
    
    def iniciar_verificacao_passaporte(self):
        """Inicia verificação por passaporte (captura de tela)"""
        self.modo_verificacao = 'passaporte'
        self.verify_button.config(state=tk.DISABLED)
        self.doc_button.config(state=tk.DISABLED)
        self.status_label.config(text="Status: Capturando foto do passaporte...")
        
        threading.Thread(target=self._worker_verificacao_passaporte, daemon=True).start()
    
    def _worker_verificacao_passaporte(self):
        """Worker para captura de passaporte (screenshot)"""
        try:
            self.root.withdraw()
            time.sleep(0.3)
            
            # Tenta captura via pyautogui, com fallback para PIL.ImageGrab
            screenshot = None
            try:
                screenshot = pyautogui.screenshot()
            except Exception as e:
                print(f"Erro no pyautogui.screenshot: {e}")
            
            # Fallback para PIL.ImageGrab se pyautogui falhar
            if screenshot is None:
                try:
                    screenshot = ImageGrab.grab()
                except Exception as e:
                    print(f"Erro no ImageGrab.grab: {e}")
            
            self.root.deiconify()
            
            if screenshot is None:
                messagebox.showerror(
                    "Erro na Captura",
                    "Não foi possível capturar a tela. Verifique as permissões do sistema."
                )
                self.cancelar_operacao()
                return
            
            img_bgr = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            self.doc_img, self.doc_emb = self.capturar_face(img_bgr, criterio='esquerda')
            
            if self.doc_img is None:
                messagebox.showerror(
                    "Erro na Captura",
                    "Nenhuma face foi detectada na foto do passaporte."
                )
                self.cancelar_operacao()
                return
            
            self.status_label.config(text="Status: Posicione o ROSTO e clique em CAPTURAR")
            self.capture_step = 'webcam'
            self.capture_button.config(state=tk.NORMAL)
            self.cancel_button.config(state=tk.NORMAL)
            
        except Exception as e:
            self.root.deiconify()
            messagebox.showerror(
                "Erro na Captura",
                f"Falha ao processar a foto do passaporte: {e}"
            )
            self.cancelar_operacao()
    
    def iniciar_verificacao_documento(self):
        """Inicia verificação por documento"""
        self.modo_verificacao = 'documento'
        self.status_label.config(text="Status: Posicione o DOCUMENTO e clique em CAPTURAR")
        self.capture_step = 'documento'
        self.capture_button.config(state=tk.NORMAL)
        self.cancel_button.config(state=tk.NORMAL)
        self.verify_button.config(state=tk.DISABLED)
        self.doc_button.config(state=tk.DISABLED)
    
    def processar_captura(self):
        """Processa captura de imagem"""
        try:
            print("=" * 50)
            print("[DEBUG] processar_captura() iniciado")
            print(f"[DEBUG] capture_step = {self.capture_step}")
            print(f"[DEBUG] camera_handler existe = {self.camera_handler is not None}")
            
            # Captura frame diretamente da câmera no momento do clique
            frame_capturado = None
            
            # Tenta capturar diretamente da câmera (mais confiável no .exe)
            if self.camera_handler and self.camera_handler.is_opened():
                print("[DEBUG] Câmera está aberta, tentando ler frame...")
                frame_capturado = self.camera_handler.read_frame()
                print(f"[DEBUG] Frame da câmera: {type(frame_capturado)}")
                if frame_capturado is not None:
                    print(f"[DEBUG] Frame shape: {frame_capturado.shape if hasattr(frame_capturado, 'shape') else 'N/A'}")
                    print(f"[DEBUG] Frame dtype: {frame_capturado.dtype if hasattr(frame_capturado, 'dtype') else 'N/A'}")
                    print(f"[DEBUG] Frame size: {frame_capturado.size if hasattr(frame_capturado, 'size') else 'N/A'}")
            else:
                print("[DEBUG] Câmera NÃO está aberta!")
            
            # Fallback para frame_atual se captura direta falhar
            if frame_capturado is None:
                print("[DEBUG] Frame da câmera é None, tentando fallback para frame_atual...")
                print(f"[DEBUG] frame_atual type: {type(self.frame_atual)}")
                if self.frame_atual is not None:
                    print(f"[DEBUG] frame_atual shape: {self.frame_atual.shape if hasattr(self.frame_atual, 'shape') else 'N/A'}")
                frame_capturado = self.frame_atual
            
            # Validação robusta do frame
            print(f"[DEBUG] Frame final type: {type(frame_capturado)}")
            
            if frame_capturado is None:
                print("[DEBUG] ERRO: frame_capturado é None!")
                messagebox.showerror(
                    "Erro na Captura",
                    "Imagem da webcam não disponível. Verifique se a câmera está funcionando."
                )
                return
            
            if not isinstance(frame_capturado, np.ndarray):
                print(f"[DEBUG] ERRO: frame_capturado não é ndarray! Tipo: {type(frame_capturado)}")
                messagebox.showerror(
                    "Erro na Captura",
                    f"Frame inválido recebido da câmera. Tipo: {type(frame_capturado)}"
                )
                return
                
            if frame_capturado.size == 0:
                print("[DEBUG] ERRO: frame_capturado está vazio!")
                messagebox.showerror(
                    "Erro na Captura",
                    "Frame vazio recebido da câmera."
                )
                return
            
            print(f"[DEBUG] Frame válido! Shape: {frame_capturado.shape}, Dtype: {frame_capturado.dtype}")
            
            # Faz uma cópia para evitar problemas de referência
            frame_para_processar = frame_capturado.copy()
            print(f"[DEBUG] Cópia criada. Shape: {frame_para_processar.shape}")
            
            if self.capture_step == 'documento':
                print("[DEBUG] Processando captura de DOCUMENTO...")
                self.doc_img, self.doc_emb = self.capturar_face(frame_para_processar)
                print(f"[DEBUG] doc_img type: {type(self.doc_img)}, doc_emb type: {type(self.doc_emb)}")
                
                if self.doc_img is None:
                    print("[DEBUG] ERRO: Nenhuma face detectada no documento!")
                    messagebox.showerror(
                        "Erro na Captura",
                        "Nenhuma face foi detectada na imagem do documento."
                    )
                    self.cancelar_operacao()
                    return
                
                print("[DEBUG] Face do documento capturada com sucesso!")
                messagebox.showinfo(
                    "Sucesso",
                    "Face do documento capturada! Agora posicione o rosto para a captura da webcam."
                )
                self.status_label.config(text="Status: Posicione o ROSTO e clique em CAPTURAR")
                self.capture_step = 'webcam'
                
            elif self.capture_step == 'webcam':
                print("[DEBUG] Processando captura de WEBCAM...")
                webcam_img, webcam_emb = self.capturar_face(frame_para_processar)
                print(f"[DEBUG] webcam_img type: {type(webcam_img)}, webcam_emb type: {type(webcam_emb)}")
                
                if webcam_img is None:
                    print("[DEBUG] ERRO: Nenhuma face detectada na webcam!")
                    messagebox.showerror(
                        "Erro na Captura",
                        "Nenhuma face foi detectada na imagem da webcam."
                    )
                    self.cancelar_operacao()
                    return
                
                print("[DEBUG] Face da webcam capturada! Finalizando comparação...")
                self.finalizar_comparacao(self.doc_img, webcam_img, self.doc_emb, webcam_emb)
                self.cancelar_operacao()
            
            print("[DEBUG] processar_captura() finalizado com sucesso")
            print("=" * 50)
                
        except Exception as e:
            import traceback
            print("=" * 50)
            print(f"[DEBUG] EXCEÇÃO em processar_captura: {e}")
            print(f"[DEBUG] Tipo da exceção: {type(e).__name__}")
            print("[DEBUG] Traceback completo:")
            traceback.print_exc()
            print("=" * 50)
            messagebox.showerror("Erro na Captura", f"Erro ao processar captura: {e}\n\nTipo: {type(e).__name__}")
            self.cancelar_operacao()
    
    def finalizar_comparacao(self, img1, img2, emb1, emb2):
        """Finaliza comparação e salva no banco"""
        cos_sim = np.dot(emb1, emb2)
        cos_sim = np.clip(cos_sim, -1.0, 1.0)
        sim_percent = ((cos_sim + 1) / 2) * 100
        
        # Determina status
        if sim_percent > AppConfig.SIMILARITY_THRESHOLD_VERIFIED:
            status = "Verificado"
            cor_hex, icone = "#2ea628", "✓"
        elif sim_percent >= AppConfig.SIMILARITY_THRESHOLD_WARNING:
            status = "Atenção durante a captura"
            cor_hex, icone = "#dede33", "⚠"
        else:
            status = "Chamar Policial Federal"
            cor_hex, icone = "#cf2929", "✗"
        
        # Salva no banco
        if self.db:
            try:
                camera_idx = int(self.camera_combobox.get().split()[-1])
            except:
                camera_idx = 0
            
            self.ultimo_verificacao_id = self.db.salvar_verificacao(
                similaridade=sim_percent,
                status=status,
                modo_verificacao=self.modo_verificacao,
                camera_index=camera_idx,
                cabine_id=self.cabine_id,
                img_documento=img1,
                img_webcam=img2,
                screenshot_resultado=None
            )
            
            self.atualizar_contador()
        
        self.mostrar_comparacao(img1, img2, sim_percent, status, cor_hex, icone)
    
    def mostrar_comparacao(self, img1, img2, similaridade, status, cor, icone):
        """Exibe janela de resultado"""
        janela = tk.Toplevel(self.root)
        janela.title("Resultado da Comparação")
        janela.configure(background=cor)
        janela.geometry("+0+0")
        janela.update_idletasks()
        janela.state('zoomed')
        
        # Styles
        style = ttk.Style()
        style_frame = f"Color.{cor}.TFrame"
        style.configure(style_frame, background=cor)
        
        style_titulo = f"Title.{cor}.TLabel"
        style.configure(style_titulo, background=cor, foreground="white", font=("Segoe UI", 16, "bold"))
        
        style_icone = f"Icon.{cor}.TLabel"
        style.configure(style_icone, background=cor, foreground="white", font=("Segoe UI Symbol", 48))
        
        style_status = f"Status.{cor}.TLabel"
        style.configure(style_status, background=cor, foreground="white", font=("Segoe UI", 22, "bold"))
        
        # Frame externo
        frame_externo = ttk.Frame(janela, style=style_frame)
        frame_externo.pack(expand=True, fill="both", padx=25, pady=25)
        frame_externo.grid_columnconfigure((0, 1), weight=1)
        frame_externo.grid_rowconfigure(0, weight=0)
        frame_externo.grid_rowconfigure(1, weight=1)
        frame_externo.grid_rowconfigure(2, weight=0)
        
        # Títulos
        titulo_ref = "Foto do Passaporte" if self.modo_verificacao == 'passaporte' else "Documento de Identidade"
        ttk.Label(
            frame_externo,
            text=titulo_ref,
            style=style_titulo
        ).grid(row=0, column=0, pady=(0, 10))
        
        ttk.Label(
            frame_externo,
            text="Captura da Webcam",
            style=style_titulo
        ).grid(row=0, column=1, pady=(0, 10))
        
        # Imagens
        for i, imagem_cv in enumerate([img1, img2]):
            frame_img = ttk.Frame(frame_externo, bootstyle="light", padding=5)
            frame_img.grid(row=1, column=i, sticky="nsew", padx=20, pady=10)
            frame_img.grid_rowconfigure(0, weight=1)
            frame_img.grid_columnconfigure(0, weight=1)
            
            canvas = ZoomPanCanvas(frame_img, highlightthickness=0)
            canvas.pack(fill="both", expand=True)
            
            if imagem_cv is not None:
                img_rgb = cv2.cvtColor(imagem_cv, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(img_rgb)
                canvas.set_image(pil_img)
        
        # Resultado
        resultado_frame = ttk.Frame(frame_externo, style=style_frame)
        resultado_frame.grid(row=2, column=0, columnspan=2, pady=(20, 0), sticky="ew")
        resultado_frame.columnconfigure(0, weight=1)
        resultado_frame.columnconfigure(1, weight=0)
        resultado_frame.columnconfigure(2, weight=1)
        
        center_sub_frame = ttk.Frame(resultado_frame, style=style_frame)
        center_sub_frame.grid(row=0, column=1)
        
        ttk.Label(center_sub_frame, text=icone, style=style_icone).pack(side="left", padx=(0, 20))
        ttk.Label(center_sub_frame, text=status, style=style_status, anchor="w").pack(side="left")
        
        # Salva screenshot se suspeito
        if similaridade < AppConfig.SIMILARITY_THRESHOLD_VERIFIED:
            self.salvar_janela_resultado(janela)
    
    def salvar_janela_resultado(self, janela):
        """Salva screenshot do resultado no banco"""
        try:
            janela.update()
            time.sleep(0.5)
            
            x, y = janela.winfo_rootx(), janela.winfo_rooty()
            w, h = janela.winfo_width(), janela.winfo_height()
            
            # Tenta captura via pyautogui, com fallback para PIL.ImageGrab
            img = None
            try:
                img = pyautogui.screenshot(region=(x, y, w, h))
            except Exception as e:
                print(f"Erro no pyautogui.screenshot region: {e}")
            
            # Fallback para PIL.ImageGrab se pyautogui falhar
            if img is None:
                try:
                    img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
                except Exception as e:
                    print(f"Erro no ImageGrab.grab region: {e}")
            
            if img is not None and self.db and hasattr(self, 'ultimo_verificacao_id') and self.ultimo_verificacao_id:
                self.db.atualizar_screenshot_suspeito(self.ultimo_verificacao_id, img)
                
        except Exception as e:
            print(f"Erro ao salvar screenshot: {e}")
    
    def cancelar_operacao(self):
        """Cancela operação atual"""
        self.capture_step = None
        self.doc_img, self.doc_emb = None, None
        self.modo_verificacao = None
        
        self.status_label.config(text="Status: Operação cancelada. Pronto.")
        self.capture_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.DISABLED)
        self.verify_button.config(state=tk.NORMAL)
        self.doc_button.config(state=tk.NORMAL)
    
    def atualizar_contador(self):
        """Atualiza contador de verificações"""
        if self.db:
            self.verificacoes_realizadas = self.db.contar_verificacoes_hoje()
            self.contador_label.config(text=f"Verificações: {self.verificacoes_realizadas}")
    
    def inicializar_contador_do_dia(self):
        """Inicializa contador do dia"""
        if self.db:
            self.verificacoes_realizadas = self.db.contar_verificacoes_hoje()
            self.contador_label.config(text=f"Verificações: {self.verificacoes_realizadas}")
    
    def on_closing(self):
        """Fecha aplicação"""
        if self.camera_handler:
            self.camera_handler.close_camera()
        
        if hasattr(self, 'db') and self.db:
            self.db.close()
        
        self.root.destroy()
