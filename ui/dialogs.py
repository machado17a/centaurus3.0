"""
Dialogs - Diálogos da Interface
Contém ConfiguradorCabineDialog e outros diálogos
"""
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import tkinter as tk
from tkinter import messagebox
from config.cabine_config import CabineConfigManager


class ConfiguradorCabineDialog:
    def __init__(self, root, is_dialog=False):
        self.root = root
        self.is_dialog = is_dialog
        
        if self.is_dialog:
            self.window = tk.Toplevel(root)
            self.window.title("Configuração Inicial - Centaurus")
            self.window.transient(root)
            self.window.grab_set()
        else:
            self.window = root
            self.window.title("Configuração Inicial - Centaurus")
        
        # Janela responsiva e maximizável
        min_width, min_height = 500, 450
        initial_width, initial_height = 700, 600
        
        self.window.minsize(min_width, min_height)
        self.window.resizable(True, True)
        
        # Centralizar janela
        self.window.update_idletasks()
        screen_w = self.window.winfo_screenwidth()
        screen_h = self.window.winfo_screenheight()
        x = (screen_w // 2) - (initial_width // 2)
        y = (screen_h // 2) - (initial_height // 2)
        self.window.geometry(f"{initial_width}x{initial_height}+{x}+{y}")
        
        self.config_manager = CabineConfigManager()
        self.create_widgets()
        
        if self.is_dialog:
            self.root.wait_window(self.window)
    
    def create_widgets(self):
        # Frame principal com scroll
        main_container = ttk.Frame(self.window)
        main_container.pack(fill=BOTH, expand=True)
        
        # Canvas com scrollbar para responsividade
        canvas = tk.Canvas(main_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_container, orient=VERTICAL, command=canvas.yview)
        
        # Frame scrollável
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas e scrollbar
        canvas.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        # Bind mousewheel para scroll (apenas quando mouse sobre canvas)
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        def _bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
        def _unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
        canvas.bind("<Enter>", _bind_mousewheel)
        canvas.bind("<Leave>", _unbind_mousewheel)
        
        # Conteúdo dentro do frame scrollável
        main_frame = ttk.Frame(scrollable_frame, padding=30)
        main_frame.pack(fill=BOTH, expand=True)
        
        # Título
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=X, pady=(0, 10))
        
        ttk.Label(
            title_frame,
            text="⚙️ Configuração de Cabine",
            font=("Segoe UI", 24, "bold"),
            foreground="gold"
        ).pack()
        
        ttk.Separator(main_frame, orient=HORIZONTAL).pack(fill=X, pady=10)
        
        # Instruções
        instruction_frame = ttk.Frame(main_frame)
        instruction_frame.pack(fill=X, pady=(10, 20))
        
        ttk.Label(
            instruction_frame,
            text="📍 Selecione a identificação da cabine onde este sistema está sendo instalado:",
            font=("Segoe UI", 12),
            wraplength=600,
            justify=CENTER
        ).pack()
        
        ttk.Label(
            instruction_frame,
            text="Esta informação será usada para identificar as verificações no banco de dados.",
            font=("Segoe UI", 9, "italic"),
            foreground="gray",
            wraplength=600,
            justify=CENTER
        ).pack(pady=(5, 0))
        
        # Frame para seleção (centralizado e responsivo)
        selection_container = ttk.Frame(main_frame)
        selection_container.pack(pady=30, expand=True)
        
        # Grid para melhor organização
        selection_frame = ttk.Frame(selection_container)
        selection_frame.pack()
        
        # Seleção de letra
        letra_frame = ttk.Labelframe(
            selection_frame,
            text="Letra da Cabine",
            padding=20,
            bootstyle="warning"
        )
        letra_frame.grid(row=0, column=0, padx=20, pady=10, sticky="nsew")
        
        ttk.Label(
            letra_frame,
            text="Escolha E (Embarque) ou D (Desembarque):",
            font=("Segoe UI", 10)
        ).pack(pady=(0, 10))
        
        self.letra_var = tk.StringVar(value="E")
        
        letra_buttons = ttk.Frame(letra_frame)
        letra_buttons.pack()
        
        ttk.Radiobutton(
            letra_buttons,
            text="E - Embarque",
            variable=self.letra_var,
            value="E",
            command=self.atualizar_preview,
            bootstyle="warning",
            width=15
        ).pack(pady=5, fill=X)
        
        ttk.Radiobutton(
            letra_buttons,
            text="D - Desembarque",
            variable=self.letra_var,
            value="D",
            command=self.atualizar_preview,
            bootstyle="info",
            width=15
        ).pack(pady=5, fill=X)
        
        # Seleção de número
        numero_frame = ttk.Labelframe(
            selection_frame,
            text="Número da Cabine",
            padding=20,
            bootstyle="primary"
        )
        numero_frame.grid(row=0, column=1, padx=20, pady=10, sticky="nsew")
        
        ttk.Label(
            numero_frame,
            text="Selecione o número (1-20):",
            font=("Segoe UI", 10)
        ).pack(pady=(0, 10))
        
        self.numero_var = tk.StringVar(value="1")
        self.numero_combo = ttk.Combobox(
            numero_frame,
            textvariable=self.numero_var,
            values=[str(i) for i in range(1, 21)],
            state="readonly",
            width=15,
            font=("Segoe UI", 14),
            bootstyle="primary"
        )
        self.numero_combo.pack(pady=5, ipady=5)
        self.numero_combo.bind("<<ComboboxSelected>>", lambda e: self.atualizar_preview())
        
        # Preview da cabine selecionada (mais destacado)
        preview_container = ttk.Frame(main_frame)
        preview_container.pack(pady=30, fill=X)
        
        self.preview_frame = ttk.Frame(
            preview_container,
            bootstyle="dark",
            padding=20
        )
        self.preview_frame.pack(fill=X, expand=True)
        
        ttk.Label(
            self.preview_frame,
            text="✓ Cabine Selecionada:",
            font=("Segoe UI", 12, "bold"),
            foreground="lightgreen"
        ).pack(pady=(0, 10))
        
        self.preview_label = ttk.Label(
            self.preview_frame,
            text="E1",
            font=("Segoe UI", 48, "bold"),
            foreground="gold"
        )
        self.preview_label.pack(pady=(0, 10))
        
        # Descrição do tipo
        self.preview_desc = ttk.Label(
            self.preview_frame,
            text="Entrada - Cabine 1",
            font=("Segoe UI", 11, "italic"),
            foreground="lightgray"
        )
        self.preview_desc.pack()
        
        # Botões (responsivos)
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=30, fill=X)
        
        button_container = ttk.Frame(button_frame)
        button_container.pack()
        
        ttk.Button(
            button_container,
            text="❌ Cancelar",
            command=self.cancelar,
            bootstyle="danger-outline",
            width=18
        ).pack(side=LEFT, padx=10, ipady=5)
        
        ttk.Button(
            button_container,
            text="✓ Salvar Configuração",
            command=self.salvar,
            bootstyle="success",
            width=25
        ).pack(side=LEFT, padx=10, ipady=5)
        
        # Nota de rodapé
        footer_frame = ttk.Frame(main_frame, bootstyle="secondary")
        footer_frame.pack(fill=X, pady=(20, 0))
        
        ttk.Label(
            footer_frame,
            text="ℹ️ Esta configuração só poderá ser alterada manualmente após a instalação.",
            font=("Segoe UI", 9),
            foreground="orange",
            wraplength=600,
            justify=CENTER
        ).pack(pady=10)
    
    def atualizar_preview(self):
        """Atualiza o preview da cabine selecionada"""
        letra = self.letra_var.get()
        numero = self.numero_var.get()
        cabine_id = f"{letra}{numero}"
        tipo = "Embarque" if letra == "E" else "Desembarque"
        
        self.preview_label.config(text=cabine_id)
        self.preview_desc.config(text=f"{tipo} - Cabine {numero}")
    
    def salvar(self):
        """Salva a configuração e fecha"""
        cabine_id = f"{self.letra_var.get()}{self.numero_var.get()}"
        
        if self.config_manager.set_cabine_id(cabine_id):
            messagebox.showinfo(
                "Configuração Salva",
                f"Cabine {cabine_id} configurada com sucesso!\n\n"
                "O sistema está pronto para uso."
            )
            if self.is_dialog:
                self.window.destroy()
            else:
                self.root.quit()
        else:
            messagebox.showerror(
                "Erro",
                f"Não foi possível salvar a configuração.\n\n"
                "Verifique as permissões do sistema."
            )
    
    def cancelar(self):
        """Cancela e fecha sem salvar"""
        if messagebox.askyesno(
            "Cancelar Configuração",
            "Deseja realmente cancelar sem configurar a cabine?\n\n"
            "O sistema não poderá ser utilizado sem uma cabine configurada."
        ):
            if self.is_dialog:
                self.window.destroy()
            else:
                self.root.quit()

def run_as_dialog(root):
    """Executa o configurador como um diálogo modal"""
    ConfiguradorCabine(root, is_dialog=True)

def main():
    """Função principal para executar o configurador"""
    # Verifica se já existe configuração
    config = ConfigManager()
    
    if config.config_exists():
        cabine_atual = config.get_cabine_id()
        # Se rodar direto, pergunta. Se for importado, a lógica pode ser diferente.
        # Aqui mantemos a lógica original para execução direta.
        app = ttk.Window(themename="darkly")
        app.withdraw() # Esconde janela principal temporária
        resposta = messagebox.askyesno(
            "Configuração Existente",
            f"Este sistema já está configurado como Cabine {cabine_atual}.\n\n"
            "Deseja alterar a configuração?"
        )
        app.destroy()
        if not resposta:
            return
    
    # Cria e executa a interface
    app = ttk.Window(themename="darkly")
    ConfiguradorCabine(app)
    app.mainloop()

if __name__ == "__main__":
    main()
