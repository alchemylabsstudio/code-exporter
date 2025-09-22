import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font
from pathlib import Path
import threading
import queue
import time
import sys

# Installa customtkinter se non è installato
try:
    import customtkinter as ctk
    CUSTOMTKINTER_AVAILABLE = True
except ImportError:
    CUSTOMTKINTER_AVAILABLE = False
    print("customtkinter non è installato. Usa 'pip install customtkinter' per installarlo.")
    print("Eseguendo con tkinter standard...")

# Classe per le label colorate
class ColoredLabel(tk.Label):
    def __init__(self, master=None, **kwargs):
        self.emoji = kwargs.pop("emoji", None)
        super().__init__(master, **kwargs)
    
    def update_colors(self):
        if hasattr(self, "app") and self.app and self.emoji:
            self.configure(fg=self.app.theme.get_emoji_color(self.emoji))

# Classe Node per la struttura ad albero
class Node:
    def __init__(self, name, path, is_excluded, is_dir):
        self.name = name
        self.path = path
        self.is_excluded = is_excluded
        self.is_dir = is_dir
        self.children = []

# Tema moderno con colori arancione e ciano
class ModernTheme:
    def __init__(self):
        # Tema chiaro con bianco leggermente meno bianco
        self.themes = {
            "light": {
                "bg": "#f5f5f7",  # Grigio chiaro invece di bianco puro
                "fg": "#1d1d1f",
                "header_bg": "#f8f9fa",  # Grigio molto chiaro
                "header_fg": "#1d1d1f",
                "card_bg": "#ffffff",  # Bianco leggermente sporco
                "card_fg": "#1d1d1f",
                "button_bg": "#007aff",
                "button_fg": "#ffffff",
                "button_hover": "#0051d5",
                "button_border": "#0051d5",  # Bordo blu scuro per pulsanti blu
                "button_secondary_bg": "#ff9500",
                "button_secondary_fg": "#ffffff",
                "button_secondary_hover": "#ff8000",
                "button_secondary_border": "#e67300",  # Bordo arancione scuro per pulsanti arancioni
                "success": "#34c759",
                "success_border": "#2d9e4a",  # Bordo verde scuro
                "danger": "#ff3b30",
                "danger_border": "#d70015",  # Bordo rosso scuro
                "warning": "#ffcc00",
                "warning_border": "#e6ac00",  # Bordo giallo scuro
                "info": "#5ac8fa",
                "info_border": "#4aa3c8",  # Bordo ciano scuro
                "tree_bg": "#ffffff",
                "tree_fg": "#1d1d1f",
                "tree_selected_bg": "#007aff",
                "tree_selected_fg": "#ffffff",
                "progress_bg": "#5ac8fa",
                "progress_trough": "#e5e5ea",
                "border": "#d2d2d7",
                "shadow": "rgba(0, 0, 0, 0.1)",
                "accent": "#5ac8fa",  # Ciano
                "secondary": "#ff9500",  # Arancione
                "emoji_colors": {
                    "📁": "#5ac8fa",
                    "📂": "#5ac8fa",
                    "📊": "#34c759",
                    "✅": "#34c759",
                    "❌": "#ff3b30",
                    "📏": "#5ac8fa",
                    "👁️": "#af52de",
                    "🔍": "#5ac8fa",
                    "✨": "#ffcc00",
                    "⏳": "#ffcc00",
                    "📄": "#5ac8fa",
                    "💾": "#34c759",
                    "🌙": "#af52de",
                    "☀️": "#ffcc00",
                    "ℹ️": "#5ac8fa",
                    "📂": "#ff9500"
                }
            }
        }
    
    def get(self, key):
        return self.themes["light"][key]
    
    def get_emoji_color(self, emoji):
        return self.themes["light"]["emoji_colors"].get(emoji, self.get("fg"))

class CodeExporterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Code Exporter")
        self.root.geometry("1200x800")
        self.root.configure(bg="#f5f5f7")
        self.root.minsize(1000, 700)
        
        # Imposta l'icona della finestra
        try:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
                self.icon_path = icon_path
            else:
                self.icon_path = None
        except:
            self.icon_path = None
        
        # Tema
        self.theme = ModernTheme()
        
        # Variabili
        self.project_path = tk.StringVar()
        self.file_tree = {}
        self.show_excluded = tk.BooleanVar(value=False)
        self.selected_count = tk.StringVar(value="0")
        self.excluded_count = tk.StringVar(value="0")
        self.total_size = tk.StringVar(value="0")
        
        self.exclude_folders = ['node_modules', '.git', '.next', '.venv', 'venv', '__pycache__', '.idea', '.vscode']
        self.exclude_files = ['package-lock.json', 'yarn.lock', '.DS_Store']
        self.exclude_extensions = [
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico', '.tiff', '.psd',
            '.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a', '.wma', '.opus',
            '.mp4', '.mov', '.avi', '.mkv', '.flv', '.webm', '.wmv', '.m4v', '.3gp',
            '.pdf', '.zip', '.tar', '.gz', '.7z', '.rar', '.exe', '.dll', '.so', '.dylib'
        ]
        self.include_extensions = ['.py', '.js', '.ts', '.tsx', '.jsx', '.html', '.css', '.json', '.env', '.md', '.txt', '.yml', '.yaml', '.xml', '.csv', '.ini', '.cfg', '.conf']
        
        self.queue = queue.Queue()
        self.scan_active = False
        self.scan_thread = None
        
        # Creazione UI
        self.create_widgets()
        
        # Controlla periodicamente la coda
        self.root.after(100, self.process_queue)
    
    def create_widgets(self):
        # Frame principale con padding
        self.main_frame = tk.Frame(self.root, bg=self.theme.get("bg"))
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header con design minimal
        self.header_frame = tk.Frame(self.main_frame, bg=self.theme.get("header_bg"), height=80)
        self.header_frame.pack(fill=tk.X, pady=(0, 20))
        self.header_frame.pack_propagate(False)
        
        # Container per il contenuto dell'header
        header_container = tk.Frame(self.header_frame, bg=self.theme.get("header_bg"))
        header_container.pack(fill=tk.BOTH, expand=True)
        
        # Logo e titolo allineati orizzontalmente
        header_left = tk.Frame(header_container, bg=self.theme.get("header_bg"))
        header_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Logo (icona o emoji)
        if self.icon_path:
            try:
                self.logo_image = tk.PhotoImage(file=self.icon_path)
                self.logo_label = tk.Label(
                    header_left, 
                    image=self.logo_image,
                    bg=self.theme.get("header_bg"),
                    width=40,
                    height=40
                )
                self.logo_label.pack(side=tk.LEFT, padx=(20, 15))
            except:
                # Fallback a emoji se l'icona non può essere caricata
                self.logo_label = self.create_colored_label(
                    header_left, 
                    text="📂", 
                    font=("Segoe UI Emoji", 32),
                    bg=self.theme.get("header_bg"),
                    emoji="📂"
                )
                self.logo_label.pack(side=tk.LEFT, padx=(20, 15))
        else:
            # Usa emoji se l'icona non è disponibile
            self.logo_label = self.create_colored_label(
                header_left, 
                text="📂", 
                font=("Segoe UI Emoji", 32),
                bg=self.theme.get("header_bg"),
                emoji="📂"
            )
            self.logo_label.pack(side=tk.LEFT, padx=(20, 15))
        
        # Titolo e sottotitolo
        title_container = tk.Frame(header_left, bg=self.theme.get("header_bg"))
        title_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.title_label = self.create_colored_label(
            title_container, 
            text="Code Exporter", 
            font=("Segoe UI", 20, "bold"),
            bg=self.theme.get("header_bg"),
            fg=self.theme.get("header_fg"),
            emoji="📂"
        )
        self.title_label.pack(anchor=tk.W)
        
        self.subtitle_label = self.create_colored_label(
            title_container, 
            text="Export your code to a single file", 
            font=("Segoe UI", 12),
            bg=self.theme.get("header_bg"),
            fg=self.theme.get("secondary"),
            emoji="📂"
        )
        self.subtitle_label.pack(anchor=tk.W, pady=(2, 0))
        
        # Pulsanti nell'header (solo pulsante info, rimosso tema)
        header_buttons = tk.Frame(header_container, bg=self.theme.get("header_bg"))
        header_buttons.pack(side=tk.RIGHT, padx=20)
        
        # Pulsante credits
        self.credits_btn = tk.Button(
            header_buttons, 
            text="ℹ️", 
            font=("Segoe UI Emoji", 16),
            bg=self.theme.get("header_bg"),
            fg=self.theme.get_emoji_color("ℹ️"),
            bd=0,
            highlightthickness=0,
            padx=8,
            pady=5,
            cursor="hand2",
            command=self.show_credits
        )
        self.credits_btn.pack(side=tk.RIGHT, padx=5)
        
        # Frame per la selezione cartella
        folder_frame = tk.Frame(self.main_frame, bg=self.theme.get("card_bg"), relief=tk.RAISED, bd=1)
        folder_frame.pack(fill=tk.X, pady=(0, 20))
        
        folder_content = tk.Frame(folder_frame, bg=self.theme.get("card_bg"))
        folder_content.pack(fill=tk.X, padx=15, pady=15)
        
        folder_label = self.create_colored_label(
            folder_content, 
            text="📁 Project folder:", 
            font=("Segoe UI", 14),
            bg=self.theme.get("card_bg"),
            fg=self.theme.get("fg"),
            emoji="📁"
        )
        folder_label.pack(side=tk.LEFT, padx=(0, 15))
        
        folder_entry = tk.Entry(
            folder_content, 
            textvariable=self.project_path, 
            width=60, 
            font=("Segoe UI", 14),
            bg=self.theme.get("bg"),
            fg=self.theme.get("fg"),
            relief="solid",
            borderwidth=1,
            highlightthickness=1,
            highlightbackground=self.theme.get("border")
        )
        folder_entry.pack(side=tk.LEFT, padx=(0, 15), fill=tk.X, expand=True)
        
        browse_btn = tk.Button(
            folder_content, 
            text="Browse", 
            font=("Segoe UI", 12, "bold"),
            bg=self.theme.get("button_bg"),
            fg=self.theme.get("button_fg"),
            activebackground=self.theme.get("button_hover"),
            relief="solid",
            borderwidth=1,
            highlightthickness=0,
            highlightbackground=self.theme.get("button_border"),
            padx=12,
            pady=6,
            cursor="hand2",
            command=self.select_folder
        )
        browse_btn.pack(side=tk.LEFT)
        
        # Frame per le statistiche
        self.stats_frame = tk.Frame(self.main_frame, bg=self.theme.get("card_bg"), relief=tk.RAISED, bd=1)
        self.stats_frame.pack(fill=tk.X, pady=(0, 20))
        
        stats_content = tk.Frame(self.stats_frame, bg=self.theme.get("card_bg"))
        stats_content.pack(fill=tk.X, padx=15, pady=15)
        
        # Statistiche con design minimal
        stats_container = tk.Frame(stats_content, bg=self.theme.get("card_bg"))
        stats_container.pack(fill=tk.X)
        
        # Statistiche in una riga
        self.create_stat_card(stats_container, "✅ Selected", self.selected_count, self.theme.get("success"), 0)
        self.create_stat_card(stats_container, "❌ Excluded", self.excluded_count, self.theme.get("danger"), 1)
        self.create_stat_card(stats_container, "📏 Total size", self.total_size, self.theme.get("info"), 2)
        
        # Frame per i controlli
        self.controls_frame = tk.Frame(self.main_frame, bg=self.theme.get("card_bg"), relief=tk.RAISED, bd=1)
        self.controls_frame.pack(fill=tk.X, pady=(0, 20))
        
        controls_content = tk.Frame(self.controls_frame, bg=self.theme.get("card_bg"))
        controls_content.pack(fill=tk.X, padx=15, pady=15)
        
        # Checkbox per mostrare file esclusi
        show_excluded_cb = tk.Checkbutton(
            controls_content, 
            text="👁️ Show excluded files", 
            variable=self.show_excluded,
            command=self.toggle_excluded_files,
            font=("Segoe UI", 12),
            bg=self.theme.get("card_bg"),
            fg=self.theme.get("fg"),
            selectcolor=self.theme.get("card_bg"),
            activebackground=self.theme.get("card_bg"),
            activeforeground=self.theme.get("fg")
        )
        show_excluded_cb.pack(side=tk.LEFT, padx=(0, 20))
        
        # Bottoni di selezione
        select_all_btn = tk.Button(
            controls_content, 
            text="✅ Select all", 
            font=("Segoe UI", 12, "bold"),
            bg=self.theme.get("button_bg"),
            fg=self.theme.get("button_fg"),
            activebackground=self.theme.get("button_hover"),
            relief="solid",
            borderwidth=1,
            highlightthickness=0,
            highlightbackground=self.theme.get("button_border"),
            padx=12,
            pady=6,
            cursor="hand2",
            command=self.select_all
        )
        select_all_btn.pack(side=tk.LEFT, padx=5)
        
        deselect_all_btn = tk.Button(
            controls_content, 
            text="❌ Deselect all", 
            font=("Segoe UI", 12, "bold"),
            bg=self.theme.get("button_bg"),
            fg=self.theme.get("button_fg"),
            activebackground=self.theme.get("button_hover"),
            relief="solid",
            borderwidth=1,
            highlightthickness=0,
            highlightbackground=self.theme.get("button_border"),
            padx=12,
            pady=6,
            cursor="hand2",
            command=self.deselect_all
        )
        deselect_all_btn.pack(side=tk.LEFT, padx=5)
        
        # Bottoni di esportazione
        export_btn = tk.Button(
            controls_content, 
            text="💾 Export Content", 
            font=("Segoe UI", 12, "bold"),
            bg=self.theme.get("button_secondary_bg"),
            fg=self.theme.get("button_secondary_fg"),
            activebackground=self.theme.get("button_secondary_hover"),
            relief="solid",
            borderwidth=1,
            highlightthickness=0,
            highlightbackground=self.theme.get("button_secondary_border"),
            padx=12,
            pady=6,
            cursor="hand2",
            command=self.export_files
        )
        export_btn.pack(side=tk.RIGHT, padx=5)
        
        export_structure_btn = tk.Button(
            controls_content, 
            text="📁 Export Structure", 
            font=("Segoe UI", 12, "bold"),
            bg=self.theme.get("button_bg"),
            fg=self.theme.get("button_fg"),
            activebackground=self.theme.get("button_hover"),
            relief="solid",
            borderwidth=1,
            highlightthickness=0,
            highlightbackground=self.theme.get("button_border"),
            padx=12,
            pady=6,
            cursor="hand2",
            command=self.export_structure
        )
        export_structure_btn.pack(side=tk.RIGHT, padx=5)
        
        # Progress bar (inizialmente nascosta)
        self.progress_frame = tk.Frame(self.main_frame, bg=self.theme.get("card_bg"), relief=tk.RAISED, bd=1)
        self.progress_frame.pack(fill=tk.X, pady=(0, 20))
        self.progress_frame.pack_forget()  # Nascondi inizialmente
        
        progress_content = tk.Frame(self.progress_frame, bg=self.theme.get("card_bg"))
        progress_content.pack(fill=tk.X, padx=15, pady=15)
        
        self.progress = ttk.Progressbar(
            progress_content, 
            mode="indeterminate",
            length=500,
            style="Modern.Horizontal.TProgressbar"
        )
        self.progress.pack(side=tk.LEFT, padx=10, pady=10)
        
        self.status_label = self.create_colored_label(
            progress_content, 
            text="✨ Ready", 
            font=("Segoe UI", 12),
            bg=self.theme.get("card_bg"),
            emoji="✨"
        )
        self.status_label.pack(side=tk.LEFT, padx=10, pady=10)
        
        # Frame per la lista file
        self.list_frame = tk.Frame(self.main_frame, bg=self.theme.get("card_bg"), relief=tk.RAISED, bd=1)
        self.list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header della lista
        list_header = tk.Frame(self.list_frame, bg=self.theme.get("border"), height=40)
        list_header.pack(fill=tk.X)
        list_header.pack_propagate(False)
        
        list_title_label = self.create_colored_label(
            list_header, 
            text="📁 File Structure", 
            font=("Segoe UI", 14, "bold"),
            bg=self.theme.get("border"),
            fg=self.theme.get("fg"),
            emoji="📁"
        )
        list_title_label.pack(pady=10)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(self.list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Treeview
        self.tree = ttk.Treeview(self.list_frame, columns=("selected",), show="tree headings", yscrollcommand=scrollbar.set, style="Modern.Treeview")
        self.tree.heading("#0", text="Name")
        self.tree.heading("selected", text="✅")
        self.tree.column("selected", width=60, anchor=tk.CENTER)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=(15, 0), pady=(0, 15))
        scrollbar.config(command=self.tree.yview)
        
        # Configura i tag per i colori
        self.tree.tag_configure("included", foreground=self.theme.get("success"), font=("Segoe UI", 11, "bold"))
        self.tree.tag_configure("excluded", foreground=self.theme.get("danger"), font=("Segoe UI", 11))
        
        # Bind per la selezione/deselezione singola
        self.tree.bind("<ButtonRelease-1>", self.on_tree_click)
        
        # Configura gli stili
        self.setup_styles()
    
    def create_colored_label(self, parent, **kwargs):
        emoji = kwargs.pop("emoji", None)
        
        if emoji:
            label = ColoredLabel(parent, emoji=emoji, **kwargs)
            label.app = self
            label.update_colors()
        else:
            label = tk.Label(parent, **kwargs)
        
        return label
    
    def setup_styles(self):
        style = ttk.Style()
        
        # Stile per i frame
        style.configure("Modern.TFrame", background=self.theme.get("bg"))
        
        # Stile per la progress bar
        style.configure("Modern.Horizontal.TProgressbar", 
                       background=self.theme.get("progress_bg"),
                       troughcolor=self.theme.get("progress_trough"),
                       borderwidth=0)
        
        # Stile per la treeview
        style.configure("Modern.Treeview", 
                       background=self.theme.get("tree_bg"),
                       foreground=self.theme.get("tree_fg"),
                       fieldbackground=self.theme.get("tree_bg"),
                       borderwidth=1,
                       relief="solid",
                       font=("Segoe UI", 11),
                       rowheight=28)
        style.configure("Modern.Treeview.Heading", 
                       background=self.theme.get("card_bg"),
                       foreground=self.theme.get("fg"),
                       font=("Segoe UI", 12, "bold"),
                       relief="flat")
        style.map("Modern.Treeview",
                 background=[('selected', self.theme.get("tree_selected_bg"))],
                 foreground=[('selected', self.theme.get("tree_selected_fg"))])
    
    def create_stat_card(self, parent, title, variable, color, column):
        card_frame = tk.Frame(parent, bg=self.theme.get("card_bg"))
        card_frame.grid(row=0, column=column, padx=10, sticky="nsew")
        
        # Configura le colonne per espandersi
        parent.grid_columnconfigure(column, weight=1)
        
        # Titolo
        title_label = self.create_colored_label(card_frame, text=title, font=("Segoe UI", 12), bg=self.theme.get("card_bg"), fg=self.theme.get("fg"))
        title_label.pack(anchor=tk.W)
        
        # Valore
        value_label = self.create_colored_label(card_frame, textvariable=variable, font=("Segoe UI", 16, "bold"), bg=self.theme.get("card_bg"), fg=color)
        value_label.pack(anchor=tk.W, pady=(5, 0))
    
    def update_colored_labels(self):
        # Aggiorna tutte le label colorate
        for widget in self.root.winfo_children():
            self.update_colored_labels_recursive(widget)
    
    def update_colored_labels_recursive(self, widget):
        # Se è una label con metodo update_colors, aggiorna i colori
        if hasattr(widget, 'update_colors'):
            widget.update_colors()
        
        # Ricorsione per i figli
        for child in widget.winfo_children():
            self.update_colored_labels_recursive(child)
    
    def show_credits(self):
        # Crea una finestra popup per i crediti
        credits_window = tk.Toplevel(self.root)
        credits_window.title("Credits & License")
        credits_window.geometry("600x500")
        credits_window.configure(bg=self.theme.get("card_bg"))
        credits_window.transient(self.root)
        credits_window.grab_set()
        
        # Imposta l'icona della finestra se disponibile
        if self.icon_path:
            try:
                credits_window.iconbitmap(self.icon_path)
            except:
                pass
        
        # Centra la finestra
        credits_window.update_idletasks()
        width = credits_window.winfo_width()
        height = credits_window.winfo_height()
        x = (credits_window.winfo_screenwidth() // 2) - (width // 2)
        y = credits_window.winfo_screenheight() // 2 - (height // 2)
        credits_window.geometry(f'{width}x{height}+{x}+{y}')
        
        # Header
        header_frame = tk.Frame(credits_window, bg=self.theme.get("header_bg"), height=70)
        header_frame.pack(fill=tk.X)
        
        # Logo nella finestra dei crediti
        if self.icon_path:
            try:
                credits_logo_image = tk.PhotoImage(file=self.icon_path)
                credits_logo = tk.Label(
                    header_frame, 
                    image=credits_logo_image,
                    bg=self.theme.get("header_bg"),
                    width=30,
                    height=30
                )
                credits_logo.image = credits_logo_image  # Mantieni un riferimento
                credits_logo.pack(side=tk.LEFT, padx=(20, 10))
            except:
                # Fallback a emoji se l'icona non può essere caricata
                credits_logo = self.create_colored_label(
                    header_frame, 
                    text="📂", 
                    font=("Segoe UI Emoji", 24),
                    bg=self.theme.get("header_bg"),
                    emoji="📂"
                )
                credits_logo.pack(side=tk.LEFT, padx=(20, 10))
        else:
            # Usa emoji se l'icona non è disponibile
            credits_logo = self.create_colored_label(
                header_frame, 
                text="📂", 
                font=("Segoe UI Emoji", 24),
                bg=self.theme.get("header_bg"),
                emoji="📂"
            )
            credits_logo.pack(side=tk.LEFT, padx=(20, 10))
        
        title_label = self.create_colored_label(
            header_frame, 
            text="Code Exporter", 
            font=("Segoe UI", 18, "bold"),
            bg=self.theme.get("header_bg"),
            fg=self.theme.get("header_fg"),
            emoji="📂"
        )
        title_label.pack(side=tk.LEFT, pady=20)
        
        # Contenuto
        content_frame = tk.Frame(credits_window, bg=self.theme.get("card_bg"))
        content_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)
        
        # Autore
        author_label = self.create_colored_label(
            content_frame,
            text="Author: Link of Alchemy Labs Studio",
            font=("Segoe UI", 14, "bold"),
            bg=self.theme.get("card_bg"),
            fg=self.theme.get("fg"),
            emoji="📂"
        )
        author_label.pack(anchor=tk.W, pady=(0, 20))
        
        # Licenza
        license_label = self.create_colored_label(
            content_frame,
            text="License:",
            font=("Segoe UI", 14, "bold"),
            bg=self.theme.get("card_bg"),
            fg=self.theme.get("fg"),
            emoji="📄"
        )
        license_label.pack(anchor=tk.W, pady=(0, 10))
        
        license_text = tk.Text(
            content_frame,
            height=12,
            wrap=tk.WORD,
            font=("Segoe UI", 11),
            bg=self.theme.get("bg"),
            fg=self.theme.get("fg"),
            relief=tk.FLAT,
            padx=10,
            pady=10
        )
        license_text.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        license_content = """This is free and unencumbered software released into the public domain.

Anyone is free to copy, modify, publish, use, compile, sell, or distribute this software, either in source code form or as a compiled binary, for any purpose, commercial or non-commercial, and by any means.

In jurisdictions that recognize copyright laws, the author or authors of this software dedicate any and all copyright interest in the software to the public domain. We make this dedication for the benefit of the public at large and to the detriment of our heirs and successors. We intend this dedication to be an overt act of relinquishment in perpetuity of all present and future rights to this software under copyright law.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

For more information, please refer to <https://unlicense.org/>"""
        
        license_text.insert("1.0", license_content)
        license_text.configure(state="disabled")
        
        # Pulsante chiudi
        close_btn = tk.Button(
            content_frame,
            text="Close",
            font=("Segoe UI", 12, "bold"),
            bg=self.theme.get("button_bg"),
            fg=self.theme.get("button_fg"),
            activebackground=self.theme.get("button_hover"),
            relief="solid",
            borderwidth=1,
            highlightthickness=0,
            highlightbackground=self.theme.get("button_border"),
            padx=12,
            pady=6,
            cursor="hand2",
            command=credits_window.destroy
        )
        close_btn.pack(pady=10)
        
        # Aggiorna i colori delle label nella finestra popup
        self.update_colored_labels_recursive(credits_window)
    
    def on_tree_click(self, event):
        # Gestisce la selezione/deselezione singola
        item = self.tree.identify('item', event.x, event.y)
        column = self.tree.identify_column(event.x)
        
        if item and column == '#1':  # Colonna del checkbox
            # Ottieni lo stato attuale
            current_value = self.tree.set(item, "selected")
            
            # Inverti lo stato
            if current_value == "✔️":
                self.tree.set(item, "selected", "")
            else:
                # Controlla se il file è escluso
                if item in self.file_tree and not self.file_tree[item][1]:  # [1] è is_excluded
                    self.tree.set(item, "selected", "✔️")
            
            # Aggiorna i contatori
            self.update_selection_count()
    
    def update_selection_count(self):
        # Aggiorna il conteggio dei file selezionati
        selected_count = 0
        total_size = 0
        
        for item in self.tree.get_children():
            if self.tree.set(item, "selected") == "✔️":
                file_path = self.file_tree.get(item)
                if file_path and file_path[0].is_file() and not file_path[1]:  # [1] è is_excluded
                    selected_count += 1
                    try:
                        total_size += file_path[0].stat().st_size
                    except:
                        pass
            selected_count, size = self._count_selected_files(item, selected_count, total_size)
        
        self.selected_count.set(str(selected_count))
        self.total_size.set(self.format_size(total_size))
    
    def _count_selected_files(self, parent, count, size):
        for item in self.tree.get_children(parent):
            if self.tree.set(item, "selected") == "✔️":
                file_path = self.file_tree.get(item)
                if file_path and file_path[0].is_file() and not file_path[1]:  # [1] è is_excluded
                    count += 1
                    try:
                        size += file_path[0].stat().st_size
                    except:
                        pass
            count, size = self._count_selected_files(item, count, size)
        return count, size
    
    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.project_path.set(folder)
            self.start_scan()
    
    def start_scan(self):
        # Reset UI
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.file_tree = {}
        self.selected_count.set("0")
        self.excluded_count.set("0")
        self.total_size.set("0")
        
        # Mostra progress bar
        self.progress_frame.pack(fill=tk.X, pady=(0, 20), after=self.controls_frame)
        self.progress.start()
        self.status_label.configure(text="🔍 Scanning in progress...")
        self.scan_active = True
        
        # Forza l'aggiornamento dell'interfaccia
        self.root.update_idletasks()
        
        # Ferma eventuali scansioni precedenti
        if self.scan_thread and self.scan_thread.is_alive():
            self.scan_active = False
            self.scan_thread.join(timeout=1.0)
        
        # Avvia la scansione in un thread separato
        self.scan_thread = threading.Thread(target=self.scan_directory_thread, daemon=True)
        self.scan_thread.start()
    
    def scan_directory_thread(self):
        try:
            root_path = Path(self.project_path.get())
            if not root_path.exists():
                self.queue.put(("error", "The selected folder does not exist"))
                return
            
            self.queue.put(("status", "🔍 Analyzing structure..."))
            
            # Prima conta i file totali per la progress bar
            total_files = self.count_files(root_path)
            self.queue.put(("total_files", total_files))
            
            # Esegui la scansione vera e propria
            root_node, excluded_count, selected_count, total_size = self.build_tree(root_path)
            
            if self.scan_active:  # Solo se la scansione non è stata interrotta
                self.queue.put(("scan_complete", root_node, excluded_count, selected_count, total_size))
            else:
                self.queue.put(("status", "❌ Scan interrupted"))
        except Exception as e:
            self.queue.put(("error", f"Error during scanning: {str(e)}"))
    
    def count_files(self, current_path):
        count = 0
        try:
            for item in current_path.iterdir():
                if item.is_dir() and item.name in self.exclude_folders:
                    continue
                
                if item.is_file() and item.name in self.exclude_files:
                    continue
                
                if item.is_file() and item.suffix.lower() in self.exclude_extensions:
                    continue
                
                if item.is_file() and item.suffix not in self.include_extensions:
                    continue
                
                if item.is_dir():
                    count += self.count_files(item)
                else:
                    count += 1
        except PermissionError:
            pass
        
        return count
    
    def build_tree(self, current_path):
        node = Node(current_path.name, current_path, False, current_path.is_dir())
        excluded_count = 0
        selected_count = 0
        total_size = 0
        processed_count = 0
        
        try:
            items = list(current_path.iterdir())
            for item in items:
                if not self.scan_active:
                    break
                    
                processed_count += 1
                
                # Aggiorna periodicamente la coda per mostrare il progresso
                if processed_count % 10 == 0:
                    self.queue.put(("progress", processed_count))
                
                is_excluded = False
                
                if item.is_dir() and item.name in self.exclude_folders:
                    is_excluded = True
                
                if item.is_file() and item.name in self.exclude_files:
                    is_excluded = True
                
                if item.is_file() and item.suffix.lower() in self.exclude_extensions:
                    is_excluded = True
                
                if item.is_file() and item.suffix not in self.include_extensions:
                    is_excluded = True
                
                if not is_excluded or self.show_excluded.get():
                    if item.is_dir():
                        child_node, child_excluded, child_selected, child_size = self.build_tree(item)
                        node.children.append(child_node)
                        excluded_count += child_excluded
                        selected_count += child_selected
                        total_size += child_size
                    else:
                        child_node = Node(item.name, item, is_excluded, False)
                        node.children.append(child_node)
                        
                        if is_excluded:
                            excluded_count += 1
                        else:
                            selected_count += 1
                            try:
                                total_size += item.stat().st_size
                            except:
                                pass
                    
        except PermissionError:
            pass
        
        return node, excluded_count, selected_count, total_size
    
    def process_queue(self):
        try:
            while True:
                msg = self.queue.get_nowait()
                msg_type = msg[0]
                
                if msg_type == "progress":
                    _, count = msg
                    self.status_label.configure(text=f"🔍 Scanning... {count} items processed")
                
                elif msg_type == "total_files":
                    _, total = msg
                    self.status_label.configure(text=f"🔍 Found {total} files to analyze...")
                
                elif msg_type == "status":
                    _, status = msg
                    self.status_label.configure(text=status)
                
                elif msg_type == "error":
                    _, error_msg = msg
                    messagebox.showerror("❌ Error", error_msg)
                    self.stop_scan()
                
                elif msg_type == "scan_complete":
                    _, root_node, excluded_count, selected_count, total_size = msg
                    self.stop_scan()
                    
                    # Aggiorna l'interfaccia con i risultati
                    self.insert_tree("", root_node)
                    
                    self.excluded_count.set(str(excluded_count))
                    self.selected_count.set(str(selected_count))
                    self.total_size.set(self.format_size(total_size))
                    self.status_label.configure(text="✅ Scan completed")
                
        except queue.Empty:
            pass
        
        # Continua a controllare la coda
        self.root.after(100, self.process_queue)
    
    def format_size(self, size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes} bytes"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    
    def stop_scan(self):
        self.progress.stop()
        self.progress_frame.pack_forget()
        self.scan_active = False
    
    def insert_tree(self, parent_id, node):
        item_id = self.tree.insert(parent_id, tk.END, text=node.name, values=("✔️",))
        
        if node.is_excluded:
            self.tree.item(item_id, tags=("excluded",))
        else:
            self.tree.item(item_id, tags=("included",))
        
        self.file_tree[item_id] = (node.path, node.is_excluded)
        
        for child in node.children:
            self.insert_tree(item_id, child)
    
    def toggle_excluded_files(self):
        if self.scan_active:
            messagebox.showinfo("⏳ Wait", "Please wait for the current scan to complete")
            return
            
        self.start_scan()
    
    def select_all(self):
        for item in self.tree.get_children():
            if not self.file_tree[item][1]:  # Non selezionare file esclusi
                self.tree.set(item, "selected", "✔️")
            self._select_children(item)
        self.update_selection_count()
    
    def deselect_all(self):
        for item in self.tree.get_children():
            self.tree.set(item, "selected", "")
            self._deselect_children(item)
        self.update_selection_count()
    
    def _select_children(self, item):
        for child in self.tree.get_children(item):
            if not self.file_tree[child][1]:  # Non selezionare file esclusi
                self.tree.set(child, "selected", "✔️")
            self._select_children(child)
    
    def _deselect_children(self, item):
        for child in self.tree.get_children(item):
            self.tree.set(child, "selected", "")
            self._deselect_children(child)
    
    def export_files(self):
        if not self.project_path.get():
            messagebox.showerror("❌ Error", "Please select a project folder!")
            return
        
        selected_files = []
        self._get_selected_files("", selected_files)
        
        if not selected_files:
            messagebox.showwarning("⚠️ Warning", "No files selected!")
            return
        
        output_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if not output_path:
            return
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                for file_path in selected_files:
                    try:
                        f.write(f"\n\n{'='*50}\n")
                        f.write(f"📄 FILE: {file_path.relative_to(Path(self.project_path.get()))}\n")
                        f.write(f"{'='*50}\n\n")
                        
                        with open(file_path, 'r', encoding='utf-8') as source:
                            f.write(source.read())
                    except Exception as e:
                        f.write(f"\n\n❌ ERROR READING FILE: {str(e)}\n")
            
            messagebox.showinfo("✅ Success", f"Export completed!\nFile saved to:\n{output_path}")
        except Exception as e:
            messagebox.showerror("❌ Error", f"Error during export:\n{str(e)}")
    
    def export_structure(self):
        if not self.project_path.get():
            messagebox.showerror("❌ Error", "Please select a project folder!")
            return
        
        output_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if not output_path:
            return
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("PROJECT STRUCTURE\n")
                f.write("="*50 + "\n\n")
                
                # Esporta la struttura completa
                self._export_tree_structure("", f, 0)
            
            messagebox.showinfo("✅ Success", f"Structure exported!\nFile saved to:\n{output_path}")
        except Exception as e:
            messagebox.showerror("❌ Error", f"Error exporting structure:\n{str(e)}")
    
    def _export_tree_structure(self, parent, f, level):
        for item in self.tree.get_children(parent):
            file_info = self.file_tree.get(item)
            if file_info:
                path, is_excluded = file_info
                name = self.tree.item(item, "text")
                
                # Indentazione per mostrare la gerarchia
                indent = "  " * level
                
                if path.is_dir():
                    f.write(f"{indent}📁 {name}/\n")
                    # Ricorsione per le sottocartelle
                    self._export_tree_structure(item, f, level + 1)
                else:
                    # Per i file, mostra se è selezionato o meno
                    selected = self.tree.set(item, "selected") == "✔️"
                    status = "✅" if selected else "❌"
                    f.write(f"{indent}📄 {name} {status}\n")
    
    def _get_selected_files(self, parent, selected_list):
        for item in self.tree.get_children(parent):
            if self.tree.set(item, "selected") == "✔️":
                file_path = self.file_tree.get(item)
                if file_path and file_path[0].is_file() and not file_path[1]:  # [1] è is_excluded
                    selected_list.append(file_path[0])
            self._get_selected_files(item, selected_list)

if __name__ == "__main__":
    # Usa customtkinter se disponibile, altrimenti usa tkinter standard
    if CUSTOMTKINTER_AVAILABLE:
        root = ctk.CTk()
    else:
        root = tk.Tk()
    
    app = CodeExporterApp(root)
    root.mainloop()