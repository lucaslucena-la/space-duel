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
from protocol import MSG_ASSIGN_ID, MSG_DISCONNECT, MSG_STATE, MSG_MOVE, MSG_SHOOT, MSG_READY
import time 
import random


# Configuração do Servidor

HOST = "0.0.0.0" # Aceita conexões de qualquer endereço
PORT = 5000
MAX_PLAYERS = 2
MOVE_STEP = 2 #Pixels por movimento

BULLET_SPEED = 4
BULLET_SIZE = 2
DAMAGE = 10
SCREEN_WIDTH = 160
SCREEN_HEIGHT = 120

SHOT_COOLDOWN = 0.35  # segundos entre tiros (quanto maior, mais lento)
BONUS_INTERVAL = 7      # tempo entre bônus
BONUS_DURATION = 4      # tempo que o bônus fica na tela

# variáveis globais
game_over = False
winner = None
game_phase = "WAITING"
countdown = 0
last_bonus_spawn = time.time()
bonus_end_time = None

#estado global do jogo
game_state = {
    "players": {
        1: {"x": (SCREEN_WIDTH - 8) // 2 - 60, "y": (SCREEN_HEIGHT - 8) // 2, "hp": 100},
        2: {"x": (SCREEN_WIDTH - 8) // 2 + 60, "y": (SCREEN_HEIGHT - 8) // 2, "hp": 100}
    },
    "bullets": [],
    "bonus": None

}

last_shot_time = {
    1: 0,
    2: 0
}

# placar
score = {
    1: 0,
    2: 0
}

# jogadores prontos
ready_players = {
    1: False,
    2: False
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
        "bullets": game_state["bullets"],
        "score": score,
        "game_over": game_over,
        "winner": winner,
        "phase": game_phase,
        "countdown": countdown,
        "ready": ready_players,
        "bonus": game_state["bonus"],
        "bonus_end_time": bonus_end_time
    }

    for conn in clients.values():
        send_message(conn, message)

def process_move(player_id, direction):
    """Atualiza a posição do jogador com base na direção."""
    if game_over:
        return
    if game_phase != "PLAYING":
        return

    player = game_state["players"].get(player_id)
    if not player:
        return

    # Limita movimento para dentro da tela
    if direction == "up":
        if player["y"] >= 18:
            player["y"] -= MOVE_STEP
    elif direction == "down":
        if player["y"] <= SCREEN_HEIGHT - 11:
            player["y"] += MOVE_STEP
    elif direction == "left":
        if player["x"] >= 3:
            player["x"] -= MOVE_STEP
    elif direction == "right":
        if player["x"] <= SCREEN_WIDTH - 11:
            player["x"] += MOVE_STEP

def create_bullet(player_id):
    """Cria uma bala disparada por um jogador."""
    if game_over:
        return
    if game_phase != "PLAYING":
        return
    
    now = time.time()

    # Verifica cooldown
    if now - last_shot_time[player_id] < SHOT_COOLDOWN:
        return
    
    last_shot_time[player_id] = now

    player = game_state["players"].get(player_id)
    if not player:
        return

    if player.get("power", False):
    # tiro triplo
        offsets = [-4, 0, 4]
        for offset in offsets:
            bullet = {
                "x": player["x"] + 3,
                "y": player["y"] + 3 + offset,
                "dir": 1 if player_id == 1 else -1,
                "owner": player_id
            }
            game_state["bullets"].append(bullet)
    else:
        bullet = {
            "x": player["x"] + 3,
            "y": player["y"] + 3,
            "dir": 1 if player_id == 1 else -1,
            "owner": player_id
        }
        game_state["bullets"].append(bullet)

def spawn_bonus():
    game_state["bonus"] = {
        "x": random.randint(20, SCREEN_WIDTH - 20),
        "y": random.randint(20, SCREEN_HEIGHT - 20)
    }

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
            # colisão entre bala e jogador
            if (
                bullet["x"] < player["x"] + 8 and
                bullet["x"] > player["x"] and
                bullet["y"] < player["y"] + 8 and
                bullet["y"] + 2 > player["y"]
            ):
                player["hp"] -= DAMAGE
                player["hit_timer"] = 2  # frames de efeito vermelho
                # se jogador morreu 
                if player["hp"] <= 0:
                    handle_game_over(bullet["owner"])
                bullets_to_remove.append(bullet)
    
    # tempo de efeito de dano
    for player in game_state["players"].values():
        if player.get("hit_timer", 0) > 0:
            player["hit_timer"] -= 1

    for b in bullets_to_remove:
        if b in game_state["bullets"]:
            game_state["bullets"].remove(b)

def update_bonus():
    global last_bonus_spawn, bonus_end_time

    # Só funciona durante partida ativa
    if game_phase != "PLAYING":
        return

    current_time = time.time()

    # -------------------------
    # Se NÃO há bônus ativo
    # -------------------------
    if game_state["bonus"] is None:

        # Espera 7 segundos desde o último evento
        if current_time - last_bonus_spawn >= BONUS_INTERVAL:
            bonus_type = random.choice(["power", "health"])

            game_state["bonus"] = {
                "x": random.randint(20, SCREEN_WIDTH - 20),
                "y": random.randint(20, SCREEN_HEIGHT - 20),
                "type": bonus_type
            }

            bonus_end_time = current_time + BONUS_DURATION
            last_bonus_spawn = current_time

    # -------------------------
    # Se há bônus ativo
    # -------------------------
    else:
        bonus = game_state["bonus"]

        # Verifica tempo de expiração (4 segundos)
        if current_time >= bonus_end_time:
            game_state["bonus"] = None
            last_bonus_spawn = current_time
            bonus_end_time = None
            return

        # Verifica colisão com jogadores
        for pid, player in game_state["players"].items():
            if (
                bonus["x"] < player["x"] + 8 and
                bonus["x"] > player["x"] and
                bonus["y"] < player["y"] + 8 and
                bonus["y"] > player["y"]
            ):
                bonus_type = bonus.get("type")

                if bonus_type == "power":
                    player["power"] = True
                    player["power_end"] = current_time + 5

                elif bonus_type == "health":
                    player["hp"] += 40  # +2 corações
                    if player["hp"] > 100:
                        player["hp"] = 100

                game_state["bonus"] = None
                last_bonus_spawn = current_time
                bonus_end_time = None
                break

def game_loop():
    """Loop principal do jogo, atualiza o estado e envia para os clientes."""
    while True:
        with lock:
            update_bullets()
            update_bonus()

            current_time = time.time()

            for player in game_state["players"].values():
                if player.get("power", False):
                    if current_time >= player.get("power_end", 0):
                        player["power"] = False

            broadcast_state()
        time.sleep(0.05) # 20 FPS

def handle_game_over(winner_id):
    global game_over, winner

    # Se o jogo já terminou, não faz nada (evita duplicar pontos)
    if game_over:
        return

    # Marca que a partida terminou
    game_over = True

    # Define qual jogador venceu
    winner = winner_id

    # Incrementa o placar do vencedor
    score[winner_id] += 1

    # Reseta estado de "pronto para reiniciar"
    # Ambos jogadores precisarão apertar ENTER novamente
    ready_players[1] = False
    ready_players[2] = False

    # Log no servidor
    print(f"[GAME OVER] Jogador {winner_id} venceu!")

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
                elif message["type"] == MSG_SHOOT:
                    with lock:
                        create_bullet(player_id)
                elif message["type"] == MSG_READY:
                    with lock:
                        ready_players[player_id] = True

                        # se os dois prontos, reinicia
                        if ready_players[1] and ready_players[2]:
                            start_countdown()
                            reset_match()

    except Exception as e:
        print(f"[ERROR] Jogador {player_id}: {e}")
    finally:
        print(f"[INFO] Jogador {player_id} desconectado")
        with lock:
            clients.pop(player_id, None)

            # Se todos os jogadores desconectarem, reinicia o jogo
            if len(clients) < 2:
                reset_game()
        conn.close()

def get_free_player_id():
    """Retorna o menor ID de jogador disponível."""
    for pid in range(1, MAX_PLAYERS + 1):
        if pid not in clients:
            return pid
    return None

def start_countdown():
    global game_phase, countdown

    # Define a fase atual como contagem regressiva
    game_phase = "COUNTDOWN"
    countdown = 3

    def tick():
        global countdown, game_phase
        # Se ainda há tempo na contagem
        if countdown > 0:
            countdown -= 1 # diminui 1 segundo

            # Agenda nova chamada em 1 segundo
            threading.Timer(1.0, tick).start()
        else:
            # Antes de iniciar partida, checa se ainda tem dois jogadores
            if len(clients) < 2:
                game_phase = "WAITING"
                return

            # Quando chega em 0 o jogo começa
            game_phase = "PLAYING"

    # Inicia a primeira chamada após 1 segundo
    threading.Timer(1.0, tick).start()

def reset_game():
    global game_over, winner, game_phase, countdown
    global last_bonus_spawn
    global bonus_end_time
    
    last_bonus_spawn = time.time()
    bonus_end_time = None
    
    game_state["bonus"] = None

    # Reseta jogadores para posições e HP iniciais e remove as balas
    reset_player(1)
    reset_player(2)
    game_state["bullets"].clear()

    # Zera o placar geral
    score[1] = 0
    score[2] = 0

    # Volta para fase de espera por jogadores
    game_phase = "WAITING"
    countdown = 0

    # Marca que não há partida encerrada e remove o vencedor
    game_over = False
    winner = None

def reset_match():
    global game_over, winner, last_bonus_spawn, bonus_end_time
    last_bonus_spawn = time.time()
    bonus_end_time = None
    game_state["bonus"] = None

    # Reseta jogadores para posições e HP iniciais e remove as balas
    reset_player(1)
    reset_player(2)
    game_state["bullets"].clear()

    # Marca que não há partida encerrada e remove o vencedor
    game_over = False
    winner = None

def reset_player(player_id):
    """Reseta posição e HP do jogador."""
    if player_id == 1:
        game_state["players"][1] = {"x": (SCREEN_WIDTH - 8) // 2 - 60, "y": (SCREEN_HEIGHT - 8) // 2, "hp": 100}
    elif player_id == 2:
        game_state["players"][2] = {"x": (SCREEN_WIDTH - 8) // 2 + 60, "y": (SCREEN_HEIGHT - 8) // 2, "hp": 100}

def start_server():
    """Inicializa o servidor e aceita conexões de clientes."""
    print("[INFO] Iniciando servidor...")

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Cria socket TCP
    server_sock.bind((HOST, PORT)) # Liga o socket ao endereço e porta
    server_sock.listen() # Começa a escutar conexões

    print(f"[INFO] Servidor iniciado em {HOST}:{PORT}")

    threading.Thread(target=game_loop, daemon=True).start()

    while True:
        conn, addr = server_sock.accept()

        with lock:
            player_id = get_free_player_id()

            if player_id is None:
                send_message(conn, {
                    "type": MSG_DISCONNECT,
                    "reason": "Servidor cheio"
                })
                conn.close()
                continue

            clients[player_id] = conn

            # Se todos os jogadores estiverem conectados, resetar os jogadores
            if len(clients) == 2:
                reset_game()
                start_countdown()

        thread = threading.Thread(target=handle_client, args=(conn, addr, player_id), daemon=True)
        thread.start()
if __name__ == "__main__":
    try:
        start_server()
    except KeyboardInterrupt:
        print("\n[INFO] Servidor encerrado")