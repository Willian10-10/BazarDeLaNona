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

def iniciar_bd():
    conn = conectar_bd()
    if not conn: return
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS usuarios (id INT AUTO_INCREMENT PRIMARY KEY, usuario VARCHAR(50) UNIQUE NOT NULL, clave VARCHAR(255) NOT NULL, rol ENUM('vendedor', 'admin') NOT NULL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS productos (id INT AUTO_INCREMENT PRIMARY KEY, nombre VARCHAR(100) UNIQUE NOT NULL, precio DECIMAL(10,2) NOT NULL, stock INT NOT NULL, estado ENUM('activo', 'inactivo') NOT NULL DEFAULT 'activo')")
    cursor.execute("CREATE TABLE IF NOT EXISTS ventas (id INT AUTO_INCREMENT PRIMARY KEY, producto_id INT NOT NULL, cantidad INT NOT NULL, total DECIMAL(10,2) NOT NULL, fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP, vendedor_usuario VARCHAR(50), FOREIGN KEY (producto_id) REFERENCES productos(id))")
    
    cursor.execute("SHOW COLUMNS FROM productos LIKE 'estado'")
    if not cursor.fetchone(): cursor.execute("ALTER TABLE productos ADD COLUMN estado ENUM('activo', 'inactivo') NOT NULL DEFAULT 'activo'")
    
    cursor.execute("SELECT * FROM usuarios WHERE usuario = 'admin'")
    if cursor.fetchone() is None:
        print("Usuario 'admin' no encontrado. Creando usuario por defecto...")
        clave_admin_texto = 'admin'
        hashed_password = bcrypt.hashpw(clave_admin_texto.encode('utf-8'), bcrypt.gensalt())
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
    vistas = {"login": mostrar_vista_login, "dashboard": mostrar_vista_dashboard, "productos": mostrar_vista_productos, "formulario_producto": mostrar_vista_formulario_producto, "usuarios": mostrar_vista_usuarios, "venta": mostrar_vista_venta, "historial": mostrar_vista_historial}
    funcion_vista = vistas.get(nombre_vista)
    if funcion_vista: funcion_vista(content_frame, **kwargs)

def _crear_header(parent_frame, titulo, vista_volver):
    header_frame = ctk.CTkFrame(master=parent_frame, fg_color="transparent"); header_frame.pack(fill="x", pady=(0, 20))
    ctk.CTkLabel(master=header_frame, text=titulo, font=("Roboto", 24, "bold")).pack(side="left")
    ctk.CTkButton(master=header_frame, text="← Volver al Inicio", width=150, command=lambda: mostrar_vista(vista_volver)).pack(side="right")

# ==============================================================================
# 5. CONSTRUCTORES DE VISTAS PRINCIPALES
# ==============================================================================

def mostrar_vista_login(frame, **kwargs):
    detener_temporizador_inactividad()
    root.geometry("400x500")
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
                iniciar_temporizador_inactividad()
                root.geometry("800x600"); mostrar_vista("dashboard")
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

def mostrar_vista_productos(frame, **kwargs):
    # (Esta función esta 100% funcional)
    root.geometry("1000x600"); frame.pack(pady=20, padx=20, fill="both", expand=True); _crear_header(frame, "Gestión de Productos", "dashboard")
    producto_seleccionado_actual = {"id": None, "nombre": None, "data_completa": None}
    if current_user['rol'] == 'admin':
        actions_frame = ctk.CTkFrame(master=frame); actions_frame.pack(fill="x", pady=10)
        ctk.CTkButton(master=actions_frame, text="Agregar Nuevo Producto", command=lambda: mostrar_vista("formulario_producto", modo="agregar")).pack(side="left", padx=10)
        btn_editar = ctk.CTkButton(master=actions_frame, text="Editar Producto", state="disabled"); btn_editar.pack(side="left", padx=10)
        btn_archivar = ctk.CTkButton(master=actions_frame, text="Archivar Producto", state="disabled", fg_color="#E67E22", hover_color="#D35400"); btn_archivar.pack(side="left", padx=10)
    tree_frame = ctk.CTkFrame(master=frame); tree_frame.pack(fill="both", expand=True, pady=10)
    cols = ("ID", "Nombre", "Precio", "Stock"); tree = ttk.Treeview(tree_frame, columns=cols, show='headings', style="Treeview")
    for col in cols: tree.heading(col, text=col)
    tree.column("ID", width=50, anchor='center'); tree.column("Nombre", width=300); tree.column("Precio", width=120, anchor='e'); tree.column("Stock", width=100, anchor='center')
    def cargar_productos():
        for i in tree.get_children(): tree.delete(i)
        conn = conectar_bd();
        if not conn: return
        cursor = conn.cursor(); cursor.execute("SELECT id, nombre, precio, stock FROM productos WHERE estado = 'activo' ORDER BY nombre ASC")
        for producto in cursor.fetchall():
            valores_formateados = (producto[0], producto[1], formatear_a_clp(producto[2]), producto[3]); tree.insert("", "end", values=valores_formateados, iid=producto[0])
        conn.close()
    cargar_productos(); tree.pack(fill='both', expand=True)
    if current_user['rol'] == 'admin':
        def on_select(event):
            if tree.selection():
                item_id = tree.selection()[0]; conn = conectar_bd(); cursor=conn.cursor(); cursor.execute("SELECT * FROM productos WHERE id=%s", (item_id,)); producto_data = cursor.fetchone(); conn.close()
                if producto_data:
                    producto_seleccionado_actual["id"] = producto_data[0]; producto_seleccionado_actual["nombre"] = producto_data[1]; producto_seleccionado_actual["data_completa"] = producto_data
                    btn_editar.configure(state="normal"); btn_archivar.configure(state="normal")
            else:
                producto_seleccionado_actual["id"] = None; producto_seleccionado_actual["nombre"] = None; producto_seleccionado_actual["data_completa"] = None
                btn_editar.configure(state="disabled"); btn_archivar.configure(state="disabled")
        def editar_seleccionado():
            if producto_seleccionado_actual["id"] is not None: mostrar_vista("formulario_producto", modo="editar", data=producto_seleccionado_actual["data_completa"])
        def archivar_seleccionado():
            prod_id, prod_nombre = producto_seleccionado_actual["id"], producto_seleccionado_actual["nombre"]
            if prod_id is not None:
                if messagebox.askyesno("Archivar Producto", f"¿Seguro que desea archivar '{prod_nombre}'?"):
                    conn = conectar_bd();
                    if not conn: return
                    cursor = conn.cursor(); cursor.execute("UPDATE productos SET estado = 'inactivo' WHERE id=%s", (prod_id,)); conn.commit(); conn.close()
                    cargar_productos(); messagebox.showinfo("Éxito", "Producto archivado.")
        tree.bind("<<TreeviewSelect>>", on_select); btn_editar.configure(command=editar_seleccionado); btn_archivar.configure(command=archivar_seleccionado)

def mostrar_vista_formulario_producto(frame, modo, data=None):
    # (Esta función esta completa)
    root.geometry("1100x600"); frame.pack(pady=20, padx=20, fill="both", expand=True); frame.grid_columnconfigure(0, weight=1); frame.grid_columnconfigure(1, weight=2); frame.grid_rowconfigure(0, weight=1)
    form_frame = ctk.CTkFrame(master=frame); form_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10)); titulo = "Agregar Nuevo Producto" if modo == "agregar" else "Editar Producto"; ctk.CTkLabel(master=form_frame, text=titulo, font=("Roboto", 20, "bold")).pack(pady=20)
    id_label = ctk.CTkLabel(master=form_frame, text="ID del Producto:"); id_value = ctk.CTkLabel(master=form_frame, text="", font=("Roboto", 14, "bold"))
    ctk.CTkLabel(master=form_frame, text="Nombre:").pack(anchor="w", padx=20); entry_nombre = ctk.CTkEntry(master=form_frame, height=35); entry_nombre.pack(fill="x", padx=20)
    ctk.CTkLabel(master=form_frame, text="Precio (CLP):").pack(anchor="w", padx=20); entry_precio = ctk.CTkEntry(master=form_frame, height=35); entry_precio.pack(fill="x", padx=20)
    ctk.CTkLabel(master=form_frame, text="Stock:").pack(anchor="w", padx=20); entry_stock = ctk.CTkEntry(master=form_frame, height=35); entry_stock.pack(fill="x", padx=20)
    list_frame = ctk.CTkFrame(master=frame); list_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0)); ctk.CTkLabel(master=list_frame, text="Productos Existentes", font=("Roboto", 16, "bold")).pack(pady=10)
    cols = ("ID", "Nombre"); tree = ttk.Treeview(list_frame, columns=cols, show='headings', style="Treeview", height=15); tree.heading("ID", text="ID"); tree.heading("Nombre", text="Nombre"); tree.column("ID", width=60, anchor="center"); tree.pack(fill="both", expand=True, padx=10, pady=10)
    def cargar_lista_productos():
        for i in tree.get_children(): tree.delete(i)
        conn = conectar_bd(); cursor = conn.cursor(); cursor.execute("SELECT id, nombre FROM productos WHERE estado = 'activo' ORDER BY nombre ASC");
        for p in cursor.fetchall(): tree.insert("", "end", values=p)
        conn.close()
    def autocompletar_formulario(event):
        if not tree.selection(): return
        producto_id = tree.item(tree.selection()[0])['values'][0]; conn = conectar_bd(); cursor = conn.cursor(); cursor.execute("SELECT id, nombre, precio, stock FROM productos WHERE id=%s", (producto_id,)); producto_completo = cursor.fetchone(); conn.close()
        if producto_completo:
            id_value.configure(text=str(producto_completo[0])); entry_nombre.delete(0, "end"); entry_nombre.insert(0, producto_completo[1]); entry_precio.delete(0, "end"); entry_precio.insert(0, str(int(round(float(producto_completo[2]))))); entry_stock.delete(0, "end"); entry_stock.insert(0, str(producto_completo[3])); btn_guardar.configure(command=lambda: guardar_cambios("editar", producto_completo[0]))
    tree.bind("<<TreeviewSelect>>", autocompletar_formulario); cargar_lista_productos()
    def guardar_cambios(modo_guardar, producto_id=None):
        nombre, precio_str, stock_str = entry_nombre.get(), entry_precio.get(), entry_stock.get()
        if not all([nombre, precio_str, stock_str]): messagebox.showerror("Error", "Todos los campos son obligatorios."); return
        try: precio, stock = int(precio_str), int(stock_str)
        except ValueError: messagebox.showerror("Error", "Precio y Stock deben ser números enteros."); return
        conn = conectar_bd(); cursor = conn.cursor()
        try:
            if modo_guardar == "agregar": cursor.execute("INSERT INTO productos (nombre, precio, stock) VALUES (%s, %s, %s)", (nombre, precio, stock)); messagebox.showinfo("Éxito", "Producto agregado.")
            elif modo_guardar == "editar": cursor.execute("UPDATE productos SET nombre=%s, precio=%s, stock=%s WHERE id=%s", (nombre, precio, stock, producto_id)); messagebox.showinfo("Éxito", f"Producto ID {producto_id} actualizado.")
            conn.commit(); cargar_lista_productos(); id_value.configure(text=""); entry_nombre.delete(0, "end"); entry_precio.delete(0, "end"); entry_stock.delete(0, "end")
        except mysql.connector.Error as err: messagebox.showerror("Error de DB", f"No se pudo guardar: {err}")
        finally: conn.close()
    action_form_frame = ctk.CTkFrame(master=form_frame, fg_color="transparent"); action_form_frame.pack(pady=20, fill="x", padx=20)
    btn_guardar = ctk.CTkButton(master=action_form_frame, text="Guardar Cambios", height=40); btn_guardar.pack(side="left", expand=True, padx=(0,5)); ctk.CTkButton(master=action_form_frame, text="Volver", height=40, fg_color="gray", command=lambda: mostrar_vista("productos")).pack(side="left", expand=True, padx=(5,0))
    if modo == "agregar": btn_guardar.configure(command=lambda: guardar_cambios("agregar"))
    elif modo == "editar" and data:
        id_value.configure(text=str(data[0])); id_label.pack(anchor="w", padx=20); id_value.pack(anchor="w", padx=20); entry_nombre.insert(0, data[1]); entry_precio.insert(0, str(int(round(float(data[2]))))); entry_stock.insert(0, str(data[3])); btn_guardar.configure(command=lambda: guardar_cambios("editar", data[0]))

def mostrar_vista_usuarios(frame, **kwargs):
    # (Esta función funciona)
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
    # (Esta función funciona)
    root.geometry("1200x700"); frame.pack(pady=20, padx=20, fill="both", expand=True); _crear_header(frame, "Punto de Venta", "dashboard")
    main_content = ctk.CTkFrame(frame, fg_color="transparent"); main_content.pack(fill="both", expand=True); main_content.grid_columnconfigure(0, weight=1); main_content.grid_columnconfigure(1, weight=1); main_content.grid_rowconfigure(0, weight=1)
    carrito = []; conn = conectar_bd(); cursor = conn.cursor(); cursor.execute("SELECT id, nombre, precio, stock FROM productos WHERE stock > 0 AND estado = 'activo'"); productos_disponibles = {f"{p[1]} (Stock: {p[3]})": p for p in cursor.fetchall()}; conn.close()
    select_frame = ctk.CTkFrame(main_content); select_frame.grid(row=0, column=0, sticky="nsew", padx=(0,10)); ctk.CTkLabel(select_frame, text="Añadir Producto", font=("Roboto", 16, "bold")).pack(pady=10); ctk.CTkLabel(select_frame, text="Producto:").pack(anchor="w", padx=20); combo_productos = ctk.CTkComboBox(select_frame, height=35, values=list(productos_disponibles.keys()), state="readonly"); combo_productos.pack(fill="x", padx=20); ctk.CTkLabel(select_frame, text="Cantidad:").pack(anchor="w", padx=20); entry_cantidad = ctk.CTkEntry(select_frame, height=35); entry_cantidad.pack(fill="x", padx=20)
    cart_frame = ctk.CTkFrame(main_content); cart_frame.grid(row=0, column=1, sticky="nsew", padx=(10,0)); ctk.CTkLabel(cart_frame, text="Carrito de Compras", font=("Roboto", 16, "bold")).pack(pady=10); cols = ("Producto", "Cant.", "Precio Unit.", "Subtotal"); tree_carrito = ttk.Treeview(cart_frame, columns=cols, show='headings', style="Treeview");
    for col in cols: tree_carrito.heading(col, text=col)
    tree_carrito.column("Cant.", width=60, anchor="center"); tree_carrito.column("Precio Unit.", width=120, anchor="e"); tree_carrito.column("Subtotal", width=120, anchor="e"); tree_carrito.pack(fill="both", expand=True, padx=10, pady=10)
    total_label = ctk.CTkLabel(cart_frame, text=formatear_a_clp(0), font=("Roboto", 22, "bold")); total_label.pack(pady=10)
    def actualizar_vista_carrito():
        for i in tree_carrito.get_children(): tree_carrito.delete(i)
        total = 0
        for item in carrito:
            valores_formateados = (item['nombre'], item['cantidad'], formatear_a_clp(item['precio']), formatear_a_clp(item['subtotal'])); tree_carrito.insert("", "end", values=valores_formateados); total += item['subtotal']
        total_label.configure(text=formatear_a_clp(total))
    def anadir_al_carrito():
        prod_str, cant_str = combo_productos.get(), entry_cantidad.get()
        if not all([prod_str, cant_str]): return
        try: cantidad = int(cant_str)
        except ValueError: messagebox.showerror("Error", "Cantidad debe ser un número."); return
        prod_id, nombre, precio, stock = productos_disponibles[prod_str]; stock_en_carrito = sum(item['cantidad'] for item in carrito if item['id'] == prod_id)
        if cantidad > stock - stock_en_carrito: messagebox.showerror("Stock insuficiente", f"No hay suficiente stock."); return
        item_existente = next((item for item in carrito if item['id'] == prod_id), None); precio_float = float(precio)
        if item_existente: item_existente['cantidad'] += cantidad; item_existente['subtotal'] = item_existente['cantidad'] * precio_float
        else: carrito.append({'id': prod_id, 'nombre': nombre, 'precio': precio_float, 'cantidad': cantidad, 'subtotal': cantidad * precio_float})
        actualizar_vista_carrito(); entry_cantidad.delete(0, 'end')
    def confirmar_venta():
        if not carrito: return
        total_venta_str = total_label.cget('text')
        if not messagebox.askyesno("Confirmar", f"Total: {total_venta_str}. ¿Continuar?"): return
        conn = conectar_bd(); cursor = conn.cursor()
        try:
            for item in carrito:
                cursor.execute("INSERT INTO ventas (producto_id, cantidad, total, vendedor_usuario) VALUES (%s, %s, %s, %s)", (item['id'], item['cantidad'], item['subtotal'], current_user['usuario']))
                cursor.execute("UPDATE productos SET stock = stock - %s WHERE id = %s", (item['cantidad'], item['id']))
            conn.commit(); messagebox.showinfo("Éxito", "Venta registrada."); mostrar_vista("dashboard")
        except mysql.connector.Error as err: conn.rollback(); messagebox.showerror("Error de DB", f"No se pudo completar la venta: {err}")
        finally: conn.close()
    cart_add_icon = cargar_icono("cart-add.png", size=(20, 20))
    ctk.CTkButton(select_frame, text="Añadir al Carrito", height=40, image=cart_add_icon, compound="left", command=anadir_al_carrito).pack(pady=20, fill="x", padx=20)
    ctk.CTkButton(cart_frame, text="Confirmar Venta", height=40, fg_color="green", command=confirmar_venta).pack(pady=10, fill="x", padx=10)

def mostrar_vista_historial(frame, **kwargs):
    # (Esta función funciona)
    root.geometry("1200x700"); frame.pack(pady=20, padx=20, fill="both", expand=True); _crear_header(frame, "Historial y Análisis de Ventas", "dashboard")
    filtros_frame = ctk.CTkFrame(master=frame); filtros_frame.pack(fill="x", pady=10); controles_superiores = ctk.CTkFrame(master=filtros_frame, fg_color="transparent"); controles_superiores.pack(fill="x", padx=10, pady=5); controles_superiores.grid_columnconfigure((0, 1, 2, 3), weight=1)
    ctk.CTkLabel(master=controles_superiores, text="Fecha Inicio:").grid(row=0, column=0, sticky="w"); entry_fecha_inicio = ctk.CTkEntry(master=controles_superiores, placeholder_text="YYYY-MM-DD"); entry_fecha_inicio.grid(row=1, column=0, sticky="ew", padx=(0, 5))
    ctk.CTkLabel(master=controles_superiores, text="Fecha Fin:").grid(row=0, column=1, sticky="w"); entry_fecha_fin = ctk.CTkEntry(master=controles_superiores, placeholder_text="YYYY-MM-DD"); entry_fecha_fin.grid(row=1, column=1, sticky="ew", padx=(0, 5))
    date_picker_frame = ctk.CTkFrame(master=filtros_frame, fg_color="transparent")
    def toggle_date_picker(entry_widget, picker_frame):
        if picker_frame.winfo_viewable(): picker_frame.pack_forget()
        else:
            for widget in picker_frame.winfo_children(): widget.destroy()
            crear_date_picker(entry_widget, picker_frame); picker_frame.pack(fill="x", padx=10, pady=10)
    def crear_date_picker(entry_widget, picker_frame):
        current_year = datetime.now().year; years = [str(y) for y in range(current_year - 5, current_year + 2)]; months = [f"{m:02d}" for m in range(1, 13)]; days = [f"{d:02d}" for d in range(1, 32)]
        picker_content = ctk.CTkFrame(master=picker_frame); picker_content.pack()
        ctk.CTkLabel(picker_content, text="Año:").grid(row=0, column=0, padx=5); combo_year = ctk.CTkComboBox(picker_content, values=years); combo_year.set(str(current_year)); combo_year.grid(row=1, column=0, padx=5)
        ctk.CTkLabel(picker_content, text="Mes:").grid(row=0, column=1, padx=5); combo_month = ctk.CTkComboBox(picker_content, values=months); combo_month.set(f"{datetime.now().month:02d}"); combo_month.grid(row=1, column=1, padx=5)
        ctk.CTkLabel(picker_content, text="Día:").grid(row=0, column=2, padx=5); combo_day = ctk.CTkComboBox(picker_content, values=days); combo_day.set(f"{datetime.now().day:02d}"); combo_day.grid(row=1, column=2, padx=5)
        def on_select():
            fecha_seleccionada = f"{combo_year.get()}-{combo_month.get()}-{combo_day.get()}"; entry_widget.delete(0, "end"); entry_widget.insert(0, fecha_seleccionada); picker_frame.pack_forget()
        ctk.CTkButton(picker_content, text="Confirmar", command=on_select).grid(row=1, column=3, padx=10)
    ctk.CTkButton(master=controles_superiores, text="🗓️", width=30, command=lambda: toggle_date_picker(entry_fecha_inicio, date_picker_frame)).grid(row=1, column=0, sticky="e", padx=(0,5))
    ctk.CTkButton(master=controles_superiores, text="🗓️", width=30, command=lambda: toggle_date_picker(entry_fecha_fin, date_picker_frame)).grid(row=1, column=1, sticky="e", padx=(0,5))
    conn = conectar_bd(); 
    if not conn: return
    cursor = conn.cursor(); cursor.execute("SELECT DISTINCT vendedor_usuario FROM ventas ORDER BY vendedor_usuario")
    vendedores = ["Todos"] + [row[0] for row in cursor.fetchall() if row[0] is not None]; conn.close()
    ctk.CTkLabel(master=controles_superiores, text="Vendedor:").grid(row=0, column=2, sticky="w"); combo_vendedor = ctk.CTkComboBox(master=controles_superiores, values=vendedores); combo_vendedor.set("Todos"); combo_vendedor.grid(row=1, column=2, sticky="ew", padx=(0,5))
    ctk.CTkLabel(master=controles_superiores, text="Nombre del Producto:").grid(row=0, column=3, sticky="w"); entry_producto = ctk.CTkEntry(master=controles_superiores, placeholder_text="Buscar por nombre..."); entry_producto.grid(row=1, column=3, sticky="ew")
    btn_filtrar = ctk.CTkButton(master=filtros_frame, text="Buscar", command=lambda: aplicar_filtros(), height=40); btn_filtrar.pack(pady=10, padx=10, fill="x")
    tree_frame = ctk.CTkFrame(frame); tree_frame.pack(fill="both", expand=True, pady=5)
    cols = ("ID Venta", "Fecha", "Vendedor", "Producto", "Cant.", "Total Venta"); tree = ttk.Treeview(tree_frame, columns=cols, show='headings', style="Treeview")
    for col in cols: tree.heading(col, text=col)
    tree.column("ID Venta", width=80, anchor="center"); tree.column("Fecha", width=140); tree.column("Vendedor", width=120); tree.column("Producto", width=250); tree.column("Cant.", width=60, anchor="center"); tree.column("Total Venta", anchor="e", width=120); tree.pack(fill='both', expand=True)
    resumen_frame = ctk.CTkFrame(master=frame, fg_color=("gray85", "gray17")); resumen_frame.pack(fill="x", pady=10, ipady=10)
    label_ventas_totales = ctk.CTkLabel(master=resumen_frame, text="Ventas Encontradas: 0", font=("Roboto", 14, "bold")); label_ventas_totales.pack(side="left", padx=20)
    label_ganancia_total = ctk.CTkLabel(master=resumen_frame, text="Ganancia Total: CLP$ 0", font=("Roboto", 14, "bold")); label_ganancia_total.pack(side="right", padx=20)
    def aplicar_filtros():
        date_picker_frame.pack_forget()
        for i in tree.get_children(): tree.delete(i)
        query = "SELECT v.id, v.fecha, v.vendedor_usuario, p.nombre, v.cantidad, v.total FROM ventas v JOIN productos p ON v.producto_id = p.id WHERE 1=1"
        params = []
        if entry_fecha_inicio.get(): query += " AND v.fecha >= %s"; params.append(entry_fecha_inicio.get() + " 00:00:00")
        if entry_fecha_fin.get(): query += " AND v.fecha <= %s"; params.append(entry_fecha_fin.get() + " 23:59:59")
        if combo_vendedor.get() != "Todos": query += " AND v.vendedor_usuario = %s"; params.append(combo_vendedor.get())
        if entry_producto.get(): query += " AND p.nombre LIKE %s"; params.append(f"%{entry_producto.get()}%")
        query += " ORDER BY v.fecha DESC"
        conn = conectar_bd();
        if not conn: return
        cursor = conn.cursor(); cursor.execute(query, tuple(params))
        total_ganancia = 0; num_ventas = 0
        for venta in cursor.fetchall():
            num_ventas += 1; ganancia_venta = float(venta[5]); total_ganancia += ganancia_venta
            valores_formateados = (venta[0], venta[1].strftime('%Y-%m-%d %H:%M'), venta[2] if venta[2] else "N/A", venta[3], venta[4], formatear_a_clp(ganancia_venta))
            tree.insert("", "end", values=valores_formateados)
        conn.close()
        label_ventas_totales.configure(text=f"Ventas Encontradas: {num_ventas}")
        label_ganancia_total.configure(text=f"Ganancia Total: {formatear_a_clp(total_ganancia)}")
    aplicar_filtros()


# ==============================================================================
# 6. PUNTO DE ENTRADA PRINCIPAL
# ==============================================================================
if __name__ == "__main__":
    root = ctk.CTk()
    root.title("Sistema Bazar Integrado 2024")
    root.geometry("800x600")

    root.update_idletasks(); x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2); y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2); root.geometry(f'+{x}+{y}')

    content_frame = ctk.CTkFrame(master=root, fg_color="transparent")
    content_frame.pack(fill="both", expand=True)

    configurar_estilo_treeview()
    iniciar_bd()
    
    mostrar_vista("login")
    
    root.mainloop()