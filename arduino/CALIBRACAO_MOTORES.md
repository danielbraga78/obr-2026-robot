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

Quem trata a zona morta é o `fit_to_motor_deadband` no Raspberry
(`raspberry/motion.py`), reduzindo o avanço até a curva pedida caber na faixa
útil dos motores. O firmware só precisa ser honesto sobre onde essa faixa começa.

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

`MOTOR_DEADBAND_PWM` em `raspberry/config.py` precisa ser o mínimo do **pior**
motor, expresso na escala de comando:

```
MOTOR_DEADBAND_PWM = max(kMotorMinDuty[i] / kMotorGain[i])
```

Esse número define quando o robô troca avanço por pivô nas curvas fechadas. Se
ficar menor que o valor atual (110), o robô ganha autoridade de curva sem
precisar pivotar — é o principal ganho prático da calibração.

## Verificação

1. **Reta:** `MOVE,180,0,0` por 2 metros. O desvio lateral deve ficar abaixo de
   10 cm. Se puxar para um lado, os ganhos ainda não estão nivelados.
2. **Pivô:** `MOVE,0,0,150`. O robô deve girar no lugar, sem transladar.
3. **Curva fechada:** `MOVE,110,0,125`. Deve virar visivelmente mais fechado que
   `MOVE,110,0,60`. Se os dois parecerem iguais, a zona morta ainda está
   engolindo o diferencial.

## Ultrassônico

O PWM por software mantém uma interrupção a 31,25 kHz, e `pulseIn` conta ciclos
com as interrupções ligadas. A distância medida sai cerca de 8% maior do que a
real enquanto os motores estão sob controle do soft PWM.

Aponte o sensor para uma parede a 100 cm medidos com trena e compare com o
`DIST` reportado. Ajuste o fator `0.01715` em `handleUltrasonic` pela razão entre
o valor real e o lido.
