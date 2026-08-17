# Conexões atuais — Arduino Mega + 2x TB6612FNG

| Origem | Destino | Função |
|---|---|---|
| Arduino **D23** | TB6612 **A — PWMB** | PWM Motor B |
| Arduino **D25** | TB6612 **A — BIN2** | Direção Motor B |
| Arduino **D27** | TB6612 **A — BIN1** | Direção Motor B |
| Arduino **D29** | TB6612 **A — AIN1** | Direção Motor A |
| Arduino **D31** | TB6612 **A — AIN2** | Direção Motor A |
| Arduino **D33** | TB6612 **A — PWMA** | PWM Motor A |
| Arduino **D43** | TB6612 **B — PWMB** | PWM Motor B |
| Arduino **D45** | TB6612 **B — BIN2** | Direção Motor B |
| Arduino **D47** | TB6612 **B — BIN1** | Direção Motor B |
| Arduino **D49** | TB6612 **B — AIN1** | Direção Motor A |
| Arduino **D51** | TB6612 **B — AIN2** | Direção Motor A |
| Arduino **D53** | TB6612 **B — PWMA** | PWM Motor A |
| **J1 pino 1** | GND dos 2 TB6612 | Terra |
| **J1 pino 2** | VM + VCC dos 2 TB6612 | Alimentação |
| TB6612 **A — A01** | **J3 pino 2** | Motor 1 |
| TB6612 **A — A02** | **J3 pino 1** | Motor 1 |
| TB6612 **A — B01** | **J2 pino 1** | Motor 2 |
| TB6612 **A — B02** | **J2 pino 2** | Motor 2 |
| TB6612 **B — A01** | **J5 pino 2** | Motor 3 |
| TB6612 **B — A02** | **J5 pino 1** | Motor 3 |
| TB6612 **B — B01** | **J4 pino 1** | Motor 4 |
| TB6612 **B — B02** | **J4 pino 2** | Motor 4 |
| **STBY dos 2 TB6612** | **Jumper** | Habilitação comum |

## Resumo por driver

### TB6612 A

- PWMA → Arduino D33
- AIN1 → Arduino D29
- AIN2 → Arduino D31
- PWMB → Arduino D23
- BIN1 → Arduino D27
- BIN2 → Arduino D25
- A01 → J3 pino 2
- A02 → J3 pino 1
- B01 → J2 pino 1
- B02 → J2 pino 2
- VM → J1 pino 2
- VCC → J1 pino 2
- GND → J1 pino 1
- STBY → jumper comum

### TB6612 B

- PWMA → Arduino D53
- AIN1 → Arduino D49
- AIN2 → Arduino D51
- PWMB → Arduino D43
- BIN1 → Arduino D47
- BIN2 → Arduino D45
- A01 → J5 pino 2
- A02 → J5 pino 1
- B01 → J4 pino 1
- B02 → J4 pino 2
- VM → J1 pino 2
- VCC → J1 pino 2
- GND → J1 pino 1
- STBY → jumper comum
