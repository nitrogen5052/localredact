"""localredact for Windows: pick files in a File Explorer dialog, get redacted copies in Downloads."""
import logging
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "core")]
from redact_core import read_terms, redact_with  # noqa: E402
import engine_torch as engine  # noqa: E402

DATA_DIR = Path(os.environ.get("LOCALREDACT_HOME", Path(os.environ.get("LOCALAPPDATA", Path.home())) / "localredact"))
LIST_PATH = DATA_DIR / "Always redact.txt"
DATA_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=DATA_DIR / "localredact.log", level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")  # paths and errors only, never content


def downloads_dir():
    """The user's real Downloads folder (it can be moved), falling back to ~/Downloads."""
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            from uuid import UUID

            class GUID(ctypes.Structure):
                _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                            ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]

            u = UUID("374DE290-123F-4565-9164-39C4925E467B")  # FOLDERID_Downloads
            guid = GUID(u.fields[0], u.fields[1], u.fields[2], (ctypes.c_ubyte * 8)(*u.bytes[8:]))
            p = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(p)) == 0:
                path = p.value
                ctypes.windll.ole32.CoTaskMemFree(p)
                return Path(path)
        except Exception:
            logging.exception("Downloads folder lookup failed; using ~/Downloads")
    return Path.home() / "Downloads"


def reveal(paths):
    if sys.platform == "win32":
        subprocess.Popen(["explorer", "/select,", str(paths[-1])])
        for p in paths:
            os.startfile(p)  # opens in the default text editor
    else:  # lets the app be tried on a Mac during development
        subprocess.Popen(["open", "-R", str(paths[-1])])


def run(files, ui):
    """Worker thread: posts ('status', text) / ('step',) / ('done', outputs, failures) to ui."""
    out_dir = downloads_dir()
    outputs, failures = [], []
    try:
        # A list that exists but can't be read must stop the run, never be skipped.
        terms = read_terms(LIST_PATH) if LIST_PATH.exists() else []
        ui.put(("status", "Loading the model…"))
        redactor = engine.build_redactor()
        speed = "GPU" if engine.device_name() == "cuda" else "CPU — long files can take several minutes"
        for i, f in enumerate(files, 1):
            ui.put(("status", f"Redacting {Path(f).name} ({i} of {len(files)}) · {speed}"))
            logging.info("redact %s", f)
            try:
                out = engine.output_path(f, out_dir)
                out.write_text(redact_with(redactor, engine.extract_text(f), terms), encoding="utf-8")
                outputs.append(out)
            except Exception as e:
                logging.exception("failed %s", f)
                failures.append(f"{Path(f).name}: {e}")
            ui.put(("step",))
    except Exception as e:
        logging.exception("setup failed")
        failures.append(f"localredact could not start: {e}")
    ui.put(("done", outputs, failures))


def finish(root, outputs, failures):
    root.withdraw()
    if outputs:
        reveal(outputs)
    if failures:
        messagebox.showerror("localredact", "\n\n".join(failures))
    elif outputs:
        messagebox.showinfo("localredact", f"{len(outputs)} file(s) saved to Downloads.\n\n"
                            "Read the result before sharing it: redaction is not a guarantee.")
    root.destroy()


def main():
    root = tk.Tk()
    root.withdraw()
    types = [("Documents", " ".join(f"*{e}" for e in sorted(engine.SUPPORTED_EXTS)))]
    files = filedialog.askopenfilenames(title="Choose file(s) to redact", initialdir=downloads_dir(), filetypes=types)
    if not files:
        root.destroy()
        return
    root.title("localredact")
    root.resizable(False, False)
    status = tk.StringVar(value="Starting…")
    frame = ttk.Frame(root, padding=16)
    frame.pack()
    ttk.Label(frame, textvariable=status, width=60).pack(anchor="w")
    bar = ttk.Progressbar(frame, maximum=len(files), length=420)
    bar.pack(pady=(10, 4))
    ttk.Label(frame, text="Keep this window open. Results go to your Downloads folder.").pack(anchor="w")
    root.deiconify()
    ui = queue.Queue()

    def poll():
        while True:
            try:
                msg = ui.get_nowait()
            except queue.Empty:
                break
            if msg[0] == "status":
                status.set(msg[1])
            elif msg[0] == "step":
                bar.step(1)
            else:
                finish(root, msg[1], msg[2])
                return
        root.after(200, poll)

    threading.Thread(target=run, args=(files, ui), daemon=True).start()
    poll()
    root.mainloop()


if __name__ == "__main__":
    main()
