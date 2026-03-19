import subprocess
import time
import psutil
import json
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import winreg
import ctypes

# ─── Configuração persistente ──────────────────────────────────────────────────
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".wallpaper_switcher_config.json")

DEFAULT_CONFIG = {
    "wallpaper_engine": r"C:/Program Files (x86)/Steam/steamapps/common/wallpaper_engine/wallpaper32.exe",
    "check_interval": 10,
    "mappings": [
        {
            "app": "P3R.exe",
            "wallpaper": r"C:\Program Files (x86)\Steam\steamapps\workshop\content\431960\3030059203\project.json"
        },
        {
            "app": "P4G.exe",
            "wallpaper": r"C:\Program Files (x86)\Steam\steamapps\workshop\content\431960\1642100196\project.json"
        },
        {
            "app": "P5R.exe",
            "wallpaper": r"C:\Program Files (x86)\Steam\steamapps\workshop\content\431960\2062717574\project.json"
        }
    ]
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # garante campos obrigatórios
                for k, v in DEFAULT_CONFIG.items():
                    if k not in data:
                        data[k] = v
                return data
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

# ─── Lógica do switcher ────────────────────────────────────────────────────────
def ta_rodando(app_name):
    for proc in psutil.process_iter(['name']):
        try:
            if app_name.lower() in proc.info['name'].lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

def checar(mappings):
    for m in mappings:
        if ta_rodando(m["app"]):
            return m["app"]
    return None

def mudar_wallpaper(wallpaper_engine, caminho):
    try:
        subprocess.run(
            [wallpaper_engine, "-control", "openWallpaper", "-file", caminho, "-monitor", "1"],
            timeout=10
        )
    except Exception:
        pass

# ─── Interface ─────────────────────────────────────────────────────────────────
COLORS = {
    "bg":           "#FFFFFF",
    "surface":      "#F3F3F3",
    "surface2":     "#E8E8E8",
    "border":       "#E0E0E0",
    "accent":       "#0067C0",
    "accent_hover": "#005BA1",
    "accent_light": "#EBF3FB",
    "text":         "#1A1A1A",
    "text_muted":   "#6B6B6B",
    "danger":       "#C42B1C",
    "danger_hover": "#A42315",
    "success":      "#0F7B0F",
    "warning":      "#9D5D00",
    "tag_bg":       "#E3F0FB",
    "tag_text":     "#004E8C",
}

FONT_TITLE   = ("Segoe UI", 20, "bold")
FONT_HEADING = ("Segoe UI", 11, "bold")
FONT_BODY    = ("Segoe UI", 10)
FONT_SMALL   = ("Segoe UI", 9)
FONT_MONO    = ("Consolas", 9)


class WallpaperSwitcherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.config_data = load_config()
        self._worker_thread = None
        self._running = False
        self._ultimo_game = None
        self._status_text = tk.StringVar(value="Parado")
        self._active_app_text = tk.StringVar(value="—")

        self.title("Wallpaper Switcher")
        self.geometry("780x660")
        self.minsize(720, 580)
        self.configure(bg=COLORS["bg"])
        self.resizable(True, True)

        # ícone (ignora se não achar)
        try:
            self.iconbitmap(default="")
        except Exception:
            pass

        self._build_ui()
        self._refresh_table()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Construção da UI ────────────────────────────────────────────────────────
    def _build_ui(self):
        # Barra de título customizada (apenas decorativa — usa título nativo)
        header = tk.Frame(self, bg=COLORS["bg"], pady=0)
        header.pack(fill="x", padx=0, pady=0)

        title_row = tk.Frame(header, bg=COLORS["bg"])
        title_row.pack(fill="x", padx=28, pady=(22, 4))

        tk.Label(title_row, text="Wallpaper Switcher",
                 font=FONT_TITLE, bg=COLORS["bg"], fg=COLORS["text"]).pack(side="left")

        # pill de status
        self._status_pill = tk.Label(title_row, textvariable=self._status_text,
                                     font=FONT_SMALL, bg=COLORS["surface2"],
                                     fg=COLORS["text_muted"], padx=10, pady=3,
                                     relief="flat", bd=0)
        self._status_pill.pack(side="left", padx=(14, 0), pady=(6, 0))

        tk.Label(header, text="Troca automaticamente o wallpaper do Wallpaper Engine conforme o app ativo.",
                 font=FONT_SMALL, bg=COLORS["bg"], fg=COLORS["text_muted"]).pack(anchor="w", padx=28)

        sep = tk.Frame(self, bg=COLORS["border"], height=1)
        sep.pack(fill="x", padx=0, pady=(14, 0))

        # Container principal scrollável
        body = tk.Frame(self, bg=COLORS["bg"])
        body.pack(fill="both", expand=True, padx=28, pady=20)

        # ── Seção: Wallpaper Engine ─────────────────────────────────────────────
        self._section_label(body, "Wallpaper Engine")
        we_row = tk.Frame(body, bg=COLORS["bg"])
        we_row.pack(fill="x", pady=(4, 16))

        self._we_var = tk.StringVar(value=self.config_data["wallpaper_engine"])
        we_entry = self._entry(we_row, self._we_var, font=FONT_MONO)
        we_entry.pack(side="left", fill="x", expand=True)

        self._btn(we_row, "Procurar…", self._browse_we, style="secondary").pack(side="left", padx=(8, 0))

        # ── Seção: Mapeamentos ──────────────────────────────────────────────────
        self._section_label(body, "Mapeamentos")

        # Tabela
        table_frame = tk.Frame(body, bg=COLORS["border"], bd=0)
        table_frame.pack(fill="both", expand=True, pady=(4, 0))

        inner = tk.Frame(table_frame, bg=COLORS["bg"], padx=1, pady=1)
        inner.pack(fill="both", expand=True)

        cols = ("app", "wallpaper")
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Custom.Treeview",
                         background=COLORS["bg"],
                         foreground=COLORS["text"],
                         fieldbackground=COLORS["bg"],
                         borderwidth=0,
                         font=FONT_BODY,
                         rowheight=34)
        style.configure("Custom.Treeview.Heading",
                         background=COLORS["surface"],
                         foreground=COLORS["text_muted"],
                         font=("Segoe UI", 9, "bold"),
                         borderwidth=0,
                         relief="flat")
        style.map("Custom.Treeview",
                  background=[("selected", COLORS["accent_light"])],
                  foreground=[("selected", COLORS["text"])])
        style.layout("Custom.Treeview", [
            ('Treeview.treearea', {'sticky': 'nswe'})
        ])

        self._tree = ttk.Treeview(inner, columns=cols, show="headings",
                                   style="Custom.Treeview", selectmode="browse")
        self._tree.heading("app",       text="Processo (.exe)")
        self._tree.heading("wallpaper", text="Caminho do Wallpaper (string)")
        self._tree.column("app",       width=160, minwidth=120, anchor="w")
        self._tree.column("wallpaper", width=420, minwidth=200, anchor="w")

        vsb = ttk.Scrollbar(inner, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)

        self._tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self._tree.tag_configure("odd",  background=COLORS["bg"])
        self._tree.tag_configure("even", background=COLORS["surface"])

        # Barra de ações da tabela
        action_bar = tk.Frame(body, bg=COLORS["bg"])
        action_bar.pack(fill="x", pady=(10, 0))

        self._btn(action_bar, "+ Adicionar",  self._add_mapping,    style="accent").pack(side="left")
        self._btn(action_bar, "✎ Editar",     self._edit_mapping,   style="secondary").pack(side="left", padx=(8, 0))
        self._btn(action_bar, "✕ Remover",    self._remove_mapping, style="danger").pack(side="left", padx=(8, 0))

        # ── Painel inferior ─────────────────────────────────────────────────────
        sep2 = tk.Frame(self, bg=COLORS["border"], height=1)
        sep2.pack(fill="x", padx=0)

        bottom = tk.Frame(self, bg=COLORS["surface"], pady=12)
        bottom.pack(fill="x", padx=0)

        left_info = tk.Frame(bottom, bg=COLORS["surface"])
        left_info.pack(side="left", padx=28)

        tk.Label(left_info, text="App ativo:", font=FONT_SMALL,
                 bg=COLORS["surface"], fg=COLORS["text_muted"]).pack(side="left")
        tk.Label(left_info, textvariable=self._active_app_text, font=("Segoe UI", 9, "bold"),
                 bg=COLORS["surface"], fg=COLORS["text"]).pack(side="left", padx=(4, 0))

        right_btns = tk.Frame(bottom, bg=COLORS["surface"])
        right_btns.pack(side="right", padx=28)

        self._save_btn  = self._btn(right_btns, "Salvar configuração", self._save_config, style="secondary")
        self._save_btn.pack(side="left", padx=(0, 8))

        self._toggle_btn = self._btn(right_btns, "▶  Iniciar monitoramento", self._toggle_monitor, style="accent")
        self._toggle_btn.pack(side="left")

    # ── Helpers de widget ───────────────────────────────────────────────────────
    def _section_label(self, parent, text):
        row = tk.Frame(parent, bg=COLORS["bg"])
        row.pack(fill="x", pady=(0, 2))
        tk.Label(row, text=text, font=FONT_HEADING,
                 bg=COLORS["bg"], fg=COLORS["text"]).pack(side="left")

    def _entry(self, parent, var, font=None):
        font = font or FONT_BODY
        e = tk.Entry(parent, textvariable=var, font=font,
                     bg=COLORS["surface"], fg=COLORS["text"],
                     relief="flat", bd=0,
                     insertbackground=COLORS["text"],
                     highlightthickness=1,
                     highlightcolor=COLORS["accent"],
                     highlightbackground=COLORS["border"])
        e.configure(width=1)
        # padding interno via padding
        e.configure(fg=COLORS["text"])
        return e

    def _btn(self, parent, text, command, style="secondary"):
        styles = {
            "accent":    (COLORS["accent"],   "#FFFFFF", COLORS["accent_hover"]),
            "secondary": (COLORS["surface2"], COLORS["text"], COLORS["border"]),
            "danger":    (COLORS["danger"],   "#FFFFFF", COLORS["danger_hover"]),
        }
        bg, fg, hover = styles[style]
        b = tk.Label(parent, text=text, font=FONT_BODY,
                     bg=bg, fg=fg, padx=14, pady=6,
                     cursor="hand2", relief="flat")
        b.bind("<Button-1>", lambda e: command())
        b.bind("<Enter>",    lambda e: b.configure(bg=hover))
        b.bind("<Leave>",    lambda e: b.configure(bg=bg))
        return b

    # ── Tabela ──────────────────────────────────────────────────────────────────
    def _refresh_table(self):
        for row in self._tree.get_children():
            self._tree.delete(row)
        for i, m in enumerate(self.config_data["mappings"]):
            tag = "even" if i % 2 == 0 else "odd"
            self._tree.insert("", "end", iid=str(i),
                               values=(m["app"], m["wallpaper"]), tags=(tag,))

    # ── Ações dos botões ────────────────────────────────────────────────────────
    def _browse_we(self):
        path = filedialog.askopenfilename(
            title="Selecionar wallpaper32.exe",
            filetypes=[("Executável", "*.exe"), ("Todos", "*.*")],
            initialdir=r"C:/Program Files (x86)/Steam"
        )
        if path:
            self._we_var.set(path.replace("/", "\\"))

    def _add_mapping(self):
        self._mapping_dialog()

    def _edit_mapping(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showinfo("Wallpaper Switcher", "Selecione um mapeamento para editar.", parent=self)
            return
        idx = int(sel[0])
        self._mapping_dialog(idx)

    def _remove_mapping(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showinfo("Wallpaper Switcher", "Selecione um mapeamento para remover.", parent=self)
            return
        idx = int(sel[0])
        mapping = self.config_data["mappings"][idx]
        if messagebox.askyesno("Remover", f"Remover mapeamento para '{mapping['app']}'?", parent=self):
            self.config_data["mappings"].pop(idx)
            self._refresh_table()

    def _save_config(self):
        self.config_data["wallpaper_engine"] = self._we_var.get()
        save_config(self.config_data)
        self._flash_status("Configuração salva ✓", color=COLORS["success"])

    def _toggle_monitor(self):
        if self._running:
            self._stop_monitor()
        else:
            self._save_config()
            self._start_monitor()

    def _start_monitor(self):
        self._running = True
        self._ultimo_game = None
        self._toggle_btn.configure(text="⏹  Parar monitoramento", bg=COLORS["surface2"], fg=COLORS["text"])
        self._toggle_btn.unbind("<Enter>")
        self._toggle_btn.unbind("<Leave>")
        self._toggle_btn.bind("<Enter>", lambda e: self._toggle_btn.configure(bg=COLORS["border"]))
        self._toggle_btn.bind("<Leave>", lambda e: self._toggle_btn.configure(bg=COLORS["surface2"]))
        self._set_status("Monitorando…", COLORS["success"])
        self._worker_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._worker_thread.start()

    def _stop_monitor(self):
        self._running = False
        self._toggle_btn.configure(text="▶  Iniciar monitoramento", bg=COLORS["accent"], fg="#FFFFFF")
        self._toggle_btn.unbind("<Enter>")
        self._toggle_btn.unbind("<Leave>")
        self._toggle_btn.bind("<Enter>", lambda e: self._toggle_btn.configure(bg=COLORS["accent_hover"]))
        self._toggle_btn.bind("<Leave>", lambda e: self._toggle_btn.configure(bg=COLORS["accent"]))
        self._set_status("Parado", COLORS["text_muted"])
        self._active_app_text.set("—")

    def _monitor_loop(self):
        while self._running:
            mappings = self.config_data["mappings"]
            game = checar(mappings)
            if game and game != self._ultimo_game:
                wallpaper = next((m["wallpaper"] for m in mappings if m["app"] == game), None)
                if wallpaper:
                    mudar_wallpaper(self.config_data["wallpaper_engine"], wallpaper)
                    self._ultimo_game = game
                    self.after(0, lambda g=game: self._active_app_text.set(g))
            elif not game:
                self._ultimo_game = None
                self.after(0, lambda: self._active_app_text.set("—"))
            interval = self.config_data.get("check_interval", 10)
            time.sleep(interval)

    # ── Helpers de status ───────────────────────────────────────────────────────
    def _set_status(self, text, color):
        self._status_text.set(text)
        self._status_pill.configure(fg=color)

    def _flash_status(self, text, color):
        self._set_status(text, color)
        self.after(3000, lambda: self._set_status(
            "Monitorando…" if self._running else "Parado",
            COLORS["success"] if self._running else COLORS["text_muted"]
        ))

    def _on_close(self):
        self._running = False
        self.destroy()

    # ── Diálogo de mapeamento ───────────────────────────────────────────────────
    def _mapping_dialog(self, idx=None):
        editing = idx is not None
        mapping = self.config_data["mappings"][idx] if editing else {"app": "", "wallpaper": ""}

        dlg = tk.Toplevel(self)
        dlg.title("Editar mapeamento" if editing else "Novo mapeamento")
        dlg.configure(bg=COLORS["bg"])
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()

        # Centralizar
        dlg.geometry("560x260")
        dlg.update_idletasks()
        x = self.winfo_x() + (self.winfo_width()  - 560) // 2
        y = self.winfo_y() + (self.winfo_height() - 260) // 2
        dlg.geometry(f"560x260+{x}+{y}")

        pad = tk.Frame(dlg, bg=COLORS["bg"], padx=24, pady=20)
        pad.pack(fill="both", expand=True)

        tk.Label(pad, text="Editar mapeamento" if editing else "Novo mapeamento",
                 font=FONT_HEADING, bg=COLORS["bg"], fg=COLORS["text"]).pack(anchor="w")
        tk.Label(pad, text="Informe o nome do processo (.exe) e o caminho completo como string.",
                 font=FONT_SMALL, bg=COLORS["bg"], fg=COLORS["text_muted"]).pack(anchor="w", pady=(2, 14))

        # Campo app
        tk.Label(pad, text="Processo (.exe)", font=FONT_SMALL,
                 bg=COLORS["bg"], fg=COLORS["text_muted"]).pack(anchor="w")
        app_var = tk.StringVar(value=mapping["app"])
        app_e = self._entry(pad, app_var)
        app_e.pack(fill="x", pady=(2, 10), ipady=6)

        # Campo wallpaper
        tk.Label(pad, text="Caminho do wallpaper (project.json)", font=FONT_SMALL,
                 bg=COLORS["bg"], fg=COLORS["text_muted"]).pack(anchor="w")

        wp_row = tk.Frame(pad, bg=COLORS["bg"])
        wp_row.pack(fill="x", pady=(2, 16))

        wp_var = tk.StringVar(value=mapping["wallpaper"])
        wp_e = self._entry(wp_row, wp_var, font=FONT_MONO)
        wp_e.pack(side="left", fill="x", expand=True, ipady=6)

        def browse_wp():
            path = filedialog.askopenfilename(
                title="Selecionar project.json",
                filetypes=[("JSON", "*.json"), ("Todos", "*.*")],
                initialdir=r"C:\Program Files (x86)\Steam\steamapps\workshop\content"
            )
            if path:
                wp_var.set(path.replace("/", "\\"))

        self._btn(wp_row, "…", browse_wp, style="secondary").pack(side="left", padx=(6, 0))

        # Botões
        btn_row = tk.Frame(pad, bg=COLORS["bg"])
        btn_row.pack(fill="x")

        def confirm():
            app_val = app_var.get().strip()
            wp_val  = wp_var.get().strip()
            if not app_val or not wp_val:
                messagebox.showwarning("Campo obrigatório", "Preencha todos os campos.", parent=dlg)
                return
            entry = {"app": app_val, "wallpaper": wp_val}
            if editing:
                self.config_data["mappings"][idx] = entry
            else:
                self.config_data["mappings"].append(entry)
            self._refresh_table()
            dlg.destroy()

        self._btn(btn_row, "Cancelar", dlg.destroy, style="secondary").pack(side="right", padx=(8, 0))
        self._btn(btn_row, "Salvar",   confirm,      style="accent").pack(side="right")


if __name__ == "__main__":
    # DPI awareness para Windows
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    app = WallpaperSwitcherApp()
    app.mainloop()
