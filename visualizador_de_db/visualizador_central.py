"""
Visualizador Central - Ferramenta para Computador Central
Permite descriptografar e visualizar dados de verificações de múltiplas cabines
"""
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import tkinter as tk
from tkinter import messagebox, filedialog, ttk as tkttk
import sqlite3
import os
from datetime import datetime
import cv2
import numpy as np
from PIL import Image, ImageTk
import sys
import os

# Adiciona o diretório 'centaurus' ao path para importar módulos
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'centaurus'))

from database_manager import DatabaseManager
import tempfile
import shutil

class VisualizadorCentral:
    def __init__(self, root):
        self.root = root
        self.root.title("Visualizador Central - Centaurus")
        self.root.geometry("1400x800")
        
        self.databases = []  # Lista de DatabaseManagers abertos
        self.verification_data = []  # Dados consolidados de verificações
        self.current_image_window = None
        
        self.create_widgets()
    
    def create_widgets(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=BOTH, expand=True)
        
        # Título
        ttk.Label(
            main_frame,
            text="Visualizador Central - Centaurus",
            font=("Segoe UI", 24, "bold"),
            foreground="gold"
        ).pack(pady=(0, 10))
        
        ttk.Separator(main_frame, orient=HORIZONTAL).pack(fill=X, pady=10)
        
        # Frame de controles
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=X, pady=(0, 10))
        
        # Pasta de bancos
        ttk.Label(control_frame, text="Pasta com bancos (.db):", font=("Segoe UI", 10)).pack(side=LEFT, padx=(0, 5))
        self.pasta_var = tk.StringVar()
        self.pasta_entry = ttk.Entry(control_frame, textvariable=self.pasta_var, width=50)
        self.pasta_entry.pack(side=LEFT, padx=5)
        
        ttk.Button(
            control_frame,
            text="Selecionar Pasta",
            command=self.selecionar_pasta,
            bootstyle="primary"
        ).pack(side=LEFT, padx=5)
        
        ttk.Button(
            control_frame,
            text="Carregar Dados",
            command=self.carregar_dados,
            bootstyle="success"
        ).pack(side=LEFT, padx=5)
        
        # Frame de filtros
        filter_frame = ttk.Labelframe(main_frame, text="Filtros", padding=10)
        filter_frame.pack(fill=X, pady=(0, 10))
        
        filter_grid = ttk.Frame(filter_frame)
        filter_grid.pack(fill=X)
        
        # Cabine
        ttk.Label(filter_grid, text="Cabine:").grid(row=0, column=0, sticky=W, padx=(0, 5))
        self.cabine_filter = ttk.Combobox(filter_grid, values=["Todas"], state="readonly", width=15)
        self.cabine_filter.current(0)
        self.cabine_filter.grid(row=0, column=1, sticky=W, padx=5)
        self.cabine_filter.bind("<<ComboboxSelected>>", lambda e: self.aplicar_filtros())
        
        #  Status
        ttk.Label(filter_grid, text="Status:").grid(row=0, column=2, sticky=W, padx=(20, 5))
        self.status_filter = ttk.Combobox(filter_grid, values=["Todos", "Verificado", "Atenção", "Suspeito"], state="readonly", width=20)
        self.status_filter.current(0)
        self.status_filter.grid(row=0, column=3, sticky=W, padx=5)
        self.status_filter.bind("<<ComboboxSelected>>", lambda e: self.aplicar_filtros())
        
        # Similaridade
        ttk.Label(filter_grid, text="Similaridade:").grid(row=0, column=4, sticky=W, padx=(20, 5))
        sim_frame = ttk.Frame(filter_grid)
        sim_frame.grid(row=0, column=5, sticky=W, padx=5)
        
        self.sim_min_var = tk.StringVar(value="0")
        self.sim_max_var = tk.StringVar(value="100")
        ttk.Entry(sim_frame, textvariable=self.sim_min_var, width=5).pack(side=LEFT)
        ttk.Label(sim_frame, text=" - ").pack(side=LEFT)
        ttk.Entry(sim_frame, textvariable=self.sim_max_var, width=5).pack(side=LEFT)
        ttk.Label(sim_frame, text=" %").pack(side=LEFT)
        
        ttk.Button(
            filter_grid,
            text="Aplicar",
            command=self.aplicar_filtros,
            bootstyle="info"
        ).grid(row=0, column=6, padx=(10, 0))
        
        # Treeview para exibir dados
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=BOTH, expand=True)
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        
        # Treeview
        columns = ("ID", "Cabine", "Data/Hora", "Similaridade", "Status", "Modo", "Câmera")
        self.tree = tkttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
            height=20
        )
        
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)
        
        # Configurar colunas
        self.tree.heading("ID", text="ID")
        self.tree.heading("Cabine", text="Cabine")
        self.tree.heading("Data/Hora", text="Data/Hora")
        self.tree.heading("Similaridade", text="Similaridade (%)")
        self.tree.heading("Status", text="Status")
        self.tree.heading("Modo", text="Modo")
        self.tree.heading("Câmera", text="Câmera")
        
        self.tree.column("ID", width=50, anchor=CENTER)
        self.tree.column("Cabine", width=80, anchor=CENTER)
        self.tree.column("Data/Hora", width=150, anchor=CENTER)
        self.tree.column("Similaridade", width=120, anchor=CENTER)
        self.tree.column("Status", width=250, anchor=W)
        self.tree.column("Modo", width=120, anchor=CENTER)
        self.tree.column("Câmera", width=80, anchor=CENTER)
        
        # Layout
        self.tree.grid(row=0, column=0, sticky=NSEW)
        vsb.grid(row=0, column=1, sticky=NS)
        hsb.grid(row=1, column=0, sticky=EW)
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Bind double-click
        self.tree.bind("<Double-1>", self.ver_imagens)
        
        # Frame de ações
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=X, pady=(10, 0))
        
        self.info_label = ttk.Label(action_frame, text="Nenhum dado carregado", font=("Segoe UI", 10))
        self.info_label.pack(side=LEFT)
        
        ttk.Button(
            action_frame,
            text="Ver Imagens",
            command=self.ver_imagens,
            bootstyle="primary"
        ).pack(side=RIGHT, padx=5)
        
        ttk.Button(
            action_frame,
            text="Exportar Imagens",
            command=self.exportar_imagens,
            bootstyle="secondary"
        ).pack(side=RIGHT, padx=5)
    
    def selecionar_pasta(self):
        """Seleciona pasta contendo arquivos .db"""
        pasta = filedialog.askdirectory(title="Selecione a pasta com os arquivos .db")
        if pasta:
            self.pasta_var.set(pasta)
    
    def carregar_dados(self):
        """Carrega dados de todos os .db da pasta"""
        pasta = self.pasta_var.get()
        if not pasta or not os.path.exists(pasta):
            messagebox.showerror("Erro", "Selecione uma pasta válida")
            return
        
        # Fechar databases anteriores
        for db in self.databases:
            db.close()
        self.databases = []
        self.verification_data = []
        
        # Encontrar todos os .db
        db_files = [f for f in os.listdir(pasta) if f.endswith('.db')]
        
        if not db_files:
            messagebox.showwarning("Aviso", "Nenhum arquivo .db encontrado na pasta selecionada")
            return
        
        # Carregar cada database
        cabines_set = set()
        for db_file in db_files:
            db_path = os.path.join(pasta, db_file)
            try:
                # Cria gerenciador temporário
                db = DatabaseManager(os.path.dirname(db_path))
                db.db_path = db_path
                db.conn = sqlite3.connect(db_path, check_same_thread=False)
                
                # Buscar verificações
                cursor = db.conn.cursor()
                cursor.execute("""
                    SELECT id, cabine_id, timestamp, similaridade, status, modo_verificacao, camera_index
                    FROM verificacoes
                    ORDER BY timestamp DESC
                """)
                
                for row in cursor.fetchall():
                    self.verification_data.append({
                        'id': row[0],
                        'cabine_id': row[1] or "N/A",
                        'timestamp': row[2],
                        'similaridade': row[3],
                        'status': row[4],
                        'modo_verificacao': row[5],
                        'camera_index': row[6],
                        'db': db
                    })
                    if row[1]:
                        cabines_set.add(row[1])
                
                self.databases.append(db)
                
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao carregar {db_file}:\n{e}")
        
        # Atualizar filtro de cabines
        cabines = ["Todas"] + sorted(list(cabines_set))
        self.cabine_filter['values'] = cabines
        self.cabine_filter.current(0)
        
        # Atualizar árvore
        self.aplicar_filtros()
        
        self.info_label.config(text=f"{len(self.verification_data)} verificações carregadas de {len(db_files)} banco(s)")
    
    def aplicar_filtros(self):
        """Aplica   filtros e atualiza a árvore"""
        # Limpar árvore
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Obter filtros
        cabine = self.cabine_filter.get()
        status = self.status_filter.get()
        
        try:
            sim_min = float(self.sim_min_var.get())
            sim_max = float(self.sim_max_var.get())
        except:
            sim_min, sim_max = 0, 100
        
        # Filtrar e inserir dados
        count = 0
        for v in self.verification_data:
            # Filtro de cabine
            if cabine != "Todas" and v['cabine_id'] != cabine:
                continue
            
            # Filtro de status
            if status != "Todos":
                if status == "Verificado" and "Verificado" not in v['status']:
                    continue
                if status == "Atenção" and "Atenção" not in v['status']:
                    continue
                if status == "Suspeito" and ("Chamar" not in v['status'] and "especialista" not in v['status']):
                    continue
            
            # Filtro de similaridade
            if not (sim_min <= v['similaridade'] <= sim_max):
                continue
            
            # Inserir na árvore
            self.tree.insert("", END, values=(
                v['id'],
                v['cabine_id'],
                v['timestamp'],
                f"{v['similaridade']:.2f}%",
                v['status'],
                v['modo_verificacao'],
                v['camera_index']
            ), tags=(str(v['id']),))
            
            count += 1
        
        self.info_label.config(text=f"{count} verificações exibidas de {len(self.verification_data)} total")
    
    def ver_imagens(self, event=None):
        """Exibe imagens da verificação selecionada"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Aviso", "Selecione uma verificação")
            return
        
        # Obter ID da verificação
        values = self.tree.item(selection[0], 'values')
        verif_id = int(values[0])
        
        # Encontrar dados da verificação
        verif_data = None
        for v in self.verification_data:
            if v['id'] == verif_id:
                verif_data = v
                break
        
        if not verif_data:
            return
        
        # Buscar imagens do banco
        db = verif_data['db']
        cursor = db.conn.cursor()
        cursor.execute("""
            SELECT tipo_imagem, imagem_blob_encrypted
            FROM imagens
            WHERE verificacao_id = ?
        """, (verif_id,))
        
        images = {}
        for row in cursor.fetchall():
            tipo = row[0]
            encrypted_blob = row[1]
            
            # Descriptografar
            decrypted_bytes = db._decrypt_blob(encrypted_blob)
            img_cv = db._bytes_to_image(decrypted_bytes)
            
            if img_cv is not None:
                images[tipo] = img_cv
        
        if not images:
            messagebox.showinfo("Info", "Nenhuma imagem encontrada para esta verificação")
            return
        
        # Criar janela para exibir imagens
        self.mostrar_janela_imagens(images, verif_data)
    
    def mostrar_janela_imagens(self, images, verif_data):
        """Mostra janela com as imagens"""
        if self.current_image_window:
            self.current_image_window.destroy()
        
        win = tk.Toplevel(self.root)
        win.title(f"Imagens - Verificação {verif_data['id']}")
        win.geometry("1200x700")
        self.current_image_window = win
        
        # Info frame
        info_frame = ttk.Frame(win, padding=10)
        info_frame.pack(fill=X)
        
        info_text = f"ID: {verif_data['id']} | Cabine: {verif_data['cabine_id']} | {verif_data['timestamp']} | Similaridade: {verif_data['similaridade']:.2f}% | {verif_data['status']}"
        ttk.Label(info_frame, text=info_text, font=("Segoe UI", 11, "bold")).pack()
        
        # Images frame
        img_frame = ttk.Frame(win)
        img_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        img_frame.grid_columnconfigure(0, weight=1)
        img_frame.grid_columnconfigure(1, weight=1)
        img_frame.grid_rowconfigure(0, weight=1)
        
        # Exibir imagens
        for i, (tipo, img_cv) in enumerate(images.items()):
            canvas_frame = ttk.Labelframe(img_frame, text=tipo.capitalize(), padding=5)
            canvas_frame.grid(row=0, column=i, sticky=NSEW, padx=5)
            
            # Converter para RGB e exibir
            img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
            h, w = img_rgb.shape[:2]
            
            # Redimensionar para caber
            max_size = 500
            scale = min(max_size/w, max_size/h)
            new_size = (int(w*scale), int(h*scale))
            img_resized = cv2.resize(img_rgb, new_size)
            
            img_pil = Image.fromarray(img_resized)
            img_tk = ImageTk.PhotoImage(img_pil)
            
            label = tk.Label(canvas_frame, image=img_tk)
            label.image = img_tk  # Keep reference
            label.pack()
    
    def exportar_imagens(self):
        """Exporta imagens selecionadas"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Aviso", "Selecione pelo menos uma verificação")
            return
        
        # Selecionar pasta de destino
        dest_folder = filedialog.askdirectory(title="Selecione a pasta para exportar as imagens")
        if not dest_folder:
            return
        
        exported = 0
        for item in selection:
            values = self.tree.item(item, 'values')
            verif_id = int(values[0])
            
            # Encontrar dados
            verif_data = None
            for v in self.verification_data:
                if v['id'] == verif_id:
                    verif_data = v
                    break
            
            if not verif_data:
                continue
            
            # Buscar imagens
            db = verif_data['db']
            cursor = db.conn.cursor()
            cursor.execute("""
                SELECT tipo_imagem, imagem_blob_encrypted
                FROM imagens
                WHERE verificacao_id = ?
            """, (verif_id,))
            
            for row in cursor.fetchall():
                tipo, encrypted_blob = row
                decrypted_bytes = db._decrypt_blob(encrypted_blob)
                img_cv = db._bytes_to_image(decrypted_bytes)
                
                if img_cv is not None:
                    filename = f"{verif_data['cabine_id']}_{verif_id}_{tipo}.png"
                    filepath = os.path.join(dest_folder, filename)
                    cv2.imwrite(filepath, img_cv)
                    exported += 1
        
        messagebox.showinfo("Sucesso", f"{exported} imagens exportadas para {dest_folder}")


def main():
    app = ttk.Window(themename="darkly")
    VisualizadorCentral(app)
    app.mainloop()


if __name__ == "__main__":
    main()
