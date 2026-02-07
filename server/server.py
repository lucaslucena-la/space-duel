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
from protocol import MSG_ASSIGN_ID, MSG_DISCONNECT, MSG_STATE, MSG_MOVE, MSG_SHOOT
import time 

# Configuração do Servidor

HOST = "127.0.0.1"   # localhost
PORT = 5000
MAX_PLAYERS = 2
MOVE_STEP = 2 #Pixels por movimento

BULLET_SPEED = 4
BULLET_SIZE = 2
DAMAGE = 10
SCREEN_WIDTH = 160
SCREEN_HEIGHT = 120

SHOT_COOLDOWN = 0.25  # segundos entre tiros (quanto maior, mais lento)




#estado global do jogo
game_state = {
    "players": {
        1: {"x": 20, "y": 60, "hp": 100},
        2: {"x": 120, "y": 60, "hp": 100}
    },
    "bullets": []
}

last_shot_time = {
    1: 0,
    2: 0
}


# Estado do servidor
clients = {}  # player_id -> socket
lock = threading.Lock()

def send_message(conn, message: dict):
    """Envia uma mensagem JSON para o cliente pelo socket."""
    try:
        data = json.dumps(message) + "\n"
        conn.sendall(data.encode("utf-8"))
    except Exception as e:
        print(f"[ERROR]: Falha ao enviar mensagem: {e}")

def broadcast_state():
    """Envia o estado atual do jogo para todos os clientes"""
    message = {
        "type": MSG_STATE,
        "players": game_state["players"],
        "bullets": game_state["bullets"]
    }

    for conn in clients.values():
        send_message(conn, message)

def process_move(player_id, direction):
    """Atualiza a posição do jogador com base na direção."""
    player = game_state["players"].get(player_id)
    if not player:
        return

    if direction == "up":
        player["y"] -= MOVE_STEP
    elif direction == "down":
        player["y"] += MOVE_STEP
    elif direction == "left":
        player["x"] -= MOVE_STEP
    elif direction == "right":
        player["x"] += MOVE_STEP

def create_bullet(player_id):
    """Cria uma bala disparada por um jogador."""

    now = time.time()

    # Verifica cooldown
    if now - last_shot_time[player_id] < SHOT_COOLDOWN:
        return
    
    last_shot_time[player_id] = now

    player = game_state["players"].get(player_id)
    if not player:
        return

    bullet = {
        "x": player["x"] + 3 , 
        "y": player["y"],
        "dir": 1 if player_id == 1 else -1,
        "owner": player_id
    }
    game_state["bullets"].append(bullet)

def update_bullets():
    """Atualiza a Posição das balas e verifica colisões."""
    bullets_to_remove = []

    for bullet in game_state["bullets"]:

        bullet["x"] += bullet["dir"] * BULLET_SPEED

        # fora da tela 
        if bullet["x"] < 0 or bullet["x"] > SCREEN_WIDTH:
            bullets_to_remove.append(bullet)
            continue

        # Verifica colisão com jogadores
        for pid, player in game_state["players"].items():
            if pid == bullet["owner"]:
                continue
            
            if (abs(bullet["x"] - player["x"]) < 6 and
                abs (bullet["y"] - player["y"]) < 6):
                player["hp"] -= DAMAGE
                bullets_to_remove.append(bullet)
    
    for b in bullets_to_remove:
        if b in game_state["bullets"]:
            game_state["bullets"].remove(b)

def game_loop():
    """Loop principal do jogo, atualiza o estado e envia para os clientes."""
    while True:
        with lock:
            update_bullets()
            broadcast_state()
        time.sleep(0.05) # 20 FPS


def handle_client(conn, addr, player_id):
    """Thread responsável por escutar mensagens de um cliente."""

    print(f"[INFO] Jogador {player_id} conectado de {addr}")

    # Envia ID atribuído ao jogador
    send_message(conn, {
        "type": MSG_ASSIGN_ID,
        "player_id": player_id
    })

    buffer = ""

    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            buffer += data.decode("utf-8")
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                message = json.loads(line)

                if message["type"] == MSG_MOVE:
                    with lock:
                        process_move(player_id, message["direction"])
                        broadcast_state()
                elif message["type"] == MSG_SHOOT:
                    with lock:
                        create_bullet(player_id)

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

    threading.Thread(target=game_loop, daemon=True).start()

    while True:
        conn, addr = server_sock.accept()

        with lock:
            if len(clients) >= MAX_PLAYERS:
                send_message(conn, {
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