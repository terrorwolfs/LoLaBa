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
        
        # Itt tárolom a projekt állapotát, meg az oldalakat
        self.current_layout = 1
        self.pages = []
        
        # Most elindítom a főmenüt
        self.create_main_menu()
    
    def create_main_menu(self):
        """Itt készítem el a főmenüt ahonnan mindent el lehet érni"""
        # Először kitörlöm az összes widget-et, hogy tiszta legyen
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Nagy cím a tetején
        title_font = tkfont.Font(family="Arial", size=24, weight="bold")
        title_label = tk.Label(self.root, text="LoLaBa Fotókönyv", 
                              font=title_font, bg='#C4A484', fg='white')
        title_label.pack(pady=50)
        
        subtitle_label = tk.Label(self.root, text="Készíts saját, egyedi fotókönyvet egyszerű lépésekkel!", 
                                 font=("Arial", 12), bg='#C4A484', fg='white')
        subtitle_label.pack(pady=10)
        
        # Itt vannak a főmenü gombjai
        button_frame = tk.Frame(self.root, bg='#C4A484')
        button_frame.pack(pady=50)
        
        # Beállítom a gombok kinézetét
        button_width = 25
        button_height = 2
        button_font = ("Arial", 11)
        
        # Új fotókönyv kezdése
        new_project_btn = tk.Button(button_frame, text="Új projekt létrehozása",
                                   width=button_width, height=button_height,
                                   font=button_font, bg='#E8E8E8', fg='black',
                                   command=self.show_page_selection)
        new_project_btn.pack(pady=10)
        
        # Régi projekt megnyitása
        open_project_btn = tk.Button(button_frame, text="Korábbi projekt megnyitása",
                                    width=button_width, height=button_height,
                                    font=button_font, bg='#E8E8E8', fg='black',
                                    command=self.load_project)
        open_project_btn.pack(pady=10)
        
        # Kilépés a programból
        exit_btn = tk.Button(button_frame, text="Kilépés",
                            width=button_width, height=button_height,
                            font=button_font, bg='#E8E8E8', fg='black',
                            command=self.root.quit)
        exit_btn.pack(pady=10)
    
    def show_project_menu(self):
        """Ez a projekt menü, itt lehet menteni, betölteni stb."""
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Menü gombok egy keretben
        button_frame = tk.Frame(self.root, bg='#C4A484')
        button_frame.pack(expand=True)
        
        button_width = 20
        button_height = 2
        button_font = ("Arial", 11)
        
        # Projekt elmentése
        save_btn = tk.Button(button_frame, text="Projekt mentése",
                            width=button_width, height=button_height,
                            font=button_font, bg='#E8E8E8', fg='black',
                            command=self.save_project)
        save_btn.pack(pady=15)
        
        # Projekt betöltése
        load_btn = tk.Button(button_frame, text="Projekt betöltése",
                            width=button_width, height=button_height,
                            font=button_font, bg='#E8E8E8', fg='black',
                            command=self.load_project)
        load_btn.pack(pady=15)
        
        # Fotókönyv exportálása PDF-be
        export_btn = tk.Button(button_frame, text="Projekt exportálása",
                              width=button_width, height=button_height,
                              font=button_font, bg='#E8E8E8', fg='black',
                              command=self.show_page_selection)
        export_btn.pack(pady=15)
        
        # Vissza a főmenübe
        back_btn = tk.Button(button_frame, text="Vissza a főmenübe",
                            width=button_width, height=button_height,
                            font=button_font, bg='#E8E8E8', fg='black',
                            command=self.create_main_menu)
        back_btn.pack(pady=15)
    
    def show_page_selection(self):
        """Itt lehet kiválasztani hogy hány kép legyen egy oldalon"""
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Cím a lap tetején
        title_label = tk.Label(self.root, text="Oldalnézet kiválasztása", 
                              font=("Arial", 18, "bold"), bg='#C4A484', fg='white')
        title_label.pack(pady=30)
        
        # Itt lesznek a layout opciók
        layout_frame = tk.Frame(self.root, bg='#C4A484')
        layout_frame.pack(expand=True)
        
        # 3 féle layout: 1, 2 vagy 4 kép
        layouts = [
            ("1 kép", lambda: self.select_layout(1)),
            ("2 kép", lambda: self.select_layout(2)), 
            ("4 kép", lambda: self.select_layout(4))
        ]
        
        layout_container = tk.Frame(layout_frame, bg='#C4A484')
        layout_container.pack()
        
        for i, (text, command) in enumerate(layouts):
            # Layout előnézeti keret
            preview_frame = tk.Frame(layout_container, bg='#E8E8E8', width=200, height=150)
            preview_frame.grid(row=0, column=i, padx=20, pady=10)
            preview_frame.pack_propagate(False)
            
            # Itt mutatom meg hogy néz ki az adott layout
            if i == 0:
                # Egy nagy kép az egész oldalon
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
                # Négy kis kép 2x2-es elrendezésben
                img_container = tk.Frame(preview_frame, bg='#E8E8E8')
                img_container.pack(pady=15)
                for row in range(2):
                    for col in range(2):
                        img = tk.Frame(img_container, bg='#A4B068', width=60, height=35)
                        img.grid(row=row, column=col, padx=3, pady=3)
            
            # Layout neve alul
            select_label = tk.Label(layout_container, text=text, 
                                   font=("Arial", 10), bg='#C4A484', fg='white')
            select_label.grid(row=1, column=i, pady=5)
            
            # Ha rákattintanak akkor kiválasztódik
            preview_frame.bind("<Button-1>", lambda e, cmd=command: cmd())
            for child in preview_frame.winfo_children():
                child.bind("<Button-1>", lambda e, cmd=command: cmd())
        
        # Ezzel a gombbal lehet továbblépni
        apply_btn = tk.Button(self.root, text="🔧 Kiválaszt és alkalmaz",
                             font=("Arial", 11), bg='#E8E8E8', fg='black',
                             command=self.show_photo_editor)
        apply_btn.pack(pady=20)
    
    def show_photo_editor(self):
        """Itt történik a varázslat - ide lehet fotókat rakni és szerkeszteni"""
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Fő tároló az egész szerkesztőnek
        main_frame = tk.Frame(self.root, bg='#C4A484')
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Bal oldal - itt látszanak az oldalak
        left_panel = tk.Frame(main_frame, bg='#C4A484', width=200)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        left_panel.pack_propagate(False)
        
        # Oldalak címe
        pages_label = tk.Label(left_panel, text="Oldalak", 
                              font=("Arial", 14, "bold"), bg='#C4A484', fg='white')
        pages_label.pack(pady=10)
        
        # Itt látszanak az oldalak kis előnézetben
        for i in range(1, 3):
            page_frame = tk.Frame(left_panel, bg='#E8E8E8', width=180, height=120)
            page_frame.pack(pady=5)
            page_frame.pack_propagate(False)
            
            page_label = tk.Label(page_frame, text=f"{i}. oldal", 
                                 font=("Arial", 8), bg='#E8E8E8', fg='black')
            page_label.pack(side=tk.BOTTOM)
        
        # Új oldal hozzáadása gomb (+ jel)
        add_page_frame = tk.Frame(left_panel, bg='#E8E8E8', width=180, height=120)
        add_page_frame.pack(pady=5)
        add_page_frame.pack_propagate(False)
        
        add_btn = tk.Label(add_page_frame, text="+", 
                          font=("Arial", 24), bg='#E8E8E8', fg='#A4B068', cursor="hand2")
        add_btn.pack(expand=True)
        add_btn.bind("<Button-1>", lambda e: self.add_new_page())
        
        # Középső rész - itt szerkesztem a fotókönyvet
        center_panel = tk.Frame(main_frame, bg='#C4A484')
        center_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        
        # Fotókönyv címe
        book_label = tk.Label(center_panel, text="Fotókönyv", 
                             font=("Arial", 18, "bold"), bg='#C4A484', fg='white')
        book_label.pack(pady=10)
        
        # Itt vannak a fotók helye
        photo_container = tk.Frame(center_panel, bg='#C4A484')
        photo_container.pack(expand=True)
        
        # Két oldal a fotókönyvben
        for i in range(2):
            photo_frame = tk.Frame(photo_container, bg='#E8E8E8', width=350, height=250)
            photo_frame.pack(side=tk.LEFT, padx=10, pady=20)
            photo_frame.pack_propagate(False)
            
            # Itt lesz a fotó
            photo_area = tk.Frame(photo_frame, bg='#A4B068', width=310, height=200)
            photo_area.pack(pady=20)
            
            if i == 0:
                # Bal oldali fotó beállításai
                controls_frame = tk.Frame(photo_container, bg='#C4A484')
                controls_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10)
                
                # Fotó feltöltése gomb
                add_photo_btn = tk.Button(controls_frame, text="Fotó hozzáadása ehhez az oldalhoz",
                                         font=("Arial", 9), bg='#E8E8E8', fg='black',
                                         command=self.add_photo)
                add_photo_btn.pack(pady=5)
                
                # Méret állítása csúszkával
                size_label = tk.Label(controls_frame, text="Méretezés", 
                                     font=("Arial", 10), bg='#C4A484', fg='white')
                size_label.pack(pady=(20, 5))
                
                size_scale = tk.Scale(controls_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                                     bg='#C4A484', fg='white', length=200)
                size_scale.set(35)
                size_scale.pack()
                
                # Pozíció állítása csúszkával
                pos_label = tk.Label(controls_frame, text="Pozíció", 
                                    font=("Arial", 10), bg='#C4A484', fg='white')
                pos_label.pack(pady=(20, 5))
                
                pos_scale = tk.Scale(controls_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                                    bg='#C4A484', fg='white', length=200)
                pos_scale.set(35)
                pos_scale.pack()
                
            else:
                # Jobb oldali fotó extra beállításai
                right_controls = tk.Frame(photo_container, bg='#C4A484')
                right_controls.pack(side=tk.RIGHT, fill=tk.Y, padx=10)
                
                # Extra funkciók gombjai
                bg_buttons = ["Háttér beállítása", "Szöveg hozzáadása", "Keret hozzáadása"]
                for btn_text in bg_buttons:
                    btn = tk.Button(right_controls, text=btn_text,
                                   font=("Arial", 9), bg='#E8E8E8', fg='black',
                                   width=15)
                    btn.pack(pady=5)
        
        # Alsó eszköztár
        bottom_panel = tk.Frame(self.root, bg='#C4A484', height=60)
        bottom_panel.pack(side=tk.BOTTOM, fill=tk.X)
        bottom_panel.pack_propagate(False)
        
        # Fontos gombok alul (mentés, betöltés stb.)
        toolbar_buttons = [
            ("Mentés", self.save_project),
            ("Betöltés", self.load_project), 
            ("Exportálás", self.export_project),
            ("Főmenü", self.create_main_menu)
        ]
        toolbar_frame = tk.Frame(bottom_panel, bg='#C4A484')
        toolbar_frame.pack(expand=True)
        
        for btn_text, command in toolbar_buttons:
            btn = tk.Button(toolbar_frame, text=btn_text,
                           font=("Arial", 10), bg='#E8E8E8', fg='black',
                           command=command)
            btn.pack(side=tk.LEFT, padx=10, pady=15)
    
    def select_layout(self, layout_type):
        """Kiválasztja hogy milyen layout legyen (hány kép)"""
        layout_names = {1: "egy képes", 2: "két képes", 4: "négy képes"}
        messagebox.showinfo("Layout", f"{layout_names[layout_type]} layout kiválasztva")
        # Itt állítom be a layout típusát
        self.current_layout = layout_type
    
    def add_new_page(self):
        """Új oldalt ad hozzá a fotókönyvhöz"""
        messagebox.showinfo("Új oldal", "Új oldal hozzáadva a fotókönyvhöz!")
        # Itt csinálnám meg az új oldal létrehozását
    
    def create_layout1(self):
        """Layout 1 használata - ezt még régebben csináltam"""
        self.select_layout(1)
    
    def create_layout2(self):
        """Layout 2 használata - ezt még régebben csináltam"""
        self.select_layout(2)
    
    def create_layout3(self):
        """Layout 3 használata - ezt még régebben csináltam"""
        self.select_layout(4)
    
    def add_photo(self):
        """Fotót ad hozzá a projekthez"""
        filename = filedialog.askopenfilename(
            title="Válassz fotót",
            filetypes=[("Képfájlok", "*.jpg *.jpeg *.png *.gif *.bmp")]
        )
        if filename:
            messagebox.showinfo("Fotó", f"Fotó hozzáadva: {os.path.basename(filename)}")
    
    def save_project(self):
        """Elmenti a projektet fájlba"""
        filename = filedialog.asksaveasfilename(
            title="Projekt mentése",
            defaultextension=".lolaba",
            filetypes=[("LoLaBa projekt", "*.lolaba"), ("Minden fájl", "*.*")]
        )
        if filename:
            messagebox.showinfo("Mentés", f"Projekt mentve: {os.path.basename(filename)}")
    
    def load_project(self):
        """Betölt egy korábban mentett projektet"""
        filename = filedialog.askopenfilename(
            title="Projekt betöltése",
            filetypes=[("LoLaBa projekt", "*.lolaba"), ("Minden fájl", "*.*")]
        )
        if filename:
            messagebox.showinfo("Betöltés", f"Projekt betöltve: {os.path.basename(filename)}")
            # ha sikerült betölteni akkor rögtön a szerkesztőbe lépek
            self.show_photo_editor()
    
    def export_project(self):
        """Exportálja a kész fotókönyvet PDF formátumban"""
        filename = filedialog.asksaveasfilename(
            title="Projekt exportálása",
            defaultextension=".pdf",
            filetypes=[("PDF fájl", "*.pdf"), ("Minden fájl", "*.*")]
        )
        if filename:
            messagebox.showinfo("Exportálás", f"Projekt exportálva: {os.path.basename(filename)}")

def main():
    root = tk.Tk()
    app = FotokonyvGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
