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

# Mecânicas do jogo
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

# controle de cooldown de tiro por jogador 
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
lock = threading.Lock() # para sincronizar acesso ao estado do jogo entre threads 

# Funções para comunicação e lógica do jogo
def send_message(conn, message: dict): 
    """Envia uma mensagem JSON para o cliente pelo socket."""
    try:
        data = json.dumps(message) + "\n" # o \n é importante para o cliente saber onde termina a mensagem
        conn.sendall(data.encode("utf-8")) # envia os dados codificados como bytes
    except Exception as e:
        print(f"[ERROR]: Falha ao enviar mensagem: {e}")

# Função por manter a "ilusão" de sincronização do jogo entre os clientes, enviando o estado atualizado a cada 50ms
def broadcast_state():
    """Envia o estado atual do jogo para todos os clientes"""
    message = {
        "type": MSG_STATE,
        "players": game_state["players"],
        "bullets": game_state["bullets"],
        "bonus": game_state["bonus"],
        "score": score,
        "game_over": game_over,
        "winner": winner,
        "phase": game_phase,
        "countdown": countdown,
        "ready": ready_players,
        "bonus_end_time": bonus_end_time
    }

    for conn in clients.values():
        send_message(conn, message)

# Funções de lógica do jogo (gerenciamento de movimento, tiros, bônus, colisões, etc)
def process_move(player_id, direction):
    """Atualiza a posição do jogador com base na direção."""

    if game_over: # se o jogo já terminou, o servidor ignora qualquer pacote de movimento
        return
    if game_phase != "PLAYING": # só permite movimento durante a partida ativa
        return

    player = game_state["players"].get(player_id) # o servidor busca o dicionário de dados específico do jogador no game_state
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

# Função para criar uma nova bala quando um jogador atira, respeitando o cooldown e o tipo de tiro (normal ou triplo)
def create_bullet(player_id): # o servidor indentifica qual jogador enviou o comando de tiro 
    """Cria uma bala disparada por um jogador."""
    if game_over:
        return
    if game_phase != "PLAYING":
        return
    
    now = time.time() # servidor verifica o horário atual para comparar com o último tiro do jogador e garantir que o cooldown seja respeitado

    # Verifica cooldown
    if now - last_shot_time[player_id] < SHOT_COOLDOWN: # impede que o jogador dispare novamente antes de passar o tempo mínimo definido em SHOT_COOLDOWN
        return
    
    last_shot_time[player_id] = now # atualiza o horário do último tiro para o jogador

    # Lógica de disparo (Simples ou com Bonus)
    player = game_state["players"].get(player_id)  # o servidor busca o dicionário de dados específico do jogador para verificar se ele tem o bônus de tiro triplo ativo
    if not player:
        return

    if player.get("power", False): # se o jogador tiver o bônus de tiro triplo ativo, o servidor cria 3 balas com offsets verticais para simular um tiro em cone
        
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
    else: # cria apenas uma bala centralizada na posição da nave
        bullet = {
            "x": player["x"] + 3,
            "y": player["y"] + 3,
            "dir": 1 if player_id == 1 else -1,
            "owner": player_id
        }
        game_state["bullets"].append(bullet)

# Função para atualizar a posição das balas, verificar colisões com jogadores e remover balas que saíram da tela ou colidiram
def update_bullets():
    """Atualiza a Posição das balas e verifica colisões."""
    bullets_to_remove = [] # lista auxiliar para armazenar balas que precisam ser removidas após a atualização (se colidiram ou saíram da tela)

    for bullet in game_state["bullets"]: 

        bullet["x"] += bullet["dir"] * BULLET_SPEED # atualiza a posição horizontal da bala com base na direção e velocidade

        # fora da tela 
        if bullet["x"] < 0 or bullet["x"] > SCREEN_WIDTH:
            bullets_to_remove.append(bullet)
            continue

        # Verifica colisão com jogadores
        for pid, player in game_state["players"].items():
            if pid == bullet["owner"]: # regra de segurança para impedir que o jogador seja atingido por sua própia bala
                continue
            # colisão entre bala e jogador
            if ( 
                bullet["x"] < player["x"] + 8 and
                bullet["x"] > player["x"] and
                bullet["y"] < player["y"] + 8 and
                bullet["y"] + 2 > player["y"]
            ):
                player["hp"] -= DAMAGE # reduz a vida do jogador diretamente no game_state
                player["hit_timer"] = 2  # frames de efeito vermelho
                # se jogador morreu 
                if player["hp"] <= 0:
                    handle_game_over(bullet["owner"])
                bullets_to_remove.append(bullet)
    
    # tempo de efeito de dano
    for player in game_state["players"].values():
        if player.get("hit_timer", 0) > 0:
            player["hit_timer"] -= 1

    # remove balas que colidiram ou saíram da tela
    for b in bullets_to_remove:
        if b in game_state["bullets"]:
            game_state["bullets"].remove(b)

# Função para gerenciar o surgimento de bônus no mapa, verificando o tempo desde o último bônus e a duração do bônus ativo, além de verificar colisões com jogadores para aplicar os efeitos dos bônus
def spawn_bonus():
    game_state["bonus"] = {
        "x": random.randint(20, SCREEN_WIDTH - 20),
        "y": random.randint(20, SCREEN_HEIGHT - 20)
    }

# Função para atualizar o estado dos bônus, gerenciar o tempo de surgimento e expiração, e aplicar os efeitos dos bônus aos jogadores que os coletarem
def update_bonus():
    global last_bonus_spawn, bonus_end_time # variáveis globais para controlar o tempo de surgimento e expiração dos bônus

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
            bonus_type = random.choice(["power", "health"]) # servidor define aleatoriamente qual bonus irá aparecer

            # gera posição aleatória para o bônus dentro da tela e armazena o tipo do bônus no game_state
            game_state["bonus"] = {
                "x": random.randint(20, SCREEN_WIDTH - 20),
                "y": random.randint(20, SCREEN_HEIGHT - 20),
                "type": bonus_type
            }

            bonus_end_time = current_time + BONUS_DURATION # define o tempo de expiração do bonus na tela
            last_bonus_spawn = current_time

    # -------------------------
    # Se há bônus ativo
    # -------------------------
    else:
        bonus = game_state["bonus"]

        # Verifica tempo de expiração 
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
                
                # Aplica efeito do bônus tiro triplo
                if bonus_type == "power":
                    player["power"] = True
                    player["power_end"] = current_time + 5
                
                # Aplica efeito do bônus de vida
                elif bonus_type == "health":
                    player["hp"] += 40  # +2 corações
                    if player["hp"] > 100:
                        player["hp"] = 100

                game_state["bonus"] = None
                last_bonus_spawn = current_time
                bonus_end_time = None
                break

# Função para lidar com o encerramento da partida, definindo o vencedor, atualizando o placar e preparando o estado para uma possível nova partida
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

# Thread para lidar com a comunicação de cada cliente, processando mensagens recebidas e atualizando o estado do jogo conforme as ações dos jogadores
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
            while "\n" in buffer: # processa cada mensagem completa (terminada em \n) que chegar do cliente
                line, buffer = buffer.split("\n", 1)
                message = json.loads(line)

                if message["type"] == MSG_MOVE: # chama lógica de moviemnto 
                    with lock:
                        process_move(player_id, message["direction"]) 
                elif message["type"] == MSG_SHOOT: # chama lógica de tiro
                    with lock:
                        create_bullet(player_id)
                elif message["type"] == MSG_READY: # marca jogador como pronto para reiniciar a partida após um game over
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

# Funções para gerenciar o estado do jogo, como resetar posições, iniciar contagem regressiva para início da partida e resetar o estado para uma nova partida
def get_free_player_id():
    """Retorna o menor ID de jogador disponível."""
    for pid in range(1, MAX_PLAYERS + 1):
        if pid not in clients:
            return pid
    return None

# Função para iniciar a contagem regressiva antes do início da partida, gerenciando a transição entre as fases de espera e jogo ativo
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

# Função para resetar o estado do jogo, incluindo posições dos jogadores, vida, balas, bônus e placar, preparando para uma nova partida ou para o estado inicial de espera por jogadores
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

# Função para resetar o estado dos jogadores e do jogo para o início de uma nova partida, mantendo o placar acumulado
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

# Função para resetar a posição e HP de um jogador específico, usada tanto no reset geral do jogo quanto no reset para nova partida
def reset_player(player_id):
    """Reseta posição e HP do jogador."""
    if player_id == 1:
        game_state["players"][1] = {"x": (SCREEN_WIDTH - 8) // 2 - 60, "y": (SCREEN_HEIGHT - 8) // 2, "hp": 100}
    elif player_id == 2:
        game_state["players"][2] = {"x": (SCREEN_WIDTH - 8) // 2 + 60, "y": (SCREEN_HEIGHT - 8) // 2, "hp": 100}

# Loop principal do jogo, responsável por atualizar o estado do jogo (movimento de balas, surgimento de bônus, duração dos efeitos) e enviar o estado atualizado para os clientes a cada 50ms
def game_loop():
    """Loop principal do jogo, atualiza o estado e envia para os clientes."""
    while True:
        with lock: # garante exclusão mútua 
            update_bullets() # move os projéteis e checa colisões
            update_bonus() # gerencia o ciclo de vida dos itens especiais

            current_time = time.time()

            for player in game_state["players"].values():
                if player.get("power", False):
                    if current_time >= player.get("power_end", 0): # garante que o efeito de bônus de tire expire após o tempo definido
                        player["power"] = False

            broadcast_state() # envia estado atualizado para os clientes
        time.sleep(0.05) # 20 FPS


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