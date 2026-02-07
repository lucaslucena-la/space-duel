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
from protocol import MSG_ASSIGN_ID, MSG_DISCONNECT, MSG_STATE, MSG_MOVE

# Configuração do Cliente

SERVER_HOST = "127.0.0.1" # Endereço IP do servidor
SERVER_PORT = 5000       # Porta do servidor

SCREEN_WIDTH = 160
SCREEN_HEIGHT = 120
SHIP_SIZE = 6

# Estado global (renderização)

player_id = None
players_state ={}

lock = threading.Lock()

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
        pyxel.run(self.update, self.draw)

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
                            players_state = message["players"]
                            
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

    def update(self):
        """Captura input do teclado"""
        if pyxel.btnp(pyxel.KEY_UP):
            self.send_move("up")
        elif pyxel.btnp(pyxel.KEY_DOWN):
            self.send_move("down")
        elif pyxel.btnp(pyxel.KEY_LEFT):
            self.send_move("left")
        elif pyxel.btnp(pyxel.KEY_RIGHT):
            self.send_move("right")
                
    def draw(self):
        """Renderiza o jogo."""
        pyxel.cls(0)

        with lock:
            for pid, player in players_state.items():
                x = player["x"]
                y = player["y"]

                # Cor diferente para o próprio jogador
                color = 11 if player_id is not None and int(pid) == player_id else 8

                pyxel.rect(x, y, SHIP_SIZE, SHIP_SIZE, color)

if __name__ == "__main__":
    SpaceDuelClient()