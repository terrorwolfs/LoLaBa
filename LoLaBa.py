import customtkinter as ctk
from tkinter import messagebox, filedialog, colorchooser
import os
from PIL import Image, ImageDraw, ImageTk
import traceback
import re

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
        
        self.colors = {
            'bg_primary': '#C4A484', 'bg_secondary': '#B5956B', 
            'card_bg': '#F5F5F5', 'button_bg': '#E8E8E8',
            'accent': '#A4B068', 'text_primary': '#333333',
            'text_secondary': '#666666', 'green_box': '#4CAF50',
            'selected_card': '#E8F5E8', 'selected_photo_border': '#4CAF50',
            'selected_text_color': '#007BFF',
        }
        
        self.frame_editor_window = None
        self.text_editor_window = None
        self._reset_project_state()
        self.create_main_menu()

    # --- BELSŐ MŰKÖDÉST SEGÍTŐ METÓDUSOK ---

    def _reset_project_state(self):
        """Minden projekt-specifikus változót alaphelyzetbe állít."""
        self.current_layout = 1
        self.custom_image_count = 1
        self.selected_layout_card = None
        self.pages = []
        self.current_page = 0
        self.uploaded_photos = []
        self.selected_photo_index = None
        self.photo_frames = []
        self.photo_properties = {}
        self.text_widgets = []
        self.selected_text_index = None
        self._drag_data = {}
        
        if self.frame_editor_window and self.frame_editor_window.winfo_exists(): self.frame_editor_window.destroy()
        self.frame_editor_window = None
        if self.text_editor_window and self.text_editor_window.winfo_exists(): self.text_editor_window.destroy()
        self.text_editor_window = None

    def _select_photo(self, photo_index):
        """Kiválaszt egy képet az oldalon."""
        self._deselect_all()
        self.selected_photo_index = photo_index

        if self.selected_photo_index is not None and self.selected_photo_index < len(self.photo_frames):
            selected_frame = self.photo_frames[self.selected_photo_index]
            selected_frame.configure(border_width=3, border_color=self.colors['selected_photo_border'])
            selected_frame.lift()
            
            props = self.photo_properties.get((self.current_page, photo_index), {})
            photo_data = self.pages[self.current_page]['photos'][photo_index]

            self.zoom_slider.configure(state="normal")
            self.pan_x_slider.configure(state="normal")
            self.pan_y_slider.configure(state="normal")
            self.zoom_slider.set(props.get('zoom', 1.0))
            self.pan_x_slider.set(props.get('pan_x', 0.5))
            self.pan_y_slider.set(props.get('pan_y', 0.5))

            self.width_slider.configure(state="normal")
            self.height_slider.configure(state="normal")
            self.width_slider.set(photo_data.get('relwidth', 0.5))
            self.height_slider.set(photo_data.get('relheight', 0.5))
            
            if self.frame_editor_window and self.frame_editor_window.winfo_exists():
                self.update_frame_editor_ui()

    def _select_text(self, text_index):
        """Kiválaszt egy szövegdobozt az oldalon."""
        self._deselect_all()
        self.selected_text_index = text_index
        if self.selected_text_index < len(self.text_widgets):
            text_widget_container = self.text_widgets[self.selected_text_index]
            text_label = text_widget_container.winfo_children()[0]
            text_label.configure(text_color=self.colors['selected_text_color'])
            text_widget_container.lift()
        if self.text_editor_window and self.text_editor_window.winfo_exists():
            self.update_text_editor_ui()

    def _deselect_all(self):
        """Minden kijelölt elemről leveszi a kijelölést."""
        if self.selected_photo_index is not None and self.selected_photo_index < len(self.photo_frames):
            if self.photo_frames[self.selected_photo_index].winfo_exists():
                self.photo_frames[self.selected_photo_index].configure(border_width=0)
        self.selected_photo_index = None
        
        if self.selected_text_index is not None and self.selected_text_index < len(self.text_widgets):
            text_widget_container = self.text_widgets[self.selected_text_index]
            if text_widget_container.winfo_exists() and len(text_widget_container.winfo_children()) > 0:
                text_label = text_widget_container.winfo_children()[0]
                original_color = self.pages[self.current_page]['texts'][self.selected_text_index].get('font_color', '#000000')
                text_label.configure(text_color=original_color)
        self.selected_text_index = None

        if hasattr(self, 'zoom_slider'):
            self.zoom_slider.configure(state="disabled")
            self.pan_x_slider.configure(state="disabled")
            self.pan_y_slider.configure(state="disabled")
            self.width_slider.configure(state="disabled")
            self.height_slider.configure(state="disabled")

        if self.frame_editor_window and self.frame_editor_window.winfo_exists(): self.update_frame_editor_ui()
        if self.text_editor_window and self.text_editor_window.winfo_exists(): self.update_text_editor_ui()

    def _update_photo_properties(self, value=None):
        """Frissíti a kiválasztott kép belső tulajdonságait (zoom, pan, keret)."""
        if self.selected_photo_index is None: return
        key = (self.current_page, self.selected_photo_index)
        if key not in self.photo_properties: self.photo_properties[key] = {}
        
        if hasattr(self, 'zoom_slider'):
            self.photo_properties[key]['zoom'] = self.zoom_slider.get()
            self.photo_properties[key]['pan_x'] = self.pan_x_slider.get()
            self.photo_properties[key]['pan_y'] = self.pan_y_slider.get()
        
        if self.frame_editor_window and self.frame_editor_window.winfo_exists():
            self.photo_properties[key]['frame_scale'] = self.frame_scale_slider.get()
            self.photo_properties[key]['frame_offset_x'] = int(self.frame_offset_x_slider.get())
            self.photo_properties[key]['frame_offset_y'] = int(self.frame_offset_y_slider.get())
        
        if hasattr(self, 'photo_frames') and self.photo_frames and self.selected_photo_index < len(self.photo_frames):
            frame = self.photo_frames[self.selected_photo_index]
            photo_data = self.pages[self.current_page]['photos'][self.selected_photo_index]
            self.display_photo_placeholder(frame, photo_data, self.selected_photo_index, is_update=True)

    def _update_photo_size_from_sliders(self, value=None):
        """Frissíti a kiválasztott képkeret méretét a csúszkák alapján."""
        if self.selected_photo_index is None: return
        
        photo_data = self.pages[self.current_page]['photos'][self.selected_photo_index]
        photo_frame = self.photo_frames[self.selected_photo_index]

        new_relwidth = self.width_slider.get()
        new_relheight = self.height_slider.get()

        photo_data['relwidth'] = new_relwidth
        photo_data['relheight'] = new_relheight
        
        photo_frame.place_configure(relwidth=new_relwidth, relheight=new_relheight)
        
        self.display_photo_placeholder(photo_frame, photo_data, self.selected_photo_index, is_update=True)
    
    # --- FELÜLETET ÉPÍTŐ METÓDUSOK ---

    def clear_window(self):
        for widget in self.root.winfo_children(): widget.destroy()

    def create_main_menu(self):
        self._reset_project_state()
        self.clear_window()
        main_frame = ctk.CTkFrame(self.root, fg_color=self.colors['bg_primary'], corner_radius=0)
        main_frame.pack(fill="both", expand=True)
        ctk.CTkLabel(main_frame, text="LoLaBa Fotókönyv", font=ctk.CTkFont(size=48, weight="bold"), text_color="white").pack(pady=(80, 20))
        ctk.CTkLabel(main_frame, text="Készíts saját, egyedi fotókönyvet egyszerű lépésekkel!", font=ctk.CTkFont(size=18), text_color="white").pack(pady=(0, 60))
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent"); button_frame.pack(expand=True)
        button_style = {'width': 350, 'height': 60, 'font': ctk.CTkFont(size=16, weight="bold"), 'corner_radius': 15, 'fg_color': self.colors['card_bg'], 'text_color': self.colors['text_primary'], 'hover_color': '#F0F0F0'}
        ctk.CTkButton(button_frame, text="🆕 Új projekt létrehozása", command=lambda: self.show_page_selection(is_new_project=True), **button_style).pack(pady=15)
        ctk.CTkButton(button_frame, text="📁 Korábbi projekt megnyitása", command=self.load_project, **button_style).pack(pady=15)
        ctk.CTkButton(button_frame, text="🚪 Kilépés", command=self.root.quit, **button_style).pack(pady=15)

    def create_layout_preview(self, parent, layout_count, click_handler=None):
        preview_frame = ctk.CTkFrame(parent, width=180, height=100, fg_color=self.colors['accent'], corner_radius=15)
        preview_frame.pack(pady=(20, 10)); preview_frame.pack_propagate(False)
        if click_handler: preview_frame.bind("<Button-1>", click_handler)
        if layout_count == 1:
            box = ctk.CTkFrame(preview_frame, fg_color=self.colors['green_box'], corner_radius=6); box.place(relx=0.5, rely=0.5, relwidth=0.8, relheight=0.8, anchor="center")
        elif layout_count == 2:
            box1 = ctk.CTkFrame(preview_frame, fg_color=self.colors['green_box'], corner_radius=6); box1.place(relx=0.25, rely=0.5, relwidth=0.4, relheight=0.8, anchor="center")
            box2 = ctk.CTkFrame(preview_frame, fg_color=self.colors['green_box'], corner_radius=6); box2.place(relx=0.75, rely=0.5, relwidth=0.4, relheight=0.8, anchor="center")
        elif layout_count == 4:
            box1 = ctk.CTkFrame(preview_frame, fg_color=self.colors['green_box'], corner_radius=6); box1.place(relx=0.25, rely=0.25, relwidth=0.4, relheight=0.4, anchor="center")
            box2 = ctk.CTkFrame(preview_frame, fg_color=self.colors['green_box'], corner_radius=6); box2.place(relx=0.75, rely=0.25, relwidth=0.4, relheight=0.4, anchor="center")
            box3 = ctk.CTkFrame(preview_frame, fg_color=self.colors['green_box'], corner_radius=6); box3.place(relx=0.25, rely=0.75, relwidth=0.4, relheight=0.4, anchor="center")
            box4 = ctk.CTkFrame(preview_frame, fg_color=self.colors['green_box'], corner_radius=6); box4.place(relx=0.75, rely=0.75, relwidth=0.4, relheight=0.4, anchor="center")
        else:
            ctk.CTkLabel(preview_frame, text=f"{layout_count}\nkép", font=ctk.CTkFont(size=16, weight="bold"), text_color=self.colors['green_box']).place(relx=0.5, rely=0.5, anchor="center")

    def show_page_selection(self, is_new_project=False):
        if is_new_project: self._reset_project_state()
        self.selected_layout_card = None 
        self.clear_window()
        main_frame = ctk.CTkFrame(self.root, fg_color=self.colors['bg_primary'], corner_radius=0)
        main_frame.pack(fill="both", expand=True)
        ctk.CTkLabel(main_frame, text="Válassz egy kiinduló elrendezést", font=ctk.CTkFont(size=32, weight="bold"), text_color="white").pack(pady=(50, 40))
        layout_frame = ctk.CTkFrame(main_frame, fg_color="transparent"); layout_frame.pack(expand=True)
        cards_frame = ctk.CTkFrame(layout_frame, fg_color="transparent"); cards_frame.pack()
        layouts = [{"name": "1 kép", "value": 1}, {"name": "2 kép", "value": 2}, {"name": "4 kép", "value": 4}]
        self.layout_cards = []
        for i, layout in enumerate(layouts):
            card = ctk.CTkFrame(cards_frame, width=220, height=180, fg_color=self.colors['card_bg'], corner_radius=20)
            card.grid(row=0, column=i, padx=25, pady=20); card.pack_propagate(False)
            name_label = ctk.CTkLabel(card, text=layout["name"], font=ctk.CTkFont(size=16, weight="bold"), text_color=self.colors['text_primary'])
            name_label.pack(pady=(0, 15))
            def make_click_handler(value, card_widget): return lambda e: self.select_layout(value, card_widget)
            click_handler = make_click_handler(layout["value"], card)
            card.bind("<Button-1>", click_handler); name_label.bind("<Button-1>", click_handler)
            self.create_layout_preview(card, layout["value"], click_handler)
            self.layout_cards.append(card)
        self.custom_card = ctk.CTkFrame(layout_frame, fg_color=self.colors['card_bg'], corner_radius=20); self.custom_card.pack(pady=20)
        custom_title = ctk.CTkLabel(self.custom_card, text="Egyéni mennyiség", font=ctk.CTkFont(size=18, weight="bold"), text_color=self.colors['text_primary'])
        custom_title.pack(pady=(15, 10), padx=20)
        count_frame = ctk.CTkFrame(self.custom_card, fg_color="transparent"); count_frame.pack(pady=10)
        ctk.CTkButton(count_frame, text="−", width=30, height=30, command=self.decrease_custom_count).pack(side="left", padx=10)
        self.custom_count_label = ctk.CTkLabel(self.custom_card, text=str(self.custom_image_count), font=ctk.CTkFont(size=16, weight="bold"), width=40)
        self.custom_count_label.pack(side="left", in_=count_frame)
        ctk.CTkButton(count_frame, text="+", width=30, height=30, command=self.increase_custom_count).pack(side="left", padx=10)
        self.custom_preview_frame = ctk.CTkFrame(self.custom_card, fg_color="transparent"); self.custom_preview_frame.pack(pady=15)
        self.update_custom_preview()
        self.custom_card.bind("<Button-1>", lambda e: self.select_custom_layout())
        ctk.CTkButton(main_frame, text="🔧 Tovább a szerkesztőbe", command=self.proceed_to_editor, height=50, font=ctk.CTkFont(size=16, weight="bold")).pack(pady=40)

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
        """Legenerálja a képkeretek alapértelmezett pozícióit és méreteit."""
        geometries = []
        if count == 1:
            geometries.append({'path': None, 'relx': 0.05, 'rely': 0.05, 'relwidth': 0.9, 'relheight': 0.9})
        elif count == 2:
            geometries.append({'path': None, 'relx': 0.05, 'rely': 0.1, 'relwidth': 0.42, 'relheight': 0.8})
            geometries.append({'path': None, 'relx': 0.53, 'rely': 0.1, 'relwidth': 0.42, 'relheight': 0.8})
        elif count == 4:
            geometries.append({'path': None, 'relx': 0.05, 'rely': 0.05, 'relwidth': 0.42, 'relheight': 0.42})
            geometries.append({'path': None, 'relx': 0.53, 'rely': 0.05, 'relwidth': 0.42, 'relheight': 0.42})
            geometries.append({'path': None, 'relx': 0.05, 'rely': 0.53, 'relwidth': 0.42, 'relheight': 0.42})
            geometries.append({'path': None, 'relx': 0.53, 'rely': 0.53, 'relwidth': 0.42, 'relheight': 0.42})
        else:
            for i in range(count):
                geometries.append({'path': None, 'relx': 0.1 + (i*0.05), 'rely': 0.1 + (i*0.05), 'relwidth': 0.3, 'relheight': 0.4})
        return geometries

    def proceed_to_editor(self):
        if not self.selected_layout_card:
            messagebox.showwarning("Figyelem", "Kérjük válassz egy oldalelrendezést!"); return
        if not self.pages:
            new_page = {'photos': self._generate_layout_template(self.current_layout), 'texts': []}
            self.pages.append(new_page); self.current_page = 0
        else:
            # Csak a 'photos' részt cseréljük, a többi adat (háttér, szöveg) megmarad
            self.pages[self.current_page]['photos'] = self._generate_layout_template(self.current_layout)
        self.show_photo_editor()

    def show_photo_editor(self):
        self.clear_window()
        main_frame = ctk.CTkFrame(self.root, fg_color=self.colors['bg_primary'], corner_radius=0)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        if not self.pages or self.current_page >= len(self.pages):
            self.create_main_menu(); messagebox.showerror("Hiba", "Nem található a projekt oldal."); return
        current_page_data = self.pages[self.current_page]
        title_text = f"Fotókönyv szerkesztő - Oldal {self.current_page + 1} ({len(current_page_data.get('photos',[]))} képes)"
        ctk.CTkLabel(main_frame, text=title_text, font=ctk.CTkFont(size=28, weight="bold"), text_color="white").pack(pady=(10, 20))
        toolbar = ctk.CTkFrame(main_frame, height=70, fg_color=self.colors['card_bg'], corner_radius=15)
        toolbar.pack(side="bottom", fill="x", pady=(20, 0)); toolbar.pack_propagate(False)
        toolbar_buttons = [("💾 Mentés", self.save_project), ("📁 Betöltés", self.load_project), ("📤 Exportálás", self.export_project), ("🏠 Főmenü", self.create_main_menu)]
        buttons_frame = ctk.CTkFrame(toolbar, fg_color="transparent"); buttons_frame.pack(expand=True)
        for text, command in toolbar_buttons:
            ctk.CTkButton(buttons_frame, text=text, command=command, width=140, height=40, font=ctk.CTkFont(size=12), corner_radius=10, fg_color=self.colors['button_bg'], text_color=self.colors['text_secondary'], hover_color='#F0F0F0').pack(side="left", padx=10, pady=15)
        workspace = ctk.CTkFrame(main_frame, fg_color="transparent"); workspace.pack(fill="both", expand=True)
        left_panel = ctk.CTkFrame(workspace, width=220, fg_color=self.colors['card_bg'], corner_radius=20)
        left_panel.pack(side="left", fill="y", padx=(0, 15)); left_panel.pack_propagate(False)
        ctk.CTkLabel(left_panel, text="Oldalak", font=ctk.CTkFont(size=18, weight="bold"), text_color=self.colors['text_primary']).pack(pady=(20, 15))
        pages_scroll = ctk.CTkScrollableFrame(left_panel, fg_color="transparent")
        pages_scroll.pack(expand=True, fill="both", pady=10, padx=10)
        for i, page in enumerate(self.pages):
            page_frame = ctk.CTkFrame(pages_scroll, height=90, fg_color=self.colors['accent'] if i == self.current_page else self.colors['bg_secondary'], corner_radius=15)
            page_frame.pack(pady=5, fill="x"); page_frame.pack_propagate(False)
            page_label = ctk.CTkLabel(page_frame, text=f"{i + 1}. oldal\n({len(page.get('photos',[]))} kép)", font=ctk.CTkFont(size=11), text_color="white")
            page_label.pack(expand=True)
            page_frame.bind("<Button-1>", lambda e, idx=i: self.select_page(idx)); page_label.bind("<Button-1>", lambda e, idx=i: self.select_page(idx))
        ctk.CTkButton(left_panel, text="+ Új oldal", command=self.add_new_page, height=40, font=ctk.CTkFont(size=14, weight="bold"), corner_radius=15, fg_color=self.colors['accent'], hover_color='#8A9654').pack(pady=15, padx=10, fill="x")
        
        # JAVÍTÁS: Görgethetővé tett jobb panel
        right_panel = ctk.CTkFrame(workspace, width=260, fg_color=self.colors['card_bg'], corner_radius=20)
        right_panel.pack(side="right", fill="y", padx=(0,0)); right_panel.pack_propagate(False)
        ctk.CTkLabel(right_panel, text="Eszközök", font=ctk.CTkFont(size=18, weight="bold"), text_color=self.colors['text_primary']).pack(pady=(10, 5))

        tools_scroll_area = ctk.CTkScrollableFrame(right_panel, fg_color="transparent")
        tools_scroll_area.pack(fill="both", expand=True, padx=5, pady=5)

        slider_frame = ctk.CTkFrame(tools_scroll_area, fg_color="transparent")
        slider_frame.pack(pady=5, fill="x", padx=10)
        
        ctk.CTkLabel(slider_frame, text="Kép nagyítása", font=ctk.CTkFont(size=12)).pack()
        self.zoom_slider = ctk.CTkSlider(slider_frame, from_=1.0, to=3.0, command=self._update_photo_properties)
        self.zoom_slider.pack(fill="x", padx=5, pady=(0, 10))
        
        ctk.CTkLabel(slider_frame, text="Vízszintes pozíció", font=ctk.CTkFont(size=12)).pack()
        self.pan_x_slider = ctk.CTkSlider(slider_frame, from_=0.0, to=1.0, command=self._update_photo_properties)
        self.pan_x_slider.pack(fill="x", padx=5, pady=(0, 10))
        
        ctk.CTkLabel(slider_frame, text="Függőleges pozíció", font=ctk.CTkFont(size=12)).pack()
        self.pan_y_slider = ctk.CTkSlider(slider_frame, from_=0.0, to=1.0, command=self._update_photo_properties)
        self.pan_y_slider.pack(fill="x", padx=5, pady=(0, 10))
        
        ctk.CTkLabel(slider_frame, text="Szélesség", font=ctk.CTkFont(size=12)).pack()
        self.width_slider = ctk.CTkSlider(slider_frame, from_=0.1, to=1.0, command=self._update_photo_size_from_sliders)
        self.width_slider.pack(fill="x", padx=5, pady=(0, 10))

        ctk.CTkLabel(slider_frame, text="Magasság", font=ctk.CTkFont(size=12)).pack()
        self.height_slider = ctk.CTkSlider(slider_frame, from_=0.1, to=1.0, command=self._update_photo_size_from_sliders)
        self.height_slider.pack(fill="x", padx=5, pady=(0, 10))

        tools_frame = ctk.CTkFrame(tools_scroll_area, fg_color="transparent")
        tools_frame.pack(pady=5, fill="x", padx=10)
        
        # ÚJ: "Elrendezés váltása" gomb hozzáadva
        tools = [
            ("🎨 Háttér", self.set_background), 
            ("📝 Szöveg", self.add_text), 
            ("🖼️ Képkeret", self.add_frame), 
            ("🖼️ Oldalkerete", self.add_page_frame),
            ("🔄 Elrendezés váltása", self.change_current_page_layout),
            ("🖼️+ Kép hozzáadása", self._add_photo_placeholder), 
            ("🖼️- Kép törlése", self._delete_photo_placeholder), 
            ("🗑️ Oldal törlése", self.delete_page)
        ]
        for text, command in tools:
            ctk.CTkButton(tools_frame, text=text, command=command, height=35, font=ctk.CTkFont(size=12), corner_radius=10, fg_color=self.colors['button_bg'], text_color=self.colors['text_secondary'], hover_color='#F0F0F0').pack(pady=3, fill="x")
        
        self.center_panel = ctk.CTkFrame(workspace, fg_color=current_page_data.get('background') or self.colors['card_bg'], corner_radius=20)
        self.center_panel.pack(side="left", fill="both", expand=True, padx=15)
        self.center_panel.bind("<Button-1>", lambda e: self._deselect_all())
        
        page_frame_path = current_page_data.get('page_frame_path')
        padding = 0
        if page_frame_path:
            self.center_panel.update_idletasks()
            w, h = self.center_panel.winfo_width(), self.center_panel.winfo_height()
            if w > 1 and h > 1:
                padding = int(min(w, h) * 0.05)
                frame_img = None
                if page_frame_path.startswith('preset_'): frame_img = self._create_preset_frame(page_frame_path, (w, h))
                elif os.path.exists(page_frame_path): frame_img = Image.open(page_frame_path)
                if frame_img:
                    page_frame_ctk_img = ctk.CTkImage(light_image=frame_img.resize((w,h), Image.LANCZOS), dark_image=frame_img.resize((w,h), Image.LANCZOS), size=(w,h))
                    page_frame_label = ctk.CTkLabel(self.center_panel, image=page_frame_ctk_img, text="")
                    page_frame_label.place(x=0, y=0, relwidth=1, relheight=1)
        
        photo_container_parent = ctk.CTkFrame(self.center_panel, fg_color="transparent")
        photo_container_parent.pack(fill="both", expand=True, padx=padding, pady=padding)

        self.create_photo_layout(photo_container_parent)
        self._render_text_boxes(self.center_panel)
        self._deselect_all()

    # --- FOTÓ ÉS KERET KEZELŐ METÓDUSOK ---

    def create_photo_layout(self, parent_frame):
        for frame in self.photo_frames: frame.destroy()
        self.photo_frames.clear()
        photos_data = self.pages[self.current_page].get('photos', [])
        for i, photo_data in enumerate(photos_data):
            photo_frame = ctk.CTkFrame(parent_frame, fg_color="#CCCCCC", corner_radius=10, border_width=0)
            photo_frame.place(relx=photo_data['relx'], rely=photo_data['rely'], relwidth=photo_data['relwidth'], relheight=photo_data['relheight'])
            
            photo_frame.bind("<ButtonPress-1>", lambda e, index=i: self._on_widget_press(e, 'photo', index))
            photo_frame.bind("<B1-Motion>", lambda e: self._on_widget_drag(e))
            photo_frame.bind("<ButtonRelease-1>", lambda e: self._on_widget_release(e))

            self.photo_frames.append(photo_frame)
            self.display_photo_placeholder(photo_frame, photo_data, i, is_update=False)

    def display_photo_placeholder(self, parent_frame, photo_data, photo_index, is_update=False):
        if not is_update:
            for widget in parent_frame.winfo_children(): widget.destroy()
        
        photo_path = photo_data['path']
        if not photo_path or not os.path.exists(photo_path):
            add_btn = ctk.CTkButton(parent_frame, text="+", font=ctk.CTkFont(size=24), fg_color=self.colors['accent'], hover_color='#8A9654', command=lambda idx=photo_index: self.add_photo_to_slot(idx))
            add_btn.place(relx=0.5, rely=0.5, anchor="center")
            return

        try:
            key = (self.current_page, photo_index)
            props = self.photo_properties.get(key, {})
            parent_frame.update_idletasks()
            frame_w, frame_h = parent_frame.winfo_width(), parent_frame.winfo_height()
            if frame_w <= 1 or frame_h <= 1: return
            
            original_img = Image.open(photo_path).convert("RGBA")
            img_ratio = original_img.width / original_img.height; frame_ratio = frame_w / frame_h
            zoom = props.get('zoom', 1.0); pan_x = props.get('pan_x', 0.5); pan_y = props.get('pan_y', 0.5)
            
            if img_ratio > frame_ratio: new_h, new_w = int(frame_h * zoom), int(frame_h * zoom * img_ratio)
            else: new_w, new_h = int(frame_w * zoom), int(frame_w * zoom / img_ratio)
            
            if new_w < 1 or new_h < 1: new_w, new_h = frame_w, frame_h
            zoomed_img = original_img.resize((new_w, new_h), Image.LANCZOS)
            
            extra_w, extra_h = max(0, zoomed_img.width - frame_w), max(0, zoomed_img.height - frame_h)
            crop_x, crop_y = int(extra_w * pan_x), int(extra_h * pan_y)
            cropped_photo = zoomed_img.crop((crop_x, crop_y, crop_x + frame_w, crop_y + frame_h))
            final_image = cropped_photo
            
            frame_path = props.get('frame_path')
            if frame_path:
                frame_img = None
                if frame_path.startswith('preset_'): frame_img = self._create_preset_frame(frame_path, (frame_w, frame_h))
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

    def _create_preset_frame(self, preset_name, size):
        width, height = size
        frame_thickness = int(min(width, height) * 0.05)
        if frame_thickness < 1: frame_thickness = 1
        color_map = {'preset_black': (0, 0, 0, 200), 'preset_white': (255, 255, 255, 200), 'preset_gold': (212, 175, 55, 220)}
        color = color_map.get(preset_name, (0,0,0,0))
        frame_image = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(frame_image)
        for i in range(frame_thickness):
            draw.rectangle((i, i, width - 1 - i, height - 1 - i), outline=color, width=1)
        return frame_image

    def add_photo_to_slot(self, photo_index):
        filename = filedialog.askopenfilename(title="Válassz fotót", filetypes=[("Képfájlok", "*.jpg *.jpeg *.png *.gif *.bmp")])
        if filename:
            self.pages[self.current_page]['photos'][photo_index]['path'] = filename
            if filename not in self.uploaded_photos: self.uploaded_photos.append(filename)
            self.show_photo_editor()

    def _add_photo_placeholder(self):
        new_photo = {'path': None, 'relx': 0.35, 'rely': 0.3, 'relwidth': 0.3, 'relheight': 0.4}
        self.pages[self.current_page]['photos'].append(new_photo)
        self.show_photo_editor()

    def _delete_photo_placeholder(self):
        if self.selected_photo_index is None:
            messagebox.showwarning("Törlés", "Nincs képkeret kiválasztva a törléshez.")
            return
        self.pages[self.current_page]['photos'].pop(self.selected_photo_index)
        self._deselect_all()
        self.show_photo_editor()

    def add_frame(self):
        if self.selected_photo_index is None:
            messagebox.showwarning("Nincs kiválasztott kép", "Kérlek, először kattints egy képre a szerkesztéshez!")
            return
        if self.frame_editor_window is not None and self.frame_editor_window.winfo_exists():
            self.frame_editor_window.focus(); return
        self.frame_editor_window = ctk.CTkToplevel(self.root)
        self.frame_editor_window.title("Képkeret szerkesztése"); self.frame_editor_window.geometry("300x480")
        self.frame_editor_window.transient(self.root); self.frame_editor_window.attributes("-topmost", True)
        ctk.CTkLabel(self.frame_editor_window, text="Beépített keretek", font=ctk.CTkFont(weight="bold")).pack(pady=(15, 5))
        preset_frame_ui = ctk.CTkFrame(self.frame_editor_window); preset_frame_ui.pack(pady=5, padx=10, fill="x")
        presets = [("Fekete", "preset_black"), ("Fehér", "preset_white"), ("Arany", "preset_gold")]
        for i, (name, path) in enumerate(presets):
            ctk.CTkButton(preset_frame_ui, text=name, command=lambda p=path: self._apply_frame(p)).grid(row=0, column=i, padx=5, pady=5, sticky="ew")
        preset_frame_ui.grid_columnconfigure((0,1,2), weight=1)
        ctk.CTkButton(self.frame_editor_window, text="Saját keret feltöltése...", command=lambda: self._apply_frame(self._upload_custom_frame_path())).pack(pady=(10, 5), padx=10, fill="x")
        ctk.CTkLabel(self.frame_editor_window, text="Beállítások", font=ctk.CTkFont(weight="bold")).pack(pady=(15, 5))
        self.slider_panel = ctk.CTkFrame(self.frame_editor_window); self.slider_panel.pack(pady=5, padx=10, fill="x")
        ctk.CTkLabel(self.slider_panel, text="Méret").pack()
        self.frame_scale_slider = ctk.CTkSlider(self.slider_panel, from_=0.5, to=1.5, command=self._update_photo_properties); self.frame_scale_slider.pack(fill="x", padx=10, pady=(0,10))
        ctk.CTkLabel(self.slider_panel, text="Vízszintes eltolás").pack()
        self.frame_offset_x_slider = ctk.CTkSlider(self.slider_panel, from_=-100, to=100, number_of_steps=200, command=self._update_photo_properties); self.frame_offset_x_slider.pack(fill="x", padx=10, pady=(0,10))
        ctk.CTkLabel(self.slider_panel, text="Függőleges eltolás").pack()
        self.frame_offset_y_slider = ctk.CTkSlider(self.slider_panel, from_=-100, to=100, number_of_steps=200, command=self._update_photo_properties); self.frame_offset_y_slider.pack(fill="x", padx=10, pady=(0,10))
        ctk.CTkButton(self.frame_editor_window, text="Keret eltávolítása", fg_color="#D32F2F", hover_color="#B71C1C", command=lambda: self._apply_frame(None)).pack(pady=10, padx=10, fill="x")
        self.update_frame_editor_ui()

    def _apply_frame(self, frame_path):
        if self.selected_photo_index is None: return
        key = (self.current_page, self.selected_photo_index)
        if key not in self.photo_properties: self.photo_properties[key] = {}
        self.photo_properties[key]['frame_path'] = frame_path
        self.photo_properties[key]['frame_scale'] = 1.0; self.photo_properties[key]['frame_offset_x'] = 0; self.photo_properties[key]['frame_offset_y'] = 0
        if self.frame_editor_window and self.frame_editor_window.winfo_exists(): self.update_frame_editor_ui()
        self._update_photo_properties()

    def update_frame_editor_ui(self):
        if not (self.frame_editor_window and self.frame_editor_window.winfo_exists()): return
        key = (self.current_page, self.selected_photo_index)
        props = self.photo_properties.get(key, {})
        sliders = [self.frame_scale_slider, self.frame_offset_x_slider, self.frame_offset_y_slider]
        if self.selected_photo_index is not None and props.get('frame_path'):
            for slider in sliders: slider.configure(state="normal")
            self.frame_scale_slider.set(props.get('frame_scale', 1.0))
            self.frame_offset_x_slider.set(props.get('frame_offset_x', 0))
            self.frame_offset_y_slider.set(props.get('frame_offset_y', 0))
        else:
            for slider in sliders: slider.configure(state="disabled")
            self.frame_scale_slider.set(1.0); self.frame_offset_x_slider.set(0); self.frame_offset_y_slider.set(0)
            
    def add_page_frame(self):
        window = ctk.CTkToplevel(self.root)
        window.title("Oldal keretének kiválasztása"); window.geometry("280x200")
        window.transient(self.root); window.grab_set()
        def _select_page_frame(path):
            if path is not None: self.pages[self.current_page]['page_frame_path'] = path
            else: self.pages[self.current_page].pop('page_frame_path', None)
            window.destroy()
            self.show_photo_editor()
        ctk.CTkLabel(window, text="Válassz keretet az oldalhoz!", font=ctk.CTkFont(weight="bold")).pack(pady=10)
        preset_frame_ui = ctk.CTkFrame(window); preset_frame_ui.pack(pady=5, padx=10, fill="x")
        presets = [("Fekete", "preset_black"), ("Fehér", "preset_white"), ("Arany", "preset_gold")]
        for i, (name, path) in enumerate(presets):
            ctk.CTkButton(preset_frame_ui, text=name, command=lambda p=path: _select_page_frame(p)).grid(row=0, column=i, padx=5, pady=5, sticky="ew")
        preset_frame_ui.grid_columnconfigure((0,1,2), weight=1)
        ctk.CTkButton(window, text="Saját keret feltöltése...", command=lambda: _select_page_frame(self._upload_custom_frame_path())).pack(pady=5, padx=10, fill="x")
        ctk.CTkButton(window, text="Keret eltávolítása", fg_color="#D32F2F", hover_color="#B71C1C", command=lambda: _select_page_frame(None)).pack(pady=5, padx=10, fill="x")
    
    def _upload_custom_frame_path(self):
        return filedialog.askopenfilename(title="Válassz egy keret képet", filetypes=[("PNG képek", "*.png")]) or None
    
    # --- OLDALNAVIGÁCIÓ ÉS EGYÉB FUNKCIÓK ---

    def select_page(self, page_idx):
        if 0 <= page_idx < len(self.pages):
            self.current_page = page_idx
            self.show_photo_editor()

    def add_new_page(self):
        self.pages.append({'photos': self._generate_layout_template(1), 'texts': []})
        self.current_page = len(self.pages) - 1
        self.show_photo_editor()

    def delete_page(self):
        if len(self.pages) > 1:
            if messagebox.askyesno("Oldal törlése", f"Biztosan törölni szeretnéd a(z) {self.current_page + 1}. oldalt?"):
                self._deselect_all()
                del self.pages[self.current_page]
                if self.current_page >= len(self.pages): self.current_page = len(self.pages) - 1
                self.show_photo_editor()
        else: messagebox.showwarning("Utolsó oldal", "Nem törölheted az utolsó oldalt!")
    
    def change_current_page_layout(self):
        """Lehetővé teszi a jelenlegi oldal elrendezésének megváltoztatását."""
        self.show_page_selection(is_new_project=False)

    def set_background(self):
        color_picker = ctk.CTkToplevel(self.root)
        color_picker.title("Háttérszín választása"); color_picker.geometry("320x320")
        color_picker.transient(self.root); color_picker.grab_set()
        def _apply_background_color(color):
            if color is None or (isinstance(color, str) and re.search(r'^#(?:[0-9a-fA-F]{3}){1,2}$', color)):
                self.pages[self.current_page]['background'] = color
                color_picker.destroy()
                self.show_photo_editor()
            else: messagebox.showerror("Érvénytelen színkód", f"A megadott kód ('{color}') nem érvényes.", parent=color_picker)
        ctk.CTkLabel(color_picker, text="Válassz egy színt a palettáról:", font=ctk.CTkFont(size=14)).pack(pady=(15, 5))
        palette_frame = ctk.CTkFrame(color_picker, fg_color="transparent"); palette_frame.pack(pady=5, padx=10)
        colors_list = ['#FFFFFF', '#F0F0F0', '#D3E3F1', '#D1F0D1', '#F5E6D3', '#E6D3F5', '#FFDDC1', '#FFD1D1']
        for i, color in enumerate(colors_list):
            ctk.CTkButton(palette_frame, text="", fg_color=color, width=40, height=40, corner_radius=8, command=lambda c=color: _apply_background_color(c)).grid(row=i // 4, column=i % 4, padx=10, pady=10)
        ctk.CTkLabel(color_picker, text="Vagy adj meg egyéni színt:", font=ctk.CTkFont(size=14)).pack(pady=(15, 5))
        custom_color_frame = ctk.CTkFrame(color_picker, fg_color="transparent"); custom_color_frame.pack(pady=5, padx=20, fill="x")
        custom_color_entry = ctk.CTkEntry(custom_color_frame, placeholder_text="#RRGGBB"); custom_color_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(custom_color_frame, text="Alkalmaz", width=80, command=lambda: _apply_background_color(custom_color_entry.get())).pack(side="left")
        ctk.CTkButton(color_picker, text="Háttér eltávolítása", command=lambda: _apply_background_color(None)).pack(pady=15)

    def save_project(self): messagebox.showinfo("Fejlesztés alatt", "Ez a funkció még nem elérhető.")
    def load_project(self): messagebox.showinfo("Fejlesztés alatt", "Ez a funkció még nem elérhető.")
    def export_project(self): messagebox.showinfo("Fejlesztés alatt", "Ez a funkció még nem elérhető.")
    
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
        self._render_text_boxes(self.center_panel)
        self._select_text(len(self.pages[self.current_page]['texts']) - 1)

    def _delete_selected_text(self):
        if self.selected_text_index is not None:
            text_index_to_delete = self.selected_text_index
            self._deselect_all()
            
            del self.pages[self.current_page]['texts'][text_index_to_delete]
            self._render_text_boxes(self.center_panel)
            self.update_text_editor_ui()
    
    def _render_text_boxes(self, parent):
        for widget in self.text_widgets: widget.destroy()
        self.text_widgets.clear()
        if 'texts' not in self.pages[self.current_page]: return
        for i, text_data in enumerate(self.pages[self.current_page]['texts']):
            font_style_parts = []
            style = text_data.get('font_style', 'normal')
            if 'bold' in style: font_style_parts.append('bold')
            if 'italic' in style: font_style_parts.append('italic')
            style_string = " ".join(font_style_parts) if font_style_parts else "normal"
            font_tuple = (text_data.get('font_family', 'Arial'), text_data.get('font_size', 12), style_string)
            
            container = ctk.CTkFrame(parent, fg_color="transparent")
            label = ctk.CTkLabel(container, text=text_data['text'], font=font_tuple, text_color=text_data.get('font_color', '#000000'), fg_color="transparent")
            label.pack(padx=2, pady=2)
            container.place(relx=text_data['relx'], rely=text_data['rely'], anchor="center")

            container.bind("<ButtonPress-1>", lambda e, index=i: self._on_widget_press(e, 'text', index))
            container.bind("<B1-Motion>", lambda e: self._on_widget_drag(e))
            container.bind("<ButtonRelease-1>", lambda e: self._on_widget_release(e))
            label.bind("<ButtonPress-1>", lambda e, index=i: self._on_widget_press(e, 'text', index))
            label.bind("<B1-Motion>", lambda e: self._on_widget_drag(e))
            label.bind("<ButtonRelease-1>", lambda e: self._on_widget_release(e))

            self.text_widgets.append(container)
            container.lift()

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
            
            self._render_text_boxes(self.center_panel)
            if self.selected_text_index is not None and self.selected_text_index < len(self.text_widgets):
                self._select_text(self.selected_text_index)
        except (AttributeError, IndexError, ValueError): 
            pass

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
        current_color = self.pages[self.current_page]['texts'][self.selected_text_index]['font_color']
        color_code = colorchooser.askcolor(title="Válassz színt", initialcolor=current_color)
        if color_code and color_code[1]:
            self.pages[self.current_page]['texts'][self.selected_text_index]['font_color'] = color_code[1]
            self._update_text_properties()

    # --- MOZGATÁS METÓDUSAI ---
    
    def _on_widget_press(self, event, item_type, index):
        """Előkészíti a widgetet (kép vagy szöveg) a mozgatásra."""
        if item_type == 'photo':
            self._select_photo(index)
            widget = self.photo_frames[index]
        elif item_type == 'text':
            self._select_text(index)
            widget = self.text_widgets[index]
        else:
            return
        
        widget.lift()
        self._drag_data = {
            "widget": widget,
            "item_type": item_type,
            "index": index,
            "offset_x": event.x,
            "offset_y": event.y,
        }

    def _on_widget_drag(self, event):
        """Mozgatja a kiválasztott widgetet az egérrel."""
        if not self._drag_data: return

        widget = self._drag_data["widget"]
        parent = widget.master
        
        new_x = parent.winfo_pointerx() - parent.winfo_rootx() - self._drag_data["offset_x"]
        new_y = parent.winfo_pointery() - parent.winfo_rooty() - self._drag_data["offset_y"]
        
        widget.place(x=new_x, y=new_y)

    def _on_widget_release(self, event):
        """Befejezi a mozgatást és elmenti az új relatív koordinátákat."""
        if not self._drag_data: return

        widget = self._drag_data["widget"]
        item_type = self._drag_data["item_type"]
        index = self._drag_data["index"]
        parent = self.center_panel if item_type == 'text' else widget.master
        
        parent_w, parent_h = parent.winfo_width(), parent.winfo_height()
        if parent_w == 0 or parent_h == 0: 
            self._drag_data = {}
            return

        widget_x, widget_y = widget.winfo_x(), widget.winfo_y()
        
        if item_type == 'photo':
            data_list = self.pages[self.current_page]['photos']
            data_list[index]['relx'] = widget_x / parent_w
            data_list[index]['rely'] = widget_y / parent_h
        elif item_type == 'text':
            data_list = self.pages[self.current_page]['texts']
            widget_w, widget_h = widget.winfo_width(), widget.winfo_height()
            data_list[index]['relx'] = (widget_x + widget_w / 2) / parent_w
            data_list[index]['rely'] = (widget_y + widget_h / 2) / parent_h

        self._drag_data = {}

    def run(self):
        """Elindítja az alkalmazás fő ciklusát."""
        self.root.mainloop()

def main():
    """A program belépési pontja."""
    app = FotokonyvGUI()
    app.run()

if __name__ == "__main__":
    main()
