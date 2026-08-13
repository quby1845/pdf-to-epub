"""Turkish desktop interface for PDF to EPUB OCR."""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from pdf_to_epub.converter import ConversionOptions, ConversionResult, check_runtime, convert_pdf
from pdf_to_epub.desktop import (
    DEFAULT_MODEL_LABEL,
    MODEL_LABELS,
    build_conversion_options,
    default_epub_path,
    friendly_error,
    friendly_progress,
)


class PdfToEpubApp:
    """Small, dependency-free desktop shell around the conversion pipeline."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("PDF → EPUB Dönüştürücü")
        self.root.geometry("760x620")
        self.root.minsize(680, 560)
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.last_output: Path | None = None

        self.pdf_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.title_var = tk.StringVar()
        self.author_var = tk.StringVar(value="Bilinmiyor")
        self.language_var = tk.StringVar(value="tr")
        self.model_var = tk.StringVar(value=DEFAULT_MODEL_LABEL)
        self.status_var = tk.StringVar(value="Bir PDF seçerek başlayın.")

        self._build_ui()
        self.root.after(100, self._poll_events)

    def _build_ui(self) -> None:
        style = ttk.Style()
        style.configure("Title.TLabel", font=("Segoe UI", 20, "bold"))
        style.configure("Hint.TLabel", foreground="#555555")
        style.configure("Action.TButton", font=("Segoe UI", 11, "bold"), padding=(12, 9))

        frame = ttk.Frame(self.root, padding=24)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="PDF → EPUB Dönüştürücü", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            frame,
            text=(
                "Belgeniz bilgisayarınızdan ayrılmaz. İlk dönüşüm model indirdiği için "
                "uzun sürebilir."
            ),
            style="Hint.TLabel",
        ).pack(anchor="w", pady=(4, 22))

        form = ttk.Frame(frame)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)

        self._row(form, 0, "PDF dosyası", self.pdf_var, "PDF seç", self._choose_pdf)
        self._row(form, 1, "Kitap adı", self.title_var)
        self._row(form, 2, "Yazar", self.author_var)

        ttk.Label(form, text="Dil").grid(row=3, column=0, sticky="w", padx=(0, 12), pady=7)
        ttk.Entry(form, textvariable=self.language_var, width=10).grid(
            row=3, column=1, sticky="w", pady=7
        )

        ttk.Label(form, text="OCR modeli").grid(row=4, column=0, sticky="w", padx=(0, 12), pady=7)
        ttk.Combobox(
            form,
            textvariable=self.model_var,
            values=list(MODEL_LABELS),
            state="readonly",
        ).grid(row=4, column=1, sticky="ew", pady=7)

        self._row(
            form,
            5,
            "EPUB konumu",
            self.output_var,
            "Konum seç",
            self._choose_output,
        )

        controls = ttk.Frame(frame)
        controls.pack(fill="x", pady=(22, 12))
        self.convert_button = ttk.Button(
            controls,
            text="EPUB'a Dönüştür",
            style="Action.TButton",
            command=self._start_conversion,
        )
        self.convert_button.pack(side="left")
        self.folder_button = ttk.Button(
            controls, text="Çıktı klasörünü aç", command=self._open_output_folder, state="disabled"
        )
        self.folder_button.pack(side="left", padx=10)

        self.progress = ttk.Progressbar(frame, mode="indeterminate")
        self.progress.pack(fill="x", pady=(2, 10))
        ttk.Label(frame, textvariable=self.status_var, wraplength=690).pack(anchor="w")

        ttk.Separator(frame).pack(fill="x", pady=18)
        ttk.Label(
            frame,
            text=(
                "İpucu: Ekran kartı belleği hatası alırsanız OCR modelini base veya small "
                "olarak seçin. Kaliteli ve temiz taramalar daha iyi sonuç verir."
            ),
            style="Hint.TLabel",
            wraplength=690,
        ).pack(anchor="w")

    def _row(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        button_text: str | None = None,
        command: Callable[[], None] | None = None,
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=7)
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", pady=7)
        if button_text:
            ttk.Button(parent, text=button_text, command=command).grid(
                row=row, column=2, padx=(10, 0), pady=7
            )

    def _choose_pdf(self) -> None:
        selected = filedialog.askopenfilename(
            title="Dönüştürülecek PDF'yi seçin", filetypes=[("PDF dosyaları", "*.pdf")]
        )
        if not selected:
            return
        pdf_path = Path(selected)
        self.pdf_var.set(str(pdf_path))
        self.title_var.set(pdf_path.stem)
        self.output_var.set(str(default_epub_path(pdf_path, pdf_path.stem, self.author_var.get())))
        self.status_var.set("PDF hazır. İsterseniz kitap bilgilerini düzenleyin.")

    def _choose_output(self) -> None:
        initial = (
            Path(self.output_var.get()) if self.output_var.get() else Path.home() / "kitap.epub"
        )
        selected = filedialog.asksaveasfilename(
            title="EPUB dosyasını kaydet",
            defaultextension=".epub",
            filetypes=[("EPUB dosyaları", "*.epub")],
            initialdir=initial.parent,
            initialfile=initial.name,
        )
        if selected:
            self.output_var.set(selected)

    def _start_conversion(self) -> None:
        pdf_path = Path(self.pdf_var.get())
        output_path = Path(self.output_var.get())
        try:
            options = build_conversion_options(
                pdf_path=pdf_path,
                epub_path=output_path,
                title=self.title_var.get(),
                author=self.author_var.get(),
                language=self.language_var.get(),
                model_label=self.model_var.get(),
                overwrite=False,
            )
        except ValueError as error:
            messagebox.showerror("Eksik bilgi", str(error))
            return

        if options.epub_path.exists():
            overwrite = messagebox.askyesno(
                "Dosya zaten var", "Aynı isimde bir EPUB var. Üzerine yazılsın mı?"
            )
            if not overwrite:
                return
            options = replace(options, overwrite=True)

        self.convert_button.configure(state="disabled")
        self.folder_button.configure(state="disabled")
        self.progress.start(12)
        self.status_var.set("Sistem gereksinimleri kontrol ediliyor…")
        threading.Thread(target=self._convert, args=(options,), daemon=True).start()

    def _convert(self, options: ConversionOptions) -> None:
        try:
            warning = check_runtime()
            if warning:
                self.events.put(("progress", f"Uyarı: {friendly_error(RuntimeError(warning))}"))
            result = convert_pdf(
                options,
                progress=lambda message: self.events.put(("progress", friendly_progress(message))),
            )
            self.events.put(("success", result))
        except Exception as error:
            self.events.put(("error", friendly_error(error)))

    def _poll_events(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "progress":
                    self.status_var.set(str(payload))
                elif kind == "success":
                    self._finish_success(payload)
                elif kind == "error":
                    self._finish_error(str(payload))
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

    def _finish_success(self, result: ConversionResult) -> None:
        self.progress.stop()
        self.convert_button.configure(state="normal")
        self.last_output = Path(result.epub_path)
        self.folder_button.configure(state="normal")
        self.status_var.set(
            f"Tamamlandı: {result.epub_path} ({result.elapsed_seconds / 60:.1f} dakika)"
        )
        messagebox.showinfo("EPUB hazır", f"Dosya oluşturuldu:\n\n{result.epub_path}")

    def _finish_error(self, message: str) -> None:
        self.progress.stop()
        self.convert_button.configure(state="normal")
        self.status_var.set(f"Dönüşüm tamamlanamadı: {message}")
        messagebox.showerror("Dönüşüm hatası", message)

    def _open_output_folder(self) -> None:
        if self.last_output is None:
            return
        folder = self.last_output.parent
        if sys.platform == "win32":
            os.startfile(folder)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])


def main() -> None:
    root = tk.Tk()
    PdfToEpubApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
