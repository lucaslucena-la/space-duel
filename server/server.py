"""
server.py

Servidor do jogo Space Duel.
Responsável por:
- Aceitar conexões TCP
- Atribuir IDs aos jogadores
- Gerenciar comunicação básica

"""

import socket
import threading
import json
from protocol import MSG_ASSIGN_ID, MSG_DISCONNECT

# Configuração do Servidor

HOST = "127.0.0.1"   # localhost
PORT = 5000
MAX_PLAYERS = 2

# Estado do servidor
clients = {}  # player_id -> socket
lock = threading.Lock()

def send_messahe(conn, messahe: dict):
    """Envia uma mensagem JSON para o cliente pelo socket."""
    try:
        conn.sendall(json.dumps(messahe).encode("utf-8"))
    except Exception as e:
        print(f"[ERROR]: Falha ao enviar mensagem: {e}")

def handle_client(conn, addr, player_id):
    """Thread responsável por escutar mensagens de um cliente."""

    print(f"[INFO] Jogador {player_id} conectado de {addr}")

    # Envia ID atribuído ao jogador
    send_messahe(conn, {
        "type": MSG_ASSIGN_ID,
        "player_id": player_id
    })

    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            message = json.loads(data.decode("utf-8"))
            print(f"[RECEBIDO] Jogador {player_id}: {message}")
    except Exception as e:
        print(f"[ERROR] Jogador {player_id}: {e}")
    finally:
        print(f"[INFO] Jogador {player_id} desconectado")
        with lock:
            del clients[player_id]
        conn.close()

def start_server():
    """Inicializa o servidor e aceita conexões de clientes."""
    print("[INFO] Iniciando servidor...")

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Cria socket TCP
    server_sock.bind((HOST, PORT)) # Liga o socket ao endereço e porta
    server_sock.listen() # Começa a escutar conexões

    print(f"[INFO] Servidor iniciado em {HOST}:{PORT}")

    player_id_counter = 1

    
    while True:
        conn, addr = server_sock.accept()

        with lock:
            if len(clients) >= MAX_PLAYERS:
                send_messahe(conn, {
                    "type": MSG_DISCONNECT,
                    "reason": "Servidor cheio"
                })
                conn.close()
                continue

            player_id = player_id_counter
            clients[player_id] = conn
            player_id_counter += 1

        thread = threading.Thread(target=handle_client, args=(conn, addr, player_id), daemon=True)
        thread.start()
if __name__ == "__main__":
    start_server()