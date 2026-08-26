# Diagnostico do controle de linha

## Arquitetura encontrada

O projeto nao usa uma matriz de sensores digitais de linha. O sensor de linha
e a camera do Raspberry Pi:

1. `CameraManager` captura e, quando `CAMERA_INVERTED=True`, gira o quadro 180 graus.
2. `VisionPipeline` recorta a ROI inferior (`y=0.55..1.0`) e a reduz sem deformar.
3. `LineDetector` cria uma mascara adaptativa, escolhe o maior contorno e calcula
   `error = near_x - largura/2`. O erro e negativo quando a linha esta a esquerda
   e positivo quando esta a direita.
4. `FollowLineState` normaliza o erro, filtra-o, aplica PID e envia
   `MOVE,velocidade,0,wz`.
5. `normalize_motor_command` aplica a zona morta e a matriz de rodas prevista.
6. O Arduino recebe o ultimo comando valido e calcula as quatro rodas.

O sensor ultrassonico nao entra no calculo do erro da linha. Ele pode, contudo,
interromper o seguimento ao ativar `AVOID_OBSTACLE`; isso e uma decisao de
estrategia, nao uma correcao de linha.

## Causa encontrada

Foram encontradas duas divergencias objetivas:

- O firmware Mega e a variante PCB usavam uma matriz diferente da matriz do
  firmware legado e do Raspberry. Com `MOVE,180,0,0`, o Mega antigo produzia
  `(+180,-180,-180,+180)`, enquanto a matriz esperada para avanco produzia
  `(+180,+180,+180,+180)`. O robô podia girar quando o controlador pedia reta.
- O quadro ja era girado em `camera.py`, mas `motion.py` invertia `vx` e `vy`
  novamente. Assim, a referencia visual e a referencia de movimento podiam
  ficar opostas.

Tambem havia riscos de instabilidade que nao foram mascarados:

- `LINE_ERROR_FILTER_ALPHA=0.35` privilegia o historico e atrasa a resposta.
- `PID_DERIVATIVE_FILTER_ALPHA=0.0` deixa a derivada sem filtragem; pequenas
  variacoes de centroide podem gerar mudancas bruscas em `wz`.
- A zona morta e alta (`110/255`). Uma roda abaixo de 110 e desligada no
  firmware; a funcao `fit_to_motor_deadband` precisa alterar o comando inteiro
  ou reduzir a translacao, criando descontinuidades perceptiveis perto do limite.
- A serial acumulava `MOVE` antigos em caso de escrita lenta ou reconexao.
  Agora apenas o `MOVE` mais recente fica pendente; `STOP`, heartbeat e eventos
  nao sao descartados.

## Tabela de estados da linha

Como nao ha sensores L/C/R, a tabela abaixo traduz as combinacoes discretas
solicitadas para estados equivalentes da deteccao visual. `wz > 0` e a
correcao positiva definida pelo software; a direcao fisica final ainda precisa
ser confirmada com um teste de bancada marcado no chassi.

| Estado equivalente | Ativos | Erro | Esperado | Codigo antes | Motores esperados |
|---|---|---:|---|---|---|
| Linha perdida | nenhum valido | ultimo erro | recuperar para o ultimo lado; apos 3 ciclos parar | recupera por `last_steering`, ou pivota pela ultima curva; depois `STOP` | manter avanco reduzido ou girar para o lado memorizado; nenhum apos timeout |
| So esquerda | faixa esquerda | negativo | corrigir para direita | `wz < 0` | reduzir/elevar diferencial conforme a matriz, sem inverter o sentido |
| So centro | faixa central | proximo de 0 | reta com pequena correcao | `wz ~= 0`, velocidade base | quatro rodas equivalentes para avanco |
| So direita | faixa direita | positivo | corrigir para esquerda | `wz > 0` | diferencial oposto ao caso esquerda |
| esquerda + centro | contorno deslocado a esquerda | negativo pequeno | curva suave para direita | `wz < 0`, filtrado | pequena diferenca entre rodas |
| centro + direita | contorno deslocado a direita | positivo pequeno | curva suave para esquerda | `wz > 0`, filtrado | pequena diferenca entre rodas |
| esquerda + direita, centro ausente | linha larga/curva ou mascara ambigua | indefinido | nao escolher lado arbitrario; validar contorno e recuperar | maior contorno; se rejeitado, recuperacao | ultimo sentido conhecido; nao ha sensor discreto para decidir |
| esquerda + centro + direita | linha larga/intersecao | depende do `near_x` e `heading` | reduzir velocidade e usar rumo | contorno `near_x`, antecipacao de curva | menor velocidade; giro proporcional |

Na implementacao corrigida, `motor1..4` seguem:

```text
motor1 = vx + vy + wz
motor2 = vx - vy - wz
motor3 = vx - vy + wz
motor4 = vx + vy - wz
```

Para `vy=0`, `wz=0`, os quatro recebem `vx`. Para um giro positivo, os
termos de giro aumentam os motores 1 e 3 e reduzem 2 e 4; o sentido fisico
deve ser validado observando o chassi, pois o codigo nao mede encoders.

## Alteracao realizada

- Alinhada a matriz nos firmwares `robot_mega` e `robot_mega_pcb` e no calculo
  equivalente do Raspberry.
- Removida a segunda inversao de `vx`/`vy`; a orientacao passa a ser aplicada
  uma unica vez na captura da camera.
- Comandos `MOVE` pendentes agora sao substituidos pelo mais recente.
- Adicionado log `DEBUG` por ciclo com centro, bandas near/far, erro em pixels,
  erro normalizado, heading, curva, steering e velocidade. O resumo existente
  tambem continua registrando a comunicacao a cada segundo em `INFO`.

Para habilitar os logs detalhados, execute com `ROBOT_LOG_LEVEL=DEBUG`. Para
desativar depois do teste, remova a variavel ou use `ROBOT_LOG_LEVEL=INFO`.

## O que ainda exige bancada

Nao e possivel determinar somente pelo codigo se cada conector esta realmente
na roda fisica indicada, nem se `wz > 0` produz giro para esquerda ou direita.
Com o robô suspenso, envie `MOVE,150,0,0` e depois comandos de giro com baixa
duracao, identificando cada roda e o sentido real. Se o sentido estiver
invertido, ajuste a polaridade do canal especifico no firmware, sem alterar
pinagem ou limiares de visao.

## Sequencia de validacao

| Teste | Resposta esperada |
|---|---|
| linha centralizada | `wz` proximo de zero; quatro rodas com velocidade equivalente |
| pequeno desvio esquerda | `wz` negativo pequeno; diferenca gradual entre rodas |
| pequeno desvio direita | `wz` positivo pequeno; diferenca gradual oposta |
| grande desvio esquerda/direita | `wz` cresce ate `MAX_STEER`, velocidade cai, sem inversao de lado |
| perda completa | ate 3 ciclos usa ultimo steering; depois para e entra em busca |
| recuperacao | retorna ao movimento quando chega uma deteccao valida, sem comando antigo |
| curva | `heading` antecipa, velocidade reduz e o sentido permanece consistente |
| transicao rapida | serial entrega o ultimo `MOVE`, sem executar a sequencia de correcoes velhas |
