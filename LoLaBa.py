import customtkinter as ctk
from tkinter import messagebox, filedialog
import os
from PIL import Image, ImageTk

# Modern téma beállítása
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class FotokonyvGUI:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("LoLaBa Fotókönyv")
        self.root.geometry("1200x800")
        
        # Egyedi színek beállítása
        self.colors = {
            'bg_primary': '#C4A484',
            'bg_secondary': '#B5956B', 
            'card_bg': '#F5F5F5',
            'button_bg': '#E8E8E8',
            'accent': '#A4B068',
            'text_primary': '#333333',
            'text_secondary': '#666666'
        }
        
        # Projekt állapot
        self.current_layout = 1
        self.pages = []
        
        # Indítás
        self.create_main_menu()
    
    def create_main_menu(self):
        """Főmenü modern megjelenéssel"""
        self.clear_window()
        
        # Fő container
        main_frame = ctk.CTkFrame(self.root, 
                                 fg_color=self.colors['bg_primary'],
                                 corner_radius=0)
        main_frame.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Cím
        title_label = ctk.CTkLabel(main_frame, 
                                  text="LoLaBa Fotókönyv",
                                  font=ctk.CTkFont(size=48, weight="bold"),
                                  text_color="white")
        title_label.pack(pady=(80, 20))
        
        # Alcím
        subtitle_label = ctk.CTkLabel(main_frame,
                                     text="Készíts saját, egyedi fotókönyvet egyszerű lépésekkel!",
                                     font=ctk.CTkFont(size=18),
                                     text_color="white")
        subtitle_label.pack(pady=(0, 60))
        
        # Gombok container
        button_frame = ctk.CTkFrame(main_frame, 
                                   fg_color="transparent")
        button_frame.pack(expand=True)
        
        # Gombok stílusa
        button_style = {
            'width': 350,
            'height': 60,
            'font': ctk.CTkFont(size=16, weight="bold"),
            'corner_radius': 15,
            'fg_color': self.colors['card_bg'],
            'text_color': self.colors['text_primary'],
            'hover_color': '#F0F0F0'
        }
        
        # Új projekt gomb
        new_btn = ctk.CTkButton(button_frame, 
                               text="🆕 Új projekt létrehozása",
                               command=self.show_page_selection,
                               **button_style)
        new_btn.pack(pady=15)
        
        # Projekt betöltés gomb
        load_btn = ctk.CTkButton(button_frame,
                                text="📁 Korábbi projekt megnyitása", 
                                command=self.load_project,
                                **button_style)
        load_btn.pack(pady=15)
        
        # Kilépés gomb
        exit_btn = ctk.CTkButton(button_frame,
                                text="🚪 Kilépés",
                                command=self.root.quit,
                                **button_style)
        exit_btn.pack(pady=15)
    
    def show_page_selection(self):
        """Layout kiválasztás szép kerekített kártyákkal"""
        self.clear_window()
        
        # Fő container
        main_frame = ctk.CTkFrame(self.root, 
                                 fg_color=self.colors['bg_primary'],
                                 corner_radius=0)
        main_frame.pack(fill="both", expand=True)
        
        # Cím
        title_label = ctk.CTkLabel(main_frame,
                                  text="Oldalnézet kiválasztása",
                                  font=ctk.CTkFont(size=32, weight="bold"),
                                  text_color="white")
        title_label.pack(pady=(50, 40))
        
        # Layout opciók container
        layout_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        layout_frame.pack(expand=True)
        
        # Layout kártyák
        cards_frame = ctk.CTkFrame(layout_frame, fg_color="transparent")
        cards_frame.pack()
        
        # Layout definíciók
        layouts = [
            {"name": "1 kép", "value": 1, "icon": "🖼️"},
            {"name": "2 kép", "value": 2, "icon": "🖼️🖼️"},
            {"name": "4 kép", "value": 4, "icon": "🖼️🖼️\n🖼️🖼️"}
        ]
        
        self.layout_buttons = []
        
        for i, layout in enumerate(layouts):
            # Kártya container
            card = ctk.CTkFrame(cards_frame,
                               width=220,
                               height=180,
                               fg_color=self.colors['card_bg'],
                               corner_radius=20)
            card.grid(row=0, column=i, padx=25, pady=20)
            card.pack_propagate(False)
            
            # Layout előnézet
            preview_frame = ctk.CTkFrame(card,
                                        width=180,
                                        height=100,
                                        fg_color=self.colors['accent'],
                                        corner_radius=15)
            preview_frame.pack(pady=(20, 10))
            preview_frame.pack_propagate(False)
            
            # Layout ikon
            icon_label = ctk.CTkLabel(preview_frame,
                                     text=layout["icon"],
                                     font=ctk.CTkFont(size=20),
                                     text_color="white")
            icon_label.pack(expand=True)
            
            # Layout név
            name_label = ctk.CTkLabel(card,
                                     text=layout["name"],
                                     font=ctk.CTkFont(size=16, weight="bold"),
                                     text_color=self.colors['text_primary'])
            name_label.pack(pady=(0, 15))
            
            # Klikkelhetőség
            def make_click_handler(value):
                return lambda: self.select_layout(value)
            
            card.bind("<Button-1>", lambda e, v=layout["value"]: self.select_layout(v))
            preview_frame.bind("<Button-1>", lambda e, v=layout["value"]: self.select_layout(v))
            icon_label.bind("<Button-1>", lambda e, v=layout["value"]: self.select_layout(v))
            name_label.bind("<Button-1>", lambda e, v=layout["value"]: self.select_layout(v))
            
            self.layout_buttons.append(card)
        
        # Tovább gomb
        continue_btn = ctk.CTkButton(main_frame,
                                    text="🔧 Kiválaszt és alkalmaz",
                                    command=self.show_photo_editor,
                                    width=250,
                                    height=50,
                                    font=ctk.CTkFont(size=16, weight="bold"),
                                    corner_radius=15,
                                    fg_color=self.colors['card_bg'],
                                    text_color=self.colors['text_primary'],
                                    hover_color='#F0F0F0')
        continue_btn.pack(pady=40)
    
    def show_photo_editor(self):
        """Fotószerkesztő modern megjelenéssel"""
        self.clear_window()
        
        # Fő container
        main_frame = ctk.CTkFrame(self.root,
                                 fg_color=self.colors['bg_primary'], 
                                 corner_radius=0)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Cím
        title_label = ctk.CTkLabel(main_frame,
                                  text="Fotókönyv szerkesztő",
                                  font=ctk.CTkFont(size=28, weight="bold"),
                                  text_color="white")
        title_label.pack(pady=(10, 20))
        
        # Fő munkafelület
        workspace = ctk.CTkFrame(main_frame, fg_color="transparent")
        workspace.pack(fill="both", expand=True)
        
        # Bal panel - oldalak
        left_panel = ctk.CTkFrame(workspace,
                                 width=220,
                                 fg_color=self.colors['card_bg'],
                                 corner_radius=20)
        left_panel.pack(side="left", fill="y", padx=(0, 15))
        left_panel.pack_propagate(False)
        
        # Oldalak címe
        pages_title = ctk.CTkLabel(left_panel,
                                  text="Oldalak",
                                  font=ctk.CTkFont(size=18, weight="bold"),
                                  text_color=self.colors['text_primary'])
        pages_title.pack(pady=(20, 15))
        
        # Oldal előnézetek
        for i in range(1, 3):
            page_preview = ctk.CTkFrame(left_panel,
                                       width=180,
                                       height=100,
                                       fg_color=self.colors['accent'],
                                       corner_radius=15)
            page_preview.pack(pady=8, padx=20)
            page_preview.pack_propagate(False)
            
            page_label = ctk.CTkLabel(page_preview,
                                     text=f"{i}. oldal",
                                     font=ctk.CTkFont(size=12),
                                     text_color="white")
            page_label.pack(expand=True)
        
        # Új oldal gomb
        add_page_btn = ctk.CTkButton(left_panel,
                                    text="+ Új oldal",
                                    command=self.add_new_page,
                                    width=180,
                                    height=50,
                                    font=ctk.CTkFont(size=14, weight="bold"),
                                    corner_radius=15,
                                    fg_color=self.colors['accent'],
                                    hover_color='#8A9654')
        add_page_btn.pack(pady=15)
        
        # Középső panel - fotókönyv
        center_panel = ctk.CTkFrame(workspace,
                                   fg_color=self.colors['card_bg'],
                                   corner_radius=20)
        center_panel.pack(side="left", fill="both", expand=True, padx=15)
        
        # Fotókönyv címe
        book_title = ctk.CTkLabel(center_panel,
                                 text="Fotókönyv",
                                 font=ctk.CTkFont(size=20, weight="bold"),
                                 text_color=self.colors['text_primary'])
        book_title.pack(pady=(20, 15))
        
        # Fotó container
        photo_container = ctk.CTkFrame(center_panel, fg_color="transparent")
        photo_container.pack(expand=True, padx=20, pady=20)
        
        # Két oldal
        for i in range(2):
            photo_frame = ctk.CTkFrame(photo_container,
                                      width=300,
                                      height=220,
                                      fg_color="white",
                                      corner_radius=20)
            photo_frame.pack(side="left", padx=15)
            photo_frame.pack_propagate(False)
            
            # Fotó terület
            photo_area = ctk.CTkFrame(photo_frame,
                                     width=260,
                                     height=180,
                                     fg_color=self.colors['accent'],
                                     corner_radius=15)
            photo_area.pack(pady=20)
            photo_area.pack_propagate(False)
            
            # Fotó hozzáadás szöveg
            photo_label = ctk.CTkLabel(photo_area,
                                      text="Kattints fotó\nhozzáadásához",
                                      font=ctk.CTkFont(size=14),
                                      text_color="white")
            photo_label.pack(expand=True)
            
            # Klikkelhetőség
            photo_area.bind("<Button-1>", lambda e: self.add_photo())
            photo_label.bind("<Button-1>", lambda e: self.add_photo())
        
        # Jobb panel - vezérlők
        right_panel = ctk.CTkFrame(workspace,
                                  width=260,
                                  fg_color=self.colors['card_bg'],
                                  corner_radius=20)
        right_panel.pack(side="right", fill="y", padx=(15, 0))
        right_panel.pack_propagate(False)
        
        # Vezérlők címe
        controls_title = ctk.CTkLabel(right_panel,
                                     text="Beállítások",
                                     font=ctk.CTkFont(size=18, weight="bold"),
                                     text_color=self.colors['text_primary'])
        controls_title.pack(pady=(20, 15))
        
        # Fotó hozzáadás gomb
        add_photo_btn = ctk.CTkButton(right_panel,
                                     text="📷 Fotó hozzáadása",
                                     command=self.add_photo,
                                     width=220,
                                     height=40,
                                     font=ctk.CTkFont(size=14),
                                     corner_radius=10,
                                     fg_color=self.colors['accent'],
                                     hover_color='#8A9654')
        add_photo_btn.pack(pady=10, padx=20)
        
        # Méretezés csúszka
        size_label = ctk.CTkLabel(right_panel,
                                 text="Méretezés",
                                 font=ctk.CTkFont(size=14, weight="bold"),
                                 text_color=self.colors['text_primary'])
        size_label.pack(pady=(20, 5))
        
        size_slider = ctk.CTkSlider(right_panel,
                                   from_=0,
                                   to=100,
                                   width=200,
                                   button_color=self.colors['accent'],
                                   button_hover_color='#8A9654')
        size_slider.pack(pady=5)
        size_slider.set(35)
        
        # Pozíció csúszka
        pos_label = ctk.CTkLabel(right_panel,
                                text="Pozíció",
                                font=ctk.CTkFont(size=14, weight="bold"),
                                text_color=self.colors['text_primary'])
        pos_label.pack(pady=(20, 5))
        
        pos_slider = ctk.CTkSlider(right_panel,
                                  from_=0,
                                  to=100,
                                  width=200,
                                  button_color=self.colors['accent'],
                                  button_hover_color='#8A9654')
        pos_slider.pack(pady=5)
        pos_slider.set(35)
        
        # További gombok
        extra_buttons = [
            ("🎨 Háttér beállítása", self.set_background),
            ("📝 Szöveg hozzáadása", self.add_text),
            ("🖼️ Keret hozzáadása", self.add_frame)
        ]
        
        for text, command in extra_buttons:
            btn = ctk.CTkButton(right_panel,
                               text=text,
                               command=command,
                               width=220,
                               height=35,
                               font=ctk.CTkFont(size=12),
                               corner_radius=10,
                               fg_color=self.colors['button_bg'],
                               text_color=self.colors['text_secondary'],
                               hover_color='#F0F0F0')
            btn.pack(pady=5, padx=20)
        
        # Alsó eszköztár
        toolbar = ctk.CTkFrame(main_frame,
                              height=70,
                              fg_color=self.colors['card_bg'],
                              corner_radius=15)
        toolbar.pack(fill="x", pady=(20, 0))
        toolbar.pack_propagate(False)
        
        # Eszköztár gombok
        toolbar_buttons = [
            ("💾 Mentés", self.save_project),
            ("📁 Betöltés", self.load_project),
            ("📤 Exportálás", self.export_project),
            ("🏠 Főmenü", self.create_main_menu)
        ]
        
        buttons_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        buttons_frame.pack(expand=True)
        
        for text, command in toolbar_buttons:
            btn = ctk.CTkButton(buttons_frame,
                               text=text,
                               command=command,
                               width=140,
                               height=40,
                               font=ctk.CTkFont(size=12),
                               corner_radius=10,
                               fg_color=self.colors['button_bg'],
                               text_color=self.colors['text_secondary'],
                               hover_color='#F0F0F0')
            btn.pack(side="left", padx=10, pady=15)
    
    def clear_window(self):
        """Törli az ablak tartalmát"""
        for widget in self.root.winfo_children():
            widget.destroy()
    
    def select_layout(self, layout_type):
        """Layout kiválasztása"""
        self.current_layout = layout_type
        layout_names = {1: "egy képes", 2: "két képes", 4: "négy képes"}
        messagebox.showinfo("Layout", f"{layout_names[layout_type]} layout kiválasztva")
    
    def add_new_page(self):
        """Új oldal hozzáadása"""
        messagebox.showinfo("Új oldal", "Új oldal hozzáadva a fotókönyvhöz!")
    
    def add_photo(self):
        """Fotó hozzáadása"""
        filename = filedialog.askopenfilename(
            title="Válassz fotót",
            filetypes=[("Képfájlok", "*.jpg *.jpeg *.png *.gif *.bmp")]
        )
        if filename:
            messagebox.showinfo("Fotó", f"Fotó hozzáadva: {os.path.basename(filename)}")
    
    def save_project(self):
        """Projekt mentése"""
        filename = filedialog.asksaveasfilename(
            title="Projekt mentése",
            defaultextension=".lolaba",
            filetypes=[("LoLaBa projekt", "*.lolaba"), ("Minden fájl", "*.*")]
        )
        if filename:
            messagebox.showinfo("Mentés", f"Projekt mentve: {os.path.basename(filename)}")
    
    def load_project(self):
        """Projekt betöltése"""
        filename = filedialog.askopenfilename(
            title="Projekt betöltése",
            filetypes=[("LoLaBa projekt", "*.lolaba"), ("Minden fájl", "*.*")]
        )
        if filename:
            messagebox.showinfo("Betöltés", f"Projekt betöltve: {os.path.basename(filename)}")
            self.show_photo_editor()
    
    def export_project(self):
        """Projekt exportálása"""
        filename = filedialog.asksaveasfilename(
            title="Projekt exportálása",
            defaultextension=".pdf",
            filetypes=[("PDF fájl", "*.pdf"), ("Minden fájl", "*.*")]
        )
        if filename:
            messagebox.showinfo("Exportálás", f"Projekt exportálva: {os.path.basename(filename)}")
    
    def set_background(self):
        """Háttér beállítása"""
        messagebox.showinfo("Háttér", "Háttér beállítása...")
    
    def add_text(self):
        """Szöveg hozzáadása"""
        messagebox.showinfo("Szöveg", "Szöveg hozzáadása...")
    
    def add_frame(self):
        """Keret hozzáadása"""
        messagebox.showinfo("Keret", "Keret hozzáadása...")
    
    def run(self):
        """Alkalmazás indítása"""
        self.root.mainloop()

def main():
    """Főprogram"""
    app = FotokonyvGUI()
    app.run()

if __name__ == "__main__":
    main()
