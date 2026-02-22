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
import time


# Configuração do Cliente

SERVER_HOST = "" # Endereço IP do servidor
SERVER_PORT = 5000       # Porta do servidor

SCREEN_WIDTH = 160 # Largura da tela
SCREEN_HEIGHT = 120 # Altura da tela 
PLAYER_SIZE = 8 # Tamanho do jogador (largura e altura)

HEART_SIZE = 8      # largura e altura do coração no banco de imagens
MAX_HEARTS = 5      # número total de corações por jogador
HEART_HP = 20       # cada coração representa 20 HP

# Estado global (renderização)

player_id = None # ID do jogador, atribuído pelo servidor após conexão
players_state ={} # estado dos jogadores, balas, bônus e outras informações do jogo, atualizado a cada mensagem do servidor

lock = threading.Lock()

disconnect_reason = None 

server_disconnected = False

# Classe para gerenciar o background animado de estrelas, criando um efeito visual de movimento no espaço
class Background:
    # Inicializa o background com um número definido de estrelas em posições aleatórias dentro dos limites da tela
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

    # Atualiza a posição das estrelas, movendo-as para baixo e reiniciando no topo quando saem da tela, criando um efeito de movimento contínuo
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

    # Desenha as estrelas na tela usando a função pset do Pyxel, que define um pixel na posição (x, y) com a cor ciana, criando o efeito visual do fundo estrelado
    def draw(self):
        # Desenha todas as estrelas
        for x, y in self.stars:
            pyxel.pset(x, y, pyxel.COLOR_CYAN) # Desenha a estrela na cor ciana na posição (x, y)

class SpaceDuelClient:
    # Inicializa o cliente, conecta ao servidor, inicia a thread de escuta e configura o Pyxel para renderização
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

        # inicializa o audio
        self.init_audio()

        self.last_move_time = 0
        self.move_interval = 0.05  # 50ms (20 movimentos por segundo)
        pyxel.run(self.update, self.draw)

    # Configura os sons e músicas do jogo, definindo os efeitos sonoros para tiros, hits e música de fundo, e inicia a reprodução da música de fundo em loop
    def init_audio(self):
        pyxel.sounds[0].set("c3e3g3c4a3a2c1a1","t","2","n",25)
        pyxel.musics[0].set([0],[],[],[])

        pyxel.sounds[1].set("a2a1c0a0", "p", "5", "s", 5)
        pyxel.sounds[2].set("f4c4","n","5","n",12)

        pyxel.playm(0, loop=True)

    # Desenha os jogadores na tela, aplicando efeitos visuais para indicar quando um jogador está com o bônus de tiro ativo ou quando foi atingido, usando sprites diferentes para cada estado e um efeito pulsante para o bônus
    def draw_players(self, players):

        for pid, player in players.items():
            x, y = player["x"], player["y"]

            hit_timer = player.get("hit_timer", 0)
            power = player.get("power", False)

            if power:
                # efeito pulsante
                pulse = 5 + (pyxel.frame_count % 4)  # varia raio

                # efeito piscando
                if pyxel.frame_count % 6 < 3:
                    pyxel.circ(x + 4, y + 4, pulse, pyxel.COLOR_YELLOW)

            # Feedback de dano
            if int(pid) == 1:
                if hit_timer > 0:
                    pyxel.blt(x, y, 0, 16, 0, 8, 8, 0)
                    pyxel.play(2, 2)  # canal 2, som de hit
                else:
                    pyxel.blt(x, y, 0, 0, 0, 8, 8, 0)
            else:
                if hit_timer > 0:
                    pyxel.blt(x, y, 0, 24, 0, 8, 8, 0)
                    pyxel.play(2, 2)  # canal 2, som de hit
                else:
                    pyxel.blt(x, y, 0, 8, 0, 8, 8, 0)
    
    # Desenha os corações de vida dos jogadores, mostrando corações cheios, meio cheios ou vazios de acordo com o HP restante, e posicionando os corações no topo da tela para cada jogador
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

    # Escuta mensagens do servidor em uma thread separada, processando mensagens de atribuição de ID, atualização de estado do jogo e notificações de desconexão, e atualizando o estado global do cliente de acordo com as informações recebidas
    def listen_server(self):
        """Escuta mensagens do servidor"""

        global player_id, players_state
        buffer = ""

        while True:
            try:
                data = self.sock.recv(1024)
                if not data:
                    print("Desconectado do servidor")
                    global server_disconnected
                    server_disconnected = True
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
                    server_disconnected = True
                    break
    
    # Envia comando de movimento ao servidor, construindo uma mensagem JSON com o tipo de movimento e a direção, e enviando-a através do socket para o servidor processar
    def send_move(self, direction):
        """Envia comando de movimento ao servidor"""

        message = {
            "type": MSG_MOVE,
            "direction": direction
        }

        self.sock.sendall((json.dumps(message) + "\n").encode("utf-8"))

    # Envia comando de atirar ao servidor, construindo uma mensagem JSON com o tipo de ação de tiro e enviando-a através do socket para o servidor processar
    def send_shoot(self):
        """Envia comando de atirar ao servidor"""

        message = {
            "type": MSG_SHOOT
        }

        self.sock.sendall((json.dumps(message) + "\n").encode("utf-8"))

    # Captura input do teclado, gerenciando o tempo entre movimentos para evitar excesso de comandos, e enviando comandos de movimento ou tiro ao servidor conforme as teclas pressionadas, além de lidar com estados de jogo como espera por jogadores, contagem regressiva e fim de jogo
    def update(self):
        """Captura input do teclado"""

        # Se o servidor estiver cair, fecha o jogo
        global server_disconnected
        if server_disconnected:
            pyxel.quit()
            return

        # Se o servidor estiver cheio, informa e aguarda apertar Q para sair
        global disconnect_reason
        if disconnect_reason:
            if pyxel.btnp(pyxel.KEY_Q):
                pyxel.quit()
            return

        game_over = players_state.get("game_over", False)

        # Se o jogo acabou, aguarda apertar ENTER para reiniciar
        if game_over:
            if pyxel.btnp(pyxel.KEY_RETURN):
                pyxel.play(1, 1)
                self.sock.sendall((json.dumps({"type": MSG_READY})+"\n").encode("utf-8"))
            elif pyxel.btnp(pyxel.KEY_Q):
                pyxel.play(2, 2)
                pyxel.quit()
            return
        # Se estiver esperando por jogadores, aguarda apertar Q para sair
        phase = players_state.get("phase", "WAITING")
        if phase == "WAITING":
            if pyxel.btnp(pyxel.KEY_Q):
                pyxel.play(2, 2)
                pyxel.quit()


        current_time = time.time()
        
        # Gerencia o tempo entre movimentos para evitar enviar comandos de movimento muito rapidamente
        if current_time - self.last_move_time > self.move_interval:

            if pyxel.btn(pyxel.KEY_UP):
                self.send_move("up")
                self.last_move_time = current_time

            elif pyxel.btn(pyxel.KEY_DOWN):
                self.send_move("down")
                self.last_move_time = current_time

            elif pyxel.btn(pyxel.KEY_LEFT):
                self.send_move("left")
                self.last_move_time = current_time

            elif pyxel.btn(pyxel.KEY_RIGHT):
                self.send_move("right")
                self.last_move_time = current_time
    
        if pyxel.btnp(pyxel.KEY_SPACE):
            self.send_shoot()
            pyxel.play(1, 1)

        # Atualiza o background
        self.background.update()

    # Renderiza o estado do jogo, desenhando o background, os jogadores, balas, bônus e informações de HUD como vida e placar, e mostrando mensagens específicas para estados como espera por jogadores, contagem regressiva e fim de jogo, além de lidar com a exibição de mensagens de desconexão do servidor      
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

    # Desenha o estado de jogo ativo, incluindo jogadores, balas, bônus, vida e placar, aplicando efeitos visuais para indicar estados como bônus ativo e dano recebido, e mostrando as informações de vida e placar de forma clara para os jogadores
    def draw_playing(self):
        players = players_state.get("players", {})
        bullets = players_state.get("bullets", [])
        bonus = players_state.get("bonus", None)
        bonus_end_time = players_state.get("bonus_end_time")


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

        # bonus
        if bonus is not None:
            bonus_type = bonus.get("type")
            bonus_end_time = players_state.get("bonus_end_time")

            current_time = time.time()
            time_left = bonus_end_time - current_time if bonus_end_time else 0

            # ---------------------------
            # BONUS DE TIRO (power)
            # ---------------------------
            if bonus_type == "power":

                radius = 3 + (pyxel.frame_count % 3)

                if time_left <= 1:
                    if pyxel.frame_count % 4 < 2:
                        pyxel.circ(bonus["x"], bonus["y"], radius, pyxel.COLOR_RED)
                else:
                    pyxel.circ(bonus["x"], bonus["y"], radius, pyxel.COLOR_LIME)

            # ---------------------------
            # BONUS DE VIDA (coração)
            # ---------------------------
            elif bonus_type == "health":
                pyxel.blt(bonus["x"] - 4, bonus["y"] - 4, 0, 0, 8, 8, 8, 0)

        # placar
        score = players_state.get("score", {})
        pyxel.text(4, 9, f"P1: {score.get('1',0)}", pyxel.COLOR_WHITE)
        pyxel.text((SCREEN_WIDTH - 28) // 2 + 52, 9, f"P2: {score.get('2',0)}", pyxel.COLOR_WHITE)

    # Desenha a tela de espera por jogadores, mostrando uma mensagem centralizada e piscante para indicar que o cliente está aguardando outro jogador se conectar, e instruções para sair do jogo
    def draw_waiting(self):
        pyxel.text((SCREEN_WIDTH - 68)//2, (SCREEN_HEIGHT - 6)//2, "WAITING PLAYER...", pyxel.frame_count % 16)
        pyxel.text((SCREEN_WIDTH - 32)//2, (SCREEN_HEIGHT - 6)//2 + 10, "Q - QUIT", pyxel.COLOR_WHITE)
    
    # Desenha a contagem regressiva antes do início da partida, mostrando os números da contagem ou a mensagem "FIGHT!" de forma centralizada e piscante para indicar o início iminente da partida
    def draw_countdown(self):
        countdown = players_state.get("countdown", 0)

        if countdown > 0:
            pyxel.text((SCREEN_WIDTH - 4)//2, (SCREEN_HEIGHT - 6)//2, str(countdown), pyxel.frame_count % 16)
        else:
            pyxel.text((SCREEN_WIDTH - 24)//2, (SCREEN_HEIGHT - 6)//2, "FIGHT!", pyxel.frame_count % 16)
    
    # Desenha a tela de fim de jogo, mostrando o vencedor, o placar final, o status de pronto para nova partida de cada jogador e instruções para reiniciar ou sair, com efeitos visuais para destacar o vencedor e os jogadores prontos
    def draw_game_over(self):
        winner = players_state.get("winner")
        ready = players_state.get("ready", {})
        score = players_state.get("score", {})

        # posição base vertical
        base_y = SCREEN_HEIGHT // 3

        # ---- Título ----
        pyxel.text((SCREEN_WIDTH - 52)//2,base_y, f"PLAYER {winner} WINS",pyxel.frame_count % 16)

        # ---- Placar ----
        pyxel.text((SCREEN_WIDTH - 60)//2, base_y + 20 ,f"P1: {score.get('1',0)}  x  p2: {score.get('2',0)}",pyxel.COLOR_WHITE)

        p1 = "READY" if ready.get("1") else "WAIT"
        p2 = "READY" if ready.get("2") else "WAIT"

        color1 = pyxel.frame_count % 16 if p1 == "READY" else pyxel.COLOR_WHITE
        color2 = pyxel.frame_count % 16 if p2 == "READY" else pyxel.COLOR_WHITE

        pyxel.text((SCREEN_WIDTH - 36) // 2 - 25, base_y + 40, f"P1: {p1}", color1)
        pyxel.text((SCREEN_WIDTH - 36) // 2 + 25, base_y + 40, f"P2: {p2}", color2)

        pyxel.text((SCREEN_WIDTH - 72)//2, base_y + 50, "ENTER - PLAY AGAIN", pyxel.COLOR_WHITE)
        pyxel.text((SCREEN_WIDTH - 32)//2, base_y + 60, "Q - QUIT", pyxel.COLOR_WHITE)

if __name__ == "__main__":
    SpaceDuelClient()