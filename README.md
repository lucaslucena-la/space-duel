# Space Duel — Jogo Multiplayer em Rede

Projeto desenvolvido para a disciplina de Redes de Computadores.

## 🎮 Descrição
Space Duel é um jogo multiplayer em tempo real onde dois jogadores controlam naves espaciais.
A comunicação é feita via sockets TCP no modelo cliente-servidor.

## 🧠 Arquitetura
- Cliente–Servidor
- Servidor autoritário
- Comunicação via sockets (TCP)
- Mensagens em JSON

## 🛠️ Tecnologias
- Python 3
- socket
- threading
- pyxel (nas próximas etapas)

## ▶️ Execução

### Servidor
```bash
python -m server.server
```

### Cliente
```bash
python -m server.server
```

## 📌 Status do Projeto

### ✔ Passo 1 — Conexão de Rede
- Servidor TCP
- Conexão de dois clientes
- Identificação dos jogadores

### ✔ Passo 2 — Estado Compartilhado
- Servidor autoritário
- Estado global do jogo
- Movimento sincronizado em tempo real
- Comunicação via JSON sobre TCP

⬜ Passo 3 — Interface Gráfica (Pyxel)
⬜ Passo 4 — Tiros e colisões
