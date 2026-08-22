# Ligações atuais — Arduino Mega + 2x TB6612FNG + sensores/servos

> Conferido contra o netlist do Fritzing em 2026-08-22. As letras A e B das
> pontes seguem a placa física; no arquivo do Fritzing elas aparecem trocadas.
> Correção aplicada: o pino 1 do J7 é **D46**, não GND — é o segundo sinal do
> HC-SR04, que estava faltando na documentação.

## 1. TB6612FNG — Ponte H A

| Origem | Destino | Função |
|---|---|---|
| Arduino **D23** | TB6612 **A — PWMB** | PWM Motor 2 |
| Arduino **D25** | TB6612 **A — BIN2** | Direção Motor 2 |
| Arduino **D27** | TB6612 **A — BIN1** | Direção Motor 2 |
| Arduino **D29** | TB6612 **A — AIN1** | Direção Motor 1 |
| Arduino **D31** | TB6612 **A — AIN2** | Direção Motor 1 |
| Arduino **D33** | TB6612 **A — PWMA** | PWM Motor 1 |
| TB6612 **A — A01** | **J3 pino 2** | Motor 1 |
| TB6612 **A — A02** | **J3 pino 1** | Motor 1 |
| TB6612 **A — B01** | **J2 pino 1** | Motor 2 |
| TB6612 **A — B02** | **J2 pino 2** | Motor 2 |
| TB6612 **A — VM** | **J1 pino 2** | Alimentação dos motores |
| TB6612 **A — VCC** | **J1 pino 2** | Alimentação lógica |
| TB6612 **A — GND** | **J1 pino 1** | Terra |
| TB6612 **A — STBY** | **Jumper comum** | Habilitação |

## 2. TB6612FNG — Ponte H B

| Origem | Destino | Função |
|---|---|---|
| Arduino **D43** | TB6612 **B — PWMB** | PWM Motor 4 |
| Arduino **D45** | TB6612 **B — BIN2** | Direção Motor 4 |
| Arduino **D47** | TB6612 **B — BIN1** | Direção Motor 4 |
| Arduino **D49** | TB6612 **B — AIN1** | Direção Motor 3 |
| Arduino **D51** | TB6612 **B — AIN2** | Direção Motor 3 |
| Arduino **D53** | TB6612 **B — PWMA** | PWM Motor 3 |
| TB6612 **B — A01** | **J5 pino 2** | Motor 3 |
| TB6612 **B — A02** | **J5 pino 1** | Motor 3 |
| TB6612 **B — B01** | **J4 pino 1** | Motor 4 |
| TB6612 **B — B02** | **J4 pino 2** | Motor 4 |
| TB6612 **B — VM** | **J1 pino 2** | Alimentação dos motores |
| TB6612 **B — VCC** | **J1 pino 2** | Alimentação lógica |
| TB6612 **B — GND** | **J1 pino 1** | Terra |
| TB6612 **B — STBY** | **Jumper comum** | Habilitação |

## 3. Alimentação

| Origem | Destino | Função |
|---|---|---|
| **J1 pino 1** | GND dos dois TB6612 | Terra |
| **J1 pino 2** | VM dos dois TB6612 | Alimentação dos motores |
| **J1 pino 2** | VCC dos dois TB6612 | Alimentação lógica |

## 4. Servomotores

Existem **3 conectores destinados aos servomotores**:

| Conector | Sinal | Arduino | Alimentação |
|---|---|---|---|
| **J8** | Pulse | **D50** | VCC + GND comuns |
| **J9** | Pulse | **D48** | VCC + GND comuns |
| **J12** | Pulse | **D52** | VCC + GND comuns |

Alimentação dos três servos:

| Origem | Destino |
|---|---|
| **J7 pino 2** | J8 VCC |
| **J7 pino 2** | J9 VCC |
| **J7 pino 2** | J12 VCC |
| Terra comum (J1 pino 1) | J8 GND |
| Terra comum (J1 pino 1) | J9 GND |
| Terra comum (J1 pino 1) | J12 GND |

O pino 1 do J7 **não é GND**: é o sinal D46, do ultrassônico. Os três servos
tiram o terra do plano comum, junto com as pontes e o Arduino.

## 5. Sensor ultrassônico HC-SR04

O sensor usa os quatro pinos dos conectores **J6 e J7** juntos: são os quatro
fios de que o HC-SR04 precisa, distribuídos em dois conectores de dois pinos.

| Conector | Pino | Arduino | Função |
|---|---:|---|---|
| **J7** | 2 | VCC | Alimentação |
| **J7** | 1 | **D46** | Sinal |
| **J6** | 2 | **D44** | Sinal |
| **J6** | 1 | GND | Terra |

Qual dos dois sinais é TRIG e qual é ECHO depende de como o sensor foi
encaixado. A tabela está na ordem física dos pinos, e a pinagem padrão do
HC-SR04 é VCC, TRIG, ECHO, GND — daí o firmware assumir **TRIG em D46** e
**ECHO em D44**. Se nenhum `DIST` for reportado, é porque os dois estão
invertidos: com TRIG e ECHO trocados o `pulseIn` só dá timeout, e basta trocar
as duas constantes no sketch.

## 6. Conectores reservados para expansão futura

Estes conectores permanecem disponíveis para futuras expansões:

| Conector | Pino 1 | Pino 2 |
|---|---|---|
| **J13** | Arduino **D38** | Arduino **D36** |
| **J14** | Arduino **D42** | Arduino **D40** |
| **J15** | Arduino **A7** | Arduino **A6** |

Esses conectores não possuem função definida no projeto atual e ficam reservados para uso futuro.

## 7. Mapa rápido dos pinos adicionais

| Arduino | Conectado a | Uso |
|---:|---|---|
| **D50** | J8 Pulse | Servo 1 |
| **D48** | J9 Pulse | Servo 2 |
| **D52** | J12 Pulse | Servo 3 |
| **D44** | J6 pino 2 | Ultrassônico (ECHO) |
| **D46** | J7 pino 1 | Ultrassônico (TRIG) |
| **D38** | J13 pino 1 | Reserva |
| **D36** | J13 pino 2 | Reserva |
| **D42** | J14 pino 1 | Reserva |
| **D40** | J14 pino 2 | Reserva |
| **A7** | J15 pino 1 | Reserva |
| **A6** | J15 pino 2 | Reserva |
| **J7 pino 2** | VCC | Alimentação do ultrassônico |
| **J6 pino 1** | GND | Terra do ultrassônico |

## 8. Resumo dos motores

| Motor | Ponte H | Saídas | Conector | PWM | IN1 | IN2 |
|---|---|---|---|---|---|---|
| **Motor 1** | TB6612 A | A01 / A02 | J3 | D33 | D29 | D31 |
| **Motor 2** | TB6612 A | B01 / B02 | J2 | D23 | D27 | D25 |
| **Motor 3** | TB6612 B | A01 / A02 | J5 | D53 | D49 | D51 |
| **Motor 4** | TB6612 B | B01 / B02 | J4 | D43 | D47 | D45 |

Nenhum dos quatro pinos de PWM tem PWM por hardware no Mega, que só o oferece
nos pinos 2 a 13 e 44 a 46. Por isso o firmware da placa
(`arduino/firmware/robot_mega_pcb/`) gera o PWM por software, com uma
interrupção de timer a 31,25 kHz.