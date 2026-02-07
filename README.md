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

### ✔ Conexão de Rede
- Servidor TCP
- Conexão de dois clientes
- Identificação dos jogadores

### ✔ Estado Compartilhado
- Servidor autoritário
- Estado global do jogo
- Movimento sincronizado em tempo real
- Comunicação via JSON sobre TCP

### ✔ Interface Gráfica (Pyxel)
- Integração com Pyxel
- Renderização das naves
- Controle por teclado
- Estado sincronizado em tempo real
- Cliente fino (apenas renderiza e envia eventos)
⬜ Passo 4 — Tiros e colisões
