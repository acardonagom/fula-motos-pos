from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from datetime import datetime
import sqlite3
import os
import tempfile
from flask import send_file
from fpdf import FPDF

app = Flask(__name__)
# Una clave secreta necesaria para mantener la sesión del usuario abierta
app.secret_key = "fula_motos_secreto_123" 

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUTA_DB = os.path.join(BASE_DIR, "Database", "fula_motos.db")

def conectar_db():
    conn = sqlite3.connect(RUTA_DB)
    conn.row_factory = sqlite3.Row
    return conn

# --- RUTAS DE LA PÁGINA WEB ---

@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        # Lo que el usuario escribe en la pantallita del celular
        usuario_input = request.form['usuario'] 
        password_input = request.form['password']
        
        conexion = conectar_db()
        cursor = conexion.cursor()
        
        # ¡LA CORRECCIÓN MÁGICA! Buscamos la columna 'username'
        cursor.execute("SELECT id, username, rol FROM usuarios WHERE username = ? AND password = ?", (usuario_input, password_input))
        user = cursor.fetchone()
        conexion.close()
        
        if user:
            # Guardamos los datos en la "memoria" del celular usando 'username'
            session['user_id'] = user['id']
            session['nombre'] = user['username'] 
            session['rol'] = user['rol']
            return redirect(url_for('dashboard'))
        else:
            error = "Usuario o contraseña incorrectos"
            
    # Si entra normal (GET) o hay error, mostramos la pantalla de login
    return render_template('login.html', error=error)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Cargamos el HTML del menú que acabamos de crear
    return render_template('dashboard.html')

@app.route('/motos', methods=['GET', 'POST'])
def motos():
    if 'user_id' not in session: return redirect(url_for('login'))
    if session['rol'] == 'Vendedor': return redirect(url_for('dashboard')) 

    conexion = conectar_db()
    cursor = conexion.cursor()
    mensaje = None

    if request.args.get('exito'):
        mensaje = "¡Operación guardada con éxito!"

    if request.method == 'POST':
        placa = request.form['placa'].upper()
        marca = request.form['marca']
        modelo = request.form['modelo']
        documento = request.form['documento']  # <--- NUEVA TUERCA: CÉDULA
        cliente = request.form['cliente']
        telefono = request.form['telefono']
        diagnostico = request.form['diagnostico']
        kilometraje = request.form.get('kilometraje', '0')
        
        try:
            mano_obra = float(request.form.get('mano_obra', 0))
        except ValueError:
            mano_obra = 0.0

        nombre_actual = session['nombre']

        # 1. Guardar/Actualizar al CLIENTE en su tabla oficial
        cursor.execute("SELECT documento FROM clientes WHERE documento = ?", (documento,))
        if cursor.fetchone():
            cursor.execute("UPDATE clientes SET nombre=?, telefono=? WHERE documento=?", (cliente, telefono, documento))
        else:
            cursor.execute("INSERT INTO clientes (documento, nombre, telefono) VALUES (?, ?, ?)", (documento, cliente, telefono))

        # 2. Guardar/Actualizar el VEHÍCULO
        cursor.execute("SELECT placa FROM vehiculos WHERE placa = ?", (placa,))
        if cursor.fetchone():
            cursor.execute("UPDATE vehiculos SET marca=?, modelo=?, propietario=?, telefono=? WHERE placa=?", 
                           (marca, modelo, cliente, telefono, placa))
        else:
            cursor.execute("INSERT INTO vehiculos (placa, marca, modelo, propietario, telefono) VALUES (?, ?, ?, ?, ?)", 
                           (placa, marca, modelo, cliente, telefono))

        # 3. Revisar si hay SERVICIO ABIERTO
        cursor.execute("""
            SELECT id, diagnostico, valor_mano_obra 
            FROM servicios WHERE placa_moto = ? AND estado = 'Pendiente'
        """, (placa,))
        servicio_abierto = cursor.fetchone()

        if servicio_abierto:
            id_abierto = servicio_abierto['id']
            diag_viejo = servicio_abierto['diagnostico']
            mo_vieja = servicio_abierto['valor_mano_obra'] if servicio_abierto['valor_mano_obra'] else 0.0
            
            # --- CORRECCIÓN: Inyectamos la variable 'kilometraje' en el texto ---
            nuevo_diag = f"{diag_viejo}\n[+ {nombre_actual} | KM: {kilometraje} | Cobro: ${mano_obra:,.0f}]: {diagnostico}"
            nueva_mo = mo_vieja + mano_obra
            
            cursor.execute("""
                UPDATE servicios 
                SET diagnostico = ?, valor_mano_obra = ?, cliente_nombre = ?, cliente_telefono = ?, marca_moto = ?, modelo_moto = ?, documento_cliente = ? 
                WHERE id = ?
            """, (nuevo_diag, nueva_mo, cliente, telefono, marca, modelo, documento, id_abierto))
        else:
            # --- CORRECCIÓN: Aquí también inyectamos la variable 'kilometraje' ---
            diag_inicial = f"[{nombre_actual} | KM: {kilometraje} | Cobro: ${mano_obra:,.0f}]: {diagnostico}"
            
            cursor.execute("""
                INSERT INTO servicios (placa_moto, diagnostico, estado, id_usuario, cliente_nombre, cliente_telefono, marca_moto, modelo_moto, valor_mano_obra, documento_cliente)
                VALUES (?, ?, 'Pendiente', ?, ?, ?, ?, ?, ?, ?)
            """, (placa, diag_inicial, session['user_id'], cliente, telefono, marca, modelo, mano_obra, documento))
            
        conexion.commit()
        conexion.close()
        return redirect(url_for('motos', exito='1'))

    # Traer las activas (Añadimos s.valor_mano_obra a la búsqueda)
    cursor.execute("""
        SELECT s.id, s.placa_moto, s.marca_moto, s.modelo_moto, s.documento_cliente, s.cliente_nombre, s.cliente_telefono, s.fecha_ingreso, s.diagnostico, s.valor_mano_obra, u.username as mecanico
        FROM servicios s JOIN usuarios u ON s.id_usuario = u.id
        WHERE s.estado = 'Pendiente' ORDER BY s.fecha_ingreso DESC
    """)
    servicios_raw = cursor.fetchall()
    
    servicios_activos = []
    for s in servicios_raw:
        s_dict = dict(s)
        cursor.execute("""
            SELECT i.nombre_repuesto, sr.cantidad, sr.precio_unitario 
            FROM servicios_repuestos sr JOIN inventario i ON sr.id_repuesto = i.id 
            WHERE sr.id_servicio = ?
        """, (s['id'],))
        
        repuestos_lista = cursor.fetchall()
        total_repuestos = 0
        repuestos_con_subtotal = []
        for rep in repuestos_lista:
            rep_dict = dict(rep)
            precio = rep_dict['precio_unitario'] if rep_dict['precio_unitario'] else 0 
            subtotal_rep = rep_dict['cantidad'] * precio
            total_repuestos += subtotal_rep
            rep_dict['precio_fmt'] = f"${precio:,.0f}"
            rep_dict['subtotal_fmt'] = f"${subtotal_rep:,.0f}"
            repuestos_con_subtotal.append(rep_dict)

        mano_obra = s['valor_mano_obra'] if s['valor_mano_obra'] else 0
        gran_total = total_repuestos + mano_obra

        # LA MAGIA: Cortamos el texto por cada 'Enter' para hacer una lista
        s_dict['diagnostico_lista'] = s['diagnostico'].split('\n') if s['diagnostico'] else []
        
        s_dict['repuestos'] = repuestos_con_subtotal
        s_dict['mano_obra_fmt'] = f"${mano_obra:,.0f}"
        s_dict['total_repuestos_fmt'] = f"${total_repuestos:,.0f}"
        s_dict['gran_total_fmt'] = f"${gran_total:,.0f}"
        
        servicios_activos.append(s_dict)

    conexion.close()
    return render_template('motos.html', servicios=servicios_activos, mensaje=mensaje)

# --- EL API AHORA TAMBIÉN BUSCA LA CÉDULA ---
@app.route('/api/vehiculo/<placa>')
def api_vehiculo(placa):
    conexion = conectar_db()
    cursor = conexion.cursor()
    cursor.execute("SELECT marca, modelo, propietario, telefono FROM vehiculos WHERE placa = ?", (placa.upper(),))
    vehiculo = cursor.fetchone()
    
    documento_encontrado = ""
    if vehiculo:
        # Buscamos la última cédula que se usó para esta moto en los servicios
        cursor.execute("SELECT documento_cliente FROM servicios WHERE placa_moto = ? AND documento_cliente IS NOT NULL ORDER BY id DESC LIMIT 1", (placa.upper(),))
        doc_row = cursor.fetchone()
        if doc_row:
            documento_encontrado = doc_row['documento_cliente']
            
    conexion.close()
    
    if vehiculo:
        return jsonify({'encontrado': True, 'marca': vehiculo['marca'], 'modelo': vehiculo['modelo'], 'propietario': vehiculo['propietario'], 'telefono': vehiculo['telefono'], 'documento': documento_encontrado})
    return jsonify({'encontrado': False})

@app.route('/historial_motos')
def historial_motos():
    if 'user_id' not in session or session['rol'] == 'Vendedor':
        return redirect(url_for('dashboard'))
        
    conexion = conectar_db()
    cursor = conexion.cursor()
    cursor.execute("""
        SELECT s.id, s.placa_moto, s.marca_moto, s.modelo_moto, s.cliente_nombre, s.cliente_telefono, s.fecha_ingreso, s.diagnostico, s.estado, s.valor_mano_obra, u.username as mecanico
        FROM servicios s JOIN usuarios u ON s.id_usuario = u.id
        ORDER BY s.fecha_ingreso DESC
    """)
    historial_raw = cursor.fetchall()
    
    historial = []
    for s in historial_raw:
        s_dict = dict(s)
        cursor.execute("""
            SELECT i.nombre_repuesto, sr.cantidad, sr.precio_unitario 
            FROM servicios_repuestos sr JOIN inventario i ON sr.id_repuesto = i.id 
            WHERE sr.id_servicio = ?
        """, (s['id'],))
        
        repuestos_lista = cursor.fetchall()
        total_repuestos = 0
        repuestos_con_subtotal = []
        for rep in repuestos_lista:
            rep_dict = dict(rep)
            precio = rep_dict['precio_unitario'] if rep_dict['precio_unitario'] else 0
            subtotal_rep = rep_dict['cantidad'] * precio
            total_repuestos += subtotal_rep
            rep_dict['precio_fmt'] = f"${precio:,.0f}"
            rep_dict['subtotal_fmt'] = f"${subtotal_rep:,.0f}"
            repuestos_con_subtotal.append(rep_dict)

        mano_obra = s['valor_mano_obra'] if s['valor_mano_obra'] else 0
        gran_total = total_repuestos + mano_obra

        # LA MAGIA: Cortamos el texto por cada 'Enter' para hacer una lista
        s_dict['diagnostico_lista'] = s['diagnostico'].split('\n') if s['diagnostico'] else []

        s_dict['repuestos'] = repuestos_con_subtotal
        s_dict['mano_obra_fmt'] = f"${mano_obra:,.0f}"
        s_dict['total_repuestos_fmt'] = f"${total_repuestos:,.0f}"
        s_dict['gran_total_fmt'] = f"${gran_total:,.0f}"
        
        historial.append(s_dict)
        
    conexion.close()
    return render_template('historial_motos.html', historial=historial)

from datetime import datetime

@app.route('/admin_dashboard')
def admin_dashboard():
    # 1. Verificar que haya iniciado sesión
    if 'user_id' not in session: 
        return redirect(url_for('login'))
        
    rol = session.get('rol')
    # 2. Permitir tanto al Admin como al Vendedor
    if rol not in ['Admin', 'Vendedor']: 
        return "Acceso denegado. No tienes permisos para ver la caja.", 403

    conexion = conectar_db()
    # Aseguramos que los resultados se puedan leer como diccionario para el HTML
    conexion.row_factory = sqlite3.Row 
    cursor = conexion.cursor()

    # ==========================================
    # 3. LA MÁQUINA DEL TIEMPO (Filtros)
    # ==========================================
    filtro_fecha = request.args.get('fecha') # Viene como YYYY-MM-DD
    filtro_mes = request.args.get('mes')     # Viene como YYYY-MM
    
    # Creamos condiciones separadas porque la tabla facturas usa alias 'f'
    if rol == 'Admin' and filtro_fecha:
        cond_f = f"date(f.fecha) = '{filtro_fecha}'"
        cond_c = f"date(fecha) = '{filtro_fecha}'"
        fecha_texto = f"{filtro_fecha}"
    elif rol == 'Admin' and filtro_mes:
        cond_f = f"strftime('%Y-%m', f.fecha) = '{filtro_mes}'"
        cond_c = f"strftime('%Y-%m', fecha) = '{filtro_mes}'"
        fecha_texto = f"Mes {filtro_mes}"
    else:
        # Por defecto es HOY
        cond_f = "date(f.fecha) = date('now', 'localtime')"
        cond_c = "date(fecha) = date('now', 'localtime')"
        fecha_texto = "Hoy"

    # ==========================================
    # 4. CÁLCULO DE CAJA (Ventas + Entradas - Gastos)
    # ==========================================
    cursor.execute(f"SELECT SUM(total) FROM facturas f WHERE {cond_f} AND f.estado = 'Pagada'")
    ventas_pos = cursor.fetchone()[0] or 0.0
    
    cursor.execute(f"SELECT SUM(monto) FROM entradas_caja WHERE {cond_c}")
    ingresos_manuales = cursor.fetchone()[0] or 0.0
    
    total_ingresos = ventas_pos + ingresos_manuales

    cursor.execute(f"SELECT SUM(monto) FROM gastos_diarios WHERE {cond_c}")
    total_gastos = cursor.fetchone()[0] or 0.0
    
    saldo_caja = total_ingresos - total_gastos

    # ==========================================
    # 5. INVENTARIO Y TOP 10
    # ==========================================
    # Reposición
    cursor.execute("SELECT nombre_repuesto, stock, stock_minimo FROM inventario WHERE stock <= stock_minimo ORDER BY stock ASC")
    reposicion = [dict(row) for row in cursor.fetchall()]

    # Top 10 (Histórico global: le quitamos el cond_f y lo hacemos insensible a mayúsculas)
    cursor.execute("""
        SELECT i.nombre_repuesto, SUM(df.cantidad) as total_vendido 
        FROM detalles_factura df 
        JOIN facturas f ON df.id_factura = f.id 
        JOIN inventario i ON df.id_item = i.id 
        WHERE LOWER(df.tipo_item) LIKE '%repuesto%' AND f.estado = 'Pagada'
        GROUP BY i.id 
        ORDER BY total_vendido DESC LIMIT 10
    """)
    top_repuestos = [dict(row) for row in cursor.fetchall()]
    
    conexion.close()

    # Como el nuevo HTML que te pasé hace el formato con Jinja ( {:,.0f} ), 
    # enviamos los números puros.
    return render_template('admin_dashboard.html', 
                           ventas=total_ingresos, 
                           gastos=total_gastos, 
                           saldo=saldo_caja, 
                           reposicion=reposicion, 
                           top=top_repuestos, 
                           fecha_texto=fecha_texto)

@app.route('/inventario')
def inventario():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conexion = conectar_db()
    cursor = conexion.cursor()
    
    # 1. Traemos el inventario incluyendo la categoría
    cursor.execute("SELECT sku, nombre_repuesto, stock, stock_minimo, ubicacion, categoria FROM inventario ORDER BY nombre_repuesto ASC")
    repuestos = cursor.fetchall()
    
    # 2. Traemos las categorías únicas para el menú desplegable
    cursor.execute("SELECT DISTINCT categoria FROM inventario WHERE categoria IS NOT NULL AND categoria != '' ORDER BY categoria ASC")
    categorias = [row['categoria'] for row in cursor.fetchall()]
    
    conexion.close()
    
    return render_template('inventario.html', repuestos=repuestos, categorias=categorias)

# --- INVENTARIO MAESTRO (SOLO ADMIN) ---
@app.route('/inventario_maestro')
def inventario_maestro():
    if 'user_id' not in session or session.get('rol') != 'Admin':
        return redirect(url_for('dashboard'))

    conexion = conectar_db()
    cursor = conexion.cursor()
    
    # 1. Traemos los repuestos
    cursor.execute("""
        SELECT id, sku, nombre_repuesto, categoria, ubicacion, stock, stock_minimo, 
               IFNULL(precio_costo, 0) as precio_costo, 
               IFNULL(precio_venta, 0) as precio_venta 
        FROM inventario 
        ORDER BY nombre_repuesto ASC
    """)
    repuestos = cursor.fetchall()
    
    # 2. NUEVO: Traemos las categorías únicas para el filtro
    cursor.execute("SELECT DISTINCT categoria FROM inventario WHERE categoria IS NOT NULL AND categoria != '' ORDER BY categoria ASC")
    categorias = [row[0] for row in cursor.fetchall()]
    
    conexion.close()
    
    mensaje = None
    if request.args.get('exito'): mensaje = "✅ Repuesto guardado correctamente."
    if request.args.get('borrado'): mensaje = "🗑️ Repuesto eliminado del sistema."
    
    # Le pasamos la variable "categorias" al HTML
    return render_template('inventario_maestro.html', repuestos=repuestos, categorias=categorias, mensaje=mensaje)

@app.route('/inventario_maestro/guardar', methods=['POST'])
def guardar_repuesto():
    if 'user_id' not in session or session.get('rol') != 'Admin':
        return redirect(url_for('login'))
        
    id_repuesto = request.form.get('id_repuesto') 
    sku = request.form.get('sku', '').upper()
    nombre = request.form.get('nombre', '').upper()
    categoria = request.form.get('categoria', 'GENERAL').upper()
    ubicacion = request.form.get('ubicacion', '').upper()
    
    try: stock = int(request.form.get('stock', 0))
    except ValueError: stock = 0
    try: stock_min = int(request.form.get('stock_minimo', 0))
    except ValueError: stock_min = 0
    
    # Capturamos ambos precios
    try: costo = float(request.form.get('precio_costo', 0))
    except ValueError: costo = 0.0
    try: venta = float(request.form.get('precio_venta', 0))
    except ValueError: venta = 0.0
    
    conexion = conectar_db()
    cursor = conexion.cursor()
    
    if id_repuesto: # EDITAR
        cursor.execute("""
            UPDATE inventario 
            SET sku=?, nombre_repuesto=?, categoria=?, ubicacion=?, stock=?, stock_minimo=?, precio_costo=?, precio_venta=?
            WHERE id=?
        """, (sku, nombre, categoria, ubicacion, stock, stock_min, costo, venta, id_repuesto))
    else: # NUEVO
        cursor.execute("""
            INSERT INTO inventario (sku, nombre_repuesto, categoria, ubicacion, stock, stock_minimo, precio_costo, precio_venta)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (sku, nombre, categoria, ubicacion, stock, stock_min, costo, venta))
        
    conexion.commit()
    conexion.close()
    return redirect(url_for('inventario_maestro', exito='1'))

@app.route('/inventario_maestro/eliminar/<int:id_repuesto>', methods=['POST'])
def eliminar_repuesto(id_repuesto):
    if 'user_id' not in session or session.get('rol') != 'Admin':
        return redirect(url_for('login'))
        
    conexion = conectar_db()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM inventario WHERE id=?", (id_repuesto,))
    conexion.commit()
    conexion.close()
    return redirect(url_for('inventario_maestro', borrado='1'))

# ==========================================
# --- MÓDULO DE NÓMINA Y COMISIONES WEB ---
# ==========================================
@app.route('/nomina_web')
def nomina_web():
    if 'user_id' not in session or session.get('rol') != 'Admin':
        return redirect(url_for('dashboard'))
        
    conexion = conectar_db()
    cursor = conexion.cursor()
    
    # 1. PENDIENTES DE PAGO (Mano de obra terminada y facturada)
    cursor.execute("""
        SELECT u.id, u.username, u.comision, SUM(df.subtotal) as total_mo
        FROM detalles_factura df
        JOIN facturas f ON df.id_factura = f.id
        JOIN servicios s ON df.id_item = s.id
        JOIN usuarios u ON s.id_usuario = u.id
        WHERE df.tipo_item = 'servicio' AND f.estado = 'Pagada' AND s.pago_tecnico = 0
        GROUP BY u.id
    """)
    resumen_raw = cursor.fetchall()
    
    # 2. DETALLE DE TRABAJOS PENDIENTES (Para mostrar en el recibo)
    cursor.execute("""
        SELECT s.id_usuario, f.consecutivo, f.fecha, s.placa_moto, df.descripcion, df.subtotal 
        FROM detalles_factura df
        JOIN facturas f ON df.id_factura = f.id
        JOIN servicios s ON df.id_item = s.id
        WHERE df.tipo_item = 'servicio' AND f.estado = 'Pagada' AND s.pago_tecnico = 0
        ORDER BY f.fecha DESC
    """)
    detalles_raw = cursor.fetchall()
    
    # Preparamos los datos organizados para enviarlos al HTML
    nominas = []
    for r in resumen_raw:
        id_tec = r['id']
        nombre = r['username']
        comision = r['comision'] if r['comision'] else 0
        total_mo = r['total_mo']
        pago = total_mo * (comision / 100)
        
        # Filtramos solo los trabajos que pertenecen a este técnico
        trabajos = [dict(d) for d in detalles_raw if d['id_usuario'] == id_tec]
        
        # Armamos el texto gigante del recibo que se guardará en el historial
        texto_detalle = ""
        for t in trabajos:
            fecha_str = str(t['fecha'])[:16] if t['fecha'] else "S/F"
            texto_detalle += f"[{t['placa_moto']}] Fac: {t['consecutivo']} | {t['descripcion']} (${t['subtotal']:,.0f})\n"
            
        nominas.append({
            'id_tec': id_tec,
            'nombre': nombre,
            'comision': comision,
            'total_mo': total_mo,
            'pago': pago,
            'trabajos': trabajos,
            'texto_detalle': texto_detalle
        })
        
    # 3. HISTORIAL DE PAGOS REALIZADOS (Últimos 30 para no saturar el celular)
    cursor.execute("""
        SELECT hp.id, u.username, hp.fecha_pago, hp.total_pagado, hp.notas, hp.detalle_trabajos 
        FROM historial_pagos hp
        LEFT JOIN usuarios u ON hp.id_usuario = u.id
        ORDER BY hp.fecha_pago DESC LIMIT 30
    """)
    historial = cursor.fetchall()
    conexion.close()
    
    mensaje = None
    if request.args.get('exito'): mensaje = "✅ Liquidación procesada y descontada de caja con éxito."
    
    return render_template('nomina_web.html', nominas=nominas, historial=historial, mensaje=mensaje)

@app.route('/nomina_web/pagar', methods=['POST'])
def procesar_pago_nomina_web():
    if 'user_id' not in session or session.get('rol') != 'Admin':
        return redirect(url_for('login'))
        
    id_tec = request.form.get('id_tec')
    nombre = request.form.get('nombre')
    total_pagado = float(request.form.get('total_pagado', 0))
    notas = request.form.get('notas', '').strip()
    detalle_trabajos = request.form.get('detalle_trabajos', '')
    
    if not notas: notas = "Sin notas adicionales."
        
    conexion = conectar_db()
    cursor = conexion.cursor()
    
    try:
        # 1. Guardar en la bóveda (Historial)
        cursor.execute("""
            INSERT INTO historial_pagos (id_usuario, total_pagado, notas, detalle_trabajos)
            VALUES (?, ?, ?, ?)
        """, (id_tec, total_pagado, notas, detalle_trabajos))
        
        # 2. Marcar cada moto facturada de este técnico como "PAGADA"
        cursor.execute("""
            UPDATE servicios SET pago_tecnico = 1 
            WHERE id IN (
                SELECT s.id FROM servicios s
                JOIN detalles_factura df ON s.id = df.id_item
                JOIN facturas f ON df.id_factura = f.id
                WHERE s.id_usuario = ? AND df.tipo_item = 'servicio' AND f.estado = 'Pagada'
            )
        """, (id_tec,))
        
        # 3. Registrar la salida del dinero de la caja
        cursor.execute("""
            INSERT INTO gastos_diarios (descripcion, monto, fecha) 
            VALUES (?, ?, datetime('now', 'localtime'))
        """, (f"Pago Nómina: {nombre.upper()}", total_pagado))
        
        conexion.commit()
    except Exception as e:
        print("Error al pagar nómina en Web:", e)
    finally:
        conexion.close()
        
    return redirect(url_for('nomina_web', exito='1'))

# ==========================================
# --- PUNTO DE VENTA (POS WEB) ---
# ==========================================

@app.route('/pos_web')
def pos_web():
    if 'user_id' not in session: return redirect(url_for('login'))
        
    conexion = conectar_db()
    cursor = conexion.cursor()
    
    # 1. Repuestos
    cursor.execute("SELECT id, sku, nombre_repuesto, stock, IFNULL(precio_venta, 0) as precio_venta FROM inventario WHERE stock > 0 ORDER BY nombre_repuesto ASC")
    repuestos = cursor.fetchall()
    
    # 2. Generar Pre-consecutivo
    cursor.execute("SELECT COUNT(id) FROM facturas")
    conteo = cursor.fetchone()[0]
    siguiente_factura = f"POS-{conteo + 1000}"
    
    # 3. Traer motos pendientes en el taller
    cursor.execute("SELECT id, placa_moto, cliente_nombre FROM servicios WHERE estado = 'Pendiente'")
    motos_taller = cursor.fetchall()
    conexion.close()
    
    return render_template('pos_web.html', repuestos=repuestos, numero_factura=siguiente_factura, motos=motos_taller)

@app.route('/api/moto_detalles/<int:id_servicio>')
def api_moto_detalles(id_servicio):
    conexion = conectar_db()
    cursor = conexion.cursor()
    cursor.execute("SELECT placa_moto, cliente_nombre, cliente_telefono, documento_cliente, valor_mano_obra FROM servicios WHERE id = ?", (id_servicio,))
    moto = cursor.fetchone()
    
    cursor.execute("""
        SELECT i.id, i.nombre_repuesto, sr.cantidad, sr.precio_unitario 
        FROM servicios_repuestos sr
        JOIN inventario i ON sr.id_repuesto = i.id
        WHERE sr.id_servicio = ?
    """, (id_servicio,))
    repuestos = cursor.fetchall()
    conexion.close()
    
    if moto:
        res_rep = [{'id': r['id'], 'nombre': r['nombre_repuesto'], 'cantidad': r['cantidad'], 'precio': r['precio_unitario'], 'tipo': 'repuesto_taller'} for r in repuestos]
        return jsonify({
            'success': True,
            'placa': moto['placa_moto'],
            'nombre': moto['cliente_nombre'],
            'telefono': moto['cliente_telefono'],
            'documento': moto['documento_cliente'],
            'mano_obra': moto['valor_mano_obra'] or 0,
            'repuestos_taller': res_rep
        })
    return jsonify({'success': False})

@app.route('/pos_web/procesar', methods=['POST'])
def pos_web_procesar():
    if 'user_id' not in session: return jsonify({'success': False, 'mensaje': 'Sesión expirada'})

    datos = request.get_json()
    accion = datos.get('accion') # 'Cobrar', 'Guardar' o 'Cotizar'
    
    cliente = datos.get('cliente', 'Cliente Mostrador').strip() or 'Cliente Mostrador'
    documento = datos.get('documento', '000000000').strip() or '000000000'
    telefono = datos.get('telefono', '').strip()
    direccion = datos.get('direccion', '').strip()
    placa_moto = datos.get('placa', '').upper()
    
    id_servicio = datos.get('id_servicio')
    id_factura_abierta = datos.get('id_factura_abierta')
    carrito = datos.get('carrito', [])
    
    total_factura = sum(item['subtotal'] for item in carrito)
    if not carrito: return jsonify({'success': False, 'mensaje': 'El carrito está vacío'})

    try:
        conexion = conectar_db()
        cursor = conexion.cursor()

        # Cliente
        cursor.execute("INSERT OR IGNORE INTO clientes (documento, nombre, telefono, direccion, correo) VALUES (?, ?, ?, ?, '')", (documento, cliente, telefono, direccion))
        cursor.execute("UPDATE clientes SET nombre=?, telefono=?, direccion=? WHERE documento=?", (cliente, telefono, direccion, documento))

        # Consecutivo
        prefijo = "COT-" if accion == "Cotizar" else "POS-"
        cursor.execute(f"SELECT consecutivo FROM facturas WHERE consecutivo LIKE '{prefijo}%' ORDER BY id DESC LIMIT 1")
        ultimo = cursor.fetchone()
        num = int(ultimo[0].split("-")[1]) + 1 if ultimo else 1000
        consecutivo = f"{prefijo}{num}"

        # Eliminar factura vieja si estábamos editando una guardada
        if id_factura_abierta:
            cursor.execute("DELETE FROM detalles_factura WHERE id_factura = ?", (id_factura_abierta,))
            cursor.execute("DELETE FROM facturas WHERE id = ?", (id_factura_abierta,))

        tipo_doc = "Cotizacion" if accion == "Cotizar" else "Factura"
        estado_fac = "Pagada" if accion == "Cobrar" else "Abierta" if accion == "Guardar" else "Cotizacion"
        
        cursor.execute("""
            INSERT INTO facturas (
                consecutivo, tipo_documento, documento_cliente, placa_moto, marca_moto,
                subtotal, descuento, total, metodo_pago, monto_pagado, saldo_pendiente, estado, id_usuario, fecha
            ) VALUES (?, ?, ?, ?, '', ?, 0, ?, 'Efectivo', ?, ?, ?, ?, datetime('now', 'localtime'))
        """, (consecutivo, tipo_doc, documento, placa_moto, total_factura, total_factura,
              total_factura if accion == "Cobrar" else 0,
              0 if accion == "Cobrar" else total_factura,
              estado_fac, session['user_id']))
        
        id_factura = cursor.lastrowid

        for item in carrito:
            tipo = item.get('tipo', 'repuesto')
            tipo_bd = "repuesto" if tipo == "repuesto_taller" else tipo

            cursor.execute("""
                INSERT INTO detalles_factura (id_factura, tipo_item, id_item, descripcion, cantidad, precio_unitario, subtotal)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (id_factura, tipo_bd, item['id'], item['nombre'], item['cantidad'], item['precio'], item['subtotal']))
            
            # Solo se mueve el inventario si la venta se cobró realmente
            if accion == "Cobrar":
                if tipo == 'repuesto':
                    cursor.execute("UPDATE inventario SET stock = stock - ? WHERE id = ?", (item['cantidad'], item['id']))
                    if id_servicio:
                        cursor.execute("INSERT INTO servicios_repuestos (id_servicio, id_repuesto, cantidad, precio_unitario) VALUES (?, ?, ?, ?)", (id_servicio, item['id'], item['cantidad'], item['precio']))
                elif tipo == 'servicio':
                    cursor.execute("UPDATE servicios SET estado = 'Terminado' WHERE id = ?", (item['id'],))

        if accion == "Cobrar":
            cursor.execute("INSERT INTO entradas_caja (descripcion, monto, fecha) VALUES (?, ?, datetime('now', 'localtime'))", (f"Venta POS ({consecutivo})", total_factura))

        conexion.commit()
        return jsonify({'success': True, 'consecutivo': consecutivo, 'accion': accion})
    except Exception as e:
        return jsonify({'success': False, 'mensaje': str(e)})
    finally:
        if 'conexion' in locals(): conexion.close()

@app.route('/api/facturas_abiertas')
def api_facturas_abiertas():
    conexion = conectar_db()
    cursor = conexion.cursor()
    cursor.execute("""
        SELECT f.id, f.consecutivo, f.fecha, f.total, c.nombre 
        FROM facturas f LEFT JOIN clientes c ON f.documento_cliente = c.documento
        WHERE f.estado = 'Abierta' ORDER BY f.fecha DESC
    """)
    abiertas = [dict(r) for r in cursor.fetchall()]
    conexion.close()
    return jsonify({'success': True, 'abiertas': abiertas})

@app.route('/api/cargar_factura/<int:id_factura>')
def api_cargar_factura(id_factura):
    conexion = conectar_db()
    cursor = conexion.cursor()
    cursor.execute("SELECT f.documento_cliente, f.placa_moto, c.nombre, c.telefono, c.direccion FROM facturas f LEFT JOIN clientes c ON f.documento_cliente = c.documento WHERE f.id = ?", (id_factura,))
    fac = cursor.fetchone()
    cursor.execute("SELECT id_item, tipo_item, descripcion, cantidad, precio_unitario FROM detalles_factura WHERE id_factura = ?", (id_factura,))
    items = cursor.fetchall()
    conexion.close()
    
    if not fac: return jsonify({'success': False})
    
    carrito = []
    for i in items:
        carrito.append({
            'id': i['id_item'], 'tipo': i['tipo_item'], 'nombre': i['descripcion'],
            'cantidad': i['cantidad'], 'precio': i['precio_unitario'], 'subtotal': i['cantidad'] * i['precio_unitario']
        })
        
    return jsonify({
        'success': True,
        'cliente': {'doc': fac['documento_cliente'], 'nom': fac['nombre'], 'tel': fac['telefono'], 'dir': fac['direccion'], 'placa': fac['placa_moto']},
        'carrito': carrito
    })

@app.route('/pos_web/enviar_taller', methods=['POST'])
def pos_web_enviar_taller():
    if 'user_id' not in session: return jsonify({'success': False, 'mensaje': 'Sesión expirada'})
    datos = request.get_json()
    id_servicio = datos.get('id_servicio')
    carrito = datos.get('carrito', [])

    try:
        conexion = conectar_db()
        cursor = conexion.cursor()
        for item in carrito:
            if item.get('tipo', 'repuesto') == 'repuesto':
                cursor.execute("UPDATE inventario SET stock = stock - ? WHERE id = ?", (item['cantidad'], item['id']))
                cursor.execute("INSERT INTO servicios_repuestos (id_servicio, id_repuesto, cantidad, precio_unitario) VALUES (?, ?, ?, ?)", (id_servicio, item['id'], item['cantidad'], item['precio']))
        conexion.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'mensaje': str(e)})
    finally:
        if 'conexion' in locals(): conexion.close()

@app.route('/historial_web')
def historial_web():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    conexion = conectar_db()
    cursor = conexion.cursor()
    cursor.execute("""
        SELECT f.id, f.consecutivo, f.fecha, c.nombre, f.total, f.estado, f.placa_moto 
        FROM facturas f 
        LEFT JOIN clientes c ON f.documento_cliente = c.documento 
        ORDER BY f.id DESC LIMIT 100
    """)
    facturas = [dict(row) for row in cursor.fetchall()]
    conexion.close()
    
    # Asumimos que guardaste el rol en la sesión al hacer login (ej. session['rol'])
    rol_usuario = session.get('rol', 'Vendedor') 
    
    return render_template('historial_web.html', facturas=facturas, rol=rol_usuario)

@app.route('/api/eliminar_factura/<int:id_factura>', methods=['DELETE'])
def api_eliminar_factura(id_factura):
    if session.get('rol') != 'Admin': return jsonify({'success': False, 'mensaje': 'Sin permisos'})
    try:
        conexion = conectar_db()
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM detalles_factura WHERE id_factura = ?", (id_factura,))
        cursor.execute("DELETE FROM facturas WHERE id = ?", (id_factura,))
        conexion.commit()
        conexion.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'mensaje': str(e)})

# ==========================================
# --- MÓDULO PROVEEDORES (WEB) ---
# ==========================================
@app.route('/proveedores_web')
def proveedores_web():
    if 'user_id' not in session: return redirect(url_for('login'))
    if session.get('rol') not in ['Admin', 'Vendedor']: return "Acceso denegado.", 403
    
    conexion = conectar_db()
    cursor = conexion.cursor()
    # Traemos las deudas y calculamos el semáforo directamente en la base de datos
    cursor.execute("""
        SELECT id, proveedor, num_factura, fecha_limite_descuento, fecha_vencimiento_final, total_normal, total_con_descuento, saldo_pendiente, inventario_cargado,
        (date('now', 'localtime') <= fecha_limite_descuento) as aplica_descuento
        FROM compras_facturas
        WHERE estado = 'Pendiente'
        ORDER BY fecha_limite_descuento ASC
    """)
    deudas = [dict(row) for row in cursor.fetchall()]
    conexion.close()
    
    return render_template('proveedores_web.html', deudas=deudas, rol=session.get('rol'))

@app.route('/api/guardar_proveedor', methods=['POST'])
def api_guardar_proveedor():
    if session.get('rol') not in ['Admin', 'Vendedor']: return jsonify({'success': False, 'mensaje': 'Sin permisos'})
    
    datos = request.get_json()
    prov = datos.get('proveedor', '').strip().upper()
    num = datos.get('num_factura', '').strip()
    f_desc = datos.get('fecha_desc', '').strip()
    f_max = datos.get('fecha_max', '').strip()
    t_norm = datos.get('total_normal')
    t_desc = datos.get('total_desc')

    if not all([prov, num, f_desc, f_max, t_norm]):
        return jsonify({'success': False, 'mensaje': 'Faltan datos obligatorios'})

    try:
        t_norm = float(t_norm)
        t_desc = float(t_desc) if t_desc else t_norm
        
        conexion = conectar_db()
        cursor = conexion.cursor()
        cursor.execute("""
            INSERT INTO compras_facturas (proveedor, num_factura, fecha_limite_descuento, fecha_vencimiento_final, total_normal, total_con_descuento, saldo_pendiente)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (prov, num, f_desc, f_max, t_norm, t_desc, t_norm))
        conexion.commit()
        conexion.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'mensaje': str(e)})

# ==========================================
# --- API PARA GASTOS DE CAJA ---
# ==========================================
@app.route('/api/registrar_gasto', methods=['POST'])
def api_registrar_gasto():
    if session.get('rol') != 'Admin': return jsonify({'success': False, 'mensaje': 'Solo el Admin puede registrar gastos o editar caja.'})
    
    datos = request.get_json()
    descripcion = datos.get('descripcion', '').strip()
    monto = datos.get('monto')
    tipo = datos.get('tipo', 'gasto') # Puede ser 'gasto' o 'ajuste_ingreso'

    try:
        monto = float(monto)
        conexion = conectar_db()
        cursor = conexion.cursor()
        
        if tipo == 'gasto':
            cursor.execute("INSERT INTO gastos_diarios (descripcion, monto, fecha) VALUES (?, ?, datetime('now', 'localtime'))", (descripcion, monto))
        else:
            # Si quiere cuadrar la caja sumando plata que faltaba
            cursor.execute("INSERT INTO entradas_caja (descripcion, monto, fecha) VALUES (?, ?, datetime('now', 'localtime'))", (f"Ajuste Manual: {descripcion}", monto))
            
        conexion.commit()
        conexion.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'mensaje': str(e)})




@app.route('/logout')
def logout():
    session.clear() # Borramos la sesión
    return redirect(url_for('login'))

@app.route('/api/descargar_pdf/<int:id_factura>')
def api_descargar_pdf(id_factura):
    if 'user_id' not in session: return redirect(url_for('login'))
    
    try:
        conexion = conectar_db()
        cursor = conexion.cursor()
        
        cursor.execute("""
            SELECT f.total, f.estado, f.fecha, c.documento, c.nombre, c.telefono, c.direccion, f.consecutivo 
            FROM facturas f
            LEFT JOIN clientes c ON f.documento_cliente = c.documento
            WHERE f.id = ?
        """, (id_factura,))
        info_fac = cursor.fetchone()
        
        cursor.execute("SELECT cantidad, descripcion, precio_unitario, subtotal FROM detalles_factura WHERE id_factura = ?", (id_factura,))
        detalles = cursor.fetchall()
        conexion.close()

        if not info_fac:
            return "Factura no encontrada", 404

        total_fac, estado, fecha, doc, nom, tel, dir_c, consecutivo = info_fac

        # --- CONSTRUCCIÓN DEL PDF (Tu código exacto) ---
        pdf = FPDF('P', 'mm', 'Letter')
        pdf.add_page()
        
        carpeta_actual = os.path.dirname(os.path.abspath(__file__))
        ruta_logo = os.path.join(carpeta_actual, "recursos", "logo.png")
        ruta_qr = os.path.join(carpeta_actual, "recursos", "qr.png")

        if os.path.exists(ruta_logo):
            pdf.image(ruta_logo, x=10, y=10, w=40) 
        
        pdf.set_font('Arial', 'B', 22)
        pdf.cell(0, 10, 'FULA MOTOS', ln=1, align='C')
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 5, 'Confianza, experiencia y calidad en cada reparación', ln=1, align='C')
        pdf.cell(0, 5, 'Bogota, Colombia | Tel: 3016016433', ln=1, align='C') 
        pdf.ln(15)

        pdf.set_font('Arial', 'B', 12)
        pdf.cell(100, 8, f'Documento: {consecutivo}', 0, 0)
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 8, f'Fecha: {fecha[:16] if fecha else "S/F"}', 0, 1, 'R')
        
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 6, 'DATOS DEL CLIENTE', ln=1)
        pdf.set_font('Arial', '', 10)
        nombre_cliente = nom if nom else 'Consumidor Final'
        pdf.cell(0, 6, f"Nombre: {nombre_cliente}", ln=1)
        pdf.cell(0, 6, f"Cedula/NIT: {doc if doc else 'N/A'}", ln=1)
        pdf.cell(0, 6, f"Telefono: {tel if tel else 'N/A'}", ln=1)
        pdf.ln(5)

        pdf.set_font('Arial', 'B', 10)
        pdf.set_fill_color(220, 220, 220)
        pdf.cell(20, 8, 'Cant.', 1, 0, 'C', fill=True)
        pdf.cell(110, 8, 'Descripcion', 1, 0, 'C', fill=True)
        pdf.cell(30, 8, 'V. Unit.', 1, 0, 'C', fill=True)
        pdf.cell(30, 8, 'Subtotal', 1, 1, 'C', fill=True)

        pdf.set_font('Arial', '', 10)
        for cant, desc, precio, sub in detalles:
            desc_corta = desc[:55] + ".." if len(desc) > 55 else desc
            pdf.cell(20, 8, str(cant), 1, 0, 'C')
            pdf.cell(110, 8, desc_corta, 1, 0, 'L')
            pdf.cell(30, 8, f"${precio:,.0f}", 1, 0, 'R')
            pdf.cell(30, 8, f"${sub:,.0f}", 1, 1, 'R')

        pdf.ln(2)
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(160, 10, 'TOTAL A PAGAR:', 0, 0, 'R')
        pdf.set_text_color(0, 150, 0) 
        pdf.cell(30, 10, f"${total_fac:,.0f}", 0, 1, 'R')
        pdf.set_text_color(0, 0, 0) 

        pdf.ln(15)
        if os.path.exists(ruta_qr):
            pdf.image(ruta_qr, x=85, y=pdf.get_y(), w=40)
            pdf.ln(45)

        pdf.set_font('Arial', 'I', 10)
        pdf.cell(0, 10, '¡Gracias por confiar en Fula Motos! - Escanea el QR para visitar nuestra web.', ln=1, align='C')

        # --- MAGIA WEB: Guardar en temporal y enviarlo al navegador ---
        temp_dir = tempfile.gettempdir()
        pdf_path = os.path.join(temp_dir, f"{consecutivo}.pdf")
        pdf.output(pdf_path)

        return send_file(pdf_path, as_attachment=False, mimetype='application/pdf')

    except Exception as e:
        return f"Error interno al generar PDF: {str(e)}", 500

if __name__ == '__main__':
    print("Iniciando servidor web de Fula Motos...")
    app.run(host='0.0.0.0', port=5000, debug=True)