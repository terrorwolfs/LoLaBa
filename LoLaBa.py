import customtkinter as ctk
from tkinter import messagebox, filedialog, colorchooser, Canvas
import os
from PIL import Image, ImageDraw, ImageTk, ImageFont, ImageEnhance, ImageFilter
import traceback
import json
import copy 
import random 
import math 
import re 

# --- Alapbeállítások ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class FotokonyvGUI:
    """A fotókönyv-szerkesztő alkalmazás fő grafikus felületét (GUI) kezelő osztály."""

    # Előre definiált könyvméretek pixelben (300 DPI alapon)
    BOOK_SIZES = {
        "A4 Álló (21x29.7cm)": (2480, 3508),
        "A4 Fekvő (29.7x21cm)": (3508, 2480),
        "Négyzetes (21x21cm)": (2480, 2480),
        "Kis Négyzetes (15x15cm)": (1772, 1772)
    }
    DEFAULT_BOOK_SIZE_NAME = "A4 Álló (21x29.7cm)"
    DEFAULT_BOOK_SIZE_PIXELS = BOOK_SIZES[DEFAULT_BOOK_SIZE_NAME]


    def __init__(self):
        """Az osztály inicializálása, a fő ablak és az alapvető állapotok beállítása."""
        self.root = ctk.CTk()
        self.root.title("LoLaBa Fotókönyv")
        self.root.geometry("1200x800")
        
        self.colors = {
            'bg_primary': '#C4A484', 'bg_secondary': '#B5956B', 
            'card_bg': '#F5F5F5', 'button_bg': '#E8E8E8',
            'accent': '#A4B068', 'text_primary': '#333333',
            'text_secondary': '#666666', 'green_box': '#4CAF50',
            'selected_card': '#556B2F',
            'selected_photo_border': '#4CAF50',
            'selected_text_color': '#007BFF',
            'canvas_workspace_bg': '#5A5A5A' 
        }
        
        # --- Assets mappa elérési útjának meghatározása ---
        try:
            self.script_path = os.path.dirname(os.path.abspath(__file__))
        except NameError:
            self.script_path = os.getcwd() 
        self.assets_path = os.path.join(self.script_path, "assets")
        
        self.editor_ui_built = False
        self.main_editor_frame = None
        self.left_panel_scroll = None
        self.title_label = None
        self.original_bg_pil_image = None
        
        self.canvas = None
        self.canvas_bg_item = None
        self.canvas_page_frame_item = None
        self.bg_photo_image = None
        self.page_frame_photo_image = None
        self.widget_to_canvas_item = {}

        self.frame_editor_window = None
        self.text_editor_window = None
        
        # Változó a méretválasztó menühöz
        self.selected_book_size_name = ctk.StringVar()
        
        self._reset_project_state()
        self.create_main_menu()

    # --- BELSŐ MŰKÖDÉST SEGÍTŐ METÓDUSOK ---
    def _reset_project_state(self):
        self.current_layout = 1
        self.custom_image_count = 1
        self.selected_layout_card = None
        self.pages = []
        self.current_page = 0
        self.z_order = {}
        self.uploaded_photos = []
        self.selected_photo_index = None
        self.photo_frames = []
        self.photo_properties = {}
        self.text_widgets = []
        self.selected_text_index = None
        self.page_frame_editor_window = None
        self._drag_data = {}
        self.editor_ui_built = False
        self.widget_to_canvas_item = {}
        
        if hasattr(self, 'selected_book_size_name'):
             self.selected_book_size_name.set(self.DEFAULT_BOOK_SIZE_NAME)
        
        if self.frame_editor_window and self.frame_editor_window.winfo_exists(): self.frame_editor_window.destroy()
        self.frame_editor_window = None
        if self.text_editor_window and self.text_editor_window.winfo_exists(): self.text_editor_window.destroy()
        self.text_editor_window = None



  

    def _resize_main_menu_bg(self, event):
        """Az ablak átméretezésekor frissíti a főmenü háttérképét, hogy arányosan kitöltse a teret."""
        # Ha a kép betöltése sikertelen volt, ne csináljon semmit
        if not hasattr(self, 'original_bg_pil_image') or not self.original_bg_pil_image:
            return

        # Kérjük le a keret új méretét az eseményből
        new_width = event.width
        new_height = event.height
    
        # Elkerüljük a hibát, ha az ablak 0 méretűre van kicsinyítve
        if new_width <= 0 or new_height <= 0:
            return

        try:
            # Méretezzük át az eredeti PIL képet az új méretre
            resized_pil_image = self.original_bg_pil_image.resize((new_width, new_height), Image.LANCZOS)

            # Hozzunk létre egy új CTkImage objektumot a frissített méretekkel
            self.main_menu_bg_image = ctk.CTkImage(resized_pil_image, size=(new_width, new_height))
        
            # Frissítsük a címkét az új képpel
            self.bg_label.configure(image=self.main_menu_bg_image)
        except Exception as e:
            print(f"Hiba a háttérkép átméretezésekor: {e}")

    def _set_cursor_recursive(self, widget, cursor_style):
        """Rekurzívan beállítja a kurzort egy widgeten és annak összes gyerek-widgetjén."""
        try:
            # Beállítja a kurzort a jelenlegi elemen
            widget.config(cursor=cursor_style)
        except Exception:
            # Előfordulhat hiba, ha a widget épp megsemmisül, ezt figyelmen kívül hagyjuk
            pass
        
        # Végigmegy az összes gyerek-elemen és meghívja önmagát rájuk
        for child in widget.winfo_children():
            self._set_cursor_recursive(child, cursor_style)

    def _show_working_indicator(self, message=None):
        """A kurzort 'várakozó' állapotba kapcsolja az egész alkalmazáson, rekurzívan."""
        self._set_cursor_recursive(self.root, "watch")
        # Fontos, hogy a GUI frissüljön a blokkoló művelet elindítása előtt
        self.root.update_idletasks()

    def _hide_working_indicator(self):
        """Visszaállítja a kurzort az alapértelmezett állapotba az egész alkalmazáson, rekurzívan."""
        self._set_cursor_recursive(self.root, "")

    def _select_photo(self, photo_index):
        self._deselect_all()
        self.selected_photo_index = photo_index

        if self.selected_photo_index is not None and self.selected_photo_index < len(self.pages[self.current_page]['photos']):
            if self.selected_photo_index < len(self.photo_frames) and self.photo_frames[self.selected_photo_index]:
                selected_frame = self.photo_frames[self.selected_photo_index]
                selected_frame.configure(border_width=3, border_color=self.colors['selected_photo_border'])
                if selected_frame in self.widget_to_canvas_item:
                    self.canvas.tag_raise(self.widget_to_canvas_item[selected_frame])
                
                props_key = str((self.current_page, photo_index))
                props = self.photo_properties.get(props_key, {})
                photo_data = self.pages[self.current_page]['photos'][photo_index]

                widgets_to_enable = [
                    self.zoom_slider, self.pan_x_slider, self.pan_y_slider,
                    self.width_slider, self.height_slider,
                    self.brightness_slider, self.contrast_slider, self.saturation_slider,
                    self.grayscale_checkbox, self.fit_mode_button
                ]
                for widget in widgets_to_enable:
                    widget.configure(state="normal")
                
                self.zoom_slider.set(props.get('zoom', 1.0))
                self.pan_x_slider.set(props.get('pan_x', 0.5))
                self.pan_y_slider.set(props.get('pan_y', 0.5))
                self.width_slider.set(photo_data.get('relwidth', 0.5))
                self.height_slider.set(photo_data.get('relheight', 0.5))
                self.brightness_slider.set(props.get('brightness', 1.0))
                self.contrast_slider.set(props.get('contrast', 1.0))
                self.saturation_slider.set(props.get('saturation', 1.0))
                
                if props.get('grayscale', False):
                    self.grayscale_checkbox.select()
                else:
                    self.grayscale_checkbox.deselect()

                
                fit_mode = props.get('fit_mode', 'fill') 
                self.fit_mode_button.set("Beleillesztés" if fit_mode == 'fit' else "Kitöltés")

                if self.frame_editor_window and self.frame_editor_window.winfo_exists():
                    self.update_frame_editor_ui()

    def _deselect_all(self):
        if self.selected_photo_index is not None and self.selected_photo_index < len(self.photo_frames):
            if self.photo_frames[self.selected_photo_index] and self.photo_frames[self.selected_photo_index].winfo_exists():
                self.photo_frames[self.selected_photo_index].configure(border_width=0)
        self.selected_photo_index = None
        
        if self.selected_text_index is not None and self.selected_text_index < len(self.text_widgets):
            if self.text_widgets[self.selected_text_index].winfo_exists() and len(self.text_widgets[self.selected_text_index].winfo_children()) > 0:
                text_label = self.text_widgets[self.selected_text_index].winfo_children()[0]
                original_color = self.pages[self.current_page]['texts'][self.selected_text_index].get('font_color', '#000000')
                text_label.configure(text_color=original_color)
        self.selected_text_index = None

        if hasattr(self, 'zoom_slider'):
            widgets_to_disable = [
                self.zoom_slider, self.pan_x_slider, self.pan_y_slider,
                self.width_slider, self.height_slider,
                self.brightness_slider, self.contrast_slider, self.saturation_slider,
                self.grayscale_checkbox, self.fit_mode_button
            ]
            for widget in widgets_to_disable:
                widget.configure(state="disabled")

        if self.frame_editor_window and self.frame_editor_window.winfo_exists(): self.update_frame_editor_ui()
        if self.text_editor_window and self.text_editor_window.winfo_exists(): self.update_text_editor_ui()

    def _select_text(self, text_index):
        self._deselect_all()
        self.selected_text_index = text_index
        if self.selected_text_index is not None and self.selected_text_index < len(self.text_widgets):
            text_widget_container = self.text_widgets[self.selected_text_index]
            text_label = text_widget_container.winfo_children()[0]
            text_label.configure(text_color=self.colors['selected_text_color'])
            self.canvas.tag_raise(self.widget_to_canvas_item[text_widget_container])
        if self.text_editor_window and self.text_editor_window.winfo_exists():
            self.update_text_editor_ui()

    


    def _change_fit_mode(self, value):
        """A képillesztési mód (Beleillesztés/Kitöltés) változását kezeli."""
        if self.selected_photo_index is None:
            return
            
        key = str((self.current_page, self.selected_photo_index))
        if key not in self.photo_properties:
            self.photo_properties[key] = {}
            
        # A gomb szöveges értékét lefordítjuk a belsőleg használt kulcsszóra
        mode = 'fit' if value == "Beleillesztés" else 'fill'
        self.photo_properties[key]['fit_mode'] = mode
        
        # Frissítjük a kép megjelenítését az új beállítással
        self._update_photo_properties()


    def _update_photo_properties(self, value=None):
        if self.selected_photo_index is None: return
        key = str((self.current_page, self.selected_photo_index))
        if key not in self.photo_properties: self.photo_properties[key] = {}
        
        if hasattr(self, 'zoom_slider'):
            self.photo_properties[key]['zoom'] = self.zoom_slider.get()
            self.photo_properties[key]['pan_x'] = self.pan_x_slider.get()
            self.photo_properties[key]['pan_y'] = self.pan_y_slider.get()
        
        if hasattr(self, 'brightness_slider'):
            self.photo_properties[key]['brightness'] = self.brightness_slider.get()
            self.photo_properties[key]['contrast'] = self.contrast_slider.get()
            self.photo_properties[key]['saturation'] = self.saturation_slider.get()
            self.photo_properties[key]['grayscale'] = self.grayscale_checkbox.get() == 1

        if self.frame_editor_window and self.frame_editor_window.winfo_exists():
            self.photo_properties[key]['frame_scale'] = self.frame_scale_slider.get()
            self.photo_properties[key]['frame_offset_x'] = int(self.frame_offset_x_slider.get())
            self.photo_properties[key]['frame_offset_y'] = int(self.frame_offset_y_slider.get())
            self.photo_properties[key]['frame_thickness'] = self.frame_thickness_slider.get()
        
        if hasattr(self, 'photo_frames') and self.photo_frames and self.selected_photo_index < len(self.photo_frames):
            frame = self.photo_frames[self.selected_photo_index]
            photo_data = self.pages[self.current_page]['photos'][self.selected_photo_index]
            self.display_photo_placeholder(frame, photo_data, self.selected_photo_index, is_update=True)

    
    
    # --- FELÜLETET ÉPÍTŐ METÓDUSOK ---
    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def create_main_menu(self):
        self._reset_project_state()
        self.clear_window()
        main_frame = ctk.CTkFrame(self.root, fg_color=self.colors['bg_primary'], corner_radius=0)
        main_frame.pack(fill="both", expand=True)

        
        
        try:
            bg_image_path = os.path.join(self.assets_path, "backgrounds", "main_menu_bg.png")
            # 1. Töltsük be az eredeti, nagy felbontású képet és mentsük el
            self.original_bg_pil_image = Image.open(bg_image_path)

            # 2. Hozzuk létre a címkét, amiben a kép lesz, de még kép nélkül
            self.bg_label = ctk.CTkLabel(main_frame, text="")
            self.bg_label.place(relx=0, rely=0, relwidth=1, relheight=1)

            # 3. Kössük hozzá az átméretezést figyelő eseményt a kerethez
            main_frame.bind("<Configure>", self._resize_main_menu_bg)

        except Exception as e:
            # Hiba esetén is hozzuk létre a változót, hogy ne legyen később gond
            self.original_bg_pil_image = None
            print(f"Főmenü háttérképét nem sikerült betölteni: {e}")

        ctk.CTkLabel(main_frame, text="LoLaBa Fotókönyv", font=ctk.CTkFont(size=48, weight="bold"), text_color="white", fg_color="transparent").pack(pady=(80, 20))
        ctk.CTkLabel(main_frame, text="Készíts saját, egyedi fotókönyvet egyszerű lépésekkel!", font=ctk.CTkFont(size=18), text_color="white", fg_color="transparent").pack(pady=(0, 60))
        
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(expand=True, padx=40)
        
        # --- GOMBOK LÉTREHOZÁSA (FINOMHANGOLVA) ---
        
        buttons_data = [
            ("🆕", "Új projekt létrehozása", lambda: self.show_page_selection(is_new_project=True)),
            ("📁", "Korábbi projekt megnyitása", self.load_project),
            ("🚪", "Kilépés", self.root.quit)
        ]
        
        bg_color = self.colors['card_bg']
        hover_color = '#F0F0F0'
        text_color = self.colors['text_primary']
        icon_font = ctk.CTkFont(size=22)
        text_font = ctk.CTkFont(size=16, weight="bold")

        for icon, text, command in buttons_data:
            button_container = ctk.CTkFrame(
                button_frame, 
                height=60, 
                width=350, 
                fg_color=bg_color, 
                corner_radius=15,
                cursor="hand2"
            )
            button_container.pack(pady=15, fill="x")
            button_container.pack_propagate(False)

            def on_enter(e, widget=button_container):
                widget.configure(fg_color=hover_color)
            
            def on_leave(e, widget=button_container):
                widget.configure(fg_color=bg_color)

            button_container.bind("<Enter>", on_enter)
            button_container.bind("<Leave>", on_leave)
            button_container.bind("<Button-1>", lambda e, cmd=command: cmd())

            # Ikon címke - A FÜGGŐLEGES IGAZÍTÁS ITT TÖRTÉNIK
            icon_label = ctk.CTkLabel(
                button_container, 
                text=icon, 
                font=icon_font, 
                fg_color="transparent",
                text_color=text_color
            )
            # A pady=(8, 12) felfelé tolja az ikont a (10, 10) középhez képest
            icon_label.pack(side="left", padx=(20, 10), pady=(8, 12)) 
            icon_label.bind("<Enter>", on_enter)
            icon_label.bind("<Leave>", on_leave)
            icon_label.bind("<Button-1>", lambda e, cmd=command: cmd())

            # Szöveg címke
            text_label = ctk.CTkLabel(
                button_container, 
                text=text, 
                font=text_font, 
                fg_color="transparent",
                text_color=text_color
            )
            # A szöveg marad középen a (10, 10) pady értékkel
            text_label.pack(side="left", padx=(0, 20), pady=(10, 10), expand=True, fill="x", anchor="w")
            text_label.bind("<Enter>", on_enter)
            text_label.bind("<Leave>", on_leave)
            text_label.bind("<Button-1>", lambda e, cmd=command: cmd())

    def create_layout_preview(self, parent, layout_count, click_handler=None):
        """
        Létrehoz egy előnézeti keretet a megadott számú elrendezéshez,
        VIZUÁLISAN egyenletes, pixel-alapú margókkal és közökkel.
        """
        preview_frame = ctk.CTkFrame(parent, width=180, height=100, fg_color=self.colors['accent'], corner_radius=10)
        preview_frame.pack(pady=(20, 10))
        preview_frame.pack_propagate(False)
        if click_handler:
            preview_frame.bind("<Button-1>", click_handler)

        if layout_count == 0:
            return

        # --- ÚJ LOGIKA: Pixel-alapú számítás a vizuális szimmetriáért ---

        # 1. A keret fix méretei és a kívánt margó pixelben
        frame_w_px = 180
        frame_h_px = 100
        padding_px = 8 # Ezt a pixel értéket használjuk mindenhol (margóként és közként is)

        # 2. Rács méretének meghatározása
        cols = max(1, int(math.ceil(math.sqrt(layout_count))))
        rows = max(1, int(math.ceil(layout_count / cols)))
        
        # Biztonsági ellenőrzés: ha a padding túl sok helyet foglalna, csökkentjük
        if padding_px * (cols + 1) >= frame_w_px or padding_px * (rows + 1) >= frame_h_px:
            padding_px = 4

        # 3. Dobozok méretének kiszámítása PIXELBEN
        total_padding_w_px = padding_px * (cols + 1)
        total_padding_h_px = padding_px * (rows + 1)

        box_w_px = (frame_w_px - total_padding_w_px) / cols
        box_h_px = (frame_h_px - total_padding_h_px) / rows
        
        # Ha a számítás negatív méretet adna, ne rajzoljunk semmit
        if box_w_px <= 0 or box_h_px <= 0:
            return

        # 4. Dobozok elhelyezése a pixel értékekből számolt relatív pozíciókkal
        for i in range(layout_count):
            c = i % cols
            r = i // cols

            # Doboz pozíciója pixelben a bal felső saroktól
            x_px = padding_px + c * (box_w_px + padding_px)
            y_px = padding_px + r * (box_h_px + padding_px)

            # Átváltás relatív értékekre a .place() metódushoz
            rel_x = x_px / frame_w_px
            rel_y = y_px / frame_h_px
            rel_w = box_w_px / frame_w_px
            rel_h = box_h_px / frame_h_px

            box = ctk.CTkFrame(preview_frame, fg_color=self.colors['green_box'], corner_radius=3, border_width=0)
            box.place(relx=rel_x, rely=rel_y, relwidth=rel_w, relheight=rel_h)
            if click_handler:
                box.bind("<Button-1>", click_handler)

    def show_page_selection(self, is_new_project=False):
        if is_new_project: self._reset_project_state()
        self.selected_layout_card = None
        self.clear_window()
        self.editor_ui_built = False
        main_frame = ctk.CTkFrame(self.root, fg_color=self.colors['bg_primary'], corner_radius=0)
        main_frame.pack(fill="both", expand=True)
        ctk.CTkLabel(main_frame, text="Válassz egy kiinduló elrendezést", font=ctk.CTkFont(size=32, weight="bold"), text_color="white").pack(pady=(50, 20))

        # --- Méretválasztó szekció (MÓDOSÍTVA) ---
        if is_new_project:
            size_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
            size_frame.pack(pady=(0, 20))
            ctk.CTkLabel(size_frame, text="Fotókönyv mérete:", font=ctk.CTkFont(size=16), text_color="white").pack(side="left", padx=10)
            
            # Az opciók listájának dinamikus összeállítása
            size_options = list(self.BOOK_SIZES.keys())
            # "Egyéni méret..." opció hozzáadása, ha még nincs
            if "Egyéni méret..." not in size_options:
                 size_options.append("Egyéni méret...")

            # A menü widgetet elmentjük egy példányváltozóba, hogy később frissíthessük
            self.size_menu = ctk.CTkOptionMenu(
                size_frame, 
                variable=self.selected_book_size_name, 
                values=size_options,
                command=self._handle_size_selection  # Figyeli a kiválasztást
            )
            self.size_menu.pack(side="left")

        layout_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        layout_frame.pack(expand=True, padx=20, pady=10)
        cards_frame = ctk.CTkFrame(layout_frame, fg_color="transparent")
        cards_frame.pack()

        layouts = [{"name": "1 kép", "value": 1}, {"name": "2 kép", "value": 2}, {"name": "4 kép", "value": 4}]
        self.layout_cards = []

        for i, layout in enumerate(layouts):
            card = ctk.CTkFrame(cards_frame, width=220, height=180, fg_color=self.colors['card_bg'], corner_radius=20)
            card.grid(row=0, column=i, padx=25, pady=20)
            card.pack_propagate(False)
            name_label = ctk.CTkLabel(card, text=layout["name"], font=ctk.CTkFont(size=16, weight="bold"), text_color=self.colors['text_primary'])
            name_label.pack(pady=(0, 15))
            def make_click_handler(value, card_widget): return lambda e: self.select_layout(value, card_widget)
            click_handler = make_click_handler(layout["value"], card)
            card.bind("<Button-1>", click_handler)
            name_label.bind("<Button-1>", click_handler)
            self.create_layout_preview(card, layout["value"], click_handler)
            self.layout_cards.append(card)

        self.custom_card = ctk.CTkFrame(cards_frame, width=220, height=180, fg_color=self.colors['card_bg'], corner_radius=20)
        self.custom_card.grid(row=1, column=1, padx=25, pady=20)
        self.custom_card.pack_propagate(False)

        custom_title = ctk.CTkLabel(self.custom_card, text="Egyéni mennyiség", font=ctk.CTkFont(size=16, weight="bold"), text_color=self.colors['text_primary'])
        custom_title.pack(pady=(10, 5))

        count_frame = ctk.CTkFrame(self.custom_card, fg_color="transparent")
        count_frame.pack(pady=5)

        ctk.CTkButton(count_frame, text="−", width=30, height=30, command=self.decrease_custom_count).pack(side="left", padx=5)
        self.custom_count_label = ctk.CTkLabel(count_frame, text=str(self.custom_image_count), font=ctk.CTkFont(size=16, weight="bold"), width=40)
        self.custom_count_label.pack(side="left", padx=5)
        ctk.CTkButton(count_frame, text="+", width=30, height=30, command=self.increase_custom_count).pack(side="left", padx=5)

        self.custom_preview_frame = ctk.CTkFrame(self.custom_card, fg_color="transparent", width=180, height=100)
        self.custom_preview_frame.pack(pady=(5, 10))
        self.custom_preview_frame.pack_propagate(False)
        self.update_custom_preview()

        self.custom_card.bind("<Button-1>", lambda e: self.select_custom_layout())

        ctk.CTkButton(main_frame, text="🔧 Tovább a szerkesztőbe", command=self.proceed_to_editor, height=50, font=ctk.CTkFont(size=16, weight="bold")).pack(pady=40, padx=40)

    def _handle_size_selection(self, choice: str):
        """A méretválasztó menü eseménykezelője. Ha az "Egyéni méret..." opciót választják, megnyit egy ablakot."""
        if choice == "Egyéni méret...":
            self._prompt_for_custom_size()

    def _prompt_for_custom_size(self):
        """Felugró ablakot hoz létre, ahol a felhasználó megadhatja az egyéni oldalméretet pixelben."""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Egyéni méret megadása")
        dialog.geometry("300x200")
        dialog.transient(self.root)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Add meg a méreteket pixelben (300 DPI):", font=ctk.CTkFont(size=12)).pack(pady=(10, 5))

        width_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        width_frame.pack(pady=5, padx=20, fill="x")
        ctk.CTkLabel(width_frame, text="Szélesség (px):", width=100).pack(side="left")
        width_entry = ctk.CTkEntry(width_frame)
        width_entry.pack(side="left", expand=True, fill="x")

        height_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        height_frame.pack(pady=5, padx=20, fill="x")
        ctk.CTkLabel(height_frame, text="Magasság (px):", width=100).pack(side="left")
        height_entry = ctk.CTkEntry(height_frame)
        height_entry.pack(side="left", expand=True, fill="x")

        def apply_custom_size():
            try:
                width = int(width_entry.get())
                height = int(height_entry.get())
                if width <= 0 or height <= 0:
                    raise ValueError("A méreteknek pozitívnak kell lenniük.")

                # Létrehozzuk az új méret nevét és értékét
                custom_key = f"Egyéni ({width}x{height}px)"
                custom_value = (width, height)

                # Hozzáadjuk a szótárhoz
                self.BOOK_SIZES[custom_key] = custom_value
                
                # Frissítjük a legördülő menü opcióit
                new_options = list(self.BOOK_SIZES.keys())
                if "Egyéni méret..." not in new_options:
                    new_options.append("Egyéni méret...")
                self.size_menu.configure(values=new_options)

                # Beállítjuk az új, egyéni méretet kiválasztottnak
                self.selected_book_size_name.set(custom_key)

                dialog.destroy()

            except ValueError as e:
                messagebox.showerror("Hiba", f"Érvénytelen érték!\nKérlek, pozitív egész számokat adj meg.\n({e})", parent=dialog)

        apply_button = ctk.CTkButton(dialog, text="Alkalmaz", command=apply_custom_size)
        apply_button.pack(pady=20)
    

    def select_layout(self, layout_value, card_widget):
        if self.selected_layout_card: self.selected_layout_card.configure(fg_color=self.colors['card_bg'])
        self.custom_card.configure(fg_color=self.colors['card_bg'])
        self.current_layout = layout_value; self.selected_layout_card = card_widget
        card_widget.configure(fg_color=self.colors['selected_card'])

    def select_custom_layout(self):
        if self.selected_layout_card: self.selected_layout_card.configure(fg_color=self.colors['card_bg'])
        self.current_layout = self.custom_image_count
        self.selected_layout_card = self.custom_card
        self.custom_card.configure(fg_color=self.colors['selected_card'])

    def decrease_custom_count(self):
        if self.custom_image_count > 1:
            self.custom_image_count -= 1
            self.custom_count_label.configure(text=str(self.custom_image_count))
            self.update_custom_preview(); self.select_custom_layout()

    def increase_custom_count(self):
        if self.custom_image_count < 20:
            self.custom_image_count += 1
            self.custom_count_label.configure(text=str(self.custom_image_count))
            self.update_custom_preview(); self.select_custom_layout()

    def update_custom_preview(self):
        for widget in self.custom_preview_frame.winfo_children(): widget.destroy()
        self.create_layout_preview(self.custom_preview_frame, self.custom_image_count, click_handler=lambda e: self.select_custom_layout())

    def _generate_layout_template(self, count):
        geometries = []
        base_photo_data = {'path': None, 'relx': 0, 'rely': 0, 'relwidth': 0, 'relheight': 0, 'layout_relwidth': 0, 'layout_relheight': 0}
        
        if count == 1:
            geo = base_photo_data.copy()
            geo.update({'relx': 0.05, 'rely': 0.05, 'relwidth': 0.9, 'relheight': 0.9, 'layout_relwidth': 0.9, 'layout_relheight': 0.9})
            geometries.append(geo)
        elif count == 2:
            for relx in [0.05, 0.53]:
                geo = base_photo_data.copy()
                geo.update({'relx': relx, 'rely': 0.1, 'relwidth': 0.42, 'relheight': 0.8, 'layout_relwidth': 0.42, 'layout_relheight': 0.8})
                geometries.append(geo)
        elif count == 3:
            geo1 = base_photo_data.copy(); geo1.update({'relx': 0.05, 'rely': 0.05, 'relwidth': 0.9, 'relheight': 0.42, 'layout_relwidth': 0.9, 'layout_relheight': 0.42}); geometries.append(geo1)
            geo2 = base_photo_data.copy(); geo2.update({'relx': 0.05, 'rely': 0.53, 'relwidth': 0.42, 'relheight': 0.42, 'layout_relwidth': 0.42, 'layout_relheight': 0.42}); geometries.append(geo2)
            geo3 = base_photo_data.copy(); geo3.update({'relx': 0.53, 'rely': 0.53, 'relwidth': 0.42, 'relheight': 0.42, 'layout_relwidth': 0.42, 'layout_relheight': 0.42}); geometries.append(geo3)
        elif count == 4:
            for rely in [0.05, 0.53]:
                for relx in [0.05, 0.53]:
                    geo = base_photo_data.copy()
                    geo.update({'relx': relx, 'rely': rely, 'relwidth': 0.42, 'relheight': 0.42, 'layout_relwidth': 0.42, 'layout_relheight': 0.42})
                    geometries.append(geo)
        else:
            if count == 0: return []
            
            cols = int(math.ceil(math.sqrt(count)))
            rows = int(math.ceil(count / cols))
            
            padding, spacing = 0.05, 0.03
            total_space_w = 1.0 - (2 * padding) - ((cols - 1) * spacing)
            total_space_h = 1.0 - (2 * padding) - ((rows - 1) * spacing)
            cell_w, cell_h = total_space_w / cols, total_space_h / rows

            for i in range(count):
                c, r = i % cols, i // cols
                
                last_row_item_count = count % cols
                if last_row_item_count == 0: last_row_item_count = cols
                
                row_offset = 0
                if r == rows - 1 and last_row_item_count < cols:
                    row_width = (last_row_item_count * cell_w) + ((last_row_item_count - 1) * spacing)
                    row_offset = (1.0 - row_width - 2 * padding) / 2
                
                rel_x = padding + row_offset + c * (cell_w + spacing)
                rel_y = padding + r * (cell_h + spacing)
                
                geo = base_photo_data.copy()
                geo.update({'relx': rel_x, 'rely': rel_y, 'relwidth': cell_w, 'relheight': cell_h, 'layout_relwidth': cell_w, 'layout_relheight': cell_h})
                geometries.append(geo)
            
        return geometries

    def proceed_to_editor(self):
        if not self.selected_layout_card:
            messagebox.showwarning("Figyelem", "Kérjük válassz egy oldalelrendezést!")
            return

        new_layout_count = self.current_layout

        if not self.pages:
            # Új projekt létrehozása
            page_size_name = self.selected_book_size_name.get()
            page_size_pixels = self.BOOK_SIZES.get(page_size_name, self.DEFAULT_BOOK_SIZE_PIXELS)
            
            new_page = {
                'photos': self._generate_layout_template(new_layout_count), 
                'texts': [],
                'size': page_size_pixels  # Méret hozzáadása az oldal adataihoz
            }
            self.pages.append(new_page)
            self.current_page = 0
        else:
            # Meglévő oldal módosítása
            current_page_data = self.pages[self.current_page]
            current_photos = current_page_data.get('photos', [])
            current_photo_count = len(current_photos)
            
            photos_with_content = [p for p in current_photos if p.get('path')]
            if new_layout_count < len(photos_with_content):
                if not messagebox.askyesno("Figyelem!",
                                           f"Az új elrendezés ({new_layout_count} kép) kevesebb helyet tartalmaz, mint a jelenleg beillesztett képek száma ({len(photos_with_content)}).\n\n"
                                           "A felesleges képek el fognak veszni erről az oldalról.\n"
                                           "A háttér és a szövegek megmaradnak.\n\n"
                                           "Biztosan folytatja?"):
                    self.show_page_selection(is_new_project=False)
                    return

            old_photo_paths_to_keep = []
            old_properties_to_remap = {}
            for i in range(current_photo_count):
                if current_photos[i].get('path'):
                    old_photo_paths_to_keep.append(current_photos[i]['path'])
                    
                    key = str((self.current_page, i))
                    if key in self.photo_properties:
                        new_temp_index = len(old_photo_paths_to_keep) - 1
                        old_properties_to_remap[new_temp_index] = self.photo_properties[key]

            for i in range(current_photo_count):
                key_to_delete = str((self.current_page, i))
                if key_to_delete in self.photo_properties:
                    del self.photo_properties[key_to_delete]
            
            new_layout = self._generate_layout_template(new_layout_count)

            for i in range(len(new_layout)):
                if i < len(old_photo_paths_to_keep):
                    new_layout[i]['path'] = old_photo_paths_to_keep[i]
                    
                    if i in old_properties_to_remap:
                        new_key = str((self.current_page, i))
                        self.photo_properties[new_key] = old_properties_to_remap[i]
            
            current_page_data['photos'] = new_layout
            self.z_order[str(self.current_page)] = list(range(new_layout_count))

        if not self.editor_ui_built:
            self._build_editor_ui()
            self.editor_ui_built = True
        
        self.refresh_editor_view()

    def _build_editor_ui(self):
        self.clear_window()
        self.main_editor_frame = ctk.CTkFrame(self.root, fg_color=self.colors['bg_primary'], corner_radius=0)
        self.main_editor_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.title_label = ctk.CTkLabel(self.main_editor_frame, text="", font=ctk.CTkFont(size=28, weight="bold"), text_color="white")
        self.title_label.pack(pady=(5, 15))
        
        toolbar = ctk.CTkFrame(self.main_editor_frame, height=70, fg_color=self.colors['card_bg'], corner_radius=15)
        toolbar.pack(side="bottom", fill="x", pady=(15, 0))
        toolbar.pack_propagate(False)
        toolbar_buttons = [("💾 Mentés", self.save_project), ("📁 Betöltés", self.load_project), ("📤 Exportálás", self.export_project), ("🏠 Főmenü", self.create_main_menu)]
        buttons_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        buttons_frame.pack(expand=True)
        for text, command in toolbar_buttons:
            ctk.CTkButton(buttons_frame, text=text, command=command, width=140, height=40, font=ctk.CTkFont(size=12), corner_radius=10, fg_color=self.colors['button_bg'], text_color=self.colors['text_secondary'], hover_color='#F0F0F0').pack(side="left", padx=10, pady=15)
        
        workspace = ctk.CTkFrame(self.main_editor_frame, fg_color="transparent")
        workspace.pack(fill="both", expand=True, pady=5, padx=10)
        
        left_panel = ctk.CTkFrame(workspace, width=220, fg_color=self.colors['card_bg'], corner_radius=20)
        left_panel.pack(side="left", fill="y", padx=(0, 10))
        left_panel.pack_propagate(False)
        ctk.CTkLabel(left_panel, text="Oldalak", font=ctk.CTkFont(size=18, weight="bold"), text_color=self.colors['text_primary']).pack(pady=(20, 15))
        self.left_panel_scroll = ctk.CTkScrollableFrame(left_panel, fg_color="transparent")
        self.left_panel_scroll.pack(expand=True, fill="both", pady=10, padx=10)
        ctk.CTkButton(left_panel, text="+ Új oldal", command=self.add_new_page_and_refresh, height=40, font=ctk.CTkFont(size=14, weight="bold"), corner_radius=15, fg_color=self.colors['accent'], hover_color='#8A9654').pack(pady=15, padx=10, fill="x")
        
        right_panel = ctk.CTkFrame(workspace, width=260, fg_color=self.colors['card_bg'], corner_radius=20)
        right_panel.pack(side="right", fill="y", padx=(10,0))
        right_panel.pack_propagate(False)
        self._build_right_panel(right_panel)

        self.canvas = Canvas(workspace, bg=self.colors['canvas_workspace_bg'], highlightthickness=0, relief='ridge')
        self.canvas.pack(side="left", fill="both", expand=True, padx=10)

    
    def _build_right_panel(self, right_panel):
        ctk.CTkLabel(right_panel, text="Eszközök", font=ctk.CTkFont(size=18, weight="bold"), text_color=self.colors['text_primary']).pack(pady=(10, 5))
        tools_scroll_area = ctk.CTkScrollableFrame(right_panel, fg_color="transparent")
        tools_scroll_area.pack(fill="both", expand=True, padx=5, pady=5)
        
        wizard_frame = ctk.CTkFrame(tools_scroll_area, fg_color="transparent")
        wizard_frame.pack(pady=5, fill="x", padx=10)
        ctk.CTkButton(wizard_frame, text="✨ Alap Varázsló", command=self.run_basic_wizard).pack(pady=4, fill="x")
        ctk.CTkButton(wizard_frame, text="🧠 Okos Varázsló", command=self.run_smart_wizard, fg_color=self.colors['accent'], hover_color='#8A9654').pack(pady=4, fill="x")

        # --- KÉP ILLESZTÉS SZEKCIÓ ---
        fit_mode_frame = ctk.CTkFrame(tools_scroll_area, fg_color="transparent")
        fit_mode_frame.pack(pady=(10, 5), fill="x", padx=10)
        ctk.CTkLabel(fit_mode_frame, text="Kép illesztése", font=ctk.CTkFont(size=12, weight="bold"), text_color="grey").pack()
        
        self.fit_mode_button = ctk.CTkSegmentedButton(
            fit_mode_frame,
            values=["Beleillesztés", "Kitöltés"],
            command=self._change_fit_mode
        )
        self.fit_mode_button.pack(fill="x", padx=5, pady=(5, 10))
        self.fit_mode_button.set("Kitöltés") # MÓDOSÍTVA: Alapértelmezett a Kitöltés
        
        slider_frame = ctk.CTkFrame(tools_scroll_area, fg_color="transparent")
        slider_frame.pack(pady=5, fill="x", padx=10)

        ctk.CTkLabel(slider_frame, text="Kép nagyítása és mozgatása", font=ctk.CTkFont(size=12, weight="bold"), text_color="grey").pack()

        ctk.CTkLabel(slider_frame, text="Nagyítás", font=ctk.CTkFont(size=12), text_color="grey").pack()
        self.zoom_slider = ctk.CTkSlider(slider_frame, from_=1.0, to=5.0, command=self._update_photo_properties)
        self.zoom_slider.pack(fill="x", padx=5, pady=(0, 10))
        ctk.CTkLabel(slider_frame, text="Vízszintes pozíció", font=ctk.CTkFont(size=12), text_color="grey").pack()
        self.pan_x_slider = ctk.CTkSlider(slider_frame, from_=0.0, to=1.0, command=self._update_photo_properties)
        self.pan_x_slider.pack(fill="x", padx=5, pady=(0, 10))
        ctk.CTkLabel(slider_frame, text="Függőleges pozíció", font=ctk.CTkFont(size=12), text_color="grey").pack()
        self.pan_y_slider = ctk.CTkSlider(slider_frame, from_=0.0, to=1.0, command=self._update_photo_properties)
        self.pan_y_slider.pack(fill="x", padx=5, pady=(0, 10))

        ctk.CTkLabel(slider_frame, text="Keret mérete", font=ctk.CTkFont(size=12, weight="bold"), text_color="grey").pack()
        ctk.CTkLabel(slider_frame, text="Szélesség", font=ctk.CTkFont(size=12), text_color="grey").pack()
        self.width_slider = ctk.CTkSlider(slider_frame, from_=0.1, to=1.0, command=self._update_photo_size_from_sliders)
        self.width_slider.pack(fill="x", padx=5, pady=(0, 10))
        ctk.CTkLabel(slider_frame, text="Magasság", font=ctk.CTkFont(size=12), text_color="grey").pack()
        self.height_slider = ctk.CTkSlider(slider_frame, from_=0.1, to=1.0, command=self._update_photo_size_from_sliders)
        self.height_slider.pack(fill="x", padx=5, pady=(0, 10))
        
        effects_frame = ctk.CTkFrame(tools_scroll_area, fg_color="transparent")
        effects_frame.pack(pady=5, fill="x", padx=10)
        ctk.CTkLabel(effects_frame, text="Kép effektek", font=ctk.CTkFont(size=12, weight="bold"), text_color="grey").pack()
        ctk.CTkLabel(effects_frame, text="Fényerő", font=ctk.CTkFont(size=12), text_color="grey").pack()
        self.brightness_slider = ctk.CTkSlider(effects_frame, from_=0.5, to=1.5, command=self._update_photo_properties)
        self.brightness_slider.pack(fill="x", padx=5, pady=(0, 10)); self.brightness_slider.set(1.0)
        ctk.CTkLabel(effects_frame, text="Kontraszt", font=ctk.CTkFont(size=12), text_color="grey").pack()
        self.contrast_slider = ctk.CTkSlider(effects_frame, from_=0.5, to=1.5, command=self._update_photo_properties)
        self.contrast_slider.pack(fill="x", padx=5, pady=(0, 10)); self.contrast_slider.set(1.0)
        ctk.CTkLabel(effects_frame, text="Színerősség", font=ctk.CTkFont(size=12), text_color="grey").pack()
        self.saturation_slider = ctk.CTkSlider(effects_frame, from_=0.0, to=2.0, command=self._update_photo_properties)
        self.saturation_slider.pack(fill="x", padx=5, pady=(0, 10)); self.saturation_slider.set(1.0)
        self.grayscale_checkbox = ctk.CTkCheckBox(effects_frame, text="Fekete-fehér", command=self._update_photo_properties)
        self.grayscale_checkbox.pack(pady=5)
        
        tools_frame = ctk.CTkFrame(tools_scroll_area, fg_color="transparent")
        tools_frame.pack(pady=5, fill="x", padx=10)
        tools = [
            ("🎨 Háttér (Szín/Kép)", self.set_background),
            ("📝 Szöveg", self.add_text), 
            ("🖼️ Képkeret", self.add_frame), 
            ("🖼️ Oldalkerete", self.add_page_frame),
            ("📏 Oldalméret módosítása", self.change_page_size), 
            ("🔄 Elrendezés váltása", self.change_current_page_layout),
            ("🖼️ Kép cseréje", self._replace_photo),
            ("🔼 Előrehozás", self._bring_photo_forward),
            ("🔽 Hátraküldés", self._send_photo_backward),
            ("⏫ Legelőre hozás", self._bring_photo_to_front),
            ("⏬ Leghátra küldés", self._send_photo_to_back),
            ("🖼️+ Kép hozzáadása", self._add_photo_placeholder), 
            ("🖼️- Kép törlése", self._delete_photo_placeholder), 
            ("🗑️ Oldal törlése", self.delete_page)
        ]
        for text, command in tools:
            ctk.CTkButton(tools_frame, text=text, command=command, height=35, font=ctk.CTkFont(size=12), corner_radius=10, fg_color=self.colors['button_bg'], text_color=self.colors['text_secondary'], hover_color='#F0F0F0').pack(pady=4, fill="x")

    def _bring_photo_to_front(self):
        """A kiválasztott képet a rétegsorrend legtetejére helyezi."""
        if self.selected_photo_index is None:
            messagebox.showwarning("Nincs Kijelölés", "Kérlek, válassz ki egy képet a művelethez!")
            return

        page_key = str(self.current_page)
        if page_key not in self.z_order:
             self.z_order[page_key] = list(range(len(self.pages[self.current_page]['photos'])))

        order = self.z_order[page_key]
        if self.selected_photo_index in order:
            order.remove(self.selected_photo_index)
        order.append(self.selected_photo_index) # A lista végére helyezzük, ami a legfelső réteg
        self.refresh_editor_view()

    def _send_photo_to_back(self):
        """A kiválasztott képet a rétegsorrend legaljára helyezi."""
        if self.selected_photo_index is None:
            messagebox.showwarning("Nincs Kijelölés", "Kérlek, válassz ki egy képet a művelethez!")
            return

        page_key = str(self.current_page)
        if page_key not in self.z_order:
            self.z_order[page_key] = list(range(len(self.pages[self.current_page]['photos'])))

        order = self.z_order[page_key]
        if self.selected_photo_index in order:
            order.remove(self.selected_photo_index)
        order.insert(0, self.selected_photo_index) # A lista elejére helyezzük, ami a legalsó réteg
        self.refresh_editor_view()


    def refresh_editor_view(self):
        if not self.editor_ui_built or not self.pages:
            return

        current_page_data = self.pages[self.current_page]
        title_text = f"Fotókönyv szerkesztő - Oldal {self.current_page + 1} ({len(current_page_data.get('photos',[]))} képes)"
        self.title_label.configure(text=title_text)

        for widget in self.left_panel_scroll.winfo_children():
            widget.destroy()
        
        for i, page in enumerate(self.pages):
            page_frame = ctk.CTkFrame(self.left_panel_scroll, height=90, fg_color=self.colors['accent'] if i == self.current_page else self.colors['bg_secondary'], corner_radius=15)
            page_frame.pack(pady=5, fill="x"); page_frame.pack_propagate(False)
            page_label = ctk.CTkLabel(page_frame, text=f"{i + 1}. oldal\n({len(page.get('photos',[]))} kép)", font=ctk.CTkFont(size=11), text_color="white")
            page_label.pack(expand=True)
            page_frame.bind("<Button-1>", lambda e, idx=i: self.select_page(idx)); page_label.bind("<Button-1>", lambda e, idx=i: self.select_page(idx))
        
        # A renderelés előtt a vászon frissítése biztosítja a helyes méreteket
        self.root.update_idletasks() 
        self._render_page_content()
        
        current_selection = self.selected_photo_index
        self._deselect_all()
        if current_selection is not None:
                 self._select_photo(current_selection)

    def _render_page_content(self):
        self.canvas.delete("all")
        self.widget_to_canvas_item.clear()
        self.photo_frames.clear()
        self.text_widgets.clear()
        
        self._render_background()
        self.create_photo_layout()
        self._render_text_boxes()
        self._render_page_frame()

    # --- CANVAS-ALAPÚ RENDERELŐ FÜGGVÉNYEK ---

    def _get_page_draw_area(self):
        """Kiszámolja a lap arányainak megfelelő rajzolási területet a vásznon belül."""
        # ÚJ: Árnyék mérete pixelben
        shadow_offset = 15 

        canvas_w = self.canvas.winfo_width() - (shadow_offset * 2)
        canvas_h = self.canvas.winfo_height() - (shadow_offset * 2)

        page_data = self.pages[self.current_page]
        page_pixel_w, page_pixel_h = page_data.get('size', self.DEFAULT_BOOK_SIZE_PIXELS)
        
        if page_pixel_h == 0 or canvas_h <= 0:
            return 0, 0, self.canvas.winfo_width(), self.canvas.winfo_height()

        page_ratio = page_pixel_w / page_pixel_h
        canvas_ratio = canvas_w / canvas_h

        if page_ratio > canvas_ratio:
            draw_w = canvas_w
            draw_h = canvas_w / page_ratio
        else:
            draw_h = canvas_h
            draw_w = canvas_h * page_ratio
            
        # Az eltolást most már az eredeti vászonmérethez és az árnyékhoz is igazítjuk
        offset_x = (self.canvas.winfo_width() - draw_w) / 2
        offset_y = (self.canvas.winfo_height() - draw_h) / 2
        
        return int(offset_x), int(offset_y), int(draw_w), int(draw_h)

    def _render_background(self):
        offset_x, offset_y, draw_w, draw_h = self._get_page_draw_area()
        if draw_w <= 1 or draw_h <= 1: return

        page_data = self.pages[self.current_page]
        bg_setting = page_data.get('background')

        if self.canvas_bg_item:
            self.canvas.delete(self.canvas_bg_item)
            self.canvas_bg_item = None
            self.bg_photo_image = None

        try:
            # --- ÁRNYÉK ÉS HÁTTÉR LÉTREHOZÁSA KÉPKÉNT ---
            shadow_blur = 15  # Az elmosás mértéke
            shadow_color = '#282828' # Sötétszürke árnyék

            # 1. Létrehozunk egy nagyobb, átlátszó vásznat az árnyéknak
            shadow_canvas = Image.new('RGBA', (draw_w + shadow_blur*2, draw_h + shadow_blur*2), (0, 0, 0, 0))
            shadow_draw = ImageDraw.Draw(shadow_canvas)

            # 2. Rajzolunk egy fekete téglalapot a közepére (ez lesz az elmosott árnyék)
            shadow_draw.rectangle(
                (shadow_blur, shadow_blur, draw_w + shadow_blur, draw_h + shadow_blur),
                fill=shadow_color
            )

            # 3. Alkalmazzuk az elmosás effektet
            shadow_canvas = shadow_canvas.filter(ImageFilter.GaussianBlur(radius=shadow_blur / 2))

            # 4. Létrehozzuk a tényleges oldal hátterét
            if isinstance(bg_setting, dict) and bg_setting.get('type') == 'image':
                img_path = bg_setting.get('path')
                if img_path and os.path.exists(img_path):
                    page_bg_img = Image.open(img_path).convert("RGBA").resize((draw_w, draw_h), Image.LANCZOS)
                else: # Ha a kép nem található, fehér lesz
                    page_bg_img = Image.new('RGBA', (draw_w, draw_h), 'white')
            else:
                bg_color = bg_setting if isinstance(bg_setting, str) and bg_setting.startswith('#') else self.colors['card_bg']
                page_bg_img = Image.new('RGBA', (draw_w, draw_h), bg_color)

            # 5. A kész oldal hátterét ráillesztjük az árnyék közepére
            shadow_canvas.paste(page_bg_img, (shadow_blur, shadow_blur))

            # 6. A végső, árnyékkal ellátott képet jelenítjük meg
            self.bg_photo_image = ImageTk.PhotoImage(shadow_canvas)
            self.canvas_bg_item = self.canvas.create_image(
                offset_x - shadow_blur,  # Az eltolást korrigáljuk az árnyék méretével
                offset_y - shadow_blur, 
                image=self.bg_photo_image, 
                anchor="nw", 
                tags="background"
            )

        except Exception as e:
            print(f"HIBA a háttér renderelésekor: {e}")
            traceback.print_exc()
            self.canvas.create_rectangle(offset_x, offset_y, offset_x + draw_w, offset_y + draw_h, fill="red", outline="")

    def set_background_image(self):
        filename = filedialog.askopenfilename(
            title="Válassz háttérképet",
            filetypes=[("Képfájlok", "*.jpg *.jpeg *.png"), ("Minden fájl", "*.*")]
        )
        if filename:
            self.pages[self.current_page]['background'] = {'type': 'image', 'path': filename}
            self.refresh_editor_view()
    
    def set_background(self):
        """Felugró ablakot nyit a háttér beállításához, ami már görgethető, ha a tartalom túl nagy."""
        color_picker = ctk.CTkToplevel(self.root)
        color_picker.title("Háttér beállítása")
        color_picker.geometry("400x500")
        color_picker.transient(self.root)
        color_picker.grab_set()

        # Létrehozunk egy fő görgethető keretet, amibe minden más elem kerül.
        main_scroll_frame = ctk.CTkScrollableFrame(color_picker)
        main_scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

        def _apply_background(setting):
            self.pages[self.current_page]['background'] = setting
            color_picker.destroy()
            self.refresh_editor_view()

        def _upload_background_image():
            filename = filedialog.askopenfilename(
                title="Válassz háttérképet",
                filetypes=[("Képfájlok", "*.jpg *.jpeg *.png"), ("Minden fájl", "*.*")]
            )
            if filename:
                _apply_background({'type': 'image', 'path': filename})

        # Az elemek szülője mostantól a 'main_scroll_frame'
        ctk.CTkLabel(main_scroll_frame, text="Beépített hátterek", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(15, 5))
        preset_bg_frame = ctk.CTkFrame(main_scroll_frame, fg_color="transparent")
        preset_bg_frame.pack(pady=5, padx=10)
        
        backgrounds_path = os.path.join(self.assets_path, "backgrounds")
        if os.path.exists(backgrounds_path):
            preset_files = [f for f in os.listdir(backgrounds_path) if f.lower().endswith(('.png', '.jpg'))]
            for i, fname in enumerate(preset_files):
                fpath = os.path.join(backgrounds_path, fname)
                try:
                    thumb = ctk.CTkImage(Image.open(fpath), size=(60,60))
                    btn = ctk.CTkButton(preset_bg_frame, image=thumb, text="", width=60, height=60,
                                        command=lambda p=fpath: _apply_background({'type': 'image', 'path': p}))
                    btn.grid(row=i // 4, column=i % 4, padx=5, pady=5)
                except Exception as e:
                    print(f"Hiba a beépített háttér betöltésekor ({fname}): {e}")

        ctk.CTkLabel(main_scroll_frame, text="Színek", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(15, 5))
        palette_frame = ctk.CTkFrame(main_scroll_frame, fg_color="transparent")
        palette_frame.pack(pady=5, padx=10)
        colors_list = ['#FFFFFF', '#F0F0F0', '#D3E3F1', '#D1F0D1', '#F5E6D3', '#E6D3F5', '#FFDDC1', '#FFD1D1']
        for i, color in enumerate(colors_list):
            ctk.CTkButton(palette_frame, text="", fg_color=color, width=40, height=40, corner_radius=8, command=lambda c=color: _apply_background(c)).grid(row=i // 4, column=i % 4, padx=10, pady=10)
        
        ctk.CTkLabel(main_scroll_frame, text="Vagy adj meg egyéni színt:", font=ctk.CTkFont(size=14)).pack(pady=(10, 5))
        custom_color_frame = ctk.CTkFrame(main_scroll_frame, fg_color="transparent")
        custom_color_frame.pack(pady=5, padx=20, fill="x")
        custom_color_entry = ctk.CTkEntry(custom_color_frame, placeholder_text="#RRGGBB")
        custom_color_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(custom_color_frame, text="Alkalmaz", width=80, command=lambda: _apply_background(custom_color_entry.get())).pack(side="left")

        ctk.CTkLabel(main_scroll_frame, text="Vagy tölts fel saját képet:", font=ctk.CTkFont(size=14)).pack(pady=(15, 5))
        ctk.CTkButton(main_scroll_frame, text="🖼️ Háttérkép feltöltése...", command=_upload_background_image).pack(pady=5, padx=20, fill="x")
        
        ctk.CTkButton(main_scroll_frame, text="Háttér eltávolítása", command=lambda: _apply_background(None)).pack(pady=15, padx=20, fill="x")

    def _render_page_frame(self):
        offset_x, offset_y, draw_w, draw_h = self._get_page_draw_area()
        if draw_w <= 1 or draw_h <= 1: return

        current_page_data = self.pages[self.current_page]
        page_frame_path = current_page_data.get('page_frame_path')
        
        if self.canvas_page_frame_item:
            self.canvas.delete(self.canvas_page_frame_item)
            self.canvas_page_frame_item = None
            self.page_frame_photo_image = None

        if page_frame_path:
            thickness_ratio = current_page_data.get('page_frame_thickness', 0.05)
            frame_img = None
            if page_frame_path.startswith('preset_'): 
                frame_img = self._create_preset_frame(page_frame_path, (draw_w, draw_h), thickness_ratio)
            elif os.path.exists(page_frame_path): 
                frame_img = Image.open(page_frame_path).convert("RGBA").resize((draw_w, draw_h), Image.LANCZOS)
            
            if frame_img:
                self.page_frame_photo_image = ImageTk.PhotoImage(frame_img)
                self.canvas_page_frame_item = self.canvas.create_image(offset_x, offset_y, image=self.page_frame_photo_image, anchor="nw", tags="page_frame")

    def _create_preset_frame(self, preset_name, size, thickness_ratio=0.05):
        width, height = size
        frame_thickness = int(min(width, height) * thickness_ratio)
        if frame_thickness < 1: frame_thickness = 1
        color_map = {'preset_black': (0, 0, 0, 200), 'preset_white': (255, 255, 255, 200), 'preset_gold': (212, 175, 55, 220)}
        color = color_map.get(preset_name, (0,0,0,0))
        frame_image = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(frame_image)
        for i in range(frame_thickness):
            draw.rectangle((i, i, width - 1 - i, height - 1 - i), outline=color, width=1)
        return frame_image

    def create_photo_layout(self):
        if not hasattr(self.pages[self.current_page], 'get'): return
        photos_data = self.pages[self.current_page].get('photos', [])
        offset_x, offset_y, draw_w, draw_h = self._get_page_draw_area()
        if draw_w <= 1 or draw_h <= 1: return

        self.photo_frames = [None] * len(photos_data)
        
        page_key = str(self.current_page)
        if page_key not in self.z_order or len(self.z_order[page_key]) != len(photos_data):
            self.z_order[page_key] = list(range(len(photos_data)))
        
        ordered_indices = self.z_order[page_key]
        valid_indices = [i for i in ordered_indices if i < len(photos_data)]

        for i in valid_indices:
            photo_data = photos_data[i]
            photo_frame = ctk.CTkFrame(self.canvas, fg_color="#CCCCCC", corner_radius=10, border_width=0)
            
            self.photo_frames[i] = photo_frame
            
            frame_w = int(photo_data['relwidth'] * draw_w)
            frame_h = int(photo_data['relheight'] * draw_h)
            abs_x = offset_x + int(photo_data['relx'] * draw_w)
            abs_y = offset_y + int(photo_data['rely'] * draw_h)
            
            canvas_item_id = self.canvas.create_window(abs_x, abs_y, window=photo_frame, width=frame_w, height=frame_h, anchor='nw', tags="photo")
            self.widget_to_canvas_item[photo_frame] = canvas_item_id
            
            photo_frame.bind("<ButtonPress-1>", lambda e, index=i: self._on_widget_press(e, 'photo', index))
            photo_frame.bind("<B1-Motion>", lambda e: self._on_widget_drag(e))
            photo_frame.bind("<ButtonRelease-1>", lambda e: self._on_widget_release(e))

            self.display_photo_placeholder(photo_frame, photo_data, i, is_update=False)

    def display_photo_placeholder(self, parent_frame, photo_data, photo_index, is_update=False):
        if not is_update:
            for widget in parent_frame.winfo_children(): widget.destroy()
        
        photo_path = photo_data.get('path')
        if not photo_path or not os.path.exists(photo_path):
            add_btn = ctk.CTkButton(parent_frame, text="+", font=ctk.CTkFont(size=24), fg_color=self.colors['accent'], hover_color='#8A9654', command=lambda idx=photo_index: self.add_photo_to_slot(idx))
            add_btn.place(relx=0.5, rely=0.5, anchor="center")
            return

        try:
            key = str((self.current_page, photo_index))
            props = self.photo_properties.get(key, {})
            parent_frame.update_idletasks()

            # --- ÚJ LOGIKA A KERET MÉRETÉNEK DINAMIKUS BEÁLLÍTÁSÁHOZ ---
            fit_mode = props.get('fit_mode', 'fill')
            _, _, draw_w, draw_h = self._get_page_draw_area()

            # Először az elrendezésben definiált "mester" méretet használjuk
            master_rel_w = photo_data.get('layout_relwidth', photo_data['relwidth'])
            master_rel_h = photo_data.get('layout_relheight', photo_data['relheight'])
            
            frame_w = int(master_rel_w * draw_w)
            frame_h = int(master_rel_h * draw_h)

            original_img = Image.open(photo_path) # Csak az arányok miatt kell betölteni

            # Ha "Beleillesztés" módban vagyunk, a keret méretét a kép arányaihoz igazítjuk
            if fit_mode == 'fit':
                img_ratio = original_img.width / original_img.height
                frame_ratio = frame_w / frame_h if frame_h > 0 else 1
                
                if img_ratio > frame_ratio: # A kép szélesebb, mint a keret
                    frame_h = int(frame_w / img_ratio)
                else: # A kép magasabb, mint a keret
                    frame_w = int(frame_h * img_ratio)
            
            # Frissítjük a widget méretét a vásznon
            canvas_item_id = self.widget_to_canvas_item.get(parent_frame)
            if canvas_item_id:
                self.canvas.itemconfig(canvas_item_id, width=frame_w, height=frame_h)
            parent_frame.update_idletasks() # Várakozás, hogy az új méret érvénybe lépjen

            # --- EDDIGI LOGIKA INNENTŐL FOLYTATÓDIK, DE MÁR A HELYES `frame_w` ÉS `frame_h` ÉRTÉKEKKEL ---
            if frame_w <= 1 or frame_h <= 1: return

            original_img = original_img.convert("RGBA") # Újra konvertáljuk, ha kell
            
            if props.get('grayscale', False):
                original_img = original_img.convert('L').convert('RGBA')
            enhancer = ImageEnhance.Brightness(original_img); original_img = enhancer.enhance(props.get('brightness', 1.0))
            enhancer = ImageEnhance.Contrast(original_img); original_img = enhancer.enhance(props.get('contrast', 1.0))
            enhancer = ImageEnhance.Color(original_img); original_img = enhancer.enhance(props.get('saturation', 1.0))

            zoom, pan_x, pan_y = props.get('zoom', 1.0), props.get('pan_x', 0.5), props.get('pan_y', 0.5)
            
            if fit_mode == 'fill':
                img_ratio = original_img.width / original_img.height; frame_ratio = frame_w / frame_h
                if img_ratio > frame_ratio: new_h, new_w = int(frame_h * zoom), int(frame_h * zoom * img_ratio)
                else: new_w, new_h = int(frame_w * zoom), int(frame_w * zoom / img_ratio)
                if new_w < frame_w: new_w = frame_w; new_h = int(new_w / img_ratio)
                if new_h < frame_h: new_h = frame_h; new_w = int(new_h * img_ratio)
                zoomed_img = original_img.resize((new_w, new_h), Image.LANCZOS)
                extra_w, extra_h = max(0, new_w - frame_w), max(0, new_h - frame_h)
                crop_x, crop_y = int(extra_w * pan_x), int(extra_h * pan_y)
                final_image = zoomed_img.crop((crop_x, crop_y, crop_x + frame_w, crop_y + frame_h))
            else: # 'fit' mód
                fit_w, fit_h = frame_w, frame_h # A keret már a helyes méretű
                new_w, new_h = int(fit_w * zoom), int(fit_h * zoom)
                if new_w < 1 or new_h < 1: new_w, new_h = 1, 1
                resized_img = original_img.resize((new_w, new_h), Image.LANCZOS)
                final_image = Image.new('RGBA', (frame_w, frame_h), (0, 0, 0, 0))
                extra_w, extra_h = max(0, new_w - frame_w), max(0, new_h - frame_h)
                paste_x = (frame_w - new_w) // 2 - int(extra_w * (pan_x - 0.5))
                paste_y = (frame_h - new_h) // 2 - int(extra_h * (pan_y - 0.5))
                final_image.paste(resized_img, (paste_x, paste_y), resized_img)

            frame_path = props.get('frame_path')
            if frame_path:
                # ... (a keret logika változatlan) ...
                thickness_ratio = props.get('frame_thickness', 0.05)
                frame_img = None
                if frame_path.startswith('preset_'): frame_img = self._create_preset_frame(frame_path, (frame_w, frame_h), thickness_ratio)
                elif os.path.exists(frame_path): frame_img = Image.open(frame_path).convert("RGBA")
                if frame_img:
                    f_scale = props.get('frame_scale', 1.0); f_off_x = props.get('frame_offset_x', 0); f_off_y = props.get('frame_offset_y', 0)
                    new_fw, new_fh = int(frame_w * f_scale), int(frame_h * f_scale)
                    resized_frame = frame_img.resize((new_fw, new_fh), Image.LANCZOS)
                    paste_x, paste_y = (frame_w - new_fw) // 2 + f_off_x, (frame_h - new_fh) // 2 + f_off_y
                    final_image.paste(resized_frame, (paste_x, paste_y), resized_frame)
            
            final_ctk_image = ctk.CTkImage(light_image=final_image.convert("RGB"), dark_image=final_image.convert("RGB"), size=(frame_w, frame_h))
            img_label = None
            if is_update and len(parent_frame.winfo_children()) > 0 and isinstance(parent_frame.winfo_children()[0], ctk.CTkLabel):
                img_label = parent_frame.winfo_children()[0]
            
            if img_label: img_label.configure(image=final_ctk_image)
            else:
                for widget in parent_frame.winfo_children(): widget.destroy()
                img_label = ctk.CTkLabel(parent_frame, image=final_ctk_image, text="")
                img_label.pack(fill="both", expand=True)
                img_label.bind("<ButtonPress-1>", lambda e, idx=photo_index: self._on_widget_press(e, 'photo', idx))
                img_label.bind("<B1-Motion>", lambda e: self._on_widget_drag(e))
                img_label.bind("<ButtonRelease-1>", lambda e: self._on_widget_release(e))

        except Exception as e:
            print(f"HIBA a kép megjelenítésekor: {e}\n{traceback.format_exc()}")
            ctk.CTkLabel(parent_frame, text="Hiba a kép\nbetöltésekor", text_color="red").place(relx=0.5, rely=0.5, anchor="center")

    def add_photo_to_slot(self, photo_index):
        filename = filedialog.askopenfilename(title="Válassz fotót", filetypes=[("Képfájlok", "*.jpg *.jpeg *.png *.gif *.bmp")])
        if filename:
            try:
                self.pages[self.current_page]['photos'][photo_index]['path'] = filename
                if filename not in self.uploaded_photos:
                    self.uploaded_photos.append(filename)
                
                frame_to_update = self.photo_frames[photo_index]
                data_to_update = self.pages[self.current_page]['photos'][photo_index]
                self.display_photo_placeholder(frame_to_update, data_to_update, photo_index, is_update=False)
            except IndexError:
                messagebox.showerror("Hiba", "Belső hiba történt a fotó hozzáadásakor. Kérem próbálja újra.")
                self.refresh_editor_view()

    def _add_photo_placeholder(self):
        new_photo = {
            'path': None, 
            'relx': 0.35, 'rely': 0.3, 
            'relwidth': 0.3, 'relheight': 0.4,
            'layout_relwidth': 0.3, 'layout_relheight': 0.4
        }
        photo_list = self.pages[self.current_page]['photos']
        photo_list.append(new_photo)
        
        new_index = len(photo_list) - 1

        page_key = str(self.current_page)
        if page_key not in self.z_order:
            self.z_order[page_key] = list(range(len(photo_list)))
        else:
            self.z_order[page_key].append(new_index)
        
        self.refresh_editor_view()

    def _update_photo_size_from_sliders(self, value=None):
        if self.selected_photo_index is None: return
        
        photo_data = self.pages[self.current_page]['photos'][self.selected_photo_index]
        photo_frame = self.photo_frames[self.selected_photo_index]
        
        _, _, draw_w, draw_h = self._get_page_draw_area()
        
        new_relwidth = self.width_slider.get()
        new_relheight = self.height_slider.get()
        
        # Mentsük el a manuális átméretezést mint új alapértelmezett elrendezési méret
        photo_data['relwidth'] = new_relwidth
        photo_data['relheight'] = new_relheight
        photo_data['layout_relwidth'] = new_relwidth
        photo_data['layout_relheight'] = new_relheight
        
        canvas_item_id = self.widget_to_canvas_item.get(photo_frame)
        if canvas_item_id:
            self.canvas.itemconfig(canvas_item_id, width=int(new_relwidth * draw_w), height=int(new_relheight * draw_h))
            
        self.display_photo_placeholder(photo_frame, photo_data, self.selected_photo_index, is_update=True)

    def _delete_photo_placeholder(self):
        """Törli a kiválasztott képkeretet és a hozzá tartozó tulajdonságokat,
        majd helyesen újraindexeli a többi kép tulajdonságait az oldalon."""
        if self.selected_photo_index is None:
            messagebox.showwarning("Törlés", "Nincs képkeret kiválasztva a törléshez.")
            return

        index_to_delete = self.selected_photo_index
        
        # 1. Töröljük a fotó adatait az oldal listájából
        self.pages[self.current_page]['photos'].pop(index_to_delete)
        
        # 2. Javítjuk a Z-sorrendet (rétegsorrend)
        page_key = str(self.current_page)
        if page_key in self.z_order:
            order = self.z_order[page_key]
            if index_to_delete in order:
                order.remove(index_to_delete)
            # A törölt index utáni elemek indexét eggyel csökkentjük
            self.z_order[page_key] = [idx - 1 if idx > index_to_delete else idx for idx in order]

        # 3. JAVÍTÁS: Újraindexeljük a `photo_properties` szótárat
        new_properties = {}
        for key_str, props in self.photo_properties.items():
            try:
                # A kulcsot (pl. '(0, 2)') felbontjuk oldal- és fotóindexre
                page_idx, photo_idx = tuple(map(int, key_str.strip('()').split(',')))
            except (ValueError, TypeError):
                new_properties[key_str] = props # Ha a kulcs formátuma más, megtartjuk
                continue

            if page_idx != self.current_page:
                new_properties[key_str] = props # Más oldalak tulajdonságait érintetlenül hagyjuk
            else:
                # Az aktuális oldalon lévő tulajdonságokat kezeljük
                if photo_idx < index_to_delete:
                    new_properties[key_str] = props # A törölt elem előttiakat megtartjuk
                elif photo_idx > index_to_delete:
                    # A törölt elem utániaknak új, eggyel kisebb indexet adunk
                    new_key = str((page_idx, photo_idx - 1))
                    new_properties[new_key] = props
        
        self.photo_properties = new_properties

        self._deselect_all()
        self.refresh_editor_view()

    def _replace_photo(self):
        """A kiválasztott kép cseréje egy újra, a beállítások megtartásával."""
        if self.selected_photo_index is None:
            messagebox.showwarning("Nincs Kijelölés", "Kérlek, először válassz ki egy képet a cseréhez!")
            return

        filename = filedialog.askopenfilename(
            title="Válassz egy új fotót",
            filetypes=[("Képfájlok", "*.jpg *.jpeg *.png *.gif *.bmp")]
        )
        
        if not filename:
            return

        try:
            self.pages[self.current_page]['photos'][self.selected_photo_index]['path'] = filename
            
            frame_to_update = self.photo_frames[self.selected_photo_index]
            data_to_update = self.pages[self.current_page]['photos'][self.selected_photo_index]
            self.display_photo_placeholder(frame_to_update, data_to_update, self.selected_photo_index, is_update=False)

        except IndexError:
            messagebox.showerror("Hiba", "Belső hiba történt a fotó cseréjekor. Kérem próbálja újra.")
            self.refresh_editor_view()



    def _bring_photo_forward(self):
        """A kiválasztott képet előrébb hozza a rétegsorrendben."""
        if self.selected_photo_index is None:
            messagebox.showwarning("Nincs Kijelölés", "Kérlek, válassz ki egy képet az előrehozáshoz!")
            return

        if str(self.current_page) not in self.z_order:
            self.z_order[str(self.current_page)] = list(range(len(self.pages[self.current_page]['photos'])))

        order = self.z_order[str(self.current_page)]
        
        try:
            current_pos = order.index(self.selected_photo_index)
        except ValueError:
            order.append(self.selected_photo_index)
            current_pos = order.index(self.selected_photo_index)

        if current_pos < len(order) - 1:
            order[current_pos], order[current_pos + 1] = order[current_pos + 1], order[current_pos]
            self.refresh_editor_view()

    def _send_photo_backward(self):
        """A kiválasztott képet hátrébb küldi a rétegsorrendben."""
        if self.selected_photo_index is None:
            messagebox.showwarning("Nincs Kijelölés", "Kérlek, válassz ki egy képet a hátraküldéshez!")
            return
            
        if str(self.current_page) not in self.z_order:
            self.z_order[str(self.current_page)] = list(range(len(self.pages[self.current_page]['photos'])))

        order = self.z_order[str(self.current_page)]
        
        try:
            current_pos = order.index(self.selected_photo_index)
        except ValueError:
            order.append(self.selected_photo_index)
            current_pos = order.index(self.selected_photo_index)

        if current_pos > 0:
            order[current_pos], order[current_pos - 1] = order[current_pos - 1], order[current_pos]
            self.refresh_editor_view()

    def add_frame(self):
        if self.selected_photo_index is None:
            messagebox.showwarning("Nincs kiválasztott kép", "Kérlek, először kattints egy képre a szerkesztéshez!")
            return
        if self.frame_editor_window is not None and self.frame_editor_window.winfo_exists():
            self.frame_editor_window.focus()
            return
        
        self.frame_editor_window = ctk.CTkToplevel(self.root)
        self.frame_editor_window.title("Képkeret szerkesztése")
        self.frame_editor_window.geometry("350x550")
        self.frame_editor_window.transient(self.root)
        self.frame_editor_window.attributes("-topmost", True)

        # --- JAVÍTÁS: Létrehozunk egy fő görgethető keretet ---
        # Minden mást ebbe a keretbe fogunk pakolni.
        main_scroll_frame = ctk.CTkScrollableFrame(self.frame_editor_window)
        main_scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
        # --------------------------------------------------------
        
        ctk.CTkLabel(main_scroll_frame, text="Beépített keretek", font=ctk.CTkFont(weight="bold")).pack(pady=(10, 5))
        
        preset_frame_container = ctk.CTkFrame(main_scroll_frame) # A szülő mostantól a main_scroll_frame
        preset_frame_container.pack(pady=5, padx=5, fill="x")

        preset_frame_ui = ctk.CTkFrame(preset_frame_container)
        preset_frame_ui.pack(pady=5, padx=0, fill="x")
        presets = [("Fekete", "preset_black"), ("Fehér", "preset_white"), ("Arany", "preset_gold")]
        for i, (name, path) in enumerate(presets):
            ctk.CTkButton(preset_frame_ui, text=name, command=lambda p=path: self._apply_frame(p)).grid(row=0, column=i, padx=5, pady=5, sticky="ew")
        preset_frame_ui.grid_columnconfigure((0, 1, 2), weight=1)

        frames_path = os.path.join(self.assets_path, "frames")
        if os.path.exists(frames_path):
            custom_preset_frame = ctk.CTkFrame(preset_frame_container) # Ez már lehet sima Frame
            custom_preset_frame.pack(pady=5, padx=0, fill="x")
            preset_files = [f for f in os.listdir(frames_path) if f.lower().endswith('.png')]
            for i, fname in enumerate(preset_files):
                fpath = os.path.join(frames_path, fname)
                try:
                    thumb = ctk.CTkImage(Image.open(fpath), size=(40, 40))
                    btn = ctk.CTkButton(custom_preset_frame, image=thumb, text="", width=60, height=60, command=lambda p=fpath: self._apply_frame(p))
                    btn.grid(row=i // 4, column=i % 4, padx=5, pady=5)
                except Exception as e:
                    print(f"Hiba a beépített keret betöltésekor ({fname}): {e}")

        ctk.CTkButton(main_scroll_frame, text="Saját keret feltöltése...", command=lambda: self._apply_frame(self._upload_custom_frame_path())).pack(pady=(10, 5), padx=5, fill="x")
        ctk.CTkLabel(main_scroll_frame, text="Beállítások", font=ctk.CTkFont(weight="bold")).pack(pady=(15, 5))
        
        self.slider_panel = ctk.CTkFrame(main_scroll_frame) # A szülő mostantól a main_scroll_frame
        self.slider_panel.pack(pady=5, padx=5, fill="both", expand=True)
        ctk.CTkLabel(self.slider_panel, text="Vastagság (beépített kereteknél)").pack()
        self.frame_thickness_slider = ctk.CTkSlider(self.slider_panel, from_=0.01, to=0.2, command=self._update_photo_properties)
        self.frame_thickness_slider.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(self.slider_panel, text="Méret").pack()
        self.frame_scale_slider = ctk.CTkSlider(self.slider_panel, from_=0.5, to=1.5, command=self._update_photo_properties)
        self.frame_scale_slider.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(self.slider_panel, text="Vízszintes eltolás").pack()
        self.frame_offset_x_slider = ctk.CTkSlider(self.slider_panel, from_=-100, to=100, number_of_steps=200, command=self._update_photo_properties)
        self.frame_offset_x_slider.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(self.slider_panel, text="Függőleges eltolás").pack()
        self.frame_offset_y_slider = ctk.CTkSlider(self.slider_panel, from_=-100, to=100, number_of_steps=200, command=self._update_photo_properties)
        self.frame_offset_y_slider.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkButton(main_scroll_frame, text="Keret eltávolítása", fg_color="#D32F2F", hover_color="#B71C1C", command=lambda: self._apply_frame(None)).pack(pady=10, padx=5, fill="x")
        self.update_frame_editor_ui()

    def _apply_frame(self, frame_path):
        if self.selected_photo_index is None: return
        key = str((self.current_page, self.selected_photo_index))
        if key not in self.photo_properties: self.photo_properties[key] = {}
        self.photo_properties[key]['frame_path'] = frame_path
        self.photo_properties[key]['frame_scale'] = 1.0; self.photo_properties[key]['frame_offset_x'] = 0; self.photo_properties[key]['frame_offset_y'] = 0
        self.photo_properties[key]['frame_thickness'] = 0.05
        
        if self.frame_editor_window and self.frame_editor_window.winfo_exists(): self.update_frame_editor_ui()
        self._update_photo_properties()

    def update_frame_editor_ui(self):
        if not (self.frame_editor_window and self.frame_editor_window.winfo_exists()): return
        key = str((self.current_page, self.selected_photo_index))
        props = self.photo_properties.get(key, {})
        
        sliders = [self.frame_scale_slider, self.frame_offset_x_slider, self.frame_offset_y_slider, self.frame_thickness_slider]
        
        if self.selected_photo_index is not None and props.get('frame_path'):
            for slider in sliders: slider.configure(state="normal")
            self.frame_scale_slider.set(props.get('frame_scale', 1.0))
            self.frame_offset_x_slider.set(props.get('frame_offset_x', 0))
            self.frame_offset_y_slider.set(props.get('frame_offset_y', 0))
            self.frame_thickness_slider.set(props.get('frame_thickness', 0.05))
            
            if not props.get('frame_path', '').startswith('preset_'):
                self.frame_thickness_slider.configure(state="disabled")

        else:
            for slider in sliders: slider.configure(state="disabled")
            self.frame_scale_slider.set(1.0); self.frame_offset_x_slider.set(0); self.frame_offset_y_slider.set(0)
            self.frame_thickness_slider.set(0.05)
            
    # --- KÉPKERET ÉS OLDALKERET METÓDUSOK ---

    def add_page_frame(self):
        """Felugró ablakot nyit az oldalkeretet beállításához, méretezési és eltolási opciókkal."""
        if self.page_frame_editor_window is not None and self.page_frame_editor_window.winfo_exists():
            self.page_frame_editor_window.focus()
            return
        
        self.page_frame_editor_window = ctk.CTkToplevel(self.root)
        self.page_frame_editor_window.title("Oldalkeretet szerkesztése")
        self.page_frame_editor_window.geometry("350x550")
        self.page_frame_editor_window.transient(self.root)
        self.page_frame_editor_window.attributes("-topmost", True)

        # --- JAVÍTÁS: Létrehozunk egy fő görgethető keretet ---
        main_scroll_frame = ctk.CTkScrollableFrame(self.page_frame_editor_window)
        main_scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
        # --------------------------------------------------------

        ctk.CTkLabel(main_scroll_frame, text="Válassz keretet az oldalhoz!", font=ctk.CTkFont(weight="bold")).pack(pady=10)

        preset_frame_container = ctk.CTkFrame(main_scroll_frame, fg_color="transparent") # A szülő mostantól a main_scroll_frame
        preset_frame_container.pack(pady=5, padx=5, fill="x")

        preset_frame_ui = ctk.CTkFrame(preset_frame_container)
        preset_frame_ui.pack(pady=5, fill="x")
        presets = [("Fekete", "preset_black"), ("Fehér", "preset_white"), ("Arany", "preset_gold")]
        for i, (name, path) in enumerate(presets):
            ctk.CTkButton(preset_frame_ui, text=name, command=lambda p=path: self._apply_page_frame(p)).grid(row=0, column=i, padx=5, pady=5, sticky="ew")
        preset_frame_ui.grid_columnconfigure((0, 1, 2), weight=1)

        frames_path = os.path.join(self.assets_path, "frames")
        if os.path.exists(frames_path):
            ctk.CTkLabel(preset_frame_container, text="Beépített keretek", font=ctk.CTkFont(size=12)).pack(pady=(10, 0))
            custom_preset_frame = ctk.CTkFrame(preset_frame_container) # Ez is lehet sima Frame
            custom_preset_frame.pack(pady=5, fill="x")
            preset_files = [f for f in os.listdir(frames_path) if f.lower().endswith('.png')]
            for i, fname in enumerate(preset_files):
                fpath = os.path.join(frames_path, fname)
                try:
                    thumb = ctk.CTkImage(Image.open(fpath), size=(50, 50))
                    btn = ctk.CTkButton(custom_preset_frame, image=thumb, text="", width=60, height=60, command=lambda p=fpath: self._apply_page_frame(p))
                    btn.grid(row=i // 4, column=i % 4, padx=5, pady=5)
                except Exception as e:
                    print(f"Hiba a beépített oldalkeret betöltésekor ({fname}): {e}")

        ctk.CTkButton(main_scroll_frame, text="Saját keret feltöltése...", command=lambda: self._apply_page_frame(self._upload_custom_frame_path())).pack(pady=(10, 5), padx=5, fill="x")
        
        ctk.CTkLabel(main_scroll_frame, text="Beállítások", font=ctk.CTkFont(weight="bold")).pack(pady=(15, 5))
        
        slider_panel = ctk.CTkFrame(main_scroll_frame) # A szülő mostantól a main_scroll_frame
        slider_panel.pack(pady=5, padx=5, fill="both", expand=True)

        ctk.CTkLabel(slider_panel, text="Vastagság (beépített kereteknél)").pack()
        self.page_frame_thickness_slider = ctk.CTkSlider(slider_panel, from_=0.01, to=0.2, command=self._update_page_frame_properties)
        self.page_frame_thickness_slider.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkLabel(slider_panel, text="Méret").pack()
        self.page_frame_scale_slider = ctk.CTkSlider(slider_panel, from_=0.5, to=1.5, command=self._update_page_frame_properties)
        self.page_frame_scale_slider.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(slider_panel, text="Vízszintes eltolás").pack()
        self.page_frame_offset_x_slider = ctk.CTkSlider(slider_panel, from_=-200, to=200, number_of_steps=400, command=self._update_page_frame_properties)
        self.page_frame_offset_x_slider.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(slider_panel, text="Függőleges eltolás").pack()
        self.page_frame_offset_y_slider = ctk.CTkSlider(slider_panel, from_=-200, to=200, number_of_steps=400, command=self._update_page_frame_properties)
        self.page_frame_offset_y_slider.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkButton(main_scroll_frame, text="Keret eltávolítása", fg_color="#D32F2F", hover_color="#B71C1C", command=lambda: self._apply_page_frame(None)).pack(pady=10, padx=5, fill="x")
        
        self.update_page_frame_editor_ui()

    def _apply_page_frame(self, path):
        """Alkalmazza a kiválasztott keretet az oldalra és alaphelyzetbe állítja a beállításokat."""
        current_page_data = self.pages[self.current_page]
        if path:
            current_page_data['page_frame_path'] = path
            # Új keret választásakor alaphelyzetbe állítjuk a csúszkákat
            current_page_data['page_frame_thickness'] = 0.05
            current_page_data['page_frame_scale'] = 1.0
            current_page_data['page_frame_offset_x'] = 0
            current_page_data['page_frame_offset_y'] = 0
        else:
            # Törléskor eltávolítjuk az összes kapcsolódó kulcsot
            for key in ['page_frame_path', 'page_frame_thickness', 'page_frame_scale', 'page_frame_offset_x', 'page_frame_offset_y']:
                current_page_data.pop(key, None)

        self.update_page_frame_editor_ui()
        self.refresh_editor_view()

    def _update_page_frame_properties(self, value=None):
        """Frissíti az oldalkeretet tulajdonságait a csúszkák alapján."""
        if not (self.page_frame_editor_window and self.page_frame_editor_window.winfo_exists()):
            return
        
        current_page_data = self.pages[self.current_page]
        current_page_data['page_frame_thickness'] = self.page_frame_thickness_slider.get()
        current_page_data['page_frame_scale'] = self.page_frame_scale_slider.get()
        current_page_data['page_frame_offset_x'] = int(self.page_frame_offset_x_slider.get())
        current_page_data['page_frame_offset_y'] = int(self.page_frame_offset_y_slider.get())
        
        self.refresh_editor_view()
    
    def update_page_frame_editor_ui(self):
        """Frissíti az oldalkeretet szerkesztő ablak vezérlőinek állapotát."""
        if not (self.page_frame_editor_window and self.page_frame_editor_window.winfo_exists()):
            return

        current_page_data = self.pages[self.current_page]
        props = current_page_data
        
        sliders = [self.page_frame_scale_slider, self.page_frame_offset_x_slider, self.page_frame_offset_y_slider, self.page_frame_thickness_slider]
        
        if props.get('page_frame_path'):
            for slider in sliders:
                slider.configure(state="normal")
            
            self.page_frame_scale_slider.set(props.get('page_frame_scale', 1.0))
            self.page_frame_offset_x_slider.set(props.get('page_frame_offset_x', 0))
            self.page_frame_offset_y_slider.set(props.get('page_frame_offset_y', 0))
            self.page_frame_thickness_slider.set(props.get('page_frame_thickness', 0.05))

            if not props.get('page_frame_path', '').startswith('preset_'):
                self.page_frame_thickness_slider.configure(state="disabled")
        else:
            for slider in sliders:
                slider.configure(state="disabled")
            self.page_frame_scale_slider.set(1.0)
            self.page_frame_offset_x_slider.set(0)
            self.page_frame_offset_y_slider.set(0)
            self.page_frame_thickness_slider.set(0.05)


    def _render_page_frame(self):
        """Kirajzolja az oldalkeretet a vászonra, figyelembe véve a méretezési és eltolási beállításokat."""
        offset_x, offset_y, draw_w, draw_h = self._get_page_draw_area()
        if draw_w <= 1 or draw_h <= 1: return

        current_page_data = self.pages[self.current_page]
        page_frame_path = current_page_data.get('page_frame_path')
        
        if self.canvas_page_frame_item:
            self.canvas.delete(self.canvas_page_frame_item)
            self.canvas_page_frame_item = None
            self.page_frame_photo_image = None

        if page_frame_path:
            frame_img = None
            if page_frame_path.startswith('preset_'):
                thickness_ratio = current_page_data.get('page_frame_thickness', 0.05)
                frame_img = self._create_preset_frame(page_frame_path, (draw_w, draw_h), thickness_ratio)
            elif os.path.exists(page_frame_path):
                frame_img = Image.open(page_frame_path).convert("RGBA")
            
            if frame_img:
                # ÚJ RÉSZ: Méretezés és eltolás alkalmazása
                f_scale = current_page_data.get('page_frame_scale', 1.0)
                f_off_x = current_page_data.get('page_frame_offset_x', 0)
                f_off_y = current_page_data.get('page_frame_offset_y', 0)

                # Az új keret méretei a skálázás alapján
                new_fw = int(draw_w * f_scale)
                new_fh = int(draw_h * f_scale)
                
                # A keret átméretezése
                resized_frame = frame_img.resize((new_fw, new_fh), Image.LANCZOS)
                
                # A beillesztés pozíciójának kiszámítása a középpontból és az eltolásból
                paste_x = (draw_w - new_fw) // 2 + f_off_x
                paste_y = (draw_h - new_fh) // 2 + f_off_y
                
                # Létrehozunk egy üres, átlátszó réteget, amire a keretet helyezzük,
                # hogy a vászonra egyetlen képként kerüljön ki.
                final_frame_layer = Image.new('RGBA', (draw_w, draw_h), (0, 0, 0, 0))
                final_frame_layer.paste(resized_frame, (paste_x, paste_y), resized_frame)
                
                self.page_frame_photo_image = ImageTk.PhotoImage(final_frame_layer)
                self.canvas_page_frame_item = self.canvas.create_image(
                    offset_x, offset_y, 
                    image=self.page_frame_photo_image, 
                    anchor="nw", 
                    tags="page_frame"
                )
    
    def _upload_custom_frame_path(self):
        return filedialog.askopenfilename(title="Válassz egy keret képet", filetypes=[("Képfájlok", "*.jpg *.jpeg *.png *.bmp"), ("Minden fájl", "*.*")]) or None
    
    def select_page(self, page_idx):
        if 0 <= page_idx < len(self.pages):
            self.current_page = page_idx
            self.refresh_editor_view()

    def add_new_page(self):
        # Az új oldal mérete legyen ugyanaz, mint az előzőé
        previous_page_size = self.pages[-1].get('size', self.DEFAULT_BOOK_SIZE_PIXELS) if self.pages else self.DEFAULT_BOOK_SIZE_PIXELS
        self.pages.append({'photos': [], 'texts': [], 'size': previous_page_size})
        self.current_page = len(self.pages) - 1
        
    def add_new_page_and_refresh(self):
        """Létrehoz egy új oldalt, amely az utolsó oldal elrendezését és méretét másolja, 
        majd frissíti a nézetet. Nem nyitja meg újra az elrendezés-választót."""
        if not self.pages:
            # Ez a helyzet nem fordulhat elő a szerkesztőben, de biztonsági tartalékként
            # visszairányít a főmenübe, ha valahogy mégis megtörténne.
            self.create_main_menu()
            messagebox.showinfo("Információ", "Először hozzon létre egy projektet.")
            return

        # Vesszük az utolsó oldal adatait mintaként
        last_page_data = self.pages[-1]
        layout_count_to_copy = len(last_page_data.get('photos', []))
        page_size_to_copy = last_page_data.get('size', self.DEFAULT_BOOK_SIZE_PIXELS)
        
        # Ha az előző oldal véletlenül üres volt, alapértelmezetten 1 képes elrendezést kap
        if layout_count_to_copy == 0:
            layout_count_to_copy = 1
            
        # Generáljuk az új oldal fotóinak sablonját
        new_photos_layout = self._generate_layout_template(layout_count_to_copy)
        
        # Létrehozzuk az új oldalt a másolt adatokkal
        new_page = {
            'photos': new_photos_layout,
            'texts': [],
            'size': page_size_to_copy
        }
        self.pages.append(new_page)
        
        # Az új, üres oldalra ugrunk és frissítjük a szerkesztőfelületet
        self.current_page = len(self.pages) - 1
        self.refresh_editor_view()
    def delete_page(self):
        if len(self.pages) > 1:
            if messagebox.askyesno("Oldal törlése", f"Biztosan törölni szeretnéd a(z) {self.current_page + 1}. oldalt?"):
                self._deselect_all()
                del self.pages[self.current_page]
                if self.current_page >= len(self.pages): self.current_page = len(self.pages) - 1
                self.refresh_editor_view()
        else: messagebox.showwarning("Utolsó oldal", "Nem törölheted az utolsó oldalt!")
    
    def change_current_page_layout(self):
        self.show_page_selection(is_new_project=False)

    def change_page_size(self):
        """Felugró ablakot nyit az aktuális oldal méretének módosítására, egyéni méret opcióval."""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Oldalméret módosítása")
        dialog.geometry("350x180")
        dialog.transient(self.root)
        dialog.grab_set()

        # --- Belső segédfüggvény az egyéni méret ablakhoz ---
        def prompt_and_apply_custom_size():
            """
            Kezeli az új, egyéni méret bekérését és alkalmazását.
            """
            dialog.withdraw() # Az eredeti dialógus elrejtése

            custom_dialog = ctk.CTkToplevel(self.root)
            custom_dialog.title("Egyéni méret megadása")
            custom_dialog.geometry("300x200")
            custom_dialog.transient(self.root)
            custom_dialog.grab_set()

            ctk.CTkLabel(custom_dialog, text="Add meg a méreteket pixelben (300 DPI):", font=ctk.CTkFont(size=12)).pack(pady=(10, 5))

            width_frame = ctk.CTkFrame(custom_dialog, fg_color="transparent")
            width_frame.pack(pady=5, padx=20, fill="x")
            ctk.CTkLabel(width_frame, text="Szélesség (px):", width=100).pack(side="left")
            width_entry = ctk.CTkEntry(width_frame)
            width_entry.pack(side="left", expand=True, fill="x")

            height_frame = ctk.CTkFrame(custom_dialog, fg_color="transparent")
            height_frame.pack(pady=5, padx=20, fill="x")
            ctk.CTkLabel(height_frame, text="Magasság (px):", width=100).pack(side="left")
            height_entry = ctk.CTkEntry(height_frame)
            height_entry.pack(side="left", expand=True, fill="x")

            def apply_custom_size():
                try:
                    width = int(width_entry.get())
                    height = int(height_entry.get())
                    if width <= 0 or height <= 0:
                        raise ValueError("A méreteknek pozitívnak kell lenniük.")

                    custom_key = f"Egyéni ({width}x{height}px)"
                    custom_value = (width, height)
                    
                    if custom_key not in self.BOOK_SIZES:
                        self.BOOK_SIZES[custom_key] = custom_value
                    
                    self.pages[self.current_page]['size'] = custom_value
                    
                    custom_dialog.destroy()
                    dialog.destroy()
                    self.refresh_editor_view()

                except ValueError as e:
                    messagebox.showerror("Hiba", f"Érvénytelen érték!\nKérlek, pozitív egész számokat adj meg.\n({e})", parent=custom_dialog)

            def on_custom_close():
                dialog.deiconify()
                custom_dialog.destroy()

            custom_dialog.protocol("WM_DELETE_WINDOW", on_custom_close)
            ctk.CTkButton(custom_dialog, text="Alkalmaz", command=apply_custom_size).pack(pady=20)

        # --- A fő dialógus felépítése ---
        ctk.CTkLabel(dialog, text=f"Új méret a(z) {self.current_page + 1}. oldalhoz:", font=ctk.CTkFont(size=14)).pack(pady=10)

        size_var = ctk.StringVar()
        current_size_pixels = self.pages[self.current_page].get('size', self.DEFAULT_BOOK_SIZE_PIXELS)
        current_size_name = next((name for name, size in self.BOOK_SIZES.items() if size == current_size_pixels), self.DEFAULT_BOOK_SIZE_NAME)
        size_var.set(current_size_name)

        options = list(self.BOOK_SIZES.keys())
        if "Egyéni méret..." in options:
            options.remove("Egyéni méret...")
        options.append("Egyéni méret...")

        def handle_menu_selection(choice):
            if choice == "Egyéni méret...":
                prompt_and_apply_custom_size()

        menu = ctk.CTkOptionMenu(dialog, variable=size_var, values=options, command=handle_menu_selection)
        menu.pack(pady=5, padx=20, fill="x")

        def apply_preset_size():
            chosen_name = size_var.get()
            if chosen_name == "Egyéni méret...":
                return 
            
            self.pages[self.current_page]['size'] = self.BOOK_SIZES[chosen_name]
            dialog.destroy()
            self.refresh_editor_view()

        ctk.CTkButton(dialog, text="Kiválasztott alkalmazása", command=apply_preset_size).pack(pady=20, padx=20)


    def save_project(self):
        if not self.pages:
            messagebox.showerror("Hiba", "Nincs mit menteni. Hozz létre legalább egy oldalt!")
            return
        filepath = filedialog.asksaveasfilename(title="Projekt mentése másként", defaultextension=".lolaba", filetypes=[("LoLaBa Fotókönyv Projekt", "*.lolaba"), ("Minden fájl", "*.*")])
        if not filepath: return
        
        pages_to_save = copy.deepcopy(self.pages)
        for page in pages_to_save:
            bg = page.get('background')
            if isinstance(bg, dict) and 'image_obj' in bg:
                del bg['image_obj']

        project_data = {
            "version": 1.1, # Verziószám a jövőbeli kompatibilitáshoz
            "pages": pages_to_save, 
            "photo_properties": self.photo_properties,
            "z_order": self.z_order
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("Mentés sikeres", f"A projekt sikeresen elmentve ide:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Mentési hiba", f"Hiba történt a projekt mentése során:\n{e}")

    def load_project(self):
        filepath = filedialog.askopenfilename(title="Projekt megnyitása", filetypes=[("LoLaBa Fotókönyv Projekt", "*.lolaba"), ("Minden fájl", "*.*")])
        if not filepath: return
        
        self._show_working_indicator() # Nincs többé üzenet
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                project_data = json.load(f)
            
            self._reset_project_state()
            self.pages = project_data.get("pages", [])
            
            for page in self.pages:
                if 'size' not in page:
                    page['size'] = self.DEFAULT_BOOK_SIZE_PIXELS

            self.photo_properties = project_data.get("photo_properties", {})
            self.z_order = project_data.get("z_order", {})
            self.current_page = 0
            
            if not self.pages:
                messagebox.showwarning("Betöltési hiba", "A projektfájl üres vagy sérült.")
                self.create_main_menu()
                return
            
            if not self.editor_ui_built:
                self._build_editor_ui()
                self.editor_ui_built = True
            self.refresh_editor_view()
            messagebox.showinfo("Betöltés sikeres", "A projekt sikeresen betöltve.")

        except Exception as e:
            messagebox.showerror("Betöltési hiba", f"Hiba történt a projekt betöltése során:\n{e}")
            self._reset_project_state()
            self.create_main_menu()
        finally:
            self._hide_working_indicator()

    def export_project(self):
        if not self.pages:
            messagebox.showerror("Hiba", "Nincs mit exportálni. Hozz létre legalább egy oldalt!")
            return
        export_window = ctk.CTkToplevel(self.root)
        export_window.title("Exportálás"); export_window.geometry("300x200")
        export_window.transient(self.root); export_window.grab_set()
        ctk.CTkLabel(export_window, text="Válassz exportálási formátumot:", font=ctk.CTkFont(size=16)).pack(pady=20)
        btn_style = {'height': 40, 'width': 200}
        ctk.CTkButton(export_window, text="Exportálás Képként", command=lambda: [export_window.destroy(), self._export_as_images()], **btn_style).pack(pady=10)
        ctk.CTkButton(export_window, text="Exportálás PDF-ként", command=lambda: [export_window.destroy(), self._export_as_pdf()], **btn_style).pack(pady=10)

    def _export_as_images(self):
        filepath = filedialog.asksaveasfilename(
            title="Képek mentése másként",
            defaultextension=".png",
            filetypes=[("PNG képfájl", "*.png"), ("JPEG képfájl", "*.jpg")]
        )
        if not filepath:
            return

        self._show_working_indicator()
        try:
            directory = os.path.dirname(filepath)
            base_name, extension = os.path.splitext(os.path.basename(filepath))
            save_format = "JPEG" if extension.lower() in ['.jpg', '.jpeg'] else "PNG"
            num_pages = len(self.pages)
            
            for i in range(num_pages):
                page_image = self._render_page_to_image(i)
                if page_image:
                    if num_pages > 1:
                        current_filename = f"{base_name}_{i+1}{extension}"
                        final_path = os.path.join(directory, current_filename)
                    else:
                        final_path = filepath
                    page_image.save(final_path, save_format)
            
            messagebox.showinfo("Exportálás sikeres", f"Az oldalak sikeresen exportálva a következő mappába:\n{directory}")
        
        except Exception as e:
            messagebox.showerror("Exportálási hiba", f"Hiba történt a képek exportálása során:\n{e}")
        finally:
            self._hide_working_indicator()

    def _export_as_pdf(self):
        filepath = filedialog.asksaveasfilename(title="PDF mentése másként", defaultextension=".pdf", filetypes=[("PDF Dokumentum", "*.pdf")])
        if not filepath: return
        
        self._show_working_indicator()
        try:
            rendered_images = []
            for i in range(len(self.pages)):
                page_image = self._render_page_to_image(i)
                if page_image:
                    rendered_images.append(page_image)
            
            if not rendered_images:
                messagebox.showerror("Hiba", "Nem sikerült egyetlen oldalt sem renderelni.")
                return

            if len(rendered_images) > 1:
                rendered_images[0].save(
                    filepath, "PDF", resolution=300.0, save_all=True, append_images=rendered_images[1:]
                )
            elif rendered_images:
                rendered_images[0].save(filepath, "PDF", resolution=300.0)

            messagebox.showinfo("Exportálás sikeres", f"A PDF sikeresen létrehozva:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Exportálási hiba", f"Hiba történt a PDF létrehozása során:\n{e}\n{traceback.format_exc()}")
        finally:
            self._hide_working_indicator()

    
    
    import customtkinter as ctk
from tkinter import messagebox, filedialog, colorchooser, Canvas
import os
from PIL import Image, ImageDraw, ImageTk, ImageFont, ImageEnhance, ImageFilter
import traceback
import json
import copy 
import random 
import math 
import re 

# --- Alapbeállítások ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class FotokonyvGUI:
    """A fotókönyv-szerkesztő alkalmazás fő grafikus felületét (GUI) kezelő osztály."""

    # Előre definiált könyvméretek pixelben (300 DPI alapon)
    BOOK_SIZES = {
        "A4 Álló (21x29.7cm)": (2480, 3508),
        "A4 Fekvő (29.7x21cm)": (3508, 2480),
        "Négyzetes (21x21cm)": (2480, 2480),
        "Kis Négyzetes (15x15cm)": (1772, 1772)
    }
    DEFAULT_BOOK_SIZE_NAME = "A4 Álló (21x29.7cm)"
    DEFAULT_BOOK_SIZE_PIXELS = BOOK_SIZES[DEFAULT_BOOK_SIZE_NAME]


    def __init__(self):
        """Az osztály inicializálása, a fő ablak és az alapvető állapotok beállítása."""
        self.root = ctk.CTk()
        self.root.title("LoLaBa Fotókönyv")
        self.root.geometry("1200x800")
        
        self.colors = {
            'bg_primary': '#C4A484', 'bg_secondary': '#B5956B', 
            'card_bg': '#F5F5F5', 'button_bg': '#E8E8E8',
            'accent': '#A4B068', 'text_primary': '#333333',
            'text_secondary': '#666666', 'green_box': '#4CAF50',
            'selected_card': '#556B2F',
            'selected_photo_border': '#4CAF50',
            'selected_text_color': '#007BFF',
            'canvas_workspace_bg': '#5A5A5A' 
        }
        
        # --- Assets mappa elérési útjának meghatározása ---
        try:
            self.script_path = os.path.dirname(os.path.abspath(__file__))
        except NameError:
            self.script_path = os.getcwd() 
        self.assets_path = os.path.join(self.script_path, "assets")
        
        self.editor_ui_built = False
        self.main_editor_frame = None
        self.left_panel_scroll = None
        self.title_label = None
        self.original_bg_pil_image = None
        
        self.canvas = None
        self.canvas_bg_item = None
        self.canvas_page_frame_item = None
        self.bg_photo_image = None
        self.page_frame_photo_image = None
        self.widget_to_canvas_item = {}

        self.frame_editor_window = None
        self.text_editor_window = None
        
        # Változó a méretválasztó menühöz
        self.selected_book_size_name = ctk.StringVar()
        
        self._reset_project_state()
        self.create_main_menu()

    # --- BELSŐ MŰKÖDÉST SEGÍTŐ METÓDUSOK ---
    def _reset_project_state(self):
        self.current_layout = 1
        self.custom_image_count = 1
        self.selected_layout_card = None
        self.pages = []
        self.current_page = 0
        self.z_order = {}
        self.uploaded_photos = []
        self.selected_photo_index = None
        self.photo_frames = []
        self.photo_properties = {}
        self.text_widgets = []
        self.selected_text_index = None
        self.page_frame_editor_window = None
        self._drag_data = {}
        self.editor_ui_built = False
        self.widget_to_canvas_item = {}
        
        if hasattr(self, 'selected_book_size_name'):
             self.selected_book_size_name.set(self.DEFAULT_BOOK_SIZE_NAME)
        
        if self.frame_editor_window and self.frame_editor_window.winfo_exists(): self.frame_editor_window.destroy()
        self.frame_editor_window = None
        if self.text_editor_window and self.text_editor_window.winfo_exists(): self.text_editor_window.destroy()
        self.text_editor_window = None



  

    def _resize_main_menu_bg(self, event):
        """Az ablak átméretezésekor frissíti a főmenü háttérképét, hogy arányosan kitöltse a teret."""
        # Ha a kép betöltése sikertelen volt, ne csináljon semmit
        if not hasattr(self, 'original_bg_pil_image') or not self.original_bg_pil_image:
            return

        # Kérjük le a keret új méretét az eseményből
        new_width = event.width
        new_height = event.height
    
        # Elkerüljük a hibát, ha az ablak 0 méretűre van kicsinyítve
        if new_width <= 0 or new_height <= 0:
            return

        try:
            # Méretezzük át az eredeti PIL képet az új méretre
            resized_pil_image = self.original_bg_pil_image.resize((new_width, new_height), Image.LANCZOS)

            # Hozzunk létre egy új CTkImage objektumot a frissített méretekkel
            self.main_menu_bg_image = ctk.CTkImage(resized_pil_image, size=(new_width, new_height))
        
            # Frissítsük a címkét az új képpel
            self.bg_label.configure(image=self.main_menu_bg_image)
        except Exception as e:
            print(f"Hiba a háttérkép átméretezésekor: {e}")

    def _set_cursor_recursive(self, widget, cursor_style):
        """Rekurzívan beállítja a kurzort egy widgeten és annak összes gyerek-widgetjén."""
        try:
            # Beállítja a kurzort a jelenlegi elemen
            widget.config(cursor=cursor_style)
        except Exception:
            # Előfordulhat hiba, ha a widget épp megsemmisül, ezt figyelmen kívül hagyjuk
            pass
        
        # Végigmegy az összes gyerek-elemen és meghívja önmagát rájuk
        for child in widget.winfo_children():
            self._set_cursor_recursive(child, cursor_style)

    def _show_working_indicator(self, message=None):
        """A kurzort 'várakozó' állapotba kapcsolja az egész alkalmazáson, rekurzívan."""
        self._set_cursor_recursive(self.root, "watch")
        # Fontos, hogy a GUI frissüljön a blokkoló művelet elindítása előtt
        self.root.update_idletasks()

    def _hide_working_indicator(self):
        """Visszaállítja a kurzort az alapértelmezett állapotba az egész alkalmazáson, rekurzívan."""
        self._set_cursor_recursive(self.root, "")

    def _select_photo(self, photo_index):
        self._deselect_all()
        self.selected_photo_index = photo_index

        if self.selected_photo_index is not None and self.selected_photo_index < len(self.pages[self.current_page]['photos']):
            if self.selected_photo_index < len(self.photo_frames) and self.photo_frames[self.selected_photo_index]:
                selected_frame = self.photo_frames[self.selected_photo_index]
                selected_frame.configure(border_width=3, border_color=self.colors['selected_photo_border'])
                if selected_frame in self.widget_to_canvas_item:
                    self.canvas.tag_raise(self.widget_to_canvas_item[selected_frame])
                
                props_key = str((self.current_page, photo_index))
                props = self.photo_properties.get(props_key, {})
                photo_data = self.pages[self.current_page]['photos'][photo_index]

                widgets_to_enable = [
                    self.zoom_slider, self.pan_x_slider, self.pan_y_slider,
                    self.width_slider, self.height_slider,
                    self.brightness_slider, self.contrast_slider, self.saturation_slider,
                    self.grayscale_checkbox, self.fit_mode_button
                ]
                for widget in widgets_to_enable:
                    widget.configure(state="normal")
                
                self.zoom_slider.set(props.get('zoom', 1.0))
                self.pan_x_slider.set(props.get('pan_x', 0.5))
                self.pan_y_slider.set(props.get('pan_y', 0.5))
                self.width_slider.set(photo_data.get('relwidth', 0.5))
                self.height_slider.set(photo_data.get('relheight', 0.5))
                self.brightness_slider.set(props.get('brightness', 1.0))
                self.contrast_slider.set(props.get('contrast', 1.0))
                self.saturation_slider.set(props.get('saturation', 1.0))
                
                if props.get('grayscale', False):
                    self.grayscale_checkbox.select()
                else:
                    self.grayscale_checkbox.deselect()

                
                fit_mode = props.get('fit_mode', 'fill') 
                self.fit_mode_button.set("Beleillesztés" if fit_mode == 'fit' else "Kitöltés")

                if self.frame_editor_window and self.frame_editor_window.winfo_exists():
                    self.update_frame_editor_ui()

    def _deselect_all(self):
        if self.selected_photo_index is not None and self.selected_photo_index < len(self.photo_frames):
            if self.photo_frames[self.selected_photo_index] and self.photo_frames[self.selected_photo_index].winfo_exists():
                self.photo_frames[self.selected_photo_index].configure(border_width=0)
        self.selected_photo_index = None
        
        if self.selected_text_index is not None and self.selected_text_index < len(self.text_widgets):
            if self.text_widgets[self.selected_text_index].winfo_exists() and len(self.text_widgets[self.selected_text_index].winfo_children()) > 0:
                text_label = self.text_widgets[self.selected_text_index].winfo_children()[0]
                original_color = self.pages[self.current_page]['texts'][self.selected_text_index].get('font_color', '#000000')
                text_label.configure(text_color=original_color)
        self.selected_text_index = None

        if hasattr(self, 'zoom_slider'):
            widgets_to_disable = [
                self.zoom_slider, self.pan_x_slider, self.pan_y_slider,
                self.width_slider, self.height_slider,
                self.brightness_slider, self.contrast_slider, self.saturation_slider,
                self.grayscale_checkbox, self.fit_mode_button
            ]
            for widget in widgets_to_disable:
                widget.configure(state="disabled")

        if self.frame_editor_window and self.frame_editor_window.winfo_exists(): self.update_frame_editor_ui()
        if self.text_editor_window and self.text_editor_window.winfo_exists(): self.update_text_editor_ui()

    def _select_text(self, text_index):
        self._deselect_all()
        self.selected_text_index = text_index
        if self.selected_text_index is not None and self.selected_text_index < len(self.text_widgets):
            text_widget_container = self.text_widgets[self.selected_text_index]
            text_label = text_widget_container.winfo_children()[0]
            text_label.configure(text_color=self.colors['selected_text_color'])
            self.canvas.tag_raise(self.widget_to_canvas_item[text_widget_container])
        if self.text_editor_window and self.text_editor_window.winfo_exists():
            self.update_text_editor_ui()

    


    def _change_fit_mode(self, value):
        """A képillesztési mód (Beleillesztés/Kitöltés) változását kezeli."""
        if self.selected_photo_index is None:
            return
            
        key = str((self.current_page, self.selected_photo_index))
        if key not in self.photo_properties:
            self.photo_properties[key] = {}
            
        # A gomb szöveges értékét lefordítjuk a belsőleg használt kulcsszóra
        mode = 'fit' if value == "Beleillesztés" else 'fill'
        self.photo_properties[key]['fit_mode'] = mode
        
        # Frissítjük a kép megjelenítését az új beállítással
        self._update_photo_properties()


    def _update_photo_properties(self, value=None):
        if self.selected_photo_index is None: return
        key = str((self.current_page, self.selected_photo_index))
        if key not in self.photo_properties: self.photo_properties[key] = {}
        
        if hasattr(self, 'zoom_slider'):
            self.photo_properties[key]['zoom'] = self.zoom_slider.get()
            self.photo_properties[key]['pan_x'] = self.pan_x_slider.get()
            self.photo_properties[key]['pan_y'] = self.pan_y_slider.get()
        
        if hasattr(self, 'brightness_slider'):
            self.photo_properties[key]['brightness'] = self.brightness_slider.get()
            self.photo_properties[key]['contrast'] = self.contrast_slider.get()
            self.photo_properties[key]['saturation'] = self.saturation_slider.get()
            self.photo_properties[key]['grayscale'] = self.grayscale_checkbox.get() == 1

        if self.frame_editor_window and self.frame_editor_window.winfo_exists():
            self.photo_properties[key]['frame_scale'] = self.frame_scale_slider.get()
            self.photo_properties[key]['frame_offset_x'] = int(self.frame_offset_x_slider.get())
            self.photo_properties[key]['frame_offset_y'] = int(self.frame_offset_y_slider.get())
            self.photo_properties[key]['frame_thickness'] = self.frame_thickness_slider.get()
        
        if hasattr(self, 'photo_frames') and self.photo_frames and self.selected_photo_index < len(self.photo_frames):
            frame = self.photo_frames[self.selected_photo_index]
            photo_data = self.pages[self.current_page]['photos'][self.selected_photo_index]
            self.display_photo_placeholder(frame, photo_data, self.selected_photo_index, is_update=True)

    
    
    # --- FELÜLETET ÉPÍTŐ METÓDUSOK ---
    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def create_main_menu(self):
        self._reset_project_state()
        self.clear_window()
        main_frame = ctk.CTkFrame(self.root, fg_color=self.colors['bg_primary'], corner_radius=0)
        main_frame.pack(fill="both", expand=True)

        
        
        try:
            bg_image_path = os.path.join(self.assets_path, "backgrounds", "main_menu_bg.png")
            # 1. Töltsük be az eredeti, nagy felbontású képet és mentsük el
            self.original_bg_pil_image = Image.open(bg_image_path)

            # 2. Hozzuk létre a címkét, amiben a kép lesz, de még kép nélkül
            self.bg_label = ctk.CTkLabel(main_frame, text="")
            self.bg_label.place(relx=0, rely=0, relwidth=1, relheight=1)

            # 3. Kössük hozzá az átméretezést figyelő eseményt a kerethez
            main_frame.bind("<Configure>", self._resize_main_menu_bg)

        except Exception as e:
            # Hiba esetén is hozzuk létre a változót, hogy ne legyen később gond
            self.original_bg_pil_image = None
            print(f"Főmenü háttérképét nem sikerült betölteni: {e}")

        ctk.CTkLabel(main_frame, text="LoLaBa Fotókönyv", font=ctk.CTkFont(size=48, weight="bold"), text_color="white", fg_color="transparent").pack(pady=(80, 20))
        ctk.CTkLabel(main_frame, text="Készíts saját, egyedi fotókönyvet egyszerű lépésekkel!", font=ctk.CTkFont(size=18), text_color="white", fg_color="transparent").pack(pady=(0, 60))
        
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(expand=True, padx=40)
        
        # --- GOMBOK LÉTREHOZÁSA (FINOMHANGOLVA) ---
        
        buttons_data = [
            ("🆕", "Új projekt létrehozása", lambda: self.show_page_selection(is_new_project=True)),
            ("📁", "Korábbi projekt megnyitása", self.load_project),
            ("🚪", "Kilépés", self.root.quit)
        ]
        
        bg_color = self.colors['card_bg']
        hover_color = '#F0F0F0'
        text_color = self.colors['text_primary']
        icon_font = ctk.CTkFont(size=22)
        text_font = ctk.CTkFont(size=16, weight="bold")

        for icon, text, command in buttons_data:
            button_container = ctk.CTkFrame(
                button_frame, 
                height=60, 
                width=350, 
                fg_color=bg_color, 
                corner_radius=15,
                cursor="hand2"
            )
            button_container.pack(pady=15, fill="x")
            button_container.pack_propagate(False)

            def on_enter(e, widget=button_container):
                widget.configure(fg_color=hover_color)
            
            def on_leave(e, widget=button_container):
                widget.configure(fg_color=bg_color)

            button_container.bind("<Enter>", on_enter)
            button_container.bind("<Leave>", on_leave)
            button_container.bind("<Button-1>", lambda e, cmd=command: cmd())

            # Ikon címke - A FÜGGŐLEGES IGAZÍTÁS ITT TÖRTÉNIK
            icon_label = ctk.CTkLabel(
                button_container, 
                text=icon, 
                font=icon_font, 
                fg_color="transparent",
                text_color=text_color
            )
            # A pady=(8, 12) felfelé tolja az ikont a (10, 10) középhez képest
            icon_label.pack(side="left", padx=(20, 10), pady=(8, 12)) 
            icon_label.bind("<Enter>", on_enter)
            icon_label.bind("<Leave>", on_leave)
            icon_label.bind("<Button-1>", lambda e, cmd=command: cmd())

            # Szöveg címke
            text_label = ctk.CTkLabel(
                button_container, 
                text=text, 
                font=text_font, 
                fg_color="transparent",
                text_color=text_color
            )
            # A szöveg marad középen a (10, 10) pady értékkel
            text_label.pack(side="left", padx=(0, 20), pady=(10, 10), expand=True, fill="x", anchor="w")
            text_label.bind("<Enter>", on_enter)
            text_label.bind("<Leave>", on_leave)
            text_label.bind("<Button-1>", lambda e, cmd=command: cmd())

    def create_layout_preview(self, parent, layout_count, click_handler=None):
        """
        Létrehoz egy előnézeti keretet a megadott számú elrendezéshez,
        VIZUÁLISAN egyenletes, pixel-alapú margókkal és közökkel.
        """
        preview_frame = ctk.CTkFrame(parent, width=180, height=100, fg_color=self.colors['accent'], corner_radius=10)
        preview_frame.pack(pady=(20, 10))
        preview_frame.pack_propagate(False)
        if click_handler:
            preview_frame.bind("<Button-1>", click_handler)

        if layout_count == 0:
            return

        # --- ÚJ LOGIKA: Pixel-alapú számítás a vizuális szimmetriáért ---

        # 1. A keret fix méretei és a kívánt margó pixelben
        frame_w_px = 180
        frame_h_px = 100
        padding_px = 8 # Ezt a pixel értéket használjuk mindenhol (margóként és közként is)

        # 2. Rács méretének meghatározása
        cols = max(1, int(math.ceil(math.sqrt(layout_count))))
        rows = max(1, int(math.ceil(layout_count / cols)))
        
        # Biztonsági ellenőrzés: ha a padding túl sok helyet foglalna, csökkentjük
        if padding_px * (cols + 1) >= frame_w_px or padding_px * (rows + 1) >= frame_h_px:
            padding_px = 4

        # 3. Dobozok méretének kiszámítása PIXELBEN
        total_padding_w_px = padding_px * (cols + 1)
        total_padding_h_px = padding_px * (rows + 1)

        box_w_px = (frame_w_px - total_padding_w_px) / cols
        box_h_px = (frame_h_px - total_padding_h_px) / rows
        
        # Ha a számítás negatív méretet adna, ne rajzoljunk semmit
        if box_w_px <= 0 or box_h_px <= 0:
            return

        # 4. Dobozok elhelyezése a pixel értékekből számolt relatív pozíciókkal
        for i in range(layout_count):
            c = i % cols
            r = i // cols

            # Doboz pozíciója pixelben a bal felső saroktól
            x_px = padding_px + c * (box_w_px + padding_px)
            y_px = padding_px + r * (box_h_px + padding_px)

            # Átváltás relatív értékekre a .place() metódushoz
            rel_x = x_px / frame_w_px
            rel_y = y_px / frame_h_px
            rel_w = box_w_px / frame_w_px
            rel_h = box_h_px / frame_h_px

            box = ctk.CTkFrame(preview_frame, fg_color=self.colors['green_box'], corner_radius=3, border_width=0)
            box.place(relx=rel_x, rely=rel_y, relwidth=rel_w, relheight=rel_h)
            if click_handler:
                box.bind("<Button-1>", click_handler)

    def show_page_selection(self, is_new_project=False):
        if is_new_project: self._reset_project_state()
        self.selected_layout_card = None
        self.clear_window()
        self.editor_ui_built = False
        main_frame = ctk.CTkFrame(self.root, fg_color=self.colors['bg_primary'], corner_radius=0)
        main_frame.pack(fill="both", expand=True)
        ctk.CTkLabel(main_frame, text="Válassz egy kiinduló elrendezést", font=ctk.CTkFont(size=32, weight="bold"), text_color="white").pack(pady=(50, 20))

        # --- Méretválasztó szekció (MÓDOSÍTVA) ---
        if is_new_project:
            size_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
            size_frame.pack(pady=(0, 20))
            ctk.CTkLabel(size_frame, text="Fotókönyv mérete:", font=ctk.CTkFont(size=16), text_color="white").pack(side="left", padx=10)
            
            # Az opciók listájának dinamikus összeállítása
            size_options = list(self.BOOK_SIZES.keys())
            # "Egyéni méret..." opció hozzáadása, ha még nincs
            if "Egyéni méret..." not in size_options:
                 size_options.append("Egyéni méret...")

            # A menü widgetet elmentjük egy példányváltozóba, hogy később frissíthessük
            self.size_menu = ctk.CTkOptionMenu(
                size_frame, 
                variable=self.selected_book_size_name, 
                values=size_options,
                command=self._handle_size_selection  # Figyeli a kiválasztást
            )
            self.size_menu.pack(side="left")

        layout_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        layout_frame.pack(expand=True, padx=20, pady=10)
        cards_frame = ctk.CTkFrame(layout_frame, fg_color="transparent")
        cards_frame.pack()

        layouts = [{"name": "1 kép", "value": 1}, {"name": "2 kép", "value": 2}, {"name": "4 kép", "value": 4}]
        self.layout_cards = []

        for i, layout in enumerate(layouts):
            card = ctk.CTkFrame(cards_frame, width=220, height=180, fg_color=self.colors['card_bg'], corner_radius=20)
            card.grid(row=0, column=i, padx=25, pady=20)
            card.pack_propagate(False)
            name_label = ctk.CTkLabel(card, text=layout["name"], font=ctk.CTkFont(size=16, weight="bold"), text_color=self.colors['text_primary'])
            name_label.pack(pady=(0, 15))
            def make_click_handler(value, card_widget): return lambda e: self.select_layout(value, card_widget)
            click_handler = make_click_handler(layout["value"], card)
            card.bind("<Button-1>", click_handler)
            name_label.bind("<Button-1>", click_handler)
            self.create_layout_preview(card, layout["value"], click_handler)
            self.layout_cards.append(card)

        self.custom_card = ctk.CTkFrame(cards_frame, width=220, height=180, fg_color=self.colors['card_bg'], corner_radius=20)
        self.custom_card.grid(row=1, column=1, padx=25, pady=20)
        self.custom_card.pack_propagate(False)

        custom_title = ctk.CTkLabel(self.custom_card, text="Egyéni mennyiség", font=ctk.CTkFont(size=16, weight="bold"), text_color=self.colors['text_primary'])
        custom_title.pack(pady=(10, 5))

        count_frame = ctk.CTkFrame(self.custom_card, fg_color="transparent")
        count_frame.pack(pady=5)

        ctk.CTkButton(count_frame, text="−", width=30, height=30, command=self.decrease_custom_count).pack(side="left", padx=5)
        self.custom_count_label = ctk.CTkLabel(count_frame, text=str(self.custom_image_count), font=ctk.CTkFont(size=16, weight="bold"), width=40)
        self.custom_count_label.pack(side="left", padx=5)
        ctk.CTkButton(count_frame, text="+", width=30, height=30, command=self.increase_custom_count).pack(side="left", padx=5)

        self.custom_preview_frame = ctk.CTkFrame(self.custom_card, fg_color="transparent", width=180, height=100)
        self.custom_preview_frame.pack(pady=(5, 10))
        self.custom_preview_frame.pack_propagate(False)
        self.update_custom_preview()

        self.custom_card.bind("<Button-1>", lambda e: self.select_custom_layout())

        ctk.CTkButton(main_frame, text="🔧 Tovább a szerkesztőbe", command=self.proceed_to_editor, height=50, font=ctk.CTkFont(size=16, weight="bold")).pack(pady=40, padx=40)

    def _handle_size_selection(self, choice: str):
        """A méretválasztó menü eseménykezelője. Ha az "Egyéni méret..." opciót választják, megnyit egy ablakot."""
        if choice == "Egyéni méret...":
            self._prompt_for_custom_size()

    def _prompt_for_custom_size(self):
        """Felugró ablakot hoz létre, ahol a felhasználó megadhatja az egyéni oldalméretet pixelben."""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Egyéni méret megadása")
        dialog.geometry("300x200")
        dialog.transient(self.root)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Add meg a méreteket pixelben (300 DPI):", font=ctk.CTkFont(size=12)).pack(pady=(10, 5))

        width_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        width_frame.pack(pady=5, padx=20, fill="x")
        ctk.CTkLabel(width_frame, text="Szélesség (px):", width=100).pack(side="left")
        width_entry = ctk.CTkEntry(width_frame)
        width_entry.pack(side="left", expand=True, fill="x")

        height_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        height_frame.pack(pady=5, padx=20, fill="x")
        ctk.CTkLabel(height_frame, text="Magasság (px):", width=100).pack(side="left")
        height_entry = ctk.CTkEntry(height_frame)
        height_entry.pack(side="left", expand=True, fill="x")

        def apply_custom_size():
            try:
                width = int(width_entry.get())
                height = int(height_entry.get())
                if width <= 0 or height <= 0:
                    raise ValueError("A méreteknek pozitívnak kell lenniük.")

                # Létrehozzuk az új méret nevét és értékét
                custom_key = f"Egyéni ({width}x{height}px)"
                custom_value = (width, height)

                # Hozzáadjuk a szótárhoz
                self.BOOK_SIZES[custom_key] = custom_value
                
                # Frissítjük a legördülő menü opcióit
                new_options = list(self.BOOK_SIZES.keys())
                if "Egyéni méret..." not in new_options:
                    new_options.append("Egyéni méret...")
                self.size_menu.configure(values=new_options)

                # Beállítjuk az új, egyéni méretet kiválasztottnak
                self.selected_book_size_name.set(custom_key)

                dialog.destroy()

            except ValueError as e:
                messagebox.showerror("Hiba", f"Érvénytelen érték!\nKérlek, pozitív egész számokat adj meg.\n({e})", parent=dialog)

        apply_button = ctk.CTkButton(dialog, text="Alkalmaz", command=apply_custom_size)
        apply_button.pack(pady=20)
    

    def select_layout(self, layout_value, card_widget):
        if self.selected_layout_card: self.selected_layout_card.configure(fg_color=self.colors['card_bg'])
        self.custom_card.configure(fg_color=self.colors['card_bg'])
        self.current_layout = layout_value; self.selected_layout_card = card_widget
        card_widget.configure(fg_color=self.colors['selected_card'])

    def select_custom_layout(self):
        if self.selected_layout_card: self.selected_layout_card.configure(fg_color=self.colors['card_bg'])
        self.current_layout = self.custom_image_count
        self.selected_layout_card = self.custom_card
        self.custom_card.configure(fg_color=self.colors['selected_card'])

    def decrease_custom_count(self):
        if self.custom_image_count > 1:
            self.custom_image_count -= 1
            self.custom_count_label.configure(text=str(self.custom_image_count))
            self.update_custom_preview(); self.select_custom_layout()

    def increase_custom_count(self):
        if self.custom_image_count < 20:
            self.custom_image_count += 1
            self.custom_count_label.configure(text=str(self.custom_image_count))
            self.update_custom_preview(); self.select_custom_layout()

    def update_custom_preview(self):
        for widget in self.custom_preview_frame.winfo_children(): widget.destroy()
        self.create_layout_preview(self.custom_preview_frame, self.custom_image_count, click_handler=lambda e: self.select_custom_layout())

    def _generate_layout_template(self, count):
        geometries = []
        base_photo_data = {'path': None, 'relx': 0, 'rely': 0, 'relwidth': 0, 'relheight': 0, 'layout_relwidth': 0, 'layout_relheight': 0}
        
        if count == 1:
            geo = base_photo_data.copy()
            geo.update({'relx': 0.05, 'rely': 0.05, 'relwidth': 0.9, 'relheight': 0.9, 'layout_relwidth': 0.9, 'layout_relheight': 0.9})
            geometries.append(geo)
        elif count == 2:
            for relx in [0.05, 0.53]:
                geo = base_photo_data.copy()
                geo.update({'relx': relx, 'rely': 0.1, 'relwidth': 0.42, 'relheight': 0.8, 'layout_relwidth': 0.42, 'layout_relheight': 0.8})
                geometries.append(geo)
        elif count == 3:
            geo1 = base_photo_data.copy(); geo1.update({'relx': 0.05, 'rely': 0.05, 'relwidth': 0.9, 'relheight': 0.42, 'layout_relwidth': 0.9, 'layout_relheight': 0.42}); geometries.append(geo1)
            geo2 = base_photo_data.copy(); geo2.update({'relx': 0.05, 'rely': 0.53, 'relwidth': 0.42, 'relheight': 0.42, 'layout_relwidth': 0.42, 'layout_relheight': 0.42}); geometries.append(geo2)
            geo3 = base_photo_data.copy(); geo3.update({'relx': 0.53, 'rely': 0.53, 'relwidth': 0.42, 'relheight': 0.42, 'layout_relwidth': 0.42, 'layout_relheight': 0.42}); geometries.append(geo3)
        elif count == 4:
            for rely in [0.05, 0.53]:
                for relx in [0.05, 0.53]:
                    geo = base_photo_data.copy()
                    geo.update({'relx': relx, 'rely': rely, 'relwidth': 0.42, 'relheight': 0.42, 'layout_relwidth': 0.42, 'layout_relheight': 0.42})
                    geometries.append(geo)
        else:
            if count == 0: return []
            
            cols = int(math.ceil(math.sqrt(count)))
            rows = int(math.ceil(count / cols))
            
            padding, spacing = 0.05, 0.03
            total_space_w = 1.0 - (2 * padding) - ((cols - 1) * spacing)
            total_space_h = 1.0 - (2 * padding) - ((rows - 1) * spacing)
            cell_w, cell_h = total_space_w / cols, total_space_h / rows

            for i in range(count):
                c, r = i % cols, i // cols
                
                last_row_item_count = count % cols
                if last_row_item_count == 0: last_row_item_count = cols
                
                row_offset = 0
                if r == rows - 1 and last_row_item_count < cols:
                    row_width = (last_row_item_count * cell_w) + ((last_row_item_count - 1) * spacing)
                    row_offset = (1.0 - row_width - 2 * padding) / 2
                
                rel_x = padding + row_offset + c * (cell_w + spacing)
                rel_y = padding + r * (cell_h + spacing)
                
                geo = base_photo_data.copy()
                geo.update({'relx': rel_x, 'rely': rel_y, 'relwidth': cell_w, 'relheight': cell_h, 'layout_relwidth': cell_w, 'layout_relheight': cell_h})
                geometries.append(geo)
            
        return geometries

    def proceed_to_editor(self):
        if not self.selected_layout_card:
            messagebox.showwarning("Figyelem", "Kérjük válassz egy oldalelrendezést!")
            return

        new_layout_count = self.current_layout

        if not self.pages:
            # Új projekt létrehozása
            page_size_name = self.selected_book_size_name.get()
            page_size_pixels = self.BOOK_SIZES.get(page_size_name, self.DEFAULT_BOOK_SIZE_PIXELS)
            
            new_page = {
                'photos': self._generate_layout_template(new_layout_count), 
                'texts': [],
                'size': page_size_pixels  # Méret hozzáadása az oldal adataihoz
            }
            self.pages.append(new_page)
            self.current_page = 0
        else:
            # Meglévő oldal módosítása
            current_page_data = self.pages[self.current_page]
            current_photos = current_page_data.get('photos', [])
            current_photo_count = len(current_photos)
            
            photos_with_content = [p for p in current_photos if p.get('path')]
            if new_layout_count < len(photos_with_content):
                if not messagebox.askyesno("Figyelem!",
                                           f"Az új elrendezés ({new_layout_count} kép) kevesebb helyet tartalmaz, mint a jelenleg beillesztett képek száma ({len(photos_with_content)}).\n\n"
                                           "A felesleges képek el fognak veszni erről az oldalról.\n"
                                           "A háttér és a szövegek megmaradnak.\n\n"
                                           "Biztosan folytatja?"):
                    self.show_page_selection(is_new_project=False)
                    return

            old_photo_paths_to_keep = []
            old_properties_to_remap = {}
            for i in range(current_photo_count):
                if current_photos[i].get('path'):
                    old_photo_paths_to_keep.append(current_photos[i]['path'])
                    
                    key = str((self.current_page, i))
                    if key in self.photo_properties:
                        new_temp_index = len(old_photo_paths_to_keep) - 1
                        old_properties_to_remap[new_temp_index] = self.photo_properties[key]

            for i in range(current_photo_count):
                key_to_delete = str((self.current_page, i))
                if key_to_delete in self.photo_properties:
                    del self.photo_properties[key_to_delete]
            
            new_layout = self._generate_layout_template(new_layout_count)

            for i in range(len(new_layout)):
                if i < len(old_photo_paths_to_keep):
                    new_layout[i]['path'] = old_photo_paths_to_keep[i]
                    
                    if i in old_properties_to_remap:
                        new_key = str((self.current_page, i))
                        self.photo_properties[new_key] = old_properties_to_remap[i]
            
            current_page_data['photos'] = new_layout
            self.z_order[str(self.current_page)] = list(range(new_layout_count))

        if not self.editor_ui_built:
            self._build_editor_ui()
            self.editor_ui_built = True
        
        self.refresh_editor_view()

    def _build_editor_ui(self):
        self.clear_window()
        self.main_editor_frame = ctk.CTkFrame(self.root, fg_color=self.colors['bg_primary'], corner_radius=0)
        self.main_editor_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.title_label = ctk.CTkLabel(self.main_editor_frame, text="", font=ctk.CTkFont(size=28, weight="bold"), text_color="white")
        self.title_label.pack(pady=(5, 15))
        
        toolbar = ctk.CTkFrame(self.main_editor_frame, height=70, fg_color=self.colors['card_bg'], corner_radius=15)
        toolbar.pack(side="bottom", fill="x", pady=(15, 0))
        toolbar.pack_propagate(False)
        toolbar_buttons = [("💾 Mentés", self.save_project), ("📁 Betöltés", self.load_project), ("📤 Exportálás", self.export_project), ("🏠 Főmenü", self.create_main_menu)]
        buttons_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        buttons_frame.pack(expand=True)
        for text, command in toolbar_buttons:
            ctk.CTkButton(buttons_frame, text=text, command=command, width=140, height=40, font=ctk.CTkFont(size=12), corner_radius=10, fg_color=self.colors['button_bg'], text_color=self.colors['text_secondary'], hover_color='#F0F0F0').pack(side="left", padx=10, pady=15)
        
        workspace = ctk.CTkFrame(self.main_editor_frame, fg_color="transparent")
        workspace.pack(fill="both", expand=True, pady=5, padx=10)
        
        left_panel = ctk.CTkFrame(workspace, width=220, fg_color=self.colors['card_bg'], corner_radius=20)
        left_panel.pack(side="left", fill="y", padx=(0, 10))
        left_panel.pack_propagate(False)
        ctk.CTkLabel(left_panel, text="Oldalak", font=ctk.CTkFont(size=18, weight="bold"), text_color=self.colors['text_primary']).pack(pady=(20, 15))
        self.left_panel_scroll = ctk.CTkScrollableFrame(left_panel, fg_color="transparent")
        self.left_panel_scroll.pack(expand=True, fill="both", pady=10, padx=10)
        ctk.CTkButton(left_panel, text="+ Új oldal", command=self.add_new_page_and_refresh, height=40, font=ctk.CTkFont(size=14, weight="bold"), corner_radius=15, fg_color=self.colors['accent'], hover_color='#8A9654').pack(pady=15, padx=10, fill="x")
        
        right_panel = ctk.CTkFrame(workspace, width=260, fg_color=self.colors['card_bg'], corner_radius=20)
        right_panel.pack(side="right", fill="y", padx=(10,0))
        right_panel.pack_propagate(False)
        self._build_right_panel(right_panel)

        self.canvas = Canvas(workspace, bg=self.colors['canvas_workspace_bg'], highlightthickness=0, relief='ridge')
        self.canvas.pack(side="left", fill="both", expand=True, padx=10)

    
    def _build_right_panel(self, right_panel):
        ctk.CTkLabel(right_panel, text="Eszközök", font=ctk.CTkFont(size=18, weight="bold"), text_color=self.colors['text_primary']).pack(pady=(10, 5))
        tools_scroll_area = ctk.CTkScrollableFrame(right_panel, fg_color="transparent")
        tools_scroll_area.pack(fill="both", expand=True, padx=5, pady=5)
        
        wizard_frame = ctk.CTkFrame(tools_scroll_area, fg_color="transparent")
        wizard_frame.pack(pady=5, fill="x", padx=10)
        ctk.CTkButton(wizard_frame, text="✨ Alap Varázsló", command=self.run_basic_wizard).pack(pady=4, fill="x")
        ctk.CTkButton(wizard_frame, text="🧠 Okos Varázsló", command=self.run_smart_wizard, fg_color=self.colors['accent'], hover_color='#8A9654').pack(pady=4, fill="x")

        # --- KÉP ILLESZTÉS SZEKCIÓ ---
        fit_mode_frame = ctk.CTkFrame(tools_scroll_area, fg_color="transparent")
        fit_mode_frame.pack(pady=(10, 5), fill="x", padx=10)
        ctk.CTkLabel(fit_mode_frame, text="Kép illesztése", font=ctk.CTkFont(size=12, weight="bold"), text_color="grey").pack()
        
        self.fit_mode_button = ctk.CTkSegmentedButton(
            fit_mode_frame,
            values=["Beleillesztés", "Kitöltés"],
            command=self._change_fit_mode
        )
        self.fit_mode_button.pack(fill="x", padx=5, pady=(5, 10))
        self.fit_mode_button.set("Kitöltés") # MÓDOSÍTVA: Alapértelmezett a Kitöltés
        
        slider_frame = ctk.CTkFrame(tools_scroll_area, fg_color="transparent")
        slider_frame.pack(pady=5, fill="x", padx=10)

        ctk.CTkLabel(slider_frame, text="Kép nagyítása és mozgatása", font=ctk.CTkFont(size=12, weight="bold"), text_color="grey").pack()

        ctk.CTkLabel(slider_frame, text="Nagyítás", font=ctk.CTkFont(size=12), text_color="grey").pack()
        self.zoom_slider = ctk.CTkSlider(slider_frame, from_=1.0, to=5.0, command=self._update_photo_properties)
        self.zoom_slider.pack(fill="x", padx=5, pady=(0, 10))
        ctk.CTkLabel(slider_frame, text="Vízszintes pozíció", font=ctk.CTkFont(size=12), text_color="grey").pack()
        self.pan_x_slider = ctk.CTkSlider(slider_frame, from_=0.0, to=1.0, command=self._update_photo_properties)
        self.pan_x_slider.pack(fill="x", padx=5, pady=(0, 10))
        ctk.CTkLabel(slider_frame, text="Függőleges pozíció", font=ctk.CTkFont(size=12), text_color="grey").pack()
        self.pan_y_slider = ctk.CTkSlider(slider_frame, from_=0.0, to=1.0, command=self._update_photo_properties)
        self.pan_y_slider.pack(fill="x", padx=5, pady=(0, 10))

        ctk.CTkLabel(slider_frame, text="Keret mérete", font=ctk.CTkFont(size=12, weight="bold"), text_color="grey").pack()
        ctk.CTkLabel(slider_frame, text="Szélesség", font=ctk.CTkFont(size=12), text_color="grey").pack()
        self.width_slider = ctk.CTkSlider(slider_frame, from_=0.1, to=1.0, command=self._update_photo_size_from_sliders)
        self.width_slider.pack(fill="x", padx=5, pady=(0, 10))
        ctk.CTkLabel(slider_frame, text="Magasság", font=ctk.CTkFont(size=12), text_color="grey").pack()
        self.height_slider = ctk.CTkSlider(slider_frame, from_=0.1, to=1.0, command=self._update_photo_size_from_sliders)
        self.height_slider.pack(fill="x", padx=5, pady=(0, 10))
        
        effects_frame = ctk.CTkFrame(tools_scroll_area, fg_color="transparent")
        effects_frame.pack(pady=5, fill="x", padx=10)
        ctk.CTkLabel(effects_frame, text="Kép effektek", font=ctk.CTkFont(size=12, weight="bold"), text_color="grey").pack()
        ctk.CTkLabel(effects_frame, text="Fényerő", font=ctk.CTkFont(size=12), text_color="grey").pack()
        self.brightness_slider = ctk.CTkSlider(effects_frame, from_=0.5, to=1.5, command=self._update_photo_properties)
        self.brightness_slider.pack(fill="x", padx=5, pady=(0, 10)); self.brightness_slider.set(1.0)
        ctk.CTkLabel(effects_frame, text="Kontraszt", font=ctk.CTkFont(size=12), text_color="grey").pack()
        self.contrast_slider = ctk.CTkSlider(effects_frame, from_=0.5, to=1.5, command=self._update_photo_properties)
        self.contrast_slider.pack(fill="x", padx=5, pady=(0, 10)); self.contrast_slider.set(1.0)
        ctk.CTkLabel(effects_frame, text="Színerősség", font=ctk.CTkFont(size=12), text_color="grey").pack()
        self.saturation_slider = ctk.CTkSlider(effects_frame, from_=0.0, to=2.0, command=self._update_photo_properties)
        self.saturation_slider.pack(fill="x", padx=5, pady=(0, 10)); self.saturation_slider.set(1.0)
        self.grayscale_checkbox = ctk.CTkCheckBox(effects_frame, text="Fekete-fehér", command=self._update_photo_properties)
        self.grayscale_checkbox.pack(pady=5)
        
        tools_frame = ctk.CTkFrame(tools_scroll_area, fg_color="transparent")
        tools_frame.pack(pady=5, fill="x", padx=10)
        tools = [
            ("🎨 Háttér (Szín/Kép)", self.set_background),
            ("📝 Szöveg", self.add_text), 
            ("🖼️ Képkeret", self.add_frame), 
            ("🖼️ Oldalkerete", self.add_page_frame),
            ("📏 Oldalméret módosítása", self.change_page_size), 
            ("🔄 Elrendezés váltása", self.change_current_page_layout),
            ("🖼️ Kép cseréje", self._replace_photo),
            ("🔼 Előrehozás", self._bring_photo_forward),
            ("🔽 Hátraküldés", self._send_photo_backward),
            ("⏫ Legelőre hozás", self._bring_photo_to_front),
            ("⏬ Leghátra küldés", self._send_photo_to_back),
            ("🖼️+ Kép hozzáadása", self._add_photo_placeholder), 
            ("🖼️- Kép törlése", self._delete_photo_placeholder), 
            ("🗑️ Oldal törlése", self.delete_page)
        ]
        for text, command in tools:
            ctk.CTkButton(tools_frame, text=text, command=command, height=35, font=ctk.CTkFont(size=12), corner_radius=10, fg_color=self.colors['button_bg'], text_color=self.colors['text_secondary'], hover_color='#F0F0F0').pack(pady=4, fill="x")

    def _bring_photo_to_front(self):
        """A kiválasztott képet a rétegsorrend legtetejére helyezi."""
        if self.selected_photo_index is None:
            messagebox.showwarning("Nincs Kijelölés", "Kérlek, válassz ki egy képet a művelethez!")
            return

        page_key = str(self.current_page)
        if page_key not in self.z_order:
             self.z_order[page_key] = list(range(len(self.pages[self.current_page]['photos'])))

        order = self.z_order[page_key]
        if self.selected_photo_index in order:
            order.remove(self.selected_photo_index)
        order.append(self.selected_photo_index) # A lista végére helyezzük, ami a legfelső réteg
        self.refresh_editor_view()

    def _send_photo_to_back(self):
        """A kiválasztott képet a rétegsorrend legaljára helyezi."""
        if self.selected_photo_index is None:
            messagebox.showwarning("Nincs Kijelölés", "Kérlek, válassz ki egy képet a művelethez!")
            return

        page_key = str(self.current_page)
        if page_key not in self.z_order:
            self.z_order[page_key] = list(range(len(self.pages[self.current_page]['photos'])))

        order = self.z_order[page_key]
        if self.selected_photo_index in order:
            order.remove(self.selected_photo_index)
        order.insert(0, self.selected_photo_index) # A lista elejére helyezzük, ami a legalsó réteg
        self.refresh_editor_view()


    def refresh_editor_view(self):
        if not self.editor_ui_built or not self.pages:
            return

        current_page_data = self.pages[self.current_page]
        title_text = f"Fotókönyv szerkesztő - Oldal {self.current_page + 1} ({len(current_page_data.get('photos',[]))} képes)"
        self.title_label.configure(text=title_text)

        for widget in self.left_panel_scroll.winfo_children():
            widget.destroy()
        
        for i, page in enumerate(self.pages):
            page_frame = ctk.CTkFrame(self.left_panel_scroll, height=90, fg_color=self.colors['accent'] if i == self.current_page else self.colors['bg_secondary'], corner_radius=15)
            page_frame.pack(pady=5, fill="x"); page_frame.pack_propagate(False)
            page_label = ctk.CTkLabel(page_frame, text=f"{i + 1}. oldal\n({len(page.get('photos',[]))} kép)", font=ctk.CTkFont(size=11), text_color="white")
            page_label.pack(expand=True)
            page_frame.bind("<Button-1>", lambda e, idx=i: self.select_page(idx)); page_label.bind("<Button-1>", lambda e, idx=i: self.select_page(idx))
        
        # A renderelés előtt a vászon frissítése biztosítja a helyes méreteket
        self.root.update_idletasks() 
        self._render_page_content()
        
        current_selection = self.selected_photo_index
        self._deselect_all()
        if current_selection is not None:
                 self._select_photo(current_selection)

    def _render_page_content(self):
        self.canvas.delete("all")
        self.widget_to_canvas_item.clear()
        self.photo_frames.clear()
        self.text_widgets.clear()
        
        self._render_background()
        self.create_photo_layout()
        self._render_text_boxes()
        self._render_page_frame()

    # --- CANVAS-ALAPÚ RENDERELŐ FÜGGVÉNYEK ---

    def _get_page_draw_area(self):
        """Kiszámolja a lap arányainak megfelelő rajzolási területet a vásznon belül."""
        # ÚJ: Árnyék mérete pixelben
        shadow_offset = 15 

        canvas_w = self.canvas.winfo_width() - (shadow_offset * 2)
        canvas_h = self.canvas.winfo_height() - (shadow_offset * 2)

        page_data = self.pages[self.current_page]
        page_pixel_w, page_pixel_h = page_data.get('size', self.DEFAULT_BOOK_SIZE_PIXELS)
        
        if page_pixel_h == 0 or canvas_h <= 0:
            return 0, 0, self.canvas.winfo_width(), self.canvas.winfo_height()

        page_ratio = page_pixel_w / page_pixel_h
        canvas_ratio = canvas_w / canvas_h

        if page_ratio > canvas_ratio:
            draw_w = canvas_w
            draw_h = canvas_w / page_ratio
        else:
            draw_h = canvas_h
            draw_w = canvas_h * page_ratio
            
        # Az eltolást most már az eredeti vászonmérethez és az árnyékhoz is igazítjuk
        offset_x = (self.canvas.winfo_width() - draw_w) / 2
        offset_y = (self.canvas.winfo_height() - draw_h) / 2
        
        return int(offset_x), int(offset_y), int(draw_w), int(draw_h)

    def _render_background(self):
        offset_x, offset_y, draw_w, draw_h = self._get_page_draw_area()
        if draw_w <= 1 or draw_h <= 1: return

        page_data = self.pages[self.current_page]
        bg_setting = page_data.get('background')

        if self.canvas_bg_item:
            self.canvas.delete(self.canvas_bg_item)
            self.canvas_bg_item = None
            self.bg_photo_image = None

        try:
            # --- ÁRNYÉK ÉS HÁTTÉR LÉTREHOZÁSA KÉPKÉNT ---
            shadow_blur = 15  # Az elmosás mértéke
            shadow_color = '#282828' # Sötétszürke árnyék

            # 1. Létrehozunk egy nagyobb, átlátszó vásznat az árnyéknak
            shadow_canvas = Image.new('RGBA', (draw_w + shadow_blur*2, draw_h + shadow_blur*2), (0, 0, 0, 0))
            shadow_draw = ImageDraw.Draw(shadow_canvas)

            # 2. Rajzolunk egy fekete téglalapot a közepére (ez lesz az elmosott árnyék)
            shadow_draw.rectangle(
                (shadow_blur, shadow_blur, draw_w + shadow_blur, draw_h + shadow_blur),
                fill=shadow_color
            )

            # 3. Alkalmazzuk az elmosás effektet
            shadow_canvas = shadow_canvas.filter(ImageFilter.GaussianBlur(radius=shadow_blur / 2))

            # 4. Létrehozzuk a tényleges oldal hátterét
            if isinstance(bg_setting, dict) and bg_setting.get('type') == 'image':
                img_path = bg_setting.get('path')
                if img_path and os.path.exists(img_path):
                    page_bg_img = Image.open(img_path).convert("RGBA").resize((draw_w, draw_h), Image.LANCZOS)
                else: # Ha a kép nem található, fehér lesz
                    page_bg_img = Image.new('RGBA', (draw_w, draw_h), 'white')
            else:
                bg_color = bg_setting if isinstance(bg_setting, str) and bg_setting.startswith('#') else self.colors['card_bg']
                page_bg_img = Image.new('RGBA', (draw_w, draw_h), bg_color)

            # 5. A kész oldal hátterét ráillesztjük az árnyék közepére
            shadow_canvas.paste(page_bg_img, (shadow_blur, shadow_blur))

            # 6. A végső, árnyékkal ellátott képet jelenítjük meg
            self.bg_photo_image = ImageTk.PhotoImage(shadow_canvas)
            self.canvas_bg_item = self.canvas.create_image(
                offset_x - shadow_blur,  # Az eltolást korrigáljuk az árnyék méretével
                offset_y - shadow_blur, 
                image=self.bg_photo_image, 
                anchor="nw", 
                tags="background"
            )

        except Exception as e:
            print(f"HIBA a háttér renderelésekor: {e}")
            traceback.print_exc()
            self.canvas.create_rectangle(offset_x, offset_y, offset_x + draw_w, offset_y + draw_h, fill="red", outline="")

    def set_background_image(self):
        filename = filedialog.askopenfilename(
            title="Válassz háttérképet",
            filetypes=[("Képfájlok", "*.jpg *.jpeg *.png"), ("Minden fájl", "*.*")]
        )
        if filename:
            self.pages[self.current_page]['background'] = {'type': 'image', 'path': filename}
            self.refresh_editor_view()
    
    def set_background(self):
        """Felugró ablakot nyit a háttér beállításához, ami már görgethető, ha a tartalom túl nagy."""
        color_picker = ctk.CTkToplevel(self.root)
        color_picker.title("Háttér beállítása")
        color_picker.geometry("400x500")
        color_picker.transient(self.root)
        color_picker.grab_set()

        # Létrehozunk egy fő görgethető keretet, amibe minden más elem kerül.
        main_scroll_frame = ctk.CTkScrollableFrame(color_picker)
        main_scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

        def _apply_background(setting):
            self.pages[self.current_page]['background'] = setting
            color_picker.destroy()
            self.refresh_editor_view()

        def _upload_background_image():
            filename = filedialog.askopenfilename(
                title="Válassz háttérképet",
                filetypes=[("Képfájlok", "*.jpg *.jpeg *.png"), ("Minden fájl", "*.*")]
            )
            if filename:
                _apply_background({'type': 'image', 'path': filename})

        # Az elemek szülője mostantól a 'main_scroll_frame'
        ctk.CTkLabel(main_scroll_frame, text="Beépített hátterek", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(15, 5))
        preset_bg_frame = ctk.CTkFrame(main_scroll_frame, fg_color="transparent")
        preset_bg_frame.pack(pady=5, padx=10)
        
        backgrounds_path = os.path.join(self.assets_path, "backgrounds")
        if os.path.exists(backgrounds_path):
            preset_files = [f for f in os.listdir(backgrounds_path) if f.lower().endswith(('.png', '.jpg'))]
            for i, fname in enumerate(preset_files):
                fpath = os.path.join(backgrounds_path, fname)
                try:
                    thumb = ctk.CTkImage(Image.open(fpath), size=(60,60))
                    btn = ctk.CTkButton(preset_bg_frame, image=thumb, text="", width=60, height=60,
                                        command=lambda p=fpath: _apply_background({'type': 'image', 'path': p}))
                    btn.grid(row=i // 4, column=i % 4, padx=5, pady=5)
                except Exception as e:
                    print(f"Hiba a beépített háttér betöltésekor ({fname}): {e}")

        ctk.CTkLabel(main_scroll_frame, text="Színek", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(15, 5))
        palette_frame = ctk.CTkFrame(main_scroll_frame, fg_color="transparent")
        palette_frame.pack(pady=5, padx=10)
        colors_list = ['#FFFFFF', '#F0F0F0', '#D3E3F1', '#D1F0D1', '#F5E6D3', '#E6D3F5', '#FFDDC1', '#FFD1D1']
        for i, color in enumerate(colors_list):
            ctk.CTkButton(palette_frame, text="", fg_color=color, width=40, height=40, corner_radius=8, command=lambda c=color: _apply_background(c)).grid(row=i // 4, column=i % 4, padx=10, pady=10)
        
        ctk.CTkLabel(main_scroll_frame, text="Vagy adj meg egyéni színt:", font=ctk.CTkFont(size=14)).pack(pady=(10, 5))
        custom_color_frame = ctk.CTkFrame(main_scroll_frame, fg_color="transparent")
        custom_color_frame.pack(pady=5, padx=20, fill="x")
        custom_color_entry = ctk.CTkEntry(custom_color_frame, placeholder_text="#RRGGBB")
        custom_color_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(custom_color_frame, text="Alkalmaz", width=80, command=lambda: _apply_background(custom_color_entry.get())).pack(side="left")

        ctk.CTkLabel(main_scroll_frame, text="Vagy tölts fel saját képet:", font=ctk.CTkFont(size=14)).pack(pady=(15, 5))
        ctk.CTkButton(main_scroll_frame, text="🖼️ Háttérkép feltöltése...", command=_upload_background_image).pack(pady=5, padx=20, fill="x")
        
        ctk.CTkButton(main_scroll_frame, text="Háttér eltávolítása", command=lambda: _apply_background(None)).pack(pady=15, padx=20, fill="x")

    def _render_page_frame(self):
        offset_x, offset_y, draw_w, draw_h = self._get_page_draw_area()
        if draw_w <= 1 or draw_h <= 1: return

        current_page_data = self.pages[self.current_page]
        page_frame_path = current_page_data.get('page_frame_path')
        
        if self.canvas_page_frame_item:
            self.canvas.delete(self.canvas_page_frame_item)
            self.canvas_page_frame_item = None
            self.page_frame_photo_image = None

        if page_frame_path:
            thickness_ratio = current_page_data.get('page_frame_thickness', 0.05)
            frame_img = None
            if page_frame_path.startswith('preset_'): 
                frame_img = self._create_preset_frame(page_frame_path, (draw_w, draw_h), thickness_ratio)
            elif os.path.exists(page_frame_path): 
                frame_img = Image.open(page_frame_path).convert("RGBA").resize((draw_w, draw_h), Image.LANCZOS)
            
            if frame_img:
                self.page_frame_photo_image = ImageTk.PhotoImage(frame_img)
                self.canvas_page_frame_item = self.canvas.create_image(offset_x, offset_y, image=self.page_frame_photo_image, anchor="nw", tags="page_frame")

    def _create_preset_frame(self, preset_name, size, thickness_ratio=0.05):
        width, height = size
        frame_thickness = int(min(width, height) * thickness_ratio)
        if frame_thickness < 1: frame_thickness = 1
        color_map = {'preset_black': (0, 0, 0, 200), 'preset_white': (255, 255, 255, 200), 'preset_gold': (212, 175, 55, 220)}
        color = color_map.get(preset_name, (0,0,0,0))
        frame_image = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(frame_image)
        for i in range(frame_thickness):
            draw.rectangle((i, i, width - 1 - i, height - 1 - i), outline=color, width=1)
        return frame_image

    def create_photo_layout(self):
        if not hasattr(self.pages[self.current_page], 'get'): return
        photos_data = self.pages[self.current_page].get('photos', [])
        offset_x, offset_y, draw_w, draw_h = self._get_page_draw_area()
        if draw_w <= 1 or draw_h <= 1: return

        self.photo_frames = [None] * len(photos_data)
        
        page_key = str(self.current_page)
        if page_key not in self.z_order or len(self.z_order[page_key]) != len(photos_data):
            self.z_order[page_key] = list(range(len(photos_data)))
        
        ordered_indices = self.z_order[page_key]
        valid_indices = [i for i in ordered_indices if i < len(photos_data)]

        for i in valid_indices:
            photo_data = photos_data[i]
            photo_frame = ctk.CTkFrame(self.canvas, fg_color="#CCCCCC", corner_radius=10, border_width=0)
            
            self.photo_frames[i] = photo_frame
            
            frame_w = int(photo_data['relwidth'] * draw_w)
            frame_h = int(photo_data['relheight'] * draw_h)
            abs_x = offset_x + int(photo_data['relx'] * draw_w)
            abs_y = offset_y + int(photo_data['rely'] * draw_h)
            
            canvas_item_id = self.canvas.create_window(abs_x, abs_y, window=photo_frame, width=frame_w, height=frame_h, anchor='nw', tags="photo")
            self.widget_to_canvas_item[photo_frame] = canvas_item_id
            
            photo_frame.bind("<ButtonPress-1>", lambda e, index=i: self._on_widget_press(e, 'photo', index))
            photo_frame.bind("<B1-Motion>", lambda e: self._on_widget_drag(e))
            photo_frame.bind("<ButtonRelease-1>", lambda e: self._on_widget_release(e))

            self.display_photo_placeholder(photo_frame, photo_data, i, is_update=False)

    def display_photo_placeholder(self, parent_frame, photo_data, photo_index, is_update=False):
        if not is_update:
            for widget in parent_frame.winfo_children(): widget.destroy()
        
        photo_path = photo_data.get('path')
        if not photo_path or not os.path.exists(photo_path):
            add_btn = ctk.CTkButton(parent_frame, text="+", font=ctk.CTkFont(size=24), fg_color=self.colors['accent'], hover_color='#8A9654', command=lambda idx=photo_index: self.add_photo_to_slot(idx))
            add_btn.place(relx=0.5, rely=0.5, anchor="center")
            return

        try:
            key = str((self.current_page, photo_index))
            props = self.photo_properties.get(key, {})
            parent_frame.update_idletasks()

            # --- ÚJ LOGIKA A KERET MÉRETÉNEK DINAMIKUS BEÁLLÍTÁSÁHOZ ---
            fit_mode = props.get('fit_mode', 'fill')
            _, _, draw_w, draw_h = self._get_page_draw_area()

            # Először az elrendezésben definiált "mester" méretet használjuk
            master_rel_w = photo_data.get('layout_relwidth', photo_data['relwidth'])
            master_rel_h = photo_data.get('layout_relheight', photo_data['relheight'])
            
            frame_w = int(master_rel_w * draw_w)
            frame_h = int(master_rel_h * draw_h)

            original_img = Image.open(photo_path) # Csak az arányok miatt kell betölteni

            # Ha "Beleillesztés" módban vagyunk, a keret méretét a kép arányaihoz igazítjuk
            if fit_mode == 'fit':
                img_ratio = original_img.width / original_img.height
                frame_ratio = frame_w / frame_h if frame_h > 0 else 1
                
                if img_ratio > frame_ratio: # A kép szélesebb, mint a keret
                    frame_h = int(frame_w / img_ratio)
                else: # A kép magasabb, mint a keret
                    frame_w = int(frame_h * img_ratio)
            
            # Frissítjük a widget méretét a vásznon
            canvas_item_id = self.widget_to_canvas_item.get(parent_frame)
            if canvas_item_id:
                self.canvas.itemconfig(canvas_item_id, width=frame_w, height=frame_h)
            parent_frame.update_idletasks() # Várakozás, hogy az új méret érvénybe lépjen

            # --- EDDIGI LOGIKA INNENTŐL FOLYTATÓDIK, DE MÁR A HELYES `frame_w` ÉS `frame_h` ÉRTÉKEKKEL ---
            if frame_w <= 1 or frame_h <= 1: return

            original_img = original_img.convert("RGBA") # Újra konvertáljuk, ha kell
            
            if props.get('grayscale', False):
                original_img = original_img.convert('L').convert('RGBA')
            enhancer = ImageEnhance.Brightness(original_img); original_img = enhancer.enhance(props.get('brightness', 1.0))
            enhancer = ImageEnhance.Contrast(original_img); original_img = enhancer.enhance(props.get('contrast', 1.0))
            enhancer = ImageEnhance.Color(original_img); original_img = enhancer.enhance(props.get('saturation', 1.0))

            zoom, pan_x, pan_y = props.get('zoom', 1.0), props.get('pan_x', 0.5), props.get('pan_y', 0.5)
            
            if fit_mode == 'fill':
                img_ratio = original_img.width / original_img.height; frame_ratio = frame_w / frame_h
                if img_ratio > frame_ratio: new_h, new_w = int(frame_h * zoom), int(frame_h * zoom * img_ratio)
                else: new_w, new_h = int(frame_w * zoom), int(frame_w * zoom / img_ratio)
                if new_w < frame_w: new_w = frame_w; new_h = int(new_w / img_ratio)
                if new_h < frame_h: new_h = frame_h; new_w = int(new_h * img_ratio)
                zoomed_img = original_img.resize((new_w, new_h), Image.LANCZOS)
                extra_w, extra_h = max(0, new_w - frame_w), max(0, new_h - frame_h)
                crop_x, crop_y = int(extra_w * pan_x), int(extra_h * pan_y)
                final_image = zoomed_img.crop((crop_x, crop_y, crop_x + frame_w, crop_y + frame_h))
            else: # 'fit' mód
                fit_w, fit_h = frame_w, frame_h # A keret már a helyes méretű
                new_w, new_h = int(fit_w * zoom), int(fit_h * zoom)
                if new_w < 1 or new_h < 1: new_w, new_h = 1, 1
                resized_img = original_img.resize((new_w, new_h), Image.LANCZOS)
                final_image = Image.new('RGBA', (frame_w, frame_h), (0, 0, 0, 0))
                extra_w, extra_h = max(0, new_w - frame_w), max(0, new_h - frame_h)
                paste_x = (frame_w - new_w) // 2 - int(extra_w * (pan_x - 0.5))
                paste_y = (frame_h - new_h) // 2 - int(extra_h * (pan_y - 0.5))
                final_image.paste(resized_img, (paste_x, paste_y), resized_img)

            frame_path = props.get('frame_path')
            if frame_path:
                # ... (a keret logika változatlan) ...
                thickness_ratio = props.get('frame_thickness', 0.05)
                frame_img = None
                if frame_path.startswith('preset_'): frame_img = self._create_preset_frame(frame_path, (frame_w, frame_h), thickness_ratio)
                elif os.path.exists(frame_path): frame_img = Image.open(frame_path).convert("RGBA")
                if frame_img:
                    f_scale = props.get('frame_scale', 1.0); f_off_x = props.get('frame_offset_x', 0); f_off_y = props.get('frame_offset_y', 0)
                    new_fw, new_fh = int(frame_w * f_scale), int(frame_h * f_scale)
                    resized_frame = frame_img.resize((new_fw, new_fh), Image.LANCZOS)
                    paste_x, paste_y = (frame_w - new_fw) // 2 + f_off_x, (frame_h - new_fh) // 2 + f_off_y
                    final_image.paste(resized_frame, (paste_x, paste_y), resized_frame)
            
            final_ctk_image = ctk.CTkImage(light_image=final_image.convert("RGB"), dark_image=final_image.convert("RGB"), size=(frame_w, frame_h))
            img_label = None
            if is_update and len(parent_frame.winfo_children()) > 0 and isinstance(parent_frame.winfo_children()[0], ctk.CTkLabel):
                img_label = parent_frame.winfo_children()[0]
            
            if img_label: img_label.configure(image=final_ctk_image)
            else:
                for widget in parent_frame.winfo_children(): widget.destroy()
                img_label = ctk.CTkLabel(parent_frame, image=final_ctk_image, text="")
                img_label.pack(fill="both", expand=True)
                img_label.bind("<ButtonPress-1>", lambda e, idx=photo_index: self._on_widget_press(e, 'photo', idx))
                img_label.bind("<B1-Motion>", lambda e: self._on_widget_drag(e))
                img_label.bind("<ButtonRelease-1>", lambda e: self._on_widget_release(e))

        except Exception as e:
            print(f"HIBA a kép megjelenítésekor: {e}\n{traceback.format_exc()}")
            ctk.CTkLabel(parent_frame, text="Hiba a kép\nbetöltésekor", text_color="red").place(relx=0.5, rely=0.5, anchor="center")

    def add_photo_to_slot(self, photo_index):
        filename = filedialog.askopenfilename(title="Válassz fotót", filetypes=[("Képfájlok", "*.jpg *.jpeg *.png *.gif *.bmp")])
        if filename:
            try:
                self.pages[self.current_page]['photos'][photo_index]['path'] = filename
                if filename not in self.uploaded_photos:
                    self.uploaded_photos.append(filename)
                
                frame_to_update = self.photo_frames[photo_index]
                data_to_update = self.pages[self.current_page]['photos'][photo_index]
                self.display_photo_placeholder(frame_to_update, data_to_update, photo_index, is_update=False)
            except IndexError:
                messagebox.showerror("Hiba", "Belső hiba történt a fotó hozzáadásakor. Kérem próbálja újra.")
                self.refresh_editor_view()

    def _add_photo_placeholder(self):
        new_photo = {
            'path': None, 
            'relx': 0.35, 'rely': 0.3, 
            'relwidth': 0.3, 'relheight': 0.4,
            'layout_relwidth': 0.3, 'layout_relheight': 0.4
        }
        photo_list = self.pages[self.current_page]['photos']
        photo_list.append(new_photo)
        
        new_index = len(photo_list) - 1

        page_key = str(self.current_page)
        if page_key not in self.z_order:
            self.z_order[page_key] = list(range(len(photo_list)))
        else:
            self.z_order[page_key].append(new_index)
        
        self.refresh_editor_view()

    def _update_photo_size_from_sliders(self, value=None):
        if self.selected_photo_index is None: return
        
        photo_data = self.pages[self.current_page]['photos'][self.selected_photo_index]
        photo_frame = self.photo_frames[self.selected_photo_index]
        
        _, _, draw_w, draw_h = self._get_page_draw_area()
        
        new_relwidth = self.width_slider.get()
        new_relheight = self.height_slider.get()
        
        # Mentsük el a manuális átméretezést mint új alapértelmezett elrendezési méret
        photo_data['relwidth'] = new_relwidth
        photo_data['relheight'] = new_relheight
        photo_data['layout_relwidth'] = new_relwidth
        photo_data['layout_relheight'] = new_relheight
        
        canvas_item_id = self.widget_to_canvas_item.get(photo_frame)
        if canvas_item_id:
            self.canvas.itemconfig(canvas_item_id, width=int(new_relwidth * draw_w), height=int(new_relheight * draw_h))
            
        self.display_photo_placeholder(photo_frame, photo_data, self.selected_photo_index, is_update=True)

    def _delete_photo_placeholder(self):
        """Törli a kiválasztott képkeretet és a hozzá tartozó tulajdonságokat,
        majd helyesen újraindexeli a többi kép tulajdonságait az oldalon."""
        if self.selected_photo_index is None:
            messagebox.showwarning("Törlés", "Nincs képkeret kiválasztva a törléshez.")
            return

        index_to_delete = self.selected_photo_index
        
        # 1. Töröljük a fotó adatait az oldal listájából
        self.pages[self.current_page]['photos'].pop(index_to_delete)
        
        # 2. Javítjuk a Z-sorrendet (rétegsorrend)
        page_key = str(self.current_page)
        if page_key in self.z_order:
            order = self.z_order[page_key]
            if index_to_delete in order:
                order.remove(index_to_delete)
            # A törölt index utáni elemek indexét eggyel csökkentjük
            self.z_order[page_key] = [idx - 1 if idx > index_to_delete else idx for idx in order]

        # 3. JAVÍTÁS: Újraindexeljük a `photo_properties` szótárat
        new_properties = {}
        for key_str, props in self.photo_properties.items():
            try:
                # A kulcsot (pl. '(0, 2)') felbontjuk oldal- és fotóindexre
                page_idx, photo_idx = tuple(map(int, key_str.strip('()').split(',')))
            except (ValueError, TypeError):
                new_properties[key_str] = props # Ha a kulcs formátuma más, megtartjuk
                continue

            if page_idx != self.current_page:
                new_properties[key_str] = props # Más oldalak tulajdonságait érintetlenül hagyjuk
            else:
                # Az aktuális oldalon lévő tulajdonságokat kezeljük
                if photo_idx < index_to_delete:
                    new_properties[key_str] = props # A törölt elem előttiakat megtartjuk
                elif photo_idx > index_to_delete:
                    # A törölt elem utániaknak új, eggyel kisebb indexet adunk
                    new_key = str((page_idx, photo_idx - 1))
                    new_properties[new_key] = props
        
        self.photo_properties = new_properties

        self._deselect_all()
        self.refresh_editor_view()

    def _replace_photo(self):
        """A kiválasztott kép cseréje egy újra, a beállítások megtartásával."""
        if self.selected_photo_index is None:
            messagebox.showwarning("Nincs Kijelölés", "Kérlek, először válassz ki egy képet a cseréhez!")
            return

        filename = filedialog.askopenfilename(
            title="Válassz egy új fotót",
            filetypes=[("Képfájlok", "*.jpg *.jpeg *.png *.gif *.bmp")]
        )
        
        if not filename:
            return

        try:
            self.pages[self.current_page]['photos'][self.selected_photo_index]['path'] = filename
            
            frame_to_update = self.photo_frames[self.selected_photo_index]
            data_to_update = self.pages[self.current_page]['photos'][self.selected_photo_index]
            self.display_photo_placeholder(frame_to_update, data_to_update, self.selected_photo_index, is_update=False)

        except IndexError:
            messagebox.showerror("Hiba", "Belső hiba történt a fotó cseréjekor. Kérem próbálja újra.")
            self.refresh_editor_view()



    def _bring_photo_forward(self):
        """A kiválasztott képet előrébb hozza a rétegsorrendben."""
        if self.selected_photo_index is None:
            messagebox.showwarning("Nincs Kijelölés", "Kérlek, válassz ki egy képet az előrehozáshoz!")
            return

        if str(self.current_page) not in self.z_order:
            self.z_order[str(self.current_page)] = list(range(len(self.pages[self.current_page]['photos'])))

        order = self.z_order[str(self.current_page)]
        
        try:
            current_pos = order.index(self.selected_photo_index)
        except ValueError:
            order.append(self.selected_photo_index)
            current_pos = order.index(self.selected_photo_index)

        if current_pos < len(order) - 1:
            order[current_pos], order[current_pos + 1] = order[current_pos + 1], order[current_pos]
            self.refresh_editor_view()

    def _send_photo_backward(self):
        """A kiválasztott képet hátrébb küldi a rétegsorrendben."""
        if self.selected_photo_index is None:
            messagebox.showwarning("Nincs Kijelölés", "Kérlek, válassz ki egy képet a hátraküldéshez!")
            return
            
        if str(self.current_page) not in self.z_order:
            self.z_order[str(self.current_page)] = list(range(len(self.pages[self.current_page]['photos'])))

        order = self.z_order[str(self.current_page)]
        
        try:
            current_pos = order.index(self.selected_photo_index)
        except ValueError:
            order.append(self.selected_photo_index)
            current_pos = order.index(self.selected_photo_index)

        if current_pos > 0:
            order[current_pos], order[current_pos - 1] = order[current_pos - 1], order[current_pos]
            self.refresh_editor_view()

    def add_frame(self):
        if self.selected_photo_index is None:
            messagebox.showwarning("Nincs kiválasztott kép", "Kérlek, először kattints egy képre a szerkesztéshez!")
            return
        if self.frame_editor_window is not None and self.frame_editor_window.winfo_exists():
            self.frame_editor_window.focus()
            return
        
        self.frame_editor_window = ctk.CTkToplevel(self.root)
        self.frame_editor_window.title("Képkeret szerkesztése")
        self.frame_editor_window.geometry("350x550")
        self.frame_editor_window.transient(self.root)
        self.frame_editor_window.attributes("-topmost", True)

        # --- JAVÍTÁS: Létrehozunk egy fő görgethető keretet ---
        # Minden mást ebbe a keretbe fogunk pakolni.
        main_scroll_frame = ctk.CTkScrollableFrame(self.frame_editor_window)
        main_scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
        # --------------------------------------------------------
        
        ctk.CTkLabel(main_scroll_frame, text="Beépített keretek", font=ctk.CTkFont(weight="bold")).pack(pady=(10, 5))
        
        preset_frame_container = ctk.CTkFrame(main_scroll_frame) # A szülő mostantól a main_scroll_frame
        preset_frame_container.pack(pady=5, padx=5, fill="x")

        preset_frame_ui = ctk.CTkFrame(preset_frame_container)
        preset_frame_ui.pack(pady=5, padx=0, fill="x")
        presets = [("Fekete", "preset_black"), ("Fehér", "preset_white"), ("Arany", "preset_gold")]
        for i, (name, path) in enumerate(presets):
            ctk.CTkButton(preset_frame_ui, text=name, command=lambda p=path: self._apply_frame(p)).grid(row=0, column=i, padx=5, pady=5, sticky="ew")
        preset_frame_ui.grid_columnconfigure((0, 1, 2), weight=1)

        frames_path = os.path.join(self.assets_path, "frames")
        if os.path.exists(frames_path):
            custom_preset_frame = ctk.CTkFrame(preset_frame_container) # Ez már lehet sima Frame
            custom_preset_frame.pack(pady=5, padx=0, fill="x")
            preset_files = [f for f in os.listdir(frames_path) if f.lower().endswith('.png')]
            for i, fname in enumerate(preset_files):
                fpath = os.path.join(frames_path, fname)
                try:
                    thumb = ctk.CTkImage(Image.open(fpath), size=(40, 40))
                    btn = ctk.CTkButton(custom_preset_frame, image=thumb, text="", width=60, height=60, command=lambda p=fpath: self._apply_frame(p))
                    btn.grid(row=i // 4, column=i % 4, padx=5, pady=5)
                except Exception as e:
                    print(f"Hiba a beépített keret betöltésekor ({fname}): {e}")

        ctk.CTkButton(main_scroll_frame, text="Saját keret feltöltése...", command=lambda: self._apply_frame(self._upload_custom_frame_path())).pack(pady=(10, 5), padx=5, fill="x")
        ctk.CTkLabel(main_scroll_frame, text="Beállítások", font=ctk.CTkFont(weight="bold")).pack(pady=(15, 5))
        
        self.slider_panel = ctk.CTkFrame(main_scroll_frame) # A szülő mostantól a main_scroll_frame
        self.slider_panel.pack(pady=5, padx=5, fill="both", expand=True)
        ctk.CTkLabel(self.slider_panel, text="Vastagság (beépített kereteknél)").pack()
        self.frame_thickness_slider = ctk.CTkSlider(self.slider_panel, from_=0.01, to=0.2, command=self._update_photo_properties)
        self.frame_thickness_slider.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(self.slider_panel, text="Méret").pack()
        self.frame_scale_slider = ctk.CTkSlider(self.slider_panel, from_=0.5, to=1.5, command=self._update_photo_properties)
        self.frame_scale_slider.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(self.slider_panel, text="Vízszintes eltolás").pack()
        self.frame_offset_x_slider = ctk.CTkSlider(self.slider_panel, from_=-100, to=100, number_of_steps=200, command=self._update_photo_properties)
        self.frame_offset_x_slider.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(self.slider_panel, text="Függőleges eltolás").pack()
        self.frame_offset_y_slider = ctk.CTkSlider(self.slider_panel, from_=-100, to=100, number_of_steps=200, command=self._update_photo_properties)
        self.frame_offset_y_slider.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkButton(main_scroll_frame, text="Keret eltávolítása", fg_color="#D32F2F", hover_color="#B71C1C", command=lambda: self._apply_frame(None)).pack(pady=10, padx=5, fill="x")
        self.update_frame_editor_ui()

    def _apply_frame(self, frame_path):
        if self.selected_photo_index is None: return
        key = str((self.current_page, self.selected_photo_index))
        if key not in self.photo_properties: self.photo_properties[key] = {}
        self.photo_properties[key]['frame_path'] = frame_path
        self.photo_properties[key]['frame_scale'] = 1.0; self.photo_properties[key]['frame_offset_x'] = 0; self.photo_properties[key]['frame_offset_y'] = 0
        self.photo_properties[key]['frame_thickness'] = 0.05
        
        if self.frame_editor_window and self.frame_editor_window.winfo_exists(): self.update_frame_editor_ui()
        self._update_photo_properties()

    def update_frame_editor_ui(self):
        if not (self.frame_editor_window and self.frame_editor_window.winfo_exists()): return
        key = str((self.current_page, self.selected_photo_index))
        props = self.photo_properties.get(key, {})
        
        sliders = [self.frame_scale_slider, self.frame_offset_x_slider, self.frame_offset_y_slider, self.frame_thickness_slider]
        
        if self.selected_photo_index is not None and props.get('frame_path'):
            for slider in sliders: slider.configure(state="normal")
            self.frame_scale_slider.set(props.get('frame_scale', 1.0))
            self.frame_offset_x_slider.set(props.get('frame_offset_x', 0))
            self.frame_offset_y_slider.set(props.get('frame_offset_y', 0))
            self.frame_thickness_slider.set(props.get('frame_thickness', 0.05))
            
            if not props.get('frame_path', '').startswith('preset_'):
                self.frame_thickness_slider.configure(state="disabled")

        else:
            for slider in sliders: slider.configure(state="disabled")
            self.frame_scale_slider.set(1.0); self.frame_offset_x_slider.set(0); self.frame_offset_y_slider.set(0)
            self.frame_thickness_slider.set(0.05)
            
    # --- KÉPKERET ÉS OLDALKERET METÓDUSOK ---

    def add_page_frame(self):
        """Felugró ablakot nyit az oldalkeretet beállításához, méretezési és eltolási opciókkal."""
        if self.page_frame_editor_window is not None and self.page_frame_editor_window.winfo_exists():
            self.page_frame_editor_window.focus()
            return
        
        self.page_frame_editor_window = ctk.CTkToplevel(self.root)
        self.page_frame_editor_window.title("Oldalkeretet szerkesztése")
        self.page_frame_editor_window.geometry("350x550")
        self.page_frame_editor_window.transient(self.root)
        self.page_frame_editor_window.attributes("-topmost", True)

        # --- JAVÍTÁS: Létrehozunk egy fő görgethető keretet ---
        main_scroll_frame = ctk.CTkScrollableFrame(self.page_frame_editor_window)
        main_scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
        # --------------------------------------------------------

        ctk.CTkLabel(main_scroll_frame, text="Válassz keretet az oldalhoz!", font=ctk.CTkFont(weight="bold")).pack(pady=10)

        preset_frame_container = ctk.CTkFrame(main_scroll_frame, fg_color="transparent") # A szülő mostantól a main_scroll_frame
        preset_frame_container.pack(pady=5, padx=5, fill="x")

        preset_frame_ui = ctk.CTkFrame(preset_frame_container)
        preset_frame_ui.pack(pady=5, fill="x")
        presets = [("Fekete", "preset_black"), ("Fehér", "preset_white"), ("Arany", "preset_gold")]
        for i, (name, path) in enumerate(presets):
            ctk.CTkButton(preset_frame_ui, text=name, command=lambda p=path: self._apply_page_frame(p)).grid(row=0, column=i, padx=5, pady=5, sticky="ew")
        preset_frame_ui.grid_columnconfigure((0, 1, 2), weight=1)

        frames_path = os.path.join(self.assets_path, "frames")
        if os.path.exists(frames_path):
            ctk.CTkLabel(preset_frame_container, text="Beépített keretek", font=ctk.CTkFont(size=12)).pack(pady=(10, 0))
            custom_preset_frame = ctk.CTkFrame(preset_frame_container) # Ez is lehet sima Frame
            custom_preset_frame.pack(pady=5, fill="x")
            preset_files = [f for f in os.listdir(frames_path) if f.lower().endswith('.png')]
            for i, fname in enumerate(preset_files):
                fpath = os.path.join(frames_path, fname)
                try:
                    thumb = ctk.CTkImage(Image.open(fpath), size=(50, 50))
                    btn = ctk.CTkButton(custom_preset_frame, image=thumb, text="", width=60, height=60, command=lambda p=fpath: self._apply_page_frame(p))
                    btn.grid(row=i // 4, column=i % 4, padx=5, pady=5)
                except Exception as e:
                    print(f"Hiba a beépített oldalkeret betöltésekor ({fname}): {e}")

        ctk.CTkButton(main_scroll_frame, text="Saját keret feltöltése...", command=lambda: self._apply_page_frame(self._upload_custom_frame_path())).pack(pady=(10, 5), padx=5, fill="x")
        
        ctk.CTkLabel(main_scroll_frame, text="Beállítások", font=ctk.CTkFont(weight="bold")).pack(pady=(15, 5))
        
        slider_panel = ctk.CTkFrame(main_scroll_frame) # A szülő mostantól a main_scroll_frame
        slider_panel.pack(pady=5, padx=5, fill="both", expand=True)

        ctk.CTkLabel(slider_panel, text="Vastagság (beépített kereteknél)").pack()
        self.page_frame_thickness_slider = ctk.CTkSlider(slider_panel, from_=0.01, to=0.2, command=self._update_page_frame_properties)
        self.page_frame_thickness_slider.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkLabel(slider_panel, text="Méret").pack()
        self.page_frame_scale_slider = ctk.CTkSlider(slider_panel, from_=0.5, to=1.5, command=self._update_page_frame_properties)
        self.page_frame_scale_slider.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(slider_panel, text="Vízszintes eltolás").pack()
        self.page_frame_offset_x_slider = ctk.CTkSlider(slider_panel, from_=-200, to=200, number_of_steps=400, command=self._update_page_frame_properties)
        self.page_frame_offset_x_slider.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(slider_panel, text="Függőleges eltolás").pack()
        self.page_frame_offset_y_slider = ctk.CTkSlider(slider_panel, from_=-200, to=200, number_of_steps=400, command=self._update_page_frame_properties)
        self.page_frame_offset_y_slider.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkButton(main_scroll_frame, text="Keret eltávolítása", fg_color="#D32F2F", hover_color="#B71C1C", command=lambda: self._apply_page_frame(None)).pack(pady=10, padx=5, fill="x")
        
        self.update_page_frame_editor_ui()

    def _apply_page_frame(self, path):
        """Alkalmazza a kiválasztott keretet az oldalra és alaphelyzetbe állítja a beállításokat."""
        current_page_data = self.pages[self.current_page]
        if path:
            current_page_data['page_frame_path'] = path
            # Új keret választásakor alaphelyzetbe állítjuk a csúszkákat
            current_page_data['page_frame_thickness'] = 0.05
            current_page_data['page_frame_scale'] = 1.0
            current_page_data['page_frame_offset_x'] = 0
            current_page_data['page_frame_offset_y'] = 0
        else:
            # Törléskor eltávolítjuk az összes kapcsolódó kulcsot
            for key in ['page_frame_path', 'page_frame_thickness', 'page_frame_scale', 'page_frame_offset_x', 'page_frame_offset_y']:
                current_page_data.pop(key, None)

        self.update_page_frame_editor_ui()
        self.refresh_editor_view()

    def _update_page_frame_properties(self, value=None):
        """Frissíti az oldalkeretet tulajdonságait a csúszkák alapján."""
        if not (self.page_frame_editor_window and self.page_frame_editor_window.winfo_exists()):
            return
        
        current_page_data = self.pages[self.current_page]
        current_page_data['page_frame_thickness'] = self.page_frame_thickness_slider.get()
        current_page_data['page_frame_scale'] = self.page_frame_scale_slider.get()
        current_page_data['page_frame_offset_x'] = int(self.page_frame_offset_x_slider.get())
        current_page_data['page_frame_offset_y'] = int(self.page_frame_offset_y_slider.get())
        
        self.refresh_editor_view()
    
    def update_page_frame_editor_ui(self):
        """Frissíti az oldalkeretet szerkesztő ablak vezérlőinek állapotát."""
        if not (self.page_frame_editor_window and self.page_frame_editor_window.winfo_exists()):
            return

        current_page_data = self.pages[self.current_page]
        props = current_page_data
        
        sliders = [self.page_frame_scale_slider, self.page_frame_offset_x_slider, self.page_frame_offset_y_slider, self.page_frame_thickness_slider]
        
        if props.get('page_frame_path'):
            for slider in sliders:
                slider.configure(state="normal")
            
            self.page_frame_scale_slider.set(props.get('page_frame_scale', 1.0))
            self.page_frame_offset_x_slider.set(props.get('page_frame_offset_x', 0))
            self.page_frame_offset_y_slider.set(props.get('page_frame_offset_y', 0))
            self.page_frame_thickness_slider.set(props.get('page_frame_thickness', 0.05))

            if not props.get('page_frame_path', '').startswith('preset_'):
                self.page_frame_thickness_slider.configure(state="disabled")
        else:
            for slider in sliders:
                slider.configure(state="disabled")
            self.page_frame_scale_slider.set(1.0)
            self.page_frame_offset_x_slider.set(0)
            self.page_frame_offset_y_slider.set(0)
            self.page_frame_thickness_slider.set(0.05)


    def _render_page_frame(self):
        """Kirajzolja az oldalkeretet a vászonra, figyelembe véve a méretezési és eltolási beállításokat."""
        offset_x, offset_y, draw_w, draw_h = self._get_page_draw_area()
        if draw_w <= 1 or draw_h <= 1: return

        current_page_data = self.pages[self.current_page]
        page_frame_path = current_page_data.get('page_frame_path')
        
        if self.canvas_page_frame_item:
            self.canvas.delete(self.canvas_page_frame_item)
            self.canvas_page_frame_item = None
            self.page_frame_photo_image = None

        if page_frame_path:
            frame_img = None
            if page_frame_path.startswith('preset_'):
                thickness_ratio = current_page_data.get('page_frame_thickness', 0.05)
                frame_img = self._create_preset_frame(page_frame_path, (draw_w, draw_h), thickness_ratio)
            elif os.path.exists(page_frame_path):
                frame_img = Image.open(page_frame_path).convert("RGBA")
            
            if frame_img:
                # ÚJ RÉSZ: Méretezés és eltolás alkalmazása
                f_scale = current_page_data.get('page_frame_scale', 1.0)
                f_off_x = current_page_data.get('page_frame_offset_x', 0)
                f_off_y = current_page_data.get('page_frame_offset_y', 0)

                # Az új keret méretei a skálázás alapján
                new_fw = int(draw_w * f_scale)
                new_fh = int(draw_h * f_scale)
                
                # A keret átméretezése
                resized_frame = frame_img.resize((new_fw, new_fh), Image.LANCZOS)
                
                # A beillesztés pozíciójának kiszámítása a középpontból és az eltolásból
                paste_x = (draw_w - new_fw) // 2 + f_off_x
                paste_y = (draw_h - new_fh) // 2 + f_off_y
                
                # Létrehozunk egy üres, átlátszó réteget, amire a keretet helyezzük,
                # hogy a vászonra egyetlen képként kerüljön ki.
                final_frame_layer = Image.new('RGBA', (draw_w, draw_h), (0, 0, 0, 0))
                final_frame_layer.paste(resized_frame, (paste_x, paste_y), resized_frame)
                
                self.page_frame_photo_image = ImageTk.PhotoImage(final_frame_layer)
                self.canvas_page_frame_item = self.canvas.create_image(
                    offset_x, offset_y, 
                    image=self.page_frame_photo_image, 
                    anchor="nw", 
                    tags="page_frame"
                )
    
    def _upload_custom_frame_path(self):
        return filedialog.askopenfilename(title="Válassz egy keret képet", filetypes=[("Képfájlok", "*.jpg *.jpeg *.png *.bmp"), ("Minden fájl", "*.*")]) or None
    
    def select_page(self, page_idx):
        if 0 <= page_idx < len(self.pages):
            self.current_page = page_idx
            self.refresh_editor_view()

    def add_new_page(self):
        # Az új oldal mérete legyen ugyanaz, mint az előzőé
        previous_page_size = self.pages[-1].get('size', self.DEFAULT_BOOK_SIZE_PIXELS) if self.pages else self.DEFAULT_BOOK_SIZE_PIXELS
        self.pages.append({'photos': [], 'texts': [], 'size': previous_page_size})
        self.current_page = len(self.pages) - 1
        
    def add_new_page_and_refresh(self):
        """Létrehoz egy új oldalt, amely az utolsó oldal elrendezését és méretét másolja, 
        majd frissíti a nézetet. Nem nyitja meg újra az elrendezés-választót."""
        if not self.pages:
            # Ez a helyzet nem fordulhat elő a szerkesztőben, de biztonsági tartalékként
            # visszairányít a főmenübe, ha valahogy mégis megtörténne.
            self.create_main_menu()
            messagebox.showinfo("Információ", "Először hozzon létre egy projektet.")
            return

        # Vesszük az utolsó oldal adatait mintaként
        last_page_data = self.pages[-1]
        layout_count_to_copy = len(last_page_data.get('photos', []))
        page_size_to_copy = last_page_data.get('size', self.DEFAULT_BOOK_SIZE_PIXELS)
        
        # Ha az előző oldal véletlenül üres volt, alapértelmezetten 1 képes elrendezést kap
        if layout_count_to_copy == 0:
            layout_count_to_copy = 1
            
        # Generáljuk az új oldal fotóinak sablonját
        new_photos_layout = self._generate_layout_template(layout_count_to_copy)
        
        # Létrehozzuk az új oldalt a másolt adatokkal
        new_page = {
            'photos': new_photos_layout,
            'texts': [],
            'size': page_size_to_copy
        }
        self.pages.append(new_page)
        
        # Az új, üres oldalra ugrunk és frissítjük a szerkesztőfelületet
        self.current_page = len(self.pages) - 1
        self.refresh_editor_view()
    def delete_page(self):
        if len(self.pages) > 1:
            if messagebox.askyesno("Oldal törlése", f"Biztosan törölni szeretnéd a(z) {self.current_page + 1}. oldalt?"):
                self._deselect_all()
                del self.pages[self.current_page]
                if self.current_page >= len(self.pages): self.current_page = len(self.pages) - 1
                self.refresh_editor_view()
        else: messagebox.showwarning("Utolsó oldal", "Nem törölheted az utolsó oldalt!")
    
    def change_current_page_layout(self):
        self.show_page_selection(is_new_project=False)

    def change_page_size(self):
        """Felugró ablakot nyit az aktuális oldal méretének módosítására, egyéni méret opcióval."""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Oldalméret módosítása")
        dialog.geometry("350x180")
        dialog.transient(self.root)
        dialog.grab_set()

        # --- Belső segédfüggvény az egyéni méret ablakhoz ---
        def prompt_and_apply_custom_size():
            """
            Kezeli az új, egyéni méret bekérését és alkalmazását.
            """
            dialog.withdraw() # Az eredeti dialógus elrejtése

            custom_dialog = ctk.CTkToplevel(self.root)
            custom_dialog.title("Egyéni méret megadása")
            custom_dialog.geometry("300x200")
            custom_dialog.transient(self.root)
            custom_dialog.grab_set()

            ctk.CTkLabel(custom_dialog, text="Add meg a méreteket pixelben (300 DPI):", font=ctk.CTkFont(size=12)).pack(pady=(10, 5))

            width_frame = ctk.CTkFrame(custom_dialog, fg_color="transparent")
            width_frame.pack(pady=5, padx=20, fill="x")
            ctk.CTkLabel(width_frame, text="Szélesség (px):", width=100).pack(side="left")
            width_entry = ctk.CTkEntry(width_frame)
            width_entry.pack(side="left", expand=True, fill="x")

            height_frame = ctk.CTkFrame(custom_dialog, fg_color="transparent")
            height_frame.pack(pady=5, padx=20, fill="x")
            ctk.CTkLabel(height_frame, text="Magasság (px):", width=100).pack(side="left")
            height_entry = ctk.CTkEntry(height_frame)
            height_entry.pack(side="left", expand=True, fill="x")

            def apply_custom_size():
                try:
                    width = int(width_entry.get())
                    height = int(height_entry.get())
                    if width <= 0 or height <= 0:
                        raise ValueError("A méreteknek pozitívnak kell lenniük.")

                    custom_key = f"Egyéni ({width}x{height}px)"
                    custom_value = (width, height)
                    
                    if custom_key not in self.BOOK_SIZES:
                        self.BOOK_SIZES[custom_key] = custom_value
                    
                    self.pages[self.current_page]['size'] = custom_value
                    
                    custom_dialog.destroy()
                    dialog.destroy()
                    self.refresh_editor_view()

                except ValueError as e:
                    messagebox.showerror("Hiba", f"Érvénytelen érték!\nKérlek, pozitív egész számokat adj meg.\n({e})", parent=custom_dialog)

            def on_custom_close():
                dialog.deiconify()
                custom_dialog.destroy()

            custom_dialog.protocol("WM_DELETE_WINDOW", on_custom_close)
            ctk.CTkButton(custom_dialog, text="Alkalmaz", command=apply_custom_size).pack(pady=20)

        # --- A fő dialógus felépítése ---
        ctk.CTkLabel(dialog, text=f"Új méret a(z) {self.current_page + 1}. oldalhoz:", font=ctk.CTkFont(size=14)).pack(pady=10)

        size_var = ctk.StringVar()
        current_size_pixels = self.pages[self.current_page].get('size', self.DEFAULT_BOOK_SIZE_PIXELS)
        current_size_name = next((name for name, size in self.BOOK_SIZES.items() if size == current_size_pixels), self.DEFAULT_BOOK_SIZE_NAME)
        size_var.set(current_size_name)

        options = list(self.BOOK_SIZES.keys())
        if "Egyéni méret..." in options:
            options.remove("Egyéni méret...")
        options.append("Egyéni méret...")

        def handle_menu_selection(choice):
            if choice == "Egyéni méret...":
                prompt_and_apply_custom_size()

        menu = ctk.CTkOptionMenu(dialog, variable=size_var, values=options, command=handle_menu_selection)
        menu.pack(pady=5, padx=20, fill="x")

        def apply_preset_size():
            chosen_name = size_var.get()
            if chosen_name == "Egyéni méret...":
                return 
            
            self.pages[self.current_page]['size'] = self.BOOK_SIZES[chosen_name]
            dialog.destroy()
            self.refresh_editor_view()

        ctk.CTkButton(dialog, text="Kiválasztott alkalmazása", command=apply_preset_size).pack(pady=20, padx=20)


    def save_project(self):
        if not self.pages:
            messagebox.showerror("Hiba", "Nincs mit menteni. Hozz létre legalább egy oldalt!")
            return
        filepath = filedialog.asksaveasfilename(title="Projekt mentése másként", defaultextension=".lolaba", filetypes=[("LoLaBa Fotókönyv Projekt", "*.lolaba"), ("Minden fájl", "*.*")])
        if not filepath: return
        
        pages_to_save = copy.deepcopy(self.pages)
        for page in pages_to_save:
            bg = page.get('background')
            if isinstance(bg, dict) and 'image_obj' in bg:
                del bg['image_obj']

        project_data = {
            "version": 1.1, # Verziószám a jövőbeli kompatibilitáshoz
            "pages": pages_to_save, 
            "photo_properties": self.photo_properties,
            "z_order": self.z_order
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("Mentés sikeres", f"A projekt sikeresen elmentve ide:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Mentési hiba", f"Hiba történt a projekt mentése során:\n{e}")

    def load_project(self):
        filepath = filedialog.askopenfilename(title="Projekt megnyitása", filetypes=[("LoLaBa Fotókönyv Projekt", "*.lolaba"), ("Minden fájl", "*.*")])
        if not filepath: return
        
        self._show_working_indicator() # Nincs többé üzenet
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                project_data = json.load(f)
            
            self._reset_project_state()
            self.pages = project_data.get("pages", [])
            
            for page in self.pages:
                if 'size' not in page:
                    page['size'] = self.DEFAULT_BOOK_SIZE_PIXELS

            self.photo_properties = project_data.get("photo_properties", {})
            self.z_order = project_data.get("z_order", {})
            self.current_page = 0
            
            if not self.pages:
                messagebox.showwarning("Betöltési hiba", "A projektfájl üres vagy sérült.")
                self.create_main_menu()
                return
            
            if not self.editor_ui_built:
                self._build_editor_ui()
                self.editor_ui_built = True
            self.refresh_editor_view()
            messagebox.showinfo("Betöltés sikeres", "A projekt sikeresen betöltve.")

        except Exception as e:
            messagebox.showerror("Betöltési hiba", f"Hiba történt a projekt betöltése során:\n{e}")
            self._reset_project_state()
            self.create_main_menu()
        finally:
            self._hide_working_indicator()

    def export_project(self):
        if not self.pages:
            messagebox.showerror("Hiba", "Nincs mit exportálni. Hozz létre legalább egy oldalt!")
            return
        export_window = ctk.CTkToplevel(self.root)
        export_window.title("Exportálás"); export_window.geometry("300x200")
        export_window.transient(self.root); export_window.grab_set()
        ctk.CTkLabel(export_window, text="Válassz exportálási formátumot:", font=ctk.CTkFont(size=16)).pack(pady=20)
        btn_style = {'height': 40, 'width': 200}
        ctk.CTkButton(export_window, text="Exportálás Képként", command=lambda: [export_window.destroy(), self._export_as_images()], **btn_style).pack(pady=10)
        ctk.CTkButton(export_window, text="Exportálás PDF-ként", command=lambda: [export_window.destroy(), self._export_as_pdf()], **btn_style).pack(pady=10)

    def _export_as_images(self):
        filepath = filedialog.asksaveasfilename(
            title="Képek mentése másként",
            defaultextension=".png",
            filetypes=[("PNG képfájl", "*.png"), ("JPEG képfájl", "*.jpg")]
        )
        if not filepath:
            return

        self._show_working_indicator()
        try:
            directory = os.path.dirname(filepath)
            base_name, extension = os.path.splitext(os.path.basename(filepath))
            save_format = "JPEG" if extension.lower() in ['.jpg', '.jpeg'] else "PNG"
            num_pages = len(self.pages)
            
            for i in range(num_pages):
                page_image = self._render_page_to_image(i)
                if page_image:
                    if num_pages > 1:
                        current_filename = f"{base_name}_{i+1}{extension}"
                        final_path = os.path.join(directory, current_filename)
                    else:
                        final_path = filepath
                    page_image.save(final_path, save_format)
            
            messagebox.showinfo("Exportálás sikeres", f"Az oldalak sikeresen exportálva a következő mappába:\n{directory}")
        
        except Exception as e:
            messagebox.showerror("Exportálási hiba", f"Hiba történt a képek exportálása során:\n{e}")
        finally:
            self._hide_working_indicator()

    def _export_as_pdf(self):
        filepath = filedialog.asksaveasfilename(title="PDF mentése másként", defaultextension=".pdf", filetypes=[("PDF Dokumentum", "*.pdf")])
        if not filepath: return
        
        self._show_working_indicator()
        try:
            rendered_images = []
            for i in range(len(self.pages)):
                page_image = self._render_page_to_image(i)
                if page_image:
                    rendered_images.append(page_image)
            
            if not rendered_images:
                messagebox.showerror("Hiba", "Nem sikerült egyetlen oldalt sem renderelni.")
                return

            if len(rendered_images) > 1:
                rendered_images[0].save(
                    filepath, "PDF", resolution=300.0, save_all=True, append_images=rendered_images[1:]
                )
            elif rendered_images:
                rendered_images[0].save(filepath, "PDF", resolution=300.0)

            messagebox.showinfo("Exportálás sikeres", f"A PDF sikeresen létrehozva:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Exportálási hiba", f"Hiba történt a PDF létrehozása során:\n{e}\n{traceback.format_exc()}")
        finally:
            self._hide_working_indicator()

    
    
    def _render_page_to_image(self, page_index):
        if page_index >= len(self.pages): return None

        page_data = self.pages[page_index]
        W, H = page_data.get('size', self.DEFAULT_BOOK_SIZE_PIXELS)
        
        REFERENCE_EDITOR_HEIGHT = 600.0 
        height_scale_factor = H / REFERENCE_EDITOR_HEIGHT

        bg_setting = page_data.get('background')
        if isinstance(bg_setting, dict) and bg_setting.get('type') == 'image' and os.path.exists(bg_setting.get('path')):
            bg_img = Image.open(bg_setting['path']).convert("RGBA")
            page_image = bg_img.resize((W,H), Image.LANCZOS)
        else:
            bg_color = bg_setting if isinstance(bg_setting, str) and bg_setting.startswith('#') else self.colors['card_bg']
            page_image = Image.new('RGBA', (W, H), bg_color)
        
        draw = ImageDraw.Draw(page_image)
        
        photos_data = page_data.get('photos', [])
        page_key = str(page_index)
        ordered_indices = self.z_order.get(page_key, list(range(len(photos_data))))

        for photo_idx in ordered_indices:
            if photo_idx >= len(photos_data): continue
            photo_data = photos_data[photo_idx]
            photo_path = photo_data.get('path')
            if not photo_path or not os.path.exists(photo_path): continue
            
            try:
                key = str((page_index, photo_idx))
                props = self.photo_properties.get(key, {})
                fit_mode = props.get('fit_mode', 'fill')

                # Az eredeti, elrendezésből származó méretek használata
                master_rel_w = photo_data.get('layout_relwidth', photo_data['relwidth'])
                master_rel_h = photo_data.get('layout_relheight', photo_data['relheight'])
                frame_w, frame_h = int(master_rel_w * W), int(master_rel_h * H)

                # Ha 'fit' módban van, exportáláskor is átméretezzük a keretet
                if fit_mode == 'fit':
                    with Image.open(photo_path) as temp_img:
                        img_ratio = temp_img.width / temp_img.height
                        frame_ratio = frame_w / frame_h if frame_h > 0 else 1
                        if img_ratio > frame_ratio: frame_h = int(frame_w / img_ratio)
                        else: frame_w = int(frame_h * img_ratio)

                frame_x, frame_y = int(photo_data['relx'] * W), int(photo_data['rely'] * H)

                # Kép feldolgozása (ugyanaz a logika, mint a megjelenítésnél)
                original_img = Image.open(photo_path).convert("RGBA")
                if props.get('grayscale', False): original_img = original_img.convert('L').convert('RGBA')
                enhancer = ImageEnhance.Brightness(original_img); original_img = enhancer.enhance(props.get('brightness', 1.0))
                enhancer = ImageEnhance.Contrast(original_img); original_img = enhancer.enhance(props.get('contrast', 1.0))
                enhancer = ImageEnhance.Color(original_img); original_img = enhancer.enhance(props.get('saturation', 1.0))

                zoom, pan_x, pan_y = props.get('zoom', 1.0), props.get('pan_x', 0.5), props.get('pan_y', 0.5)

                if fit_mode == 'fill':
                    img_ratio = original_img.width / original_img.height; frame_ratio = frame_w / frame_h if frame_h > 0 else 1
                    if img_ratio > frame_ratio: new_h, new_w = int(frame_h * zoom), int(frame_h * zoom * img_ratio)
                    else: new_w, new_h = int(frame_w * zoom), int(frame_w * zoom / img_ratio)
                    if new_w < frame_w: new_w, new_h = frame_w, int(frame_w / img_ratio)
                    if new_h < frame_h: new_h, new_w = frame_h, int(frame_h * img_ratio)
                    zoomed_img = original_img.resize((new_w, new_h), Image.LANCZOS)
                    extra_w, extra_h = max(0, new_w - frame_w), max(0, new_h - frame_h)
                    crop_x, crop_y = int(extra_w * pan_x), int(extra_h * pan_y)
                    final_photo = zoomed_img.crop((crop_x, crop_y, crop_x + frame_w, crop_y + frame_h))
                else:
                    fit_w, fit_h = frame_w, frame_h
                    new_w, new_h = int(fit_w * zoom), int(fit_h * zoom)
                    if new_w < 1 or new_h < 1: new_w, new_h = 1, 1
                    resized_img = original_img.resize((new_w, new_h), Image.LANCZOS)
                    final_photo = Image.new('RGBA', (frame_w, frame_h), (0, 0, 0, 0))
                    extra_w, extra_h = max(0, new_w - frame_w), max(0, new_h - frame_h)
                    paste_x = (frame_w - new_w) // 2 - int(extra_w * (pan_x - 0.5))
                    paste_y = (frame_h - new_h) // 2 - int(extra_h * (pan_y - 0.5))
                    final_photo.paste(resized_img, (paste_x, paste_y), resized_img)

                # ... (a keret és a beillesztés logika változatlan) ...
                photo_frame_path = props.get('frame_path')
                if photo_frame_path:
                    thickness_ratio_photo = props.get('frame_thickness', 0.05)
                    photo_frame_img = None
                    if photo_frame_path.startswith('preset_'): photo_frame_img = self._create_preset_frame(photo_frame_path, (frame_w, frame_h), thickness_ratio_photo)
                    elif os.path.exists(photo_frame_path): photo_frame_img = Image.open(photo_frame_path).convert("RGBA")
                    if photo_frame_img:
                        f_scale = props.get('frame_scale', 1.0); f_off_x = props.get('frame_offset_x', 0); f_off_y = props.get('frame_offset_y', 0)
                        new_fw, new_fh = int(frame_w * f_scale), int(frame_h * f_scale)
                        resized_frame = photo_frame_img.resize((new_fw, new_fh), Image.LANCZOS)
                        paste_x, paste_y = (frame_w - new_fw) // 2 + f_off_x, (frame_h - new_fh) // 2 + f_off_y
                        final_photo.paste(resized_frame, (paste_x, paste_y), resized_frame)
                
                page_image.paste(final_photo, (frame_x, frame_y), final_photo)

            except Exception as e:
                print(f"HIBA a(z) {page_index}. oldal, {photo_idx}. kép renderelésekor: {e}")
                draw.rectangle([frame_x, frame_y, frame_x + frame_w, frame_y + frame_h], outline="red", width=5)
                draw.text((frame_x + 10, frame_y + 10), "Kép hiba", fill="red")
        
        # ... (az oldalkeretet és szöveget renderelő részek változatlanok) ...
        page_frame_path = page_data.get('page_frame_path')
        if page_frame_path:
            frame_img = None
            if page_frame_path.startswith('preset_'):
                thickness_ratio = page_data.get('page_frame_thickness', 0.05)
                frame_img = self._create_preset_frame(page_frame_path, (W, H), thickness_ratio)
            elif os.path.exists(page_frame_path):
                frame_img = Image.open(page_frame_path).convert("RGBA")
            
            if frame_img:
                f_scale = page_data.get('page_frame_scale', 1.0)
                f_off_x = page_data.get('page_frame_offset_x', 0)
                f_off_y = page_data.get('page_frame_offset_y', 0)
                new_fw = int(W * f_scale); new_fh = int(H * f_scale)
                if new_fw > 0 and new_fh > 0:
                    resized_frame = frame_img.resize((new_fw, new_fh), Image.LANCZOS)
                    paste_x = (W - new_fw) // 2 + f_off_x
                    paste_y = (H - new_fh) // 2 + f_off_y
                    page_image.paste(resized_frame, (paste_x, paste_y), resized_frame)
                    
        for text_data in page_data.get('texts', []):
            try:
                font_family = text_data.get('font_family', 'Arial')
                font_style = text_data.get('font_style', 'normal')
                font_color = text_data.get('font_color', '#000000')
                
                original_font_size = text_data.get('font_size', 24)
                scaled_font_size = int(original_font_size * height_scale_factor)
                
                font_variant = ""
                if 'bold' in font_style and 'italic' in font_style: font_variant = "bi"
                elif 'bold' in font_style: font_variant = "bd"
                elif 'italic' in font_style: font_variant = "i"
                font_name_base = font_family.lower().replace(' ', '')
                
                font_filenames_to_try = [f"{font_name_base}{font_variant}.ttf", f"{font_family}.ttf"]
                if font_family == "Times New Roman": font_filenames_to_try.append("times.ttf")
                if font_family == "Courier New": font_filenames_to_try.append("cour.ttf")

                font = None
                for name in font_filenames_to_try:
                    try:
                        font = ImageFont.truetype(name, size=scaled_font_size)
                        break 
                    except IOError:
                        continue 
                
                if font is None:
                    print(f"Figyelmeztetés: '{font_family}' betűtípus nem található, alapértelmezett betűtípus lesz használva.")
                    font = ImageFont.load_default(size=scaled_font_size)

                text_x, text_y = int(text_data['relx'] * W), int(text_data['rely'] * H)
                draw.text((text_x, text_y), text_data['text'], fill=font_color, font=font, anchor="mm")
            
            except Exception as e:
                print(f"HIBA a szöveg renderelésekor: {e}")
                traceback.print_exc()

        return page_image.convert("RGB")
    # --- SZÖVEGSZERKESZTŐ METÓDUSOK ---
    def add_text(self):
        if self.text_editor_window is not None and self.text_editor_window.winfo_exists():
            self.text_editor_window.focus(); return
        self._create_text_editor_window()

    def _create_text_editor_window(self):
        self.text_editor_window = ctk.CTkToplevel(self.root)
        self.text_editor_window.title("Szöveg Eszköztár"); self.text_editor_window.geometry("350x550")
        self.text_editor_window.transient(self.root)
        button_frame = ctk.CTkFrame(self.text_editor_window, fg_color="transparent")
        button_frame.pack(pady=10, padx=10, fill="x")
        ctk.CTkButton(button_frame, text="Új szövegdoboz", command=self._add_new_textbox).pack(side="left", expand=True, padx=5)
        self.delete_text_button = ctk.CTkButton(button_frame, text="Kijelölt törlése", fg_color="#D32F2F", hover_color="#B71C1C", command=self._delete_selected_text)
        self.delete_text_button.pack(side="left", expand=True, padx=5)
        self.text_editor_panel = ctk.CTkFrame(self.text_editor_window)
        self.text_editor_panel.pack(pady=10, padx=10, fill="both", expand=True)
        ctk.CTkLabel(self.text_editor_panel, text="Szöveg tartalma:").pack(anchor="w", padx=10)
        self.text_input = ctk.CTkTextbox(self.text_editor_panel, height=100)
        self.text_input.pack(fill="x", padx=10, pady=5)
        self.text_input.bind("<KeyRelease>", self._update_text_properties) 
        ctk.CTkLabel(self.text_editor_panel, text="Betűtípus:").pack(anchor="w", padx=10, pady=(10,0))
        self.font_family_var = ctk.StringVar(value="Arial")
        self.font_family_menu = ctk.CTkOptionMenu(self.text_editor_panel, variable=self.font_family_var, values=["Arial", "Times New Roman", "Courier New", "Verdana", "Impact"], command=self._update_text_properties)
        self.font_family_menu.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(self.text_editor_panel, text="Betűméret:").pack(anchor="w", padx=10, pady=(10,0))
        self.font_size_slider = ctk.CTkSlider(self.text_editor_panel, from_=10, to=100, number_of_steps=90, command=self._update_text_properties)
        self.font_size_slider.pack(fill="x", padx=10, pady=5)
        style_frame = ctk.CTkFrame(self.text_editor_panel, fg_color="transparent")
        style_frame.pack(fill="x", padx=10, pady=5)
        self.font_bold_var = ctk.StringVar(value="off")
        self.font_italic_var = ctk.StringVar(value="off")
        self.font_bold_checkbox = ctk.CTkCheckBox(style_frame, text="Félkövér", variable=self.font_bold_var, onvalue="on", offvalue="off", command=self._update_text_properties)
        self.font_bold_checkbox.pack(side="left", padx=5)
        self.font_italic_checkbox = ctk.CTkCheckBox(style_frame, text="Dőlt", variable=self.font_italic_var, onvalue="on", offvalue="off", command=self._update_text_properties)
        self.font_italic_checkbox.pack(side="left", padx=5)
        self.text_color_button = ctk.CTkButton(self.text_editor_panel, text="Szín választása", command=self._choose_text_color)
        self.text_color_button.pack(pady=10)
        self.show_bg_var = ctk.StringVar(value="off")
        self.show_bg_checkbox = ctk.CTkCheckBox(self.text_editor_panel, text="Kijelölés háttere", variable=self.show_bg_var, onvalue="on", offvalue="off", command=self._update_text_properties)
        self.show_bg_checkbox.pack(pady=10, padx=10, anchor="w")
        self.update_text_editor_ui()

    def _add_new_textbox(self):
        new_text = {"text": "Új szöveg", "relx": 0.5, "rely": 0.5, "font_family": "Arial", "font_size": 24, "font_style": "normal", "font_color": "#000000", "show_bg_on_select": False}
        if 'texts' not in self.pages[self.current_page]: self.pages[self.current_page]['texts'] = []
        self.pages[self.current_page]['texts'].append(new_text)
        self.refresh_editor_view()
        self._select_text(len(self.pages[self.current_page]['texts']) - 1)

    def _delete_selected_text(self):
        if self.selected_text_index is not None:
            text_index_to_delete = self.selected_text_index
            self._deselect_all()
            del self.pages[self.current_page]['texts'][text_index_to_delete]
            self.refresh_editor_view()
            self.update_text_editor_ui()
    
    def _render_text_boxes(self):
        if 'texts' not in self.pages[self.current_page]: return
        offset_x, offset_y, draw_w, draw_h = self._get_page_draw_area()
        if draw_w <= 1 or draw_h <= 1: return
        
        for i, text_data in enumerate(self.pages[self.current_page]['texts']):
            style_string = text_data.get('font_style', 'normal')
            font_obj = ctk.CTkFont(family=text_data.get('font_family', 'Arial'), size=text_data.get('font_size', 12), weight="bold" if "bold" in style_string else "normal", slant="italic" if "italic" in style_string else "roman")
            container = ctk.CTkFrame(self.canvas, fg_color="transparent")
            label = ctk.CTkLabel(container, text=text_data['text'], font=font_obj, text_color=text_data.get('font_color', '#000000'), fg_color="transparent")
            label.pack(padx=2, pady=2)
            
            abs_x = offset_x + int(text_data['relx'] * draw_w)
            abs_y = offset_y + int(text_data['rely'] * draw_h)

            canvas_item_id = self.canvas.create_window(abs_x, abs_y, window=container, anchor="center", tags="text")
            self.widget_to_canvas_item[container] = canvas_item_id
            
            container.bind("<ButtonPress-1>", lambda e, index=i: self._on_widget_press(e, 'text', index))
            container.bind("<B1-Motion>", lambda e: self._on_widget_drag(e))
            container.bind("<ButtonRelease-1>", lambda e: self._on_widget_release(e))
            label.bind("<ButtonPress-1>", lambda e, index=i: self._on_widget_press(e, 'text', index))
            label.bind("<B1-Motion>", lambda e: self._on_widget_drag(e))
            label.bind("<ButtonRelease-1>", lambda e: self._on_widget_release(e))
            self.text_widgets.append(container)

    def _update_selected_text_widget(self):
        if self.selected_text_index is None: return

        try:
            text_data = self.pages[self.current_page]['texts'][self.selected_text_index]
            text_widget_container = self.text_widgets[self.selected_text_index]
            text_label = text_widget_container.winfo_children()[0]

            font_obj = ctk.CTkFont(
                family=text_data.get('font_family', 'Arial'),
                size=text_data.get('font_size', 12),
                weight="bold" if "bold" in text_data.get('font_style', 'normal') else "normal",
                slant="italic" if "italic" in text_data.get('font_style', 'normal') else "roman"
            )
            
            text_label.configure(text=text_data['text'], font=font_obj)
        except (IndexError, AttributeError) as e:
            print(f"Hiba a szöveg widget frissítésekor: {e}")

    def _update_text_properties(self, event=None):
        if self.selected_text_index is None: return
        
        try:
            text_data = self.pages[self.current_page]['texts'][self.selected_text_index]
            text_data['text'] = self.text_input.get("1.0", "end-1c")
            text_data['font_family'] = self.font_family_var.get()
            text_data['font_size'] = int(self.font_size_slider.get())
            style = []
            if self.font_bold_var.get() == "on": style.append("bold")
            if self.font_italic_var.get() == "on": style.append("italic")
            text_data['font_style'] = " ".join(style) if style else "normal"
            text_data['show_bg_on_select'] = self.show_bg_var.get() == "on"

            self._update_selected_text_widget()

        except (AttributeError, IndexError, ValueError) as e:
            print(f"Hiba a szöveg tulajdonságainak frissítésekor: {e}")

    def update_text_editor_ui(self):
        if not (self.text_editor_window and self.text_editor_window.winfo_exists()): return
        is_text_selected = self.selected_text_index is not None
        widgets_to_toggle = [self.text_input, self.font_family_menu, self.font_size_slider, self.font_bold_checkbox, self.font_italic_checkbox, self.text_color_button, self.delete_text_button, self.show_bg_checkbox]
        for widget in widgets_to_toggle:
            widget.configure(state="normal" if is_text_selected else "disabled")
        
        if is_text_selected:
            text_data = self.pages[self.current_page]['texts'][self.selected_text_index]
            self.text_input.delete("1.0", "end"); self.text_input.insert("1.0", text_data['text'])
            self.font_family_var.set(text_data.get('font_family', 'Arial'))
            self.font_size_slider.set(text_data.get('font_size', 12))
            self.font_bold_var.set("on" if "bold" in text_data.get('font_style', '') else "off")
            self.font_italic_var.set("on" if "italic" in text_data.get('font_style', '') else "off")
            self.show_bg_var.set("on" if text_data.get('show_bg_on_select', True) else "off")
        else: self.text_input.delete("1.0", "end")
            
    def _choose_text_color(self):
        if self.selected_text_index is None: return
        current_color = self.pages[self.current_page]['texts'][self.selected_text_index].get('font_color', '#000000')
        color_code = colorchooser.askcolor(title="Válassz színt", initialcolor=current_color)
        if color_code and color_code[1]:
            self.pages[self.current_page]['texts'][self.selected_text_index]['font_color'] = color_code[1]

    # --- MOZGATÁS METÓDUSAI ---
    def _on_widget_press(self, event, item_type, index):
        widget_to_drag = None
        if item_type == 'photo':
            if index < len(self.photo_frames):
                self._select_photo(index)
                widget_to_drag = self.photo_frames[index]
            else: return
        elif item_type == 'text':
            if index < len(self.text_widgets):
                self._select_text(index)
                widget_to_drag = self.text_widgets[index]
            else: return
        else: return
        
        canvas_item_id = self.widget_to_canvas_item.get(widget_to_drag)
        if canvas_item_id:
            self.canvas.tag_raise(canvas_item_id)
            # Elmentjük a kezdő pozíciót is
            x, y = self.canvas.coords(canvas_item_id)
            self._drag_data = {
                "widget": widget_to_drag, 
                "item_id": canvas_item_id, 
                "item_type": item_type, 
                "index": index, 
                "offset_x": event.x_root, 
                "offset_y": event.y_root,
                "start_pos": (x, y) # ÚJ: Kezdő pozíció elmentése
            }

    def _on_widget_drag(self, event):
        if not self._drag_data: return
        
        item_id = self._drag_data["item_id"]
        
        dx = event.x_root - self._drag_data["offset_x"]
        dy = event.y_root - self._drag_data["offset_y"]
        
        self.canvas.move(item_id, dx, dy)
        
        self._drag_data["offset_x"] = event.x_root
        self._drag_data["offset_y"] = event.y_root

    def _on_widget_release(self, event):
        if not self._drag_data: return
        
        dragged_index = self._drag_data["index"]
        dragged_type = self._drag_data["item_type"]
        dragged_id = self._drag_data["item_id"]
        
        # Csak fotók cseréjét kezeljük
        if dragged_type == 'photo':
            # Megkeressük az elemet az egér kurzor alatt
            x, y = event.x_root - self.canvas.winfo_rootx(), event.y_root - self.canvas.winfo_rooty()
            overlapping_items = self.canvas.find_overlapping(x, y, x, y)
            
            target_index = None
            for item_id in overlapping_items:
                # Keressük azt a widgetet, amihez az item_id tartozik
                for i, frame in enumerate(self.photo_frames):
                    if frame and self.widget_to_canvas_item.get(frame) == item_id:
                        if i != dragged_index: # Nem a saját magára dobta
                            target_index = i
                            break
                if target_index is not None:
                    break

            # --- KÉPCSERE LOGIKA ---
            if target_index is not None:
                # Megcseréljük a képek útvonalait és a tulajdonságokat
                photos = self.pages[self.current_page]['photos']
                photos[dragged_index]['path'], photos[target_index]['path'] = \
                    photos[target_index]['path'], photos[dragged_index]['path']

                # Tulajdonságok cseréje
                dragged_key = str((self.current_page, dragged_index))
                target_key = str((self.current_page, target_index))
                
                dragged_props = self.photo_properties.pop(dragged_key, {})
                target_props = self.photo_properties.pop(target_key, {})

                self.photo_properties[dragged_key] = target_props
                self.photo_properties[target_key] = dragged_props
                
                self.refresh_editor_view()
                self._drag_data = {}
                return # Befejeztük a cserét

        # --- EREDETI MOZGATÁS LOGIKA (ha nem történt csere) ---
        offset_x, offset_y, draw_w, draw_h = self._get_page_draw_area()
        if draw_w == 0 or draw_h == 0: 
            self._drag_data = {}
            return
            
        x, y = self.canvas.coords(dragged_id)

        if dragged_type == 'photo':
            data_list = self.pages[self.current_page]['photos']
            data_list[dragged_index]['relx'] = (x - offset_x) / draw_w
            data_list[dragged_index]['rely'] = (y - offset_y) / draw_h
        elif dragged_type == 'text':
            data_list = self.pages[self.current_page]['texts']
            data_list[dragged_index]['relx'] = (x - offset_x) / draw_w
            data_list[dragged_index]['rely'] = (y - offset_y) / draw_h
            
        self._drag_data = {}
    
    # --- VARÁZSLÓ FUNKCIÓK ---
    def run_basic_wizard(self):
        folder_path = filedialog.askdirectory(title="Mappa kiválasztása a Varázslóhoz")
        if not folder_path: return

        self._show_working_indicator()
        try:
            image_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            if not image_files:
                messagebox.showwarning("Varázsló", "A mappa nem tartalmaz képeket.")
                return

            self._reset_project_state()
            images_per_page = 4
            
            for i in range(0, len(image_files), images_per_page):
                page_images = image_files[i:i + images_per_page]
                
                if i == 0:
                    page_size = self.BOOK_SIZES.get(self.selected_book_size_name.get(), self.DEFAULT_BOOK_SIZE_PIXELS)
                    self.pages.append({'photos': [], 'texts': [], 'size': page_size})
                else:
                    self.add_new_page()
                
                self.pages[self.current_page]['photos'] = self._generate_layout_template(len(page_images))
                
                for idx, path in enumerate(page_images):
                    self.pages[self.current_page]['photos'][idx]['path'] = path
                    key = str((self.current_page, idx))
                    self.photo_properties[key] = {'frame_path': random.choice(['preset_black', 'preset_white'])}
                
                bg_colors = ['#F0F0F0', '#D3E3F1', '#D1F0D1', '#F5E6D3']
                self.pages[self.current_page]['background'] = random.choice(bg_colors)

            if not self.editor_ui_built: 
                self._build_editor_ui()
                self.editor_ui_built = True
            
            self.current_page = 0
            self.refresh_editor_view()
            messagebox.showinfo("Varázsló kész", f"{len(image_files)} kép elhelyezve {len(self.pages)} oldalon.")
        except Exception as e:
            messagebox.showerror("Varázsló Hiba", f"Hiba történt: {e}")
            traceback.print_exc()
        finally:
            self._hide_working_indicator()


    def _analyze_images_by_subfolder(self, parent_folder_path):
        """
        Bejárja a megadott mappát és annak összes almappáját,
        majd csoportosítva adja vissza a képeket.
        A visszatérési érték egy szótár, ahol a kulcsok az almappák útvonalai,
        az értékek pedig az adott mappában található képek elemzett listái.
        """
        image_groups = {}
        
        # A képek "természetes" sorrendbe rendezéséhez kell
        def natural_sort_key(s):
            filename = os.path.basename(s)
            return [int(text) if text.isdigit() else text.lower() for text in re.split(r'([0-9]+)', filename)]

        for dirpath, _, filenames in os.walk(parent_folder_path):
            analyzed_in_folder = []
            
            # Fájlok rendezése a természetes sorrend alapján
            sorted_filenames = sorted(filenames, key=natural_sort_key)

            for filename in sorted_filenames:
                if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    continue
                
                path = os.path.join(dirpath, filename)
                try:
                    with Image.open(path) as img:
                        w, h = img.size
                        ratio = w / h if h > 0 else 1
                        orientation = 'square'
                        if ratio > 1.1: orientation = 'landscape'
                        elif ratio < 0.9: orientation = 'portrait'
                        analyzed_in_folder.append({'path': path, 'orientation': orientation})
                except Exception as e:
                    print(f"Hiba a kép elemzésekor ({os.path.basename(path)}): {e}")
            
            # Csak akkor adjuk hozzá a csoporthoz, ha találtunk benne képet
            if analyzed_in_folder:
                image_groups[dirpath] = analyzed_in_folder
                
        return image_groups


    def _analyze_images(self, folder_path):
        def natural_sort_key(s):
            filename = os.path.basename(s)
            return [int(text) if text.isdigit() else text.lower() for text in re.split(r'([0-9]+)', filename)]

        analyzed = []
        image_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        image_files.sort(key=natural_sort_key)

        for path in image_files:
            try:
                with Image.open(path) as img:
                    w, h = img.size
                    ratio = w / h if h > 0 else 1
                    orientation = 'square'
                    if ratio > 1.1: orientation = 'landscape'
                    elif ratio < 0.9: orientation = 'portrait'
                    analyzed.append({'path': path, 'orientation': orientation})
            except Exception as e:
                print(f"Hiba a kép elemzésekor ({os.path.basename(path)}): {e}")
        return analyzed

    def _define_smart_layouts(self):
        layouts = {
            '1_landscape_4_square': { 'priority': 20, 'orientations': ['landscape', 'square', 'square', 'square', 'square'], 'geometry': [{'relx': 0.05, 'rely': 0.05, 'relwidth': 0.9, 'relheight': 0.55}, {'relx': 0.05, 'rely': 0.65, 'relwidth': 0.2, 'relheight': 0.3}, {'relx': 0.275, 'rely': 0.65, 'relwidth': 0.2, 'relheight': 0.3}, {'relx': 0.5, 'rely': 0.65, 'relwidth': 0.2, 'relheight': 0.3}, {'relx': 0.725, 'rely': 0.65, 'relwidth': 0.2, 'relheight': 0.3}] },
            '1_portrait_4_landscape': { 'priority': 19, 'orientations': ['portrait', 'landscape', 'landscape', 'landscape', 'landscape'], 'geometry': [{'relx': 0.05, 'rely': 0.05, 'relwidth': 0.4, 'relheight': 0.9}, {'relx': 0.5, 'rely': 0.05, 'relwidth': 0.45, 'relheight': 0.2}, {'relx': 0.5, 'rely': 0.275, 'relwidth': 0.45, 'relheight': 0.2}, {'relx': 0.5, 'rely': 0.5, 'relwidth': 0.45, 'relheight': 0.2}, {'relx': 0.5, 'rely': 0.725, 'relwidth': 0.45, 'relheight': 0.2}] },
            '1_landscape_3_portrait': { 'priority': 15, 'orientations': ['landscape', 'portrait', 'portrait', 'portrait'], 'geometry': [{'relx': 0.05, 'rely': 0.05, 'relwidth': 0.9, 'relheight': 0.5}, {'relx': 0.05, 'rely': 0.60, 'relwidth': 0.28, 'relheight': 0.35}, {'relx': 0.36, 'rely': 0.60, 'relwidth': 0.28, 'relheight': 0.35}, {'relx': 0.67, 'rely': 0.60, 'relwidth': 0.28, 'relheight': 0.35}] },
            '2_landscape_2_portrait': { 'priority': 14, 'orientations': ['landscape', 'landscape', 'portrait', 'portrait'], 'geometry': [{'relx': 0.05, 'rely': 0.05, 'relwidth': 0.55, 'relheight': 0.42}, {'relx': 0.05, 'rely': 0.53, 'relwidth': 0.55, 'relheight': 0.42}, {'relx': 0.65, 'rely': 0.05, 'relwidth': 0.3, 'relheight': 0.42}, {'relx': 0.65, 'rely': 0.53, 'relwidth': 0.3, 'relheight': 0.42}] },
            '4_any_diamond': { 'priority': 13, 'orientations': ['any', 'any', 'any', 'any'], 'geometry': [{'relx': 0.25, 'rely': 0.05, 'relwidth': 0.5, 'relheight': 0.4}, {'relx': 0.05, 'rely': 0.3, 'relwidth': 0.4, 'relheight': 0.4}, {'relx': 0.55, 'rely': 0.3, 'relwidth': 0.4, 'relheight': 0.4}, {'relx': 0.25, 'rely': 0.55, 'relwidth': 0.5, 'relheight': 0.4}] },
            '1_landscape_2_portrait': { 'priority': 10, 'orientations': ['landscape', 'portrait', 'portrait'], 'geometry': [{'relx': 0.05, 'rely': 0.05, 'relwidth': 0.9, 'relheight': 0.55}, {'relx': 0.1, 'rely': 0.65, 'relwidth': 0.35, 'relheight': 0.3}, {'relx': 0.55, 'rely': 0.65, 'relwidth': 0.35, 'relheight': 0.3}] },
            '2_portrait_1_landscape': { 'priority': 9, 'orientations': ['portrait', 'portrait', 'landscape'], 'geometry': [{'relx': 0.05, 'rely': 0.05, 'relwidth': 0.42, 'relheight': 0.9}, {'relx': 0.53, 'rely': 0.05, 'relwidth': 0.42, 'relheight': 0.42}, {'relx': 0.53, 'rely': 0.53, 'relwidth': 0.42, 'relheight': 0.42}] },
            '3_portrait': { 'priority': 8, 'orientations': ['portrait', 'portrait', 'portrait'], 'geometry': [{'relx': 0.05, 'rely': 0.1, 'relwidth': 0.28, 'relheight': 0.8}, {'relx': 0.36, 'rely': 0.1, 'relwidth': 0.28, 'relheight': 0.8}, {'relx': 0.67, 'rely': 0.1, 'relwidth': 0.28, 'relheight': 0.8}] },
            '2_landscape': { 'priority': 7, 'orientations': ['landscape', 'landscape'], 'geometry': [{'relx': 0.05, 'rely': 0.05, 'relwidth': 0.9, 'relheight': 0.42}, {'relx': 0.05, 'rely': 0.53, 'relwidth': 0.9, 'relheight': 0.42}] },
            '2_portrait': { 'priority': 6, 'orientations': ['portrait', 'portrait'], 'geometry': [{'relx': 0.05, 'rely': 0.1, 'relwidth': 0.42, 'relheight': 0.8}, {'relx': 0.53, 'rely': 0.1, 'relwidth': 0.42, 'relheight': 0.8}] },
            '1_portrait_1_landscape_MODIFIED': { 'priority': 5, 'orientations': ['portrait', 'landscape'], 'geometry': [{'relx': 0.05, 'rely': 0.05, 'relwidth': 0.4, 'relheight': 0.9}, {'relx': 0.5, 'rely': 0.3, 'relwidth': 0.45, 'relheight': 0.4}] },
            '1_any': { 'priority': 1, 'orientations': ['any'], 'geometry': [{'relx': 0.05, 'rely': 0.05, 'relwidth': 0.9, 'relheight': 0.9}] }
        }
        return layouts

    def _generate_page_definitions(self, all_images):
        """A képek listájából súlyozott véletlenszerűséggel generálja az oldalak felépítését,
        figyelembe véve a képek tájolását (álló/fekvő) is."""
        page_definitions = []
        layouts = self._define_smart_layouts()
        layout_priority = sorted(layouts.items(), key=lambda item: item[1]['priority'], reverse=True)
        
        image_index = 0
        while image_index < len(all_images):
            
            candidate_layouts = []
            # Végigmegyünk a lehetséges elrendezéseken prioritás szerint
            for layout_name, config in layout_priority:
                num_needed = len(config['orientations'])
                
                # 1. Ellenőrizzük, van-e elég kép a hátralévőkből ehhez a sablonhoz
                if image_index + num_needed <= len(all_images):
                    
                    # 2. JAVÍTÁS: Ellenőrizzük, hogy a képek tájolása megfelel-e a sablonnak
                    is_match = True
                    # A következő N darab kép tájolásának listája
                    user_orientations_chunk = [img['orientation'] for img in all_images[image_index : image_index + num_needed]]
                    
                    for i in range(num_needed):
                        required = config['orientations'][i]
                        user_orientation = user_orientations_chunk[i]
                        
                        # Ha a sablon nem 'any' (bármilyen) és nem egyezik a kép tájolásával, akkor ez nem jó sablon.
                        if required != 'any' and required != user_orientation:
                            is_match = False
                            break # Felesleges tovább vizsgálni ezt a sablont
                    
                    # Ha a tájolások egyeztek, hozzáadjuk a lehetséges jelöltekhez
                    if is_match:
                        candidate_layouts.append(config)

            chosen_layout = None
            if candidate_layouts:
                # A jelöltek közül választunk egyet a prioritásuk alapján (súlyozott véletlen)
                priorities = [layout['priority'] for layout in candidate_layouts]
                if sum(priorities) > 0:
                    chosen_layout = random.choices(candidate_layouts, weights=priorities, k=1)[0]
                else: # Ha minden jelöltnek 0 a prioritása
                    chosen_layout = random.choice(candidate_layouts)

            # Ha találtunk megfelelő sablont, alkalmazzuk
            if chosen_layout:
                chunk_size = len(chosen_layout['orientations'])
                images_for_page = all_images[image_index : image_index + chunk_size]
                layout_geo = chosen_layout['geometry']
                page_definitions.append({'images': images_for_page, 'layout_geo': layout_geo})
                image_index += chunk_size
            else:
                # Tartalék logika: ha egyetlen sablon sem illik, a maradék képeket
                # egy alapértelmezett, rácsos elrendezésbe tesszük.
                remaining_count = len(all_images) - image_index
                images_for_page = all_images[image_index : image_index + remaining_count]
                layout_geo = self._generate_layout_template(len(images_for_page))
                page_definitions.append({'images': images_for_page, 'layout_geo': layout_geo})
                image_index += remaining_count # Ezzel biztosan kilépünk a ciklusból

        return page_definitions

    def _prompt_wizard_style_choice(self):
        """Felugró ablak a varázsló stílusának kiválasztásához."""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Okos Varázsló Stílus")
        dialog.geometry("400x200")
        dialog.transient(self.root); dialog.grab_set()
        
        def set_mode(mode):
            self.wizard_mode = mode
            dialog.destroy()

        ctk.CTkLabel(dialog, text="Milyen stílusban kéred a fotókönyvet?", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(20, 10))
        ctk.CTkButton(dialog, text="🎨 Szín alapú (Automatikus hangulatfelismerés)", command=lambda: set_mode('color'), height=40).pack(pady=10, padx=20, fill="x")
        ctk.CTkButton(dialog, text="🖼️ Kép alapú (Automatikus témaillesztés)", command=lambda: set_mode('image'), height=40).pack(pady=10, padx=20, fill="x")
        
        self.root.wait_window(dialog)

    def _get_best_matching_image_theme(self, user_images_info):
        """Kiválasztja a felhasználó képeihez legjobban illő, előre definiált téma-mappát."""
        user_color_category = self._get_dominant_color_category(user_images_info)
        
        themes_path = os.path.join(self.assets_path, "themes")
        available_themes = []
        if os.path.exists(themes_path):
            available_themes = [d for d in os.listdir(themes_path) if os.path.isdir(os.path.join(themes_path, d))]

        if not available_themes: return None
        
        if not user_color_category:
            return random.choice(available_themes)

        theme_profiles = {}
        for theme_name in available_themes:
            try:
                theme_bg_path = os.path.join(themes_path, theme_name, "backgrounds")
                if not os.path.exists(theme_bg_path): continue
                
                sample_images = [os.path.join(theme_bg_path, f) for f in os.listdir(theme_bg_path)][:3]
                if not sample_images: continue

                sample_images_info = [{'path': p} for p in sample_images]
                theme_category = self._get_dominant_color_category(sample_images_info)
                if theme_category:
                    theme_profiles[theme_name] = theme_category
            except Exception as e:
                print(f"Hiba a(z) '{theme_name}' téma profilozása közben: {e}")
                continue

        matching_themes = [name for name, category in theme_profiles.items() if category == user_color_category]
        
        if matching_themes:
            return random.choice(matching_themes)
        else:
            return random.choice(available_themes) if available_themes else None

    def _get_random_assets_from_image_theme(self, theme_name):
        """Visszaad egy véletlen háttér- és keret-elérési utat a megadott téma mappából."""
        theme_path = os.path.join(self.assets_path, "themes", theme_name)
        bg_path = os.path.join(theme_path, "backgrounds")
        fr_path = os.path.join(theme_path, "frames")
        
        chosen_bg, chosen_fr = None, None
        
        if os.path.exists(bg_path):
            bgs = [os.path.join(bg_path, f) for f in os.listdir(bg_path) if f.lower().endswith(('.png', '.jpg'))]
            if bgs: chosen_bg = random.choice(bgs)
            
        if os.path.exists(fr_path):
            frs = [os.path.join(fr_path, f) for f in os.listdir(fr_path) if f.lower().endswith('.png')]
            if frs: chosen_fr = random.choice(frs)
            
        return chosen_bg, chosen_fr

    def _get_dominant_color_category(self, image_info_list):
        """Képek listájából visszaadja a domináns színkategória nevét (pl. 'warm', 'cool')."""
        def get_color_category(r, g, b):
            if r > 150 and g > 150 and b < 100: return 'warm'
            if r > 130 and g > 90 and g < 150 and b < 100: return 'autumn'
            if b > 150 and r < 100 and g < 150: return 'cool'
            if g > 130 and r < 130 and b < 130: return 'forest'
            if r > 180 and g > 180 and b > 180: return 'light'
            return 'other'

        category_counts = {'warm': 0, 'autumn': 0, 'cool': 0, 'forest': 0, 'light': 0}
        
        for image_info in image_info_list[:5]:
            try:
                with Image.open(image_info['path']) as img:
                    img = img.resize((50, 50))
                    for pixel in list(img.getdata()):
                        if len(pixel) < 3: continue
                        category = get_color_category(pixel[0], pixel[1], pixel[2])
                        if category in category_counts:
                            category_counts[category] += 1
            except Exception:
                continue
        
        filtered_counts = {k: v for k, v in category_counts.items() if k != 'light'}
        if not filtered_counts or max(filtered_counts.values()) == 0:
            return 'light' if category_counts.get('light', 0) > 0 else None
        else:
            return max(filtered_counts, key=filtered_counts.get)
            
    def _create_color_theme_from_images(self, all_images):
        """A képek színvilága alapján létrehoz egy teljes téma szótárat (név, paletta, keret)."""
        dominant_category = self._get_dominant_color_category(all_images)
        
        palettes = {
            'autumn': {'name': 'Meleg Őszi', 'palette': ['#DABBAA', '#C4A484', '#A47A68', '#E6D3F5'], 'frame': 'preset_gold'},
            'warm': {'name': 'Napfényes', 'palette': ['#F5E6D3', '#FFDDC1', '#FFD1D1', '#FFF9C4'], 'frame': 'preset_gold'},
            'cool': {'name': 'Hűvös Vízparti', 'palette': ['#D3E3F1', '#A9CCE3', '#D4E6F1', '#EAF2F8'], 'frame': 'preset_white'},
            'forest': {'name': 'Erdei Séta', 'palette': ['#D1F0D1', '#A9DFBF', '#ABEBC6', '#E8F5E9'], 'frame': 'preset_white'},
            'light': {'name': 'Letisztult Modern', 'palette': ['#FFFFFF', '#F0F0F0', '#EAEAEA'], 'frame': 'preset_black'}
        }
        
        return palettes.get(dominant_category, palettes['light'])

    def run_smart_wizard(self):
        self.wizard_mode = None
        self._prompt_wizard_style_choice()
        if self.wizard_mode is None: return

        folder_path = filedialog.askdirectory(title="Mappa kiválasztása az Okos Varázslóhoz")
        if not folder_path: return

        self._show_working_indicator()
        try:
            image_groups = self._analyze_images_by_subfolder(folder_path)
            
            if not image_groups:
                messagebox.showwarning("Okos Varázsló", "A kiválasztott mappa vagy annak almappái nem tartalmaznak képeket.")
                self._hide_working_indicator()
                return

            all_images_flat_for_theme = [img for group in image_groups.values() for img in group]
            
            final_style_name = ""
            if self.wizard_mode == 'color':
                self.wizard_color_theme = self._create_color_theme_from_images(all_images_flat_for_theme)
                final_style_name = self.wizard_color_theme['name']
            else:
                self.wizard_image_theme_name = self._get_best_matching_image_theme(all_images_flat_for_theme)
                if self.wizard_image_theme_name is None:
                    messagebox.showwarning("Nincs téma", "Nem találtam egyetlen téma mappát sem az 'assets/themes' útvonalon.")
                    self._hide_working_indicator()
                    return
                final_style_name = self.wizard_image_theme_name.capitalize()
            
            self._reset_project_state()
            page_size = self.BOOK_SIZES.get(self.selected_book_size_name.get(), self.DEFAULT_BOOK_SIZE_PIXELS)
            # Az első oldalt itt még nem hozzuk létre, mert a ciklus kezeli
            
            group_paths = list(image_groups.keys())
            random.shuffle(group_paths)
            
            is_first_page_ever = True

            for group_path in group_paths:
                images_in_group = image_groups[group_path]
                # A mappa nevét kinyerjük az elérési útból
                folder_name = os.path.basename(group_path)
                
                group_page_defs = self._generate_page_definitions(images_in_group)
                
                # Végigmegyünk a mappához tartozó oldalakon
                for i, page_def in enumerate(group_page_defs):
                    # Ha ez a legelső oldal, akkor létrehozzuk az alap oldalt
                    if is_first_page_ever:
                        self.pages.append({'photos': [], 'texts': [], 'size': page_size})
                        is_first_page_ever = False
                    else:
                        # Minden további oldalhoz újat adunk hozzá
                        self.add_new_page()

                   
                    # Csak a mappa első oldalára tesszük ki a címet
                    if i == 0:
                        # Esztétikusabbá tesszük a mappa nevét (pl. "balatoni_kepek" -> "Balatoni kepek")
                        title_text = folder_name.replace('_', ' ').replace('-', ' ').capitalize()
                        
                        title_text_data = {
                            "text": title_text,
                            "relx": 0.5,       # Vízszintesen középre
                            "rely": 0.08,      # Fentre, egy kis margóval
                            "font_family": "Impact", # Látványosabb betűtípus
                            "font_size": 48,       # Nagyobb méret
                            "font_style": "normal",
                            "font_color": "#333333", # Sötétszürke szín
                            "show_bg_on_select": False
                        }
                        self.pages[self.current_page]['texts'].append(title_text_data)
                    

                    if self.wizard_mode == 'color':
                        self.pages[self.current_page]['background'] = random.choice(self.wizard_color_theme['palette'])
                        frame = self.wizard_color_theme['frame']
                    else: 
                        bg_path, frame_path = self._get_random_assets_from_image_theme(self.wizard_image_theme_name)
                        if bg_path: self.pages[self.current_page]['background'] = {'type': 'image', 'path': bg_path}
                        frame = frame_path

                    self.pages[self.current_page]['photos'] = copy.deepcopy(page_def['layout_geo'])
                    for idx, image_info in enumerate(page_def['images']):
                        if idx < len(self.pages[self.current_page]['photos']):
                            self.pages[self.current_page]['photos'][idx]['path'] = image_info['path']
                            key = str((self.current_page, idx))
                            self.photo_properties[key] = {'frame_path': frame}
            
            if not self.editor_ui_built:
                self._build_editor_ui()
                self.editor_ui_built = True
            
            self.current_page = 0
            self.refresh_editor_view()
            total_images = len(all_images_flat_for_theme)
            messagebox.showinfo("Okos Varázsló kész", f"{total_images} kép elhelyezve {len(self.pages)} oldalon, a(z) '{final_style_name}' stílus alapján.")

        except Exception as e:
            messagebox.showerror("Okos Varázsló Hiba", f"Hiba történt: {e}")
            traceback.print_exc()
        finally:
            self._hide_working_indicator()


    def run(self):
        self.root.mainloop()


def main():
    app = FotokonyvGUI()
    app.run()

if __name__ == "__main__":
    main()
    # --- SZÖVEGSZERKESZTŐ METÓDUSOK ---
    def add_text(self):
        if self.text_editor_window is not None and self.text_editor_window.winfo_exists():
            self.text_editor_window.focus(); return
        self._create_text_editor_window()

    def _create_text_editor_window(self):
        self.text_editor_window = ctk.CTkToplevel(self.root)
        self.text_editor_window.title("Szöveg Eszköztár"); self.text_editor_window.geometry("350x550")
        self.text_editor_window.transient(self.root)
        button_frame = ctk.CTkFrame(self.text_editor_window, fg_color="transparent")
        button_frame.pack(pady=10, padx=10, fill="x")
        ctk.CTkButton(button_frame, text="Új szövegdoboz", command=self._add_new_textbox).pack(side="left", expand=True, padx=5)
        self.delete_text_button = ctk.CTkButton(button_frame, text="Kijelölt törlése", fg_color="#D32F2F", hover_color="#B71C1C", command=self._delete_selected_text)
        self.delete_text_button.pack(side="left", expand=True, padx=5)
        self.text_editor_panel = ctk.CTkFrame(self.text_editor_window)
        self.text_editor_panel.pack(pady=10, padx=10, fill="both", expand=True)
        ctk.CTkLabel(self.text_editor_panel, text="Szöveg tartalma:").pack(anchor="w", padx=10)
        self.text_input = ctk.CTkTextbox(self.text_editor_panel, height=100)
        self.text_input.pack(fill="x", padx=10, pady=5)
        self.text_input.bind("<KeyRelease>", self._update_text_properties) 
        ctk.CTkLabel(self.text_editor_panel, text="Betűtípus:").pack(anchor="w", padx=10, pady=(10,0))
        self.font_family_var = ctk.StringVar(value="Arial")
        self.font_family_menu = ctk.CTkOptionMenu(self.text_editor_panel, variable=self.font_family_var, values=["Arial", "Times New Roman", "Courier New", "Verdana", "Impact"], command=self._update_text_properties)
        self.font_family_menu.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(self.text_editor_panel, text="Betűméret:").pack(anchor="w", padx=10, pady=(10,0))
        self.font_size_slider = ctk.CTkSlider(self.text_editor_panel, from_=10, to=100, number_of_steps=90, command=self._update_text_properties)
        self.font_size_slider.pack(fill="x", padx=10, pady=5)
        style_frame = ctk.CTkFrame(self.text_editor_panel, fg_color="transparent")
        style_frame.pack(fill="x", padx=10, pady=5)
        self.font_bold_var = ctk.StringVar(value="off")
        self.font_italic_var = ctk.StringVar(value="off")
        self.font_bold_checkbox = ctk.CTkCheckBox(style_frame, text="Félkövér", variable=self.font_bold_var, onvalue="on", offvalue="off", command=self._update_text_properties)
        self.font_bold_checkbox.pack(side="left", padx=5)
        self.font_italic_checkbox = ctk.CTkCheckBox(style_frame, text="Dőlt", variable=self.font_italic_var, onvalue="on", offvalue="off", command=self._update_text_properties)
        self.font_italic_checkbox.pack(side="left", padx=5)
        self.text_color_button = ctk.CTkButton(self.text_editor_panel, text="Szín választása", command=self._choose_text_color)
        self.text_color_button.pack(pady=10)
        self.show_bg_var = ctk.StringVar(value="off")
        self.show_bg_checkbox = ctk.CTkCheckBox(self.text_editor_panel, text="Kijelölés háttere", variable=self.show_bg_var, onvalue="on", offvalue="off", command=self._update_text_properties)
        self.show_bg_checkbox.pack(pady=10, padx=10, anchor="w")
        self.update_text_editor_ui()

    def _add_new_textbox(self):
        new_text = {"text": "Új szöveg", "relx": 0.5, "rely": 0.5, "font_family": "Arial", "font_size": 24, "font_style": "normal", "font_color": "#000000", "show_bg_on_select": False}
        if 'texts' not in self.pages[self.current_page]: self.pages[self.current_page]['texts'] = []
        self.pages[self.current_page]['texts'].append(new_text)
        self.refresh_editor_view()
        self._select_text(len(self.pages[self.current_page]['texts']) - 1)

    def _delete_selected_text(self):
        if self.selected_text_index is not None:
            text_index_to_delete = self.selected_text_index
            self._deselect_all()
            del self.pages[self.current_page]['texts'][text_index_to_delete]
            self.refresh_editor_view()
            self.update_text_editor_ui()
    
    def _render_text_boxes(self):
        if 'texts' not in self.pages[self.current_page]: return
        offset_x, offset_y, draw_w, draw_h = self._get_page_draw_area()
        if draw_w <= 1 or draw_h <= 1: return
        
        for i, text_data in enumerate(self.pages[self.current_page]['texts']):
            style_string = text_data.get('font_style', 'normal')
            font_obj = ctk.CTkFont(family=text_data.get('font_family', 'Arial'), size=text_data.get('font_size', 12), weight="bold" if "bold" in style_string else "normal", slant="italic" if "italic" in style_string else "roman")
            container = ctk.CTkFrame(self.canvas, fg_color="transparent")
            label = ctk.CTkLabel(container, text=text_data['text'], font=font_obj, text_color=text_data.get('font_color', '#000000'), fg_color="transparent")
            label.pack(padx=2, pady=2)
            
            abs_x = offset_x + int(text_data['relx'] * draw_w)
            abs_y = offset_y + int(text_data['rely'] * draw_h)

            canvas_item_id = self.canvas.create_window(abs_x, abs_y, window=container, anchor="center", tags="text")
            self.widget_to_canvas_item[container] = canvas_item_id
            
            container.bind("<ButtonPress-1>", lambda e, index=i: self._on_widget_press(e, 'text', index))
            container.bind("<B1-Motion>", lambda e: self._on_widget_drag(e))
            container.bind("<ButtonRelease-1>", lambda e: self._on_widget_release(e))
            label.bind("<ButtonPress-1>", lambda e, index=i: self._on_widget_press(e, 'text', index))
            label.bind("<B1-Motion>", lambda e: self._on_widget_drag(e))
            label.bind("<ButtonRelease-1>", lambda e: self._on_widget_release(e))
            self.text_widgets.append(container)

    def _update_selected_text_widget(self):
        if self.selected_text_index is None: return

        try:
            text_data = self.pages[self.current_page]['texts'][self.selected_text_index]
            text_widget_container = self.text_widgets[self.selected_text_index]
            text_label = text_widget_container.winfo_children()[0]

            font_obj = ctk.CTkFont(
                family=text_data.get('font_family', 'Arial'),
                size=text_data.get('font_size', 12),
                weight="bold" if "bold" in text_data.get('font_style', 'normal') else "normal",
                slant="italic" if "italic" in text_data.get('font_style', 'normal') else "roman"
            )
            
            text_label.configure(text=text_data['text'], font=font_obj)
        except (IndexError, AttributeError) as e:
            print(f"Hiba a szöveg widget frissítésekor: {e}")

    def _update_text_properties(self, event=None):
        if self.selected_text_index is None: return
        
        try:
            text_data = self.pages[self.current_page]['texts'][self.selected_text_index]
            text_data['text'] = self.text_input.get("1.0", "end-1c")
            text_data['font_family'] = self.font_family_var.get()
            text_data['font_size'] = int(self.font_size_slider.get())
            style = []
            if self.font_bold_var.get() == "on": style.append("bold")
            if self.font_italic_var.get() == "on": style.append("italic")
            text_data['font_style'] = " ".join(style) if style else "normal"
            text_data['show_bg_on_select'] = self.show_bg_var.get() == "on"

            self._update_selected_text_widget()

        except (AttributeError, IndexError, ValueError) as e:
            print(f"Hiba a szöveg tulajdonságainak frissítésekor: {e}")

    def update_text_editor_ui(self):
        if not (self.text_editor_window and self.text_editor_window.winfo_exists()): return
        is_text_selected = self.selected_text_index is not None
        widgets_to_toggle = [self.text_input, self.font_family_menu, self.font_size_slider, self.font_bold_checkbox, self.font_italic_checkbox, self.text_color_button, self.delete_text_button, self.show_bg_checkbox]
        for widget in widgets_to_toggle:
            widget.configure(state="normal" if is_text_selected else "disabled")
        
        if is_text_selected:
            text_data = self.pages[self.current_page]['texts'][self.selected_text_index]
            self.text_input.delete("1.0", "end"); self.text_input.insert("1.0", text_data['text'])
            self.font_family_var.set(text_data.get('font_family', 'Arial'))
            self.font_size_slider.set(text_data.get('font_size', 12))
            self.font_bold_var.set("on" if "bold" in text_data.get('font_style', '') else "off")
            self.font_italic_var.set("on" if "italic" in text_data.get('font_style', '') else "off")
            self.show_bg_var.set("on" if text_data.get('show_bg_on_select', True) else "off")
        else: self.text_input.delete("1.0", "end")
            
    def _choose_text_color(self):
        if self.selected_text_index is None: return
        current_color = self.pages[self.current_page]['texts'][self.selected_text_index].get('font_color', '#000000')
        color_code = colorchooser.askcolor(title="Válassz színt", initialcolor=current_color)
        if color_code and color_code[1]:
            self.pages[self.current_page]['texts'][self.selected_text_index]['font_color'] = color_code[1]

    # --- MOZGATÁS METÓDUSAI ---
    def _on_widget_press(self, event, item_type, index):
        widget_to_drag = None
        if item_type == 'photo':
            if index < len(self.photo_frames):
                self._select_photo(index)
                widget_to_drag = self.photo_frames[index]
            else: return
        elif item_type == 'text':
            if index < len(self.text_widgets):
                self._select_text(index)
                widget_to_drag = self.text_widgets[index]
            else: return
        else: return
        
        canvas_item_id = self.widget_to_canvas_item.get(widget_to_drag)
        if canvas_item_id:
            self.canvas.tag_raise(canvas_item_id)
            # Elmentjük a kezdő pozíciót is
            x, y = self.canvas.coords(canvas_item_id)
            self._drag_data = {
                "widget": widget_to_drag, 
                "item_id": canvas_item_id, 
                "item_type": item_type, 
                "index": index, 
                "offset_x": event.x_root, 
                "offset_y": event.y_root,
                "start_pos": (x, y) # ÚJ: Kezdő pozíció elmentése
            }

    def _on_widget_drag(self, event):
        if not self._drag_data: return
        
        item_id = self._drag_data["item_id"]
        
        dx = event.x_root - self._drag_data["offset_x"]
        dy = event.y_root - self._drag_data["offset_y"]
        
        self.canvas.move(item_id, dx, dy)
        
        self._drag_data["offset_x"] = event.x_root
        self._drag_data["offset_y"] = event.y_root

    def _on_widget_release(self, event):
        if not self._drag_data: return
        
        dragged_index = self._drag_data["index"]
        dragged_type = self._drag_data["item_type"]
        dragged_id = self._drag_data["item_id"]
        
        # Csak fotók cseréjét kezeljük
        if dragged_type == 'photo':
            # Megkeressük az elemet az egér kurzor alatt
            x, y = event.x_root - self.canvas.winfo_rootx(), event.y_root - self.canvas.winfo_rooty()
            overlapping_items = self.canvas.find_overlapping(x, y, x, y)
            
            target_index = None
            for item_id in overlapping_items:
                # Keressük azt a widgetet, amihez az item_id tartozik
                for i, frame in enumerate(self.photo_frames):
                    if frame and self.widget_to_canvas_item.get(frame) == item_id:
                        if i != dragged_index: # Nem a saját magára dobta
                            target_index = i
                            break
                if target_index is not None:
                    break

            # --- KÉPCSERE LOGIKA ---
            if target_index is not None:
                # Megcseréljük a képek útvonalait és a tulajdonságokat
                photos = self.pages[self.current_page]['photos']
                photos[dragged_index]['path'], photos[target_index]['path'] = \
                    photos[target_index]['path'], photos[dragged_index]['path']

                # Tulajdonságok cseréje
                dragged_key = str((self.current_page, dragged_index))
                target_key = str((self.current_page, target_index))
                
                dragged_props = self.photo_properties.pop(dragged_key, {})
                target_props = self.photo_properties.pop(target_key, {})

                self.photo_properties[dragged_key] = target_props
                self.photo_properties[target_key] = dragged_props
                
                self.refresh_editor_view()
                self._drag_data = {}
                return # Befejeztük a cserét

        # --- EREDETI MOZGATÁS LOGIKA (ha nem történt csere) ---
        offset_x, offset_y, draw_w, draw_h = self._get_page_draw_area()
        if draw_w == 0 or draw_h == 0: 
            self._drag_data = {}
            return
            
        x, y = self.canvas.coords(dragged_id)

        if dragged_type == 'photo':
            data_list = self.pages[self.current_page]['photos']
            data_list[dragged_index]['relx'] = (x - offset_x) / draw_w
            data_list[dragged_index]['rely'] = (y - offset_y) / draw_h
        elif dragged_type == 'text':
            data_list = self.pages[self.current_page]['texts']
            data_list[dragged_index]['relx'] = (x - offset_x) / draw_w
            data_list[dragged_index]['rely'] = (y - offset_y) / draw_h
            
        self._drag_data = {}
    
    # --- VARÁZSLÓ FUNKCIÓK ---
    def run_basic_wizard(self):
        folder_path = filedialog.askdirectory(title="Mappa kiválasztása a Varázslóhoz")
        if not folder_path: return

        self._show_working_indicator()
        try:
            image_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            if not image_files:
                messagebox.showwarning("Varázsló", "A mappa nem tartalmaz képeket.")
                return

            self._reset_project_state()
            images_per_page = 4
            
            for i in range(0, len(image_files), images_per_page):
                page_images = image_files[i:i + images_per_page]
                
                if i == 0:
                    page_size = self.BOOK_SIZES.get(self.selected_book_size_name.get(), self.DEFAULT_BOOK_SIZE_PIXELS)
                    self.pages.append({'photos': [], 'texts': [], 'size': page_size})
                else:
                    self.add_new_page()
                
                self.pages[self.current_page]['photos'] = self._generate_layout_template(len(page_images))
                
                for idx, path in enumerate(page_images):
                    self.pages[self.current_page]['photos'][idx]['path'] = path
                    key = str((self.current_page, idx))
                    self.photo_properties[key] = {'frame_path': random.choice(['preset_black', 'preset_white'])}
                
                bg_colors = ['#F0F0F0', '#D3E3F1', '#D1F0D1', '#F5E6D3']
                self.pages[self.current_page]['background'] = random.choice(bg_colors)

            if not self.editor_ui_built: 
                self._build_editor_ui()
                self.editor_ui_built = True
            
            self.current_page = 0
            self.refresh_editor_view()
            messagebox.showinfo("Varázsló kész", f"{len(image_files)} kép elhelyezve {len(self.pages)} oldalon.")
        except Exception as e:
            messagebox.showerror("Varázsló Hiba", f"Hiba történt: {e}")
            traceback.print_exc()
        finally:
            self._hide_working_indicator()


    def _analyze_images_by_subfolder(self, parent_folder_path):
        """
        Bejárja a megadott mappát és annak összes almappáját,
        majd csoportosítva adja vissza a képeket.
        A visszatérési érték egy szótár, ahol a kulcsok az almappák útvonalai,
        az értékek pedig az adott mappában található képek elemzett listái.
        """
        image_groups = {}
        
        # A képek "természetes" sorrendbe rendezéséhez kell
        def natural_sort_key(s):
            filename = os.path.basename(s)
            return [int(text) if text.isdigit() else text.lower() for text in re.split(r'([0-9]+)', filename)]

        for dirpath, _, filenames in os.walk(parent_folder_path):
            analyzed_in_folder = []
            
            # Fájlok rendezése a természetes sorrend alapján
            sorted_filenames = sorted(filenames, key=natural_sort_key)

            for filename in sorted_filenames:
                if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    continue
                
                path = os.path.join(dirpath, filename)
                try:
                    with Image.open(path) as img:
                        w, h = img.size
                        ratio = w / h if h > 0 else 1
                        orientation = 'square'
                        if ratio > 1.1: orientation = 'landscape'
                        elif ratio < 0.9: orientation = 'portrait'
                        analyzed_in_folder.append({'path': path, 'orientation': orientation})
                except Exception as e:
                    print(f"Hiba a kép elemzésekor ({os.path.basename(path)}): {e}")
            
            # Csak akkor adjuk hozzá a csoporthoz, ha találtunk benne képet
            if analyzed_in_folder:
                image_groups[dirpath] = analyzed_in_folder
                
        return image_groups


    def _analyze_images(self, folder_path):
        def natural_sort_key(s):
            filename = os.path.basename(s)
            return [int(text) if text.isdigit() else text.lower() for text in re.split(r'([0-9]+)', filename)]

        analyzed = []
        image_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        image_files.sort(key=natural_sort_key)

        for path in image_files:
            try:
                with Image.open(path) as img:
                    w, h = img.size
                    ratio = w / h if h > 0 else 1
                    orientation = 'square'
                    if ratio > 1.1: orientation = 'landscape'
                    elif ratio < 0.9: orientation = 'portrait'
                    analyzed.append({'path': path, 'orientation': orientation})
            except Exception as e:
                print(f"Hiba a kép elemzésekor ({os.path.basename(path)}): {e}")
        return analyzed

    def _define_smart_layouts(self):
        layouts = {
            '1_landscape_4_square': { 'priority': 20, 'orientations': ['landscape', 'square', 'square', 'square', 'square'], 'geometry': [{'relx': 0.05, 'rely': 0.05, 'relwidth': 0.9, 'relheight': 0.55}, {'relx': 0.05, 'rely': 0.65, 'relwidth': 0.2, 'relheight': 0.3}, {'relx': 0.275, 'rely': 0.65, 'relwidth': 0.2, 'relheight': 0.3}, {'relx': 0.5, 'rely': 0.65, 'relwidth': 0.2, 'relheight': 0.3}, {'relx': 0.725, 'rely': 0.65, 'relwidth': 0.2, 'relheight': 0.3}] },
            '1_portrait_4_landscape': { 'priority': 19, 'orientations': ['portrait', 'landscape', 'landscape', 'landscape', 'landscape'], 'geometry': [{'relx': 0.05, 'rely': 0.05, 'relwidth': 0.4, 'relheight': 0.9}, {'relx': 0.5, 'rely': 0.05, 'relwidth': 0.45, 'relheight': 0.2}, {'relx': 0.5, 'rely': 0.275, 'relwidth': 0.45, 'relheight': 0.2}, {'relx': 0.5, 'rely': 0.5, 'relwidth': 0.45, 'relheight': 0.2}, {'relx': 0.5, 'rely': 0.725, 'relwidth': 0.45, 'relheight': 0.2}] },
            '1_landscape_3_portrait': { 'priority': 15, 'orientations': ['landscape', 'portrait', 'portrait', 'portrait'], 'geometry': [{'relx': 0.05, 'rely': 0.05, 'relwidth': 0.9, 'relheight': 0.5}, {'relx': 0.05, 'rely': 0.60, 'relwidth': 0.28, 'relheight': 0.35}, {'relx': 0.36, 'rely': 0.60, 'relwidth': 0.28, 'relheight': 0.35}, {'relx': 0.67, 'rely': 0.60, 'relwidth': 0.28, 'relheight': 0.35}] },
            '2_landscape_2_portrait': { 'priority': 14, 'orientations': ['landscape', 'landscape', 'portrait', 'portrait'], 'geometry': [{'relx': 0.05, 'rely': 0.05, 'relwidth': 0.55, 'relheight': 0.42}, {'relx': 0.05, 'rely': 0.53, 'relwidth': 0.55, 'relheight': 0.42}, {'relx': 0.65, 'rely': 0.05, 'relwidth': 0.3, 'relheight': 0.42}, {'relx': 0.65, 'rely': 0.53, 'relwidth': 0.3, 'relheight': 0.42}] },
            '4_any_diamond': { 'priority': 13, 'orientations': ['any', 'any', 'any', 'any'], 'geometry': [{'relx': 0.25, 'rely': 0.05, 'relwidth': 0.5, 'relheight': 0.4}, {'relx': 0.05, 'rely': 0.3, 'relwidth': 0.4, 'relheight': 0.4}, {'relx': 0.55, 'rely': 0.3, 'relwidth': 0.4, 'relheight': 0.4}, {'relx': 0.25, 'rely': 0.55, 'relwidth': 0.5, 'relheight': 0.4}] },
            '1_landscape_2_portrait': { 'priority': 10, 'orientations': ['landscape', 'portrait', 'portrait'], 'geometry': [{'relx': 0.05, 'rely': 0.05, 'relwidth': 0.9, 'relheight': 0.55}, {'relx': 0.1, 'rely': 0.65, 'relwidth': 0.35, 'relheight': 0.3}, {'relx': 0.55, 'rely': 0.65, 'relwidth': 0.35, 'relheight': 0.3}] },
            '2_portrait_1_landscape': { 'priority': 9, 'orientations': ['portrait', 'portrait', 'landscape'], 'geometry': [{'relx': 0.05, 'rely': 0.05, 'relwidth': 0.42, 'relheight': 0.9}, {'relx': 0.53, 'rely': 0.05, 'relwidth': 0.42, 'relheight': 0.42}, {'relx': 0.53, 'rely': 0.53, 'relwidth': 0.42, 'relheight': 0.42}] },
            '3_portrait': { 'priority': 8, 'orientations': ['portrait', 'portrait', 'portrait'], 'geometry': [{'relx': 0.05, 'rely': 0.1, 'relwidth': 0.28, 'relheight': 0.8}, {'relx': 0.36, 'rely': 0.1, 'relwidth': 0.28, 'relheight': 0.8}, {'relx': 0.67, 'rely': 0.1, 'relwidth': 0.28, 'relheight': 0.8}] },
            '2_landscape': { 'priority': 7, 'orientations': ['landscape', 'landscape'], 'geometry': [{'relx': 0.05, 'rely': 0.05, 'relwidth': 0.9, 'relheight': 0.42}, {'relx': 0.05, 'rely': 0.53, 'relwidth': 0.9, 'relheight': 0.42}] },
            '2_portrait': { 'priority': 6, 'orientations': ['portrait', 'portrait'], 'geometry': [{'relx': 0.05, 'rely': 0.1, 'relwidth': 0.42, 'relheight': 0.8}, {'relx': 0.53, 'rely': 0.1, 'relwidth': 0.42, 'relheight': 0.8}] },
            '1_portrait_1_landscape_MODIFIED': { 'priority': 5, 'orientations': ['portrait', 'landscape'], 'geometry': [{'relx': 0.05, 'rely': 0.05, 'relwidth': 0.4, 'relheight': 0.9}, {'relx': 0.5, 'rely': 0.3, 'relwidth': 0.45, 'relheight': 0.4}] },
            '1_any': { 'priority': 1, 'orientations': ['any'], 'geometry': [{'relx': 0.05, 'rely': 0.05, 'relwidth': 0.9, 'relheight': 0.9}] }
        }
        return layouts

    def _generate_page_definitions(self, all_images):
        """A képek listájából súlyozott véletlenszerűséggel generálja az oldalak felépítését,
        figyelembe véve a képek tájolását (álló/fekvő) is."""
        page_definitions = []
        layouts = self._define_smart_layouts()
        layout_priority = sorted(layouts.items(), key=lambda item: item[1]['priority'], reverse=True)
        
        image_index = 0
        while image_index < len(all_images):
            
            candidate_layouts = []
            # Végigmegyünk a lehetséges elrendezéseken prioritás szerint
            for layout_name, config in layout_priority:
                num_needed = len(config['orientations'])
                
                # 1. Ellenőrizzük, van-e elég kép a hátralévőkből ehhez a sablonhoz
                if image_index + num_needed <= len(all_images):
                    
                    # 2. JAVÍTÁS: Ellenőrizzük, hogy a képek tájolása megfelel-e a sablonnak
                    is_match = True
                    # A következő N darab kép tájolásának listája
                    user_orientations_chunk = [img['orientation'] for img in all_images[image_index : image_index + num_needed]]
                    
                    for i in range(num_needed):
                        required = config['orientations'][i]
                        user_orientation = user_orientations_chunk[i]
                        
                        # Ha a sablon nem 'any' (bármilyen) és nem egyezik a kép tájolásával, akkor ez nem jó sablon.
                        if required != 'any' and required != user_orientation:
                            is_match = False
                            break # Felesleges tovább vizsgálni ezt a sablont
                    
                    # Ha a tájolások egyeztek, hozzáadjuk a lehetséges jelöltekhez
                    if is_match:
                        candidate_layouts.append(config)

            chosen_layout = None
            if candidate_layouts:
                # A jelöltek közül választunk egyet a prioritásuk alapján (súlyozott véletlen)
                priorities = [layout['priority'] for layout in candidate_layouts]
                if sum(priorities) > 0:
                    chosen_layout = random.choices(candidate_layouts, weights=priorities, k=1)[0]
                else: # Ha minden jelöltnek 0 a prioritása
                    chosen_layout = random.choice(candidate_layouts)

            # Ha találtunk megfelelő sablont, alkalmazzuk
            if chosen_layout:
                chunk_size = len(chosen_layout['orientations'])
                images_for_page = all_images[image_index : image_index + chunk_size]
                layout_geo = chosen_layout['geometry']
                page_definitions.append({'images': images_for_page, 'layout_geo': layout_geo})
                image_index += chunk_size
            else:
                # Tartalék logika: ha egyetlen sablon sem illik, a maradék képeket
                # egy alapértelmezett, rácsos elrendezésbe tesszük.
                remaining_count = len(all_images) - image_index
                images_for_page = all_images[image_index : image_index + remaining_count]
                layout_geo = self._generate_layout_template(len(images_for_page))
                page_definitions.append({'images': images_for_page, 'layout_geo': layout_geo})
                image_index += remaining_count # Ezzel biztosan kilépünk a ciklusból

        return page_definitions

    def _prompt_wizard_style_choice(self):
        """Felugró ablak a varázsló stílusának kiválasztásához."""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Okos Varázsló Stílus")
        dialog.geometry("400x200")
        dialog.transient(self.root); dialog.grab_set()
        
        def set_mode(mode):
            self.wizard_mode = mode
            dialog.destroy()

        ctk.CTkLabel(dialog, text="Milyen stílusban kéred a fotókönyvet?", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(20, 10))
        ctk.CTkButton(dialog, text="🎨 Szín alapú (Automatikus hangulatfelismerés)", command=lambda: set_mode('color'), height=40).pack(pady=10, padx=20, fill="x")
        ctk.CTkButton(dialog, text="🖼️ Kép alapú (Automatikus témaillesztés)", command=lambda: set_mode('image'), height=40).pack(pady=10, padx=20, fill="x")
        
        self.root.wait_window(dialog)

    def _get_best_matching_image_theme(self, user_images_info):
        """Kiválasztja a felhasználó képeihez legjobban illő, előre definiált téma-mappát."""
        user_color_category = self._get_dominant_color_category(user_images_info)
        
        themes_path = os.path.join(self.assets_path, "themes")
        available_themes = []
        if os.path.exists(themes_path):
            available_themes = [d for d in os.listdir(themes_path) if os.path.isdir(os.path.join(themes_path, d))]

        if not available_themes: return None
        
        if not user_color_category:
            return random.choice(available_themes)

        theme_profiles = {}
        for theme_name in available_themes:
            try:
                theme_bg_path = os.path.join(themes_path, theme_name, "backgrounds")
                if not os.path.exists(theme_bg_path): continue
                
                sample_images = [os.path.join(theme_bg_path, f) for f in os.listdir(theme_bg_path)][:3]
                if not sample_images: continue

                sample_images_info = [{'path': p} for p in sample_images]
                theme_category = self._get_dominant_color_category(sample_images_info)
                if theme_category:
                    theme_profiles[theme_name] = theme_category
            except Exception as e:
                print(f"Hiba a(z) '{theme_name}' téma profilozása közben: {e}")
                continue

        matching_themes = [name for name, category in theme_profiles.items() if category == user_color_category]
        
        if matching_themes:
            return random.choice(matching_themes)
        else:
            return random.choice(available_themes) if available_themes else None

    def _get_random_assets_from_image_theme(self, theme_name):
        """Visszaad egy véletlen háttér- és keret-elérési utat a megadott téma mappából."""
        theme_path = os.path.join(self.assets_path, "themes", theme_name)
        bg_path = os.path.join(theme_path, "backgrounds")
        fr_path = os.path.join(theme_path, "frames")
        
        chosen_bg, chosen_fr = None, None
        
        if os.path.exists(bg_path):
            bgs = [os.path.join(bg_path, f) for f in os.listdir(bg_path) if f.lower().endswith(('.png', '.jpg'))]
            if bgs: chosen_bg = random.choice(bgs)
            
        if os.path.exists(fr_path):
            frs = [os.path.join(fr_path, f) for f in os.listdir(fr_path) if f.lower().endswith('.png')]
            if frs: chosen_fr = random.choice(frs)
            
        return chosen_bg, chosen_fr

    def _get_dominant_color_category(self, image_info_list):
        """Képek listájából visszaadja a domináns színkategória nevét (pl. 'warm', 'cool')."""
        def get_color_category(r, g, b):
            if r > 150 and g > 150 and b < 100: return 'warm'
            if r > 130 and g > 90 and g < 150 and b < 100: return 'autumn'
            if b > 150 and r < 100 and g < 150: return 'cool'
            if g > 130 and r < 130 and b < 130: return 'forest'
            if r > 180 and g > 180 and b > 180: return 'light'
            return 'other'

        category_counts = {'warm': 0, 'autumn': 0, 'cool': 0, 'forest': 0, 'light': 0}
        
        for image_info in image_info_list[:5]:
            try:
                with Image.open(image_info['path']) as img:
                    img = img.resize((50, 50))
                    for pixel in list(img.getdata()):
                        if len(pixel) < 3: continue
                        category = get_color_category(pixel[0], pixel[1], pixel[2])
                        if category in category_counts:
                            category_counts[category] += 1
            except Exception:
                continue
        
        filtered_counts = {k: v for k, v in category_counts.items() if k != 'light'}
        if not filtered_counts or max(filtered_counts.values()) == 0:
            return 'light' if category_counts.get('light', 0) > 0 else None
        else:
            return max(filtered_counts, key=filtered_counts.get)
            
    def _create_color_theme_from_images(self, all_images):
        """A képek színvilága alapján létrehoz egy teljes téma szótárat (név, paletta, keret)."""
        dominant_category = self._get_dominant_color_category(all_images)
        
        palettes = {
            'autumn': {'name': 'Meleg Őszi', 'palette': ['#DABBAA', '#C4A484', '#A47A68', '#E6D3F5'], 'frame': 'preset_gold'},
            'warm': {'name': 'Napfényes', 'palette': ['#F5E6D3', '#FFDDC1', '#FFD1D1', '#FFF9C4'], 'frame': 'preset_gold'},
            'cool': {'name': 'Hűvös Vízparti', 'palette': ['#D3E3F1', '#A9CCE3', '#D4E6F1', '#EAF2F8'], 'frame': 'preset_white'},
            'forest': {'name': 'Erdei Séta', 'palette': ['#D1F0D1', '#A9DFBF', '#ABEBC6', '#E8F5E9'], 'frame': 'preset_white'},
            'light': {'name': 'Letisztult Modern', 'palette': ['#FFFFFF', '#F0F0F0', '#EAEAEA'], 'frame': 'preset_black'}
        }
        
        return palettes.get(dominant_category, palettes['light'])

    def run_smart_wizard(self):
        self.wizard_mode = None
        self._prompt_wizard_style_choice()
        if self.wizard_mode is None: return

        folder_path = filedialog.askdirectory(title="Mappa kiválasztása az Okos Varázslóhoz")
        if not folder_path: return

        self._show_working_indicator()
        try:
            image_groups = self._analyze_images_by_subfolder(folder_path)
            
            if not image_groups:
                messagebox.showwarning("Okos Varázsló", "A kiválasztott mappa vagy annak almappái nem tartalmaznak képeket.")
                self._hide_working_indicator()
                return

            all_images_flat_for_theme = [img for group in image_groups.values() for img in group]
            
            final_style_name = ""
            if self.wizard_mode == 'color':
                self.wizard_color_theme = self._create_color_theme_from_images(all_images_flat_for_theme)
                final_style_name = self.wizard_color_theme['name']
            else:
                self.wizard_image_theme_name = self._get_best_matching_image_theme(all_images_flat_for_theme)
                if self.wizard_image_theme_name is None:
                    messagebox.showwarning("Nincs téma", "Nem találtam egyetlen téma mappát sem az 'assets/themes' útvonalon.")
                    self._hide_working_indicator()
                    return
                final_style_name = self.wizard_image_theme_name.capitalize()
            
            self._reset_project_state()
            page_size = self.BOOK_SIZES.get(self.selected_book_size_name.get(), self.DEFAULT_BOOK_SIZE_PIXELS)
            # Az első oldalt itt még nem hozzuk létre, mert a ciklus kezeli
            
            group_paths = list(image_groups.keys())
            random.shuffle(group_paths)
            
            is_first_page_ever = True

            for group_path in group_paths:
                images_in_group = image_groups[group_path]
                # A mappa nevét kinyerjük az elérési útból
                folder_name = os.path.basename(group_path)
                
                group_page_defs = self._generate_page_definitions(images_in_group)
                
                # Végigmegyünk a mappához tartozó oldalakon
                for i, page_def in enumerate(group_page_defs):
                    # Ha ez a legelső oldal, akkor létrehozzuk az alap oldalt
                    if is_first_page_ever:
                        self.pages.append({'photos': [], 'texts': [], 'size': page_size})
                        is_first_page_ever = False
                    else:
                        # Minden további oldalhoz újat adunk hozzá
                        self.add_new_page()

                   
                    # Csak a mappa első oldalára tesszük ki a címet
                    if i == 0:
                        # Esztétikusabbá tesszük a mappa nevét (pl. "balatoni_kepek" -> "Balatoni kepek")
                        title_text = folder_name.replace('_', ' ').replace('-', ' ').capitalize()
                        
                        title_text_data = {
                            "text": title_text,
                            "relx": 0.5,       # Vízszintesen középre
                            "rely": 0.08,      # Fentre, egy kis margóval
                            "font_family": "Impact", # Látványosabb betűtípus
                            "font_size": 48,       # Nagyobb méret
                            "font_style": "normal",
                            "font_color": "#333333", # Sötétszürke szín
                            "show_bg_on_select": False
                        }
                        self.pages[self.current_page]['texts'].append(title_text_data)
                    

                    if self.wizard_mode == 'color':
                        self.pages[self.current_page]['background'] = random.choice(self.wizard_color_theme['palette'])
                        frame = self.wizard_color_theme['frame']
                    else: 
                        bg_path, frame_path = self._get_random_assets_from_image_theme(self.wizard_image_theme_name)
                        if bg_path: self.pages[self.current_page]['background'] = {'type': 'image', 'path': bg_path}
                        frame = frame_path

                    self.pages[self.current_page]['photos'] = copy.deepcopy(page_def['layout_geo'])
                    for idx, image_info in enumerate(page_def['images']):
                        if idx < len(self.pages[self.current_page]['photos']):
                            self.pages[self.current_page]['photos'][idx]['path'] = image_info['path']
                            key = str((self.current_page, idx))
                            self.photo_properties[key] = {'frame_path': frame}
            
            if not self.editor_ui_built:
                self._build_editor_ui()
                self.editor_ui_built = True
            
            self.current_page = 0
            self.refresh_editor_view()
            total_images = len(all_images_flat_for_theme)
            messagebox.showinfo("Okos Varázsló kész", f"{total_images} kép elhelyezve {len(self.pages)} oldalon, a(z) '{final_style_name}' stílus alapján.")

        except Exception as e:
            messagebox.showerror("Okos Varázsló Hiba", f"Hiba történt: {e}")
            traceback.print_exc()
        finally:
            self._hide_working_indicator()


    def run(self):
        self.root.mainloop()


def main():
    app = FotokonyvGUI()
    app.run()

if __name__ == "__main__":
    main()
