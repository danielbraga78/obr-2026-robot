# Arduino Mega 2560 — Guia de uso e mapeamento de pinos

Este documento descreve um mapeamento sugerido de pinos e instruções para usar
o firmware do robô com uma placa **Arduino Mega 2560**. Ele complementa o
`HARDWARE.md` com detalhes específicos do Mega e instruções rápidas para
compilar e fazer upload.

## Por que usar o Mega?

- Mais pinos digitais e analógicos disponíveis para sensores futuros;
- Múltiplas UARTs (Serial1/2/3) que permitem comunicar com o Raspberry Pi sem
  ocupar a USB de programação;
- Mais memória e recursos para extensões futuras.

## Mapeamento de pinos atual

Este é o mapeamento usado no firmware atual em [arduino/firmware/robot_mega/robot_mega.ino](arduino/firmware/robot_mega/robot_mega.ino).
Mantenha o GND comum entre todos os dispositivos e siga este layout para evitar divergências.

| Constante no sketch | Função | Pino Mega |
|---|---|---:|
| `kMotor4EnablePin` | PWM enable Motor 4 | `2` (PWM) |
| `kMotor4In1Pin` | Direção Motor 4 | `22` |
| `kMotor4In2Pin` | Direção Motor 4 | `23` |
| `kMotor2EnablePin` | PWM enable Motor 2 | `3` (PWM) |
| `kMotor2In1Pin` | Direção Motor 2 | `24` |
| `kMotor2In2Pin` | Direção Motor 2 | `25` |
| `kMotor3EnablePin` | PWM enable Motor 3 | `4` (PWM) |
| `kMotor3In1Pin` | Direção Motor 3 | `26` |
| `kMotor3In2Pin` | Direção Motor 3 | `27` |
| `kMotor1EnablePin` | PWM enable Motor 1 | `5` (PWM) |
| `kMotor1In1Pin` | Direção Motor 1 | `28` |
| `kMotor1In2Pin` | Direção Motor 1 | `29` |
| `kServoPin` | Sinal do servo da garra | `44` (servo) |
| `kUltrasonicTrigPin` | TRIG HC-SR04 | `A2` |
| `kUltrasonicEchoPin` | ECHO HC-SR04 | `A3` |
| `STBY` (TB6612FNG) | Habilita ponte H (compartilhável) | usar `30` ou `31` |

Notas:
- Os pinos 2,3,4,5 são PWM no Mega e servem para os sinais `enable` (analogWrite).
- Os pinos de direção foram colocados em pinos digitais altos (22-29) para
  evitar interferência com UART/ISP.

## Serial entre Mega e Raspberry

- O protocolo serial usado pelo firmware é o seguinte:
  - Raspberry envia `HEARTBEAT` periodicamente como keepalive.
  - Arduino responde a `HEARTBEAT` sem mover o robô e reseta o watchdog local.
  - Se não houver tráfego válido por mais de 1 segundo, o Arduino para os motores e envia `WATCHDOG`.
  - O Raspberry interpreta `WATCHDOG` como falha explícita e entra em estado seguro com `STOP`.
- Para comunicação TTL dedicada (sem USB), use `Serial1` do Mega:
  - TX1 = pino `18` (Mega) — conecta ao RX do Raspberry (GPIO 15) via conversor
    de nível (ou divisor de tensão)
  - RX1 = pino `19` (Mega) — conecta ao TX do Raspberry (GPIO 14)

Se preferir o caminho USB (mais simples), basta conectar o Mega por USB ao Pi.

Importante: quando ligar TX (5V) do Mega ao RX do Raspberry (3.3V), sempre
usar um divisor de tensão ou conversor de nível (para evitar danificar o Pi).

## Compilar e fazer upload

1. Abra o `arduino/firmware/robot_mega/robot_mega.ino`.
2. No Arduino IDE ou `arduino-cli`, selecione a placa `Arduino Mega or Mega 2560`.
3. Compile e faça upload.

Exemplo com `arduino-cli`:

```bash
arduino-cli compile --fqbn arduino:avr:mega:cpu=atmega2560 arduino/firmware/robot_mega
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:mega:cpu=atmega2560 arduino/firmware/robot_mega
```

## Testes pós-upload (recomendado)

1. Verifique se `READY` aparece na serial ao inicializar.
2. Teste individualmente cada motor com os comandos de teste (ex.: `MOVE,110,0,0`).
3. Confirme que `STBY` está HIGH para habilitar os drivers.

## Observações finais

Este mapeamento é apenas uma sugestão prática. Se você quiser que eu gere a
versão do sketch com essas constantes já aplicadas e faça um commit, diga
"gere robot_mega.ino".