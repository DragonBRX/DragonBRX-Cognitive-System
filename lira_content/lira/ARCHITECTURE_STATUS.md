# Estado da Arquitetura Lira

O conceito original do Lira combina o melhor de varias linguagens:

- Rust para core seguro, mmap e controle fino de memoria;
- C++/CUDA para tensores e numerica pesada;
- Go para sincronizacao, rede e processos longos;
- Python para orquestracao, injecao de conhecimento, schema e testes;
- Node/PowerShell para instalador e visualizador Windows.

## O que esta ativo nesta versao

Esta build funciona sem instalar Rust, C++/CUDA ou Go.

Implementado agora:

- container binario `.lira`;
- slots de metadata com integridade;
- tensores base e modulos DELTA/LORA;
- protocolo LKIF;
- compilador de conhecimento associativo;
- payload compilado hidratavel;
- exportacao/importacao JSONL;
- viewer Windows que traduz o binario em categorias, conhecimento, modulos e metadata;
- instalador `.exe` com associacao de arquivo e icone proprio.

## O que fica como evolucao futura

As camadas Rust, C++/CUDA e Go continuam validas como arquitetura alvo para uma versao mais forte
do runtime. Elas nao sao obrigatorias para a build atual porque o formato ja esta funcional com
Python + Node/PowerShell.

Essa decisao mantem o Lira utilizavel agora e deixa o caminho aberto para trocar componentes por
implementacoes nativas mais rapidas depois, sem mudar o conceito do formato.
