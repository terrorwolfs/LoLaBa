
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter import font as tkfont
import os

class FotokonyvGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("LoLaBa Fotókönyv")
        self.root.geometry("1200x800")
        self.root.configure(bg='#C4A484')
        
        # Főmenü létrehozása
        self.create_main_menu()
    
    def create_main_menu(self):
        """Főmenü létrehozása"""
        # Előző widget-ek törlése
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Címsor
        title_font = tkfont.Font(family="Arial", size=24, weight="bold")
        title_label = tk.Label(self.root, text="LoLaBa Fotókönyv", 
                              font=title_font, bg='#C4A484', fg='white')
        title_label.pack(pady=50)
        
        subtitle_label = tk.Label(self.root, text="Készíts saját, egyedi fotókönyvet egyszerű lépésekkel!", 
                                 font=("Arial", 12), bg='#C4A484', fg='white')
        subtitle_label.pack(pady=10)
        
        # Menü gombok
        button_frame = tk.Frame(self.root, bg='#C4A484')
        button_frame.pack(pady=50)
        
        # Gomb stílus
        button_width = 25
        button_height = 2
        button_font = ("Arial", 11)
        
        # Új projekt létrehozása
        new_project_btn = tk.Button(button_frame, text="Új projekt létrehozása",
                                   width=button_width, height=button_height,
                                   font=button_font, bg='#E8E8E8', fg='#888888',
                                   command=self.show_project_menu)
        new_project_btn.pack(pady=10)
        
        # Korábbi projekt megnyitása
        open_project_btn = tk.Button(button_frame, text="Korábbi projekt megnyitása",
                                    width=button_width, height=button_height,
                                    font=button_font, bg='#E8E8E8', fg='#888888',
                                    command=self.open_project)
        open_project_btn.pack(pady=10)
        
        # Kilépés
        exit_btn = tk.Button(button_frame, text="Kilépés",
                            width=button_width, height=button_height,
                            font=button_font, bg='#E8E8E8', fg='#888888',
                            command=self.root.quit)
        exit_btn.pack(pady=10)
    
    def show_project_menu(self):
        """Projekt menü megjelenítése"""
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Menü gombok
        button_frame = tk.Frame(self.root, bg='#C4A484')
        button_frame.pack(expand=True)
        
        button_width = 20
        button_height = 2
        button_font = ("Arial", 11)
        
        # Projekt mentése
        save_btn = tk.Button(button_frame, text="Projekt mentése",
                            width=button_width, height=button_height,
                            font=button_font, bg='#E8E8E8', fg='#888888',
                            command=self.save_project)
        save_btn.pack(pady=15)
        
        # Projekt betöltése
        load_btn = tk.Button(button_frame, text="Projekt betöltése",
                            width=button_width, height=button_height,
                            font=button_font, bg='#E8E8E8', fg='#888888',
                            command=self.load_project)
        load_btn.pack(pady=15)
        
        # Projekt exportálása
        export_btn = tk.Button(button_frame, text="Projekt exportálása",
                              width=button_width, height=button_height,
                              font=button_font, bg='#E8E8E8', fg='#888888',
                              command=self.show_page_selection)
        export_btn.pack(pady=15)
        
        # Vissza gomb
        back_btn = tk.Button(button_frame, text="Vissza a főmenübe",
                            width=button_width, height=button_height,
                            font=button_font, bg='#E8E8E8', fg='#888888',
                            command=self.create_main_menu)
        back_btn.pack(pady=15)
    
    def show_page_selection(self):
        """Oldalnézet kiválasztása"""
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Címsor
        title_label = tk.Label(self.root, text="Oldalnézet kiválasztása", 
                              font=("Arial", 18, "bold"), bg='#C4A484', fg='white')
        title_label.pack(pady=30)
        
        # Layout opciók
        layout_frame = tk.Frame(self.root, bg='#C4A484')
        layout_frame.pack(expand=True)
        
        # 3 layout opció létrehozása
        layouts = [
            ("Kiválasztva", self.create_layout1),
            ("Kiválasztva", self.create_layout2), 
            ("Kiválasztva", self.create_layout3)
        ]
        
        layout_container = tk.Frame(layout_frame, bg='#C4A484')
        layout_container.pack()
        
        for i, (text, command) in enumerate(layouts):
            # Layout előnézet frame
            preview_frame = tk.Frame(layout_container, bg='#E8E8E8', width=200, height=150)
            preview_frame.grid(row=0, column=i, padx=20, pady=10)
            preview_frame.pack_propagate(False)
            
            # Layout előnézet
            if i == 0:
                # Egy nagy kép
                img_frame = tk.Frame(preview_frame, bg='#A4B068', width=160, height=110)
                img_frame.pack(padx=20, pady=20)
            elif i == 1:
                # Két kép egymás mellett
                img_container = tk.Frame(preview_frame, bg='#E8E8E8')
                img_container.pack(pady=20)
                img1 = tk.Frame(img_container, bg='#A4B068', width=70, height=90)
                img1.pack(side=tk.LEFT, padx=5)
                img2 = tk.Frame(img_container, bg='#A4B068', width=70, height=90)
                img2.pack(side=tk.LEFT, padx=5)
            else:
                # Négy kis kép
                img_container = tk.Frame(preview_frame, bg='#E8E8E8')
                img_container.pack(pady=15)
                for row in range(2):
                    for col in range(2):
                        img = tk.Frame(img_container, bg='#A4B068', width=60, height=35)
                        img.grid(row=row, column=col, padx=3, pady=3)
            
            # Kiválasztva címke
            select_label = tk.Label(layout_container, text=text, 
                                   font=("Arial", 10), bg='#C4A484', fg='white')
            select_label.grid(row=1, column=i, pady=5)
        
        # Kiválaszt és alkalmaz gomb
        apply_btn = tk.Button(self.root, text="🔧 Kiválaszt és alkalmaz",
                             font=("Arial", 11), bg='#E8E8E8', fg='#888888',
                             command=self.show_photo_editor)
        apply_btn.pack(pady=20)
    
    def show_photo_editor(self):
        """Fő fotószerkesztő nézet"""
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Fő container
        main_frame = tk.Frame(self.root, bg='#C4A484')
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Bal oldali panel - Oldalak
        left_panel = tk.Frame(main_frame, bg='#C4A484', width=200)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        left_panel.pack_propagate(False)
        
        # Oldalak címke
        pages_label = tk.Label(left_panel, text="Oldalak", 
                              font=("Arial", 14, "bold"), bg='#C4A484', fg='white')
        pages_label.pack(pady=10)
        
        # Oldal előnézetek
        for i in range(1, 3):
            page_frame = tk.Frame(left_panel, bg='#E8E8E8', width=180, height=120)
            page_frame.pack(pady=5)
            page_frame.pack_propagate(False)
            
            page_label = tk.Label(page_frame, text=f"{i}. oldal", 
                                 font=("Arial", 8), bg='#E8E8E8', fg='#888888')
            page_label.pack(side=tk.BOTTOM)
        
        # Új oldal hozzáadása gomb
        add_page_frame = tk.Frame(left_panel, bg='#E8E8E8', width=180, height=120)
        add_page_frame.pack(pady=5)
        add_page_frame.pack_propagate(False)
        
        add_btn = tk.Label(add_page_frame, text="+", 
                          font=("Arial", 24), bg='#E8E8E8', fg='#A4B068')
        add_btn.pack(expand=True)
        
        # Középső panel - Fotókönyv
        center_panel = tk.Frame(main_frame, bg='#C4A484')
        center_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        
        # Fotókönyv címke
        book_label = tk.Label(center_panel, text="Fotókönyv", 
                             font=("Arial", 18, "bold"), bg='#C4A484', fg='white')
        book_label.pack(pady=10)
        
        # Fotó területek
        photo_container = tk.Frame(center_panel, bg='#C4A484')
        photo_container.pack(expand=True)
        
        # Két fő fotó terület
        for i in range(2):
            photo_frame = tk.Frame(photo_container, bg='#E8E8E8', width=350, height=250)
            photo_frame.pack(side=tk.LEFT, padx=10, pady=20)
            photo_frame.pack_propagate(False)
            
            # Fotó terület
            photo_area = tk.Frame(photo_frame, bg='#A4B068', width=310, height=200)
            photo_area.pack(pady=20)
            
            if i == 0:
                # Bal oldali fotó beállítások
                controls_frame = tk.Frame(photo_container, bg='#C4A484')
                controls_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10)
                
                # Fotó hozzáadása gomb
                add_photo_btn = tk.Button(controls_frame, text="Fotó hozzáadása ehhez az oldalhoz",
                                         font=("Arial", 9), bg='#E8E8E8', fg='#888888',
                                         command=self.add_photo)
                add_photo_btn.pack(pady=5)
                
                # Méretezés csúszkák
                size_label = tk.Label(controls_frame, text="Méretezés", 
                                     font=("Arial", 10), bg='#C4A484', fg='white')
                size_label.pack(pady=(20, 5))
                
                size_scale = tk.Scale(controls_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                                     bg='#C4A484', fg='white', length=200)
                size_scale.set(35)
                size_scale.pack()
                
                # Pozíció csúszka
                pos_label = tk.Label(controls_frame, text="Pozíció", 
                                    font=("Arial", 10), bg='#C4A484', fg='white')
                pos_label.pack(pady=(20, 5))
                
                pos_scale = tk.Scale(controls_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                                    bg='#C4A484', fg='white', length=200)
                pos_scale.set(35)
                pos_scale.pack()
                
            else:
                # Jobb oldali fotó beállítások
                right_controls = tk.Frame(photo_container, bg='#C4A484')
                right_controls.pack(side=tk.RIGHT, fill=tk.Y, padx=10)
                
                # Háttér beállítás gombok
                bg_buttons = ["Háttér beállítása", "Szöveg hozzáadása", "Keret hozzáadása"]
                for btn_text in bg_buttons:
                    btn = tk.Button(right_controls, text=btn_text,
                                   font=("Arial", 9), bg='#E8E8E8', fg='#888888',
                                   width=15)
                    btn.pack(pady=5)
        
        # Alsó panel - eszköztár
        bottom_panel = tk.Frame(self.root, bg='#C4A484', height=60)
        bottom_panel.pack(side=tk.BOTTOM, fill=tk.X)
        bottom_panel.pack_propagate(False)
        
        # Eszköztár gombok
        toolbar_buttons = ["Mentés", "Betöltés", "Exportálás", "Főmenü"]
        toolbar_frame = tk.Frame(bottom_panel, bg='#C4A484')
        toolbar_frame.pack(expand=True)
        
        for btn_text in toolbar_buttons:
            if btn_text == "Főmenü":
                command = self.create_main_menu
            else:
                command = lambda: None
                
            btn = tk.Button(toolbar_frame, text=btn_text,
                           font=("Arial", 10), bg='#E8E8E8', fg='#888888',
                           command=command)
            btn.pack(side=tk.LEFT, padx=10, pady=15)
    
    def create_layout1(self):
        """Layout 1 alkalmazása"""
        messagebox.showinfo("Layout", "Egy képes layout kiválasztva")
    
    def create_layout2(self):
        """Layout 2 alkalmazása"""
        messagebox.showinfo("Layout", "Két képes layout kiválasztva")
    
    def create_layout3(self):
        """Layout 3 alkalmazása"""
        messagebox.showinfo("Layout", "Négy képes layout kiválasztva")
    
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
    
    def open_project(self):
        """Korábbi projekt megnyitása"""
        self.load_project()

def main():
    root = tk.Tk()
    app = FotokonyvGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()