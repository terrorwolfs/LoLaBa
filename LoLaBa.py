import customtkinter as ctk
from tkinter import messagebox, filedialog, colorchooser, Canvas
import os
from PIL import Image, ImageDraw, ImageTk, ImageFont, ImageEnhance
import traceback
import json
import copy # Szükséges a mentéshez

# --- Alapbeállítások ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class FotokonyvGUI:
    """A fotókönyv-szerkesztő alkalmazás fő grafikus felületét (GUI) kezelő osztály."""

    EXPORT_RESOLUTION = (2480, 3508)

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
        
        self.editor_ui_built = False
        self.main_editor_frame = None
        self.left_panel_scroll = None
        self.title_label = None
        
        # Canvas-alapú rendereléshez szükséges attribútumok
        self.canvas = None
        self.canvas_bg_item = None
        self.canvas_page_frame_item = None
        self.bg_photo_image = None # Fontos a kép referencia megtartásához
        self.page_frame_photo_image = None # Fontos a kép referencia megtartásához
        self.widget_to_canvas_item = {}

        self.frame_editor_window = None
        self.text_editor_window = None
        self._reset_project_state()
        self.create_main_menu()

    # --- BELSŐ MŰKÖDÉST SEGÍTŐ METÓDUSOK ---
    def _reset_project_state(self):
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
        self.editor_ui_built = False
        self.widget_to_canvas_item = {}
        
        if self.frame_editor_window and self.frame_editor_window.winfo_exists(): self.frame_editor_window.destroy()
        self.frame_editor_window = None
        if self.text_editor_window and self.text_editor_window.winfo_exists(): self.text_editor_window.destroy()
        self.text_editor_window = None

    def _select_photo(self, photo_index):
        self._deselect_all()
        self.selected_photo_index = photo_index

        if self.selected_photo_index is not None and self.selected_photo_index < len(self.photo_frames):
            selected_frame = self.photo_frames[self.selected_photo_index]
            selected_frame.configure(border_width=3, border_color=self.colors['selected_photo_border'])
            self.canvas.tag_raise(self.widget_to_canvas_item[selected_frame])
            
            props_key = str((self.current_page, photo_index))
            props = self.photo_properties.get(props_key, {})
            photo_data = self.pages[self.current_page]['photos'][photo_index]

            widgets_to_enable = [
                self.zoom_slider, self.pan_x_slider, self.pan_y_slider,
                self.width_slider, self.height_slider,
                self.brightness_slider, self.contrast_slider, self.saturation_slider,
                self.grayscale_checkbox
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

            if self.frame_editor_window and self.frame_editor_window.winfo_exists():
                self.update_frame_editor_ui()

    def _select_text(self, text_index):
        self._deselect_all()
        self.selected_text_index = text_index
        if self.selected_text_index < len(self.text_widgets):
            text_widget_container = self.text_widgets[self.selected_text_index]
            text_label = text_widget_container.winfo_children()[0]
            text_label.configure(text_color=self.colors['selected_text_color'])
            self.canvas.tag_raise(self.widget_to_canvas_item[text_widget_container])
        if self.text_editor_window and self.text_editor_window.winfo_exists():
            self.update_text_editor_ui()

    def _deselect_all(self):
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
            widgets_to_disable = [
                self.zoom_slider, self.pan_x_slider, self.pan_y_slider,
                self.width_slider, self.height_slider,
                self.brightness_slider, self.contrast_slider, self.saturation_slider,
                self.grayscale_checkbox
            ]
            for widget in widgets_to_disable:
                widget.configure(state="disabled")

        if self.frame_editor_window and self.frame_editor_window.winfo_exists(): self.update_frame_editor_ui()
        if self.text_editor_window and self.text_editor_window.winfo_exists(): self.update_text_editor_ui()

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

    def _update_photo_size_from_sliders(self, value=None):
        if self.selected_photo_index is None: return
        
        photo_data = self.pages[self.current_page]['photos'][self.selected_photo_index]
        photo_frame = self.photo_frames[self.selected_photo_index]
        
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        
        new_relwidth = self.width_slider.get()
        new_relheight = self.height_slider.get()
        photo_data['relwidth'] = new_relwidth
        photo_data['relheight'] = new_relheight
        
        canvas_item_id = self.widget_to_canvas_item.get(photo_frame)
        if canvas_item_id:
            self.canvas.itemconfig(canvas_item_id, width=int(new_relwidth * canvas_w), height=int(new_relheight * canvas_h))
            
        self.display_photo_placeholder(photo_frame, photo_data, self.selected_photo_index, is_update=True)
    
    # --- FELÜLETET ÉPÍTŐ METÓDUSOK ---
    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

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
        self.editor_ui_built = False
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
            self.pages[self.current_page]['photos'] = self._generate_layout_template(self.current_layout)
        
        if not self.editor_ui_built:
            self._build_editor_ui()
            self.editor_ui_built = True
        self.refresh_editor_view()

    def _build_editor_ui(self):
        self.clear_window()
        self.main_editor_frame = ctk.CTkFrame(self.root, fg_color=self.colors['bg_primary'], corner_radius=0)
        self.main_editor_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.title_label = ctk.CTkLabel(self.main_editor_frame, text="", font=ctk.CTkFont(size=28, weight="bold"), text_color="white")
        self.title_label.pack(pady=(10, 20))
        
        toolbar = ctk.CTkFrame(self.main_editor_frame, height=70, fg_color=self.colors['card_bg'], corner_radius=15)
        toolbar.pack(side="bottom", fill="x", pady=(20, 0))
        toolbar.pack_propagate(False)
        toolbar_buttons = [("💾 Mentés", self.save_project), ("📁 Betöltés", self.load_project), ("📤 Exportálás", self.export_project), ("🏠 Főmenü", self.create_main_menu)]
        buttons_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        buttons_frame.pack(expand=True)
        for text, command in toolbar_buttons:
            ctk.CTkButton(buttons_frame, text=text, command=command, width=140, height=40, font=ctk.CTkFont(size=12), corner_radius=10, fg_color=self.colors['button_bg'], text_color=self.colors['text_secondary'], hover_color='#F0F0F0').pack(side="left", padx=10, pady=15)
        
        workspace = ctk.CTkFrame(self.main_editor_frame, fg_color="transparent")
        workspace.pack(fill="both", expand=True)
        
        left_panel = ctk.CTkFrame(workspace, width=220, fg_color=self.colors['card_bg'], corner_radius=20)
        left_panel.pack(side="left", fill="y", padx=(0, 15))
        left_panel.pack_propagate(False)
        ctk.CTkLabel(left_panel, text="Oldalak", font=ctk.CTkFont(size=18, weight="bold"), text_color=self.colors['text_primary']).pack(pady=(20, 15))
        self.left_panel_scroll = ctk.CTkScrollableFrame(left_panel, fg_color="transparent")
        self.left_panel_scroll.pack(expand=True, fill="both", pady=10, padx=10)
        ctk.CTkButton(left_panel, text="+ Új oldal", command=self.add_new_page, height=40, font=ctk.CTkFont(size=14, weight="bold"), corner_radius=15, fg_color=self.colors['accent'], hover_color='#8A9654').pack(pady=15, padx=10, fill="x")
        
        right_panel = ctk.CTkFrame(workspace, width=260, fg_color=self.colors['card_bg'], corner_radius=20)
        right_panel.pack(side="right", fill="y", padx=(0,0))
        right_panel.pack_propagate(False)
        self._build_right_panel(right_panel)

        # A központi szerkesztőfelület most már egy Canvas, a stabilabb rétegkezelés érdekében.
        self.canvas = Canvas(workspace, bg=self.colors['card_bg'], highlightthickness=0, relief='ridge')
        self.canvas.pack(side="left", fill="both", expand=True, padx=15)

    def _build_right_panel(self, right_panel):
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
        
        effects_frame = ctk.CTkFrame(tools_scroll_area, fg_color="transparent")
        effects_frame.pack(pady=5, fill="x", padx=10)
        ctk.CTkLabel(effects_frame, text="Kép effektek", font=ctk.CTkFont(size=12, weight="bold")).pack()
        ctk.CTkLabel(effects_frame, text="Fényerő", font=ctk.CTkFont(size=12)).pack()
        self.brightness_slider = ctk.CTkSlider(effects_frame, from_=0.5, to=1.5, command=self._update_photo_properties)
        self.brightness_slider.pack(fill="x", padx=5, pady=(0, 10)); self.brightness_slider.set(1.0)
        ctk.CTkLabel(effects_frame, text="Kontraszt", font=ctk.CTkFont(size=12)).pack()
        self.contrast_slider = ctk.CTkSlider(effects_frame, from_=0.5, to=1.5, command=self._update_photo_properties)
        self.contrast_slider.pack(fill="x", padx=5, pady=(0, 10)); self.contrast_slider.set(1.0)
        ctk.CTkLabel(effects_frame, text="Színerősség", font=ctk.CTkFont(size=12)).pack()
        self.saturation_slider = ctk.CTkSlider(effects_frame, from_=0.0, to=2.0, command=self._update_photo_properties)
        self.saturation_slider.pack(fill="x", padx=5, pady=(0, 10)); self.saturation_slider.set(1.0)
        self.grayscale_checkbox = ctk.CTkCheckBox(effects_frame, text="Fekete-fehér", command=self._update_photo_properties)
        self.grayscale_checkbox.pack(pady=5)
        
        tools_frame = ctk.CTkFrame(tools_scroll_area, fg_color="transparent")
        tools_frame.pack(pady=5, fill="x", padx=10)
        tools = [
            ("🎨 Háttér (Szín/Kép)", self.set_background),
            ("🖼️ Háttérkép beállítása", self.set_background_image),
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
        
        # A Canvas miatt a renderelési sorrend megváltozik. Először mindent törlünk,
        # majd rétegenként újraépítjük.
        self._render_page_content()
        self._deselect_all()

    def _render_page_content(self):
        # Töröljük a canvas összes elemét
        self.canvas.delete("all")
        self.widget_to_canvas_item.clear()
        self.photo_frames.clear()
        self.text_widgets.clear()
        
        # 1. Háttér renderelése (legalacsonyabb réteg)
        self._render_background()
        
        # 2. Fotók renderelése a háttér fölé
        self.create_photo_layout()
        
        # 3. Szövegek renderelése a fotók fölé
        self._render_text_boxes()
        
        # 4. Oldalkeretet renderelése (legfelső réteg)
        self._render_page_frame()

    # --- ÚJ, CANVAS-ALAPÚ HÁTTÉRKEZELÉS ---
    def _render_background(self):
        self.canvas.update_idletasks()
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w <= 1 or h <= 1: return

        page_data = self.pages[self.current_page]
        bg_setting = page_data.get('background')

        # Előző háttérkép törlése
        if self.canvas_bg_item:
            self.canvas.delete(self.canvas_bg_item)
            self.canvas_bg_item = None
            self.bg_photo_image = None

        try:
            if isinstance(bg_setting, dict) and bg_setting.get('type') == 'image':
                img_path = bg_setting.get('path')
                if not img_path or not os.path.exists(img_path):
                    raise FileNotFoundError("A háttérkép nem található.")
                
                pil_image = Image.open(img_path).convert("RGBA").resize((w, h), Image.LANCZOS)
                # Kép referencia probléma megoldása: a referenciát az osztályszinten kell tárolni
                self.bg_photo_image = ImageTk.PhotoImage(pil_image)
                
                self.canvas_bg_item = self.canvas.create_image(0, 0, image=self.bg_photo_image, anchor="nw", tags="background")
                self.canvas.tag_lower("background") # Legalulra helyezzük
                self.canvas.configure(bg=self.colors['card_bg']) # Canvas alap színe
            else:
                bg_color = bg_setting if isinstance(bg_setting, str) and bg_setting.startswith('#') else self.colors['card_bg']
                self.canvas.configure(bg=bg_color)
        except Exception as e:
            print(f"HIBA a háttér renderelésekor: {e}")
            traceback.print_exc()
            self.canvas.configure(bg="red")
            
    def set_background_image(self):
        """Közvetlenül háttérképet választ, és beállítja az oldalhoz az új adatformátumban."""
        filename = filedialog.askopenfilename(
            title="Válassz háttérképet",
            filetypes=[("Képfájlok", "*.jpg *.jpeg *.png"), ("Minden fájl", "*.*")]
        )
        if filename:
            self.pages[self.current_page]['background'] = {'type': 'image', 'path': filename}
            self.refresh_editor_view()
    
    def set_background(self):
        """Megnyitja a háttérválasztó ablakot (szín, kép, törlés)."""
        color_picker = ctk.CTkToplevel(self.root)
        color_picker.title("Háttér beállítása"); color_picker.geometry("320x440")
        color_picker.transient(self.root); color_picker.grab_set()

        def _apply_background(setting):
            self.pages[self.current_page]['background'] = setting
            color_picker.destroy()
            self.refresh_editor_view()

        def _upload_background_image():
            filename = filedialog.askopenfilename(title="Válassz háttérképet", filetypes=[("Képfájlok", "*.jpg *.jpeg *.png"), ("Minden fájl", "*.*")])
            if filename:
                _apply_background({'type': 'image', 'path': filename})

        ctk.CTkLabel(color_picker, text="Válassz egy színt a palettáról:", font=ctk.CTkFont(size=14)).pack(pady=(15, 5))
        palette_frame = ctk.CTkFrame(color_picker, fg_color="transparent"); palette_frame.pack(pady=5, padx=10)
        colors_list = ['#FFFFFF', '#F0F0F0', '#D3E3F1', '#D1F0D1', '#F5E6D3', '#E6D3F5', '#FFDDC1', '#FFD1D1']
        for i, color in enumerate(colors_list):
            ctk.CTkButton(palette_frame, text="", fg_color=color, width=40, height=40, corner_radius=8, command=lambda c=color: _apply_background(c)).grid(row=i // 4, column=i % 4, padx=10, pady=10)
        
        ctk.CTkLabel(color_picker, text="Vagy adj meg egyéni színt:", font=ctk.CTkFont(size=14)).pack(pady=(10, 5))
        custom_color_frame = ctk.CTkFrame(color_picker, fg_color="transparent"); custom_color_frame.pack(pady=5, padx=20, fill="x")
        custom_color_entry = ctk.CTkEntry(custom_color_frame, placeholder_text="#RRGGBB"); custom_color_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(custom_color_frame, text="Alkalmaz", width=80, command=lambda: _apply_background(custom_color_entry.get())).pack(side="left")

        ctk.CTkLabel(color_picker, text="Vagy tölts fel saját képet:", font=ctk.CTkFont(size=14)).pack(pady=(15, 5))
        ctk.CTkButton(color_picker, text="🖼️ Háttérkép feltöltése...", command=_upload_background_image).pack(pady=5, padx=20, fill="x")
        
        ctk.CTkButton(color_picker, text="Háttér eltávolítása", command=lambda: _apply_background(None)).pack(pady=15, padx=20, fill="x")

    def _render_page_frame(self):
        self.canvas.update_idletasks()
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w <= 1 or h <= 1: return

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
                frame_img = self._create_preset_frame(page_frame_path, (w, h), thickness_ratio)
            elif os.path.exists(page_frame_path): 
                frame_img = Image.open(page_frame_path).convert("RGBA").resize((w, h), Image.LANCZOS)
            
            if frame_img:
                self.page_frame_photo_image = ImageTk.PhotoImage(frame_img)
                self.canvas_page_frame_item = self.canvas.create_image(0, 0, image=self.page_frame_photo_image, anchor="nw", tags="page_frame")
                self.canvas.tag_raise("page_frame") # Legfelülre helyezzük

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
        photos_data = self.pages[self.current_page].get('photos', [])
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w <= 1 or h <= 1: return
        
        for i, photo_data in enumerate(photos_data):
            photo_frame = ctk.CTkFrame(self.canvas, fg_color="#CCCCCC", corner_radius=10, border_width=0)
            
            abs_x = int(photo_data['relx'] * w)
            abs_y = int(photo_data['rely'] * h)
            frame_w = int(photo_data['relwidth'] * w)
            frame_h = int(photo_data['relheight'] * h)
            
            # Widget elhelyezése a canvason a create_window segítségével
            canvas_item_id = self.canvas.create_window(abs_x, abs_y, window=photo_frame, width=frame_w, height=frame_h, anchor='nw', tags="photo")
            self.widget_to_canvas_item[photo_frame] = canvas_item_id
            
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
            key = str((self.current_page, photo_index))
            props = self.photo_properties.get(key, {})
            parent_frame.update_idletasks()
            frame_w, frame_h = parent_frame.winfo_width(), parent_frame.winfo_height()
            if frame_w <= 1 or frame_h <= 1: return
            
            original_img = Image.open(photo_path).convert("RGBA")

            if props.get('grayscale', False):
                original_img = original_img.convert('L').convert('RGBA')
            
            enhancer = ImageEnhance.Brightness(original_img); original_img = enhancer.enhance(props.get('brightness', 1.0))
            enhancer = ImageEnhance.Contrast(original_img); original_img = enhancer.enhance(props.get('contrast', 1.0))
            enhancer = ImageEnhance.Color(original_img); original_img = enhancer.enhance(props.get('saturation', 1.0))

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
                thickness_ratio = props.get('frame_thickness', 0.05)
                frame_img = None
                if frame_path.startswith('preset_'): 
                    frame_img = self._create_preset_frame(frame_path, (frame_w, frame_h), thickness_ratio)
                elif os.path.exists(frame_path): 
                    frame_img = Image.open(frame_path).convert("RGBA")
                
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
        new_photo = {'path': None, 'relx': 0.35, 'rely': 0.3, 'relwidth': 0.3, 'relheight': 0.4}
        self.pages[self.current_page]['photos'].append(new_photo)
        self.refresh_editor_view()

    def _delete_photo_placeholder(self):
        if self.selected_photo_index is None:
            messagebox.showwarning("Törlés", "Nincs képkeret kiválasztva a törléshez.")
            return
        self.pages[self.current_page]['photos'].pop(self.selected_photo_index)
        self._deselect_all()
        self.refresh_editor_view()

    def add_frame(self):
        if self.selected_photo_index is None:
            messagebox.showwarning("Nincs kiválasztott kép", "Kérlek, először kattints egy képre a szerkesztéshez!")
            return
        if self.frame_editor_window is not None and self.frame_editor_window.winfo_exists():
            self.frame_editor_window.focus(); return
        
        self.frame_editor_window = ctk.CTkToplevel(self.root)
        self.frame_editor_window.title("Képkeret szerkesztése"); self.frame_editor_window.geometry("300x550")
        self.frame_editor_window.transient(self.root); self.frame_editor_window.attributes("-topmost", True)
        
        ctk.CTkLabel(self.frame_editor_window, text="Beépített keretek", font=ctk.CTkFont(weight="bold")).pack(pady=(15, 5))
        preset_frame_ui = ctk.CTkFrame(self.frame_editor_window); preset_frame_ui.pack(pady=5, padx=10, fill="x")
        presets = [("Fekete", "preset_black"), ("Fehér", "preset_white"), ("Arany", "preset_gold")]
        for i, (name, path) in enumerate(presets):
            ctk.CTkButton(preset_frame_ui, text=name, command=lambda p=path: self._apply_frame(p)).grid(row=0, column=i, padx=5, pady=5, sticky="ew")
        preset_frame_ui.grid_columnconfigure((0,1,2), weight=1)
        
        ctk.CTkButton(self.frame_editor_window, text="Saját keret feltöltése...", command=lambda: self._apply_frame(self._upload_custom_frame_path())).pack(pady=(10, 5), padx=10, fill="x")
        ctk.CTkLabel(self.frame_editor_window, text="Beállítások", font=ctk.CTkFont(weight="bold")).pack(pady=(15, 5))
        
        self.slider_panel = ctk.CTkFrame(self.frame_editor_window); self.slider_panel.pack(pady=5, padx=10, fill="both", expand=True)
        ctk.CTkLabel(self.slider_panel, text="Vastagság (beépített kereteknél)").pack()
        self.frame_thickness_slider = ctk.CTkSlider(self.slider_panel, from_=0.01, to=0.2, command=self._update_photo_properties)
        self.frame_thickness_slider.pack(fill="x", padx=10, pady=(0,10))
        ctk.CTkLabel(self.slider_panel, text="Méret").pack()
        self.frame_scale_slider = ctk.CTkSlider(self.slider_panel, from_=0.5, to=1.5, command=self._update_photo_properties)
        self.frame_scale_slider.pack(fill="x", padx=10, pady=(0,10))
        ctk.CTkLabel(self.slider_panel, text="Vízszintes eltolás").pack()
        self.frame_offset_x_slider = ctk.CTkSlider(self.slider_panel, from_=-100, to=100, number_of_steps=200, command=self._update_photo_properties)
        self.frame_offset_x_slider.pack(fill="x", padx=10, pady=(0,10))
        ctk.CTkLabel(self.slider_panel, text="Függőleges eltolás").pack()
        self.frame_offset_y_slider = ctk.CTkSlider(self.slider_panel, from_=-100, to=100, number_of_steps=200, command=self._update_photo_properties)
        self.frame_offset_y_slider.pack(fill="x", padx=10, pady=(0,10))
        
        ctk.CTkButton(self.frame_editor_window, text="Keret eltávolítása", fg_color="#D32F2F", hover_color="#B71C1C", command=lambda: self._apply_frame(None)).pack(pady=10, padx=10, fill="x")
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
            
    def add_page_frame(self):
        window = ctk.CTkToplevel(self.root)
        window.title("Oldalkeretet beállítása"); window.geometry("320x300")
        window.transient(self.root); window.grab_set()

        current_page_data = self.pages[self.current_page]
        thickness_slider = None

        def _update_thickness(value):
            if thickness_slider:
                current_page_data['page_frame_thickness'] = value
        
        def _select_page_frame(path):
            if path is not None:
                current_page_data['page_frame_path'] = path
                if thickness_slider:
                    current_page_data['page_frame_thickness'] = thickness_slider.get()
            else:
                current_page_data.pop('page_frame_path', None)
                current_page_data.pop('page_frame_thickness', None)
            
            window.destroy()
            self.refresh_editor_view()

        ctk.CTkLabel(window, text="Válassz keretet az oldalhoz!", font=ctk.CTkFont(weight="bold")).pack(pady=10)
        
        preset_frame_ui = ctk.CTkFrame(window); preset_frame_ui.pack(pady=5, padx=10, fill="x")
        presets = [("Fekete", "preset_black"), ("Fehér", "preset_white"), ("Arany", "preset_gold")]
        for i, (name, path) in enumerate(presets):
            ctk.CTkButton(preset_frame_ui, text=name, command=lambda p=path: _select_page_frame(p)).grid(row=0, column=i, padx=5, pady=5, sticky="ew")
        preset_frame_ui.grid_columnconfigure((0,1,2), weight=1)

        ctk.CTkLabel(window, text="Keret vastagsága (beépített kereteknél)", font=ctk.CTkFont(size=12)).pack(pady=(10,0))
        thickness_slider = ctk.CTkSlider(window, from_=0.01, to=0.2, number_of_steps=19, command=_update_thickness)
        thickness_slider.set(current_page_data.get('page_frame_thickness', 0.05))
        thickness_slider.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkButton(window, text="Saját keret feltöltése...", command=lambda: _select_page_frame(self._upload_custom_frame_path())).pack(pady=10, padx=10, fill="x")
        ctk.CTkButton(window, text="Keret eltávolítása", fg_color="#D32F2F", hover_color="#B71C1C", command=lambda: _select_page_frame(None)).pack(pady=10, padx=10, fill="x")
    
    def _upload_custom_frame_path(self):
        return filedialog.askopenfilename(title="Válassz egy keret képet", filetypes=[("Képfájlok", "*.jpg *.jpeg *.png *.bmp"), ("Minden fájl", "*.*")]) or None
    
    def select_page(self, page_idx):
        if 0 <= page_idx < len(self.pages):
            self.current_page = page_idx
            self.refresh_editor_view()

    def add_new_page(self):
        self.pages.append({'photos': self._generate_layout_template(1), 'texts': []})
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

        project_data = {"pages": pages_to_save, "photo_properties": self.photo_properties}
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("Mentés sikeres", f"A projekt sikeresen elmentve ide:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Mentési hiba", f"Hiba történt a projekt mentése során:\n{e}")

    def load_project(self):
        filepath = filedialog.askopenfilename(title="Projekt megnyitása", filetypes=[("LoLaBa Fotókönyv Projekt", "*.lolaba"), ("Minden fájl", "*.*")])
        if not filepath: return
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                project_data = json.load(f)
            self._reset_project_state()
            self.pages = project_data.get("pages", [])
            self.photo_properties = project_data.get("photo_properties", {})
            self.current_page = 0
            if not self.pages:
                messagebox.showwarning("Betöltési hiba", "A projektfájl üres vagy sérült.")
                self.create_main_menu()
                return
            messagebox.showinfo("Betöltés sikeres", "A projekt sikeresen betöltve.")
            
            if not self.editor_ui_built:
                self._build_editor_ui()
                self.editor_ui_built = True
            self.refresh_editor_view()

        except Exception as e:
            messagebox.showerror("Betöltési hiba", f"Hiba történt a projekt betöltése során:\n{e}")
            self._reset_project_state()
            self.create_main_menu()

    def export_project(self):
        if not self.pages:
            messagebox.showerror("Hiba", "Nincs mit exportálni. Hozz létre legalább egy oldalt!")
            return
        export_window = ctk.CTkToplevel(self.root)
        export_window.title("Exportálás"); export_window.geometry("300x200")
        export_window.transient(self.root); export_window.grab_set()
        ctk.CTkLabel(export_window, text="Válassz exportálási formátumot:", font=ctk.CTkFont(size=16)).pack(pady=20)
        btn_style = {'height': 40, 'width': 200}
        ctk.CTkButton(export_window, text="Exportálás Képként (PNG)", command=lambda: [export_window.destroy(), self._export_as_images()], **btn_style).pack(pady=10)
        ctk.CTkButton(export_window, text="Exportálás PDF-ként", command=lambda: [export_window.destroy(), self._export_as_pdf()], **btn_style).pack(pady=10)

    def _export_as_images(self):
        folder_selected = filedialog.askdirectory(title="Válassz mappát az exportáláshoz")
        if not folder_selected: return
        try:
            for i in range(len(self.pages)):
                page_image = self._render_page_to_image(i)
                if page_image:
                    filename = os.path.join(folder_selected, f"oldal_{i+1}.png")
                    page_image.save(filename, "PNG")
            messagebox.showinfo("Exportálás sikeres", f"Az oldalak sikeresen exportálva a következő mappába:\n{folder_selected}")
        except Exception as e:
            messagebox.showerror("Exportálási hiba", f"Hiba történt a képek exportálása során:\n{e}")

    def _export_as_pdf(self):
        filepath = filedialog.asksaveasfilename(title="PDF mentése másként", defaultextension=".pdf", filetypes=[("PDF Dokumentum", "*.pdf")])
        if not filepath: return
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
                    filepath, "PDF", resolution=100.0, save_all=True, append_images=rendered_images[1:]
                )
            elif rendered_images:
                rendered_images[0].save(filepath, "PDF", resolution=100.0)

            messagebox.showinfo("Exportálás sikeres", f"A PDF sikeresen létrehozva:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Exportálási hiba", f"Hiba történt a PDF létrehozása során:\n{e}\n{traceback.format_exc()}")
    
    def _render_page_to_image(self, page_index):
        if page_index >= len(self.pages):
            return None

        page_data = self.pages[page_index]
        W, H = self.EXPORT_RESOLUTION
        
        bg_setting = page_data.get('background')
        if isinstance(bg_setting, dict) and bg_setting.get('type') == 'image' and os.path.exists(bg_setting.get('path')):
            bg_img = Image.open(bg_setting['path']).convert("RGBA")
            page_image = bg_img.resize((W,H), Image.LANCZOS)
        else:
            bg_color = bg_setting if isinstance(bg_setting, str) and bg_setting.startswith('#') else self.colors['card_bg']
            page_image = Image.new('RGBA', (W, H), bg_color)
        
        draw = ImageDraw.Draw(page_image)
        
        padding = 0
        page_frame_path = page_data.get('page_frame_path')
        if page_frame_path:
            thickness_ratio = page_data.get('page_frame_thickness', 0.05)
            if page_frame_path.startswith('preset_'):
                padding = int(min(W, H) * thickness_ratio)

            frame_img = None
            if page_frame_path.startswith('preset_'): 
                frame_img = self._create_preset_frame(page_frame_path, (W, H), thickness_ratio)
            elif os.path.exists(page_frame_path): 
                frame_img = Image.open(page_frame_path).convert("RGBA")
            
            if frame_img:
                frame_img_resized = frame_img.resize((W, H), Image.LANCZOS)
                page_image.paste(frame_img_resized, (0, 0), frame_img_resized)
        
        for photo_idx, photo_data in enumerate(page_data.get('photos', [])):
            if not photo_data.get('path') or not os.path.exists(photo_data['path']):
                continue

            container_w, container_h = W - 2 * padding, H - 2 * padding
            frame_w = int(photo_data['relwidth'] * container_w)
            frame_h = int(photo_data['relheight'] * container_h)
            frame_x = padding + int(photo_data['relx'] * container_w)
            frame_y = padding + int(photo_data['rely'] * container_h)

            try:
                key = str((page_index, photo_idx))
                props = self.photo_properties.get(key, {})
                original_img = Image.open(photo_data['path']).convert("RGBA")

                if props.get('grayscale', False):
                    original_img = original_img.convert('L').convert('RGBA')
                enhancer = ImageEnhance.Brightness(original_img); original_img = enhancer.enhance(props.get('brightness', 1.0))
                enhancer = ImageEnhance.Contrast(original_img); original_img = enhancer.enhance(props.get('contrast', 1.0))
                enhancer = ImageEnhance.Color(original_img); original_img = enhancer.enhance(props.get('saturation', 1.0))

                img_ratio = original_img.width / original_img.height
                frame_ratio = frame_w / frame_h
                zoom = props.get('zoom', 1.0); pan_x = props.get('pan_x', 0.5); pan_y = props.get('pan_y', 0.5)

                if img_ratio > frame_ratio: new_h, new_w = int(frame_h * zoom), int(frame_h * zoom * img_ratio)
                else: new_w, new_h = int(frame_w * zoom), int(frame_w * zoom / img_ratio)
                if new_w < 1 or new_h < 1: new_w, new_h = frame_w, frame_h
                zoomed_img = original_img.resize((new_w, new_h), Image.LANCZOS)
                
                extra_w, extra_h = max(0, zoomed_img.width - frame_w), max(0, zoomed_img.height - frame_h)
                crop_x, crop_y = int(extra_w * pan_x), int(extra_h * pan_y)
                final_photo = zoomed_img.crop((crop_x, crop_y, crop_x + frame_w, crop_y + frame_h))

                photo_frame_path = props.get('frame_path')
                if photo_frame_path:
                    thickness_ratio_photo = props.get('frame_thickness', 0.05)
                    photo_frame_img = None
                    if photo_frame_path.startswith('preset_'): 
                        photo_frame_img = self._create_preset_frame(photo_frame_path, (frame_w, frame_h), thickness_ratio_photo)
                    elif os.path.exists(photo_frame_path): 
                        photo_frame_img = Image.open(photo_frame_path).convert("RGBA")
                    if photo_frame_img:
                        f_scale = props.get('frame_scale', 1.0); f_off_x = props.get('frame_offset_x', 0); f_off_y = props.get('frame_offset_y', 0)
                        new_fw, new_fh = int(frame_w * f_scale), int(frame_h * f_scale)
                        resized_frame = photo_frame_img.resize((new_fw, new_fh), Image.LANCZOS)
                        paste_x = (frame_w - new_fw) // 2 + f_off_x; paste_y = (frame_h - new_fh) // 2 + f_off_y
                        final_photo.paste(resized_frame, (paste_x, paste_y), resized_frame)
                
                page_image.paste(final_photo, (frame_x, frame_y), final_photo)

            except Exception as e:
                print(f"HIBA a(z) {page_index}. oldal, {photo_idx}. kép renderelésekor: {e}")
                draw.rectangle([frame_x, frame_y, frame_x + frame_w, frame_y + frame_h], outline="red", width=5)
                draw.text((frame_x + 10, frame_y + 10), "Kép hiba", fill="red")

        for text_data in page_data.get('texts', []):
            try:
                font_family = text_data.get('font_family', 'Arial')
                font_size = text_data.get('font_size', 24)
                font_style = text_data.get('font_style', 'normal')
                
                font_path = f"{font_family.lower().replace(' ', '')}.ttf"
                if 'bold' in font_style and 'italic' in font_style: font_path = f"{font_family.lower().replace(' ', '')}bi.ttf"
                elif 'bold' in font_style: font_path = f"{font_family.lower().replace(' ', '')}bd.ttf"
                elif 'italic' in font_style: font_path = f"{font_family.lower().replace(' ', '')}i.ttf"

                try: font = ImageFont.truetype(font_path, size=font_size)
                except IOError:
                    try: font = ImageFont.truetype(f"{font_family}.ttf", size=font_size)
                    except IOError:
                        print(f"Figyelmeztetés: '{font_family}' betűtípus nem található, alapértelmezett betűtípus lesz használva.")
                        font = ImageFont.load_default(size=font_size)

                text_x = int(text_data['relx'] * W)
                text_y = int(text_data['rely'] * H)
                draw.text((text_x, text_y), text_data['text'], fill=text_data.get('font_color', '#000000'), font=font, anchor="mm")
            except Exception as e:
                print(f"HIBA a szöveg renderelésekor: {e}")

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
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w <= 1 or h <= 1: return
        
        for i, text_data in enumerate(self.pages[self.current_page]['texts']):
            style_string = text_data.get('font_style', 'normal')
            font_obj = ctk.CTkFont(family=text_data.get('font_family', 'Arial'), size=text_data.get('font_size', 12), weight="bold" if "bold" in style_string else "normal", slant="italic" if "italic" in style_string else "roman")
            container = ctk.CTkFrame(self.canvas, fg_color="transparent")
            label = ctk.CTkLabel(container, text=text_data['text'], font=font_obj, text_color=text_data.get('font_color', '#000000'), fg_color="transparent")
            label.pack(padx=2, pady=2)
            
            abs_x = int(text_data['relx'] * w)
            abs_y = int(text_data['rely'] * h)

            canvas_item_id = self.canvas.create_window(abs_x, abs_y, window=container, anchor="center", tags="text")
            self.widget_to_canvas_item[container] = canvas_item_id
            
            container.bind("<ButtonPress-1>", lambda e, index=i: self._on_widget_press(e, 'text', index))
            container.bind("<B1-Motion>", lambda e: self._on_widget_drag(e))
            container.bind("<ButtonRelease-1>", lambda e: self._on_widget_release(e))
            label.bind("<ButtonPress-1>", lambda e, index=i: self._on_widget_press(e, 'text', index))
            label.bind("<B1-Motion>", lambda e: self._on_widget_drag(e))
            label.bind("<ButtonRelease-1>", lambda e: self._on_widget_release(e))
            self.text_widgets.append(container)

    # --- JAVÍTOTT SZÖVEGKEZELÉS A FÓKUSZVESZTÉS ELKERÜLÉSÉRE ---
    def _update_selected_text_widget(self):
        """Csak a kiválasztott szöveg widgetet frissíti, a teljes vászon újra rajzolása nélkül."""
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
            
            # A label frissítése a modell alapján. A szín a kiválasztás logikája szerint változik,
            # így azt itt nem kell expliciten beállítani.
            text_label.configure(text=text_data['text'], font=font_obj)
        except (IndexError, AttributeError) as e:
            print(f"Hiba a szöveg widget frissítésekor: {e}")

    def _update_text_properties(self, event=None):
        """Frissíti a szöveg adatmodelljét a UI-ból, majd meghív egy célzott frissítést a fókuszvesztés elkerülése érdekében."""
        if self.selected_text_index is None: return
        
        try:
            # 1. Adatmodell frissítése a UI elemekből
            text_data = self.pages[self.current_page]['texts'][self.selected_text_index]
            text_data['text'] = self.text_input.get("1.0", "end-1c")
            text_data['font_family'] = self.font_family_var.get()
            text_data['font_size'] = int(self.font_size_slider.get())
            style = []
            if self.font_bold_var.get() == "on": style.append("bold")
            if self.font_italic_var.get() == "on": style.append("italic")
            text_data['font_style'] = " ".join(style) if style else "normal"
            text_data['show_bg_on_select'] = self.show_bg_var.get() == "on"

            # 2. Csak a módosított widget újrarajzolása a teljes oldal helyett
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
            # Csak az adatmodellt frissítjük. A szín a kijelölés megszüntetésekor fog látszani.
            self.pages[self.current_page]['texts'][self.selected_text_index]['font_color'] = color_code[1]

    # --- MOZGATÁS METÓDUSAI (CANVAS-HOZ IGAZÍTVA) ---
    def _on_widget_press(self, event, item_type, index):
        if item_type == 'photo':
            self._select_photo(index)
            widget = self.photo_frames[index]
        elif item_type == 'text':
            self._select_text(index)
            widget = self.text_widgets[index]
        else: return
        
        canvas_item_id = self.widget_to_canvas_item.get(widget)
        if canvas_item_id:
            self.canvas.tag_raise(canvas_item_id)
            self._drag_data = {"widget": widget, "item_id": canvas_item_id, "item_type": item_type, "index": index, "offset_x": event.x_root, "offset_y": event.y_root}

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
        
        item_type = self._drag_data["item_type"]
        index = self._drag_data["index"]
        item_id = self._drag_data["item_id"]
        
        canvas_w, canvas_h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if canvas_w == 0 or canvas_h == 0: 
            self._drag_data = {}
            return
            
        x, y = self.canvas.coords(item_id)

        if item_type == 'photo':
            data_list = self.pages[self.current_page]['photos']
            data_list[index]['relx'] = x / canvas_w
            data_list[index]['rely'] = y / canvas_h
        elif item_type == 'text':
            data_list = self.pages[self.current_page]['texts']
            data_list[index]['relx'] = x / canvas_w
            data_list[index]['rely'] = y / canvas_h
            
        self._drag_data = {}

    def run(self):
        self.root.mainloop()

def main():
    app = FotokonyvGUI()
    app.run()

if __name__ == "__main__":
    main()
