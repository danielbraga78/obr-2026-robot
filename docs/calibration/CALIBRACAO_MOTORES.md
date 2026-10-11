# Calibração dos motores (firmware da PCB)

Vale para `arduino/firmware/robot_mega_pcb/robot_mega_pcb.ino`. O sketch da
protoboard, `robot_mega/robot_mega.ino`, continua válido e não usa nada disto.

## Por que calibrar

Dois números por motor, medidos na bancada:

| Constante | O que é | O que resolve |
|---|---|---|
| `kMotorMinDuty[i]` | duty em que aquela roda começa a girar **com carga** | abaixo dele o comando vai a zero, em vez de fingir movimento |
| `kMotorGain[i]` | ganho relativo entre os quatro motores | o mesmo comando passa a dar a mesma velocidade nas quatro rodas |

O ganho é o que mais importa para o seguidor de linha. Quatro motores nunca são
iguais: com o mesmo duty, um gira mais que o outro, e o robô puxa para um lado
mesmo com `wz = 0`. Pior, a mistura omni assume que a velocidade de cada roda é
proporcional ao valor que ela recebe — se não for, um comando de curva produz
uma curva diferente da pedida.

## O que não fazer

**Não compense a zona morta somando um offset ao comando.** É tentador mapear
`duty = minDuty + (255 - minDuty) * comando / 255`, para que qualquer comando
diferente de zero mova a roda. Isso desloca a origem e quebra a
proporcionalidade que a mistura omni assume: o robô passa a girar diferente do
que foi pedido, e o erro cresce justamente nas curvas.

Quem trata a zona morta é a projeção em `fit_to_motor_deadband` no Raspberry
(`raspberry/motion.py`). Ela compara o vetor de movimento solicitado com os
comandos de roda após truncamento, ganho e corte mínimo e escolhe o movimento
executável mais próximo sem aumentar qualquer componente. Dependendo do vetor,
uma componente pode ser reduzida ou o comando pode resultar em parada; não há
conversão implícita de curva em pivô.

## Antes de tudo: descobrir qual motor é qual roda

A PCB numera os conectores de J2 a J5 sem dizer qual roda é qual, e o firmware
raciocina em frente-esquerda, trás-esquerda, frente-direita e trás-direita.

Com o robô suspenso, no monitor serial a 115200 com final de linha "Nova linha":

```
CAL,ON
CAL,0,150
```

Veja qual roda girou e em que sentido. Repita para 1, 2 e 3. Se a ordem não
bater com a esperada, corrija o vetor `g_channels` no sketch — não a fiação.

O sentido também importa: com duty positivo a roda deve girar para frente. Se
girar ao contrário, troque `in1Pin` e `in2Pin` daquele canal no sketch.

## Passo 1: duty mínimo de cada roda

Com o robô **no chão**, não suspenso. Uma roda no ar gira com muito menos duty
do que com o peso do robô em cima, e o valor medido no ar é inútil.

```
CAL,ON
CAL,0,60
CAL,0,70
CAL,0,80
...
```

Suba de 5 em 5 até a roda começar a girar de forma contínua, sem travar. Esse é
o `kMotorMinDuty` daquele motor. Repita para os quatro.

Cada comando renova o teto de 30 segundos do modo de calibração; passado esse
tempo sem comando, o modo se encerra sozinho e os motores param.

## Passo 2: ganho relativo

Marque um ponto em cada roda com fita. Com o robô suspenso:

```
CAL,0,200
```

Conte as voltas em 10 segundos. Repita para os quatro motores com o mesmo duty.

O motor **mais lento** vira a referência e recebe ganho `1.0`. Os outros recebem:

```
ganho_i = voltas_do_mais_lento / voltas_do_motor_i
```

Sempre menor ou igual a 1: nivelamos por baixo, porque acelerar um motor além do
que ele dá não é possível.

```
CAL,OFF
```

## Passo 3: aplicar

No sketch, edite:

```cpp
constexpr uint8_t kMotorMinDuty[4] = {110, 110, 110, 110};
constexpr float kMotorGain[4] = {1.0f, 1.0f, 1.0f, 1.0f};
```

Regrave o Arduino. `CAL` sozinho no monitor serial imprime a tabela em uso, para
confirmar que o que está gravado é o que você mediu.

## Passo 4: avisar o Raspberry

`MOTOR_MIN_PWM` e `MOTOR_PWM_GAINS` em `raspberry/config.py` devem espelhar as
quatro entradas gravadas no firmware PCB:

```
MOTOR_MIN_PWM = tuple(kMotorMinDuty)
MOTOR_PWM_GAINS = tuple(kMotorGain)
```

Esses valores calibram a simulação dos PWMs no Raspberry; eles não medem
velocidade física e precisam ser atualizados junto com o firmware. O mapeamento
não decide sozinho que uma curva deve virar pivô.

## Verificação

1. **Reta:** `MOVE,180,0,0` por 2 metros. O desvio lateral deve ficar abaixo de
   10 cm. Se puxar para um lado, os ganhos ainda não estão nivelados.
2. **Pivô:** `MOVE,0,0,150`. O robô deve girar no lugar, sem transladar.
3. **Curvas:** compare `MOVE,150,0,50` e `MOVE,110,0,80` com os quatro PWM
   reportados/calculados. Um componente inviável pode ser reduzido; confirme no
   chassi a direção e a trajetória antes de aumentar limites.

## Ultrassônico

O firmware consulta o pino ECHO sem bloquear o loop de controle. Para validar a
temporização, compare a cadência de aplicação do PWM e a distância `DIST` com
eco válido e sem eco, com os motores parados e acionados. A precisão da medida
continua dependendo de aferição física.
