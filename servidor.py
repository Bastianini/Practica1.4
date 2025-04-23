import socket
import select
import sys
import base64 #manejo de archivos
import os

COLORES = {
    "privado": "\033[94m",      #azul para mensaje privado
    "fichero": "\033[95m",      #morado para ficheros
    "error": "\033[91m",        #Rojo para errores
    "secret": "\033[38;5;208m", #Reservado para futuras implementaciones
    "reset": "\033[0m"          #Resetea el color al terminar
}

LISTA_COMANDOS = {
    "/help": "Muestra esta lista de comandos",
    "/users": "Muestra la lista de usuarios conectados",
    "/pm <usuario> <mensaje>": "Envía un mensaje privado a un usuario",
    "/file <usuario> <ruta>": "Envía un fichero a un usuario",
    "salir": "Cierra la conexión con el servidor "
}

def UList(clientes):
#Evia lalista  actualizada a todos los clientes
    lista_usuarios = ", ".join([nombre for _, (_, nombre) in clientes.items() if nombre])
    mensaje = f"\n--- USUARIOS CONECTADOS ({len(clientes)}) ---\n{lista_usuarios}\n-------------------------------\n"

    for cliente in clientes:
        try:
            cliente.sendall(mensaje.encode())
        except:
            continue #si falrta algun cliente se sigue con los demas

def iniciar_servidor_tcp(puerto):
    # Crear el socket del servidor
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind(("0.0.0.0", puerto))
    servidor.listen(5)
    print(f"Servidor TCP esperando conexiones en el puerto {puerto}...")

    # Lista de sockets que vamos a monitorear, empezando con el servidor
    sockets = [servidor]
    clientes = {} # diccionario que guarda el nombre y la direccion del cliente

    while True:
        # Usamos select para monitorear los sockets
        lectura, _,  _ = select.select(sockets, [], [])

        for sock in lectura:
            # Si el socket es el servidor, significa que hay una nueva conexión
            if sock == servidor:
                conexion, direccion = servidor.accept()
                print(f"Conexión establecida desde {direccion}")
                sockets.append(conexion)
                clientes[conexion] = (direccion, None) #el nombre inicia como None
                conexion.sendall("Por favor, introduce tu nombre: ".encode())
            else:
                # Si no es el servidor, es un cliente que envía datos
                try:
                    datos = sock.recv(1024)
                    if datos:
                        # Reenviar el mensaje a todos los clientes conectados
                        mensaje = datos.decode('utf-8').strip() #strip elimina espacios en blanco
                        direccion, nombre = clientes[sock]
                        #print(f"Recibido de {clientes[sock]}: {mensaje}")
                        if nombre is None: #si nombre no esta asignado, este es el nombre del cliente
                            clientes[sock] = (direccion, mensaje)
                            print(f"El cliente {direccion} se ha registrado como '{mensaje}'")

                            for cliente in clientes:
                                if cliente != sock:
                                    cliente.sendall(f"{mensaje} se ha unido al chat.\n".encode())

                           # UList(clientes)
                        else:

                            if mensaje.lower() == "/help":
                                ayuda = "\n".join([f"{cmd}: {desc}" for cmd, desc in LISTA_COMANDOS.items()])
                                sock.send(f"\n--------------- LISTA DE COMANDOS ---------------\n{ayuda}\n-------------------------------------------------\n".encode())

                            elif mensaje.lower() == "/users": #comando para ver la lista
                                UList(clientes)
                                #sock.sendall(lista.encode())

                            elif mensaje.lower().startswith("/pm "): #comando pensaje privado
                                partes = mensaje.split(maxsplit = 2)
                                if len(partes) >= 3:
                                    destino, mensaje_privado = partes[1], partes[2]
                                    encontrado = False
                                    for sock_cliente, (_, nombre_cliente) in clientes.items():
                                        if nombre_cliente == destino:
                                            try:
                                                sock_cliente.send(f"{COLORES['privado']}(Privado) {nombre}: {mensaje_privado}{COLORES['reset']}\n".encode())
                                               # sock_cliente.send(f"(Privado) {nombre}: {mensaje_privado}\n".encode())
                                               # sock.send(f"(Enviado a {destino}): {mensaje_privado})\n".encode())
                                                sock.send(f"{COLORES['privado']}(Enviado a {destino}): {mensaje_privado}{COLORES['reset']}\n".encode())
                                            except (BlockingIOError, ConnectionError):
                                                sock.send("Error: No se pudo entregar el mensaje\n".encode())
                                            encontrado = True
                                            break
                                    if not encontrado:
                                        sock.send(f"Error: Usuario '{destino}' no encontrado\n".encode())
                                else:
                                    sock.send("Formato incorrecto. Use: /pm <usuario> <mensaje>\n".encode())

                            elif mensaje.lower().startswith("/file "): #comando para envio de ficheros
                                partes = mensaje.split(maxsplit = 2)
                                if len(partes) == 3:
                                    destino, ruta_archivo = partes[1], partes[2]
                                    if os.path.exists(ruta_archivo):
                                        try:
                                            with open(ruta_archivo, "rb") as f:
                                                datos_archivo = f.read()
                                                archivo_b64 = base64.b64encode(datos_archivo).decode()

                                            for sock_cliente, (_, nombre_dest) in clientes.items():
                                                if nombre_dest == destino:
                                                    # mensaje de preparacion
                                                    sock_cliente.send(f"{COLORES['fichero']}ARCHIVO_INICIADO| {nombre}|{os.path.basename(ruta_archivo)}{COLORES['reset']}\n".encode())
                                                    #luego envia los datos en bloques
                                                    for i in range(0, len(archivo_b64),1024):
                                                        chunk = archivo_b64[i:i+1024]
                                                        sock_cliente.sendall(chunk.encode())
                                                    sock_cliente.send(f"{COLORES['fichero']}ARCHIVO_FINALIZADO{COLORES['reset']}\n".encode())
                                                    sock_cliente.send(f"{COLORES['fichero']}Archivo enviado a {destino}{COLORES['reset']}\n".encode())
                                                    break

                                                else:
                                                    sock.send(f"{COLORES['error']}Error: Usuario no encontrado{COLORES['reset']}\n".encode())

                                        except Exception as e:
                                            sock.send(f"{COLORES['error']}Error al enviar el archivo: {str(e)}{COLORES['reset']}\n".encode())

                                    else:
                                        sock.send(f"{COLORES['error']}Error: Archivo no encontrado{COLORES['reset']}\n".encode())

                                else:
                                    sock.send(f"{COLORES['error']}Formato incorrecro. Usa: /file <usuario> <ruta_archivo>{COLORES['reset']}\n".encode())

                            else:
                            # si el nombre ya se asigno, es un mensaje normal
                                print(f"Mensaje de {nombre} ({direccion}): {mensaje}") #reenvia el mensaje a el resto de clientes
                                for cliente in clientes:
                                    if cliente != sock:
                                        cliente.sendall(f"{nombre}: {mensaje}\n".encode())
                    else: #si no recivimos datos, el cliente se ha desconectado
                        direccion, nombre = clientes[sock]
                        print(f"Conexión cerrada desde {nombre} ({direccion})")
                       # UList(clientes)
                        sock.close()
                        sockets.remove(sock)
                        del clientes[sock]
                        for cliente in clientes: # notificar de la desconexion
                            cliente.sendall(f"{nombre} ha abandonado el chat.\n".encode())
                except Exception as e:
                    print(f"Error: {e}")
                    sock.close()
                    sockets.remove(sock)
                    if sock in clientes:
                        del clientes[sock]

if __name__ == "__main__":

    puerto_servidor = 10000 #puerto por defecto

    if len(sys.argv) > 1: #permite elegir el puerto por linea de comandos
        try:
            puerto_servidor = int(sys.argv[1])
            if not (1024 <= puerto_servidor <= 65535):
                print("\nError: El puerto debe estar entre el 1024 y el 65535")
                sys.exit()
        except ValueError:
            print("\nError: El puerto debe ser un numero valido")
            sys.exit(1)

    iniciar_servidor_tcp(puerto_servidor)
