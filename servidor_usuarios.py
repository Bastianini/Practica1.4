import socket
import sys
import threading
import os

# Estructura para almacenar clientes y grupos
clientes = {}
grupos = {}

# Definición de colores
COLORES = {
    "reset": "\033[0m",  # Resetea el color
    "usuario": "\033[94m",  # Azul para nombres de usuario
    "privado": "\033[38;5;214m",  # Naranja para mensajes privados
    "global": "\033[92m",  # Verde para mensajes globales
    "servidor": "\033[94m",  # Azul para mensajes del servidor
    "error": "\033[91m",  # Rojo para errores
    "grupo": "\033[35m",  # Morado para mensajes de grupos
}

def manejar_cliente(conexion, direccion):
    conexion.sendall("Por favor, introduce tu nombre: ".encode())
    nombre = conexion.recv(1024).decode('utf-8').strip()
    clientes[conexion] = nombre
    print(f"El cliente {direccion} se ha registrado como '{nombre}'")

    # Notificar a todos los clientes sobre el nuevo cliente
    for conn in clientes.keys():
        if conn != conexion:
            conn.sendall(f"{COLORES['servidor']}{nombre} se ha unido al chat.{COLORES['reset']}".encode())

    while True:
        datos = conexion.recv(1024)
        if datos:
            mensaje = datos.decode('utf-8').strip()
            if mensaje.lower().startswith("/ng "):
                # Crear un grupo
                nombre_grupo = mensaje.split(maxsplit=1)[1]
                if nombre_grupo not in grupos:
                    grupos[nombre_grupo] = [conexion]  # Agregar el creador al grupo
                    conexion.sendall(f"{COLORES['grupo']}Grupo '{nombre_grupo}' creado y te has unido a él.{COLORES['reset']}".encode())
                else:
                    conexion.sendall(f"{COLORES['error']}Error: El grupo '{nombre_grupo}' ya existe.{COLORES['reset']}".encode())
            elif mensaje.lower().startswith("/join "):
                # Unirse a un grupo
                nombre_grupo = mensaje.split(maxsplit=1)[1]
                if nombre_grupo in grupos:
                    grupos[nombre_grupo].append(conexion)
                    conexion.sendall(f"{COLORES['grupo']}Te has unido al grupo '{nombre_grupo}'.{COLORES['reset']}".encode())
                else:
                    conexion.sendall(f"{COLORES['error']}Error: El grupo '{nombre_grupo}' no existe.{COLORES['reset']}".encode())
            elif mensaje.lower() == "/grupos":
                # Listar grupos
                if grupos:
                    lista_grupos = ", ".join(grupos.keys())
                    conexion.sendall(f"{COLORES['grupo']}Grupos disponibles: {lista_grupos}.{COLORES['reset']}".encode())
                else:
                    conexion.sendall(f"{COLORES['error']}Advertencia: No hay grupos creados.{COLORES['reset']}".encode())
            elif mensaje.lower().startswith("/grupo "):
                # Enviar mensaje a un grupo
                partes = mensaje.split(maxsplit=2)
                if len(partes) < 3:
                    conexion.sendall(f"{COLORES['error']}Error: Formato incorrecto. Usa: /grupo <nombre del grupo> <mensaje>\n{COLORES['reset']}".encode())
                else:
                    nombre_grupo = partes[1]  # Obtener el nombre del grupo
                    mensaje_grupo = partes[2]  # Obtener el mensaje
                    if nombre_grupo in grupos:
                        for conn in grupos[nombre_grupo]:
                            if conn != conexion:  # No enviar al emisor
                                conn.sendall(f"{COLORES['grupo']}{nombre} (Grupo {nombre_grupo}): {mensaje_grupo}{COLORES['reset']}".encode())
                    else:
                        conexion.sendall(f"{COLORES['error']}Error: El grupo '{nombre_grupo}' no existe.{COLORES['reset']}".encode())
            elif mensaje.lower() == "/users":
                # Enviar la lista de usuarios conectados
                lista_usuarios = ", ".join(clientes.values())
                conexion.sendall(f"{COLORES['global']}Usuarios conectados: {lista_usuarios}.{COLORES['reset']}".encode())
            elif mensaje.lower() == "/help":
                # Mostrar la lista de comandos
                ayuda = (
                    "Comandos disponibles:\n"
                    "/ng <nombre> - Crea un nuevo grupo.\n"
                    "/join <nombre> - Se une a un grupo existente.\n"
                    "/grupos - Muestra la lista de grupos disponibles.\n"
                    "/grupo <nombre> <mensaje> - Envía un mensaje a un grupo.\n"
                    "/users - Muestra la lista de usuarios conectados.\n"
                    "/pm <usuario> <mensaje> - Envía un mensaje privado a un usuario específico.\n"
                    "/file <usuario> <ruta> - Envía un archivo a un usuario específico.\n"
                    "/getfile <nombre_archivo> - Solicita la descarga de un archivo.\n"
                    "salir - Cierra la conexión.\n"
                )
                conexion.sendall(f"{COLORES['global']}{ayuda}{COLORES['reset']}".encode())
            elif mensaje.lower().startswith("/pm "):
                # Manejar mensajes a usuarios específicos
                partes = mensaje.split(maxsplit=2)
                if len(partes) < 3:
                    conexion.sendall(f"{COLORES['error']}Error: Formato incorrecto. Usa: /pm <usuario> <mensaje>\n{COLORES['reset']}".encode())
                else:
                    destinatario = partes[1]
                    mensaje_privado = partes[2]
                    encontrado = False
                    for conn, user in clientes.items():
                        if user.lower() == destinatario.lower():  # Comparar sin importar mayúsculas
                            conn.sendall(f"{COLORES['privado']}(Privado de {nombre}): {mensaje_privado}{COLORES['reset']}".encode())
                            encontrado = True
                            break
                    if not encontrado:
                        conexion.sendall(f"{COLORES['error']}Error: Usuario '{destinatario}' no encontrado.{COLORES['reset']}".encode())
            elif mensaje.lower().startswith("/file "):
                # Manejar el envío de archivos
                partes = mensaje.split(maxsplit=2)
                if len(partes) < 3:
                    conexion.sendall(f"{COLORES['error']}Error: Formato incorrecto. Usa: /file <usuario> <ruta>\n{COLORES['reset']}".encode())
                else:
                    destinatario = partes[1]
                    ruta_archivo = partes[2]
                    if os.path.isfile(ruta_archivo):
                        # Leer la primera línea del archivo
                        with open(ruta_archivo, 'r') as archivo:
                            primera_linea = archivo.readline().strip()
                        
                        # Notificar al destinatario sobre el archivo
                        encontrado = False
                        for conn, user in clientes.items():
                            if user.lower() == destinatario.lower():
                                conn.sendall(f"{COLORES['servidor']}(Archivo de {nombre}): {primera_linea}\n¿Deseas descargarlo? (sí/no){COLORES['reset']}".encode())
                                encontrado = True
                                break
                        if not encontrado:
                            conexion.sendall(f"{COLORES['error']}Error: Usuario '{destinatario}' no encontrado.{COLORES['reset']}".encode())
                    else:
                        conexion.sendall(f"{COLORES['error']}Error: El archivo '{ruta_archivo}' no existe.\n{COLORES['reset']}".encode())
            elif mensaje.lower().startswith("/getfile "):
                # Manejar la solicitud de descarga del archivo
                nombre_archivo = mensaje.split(maxsplit=1)[1]
                if os.path.isfile(nombre_archivo):
                    with open(nombre_archivo, 'rb') as archivo:
                        while True:
                            contenido = archivo.read(1024)
                            if not contenido:
                                break
                            conexion.sendall(contenido)
                    conexion.sendall("FIN".encode())  # Indicar que se ha terminado de enviar el archivo
                else:
                    conexion.sendall(f"{COLORES['error']}Error: El archivo '{nombre_archivo}' no existe.\n{COLORES['reset']}".encode())
            else:
                # Enviar mensaje a todos los clientes
                for conn in clientes.keys():
                    if conn != conexion:
                        conn.sendall(f"{COLORES['global']}{nombre}: {mensaje}{COLORES['reset']}".encode())
        else:
            print(f"Conexión cerrada desde {direccion}")
            del clientes[conexion]
            break

def iniciar_servidor_tcp(puerto):
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind(("0.0.0.0", puerto))
    servidor.listen(5)
    print(f"Servidor TCP esperando conexiones en el puerto {puerto}...")

    while True:
        conexion, direccion = servidor.accept()
        print(f"Conexión establecida desde {direccion}")
        threading.Thread(target=manejar_cliente, args=(conexion, direccion)).start()

if __name__ == "__main__":
    puerto_servidor = 10000  # puerto por defecto

    if len(sys.argv) > 1:  # permite elegir el puerto por línea de comandos
        try:
            puerto_servidor = int(sys.argv[1])
            if not (1024 <= puerto_servidor <= 65535):
                print("\nError: El puerto debe estar entre el 1024 y el 65535")
                sys.exit()
        except ValueError:
            print("\nError: El puerto debe ser un número válido")
            sys.exit(1)

    iniciar_servidor_tcp(puerto_servidor)
