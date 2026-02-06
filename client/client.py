"""
client.py

Cliente do jogo Space Duel.
Responsável por:
- Conectar ao servidor
- Receber identificação do jogador
- Enviar mensagens básicas

"""

import socket
import json
import threading
from protocol import MSG_ASSIGN_ID

# Configuração do Cliente

SERVER_HOST = "127.0.0.1" # Endereço IP do servidor
SERVER_PORT = 5000       # Porta do servidor


def listen_server(sock):
    """Threaad para ouvir mensagens do servidor."""
    while True:
        try:
            data = sock.recv(1024) # Recebe dados do servidor
            if not data: 
                break
            message = json.loads(data.decode("utf-8")) # Decodifica a mensagem JSON
            print(f"[SERVER]: {message}")
        except Exception as e:
            print(f"[ERROR]: {e}")
            break

def start_client():
    """Inicializa o cliente e conecta ao servidor."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Cria socket TCP
    sock.connect((SERVER_HOST, SERVER_PORT)) # Conecta ao servidor

    print("[INFO]: Conectado ao servidor.")

    # Inicia thread para ouvir mensagens do servidor
    thread = threading.Thread(target=listen_server, args=(sock,), daemon= True)
    thread.start()

    # Envio manual de mensagens (teste)
    while True:
        msg = input("Digite uma mensagem (ou 'exit'): ")
        if msg.lower() == "exit":
            break

        sock.sendall(json.dumps({
            "type": "test",
            "message": msg
        }).encode("utf-8"))

    sock.close()


if __name__ == "__main__":
    start_client()
