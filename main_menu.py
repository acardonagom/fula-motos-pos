import customtkinter as ctk  # type: ignore
import sqlite3
from datetime import date
from tkinter import messagebox
import pandas as pd  # type: ignore
from tkinter import filedialog
import shutil
from fpdf import FPDF
from PIL import Image, ImageTk
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CARPETA_DB = os.path.join(BASE_DIR, "Database")
RUTA_DB = os.path.join(CARPETA_DB, "fula_motos.db")

def asegurar_tablas_existentes():

    if not os.path.exists(CARPETA_DB):
        os.makedirs(CARPETA_DB)
        
    conexion = sqlite3.connect(RUTA_DB)
    cursor = conexion.cursor()
    
    # --- TUS TABLAS ORIGINALES DE VENTAS ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS facturas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            consecutivo TEXT UNIQUE,
            tipo_documento TEXT,
            fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
            documento_cliente TEXT,
            placa_moto TEXT,
            marca_moto TEXT,
            subtotal REAL,
            descuento REAL DEFAULT 0,
            total REAL,
            metodo_pago TEXT,
            monto_pagado REAL,
            saldo_pendiente REAL,
            estado TEXT,
            id_usuario INTEGER
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS detalles_factura (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_factura INTEGER,
            tipo_item TEXT,
            id_item INTEGER,
            descripcion TEXT,
            cantidad INTEGER,
            precio_unitario REAL,
            subtotal REAL,
            FOREIGN KEY(id_factura) REFERENCES facturas(id)
        )
    ''')
    
    # --- NUEVAS TABLAS: PROVEEDORES Y COMPRAS ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS proveedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE,
            telefono TEXT,
            limite_credito REAL DEFAULT 0
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS compras_facturas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proveedor TEXT,
            num_factura TEXT,
            fecha_ingreso DATETIME DEFAULT (datetime('now', 'localtime')),
            fecha_limite_descuento DATE,
            fecha_vencimiento_final DATE,
            total_normal REAL,
            total_con_descuento REAL,
            saldo_pendiente REAL,
            estado TEXT DEFAULT 'Pendiente', 
            inventario_cargado INTEGER DEFAULT 0
        )
    """)
    
    conexion.commit()
    conexion.close()
    print("✅ Tablas de facturación y proveedores verificadas.")
class MenuPrincipal(ctk.CTk):
    def __init__(self, usuario, rol):
        super().__init__()
        asegurar_tablas_existentes()
        # 1. ASIGNACIÓN DE SESIÓN
        self.usuario_actual = usuario
        self.rol = rol
        
        # 2. CONFIGURAR VENTANA
        nombre_mostrar = self.usuario_actual[1] if isinstance(self.usuario_actual, (list, tuple)) else self.usuario_actual
        self.title(f"Fula Motos - Centro de Mandos | {nombre_mostrar} ({self.rol})")
        self.geometry("1200x750") # Un poco más de espacio para el Dashboard

        # --- CONFIGURAR ÍCONO DE LA APLICACIÓN ---
        try:
            carpeta_actual = os.path.dirname(os.path.abspath(__file__))
            ruta_icono = os.path.join(carpeta_actual, "recursos", "lc logo.ico") 
            
            if os.path.exists(ruta_icono):
                self.iconbitmap(ruta_icono)
        except Exception as e:
            print(f"Aviso: No se pudo cargar el ícono ({e})")
        
        # --- MENÚ LATERAL (SIDEBAR) ---
        self.menu_lateral = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.menu_lateral.pack(side="left", fill="y")

        self.label_logo = ctk.CTkLabel(self.menu_lateral, text="FULA MOTOS", font=("Roboto", 22, "bold"), text_color="cyan")
        self.label_logo.pack(pady=30, padx=20)

        # --- SECCIÓN: TALLER ---
        # Cambiamos 'abrir_modulo_taller' por 'abrir_modulo_vehiculos' (que es la que ya tienes)
        self.btn_vehiculos = ctk.CTkButton(self.menu_lateral, text="🏍️ Vehículos y Taller", anchor="w", command=self.abrir_modulo_vehiculos) # <--- NOMBRE REAL
        self.btn_vehiculos.pack(pady=5, padx=10, fill="x")

        self.btn_hist_motos = ctk.CTkButton(self.menu_lateral, text="   └ 🕒 Histórico Motos", anchor="w", fg_color="transparent", hover_color="#34495E", command=self.abrir_historico_motos) 
        self.btn_hist_motos.pack(pady=2, padx=10, fill="x")

        # --- SECCIÓN: BODEGA ---
        self.btn_inventario = ctk.CTkButton(self.menu_lateral, text="📦 Inventario", anchor="w", command=self.abrir_modulo_inventario)
        self.btn_inventario.pack(pady=10, padx=10, fill="x")

        # --- SECCIÓN: VENTAS ---
        self.btn_facturacion = ctk.CTkButton(self.menu_lateral, text="💰 Facturación (POS)", anchor="w", command=self.abrir_modulo_facturacion)
        self.btn_facturacion.pack(pady=5, padx=10, fill="x")

        self.btn_hist_facturas = ctk.CTkButton(self.menu_lateral, text="   └ 📄 Historial Facturas", anchor="w", fg_color="transparent", 
                                               hover_color="#34495E", command=self.abrir_historial_facturas)
        self.btn_hist_facturas.pack(pady=2, padx=10, fill="x")

        # --- SECCIÓN: GERENCIA (Admin) ---
        self.btn_nomina = ctk.CTkButton(self.menu_lateral, text="📊 Nómina y Comisiones", anchor="w", command=self.abrir_nominas_admin)
        self.btn_nomina.pack(pady=10, padx=10, fill="x")
        self.btn_hist_nomina = ctk.CTkButton(self.menu_lateral, text="   └ 📜 Historial Pagos", anchor="w", 
                                             fg_color="transparent", hover_color="#34495E", 
                                             command=self.abrir_historial_pagos_nomina)
        
        self.btn_usuarios = ctk.CTkButton(self.menu_lateral, text="👥 Gestionar Usuarios", anchor="w",
                                          fg_color="#8E44AD", hover_color="#732D91",
                                          command=self.abrir_gestion_usuarios)

        # Dashboard de últimas antes del botón salir
        self.btn_dashboard = ctk.CTkButton(self.menu_lateral, text="📈 Dashboard Gerencial", anchor="w", 
                                            fg_color="#1A5276", hover_color="#21618C", command=self.abrir_dashboard_admin)
        self.btn_dashboard.pack(pady=10, padx=10, fill="x")
        
# --- SECCIÓN: PROVEEDORES (Cuentas por Pagar) ---
        self.btn_proveedores = ctk.CTkButton(self.menu_lateral, text="🏢 Proveedores (CXP)", anchor="w", 
                                             fg_color="#D35400", hover_color="#A04000", 
                                             command=self.abrir_modulo_proveedores)

        # --- BOTÓN SALIR ---
        self.btn_salir = ctk.CTkButton(self.menu_lateral, text="🚪 Cerrar Sesión", fg_color="#C0392B", hover_color="#922B21", command=self.destroy)
        self.btn_salir.pack(side="bottom", pady=20, padx=20, fill="x")

        # --- ÁREA DE TRABAJO ---
        self.area_principal = ctk.CTkFrame(self, corner_radius=15)
        self.area_principal.pack(side="right", fill="both", expand=True, padx=15, pady=15)

        self.label_bienvenida = ctk.CTkLabel(self.area_principal, text=f"Bienvenido, {nombre_mostrar}", font=("Roboto", 24, "bold"))
        self.label_bienvenida.pack(pady=50)

        # Aplicar permisos inmediatamente
        self.configurar_permisos()

    def configurar_permisos(self):
        """Matriz de seguridad"""
       # Reset: ocultamos botones administrativos por defecto
        self.btn_nomina.pack_forget()
        self.btn_dashboard.pack_forget()
        self.btn_usuarios.pack_forget()
        self.btn_hist_nomina.pack_forget()
        self.btn_proveedores.pack_forget()

        if self.rol == "Tecnico":
            # Técnico: Solo Taller y su Histórico
            self.btn_facturacion.pack_forget()
            self.btn_hist_facturas.pack_forget()
            
        elif self.rol == "Vendedor":
            self.btn_vehiculos.pack_forget() # No ve taller ni histórico de motos
            self.btn_hist_motos.pack_forget() # No ve histórico de motos
            # Vendedor: No ve nómina ni dashboard, pero sí facturación y taller (para despacho)
            # Ya el reset inicial ocultó nómina y dashboard.
            # Según tu regla: No entra a Diagnóstico profundo, pero sí al historial para cobrar.
            pass 
            
        elif self.rol == "Admin":
            
            self.btn_usuarios.pack(pady=10, padx=10, fill="x")
            self.btn_nomina.pack(pady=10, padx=10, fill="x")
            self.btn_hist_nomina.pack(pady=2, padx=10, fill="x")
            self.btn_dashboard.pack(pady=10, padx=10, fill="x")
            self.btn_proveedores.pack(pady=10, padx=10, fill="x")
            self.btn_salir.pack_forget() # Lo quitamos un momento para re-ubicarlo al fondo
            self.btn_salir.pack(side="bottom", pady=20, padx=20, fill="x")

    # ==========================================
    # MÓDULO: VEHÍCULOS E HISTORIAL
    # ==========================================
    def abrir_modulo_vehiculos(self):
        for widget in self.area_principal.winfo_children():
            widget.destroy()

        self.frame_scroll_principal = ctk.CTkScrollableFrame(self.area_principal, fg_color="transparent")
        self.frame_scroll_principal.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(self.frame_scroll_principal, text="Registro de Ingreso y Diagnóstico", 
                     font=("Roboto", 20, "bold")).pack(pady=(10, 20), anchor="n")

        frame_form = ctk.CTkFrame(self.frame_scroll_principal, fg_color="transparent")
        frame_form.pack(pady=10, anchor="n") 

        self.entry_placa = ctk.CTkEntry(frame_form, placeholder_text="Placa (Ej: XYZ12A)", width=400)
        self.entry_placa.pack(pady=5)
        self.entry_placa.bind("<KeyRelease>", self.autocompletar_datos_moto)

        frame_moto = ctk.CTkFrame(frame_form, fg_color="transparent")
        frame_moto.pack(pady=5)
        self.entry_marca = ctk.CTkEntry(frame_moto, placeholder_text="Marca (Ej: Yamaha)", width=195)
        self.entry_marca.pack(side="left", padx=(0, 10))
        self.entry_modelo = ctk.CTkEntry(frame_moto, placeholder_text="Modelo (Ej: 2024 / R3)", width=195)
        self.entry_modelo.pack(side="left")

        # --- AQUÍ ESTÁ EL CAMBIO: TRES CAJONES EN UNA FILA ---
        frame_cliente = ctk.CTkFrame(frame_form, fg_color="transparent")
        frame_cliente.pack(pady=5)
        self.entry_cedula = ctk.CTkEntry(frame_cliente, placeholder_text="Cédula / NIT", width=110)
        self.entry_cedula.pack(side="left", padx=(0, 10))
        self.entry_cliente = ctk.CTkEntry(frame_cliente, placeholder_text="Nombre del Cliente", width=150)
        self.entry_cliente.pack(side="left", padx=(0, 10))
        self.entry_telefono = ctk.CTkEntry(frame_cliente, placeholder_text="Teléfono", width=120)
        self.entry_telefono.pack(side="left")

        self.entry_kilometraje = ctk.CTkEntry(frame_form, placeholder_text="Kilometraje Actual (KM)", width=400)
        self.entry_kilometraje.pack(pady=5)

        self.txt_diagnostico = ctk.CTkTextbox(frame_form, width=400, height=100)
        self.txt_diagnostico.pack(pady=5)
        self.txt_diagnostico.insert("0.0", "Descripción del daño o mantenimiento...")

        self.entry_mano_obra = ctk.CTkEntry(frame_form, placeholder_text="Valor Mano de Obra ($)", width=400)
        self.entry_mano_obra.pack(pady=5)

        self.btn_guardar = ctk.CTkButton(frame_form, text="✅ Guardar Servicio", 
                                         fg_color="green", hover_color="#228B22",
                                         command=self.guardar_servicio, width=200)
        self.btn_guardar.pack(pady=20)

        # --- SECCIÓN HISTORIAL (Buscador) ---
        ctk.CTkLabel(self.frame_scroll_principal, text="--- CONSULTAR HISTORIAL ---", 
                     font=("Roboto", 16, "bold")).pack(pady=(30, 10), anchor="n")
        
        frame_busqueda = ctk.CTkFrame(self.frame_scroll_principal)
        frame_busqueda.pack(pady=5, padx=20, fill="x", anchor="n")
        
        self.ent_historial_placa = ctk.CTkEntry(frame_busqueda, placeholder_text="Escribe la placa para buscar historial...")
        self.ent_historial_placa.pack(side="left", padx=10, pady=10, expand=True, fill="x")
        self.ent_historial_placa.bind("<KeyRelease>", self.sugerir_placas)
        
        ctk.CTkButton(frame_busqueda, text="📜 Ver Historial", command=self.ver_historial_moto, width=150).pack(side="right", padx=10)

        self.frame_sugerencias = ctk.CTkFrame(self.frame_scroll_principal, fg_color="transparent")
        self.frame_sugerencias.pack(padx=20, fill="x", anchor="n")

        self.area_historial = ctk.CTkFrame(self.frame_scroll_principal, fg_color="transparent")
        self.area_historial.pack(pady=10, padx=20, fill="both", expand=True)

    def abrir_historico_motos(self):
        """Construye la interfaz gráfica del historial y luego carga los datos"""
        # 1. Limpiamos la pantalla principal
        for widget in self.area_principal.winfo_children():
            widget.destroy()

        # 2. Título Principal
        ctk.CTkLabel(self.area_principal, text="🕒 HISTÓRICO GENERAL DE MOTOS", 
                     font=("Roboto", 24, "bold"), text_color="cyan").pack(pady=20)

        # 3. Barra de Búsqueda 
        frame_busqueda = ctk.CTkFrame(self.area_principal, fg_color="transparent")
        frame_busqueda.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(frame_busqueda, text="🔍 Buscar por Placa:", font=("Roboto", 14)).pack(side="left", padx=5)
        
        self.ent_historial_placa = ctk.CTkEntry(frame_busqueda, placeholder_text="Ej: ABC12D", width=150)
        self.ent_historial_placa.pack(side="left", padx=5)
        self.ent_historial_placa.bind("<KeyRelease>", lambda event: self.ver_historial_moto())  # Búsqueda en vivo al escribir
        
        # Botón para buscar una placa específica
        ctk.CTkButton(frame_busqueda, text="Buscar", width=100, fg_color="#2980B9", 
                      command=self.ver_historial_moto).pack(side="left", padx=10)
        
        # Botón para limpiar y ver todas de nuevo
        ctk.CTkButton(frame_busqueda, text="Ver Todas", width=100, fg_color="#7F8C8D", 
                      command=lambda: [self.ent_historial_placa.delete(0, 'end'), self.ver_historial_moto()]).pack(side="left", padx=5)

        # 4. El Contenedor donde van a aparecer las tarjetas (El Scrollable)
        self.area_historial = ctk.CTkScrollableFrame(self.area_principal, fg_color="transparent")
        self.area_historial.pack(fill="both", expand=True, padx=10, pady=10)

        # 5. EL GATILLO FINAL: Mandamos a llamar la base de datos automáticamente
        self.ver_historial_moto()

    def ver_historial_moto(self):
        placa = self.ent_historial_placa.get().upper().strip()

        for widget in self.area_historial.winfo_children():
            widget.destroy()

        try:
            conexion = sqlite3.connect(RUTA_DB)
            cursor = conexion.cursor()
            
            if placa:
                query = """
                    SELECT s.id, s.fecha_ingreso, s.marca_moto, s.modelo_moto, s.cliente_nombre, s.cliente_telefono,
                           s.diagnostico, s.valor_mano_obra, u.username, s.estado, s.placa_moto
                    FROM servicios s
                    LEFT JOIN usuarios u ON s.id_usuario = u.id 
                    WHERE s.placa_moto LIKE ?
                    ORDER BY s.fecha_ingreso DESC
                """
                cursor.execute(query, (f"%{placa}%",))
            else:
                query = """
                    SELECT s.id, s.fecha_ingreso, s.marca_moto, s.modelo_moto, s.cliente_nombre, s.cliente_telefono,
                           s.diagnostico, s.valor_mano_obra, u.username, s.estado, s.placa_moto
                    FROM servicios s
                    LEFT JOIN usuarios u ON s.id_usuario = u.id 
                    ORDER BY s.fecha_ingreso DESC
                """
                cursor.execute(query)

            servicios = cursor.fetchall()

            if not servicios:
                ctk.CTkLabel(self.area_historial, text="No hay registros en el historial.", text_color="gray").pack(pady=20)
                return

            for s_id, fecha, marca, modelo, cliente, tel, diag, mano_obra, tec, estado, placa_db in servicios:
                card = ctk.CTkFrame(self.area_historial, border_width=1, border_color="#5D6D7E")
                card.pack(pady=10, fill="x", padx=10)

                # Procesamiento de textos
                cli_m = cliente if (cliente and cliente.strip()) else "Cliente Particular"
                tel_m = tel if (tel and tel.strip()) else "Sin Teléfono"
                fec_m = fecha if fecha else "S/F"
                mar_m = marca if marca else ""
                mod_m = modelo if modelo else ""
                tec_m = tec.upper() if tec else "ANTIGUO / NO ASIGNADO"
                
                header_frame = ctk.CTkFrame(card, fg_color="transparent")
                header_frame.pack(fill="x", padx=10, pady=5)
                
                txt_header = f"📅 {fec_m} | 👤 {cli_m} (📱 {tel_m}) | 🏍️ [{placa_db}] {mar_m} {mod_m}"
                ctk.CTkLabel(header_frame, text=txt_header, font=("Roboto", 13, "bold")).pack(side="left")
                
                # --- AQUÍ VA EL BOTÓN DE ELIMINAR (SOLO PARA ADMIN) ---
                if hasattr(self, 'rol') and self.rol == "Admin":
                    btn_del = ctk.CTkButton(header_frame, text="🗑️", width=30, fg_color="#C0392B", hover_color="#7B241C",
                                            command=lambda id_s=s_id: self.eliminar_registro_historial(id_s))
                    btn_del.pack(side="right", padx=(10, 0))
                # -------------------------------------------------------

                color_estado = "#2ECC71" if estado == "Terminado" else "#E74C3C"
                ctk.CTkLabel(header_frame, text=f" {estado} ", fg_color=color_estado, corner_radius=5, text_color="white").pack(side="right")

                # --- REPUESTOS ---
                cursor.execute("""
                    SELECT i.nombre_repuesto, sr.cantidad, sr.precio_unitario
                    FROM servicios_repuestos sr
                    JOIN inventario i ON sr.id_repuesto = i.id
                    WHERE sr.id_servicio = ?
                """, (s_id,))
                repuestos = cursor.fetchall()
                
                total_r = 0
                if repuestos:
                    ctk.CTkLabel(card, text="📦 Repuestos:", font=("Roboto", 11, "bold"), text_color="cyan").pack(anchor="w", padx=15)
                    for r_nom, r_cant, r_prec in repuestos:
                        sub = r_cant * r_prec
                        total_r += sub
                        ctk.CTkLabel(card, text=f" • {r_nom} (x{r_cant}) - ${sub:,.0f}").pack(anchor="w", padx=25)

                # --- NUEVO: MOSTRAR MANO DE OBRA EN LA LISTA ---
                mo_val = mano_obra if mano_obra else 0
                
                # Le damos un pequeño margen superior si ya hay repuestos arriba
                margen_sup = 10 if repuestos else 0 
                
                ctk.CTkLabel(card, text="🔧 Servicio:", font=("Roboto", 11, "bold"), text_color="#F39C12").pack(anchor="w", padx=15, pady=(margen_sup, 0))
                ctk.CTkLabel(card, text=f" • Mano de Obra - ${mo_val:,.0f}").pack(anchor="w", padx=25)

                # --- TOTALES Y TÉCNICO ---
                resumen_f = ctk.CTkFrame(card, fg_color="#2A2A2A", corner_radius=5)
                resumen_f.pack(fill="x", padx=10, pady=10) # Le di un poco más de pady para que respire
                
                txt_footer = f"🛠️ Técnico: {tec_m} | 💰 TOTAL SERVICIO: ${(mo_val + total_r):,.0f}"
                ctk.CTkLabel(resumen_f, text=txt_footer, text_color="#2ECC71", font=("Roboto", 12, "bold")).pack(pady=5)

                # --- DIAGNÓSTICO ---
                ctk.CTkLabel(card, text=f"📝 Diagnóstico:\n{diag}", wraplength=750, justify="left").pack(anchor="w", padx=15, pady=(0, 10))
            
            conexion.close()
            
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Error", f"Error al cargar historial: {e}") 
    
    def eliminar_registro_historial(self, id_servicio):
        """Elimina un servicio del historial y sus repuestos asociados (Solo Admin)"""
        from tkinter import messagebox
        import sqlite3
        
        if messagebox.askyesno("Confirmar Acción", "⚠️ ¿Estás seguro de que deseas eliminar este registro del historial?\n\nEsta acción no se puede deshacer y borrará también los repuestos asociados a este servicio."):
            try:
                conn = sqlite3.connect(RUTA_DB)
                cursor = conn.cursor()
                
                # 1. Borramos los repuestos asociados a este servicio primero
                cursor.execute("DELETE FROM servicios_repuestos WHERE id_servicio = ?", (id_servicio,))
                
                # 2. Borramos el registro principal del servicio
                cursor.execute("DELETE FROM servicios WHERE id = ?", (id_servicio,))
                
                conn.commit()
                conn.close()
                
                # Recargamos la pestaña para que el cuadro desaparezca al instante
                self.ver_historial_moto()
                messagebox.showinfo("Éxito", "El registro ha sido eliminado correctamente.")
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo eliminar el registro: {e}")

    def autocompletar_datos_moto(self, event):
        placa = self.entry_placa.get().upper().strip()
        
        # Solo buscamos si la placa tiene un tamaño lógico
        if len(placa) >= 5:
            try:
                conexion = sqlite3.connect(RUTA_DB)
                cursor = conexion.cursor()
                
                # --- MAGIA SQL: Traemos los datos de la moto Y la última cédula usada ---
                cursor.execute("""
                    SELECT v.marca, v.modelo, v.propietario, v.telefono,
                           (SELECT documento_cliente FROM servicios s WHERE s.placa_moto = v.placa AND documento_cliente IS NOT NULL ORDER BY id DESC LIMIT 1)
                    FROM vehiculos v 
                    WHERE v.placa = ?
                """, (placa,))
                moto = cursor.fetchone()
                conexion.close()

                if moto:
                    marca, modelo, propietario, telefono, documento = moto
                    
                    # Rellenar Marca y Modelo a la fuerza (son fijos)
                    self.entry_marca.delete(0, 'end')
                    if marca: self.entry_marca.insert(0, marca)
                    
                    self.entry_modelo.delete(0, 'end')
                    if modelo: self.entry_modelo.insert(0, modelo)
                    
                    # Rellenar Cliente, Teléfono y Cédula solo si están vacíos 
                    self.entry_cliente.delete(0, 'end')
                    if propietario: self.entry_cliente.insert(0, propietario)
                        
                    self.entry_telefono.delete(0, 'end')
                    if telefono: self.entry_telefono.insert(0, telefono)

                    # --- NUEVO: Rellenar la Cédula automáticamente ---
                    if hasattr(self, 'entry_cedula'):
                        self.entry_cedula.delete(0, 'end')
                        if documento: self.entry_cedula.insert(0, documento)
                        
            except Exception as e:
                pass # Si hay error buscando en vivo, simplemente no interrumpe al usuario

    def sugerir_placas(self, event):
        texto = self.ent_historial_placa.get().upper().strip()

        # Limpiar sugerencias anteriores
        for widget in self.frame_sugerencias.winfo_children():
            widget.destroy()

        if len(texto) < 1:
            return  # No buscar si está vacío

        try:
            conexion = sqlite3.connect(RUTA_DB)
            cursor = conexion.cursor()
            # Buscar placas que coincidan con lo escrito (Máximo 5 sugerencias)
            cursor.execute("SELECT DISTINCT placa FROM vehiculos WHERE placa LIKE ? LIMIT 5", ('%'+texto+'%',))
            resultados = cursor.fetchall()
            conexion.close()

            for (placa_sug,) in resultados:
                btn = ctk.CTkButton(self.frame_sugerencias, text=f"🔍 {placa_sug}", 
                                    fg_color="#333333", hover_color="#555555", anchor="w",
                                    command=lambda p=placa_sug: self.seleccionar_sugerencia(p))
                btn.pack(fill="x", pady=1)
        except Exception as e:
            pass # Ignorar errores menores de consulta en vivo

    def seleccionar_sugerencia(self, placa):
        self.ent_historial_placa.delete(0, 'end')
        self.ent_historial_placa.insert(0, placa)
        for widget in self.frame_sugerencias.winfo_children():
            widget.destroy()
        self.ver_historial_moto() # Lanza la búsqueda automáticamente

    def guardar_servicio(self):
        if not hasattr(self, 'usuario_actual') or self.usuario_actual is None:
            from tkinter import messagebox
            messagebox.showerror("Error de Sesión", "No se detectó un usuario activo.")
            return
        
        placa = self.entry_placa.get().upper().strip()
        marca_hoy = self.entry_marca.get().strip()
        modelo_hoy = self.entry_modelo.get().strip()
        # --- NUEVA VARIABLE CEDULA (Si la dejan vacía, asume 000000000) ---
        cedula_hoy = self.entry_cedula.get().strip() or "000000000"
        cliente_hoy = self.entry_cliente.get().strip()
        telefono_hoy = self.entry_telefono.get().strip()
        kilometraje_hoy = self.entry_kilometraje.get().strip() or "0"
        diagnostico_nuevo = self.txt_diagnostico.get("1.0", "end-1c").strip()

        if not placa:
            from tkinter import messagebox
            messagebox.showwarning("Atención", "La placa es obligatoria.")
            return

        try:
            val_mo = self.entry_mano_obra.get().replace(".", "").replace(",", "")
            mano_obra_float = float(val_mo) if val_mo else 0.0
            
            conexion = sqlite3.connect(RUTA_DB)
            cursor = conexion.cursor()

            if isinstance(self.usuario_actual, (list, tuple)):
                id_tec = self.usuario_actual[0]
                nombre_tecnico = self.usuario_actual[1]
            else:
                nombre_tecnico = str(self.usuario_actual)
                cursor.execute("SELECT id FROM usuarios WHERE username = ?", (nombre_tecnico,))
                res = cursor.fetchone()
                id_tec = res[0] if res else 1

            # Mantenemos el catálogo de Vehículos actualizado
            cursor.execute("""
                INSERT OR REPLACE INTO vehiculos (placa, marca, modelo, propietario, telefono)
                VALUES (?, ?, ?, ?, ?)
            """, (placa, marca_hoy, modelo_hoy, cliente_hoy, telefono_hoy))

            # --- NUEVA MAGIA: Guardar o Actualizar al CLIENTE en la tabla clientes ---
            cursor.execute("""
                INSERT OR REPLACE INTO clientes (documento, nombre, telefono)
                VALUES (?, ?, ?)
            """, (cedula_hoy, cliente_hoy if cliente_hoy else "Consumidor Final", telefono_hoy))

            cursor.execute("SELECT id, diagnostico, valor_mano_obra FROM servicios WHERE placa_moto = ? AND estado = 'Pendiente'", (placa,))
            pendiente = cursor.fetchone()

            from tkinter import messagebox
            if pendiente:
                id_pend, diag_actual, mo_actual = pendiente
                actualizacion = f"{diag_actual}\n[+ {nombre_tecnico.title()} | KM: {kilometraje_hoy} | Cobro: ${mano_obra_float:,.0f}]: {diagnostico_nuevo}"
                nueva_mo = mo_actual + mano_obra_float
                
                # --- ACTUALIZAMOS CON EL DOCUMENTO DEL CLIENTE ---
                cursor.execute("""
                    UPDATE servicios 
                    SET diagnostico = ?, valor_mano_obra = ?, 
                        id_usuario = ?,  
                        cliente_nombre = ?, cliente_telefono = ?, documento_cliente = ?
                    WHERE id = ?
                """, (actualizacion, nueva_mo, id_tec, cliente_hoy, telefono_hoy, cedula_hoy, id_pend))
                
                messagebox.showinfo("Novedad Añadida", f"Se actualizó el historial de la placa {placa}.")
            
            else:
                # Formateamos el diagnóstico inicial para que la web lo lea bonito
                diag_inicial = f"[{nombre_tecnico.title()} | KM: {kilometraje_hoy} | Cobro: ${mano_obra_float:,.0f}]: {diagnostico_nuevo}"
                
                # --- INSERTAMOS CON EL DOCUMENTO DEL CLIENTE ---
                cursor.execute("""
                    INSERT INTO servicios (
                        placa_moto, fecha_ingreso, diagnostico, estado, 
                        id_usuario, valor_mano_obra, cliente_nombre, cliente_telefono,
                        marca_moto, modelo_moto, documento_cliente
                    ) VALUES (?, datetime('now', 'localtime'), ?, 'Pendiente', ?, ?, ?, ?, ?, ?, ?)
                """, (placa, diag_inicial, id_tec, mano_obra_float, cliente_hoy, telefono_hoy, marca_hoy, modelo_hoy, cedula_hoy))
                
                messagebox.showinfo("Éxito", f"Moto {placa} ingresada al taller por {nombre_tecnico.upper()}.")

            conexion.commit()
            conexion.close()
            
            self.limpiar_formulario_taller()

        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Error Técnico", f"Error en la base de datos: {e}")

    def limpiar_formulario_taller(self):
        """Limpia todos los campos para el siguiente ingreso"""
        self.entry_placa.delete(0, 'end')
        self.entry_marca.delete(0, 'end')
        self.entry_modelo.delete(0, 'end')
        self.entry_cliente.delete(0, 'end')
        self.entry_telefono.delete(0, 'end')
        self.txt_diagnostico.delete("1.0", "end")
        self.entry_mano_obra.delete(0, 'end')
        self.entry_cedula.delete(0, 'end')
        self.entry_kilometraje.delete(0, 'end')
    # ==========================================
    # MÓDULO: INVENTARIO (ADMINISTRADOR)
    # ==========================================
    def abrir_modulo_inventario(self):
        for widget in self.area_principal.winfo_children():
            widget.destroy()

        ctk.CTkLabel(self.area_principal, text="📦 Gestión de Inventario Avanzado", font=("Roboto", 20, "bold")).pack(pady=10)

        # --- OBTENER CATEGORÍAS DE LA BASE DE DATOS ---
        conexion = sqlite3.connect(RUTA_DB)
        cursor = conexion.cursor()
        cursor.execute("SELECT DISTINCT categoria FROM inventario WHERE categoria IS NOT NULL AND categoria != ''")
        categorias_db = [fila[0] for fila in cursor.fetchall()]
        conexion.close()
        
        lista_categorias = ["Todas las Categorías"] + categorias_db

        # --- PANEL SUPERIOR: Búsqueda, Filtros y Herramientas ---
        frame_top = ctk.CTkFrame(self.area_principal, fg_color="transparent")
        frame_top.pack(fill="x", padx=10, pady=5)

        self.ent_busqueda_inv = ctk.CTkEntry(frame_top, placeholder_text="🔍 Buscar por SKU o Nombre...", width=200)
        self.ent_busqueda_inv.pack(side="left", padx=5)
        
        # El BIND optimizado
        self.timer_busqueda_inv = None
        self.ent_busqueda_inv.bind("<KeyRelease>", self.programar_busqueda_inv)

        # --- NUEVO: Menú desplegable de Categorías ---
        self.combo_categoria = ctk.CTkOptionMenu(frame_top, values=lista_categorias, command=self.programar_busqueda_inv)
        self.combo_categoria.pack(side="left", padx=5)

        if self.rol == "Admin":
            self.lbl_inversion = ctk.CTkLabel(frame_top, text="💰 Inversión Total: Calculando...", font=("Roboto", 14, "bold"), text_color="yellow")
            self.lbl_inversion.pack(side="left", padx=20)

            btn_backup = ctk.CTkButton(frame_top, text="💾 Respaldo", width=80, fg_color="#8E44AD", hover_color="#732D91", command=self.respaldar_bd)
            btn_backup.pack(side="right", padx=5)
            btn_export = ctk.CTkButton(frame_top, text="📤 Exportar", width=80, command=self.exportar_excel)
            btn_export.pack(side="right", padx=5)
            btn_import = ctk.CTkButton(frame_top, text="📥 Importar", width=80, fg_color="#27AE60", hover_color="#1E8449", command=self.importar_excel)
            btn_import.pack(side="right", padx=5)

        # --- FORMULARIO DE REGISTRO (Solo Admin) ---
        # ... (Mantén tu código del formulario de registro igual) ...
        # (Aquí va el código de los Entry de registro: sku, nombre, etc. que ya tienes)
        if self.rol == "Admin":
            frame_registro = ctk.CTkFrame(self.area_principal)
            frame_registro.pack(pady=10, padx=10, fill="x")
            
            self.ent_sku = ctk.CTkEntry(frame_registro, placeholder_text="SKU / Código", width=120)
            self.ent_sku.grid(row=0, column=0, padx=5, pady=5)
            self.ent_nombre_rep = ctk.CTkEntry(frame_registro, placeholder_text="Nombre del Producto", width=200)
            self.ent_nombre_rep.grid(row=0, column=1, padx=5, pady=5)
            self.ent_cat = ctk.CTkEntry(frame_registro, placeholder_text="Categoría", width=120)
            self.ent_cat.grid(row=0, column=2, padx=5, pady=5)
            self.ent_ubica = ctk.CTkEntry(frame_registro, placeholder_text="Ubicación", width=120)
            self.ent_ubica.grid(row=0, column=3, padx=5, pady=5)

            self.ent_stock = ctk.CTkEntry(frame_registro, placeholder_text="Stock", width=80)
            self.ent_stock.grid(row=1, column=0, padx=5, pady=5)
            self.ent_stock_min = ctk.CTkEntry(frame_registro, placeholder_text="Stock Mínimo", width=100)
            self.ent_stock_min.grid(row=1, column=1, padx=5, pady=5, sticky="w")
            self.ent_costo = ctk.CTkEntry(frame_registro, placeholder_text="Costo Unidad ($)", width=120)
            self.ent_costo.grid(row=1, column=2, padx=5, pady=5)
            self.ent_precio_v = ctk.CTkEntry(frame_registro, placeholder_text="Precio Venta ($)", width=120)
            self.ent_precio_v.grid(row=1, column=3, padx=5, pady=5)

            btn_add = ctk.CTkButton(frame_registro, text="✅ Guardar Repuesto", fg_color="green", command=self.registrar_repuesto)
            btn_add.grid(row=1, column=4, padx=15, pady=5)

        # --- CONTENEDOR DE LA TABLA ---
        self.frame_lista_inv = ctk.CTkScrollableFrame(self.area_principal, width=800, height=350)
        self.frame_lista_inv.pack(pady=10, padx=10, fill="both", expand=True)

        self.mostrar_tabla_inventario()

    def programar_busqueda_inv(self, event=None):
        if self.timer_busqueda_inv is not None:
            self.after_cancel(self.timer_busqueda_inv)
            
        termino = self.ent_busqueda_inv.get()
        categoria = self.combo_categoria.get()
        
        self.timer_busqueda_inv = self.after(400, lambda: self.mostrar_tabla_inventario(termino, categoria))

    def registrar_repuesto(self):
        sku = self.ent_sku.get().strip().upper()
        nombre = self.ent_nombre_rep.get().strip()
        cat = self.ent_cat.get().strip()
        stock = self.ent_stock.get().strip()
        s_min = self.ent_stock_min.get().strip()
        costo = self.ent_costo.get().strip()
        venta = self.ent_precio_v.get().strip()
        ubica = self.ent_ubica.get().strip().upper()

        if not all([sku, nombre, stock, costo, venta]):
            messagebox.showwarning("Faltan Datos", "SKU, Nombre, Stock, Costo y Venta son obligatorios.")
            return

        conexion = None
        try:
            conexion = sqlite3.connect(RUTA_DB)
            cursor = conexion.cursor()
            cursor.execute("""
                INSERT INTO inventario (sku, nombre_repuesto, categoria, stock, stock_minimo, precio_costo, precio_venta, ubicacion) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (sku, nombre, cat, int(stock), int(s_min or 0), float(costo), float(venta), ubica))
            conexion.commit()
            
            messagebox.showinfo("Éxito", f"Repuesto {sku} agregado correctamente.")
            self.abrir_modulo_inventario() # Recarga la vista
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Ese SKU / Código de barras ya existe.")
        except Exception as e:
            messagebox.showerror("Error", f"Error técnico: {e}")
        finally:
            if conexion: conexion.close()

    def mostrar_tabla_inventario(self, filtro="", categoria_filtro="Todas las Categorías"):
        for widget in self.frame_lista_inv.winfo_children():
            widget.destroy()

        conexion = sqlite3.connect(RUTA_DB)
        cursor = conexion.cursor()
        
        # Construcción dinámica de la consulta SQL
        query = "SELECT id, sku, nombre_repuesto, categoria, stock, stock_minimo, precio_costo, precio_venta, ubicacion FROM inventario WHERE 1=1"
        parametros = []

        if filtro:
            query += " AND (sku LIKE ? OR nombre_repuesto LIKE ?)"
            parametros.extend(['%'+filtro+'%', '%'+filtro+'%'])
        
        if categoria_filtro != "Todas las Categorías":
            query += " AND categoria = ?"
            parametros.append(categoria_filtro)
            
        query += " LIMIT 50"
        
        cursor.execute(query, parametros)
        repuestos = cursor.fetchall()
        conexion.close()

        # --- DEFINIR COLUMNAS (Añadimos "Categoría" a Admin y Vendedor) ---
        if self.rol == "Admin":
            columnas = ["SKU", "Producto", "Categoría", "Stock", "Min.", "Costo", "Venta", "Estado", "Ubicación", "Acciones"]
        elif self.rol == "Vendedor":
            columnas = ["SKU", "Producto", "Categoría", "Stock", "Venta", "Estado", "Ubicación"]
        else: # Tecnico
            columnas = ["SKU", "Producto", "Stock", "Venta", "Ubicación"]

        for col_idx, col_name in enumerate(columnas):
            ctk.CTkLabel(self.frame_lista_inv, text=col_name, font=("Roboto", 13, "bold"), text_color="cyan").grid(row=0, column=col_idx, padx=10, pady=5, sticky="w")

        total_inversion_taller = 0

        for i, fila in enumerate(repuestos, start=1):
            id_rep, sku, nombre, cat, stock, s_min, costo, venta, ubica = fila

            valor_inv = stock * costo
            total_inversion_taller += valor_inv

            estado_texto = "🔴 BAJO" if stock <= s_min else "🟢 Normal"
            color_estado = "red" if stock <= s_min else "green"

            # --- ARMAMOS LA FILA CON LA VARIABLE 'cat' INCLUIDA ---
            if self.rol == "Admin":
                valores_fila = [sku, nombre, cat, stock, s_min, f"${costo:,.0f}", f"${venta:,.0f}", estado_texto, ubica]
            elif self.rol == "Vendedor":
                valores_fila = [sku, nombre, cat, stock, f"${venta:,.0f}", estado_texto, ubica]
            else:
                valores_fila = [sku, nombre, stock, f"${venta:,.0f}", ubica]

            for j, val in enumerate(valores_fila):
                lbl = ctk.CTkLabel(self.frame_lista_inv, text=str(val))
                if val == "🔴 BAJO": lbl.configure(text_color=color_estado)
                lbl.grid(row=i, column=j, padx=10, pady=2, sticky="w")

            if self.rol == "Admin":
                frame_acciones = ctk.CTkFrame(self.frame_lista_inv, fg_color="transparent")
                frame_acciones.grid(row=i, column=len(columnas)-1, padx=5)

                ctk.CTkButton(frame_acciones, text="➕", width=30, height=25, command=lambda id_r=id_rep: self.ajustar_stock(id_r, 1)).pack(side="left", padx=2)
                ctk.CTkButton(frame_acciones, text="➖", width=30, height=25, fg_color="#D35400", hover_color="#A04000", command=lambda id_r=id_rep: self.ajustar_stock(id_r, -1)).pack(side="left", padx=2)
                ctk.CTkButton(frame_acciones, text="✏️", width=30, height=25, fg_color="#F39C12", hover_color="#D68910", command=lambda id_r=id_rep: self.abrir_ventana_edicion(id_r)).pack(side="left", padx=2)
                ctk.CTkButton(frame_acciones, text="🗑️", width=30, height=25, fg_color="#C0392B", hover_color="#922B21", command=lambda id_r=id_rep, n=nombre: self.eliminar_repuesto(id_r, n)).pack(side="left", padx=2)

        if hasattr(self, 'lbl_inversion') and self.rol == "Admin":
            self.lbl_inversion.configure(text=f"💰 Inversión Total: ${total_inversion_taller:,.0f}")

    def verificar_inventario_bajo(self):
        tab = self.tab_control.tab("📦 Inventario Bajo")
        for w in tab.winfo_children(): w.destroy()

        conexion = sqlite3.connect(RUTA_DB)
        cursor = conexion.cursor()
        # Buscamos donde el stock es igual o menor al mínimo
        cursor.execute("SELECT sku, nombre_repuesto, stock, stock_minimo FROM inventario WHERE stock <= stock_minimo")
        criticos = cursor.fetchall()
        conexion.close()

        if not criticos:
            ctk.CTkLabel(tab, text="✅ Todo el inventario está en niveles óptimos.", text_color="#2ECC71").pack(pady=50)
            return

        # Encabezado
        h = ctk.CTkFrame(tab, fg_color="#34495E")
        h.pack(fill="x", pady=5)
        ctk.CTkLabel(h, text="SKU", width=100).pack(side="left", padx=10)
        ctk.CTkLabel(h, text="REPUESTO", width=250, anchor="w").pack(side="left", padx=10)
        ctk.CTkLabel(h, text="STOCK ACTUAL", width=100).pack(side="left", padx=10)
        ctk.CTkLabel(h, text="MÍNIMO", width=100).pack(side="left", padx=10)

        for sku, nombre, stock, mini in criticos:
            f = ctk.CTkFrame(tab)
            f.pack(fill="x", pady=2)
            color_alerta = "#E74C3C" if stock == 0 else "#F39C12"
            
            ctk.CTkLabel(f, text=sku, width=100).pack(side="left", padx=10)
            ctk.CTkLabel(f, text=nombre, width=250, anchor="w").pack(side="left", padx=10)
            ctk.CTkLabel(f, text=str(stock), width=100, text_color=color_alerta, font=("Roboto", 13, "bold")).pack(side="left", padx=10)
            ctk.CTkLabel(f, text=str(mini), width=100).pack(side="left", padx=10)

    # --- FUNCIONES DE ACCIÓN DEL INVENTARIO ---
    def ajustar_stock(self, id_rep, cantidad):
        conexion = sqlite3.connect(RUTA_DB)
        cursor = conexion.cursor()
        # Evitar stock negativo si se resta
        cursor.execute("UPDATE inventario SET stock = MAX(0, stock + ?) WHERE id = ?", (cantidad, id_rep))
        conexion.commit()
        conexion.close()
        # Recargar tabla manteniendo el filtro actual
        self.mostrar_tabla_inventario(self.ent_busqueda_inv.get())

    def eliminar_repuesto(self, id_rep, nombre_rep):
        if messagebox.askyesno("Confirmar Eliminación", f"¿Estás seguro de que deseas eliminar permanentemente '{nombre_rep}'?"):
            conexion = sqlite3.connect(RUTA_DB)
            cursor = conexion.cursor()
            cursor.execute("DELETE FROM inventario WHERE id = ?", (id_rep,))
            conexion.commit()
            conexion.close()
            self.mostrar_tabla_inventario(self.ent_busqueda_inv.get())

    # --- FUNCIONES DE EXCEL Y RESPALDO ---
    def exportar_excel(self):
        try:
            conexion = sqlite3.connect(RUTA_DB)
            # Usamos pandas para leer la tabla directamente
            df = pd.read_sql_query("SELECT sku, nombre_repuesto, categoria, stock, stock_minimo, precio_costo, precio_venta, ubicacion FROM inventario", conexion)
            conexion.close()

            ruta = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")], title="Guardar Inventario")
            if ruta:
                df.to_excel(ruta, index=False)
                messagebox.showinfo("Éxito", "Inventario exportado correctamente a Excel.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar: {e}")

    def importar_excel(self):
        ruta = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")], title="Seleccionar archivo de Inventario")
        if not ruta: return

        try:
            df = pd.read_excel(ruta)
            conexion = sqlite3.connect(RUTA_DB)
            cursor = conexion.cursor()

            for _, fila in df.iterrows():
                # Inserta o ignora si el SKU ya existe
                cursor.execute("""
                    INSERT OR IGNORE INTO inventario (sku, nombre_repuesto, categoria, stock, stock_minimo, precio_costo, precio_venta, ubicacion)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (str(fila['sku']), str(fila['nombre_repuesto']), str(fila['categoria']), 
                      int(fila['stock']), int(fila['stock_minimo']), float(fila['precio_costo']), 
                      float(fila['precio_venta']), str(fila['ubicacion'])))
            
            conexion.commit()
            conexion.close()
            messagebox.showinfo("Éxito", "Inventario importado correctamente. Los SKU existentes no se duplicaron.")
            self.abrir_modulo_inventario()
        except Exception as e:
            messagebox.showerror("Error", f"Asegúrate de que el Excel tenga las columnas correctas. Error: {e}")

    def respaldar_bd(self):
        try:
            if not os.path.exists("respaldos"):
                os.makedirs("respaldos")
            
            fecha_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            nombre_respaldo = f"respaldos/fula_motos_backup_{fecha_str}.db"
            
            shutil.copy2(RUTA_DB, nombre_respaldo)
            messagebox.showinfo("Respaldo Seguro", f"Base de datos guardada con éxito en la carpeta 'respaldos'.\nArchivo: {nombre_respaldo}")
        except Exception as e:
            messagebox.showerror("Error de Respaldo", f"No se pudo crear la copia de seguridad: {e}")

    def abrir_ventana_edicion(self, id_rep):
        # 1. Buscar los datos actuales del repuesto
        conexion = sqlite3.connect(RUTA_DB)
        cursor = conexion.cursor()
        # Traemos también el stock (índice 3 de la tupla rep)
        cursor.execute("SELECT sku, nombre_repuesto, categoria, stock, stock_minimo, precio_costo, precio_venta, ubicacion FROM inventario WHERE id = ?", (id_rep,))
        rep = cursor.fetchone()
        conexion.close()

        if not rep: return

        # 2. Crear ventana emergente
        ventana_edit = ctk.CTkToplevel(self)
        ventana_edit.title(f"Editar Repuesto - {rep[0]}")
        ventana_edit.geometry("500x500") # La hice un poco más alta para que quepa el nuevo campo
        ventana_edit.grab_set() 
        
        ctk.CTkLabel(ventana_edit, text="Modificar Datos del Repuesto", font=("Roboto", 18, "bold")).pack(pady=15)

        # 3. Formulario pre-llenado
        frame_form = ctk.CTkFrame(ventana_edit)
        frame_form.pack(pady=10, padx=20, fill="both", expand=True)

        # SKU (No se suele editar)
        ctk.CTkLabel(frame_form, text="SKU:").grid(row=0, column=0, padx=10, pady=5, sticky="e")
        ent_sku = ctk.CTkEntry(frame_form, width=200)
        ent_sku.grid(row=0, column=1, padx=10, pady=5)
        ent_sku.insert(0, str(rep[0]))
        ent_sku.configure(state="disabled") 

        # Nombre
        ctk.CTkLabel(frame_form, text="Nombre:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        ent_nombre = ctk.CTkEntry(frame_form, width=200)
        ent_nombre.grid(row=1, column=1, padx=10, pady=5)
        ent_nombre.insert(0, str(rep[1]))

        # Categoría
        ctk.CTkLabel(frame_form, text="Categoría:").grid(row=2, column=0, padx=10, pady=5, sticky="e")
        ent_cat = ctk.CTkEntry(frame_form, width=200)
        ent_cat.grid(row=2, column=1, padx=10, pady=5)
        ent_cat.insert(0, str(rep[2]))

        # --- NUEVO: Stock Actual ---
        ctk.CTkLabel(frame_form, text="Stock Actual:").grid(row=3, column=0, padx=10, pady=5, sticky="e")
        ent_stock = ctk.CTkEntry(frame_form, width=200)
        ent_stock.grid(row=3, column=1, padx=10, pady=5)
        ent_stock.insert(0, str(rep[3])) # Llenamos con el stock actual

        # Stock Mínimo (Bajamos todos una fila)
        ctk.CTkLabel(frame_form, text="Stock Mínimo:").grid(row=4, column=0, padx=10, pady=5, sticky="e")
        ent_smin = ctk.CTkEntry(frame_form, width=200)
        ent_smin.grid(row=4, column=1, padx=10, pady=5)
        ent_smin.insert(0, str(rep[4]))

        # Costo
        ctk.CTkLabel(frame_form, text="Precio Costo ($):").grid(row=5, column=0, padx=10, pady=5, sticky="e")
        ent_costo = ctk.CTkEntry(frame_form, width=200)
        ent_costo.grid(row=5, column=1, padx=10, pady=5)
        ent_costo.insert(0, str(rep[5]))

        # Venta
        ctk.CTkLabel(frame_form, text="Precio Venta ($):").grid(row=6, column=0, padx=10, pady=5, sticky="e")
        ent_venta = ctk.CTkEntry(frame_form, width=200)
        ent_venta.grid(row=6, column=1, padx=10, pady=5)
        ent_venta.insert(0, str(rep[6]))

        # Ubicación
        ctk.CTkLabel(frame_form, text="Ubicación:").grid(row=7, column=0, padx=10, pady=5, sticky="e")
        ent_ubica = ctk.CTkEntry(frame_form, width=200)
        ent_ubica.grid(row=7, column=1, padx=10, pady=5)
        ent_ubica.insert(0, str(rep[7]))

        # 4. Función de guardado interno
        def guardar_cambios():
            try:
                con = sqlite3.connect(RUTA_DB)
                cur = con.cursor()
                
                # --- ACTUALIZADO: Agregamos stock a la consulta SQL ---
                cur.execute("""
                    UPDATE inventario 
                    SET nombre_repuesto = ?, categoria = ?, stock = ?, stock_minimo = ?, 
                        precio_costo = ?, precio_venta = ?, ubicacion = ?
                    WHERE id = ?
                """, (ent_nombre.get().strip(), ent_cat.get().strip(), 
                      int(ent_stock.get().strip()), int(ent_smin.get().strip()), 
                      float(ent_costo.get().strip()), float(ent_venta.get().strip()), 
                      ent_ubica.get().strip(), id_rep))
                
                con.commit()
                con.close()
                
                messagebox.showinfo("Éxito", "Repuesto actualizado correctamente.")
                ventana_edit.destroy() 
                self.mostrar_tabla_inventario(self.ent_busqueda_inv.get()) 
            except Exception as e:
                messagebox.showerror("Error", f"Verifica los datos. Error: {e}")

        ctk.CTkButton(ventana_edit, text="💾 Guardar Cambios", fg_color="green", command=guardar_cambios).pack(pady=20)

    # ==========================================
    # MÓDULO: FACTURACION (ADMINISTRADOR Y VENDEDOR)
    # ==========================================

    def autoguardar_datos_pos(self, event=None):
        """Guarda en la memoria en tiempo real mientras el usuario escribe o cambia algo"""
        if hasattr(self, 'ent_pos_doc') and self.ent_pos_doc.winfo_exists():
            self.respaldo_datos = {
                'doc': self.ent_pos_doc.get().strip(),
                'nom': self.ent_pos_nom.get().strip(),
                'tel': self.ent_pos_tel.get().strip(),
                'dir': self.ent_pos_dir.get().strip(),
                'placa': self.ent_pos_placa.get().strip(),
                'marca': self.ent_pos_marca.get().strip(),
                'desc': self.ent_pos_desc.get().strip() if hasattr(self, 'ent_pos_desc') else "0",
                'metodo': self.combo_metodo_pago.get() if hasattr(self, 'combo_metodo_pago') else "Efectivo"
            }

    def abrir_modulo_facturacion(self):
        # 1. INICIALIZAMOS LA MEMORIA Y VARIABLES DE CONTROL
        if not hasattr(self, 'respaldo_datos'): self.respaldo_datos = {}
        if not hasattr(self, 'carrito_actual'): self.carrito_actual = []
        self.id_servicio_detectado = None # Reset de seguridad
        self.timer_busqueda_pos = None

        # --- 2. LIMPIEZA VISUAL ---
        for widget in self.area_principal.winfo_children():
            widget.destroy()

        self.frame_pos = ctk.CTkFrame(self.area_principal, fg_color="transparent")
        self.frame_pos.pack(fill="both", expand=True, padx=10, pady=10)

        # ==========================================
        # COLUMNA DERECHA: PANEL DE VENTA
        # ==========================================
        frame_der = ctk.CTkFrame(self.frame_pos, width=380, fg_color="#1E1E1E")
        frame_der.pack(side="right", fill="both", padx=(5, 0))

        ctk.CTkLabel(frame_der, text="🧾 DETALLE DE FACTURA", font=("Roboto", 18, "bold"), text_color="cyan").pack(pady=10)

        # --- SECCIÓN CLIENTE ---
        frame_cliente = ctk.CTkFrame(frame_der, fg_color="transparent")
        frame_cliente.pack(fill="x", padx=10, pady=5)
        
        botones_rapidos = ctk.CTkFrame(frame_cliente, fg_color="transparent")
        botones_rapidos.pack(fill="x", pady=(0, 5))
        ctk.CTkButton(botones_rapidos, text="⚡ Cliente Mostrador", height=25, fg_color="#2980B9", command=self.cargar_cliente_mostrador).pack(side="left", expand=True, padx=2)
        ctk.CTkButton(botones_rapidos, text="🏍️ Cargar Moto", height=25, fg_color="#8E44AD", command=self.mostrar_motos_pendientes).pack(side="right", expand=True, padx=2)

        fila1 = ctk.CTkFrame(frame_cliente, fg_color="transparent")
        fila1.pack(fill="x", pady=2)
        self.ent_pos_doc = ctk.CTkEntry(fila1, placeholder_text="Cédula / NIT", width=120)
        self.ent_pos_doc.pack(side="left", padx=2, fill="x", expand=True)
        self.ent_pos_doc.bind("<KeyRelease>", self.autoguardar_datos_pos)
        self.ent_pos_nom = ctk.CTkEntry(fila1, placeholder_text="Nombre del Cliente")
        self.ent_pos_nom.pack(side="left", padx=2, fill="x", expand=True)
        self.ent_pos_nom.bind("<KeyRelease>", self.autoguardar_datos_pos)

        fila2 = ctk.CTkFrame(frame_cliente, fg_color="transparent")
        fila2.pack(fill="x", pady=2)
        self.ent_pos_tel = ctk.CTkEntry(fila2, placeholder_text="Teléfono / WhatsApp", width=150)
        self.ent_pos_tel.pack(side="left", padx=2, fill="x", expand=True)
        self.ent_pos_tel.bind("<KeyRelease>", self.autoguardar_datos_pos)
        self.ent_pos_dir = ctk.CTkEntry(fila2, placeholder_text="Dirección / Correo")
        self.ent_pos_dir.pack(side="left", padx=2, fill="x", expand=True)
        self.ent_pos_dir.bind("<KeyRelease>", self.autoguardar_datos_pos)

        # --- SECCIÓN VEHÍCULO (Depurada) ---
        fila_v = ctk.CTkFrame(frame_der, fg_color="transparent")
        fila_v.pack(fill="x", padx=10, pady=2)
        
        self.ent_pos_placa = ctk.CTkEntry(fila_v, placeholder_text="Placa", width=100, font=("Roboto", 14, "bold"))
        self.ent_pos_placa.pack(side="left", padx=2)
        self.ent_pos_placa.bind("<KeyRelease>", lambda e: (self.verificar_moto_en_taller(self.ent_pos_placa.get().upper()), self.autoguardar_datos_pos()))

        self.ent_pos_marca = ctk.CTkEntry(fila_v, placeholder_text="Marca y Modelo (Opcional)")
        self.ent_pos_marca.pack(side="left", padx=2, fill="x", expand=True)
        self.ent_pos_marca.bind("<KeyRelease>", self.autoguardar_datos_pos)

        # --- CARGA DE RESPALDO ---
        if self.respaldo_datos.get('doc'): self.ent_pos_doc.insert(0, self.respaldo_datos['doc'])
        if self.respaldo_datos.get('nom'): self.ent_pos_nom.insert(0, self.respaldo_datos['nom'])
        if self.respaldo_datos.get('tel'): self.ent_pos_tel.insert(0, self.respaldo_datos['tel'])
        if self.respaldo_datos.get('dir'): self.ent_pos_dir.insert(0, self.respaldo_datos['dir'])
        if self.respaldo_datos.get('placa'): 
            self.ent_pos_placa.insert(0, self.respaldo_datos['placa'])
            self.after(200, lambda: self.verificar_moto_en_taller(self.respaldo_datos['placa'])) # Verificación post-carga con pequeño delay para asegurar que el widget esté listo
        if self.respaldo_datos.get('marca'): self.ent_pos_marca.insert(0, self.respaldo_datos['marca'])

        # --- EL CARRITO ---
        self.frame_carrito = ctk.CTkScrollableFrame(frame_der, height=220, fg_color="#2A2A2A")
        self.frame_carrito.pack(fill="both", expand=True, padx=10, pady=10)

        # --- TOTALES Y DESCUENTOS ---
        frame_pagos = ctk.CTkFrame(frame_der, fg_color="transparent")
        frame_pagos.pack(fill="x", padx=10, pady=5, side="bottom")

        frame_desc = ctk.CTkFrame(frame_pagos, fg_color="transparent")
        frame_desc.pack(fill="x", pady=2)
        ctk.CTkLabel(frame_desc, text="Descuento ($ o %):").pack(side="left")
        self.ent_pos_desc = ctk.CTkEntry(frame_desc, width=80, height=25)
        self.ent_pos_desc.pack(side="right")
        
        desc_guardado = self.respaldo_datos.get('desc', "0")
        if desc_guardado and desc_guardado != "0": self.ent_pos_desc.insert(0, desc_guardado)
        self.ent_pos_desc.bind("<KeyRelease>", lambda e: (self.actualizar_carrito_ui(), self.autoguardar_datos_pos()))

        self.lbl_pos_subtotal = ctk.CTkLabel(frame_pagos, text="SUBTOTAL: $ 0", font=("Roboto", 14), anchor="e")
        self.lbl_pos_subtotal.pack(fill="x", pady=2)
        self.lbl_pos_total = ctk.CTkLabel(frame_pagos, text="TOTAL: $ 0", font=("Roboto", 24, "bold"), text_color="#2ECC71", anchor="e")
        self.lbl_pos_total.pack(fill="x", pady=5)

        # --- BOTONES DE ACCIÓN (Organizados por jerarquía) ---
        # Fila superior de botones pequeños
        frame_botones_top = ctk.CTkFrame(frame_pagos, fg_color="transparent")
        frame_botones_top.pack(fill="x", pady=2)
        ctk.CTkButton(frame_botones_top, text="📝 Cotizar", fg_color="#F39C12", width=100, command=lambda: self.procesar_factura("Cotizar")).pack(side="left", padx=2, expand=True)
        ctk.CTkButton(frame_botones_top, text="⏳ Guardar", fg_color="#34495E", width=100, command=lambda: self.procesar_factura("Guardar")).pack(side="left", padx=2, expand=True)

        # Botón de Taller (Llamativo y grande)
        self.btn_enviar_taller_directo = ctk.CTkButton(frame_pagos, text="🚀 ENVIAR CONSUMO AL TALLER", 
                                                       fg_color="gray", state="disabled", height=35,
                                                       font=("Roboto", 14, "bold"),
                                                       command=self.enviar_carrito_a_taller_directo)
        self.btn_enviar_taller_directo.pack(fill="x", pady=3)

        # Botón de Cobro (El más importante)
        ctk.CTkButton(frame_pagos, text="💵 REALIZAR COBRO", font=("Roboto", 16, "bold"), 
                      fg_color="#27AE60", hover_color="#2ECC71", height=45, 
                      command=lambda: self.procesar_factura("Cobrar")).pack(fill="x", pady=5)

        # ==========================================
        # COLUMNA IZQUIERDA: BUSCADOR
        # ==========================================
        frame_izq = ctk.CTkFrame(self.frame_pos)
        frame_izq.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        ctk.CTkLabel(frame_izq, text="🔍 BUSCADOR DE PRODUCTOS", font=("Roboto", 16, "bold")).pack(pady=10)
        self.ent_buscar_pos = ctk.CTkEntry(frame_izq, placeholder_text="Escribe SKU o nombre del repuesto...", width=400, height=35)
        self.ent_buscar_pos.pack(pady=5, padx=10)
        self.ent_buscar_pos.bind("<KeyRelease>", self.buscar_para_pos)

        frame_gest = ctk.CTkFrame(frame_izq, fg_color="transparent")
        frame_gest.pack(fill="x", padx=10, pady=10)
        #ctk.CTkButton(frame_gest, text="📂 Historial de Facturas", fg_color="#34495E", command=self.abrir_historial_facturas).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(frame_gest, text="🧹 Limpiar Todo", fg_color="#C0392B", command=self.limpiar_factura).pack(side="left", expand=True, padx=5)

        self.frame_resultados_pos = ctk.CTkScrollableFrame(frame_izq)
        self.frame_resultados_pos.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.actualizar_carrito_ui()
   
    def verificar_moto_en_taller(self, placa):
        placa_limpia = placa.strip().upper()
        if len(placa_limpia) < 4: 
            # Blindaje 1
            if hasattr(self, 'btn_enviar_taller_directo'):
                self.btn_enviar_taller_directo.configure(state="disabled", fg_color="gray")
            return 
        
        conexion = sqlite3.connect(RUTA_DB)
        cursor = conexion.cursor()
        cursor.execute("SELECT id FROM servicios WHERE placa_moto = ? AND estado = 'Pendiente' LIMIT 1", (placa_limpia,))
        servicio = cursor.fetchone()
        conexion.close()

        if servicio:
            self.id_servicio_detectado = servicio[0]
            # Blindaje 2
            if hasattr(self, 'btn_enviar_taller_directo'):
                self.btn_enviar_taller_directo.configure(state="normal", fg_color="#D35400")
        else:
            self.id_servicio_detectado = None
            # Blindaje 3
            if hasattr(self, 'btn_enviar_taller_directo'):
                self.btn_enviar_taller_directo.configure(state="disabled", fg_color="gray")

    def registrar_entrega_final(self, id_serv, id_prod, nombre, precio, ventana):
        """Guarda el repuesto entregado en el historial de la moto"""
        from tkinter import simpledialog
        cant = simpledialog.askinteger("Despacho", f"¿Cuántas unidades de {nombre} entrega al técnico?", minvalue=1)
        if cant:
            try:
                con = sqlite3.connect(RUTA_DB)
                cursor = con.cursor()
                cursor.execute("UPDATE inventario SET stock = stock - ? WHERE id = ?", (cant, id_prod))
                cursor.execute("INSERT INTO servicios_repuestos (id_servicio, id_repuesto, cantidad, precio_unitario) VALUES (?, ?, ?, ?)", 
                               (id_serv, id_prod, cant, precio))
                con.commit()
                con.close()
                messagebox.showinfo("Despacho Exitoso", f"Se entregó {nombre} y se cargó a la cuenta de la moto.")
                ventana.destroy()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def preparar_despacho_desde_pos(self):
        """Abre la ventana de despacho usando el ID detectado"""
        if hasattr(self, 'id_servicio_detectado') and self.id_servicio_detectado:
            placa = self.ent_pos_placa.get().upper()
            # Esta es la función de la ventanita de búsqueda que te pasé en el mensaje anterior
            self.abrir_ventana_despacho(self.id_servicio_detectado, placa)
    
    def cargar_cliente_mostrador(self):
        # 1. Limpiamos la pantalla
        self.ent_pos_doc.delete(0, 'end')
        self.ent_pos_nom.delete(0, 'end')
        self.ent_pos_tel.delete(0, 'end')
        self.ent_pos_dir.delete(0, 'end')
        
        # 2. Insertamos la data
        self.ent_pos_doc.insert(0, "222222222")
        self.ent_pos_nom.insert(0, "Cliente Mostrador")
        self.ent_pos_tel.insert(0, "322-222-2222")
        self.ent_pos_dir.insert(0, "Mostrador")
        
        # 3. Forzamos el guardado en la memoria en caso de cambiar de pestaña inmediatamente
        #self.guardar_progreso_factura()

    def limpiar_factura(self):
        # 1. Vaciamos la memoria interna
        self.respaldo_datos = {}
        self.carrito_actual = []
        self.id_factura_abierta = None
        self.id_servicio_detectado = None

        # 2. Borramos los textos de la pantalla suavemente
        if hasattr(self, 'ent_pos_doc') and self.ent_pos_doc.winfo_exists():
            self.ent_pos_doc.delete(0, 'end')
            self.ent_pos_nom.delete(0, 'end')
            self.ent_pos_tel.delete(0, 'end')
            self.ent_pos_placa.delete(0, 'end')
            self.ent_pos_marca.delete(0, 'end')
            
            if hasattr(self, 'ent_pos_dir'):
                self.ent_pos_dir.delete(0, 'end')
            
            if hasattr(self, 'ent_pos_desc'):
                self.ent_pos_desc.delete(0, 'end')
            if hasattr(self, 'combo_metodo_pago'):
                self.combo_metodo_pago.set("Efectivo")

            # Forzar la reaparición de los textos fantasma ---
            self.ent_pos_doc.configure(placeholder_text="Cédula / NIT")
            self.ent_pos_nom.configure(placeholder_text="Nombre del Cliente")
            self.ent_pos_tel.configure(placeholder_text="Teléfono / WhatsApp")
            self.ent_pos_placa.configure(placeholder_text="Placa")
            self.ent_pos_marca.configure(placeholder_text="Marca y Modelo (Opcional)")
            
            if hasattr(self, 'ent_pos_dir'):
                self.ent_pos_dir.configure(placeholder_text="Dirección / Correo")

            if hasattr(self, 'btn_enviar_taller_directo'):
                self.btn_enviar_taller_directo.configure(state="disabled", fg_color="gray")    
            # Quitamos el foco (el cursor de escritura) para que la pantalla se vea limpia
            self.focus()

        # 3. Refrescamos la vista del carrito para que se vea vacío
        self.actualizar_carrito_ui()

    def buscar_para_pos(self, event=None):
        if self.timer_busqueda_pos is not None:
            self.after_cancel(self.timer_busqueda_pos)
        termino = self.ent_buscar_pos.get().strip()
        self.timer_busqueda_pos = self.after(400, lambda: self.ejecutar_busqueda_pos(termino))

    def ejecutar_busqueda_pos(self, termino):
        for widget in self.frame_resultados_pos.winfo_children():
            widget.destroy()

        if len(termino) < 2:
            return  # No buscar si hay menos de 2 letras

        conexion = sqlite3.connect(RUTA_DB)
        cursor = conexion.cursor()

        # 1. Buscar repuestos en inventario
        cursor.execute("SELECT id, sku, nombre_repuesto, precio_venta, stock FROM inventario WHERE sku LIKE ? OR nombre_repuesto LIKE ? LIMIT 15", ('%'+termino+'%', '%'+termino+'%'))
        repuestos = cursor.fetchall()

        # 2. Buscar Mano de Obra (AHORA TRAEMOS LOS DATOS DEL CLIENTE TAMBIÉN)
        cursor.execute("""
            SELECT id, placa_moto, valor_mano_obra, cliente_nombre, cliente_telefono, marca_moto, modelo_moto, documento_cliente 
            FROM servicios 
            WHERE estado = 'Pendiente' AND placa_moto LIKE ?
        """, ('%'+termino+'%',))
        servicios = cursor.fetchall()
        conexion.close()

        # Mostrar Servicios Pendientes primero (Color Morado)
        if servicios:
            ctk.CTkLabel(self.frame_resultados_pos, text="🔧 MANO DE OBRA PENDIENTE", font=("Roboto", 12, "bold"), text_color="#D2B4DE").pack(anchor="w", pady=(5,0))
            for id_srv, placa, mo, c_nom, c_tel, marca, modelo, c_doc in servicios:
                btn_texto = f"Mano de Obra - {placa} (${mo:,.0f})"
                
                # NUEVO: En vez de ir directo al carrito, llama a la función que llena los datos visuales
                ctk.CTkButton(self.frame_resultados_pos, text=btn_texto, fg_color="#8E44AD", hover_color="#732D91", anchor="w",
                              command=lambda s=id_srv, p=placa, cn=c_nom, ct=c_tel, m=marca, mod=modelo, val=mo, doc=c_doc: 
                                  self.seleccionar_moto_pendiente(None, s, p, cn, ct, m, mod, val, doc)
                             ).pack(fill="x", pady=2)

        # Mostrar Repuestos (Azul si hay stock, Rojo si está agotado)
        if repuestos:
            ctk.CTkLabel(self.frame_resultados_pos, text="📦 REPUESTOS", font=("Roboto", 12, "bold"), text_color="cyan").pack(anchor="w", pady=(10,0))
            for id_rep, sku, nombre, precio, stock in repuestos:
                btn_texto = f"{sku} | {nombre} (Stock: {stock}) - ${precio:,.0f}"
                color = "#2980B9" if stock > 0 else "#C0392B"
                estado = "normal" if stock > 0 else "disabled"
                ctk.CTkButton(self.frame_resultados_pos, text=btn_texto, fg_color=color, state=estado, anchor="w",
                              command=lambda i=id_rep, n=nombre, p=precio: self.agregar_al_carrito("repuesto", i, n, p)).pack(fill="x", pady=2)
                
    def agregar_al_carrito(self, tipo, id_item, nombre, precio):
        # Verificamos si ya está en el carrito para sumarle 1 a la cantidad
        encontrado = False
        for item in self.carrito_actual:
            if item["id"] == id_item and item["tipo"] == tipo:
                item["cantidad"] += 1
                encontrado = True
                break
        
        # Si no estaba, lo agregamos como nuevo
        if not encontrado:
            self.carrito_actual.append({
                "tipo": tipo,
                "id": id_item,
                "nombre": nombre,
                "precio": precio,
                "cantidad": 1
            })
        
        self.actualizar_carrito_ui()

    def eliminar_del_carrito(self, indice):
        self.carrito_actual.pop(indice)
        self.actualizar_carrito_ui()

    def actualizar_carrito_ui(self, event=None):
        # 1. Limpiamos la lista visual
        for widget in self.frame_carrito.winfo_children():
            widget.destroy()

        subtotal = 0

        # 2. Dibujamos cada item del carrito
        for i, item in enumerate(self.carrito_actual):
            total_item = item["precio"] * item["cantidad"]
            subtotal += total_item
            
            frame_item = ctk.CTkFrame(self.frame_carrito, fg_color="transparent")
            frame_item.pack(fill="x", pady=2)
            
            txt_item = f"x{item['cantidad']} {item['nombre']} - ${total_item:,.0f}"
            ctk.CTkLabel(frame_item, text=txt_item, anchor="w", justify="left", wraplength=200).pack(side="left", fill="x", expand=True)
            
            # Botón para borrar el item del carrito
            ctk.CTkButton(frame_item, text="❌", width=25, height=25, fg_color="#C0392B", hover_color="#922B21", 
                          command=lambda idx=i: self.eliminar_del_carrito(idx)).pack(side="right")

        # 3. Calculamos Matemáticas de Totales y Descuentos
        self.lbl_pos_subtotal.configure(text=f"SUBTOTAL: ${subtotal:,.0f}")
        total_final = subtotal
        
        # Leemos el descuento si escribieron algo
        texto_desc = self.ent_pos_desc.get().strip()
        if texto_desc:
            try:
                if "%" in texto_desc:
                    porcentaje = float(texto_desc.replace("%", ""))
                    descuento_dinero = subtotal * (porcentaje / 100)
                    total_final -= descuento_dinero
                else:
                    descuento_dinero = float(texto_desc.replace("$", "").replace(".", ""))
                    total_final -= descuento_dinero
            except:
                pass # Si escriben letras raras, no falla, simplemente ignora el descuento
                
        # Protegemos que el total nunca sea negativo
        total_final = max(0, total_final)
        self.lbl_pos_total.configure(text=f"TOTAL: ${total_final:,.0f}")

    def generar_consecutivo(self, cursor, tipo_documento):
        # Si es cotización usa COT-, sino FULA-
        prefijo = "COT-" if tipo_documento == "Cotizacion" else "FULA-"
        
        # Busca el último número que tenga ese prefijo específico
        cursor.execute("SELECT consecutivo FROM facturas WHERE consecutivo LIKE ? ORDER BY id DESC LIMIT 1", (f"{prefijo}%",))
        ultimo = cursor.fetchone()
        
        if ultimo:
            try:
                # Extrae el número del texto (ej: "COT-0015" -> 15) y le suma 1
                num = int(ultimo[0].split("-")[1]) + 1
            except:
                num = 1
        else:
            num = 1
            
        return f"{prefijo}{num:04d}"
    
    def abrir_ventana_cobro(self):
        # 1. Validaciones iniciales
        if not self.carrito_actual:
            messagebox.showwarning("Carrito Vacío", "No hay productos para cobrar.")
            return

        # Calcular el total aplicando descuentos
        subtotal = sum(item["precio"] * item["cantidad"] for item in self.carrito_actual)
        total_final = subtotal
        texto_desc = self.ent_pos_desc.get().strip() if hasattr(self, 'ent_pos_desc') else ""
        
        if texto_desc:
            try:
                if "%" in texto_desc:
                    total_final -= subtotal * (float(texto_desc.replace("%", "")) / 100)
                else:
                    total_final -= float(texto_desc.replace("$", "").replace(".", ""))
            except: pass
        total_final = max(0, total_final)

        # 2. Crear Ventana de Cobro (Más alta para que quepan las 6 opciones)
        ven = ctk.CTkToplevel(self)
        ven.title("💰 Cierre de Caja - Pago Dividido")
        ven.geometry("400x620") 
        ven.grab_set() 
        ven.attributes('-topmost', True)

        ctk.CTkLabel(ven, text=f"TOTAL A PAGAR: ${total_final:,.0f}", font=("Roboto", 24, "bold"), text_color="#2ECC71").pack(pady=15)

        frame_pagos = ctk.CTkFrame(ven)
        frame_pagos.pack(fill="both", expand=True, padx=20, pady=5)

        # 3. Diccionario con los 6 métodos exactos que pediste
        self.vars_pago = {
            "Efectivo": ctk.StringVar(value=""),
            "QR Bancolombia": ctk.StringVar(value=""),
            "Nequi": ctk.StringVar(value=""),
            "DaviPlata": ctk.StringVar(value=""),
            "Transferencia": ctk.StringVar(value=""),
            "Otro": ctk.StringVar(value="")
        }

        # 4. Función matemática dinámica (Suma todo lo que haya en los 6 cuadros)
        def calcular_vueltos(*args):
            total_pagado = 0
            for var in self.vars_pago.values():
                try:
                    valor = float(var.get().replace(".", "").replace(",", "")) if var.get() else 0
                    total_pagado += valor
                except:
                    pass
            
            diferencia = total_pagado - total_final

            if diferencia >= 0:
                lbl_resumen.configure(text=f"CAMBIO (Vueltos): ${diferencia:,.0f}", text_color="#2ECC71")
            else:
                lbl_resumen.configure(text=f"FALTANTE (Crédito): ${abs(diferencia):,.0f}", text_color="#E74C3C")

        # 5. Dibujar los 6 cuadros de texto automáticamente con un bucle
        fila = 0
        for nombre, var in self.vars_pago.items():
            ctk.CTkLabel(frame_pagos, text=f"{nombre}:", font=("Roboto", 14, "bold")).grid(row=fila, column=0, padx=10, pady=10, sticky="w")
            ent = ctk.CTkEntry(frame_pagos, textvariable=var, width=150, justify="right")
            ent.grid(row=fila, column=1, padx=10, pady=10, sticky="e")
            ent.bind("<KeyRelease>", calcular_vueltos)
            fila += 1

        lbl_resumen = ctk.CTkLabel(ven, text=f"FALTANTE (Crédito): ${total_final:,.0f}", font=("Roboto", 18, "bold"), text_color="#E74C3C")
        lbl_resumen.pack(pady=10)

        # 6. Confirmar y agrupar los textos para enviarlos a procesar_factura
        def confirmar():
            total_entregado = 0
            metodos_usados = []
            
            for nombre, var in self.vars_pago.items():
                try:
                    valor = float(var.get().replace(".", "").replace(",", "")) if var.get() else 0
                    if valor > 0:
                        total_entregado += valor
                        metodos_usados.append(f"{nombre}: ${valor:,.0f}")
                except: pass

            deuda = max(0, total_final - total_entregado)
            
            # Crear el texto final para la Base de Datos
            if not metodos_usados and deuda == total_final:
                texto_metodo = "Crédito Total"
            else:
                texto_metodo = " | ".join(metodos_usados)
                if deuda > 0: texto_metodo += f" | Faltante: ${deuda:,.0f}"

            desglose = {
                "pagado": min(total_final, total_entregado), # No contamos los vueltos
                "deuda": deuda,
                "metodo_texto": texto_metodo
            }
            ven.destroy()
            self.procesar_factura("Cobrar", desglose)

        ctk.CTkButton(ven, text="✅ Confirmar Pago", font=("Roboto", 16, "bold"), height=40, fg_color="#27AE60", hover_color="#2ECC71", command=confirmar).pack(pady=15)
    
    def procesar_factura(self, accion, desglose_pago=None):
        if not self.carrito_actual:
            messagebox.showwarning("Carrito Vacío", "No hay productos o servicios para procesar.")
            return

        # --- CONTROL DE PAGO MIXTO ---
        # Si le dieron a Cobrar y aún no hay dinero desglosado, abrimos la ventanita.
        if accion == "Cobrar" and desglose_pago is None:
            self.abrir_ventana_cobro()
            return

        # Extracción de datos de los campos
        doc_cliente = self.ent_pos_doc.get().strip()
        nom_cliente = self.ent_pos_nom.get().strip()
        tel_cliente = self.ent_pos_tel.get().strip()
        dir_cliente = self.ent_pos_dir.get().strip()
        
        placa = self.ent_pos_placa.get().strip().upper()
        marca = self.ent_pos_marca.get().strip()

        # Comodín para cliente mostrador
        if not doc_cliente:
            doc_cliente = "000000000"
            if not nom_cliente: nom_cliente = "Cliente Mostrador"

        # Cálculo de Totales y Descuento
        subtotal = sum(item["precio"] * item["cantidad"] for item in self.carrito_actual)
        total_final = subtotal
        descuento_dinero = 0

        texto_desc = self.ent_pos_desc.get().strip()
        if texto_desc:
            try:
                if "%" in texto_desc:
                    porc = float(texto_desc.replace("%", ""))
                    descuento_dinero = subtotal * (porc / 100)
                else:
                    descuento_dinero = float(texto_desc.replace("$", "").replace(".", ""))
                total_final -= descuento_dinero
            except: pass
        total_final = max(0, total_final)

        # ==========================================
        # CONFIGURACIÓN DE ESTADO Y MÉTODO (CORREGIDO)
        # ==========================================
        if accion == "Cotizar":
            tipo_doc = "Cotizacion"
            estado_fac = "Cotizacion"
            metodo = "Cotizado" # Ya no busca el combo_metodo_pago
            monto_pagado = 0
            saldo_pendiente = total_final
        elif accion == "Guardar":
            tipo_doc = "Factura"
            estado_fac = "Abierta"
            metodo = "Pendiente de Pago"
            monto_pagado = 0
            saldo_pendiente = total_final
        elif accion == "Cobrar":
            tipo_doc = "Factura"
            metodo = desglose_pago["metodo_texto"]
            monto_pagado = desglose_pago["pagado"]
            saldo_pendiente = desglose_pago["deuda"]
            estado_fac = "Pagada" if saldo_pendiente == 0 else "Por Cobrar"

            # Validación de crédito
            if estado_fac == "Por Cobrar" and doc_cliente == "000000000":
                messagebox.showerror("Datos Obligatorios", "Para dejar saldo pendiente, ingresa Cédula, Nombre y Teléfono del cliente.")
                return

        try:
            conexion = sqlite3.connect(RUTA_DB)
            cursor = conexion.cursor()

            # 1. CLIENTE
            cursor.execute("""
                INSERT OR IGNORE INTO clientes (documento, nombre, telefono, direccion, correo)
                VALUES (?, ?, ?, ?, '')
            """, (doc_cliente, nom_cliente, tel_cliente, dir_cliente))
            
            cursor.execute("""
                UPDATE clientes SET nombre=?, telefono=?, direccion=? WHERE documento=?
            """, (nom_cliente, tel_cliente, dir_cliente, doc_cliente))

            # 2. CONSECUTIVO Y REEMPLAZO DE FACTURA ABIERTA
            consecutivo = self.generar_consecutivo(cursor, tipo_doc)
            
            if getattr(self, 'id_factura_abierta', None):
                cursor.execute("DELETE FROM detalles_factura WHERE id_factura = ?", (self.id_factura_abierta,))
                cursor.execute("DELETE FROM facturas WHERE id = ?", (self.id_factura_abierta,))

            # Identificar usuario
            id_usuario = self.usuario_actual[0] if hasattr(self, 'usuario_actual') and isinstance(self.usuario_actual, (list, tuple)) else 1

            # 3. GUARDAR FACTURA
            cursor.execute("""
                INSERT INTO facturas (
                    consecutivo, tipo_documento, documento_cliente, placa_moto, marca_moto, 
                    subtotal, descuento, total, metodo_pago, monto_pagado, saldo_pendiente, estado, id_usuario, fecha
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
            """, (consecutivo, tipo_doc, doc_cliente, placa, marca, subtotal, descuento_dinero, total_final, metodo, monto_pagado, saldo_pendiente, estado_fac, id_usuario))
            
            id_factura = cursor.lastrowid

            # WhatsApp Inicio
            icono_doc = "📝" if accion == "Cotizar" else "🧾"
            texto_whatsapp = f"🏍️ *FULA MOTOS* 🏍️\n"
            texto_whatsapp += f"{icono_doc} _{tipo_doc.upper()} {consecutivo}_\n"
            texto_whatsapp += f"👤 Cliente: {nom_cliente}\n"
            if placa: texto_whatsapp += f"🏍️ Moto: {marca} ({placa})\n"
            texto_whatsapp += "------------------------\n"

            # 4. DETALLES E INVENTARIO
            id_servicio_taller = None
            
            # TRUCO: Buscamos primero si hay un servicio en el carrito para tener su ID listo
            for item in self.carrito_actual:
                if item["tipo"] == "servicio": 
                    id_servicio_taller = item["id"]
                    break

            for item in self.carrito_actual:
                # Si el repuesto viene del taller, en el recibo y BD lo guardamos como "repuesto" normal
                tipo_bd = "repuesto" if item["tipo"] == "repuesto_taller" else item["tipo"]

                cursor.execute("""
                    INSERT INTO detalles_factura (id_factura, tipo_item, id_item, descripcion, cantidad, precio_unitario, subtotal)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (id_factura, tipo_bd, item["id"], item["nombre"], item["cantidad"], item["precio"], item["precio"] * item["cantidad"]))

                # Mensaje de WhatsApp dinámico
                if accion == "Cotizar":
                    texto_whatsapp += f"▪ {item['cantidad']}x {item['nombre']}\n"
                else:
                    texto_whatsapp += f"▪ {item['cantidad']}x {item['nombre']} - ${(item['precio'] * item['cantidad']):,.0f}\n"

                # --- EL BLINDAJE DEL INVENTARIO ---
                if accion == "Cobrar":
                    if item["tipo"] == "repuesto":
                        # ¡NUEVO POR MOSTRADOR! Sí se descuenta del inventario
                        cursor.execute("UPDATE inventario SET stock = stock - ? WHERE id = ?", (item["cantidad"], item["id"]))
                        # Y si hay una moto en el taller, se le suma a su historial
                        if id_servicio_taller:
                            cursor.execute("INSERT INTO servicios_repuestos (id_servicio, id_repuesto, cantidad, precio_unitario) VALUES (?, ?, ?, ?)",
                                           (id_servicio_taller, item["id"], item["cantidad"], item["precio"]))
                                           
                    elif item["tipo"] == "repuesto_taller":
                        # ¡PASE VIP! Ya fue descontado por el botón naranja. No se toca el inventario.
                        pass
                        
                    elif item["tipo"] == "servicio":
                        # Cerramos la orden de servicio
                        cursor.execute("UPDATE servicios SET estado = 'Terminado' WHERE id = ?", (item["id"],))

            conexion.commit()
            conexion.close()

            # WhatsApp Final
            texto_whatsapp += "------------------------\n"
            texto_whatsapp += f"💰 *TOTAL: ${total_final:,.0f}*\n"
            if accion == "Cobrar":
                texto_whatsapp += f"💵 Pagado: ${monto_pagado:,.0f}\n"
                if saldo_pendiente > 0: texto_whatsapp += f"📝 Saldo Pendiente: ${saldo_pendiente:,.0f}\n"
            texto_whatsapp += "\n¡Gracias por preferirnos! 🚀"

            # Mensaje de éxito
            if messagebox.askyesno(f"{accion} Exitosa", f"Documento {consecutivo} generado.\n\n¿Copiar recibo para WhatsApp?"):
                self.clipboard_clear()
                self.clipboard_append(texto_whatsapp)
                self.update()

            # RESET DEL POS
            if hasattr(self, 'respaldo_datos'): self.respaldo_datos.clear() 
            self.carrito_actual = []
            self.id_factura_abierta = None
            self.abrir_modulo_facturacion()
            
        except Exception as e:
            messagebox.showerror("Error", f"Falla en transacción: {e}")

    def abrir_historial_facturas(self):
        # 1. Crear la ventana emergente un poco más ancha
        ventana_historial = ctk.CTkToplevel(self)
        ventana_historial.title("📂 Historial y Cuentas por Cobrar")
        ventana_historial.geometry("950x600")
        ventana_historial.grab_set() 

        # --- Buscador Superior ---
        frame_busqueda = ctk.CTkFrame(ventana_historial, fg_color="transparent")
        frame_busqueda.pack(fill="x", padx=20, pady=10)

        # Ahora el buscador indica que sirve para Placa, Cédula, etc.
        ent_buscar_hist = ctk.CTkEntry(frame_busqueda, placeholder_text="Buscar por Placa, Cédula, Nombre o Factura...", width=350)
        ent_buscar_hist.pack(side="left", padx=5)

        # Botón para buscar normal
        btn_buscar = ctk.CTkButton(frame_busqueda, text="🔍 Buscar", width=100, 
                                   command=lambda: self.cargar_lista_facturas(frame_lista, ent_buscar_hist.get(), "Todas"))
        btn_buscar.pack(side="left", padx=5)

        # NUEVO: Botón rápido para ver solo a los que nos deben plata
        btn_deudas = ctk.CTkButton(frame_busqueda, text="🔴 Ver Cuentas por Cobrar", width=180, fg_color="#E74C3C", hover_color="#C0392B",
                                   command=lambda: self.cargar_lista_facturas(frame_lista, ent_buscar_hist.get(), "Por Cobrar"))
        btn_deudas.pack(side="right", padx=5)

        # --- Contenedor de la lista de facturas ---
        frame_lista = ctk.CTkScrollableFrame(ventana_historial)
        frame_lista.pack(fill="both", expand=True, padx=20, pady=10)

        # Cargar todas las facturas al iniciar
        self.cargar_lista_facturas(frame_lista, "", "Todas")

    def cargar_lista_facturas(self, frame_contenedor, termino_busqueda, filtro_estado):
        for widget in frame_contenedor.winfo_children():
            widget.destroy()

        conexion = sqlite3.connect(RUTA_DB)
        cursor = conexion.cursor()

        # --- CORRECCIÓN SQL: Blindamos el JOIN y traemos también el documento_cliente ---
        query = """
            SELECT f.id, f.consecutivo, c.nombre, f.placa_moto, f.total, f.saldo_pendiente, f.estado, f.fecha, f.documento_cliente 
            FROM facturas f
            LEFT JOIN clientes c ON f.documento_cliente = c.documento AND f.documento_cliente != '' AND f.documento_cliente IS NOT NULL
            WHERE (f.consecutivo LIKE ? OR f.documento_cliente LIKE ? OR c.nombre LIKE ? OR f.placa_moto LIKE ?)
        """
        
        if filtro_estado == "Por Cobrar":
            query += " AND f.estado = 'Por Cobrar'"
            
        query += " ORDER BY f.id DESC LIMIT 50"
        
        termino = f"%{termino_busqueda.strip()}%"
        cursor.execute(query, (termino, termino, termino, termino))
        facturas = cursor.fetchall()
        conexion.close()

        if not facturas:
            ctk.CTkLabel(frame_contenedor, text="No se encontraron facturas con esos datos.", text_color="gray").pack(pady=20)
            return

        # --- ENCABEZADOS ---
        frame_encabezado = ctk.CTkFrame(frame_contenedor, fg_color="#34495E", height=30)
        frame_encabezado.pack(fill="x", pady=(0, 5))
        
        ctk.CTkLabel(frame_encabezado, text="Doc.", width=80, font=("Roboto", 12, "bold")).pack(side="left", padx=5)
        ctk.CTkLabel(frame_encabezado, text="Fecha", width=120, font=("Roboto", 12, "bold")).pack(side="left", padx=5)
        ctk.CTkLabel(frame_encabezado, text="Cliente", width=180, anchor="w", font=("Roboto", 12, "bold")).pack(side="left", padx=5, expand=True, fill="x")
        ctk.CTkLabel(frame_encabezado, text="Placa", width=80, font=("Roboto", 12, "bold")).pack(side="left", padx=5)
        ctk.CTkLabel(frame_encabezado, text="Total", width=90, anchor="e", font=("Roboto", 12, "bold")).pack(side="left", padx=5)
        ctk.CTkLabel(frame_encabezado, text="Deuda", width=90, anchor="e", font=("Roboto", 12, "bold")).pack(side="left", padx=5)
        ctk.CTkLabel(frame_encabezado, text="Estado", width=90, font=("Roboto", 12, "bold")).pack(side="left", padx=5)
        ctk.CTkLabel(frame_encabezado, text="Acciones", width=130, font=("Roboto", 12, "bold")).pack(side="right", padx=5)

        # --- DIBUJAR FILAS ---
        # Añadimos la variable 'doc_cliente' al desempaquetado del for
        for f_id, consecutivo, cliente, placa, total, deuda, estado, fecha, doc_cliente in facturas:
            fila = ctk.CTkFrame(frame_contenedor)
            fila.pack(fill="x", pady=2)

            color_estado = "#2ECC71" if estado == "Pagada" else "#E74C3C" if estado == "Por Cobrar" else "#F39C12"
            
            # BLINDAJE EN PYTHON: Si no encontró el nombre, validamos el documento
            if cliente:
                nombre_cliente = cliente
            elif doc_cliente and doc_cliente.strip() != "":
                nombre_cliente = f"C.C {doc_cliente}" # Mostramos la cédula si el nombre se borró de la tabla clientes
            else:
                nombre_cliente = "Consumidor Final"

            placa_texto = placa if placa else "N/A"
            fecha_corta = str(fecha)[:16] if fecha else "S/F"

            ctk.CTkLabel(fila, text=consecutivo, width=80).pack(side="left", padx=5)
            ctk.CTkLabel(fila, text=fecha_corta, width=120).pack(side="left", padx=5)
            ctk.CTkLabel(fila, text=nombre_cliente, width=180, anchor="w").pack(side="left", padx=5, expand=True, fill="x")
            ctk.CTkLabel(fila, text=placa_texto, width=80).pack(side="left", padx=5)
            ctk.CTkLabel(fila, text=f"${total:,.0f}", width=90, anchor="e").pack(side="left", padx=5)
            
            color_deuda = "#E74C3C" if deuda > 0 else "gray"
            ctk.CTkLabel(fila, text=f"${deuda:,.0f}", width=90, anchor="e", text_color=color_deuda).pack(side="left", padx=5)
            ctk.CTkLabel(fila, text=estado, width=90, text_color=color_estado).pack(side="left", padx=5)
            
            frame_acciones = ctk.CTkFrame(fila, fg_color="transparent")
            frame_acciones.pack(side="right", padx=5)

            if estado == "Por Cobrar":
                ctk.CTkButton(frame_acciones, text="💸 Abonar", width=65, fg_color="#27AE60", hover_color="#2ECC71",
                              command=lambda id_f=f_id, cons=consecutivo, d=deuda: self.abrir_ventana_abono(id_f, cons, d, frame_contenedor)).pack(side="left", padx=2)

            ctk.CTkButton(frame_acciones, text="👀 Ver", width=50, fg_color="#2980B9", 
                          command=lambda id_f=f_id, cons=consecutivo: self.ver_detalle_factura(id_f, cons)).pack(side="left", padx=2)
                        
    def ver_detalle_factura(self, id_factura, consecutivo):
        ventana_det = ctk.CTkToplevel(self)
        ventana_det.title(f"Detalle - {consecutivo}")
        ventana_det.geometry("450x600")
        ventana_det.attributes('-topmost', True) 
        
        # --- SOLUCIÓN AL CIERRE ---
        # Esto le dice al programa: "Concéntrate en esta ventanita y devuélvele los clics del mouse"
        ventana_det.grab_set() 

        # 1. Consultar Datos de la Factura y del Cliente
        conexion = sqlite3.connect(RUTA_DB)
        cursor = conexion.cursor()
        
        # --- CORRECCIÓN SQL: Blindamos el JOIN aquí también ---
        cursor.execute("""
            SELECT f.total, f.estado, f.fecha, f.documento_cliente, c.nombre, c.telefono, c.direccion 
            FROM facturas f
            LEFT JOIN clientes c ON f.documento_cliente = c.documento AND f.documento_cliente != '' AND f.documento_cliente IS NOT NULL
            WHERE f.id = ?
        """, (id_factura,))
        info_fac = cursor.fetchone()
        
       # 2. Dibujar Encabezado y Datos del Cliente
        ctk.CTkLabel(ventana_det, text=f"🧾 {consecutivo}", font=("Roboto", 18, "bold"), text_color="cyan").pack(pady=(10, 0))
        
        if info_fac:
            total_fac, estado, fecha, doc, nom, tel, dir_c = info_fac
            
            fecha_texto = fecha if fecha else "Fecha no registrada"
            ctk.CTkLabel(ventana_det, text=f"📅 {fecha_texto}", font=("Roboto", 13), text_color="gray").pack(pady=(0, 10))
            
            frame_cli = ctk.CTkFrame(ventana_det, fg_color="#2A2A2A")
            frame_cli.pack(fill="x", padx=10, pady=5)
            
            # --- BLINDAJE DE VARIABLES ---
            doc_final = doc if (doc and doc.strip() != "") else "N/A"
            tel_final = tel if (tel and tel.strip() != "") else "N/A"
            
            if nom and nom.strip() != "":
                nom_final = nom
            elif doc_final != "N/A":
                nom_final = f"Cliente C.C {doc_final}"
            else:
                nom_final = "Consumidor Final"
            # -----------------------------
            
            ctk.CTkLabel(frame_cli, text="👤 DATOS DEL CLIENTE", font=("Roboto", 12, "bold")).pack(anchor="w", padx=10, pady=(5,0))
            ctk.CTkLabel(frame_cli, text=f"Nombre: {nom_final}").pack(anchor="w", padx=10)
            ctk.CTkLabel(frame_cli, text=f"Cédula/NIT: {doc_final}").pack(anchor="w", padx=10)
            ctk.CTkLabel(frame_cli, text=f"Teléfono: {tel_final}").pack(anchor="w", padx=10, pady=(0,5))
        # 3. Dibujar la lista de repuestos
        frame_items = ctk.CTkScrollableFrame(ventana_det, fg_color="#1E1E1E")
        frame_items.pack(fill="both", expand=True, padx=10, pady=5)

        cursor.execute("SELECT descripcion, cantidad, precio_unitario, subtotal FROM detalles_factura WHERE id_factura = ?", (id_factura,))
        detalles = cursor.fetchall()
        conexion.close()

        total_recalculado = 0
        for desc, cant, precio, sub in detalles:
            total_recalculado += sub
            f_item = ctk.CTkFrame(frame_items, fg_color="transparent")
            f_item.pack(fill="x", pady=2)
            
            ctk.CTkLabel(f_item, text=f"{cant}x {desc}", anchor="w", wraplength=250, justify="left").pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(f_item, text=f"${sub:,.0f}").pack(side="right")
            
        ctk.CTkLabel(ventana_det, text=f"TOTAL FACTURA: ${total_recalculado:,.0f}", font=("Roboto", 16, "bold"), text_color="#2ECC71").pack(pady=10)

        # ==========================================
        # 4. BOTONES DE ACCIÓN (Exportar y Seguridad)
        # ==========================================
        # --- FILA SUPERIOR: Exportar e Imprimir ---
        frame_imprimir = ctk.CTkFrame(ventana_det, fg_color="transparent")
        frame_imprimir.pack(fill="x", padx=10, pady=(10, 5))

        btn_pdf = ctk.CTkButton(frame_imprimir, text="📄 Guardar PDF", fg_color="#8E44AD", hover_color="#732D91",
                                command=lambda: self.generar_pdf_elegante(id_factura, consecutivo))
        btn_pdf.pack(side="left", fill="x", expand=True, padx=2)

        btn_ticket = ctk.CTkButton(frame_imprimir, text="🖨️ Imprimir POS", fg_color="#2C3E50", hover_color="#1A252F",
                                   command=lambda: self.imprimir_ticket_pos(id_factura, consecutivo))
        btn_ticket.pack(side="left", fill="x", expand=True, padx=2)

        # --- FILA INFERIOR: Gestión y Cierre ---
        frame_admin = ctk.CTkFrame(ventana_det, fg_color="transparent")
        frame_admin.pack(fill="x", padx=10, pady=(0, 10))
        
        rol_actual = getattr(self, 'rol', 'Vendedor') 
        
        # BOTÓN ELIMINAR (Solo Admin)
        if rol_actual == "Admin":
            btn_eliminar = ctk.CTkButton(frame_admin, text="🗑️", fg_color="#C0392B", hover_color="#922B21", width=40,
                                         command=lambda: self.eliminar_factura(id_factura, consecutivo, ventana_det))
            btn_eliminar.pack(side="left", padx=2)
                        
        # BOTÓN Cargar a Caja (Si no está pagada o si es admin)
        if rol_actual == "Admin" or estado != "Pagada":
            btn_cargar = ctk.CTkButton(frame_admin, text="✏️ Cargar a Caja", fg_color="#F39C12", hover_color="#D68910",
                                       command=lambda: [self.cargar_factura_en_pos(id_factura), ventana_det.destroy()])
            btn_cargar.pack(side="left", fill="x", expand=True, padx=2)
        
        # BOTÓN CERRAR
        btn_cerrar = ctk.CTkButton(frame_admin, text="❌ Cerrar", fg_color="#34495E", hover_color="#2C3E50", width=80,
                                   command=ventana_det.destroy)
        btn_cerrar.pack(side="right", padx=2)
        
    def cargar_factura_en_pos(self, id_factura):
        conexion = sqlite3.connect(RUTA_DB)
        cursor = conexion.cursor()
        
        # 1. Traer datos del cliente de esa factura específica
        cursor.execute("""
            SELECT f.documento_cliente, c.nombre, c.telefono, c.direccion, f.placa_moto, f.marca_moto, f.descuento, f.metodo_pago, f.estado
            FROM facturas f
            LEFT JOIN clientes c ON f.documento_cliente = c.documento
            WHERE f.id = ?
        """, (id_factura,))
        datos = cursor.fetchone()
        
        # 2. Traer los items (el carrito viejo)
        cursor.execute("SELECT tipo_item, id_item, descripcion, precio_unitario, cantidad FROM detalles_factura WHERE id_factura = ?", (id_factura,))
        items = cursor.fetchall()
        conexion.close()

        if not datos: return
        
        doc, nom, tel, dir_c, placa, marca, desc, metodo, estado = datos
        
        # 3. Llenar la memoria visual del POS con los datos rescatados
        self.respaldo_datos = {
            'doc': doc if doc else "",
            'nom': nom if nom else "",
            'tel': tel if tel else "",
            'dir': dir_c if dir_c else "",
            'placa': placa if placa else "",
            'marca': marca if marca else "",
            'desc': str(desc) if desc else "0",
            'metodo': metodo if metodo else "Efectivo"
        }
        
        # 4. Reconstruir el carrito de compras
        self.carrito_actual = []
        for tipo, id_item, desc_item, precio, cant in items:
            self.carrito_actual.append({
                "tipo": tipo,
                "id": id_item,
                "nombre": desc_item,
                "precio": precio,
                "cantidad": cant
            })
            
        # 5. SEGURIDAD: Si es Cotización o Abierta, guardamos el ID para reemplazarla luego.
        if estado in ["Cotizacion", "Abierta"]:
            self.id_factura_abierta = id_factura
        else:
            self.id_factura_abierta = None
            
        # 6. Cerrar todas las ventanitas emergentes
        for widget in self.winfo_children():
            if isinstance(widget, ctk.CTkToplevel):
                widget.destroy()
                
        # 7. Recargar la pantalla principal
        self.abrir_modulo_facturacion()
        
        # --(Forzar placeholders) ---
        if hasattr(self, 'ent_pos_doc'):
            self.ent_pos_doc.configure(placeholder_text="Cédula / NIT")
            self.ent_pos_nom.configure(placeholder_text="Nombre del Cliente")
            self.ent_pos_tel.configure(placeholder_text="Teléfono / WhatsApp")
            self.ent_pos_placa.configure(placeholder_text="Placa")
            self.ent_pos_marca.configure(placeholder_text="Marca y Modelo (Opcional)")
            
        if hasattr(self, 'ent_pos_dir'):
            self.ent_pos_dir.configure(placeholder_text="Dirección / Correo")
            
        self.focus() # Quitamos el cursor para que la pantalla quede nítida
        # --------------------------------------------

        messagebox.showinfo("Cargada en Caja", "¡Factura rescatada con éxito!\n\nYa puedes agregarle más cosas, cambiar el descuento, o cobrarla.")

    def eliminar_factura(self, id_factura, consecutivo, ventana_det):
        # 1. Confirmación simple
        if not messagebox.askyesno("⚠️ Confirmación", f"¿Estás seguro de eliminar la factura {consecutivo}?\n\n(Recuerda ajustar el stock en el inventario manualmente si es necesario)."):
            return

        conexion = sqlite3.connect(RUTA_DB)
        cursor = conexion.cursor()
        
        try:
            # 2. Eliminar de la base de datos sin tocar el inventario
            cursor.execute("DELETE FROM detalles_factura WHERE id_factura = ?", (id_factura,))
            cursor.execute("DELETE FROM facturas WHERE id = ?", (id_factura,))
            
            conexion.commit()
            messagebox.showinfo("🗑️ Eliminada", f"La factura {consecutivo} ha sido borrada del sistema.")
            
            # 3. Cerrar la ventanita
            ventana_det.destroy()
            
            # 4. Refrescar el historial
            for widget in self.winfo_children():
                if isinstance(widget, ctk.CTkToplevel) and widget.title() == "📂 Historial de Facturas y Cotizaciones":
                    widget.destroy()
                    self.abrir_historial_facturas()
                    break

        except Exception as e:
            messagebox.showerror("Error Crítico", f"No se pudo eliminar la factura:\n{e}")
        finally:
            conexion.close()

    def mostrar_motos_pendientes(self):
        # 1. Crear ventana emergente (Toplevel)
        ventana_motos = ctk.CTkToplevel(self)
        ventana_motos.title("Motos en Taller (Pendientes)")
        ventana_motos.geometry("550x400")
        ventana_motos.grab_set() # Bloquea el fondo hasta que se elija una

        ctk.CTkLabel(ventana_motos, text="Selecciona una moto para facturar:", font=("Roboto", 16, "bold")).pack(pady=10)

        frame_lista = ctk.CTkScrollableFrame(ventana_motos)
        frame_lista.pack(fill="both", expand=True, padx=10, pady=10)

        try:
            # 2. Buscar en la base de datos (AHORA INCLUYE documento_cliente)
            conexion = sqlite3.connect(RUTA_DB)
            cursor = conexion.cursor()
            cursor.execute("""
                SELECT id, placa_moto, cliente_nombre, cliente_telefono, marca_moto, modelo_moto, valor_mano_obra, documento_cliente 
                FROM servicios 
                WHERE estado = 'Pendiente'
            """)
            pendientes = cursor.fetchall()
            conexion.close()

            if not pendientes:
                ctk.CTkLabel(frame_lista, text="No hay motos con estado 'Pendiente' en el taller.", text_color="gray").pack(pady=20)
                return

            # 3. Crear un botón por cada moto (AHORA RECIBE c_doc Y LO ENVÍA AL COMMAND)
            for s_id, placa, c_nom, c_tel, marca, modelo, mo, c_doc in pendientes:
                texto_btn = f"🏍️ Placa: {placa} | 👤 {c_nom} | 💰 Mano de Obra: ${mo:,.0f}"
                ctk.CTkButton(
                    frame_lista, 
                    text=texto_btn, 
                    fg_color="#8E44AD", 
                    hover_color="#732D91", 
                    anchor="w", height=35,
                    command=lambda i=s_id, p=placa, cn=c_nom, ct=c_tel, m1=marca, m2=modelo, v=mo, doc=c_doc: self.seleccionar_moto_pendiente(ventana_motos, i, p, cn, ct, m1, m2, v, doc)
                ).pack(fill="x", pady=5)
                
        except Exception as e:
            ctk.CTkLabel(frame_lista, text=f"Error al cargar motos: {e}").pack()

    def seleccionar_moto_pendiente(self, ventana, s_id, placa, c_nom, c_tel, marca, modelo, mo, c_doc=""):
        # 1. Rellenar los campos del cliente visualmente
        self.ent_pos_doc.delete(0, 'end')
        if c_doc: self.ent_pos_doc.insert(0, c_doc)
        
        self.ent_pos_nom.delete(0, 'end')
        if c_nom: self.ent_pos_nom.insert(0, c_nom)
        
        self.ent_pos_tel.delete(0, 'end')
        if c_tel: self.ent_pos_tel.insert(0, c_tel)
        
        self.ent_pos_placa.delete(0, 'end')
        if placa: self.ent_pos_placa.insert(0, placa)
        
        self.ent_pos_marca.delete(0, 'end')
        marca_str = f"{marca} {modelo}".strip()
        if marca_str and marca_str != "None None":
            self.ent_pos_marca.insert(0, marca_str)

        # 2. Agregar el valor de la mano de obra directamente al carrito
        self.agregar_al_carrito("servicio", s_id, f"Mano de obra ({placa})", mo)

        # --- NUEVA MAGIA: BUSCAR Y CARGAR REPUESTOS YA DESPACHADOS ---
        try:
            conexion = sqlite3.connect(RUTA_DB)
            cursor = conexion.cursor()
            cursor.execute("""
                SELECT i.id, i.nombre_repuesto, sr.cantidad, sr.precio_unitario
                FROM servicios_repuestos sr
                JOIN inventario i ON sr.id_repuesto = i.id
                WHERE sr.id_servicio = ?
            """, (s_id,))
            repuestos_despachados = cursor.fetchall()
            conexion.close()

            for id_rep, nombre, cant, precio in repuestos_despachados:
                # Los agregamos al carrito uno por uno
                # Usamos un bucle por si la cantidad es mayor a 1
                for _ in range(int(cant)):
                    self.agregar_al_carrito("repuesto_taller", id_rep, nombre, precio)
        except Exception as e:
            print(f"Error al cargar repuestos del taller: {e}")
        # ------------------------------------------------------------

        # 3. Encender botón del taller y cerrar ventana
        if placa:
            self.verificar_moto_en_taller(placa)
            
        if ventana:
            ventana.destroy()

    def abrir_ventana_abono(self, id_factura, consecutivo, deuda_actual, frame_lista):
        ven_abono = ctk.CTkToplevel(self)
        ven_abono.title(f"Abono - {consecutivo}")
        ven_abono.geometry("350x250")
        ven_abono.grab_set()
        ven_abono.attributes('-topmost', True)

        ctk.CTkLabel(ven_abono, text=f"Deuda Actual: ${deuda_actual:,.0f}", font=("Roboto", 18, "bold"), text_color="#E74C3C").pack(pady=20)
        
        ctk.CTkLabel(ven_abono, text="Monto del Abono ($):").pack(pady=5)
        ent_monto = ctk.CTkEntry(ven_abono, width=150, justify="center")
        ent_monto.pack(pady=5)
        ent_monto.focus() # Pone el cursor automáticamente ahí

        def procesar_abono():
            try:
                # Limpiamos el texto por si escriben con puntos (ej: 20.000)
                monto = float(ent_monto.get().replace(".", "").replace(",", ""))
                
                if monto <= 0:
                    messagebox.showwarning("Error", "Ingresa un monto mayor a 0.")
                    return
                if monto > deuda_actual:
                    messagebox.showwarning("Error", f"El cliente no puede abonar más de la deuda (${deuda_actual:,.0f}).")
                    return

                conexion = sqlite3.connect(RUTA_DB)
                cursor = conexion.cursor()
                
                # 1. Calculamos cómo queda la cuenta
                nueva_deuda = deuda_actual - monto
                nuevo_estado = "Pagada" if nueva_deuda == 0 else "Por Cobrar"

                # 2. Le pegamos el abono al texto de historial de pagos para que quede registro
                cursor.execute("SELECT metodo_pago FROM facturas WHERE id = ?", (id_factura,))
                metodo_actual = cursor.fetchone()[0]
                nuevo_metodo_texto = f"{metodo_actual} | Abono: ${monto:,.0f}"

                # 3. Guardamos en la base de datos
                cursor.execute("""
                    UPDATE facturas 
                    SET monto_pagado = monto_pagado + ?, saldo_pendiente = ?, estado = ?, metodo_pago = ?
                    WHERE id = ?
                """, (monto, nueva_deuda, nuevo_estado, nuevo_metodo_texto, id_factura))
                
                conexion.commit()
                conexion.close()

                messagebox.showinfo("💸 Abono Exitoso", f"Se descontaron ${monto:,.0f} de la deuda.\n\nNuevo saldo: ${nueva_deuda:,.0f}")
                ven_abono.destroy()
                
                # 4. Refrescamos la lista de fondo para que desaparezca o baje la deuda
                self.cargar_lista_facturas(frame_lista, "", "Todas")

            except ValueError:
                messagebox.showerror("Error", "Por favor ingresa un número válido.")
            except Exception as e:
                messagebox.showerror("Error de Sistema", str(e))

        ctk.CTkButton(ven_abono, text="✅ Confirmar Abono", fg_color="#27AE60", command=procesar_abono).pack(pady=20)

    def enviar_carrito_a_taller_directo(self):
        if not self.carrito_actual:
            messagebox.showwarning("Carrito Vacío", "Agregue productos al carrito primero.")
            return
        
        if not hasattr(self, 'id_servicio_detectado') or not self.id_servicio_detectado:
            messagebox.showwarning("Falta Placa", "Ingrese una placa que esté en el taller.")
            return

        confirmar = messagebox.askyesno("Confirmar Despacho", f"¿Despachar estos {len(self.carrito_actual)} ítems al taller?")
        if not confirmar: return

        try:
            conexion = sqlite3.connect(RUTA_DB)
            cursor = conexion.cursor()

            for item in self.carrito_actual:
                if item["tipo"] == "repuesto":
                    # 1. Descontar de inventario
                    cursor.execute("UPDATE inventario SET stock = stock - ? WHERE id = ?", (item["cantidad"], item["id"]))
                    # 2. Cargar al historial del taller
                    cursor.execute("""
                        INSERT INTO servicios_repuestos (id_servicio, id_repuesto, cantidad, precio_unitario)
                        VALUES (?, ?, ?, ?)
                    """, (self.id_servicio_detectado, item["id"], item["cantidad"], item["precio"]))

            conexion.commit()
            conexion.close()

            messagebox.showinfo("¡Éxito!", "Productos cargados al taller y descontados del inventario.")
            
            # Limpiar todo para la siguiente acción
            self.limpiar_factura() 
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo completar el despacho: {e}")

    def generar_pdf_elegante(self, id_factura, consecutivo):
        try:
            # 1. Traer datos de la base de datos (Igual que en el detalle)
            conexion = sqlite3.connect(RUTA_DB)
            cursor = conexion.cursor()
            
            cursor.execute("""
                SELECT f.total, f.estado, f.fecha, c.documento, c.nombre, c.telefono, c.direccion 
                FROM facturas f
                LEFT JOIN clientes c ON f.documento_cliente = c.documento
                WHERE f.id = ?
            """, (id_factura,))
            info_fac = cursor.fetchone()
            
            cursor.execute("SELECT cantidad, descripcion, precio_unitario, subtotal FROM detalles_factura WHERE id_factura = ?", (id_factura,))
            detalles = cursor.fetchall()
            conexion.close()

            if not info_fac:
                messagebox.showerror("Error", "No se encontró la información de la factura.")
                return

            total_fac, estado, fecha, doc, nom, tel, dir_c = info_fac

            # 2. Iniciar el lienzo del PDF (Tamaño Carta / Letter)
            pdf = FPDF('P', 'mm', 'Letter')
            pdf.add_page()
            
            # --- RUTAS RELATIVAS PARA PORTABILIDAD ---
            # Busca la carpeta "recursos" al lado de este script
            carpeta_actual = os.path.dirname(os.path.abspath(__file__))
            ruta_logo = os.path.join(carpeta_actual, "recursos", "logo.png")
            ruta_qr = os.path.join(carpeta_actual, "recursos", "qr.png")

            # --- ENCABEZADO CON LOGO ---
            if os.path.exists(ruta_logo):
                # Coloca la imagen en X=10, Y=10, con 40mm de ancho
                pdf.image(ruta_logo, x=10, y=10, w=40) 
            
            pdf.set_font('Arial', 'B', 22)
            pdf.cell(0, 10, 'FULA MOTOS', ln=1, align='C')
            pdf.set_font('Arial', '', 10)
            pdf.cell(0, 5, 'Mantenimiento Técnico y Venta de Repuestos', ln=1, align='C')
            pdf.cell(0, 5, 'Bogotá, Colombia | Tel: 300 000 0000', ln=1, align='C') # <-- Personaliza tu teléfono aquí
            pdf.ln(15)

            # --- CAJA DE INFORMACIÓN DEL CLIENTE Y FACTURA ---
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(100, 8, f'Documento: {consecutivo}', 0, 0)
            pdf.set_font('Arial', '', 10)
            pdf.cell(0, 8, f'Fecha: {fecha[:16] if fecha else "S/F"}', 0, 1, 'R')
            
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(0, 6, 'DATOS DEL CLIENTE', ln=1)
            pdf.set_font('Arial', '', 10)
            nombre_cliente = nom if nom else 'Consumidor Final'
            pdf.cell(0, 6, f"Nombre: {nombre_cliente}", ln=1)
            pdf.cell(0, 6, f"Cédula/NIT: {doc if doc else 'N/A'}", ln=1)
            pdf.cell(0, 6, f"Teléfono: {tel if tel else 'N/A'}", ln=1)
            pdf.ln(5)

            # --- TABLA DE ARTÍCULOS ---
            # Encabezados de tabla (Fondo gris)
            pdf.set_font('Arial', 'B', 10)
            pdf.set_fill_color(220, 220, 220)
            pdf.cell(20, 8, 'Cant.', 1, 0, 'C', fill=True)
            pdf.cell(110, 8, 'Descripción', 1, 0, 'C', fill=True)
            pdf.cell(30, 8, 'V. Unit.', 1, 0, 'C', fill=True)
            pdf.cell(30, 8, 'Subtotal', 1, 1, 'C', fill=True)

            # Filas de la tabla
            pdf.set_font('Arial', '', 10)
            for cant, desc, precio, sub in detalles:
                # Cortamos el texto si es inmensamente largo para no desarmar la tabla
                desc_corta = desc[:55] + ".." if len(desc) > 55 else desc
                pdf.cell(20, 8, str(cant), 1, 0, 'C')
                pdf.cell(110, 8, desc_corta, 1, 0, 'L')
                pdf.cell(30, 8, f"${precio:,.0f}", 1, 0, 'R')
                pdf.cell(30, 8, f"${sub:,.0f}", 1, 1, 'R')

            # --- TOTALES ---
            pdf.ln(2)
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(160, 10, 'TOTAL A PAGAR:', 0, 0, 'R')
            pdf.set_text_color(0, 150, 0) # Texto verde para el total
            pdf.cell(30, 10, f"${total_fac:,.0f}", 0, 1, 'R')
            pdf.set_text_color(0, 0, 0) # Volver a negro

            # --- CÓDIGO QR Y PIE DE PÁGINA ---
            pdf.ln(15)
            if os.path.exists(ruta_qr):
                # Centramos el QR (85 es más o menos la mitad en tamaño Carta)
                pdf.image(ruta_qr, x=85, y=pdf.get_y(), w=40)
                pdf.ln(45) # Salto de línea del tamaño del QR para que no se superponga el texto

            pdf.set_font('Arial', 'I', 10)
            pdf.cell(0, 10, '¡Gracias por confiar en Fula Motos! - Escanea el QR para visitar nuestra web.', ln=1, align='C')

            # 3. Preguntar dónde guardar y abrirlo automáticamente
            nombre_sugerido = f"{consecutivo}_{nombre_cliente.replace(' ', '_')}.pdf"
            ruta_guardado = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                initialfile=nombre_sugerido,
                filetypes=[("PDF files", "*.pdf")],
                title="Guardar Factura en PDF"
            )

            if ruta_guardado:
                pdf.output(ruta_guardado)
                # Abrir el PDF automáticamente para verlo
                os.startfile(ruta_guardado) 

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar el PDF.\nDetalle: {e}")

    def imprimir_ticket_pos(self, id_factura, consecutivo):
        try:
            conexion = sqlite3.connect(RUTA_DB)
            cursor = conexion.cursor()
            
            cursor.execute("""
                SELECT f.total, f.estado, f.fecha, c.documento, c.nombre, c.telefono 
                FROM facturas f
                LEFT JOIN clientes c ON f.documento_cliente = c.documento
                WHERE f.id = ?
            """, (id_factura,))
            info_fac = cursor.fetchone()
            
            cursor.execute("SELECT cantidad, descripcion, precio_unitario, subtotal FROM detalles_factura WHERE id_factura = ?", (id_factura,))
            detalles = cursor.fetchall()
            conexion.close()

            if not info_fac: return

            total_fac, estado, fecha, doc, nom, tel = info_fac
            
            # --- CONSTRUIR EL TEXTO DEL TICKET ---
            # Diseñado para 32 caracteres de ancho (estándar de impresoras de 58mm)
            ticket =  "================================\n"
            ticket += "           FULA MOTOS           \n"
            ticket += "================================\n"
            ticket += f"Recibo: {consecutivo}\n"
            ticket += f"Fecha: {fecha[:16] if fecha else 'S/F'}\n"
            ticket += "--------------------------------\n"
            ticket += f"Cliente: {nom if nom else 'Consumidor Final'}\n"
            if doc and doc != "000000000": ticket += f"CC/NIT: {doc}\n"
            ticket += "--------------------------------\n"
            ticket += "CANT DESCRIPCION        SUBTOTAL\n"
            ticket += "--------------------------------\n"
            
            for cant, desc, precio, sub in detalles:
                # Cortar y rellenar descripción para que los precios queden alineados
                desc_corta = desc[:16] + ".." if len(desc) > 16 else desc.ljust(18)
                ticket += f"{cant:<4} {desc_corta} ${sub:,.0f}\n"
                
            ticket += "--------------------------------\n"
            ticket += f"TOTAL A PAGAR:        ${total_fac:,.0f}\n"
            ticket += "================================\n"
            ticket += "     ¡Gracias por su compra!    \n"
            ticket += "================================\n"

            # --- VENTANA DE VISTA PREVIA ---
            ventana_ticket = ctk.CTkToplevel(self)
            ventana_ticket.title("Vista Previa POS")
            ventana_ticket.geometry("350x500")
            ventana_ticket.attributes('-topmost', True)
            ventana_ticket.grab_set()
            
            # Usamos una fuente monoespaciada (Courier New) para que no se descuadren las columnas
            txt_preview = ctk.CTkTextbox(ventana_ticket, font=("Courier New", 13))
            txt_preview.pack(fill="both", expand=True, padx=10, pady=10)
            txt_preview.insert("1.0", ticket)
            txt_preview.configure(state="disabled") # Solo lectura para que no lo borren por error

            # --- FUNCIONES DE LOS BOTONES INTERNOS ---
            def copiar_ticket():
                self.clipboard_clear()
                self.clipboard_append(ticket)
                self.update()
                messagebox.showinfo("Copiado", "Ticket copiado al portapapeles. ¡Listo para pegar en WhatsApp!")

            def imprimir_real():
                # Guarda un archivo txt temporal y le dice a Windows que lo imprima por defecto
                import tempfile
                ruta_temp = os.path.join(tempfile.gettempdir(), f"ticket_{consecutivo}.txt")
                with open(ruta_temp, "w", encoding="utf-8") as f:
                    f.write(ticket)
                try:
                    os.startfile(ruta_temp, "print")
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo enviar a la impresora.\n{e}")

            frame_btn = ctk.CTkFrame(ventana_ticket, fg_color="transparent")
            frame_btn.pack(fill="x", padx=10, pady=10)
            
            ctk.CTkButton(frame_btn, text="📋 Copiar", command=copiar_ticket).pack(side="left", expand=True, padx=5)
            ctk.CTkButton(frame_btn, text="🖨️ Imprimir", fg_color="#27AE60", hover_color="#1E8449", command=imprimir_real).pack(side="right", expand=True, padx=5)

        except Exception as e:
            messagebox.showerror("Error", f"Falla generando ticket: {e}")

#=========================================
#Dashboard y actualizar_metricas_dashboard
#==========================================
    def abrir_nominas_admin(self):
        for widget in self.area_principal.winfo_children(): widget.destroy()

        ctk.CTkLabel(self.area_principal, text="💰 LIQUIDACIÓN DE COMISIONES (MANO DE OBRA)", 
                     font=("Roboto", 22, "bold"), text_color="cyan").pack(pady=20)

        # Contenedor principal
        frame_tabla = ctk.CTkScrollableFrame(self.area_principal, fg_color="transparent")
        frame_tabla.pack(fill="both", expand=True, padx=20, pady=10)

        try:
            conexion = sqlite3.connect(RUTA_DB)
            cursor = conexion.cursor()
            
            # --- CORRECCIÓN SQL: Cambiamos u.porcentaje por u.comision ---
            query = """
                SELECT u.id, u.username, u.comision, SUM(df.subtotal) 
                FROM detalles_factura df
                JOIN facturas f ON df.id_factura = f.id
                JOIN servicios s ON df.id_item = s.id
                JOIN usuarios u ON s.id_usuario = u.id
                WHERE df.tipo_item = 'servicio' 
                  AND f.estado = 'Pagada' 
                  AND s.pago_tecnico = 0
                GROUP BY u.id
            """
            cursor.execute(query)
            resumen = cursor.fetchall()
            conexion.close()

            if not resumen:
                ctk.CTkLabel(frame_tabla, text="✅ No hay comisiones pendientes por liquidar.", 
                             font=("Roboto", 16), text_color="gray").pack(pady=50)
                return

            # Encabezados de la tabla
            h = ctk.CTkFrame(frame_tabla, fg_color="#34495E", height=40)
            h.pack(fill="x", pady=5)
            ctk.CTkLabel(h, text="TÉCNICO", width=150, font=("Roboto", 13, "bold")).pack(side="left", padx=10)
            ctk.CTkLabel(h, text="TOTAL MANO OBRA", width=150, font=("Roboto", 13, "bold")).pack(side="left", padx=10)
            ctk.CTkLabel(h, text="% COM.", width=80, font=("Roboto", 13, "bold")).pack(side="left", padx=10)
            ctk.CTkLabel(h, text="A PAGAR", width=150, font=("Roboto", 13, "bold")).pack(side="left", padx=10)

            for id_tec, nombre, porc, total_mo in resumen:
                # Validamos que porc no sea None (si el usuario no tiene comisión asignada, se asume 0)
                porcentaje_real = porc if porc else 0
                pago_tecnico = total_mo * (porcentaje_real / 100)
                
                f = ctk.CTkFrame(frame_tabla)
                f.pack(fill="x", pady=2)
                
                ctk.CTkLabel(f, text=nombre.upper(), width=150, anchor="w", font=("Roboto", 14, "bold")).pack(side="left", padx=10)
                ctk.CTkLabel(f, text=f"$ {total_mo:,.0f}", width=150).pack(side="left", padx=10)
                ctk.CTkLabel(f, text=f"{porcentaje_real}%", width=80, text_color="cyan").pack(side="left", padx=10)
                ctk.CTkLabel(f, text=f"$ {pago_tecnico:,.0f}", width=150, text_color="#2ECC71", font=("Roboto", 15, "bold")).pack(side="left", padx=10)
                
                # Botón de detalle de nómina
                ctk.CTkButton(f, text="Revisar Detalle 📋", width=120, fg_color="#2980B9", hover_color="#2471A3",
                              command=lambda t_id=id_tec, nom=nombre, p=porcentaje_real, t_mo=total_mo, pago=pago_tecnico: 
                              self.abrir_detalle_nomina(t_id, nom, p, t_mo, pago)).pack(side="right", padx=10)

        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Error de Nómina", f"No se pudo cargar la liquidación: {e}")
    
    def abrir_detalle_nomina(self, id_tec, nombre, porc, total_mo, pago_tecnico):
        ventana_det = ctk.CTkToplevel(self)
        ventana_det.title(f"Detalle de Liquidación - {nombre.upper()}")
        ventana_det.geometry("800x600") # Un poco más alta para que quepan las notas
        ventana_det.grab_set()

        ctk.CTkLabel(ventana_det, text=f"🧾 TRABAJOS PENDIENTES DE PAGO: {nombre.upper()}", 
                     font=("Roboto", 16, "bold"), text_color="cyan").pack(pady=10)

        # Contenedor de la lista de trabajos
        frame_lista = ctk.CTkScrollableFrame(ventana_det, fg_color="#1E1E1E")
        frame_lista.pack(fill="both", expand=True, padx=20, pady=5)

        # 1. Consultar el "desmenuzado" de trabajos en la BD
        conexion = sqlite3.connect(RUTA_DB)
        cursor = conexion.cursor()
        query = """
            SELECT f.consecutivo, f.fecha, s.placa_moto, df.descripcion, df.subtotal 
            FROM detalles_factura df
            JOIN facturas f ON df.id_factura = f.id
            JOIN servicios s ON df.id_item = s.id
            WHERE df.tipo_item = 'servicio' 
              AND f.estado = 'Pagada' 
              AND s.pago_tecnico = 0
              AND s.id_usuario = ?
            ORDER BY f.fecha DESC
        """
        cursor.execute(query, (id_tec,))
        trabajos = cursor.fetchall()
        conexion.close()

        for cons, fecha, placa, desc, sub in trabajos:
            f_item = ctk.CTkFrame(frame_lista, fg_color="#2A2A2A")
            f_item.pack(fill="x", pady=5, padx=5)

            fecha_corta = str(fecha)[:16] if fecha else "S/F"
            
            txt_info = f"📅 {fecha_corta}  |  🧾 Factura: {cons}  |  🏍️ Placa: {placa}"
            ctk.CTkLabel(f_item, text=txt_info, font=("Roboto", 12, "bold"), text_color="#F39C12").pack(anchor="w", padx=10, pady=(5,0))
            ctk.CTkLabel(f_item, text=f"🔧 {desc}", wraplength=500, justify="left").pack(anchor="w", padx=20, pady=(0,5))
            ctk.CTkLabel(f_item, text=f"${sub:,.0f}", font=("Roboto", 14, "bold"), text_color="#2ECC71").place(relx=0.85, rely=0.3)

        # --- NUEVO: CAJÓN DE NOTAS ---
        frame_notas = ctk.CTkFrame(ventana_det, fg_color="transparent")
        frame_notas.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(frame_notas, text="📝 Notas u Observaciones del Pago:", font=("Roboto", 12, "bold")).pack(anchor="w")
        ent_notas = ctk.CTkEntry(frame_notas, width=700, placeholder_text="Ej: Pago quincena / Se descuentan $20.000 por adelanto del martes...")
        ent_notas.pack(fill="x", pady=5)

        # 3. Resumen Financiero Inferior
        frame_resumen = ctk.CTkFrame(ventana_det, fg_color="#34495E")
        frame_resumen.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(frame_resumen, text=f"Total Trabajo: ${total_mo:,.0f}", font=("Roboto", 13)).pack(side="left", padx=15, pady=15)
        ctk.CTkLabel(frame_resumen, text=f"Comisión: {porc}%", font=("Roboto", 13)).pack(side="left", padx=10, pady=15)
        ctk.CTkLabel(frame_resumen, text=f"A PAGAR: ${pago_tecnico:,.0f}", font=("Roboto", 16, "bold"), text_color="#2ECC71").pack(side="left", padx=15, pady=15)

        # 4. Botón de Ejecución
        def ejecutar_liquidacion():
            notas_texto = ent_notas.get().strip()
            # Llamamos a la nueva mega-función que guarda el historial
            self.procesar_pago_tecnico_historial(id_tec, nombre, pago_tecnico, notas_texto, trabajos, ventana_det)

        ctk.CTkButton(frame_resumen, text="Liquidar Confirmado 💸", fg_color="#27AE60", hover_color="#1E8449", 
                      font=("Roboto", 14, "bold"), command=ejecutar_liquidacion).pack(side="right", padx=15, pady=15)

    def procesar_pago_tecnico_historial(self, id_tec, nombre, total_pagado, notas, trabajos, ventana_det):
        from tkinter import messagebox
        respuesta = messagebox.askyesno("Confirmar Liquidación", 
                                        f"¿Estás seguro de registrar este pago por ${total_pagado:,.0f} a {nombre.upper()}?\n\nEsta acción no se puede deshacer.")
        if not respuesta:
            return

        try:
            conexion = sqlite3.connect(RUTA_DB)
            cursor = conexion.cursor()
            
            # 1. Crear la tabla de historial si es la primera vez que se usa
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS historial_pagos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_usuario INTEGER,
                    fecha_pago DATETIME DEFAULT (datetime('now', 'localtime')),
                    total_pagado REAL,
                    notas TEXT,
                    detalle_trabajos TEXT
                )
            """)
            
            # 2. Empaquetar el "desmenuzado" de trabajos
            resumen_texto = ""
            for cons, fecha, placa, desc, sub in trabajos:
                resumen_texto += f"[{placa}] Fac: {cons} | {desc} (${sub:,.0f})\n"
                
            # 3. Guardar el comprobante de pago con las notas en el HISTORIAL
            notas_finales = notas if notas else "Sin notas adicionales."
            cursor.execute("""
                INSERT INTO historial_pagos (id_usuario, total_pagado, notas, detalle_trabajos)
                VALUES (?, ?, ?, ?)
            """, (id_tec, total_pagado, notas_finales, resumen_texto))
            
            # 4. Marcar CADA servicio de esa lista como PAGADO (pago_tecnico = 1)
            # Usamos tu misma consulta original que es más precisa
            cursor.execute("""
                UPDATE servicios SET pago_tecnico = 1 
                WHERE id IN (
                    SELECT s.id FROM servicios s
                    JOIN detalles_factura df ON s.id = df.id_item
                    JOIN facturas f ON df.id_factura = f.id
                    WHERE s.id_usuario = ? AND df.tipo_item = 'servicio' AND f.estado = 'Pagada'
                )
            """, (id_tec,))

            # 5. --- EL ESLABÓN PERDIDO: REGISTRO EN CAJA / DASHBOARD ---
            cursor.execute("""
                INSERT INTO gastos_diarios (descripcion, monto, fecha) 
                VALUES (?, ?, datetime('now', 'localtime'))
            """, (f"Pago Nómina: {nombre.upper()}", total_pagado))
            
            conexion.commit()
            conexion.close()
            
            messagebox.showinfo("Pago Exitoso", f"Liquidación de {nombre.upper()} procesada y descontada de caja con éxito.")
            ventana_det.destroy()
            self.abrir_nominas_admin() # Recarga la lista
            
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Error Interno", f"Ocurrió un error al guardar el pago: {e}")
    
    def abrir_dashboard_admin(self, fecha_filtro=None):
        """Dashboard con navegación y filtros de fecha"""
        for widget in self.area_principal.winfo_children(): widget.destroy()
        
        # Si no hay fecha, usamos la de hoy
        if not fecha_filtro:
            fecha_filtro = datetime.now().strftime('%Y-%m-%d')

        scroll_dash = ctk.CTkScrollableFrame(self.area_principal, fg_color="transparent")
        scroll_dash.pack(fill="both", expand=True, padx=10, pady=10)

        # --- BARRA DE NAVEGACIÓN SUPERIOR ---
        nav_frame = ctk.CTkFrame(scroll_dash, fg_color="#1A1A1A", height=50)
        nav_frame.pack(fill="x", padx=10, pady=(0, 10))

        # Botón Atrás
       # ctk.CTkButton(nav_frame, text="⬅ Atrás", width=80, fg_color="#444", 
                     # command=self.abrir_menu_admin).pack(side="left", padx=10, pady=10)
        
        ctk.CTkLabel(nav_frame, text=f"📅 Visualizando: {fecha_filtro}", 
                     font=("Roboto", 16, "bold"), text_color="cyan").pack(side="left", padx=20)

        # Grupo de botones de acción (Derecha)
        btn_frame = ctk.CTkFrame(nav_frame, fg_color="transparent")
        btn_frame.pack(side="right", padx=10)

        ctk.CTkButton(btn_frame, text="🔍 Buscar Día", width=100, fg_color="#2980B9",
                      command=self.ventana_filtro_fecha).pack(side="left", padx=5)
        
        ctk.CTkButton(btn_frame, text="💵 Entrada $", width=100, fg_color="#27AE60",
                      command=self.abrir_ventana_entrada).pack(side="left", padx=5)
        
        ctk.CTkButton(btn_frame, text="💸 Gasto $", width=100, fg_color="#E67E22",
                      command=self.abrir_ventana_gasto).pack(side="left", padx=5)
        
        ctk.CTkButton(btn_frame, text="📈 Ver Reportes", width=100, fg_color="#8E44AD",
                      command=self.abrir_ventana_reportes).pack(side="left", padx=5)
        
        # --- TÍTULO CENTRAL ---
        ctk.CTkLabel(scroll_dash, text="📊 RENDIMIENTO GERENCIAL - FULA MOTOS", 
                     font=("Roboto", 24, "bold"), text_color="cyan").pack(pady=10)

        # --- CÁLCULOS DE BALANCE (Para las tarjetas) ---
        datos = self.calcular_balance_completo(fecha_filtro)
        saldo_neto = datos['ventas'] + datos['entradas'] - datos['gastos']

        # --- FILA 1: LAS 4 TARJETAS DE BALANCE ---
        frame_kpis = ctk.CTkFrame(scroll_dash, fg_color="transparent")
        frame_kpis.pack(fill="x", padx=10, pady=10)

        self.crear_tarjeta_kpi(frame_kpis, "VENTAS", f"$ {datos['ventas']:,.0f}", "#27AE60").pack(side="left", expand=True, padx=5)
        self.crear_tarjeta_kpi(frame_kpis, "ENTRADAS (+)", f"$ {datos['entradas']:,.0f}", "#2ECC71").pack(side="left", expand=True, padx=5)
        self.crear_tarjeta_kpi(frame_kpis, "GASTOS (-)", f"$ {datos['gastos']:,.0f}", "#E67E22").pack(side="left", expand=True, padx=5)
        
        color_neto = "#3498DB" if saldo_neto >= 0 else "#E74C3C" # Azul si ganas, Rojo si pierdes
        self.crear_tarjeta_kpi(frame_kpis, "SALDO EN CAJA", f"$ {saldo_neto:,.0f}", color_neto).pack(side="left", expand=True, padx=5)

        # --- FILA 2: MEDIOS DE PAGO Y GASTOS DETALLADOS ---
        frame_balance = ctk.CTkFrame(scroll_dash, fg_color="transparent")
        frame_balance.pack(fill="x", padx=10, pady=10)

        # Columna Ingresos
        frame_ingresos = ctk.CTkFrame(frame_balance, border_width=1, border_color="#27AE60", corner_radius=15)
        frame_ingresos.pack(side="left", fill="both", expand=True, padx=10)
        ctk.CTkLabel(frame_ingresos, text="💰 INGRESOS POR MEDIO", font=("Roboto", 16, "bold"), text_color="#2ECC71").pack(pady=15)
        self.dibujar_medios_pago(frame_ingresos, fecha_filtro)

        # Columna Gastos
        frame_gastos = ctk.CTkFrame(frame_balance, border_width=1, border_color="#E67E22", corner_radius=15)
        frame_gastos.pack(side="right", fill="both", expand=True, padx=10)
        ctk.CTkLabel(frame_gastos, text="📉 GASTOS Y SALIDAS", font=("Roboto", 16, "bold"), text_color="#E67E22").pack(pady=15)
        self.dibujar_gastos_hoy(frame_gastos, fecha_filtro)

        # --- FILA 3: ALERTAS Y TOP 10 REPUESTOS ---
        frame_detalles = ctk.CTkFrame(scroll_dash, fg_color="transparent")
        frame_detalles.pack(fill="both", expand=True, padx=10, pady=20)

        # Columna Alertas Stock
        frame_stock = ctk.CTkFrame(frame_detalles, border_width=1, border_color="#C0392B", corner_radius=15)
        frame_stock.pack(side="left", fill="both", expand=True, padx=10)
        ctk.CTkLabel(frame_stock, text="🚨 REPOSICIÓN URGENTE", font=("Roboto", 16, "bold"), text_color="#E74C3C").pack(pady=15)
        self.dibujar_alertas_inventario(frame_stock)

        # Columna Top Repuestos
        frame_top = ctk.CTkFrame(frame_detalles, border_width=1, border_color="#D4AC0D", corner_radius=15)
        frame_top.pack(side="right", fill="both", expand=True, padx=10)
        ctk.CTkLabel(frame_top, text="🏆 TOP 10 REPUESTOS", font=("Roboto", 16, "bold"), text_color="#F1C40F").pack(pady=15)
        self.dibujar_top_repuestos(frame_top)

    # --- NUEVAS FUNCIONES DE APOYO ---
    def abrir_ventana_gasto(self):
        """Abre la ventana flotante para registrar un gasto"""
        ventana = ctk.CTkToplevel(self)
        ventana.title("Registrar Gasto")
        ventana.geometry("400x400")
        ventana.attributes("-topmost", True)
        ventana.grab_set()

        ctk.CTkLabel(ventana, text="💸 NUEVA SALIDA DE DINERO", font=("Roboto", 18, "bold"), text_color="#E67E22").pack(pady=20)

        ent_desc = ctk.CTkEntry(ventana, width=340, placeholder_text="Descripción (Ej: Escoba, Tornillos...)")
        ent_desc.pack(pady=10)

        opciones_cat = ["Consumibles/Insumos", "Nómina/Adelanto", "Aseo", "Servicios", "Transporte", "Otros"]
        combo_cat = ctk.CTkComboBox(ventana, width=340, values=opciones_cat)
        combo_cat.pack(pady=10)

        ent_monto = ctk.CTkEntry(ventana, width=340, placeholder_text="Monto $ (Ej: 15000)")
        ent_monto.pack(pady=10)

        def intentar_guardar():
            self.guardar_gasto(ent_desc.get(), combo_cat.get(), ent_monto.get(), ventana)

        ctk.CTkButton(ventana, text="💾 Guardar Gasto", fg_color="#27AE60", command=intentar_guardar).pack(pady=30)

    def guardar_gasto(self, descripcion, categoria, monto_str, ventana):
        """Guarda el gasto y FUERZA la recarga del Dashboard"""
        from tkinter import messagebox
        from datetime import datetime
        
        try:
            monto = float(monto_str.replace(".", "").replace(",", "").strip())
            if not descripcion.strip() or monto <= 0:
                raise ValueError
        except:
            messagebox.showwarning("Atención", "Revisa la descripción y que el monto sea un número mayor a cero.", parent=ventana)
            return

        try:
            conn = sqlite3.connect(RUTA_DB)
            cursor = conn.cursor()
            
            # Asegurar que la tabla existe
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS gastos_diarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha DATETIME,
                    descripcion TEXT,
                    monto REAL,
                    categoria TEXT
                )
            ''')
            
            # Insertamos con la fecha y hora EXACTA de este momento
            fecha_hoy = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("INSERT INTO gastos_diarios (fecha, descripcion, monto, categoria) VALUES (?, ?, ?, ?)", 
                           (fecha_hoy, descripcion.strip(), monto, categoria))
            
            # EL COMMIT ES VITAL PARA QUE SE GUARDE
            conn.commit()
            conn.close()

            ventana.destroy()
            messagebox.showinfo("Éxito", "Gasto registrado correctamente.")
            
            # RECARGA FORZADA DEL DASHBOARD PARA VER EL NUEVO SALDO
            self.abrir_dashboard_admin()
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar el gasto: {e}", parent=ventana)
    
    def abrir_ventana_reportes(self):
        """Abre un panel consolidado de Ventas, Entradas y Gastos (Semana/Mes)"""
        ventana = ctk.CTkToplevel(self)
        ventana.title("Reportes Financieros - Fula Motos")
        ventana.geometry("500x450") # Un poco más alta para la nueva fila
        ventana.attributes("-topmost", True)

        ctk.CTkLabel(ventana, text="📊 CONSOLIDADO FINANCIERO", font=("Roboto", 18, "bold"), text_color="cyan").pack(pady=10)

        # Sistema de Pestañas
        tabview = ctk.CTkTabview(ventana)
        tabview.pack(fill="both", expand=True, padx=15, pady=10)
        
        tab_semana = tabview.add("Esta Semana")
        tab_mes = tabview.add("Este Mes")

        try:
            conn = sqlite3.connect(RUTA_DB)
            cur = conn.cursor()

            # --- CÁLCULOS SEMANA (Últimos 7 días) ---
            # 1. Ventas de Facturas (Lo que faltaba)
            cur.execute("SELECT SUM(total) FROM facturas WHERE date(fecha) >= date('now', '-7 days') AND estado='Pagada'")
            ventas_sem = cur.fetchone()[0] or 0
            # 2. Entradas Ocasionales
            cur.execute("SELECT SUM(monto) FROM entradas_caja WHERE date(fecha) >= date('now', '-7 days')")
            ent_sem = cur.fetchone()[0] or 0
            # 3. Gastos
            cur.execute("SELECT SUM(monto) FROM gastos_diarios WHERE date(fecha) >= date('now', '-7 days')")
            gas_sem = cur.fetchone()[0] or 0

            # --- CÁLCULOS MES (Desde el día 1 del mes actual) ---
            # 1. Ventas de Facturas
            cur.execute("SELECT SUM(total) FROM facturas WHERE date(fecha) >= date('now', 'start of month') AND estado='Pagada'")
            ventas_mes = cur.fetchone()[0] or 0
            # 2. Entradas Ocasionales
            cur.execute("SELECT SUM(monto) FROM entradas_caja WHERE date(fecha) >= date('now', 'start of month')")
            ent_mes = cur.fetchone()[0] or 0
            # 3. Gastos
            cur.execute("SELECT SUM(monto) FROM gastos_diarios WHERE date(fecha) >= date('now', 'start of month')")
            gas_mes = cur.fetchone()[0] or 0
            
            conn.close()

            # --- DIBUJAR PESTAÑA SEMANA ---
            ctk.CTkLabel(tab_semana, text="Resumen de los últimos 7 días", text_color="gray").pack(pady=10)
            
            self.crear_fila_reporte(tab_semana, "🏍️ Ingresos por Ventas:", f"$ {ventas_sem:,.0f}", "#3498DB")
            self.crear_fila_reporte(tab_semana, "📥 Entradas Extra (Caja):", f"$ {ent_sem:,.0f}", "#2ECC71")
            self.crear_fila_reporte(tab_semana, "📉 Total Gastos:", f"$ {gas_sem:,.0f}", "#E74C3C")
            
            balance_sem = ventas_sem + ent_sem - gas_sem
            color_bal_sem = "#2ECC71" if balance_sem >= 0 else "#E74C3C"
            self.crear_fila_reporte(tab_semana, "⚖️ BALANCE NETO:", f"$ {balance_sem:,.0f}", color_bal_sem)

            # --- DIBUJAR PESTAÑA MES ---
            ctk.CTkLabel(tab_mes, text="Resumen del mes en curso", text_color="gray").pack(pady=10)
            
            self.crear_fila_reporte(tab_mes, "🏍️ Ingresos por Ventas:", f"$ {ventas_mes:,.0f}", "#3498DB")
            self.crear_fila_reporte(tab_mes, "📥 Entradas Extra (Caja):", f"$ {ent_mes:,.0f}", "#2ECC71")
            self.crear_fila_reporte(tab_mes, "📉 Total Gastos:", f"$ {gas_mes:,.0f}", "#E74C3C")
            
            balance_mes = ventas_mes + ent_mes - gas_mes
            color_bal_mes = "#2ECC71" if balance_mes >= 0 else "#E74C3C"
            self.crear_fila_reporte(tab_mes, "⚖️ BALANCE NETO:", f"$ {balance_mes:,.0f}", color_bal_mes)

        except Exception as e:
            ctk.CTkLabel(ventana, text=f"Error cargando reportes: {e}").pack()

    def crear_fila_reporte(self, master, titulo, valor, color_valor):
        """Utilidad para dibujar filas uniformes en los reportes"""
        f = ctk.CTkFrame(master, fg_color="transparent")
        f.pack(fill="x", padx=30, pady=10)
        ctk.CTkLabel(f, text=titulo, font=("Roboto", 14, "bold")).pack(side="left")
        ctk.CTkLabel(f, text=valor, font=("Roboto", 14, "bold"), text_color=color_valor).pack(side="right")

    def dibujar_medios_pago(self, master, fecha):
        """Muestra el desglose de ingresos respetando la fecha filtrada"""
        try:
            conn = sqlite3.connect(RUTA_DB)
            cur = conn.cursor()
            # AHORA USAMOS LA FECHA QUE VIENE DEL FILTRO (?)
            cur.execute("""SELECT metodo_pago, SUM(total) FROM facturas 
                           WHERE date(fecha) = ? AND estado = 'Pagada' 
                           GROUP BY metodo_pago""", (fecha,))
            medios = cur.fetchall()
            conn.close()

            iconos = {"Efectivo": "💵", "Nequi": "📱", "Daviplata": "📲", "QR Bancolombia": "🔳", "Transferencia": "🏦", "Credito": "💳"}

            if not medios:
                ctk.CTkLabel(master, text="No hay ingresos registrados en esta fecha.", text_color="gray").pack(pady=20)
            else:
                for metodo, total in medios:
                    ico = iconos.get(metodo, "💰")
                    f = ctk.CTkFrame(master, fg_color="transparent")
                    f.pack(fill="x", padx=20, pady=2)
                    ctk.CTkLabel(f, text=f"{ico} {metodo}", anchor="w").pack(side="left")
                    ctk.CTkLabel(f, text=f"$ {total:,.0f}", font=("Roboto", 12, "bold")).pack(side="right")
        except Exception as e: print(e)

    def dibujar_gastos_hoy(self, master, fecha):
        """Muestra los gastos respetando la fecha filtrada"""
        try:
            conn = sqlite3.connect(RUTA_DB)
            cur = conn.cursor()
            # AHORA USAMOS LA FECHA QUE VIENE DEL FILTRO (?)
            cur.execute("""SELECT id, descripcion, monto FROM gastos_diarios 
                           WHERE date(fecha) = ? ORDER BY id DESC""", (fecha,))
            gastos = cur.fetchall()
            
            total_g = sum(g[2] for g in gastos) if gastos else 0
            conn.close()

            if not gastos:
                ctk.CTkLabel(master, text="No hay gastos registrados en esta fecha.", text_color="gray").pack(pady=20)
            else:
                for id_g, desc, monto in gastos[:6]: 
                    f = ctk.CTkFrame(master, fg_color="transparent")
                    f.pack(fill="x", padx=10, pady=2)
                    
                    btn_del = ctk.CTkButton(f, text="❌", width=25, height=25, fg_color="transparent", 
                                            hover_color="#7B241C", text_color="#E74C3C", 
                                            command=lambda g_id=id_g: self.eliminar_gasto_erroneo(g_id))
                    btn_del.pack(side="right", padx=5)
                    
                    ctk.CTkLabel(f, text=f"$ {monto:,.0f}", text_color="#E67E22").pack(side="right", padx=5)
                    ctk.CTkLabel(f, text=f"• {desc[:18]}", anchor="w").pack(side="left")
                
                ctk.CTkLabel(master, text=f"TOTAL GASTOS: $ {total_g:,.0f}", font=("Roboto", 13, "bold"), text_color="#E74C3C").pack(pady=15)
        except Exception as e: print(e)

    def eliminar_gasto_erroneo(self, id_gasto):
        """Elimina el gasto y FUERZA la recarga del Dashboard"""
        from tkinter import messagebox
        
        if messagebox.askyesno("Borrar Gasto", "¿Seguro que deseas eliminar este gasto?\nEl Saldo en Caja subirá inmediatamente."):
            try:
                conn = sqlite3.connect(RUTA_DB)
                cursor = conn.cursor()
                
                cursor.execute("DELETE FROM gastos_diarios WHERE id = ?", (id_gasto,))
                
                # EL COMMIT ES VITAL PARA QUE SE BORRE DE VERDAD
                conn.commit()
                conn.close()
                
                # RECARGA FORZADA DEL DASHBOARD PARA ACTUALIZAR MATEMÁTICAS
                self.abrir_dashboard_admin() 
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo eliminar el gasto: {e}")
    
    def abrir_ventana_entrada(self):
        ventana = ctk.CTkToplevel(self)
        ventana.title("Entrada de Capital")
        ventana.geometry("350x300")
        ventana.attributes("-topmost", True)
        ventana.grab_set()

        ctk.CTkLabel(ventana, text="📥 ENTRADA OCASIONAL", font=("Roboto", 18, "bold"), text_color="#27AE60").pack(pady=15)
        
        ent_desc = ctk.CTkEntry(ventana, placeholder_text="Concepto (Ej: Base de caja)", width=250)
        ent_desc.pack(pady=10)
        
        ent_monto = ctk.CTkEntry(ventana, placeholder_text="Monto $", width=250)
        ent_monto.pack(pady=10)

        def guardar():
            try:
                monto = float(ent_monto.get().replace(".",""))
                conn = sqlite3.connect(RUTA_DB)
                cur = conn.cursor()
                cur.execute("INSERT INTO entradas_caja (descripcion, monto) VALUES (?, ?)", (ent_desc.get(), monto))
                conn.commit()
                conn.close()
                ventana.destroy()
                self.abrir_dashboard_admin() # Recargar
            except: pass

        ctk.CTkButton(ventana, text="Guardar Entrada", fg_color="#27AE60", command=guardar).pack(pady=20)
    
    def ventana_filtro_fecha(self):
        ventana = ctk.CTkToplevel(self)
        ventana.title("Buscar Histórico")
        ventana.geometry("300x200")
        ventana.attributes("-topmost", True)

        ctk.CTkLabel(ventana, text="Seleccione Fecha\n(AAAA-MM-DD)", font=("Roboto", 14)).pack(pady=10)
        ent_fecha = ctk.CTkEntry(ventana, placeholder_text="Ej: 2024-03-20")
        ent_fecha.insert(0, datetime.now().strftime('%Y-%m-%d'))
        ent_fecha.pack(pady=10)

        def filtrar():
            fecha = ent_fecha.get()
            ventana.destroy()
            self.abrir_dashboard_admin(fecha_filtro=fecha)

        ctk.CTkButton(ventana, text="🔍 Ver ese día", command=filtrar).pack(pady=10)

    def calcular_balance_completo(self, fecha):
        res = {'ventas': 0, 'entradas': 0, 'gastos': 0}
        try:
            conn = sqlite3.connect(RUTA_DB)
            cur = conn.cursor()
            
            # Ventas del día
            cur.execute("SELECT SUM(total) FROM facturas WHERE date(fecha) = ? AND estado='Pagada'", (fecha,))
            res['ventas'] = cur.fetchone()[0] or 0
            
            # Entradas manuales
            cur.execute("SELECT SUM(monto) FROM entradas_caja WHERE date(fecha) = ?", (fecha,))
            res['entradas'] = cur.fetchone()[0] or 0
            
            # Gastos
            cur.execute("SELECT SUM(monto) FROM gastos_diarios WHERE date(fecha) = ?", (fecha,))
            res['gastos'] = cur.fetchone()[0] or 0
            
            conn.close()
        except: pass
        return res
      
    # --- FUNCIONES DE APOYO LÓGICO ---

    def calcular_ventas_periodos(self):
        datos = {'hoy': 0, 'semana': 0, 'mes': 0, 'gastos_hoy': 0}
        try:
            conn = sqlite3.connect(RUTA_DB)
            cur = conn.cursor()
            
            # Ventas Hoy
            cur.execute("SELECT SUM(total) FROM facturas WHERE date(fecha) = date('now', 'localtime') AND estado = 'Pagada'")
            datos['hoy'] = cur.fetchone()[0] or 0
            
            # NUEVO: Gastos Hoy
            cur.execute("SELECT SUM(monto) FROM gastos_diarios WHERE date(fecha) = date('now', 'localtime')")
            datos['gastos_hoy'] = cur.fetchone()[0] or 0
            
            # Semana y Mes (Igual que antes...)
            cur.execute("SELECT SUM(total) FROM facturas WHERE date(fecha) >= date('now', '-7 days') AND estado = 'Pagada'")
            datos['semana'] = cur.fetchone()[0] or 0
            cur.execute("SELECT SUM(total) FROM facturas WHERE date(fecha) >= date('now', 'start of month') AND estado = 'Pagada'")
            datos['mes'] = cur.fetchone()[0] or 0
            
            conn.close()
        except Exception as e: print(f"Error en cálculos: {e}")
        return datos
    
    def dibujar_alertas_inventario(self, master):
        try:
            conn = sqlite3.connect(RUTA_DB)
            cur = conn.cursor()
            # Usamos tus columnas exactas: stock y stock_minimo
            cur.execute("SELECT nombre_repuesto, stock, stock_minimo FROM inventario WHERE stock <= stock_minimo LIMIT 8")
            items = cur.fetchall()
            conn.close()

            if not items:
                ctk.CTkLabel(master, text="✅ Todo el stock está óptimo", text_color="gray").pack(pady=20)
            else:
                for nom, stock, mini in items:
                    f = ctk.CTkFrame(master, fg_color="transparent")
                    f.pack(fill="x", padx=15, pady=2)
                    ctk.CTkLabel(f, text=f"• {nom}", anchor="w").pack(side="left")
                    ctk.CTkLabel(f, text=f"{stock} / {mini}", text_color="#E74C3C", font=("Roboto", 12, "bold")).pack(side="right")
        except: pass
    
    def dibujar_top_repuestos(self, master):
        """Muestra los 10 productos físicos que más rotan en el inventario"""
        try:
            conn = sqlite3.connect(RUTA_DB)
            cur = conn.cursor()
            
            # --- CONSULTA SQL PARA REPUESTOS ---
            # Sumamos las cantidades vendidas de items tipo 'repuesto'
            query = """
                SELECT descripcion, SUM(cantidad) as total_vendido 
                FROM detalles_factura 
                WHERE tipo_item = 'repuesto' 
                GROUP BY id_item 
                ORDER BY total_vendido DESC 
                LIMIT 10
            """
            cur.execute(query)
            repuestos = cur.fetchall()
            conn.close()

            if not repuestos:
                ctk.CTkLabel(master, text="Aún no hay repuestos facturados.", text_color="gray").pack(pady=20)
            else:
                for i, (nombre, cant) in enumerate(repuestos, 1):
                    f = ctk.CTkFrame(master, fg_color="transparent")
                    f.pack(fill="x", padx=15, pady=4) # Le di un poquito más de margen (pady=4) por si el texto salta de línea
                    
                    # 1. Empacamos el número a la derecha PRIMERO para proteger su espacio
                    ctk.CTkLabel(f, text=f"{int(cant)} un.", text_color="#F1C40F", font=("Roboto", 12, "bold")).pack(side="right", padx=(10, 0))
                    
                    # 2. Empacamos el nombre a la izquierda, SIN CORTARLO. 
                    # 'expand=True' y 'wraplength' permiten que use el centro y salte de línea si es necesario.
                    ctk.CTkLabel(f, text=f"{i}. {nombre}", anchor="w", wraplength=280, justify="left").pack(side="left", fill="x", expand=True)
                    
        except Exception as e:
            print(f"Error en Top Repuestos: {e}")

    def crear_tarjeta_kpi(self, master, titulo, valor, color):
        f = ctk.CTkFrame(master, corner_radius=15, border_width=2, border_color=color)
        ctk.CTkLabel(f, text=titulo, font=("Roboto", 14, "bold"), text_color=color).pack(pady=(15,0))
        ctk.CTkLabel(f, text=valor, font=("Roboto", 24, "bold")).pack(pady=20, padx=20)
        return f
    
    def actualizar_metricas_dashboard(self, periodo):
        # 1. Definir el filtro SQL según el periodo
        if periodo == "Hoy": filtro = "date(fecha) = date('now', 'localtime')"
        elif periodo == "Esta Semana": filtro = "fecha >= date('now', '-7 days')"
        else: filtro = "strftime('%m-%Y', fecha) = strftime('%m-%Y', 'now')"

        conexion = sqlite3.connect(RUTA_DB)
        cursor = conexion.cursor()

        # --- DATOS FINANCIEROS ---
        cursor.execute(f"SELECT SUM(total), SUM(monto_pagado), SUM(saldo_pendiente) FROM facturas WHERE {filtro} AND tipo_documento='Factura'")
        v_total, v_pago, v_deuda = cursor.fetchone()
        
        cursor.execute(f"SELECT SUM(monto) FROM gastos_diarios WHERE {filtro.replace('fecha', 'fecha')}")
        v_gastos = cursor.fetchone()[0] or 0

        # --- MEDIOS DE PAGO ---
        cursor.execute(f"SELECT metodo_pago, SUM(monto_pagado) FROM facturas WHERE {filtro} GROUP BY metodo_pago")
        medios = cursor.fetchall()

        # --- PRODUCTOS TOP ---
        cursor.execute(f"""
            SELECT descripcion, SUM(cantidad) as total_v 
            FROM detalles_factura df
            JOIN facturas f ON df.id_factura = f.id
            WHERE {filtro.replace('fecha', 'f.fecha')} AND df.tipo_item = 'repuesto'
            GROUP BY id_item ORDER BY total_v DESC LIMIT 5
        """)
        productos_top = cursor.fetchall()
        
        conexion.close()

        # --- DIBUJAR TARJETAS (Limpiar y Recrear) ---
        for w in self.frame_tarjetas.winfo_children(): w.destroy()
        
        self.crear_tarjeta(self.frame_tarjetas, "Ventas Brutas", v_total or 0, "blue").pack(side="left", expand=True, padx=5)
        self.crear_tarjeta(self.frame_tarjetas, "Dinero en Caja", (v_pago or 0) - v_gastos, "green").pack(side="left", expand=True, padx=5)
        self.crear_tarjeta(self.frame_tarjetas, "Gastos", v_gastos, "red").pack(side="left", expand=True, padx=5)
        self.crear_tarjeta(self.frame_tarjetas, "Por Cobrar", v_deuda or 0, "orange").pack(side="left", expand=True, padx=5)

        # --- LLENAR PESTAÑAS ---
        self.llenar_tab_finanzas(medios)
        self.llenar_tab_productos(productos_top)
        self.verificar_inventario_bajo()

    def crear_tarjeta(self, parent, titulo, valor, color):
        f = ctk.CTkFrame(parent, height=100)
        ctk.CTkLabel(f, text=titulo, font=("Roboto", 12)).pack(pady=(10, 0))
        ctk.CTkLabel(f, text=f"$ {valor:,.0f}", font=("Roboto", 20, "bold"), text_color=color).pack(pady=10)
        return f

    def abrir_gestion_usuarios(self):
        ventana_usuarios = ctk.CTkToplevel(self)
        ventana_usuarios.title("👥 Gestión de Personal y Comisiones")
        ventana_usuarios.geometry("750x600")
        ventana_usuarios.grab_set()

        # 1. AUTO-ACTUALIZAR BASE DE DATOS (Crear columna comision si no existe)
        try:
            conexion = sqlite3.connect(RUTA_DB)
            cursor = conexion.cursor()
            cursor.execute("ALTER TABLE usuarios ADD COLUMN comision REAL DEFAULT 0")
            conexion.commit()
            conexion.close()
            print("Columna 'comision' añadida a la BD con éxito.")
        except Exception:
            pass # Si la columna ya existe, SQLite arroja error y simplemente lo ignoramos.

        # 2. Variable para saber si estamos creando o editando
        estado_edicion = {"id": None}

        # --- PANEL SUPERIOR: FORMULARIO ---
        frame_form = ctk.CTkFrame(ventana_usuarios, fg_color="#2A2A2A")
        frame_form.pack(fill="x", padx=20, pady=10)

        # Fila 0: Etiquetas
        ctk.CTkLabel(frame_form, text="Usuario:", font=("Roboto", 12, "bold")).grid(row=0, column=0, padx=5, pady=(10,0))
        ctk.CTkLabel(frame_form, text="Contraseña:", font=("Roboto", 12, "bold")).grid(row=0, column=1, padx=5, pady=(10,0))
        ctk.CTkLabel(frame_form, text="Rol:", font=("Roboto", 12, "bold")).grid(row=0, column=2, padx=5, pady=(10,0))
        ctk.CTkLabel(frame_form, text="% Comisión:", font=("Roboto", 12, "bold")).grid(row=0, column=3, padx=5, pady=(10,0))

        # Fila 1: Entradas
        ent_user = ctk.CTkEntry(frame_form, placeholder_text="Nombre")
        ent_user.grid(row=1, column=0, padx=10, pady=5)

        # Aquí NO ocultamos la contraseña (show="*") para que el admin pueda ver qué clave está asignando
        ent_pass = ctk.CTkEntry(frame_form, placeholder_text="Contraseña") 
        ent_pass.grid(row=1, column=1, padx=10, pady=5)

        # CORRECCIÓN: Usamos "Tecnico" para que coincida perfecto con tu matriz de seguridad
        combo_rol = ctk.CTkComboBox(frame_form, values=["Tecnico", "Vendedor", "Admin"])
        combo_rol.grid(row=1, column=2, padx=10, pady=5)

        ent_comision = ctk.CTkEntry(frame_form, placeholder_text="Ej: 30", width=80)
        ent_comision.grid(row=1, column=3, padx=10, pady=5)

        # Funciones Internas del Formulario
        def limpiar_form():
            ent_user.delete(0, "end")
            ent_pass.delete(0, "end")
            ent_comision.delete(0, "end")
            combo_rol.set("Tecnico")
            estado_edicion["id"] = None
            btn_guardar.configure(text="➕ Guardar Nuevo Usuario", fg_color="#27AE60", hover_color="#2ECC71")

        def guardar_usuario():
            # El .strip() elimina espacios fantasma al inicio o final
            u = ent_user.get().strip()
            p = ent_pass.get().strip()
            r = combo_rol.get()
            c = ent_comision.get().strip() or "0"

            if not u:
                from tkinter import messagebox
                messagebox.showwarning("Faltan datos", "El nombre de usuario es obligatorio.")
                return

            conexion = sqlite3.connect(RUTA_DB)
            cursor = conexion.cursor()
            
            if estado_edicion["id"] is None:
                # MODO: CREAR NUEVO
                if not p:
                    from tkinter import messagebox
                    messagebox.showwarning("Faltan datos", "Para un usuario nuevo, la contraseña es obligatoria.")
                    return
                cursor.execute("INSERT INTO usuarios (username, password, rol, comision) VALUES (?, ?, ?, ?)", (u, p, r, float(c)))
            else:
                # MODO: ACTUALIZAR EXISTENTE
                if p: 
                    # Si el admin escribió una contraseña, la actualizamos
                    cursor.execute("UPDATE usuarios SET username=?, password=?, rol=?, comision=? WHERE id=?", (u, p, r, float(c), estado_edicion["id"]))
                else: 
                    # Si dejó la contraseña en blanco, conservamos la que ya tenía
                    cursor.execute("UPDATE usuarios SET username=?, rol=?, comision=? WHERE id=?", (u, r, float(c), estado_edicion["id"]))
            
            conexion.commit()
            conexion.close()
            limpiar_form()
            cargar_lista()

        btn_guardar = ctk.CTkButton(frame_form, text="➕ Guardar Nuevo Usuario", command=guardar_usuario, fg_color="#27AE60", hover_color="#2ECC71")
        btn_guardar.grid(row=2, column=0, columnspan=2, pady=15, padx=5)
        
        btn_limpiar = ctk.CTkButton(frame_form, text="🧹 Cancelar / Limpiar", command=limpiar_form, fg_color="#7F8C8D", hover_color="#95A5A6")
        btn_limpiar.grid(row=2, column=2, columnspan=2, pady=15, padx=5)

        # --- PANEL INFERIOR: LISTA DE USUARIOS ---
        frame_lista = ctk.CTkScrollableFrame(ventana_usuarios, fg_color="transparent")
        frame_lista.pack(fill="both", expand=True, padx=20, pady=10)

        def editar_usuario(uid, uname, urol, ucom):
            limpiar_form()
            estado_edicion["id"] = uid
            ent_user.insert(0, uname)
            combo_rol.set(urol)
            ent_comision.insert(0, str(ucom))
            # Cambiamos el estilo del botón para avisar que estamos editando
            btn_guardar.configure(text="💾 Actualizar Usuario", fg_color="#D35400", hover_color="#E67E22")

        def eliminar_usuario(uid, uname):
            from tkinter import messagebox
            if uname.lower() == "admin":
                messagebox.showerror("Bloqueado", "No puedes eliminar al Administrador principal.")
                return
                
            respuesta = messagebox.askyesno("Confirmar", f"¿Estás seguro de que deseas eliminar al usuario '{uname}'?\nEsta acción no se puede deshacer.")
            if respuesta:
                conexion = sqlite3.connect(RUTA_DB)
                cursor = conexion.cursor()
                cursor.execute("DELETE FROM usuarios WHERE id=?", (uid,))
                conexion.commit()
                conexion.close()
                cargar_lista()

        def cargar_lista():
            for w in frame_lista.winfo_children():
                w.destroy()
            
            conexion = sqlite3.connect(RUTA_DB)
            cursor = conexion.cursor()
            # Si el programa truena aquí, es porque la base de datos es muy vieja y no corrió el ALTER TABLE arriba
            cursor.execute("SELECT id, username, rol, comision FROM usuarios")
            usuarios = cursor.fetchall()
            conexion.close()

            for uid, uname, urol, ucom in usuarios:
                f_usr = ctk.CTkFrame(frame_lista, border_width=1, border_color="#34495E")
                f_usr.pack(fill="x", pady=5, padx=5)
                
                # Texto Informativo
                txt_info = f"👤 {uname}   |   🛡️ Rol: {urol}   |   💰 Comisión: {ucom}%"
                ctk.CTkLabel(f_usr, text=txt_info, font=("Roboto", 14, "bold")).pack(side="left", padx=15, pady=15)
                
                # Botón Eliminar
                btn_del = ctk.CTkButton(f_usr, text="🗑️", width=40, fg_color="#C0392B", hover_color="#922B21",
                                        command=lambda id_u=uid, nom=uname: eliminar_usuario(id_u, nom))
                btn_del.pack(side="right", padx=10)
                
                # Botón Editar
                btn_edit = ctk.CTkButton(f_usr, text="✏️ Editar", width=80, fg_color="#2980B9", hover_color="#2471A3",
                                         command=lambda id_u=uid, n=uname, r=urol, c=ucom: editar_usuario(id_u, n, r, c))
                btn_edit.pack(side="right", padx=5)

        # Disparamos la carga inicial
        cargar_lista()

        ctk.CTkButton(frame_form, text="💾 Guardar Usuario", command=guardar_nuevo_usuario).grid(row=2, column=0, columnspan=3, pady=10)

        # Lista de Usuarios Actuales
        frame_lista = ctk.CTkScrollableFrame(ventana_usuarios)
        frame_lista.pack(fill="both", expand=True, padx=20, pady=10)

        def cargar_lista():
            for w in frame_lista.winfo_children():
                w.destroy()
            conexion = sqlite3.connect(RUTA_DB)
            cursor = conexion.cursor()
            cursor.execute("SELECT id, username, rol FROM usuarios")
            for uid, uname, urol in cursor.fetchall():
                f_usr = ctk.CTkFrame(frame_lista)
                f_usr.pack(fill="x", pady=2)
                ctk.CTkLabel(f_usr, text=f"👤 {uname} ({urol})", font=("Roboto", 12)).pack(side="left", padx=10)
                # Opcional: Agregar botón de eliminar aquí
            conexion.close()

        cargar_lista()   
    
    def abrir_historial_pagos_nomina(self):
        # 1. Limpiamos la pantalla principal
        for widget in self.area_principal.winfo_children():
            widget.destroy()

        ctk.CTkLabel(self.area_principal, text="📜 HISTORIAL DE NÓMINAS PAGADAS", 
                     font=("Roboto", 24, "bold"), text_color="cyan").pack(pady=20)

        # 2. Contenedor con Scroll
        area_historial = ctk.CTkScrollableFrame(self.area_principal, fg_color="transparent")
        area_historial.pack(fill="both", expand=True, padx=20, pady=10)

        try:
            conexion = sqlite3.connect(RUTA_DB)
            cursor = conexion.cursor()
            
            # Traemos todo cruzando con la tabla usuarios para tener el nombre
            query = """
                SELECT hp.id, u.username, hp.fecha_pago, hp.total_pagado, hp.notas, hp.detalle_trabajos 
                FROM historial_pagos hp
                LEFT JOIN usuarios u ON hp.id_usuario = u.id
                ORDER BY hp.fecha_pago DESC
            """
            cursor.execute(query)
            pagos = cursor.fetchall()
            conexion.close()

            if not pagos:
                ctk.CTkLabel(area_historial, text="Aún no hay registros de pagos a mecánicos.", text_color="gray").pack(pady=50)
                return

            for p_id, tec, fecha, total, notas, detalle in pagos:
                # Tarjeta principal del recibo
                card = ctk.CTkFrame(area_historial, border_width=1, border_color="#5D6D7E", fg_color="#2A2A2A")
                card.pack(pady=10, fill="x", padx=10)
                
                fecha_corta = str(fecha)[:16] if fecha else "S/F"
                nombre_tec = tec.upper() if tec else "USUARIO ELIMINADO"
                
                # Cabecera de la tarjeta (Técnico, Fecha y Total)
                header = ctk.CTkFrame(card, fg_color="transparent")
                header.pack(fill="x", padx=15, pady=10)
                
                ctk.CTkLabel(header, text=f"👤 TÉCNICO: {nombre_tec}", font=("Roboto", 15, "bold")).pack(side="left")
                ctk.CTkLabel(header, text=f"📅 {fecha_corta}", font=("Roboto", 13), text_color="gray").pack(side="left", padx=20)
               
               #ACTIVAR MODO SUPERUSUARIO PARA ELIMINAR RECIBOS 
               # NECESARIO QUITAR LOS SIMBOLOS DE NUMERAL PARA QUE NO HAYA CONFLICTO CON EL TEXTO DE LA ETIQUETA
                #btn_super = ctk.CTkButton(header, text="🗑️", width=30, fg_color="#C0392B", hover_color="#7B241C",
                #                         command=lambda id_p=p_id: self.eliminar_recibo_nomina_superusuario(id_p))
                #btn_super.pack(side="right", padx=(10, 0))
               
                ctk.CTkLabel(header, text=f"💰 TOTAL PAGADO: ${total:,.0f}", font=("Roboto", 16, "bold"), text_color="#2ECC71").pack(side="right")
                
                # Sección de Notas
                if notas and notas != "Sin notas adicionales.":
                    ctk.CTkLabel(card, text=f"📝 Notas: {notas}", text_color="#F39C12", font=("Roboto", 13, "italic")).pack(anchor="w", padx=15, pady=(0, 10))
                
                # Sección de detalle (El desmenuzado de motos)
                ctk.CTkLabel(card, text="Detalle de Trabajos Pagados:", font=("Roboto", 12, "bold")).pack(anchor="w", padx=15)
                ctk.CTkLabel(card, text=detalle, justify="left", text_color="#BDC3C7").pack(anchor="w", padx=25, pady=(5, 15))

        except sqlite3.OperationalError:
            # Por si alguien entra al historial sin haber hecho su primera liquidación nunca
            ctk.CTkLabel(area_historial, text="La bóveda está limpia. Haz tu primera liquidación para activar el historial.", text_color="gray").pack(pady=50)
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Error", f"No se pudo cargar el historial: {e}")

    def eliminar_recibo_nomina_superusuario(self, id_pago):
        from tkinter import messagebox
        # Advertencia doble por seguridad
        respuesta = messagebox.askyesno("⚠️ MODO SUPERUSUARIO", 
                                        "¿Estás seguro de que quieres DESTRUIR este recibo de nómina?\n\n"
                                        "Nota: Esto borrará el registro visual del historial. (Ideal para limpiar pruebas).")
        if respuesta:
            try:
                conexion = sqlite3.connect(RUTA_DB)
                cursor = conexion.cursor()
                
                # Fulminar el registro
                cursor.execute("DELETE FROM historial_pagos WHERE id = ?", (id_pago,))
                
                conexion.commit()
                conexion.close()
                
                messagebox.showinfo("Superusuario", "Recibo eliminado de la matriz.")
                self.abrir_historial_pagos_nomina() # Recargar la pantalla para ver que desapareció
                
            except Exception as e:
                messagebox.showerror("Error", f"Error al borrar: {e}")

    #=============================================
    # Módulo de Cuentas por Pagar
    #=============================================
# Bloque de ejecución directa (Con simulación de datos corregida)
    def abrir_modulo_proveedores(self):

        # 1. Limpiamos el área de trabajo como en tus otros módulos
        for widget in self.area_principal.winfo_children():
            widget.destroy()

        ctk.CTkLabel(self.area_principal, text="🏢 GESTIÓN DE PROVEEDORES Y CUENTAS POR PAGAR", font=("Roboto", 20, "bold"), text_color="cyan").pack(pady=10)

        # ==========================================
        # 2. PANEL SUPERIOR: REGISTRO DE FACTURA
        # ==========================================
        frame_registro = ctk.CTkFrame(self.area_principal, fg_color="#2A2A2A")
        frame_registro.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(frame_registro, text="Ingresar Nueva Factura de Compra", font=("Roboto", 14, "bold")).pack(pady=5)

        fila1 = ctk.CTkFrame(frame_registro, fg_color="transparent")
        fila1.pack(fill="x", pady=5)
        
        ent_prov = ctk.CTkEntry(fila1, placeholder_text="Nombre Proveedor (Ej: Repuestos XYZ)", width=200)
        ent_prov.pack(side="left", padx=5)
        
        ent_fac = ctk.CTkEntry(fila1, placeholder_text="N° Factura", width=120)
        ent_fac.pack(side="left", padx=5)
        
        ent_total = ctk.CTkEntry(fila1, placeholder_text="Total Normal ($)", width=130)
        ent_total.pack(side="left", padx=5)
        
        ent_desc = ctk.CTkEntry(fila1, placeholder_text="Total con Descuento ($)", width=150)
        ent_desc.pack(side="left", padx=5)

        fila2 = ctk.CTkFrame(frame_registro, fg_color="transparent")
        fila2.pack(fill="x", pady=5)
        
        ctk.CTkLabel(fila2, text="Límite Descuento:").pack(side="left", padx=5)
        ent_fecha_desc = ctk.CTkEntry(fila2, placeholder_text="YYYY-MM-DD", width=110)
        ent_fecha_desc.pack(side="left", padx=5)
        
        ctk.CTkLabel(fila2, text="Vencimiento Máximo:").pack(side="left", padx=5)
        ent_fecha_max = ctk.CTkEntry(fila2, placeholder_text="YYYY-MM-DD", width=110)
        ent_fecha_max.pack(side="left", padx=5)

        def guardar_factura_proveedor():
            prov = ent_prov.get().strip().upper()
            num = ent_fac.get().strip()
            f_desc = ent_fecha_desc.get().strip()
            f_max = ent_fecha_max.get().strip()
            
            try:
                tot_norm = float(ent_total.get().replace(".", "").replace(",", ""))
                tot_desc = float(ent_desc.get().replace(".", "").replace(",", "")) if ent_desc.get() else tot_norm
            except ValueError:
                from tkinter import messagebox
                messagebox.showerror("Error", "Los valores de dinero deben ser números válidos.")
                return

            if not all([prov, num, f_desc, f_max, tot_norm]):
                from tkinter import messagebox
                messagebox.showwarning("Faltan Datos", "Llena todos los campos obligatorios.")
                return

            try:
                conexion = sqlite3.connect(RUTA_DB)
                cursor = conexion.cursor()
                cursor.execute("""
                    INSERT INTO compras_facturas (proveedor, num_factura, fecha_limite_descuento, fecha_vencimiento_final, total_normal, total_con_descuento, saldo_pendiente)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (prov, num, f_desc, f_max, tot_norm, tot_desc, tot_norm))
                conexion.commit()
                conexion.close()
                
                from tkinter import messagebox
                messagebox.showinfo("Éxito", "Factura de compra registrada.\n¡El semáforo te avisará cuándo pagar!")
                
                # Recargar la vista actual para limpiar casillas y mostrar la nueva deuda
                self.abrir_modulo_proveedores()
                
            except Exception as e:
                from tkinter import messagebox
                messagebox.showerror("Error BD", str(e))

        ctk.CTkButton(fila2, text="💾 Registrar Deuda", fg_color="#27AE60", hover_color="#1E8449", command=guardar_factura_proveedor).pack(side="right", padx=10)

        # ==========================================
        # 3. PANEL INFERIOR: SEMÁFORO DE DEUDAS
        # ==========================================
        frame_lista = ctk.CTkScrollableFrame(self.area_principal, fg_color="transparent")
        frame_lista.pack(fill="both", expand=True, padx=10, pady=10)

        try:
            conexion = sqlite3.connect(RUTA_DB)
            cursor = conexion.cursor()
            cursor.execute("""
                SELECT id, proveedor, num_factura, fecha_limite_descuento, fecha_vencimiento_final, total_normal, total_con_descuento, saldo_pendiente, inventario_cargado,
                (date('now', 'localtime') <= fecha_limite_descuento) as aplica_descuento
                FROM compras_facturas
                WHERE estado = 'Pendiente'
                ORDER BY fecha_limite_descuento ASC
            """)
            deudas = cursor.fetchall()
            conexion.close()

            if not deudas:
                ctk.CTkLabel(frame_lista, text="✅ El taller está libre de deudas. No hay facturas de proveedores pendientes.", text_color="gray").pack(pady=30)
            
            for d_id, prov, num, f_desc, f_max, t_norm, t_desc, saldo, inv_cargado, aplica_desc in deudas:
                f_item = ctk.CTkFrame(frame_lista, border_width=1, border_color="#5D6D7E", fg_color="#1E1E1E")
                f_item.pack(fill="x", pady=5, padx=2)

                if aplica_desc:
                    color_fecha = "#2ECC71" # Verde
                    monto_a_pagar = t_desc if saldo == t_norm else saldo # Si abonó algo, se respeta el saldo
                    txt_alerta = f"🟢 ¡Aplica Descuento hasta {f_desc}!"
                else:
                    color_fecha = "#E74C3C" # Rojo
                    # Si perdió el descuento, la deuda vuelve al valor normal (restando lo que ya haya abonado)
                    abonos_previos = t_norm - saldo if saldo <= t_norm else 0
                    monto_a_pagar = t_norm - abonos_previos
                    txt_alerta = f"🔴 Descuento Perdido. Pagar antes de {f_max}"

                info_frame = ctk.CTkFrame(f_item, fg_color="transparent")
                info_frame.pack(side="left", padx=10, pady=10)
                
                ctk.CTkLabel(info_frame, text=f"🏢 {prov} | Factura N°: {num}", font=("Roboto", 14, "bold")).pack(anchor="w")
                ctk.CTkLabel(info_frame, text=txt_alerta, text_color=color_fecha, font=("Roboto", 12, "bold")).pack(anchor="w")

                acciones_frame = ctk.CTkFrame(f_item, fg_color="transparent")
                acciones_frame.pack(side="right", padx=10, pady=10)
                
                ctk.CTkLabel(acciones_frame, text=f"Deuda Actual: ${monto_a_pagar:,.0f}", font=("Roboto", 16, "bold"), text_color="yellow").pack(side="left", padx=15)
                
                # --- BOTÓN DE CARGAR INVENTARIO CONECTADO ---
                if inv_cargado == 0:
                    btn_inv = ctk.CTkButton(acciones_frame, text="📦 Cargar Repuestos", width=120, fg_color="#F39C12", hover_color="#D68910",
                                             command=lambda id_fac=d_id, p_nom=prov, f_num=num: self.abrir_ventana_carga_inventario(id_fac, p_nom, f_num))
                    btn_inv.pack(side="left", padx=5)
                else:
                    ctk.CTkLabel(acciones_frame, text="✅ Inventario Cargado", text_color="gray").pack(side="left", padx=5)

                # El botón de pago llama a la ventana de cobro que hicimos antes
                btn_pago = ctk.CTkButton(acciones_frame, text="💸 Realizar Pago", width=100, fg_color="#2980B9", hover_color="#2471A3",
                                         command=lambda id_fac=d_id, p_nom=prov, f_num=num, sald=monto_a_pagar: self.abrir_ventana_pago_proveedor(id_fac, p_nom, f_num, sald))
                btn_pago.pack(side="left", padx=5)

                # --- BOTÓN SUPERUSUARIO (Eliminar Factura) ---
                # Ponle un '#' al inicio de estas dos líneas cuando quieras ocultarlo
                btn_eliminar_prov = ctk.CTkButton(acciones_frame, text="🗑️", width=40, fg_color="#C0392B", hover_color="#922B21",
                                                  command=lambda id_f=d_id: self.eliminar_factura_proveedor_superusuario(id_f))
                btn_eliminar_prov.pack(side="left", padx=2)

        except Exception as e:
            ctk.CTkLabel(frame_lista, text=f"Error cargando deudas: {e}", text_color="red").pack()

    def abrir_ventana_carga_inventario(self, id_factura, proveedor, num_factura):
        ven_inv = ctk.CTkToplevel(self)
        ven_inv.title(f"Recepción de Bodega - {proveedor} (Fac: {num_factura})")
        ven_inv.geometry("750x650")
        ven_inv.grab_set()
        ven_inv.attributes('-topmost', True)

        # --- CABECERA ---
        frame_top = ctk.CTkFrame(ven_inv, fg_color="transparent")
        frame_top.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(frame_top, text=f"📦 Recepción: {proveedor}", font=("Roboto", 18, "bold"), text_color="cyan").pack(side="left")
        
        def finalizar_carga():
            try:
                conexion = sqlite3.connect(RUTA_DB)
                cursor = conexion.cursor()
                # Marcamos la factura como cargada
                cursor.execute("UPDATE compras_facturas SET inventario_cargado = 1 WHERE id = ?", (id_factura,))
                conexion.commit()
                conexion.close()
                
                from tkinter import messagebox
                messagebox.showinfo("Éxito", "¡Recepción finalizada!\nEl inventario ha sido actualizado.")
                ven_inv.destroy()
                self.abrir_modulo_proveedores() # Recarga el semáforo
            except Exception as e:
                from tkinter import messagebox
                messagebox.showerror("Error", str(e))

        ctk.CTkButton(frame_top, text="✅ FINALIZAR Y CERRAR FACTURA", fg_color="#E74C3C", hover_color="#C0392B", command=finalizar_carga).pack(side="right")

        # --- PESTAÑAS (EXISTENTES Y NUEVOS) ---
        tab_view = ctk.CTkTabview(ven_inv)
        tab_view.pack(fill="both", expand=True, padx=10, pady=10)
        
        tab_existente = tab_view.add("🔍 Sumar a Repuestos Existentes")
        tab_nuevo = tab_view.add("✨ Crear Nuevo Repuesto")

        # ==========================================
        # PESTAÑA 1: EXISTENTES
        # ==========================================
        ent_bus = ctk.CTkEntry(tab_existente, placeholder_text="Buscar SKU o Nombre...", width=350)
        ent_bus.pack(pady=5)
        
        frame_res = ctk.CTkScrollableFrame(tab_existente)
        frame_res.pack(pady=5, fill="both", expand=True)

        def buscar_repuestos_stock(termino=""):
            for w in frame_res.winfo_children(): w.destroy()
            conexion = sqlite3.connect(RUTA_DB)
            cursor = conexion.cursor()
            cursor.execute("SELECT id, sku, nombre_repuesto, stock FROM inventario WHERE sku LIKE ? OR nombre_repuesto LIKE ? LIMIT 30", ('%'+termino+'%', '%'+termino+'%'))
            items = cursor.fetchall()
            conexion.close()
            
            for r_id, sku, nom, stk in items:
                f_row = ctk.CTkFrame(frame_res, fg_color="transparent")
                f_row.pack(fill="x", pady=2)
                ctk.CTkLabel(f_row, text=f"{sku} | {nom} (Stock Actual: {stk})", anchor="w").pack(side="left", padx=5)
                ctk.CTkButton(f_row, text="➕ Ingresar", width=100, fg_color="#27AE60", 
                              command=lambda rid=r_id, rnom=nom: sumar_existente(rid, rnom)).pack(side="right", padx=5)

        ent_bus.bind("<KeyRelease>", lambda e: buscar_repuestos_stock(ent_bus.get().strip()))
        buscar_repuestos_stock()

        def sumar_existente(id_rep, nombre_rep):
            from tkinter import simpledialog, messagebox
            cant = simpledialog.askinteger("Cantidad", f"¿Cuántas unidades de '{nombre_rep}' llegaron?", minvalue=1)
            if not cant: return
            try:
                conexion = sqlite3.connect(RUTA_DB)
                cursor = conexion.cursor()
                cursor.execute("UPDATE inventario SET stock = stock + ? WHERE id = ?", (cant, id_rep))
                conexion.commit()
                conexion.close()
                messagebox.showinfo("Agregado", f"Se sumaron {cant} unidades a '{nombre_rep}'.")
                buscar_repuestos_stock(ent_bus.get().strip()) # Recarga la listita
            except Exception as e:
                messagebox.showerror("Error", str(e))

        # ==========================================
        # PESTAÑA 2: NUEVOS REPUESTOS
        # ==========================================
        f_form = ctk.CTkFrame(tab_nuevo, fg_color="transparent")
        f_form.pack(pady=20, padx=40, fill="both", expand=True)
        
        ctk.CTkLabel(f_form, text="SKU / Código:").grid(row=0, column=0, pady=5, sticky="w")
        ent_n_sku = ctk.CTkEntry(f_form, width=150)
        ent_n_sku.grid(row=0, column=1, pady=5, padx=10, sticky="w")
        
        ctk.CTkLabel(f_form, text="Nombre del Repuesto:").grid(row=1, column=0, pady=5, sticky="w")
        ent_n_nom = ctk.CTkEntry(f_form, width=250)
        ent_n_nom.grid(row=1, column=1, pady=5, padx=10, sticky="w")
        
        ctk.CTkLabel(f_form, text="Categoría:").grid(row=2, column=0, pady=5, sticky="w")
        ent_n_cat = ctk.CTkEntry(f_form, width=150)
        ent_n_cat.grid(row=2, column=1, pady=5, padx=10, sticky="w")
        
        ctk.CTkLabel(f_form, text="Costo Unid. ($):").grid(row=3, column=0, pady=5, sticky="w")
        ent_n_costo = ctk.CTkEntry(f_form, width=120)
        ent_n_costo.grid(row=3, column=1, pady=5, padx=10, sticky="w")
        
        ctk.CTkLabel(f_form, text="Precio Venta ($):").grid(row=4, column=0, pady=5, sticky="w")
        ent_n_venta = ctk.CTkEntry(f_form, width=120)
        ent_n_venta.grid(row=4, column=1, pady=5, padx=10, sticky="w")
        
        ctk.CTkLabel(f_form, text="Cantidad Recibida (Stock):").grid(row=5, column=0, pady=5, sticky="w")
        ent_n_cant = ctk.CTkEntry(f_form, width=80)
        ent_n_cant.grid(row=5, column=1, pady=5, padx=10, sticky="w")
        
        def crear_y_sumar_nuevo():
            sku = ent_n_sku.get().strip().upper()
            nom = ent_n_nom.get().strip()
            cat = ent_n_cat.get().strip().upper()
            try:
                costo = float(ent_n_costo.get().replace(".", "").replace(",", ""))
                venta = float(ent_n_venta.get().replace(".", "").replace(",", ""))
                cant = int(ent_n_cant.get())
            except:
                from tkinter import messagebox
                messagebox.showerror("Error", "Costo, Venta y Cantidad deben ser números.")
                return
                
            if not all([sku, nom, costo, venta, cant]):
                from tkinter import messagebox
                messagebox.showwarning("Datos", "Faltan datos por llenar.")
                return
                
            try:
                conexion = sqlite3.connect(RUTA_DB)
                cursor = conexion.cursor()
                cursor.execute("""
                    INSERT INTO inventario (sku, nombre_repuesto, categoria, stock, stock_minimo, precio_costo, precio_venta, ubicacion)
                    VALUES (?, ?, ?, ?, 0, ?, ?, '')
                """, (sku, nom, cat, cant, costo, venta))
                conexion.commit()
                conexion.close()
                
                from tkinter import messagebox
                messagebox.showinfo("Éxito", f"'{nom}' creado con {cant} unidades en bodega.")
                
                # Limpiar formulario
                for entry in [ent_n_sku, ent_n_nom, ent_n_cat, ent_n_costo, ent_n_venta, ent_n_cant]:
                    entry.delete(0, 'end')
                
                buscar_repuestos_stock(ent_bus.get().strip()) # Refrescar listado
                
            except sqlite3.IntegrityError:
                from tkinter import messagebox
                messagebox.showerror("Error", "Ese SKU / Código ya existe en tu inventario.")
            except Exception as e:
                from tkinter import messagebox
                messagebox.showerror("Error", str(e))

        ctk.CTkButton(f_form, text="✨ Guardar Nuevo Repuesto en Bodega", fg_color="#8E44AD", hover_color="#732D91", 
                      command=crear_y_sumar_nuevo).grid(row=6, column=0, columnspan=2, pady=20)

    def abrir_ventana_pago_proveedor(self, id_factura, proveedor, num_factura, deuda_actual):
        ven_pago = ctk.CTkToplevel(self)
        ven_pago.title(f"Pago a {proveedor} - Fac: {num_factura}")
        ven_pago.geometry("350x250")
        ven_pago.grab_set() # Bloquea la ventana de atrás
        ven_pago.attributes('-topmost', True)

        ctk.CTkLabel(ven_pago, text=f"Deuda Actual: ${deuda_actual:,.0f}", font=("Roboto", 18, "bold"), text_color="#E74C3C").pack(pady=20)
        
        ctk.CTkLabel(ven_pago, text="Monto a Pagar / Abonar ($):").pack(pady=5)
        ent_monto = ctk.CTkEntry(ven_pago, width=150, justify="center")
        ent_monto.pack(pady=5)
        ent_monto.focus()

        def confirmar_pago():
            try:
                # Limpiamos el texto por si el usuario pone puntos o comas
                monto = float(ent_monto.get().replace(".", "").replace(",", ""))
                
                if monto <= 0:
                    from tkinter import messagebox
                    messagebox.showwarning("Error", "Ingresa un monto mayor a 0.")
                    return
                if monto > deuda_actual:
                    from tkinter import messagebox
                    messagebox.showwarning("Error", f"No puedes pagar más de la deuda actual (${deuda_actual:,.0f}).")
                    return

                conexion = sqlite3.connect(RUTA_DB)
                cursor = conexion.cursor()
                
                # 1. Actualizamos la deuda en la factura del proveedor
                nueva_deuda = deuda_actual - monto
                nuevo_estado = "Pagada" if nueva_deuda == 0 else "Pendiente"
                
                cursor.execute("""
                    UPDATE compras_facturas 
                    SET saldo_pendiente = ?, estado = ? 
                    WHERE id = ?
                """, (nueva_deuda, nuevo_estado, id_factura))
                
                # 2. Descontamos el dinero automáticamente de la caja del taller
                cursor.execute("""
                    INSERT INTO gastos_diarios (descripcion, monto, fecha) 
                    VALUES (?, ?, datetime('now', 'localtime'))
                """, (f"Pago a Proveedor: {proveedor} (Fac: {num_factura})", monto))
                
                conexion.commit()
                conexion.close()
                
                from tkinter import messagebox
                messagebox.showinfo("💸 Pago Exitoso", f"Se descontaron ${monto:,.0f} de tu caja general.\n\nNuevo saldo de la factura: ${nueva_deuda:,.0f}")
                ven_pago.destroy()
                
                # Refrescamos la pantalla para que el semáforo se actualice
                self.renderizar_cuentas_por_pagar()
                
            except ValueError:
                from tkinter import messagebox
                messagebox.showerror("Error", "Por favor ingresa un número válido.")
            except Exception as e:
                from tkinter import messagebox
                messagebox.showerror("Error de Sistema", str(e))

        ctk.CTkButton(ven_pago, text="✅ Confirmar Pago", font=("Roboto", 16, "bold"), height=40, fg_color="#27AE60", hover_color="#1E8449", command=confirmar_pago).pack(pady=20)

    def eliminar_factura_proveedor_superusuario(self, id_factura_compra):
        from tkinter import messagebox
        respuesta = messagebox.askyesno("⚠️ MODO SUPERUSUARIO", 
                                        "¿Estás seguro de que quieres DESTRUIR esta factura de proveedor?\n\n"
                                        "Nota: Esto borrará el registro de las cuentas por pagar. (Ideal para limpiar pruebas).")
        if respuesta:
            try:
                conexion = sqlite3.connect(RUTA_DB)
                cursor = conexion.cursor()
                
                cursor.execute("DELETE FROM compras_facturas WHERE id = ?", (id_factura_compra,))
                
                conexion.commit()
                conexion.close()
                
                messagebox.showinfo("Superusuario", "Factura de proveedor eliminada de la matriz.")
                self.abrir_modulo_proveedores()
                
            except Exception as e:
                messagebox.showerror("Error", f"Error al borrar: {e}")

    





if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    # CORRECCIÓN: Simulamos el usuario como lo enviaría el login para que funcione el guardado
    usuario_simulado = (1, "admin", "admin123", "Vendedor", 50) 
    app = MenuPrincipal(usuario=usuario_simulado, rol="Admin") 
    
    app.mainloop()