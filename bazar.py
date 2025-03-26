import tkinter as tk
from tkinter import messagebox
from tkinter.ttk import Combobox
import mysql.connector
from datetime import datetime

# Configuración de la base de datos
def conectar_bd():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="123456",
        database="bazar"
    )

# Función para inicializar la base de datos
def iniciar_bd():
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute(""" 
        CREATE TABLE IF NOT EXISTS usuarios (
            id INT AUTO_INCREMENT PRIMARY KEY,
            usuario VARCHAR(50) UNIQUE NOT NULL,
            clave VARCHAR(255) NOT NULL,
            rol ENUM('vendedor', 'admin') NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nombre VARCHAR(100) NOT NULL,
            precio DECIMAL(10,2) NOT NULL,
            stock INT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id INT AUTO_INCREMENT PRIMARY KEY,
            producto_id INT NOT NULL,
            cantidad INT NOT NULL,
            total DECIMAL(10,2) NOT NULL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (producto_id) REFERENCES productos(id)
        )
    """)
    conn.commit()
    conn.close()

# Función para validar login
def validar_login():
    usuario = entry_usuario.get()
    clave = entry_clave.get()

    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("SELECT clave, rol FROM usuarios WHERE usuario=%s", (usuario,))
    resultado = cursor.fetchone()
    conn.close()

    if resultado:
        if clave == resultado[0]:  # Compara la contraseña de manera directa
            if resultado[1] == "admin":
                abrir_admin()
            else:
                abrir_vendedor()
        else:
            messagebox.showerror("Error", "Usuario o contraseña incorrectos")
    else:
        messagebox.showerror("Error", "Usuario o contraseña incorrectos")

def crear_usuario(usuario, clave, rol):
    conn = conectar_bd()
    cursor = conn.cursor()

    # Insertar el usuario en la base de datos sin encriptar la contraseña
    cursor.execute("INSERT INTO usuarios (usuario, clave, rol) VALUES (%s, %s, %s)", 
                   (usuario, clave, rol))
    conn.commit()
    conn.close()

# Función para abrir la ventana de admin
def abrir_admin():
    admin_window = tk.Toplevel(root)
    admin_window.title("Panel de Administrador")
    
    tk.Label(admin_window, text="Bienvenido, Administrador").pack()
    
    # Mostrar lista de productos
    tk.Label(admin_window, text="Lista de productos:").pack()
    mostrar_productos(admin_window)
    
    # Botones para agregar, modificar y eliminar productos
    tk.Button(admin_window, text="Agregar Producto", command=lambda: agregar_producto(admin_window)).pack()
    tk.Button(admin_window, text="Modificar Producto", command=lambda: modificar_producto(admin_window)).pack()
    tk.Button(admin_window, text="Eliminar Producto", command=lambda: eliminar_producto(admin_window)).pack()
    
    # Ver historial de ventas
    tk.Button(admin_window, text="Ver Historial de Ventas", command=lambda: ver_historial_ventas(admin_window)).pack()

    # Botón para agregar un usuario
    tk.Button(admin_window, text="Crear Usuario", command=lambda: crear_usuario_window(admin_window)).pack()

# Función para abrir la ventana de vendedor
def abrir_vendedor():
    vendedor_window = tk.Toplevel(root)
    vendedor_window.title("Panel de Vendedor")
    
    tk.Label(vendedor_window, text="Bienvenido, Vendedor").pack()
    
    # Mostrar lista de productos
    tk.Label(vendedor_window, text="Lista de productos:").pack()
    mostrar_productos(vendedor_window)
    
    # Botón para realizar una venta
    tk.Button(vendedor_window, text="Realizar Venta", command=lambda: realizar_venta(vendedor_window)).pack()

# Función para crear la ventana de nuevo usuario
def crear_usuario_window(admin_window):
    def guardar_usuario():
        usuario = entry_usuario_nuevo.get()
        clave = entry_clave_nuevo.get()
        rol = combo_rol.get()

        # Verificar si el usuario ya existe
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE usuario=%s", (usuario,))
        if cursor.fetchone():
            messagebox.showerror("Error", "El usuario ya existe")
            conn.close()
            return

        crear_usuario(usuario, clave, rol)
        messagebox.showinfo("Éxito", "Usuario creado exitosamente")
        nueva_ventana.destroy()

    # Ventana para crear usuario
    nueva_ventana = tk.Toplevel(admin_window)
    nueva_ventana.title("Crear Usuario")

    tk.Label(nueva_ventana, text="Nombre de Usuario:").pack()
    entry_usuario_nuevo = tk.Entry(nueva_ventana)
    entry_usuario_nuevo.pack()

    tk.Label(nueva_ventana, text="Contraseña:").pack()
    entry_clave_nuevo = tk.Entry(nueva_ventana, show="*")
    entry_clave_nuevo.pack()

    tk.Label(nueva_ventana, text="Rol:").pack()
    combo_rol = Combobox(nueva_ventana, values=["vendedor", "admin"])
    combo_rol.pack()

    tk.Button(nueva_ventana, text="Crear Usuario", command=guardar_usuario).pack()

# Función para mostrar productos
def mostrar_productos(window):
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, precio, stock FROM productos")
    productos = cursor.fetchall()
    conn.close()

    for producto in productos:
        tk.Label(window, text=f"ID: {producto[0]}, Nombre: {producto[1]}, Precio: ${producto[2]}, Stock: {producto[3]}").pack()

# Función para agregar productos
def agregar_producto(window):
    def guardar_producto():
        nombre = entry_nombre.get()
        precio = entry_precio.get()
        stock = entry_stock.get()

        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO productos (nombre, precio, stock) VALUES (%s, %s, %s)", (nombre, precio, stock))
        conn.commit()
        conn.close()
        
        # Verificar si el stock es bajo y mostrar alerta
        if int(stock) < 5:
            messagebox.showwarning("Advertencia", f"Stock bajo para el producto {nombre}")
        
        messagebox.showinfo("Éxito", "Producto agregado con éxito")
        window.destroy()
        abrir_admin()

    # Ventana para agregar producto
    add_window = tk.Toplevel(window)
    add_window.title("Agregar Producto")
    
    tk.Label(add_window, text="Nombre del Producto:").pack()
    entry_nombre = tk.Entry(add_window)
    entry_nombre.pack()

    tk.Label(add_window, text="Precio del Producto:").pack()
    entry_precio = tk.Entry(add_window)
    entry_precio.pack()

    tk.Label(add_window, text="Stock del Producto:").pack()
    entry_stock = tk.Entry(add_window)
    entry_stock.pack()

    tk.Button(add_window, text="Guardar", command=guardar_producto).pack()

# Función para modificar producto
def modificar_producto(window):
    def actualizar_producto():
        producto_id = entry_producto_id.get()
        nombre = entry_nombre.get()
        precio = entry_precio.get()
        stock = entry_stock.get()
        
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("UPDATE productos SET nombre=%s, precio=%s, stock=%s WHERE id=%s", (nombre, precio, stock, producto_id))
        conn.commit()
        conn.close()
        
        messagebox.showinfo("Éxito", "Producto modificado con éxito")
        window.destroy()
        abrir_admin()

    # Ventana para modificar producto
    modify_window = tk.Toplevel(window)
    modify_window.title("Modificar Producto")
    
    tk.Label(modify_window, text="ID del Producto:").pack()
    entry_producto_id = tk.Entry(modify_window)
    entry_producto_id.pack()

    tk.Label(modify_window, text="Nuevo Nombre del Producto:").pack()
    entry_nombre = tk.Entry(modify_window)
    entry_nombre.pack()

    tk.Label(modify_window, text="Nuevo Precio del Producto:").pack()
    entry_precio = tk.Entry(modify_window)
    entry_precio.pack()

    tk.Label(modify_window, text="Nuevo Stock del Producto:").pack()
    entry_stock = tk.Entry(modify_window)
    entry_stock.pack()

    tk.Button(modify_window, text="Actualizar", command=actualizar_producto).pack()

# Función para eliminar producto
def eliminar_producto(window):
    def eliminar():
        producto_id = entry_producto_id.get()
        
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM productos WHERE id=%s", (producto_id,))
        conn.commit()
        conn.close()
        
        messagebox.showinfo("Éxito", "Producto eliminado con éxito")
        window.destroy()
        abrir_admin()

    # Ventana para eliminar producto
    delete_window = tk.Toplevel(window)
    delete_window.title("Eliminar Producto")
    
    tk.Label(delete_window, text="ID del Producto a Eliminar:").pack()
    entry_producto_id = tk.Entry(delete_window)
    entry_producto_id.pack()

    tk.Button(delete_window, text="Eliminar", command=eliminar).pack()

# Función para ver historial de ventas
def ver_historial_ventas(window):
    def filtrar_por_fecha():
        fecha_inicio = entry_fecha_inicio.get()
        fecha_fin = entry_fecha_fin.get()
        try:
            datetime.strptime(fecha_inicio, '%Y-%m-%d')
            datetime.strptime(fecha_fin, '%Y-%m-%d')
        except ValueError:
            messagebox.showerror("Error", "Formato de fecha inválido. Use YYYY-MM-DD.")
            return

        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT productos.nombre, ventas.cantidad, ventas.total, ventas.fecha
            FROM ventas
            JOIN productos ON ventas.producto_id = productos.id
            WHERE ventas.fecha BETWEEN %s AND %s
        """, (fecha_inicio, fecha_fin))
        ventas = cursor.fetchall()
        conn.close()

        for venta in ventas:
            tk.Label(window, text=f"Producto: {venta[0]}, Cantidad: {venta[1]}, Total: {venta[2]}, Fecha: {venta[3]}").pack()

    # Ventana para ver historial de ventas
    historial_window = tk.Toplevel(window)
    historial_window.title("Historial de Ventas")
    
    tk.Label(historial_window, text="Fecha Inicio (YYYY-MM-DD):").pack()
    entry_fecha_inicio = tk.Entry(historial_window)
    entry_fecha_inicio.pack()

    tk.Label(historial_window, text="Fecha Fin (YYYY-MM-DD):").pack()
    entry_fecha_fin = tk.Entry(historial_window)
    entry_fecha_fin.pack()

    tk.Button(historial_window, text="Filtrar", command=filtrar_por_fecha).pack()

# Función para realizar ventas
def realizar_venta(window):
    pass  # Aquí se desarrollaría la lógica para realizar una venta

# Configuración de la ventana principal
root = tk.Tk()
root.title("Login")
root.geometry("300x200")

# Campos de login
tk.Label(root, text="Usuario").pack()
entry_usuario = tk.Entry(root)
entry_usuario.pack()

tk.Label(root, text="Clave").pack()
entry_clave = tk.Entry(root, show="*")
entry_clave.pack()

tk.Button(root, text="Iniciar sesión", command=validar_login).pack()

# Iniciar base de datos
iniciar_bd()

# Ejecutar aplicación
root.mainloop()
