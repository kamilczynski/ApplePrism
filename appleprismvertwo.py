import os
import tkinter as tk
from tkinter import filedialog, Toplevel, messagebox
from tkinter import ttk  # nowoczesne widgety ttk
import numpy as np

import tifffile  # pip install tifffile
from PIL import Image, ImageTk


# ============================= Pomocnicze funkcje =============================

def make_rgb_preview(green, rededge, nir, offset_re, offset_nir):
    """
    Tworzy obraz RGB (uint8) służący do podglądu nakładania kanałów:
       - R = rededge (z przesunięciem offset_re)
       - G = green (bez przesunięcia)
       - B = nir (z przesunięciem offset_nir)
    offset = [dx, dy], gdzie dx, dy liczone w pikselach (w oryginalnej rozdzielczości).
    """
    green_f = green.astype(np.float32)
    red_f = rededge.astype(np.float32)
    nir_f = nir.astype(np.float32)

    dx_re, dy_re = offset_re
    re_shifted = np.roll(red_f, shift=dy_re, axis=0)
    re_shifted = np.roll(re_shifted, shift=dx_re, axis=1)

    dx_nir, dy_nir = offset_nir
    nir_shifted = np.roll(nir_f, shift=dy_nir, axis=0)
    nir_shifted = np.roll(nir_f, shift=dx_nir, axis=1)

    # Wspólna normalizacja intensywności
    stacked = np.stack([green_f, re_shifted, nir_shifted], axis=-1)  # (H, W, 3)
    vmin, vmax = np.nanmin(stacked), np.nanmax(stacked)
    if vmax - vmin < 1e-6:
        vmax = vmin + 1e-6
    normed = (stacked - vmin) / (vmax - vmin)  # 0..1
    rgb_8u = (normed * 255).clip(0, 255).astype(np.uint8)

    # Ustalamy kolejność: R = rededge, G = green, B = nir
    r = rgb_8u[:, :, 1]  # rededge
    g = rgb_8u[:, :, 0]  # green
    b = rgb_8u[:, :, 2]  # nir
    rgb_final = np.dstack([r, g, b])

    return rgb_final


class ARIApp:
    def __init__(self, root):
        # -- Konfiguracja głównego okna --
        self.root = root
        self.root.title("ApplePrism - Manual Alignment (50% scale)")

        # Ustawiamy styl ttk na bardziej futurystyczny wygląd
        self.style = ttk.Style(self.root)
        self.style.theme_use("clam")

        # Styl podstawowy (dla głównego okna, Frame, Label, Button)
        self.style.configure('TFrame', background='#111111')
        self.style.configure('TLabel', background='#111111', foreground='#00ffcc', font=('Orbitron', 11))
        self.style.configure('TButton', background='#222222', foreground='#00ffcc',
                             font=('Orbitron', 11, 'bold'), borderwidth=0)
        self.style.map('TButton',
                       background=[('active', '#00ffcc')],
                       foreground=[('active', '#111111')])

        # Styl specjalny do okien z czarnym tłem (Manual Alignment, ARI)
        self.style.configure('Window.TLabel', background='#000000', foreground='#00ffcc', font=('Orbitron', 11))
        self.style.configure('Window.TButton', background='#000000', foreground='#00ffcc',
                             font=('Orbitron', 11, 'bold'), borderwidth=0)
        self.style.map('Window.TButton',
                       background=[('active', '#00ffcc')],
                       foreground=[('active', '#000000')])

        # -- Ikona aplikacji (opcjonalnie) --
        try:
            self.root.iconbitmap(r"C:\Users\topgu\Desktop\Multispectral\Jabłoń\appleprism.ico")
        except Exception as e:
            print("Failed to set window icon:", e)

        # -- Tło z pliku JPG --
        bg_path = r"C:\Users\topgu\Desktop\Multispectral\Jabłoń\ApplePrism\Leonardo_Vision_XL_appleshaped_prism_3.jpg"
        self.bg_label = None
        try:
            pil_bg = Image.open(bg_path)
            base_width = 900
            w_bg, h_bg = pil_bg.size
            scale_bg = base_width / w_bg
            new_w = int(w_bg * scale_bg)
            new_h = int(h_bg * scale_bg)
            pil_bg = pil_bg.resize((new_w, new_h), Image.Resampling.LANCZOS)

            self.bg_img = ImageTk.PhotoImage(pil_bg)
            self.root.geometry(f"{new_w}x{new_h}")
            self.bg_label = tk.Label(self.root, image=self.bg_img)
            self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        except Exception as e:
            print("Failed to load or set background:", e)

        # -- Kontrolki główne --
        self.top_frame = ttk.Frame(self.root, padding=10)
        self.top_frame.pack(side=tk.TOP, anchor=tk.N)

        self.select_folder_btn = ttk.Button(
            self.top_frame,
            text="Select folder with images",
            command=self.select_folder
        )
        self.select_folder_btn.pack(side=tk.LEFT, padx=5)

        self.align_btn = ttk.Button(
            self.top_frame,
            text="Manual Alignment",
            command=self.open_manual_alignment_window
        )
        self.align_btn.pack(side=tk.LEFT, padx=5)

        self.compute_ari_btn = ttk.Button(
            self.top_frame,
            text="Compute ARI",
            command=self.compute_and_show_ari
        )
        self.compute_ari_btn.pack(side=tk.LEFT, padx=5)

        # Miejsce na podgląd RGB (tutaj zachowujemy mniejsze rozmiary)
        self.rgb_label = ttk.Label(self.root, text="Preview RGB", background="#222222")
        self.rgb_label.pack(pady=10)

        # Pola i zmienne
        self.folder_path = None

        # Kanały wczytywane
        self.green = None
        self.rededge = None
        self.nir = None
        self.rgb_path = None  # ścieżka do pliku RGB

        # Przesunięcia (offset) dla RedEdge i NIR [dx, dy]
        self.offset_re = [0, 0]
        self.offset_nir = [0, 0]

        # Zmienne do ARI
        self.img_ari = None
        self.ari_display = None

        # Okno do wyświetlania mapy ARI
        self.ari_window = None
        self.ari_canvas = None
        self.ari_photo = None

        # ROI (rysowanie okręgu)
        self.circle_center = None
        self.circle_radius = 0
        self.circle_item = None

        # Skalowanie przy wyświetlaniu (np. 50%)
        self.preview_scale = 0.5  # obrazy wyświetlane będą w 50% oryginału

    # ========================= 1) WYBÓR FOLDERU, WCZYTANIE KANAŁÓW ==========================

    def select_folder(self):
        folder_selected = filedialog.askdirectory(title="Select the folder with images for ApplePrism")
        if not folder_selected:
            return
        self.folder_path = folder_selected

        g_path = self.find_file_by_suffix("_MS_G")
        re_path = self.find_file_by_suffix("_MS_RE")
        nir_path = self.find_file_by_suffix("_MS_NIR")
        rgb_path = self.find_file_by_suffix("_D")

        if not g_path or not re_path or not nir_path or not rgb_path:
            messagebox.showerror("Error", "Could not find all required files.")
            return

        self.green = tifffile.imread(g_path).astype(np.float32)
        self.rededge = tifffile.imread(re_path).astype(np.float32)
        self.nir = tifffile.imread(nir_path).astype(np.float32)
        self.rgb_path = rgb_path

        self.load_rgb_image()

    def find_file_by_suffix(self, suffix):
        if not self.folder_path:
            return None

        possible_exts = ['.jpg', '.jpeg', '.png', '.tif', '.tiff']
        for fname in os.listdir(self.folder_path):
            full_path = os.path.join(self.folder_path, fname)
            if not os.path.isfile(full_path):
                continue
            if suffix in fname:
                _, ext = os.path.splitext(fname)
                if ext.lower() in possible_exts:
                    return full_path
        return None

    def load_rgb_image(self):
        """
        Prezentuje plik _D.* jako podgląd (pomniejszony do 600×400 tylko w tym labelu).
        """
        if not self.rgb_path:
            return
        try:
            pil_rgb = Image.open(self.rgb_path)
            max_width, max_height = 600, 400
            w, h = pil_rgb.size
            scale = min(max_width / w, max_height / h, 1.0)
            if scale < 1.0:
                w = int(w * scale)
                h = int(h * scale)
                pil_rgb = pil_rgb.resize((w, h), Image.Resampling.LANCZOS)

            self.img_rgb = ImageTk.PhotoImage(pil_rgb)
            self.rgb_label.config(image=self.img_rgb, background="#222222")
            self.rgb_label.image = self.img_rgb
        except Exception as e:
            print("load_rgb_image error:", e)

    # ========================= 2) OKNO RĘCZNEGO WYRÓWNYWANIA ==========================

    def open_manual_alignment_window(self):
        """
        Otwiera nowe okno do ręcznego przesuwania (offset) RedEdge i NIR względem Green.
        Podgląd wyświetlany jest w skali self.preview_scale (np. 50%).
        """
        if self.green is None or self.rededge is None or self.nir is None:
            messagebox.showwarning("No data", "Load images first.")
            return

        # Tworzymy nowe okno z czarnym tłem
        self.align_window = Toplevel(self.root)
        self.align_window.title("Manual Alignment (scaled)")
        self.align_window.configure(bg="#000000")  # czarne tło

        # Canvas z czarnym tłem
        self.align_canvas = tk.Canvas(self.align_window, bg="#000000")
        self.align_canvas.pack()

        info = (
            "Use arrow keys to move RedEdge\n"
            "Use SHIFT + arrow keys to move NIR\n"
            "Close or press 'Confirm' when done."
        )
        # Label z niestandardowym stylem
        self.align_label = ttk.Label(self.align_window, text=info, style="Window.TLabel")
        self.align_label.pack(pady=5)

        self.confirm_btn = ttk.Button(self.align_window, text="Confirm", style="Window.TButton",
                                      command=self.on_confirm_alignment)
        self.confirm_btn.pack(pady=5)

        # Obsługa klawiszy
        self.align_window.bind("<KeyPress>", self.on_key_press_align)
        self.update_alignment_preview()

    def on_key_press_align(self, event):
        step = 1
        shift_pressed = (event.state & 0x0001) != 0

        if event.keysym == "Up":
            if shift_pressed:
                self.offset_nir[1] -= step
            else:
                self.offset_re[1] -= step
        elif event.keysym == "Down":
            if shift_pressed:
                self.offset_nir[1] += step
            else:
                self.offset_re[1] += step
        elif event.keysym == "Left":
            if shift_pressed:
                self.offset_nir[0] -= step
            else:
                self.offset_re[0] -= step
        elif event.keysym == "Right":
            if shift_pressed:
                self.offset_nir[0] += step
            else:
                self.offset_re[0] += step

        self.update_alignment_preview()

    def update_alignment_preview(self):
        """
        Tworzy podgląd w skali self.preview_scale i ustawia rozmiar Canvas na zmniejszony rozmiar obrazu.
        """
        if self.green is None:
            return

        rgb_8u = make_rgb_preview(
            green=self.green,
            rededge=self.rededge,
            nir=self.nir,
            offset_re=self.offset_re,
            offset_nir=self.offset_nir
        )
        preview = Image.fromarray(rgb_8u)
        orig_w, orig_h = preview.size
        new_w = int(orig_w * self.preview_scale)
        new_h = int(orig_h * self.preview_scale)
        preview_small = preview.resize((new_w, new_h), Image.Resampling.LANCZOS)

        self.align_canvas.config(width=new_w, height=new_h)
        self.align_preview_img = ImageTk.PhotoImage(preview_small)
        self.align_canvas.delete("all")
        self.align_canvas.create_image(0, 0, image=self.align_preview_img, anchor=tk.NW)

    def on_confirm_alignment(self):
        self.align_window.destroy()

    # ========================= 3) OBLICZANIE I WYŚWIETLANIE ARI ==========================

    def compute_and_show_ari(self):
        """
        Stosuje przesunięcia do RedEdge i NIR, oblicza ARI względem Green,
        a następnie wyświetla wynik w skali self.preview_scale (np. 50%).
        """
        if self.green is None or self.rededge is None or self.nir is None:
            messagebox.showwarning("No data", "Load images first.")
            return

        dx_re, dy_re = self.offset_re
        dx_nir, dy_nir = self.offset_nir

        rededge_shifted = np.roll(self.rededge, shift=dy_re, axis=0)
        rededge_shifted = np.roll(rededge_shifted, shift=dx_re, axis=1)

        nir_shifted = np.roll(self.nir, shift=dy_nir, axis=0)
        nir_shifted = np.roll(nir_shifted, shift=dx_nir, axis=1)

        g = self.green
        eps = 1e-6
        ari_map = ((1.0 / (g + eps)) - (1.0 / (rededge_shifted + eps))) * nir_shifted
        self.img_ari = ari_map

        ari_min, ari_max = np.nanmin(ari_map), np.nanmax(ari_map)
        if ari_max - ari_min < 1e-9:
            ari_max = ari_min + 1e-9
        ari_norm = (ari_map - ari_min) / (ari_max - ari_min)
        ari_8u = (ari_norm * 255).astype(np.uint8)
        self.ari_display = ari_8u

        if self.ari_window is not None:
            self.ari_window.destroy()

        # Nowe okno ARI z czarnym tłem
        self.ari_window = Toplevel(self.root)
        self.ari_window.title("Area ARI (scaled 50%)")
        self.ari_window.configure(bg="#000000")  # czarne tło okna

        pil_ari = Image.fromarray(ari_8u, mode='L')
        orig_w, orig_h = pil_ari.size
        new_w = int(orig_w * self.preview_scale)
        new_h = int(orig_h * self.preview_scale)
        pil_ari_small = pil_ari.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # Aby móc poprawnie odczytywać współrzędne ROI w oryginalnych pikselach
        self.scale_factor = 1.0 / self.preview_scale

        # Canvas z czarnym tłem
        self.ari_canvas = tk.Canvas(self.ari_window, width=new_w, height=new_h, bg="#000000")
        self.ari_canvas.pack()

        self.ari_photo = ImageTk.PhotoImage(pil_ari_small)
        self.ari_canvas.create_image(0, 0, image=self.ari_photo, anchor=tk.NW)

        self.ari_canvas.bind("<Button-1>", self.on_mouse_down)
        self.ari_canvas.bind("<B1-Motion>", self.on_mouse_move)
        self.ari_canvas.bind("<ButtonRelease-1>", self.on_mouse_up)

        info_label = ttk.Label(
            self.ari_window,
            text="Click and drag to select the circle (fruit area).",
            style="Window.TLabel"
        )
        info_label.pack(pady=5)

    # ========================= 4) RYSOWANIE KOŁA W OKNIE ARI ==========================

    def on_mouse_down(self, event):
        self.circle_center = (event.x, event.y)
        self.circle_radius = 0
        if self.circle_item is not None:
            self.ari_canvas.delete(self.circle_item)
            self.circle_item = None

    def on_mouse_move(self, event):
        if self.circle_center is None:
            return

        dx = event.x - self.circle_center[0]
        dy = event.y - self.circle_center[1]
        self.circle_radius = int(np.sqrt(dx * dx + dy * dy))

        if self.circle_item is not None:
            self.ari_canvas.delete(self.circle_item)

        x0 = self.circle_center[0] - self.circle_radius
        y0 = self.circle_center[1] - self.circle_radius
        x1 = self.circle_center[0] + self.circle_radius
        y1 = self.circle_center[1] + self.circle_radius

        self.circle_item = self.ari_canvas.create_oval(x0, y0, x1, y1, outline="red", width=2)

    def on_mouse_up(self, event):
        if self.circle_center is None or self.circle_radius == 0:
            return

        cx, cy = self.circle_center
        r = self.circle_radius
        c_x_ari = int(cx * self.scale_factor)
        c_y_ari = int(cy * self.scale_factor)
        r_ari = int(r * self.scale_factor)

        if self.img_ari is None:
            return

        h, w = self.img_ari.shape
        y_grid, x_grid = np.ogrid[:h, :w]
        dist_sq = (x_grid - c_x_ari) ** 2 + (y_grid - c_y_ari) ** 2
        mask = dist_sq <= (r_ari ** 2)

        ari_values_in_circle = self.img_ari[mask]
        if len(ari_values_in_circle) == 0:
            print("Missing pixels in selected area.")
            return

        mean_ari = np.nanmean(ari_values_in_circle)
        print(f"Average ARI value in the highlighted circle = {mean_ari:.4f}")
        messagebox.showinfo("ARI result", f"Average ARI: {mean_ari:.4f}")


# ============================ Uruchamianie aplikacji ===========================
if __name__ == "__main__":
    root = tk.Tk()
    app = ARIApp(root)
    root.mainloop()

# cd "C:\Users\topgu\PycharmProjects\Python Interpreter\venv"

