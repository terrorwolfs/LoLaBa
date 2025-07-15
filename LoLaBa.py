import customtkinter as ctk
from tkinter import messagebox, filedialog
import os
from PIL import Image, ImageTk
import traceback

# --- Alapbeállítások ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class FotokonyvGUI:
    """A fotókönyv-szerkesztő alkalmazás fő grafikus felületét (GUI) kezelő osztály."""

    def __init__(self):
        """Az osztály inicializálása, a fő ablak és az alapvető állapotok beállítása."""
        self.root = ctk.CTk()
        self.root.title("LoLaBa Fotókönyv")
        self.root.geometry("1200x800")
        
        # Dizájnhoz használt színek központi tárolása.
        self.colors = {
            'bg_primary': '#C4A484', 'bg_secondary': '#B5956B', 
            'card_bg': '#F5F5F5', 'button_bg': '#E8E8E8',
            'accent': '#A4B068', 'text_primary': '#333333',
            'text_secondary': '#666666', 'green_box': '#4CAF50',
            'selected_card': '#E8F5E8', 'selected_photo_border': '#4CAF50'
        }
        
        # Projekt állapotának alaphelyzetbe állítása és a főmenü létrehozása.
        self._reset_project_state()
        self.create_main_menu()

    # --- BELSŐ MŰKÖDÉST SEGÍTŐ METÓDUSOK ---

    def _reset_project_state(self):
        """Minden projekt-specifikus változót alaphelyzetbe állít. Új projekt vagy betöltés esetén hívódik meg."""
        self.current_layout = 1
        self.custom_image_count = 1
        self.selected_layout_card = None
        self.pages = []
        self.current_page = 0
        self.uploaded_photos = []
        self.selected_photo_index = None
        self.photo_frames = []
        self.photo_properties = {}

    def _select_photo(self, photo_index):
        """Kiválaszt egy képet az oldalon, kiemeli a keretét és aktiválja a szerkesztő csúszkákat."""
        # Előző kijelölés megszüntetése, ha volt.
        if self.selected_photo_index is not None and self.selected_photo_index < len(self.photo_frames):
            self.photo_frames[self.selected_photo_index].configure(fg_color="#CCCCCC")

        # Új kép kijelölése és vizuális jelölése.
        self.selected_photo_index = photo_index
        if self.selected_photo_index < len(self.photo_frames):
            self.photo_frames[self.selected_photo_index].configure(fg_color=self.colors['selected_photo_border'])

        # A csúszkák értékének beállítása a képhez tárolt, vagy alapértelmezett értékekre.
        props = self.photo_properties.get((self.current_page, photo_index), {'zoom': 1.0, 'pan_x': 0.5})
        self.zoom_slider.set(props['zoom'])
        self.pan_x_slider.set(props['pan_x'])
        
        # Csúszkák aktiválása.
        self.zoom_slider.configure(state="normal")
        self.pan_x_slider.configure(state="normal")

    def _update_photo_properties(self, value=None):
        """A csúszkák változásakor elmenti az új zoom/pan értékeket és frissíti a kép nézetét."""
        if self.selected_photo_index is None: return

        key = (self.current_page, self.selected_photo_index)
        self.photo_properties[key] = {'zoom': self.zoom_slider.get(), 'pan_x': self.pan_x_slider.get()}
        
        # A kép újrarajzolása a frissített tulajdonságokkal.
        frame = self.photo_frames[self.selected_photo_index]
        path = self.pages[self.current_page]['photos'][self.selected_photo_index]
        self.display_photo_placeholder(frame, path, self.selected_photo_index, is_update=True)

    def _disable_sliders(self):
        """Letiltja a csúszkákat és megszünteti a kép kijelölését, pl. oldalváltáskor."""
        if hasattr(self, 'zoom_slider') and hasattr(self, 'pan_x_slider'):
            self.zoom_slider.configure(state="disabled")
            self.pan_x_slider.configure(state="disabled")
            self.zoom_slider.set(1.0)
            self.pan_x_slider.set(0.5)
        if self.selected_photo_index is not None and self.selected_photo_index < len(self.photo_frames):
             self.photo_frames[self.selected_photo_index].configure(fg_color="#CCCCCC")
        self.selected_photo_index = None

    # --- FELÜLETET ÉPÍTŐ METÓDUSOK ---

    def create_main_menu(self):
        """Felépíti a főmenüt a kezdőgombokkal."""
        self.clear_window()
        main_frame = ctk.CTkFrame(self.root, fg_color=self.colors['bg_primary'], corner_radius=0)
        main_frame.pack(fill="both", expand=True)
        ctk.CTkLabel(main_frame, text="LoLaBa Fotókönyv", font=ctk.CTkFont(size=48, weight="bold"), text_color="white").pack(pady=(80, 20))
        ctk.CTkLabel(main_frame, text="Készíts saját, egyedi fotókönyvet egyszerű lépésekkel!", font=ctk.CTkFont(size=18), text_color="white").pack(pady=(0, 60))
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(expand=True)
        button_style = {'width': 350, 'height': 60, 'font': ctk.CTkFont(size=16, weight="bold"), 'corner_radius': 15, 'fg_color': self.colors['card_bg'], 'text_color': self.colors['text_primary'], 'hover_color': '#F0F0F0'}
        ctk.CTkButton(button_frame, text="🆕 Új projekt létrehozása", command=lambda: self.show_page_selection(is_new_project=True), **button_style).pack(pady=15)
        ctk.CTkButton(button_frame, text="📁 Korábbi projekt megnyitása", command=self.load_project, **button_style).pack(pady=15)
        ctk.CTkButton(button_frame, text="🚪 Kilépés", command=self.root.quit, **button_style).pack(pady=15)

    def create_layout_preview(self, parent, layout_count, click_handler=None):
        """Legenerál egy kis előnézeti képet a layout kártyákhoz zöld négyzetekkel."""
        preview_frame = ctk.CTkFrame(parent, width=180, height=100, fg_color=self.colors['accent'], corner_radius=15)
        preview_frame.pack(pady=(20, 10))
        preview_frame.pack_propagate(False)
        if click_handler: preview_frame.bind("<Button-1>", click_handler)

        if layout_count == 1:
            box = ctk.CTkFrame(preview_frame, width=60, height=50, fg_color=self.colors['green_box'], corner_radius=8)
            box.place(relx=0.5, rely=0.5, anchor="center")
            if click_handler: box.bind("<Button-1>", click_handler)
        elif layout_count == 2:
            box1 = ctk.CTkFrame(preview_frame, width=45, height=50, fg_color=self.colors['green_box'], corner_radius=8)
            box1.place(relx=0.35, rely=0.5, anchor="center")
            box2 = ctk.CTkFrame(preview_frame, width=45, height=50, fg_color=self.colors['green_box'], corner_radius=8)
            box2.place(relx=0.65, rely=0.5, anchor="center")
            if click_handler:
                box1.bind("<Button-1>", click_handler)
                box2.bind("<Button-1>", click_handler)
        elif layout_count == 4:
            positions = [(0.35, 0.35), (0.65, 0.35), (0.35, 0.65), (0.65, 0.65)]
            for (x, y) in positions:
                box = ctk.CTkFrame(preview_frame, width=35, height=25, fg_color=self.colors['green_box'], corner_radius=6)
                box.place(relx=x, rely=y, anchor="center")
                if click_handler: box.bind("<Button-1>", click_handler)
        else:
            if layout_count <= 9:
                if layout_count <= 3: cols, rows = layout_count, 1
                elif layout_count <= 6: cols, rows = 3, 2
                else: cols, rows = 3, 3
                box_width = max(20, 60 // cols)
                box_height = max(15, 40 // rows)
                for i in range(layout_count):
                    row, col = i // cols, i % cols
                    start_x, start_y = 0.5 - (cols - 1) * 0.15, 0.5 - (rows - 1) * 0.15
                    x, y = start_x + (col * 0.3), start_y + (row * 0.3)
                    box = ctk.CTkFrame(preview_frame, width=box_width, height=box_height, fg_color=self.colors['green_box'], corner_radius=4)
                    box.place(relx=x, rely=y, anchor="center")
                    if click_handler: box.bind("<Button-1>", click_handler)
            else:
                count_label = ctk.CTkLabel(preview_frame, text=f"{layout_count}\nkép", font=ctk.CTkFont(size=16, weight="bold"), text_color=self.colors['green_box'])
                count_label.place(relx=0.5, rely=0.5, anchor="center")
                if click_handler: count_label.bind("<Button-1>", click_handler)

    def show_page_selection(self, is_new_project=False):
        """Felépíti a layout-választó képernyőt. Megkülönbözteti az új projektet a meglévő oldal módosításától."""
        if is_new_project:
            self._reset_project_state()
        
        self.selected_layout_card = None 
        
        self.clear_window()
        main_frame = ctk.CTkFrame(self.root, fg_color=self.colors['bg_primary'], corner_radius=0)
        main_frame.pack(fill="both", expand=True)
        ctk.CTkLabel(main_frame, text="Oldalnézet kiválasztása", font=ctk.CTkFont(size=32, weight="bold"), text_color="white").pack(pady=(50, 40))
        layout_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        layout_frame.pack(expand=True)
        cards_frame = ctk.CTkFrame(layout_frame, fg_color="transparent")
        cards_frame.pack()
        layouts = [{"name": "1 kép", "value": 1}, {"name": "2 kép", "value": 2}, {"name": "4 kép", "value": 4}]
        self.layout_cards = []
        first_row = ctk.CTkFrame(cards_frame, fg_color="transparent")
        first_row.pack(pady=10)
        for i, layout in enumerate(layouts):
            card = ctk.CTkFrame(first_row, width=220, height=180, fg_color=self.colors['card_bg'], corner_radius=20)
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
        second_row = ctk.CTkFrame(cards_frame, fg_color="transparent")
        second_row.pack(pady=10)
        self.custom_card = ctk.CTkFrame(second_row, width=320, height=220, fg_color=self.colors['card_bg'], corner_radius=20)
        self.custom_card.pack()
        self.custom_card.pack_propagate(False)
        custom_title = ctk.CTkLabel(self.custom_card, text="Egyéni mennyiség", font=ctk.CTkFont(size=18, weight="bold"), text_color=self.colors['text_primary'])
        custom_title.pack(pady=(15, 10))
        count_frame = ctk.CTkFrame(self.custom_card, fg_color="transparent")
        count_frame.pack(pady=10)
        ctk.CTkLabel(count_frame, text="Képek száma:", font=ctk.CTkFont(size=14), text_color=self.colors['text_primary']).pack(side="left", padx=(0, 10))
        self.custom_spinbox = ctk.CTkFrame(count_frame, fg_color="transparent")
        self.custom_spinbox.pack(side="left")
        ctk.CTkButton(self.custom_spinbox, text="−", width=30, height=30, font=ctk.CTkFont(size=16, weight="bold"), command=self.decrease_custom_count, fg_color=self.colors['accent'], hover_color='#8A9654').pack(side="left")
        self.custom_count_label = ctk.CTkLabel(self.custom_spinbox, text=str(self.custom_image_count), font=ctk.CTkFont(size=16, weight="bold"), text_color=self.colors['text_primary'], width=40)
        self.custom_count_label.pack(side="left", padx=5)
        ctk.CTkButton(self.custom_spinbox, text="+", width=30, height=30, font=ctk.CTkFont(size=16, weight="bold"), command=self.increase_custom_count, fg_color=self.colors['accent'], hover_color='#8A9654').pack(side="left")
        self.custom_preview_frame = ctk.CTkFrame(self.custom_card, fg_color="transparent")
        self.custom_preview_frame.pack(pady=15)
        self.update_custom_preview()
        ctk.CTkButton(self.custom_card, text="Egyéni layout kiválasztása", command=self.select_custom_layout, width=200, height=35, font=ctk.CTkFont(size=14, weight="bold"), corner_radius=10, fg_color=self.colors['accent'], hover_color='#8A9654').pack(pady=10)
        custom_click_handler = lambda e: self.select_custom_layout()
        self.custom_card.bind("<Button-1>", custom_click_handler)
        custom_title.bind("<Button-1>", custom_click_handler)
        ctk.CTkButton(main_frame, text="🔧 Tovább a szerkesztőbe", command=self.proceed_to_editor, width=250, height=50, font=ctk.CTkFont(size=16, weight="bold"), corner_radius=15, fg_color=self.colors['card_bg'], text_color=self.colors['text_primary'], hover_color='#F0F0F0').pack(pady=40)

    def select_layout(self, layout_value, card_widget):
        """Kezeli a layout kártyára való kattintást, vizuálisan jelöli a választást."""
        if self.selected_layout_card: self.selected_layout_card.configure(fg_color=self.colors['card_bg'])
        self.current_layout = layout_value
        self.selected_layout_card = card_widget
        card_widget.configure(fg_color=self.colors['selected_card'])
        if hasattr(self, 'custom_card') and self.custom_card is not card_widget: self.custom_card.configure(fg_color=self.colors['card_bg'])

    def select_custom_layout(self):
        """Kezeli az egyéni layout kártyára való kattintást."""
        if self.selected_layout_card: self.selected_layout_card.configure(fg_color=self.colors['card_bg'])
        for card in self.layout_cards: card.configure(fg_color=self.colors['card_bg'])
        self.current_layout = self.custom_image_count
        self.selected_layout_card = self.custom_card
        self.custom_card.configure(fg_color=self.colors['selected_card'])

    def decrease_custom_count(self):
        """Csökkenti a képek számát az egyéni layoutban."""
        if self.custom_image_count > 1:
            self.custom_image_count -= 1
            self.custom_count_label.configure(text=str(self.custom_image_count))
            self.update_custom_preview()
            if self.selected_layout_card == self.custom_card: self.current_layout = self.custom_image_count

    def increase_custom_count(self):
        """Növeli a képek számát az egyéni layoutban."""
        if self.custom_image_count < 20:
            self.custom_image_count += 1
            self.custom_count_label.configure(text=str(self.custom_image_count))
            self.update_custom_preview()
            if self.selected_layout_card == self.custom_card: self.current_layout = self.custom_image_count

    def update_custom_preview(self):
        """Frissíti az egyéni layout előnézeti képét."""
        for widget in self.custom_preview_frame.winfo_children(): widget.destroy()
        self.create_layout_preview(self.custom_preview_frame, self.custom_image_count, click_handler=lambda e: self.select_custom_layout())

    def proceed_to_editor(self):
        """Továbbnavigál a szerkesztőbe, létrehozza vagy módosítja az oldalt a választott layout alapján."""
        if not self.selected_layout_card:
            messagebox.showwarning("Figyelem", "Kérjük válassz egy layout-ot!")
            return
        
        page_data = {'layout': self.current_layout, 'texts': [], 'background': None}
        
        if not self.pages: # Ha ez az első oldal (új projekt).
            page_data['photos'] = [None] * self.current_layout
            self.pages = [page_data]
            self.current_page = 0
        else: # Ha egy meglévő oldal layoutját módosítjuk.
            old_photos = self.pages[self.current_page]['photos']
            new_photos = [None] * self.current_layout
            # Megpróbáljuk átmenteni a képeket az új layoutba.
            for i in range(min(len(old_photos), len(new_photos))):
                new_photos[i] = old_photos[i]
            page_data['photos'] = new_photos
            self.pages[self.current_page] = page_data
        
        self.show_photo_editor()

    def clear_window(self):
        """Letörli az összes widgetet a fő ablakról."""
        for widget in self.root.winfo_children(): widget.destroy()

    def create_photo_layout(self, parent_frame, page_data):
        """Dinamikusan felépíti a képhelyőrzők rácsát a szerkesztőben a megadott layout alapján."""
        for widget in parent_frame.winfo_children(): widget.destroy()
        self.photo_frames.clear()
        self._disable_sliders()
        num_photos = page_data['layout']
        
        if num_photos == 1:
            parent_frame.grid_rowconfigure(0, weight=1)
            parent_frame.grid_columnconfigure(0, weight=1)
            photo_frame = ctk.CTkFrame(parent_frame, fg_color="#CCCCCC", corner_radius=10)
            photo_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
            photo_frame.grid_propagate(False) # Megakadályozza, hogy a kép átméretezze a keretet.
            self.photo_frames.append(photo_frame)
            self.display_photo_placeholder(photo_frame, page_data['photos'][0], 0)
        elif num_photos == 2:
            parent_frame.grid_rowconfigure(0, weight=1)
            parent_frame.grid_columnconfigure((0, 1), weight=1)
            frame1 = ctk.CTkFrame(parent_frame, fg_color="#CCCCCC", corner_radius=10)
            frame1.grid(row=0, column=0, sticky="nsew", padx=5, pady=10)
            frame1.grid_propagate(False)
            self.photo_frames.append(frame1)
            self.display_photo_placeholder(frame1, page_data['photos'][0], 0)
            frame2 = ctk.CTkFrame(parent_frame, fg_color="#CCCCCC", corner_radius=10)
            frame2.grid(row=0, column=1, sticky="nsew", padx=5, pady=10)
            frame2.grid_propagate(False)
            self.photo_frames.append(frame2)
            self.display_photo_placeholder(frame2, page_data['photos'][1], 1)
        else: # Rácsos elrendezés 3+ kép esetén
            side_length = int(num_photos**0.5)
            cols = side_length if side_length > 0 and side_length**2 >= num_photos else side_length + 1
            if num_photos == 3: cols = 3
            if cols == 0: cols = 1
            rows = (num_photos + cols - 1) // cols
            for c in range(cols): parent_frame.grid_columnconfigure(c, weight=1)
            for r in range(rows): parent_frame.grid_rowconfigure(r, weight=1)
            for i in range(num_photos):
                row, col = i // cols, i % cols
                photo_frame = ctk.CTkFrame(parent_frame, fg_color="#CCCCCC", corner_radius=10)
                photo_frame.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
                photo_frame.grid_propagate(False)
                self.photo_frames.append(photo_frame)
                self.display_photo_placeholder(photo_frame, page_data['photos'][i], i)

    def display_photo_placeholder(self, parent_frame, photo_path, photo_index, is_update=False):
        """Megjelenít egy képet vagy egy "Kép hozzáadása" gombot a kép helyén."""
        if not is_update:
            for widget in parent_frame.winfo_children(): widget.destroy()
        if not photo_path or not os.path.exists(photo_path):
            add_btn = ctk.CTkButton(parent_frame, text="Kép hozzáadása", fg_color=self.colors['accent'], hover_color='#8A9654', command=lambda idx=photo_index: self.add_photo_to_slot(idx))
            add_btn.place(relx=0.5, rely=0.5, anchor="center")
            return
        try:
            key = (self.current_page, photo_index)
            props = self.photo_properties.get(key, {'zoom': 1.0, 'pan_x': 0.5})
            zoom, pan_x = props['zoom'], props['pan_x']
            parent_frame.update_idletasks()
            frame_w, frame_h = parent_frame.winfo_width(), parent_frame.winfo_height()
            
            # Fallback, ha a keret mérete még nem ismert
            if frame_w <= 1 or frame_h <= 1:
                img = Image.open(photo_path)
                img.thumbnail((200, 200), Image.LANCZOS)
            else:
                original_img = Image.open(photo_path)
                
                # Arányos nagyítás a kerethez (cover-szerű logika)
                img_ratio = original_img.width / original_img.height
                frame_ratio = frame_w / frame_h
                
                if img_ratio > frame_ratio:
                    new_h = int(frame_h * zoom)
                    new_w = int(new_h * img_ratio)
                else:
                    new_w = int(frame_w * zoom)
                    new_h = int(new_w / img_ratio)

                if new_w < 1 or new_h < 1: new_w, new_h = frame_w, frame_h
                
                zoomed_img = original_img.resize((new_w, new_h), Image.LANCZOS)
                
                # Kép kivágása a keret méretére
                extra_w, extra_h = max(0, zoomed_img.width - frame_w), max(0, zoomed_img.height - frame_h)
                crop_x, crop_y = int(extra_w * pan_x), int(extra_h / 2)
                
                img = zoomed_img.crop((crop_x, crop_y, crop_x + frame_w, crop_y + frame_h))
            
            img_tk = ImageTk.PhotoImage(img)
            
            # Kép frissítése vagy létrehozása
            if is_update and len(parent_frame.winfo_children()) > 0:
                img_label = parent_frame.winfo_children()[0]
                img_label.configure(image=img_tk)
            else:
                img_label = ctk.CTkLabel(parent_frame, image=img_tk, text="")
                img_label.place(relx=0.5, rely=0.5, anchor="center")
                img_label.bind("<Button-1>", lambda e, idx=photo_index: self._select_photo(idx))
            
            img_label.image = img_tk # Referencia mentése a garbage collector ellen.
        except Exception as e:
            print(f"--- KÉPMEGJELENÍTÉSI HIBA ---\nFájl: {photo_path}\nHiba: {e}\n{traceback.format_exc()}\n-----------------------------")
            if not parent_frame.winfo_children():
                ctk.CTkLabel(parent_frame, text="Hiba a kép\nbetöltésekor", text_color="red").place(relx=0.5, rely=0.5, anchor="center")

    def add_photo_to_slot(self, photo_index):
        """Megnyit egy fájlválasztót és hozzáadja a képet a megfelelő helyre."""
        filename = filedialog.askopenfilename(title="Válassz fotót", filetypes=[("Képfájlok", "*.jpg *.jpeg *.png *.gif *.bmp")])
        if filename:
            self.pages[self.current_page]['photos'][photo_index] = filename
            if filename not in self.uploaded_photos: self.uploaded_photos.append(filename)
            self.show_photo_editor()
    
    def select_page(self, page_idx):
        """Kiválaszt egy oldalt a bal oldali listából és frissíti a szerkesztőt."""
        if 0 <= page_idx < len(self.pages):
            self.current_page = page_idx
            self.show_photo_editor()
        
    def add_new_page(self):
        """Hozzáad egy új, üres oldalt a könyvhöz."""
        if not self.pages:
            self.pages.append({'layout': 1, 'photos': [None], 'texts': [], 'background': None})
        else:
            last_layout = self.pages[-1]['layout']
            self.pages.append({'layout': last_layout, 'photos': [None] * last_layout, 'texts': [], 'background': None})
        self.current_page = len(self.pages) - 1
        self.show_photo_editor()
    
    def change_layout(self): 
        """Elindítja a layout-váltás folyamatát a meglévő oldalhoz."""
        self.show_page_selection(is_new_project=False)

    def delete_page(self):
        """Törli az aktuálisan kiválasztott oldalt."""
        if len(self.pages) > 1:
            if messagebox.askyesno("Oldal törlése", f"Biztosan törölni szeretnéd a(z) {self.current_page + 1}. oldalt?"):
                del self.pages[self.current_page]
                if self.current_page >= len(self.pages): self.current_page = len(self.pages) - 1
                self.show_photo_editor()
        else:
            messagebox.showwarning("Utolsó oldal", "Nem törölheted az utolsó oldalt!")

    def show_photo_editor(self):
        """Felépíti a teljes szerkesztőfelületet a panelekkel és eszközökkel."""
        self.clear_window()
        main_frame = ctk.CTkFrame(self.root, fg_color=self.colors['bg_primary'], corner_radius=0)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        current_page_data = self.pages[self.current_page]
        title_text = f"Fotókönyv szerkesztő - Oldal {self.current_page + 1} ({current_page_data['layout']} képes elrendezés)"
        ctk.CTkLabel(main_frame, text=title_text, font=ctk.CTkFont(size=28, weight="bold"), text_color="white").pack(pady=(10, 20))
        
        workspace = ctk.CTkFrame(main_frame, fg_color="transparent")
        workspace.pack(fill="both", expand=True)
        
        # --- Panelek felépítése ---
        left_panel = ctk.CTkFrame(workspace, width=220, fg_color=self.colors['card_bg'], corner_radius=20)
        left_panel.pack(side="left", fill="y", padx=(0, 15))
        left_panel.pack_propagate(False)
        ctk.CTkLabel(left_panel, text="Oldalak", font=ctk.CTkFont(size=18, weight="bold"), text_color=self.colors['text_primary']).pack(pady=(20, 15))
        pages_scroll = ctk.CTkScrollableFrame(left_panel, fg_color="transparent")
        pages_scroll.pack(expand=True, fill="both", pady=10, padx=10)
        for i, page in enumerate(self.pages):
            page_frame = ctk.CTkFrame(pages_scroll, height=90, fg_color=self.colors['accent'] if i == self.current_page else self.colors['bg_secondary'], corner_radius=15)
            page_frame.pack(pady=5, fill="x")
            page_frame.pack_propagate(False)
            page_label = ctk.CTkLabel(page_frame, text=f"{i + 1}. oldal\n({page['layout']} kép)", font=ctk.CTkFont(size=11), text_color="white")
            page_label.pack(expand=True)
            def make_handler(idx): return lambda e: self.select_page(idx)
            handler = make_handler(i)
            page_frame.bind("<Button-1>", handler)
            page_label.bind("<Button-1>", handler)
        ctk.CTkButton(left_panel, text="+ Új oldal", command=self.add_new_page, height=40, font=ctk.CTkFont(size=14, weight="bold"), corner_radius=15, fg_color=self.colors['accent'], hover_color='#8A9654').pack(pady=15, padx=10, fill="x")
        
        right_panel = ctk.CTkFrame(workspace, width=260, fg_color=self.colors['card_bg'], corner_radius=20)
        right_panel.pack(side="right", fill="y", padx=(0,0))
        right_panel.pack_propagate(False)
        ctk.CTkLabel(right_panel, text="Eszközök", font=ctk.CTkFont(size=18, weight="bold"), text_color=self.colors['text_primary']).pack(pady=(20, 15))
        
        slider_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        slider_frame.pack(pady=10, fill="x", padx=20)
        ctk.CTkLabel(slider_frame, text="Méret (Zoom)", font=ctk.CTkFont(size=12)).pack()
        self.zoom_slider = ctk.CTkSlider(slider_frame, from_=1.0, to=3.0, command=self._update_photo_properties)
        self.zoom_slider.pack(fill="x", padx=5, pady=(0, 10))
        ctk.CTkLabel(slider_frame, text="Vízszintes pozíció", font=ctk.CTkFont(size=12)).pack()
        self.pan_x_slider = ctk.CTkSlider(slider_frame, from_=0.0, to=1.0, command=self._update_photo_properties)
        self.pan_x_slider.pack(fill="x", padx=5, pady=(0, 10))
        
        tools_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        tools_frame.pack(pady=10, fill="x", padx=20)
        tools = [("📷 Feltöltött fotók", self.view_uploaded_photos), ("🎨 Háttér", self.set_background), ("📝 Szöveg", self.add_text), ("🖼️ Keret", self.add_frame), ("🔄 Layout váltás", self.change_layout), ("🗑️ Oldal törlése", self.delete_page)]
        for text, command in tools:
            ctk.CTkButton(tools_frame, text=text, command=command, height=35, font=ctk.CTkFont(size=12), corner_radius=10, fg_color=self.colors['button_bg'], text_color=self.colors['text_secondary'], hover_color='#F0F0F0').pack(pady=3, fill="x")

        center_panel = ctk.CTkFrame(workspace, fg_color=current_page_data.get('background') or self.colors['card_bg'], corner_radius=20)
        center_panel.pack(side="left", fill="both", expand=True, padx=15)
        photo_container = ctk.CTkFrame(center_panel, fg_color="transparent")
        photo_container.pack(expand=True, fill="both", padx=10, pady=10)
        self.create_photo_layout(photo_container, current_page_data)
        
        toolbar = ctk.CTkFrame(main_frame, height=70, fg_color=self.colors['card_bg'], corner_radius=15)
        toolbar.pack(fill="x", pady=(20, 0))
        toolbar.pack_propagate(False)
        toolbar_buttons = [("💾 Mentés", self.save_project), ("📁 Betöltés", self.load_project), ("📤 Exportálás", self.export_project), ("🔙 Layout választás", lambda: self.show_page_selection(is_new_project=False)), ("🏠 Főmenü", self.create_main_menu)]
        buttons_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        buttons_frame.pack(expand=True)
        for text, command in toolbar_buttons:
            ctk.CTkButton(buttons_frame, text=text, command=command, width=140, height=40, font=ctk.CTkFont(size=12), corner_radius=10, fg_color=self.colors['button_bg'], text_color=self.colors['text_secondary'], hover_color='#F0F0F0').pack(side="left", padx=10, pady=15)

    def view_uploaded_photos(self):
        """Megjeleníti a már feltöltött fotókat egy külön ablakban."""
        if not self.uploaded_photos: messagebox.showinfo("Nincs feltöltött fotó", "Még nem töltöttél fel egyetlen fotót sem."); return
        photo_viewer_window = ctk.CTkToplevel(self.root)
        photo_viewer_window.title("Feltöltött fotók")
        photo_viewer_window.geometry("800x600")
        photo_viewer_window.transient(self.root)
        photo_viewer_window.grab_set()
        ctk.CTkLabel(photo_viewer_window, text="Feltöltött fotók", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=15)
        photos_frame = ctk.CTkScrollableFrame(photo_viewer_window, fg_color="transparent")
        photos_frame.pack(fill="both", expand=True, padx=20, pady=10)
        for i, photo_path in enumerate(self.uploaded_photos):
            try:
                img = Image.open(photo_path)
                img.thumbnail((150, 150), Image.LANCZOS)
                img_tk = ImageTk.PhotoImage(img)
                img_label = ctk.CTkLabel(photos_frame, image=img_tk, text=os.path.basename(photo_path), compound="top", font=ctk.CTkFont(size=10))
                img_label.image = img_tk
                img_label.grid(row=i // 4, column=i % 4, padx=10, pady=10)
            except Exception as e:
                print(f"Hiba a feltöltött kép betöltésekor {photo_path}: {e}")

    def save_project(self):
        """Projekt mentése (jelenleg csak szimulált)."""
        filename = filedialog.asksaveasfilename(title="Projekt mentése", defaultextension=".lolaba", filetypes=[("LoLaBa projekt", "*.lolaba")])
        if filename: messagebox.showinfo("Mentés", f"Projekt mentve: {os.path.basename(filename)}")
    
    def load_project(self):
        """Projekt betöltése (jelenleg csak szimulált)."""
        filename = filedialog.askopenfilename(title="Projekt betöltése", filetypes=[("LoLaBa projekt", "*.lolaba")])
        if filename:
            self._reset_project_state()
            self.pages = [{'layout': 2, 'photos': [None, None], 'texts': [], 'background': None}]
            messagebox.showinfo("Betöltés", f"Projekt betöltve: {os.path.basename(filename)}")
            self.show_photo_editor()
    
    def export_project(self):
        """Projekt exportálása (jelenleg csak szimulált)."""
        filename = filedialog.asksaveasfilename(title="Projekt exportálása", defaultextension=".pdf", filetypes=[("PDF fájl", "*.pdf")])
        if filename: messagebox.showinfo("Exportálás", f"Projekt exportálva: {os.path.basename(filename)}")
    
    def set_background(self):
        """Megnyit egy színválasztó ablakot az aktuális oldal hátterének beállításához."""
        color_picker = ctk.CTkToplevel(self.root)
        color_picker.title("Háttérszín választása")
        color_picker.geometry("320x200")
        color_picker.transient(self.root)
        color_picker.grab_set()

        def _apply_background_color(color):
            self.pages[self.current_page]['background'] = color
            color_picker.destroy()
            self.show_photo_editor()

        ctk.CTkLabel(color_picker, text="Válassz egy színt:", font=ctk.CTkFont(size=14)).pack(pady=10)
        
        palette_frame = ctk.CTkFrame(color_picker, fg_color="transparent")
        palette_frame.pack(pady=10, padx=10)
        colors = ['#FFFFFF', '#F0F0F0', '#D3E3F1', '#D1F0D1', '#F5E6D3', '#E6D3F5', '#FFDDC1', '#FFD1D1']
        
        for i, color in enumerate(colors):
            row, col = i // 4, i % 4
            color_btn = ctk.CTkButton(palette_frame, text="", fg_color=color, width=40, height=40, corner_radius=8,
                                      command=lambda c=color: _apply_background_color(c))
            color_btn.grid(row=row, column=col, padx=10, pady=10)
            
        remove_btn = ctk.CTkButton(color_picker, text="Háttér eltávolítása", command=lambda: _apply_background_color(None))
        remove_btn.pack(pady=10)

    def add_text(self): messagebox.showinfo("Szöveg", "Funkció fejlesztés alatt.")
    def add_frame(self): messagebox.showinfo("Keret", "Funkció fejlesztés alatt.")
    
    def run(self):
        """Elindítja az alkalmazás fő ciklusát."""
        self.root.mainloop()

def main():
    """A program belépési pontja."""
    app = FotokonyvGUI()
    app.run()

if __name__ == "__main__":
    main()
