"""Modern Turkish desktop interface for PDF to EPUB OCR."""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from pdf_to_epub.converter import (
    ConversionOptions,
    ConversionProgress,
    ConversionResult,
    check_runtime,
    convert_pdf,
)
from pdf_to_epub.desktop import (
    DEFAULT_MODEL_LABEL,
    MODEL_LABELS,
    build_conversion_options,
    default_epub_path,
    friendly_error,
    friendly_progress,
    load_theme_preference,
    model_description,
    progress_stage,
    save_theme_preference,
)


@dataclass(frozen=True)
class ThemePalette:
    background: str
    card: str
    field: str
    ink: str
    muted: str
    border: str
    primary: str
    primary_hover: str
    success: str
    success_bg: str
    error: str
    error_bg: str
    header: str
    header_muted: str
    privacy_fg: str
    privacy_bg: str
    progress_trough: str
    stage_inactive: str
    status_bg: str
    secondary: str
    secondary_hover: str


THEMES = {
    "light": ThemePalette(
        background="#F3F6FA",
        card="#FFFFFF",
        field="#FFFFFF",
        ink="#172033",
        muted="#667085",
        border="#DDE3EC",
        primary="#5B4CF0",
        primary_hover="#4B3ED1",
        success="#18864B",
        success_bg="#EAF8F0",
        error="#C9362B",
        error_bg="#FFF0EE",
        header="#172033",
        header_muted="#C7D0E0",
        privacy_fg="#9BE6B7",
        privacy_bg="#243047",
        progress_trough="#E7EAF0",
        stage_inactive="#98A2B3",
        status_bg="#F7F8FA",
        secondary="#EEF0F5",
        secondary_hover="#E2E6ED",
    ),
    "dark": ThemePalette(
        background="#0F1420",
        card="#181F2E",
        field="#20293A",
        ink="#F3F6FC",
        muted="#A8B3C5",
        border="#303B50",
        primary="#7C6FF7",
        primary_hover="#6B5DE7",
        success="#62DB98",
        success_bg="#173527",
        error="#FF8178",
        error_bg="#3A2024",
        header="#0A0F19",
        header_muted="#A6B2C4",
        privacy_fg="#86E5AC",
        privacy_bg="#1A2C27",
        progress_trough="#293347",
        stage_inactive="#758198",
        status_bg="#20293A",
        secondary="#293448",
        secondary_hover="#36435A",
    ),
}


class PdfToEpubApp:
    """A friendly, console-free desktop shell around the conversion pipeline."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("PDF to EPUB OCR")
        self.root.geometry("940x800")
        self.root.minsize(760, 620)
        self.theme_name = load_theme_preference()
        self.theme = THEMES[self.theme_name]
        self.root.configure(background=self.theme.background)
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.last_output: Path | None = None
        self.stage_labels: list[tk.Label] = []
        self.active_stage = -1
        self.status_kind = "neutral"
        self.converting = False

        self.pdf_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.title_var = tk.StringVar()
        self.author_var = tk.StringVar(value="Bilinmiyor")
        self.language_var = tk.StringVar(value="tr")
        self.model_var = tk.StringVar(value=DEFAULT_MODEL_LABEL)
        self.model_help_var = tk.StringVar(value=model_description(DEFAULT_MODEL_LABEL))
        self.status_var = tk.StringVar(value="Bir PDF seçerek başlayın.")

        self._configure_styles()
        self._build_ui()
        self.root.after(0, self._apply_windows_title_bar_theme)
        self.root.after(100, self._poll_events)

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        theme = self.theme
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure(
            "App.TEntry",
            fieldbackground=theme.field,
            foreground=theme.ink,
            bordercolor=theme.border,
            lightcolor=theme.border,
            darkcolor=theme.border,
            insertcolor=theme.ink,
            padding=10,
        )
        style.map("App.TEntry", bordercolor=[("focus", theme.primary)])
        style.configure(
            "App.TCombobox",
            fieldbackground=theme.field,
            background=theme.field,
            foreground=theme.ink,
            bordercolor=theme.border,
            lightcolor=theme.border,
            darkcolor=theme.border,
            padding=9,
            arrowcolor=theme.ink,
        )
        style.map(
            "App.TCombobox",
            bordercolor=[("focus", theme.primary)],
            fieldbackground=[("readonly", theme.field)],
            selectbackground=[("readonly", theme.field)],
            selectforeground=[("readonly", theme.ink)],
        )
        style.configure(
            "Primary.Horizontal.TProgressbar",
            troughcolor=theme.progress_trough,
            background=theme.primary,
            lightcolor=theme.primary,
            darkcolor=theme.primary,
            bordercolor=theme.progress_trough,
            thickness=8,
        )
        style.configure(
            "App.Vertical.TScrollbar",
            troughcolor=theme.background,
            background=theme.secondary,
            bordercolor=theme.background,
            lightcolor=theme.secondary,
            darkcolor=theme.secondary,
            arrowcolor=theme.ink,
        )
        style.map(
            "App.Vertical.TScrollbar",
            background=[("active", theme.secondary_hover)],
            arrowcolor=[("active", theme.ink)],
        )

    def _build_ui(self) -> None:
        theme = self.theme
        outer = tk.Frame(self.root, background=theme.background)
        outer.pack(fill="both", expand=True)
        self.ui_root = outer

        self._build_header(outer)

        body = tk.Frame(outer, background=theme.background)
        body.pack(fill="both", expand=True)
        self.content_canvas = tk.Canvas(
            body,
            background=theme.background,
            highlightthickness=0,
            borderwidth=0,
        )
        scrollbar = ttk.Scrollbar(
            body,
            orient="vertical",
            command=self.content_canvas.yview,
            style="App.Vertical.TScrollbar",
        )
        self.content_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.content_canvas.pack(side="left", fill="both", expand=True)

        content = tk.Frame(
            self.content_canvas,
            background=theme.background,
            padx=28,
            pady=18,
        )
        self.content_window = self.content_canvas.create_window((0, 0), window=content, anchor="nw")
        content.bind("<Configure>", self._update_scroll_region)
        self.content_canvas.bind("<Configure>", self._resize_scroll_content)
        self.content_canvas.bind_all("<MouseWheel>", self._scroll_content)

        self._build_file_card(content)
        self._build_details_card(content)
        self._build_action_area(content)

    def _update_scroll_region(self, _event: tk.Event[tk.Misc]) -> None:
        self.content_canvas.configure(scrollregion=self.content_canvas.bbox("all"))

    def _resize_scroll_content(self, event: tk.Event[tk.Misc]) -> None:
        self.content_canvas.itemconfigure(self.content_window, width=event.width)

    def _scroll_content(self, event: tk.Event[tk.Misc]) -> None:
        if self.content_canvas.bbox("all") is None:
            return
        content_height = self.content_canvas.bbox("all")[3]
        if content_height > self.content_canvas.winfo_height():
            self.content_canvas.yview_scroll(int(-event.delta / 120), "units")

    def _build_header(self, parent: tk.Widget) -> None:
        theme = self.theme
        header = tk.Frame(parent, background=theme.header, padx=30, pady=22)
        header.pack(fill="x")

        brand = tk.Frame(header, background=theme.header)
        brand.pack(fill="x")

        mark = tk.Label(
            brand,
            text="P  →  E",
            font=("Segoe UI", 11, "bold"),
            foreground="white",
            background=theme.primary,
            padx=12,
            pady=8,
        )
        mark.pack(side="left", padx=(0, 14))

        titles = tk.Frame(brand, background=theme.header)
        titles.pack(side="left", fill="x", expand=True)
        tk.Label(
            titles,
            text="PDF to EPUB OCR",
            font=("Segoe UI", 20, "bold"),
            foreground="white",
            background=theme.header,
        ).pack(anchor="w")
        tk.Label(
            titles,
            text="Taranmış kitabınızı okunabilir bir e-kitaba dönüştürün",
            font=("Segoe UI", 10),
            foreground=theme.header_muted,
            background=theme.header,
        ).pack(anchor="w", pady=(2, 0))

        privacy = tk.Label(
            brand,
            text="●  Yerel ve gizli",
            font=("Segoe UI", 9, "bold"),
            foreground=theme.privacy_fg,
            background=theme.privacy_bg,
            padx=12,
            pady=7,
        )
        privacy.pack(side="right")

        self.theme_button = tk.Button(
            brand,
            text="Açık tema" if self.theme_name == "dark" else "Koyu tema",
            command=self._toggle_theme,
            font=("Segoe UI", 9, "bold"),
            foreground="white",
            background="#303A50" if self.theme_name == "dark" else "#2A354B",
            activeforeground="white",
            activebackground="#3B4861",
            disabledforeground=theme.header_muted,
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            padx=12,
            pady=7,
            state="disabled" if self.converting else "normal",
        )
        self.theme_button.pack(side="right", padx=(0, 10))

    def _card(self, parent: tk.Widget, *, pady: tuple[int, int]) -> tk.Frame:
        theme = self.theme
        card = tk.Frame(
            parent,
            background=theme.card,
            highlightbackground=theme.border,
            highlightthickness=1,
            padx=20,
            pady=17,
        )
        card.pack(fill="x", pady=pady)
        return card

    def _section_heading(self, parent: tk.Widget, number: str, title: str, hint: str) -> None:
        theme = self.theme
        row = tk.Frame(parent, background=theme.card)
        row.pack(fill="x", pady=(0, 13))
        tk.Label(
            row,
            text=number,
            font=("Segoe UI", 9, "bold"),
            foreground="white",
            background=theme.primary,
            width=3,
            pady=4,
        ).pack(side="left", padx=(0, 10))
        text = tk.Frame(row, background=theme.card)
        text.pack(side="left", fill="x", expand=True)
        tk.Label(
            text,
            text=title,
            font=("Segoe UI", 11, "bold"),
            foreground=theme.ink,
            background=theme.card,
        ).pack(anchor="w")
        tk.Label(
            text,
            text=hint,
            font=("Segoe UI", 9),
            foreground=theme.muted,
            background=theme.card,
        ).pack(anchor="w")

    def _build_file_card(self, parent: tk.Widget) -> None:
        theme = self.theme
        card = self._card(parent, pady=(0, 13))
        self._section_heading(
            card,
            "1",
            "PDF dosyasını seçin",
            "Dosyanız bilgisayarınızdan çıkmaz; işlem tamamen yerel yapılır.",
        )

        picker = tk.Frame(card, background=theme.card)
        picker.pack(fill="x")
        ttk.Entry(picker, textvariable=self.pdf_var, style="App.TEntry").pack(
            side="left", fill="x", expand=True
        )
        self._button(
            picker,
            "PDF seç",
            self._choose_pdf,
            primary=True,
            padx=19,
        ).pack(side="left", padx=(12, 0))

    def _build_details_card(self, parent: tk.Widget) -> None:
        theme = self.theme
        card = self._card(parent, pady=(0, 13))
        self._section_heading(
            card,
            "2",
            "Kitap bilgilerini kontrol edin",
            "Bu bilgiler EPUB kapağında ve e-kitaplığınızda görünür.",
        )

        form = tk.Frame(card, background=theme.card)
        form.pack(fill="x")
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)

        self._field(form, 0, 0, "Kitap adı", self.title_var)
        self._field(form, 0, 1, "Yazar", self.author_var)
        self._field(form, 1, 0, "Dil", self.language_var)

        model_box = tk.Frame(form, background=theme.card)
        model_box.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(8, 0))
        tk.Label(
            model_box,
            text="OCR kalitesi",
            font=("Segoe UI", 9, "bold"),
            foreground=theme.ink,
            background=theme.card,
        ).pack(anchor="w", pady=(0, 5))
        self.model_combo = ttk.Combobox(
            model_box,
            textvariable=self.model_var,
            values=list(MODEL_LABELS),
            state="readonly",
            style="App.TCombobox",
        )
        self.model_combo.pack(fill="x")
        self.model_combo.bind("<<ComboboxSelected>>", self._model_changed)
        tk.Label(
            model_box,
            textvariable=self.model_help_var,
            font=("Segoe UI", 8),
            foreground=theme.muted,
            background=theme.card,
            wraplength=350,
            justify="left",
        ).pack(anchor="w", pady=(5, 0))

        output_box = tk.Frame(card, background=theme.card)
        output_box.pack(fill="x", pady=(14, 0))
        tk.Label(
            output_box,
            text="EPUB'ın kaydedileceği yer",
            font=("Segoe UI", 9, "bold"),
            foreground=theme.ink,
            background=theme.card,
        ).pack(anchor="w", pady=(0, 5))
        output_row = tk.Frame(output_box, background=theme.card)
        output_row.pack(fill="x")
        ttk.Entry(output_row, textvariable=self.output_var, style="App.TEntry").pack(
            side="left", fill="x", expand=True
        )
        self._button(output_row, "Değiştir", self._choose_output, padx=16).pack(
            side="left", padx=(12, 0)
        )

    def _field(
        self,
        parent: tk.Widget,
        row: int,
        column: int,
        label: str,
        variable: tk.StringVar,
    ) -> None:
        theme = self.theme
        box = tk.Frame(parent, background=theme.card)
        box.grid(
            row=row,
            column=column,
            sticky="ew",
            padx=(0, 8) if column == 0 else (8, 0),
            pady=(0, 8) if row == 0 else (8, 0),
        )
        tk.Label(
            box,
            text=label,
            font=("Segoe UI", 9, "bold"),
            foreground=theme.ink,
            background=theme.card,
        ).pack(anchor="w", pady=(0, 5))
        ttk.Entry(box, textvariable=variable, style="App.TEntry").pack(fill="x")

    def _build_action_area(self, parent: tk.Widget) -> None:
        theme = self.theme
        card = self._card(parent, pady=(0, 0))
        top = tk.Frame(card, background=theme.card)
        top.pack(fill="x")

        text = tk.Frame(top, background=theme.card)
        text.pack(side="left", fill="x", expand=True)
        tk.Label(
            text,
            text="3  Dönüştürmeyi başlatın",
            font=("Segoe UI", 11, "bold"),
            foreground=theme.ink,
            background=theme.card,
        ).pack(anchor="w")
        tk.Label(
            text,
            text="Süre; sayfa sayısı, tarama kalitesi ve ekran kartına göre değişir.",
            font=("Segoe UI", 9),
            foreground=theme.muted,
            background=theme.card,
        ).pack(anchor="w", pady=(2, 0))

        self.convert_button = self._button(
            top,
            "EPUB'a dönüştür",
            self._start_conversion,
            primary=True,
            padx=24,
            pady=11,
            font=("Segoe UI", 10, "bold"),
        )
        self.convert_button.pack(side="right", padx=(20, 0))

        self.progress = ttk.Progressbar(
            card,
            mode="indeterminate",
            style="Primary.Horizontal.TProgressbar",
        )
        self.progress.pack(fill="x", pady=(17, 10))

        stage_row = tk.Frame(card, background=theme.card)
        stage_row.pack(fill="x")
        for stage in ("Model hazırlanıyor", "Sayfalar okunuyor", "EPUB oluşturuluyor"):
            label = tk.Label(
                stage_row,
                text=f"○  {stage}",
                font=("Segoe UI", 8),
                foreground=theme.stage_inactive,
                background=theme.card,
            )
            label.pack(side="left", expand=True, anchor="w")
            self.stage_labels.append(label)

        self.status_panel = tk.Frame(card, background=theme.status_bg, padx=12, pady=9)
        self.status_panel.pack(fill="x", pady=(12, 0))
        self.status_label = tk.Label(
            self.status_panel,
            textvariable=self.status_var,
            font=("Segoe UI", 9),
            foreground=theme.muted,
            background=theme.status_bg,
            wraplength=800,
            justify="left",
        )
        self.status_label.pack(side="left", fill="x", expand=True)

        self.result_actions = tk.Frame(self.status_panel, background=theme.status_bg)
        self.result_actions.pack(side="right")
        self.open_button = self._button(
            self.result_actions,
            "EPUB'ı aç",
            self._open_output,
            compact=True,
        )
        self.folder_button = self._button(
            self.result_actions,
            "Klasörü aç",
            self._open_output_folder,
            compact=True,
        )

    def _button(
        self,
        parent: tk.Widget,
        text: str,
        command: Callable[[], None],
        *,
        primary: bool = False,
        compact: bool = False,
        padx: int = 14,
        pady: int = 8,
        font: tuple[str, int] | tuple[str, int, str] = ("Segoe UI", 9, "bold"),
    ) -> tk.Button:
        theme = self.theme
        background = theme.primary if primary else theme.secondary
        foreground = "white" if primary else theme.ink
        active_background = theme.primary_hover if primary else theme.secondary_hover
        return tk.Button(
            parent,
            text=text,
            command=command,
            font=font,
            foreground=foreground,
            background=background,
            activeforeground=foreground,
            activebackground=active_background,
            disabledforeground=theme.muted,
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            padx=10 if compact else padx,
            pady=5 if compact else pady,
        )

    def _choose_pdf(self) -> None:
        selected = filedialog.askopenfilename(
            title="Dönüştürülecek PDF'yi seçin",
            filetypes=[("PDF dosyaları", "*.pdf")],
        )
        if not selected:
            return
        pdf_path = Path(selected)
        self.pdf_var.set(str(pdf_path))
        self.title_var.set(pdf_path.stem)
        self.output_var.set(str(default_epub_path(pdf_path, pdf_path.stem, self.author_var.get())))
        self._set_status("PDF hazır. Kitap bilgilerini kontrol edip dönüştürmeyi başlatın.")

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

    def _model_changed(self, _event: object | None = None) -> None:
        self.model_help_var.set(model_description(self.model_var.get()))

    def _start_conversion(self) -> None:
        try:
            options = build_conversion_options(
                pdf_path=Path(self.pdf_var.get()),
                epub_path=Path(self.output_var.get()),
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
                "Dosya zaten var",
                "Aynı isimde bir EPUB var. Üzerine yazılsın mı?",
            )
            if not overwrite:
                return
            options = replace(options, overwrite=True)

        self._hide_result_actions()
        self.last_output = None
        self.converting = True
        self.theme_button.configure(state="disabled", cursor="arrow")
        self.convert_button.configure(state="disabled", text="Dönüştürülüyor…", cursor="arrow")
        self.progress.configure(mode="indeterminate", maximum=100, value=0)
        self.progress.start(12)
        self._set_stage(0)
        self._set_status("Sistem gereksinimleri kontrol ediliyor…")
        threading.Thread(target=self._convert, args=(options,), daemon=True).start()

    def _convert(self, options: ConversionOptions) -> None:
        try:
            warning = check_runtime()
            if warning:
                self.events.put(("warning", friendly_error(RuntimeError(warning))))
            result = convert_pdf(
                options,
                progress=lambda progress: self.events.put(("progress", progress)),
            )
            self.events.put(("success", result))
        except Exception as error:
            self.events.put(("error", friendly_error(error)))

    def _poll_events(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "progress":
                    self._apply_progress(payload)  # type: ignore[arg-type]
                elif kind == "warning":
                    self._set_status(f"Uyarı: {payload}")
                elif kind == "success":
                    self._finish_success(payload)  # type: ignore[arg-type]
                elif kind == "error":
                    self._finish_error(str(payload))
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

    def _apply_progress(self, progress: ConversionProgress) -> None:
        self._set_status(friendly_progress(progress))
        self._set_stage(progress_stage(progress))
        if progress.total_pages is not None and progress.completed_pages is not None:
            self.progress.stop()
            self.progress.configure(
                mode="determinate",
                maximum=progress.total_pages,
                value=progress.completed_pages,
            )

    def _finish_success(self, result: ConversionResult) -> None:
        self.progress.stop()
        self.progress.configure(mode="determinate", maximum=100, value=100)
        self.converting = False
        self.theme_button.configure(state="normal", cursor="hand2")
        self.convert_button.configure(state="normal", text="EPUB'a dönüştür", cursor="hand2")
        self.last_output = Path(result.epub_path)
        self._set_stage(3)
        self._set_status(
            f"Hazır! EPUB {result.elapsed_seconds / 60:.1f} dakikada oluşturuldu.",
            kind="success",
        )
        self.open_button.pack(side="left", padx=(0, 7))
        self.folder_button.pack(side="left")

    def _finish_error(self, message: str) -> None:
        self.progress.stop()
        self.converting = False
        self.theme_button.configure(state="normal", cursor="hand2")
        self.convert_button.configure(state="normal", text="Tekrar dene", cursor="hand2")
        self._set_status(f"Dönüştürme tamamlanamadı: {message}", kind="error")
        messagebox.showerror("Dönüştürme hatası", message)

    def _set_stage(self, active: int) -> None:
        self.active_stage = active
        theme = self.theme
        for index, label in enumerate(self.stage_labels):
            if active >= 3 or index < active:
                label.configure(
                    text=label.cget("text").replace("○", "●"),
                    foreground=theme.success,
                )
            elif index == active:
                label.configure(
                    text=label.cget("text").replace("○", "●"),
                    foreground=theme.primary,
                )
            else:
                label.configure(
                    text=label.cget("text").replace("●", "○"),
                    foreground=theme.stage_inactive,
                )

    def _set_status(self, message: str, *, kind: str = "neutral") -> None:
        self.status_kind = kind
        theme = self.theme
        colors = {
            "neutral": (theme.status_bg, theme.muted),
            "success": (theme.success_bg, theme.success),
            "error": (theme.error_bg, theme.error),
        }
        background, foreground = colors[kind]
        self.status_var.set(message)
        self.status_panel.configure(background=background)
        self.status_label.configure(background=background, foreground=foreground)
        self.result_actions.configure(background=background)

    def _toggle_theme(self) -> None:
        if self.converting:
            return
        self.theme_name = "light" if self.theme_name == "dark" else "dark"
        self.theme = THEMES[self.theme_name]
        save_theme_preference(self.theme_name)

        status_message = self.status_var.get()
        status_kind = self.status_kind
        active_stage = self.active_stage
        self.ui_root.destroy()
        self.stage_labels.clear()
        self.root.configure(background=self.theme.background)
        self._configure_styles()
        self._build_ui()
        self._apply_windows_title_bar_theme()
        self._set_stage(active_stage)
        self._set_status(status_message, kind=status_kind)
        if self.last_output is not None:
            self.progress.configure(mode="determinate", maximum=100, value=100)
            self.open_button.pack(side="left", padx=(0, 7))
            self.folder_button.pack(side="left")

    def _apply_windows_title_bar_theme(self) -> None:
        if sys.platform != "win32":
            return
        try:
            import ctypes

            self.root.update_idletasks()
            window_handle = ctypes.windll.user32.GetParent(self.root.winfo_id())
            enabled = ctypes.c_int(1 if self.theme_name == "dark" else 0)
            for attribute in (20, 19):
                result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    window_handle,
                    attribute,
                    ctypes.byref(enabled),
                    ctypes.sizeof(enabled),
                )
                if result == 0:
                    break
        except (AttributeError, OSError):
            pass

    def _hide_result_actions(self) -> None:
        self.open_button.pack_forget()
        self.folder_button.pack_forget()

    def _open_output(self) -> None:
        if self.last_output is not None:
            self._open_path(self.last_output)

    def _open_output_folder(self) -> None:
        if self.last_output is not None:
            self._open_path(self.last_output.parent)

    @staticmethod
    def _open_path(path: Path) -> None:
        if sys.platform == "win32":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])


def _enable_windows_scaling() -> None:
    """Keep the interface sharp on high-DPI Windows displays."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("quby1845.pdf-to-epub-ocr")
    except (AttributeError, OSError):
        pass


def main() -> None:
    _enable_windows_scaling()
    root = tk.Tk()
    PdfToEpubApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
