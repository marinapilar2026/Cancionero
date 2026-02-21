import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from tkinter import END, BOTH, LEFT, RIGHT, X, Y, DISABLED, NORMAL
import tkinter as tk
from tkinter import messagebox


def discover_project_root() -> Path:
    candidates = []

    # Prefer where user launched the app from.
    candidates.append(Path.cwd())

    # When running as EXE, this points to the EXE location.
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        candidates.append(exe_dir)
        candidates.append(exe_dir.parent)

    # When running as .py script.
    script_dir = Path(__file__).resolve().parent
    candidates.append(script_dir)
    candidates.append(script_dir.parent)

    seen = set()
    for base in candidates:
        try:
            base = base.resolve()
        except Exception:
            continue
        if base in seen:
            continue
        seen.add(base)
        if (base / "songs" / "index.json").exists():
            return base

    raise RuntimeError(
        "No existe songs/index.json. Ejecuta el editor dentro de la carpeta del proyecto Cancionero."
    )


PROJECT_ROOT = discover_project_root()
SONGS_DIR = PROJECT_ROOT / "songs"
INDEX_PATH = SONGS_DIR / "index.json"


def slugify(value: str) -> str:
    value = value.lower()
    value = (
        value.replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ü", "u")
        .replace("ñ", "n")
    )
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "cancion"


def find_git_executable() -> str:
    candidates = [
        "git",
        r"C:\Program Files\Git\cmd\git.exe",
        r"C:\Program Files\Git\bin\git.exe",
    ]
    for candidate in candidates:
        if candidate == "git":
            if shutil.which("git"):
                return "git"
            continue
        if Path(candidate).exists():
            return candidate
    raise RuntimeError("No se encontro Git en la PC.")


class CancioneroEditor(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Editor de Cancionero")
        self.geometry("1100x700")
        self.minsize(900, 560)

        self.git_exe = find_git_executable()
        self.songs = []
        self.current_index = None

        self._build_ui()
        self._load_data()

    def _build_ui(self) -> None:
        top = tk.Frame(self, padx=12, pady=8)
        top.pack(fill=X)

        tk.Label(top, text="Buscar:").pack(side=LEFT)
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(top, textvariable=self.search_var, width=40, font=("Segoe UI", 11))
        search_entry.pack(side=LEFT, padx=8)
        search_entry.bind("<KeyRelease>", lambda _e: self._refresh_list())

        btn_new = tk.Button(top, text="Nueva cancion", width=14, command=self.new_song)
        btn_new.pack(side=LEFT, padx=4)
        btn_delete = tk.Button(top, text="Borrar cancion", width=14, command=self.delete_song)
        btn_delete.pack(side=LEFT, padx=4)
        btn_save = tk.Button(top, text="Guardar y subir", width=16, command=self.save_current_song)
        btn_save.pack(side=LEFT, padx=8)

        main = tk.Frame(self, padx=12, pady=8)
        main.pack(fill=BOTH, expand=True)

        left_panel = tk.Frame(main)
        left_panel.pack(side=LEFT, fill=Y)

        self.listbox = tk.Listbox(left_panel, width=38, font=("Segoe UI", 11))
        self.listbox.pack(side=LEFT, fill=Y)
        self.listbox.bind("<<ListboxSelect>>", self.on_song_selected)

        scroll = tk.Scrollbar(left_panel, orient="vertical", command=self.listbox.yview)
        scroll.pack(side=RIGHT, fill=Y)
        self.listbox.config(yscrollcommand=scroll.set)

        right_panel = tk.Frame(main)
        right_panel.pack(side=LEFT, fill=BOTH, expand=True, padx=(14, 0))

        meta = tk.Frame(right_panel)
        meta.pack(fill=X)

        tk.Label(meta, text="Numero", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w")
        self.num_var = tk.StringVar()
        tk.Entry(meta, textvariable=self.num_var, width=8, font=("Segoe UI", 11)).grid(row=1, column=0, padx=(0, 12))

        tk.Label(meta, text="Titulo", font=("Segoe UI", 10)).grid(row=0, column=1, sticky="w")
        self.title_var = tk.StringVar()
        tk.Entry(meta, textvariable=self.title_var, font=("Segoe UI", 11)).grid(row=1, column=1, sticky="ew")
        meta.columnconfigure(1, weight=1)

        tk.Label(right_panel, text="Letra", font=("Segoe UI", 10)).pack(anchor="w", pady=(10, 4))
        self.text = tk.Text(right_panel, font=("Segoe UI", 12), wrap="word", undo=True)
        self.text.pack(fill=BOTH, expand=True)

        status_frame = tk.Frame(self, padx=12, pady=8)
        status_frame.pack(fill=X)
        self.status_var = tk.StringVar(value="Listo.")
        tk.Label(status_frame, textvariable=self.status_var, anchor="w", fg="#444").pack(fill=X)

    def _set_status(self, message: str) -> None:
        self.status_var.set(message)
        self.update_idletasks()

    def _load_data(self) -> None:
        if not INDEX_PATH.exists():
            messagebox.showerror("Error", f"No existe {INDEX_PATH}")
            self.destroy()
            return

        with INDEX_PATH.open("r", encoding="utf-8-sig") as f:
            self.songs = json.load(f)

        for song in self.songs:
            song_file = SONGS_DIR / song["file"]
            if song_file.exists():
                content = song_file.read_text(encoding="utf-8-sig")
            else:
                content = ""
            song["body"] = content.replace("\ufeff", "").rstrip()

        self.songs.sort(key=lambda s: (int(s.get("number", 0)), str(s.get("title", ""))))
        self._refresh_list()
        if self.songs:
            self.current_index = 0
            self._load_song_to_editor(0)

    def _refresh_list(self) -> None:
        query = self.search_var.get().strip().lower()
        self.listbox.delete(0, END)
        self.filtered_indices = []

        for idx, song in enumerate(self.songs):
            label = f'{song["number"]}. {song["title"]}'
            haystack = f'{label}\n{song.get("body", "")}'.lower()
            if query and query not in haystack:
                continue
            self.filtered_indices.append(idx)
            self.listbox.insert(END, label)

        if self.filtered_indices and self.current_index in self.filtered_indices:
            visible_index = self.filtered_indices.index(self.current_index)
            self.listbox.selection_set(visible_index)

    def _load_song_to_editor(self, index: int) -> None:
        if index is None or index < 0 or index >= len(self.songs):
            self.current_index = None
            self.num_var.set("")
            self.title_var.set("")
            self.text.delete("1.0", END)
            return

        self.current_index = index
        song = self.songs[index]
        self.num_var.set(str(song["number"]))
        self.title_var.set(song["title"])
        self.text.delete("1.0", END)
        self.text.insert("1.0", song.get("body", ""))

    def on_song_selected(self, _event=None) -> None:
        if not self.listbox.curselection():
            return
        selected_visible = self.listbox.curselection()[0]
        song_index = self.filtered_indices[selected_visible]
        self._load_song_to_editor(song_index)

    def new_song(self) -> None:
        next_number = max([int(s["number"]) for s in self.songs], default=0) + 1
        new = {
            "id": max([int(s["id"]) for s in self.songs], default=0) + 1,
            "number": next_number,
            "title": "NUEVA CANCION",
            "file": "",
            "body": "",
        }
        self.songs.append(new)
        self.songs.sort(key=lambda s: (int(s["number"]), str(s["title"])))
        self._refresh_list()
        idx = self.songs.index(new)
        self._load_song_to_editor(idx)
        self._refresh_list()
        self._set_status("Nueva cancion creada. Edita y toca Guardar y subir.")

    def delete_song(self) -> None:
        if self.current_index is None:
            return

        song = self.songs[self.current_index]
        confirm = messagebox.askyesno("Confirmar", f'Borrar "{song["number"]}. {song["title"]}"?')
        if not confirm:
            return

        old_file = song.get("file", "")
        if old_file:
            file_path = SONGS_DIR / old_file
            if file_path.exists():
                file_path.unlink()

        del self.songs[self.current_index]
        self._save_all_and_push("Borra cancion")
        self._refresh_list()
        if self.songs:
            self._load_song_to_editor(0)
        else:
            self._load_song_to_editor(None)
        self._set_status("Cancion borrada y subida a GitHub.")

    def save_current_song(self) -> None:
        if self.current_index is None:
            return

        raw_num = self.num_var.get().strip()
        if not raw_num.isdigit():
            messagebox.showerror("Numero invalido", "El numero debe ser un entero.")
            return

        title = self.title_var.get().strip()
        if not title:
            messagebox.showerror("Titulo invalido", "El titulo no puede estar vacio.")
            return

        song = self.songs[self.current_index]
        old_file = song.get("file", "")

        song["number"] = int(raw_num)
        song["title"] = title
        song["body"] = self.text.get("1.0", END).rstrip()

        base_file = f'{song["number"]:03d}-{slugify(song["title"])}.txt'
        candidate = base_file
        suffix = 2
        used = {s.get("file") for i, s in enumerate(self.songs) if i != self.current_index}
        while candidate in used:
            candidate = base_file.replace(".txt", f"-{suffix}.txt")
            suffix += 1
        song["file"] = candidate

        if old_file and old_file != candidate:
            old_path = SONGS_DIR / old_file
            if old_path.exists():
                old_path.unlink()

        self._save_all_and_push("Actualiza cancion")
        self.songs.sort(key=lambda s: (int(s["number"]), str(s["title"])))
        self._refresh_list()
        self.current_index = next((i for i, s in enumerate(self.songs) if s["id"] == song["id"]), None)
        if self.current_index is not None:
            self._load_song_to_editor(self.current_index)
        self._set_status("Guardado, commit y push completados.")

    def _write_files(self) -> None:
        SONGS_DIR.mkdir(parents=True, exist_ok=True)

        for song in self.songs:
            file_name = song.get("file", "").strip()
            if not file_name:
                file_name = f'{int(song["number"]):03d}-{slugify(song["title"])}.txt'
                song["file"] = file_name
            path = SONGS_DIR / file_name
            path.write_text((song.get("body", "").rstrip() + "\n"), encoding="utf-8")

        index_payload = []
        for i, song in enumerate(self.songs, start=1):
            song["id"] = i
            index_payload.append(
                {
                    "id": i,
                    "number": int(song["number"]),
                    "title": song["title"],
                    "file": song["file"],
                }
            )

        with INDEX_PATH.open("w", encoding="utf-8") as f:
            json.dump(index_payload, f, ensure_ascii=False, indent=2)

    def _run_git(self, *args: str, allow_fail: bool = False) -> subprocess.CompletedProcess:
        cmd = [self.git_exe, *args]
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if not allow_fail and result.returncode != 0:
            raise RuntimeError((result.stderr or result.stdout).strip() or f"Error ejecutando: {' '.join(cmd)}")
        return result

    def _save_all_and_push(self, action: str) -> None:
        try:
            self._set_status("Guardando archivos...")
            self._write_files()

            self._set_status("Creando commit...")
            self._run_git("add", "-A", "songs")

            status = self._run_git("status", "--porcelain")
            if not status.stdout.strip():
                self._set_status("No habia cambios para subir.")
                return

            stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            self._run_git("commit", "-m", f"{action} ({stamp})")

            self._set_status("Subiendo a GitHub...")
            self._run_git("push", "origin", "main")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))
            self._set_status("Hubo un error. Los archivos locales si quedaron guardados.")


def main() -> None:
    try:
        app = CancioneroEditor()
        app.mainloop()
    except Exception as exc:
        messagebox.showerror("Error fatal", str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
