# BRX — Linguagem de Programação

O **BRX** é um ecossistema de linguagens de programação projetado para ser **totalmente autossuficiente** e nativo. Este repositório contém a implementação do compilador/interpretador de bootstrap para a linguagem BRX, focando nas especificações técnicas da v1.0.

## 🚀 Filosofia

- **Autossuficiência:** Não depende de ferramentas externas para rodar em produção.
- **Sintaxe Universal:** Abreviações curtas e intuitivas (`var`, `if`, `loop`, `win`).
- **Nativo:** O formato `.brx` é tratado como um executável nativo pelo sistema operacional.

## 🏗️ Estrutura do Projeto

- `src/`: Código-fonte do interpretador (Lexer, Parser, Interpreter).
- `examples/`: Exemplos de código seguindo a especificação oficial.
- `SPEC.md`: Especificação técnica completa da linguagem.

## 🛠️ Como usar (Bootstrap Python)

Atualmente, o interpretador está em fase de bootstrap usando Python 3.

### Executando um programa
```bash
python3 src/interpreter.py examples/hello.brx
```

### Exemplo de Código (`hello.brx`)
```brx
run "hello"

var nome:txt = "Dragon"
out "Olá, " + nome

loop i:1 to 5
    out i
end
```

## 📄 Licença
Este projeto está sob a licença **MIT**.
