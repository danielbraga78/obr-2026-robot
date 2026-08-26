---
name: debug
description: Investiga e corrige bugs com diagnóstico baseado em evidências, sem pseudo-soluções.
argument-hint: Descreva o problema, erro, comportamento observado ou reprodução.
agent: agent
---
# /debug — Diagnóstico rigoroso

Investigue o problema descrito pelo usuário com prioridade máxima para evidência e causa raiz.

## Antes de alterar código

1. Inspecione a estrutura do projeto.
2. Encontre os arquivos e componentes relevantes.
3. Leia a implementação e rastreie o fluxo afetado.
4. Procure usos, callbacks, dependências e configurações relacionados.
5. Procure implementações semelhantes.
6. Tente reproduzir o problema ou encontre evidência equivalente disponível no ambiente.

## Diagnóstico

Não faça alterações aleatórias.

Formule uma hipótese explícita sobre a causa e encontre evidências a favor ou contra ela. Diferencie causa, sintoma, efeito colateral e hipótese.

Se o problema tiver múltiplas causas plausíveis, investigue as mais prováveis antes de escolher uma correção.

## Correção

Depois de identificar a causa, faça a menor alteração que a corrija de forma adequada à arquitetura existente.

Não use como substitutos de diagnóstico:

- delays arbitrários;
- ignorar exceções;
- desativar validações;
- valores mágicos;
- retornar sucesso artificialmente;
- alterar testes para fazê-los passar.

## Verificação

Depois da alteração:

1. execute a reprodução original;
2. execute testes relevantes;
3. execute build/lint/formatter quando aplicável;
4. procure regressões no fluxo relacionado;
5. releia o diff tentando encontrar uma forma de a correção estar errada.

## Resposta final

Informe obrigatoriamente:

- sintoma observado;
- causa identificada;
- arquivos alterados;
- correção aplicada;
- verificações executadas;
- resultados reais;
- o que não pôde ser testado;
- status em uma destas categorias: CONCLUÍDO E VERIFICADO / IMPLEMENTADO, MAS NÃO COMPLETAMENTE VERIFICADO / PARCIALMENTE IMPLEMENTADO / BLOQUEADO.

Nunca diga que o bug foi resolvido se ele não foi efetivamente validado ou se existe uma limitação que impede confirmar isso.
