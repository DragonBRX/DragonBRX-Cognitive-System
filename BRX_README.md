# BRX Ecosystem — Dragon Projects BR

O **BRX** é um ecossistema de linguagens de programação projetado para ser **totalmente autossuficiente**. Ele é composto por sete camadas especializadas, cada uma resolvendo uma parte específica do desenvolvimento.

## 🏗️ As Sete Camadas

| Sigla | Camada | Função | Status no Bootstrap |
| :--- | :--- | :--- | :--- |
| **BRXE** | Easy | Lógica de alto nível (Python-like) | **Funcional** |
| **BRXV** | Visual | Interface gráfica e jogos (Tkinter) | **Funcional** |
| **BRXR** | Runtime | Loop de execução em tempo real | **Funcional** |
| **BRXB** | Binary | Geração de executáveis finais | Planejado |
| **BRXH** | Hardware | Acesso direto ao processador | Planejado |
| **BRXS** | Sandbox | Execução isolada e segura | Planejado |
| **BRXT** | Translate | Tradução de binários externos | Planejado |

## 🛠️ Como usar (Fase de Bootstrap)

Atualmente, o interpretador unificado está em `src/interpreter.py`.

### Rodando um exemplo visual:
```bash
python3 src/interpreter.py examples/animacao.brx
```

### Exemplo de Sintaxe (BRXV + BRXR):
```brx
run "meu_app"

win
  sz 800x600
  tt "Janela BRX"
  spr "logo.png" x:100 y:100
    vel x:2 y:0
  end
end

loop while win.open
  upd
  drw
  wait 16
end
```

## 📄 Licença
Este projeto está sob a licença **MIT**.
