"""
client.py

Cliente gráfico do jogo Space Duel.
Responsável por:
- Conectar ao servidor
- Enviar comandos de movimento
- Receber estado do jogo
- Renderizar usando Pyxel
"""

import socket
import json
import threading
import pyxel
from protocol import MSG_ASSIGN_ID, MSG_STATE, MSG_MOVE, MSG_SHOOT, MSG_READY, MSG_DISCONNECT
import random

# Configuração do Cliente

SERVER_HOST = "127.0.0.1" # Endereço IP do servidor
SERVER_PORT = 5000       # Porta do servidor

SCREEN_WIDTH = 160
SCREEN_HEIGHT = 120
PLAYER_SIZE = 8

HEART_SIZE = 8      # largura e altura do coração no banco de imagens
MAX_HEARTS = 5      # número total de corações por jogador
HEART_HP = 20       # cada coração representa 20 HP

# Estado global (renderização)

player_id = None
players_state ={}

lock = threading.Lock()

disconnect_reason = None

class Background:
    def __init__(self, width, height, num_stars=100):
        # Guarda o tamanho da tela para saber os limites
        self.width = width
        self.height = height

        # Cria a lista de estrelas com posições aleatórias
        self.stars = [
            (random.randint(0, width - 1), # posição horizontal aleatória
             random.randint(0, height - 1)) # posição vertical aleatória
            for _ in range(num_stars) # repete num_stars vezes
        ]

    def update(self):
        # nova lista com posições atualizadas
        new_stars = []

        # Percorre todas as estrelas atuais
        for x, y in self.stars:
            y += 1 # move a estrela 1 pixel para baixo
            
            # volta a estrela para o topo da tela se ela sair
            if y > self.height:
                y -= self.height 
            
            # adiciona a nova posição à lista
            new_stars.append((x, y))

        # substitui a lista antiga pela atualizada
        self.stars = new_stars

    def draw(self):
        # Desenha todas as estrelas
        for x, y in self.stars:
            pyxel.pset(x, y, pyxel.COLOR_CYAN) # Desenha a estrela na cor ciana na posição (x, y)

class SpaceDuelClient:
    def __init__(self):
        #connexão com o servidor
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #Cria um socket TCP
        self.sock.connect((SERVER_HOST, SERVER_PORT)) #Conecta ao servidor
        
        print(f"Conectado ao servidor em {SERVER_HOST}:{SERVER_PORT}")

        #thread para ouvir o servidor 
        threading.Thread(target=self.listen_server, daemon=True).start()

        # inicializa o pyxel
        pyxel.init(SCREEN_WIDTH, SCREEN_HEIGHT, title="Space Duel")

        # carrega os assets
        pyxel.load("assets.pyxres")

        # inicializa o background
        self.background = Background(SCREEN_WIDTH, SCREEN_HEIGHT)

        pyxel.run(self.update, self.draw)

    def draw_players(self, players):
        for pid, player in players.items():
            x, y = player["x"], player["y"]

            if int(pid) == 1:
                pyxel.blt(x, y, 0, 0, 0, 8, 8, 0)
            else:
                pyxel.blt(x, y, 0, 8, 0, 8, 8, 0)
    
    def draw_hearts(self, player_hp, x, y):
        """Desenha corações de acordo com o HP do jogador"""
        hearts_to_draw = MAX_HEARTS
        hp_remaining = player_hp

        for i in range(hearts_to_draw):
            if hp_remaining >= HEART_HP:
                # coração cheio
                u = 0  # posição x do coração cheio no banco
            elif hp_remaining >= HEART_HP // 2:
                # coração meio cheio
                u = 8  # posição x do coração meio cheio no banco
            else:
                # coração vazio
                u = 16 # posição x do coração vazio no banco

            pyxel.blt(x + i * (HEART_SIZE + 1), y, 0, u, 8, HEART_SIZE, HEART_SIZE, 0)
            hp_remaining -= HEART_HP

    def listen_server(self):
        """Escuta mensagens do servidor"""

        global player_id, players_state
        buffer = ""

        while True:
            try:
                data = self.sock.recv(1024)
                if not data:
                    print("Desconectado do servidor")
                    break

                buffer += data.decode("utf-8")

                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    message = json.loads(line)

                    if message["type"] == MSG_ASSIGN_ID:
                        player_id = message["player_id"]
                        print(f"[INFO] Você é o jogador: {player_id}")

                    elif message["type"] == MSG_STATE:
                        with lock: 
                            players_state = message

                    elif message["type"] == MSG_DISCONNECT:
                        global disconnect_reason
                        disconnect_reason = message.get("reason", "")
                        return
                            
            except Exception as e:
                    print(f"[ERROR] Erro ao receber dados: {e}")
                    break
            
    def send_move(self, direction):
        """Envia comando de movimento ao servidor"""

        message = {
            "type": MSG_MOVE,
            "direction": direction
        }

        self.sock.sendall((json.dumps(message) + "\n").encode("utf-8"))

    def send_shoot(self):
        """Envia comando de atirar ao servidor"""

        message = {
            "type": MSG_SHOOT
        }

        self.sock.sendall((json.dumps(message) + "\n").encode("utf-8"))

    def update(self):
        """Captura input do teclado"""

        # Se o servidor estiver cheio e um jogador foi desconectado, aguarda apertar Q para sair
        global disconnect_reason
        if disconnect_reason:
            if pyxel.btnp(pyxel.KEY_Q):
                pyxel.quit()
            return

        game_over = players_state.get("game_over", False)

        # Se o jogo acabou, aguarda apertar ENTER para reiniciar
        if game_over:
            if pyxel.btnp(pyxel.KEY_RETURN):
                self.sock.sendall((json.dumps({"type": MSG_READY})+"\n").encode("utf-8"))
            elif pyxel.btnp(pyxel.KEY_Q):
                pyxel.quit()
            return

        if pyxel.btn(pyxel.KEY_UP):
            self.send_move("up")
        elif pyxel.btn(pyxel.KEY_DOWN):
            self.send_move("down")
        elif pyxel.btn(pyxel.KEY_LEFT):
            self.send_move("left")
        elif pyxel.btn(pyxel.KEY_RIGHT):
            self.send_move("right")

        if pyxel.btn(pyxel.KEY_SPACE):
            self.send_shoot()

        # Atualiza o background
        self.background.update()
                
    def draw(self):

        # Se o servidor estiver cheio e um jogador foi desconectado, mostra a mensagem
        global disconnect_reason
        if disconnect_reason:
            self.background.draw()
            pyxel.text((SCREEN_WIDTH - 56)//2, SCREEN_HEIGHT//3, f"Server is full", pyxel.frame_count % 16)
            pyxel.text((SCREEN_WIDTH - 32)//2, 50, "Q - QUIT", pyxel.COLOR_WHITE)
            return

        # Desenha o background
        pyxel.cls(0)
        self.background.draw()

        with lock:
            phase = players_state.get("phase", "WAITING")
            game_over = players_state.get("game_over", False)

            if game_over:
                self.draw_game_over()
            elif phase == "WAITING":
                self.draw_waiting()
            elif phase == "COUNTDOWN":
                self.draw_countdown()
            elif phase == "PLAYING":
                self.draw_playing()

    def draw_playing(self):
        players = players_state.get("players", {})
        bullets = players_state.get("bullets", [])

        self.draw_players(players)

        # vidas
        for pid, player in players.items():
            if int(pid) == 1:
                self.draw_hearts(player["hp"], 1, 0)
            else:
                self.draw_hearts(player["hp"], SCREEN_WIDTH - (HEART_SIZE+1)*MAX_HEARTS, 0)

        # balas
        for bullet in bullets:
            pyxel.rect(bullet["x"], bullet["y"], 2, 2, pyxel.COLOR_YELLOW)

        # placar
        score = players_state.get("score", {})
        pyxel.text(4, 9, f"P1: {score.get('1',0)}", pyxel.COLOR_WHITE)
        pyxel.text((SCREEN_WIDTH - 28) // 2 + 52, 9, f"P2: {score.get('2',0)}", pyxel.COLOR_WHITE)

    def draw_waiting(self):
        pyxel.text((SCREEN_WIDTH - 68)//2, (SCREEN_HEIGHT - 6)//2, "WAITING PLAYER...", pyxel.frame_count % 16)
        
    def draw_countdown(self):
        countdown = players_state.get("countdown", 0)

        if countdown > 0:
            pyxel.text((SCREEN_WIDTH - 4)//2, (SCREEN_HEIGHT - 6)//2, str(countdown), pyxel.frame_count % 16)
        else:
            pyxel.text((SCREEN_WIDTH - 24)//2, (SCREEN_HEIGHT - 6)//2, "FIGHT!", pyxel.frame_count % 16)
            
    def draw_game_over(self):
        winner = players_state.get("winner")
        ready = players_state.get("ready", {})

        pyxel.text((SCREEN_WIDTH - 52)//2, SCREEN_HEIGHT//3, f"PLAYER {winner} WINS", pyxel.frame_count % 16)

        p1 = "READY" if ready.get("1") else "WAIT"
        p2 = "READY" if ready.get("2") else "WAIT"

        color1 = pyxel.frame_count % 16 if p1 == "READY" else pyxel.COLOR_WHITE
        color2 = pyxel.frame_count % 16 if p2 == "READY" else pyxel.COLOR_WHITE

        pyxel.text((SCREEN_WIDTH - 36) // 2 - 25, 60, f"P1: {p1}", color1)
        pyxel.text((SCREEN_WIDTH - 36) // 2 + 25, 60, f"P2: {p2}", color2)

        pyxel.text((SCREEN_WIDTH - 72)//2, 50, "ENTER - PLAY AGAIN", pyxel.COLOR_WHITE)
        pyxel.text((SCREEN_WIDTH - 32)//2, 70, "Q - QUIT", pyxel.COLOR_WHITE)

if __name__ == "__main__":
    SpaceDuelClient()