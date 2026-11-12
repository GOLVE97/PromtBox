import json
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from pathlib import Path
from datetime import datetime
import sys

APP_NAME = "PromptBox"
APP_VERSION = "0.5.0"
DATA_DIR = Path.home() / "AppData" / "Local" / APP_NAME
DB_PATH = DATA_DIR / "prompts.db"
SETTINGS_PATH = DATA_DIR / "settings.json"
DEFAULT_CATEGORIES = ["General", "Trabajo", "Programación", "Estudio", "Creatividad", "Marketing"]

if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("NICOLUSA.PromptBox.Desktop")
    except Exception:
        pass


def resource_path(relative_path):
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base_path / relative_path


THEMES = {
    "dark": {
        "bg": "#0B1220", "panel": "#111A36", "panel2": "#172443",
        "surface": "#1E293B", "border": "#2B3B5C", "text": "#F1F5F9",
        "muted": "#9AA8C2", "primary": "#3882F6", "primary_hover": "#2563D9",
        "accent": "#8B5CF6", "danger": "#EF4444", "success": "#22C55E",
        "input": "#0F1A30", "selected": "#243B70", "row_alt": "#14213D"
    },
    "light": {
        "bg": "#F1F5F9", "panel": "#FFFFFF", "panel2": "#F8FAFC",
        "surface": "#E8EEF8", "border": "#D7E0EF", "text": "#17233B",
        "muted": "#64748B", "primary": "#3882F6", "primary_hover": "#2563D9",
        "accent": "#8B5CF6", "danger": "#DC3545", "success": "#16A34A",
        "input": "#FFFFFF", "selected": "#E1EAFF", "row_alt": "#F7F9FD"
    }
}


class PromptStore:
    """SQLite persistence. Existing prompts are preserved; new fields are migrated safely."""
    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'General',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(prompts)")}
        if "is_favorite" not in columns:
            self.conn.execute("ALTER TABLE prompts ADD COLUMN is_favorite INTEGER NOT NULL DEFAULT 0")
        if "tags" not in columns:
            self.conn.execute("ALTER TABLE prompts ADD COLUMN tags TEXT NOT NULL DEFAULT ''")
        self.conn.commit()

    def all(self, search="", category="Todas", favorites_only=False):
        sql = "SELECT * FROM prompts WHERE (title LIKE ? OR content LIKE ? OR tags LIKE ?)"
        args = [f"%{search}%", f"%{search}%", f"%{search}%"]
        if category != "Todas":
            sql += " AND category = ?"
            args.append(category)
        if favorites_only:
            sql += " AND is_favorite = 1"
        sql += " ORDER BY updated_at DESC, id DESC"
        return self.conn.execute(sql, args).fetchall()

    def get(self, prompt_id):
        return self.conn.execute("SELECT * FROM prompts WHERE id=?", (prompt_id,)).fetchone()

    def save(self, title, content, category, tags="", favorite=False, prompt_id=None):
        now = datetime.now().isoformat(timespec="seconds")
        if prompt_id:
            self.conn.execute(
                "UPDATE prompts SET title=?, content=?, category=?, tags=?, is_favorite=?, updated_at=? WHERE id=?",
                (title, content, category, tags, int(favorite), now, prompt_id)
            )
        else:
            self.conn.execute(
                "INSERT INTO prompts(title, content, category, created_at, updated_at, tags, is_favorite) VALUES(?,?,?,?,?,?,?)",
                (title, content, category, now, now, tags, int(favorite))
            )
        self.conn.commit()

    def delete(self, prompt_id):
        self.conn.execute("DELETE FROM prompts WHERE id=?", (prompt_id,))
        self.conn.commit()

    def categories(self):
        rows = self.conn.execute("SELECT DISTINCT category FROM prompts ORDER BY category").fetchall()
        return sorted(set(DEFAULT_CATEGORIES + [r["category"] for r in rows]))

    def category_counts(self):
        return self.conn.execute(
            "SELECT category, COUNT(*) AS total FROM prompts GROUP BY category ORDER BY category"
        ).fetchall()

    def rename_category(self, old, new):
        self.conn.execute("UPDATE prompts SET category=?, updated_at=? WHERE category=?",
                          (new, datetime.now().isoformat(timespec="seconds"), old))
        self.conn.commit()

    def delete_category(self, category):
        self.conn.execute("UPDATE prompts SET category='General', updated_at=? WHERE category=?",
                          (datetime.now().isoformat(timespec="seconds"), category))
        self.conn.commit()

    def stats(self):
        total = self.conn.execute("SELECT COUNT(*) FROM prompts").fetchone()[0]
        cats = self.conn.execute("SELECT COUNT(DISTINCT category) FROM prompts").fetchone()[0]
        favs = self.conn.execute("SELECT COUNT(*) FROM prompts WHERE is_favorite=1").fetchone()[0]
        return total, cats, favs

    def export_data(self, path):
        rows = self.conn.execute(
            "SELECT title, content, category, created_at, updated_at, tags, is_favorite FROM prompts ORDER BY id"
        ).fetchall()
        payload = {"app": APP_NAME, "version": 2, "exported_at": datetime.now().isoformat(),
                   "prompts": [dict(r) for r in rows]}
        Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def import_data(self, path):
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        prompts = payload.get("prompts") if isinstance(payload, dict) else None
        if not isinstance(prompts, list):
            raise ValueError("El archivo no contiene una lista válida de prompts.")
        valid = []
        for item in prompts:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()
            content = str(item.get("content", "")).strip()
            category = str(item.get("category", "General")).strip() or "General"
            if title and content:
                valid.append((title, content, category, str(item.get("tags", "")),
                              int(bool(item.get("is_favorite", False)))))
        now = datetime.now().isoformat(timespec="seconds")
        with self.conn:
            for title, content, category, tags, favorite in valid:
                self.conn.execute(
                    "INSERT INTO prompts(title, content, category, created_at, updated_at, tags, is_favorite) VALUES(?,?,?,?,?,?,?)",
                    (title, content, category, now, now, tags, favorite)
                )
        return len(valid)


class PromptDialog(tk.Toplevel):
    def __init__(self, parent, categories, colors, prompt=None):
        super().__init__(parent)
        self.result = None
        self.c = colors
        self.title("Editar prompt" if prompt else "Nuevo prompt")
        self.geometry("720x650")
        self.minsize(600, 540)
        self.configure(bg=self.c["bg"])
        self.transient(parent)
        self.grab_set()

        outer = tk.Frame(self, bg=self.c["panel"], padx=24, pady=22)
        outer.pack(fill="both", expand=True, padx=12, pady=12)
        tk.Label(outer, text="Editar prompt" if prompt else "Crear nuevo prompt",
                 bg=self.c["panel"], fg=self.c["text"], font=("Segoe UI Semibold", 19)).pack(anchor="w")
        tk.Label(outer, text="Organiza tu instrucción para reutilizarla cuando la necesites.",
                 bg=self.c["panel"], fg=self.c["muted"], font=("Segoe UI", 9)).pack(anchor="w", pady=(3, 20))

        self.title_var = tk.StringVar(value=prompt["title"] if prompt else "")
        self.category_var = tk.StringVar(value=prompt["category"] if prompt else "General")
        self.tags_var = tk.StringVar(value=prompt["tags"] if prompt else "")
        self.favorite_var = tk.BooleanVar(value=bool(prompt["is_favorite"]) if prompt else False)

        self._label(outer, "Título *")
        self.title_entry = self._entry(outer, self.title_var)
        self.title_entry.pack(fill="x", pady=(5, 14))
        self._label(outer, "Categoría *")
        self.category_box = ttk.Combobox(outer, textvariable=self.category_var, values=categories, state="normal")
        self.category_box.pack(fill="x", pady=(5, 14), ipady=5)
        self._label(outer, "Contenido del prompt *")
        self.content = tk.Text(outer, height=12, wrap="word", font=("Segoe UI", 10),
                               bg=self.c["input"], fg=self.c["text"], insertbackground=self.c["text"],
                               relief="flat", padx=12, pady=12, undo=True,
                               highlightthickness=1, highlightbackground=self.c["border"])
        self.content.pack(fill="both", expand=True, pady=(5, 14))
        if prompt:
            self.content.insert("1.0", prompt["content"])
        self._label(outer, "Etiquetas (separadas por comas)")
        self._entry(outer, self.tags_var).pack(fill="x", pady=(5, 10))
        fav = tk.Checkbutton(outer, text="Marcar como favorito", variable=self.favorite_var,
                             bg=self.c["panel"], fg=self.c["text"], selectcolor=self.c["surface"],
                             activebackground=self.c["panel"], activeforeground=self.c["text"])
        fav.pack(anchor="w", pady=(0, 14))
        buttons = tk.Frame(outer, bg=self.c["panel"])
        buttons.pack(fill="x")
        self._button(buttons, "Cancelar", self.destroy, secondary=True).pack(side="right")
        self._button(buttons, "Guardar cambios" if prompt else "Guardar prompt", self.save, primary=True).pack(side="right", padx=(0, 8))
        self.title_entry.focus_set()
        self.bind("<Escape>", lambda _e: self.destroy())

    def _label(self, parent, text):
        tk.Label(parent, text=text, bg=self.c["panel"], fg=self.c["text"],
                 font=("Segoe UI Semibold", 9)).pack(anchor="w")

    def _entry(self, parent, variable):
        return tk.Entry(parent, textvariable=variable, bg=self.c["input"], fg=self.c["text"],
                        insertbackground=self.c["text"], relief="flat", font=("Segoe UI", 10),
                        highlightthickness=1, highlightbackground=self.c["border"],
                        highlightcolor=self.c["primary"])

    def _button(self, parent, text, command, primary=False, secondary=False):
        bg = self.c["primary"] if primary else self.c["surface"]
        fg = "#FFFFFF" if primary else self.c["text"]
        return tk.Button(parent, text=text, command=command, bg=bg, fg=fg,
                         activebackground=self.c["primary_hover"] if primary else self.c["border"],
                         activeforeground="#FFFFFF" if primary else self.c["text"],
                         relief="flat", bd=0, padx=16, pady=9, cursor="hand2",
                         font=("Segoe UI Semibold", 9))

    def save(self):
        title = self.title_var.get().strip()
        content = self.content.get("1.0", "end-1c").strip()
        category = self.category_var.get().strip() or "General"
        tags = self.tags_var.get().strip()
        if not title or not content:
            messagebox.showwarning("Faltan datos", "Escribe un título y el contenido del prompt.", parent=self)
            return
        self.result = (title, content, category, tags, self.favorite_var.get())
        self.destroy()


class PromptBoxApp(tk.Tk):
    NAV_ITEMS = [
        ("library", "▤", "Biblioteca"), ("categories", "▱", "Categorías"),
        ("favorites", "☆", "Favoritos"), ("backups", "▣", "Respaldos"),
        ("settings", "⚙", "Configuración"), ("about", "ⓘ", "Acerca de")
    ]

    def __init__(self):
        super().__init__()
        self.store = PromptStore()
        self.selected_id = None
        self.current_view = "library"
        self.settings = self._load_settings()
        self.theme_name = self.settings.get("theme", "dark")
        if self.theme_name not in ("dark", "light", "system"):
            self.theme_name = "dark"
        self.c = self._colors()
        self.title("PromptBox")
        self.geometry("1240x800")
        self.minsize(980, 650)
        self._set_app_icons()
        self.setup_style()
        self.build_shell()
        self.show_view("library")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _load_settings(self):
        try:
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {"theme": "dark", "confirm_delete": True, "language": "Español"}

    def _save_settings(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        SETTINGS_PATH.write_text(json.dumps(self.settings, ensure_ascii=False, indent=2), encoding="utf-8")

    def _colors(self):
        if self.theme_name == "system":
            try:
                import darkdetect
                resolved = "dark" if darkdetect.isDark() else "light"
            except Exception:
                resolved = "dark"
        else:
            resolved = self.theme_name
        return THEMES[resolved]

    def _set_app_icons(self):
        try:
            self._icon_image = tk.PhotoImage(file=str(resource_path("promptbox_icon.png")))
            self.iconphoto(True, self._icon_image)
        except Exception:
            self._icon_image = None
        if sys.platform == "win32":
            try:
                self.iconbitmap(default=str(resource_path("promptbox.ico")))
            except Exception:
                pass

    def setup_style(self):
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self._apply_styles()

    def _apply_styles(self):
        c = self.c
        self.style.configure(".", font=("Segoe UI", 10))
        self.style.configure("TCombobox", padding=7, fieldbackground=c["input"], background=c["surface"],
                             foreground=c["text"], arrowcolor=c["muted"])
        self.style.map("TCombobox", fieldbackground=[("readonly", c["input"])],
                       foreground=[("readonly", c["text"])])
        self.style.configure("Treeview", rowheight=38, background=c["panel2"],
                             fieldbackground=c["panel2"], foreground=c["text"],
                             borderwidth=0, font=("Segoe UI", 10))
        self.style.configure("Treeview.Heading", background=c["surface"], foreground=c["muted"],
                             font=("Segoe UI Semibold", 9), padding=10, relief="flat")
        self.style.map("Treeview", background=[("selected", c["selected"])],
                       foreground=[("selected", c["text"])])

    def build_shell(self):
        self.configure(bg=self.c["bg"])
        self.shell = tk.Frame(self, bg=self.c["bg"])
        self.shell.pack(fill="both", expand=True)
        # Hybrid shell: fixed left navigation and top command bar.
        self.sidebar = tk.Frame(self.shell, bg=self.c["panel"], width=218)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        brand = tk.Frame(self.sidebar, bg=self.c["panel"], padx=18, pady=20)
        brand.pack(fill="x")
        try:
            self.brand_img = tk.PhotoImage(file=str(resource_path("promptbox_icon.png"))).subsample(9, 9)
            tk.Label(brand, image=self.brand_img, bg=self.c["panel"]).pack(side="left", padx=(0, 9))
        except Exception:
            self.brand_img = None
        tk.Label(brand, text="PromptBox", bg=self.c["panel"], fg=self.c["text"],
                 font=("Segoe UI Semibold", 16)).pack(side="left")
        tk.Label(self.sidebar, text="ESPACIO DE TRABAJO", bg=self.c["panel"], fg=self.c["muted"],
                 font=("Segoe UI Semibold", 8)).pack(anchor="w", padx=18, pady=(14, 8))
        self.nav_buttons = {}
        for key, icon, label in self.NAV_ITEMS:
            b = tk.Button(self.sidebar, text=f"  {icon}   {label}", anchor="w",
                          command=lambda k=key: self.show_view(k), relief="flat", bd=0,
                          padx=14, pady=11, cursor="hand2", font=("Segoe UI Semibold", 9))
            b.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[key] = b
        spacer = tk.Frame(self.sidebar, bg=self.c["panel"])
        spacer.pack(fill="both", expand=True)
        tk.Label(self.sidebar, text=f"PROMPTBOX  v{APP_VERSION}", bg=self.c["panel"],
                 fg=self.c["muted"], font=("Segoe UI", 8)).pack(anchor="w", padx=18, pady=18)

        self.main_area = tk.Frame(self.shell, bg=self.c["bg"])
        self.main_area.pack(side="left", fill="both", expand=True)
        self.topbar = tk.Frame(self.main_area, bg=self.c["panel2"], padx=22, pady=13)
        self.topbar.pack(fill="x")
        self.page_title_var = tk.StringVar(value="Biblioteca")
        tk.Label(self.topbar, textvariable=self.page_title_var, bg=self.c["panel2"],
                 fg=self.c["text"], font=("Segoe UI Semibold", 12)).pack(side="left")
        self.global_search_var = tk.StringVar()
        search = tk.Entry(self.topbar, textvariable=self.global_search_var, width=34,
                          bg=self.c["input"], fg=self.c["text"], insertbackground=self.c["text"],
                          relief="flat", font=("Segoe UI", 9))
        search.pack(side="right", ipady=7, padx=(10, 0))
        search.insert(0, "Buscar en PromptBox…")
        search.bind("<FocusIn>", lambda _e: search.delete(0, "end") if search.get() == "Buscar en PromptBox…" else None)
        search.bind("<Return>", lambda _e: self.show_view("library", search_query=self.global_search_var.get()))
        self.content_host = tk.Frame(self.main_area, bg=self.c["bg"])
        self.content_host.pack(fill="both", expand=True)
        self.status_var = tk.StringVar(value="Listo")
        footer = tk.Frame(self.main_area, bg=self.c["panel"], padx=18, pady=8)
        footer.pack(fill="x", side="bottom")
        tk.Label(footer, text="●", bg=self.c["panel"], fg=self.c["success"]).pack(side="left")
        tk.Label(footer, textvariable=self.status_var, bg=self.c["panel"],
                 fg=self.c["muted"], font=("Segoe UI", 8)).pack(side="left", padx=7)
        tk.Label(footer, text="NICOLUSA", bg=self.c["panel"], fg=self.c["muted"],
                 font=("Segoe UI Semibold", 8)).pack(side="right")

    def _clear_content(self):
        for child in self.content_host.winfo_children():
            child.destroy()

    def _panel(self, parent, **kwargs):
        return tk.Frame(parent, bg=self.c["panel"], highlightthickness=1,
                        highlightbackground=self.c["border"], **kwargs)

    def _label(self, parent, text, size=10, color=None, bold=False, **kwargs):
        return tk.Label(parent, text=text, bg=kwargs.pop("bg", self.c["bg"]),
                        fg=color or self.c["text"],
                        font=("Segoe UI Semibold" if bold else "Segoe UI", size), **kwargs)

    def _button(self, parent, text, command, kind="secondary"):
        palette = {
            "primary": (self.c["primary"], "#FFFFFF", self.c["primary_hover"]),
            "secondary": (self.c["surface"], self.c["text"], self.c["border"]),
            "danger": (self.c["danger"], "#FFFFFF", "#B91C1C"),
            "accent": (self.c["accent"], "#FFFFFF", "#7541D8")
        }
        bg, fg, active = palette[kind]
        return tk.Button(parent, text=text, command=command, bg=bg, fg=fg,
                         activebackground=active, activeforeground="#FFFFFF",
                         relief="flat", bd=0, padx=14, pady=9, cursor="hand2",
                         font=("Segoe UI Semibold", 9))

    def _page_header(self, title, subtitle, action=None, command=None):
        row = tk.Frame(self.content_host, bg=self.c["bg"])
        row.pack(fill="x", padx=26, pady=(24, 18))
        block = tk.Frame(row, bg=self.c["bg"])
        block.pack(side="left", fill="x", expand=True)
        self._label(block, title, 20, bold=True).pack(anchor="w")
        self._label(block, subtitle, 9, self.c["muted"]).pack(anchor="w", pady=(4, 0))
        if action:
            self._button(row, action, command, "primary").pack(side="right")

    def _card(self, parent, caption, value, accent=None):
        card = self._panel(parent, padx=16, pady=13)
        self._label(card, caption.upper(), 8, self.c["muted"], bold=True).pack(anchor="w")
        self._label(card, value, 21, accent or self.c["text"], bold=True).pack(anchor="w", pady=(7, 0))
        return card

    def show_view(self, view, search_query=None):
        self.current_view = view
        self.selected_id = self.selected_id if view in ("library", "favorites") else self.selected_id
        titles = dict((k, label) for k, _, label in self.NAV_ITEMS)
        self.page_title_var.set(titles.get(view, "PromptBox"))
        for key, button in self.nav_buttons.items():
            selected = key == view
            button.configure(bg=self.c["selected"] if selected else self.c["panel"],
                             fg=self.c["primary"] if selected else self.c["muted"],
                             activebackground=self.c["selected"])
        self._clear_content()
        if view == "library":
            self._view_library(search_query)
        elif view == "categories":
            self._view_categories()
        elif view == "favorites":
            self._view_favorites()
        elif view == "backups":
            self._view_backups()
        elif view == "settings":
            self._view_settings()
        elif view == "about":
            self._view_about()

    def _view_library(self, search_query=None):
        self._page_header("Biblioteca de prompts", "Organiza, guarda y reutiliza tus instrucciones de IA.",
                          "＋  Nuevo prompt", self.new_prompt)
        total, cats, favs = self.store.stats()
        stats = tk.Frame(self.content_host, bg=self.c["bg"])
        stats.pack(fill="x", padx=26, pady=(0, 16))
        for i, (cap, val, color) in enumerate((("Prompts guardados", total, self.c["primary"]),
                                               ("Categorías", cats, self.c["accent"]),
                                               ("Favoritos", favs, "#EAB308"))):
            self._card(stats, cap, str(val), color).pack(side="left", fill="x", expand=True, padx=(0 if i == 0 else 10, 0))
        toolbar = tk.Frame(self.content_host, bg=self.c["bg"])
        toolbar.pack(fill="x", padx=26, pady=(0, 12))
        self.library_search = tk.StringVar(value=search_query or "")
        ent = tk.Entry(toolbar, textvariable=self.library_search, bg=self.c["input"], fg=self.c["text"],
                       insertbackground=self.c["text"], relief="flat", font=("Segoe UI", 10))
        ent.pack(side="left", fill="x", expand=True, ipady=9, padx=(0, 10))
        ent.bind("<KeyRelease>", lambda _e: self._populate_tree(self.library_tree, self.library_search.get()))
        self.library_category = tk.StringVar(value="Todas")
        combo = ttk.Combobox(toolbar, textvariable=self.library_category,
                             values=["Todas"] + sorted(set(self.store.categories() + self.settings.get("custom_categories", []))), state="readonly", width=18)
        combo.pack(side="left", ipady=5, padx=(0, 10))
        combo.bind("<<ComboboxSelected>>", lambda _e: self._populate_tree(self.library_tree, self.library_search.get()))
        self._button(toolbar, "Importar", self.import_data).pack(side="left", padx=(0, 8))
        self._button(toolbar, "Exportar", self.export_data).pack(side="left")
        area = tk.Frame(self.content_host, bg=self.c["bg"])
        area.pack(fill="both", expand=True, padx=26, pady=(0, 22))
        left = self._panel(area, padx=12, pady=12)
        left.pack(side="left", fill="both", expand=True)
        self._label(left, "Mis prompts", 12, bold=True).pack(anchor="w", pady=(0, 10))
        self.library_tree = self._make_tree(left)
        self.library_tree.bind("<<TreeviewSelect>>", self._tree_selected)
        self.library_tree.bind("<Double-1>", lambda _e: self.edit_prompt())
        right = self._panel(area, width=330, padx=15, pady=14)
        right.pack(side="right", fill="y", padx=(14, 0))
        right.pack_propagate(False)
        self._label(right, "VISTA PREVIA", 8, self.c["muted"], bold=True).pack(anchor="w")
        self.preview_title = self._label(right, "Selecciona un prompt", 13, bold=True, wraplength=290, justify="left")
        self.preview_title.pack(anchor="w", pady=(12, 7))
        self.preview_category = self._label(right, "", 9, self.c["accent"], bold=True)
        self.preview_category.pack(anchor="w", pady=(0, 10))
        self.preview_content = tk.Text(right, wrap="word", bg=self.c["input"], fg=self.c["text"],
                                       insertbackground=self.c["text"], relief="flat", bd=0,
                                       padx=12, pady=12, font=("Segoe UI", 9), state="disabled")
        self.preview_content.pack(fill="both", expand=True)
        actions = tk.Frame(right, bg=self.c["panel"])
        actions.pack(fill="x", pady=(12, 0))
        self._button(actions, "Copiar", self.copy_prompt, "primary").pack(side="left")
        self._button(actions, "Editar", self.edit_prompt).pack(side="left", padx=6)
        self._button(actions, "Eliminar", self.delete_prompt, "danger").pack(side="right")
        self._populate_tree(self.library_tree, self.library_search.get())

    def _make_tree(self, parent):
        wrap = tk.Frame(parent, bg=self.c["panel"])
        wrap.pack(fill="both", expand=True)
        tree = ttk.Treeview(wrap, columns=("title", "category", "updated"), show="headings")
        tree.heading("title", text="TÍTULO")
        tree.heading("category", text="CATEGORÍA")
        tree.heading("updated", text="ACTUALIZADO")
        tree.column("title", width=360, anchor="w")
        tree.column("category", width=130, anchor="w")
        tree.column("updated", width=145, anchor="w")
        scroll = ttk.Scrollbar(wrap, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        tree.tag_configure("odd", background=self.c["row_alt"])
        return tree

    def _populate_tree(self, tree, search=""):
        for item in tree.get_children():
            tree.delete(item)
        category = self.library_category.get() if hasattr(self, "library_category") and self.current_view == "library" else "Todas"
        fav_only = self.current_view == "favorites"
        rows = self.store.all(search, category, fav_only)
        for index, row in enumerate(rows):
            updated = row["updated_at"].replace("T", " ")[:16]
            title = ("★  " if row["is_favorite"] else "") + row["title"]
            tree.insert("", "end", iid=str(row["id"]), values=(title, row["category"], updated),
                        tags=("odd",) if index % 2 else ())
        self.status_var.set(f"{len(rows)} prompt(s)")
        if self.selected_id and tree.exists(str(self.selected_id)):
            tree.selection_set(str(self.selected_id))
            self._show_selected_preview()

    def _tree_selected(self, _event=None):
        tree = self.library_tree if self.current_view == "library" else self.favorites_tree
        selection = tree.selection()
        if selection:
            self.selected_id = int(selection[0])
            self._show_selected_preview()

    def _show_selected_preview(self):
        prompt = self.store.get(self.selected_id) if self.selected_id else None
        if not prompt or not hasattr(self, "preview_content"):
            return
        self.preview_title.configure(text=prompt["title"])
        self.preview_category.configure(text=prompt["category"])
        self.preview_content.configure(state="normal")
        self.preview_content.delete("1.0", "end")
        self.preview_content.insert("1.0", prompt["content"])
        self.preview_content.configure(state="disabled")

    def _view_categories(self):
        self._page_header("Categorías", "Organiza tu biblioteca y administra sus grupos.",
                          "＋  Nueva categoría", self.new_category)
        panel = self._panel(self.content_host, padx=16, pady=14)
        panel.pack(fill="both", expand=True, padx=26, pady=(0, 24))
        self._label(panel, "Tus categorías", 12, bold=True).pack(anchor="w", pady=(0, 12))
        tree = ttk.Treeview(panel, columns=("name", "count"), show="headings", height=15)
        tree.heading("name", text="CATEGORÍA")
        tree.heading("count", text="PROMPTS")
        tree.column("name", width=500, anchor="w")
        tree.column("count", width=120, anchor="center")
        tree.pack(fill="both", expand=True)
        self.category_tree = tree
        counts = {row["category"]: row["total"] for row in self.store.category_counts()}
        all_categories = sorted(set(self.store.categories() + self.settings.get("custom_categories", [])))
        for category in all_categories:
            tree.insert("", "end", iid=category, values=(category, counts.get(category, 0)))
        actions = tk.Frame(panel, bg=self.c["panel"])
        actions.pack(fill="x", pady=(14, 0))
        self._button(actions, "Renombrar", self.rename_category).pack(side="left")
        self._button(actions, "Eliminar", self.remove_category, "danger").pack(side="left", padx=8)
        self._label(panel, "Al eliminar una categoría, sus prompts se conservarán en «General».",
                    8, self.c["muted"]).pack(anchor="w", pady=(12, 0))

    def _view_favorites(self):
        self._page_header("Favoritos", "Tus instrucciones importantes, siempre a mano.")
        panel = self._panel(self.content_host, padx=14, pady=14)
        panel.pack(fill="both", expand=True, padx=26, pady=(0, 24))
        self._label(panel, "Prompts favoritos", 12, bold=True).pack(anchor="w", pady=(0, 12))
        self.favorites_tree = self._make_tree(panel)
        self.favorites_tree.bind("<<TreeviewSelect>>", self._tree_selected)
        self.favorites_tree.bind("<Double-1>", lambda _e: self.edit_prompt())
        self._populate_tree(self.favorites_tree)

    def _view_backups(self):
        self._page_header("Respaldos", "Importa, exporta y protege tu biblioteca de prompts.")
        row = tk.Frame(self.content_host, bg=self.c["bg"])
        row.pack(fill="x", padx=26, pady=(0, 16))
        for title, desc, button, command in (
            ("Exportar biblioteca", "Guarda tus prompts en un archivo JSON.", "Exportar JSON", self.export_data),
            ("Importar biblioteca", "Agrega prompts desde un respaldo JSON válido.", "Importar JSON", self.import_data)
        ):
            card = self._panel(row, padx=20, pady=20)
            card.pack(side="left", fill="both", expand=True, padx=(0 if title.startswith("Exportar") else 12, 0))
            self._label(card, title, 13, bold=True).pack(anchor="w")
            self._label(card, desc, 9, self.c["muted"], wraplength=350, justify="left").pack(anchor="w", pady=(8, 18))
            self._button(card, button, command, "primary" if title.startswith("Exportar") else "secondary").pack(anchor="w")
        info = self._panel(self.content_host, padx=20, pady=18)
        info.pack(fill="x", padx=26)
        total, _, _ = self.store.stats()
        self._label(info, "Estado de la biblioteca", 12, bold=True).pack(anchor="w")
        self._label(info, f"{total} prompts almacenados localmente · Base de datos SQLite",
                    9, self.c["muted"]).pack(anchor="w", pady=(8, 0))
        self._label(info, f"Ubicación: {DB_PATH}", 8, self.c["muted"], wraplength=850).pack(anchor="w", pady=(5, 0))

    def _view_settings(self):
        self._page_header("Configuración", "Personaliza la apariencia y el comportamiento de PromptBox.")
        panel = self._panel(self.content_host, padx=22, pady=20)
        panel.pack(fill="both", expand=True, padx=26, pady=(0, 24))
        self._label(panel, "Apariencia", 14, bold=True).pack(anchor="w")
        self._label(panel, "Selecciona cómo quieres visualizar PromptBox.", 9, self.c["muted"]).pack(anchor="w", pady=(4, 18))
        self.theme_var = tk.StringVar(value=self.theme_name)
        choices = tk.Frame(panel, bg=self.c["panel"])
        choices.pack(anchor="w")
        for value, title, desc in (("dark", "Oscuro", "Azul noche y superficies profundas"),
                                   ("light", "Claro", "Blanco y tonos hielo"),
                                   ("system", "Automático", "Seguir el tema de Windows")):
            box = tk.Radiobutton(choices, text=f"{title}\n{desc}", variable=self.theme_var, value=value,
                                 command=self.change_theme, bg=self.c["surface"], fg=self.c["text"],
                                 selectcolor=self.c["selected"], activebackground=self.c["surface"],
                                 activeforeground=self.c["text"], padx=18, pady=14, justify="left",
                                 font=("Segoe UI", 9))
            box.pack(side="left", padx=(0, 10))
        ttk.Separator(panel).pack(fill="x", pady=22)
        self.confirm_var = tk.BooleanVar(value=self.settings.get("confirm_delete", True))
        tk.Checkbutton(panel, text="Confirmar antes de eliminar prompts",
                       variable=self.confirm_var, command=self.save_preferences,
                       bg=self.c["panel"], fg=self.c["text"], selectcolor=self.c["surface"],
                       activebackground=self.c["panel"], activeforeground=self.c["text"],
                       font=("Segoe UI", 9)).pack(anchor="w")
        self._label(panel, "Los cambios de apariencia se aplican inmediatamente.", 8, self.c["muted"]).pack(anchor="w", pady=(20, 0))

    def _view_about(self):
        self._page_header("Acerca de PromptBox", "Información del producto y créditos.")
        panel = self._panel(self.content_host, padx=30, pady=30)
        panel.pack(fill="both", expand=True, padx=26, pady=(0, 24))
        try:
            logo = tk.PhotoImage(file=str(resource_path("promptbox_logo.png")))
            logo = logo.subsample(max(1, logo.width() // 180), max(1, logo.width() // 180))
            self.about_logo = logo
            tk.Label(panel, image=logo, bg=self.c["panel"]).pack(pady=(12, 12))
        except Exception:
            self._label(panel, "✦  PromptBox", 25, self.c["primary"], bold=True).pack(pady=18)
        self._label(panel, "PromptBox", 22, bold=True).pack()
        self._label(panel, f"Versión {APP_VERSION}", 10, self.c["primary"], bold=True).pack(pady=(5, 8))
        self._label(panel, "Tu biblioteca personal de instrucciones para IA.", 10, self.c["muted"]).pack()
        details = self._panel(panel, padx=18, pady=14)
        details.pack(pady=24, fill="x")
        for key, value in (("Versión", APP_VERSION), ("Compilación", datetime.now().strftime("%d/%m/%Y")),
                           ("Almacenamiento", "SQLite local"), ("Créditos", "NICOLUSA")):
            line = tk.Frame(details, bg=self.c["panel"])
            line.pack(fill="x", pady=5)
            self._label(line, key, 9, self.c["muted"]).pack(side="left")
            self._label(line, value, 9, bold=True).pack(side="right")

    def new_prompt(self):
        dialog = PromptDialog(self, sorted(set(self.store.categories() + self.settings.get("custom_categories", []))), self.c)
        self.wait_window(dialog)
        if dialog.result:
            self.store.save(*dialog.result)
            self.show_view("library")
            self.status_var.set("Prompt creado correctamente")

    def edit_prompt(self):
        if not self.selected_id:
            messagebox.showinfo("Selecciona un prompt", "Elige un prompt de la lista.")
            return
        prompt = self.store.get(self.selected_id)
        if not prompt:
            return
        dialog = PromptDialog(self, sorted(set(self.store.categories() + self.settings.get("custom_categories", []))), self.c, prompt)
        self.wait_window(dialog)
        if dialog.result:
            self.store.save(*dialog.result, prompt_id=self.selected_id)
            self.show_view(self.current_view)
            self.status_var.set("Cambios guardados")

    def delete_prompt(self):
        if not self.selected_id:
            messagebox.showinfo("Selecciona un prompt", "Elige un prompt de la lista.")
            return
        prompt = self.store.get(self.selected_id)
        if self.settings.get("confirm_delete", True) and not messagebox.askyesno(
                "Eliminar prompt", f"¿Eliminar «{prompt['title']}»? Esta acción no se puede deshacer."):
            return
        self.store.delete(self.selected_id)
        self.selected_id = None
        self.show_view(self.current_view)
        self.status_var.set("Prompt eliminado")

    def copy_prompt(self):
        if not self.selected_id:
            messagebox.showinfo("Selecciona un prompt", "Elige un prompt para copiarlo.")
            return
        prompt = self.store.get(self.selected_id)
        self.clipboard_clear()
        self.clipboard_append(prompt["content"])
        self.update()
        self.status_var.set("Prompt copiado al portapapeles")

    def new_category(self):
        name = simpledialog.askstring("Nueva categoría", "Nombre de la categoría:", parent=self)
        if not name or not name.strip():
            return
        name = name.strip()
        if name.casefold() in {item.casefold() for item in (self.store.categories() + self.settings.get("custom_categories", []))}:
            messagebox.showwarning("Categoría existente", "Ya existe esa categoría.")
            return
        # Category names are represented by prompt rows; create a placeholder-less category
        # in settings metadata so it persists independently.
        custom = self.settings.setdefault("custom_categories", [])
        custom.append(name)
        custom.sort(key=str.casefold)
        self._save_settings()
        self.show_view("categories")

    def rename_category(self):
        selection = self.category_tree.selection()
        if not selection:
            messagebox.showinfo("Selecciona categoría", "Selecciona una categoría con prompts para renombrar.")
            return
        old = selection[0]
        from tkinter import simpledialog
        new = simpledialog.askstring("Renombrar categoría", "Nuevo nombre:", initialvalue=old, parent=self)
        if not new or not new.strip() or new.strip() == old:
            return
        new = new.strip()
        self.store.rename_category(old, new)
        custom = self.settings.setdefault("custom_categories", [])
        if old in custom:
            custom.remove(old)
        if new not in DEFAULT_CATEGORIES:
            custom.append(new)
        self._save_settings()
        self.show_view("categories")

    def remove_category(self):
        selection = self.category_tree.selection()
        if not selection:
            messagebox.showinfo("Selecciona categoría", "Selecciona una categoría.")
            return
        category = selection[0]
        if category == "General":
            messagebox.showwarning("Acción no permitida", "La categoría General no se puede eliminar.")
            return
        if not messagebox.askyesno("Eliminar categoría", f"Los prompts de «{category}» pasarán a General. ¿Continuar?"):
            return
        self.store.delete_category(category)
        custom = self.settings.setdefault("custom_categories", [])
        if category in custom:
            custom.remove(category)
        self._save_settings()
        self.show_view("categories")

    def change_theme(self):
        self.theme_name = self.theme_var.get()
        self.settings["theme"] = self.theme_name
        self._save_settings()
        self.c = self._colors()
        self._apply_styles()
        self._rebuild_shell()

    def save_preferences(self):
        self.settings["confirm_delete"] = bool(self.confirm_var.get())
        self._save_settings()

    def _rebuild_shell(self):
        for child in self.winfo_children():
            child.destroy()
        self.build_shell()
        self.show_view(self.current_view)

    def export_data(self):
        path = filedialog.asksaveasfilename(title="Exportar biblioteca", defaultextension=".json",
            filetypes=[("Archivo JSON", "*.json")], initialfile="promptbox-respaldo.json")
        if not path:
            return
        try:
            self.store.export_data(path)
            messagebox.showinfo("Exportación completa", "Tu biblioteca se exportó correctamente.")
            self.status_var.set("Respaldo exportado")
        except Exception as exc:
            messagebox.showerror("Error al exportar", str(exc))

    def import_data(self):
        path = filedialog.askopenfilename(title="Importar biblioteca", filetypes=[("Archivo JSON", "*.json")])
        if not path:
            return
        if not messagebox.askyesno("Confirmar importación",
                                   "Los prompts del archivo se agregarán a tu biblioteca. ¿Continuar?"):
            return
        try:
            count = self.store.import_data(path)
            self.show_view("library")
            messagebox.showinfo("Importación completa", f"Se importaron {count} prompt(s).")
            self.status_var.set(f"{count} prompt(s) importados")
        except Exception as exc:
            messagebox.showerror("Error al importar", f"No se pudo importar el archivo:\n{exc}")

    def on_close(self):
        self.store.conn.close()
        self.destroy()


if __name__ == "__main__":
    PromptBoxApp().mainloop()
