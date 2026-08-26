---
name: implement
description: Implementa uma tarefa ponta a ponta com inspeção, integração, testes e validação antes de declarar conclusão.
argument-hint: Descreva exatamente a funcionalidade ou alteração desejada.
agent: agent
---
# /implement — Implementação ponta a ponta

Implemente a solicitação como uma mudança real no projeto, não como um exemplo isolado.

## Fase 1 — Entendimento

Antes de editar:

- analise a árvore do projeto;
- localize arquivos relevantes;
- leia o código existente relacionado;
- identifique padrões, APIs, configurações e testes existentes;
- transforme a solicitação em critérios de aceitação verificáveis;
- identifique riscos de regressão.

Não invente informações que podem ser descobertas no repositório.

## Fase 2 — Planejamento técnico

Defina mentalmente:

- onde a mudança deve ocorrer;
- quais componentes precisam ser alterados;
- quais componentes devem permanecer intactos;
- como a funcionalidade será validada.

Prefira a menor mudança correta e preserve a arquitetura existente.

## Fase 3 — Implementação

Implemente todos os critérios solicitados.

Não substitua uma parte difícil por uma versão aproximada sem avisar.
Não remova requisitos para reduzir o trabalho.
Não altere testes apenas para mascarar uma implementação incorreta.

## Fase 4 — Verificação

Depois de editar:

- formatter;
- lint/static analysis;
- testes relevantes;
- build/compilação;
- reprodução manual, se necessário.

Use apenas resultados realmente obtidos.

## Fase 5 — Revisão adversarial

Revise a implementação procurando:

- bugs lógicos;
- condições invertidas;
- caminhos de erro;
- estados inválidos;
- problemas de inicialização;
- incompatibilidades;
- regressões;
- efeitos colaterais inesperados.

Pergunte internamente: "Como esta implementação pode estar errada?"

Corrija as falhas encontradas e repita a validação.

## Conclusão

Só use CONCLUÍDO E VERIFICADO quando todos os requisitos relevantes e verificações disponíveis sustentarem essa conclusão.

Caso contrário, informe claramente a limitação e escolha o status correto.

A resposta final deve conter:

### Alterações realizadas
### Verificações executadas
### Resultados
### Limitações
### Status
