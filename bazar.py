# ==============================================================================
# 1. IMPORTS DE LIBRERÍAS
# ==============================================================================
import tkinter
from tkinter import messagebox, ttk
import customtkinter as ctk
import mysql.connector
from datetime import datetime
import locale
from PIL import Image
import os
import bcrypt
import random

# ==============================================================================
# 2. CONFIGURACIÓN GLOBAL Y VARIABLES
# ==============================================================================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

try:
    locale.setlocale(locale.LC_ALL, 'es_CL.UTF-8') 
except locale.Error:
    print("ADVERTENCIA: Locale 'es_CL.UTF-8' no disponible.")
    try: locale.setlocale(locale.LC_ALL, '')
    except locale.Error: print("No se pudo establecer ningún locale.")

current_user = {"usuario": None, "rol": None}
TIEMPO_INACTIVIDAD = 600000 
temporizador_id = None
TASA_IVA = 0.19 # Tasa del 19% para el IVA

# ==============================================================================
# 3. FUNCIONES DE UTILIDAD Y BASE DE DATOS
# ==============================================================================
def formatear_a_clp(valor):
    if valor is None: return "CLP$ 0"
    try:
        valor_entero = int(round(float(valor)))
        return f"CLP$ {locale.format_string('%d', valor_entero, grouping=True)}"
    except (ValueError, TypeError): return "CLP$ 0"

def conectar_bd():
    try:
        return mysql.connector.connect(host="localhost", user="bazar_user", password="123456", database="bazar")
    except mysql.connector.Error as err:
        messagebox.showerror("Error de Conexión", f"No se pudo conectar: {err}"); root.quit(); return None

def generar_codigo_producto(nombre):
    prefijo = ''.join(filter(str.isalnum, nombre[:3].upper()))
    sufijo = ''.join(random.choices('0123456789', k=4))
    return f"{prefijo}-{sufijo}"

def iniciar_bd():
    conn = conectar_bd()
    if not conn: return
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS usuarios (id INT AUTO_INCREMENT PRIMARY KEY, usuario VARCHAR(50) UNIQUE NOT NULL, clave VARCHAR(255) NOT NULL, rol ENUM('vendedor', 'admin') NOT NULL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS productos (id INT AUTO_INCREMENT PRIMARY KEY, codigo VARCHAR(20) UNIQUE, nombre VARCHAR(100) UNIQUE NOT NULL, precio DECIMAL(10,2) NOT NULL, stock INT NOT NULL, estado ENUM('activo', 'inactivo') NOT NULL DEFAULT 'activo')")
    
    # ESTRUCTURA DE BOLETAS MODIFICADA PARA INCLUIR IVA
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS boletas (
            id INT AUTO_INCREMENT PRIMARY KEY,
            vendedor_usuario VARCHAR(50),
            neto DECIMAL(10,2) NOT NULL,
            iva DECIMAL(10,2) NOT NULL,
            total_boleta DECIMAL(10,2) NOT NULL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tipo_documento ENUM('Boleta', 'Factura') NOT NULL DEFAULT 'Boleta',
            cliente_rut VARCHAR(12),
            cliente_nombre VARCHAR(100)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detalle_ventas (
            id INT AUTO_INCREMENT PRIMARY KEY,
            boleta_id INT NOT NULL,
            producto_id INT NOT NULL,
            cantidad INT NOT NULL,
            precio_unitario DECIMAL(10,2) NOT NULL,
            subtotal DECIMAL(10,2) NOT NULL,
            FOREIGN KEY (boleta_id) REFERENCES boletas(id) ON DELETE CASCADE,
            FOREIGN KEY (producto_id) REFERENCES productos(id)
        )
    """)
    
    cursor.execute("SHOW COLUMNS FROM productos LIKE 'estado'");
    if not cursor.fetchone(): cursor.execute("ALTER TABLE productos ADD COLUMN estado ENUM('activo', 'inactivo') NOT NULL DEFAULT 'activo'")
    
    cursor.execute("SHOW COLUMNS FROM productos LIKE 'codigo'");
    if not cursor.fetchone(): cursor.execute("ALTER TABLE productos ADD COLUMN codigo VARCHAR(20) UNIQUE AFTER id")

    cursor.execute("SELECT id, nombre FROM productos WHERE codigo IS NULL OR codigo = ''")
    productos_sin_codigo = cursor.fetchall()
    if productos_sin_codigo:
        print(f"Asignando códigos a {len(productos_sin_codigo)} productos existentes...")
        for prod_id, prod_nombre in productos_sin_codigo:
            codigo_unico_encontrado = False
            while not codigo_unico_encontrado:
                nuevo_codigo = generar_codigo_producto(prod_nombre)
                cursor.execute("SELECT id FROM productos WHERE codigo = %s", (nuevo_codigo,))
                if cursor.fetchone() is None:
                    cursor.execute("UPDATE productos SET codigo = %s WHERE id = %s", (nuevo_codigo, prod_id))
                    codigo_unico_encontrado = True
    
    cursor.execute("SELECT * FROM usuarios WHERE usuario = 'admin'")
    if cursor.fetchone() is None:
        clave_admin_texto = 'admin'; hashed_password = bcrypt.hashpw(clave_admin_texto.encode('utf-8'), bcrypt.gensalt())
        cursor.execute("INSERT INTO usuarios (usuario, clave, rol) VALUES (%s, %s, %s)", ('admin', hashed_password.decode('utf-8'), 'admin'))
        
    conn.commit(); conn.close()


# ==============================================================================
# 4. ARQUITECTURA DE LA INTERFAZ Y SEGURIDAD
# ==============================================================================
def limpiar_frame(frame):
    for widget in frame.winfo_children(): widget.destroy()

def configurar_estilo_treeview():
    style = ttk.Style(); style.theme_use("default")
    style.configure("Treeview", background="#2a2d2e", foreground="white", rowheight=25, fieldbackground="#343638", bordercolor="#343638", borderwidth=0)
    style.map('Treeview', background=[('selected', '#22559b')]); style.configure("Treeview.Heading", background="#565b5e", foreground="white", relief="flat", font=('Roboto', 10, 'bold')); style.map("Treeview.Heading", background=[('active', '#3484F0')])

def cargar_icono(nombre_archivo, size=(24, 24)):
    try:
        script_dir = os.path.dirname(__file__)
        ruta_completa = os.path.join(script_dir, "icons", nombre_archivo)
        return ctk.CTkImage(Image.open(ruta_completa), size=size)
    except Exception as e:
        print(f"ADVERTENCIA: No se pudo cargar el ícono {nombre_archivo}. Error: {e}"); return None

def cerrar_sesion_por_inactividad():
    global temporizador_id
    if current_user["usuario"] is not None:
        messagebox.showwarning("Sesión Expirada", "Tu sesión ha expirado por inactividad.")
        temporizador_id = None
        mostrar_vista("login")

def reiniciar_temporizador(event=None):
    global temporizador_id
    if temporizador_id is not None: root.after_cancel(temporizador_id)
    temporizador_id = root.after(TIEMPO_INACTIVIDAD, cerrar_sesion_por_inactividad)

def iniciar_temporizador_inactividad():
    reiniciar_temporizador()
    root.bind_all("<Key>", reiniciar_temporizador)
    root.bind_all("<Button-1>", reiniciar_temporizador)

def detener_temporizador_inactividad():
    global temporizador_id
    if temporizador_id is not None:
        root.after_cancel(temporizador_id)
        temporizador_id = None
    root.unbind_all("<Key>")
    root.unbind_all("<Button-1>")

def mostrar_vista(nombre_vista, **kwargs):
    limpiar_frame(content_frame)
    vistas = {"login": mostrar_vista_login, "dashboard": mostrar_vista_dashboard, "productos": mostrar_vista_productos, "formulario_producto": mostrar_vista_formulario_producto, "usuarios": mostrar_vista_usuarios, "venta": mostrar_vista_venta, "historial": mostrar_vista_historial, "detalle_boleta": mostrar_vista_detalle_boleta}
    funcion_vista = vistas.get(nombre_vista)
    if funcion_vista: funcion_vista(content_frame, **kwargs)

def _crear_header(parent_frame, titulo, vista_volver):
    header_frame = ctk.CTkFrame(master=parent_frame, fg_color="transparent"); header_frame.pack(fill="x", pady=(0, 20))
    ctk.CTkLabel(master=header_frame, text=titulo, font=("Roboto", 24, "bold")).pack(side="left")
    ctk.CTkButton(master=header_frame, text="← Volver", width=120, command=lambda: mostrar_vista(vista_volver)).pack(side="right")

# ==============================================================================
# 5. CONSTRUCTORES DE VISTAS PRINCIPALES
# ==============================================================================

def mostrar_vista_login(frame, **kwargs):
    detener_temporizador_inactividad(); root.geometry("400x500")
    login_frame = ctk.CTkFrame(master=frame, corner_radius=15, fg_color=("#dbdbdb", "#2b2b2b")); login_frame.place(relx=0.5, rely=0.5, anchor="center")
    ctk.CTkLabel(master=login_frame, text="Sistema Bazar", font=("Roboto", 28, "bold")).pack(pady=(40, 20))
    user_icon = cargar_icono("login-user.png", size=(20, 20)); pass_icon = cargar_icono("login-pass.png", size=(20, 20))
    user_frame = ctk.CTkFrame(master=login_frame, fg_color="transparent"); user_frame.pack(pady=10, padx=30, fill="x")
    if user_icon: ctk.CTkLabel(master=user_frame, text="", image=user_icon).pack(side="left", padx=(0, 10))
    entry_usuario = ctk.CTkEntry(master=user_frame, placeholder_text="Usuario", width=220, height=40); entry_usuario.pack(side="left", fill="x", expand=True)
    pass_frame = ctk.CTkFrame(master=login_frame, fg_color="transparent"); pass_frame.pack(pady=10, padx=30, fill="x")
    if pass_icon: ctk.CTkLabel(master=pass_frame, text="", image=pass_icon).pack(side="left", padx=(0, 10))
    entry_clave = ctk.CTkEntry(master=pass_frame, placeholder_text="Contraseña", show="*", width=220, height=40); entry_clave.pack(side="left", fill="x", expand=True)
    def validar_login(usuario, clave):
        if not usuario or not clave: messagebox.showwarning("Campos Vacíos", "Por favor, ingrese usuario y contraseña."); return
        conn = conectar_bd();
        if not conn: return
        cursor = conn.cursor(); cursor.execute("SELECT clave, rol FROM usuarios WHERE usuario=%s", (usuario,)); resultado = cursor.fetchone(); conn.close()
        if resultado:
            hashed_password_db = resultado[0].encode('utf-8')
            if bcrypt.checkpw(clave.encode('utf-8'), hashed_password_db):
                current_user["usuario"], current_user["rol"] = usuario, resultado[1]
                iniciar_temporizador_inactividad(); root.geometry("800x600"); mostrar_vista("dashboard")
            else: messagebox.showerror("Error de Acceso", "Usuario o contraseña incorrectos.")
        else: messagebox.showerror("Error de Acceso", "Usuario o contraseña incorrectos.")
    btn_ingresar = ctk.CTkButton(master=login_frame, text="Ingresar", width=220, height=40, command=lambda: validar_login(entry_usuario.get(), entry_clave.get())); btn_ingresar.pack(pady=(20, 40))

def mostrar_vista_dashboard(frame, **kwargs):
    root.geometry("800x600"); frame.pack(pady=20, padx=60, fill="both", expand=True)
    header_frame = ctk.CTkFrame(master=frame, fg_color="transparent"); header_frame.pack(fill="x", pady=(0, 20))
    ctk.CTkLabel(master=header_frame, text=f"Bienvenido, {current_user['rol'].capitalize()}", font=("Roboto", 24, "bold")).pack(side="left")
    logout_icon = cargar_icono("salir.png", size=(20, 20))
    ctk.CTkButton(master=header_frame, text="Cerrar Sesión", width=140, image=logout_icon, compound="left", command=lambda: (detener_temporizador_inactividad(), mostrar_vista("login")), fg_color="#D32F2F", hover_color="#B71C1C").pack(side="right")
    
    productos_icon = cargar_icono("products.png", size=(48, 48)); usuarios_icon = cargar_icono("users.png", size=(48, 48)); historial_icon = cargar_icono("history.png", size=(48, 48)); venta_icon = cargar_icono("sales.png", size=(48, 48))
    actions_grid = ctk.CTkFrame(master=frame, fg_color="transparent"); actions_grid.pack(fill="both", expand=True); actions_grid.grid_columnconfigure((0, 1), weight=1); actions_grid.grid_rowconfigure((0, 1), weight=1)
    button_font = ("Roboto", 18, "bold")
    
    if current_user['rol'] == 'admin':
        ctk.CTkButton(master=actions_grid, text="Gestionar Productos", height=120, font=button_font, image=productos_icon, compound="top", command=lambda: mostrar_vista("productos")).grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        ctk.CTkButton(master=actions_grid, text="Gestionar Usuarios", height=120, font=button_font, image=usuarios_icon, compound="top", command=lambda: mostrar_vista("usuarios")).grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        ctk.CTkButton(master=actions_grid, text="Historial de Ventas", height=120, font=button_font, image=historial_icon, compound="top", command=lambda: mostrar_vista("historial")).grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        ctk.CTkButton(master=actions_grid, text="Realizar Venta", height=120, font=button_font, image=venta_icon, compound="top", command=lambda: mostrar_vista("venta")).grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
    else:
        ctk.CTkButton(master=actions_grid, text="Ver Productos", height=120, font=button_font, image=productos_icon, compound="top", command=lambda: mostrar_vista("productos")).grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        ctk.CTkButton(master=actions_grid, text="Realizar Venta", height=120, font=button_font, image=venta_icon, compound="top", command=lambda: mostrar_vista("venta")).grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        ctk.CTkButton(master=actions_grid, text="Mi Historial de Ventas", height=120, font=button_font, image=historial_icon, compound="top", command=lambda: mostrar_vista("historial")).grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")

def mostrar_vista_productos(frame, **kwargs):
    root.geometry("1000x600"); frame.pack(pady=20, padx=20, fill="both", expand=True); _crear_header(frame, "Gestión de Productos", "dashboard")
    producto_seleccionado_actual = {"id": None}
    if current_user['rol'] == 'admin':
        actions_frame = ctk.CTkFrame(master=frame); actions_frame.pack(fill="x", pady=10)
        ctk.CTkButton(master=actions_frame, text="Agregar Nuevo Producto", command=lambda: mostrar_vista("formulario_producto", modo="agregar")).pack(side="left", padx=10)
        btn_editar = ctk.CTkButton(master=actions_frame, text="Editar Producto", state="disabled"); btn_editar.pack(side="left", padx=10)
        btn_archivar = ctk.CTkButton(master=actions_frame, text="Archivar Producto", state="disabled", fg_color="#E67E22", hover_color="#D35400"); btn_archivar.pack(side="left", padx=10)
    tree_frame = ctk.CTkFrame(master=frame); tree_frame.pack(fill="both", expand=True, pady=10)
    cols = ("Código", "Nombre", "Precio Neto", "Stock"); tree = ttk.Treeview(tree_frame, columns=cols, show='headings', style="Treeview")
    for col in cols: tree.heading(col, text=col)
    tree.column("Código", width=100, anchor='center'); tree.column("Nombre", width=300); tree.column("Precio Neto", width=120, anchor='e'); tree.column("Stock", width=100, anchor='center')
    def cargar_productos():
        for i in tree.get_children(): tree.delete(i)
        conn = conectar_bd();
        if not conn: return
        cursor = conn.cursor(); cursor.execute("SELECT id, codigo, nombre, precio, stock FROM productos WHERE estado = 'activo' ORDER BY nombre ASC")
        for producto in cursor.fetchall():
            valores_formateados = (producto[1], producto[2], formatear_a_clp(producto[3]), producto[4]); tree.insert("", "end", values=valores_formateados, iid=producto[0])
        conn.close()
    cargar_productos(); tree.pack(fill='both', expand=True)
    if current_user['rol'] == 'admin':
        def on_select(event):
            if tree.selection():
                producto_seleccionado_actual["id"] = tree.selection()[0]
                btn_editar.configure(state="normal"); btn_archivar.configure(state="normal")
            else:
                producto_seleccionado_actual["id"] = None; btn_editar.configure(state="disabled"); btn_archivar.configure(state="disabled")
        def editar_seleccionado():
            if producto_seleccionado_actual["id"] is not None: mostrar_vista("formulario_producto", modo="editar", producto_id=producto_seleccionado_actual["id"])
        def archivar_seleccionado():
            if producto_seleccionado_actual["id"] is not None:
                conn=conectar_bd(); cursor=conn.cursor(); cursor.execute("SELECT nombre FROM productos WHERE id = %s", (producto_seleccionado_actual["id"],)); nombre_prod = cursor.fetchone()[0]; conn.close()
                if messagebox.askyesno("Archivar Producto", f"¿Seguro que desea archivar '{nombre_prod}'?"):
                    conn = conectar_bd(); cursor = conn.cursor(); cursor.execute("UPDATE productos SET estado = 'inactivo' WHERE id=%s", (producto_seleccionado_actual["id"],)); conn.commit(); conn.close()
                    cargar_productos(); messagebox.showinfo("Éxito", "Producto archivado.")
        tree.bind("<<TreeviewSelect>>", on_select); btn_editar.configure(command=editar_seleccionado); btn_archivar.configure(command=archivar_seleccionado)

def mostrar_vista_formulario_producto(frame, modo, producto_id=None):
    root.geometry("1100x600"); frame.pack(pady=20, padx=20, fill="both", expand=True); frame.grid_columnconfigure(0, weight=1); frame.grid_columnconfigure(1, weight=2); frame.grid_rowconfigure(0, weight=1)
    form_frame = ctk.CTkFrame(master=frame); form_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10)); titulo = "Agregar Nuevo Producto" if modo == "agregar" else "Editar Producto"; ctk.CTkLabel(master=form_frame, text=titulo, font=("Roboto", 20, "bold")).pack(pady=20)
    ctk.CTkLabel(master=form_frame, text="Código:", font=("Roboto", 14)).pack(anchor="w", padx=20); entry_codigo = ctk.CTkEntry(master=form_frame, height=35, state="disabled", placeholder_text="Se genera automáticamente"); entry_codigo.pack(fill="x", padx=20)
    ctk.CTkLabel(master=form_frame, text="Nombre:").pack(anchor="w", padx=20); entry_nombre = ctk.CTkEntry(master=form_frame, height=35); entry_nombre.pack(fill="x", padx=20)
    ctk.CTkLabel(master=form_frame, text="Precio Neto (sin IVA):").pack(anchor="w", padx=20); entry_precio = ctk.CTkEntry(master=form_frame, height=35); entry_precio.pack(fill="x", padx=20)
    ctk.CTkLabel(master=form_frame, text="Stock:").pack(anchor="w", padx=20); entry_stock = ctk.CTkEntry(master=form_frame, height=35); entry_stock.pack(fill="x", padx=20)
    list_frame = ctk.CTkFrame(master=frame); list_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0)); ctk.CTkLabel(master=list_frame, text="Productos Existentes", font=("Roboto", 16, "bold")).pack(pady=10)
    cols = ("Código", "Nombre"); tree = ttk.Treeview(list_frame, columns=cols, show='headings', style="Treeview", height=15); tree.heading("Código", text="Código"); tree.heading("Nombre", text="Nombre"); tree.column("Código", width=80, anchor="center"); tree.pack(fill="both", expand=True, padx=10, pady=10)
    def cargar_lista_productos():
        for i in tree.get_children(): tree.delete(i)
        conn = conectar_bd(); cursor = conn.cursor(); cursor.execute("SELECT codigo, nombre, id FROM productos WHERE estado = 'activo' ORDER BY nombre ASC");
        for p in cursor.fetchall(): tree.insert("", "end", values=(p[0], p[1]), iid=p[2])
        conn.close()
    cargar_lista_productos()
    def autocompletar_formulario_por_doble_clic(event):
        if not tree.selection(): return
        item_id = tree.selection()[0]
        mostrar_vista("formulario_producto", modo="editar", producto_id=item_id)
    tree.bind("<Double-1>", autocompletar_formulario_por_doble_clic)
    def guardar_cambios(modo_guardar, p_id=None):
        nombre, precio_str, stock_str = entry_nombre.get(), entry_precio.get(), entry_stock.get()
        if not all([nombre, precio_str, stock_str]): messagebox.showerror("Error", "Todos los campos son obligatorios."); return
        try: precio, stock = int(precio_str), int(stock_str)
        except ValueError: messagebox.showerror("Error", "Precio y Stock deben ser números enteros."); return
        conn = conectar_bd(); cursor = conn.cursor()
        try:
            if modo_guardar == "agregar":
                codigo = generar_codigo_producto(nombre)
                cursor.execute("INSERT INTO productos (codigo, nombre, precio, stock) VALUES (%s, %s, %s, %s)", (codigo, nombre, precio, stock)); messagebox.showinfo("Éxito", "Producto agregado.")
            elif modo_guardar == "editar":
                cursor.execute("UPDATE productos SET nombre=%s, precio=%s, stock=%s WHERE id=%s", (nombre, precio, stock, p_id)); messagebox.showinfo("Éxito", f"Producto actualizado.")
            conn.commit(); cargar_lista_productos(); entry_nombre.delete(0, "end"); entry_precio.delete(0, "end"); entry_stock.delete(0, "end"); entry_codigo.configure(state="normal"); entry_codigo.delete(0, "end"); entry_codigo.configure(state="disabled", placeholder_text="Se genera automáticamente")
            if modo_guardar == "editar": mostrar_vista("productos")
        except mysql.connector.Error as err: messagebox.showerror("Error de DB", f"No se pudo guardar: {err}")
        finally: conn.close()
    action_form_frame = ctk.CTkFrame(master=form_frame, fg_color="transparent"); action_form_frame.pack(pady=20, fill="x", padx=20)
    btn_guardar = ctk.CTkButton(master=action_form_frame, text="Guardar Cambios", height=40); btn_guardar.pack(side="left", expand=True, padx=(0,5)); ctk.CTkButton(master=action_form_frame, text="Volver", height=40, fg_color="gray", command=lambda: mostrar_vista("productos")).pack(side="left", expand=True, padx=(5,0))
    if modo == "agregar": btn_guardar.configure(command=lambda: guardar_cambios("agregar"))
    elif modo == "editar" and producto_id:
        conn = conectar_bd(); cursor = conn.cursor(); cursor.execute("SELECT codigo, nombre, precio, stock FROM productos WHERE id=%s", (producto_id,)); data = cursor.fetchone(); conn.close()
        if data:
            entry_codigo.configure(state="normal"); entry_codigo.delete(0, "end"); entry_codigo.insert(0, data[0]); entry_codigo.configure(state="disabled")
            entry_nombre.insert(0, data[1]); entry_precio.insert(0, str(int(round(float(data[2]))))); entry_stock.insert(0, str(data[3]))
            btn_guardar.configure(command=lambda: guardar_cambios("editar", producto_id))

def mostrar_vista_usuarios(frame, **kwargs):
    root.geometry("1100x600"); frame.pack(pady=20, padx=20, fill="both", expand=True); _crear_header(frame, "Gestión de Usuarios", "dashboard")
    main_content = ctk.CTkFrame(frame, fg_color="transparent"); main_content.pack(fill="both", expand=True); main_content.grid_columnconfigure(0, weight=2); main_content.grid_columnconfigure(1, weight=1); main_content.grid_rowconfigure(0, weight=1)
    list_frame = ctk.CTkFrame(main_content); list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10)); ctk.CTkLabel(list_frame, text="Usuarios Registrados", font=("Roboto", 16, "bold")).pack(pady=10)
    cols = ("ID", "Usuario", "Rol"); tree = ttk.Treeview(list_frame, columns=cols, show='headings', style="Treeview"); tree.heading("ID", text="ID"); tree.heading("Usuario", text="Usuario"); tree.heading("Rol", text="Rol"); tree.column("ID", width=50); tree.pack(fill="both", expand=True, padx=10, pady=10)
    form_frame = ctk.CTkFrame(main_content); form_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0)); form_title = ctk.CTkLabel(form_frame, text="Agregar/Editar Usuario", font=("Roboto", 16, "bold")); form_title.pack(pady=10)
    id_value = ctk.CTkLabel(form_frame, text=""); ctk.CTkLabel(form_frame, text="Usuario:").pack(anchor="w", padx=20); entry_usuario = ctk.CTkEntry(form_frame, height=35); entry_usuario.pack(fill="x", padx=20); ctk.CTkLabel(form_frame, text="Clave (dejar en blanco para no cambiar):").pack(anchor="w", padx=20); entry_clave = ctk.CTkEntry(form_frame, height=35); entry_clave.pack(fill="x", padx=20); ctk.CTkLabel(form_frame, text="Rol:").pack(anchor="w", padx=20); combo_rol = ctk.CTkComboBox(form_frame, height=35, values=["vendedor", "admin"], state="readonly"); combo_rol.pack(fill="x", padx=20)
    def limpiar_formulario():
        id_value.configure(text=""); entry_usuario.delete(0, "end"); entry_clave.delete(0, "end"); combo_rol.set(""); form_title.configure(text="Agregar Usuario"); btn_guardar.configure(command=lambda: guardar_usuario("agregar")); btn_eliminar.configure(state="disabled")
    def cargar_usuarios():
        for i in tree.get_children(): tree.delete(i)
        conn = conectar_bd(); cursor = conn.cursor(); cursor.execute("SELECT id, usuario, rol FROM usuarios");
        for u in cursor.fetchall(): tree.insert("", "end", values=u)
        conn.close(); limpiar_formulario()
    def seleccionar_usuario(event):
        if not tree.selection(): return
        item = tree.item(tree.selection()[0])['values']; id_value.configure(text=str(item[0])); entry_usuario.delete(0,"end"); entry_usuario.insert(0, item[1]); combo_rol.set(item[2]); form_title.configure(text=f"Editando a: {item[1]}"); btn_guardar.configure(command=lambda: guardar_usuario("editar", item[0]))
        if item[1] != 'admin': btn_eliminar.configure(state="normal")
    def guardar_usuario(modo, user_id=None):
        usuario, clave, rol = entry_usuario.get(), entry_clave.get(), combo_rol.get()
        if not all([usuario, rol]): messagebox.showerror("Error", "Usuario y Rol son obligatorios."); return
        if modo == "agregar" and not clave: messagebox.showerror("Error", "La clave es obligatoria para nuevos usuarios."); return
        hashed_password_str = None
        if clave:
            hashed_password = bcrypt.hashpw(clave.encode('utf-8'), bcrypt.gensalt())
            hashed_password_str = hashed_password.decode('utf-8')
        conn = conectar_bd(); cursor = conn.cursor()
        try:
            if modo == "agregar":
                cursor.execute("INSERT INTO usuarios (usuario, clave, rol) VALUES (%s, %s, %s)", (usuario, hashed_password_str, rol)); messagebox.showinfo("Éxito", "Usuario agregado.")
            elif modo == "editar":
                if hashed_password_str:
                    cursor.execute("UPDATE usuarios SET usuario=%s, clave=%s, rol=%s WHERE id=%s", (usuario, hashed_password_str, rol, user_id))
                else:
                    cursor.execute("UPDATE usuarios SET usuario=%s, rol=%s WHERE id=%s", (usuario, rol, user_id))
                messagebox.showinfo("Éxito", "Usuario actualizado.")
            conn.commit()
        except mysql.connector.Error as err: messagebox.showerror("Error de DB", f"No se pudo guardar: {err}")
        finally: conn.close(); cargar_usuarios()
    def eliminar_usuario():
        user_id, user_name = id_value.cget("text"), entry_usuario.get()
        if user_name == 'admin': messagebox.showerror("Error", "No se puede eliminar al usuario 'admin'."); return
        if messagebox.askyesno("Confirmar", f"¿Seguro que desea eliminar al usuario '{user_name}'?"):
            conn=conectar_bd(); cursor=conn.cursor(); cursor.execute("DELETE FROM usuarios WHERE id=%s", (user_id,)); conn.commit(); conn.close(); cargar_usuarios(); messagebox.showinfo("Éxito", "Usuario eliminado.")
    btn_guardar = ctk.CTkButton(form_frame, text="Guardar", command=lambda: guardar_usuario("agregar")); btn_guardar.pack(pady=10, fill="x", padx=20); btn_eliminar = ctk.CTkButton(form_frame, text="Eliminar Seleccionado", state="disabled", fg_color="#D32F2F", command=eliminar_usuario); btn_eliminar.pack(pady=5, fill="x", padx=20); ctk.CTkButton(form_frame, text="Limpiar / Nuevo", fg_color="gray", command=limpiar_formulario).pack(pady=5, fill="x", padx=20)
    tree.bind("<<TreeviewSelect>>", seleccionar_usuario); cargar_usuarios()

def mostrar_vista_venta(frame, **kwargs):
    root.geometry("1200x700"); frame.pack(pady=20, padx=20, fill="both", expand=True); _crear_header(frame, "Punto de Venta", "dashboard")
    main_content = ctk.CTkFrame(frame, fg_color="transparent"); main_content.pack(fill="both", expand=True); main_content.grid_columnconfigure(0, weight=1); main_content.grid_columnconfigure(1, weight=1); main_content.grid_rowconfigure(0, weight=1)
    carrito = []; conn = conectar_bd(); cursor = conn.cursor(); cursor.execute("SELECT id, nombre, precio, stock FROM productos WHERE stock > 0 AND estado = 'activo'"); productos_disponibles = {f"{p[1]} (Stock: {p[3]})": p for p in cursor.fetchall()}; conn.close()
    
    select_frame = ctk.CTkFrame(main_content); select_frame.grid(row=0, column=0, sticky="nsew", padx=(0,10))
    ctk.CTkLabel(select_frame, text="Añadir Producto", font=("Roboto", 16, "bold")).pack(pady=10)
    ctk.CTkLabel(select_frame, text="Producto:").pack(anchor="w", padx=20); combo_productos = ctk.CTkComboBox(select_frame, height=35, values=list(productos_disponibles.keys()), state="readonly"); combo_productos.pack(fill="x", padx=20)
    ctk.CTkLabel(select_frame, text="Cantidad:").pack(anchor="w", padx=20); entry_cantidad = ctk.CTkEntry(select_frame, height=35); entry_cantidad.pack(fill="x", padx=20)
    cart_add_icon = cargar_icono("cart-add.png", size=(20, 20))
    ctk.CTkButton(select_frame, text="Añadir al Carrito", height=40, image=cart_add_icon, compound="left", command=lambda: anadir_al_carrito()).pack(pady=20, fill="x", padx=20)
    
    ctk.CTkLabel(select_frame, text="Tipo de Documento:", font=("Roboto", 16, "bold")).pack(pady=(20, 5), anchor="w", padx=20)
    tipo_documento_var = tkinter.StringVar(value="Boleta")
    factura_frame = ctk.CTkFrame(select_frame, fg_color="transparent")
    def toggle_factura_fields():
        if tipo_documento_var.get() == "Factura": factura_frame.pack(fill="x", padx=20, pady=5, after=radio_factura)
        else: factura_frame.pack_forget()
    radio_boleta = ctk.CTkRadioButton(select_frame, text="Boleta", variable=tipo_documento_var, value="Boleta", command=toggle_factura_fields); radio_boleta.pack(anchor="w", padx=20, pady=5)
    radio_factura = ctk.CTkRadioButton(select_frame, text="Factura", variable=tipo_documento_var, value="Factura", command=toggle_factura_fields); radio_factura.pack(anchor="w", padx=20, pady=5)
    entry_rut_cliente = ctk.CTkEntry(factura_frame, placeholder_text="RUT Cliente"); entry_rut_cliente.pack(fill="x", pady=5)
    entry_nombre_cliente = ctk.CTkEntry(factura_frame, placeholder_text="Nombre o Razón Social"); entry_nombre_cliente.pack(fill="x", pady=5)

    cart_frame = ctk.CTkFrame(main_content); cart_frame.grid(row=0, column=1, sticky="nsew", padx=(10,0)); ctk.CTkLabel(cart_frame, text="Carrito de Compras", font=("Roboto", 16, "bold")).pack(pady=10); cols = ("Producto", "Cant.", "Precio Neto", "Subtotal"); tree_carrito = ttk.Treeview(cart_frame, columns=cols, show='headings', style="Treeview");
    for col in cols: tree_carrito.heading(col, text=col)
    tree_carrito.column("Cant.", width=60, anchor="center"); tree_carrito.column("Precio Neto", width=120, anchor="e"); tree_carrito.column("Subtotal", width=120, anchor="e"); tree_carrito.pack(fill="both", expand=True, padx=10, pady=10)
    
    # Desglose de totales
    label_neto = ctk.CTkLabel(cart_frame, text="Neto: CLP$ 0", font=("Roboto", 14)); label_neto.pack(anchor="e", padx=10)
    label_iva = ctk.CTkLabel(cart_frame, text="IVA (19%): CLP$ 0", font=("Roboto", 14)); label_iva.pack(anchor="e", padx=10)
    total_label = ctk.CTkLabel(cart_frame, text="TOTAL: CLP$ 0", font=("Roboto", 22, "bold")); total_label.pack(anchor="e", padx=10, pady=(5,10))
    
    def actualizar_vista_carrito():
        for i in tree_carrito.get_children(): tree_carrito.delete(i)
        neto = 0
        for item in carrito:
            valores_formateados = (item['nombre'], item['cantidad'], formatear_a_clp(item['precio']), formatear_a_clp(item['subtotal'])); tree_carrito.insert("", "end", values=valores_formateados); neto += item['subtotal']
        iva = neto * TASA_IVA
        total = neto + iva
        label_neto.configure(text=f"Neto: {formatear_a_clp(neto)}")
        label_iva.configure(text=f"IVA ({int(TASA_IVA*100)}%): {formatear_a_clp(iva)}")
        total_label.configure(text=f"TOTAL: {formatear_a_clp(total)}")
        
    def anadir_al_carrito():
        prod_str, cant_str = combo_productos.get(), entry_cantidad.get()
        if not all([prod_str, cant_str]): return
        try: cantidad = int(cant_str)
        except ValueError: messagebox.showerror("Error", "Cantidad debe ser un número."); return
        if cantidad <= 0: messagebox.showerror("Error", "Cantidad debe ser positiva."); return
        prod_id, nombre, precio, stock = productos_disponibles[prod_str]; stock_en_carrito = sum(item['cantidad'] for item in carrito if item['id'] == prod_id)
        if cantidad > stock - stock_en_carrito: messagebox.showerror("Stock insuficiente", f"No hay suficiente stock."); return
        item_existente = next((item for item in carrito if item['id'] == prod_id), None); precio_float = float(precio)
        if item_existente: item_existente['cantidad'] += cantidad; item_existente['subtotal'] = item_existente['cantidad'] * precio_float
        else: carrito.append({'id': prod_id, 'nombre': nombre, 'precio': precio_float, 'cantidad': cantidad, 'subtotal': cantidad * precio_float})
        actualizar_vista_carrito(); entry_cantidad.delete(0, 'end')
    
    def confirmar_venta():
        if not carrito: messagebox.showwarning("Carrito Vacío", "Debe añadir productos al carrito."); return
        
        tipo_doc = tipo_documento_var.get()
        cliente_rut, cliente_nombre = None, None
        if tipo_doc == "Factura":
            cliente_rut, cliente_nombre = entry_rut_cliente.get(), entry_nombre_cliente.get()
            if not cliente_rut or not cliente_nombre:
                messagebox.showerror("Datos Faltantes", "Para una factura, debe ingresar el RUT y Nombre del cliente."); return

        neto = sum(item['subtotal'] for item in carrito); iva = neto * TASA_IVA; total_boleta = neto + iva
        if not messagebox.askyesno("Confirmar", f"Total a pagar: {formatear_a_clp(total_boleta)}. ¿Continuar?"): return
        
        conn = conectar_bd(); cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO boletas (vendedor_usuario, neto, iva, total_boleta, tipo_documento, cliente_rut, cliente_nombre) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                           (current_user['usuario'], neto, iva, total_boleta, tipo_doc, cliente_rut, cliente_nombre))
            boleta_id = cursor.lastrowid
            for item in carrito:
                cursor.execute("INSERT INTO detalle_ventas (boleta_id, producto_id, cantidad, precio_unitario, subtotal) VALUES (%s, %s, %s, %s, %s)",
                               (boleta_id, item['id'], item['cantidad'], item['precio'], item['subtotal']))
                cursor.execute("UPDATE productos SET stock = stock - %s WHERE id = %s", (item['cantidad'], item['id']))
            conn.commit(); messagebox.showinfo("Éxito", "Venta registrada."); mostrar_vista("dashboard")
        except mysql.connector.Error as err: conn.rollback(); messagebox.showerror("Error de DB", f"No se pudo completar la venta: {err}")
        finally: conn.close()
        
    ctk.CTkButton(cart_frame, text="Confirmar Venta", height=40, fg_color="green", command=confirmar_venta).pack(pady=10, fill="x", padx=10)

def mostrar_vista_historial(frame, **kwargs):
    root.geometry("1200x700"); frame.pack(pady=20, padx=20, fill="both", expand=True)
    titulo_vista = "Historial General de Boletas" if current_user['rol'] == 'admin' else "Mi Historial de Boletas"
    _crear_header(frame, titulo_vista, "dashboard")
    main_content = ctk.CTkFrame(frame, fg_color="transparent"); main_content.pack(fill="both", expand=True); main_content.grid_columnconfigure(0, weight=2); main_content.grid_columnconfigure(1, weight=1); main_content.grid_rowconfigure(0, weight=1)
    
    left_frame = ctk.CTkFrame(main_content, fg_color="transparent"); left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10)); filtros_frame = ctk.CTkFrame(master=left_frame); filtros_frame.pack(fill="x", pady=5)
    ctk.CTkLabel(master=filtros_frame, text="Filtros:", font=("Roboto", 16, "bold")).pack(anchor="w", padx=10, pady=(5,0)); ctk.CTkLabel(master=filtros_frame, text="Buscar por Nombre de Producto:").pack(anchor="w", padx=10)
    entry_producto = ctk.CTkEntry(master=filtros_frame, placeholder_text="Ej: bebida, pan..."); entry_producto.pack(fill="x", padx=10, pady=(0,10))
    def buscar(event=None): aplicar_filtros()
    entry_producto.bind("<Return>", buscar); ctk.CTkButton(master=filtros_frame, text="Buscar", command=buscar).pack(padx=10, pady=(0, 10))
    
    tree_frame = ctk.CTkFrame(left_frame); tree_frame.pack(fill="both", expand=True, pady=5)
    cols = ("ID Boleta", "Fecha", "Tipo", "Total"); tree = ttk.Treeview(tree_frame, columns=cols, show='headings', style="Treeview")
    if current_user['rol'] == 'admin':
        tree.heading("#0", text="Vendedor"); tree.column("#0", width=180)
    else: tree.column("#0", width=0, stretch=tkinter.NO)
    tree.heading("ID Boleta", text="ID Boleta"); tree.heading("Fecha", text="Fecha"); tree.heading("Tipo", text="Tipo"); tree.heading("Total", text="Total Boleta")
    tree.column("ID Boleta", width=100, anchor="center"); tree.column("Fecha", width=150); tree.column("Tipo", width=80, anchor="center"); tree.column("Total", anchor="e")
    
    right_frame = ctk.CTkFrame(main_content); right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0)); ctk.CTkLabel(master=right_frame, text="Acciones", font=("Roboto", 16, "bold")).pack(pady=10)
    ctk.CTkLabel(master=right_frame, text="Seleccione una boleta\n(fila con ID) para ver\nsus detalles completos.", justify="center", wraplength=250).pack(pady=20, padx=10)
    btn_ver_detalle = ctk.CTkButton(master=right_frame, text="Ver Detalle de Boleta", state="disabled"); btn_ver_detalle.pack(pady=10, padx=20, fill="x")
    
    def on_tree_select(event):
        if tree.selection():
            selected_item = tree.selection()[0]
            if tree.parent(selected_item) or current_user['rol'] == 'vendedor': btn_ver_detalle.configure(state="normal")
            else: btn_ver_detalle.configure(state="disabled")
        else: btn_ver_detalle.configure(state="disabled")
        
    def ver_detalle_seleccionado():
        if tree.selection():
            selected_item = tree.selection()[0]
            if tree.parent(selected_item) or current_user['rol'] == 'vendedor':
                boleta_id = tree.item(selected_item, "values")[0]; mostrar_vista("detalle_boleta", boleta_id=boleta_id)

    tree.bind("<<TreeviewSelect>>", on_tree_select); btn_ver_detalle.configure(command=ver_detalle_seleccionado); tree.pack(fill='both', expand=True)

    def aplicar_filtros():
        for i in tree.get_children(): tree.delete(i)
        btn_ver_detalle.configure(state="disabled")
        query = "SELECT DISTINCT b.id, b.fecha, b.vendedor_usuario, b.total_boleta, b.tipo_documento FROM boletas b"
        params = []
        if entry_producto.get():
            query = "SELECT DISTINCT b.id, b.fecha, b.vendedor_usuario, b.total_boleta, b.tipo_documento FROM boletas b JOIN detalle_ventas dv ON b.id = dv.boleta_id JOIN productos p ON dv.producto_id = p.id WHERE p.nombre LIKE %s"
            params.append(f"%{entry_producto.get()}%")
        if current_user['rol'] == 'vendedor':
            if 'WHERE' in query: query += " AND b.vendedor_usuario = %s"
            else: query += " WHERE b.vendedor_usuario = %s"
            params.append(current_user['usuario'])
        query += " ORDER BY b.fecha DESC"
        
        conn = conectar_bd();
        if not conn: return
        cursor = conn.cursor(); cursor.execute(query, tuple(params))
        boletas = cursor.fetchall(); conn.close()
        
        boletas_agrupadas = {}
        for boleta in boletas:
            vendedor = boleta[2] if boleta[2] else "Desconocido"
            if vendedor not in boletas_agrupadas: boletas_agrupadas[vendedor] = []
            boletas_agrupadas[vendedor].append(boleta)
            
        for vendedor, boletas_lista in boletas_agrupadas.items():
            parent_id = ""
            if current_user['rol'] == 'admin':
                parent_id = tree.insert("", "end", text=f" {vendedor} ({len(boletas_lista)} boletas)", open=True)
            for boleta in boletas_lista:
                valores_formateados = (boleta[0], boleta[1].strftime('%d/%m/%Y %H:%M'), boleta[4], formatear_a_clp(boleta[3]))
                tree.insert(parent_id, "end", values=valores_formateados)
    
    aplicar_filtros()

def mostrar_vista_detalle_boleta(frame, boleta_id):
    root.geometry("800x600"); frame.pack(pady=20, padx=20, fill="both", expand=True); _crear_header(frame, f"Detalle de Boleta #{boleta_id}", "historial")
    main_detalle_frame = ctk.CTkScrollableFrame(master=frame, label_text="", fg_color="transparent"); main_detalle_frame.pack(fill="both", expand=True)
    detalle_frame = ctk.CTkFrame(master=main_detalle_frame, corner_radius=10); detalle_frame.pack(fill="x", padx=20, pady=10)
    
    conn = conectar_bd();
    if not conn: return
    cursor = conn.cursor()
    cursor.execute("SELECT fecha, vendedor_usuario, neto, iva, total_boleta, tipo_documento, cliente_rut, cliente_nombre FROM boletas WHERE id = %s", (boleta_id,))
    boleta_data = cursor.fetchone()
    
    if not boleta_data:
        ctk.CTkLabel(detalle_frame, text="No se encontraron datos para esta boleta.", font=("Roboto", 16)).pack(pady=20)
        conn.close(); return
        
    info_grid = ctk.CTkFrame(detalle_frame, fg_color="transparent"); info_grid.pack(pady=20, padx=40, fill="x")
    info_grid.grid_columnconfigure(0, weight=1); info_grid.grid_columnconfigure(1, weight=2)
    def crear_fila_detalle(parent, label_text, value_text, row, font_size=14, is_bold=False, value_color=None):
        label_font = ("Roboto", font_size); value_font = ("Roboto", font_size, "bold") if is_bold else ("Roboto", font_size)
        ctk.CTkLabel(parent, text=label_text, font=label_font, anchor="e").grid(row=row, column=0, sticky="e", padx=(0, 10), pady=4)
        ctk.CTkLabel(parent, text=value_text, font=value_font, anchor="w", text_color=value_color).grid(row=row, column=1, sticky="w", padx=(10, 0), pady=4)

    row_idx = 0
    crear_fila_detalle(info_grid, "Tipo Documento:", boleta_data[5], row_idx); row_idx += 1
    crear_fila_detalle(info_grid, "ID de Boleta:", boleta_id, row_idx); row_idx += 1
    crear_fila_detalle(info_grid, "Fecha y Hora:", boleta_data[0].strftime('%d de %B de %Y, %H:%M:%S'), row_idx); row_idx += 1
    crear_fila_detalle(info_grid, "Vendido por:", boleta_data[1], row_idx); row_idx += 1
    if boleta_data[5] == 'Factura':
        crear_fila_detalle(info_grid, "RUT Cliente:", boleta_data[6], row_idx); row_idx += 1
        crear_fila_detalle(info_grid, "Nombre Cliente:", boleta_data[7], row_idx); row_idx += 1

    ctk.CTkFrame(info_grid, height=2, fg_color="gray50").grid(row=row_idx, columnspan=2, sticky="ew", pady=15); row_idx += 1
    ctk.CTkLabel(info_grid, text="Productos:", font=("Roboto", 14, "bold")).grid(row=row_idx, columnspan=2, pady=(0,10)); row_idx += 1
    
    items_container_frame = ctk.CTkFrame(info_grid, fg_color="transparent"); items_container_frame.grid(row=row_idx, columnspan=2, sticky="ew"); row_idx += 1
    cursor.execute("SELECT p.codigo, p.nombre, dv.cantidad, dv.precio_unitario, dv.subtotal FROM detalle_ventas dv JOIN productos p ON dv.producto_id = p.id WHERE dv.boleta_id = %s", (boleta_id,))
    items_vendidos = cursor.fetchall(); conn.close()
    
    for item in items_vendidos:
        item_frame = ctk.CTkFrame(items_container_frame, fg_color=("gray85", "gray22"), corner_radius=6); item_frame.pack(fill="x", pady=5, padx=5, ipady=5)
        item_grid = ctk.CTkFrame(item_frame, fg_color="transparent"); item_grid.pack(fill="x", padx=10); item_grid.grid_columnconfigure(0, weight=1); item_grid.grid_columnconfigure(1, weight=1)
        crear_fila_detalle(item_grid, "Código:", item[0], 0, font_size=12); crear_fila_detalle(item_grid, "Producto:", item[1], 1, font_size=12); crear_fila_detalle(item_grid, "Cantidad:", item[2], 2, font_size=12); crear_fila_detalle(item_grid, "P. Unitario (Neto):", formatear_a_clp(item[3]), 3, font_size=12); crear_fila_detalle(item_grid, "Subtotal (Neto):", formatear_a_clp(item[4]), 4, font_size=12, is_bold=True, value_color=("#333", "#ccc"))

    ctk.CTkFrame(info_grid, height=2, fg_color="gray50").grid(row=row_idx, columnspan=2, sticky="ew", pady=15); row_idx += 1
    crear_fila_detalle(info_grid, "Neto:", formatear_a_clp(boleta_data[2]), row_idx); row_idx += 1
    crear_fila_detalle(info_grid, f"IVA ({int(TASA_IVA*100)}%):", formatear_a_clp(boleta_data[3]), row_idx); row_idx += 1
    crear_fila_detalle(info_grid, "TOTAL:", formatear_a_clp(boleta_data[4]), row_idx, font_size=18, is_bold=True, value_color="#2ECC71")


# ==============================================================================
# 6. PUNTO DE ENTRADA PRINCIPAL
# ==============================================================================
if __name__ == "__main__":
    root = ctk.CTk()
    root.title("Sistema Bazar Integrado 2025")
    root.geometry("800x600")

    root.update_idletasks(); x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2); y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2); root.geometry(f'+{x}+{y}')

    content_frame = ctk.CTkFrame(master=root, fg_color="transparent")
    content_frame.pack(fill="both", expand=True)

    configurar_estilo_treeview()
    iniciar_bd()
    
    mostrar_vista("login")
    
    root.mainloop()