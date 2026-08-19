# Ligações atuais — Arduino Mega + 2x TB6612FNG + sensores/servos

## 1. TB6612FNG — Ponte H A

| Origem | Destino | Função |
|---|---|---|
| Arduino **D23** | TB6612 **A — PWMB** | PWM Motor B |
| Arduino **D25** | TB6612 **A — BIN2** | Direção Motor B |
| Arduino **D27** | TB6612 **A — BIN1** | Direção Motor B |
| Arduino **D29** | TB6612 **A — AIN1** | Direção Motor A |
| Arduino **D31** | TB6612 **A — AIN2** | Direção Motor A |
| Arduino **D33** | TB6612 **A — PWMA** | PWM Motor A |
| TB6612 **A — A01** | **J5 pino 2** | Motor 3 |
| TB6612 **A — A02** | **J5 pino 1** | Motor 3 |
| TB6612 **A — B01** | **J4 pino 1** | Motor 4 |
| TB6612 **A — B02** | **J4 pino 2** | Motor 4 |
| TB6612 **A — VM** | **J1 pino 2** | Alimentação dos motores |
| TB6612 **A — VCC** | **J1 pino 2** | Alimentação lógica |
| TB6612 **A — GND** | **J1 pino 1** | Terra |
| TB6612 **A — STBY** | **Jumper comum** | Habilitação |

## 2. TB6612FNG — Ponte H B

| Origem | Destino | Função |
|---|---|---|
| Arduino **D43** | TB6612 **B — PWMB** | PWM Motor B |
| Arduino **D45** | TB6612 **B — BIN2** | Direção Motor B |
| Arduino **D47** | TB6612 **B — BIN1** | Direção Motor B |
| Arduino **D49** | TB6612 **B — AIN1** | Direção Motor A |
| Arduino **D51** | TB6612 **B — AIN2** | Direção Motor A |
| Arduino **D53** | TB6612 **B — PWMA** | PWM Motor A |
| TB6612 **B — A01** | **J3 pino 2** | Motor 1 |
| TB6612 **B — A02** | **J3 pino 1** | Motor 1 |
| TB6612 **B — B01** | **J2 pino 1** | Motor 2 |
| TB6612 **B — B02** | **J2 pino 2** | Motor 2 |
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
| **J7 pino 1** | J8 GND |
| **J7 pino 1** | J9 GND |
| **J7 pino 1** | J12 GND |

## 5. Sensor ultrassônico

Os conectores **J6 e J7** serão utilizados para o sensor ultrassônico.

| Conector | Pino | Conexão atual | Função planejada |
|---|---:|---|---|
| **J6** | 1 | GND | GND do ultrassônico |
| **J6** | 2 | Arduino **D44** | Sinal do ultrassônico |
| **J7** | 1 | GND | GND/alimentação do ultrassônico |
| **J7** | 2 | VCC | VCC/alimentação do ultrassônico |

> O netlist atual confirma J6 pino 1 em GND e J6 pino 2 em D44, além de J7 pino 1 em GND e J7 pino 2 em VCC. A identificação de J6/J7 como conectores do sensor ultrassônico é baseada na função definida para este projeto.

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
| **D44** | J6 pino 2 | Sensor ultrassônico |
| **D38** | J13 pino 1 | Reserva |
| **D36** | J13 pino 2 | Reserva |
| **D42** | J14 pino 1 | Reserva |
| **D40** | J14 pino 2 | Reserva |
| **A7** | J15 pino 1 | Reserva |
| **A6** | J15 pino 2 | Reserva |
| **J7 pino 1** | GND | Sensor ultrassônico / servos |
| **J7 pino 2** | VCC | Sensor ultrassônico / servos |

## 8. Resumo dos motores

| Motor | Ponte H | Saídas | Conector |
|---|---|---|---|
| **Motor 1** | TB6612 B | A01 / A02 | J3 |
| **Motor 2** | TB6612 B | B01 / B02 | J2 |
| **Motor 3** | TB6612 A | A01 / A02 | J5 |
| **Motor 4** | TB6612 A | B01 / B02 | J4 |