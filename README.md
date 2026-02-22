# Space Duel — Jogo Multiplayer em Rede

Projeto desenvolvido para a disciplina de Redes de Computadores.

O Space Duel é um jogo multiplayer em tempo real onde dois jogadores controlam naves espaciais que se movem e atiram entre si. A comunicação ocorre via **sockets TCP**, utilizando o modelo **cliente–servidor**, com o servidor atuando como **autoridade central do jogo**.


## 🎮 Descrição do Jogo

- Dois jogadores conectados simultaneamente
- Cada jogador controla uma nave
- As naves podem:
  - se mover continuamente ao segurar as teclas direcionais (↑ ↓ ← →)
  - atirar projéteis (barra de espaço)
- O servidor:
  - mantém o estado global do jogo
  - simula balas
  - detecta colisões
  - controla vida (HP)
- Todos os eventos são sincronizados em tempo real entre os clientes

## 🧠 Arquitetura

### Modelo Cliente–Servidor
- **Servidor autoritário**
  - Mantém o estado global do jogo
  - Processa eventos (`move`, `shoot`)
  - Atualiza física, colisões e vida
- **Clientes finos**
  - Capturam entradas do usuário
  - Enviam eventos ao servidor
  - Apenas renderizam o estado recebido

### Comunicação
- Protocolo: **TCP**
- Mensagens: **JSON**
- Delimitador de mensagens: `\n`
- Concorrência no servidor via `threading`

## 🛠️ Tecnologias
- **Python 3**
  - `socket`
  - `threading`
  - `json`
- **Pyxel** (renderização gráfica)

## 📁 Estrutura do Projeto

```text
game-multiplayer
 ┣ 📂 server
 ┃ ┣ 📜 __init__.py
 ┃ ┗ 📜 server.py
 ┣ 📂 client
 ┃ ┣ 📜 __init__.py
 ┃ ┗ 📜 client.py
 ┣ 📜 protocol.py
 ┣ 📜 README.md
 ┗ 📜 .gitignore
```

## ▶️ Execução

### Servidor
```bash
python -m server.server
```
### Cliente
**Iniciar dois clientes (em terminais diferentes)**
```bash
python -m client.client
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

### ✔ Tiros e Colisão
- Evento de disparo (shoot)
- Balas simuladas no servidor
- Detecção de colisão
- Sistema de vida (HP)
- Estado sincronizado entre clientes

# 🚧 Próximos Passos - Space Duel

## 🟩 Efeitos Visuais e Sons

### Objetivo
Adicionar feedback sensorial às ações do jogo.

### Funcionalidades
- Som de tiro
- Som de impacto
- Feedback visual ao receber dano
- Pequenas animações (explosão simples)