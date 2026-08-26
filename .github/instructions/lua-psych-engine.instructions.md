---
applyTo: "**/*.lua"
---
# Lua / Psych Engine

Estas regras complementam as instruções globais quando o arquivo é Lua, especialmente scripts de Friday Night Funkin' / Psych Engine.

## Contexto e compatibilidade

- Descubra primeiro a versão real do Psych Engine usada pelo projeto antes de assumir APIs.
- Não presuma que uma função, callback, objeto ou evento existe só porque aparece em exemplos de outra versão.
- Procure usos existentes no projeto antes de introduzir uma API nova.
- Preserve convenções do mod e do engine já existentes.

## Callbacks e ciclo de vida

- Verifique o momento correto para criar objetos, registrar callbacks, responder a eventos e destruir recursos.
- Não mova código para outro callback sem verificar como isso altera ordem de execução.
- Evite inicializações repetidas em callbacks executados a cada frame.
- Se algo depende de um objeto criado em outro callback, confirme que o objeto existe antes do primeiro uso.

## Input e lógica de jogo

- Trate teclado, mouse, toque e controles virtuais de forma explícita.
- Verifique o sistema de câmera correto quando calcular coordenadas de HUD/world.
- Não assuma resolução fixa sem verificar como o projeto trata escalonamento.
- Ao corrigir uma condição de input, teste também estado de pressionado, liberado e repetição, quando aplicável.

## Sprites e animações

- Confirme nomes de animações, atlas/prefixos e câmera do objeto no código ou assets existentes.
- Não declare que uma animação foi corrigida apenas porque o sprite foi criado.
- Verifique posição, escala, câmera, ordem de desenho e condição que dispara cada animação.

## Lua e erros

- Não esconda erros com `pcall`/tratamento genérico sem investigar a causa.
- Verifique nil antes de usar referências cuja criação dependa de ordem de execução.
- Prefira condições simples e legíveis; evite alterar a lógica de uma condição apenas para satisfazer um caso de teste isolado.

## Verificação

Para bugs de gameplay, input, câmera ou UI, considere que um teste textual/Lua pode não ser suficiente. Se o ambiente não permitir iniciar o engine e reproduzir o comportamento, informe isso explicitamente.
