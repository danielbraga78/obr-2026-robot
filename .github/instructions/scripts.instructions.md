---
applyTo: "**/*.sh,**/*.bash,**/*.zsh,**/*.fish,**/*.bat,**/*.cmd,**/*.ps1"
---
# Scripts e Automação

## Segurança

- Não use comandos destrutivos sem necessidade.
- Tenha cuidado com `rm`, `mv`, `dd`, redirecionamentos, substituição de arquivos e comandos executados como root.
- Não coloque segredos em argumentos, código, logs ou arquivos gerados.

## Portabilidade

- Identifique o shell-alvo antes de usar sintaxe específica.
- Não misture sintaxe Bash em scripts declarados como `sh` sem verificar compatibilidade.
- Não suponha que uma ferramenta exista; verifique o projeto e o ambiente quando necessário.

## Robustez

- Trate códigos de saída.
- Em Bash, use quoting adequado e considere `set -euo pipefail` somente quando compatível com o script e suas intenções.
- Valide argumentos e caminhos.
- Não confie em parsing frágil de saída humana quando houver uma interface estruturada.

## Automação

Uma automação só está pronta quando o fluxo completo foi validado. Não declare sucesso porque apenas uma etapa do script executou.
