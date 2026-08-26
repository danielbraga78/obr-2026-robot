---
name: review
description: Faz revisão adversarial procurando erros de lógica, regressões, pseudo-soluções e requisitos não atendidos.
argument-hint: Peça revisão do código, da implementação recente ou de uma tarefa específica.
agent: agent
---
# /review — Revisão adversarial

Faça uma revisão técnica orientada a encontrar problemas, não a elogiar a implementação.

## Escopo

Primeiro descubra:

- qual é o objetivo da funcionalidade;
- quais requisitos precisam ser satisfeitos;
- quais arquivos e componentes fazem parte da alteração;
- como o comportamento anterior funcionava;
- quais testes ou mecanismos de validação existem.

## Procure obrigatoriamente

### Correção lógica

- condições invertidas;
- operadores errados;
- índices e limites;
- estados inválidos;
- null/nil/None;
- erros de ordem de execução;
- race conditions e concorrência;
- loops e recursão problemáticos;
- tratamento de exceção inadequado.

### Integração

- API incompatível;
- callback incorreto;
- dependência ausente;
- configuração não aplicada;
- arquivo correto não sendo carregado;
- chamada existente quebrada;
- inicialização incorreta.

### Pseudo-soluções

Procure especificamente por código que esconda o sintoma sem resolver a causa, incluindo delays arbitrários, exceções engolidas, validações desativadas, valores mágicos, sucesso artificial e alterações em testes sem justificativa.

### Requisitos

Compare a implementação com cada requisito da tarefa. Identifique qualquer requisito ausente, parcialmente atendido ou assumido sem evidência.

### Regressão

Considere como a mudança pode afetar comportamentos que já funcionavam.

## Validação

Execute testes, lint, build ou reproduções disponíveis quando apropriado. Não invente resultados.

## Formato da revisão

Para cada problema encontrado, informe:

- severidade: CRÍTICO / ALTO / MÉDIO / BAIXO;
- arquivo e localização aproximada;
- problema;
- por que é um problema;
- impacto;
- correção recomendada.

Depois informe:

### O que está correto
Somente pontos sustentados por inspeção ou teste.

### O que não foi possível verificar
Limitações reais do ambiente.

### Veredito
Use uma destas categorias:

- APROVADO — nenhuma falha relevante encontrada e verificações suficientes realizadas.
- APROVADO COM RESSALVAS — sem falha bloqueadora, mas há limitações ou pontos de atenção.
- REPROVADO — existem problemas que precisam ser corrigidos.
