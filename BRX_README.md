# Ecossistema BRX — Dragon Projects BR

O **BRX** é um ecossistema de linguagens de programação e ferramentas de execução projetado para ser **totalmente autossuficiente** e nativo. Ele substitui a dependência de runtimes e compiladores externos por uma arquitetura integrada de sete camadas especializadas.

## 🚀 Filosofia do Projeto

1.  **Autossuficiência Total:** O BRX não depende de ferramentas externas (Python, Node.js, GCC, etc.) para rodar em produção.
2.  **Nacionalidade Digital:** O formato `.brx` é registrado no Sistema Operacional como um executável nativo.
3.  **Sintaxe Universal:** Abreviações curtas e intuitivas (`var`, `if`, `loop`, `win`) independentes de idioma humano.
4.  **Interoperabilidade sem Dependência:** Pode integrar com outras linguagens, mas nunca *precisa* delas para funcionar.

## 🏗️ As Sete Camadas

| Sigla | Camada | Função | Substitui hoje |
| :--- | :--- | :--- | :--- |
| **BRXE** | Easy | Sintaxe simples de alto nível | Python, Ruby |
| **BRXV** | Visual | Janelas, UI, apps gráficos | Qt, Electron, GTK |
| **BRXR** | Runtime | Execução em tempo real | JVM, Node.js, CPython |
| **BRXB** | Binary | Geração do executável final | GCC, Clang, linkers |
| **BRXH** | Hardware | Acesso direto ao processador | Assembly, Drivers |
| **BRXS** | Sandbox | Execução isolada e segura | Containers, VMs |
| **BRXT** | Translate | Tradução de binários externos | Proton, Wine |

## 🛠️ Como testar (Fase de Bootstrap)

Atualmente, o projeto está em fase de **bootstrap**. Isso significa que utilizamos ferramentas temporárias (como Python) para construir os primeiros compiladores que, futuramente, serão reescritos em BRX.

### Requisitos
- Python 3.x (apenas para a fase de bootstrap)
- VS Code (recomendado)

### Executando um arquivo .brx
Para rodar um exemplo da camada BRXE:
```bash
python3 brxe/brxe_interpreter.py exemplos/ola_mundo.brx
```

## 📄 Licença
Este projeto está sob a licença **MIT**. Veja o arquivo `LICENSE` para detalhes.

## 💻 Integração com VS Code

Para facilitar o desenvolvimento no VS Code:
1. Abra a pasta do projeto no VS Code.
2. Para rodar um arquivo `.brx` ou `.brxe`:
   - Pressione `Ctrl+Shift+B` (ou `Cmd+Shift+B` no Mac).
   - Selecione **BRX: Rodar Arquivo Atual**.
3. O resultado aparecerá no terminal integrado.

> **Nota:** O reconhecimento de sintaxe completo via extensão oficial está em desenvolvimento. Por enquanto, o VS Code usará as configurações básicas incluídas na pasta `.vscode`.
