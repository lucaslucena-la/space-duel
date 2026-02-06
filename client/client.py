"""
client.py

Cliente do jogo Space Duel.
Envia comandos de movimento e recebe estado do jogo.
"""

import socket
import json
import threading
from protocol import MSG_ASSIGN_ID, MSG_DISCONNECT, MSG_STATE, MSG_MOVE

# Configuração do Cliente

SERVER_HOST = "127.0.0.1" # Endereço IP do servidor
SERVER_PORT = 5000       # Porta do servidor


def listen_server(sock):
    buffer = ""

    while True:
        try:
            data = sock.recv(1024)
            if not data:
                break

            buffer += data.decode("utf-8")

            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                message = json.loads(line)

                if message["type"] == MSG_ASSIGN_ID:
                    print(f"[INFO] Você é o jogador {message['player_id']}")

                elif message["type"] == MSG_STATE:
                    print(f"[ESTADO] {message['players']}")

        except Exception as e:
            print(f"[ERRO] {e}")
            break


def start_client():
    """Inicializa o cliente e conecta ao servidor."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Cria socket TCP
    sock.connect((SERVER_HOST, SERVER_PORT)) # Conecta ao servidor

    print("[INFO]: Conectado ao servidor.")

    # Inicia thread para ouvir mensagens do servidor
    thread = threading.Thread(target=listen_server, args=(sock,), daemon= True)
    thread.start()

    while True:
        direction = input("Mover (up/down/left/right): ")

        sock.sendall((json.dumps({
            "type": MSG_MOVE,
            "direction": direction
        }) + "\n").encode("utf-8"))


if __name__ == "__main__":
    start_client()
