import customtkinter as ctk # type: ignore
from tkinter import messagebox
import sqlite3
import os
from main_menu import MenuPrincipal  # type: ignore

# --- CONFIGURACIÓN DE RUTA IGUAL AL ARCHIVO PRINCIPAL ---
CARPETA_DB = "Database"
RUTA_DB = os.path.join(CARPETA_DB, "fula_motos.db")

# Configuración de apariencia
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class LoginApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Fula Motos - Inicio de Sesión")
        self.geometry("400x450")
        self.resizable(False, False)

        # Contenedor principal
        self.frame = ctk.CTkFrame(self, corner_radius=15)
        self.frame.pack(pady=40, padx=40, fill="both", expand=True)

        self.label = ctk.CTkLabel(self.frame, text="FULA MOTOS", font=("Roboto", 24, "bold"), text_color="cyan")
        self.label.pack(pady=20)

        self.user_entry = ctk.CTkEntry(self.frame, placeholder_text="Usuario", width=200)
        self.user_entry.pack(pady=12)

        self.pass_entry = ctk.CTkEntry(self.frame, placeholder_text="Contraseña", show="*", width=200)
        self.pass_entry.pack(pady=12)

        self.login_button = ctk.CTkButton(self.frame, text="Entrar", command=self.validar_login, width=200)
        self.login_button.pack(pady=20)
        
        # Opcional: Permitir entrar dando "Enter"
        self.bind('<Return>', lambda event: self.validar_login())

    def validar_login(self):
        usuario = self.user_entry.get().strip()
        clave = self.pass_entry.get().strip()

        # Verificamos que la base de datos exista antes de intentar conectar
        if not os.path.exists(RUTA_DB):
            messagebox.showerror("Error Critico", f"No se encontró la base de datos en:\n{RUTA_DB}\n\nEjecuta primero el inicializador.")
            return

        try:
            conexion = sqlite3.connect(RUTA_DB) # <--- AHORA USA LA RUTA CORRECTA
            cursor = conexion.cursor()
            
            # Buscamos al usuario en la base de datos
            cursor.execute("SELECT rol FROM usuarios WHERE username = ? AND password = ?", (usuario, clave))
            resultado = cursor.fetchone()
            conexion.close()

            if resultado:
                rol_usuario = resultado[0]
                messagebox.showinfo("Éxito", f"Bienvenido {usuario}\nRol: {rol_usuario}")
                
                # Pasamos directo a abrir el menú
                self.abrir_menu_principal(usuario, rol_usuario)
            else:
                messagebox.showerror("Error", "Usuario o contraseña incorrectos")
        except Exception as e:
            messagebox.showerror("Error de Conexión", f"Error al acceder a la BD: {e}")

    def abrir_menu_principal(self, usuario, rol):
        self.destroy()  

        menu = MenuPrincipal(usuario, rol)
        menu.mainloop()

if __name__ == "__main__":
    app = LoginApp()
    app.mainloop()