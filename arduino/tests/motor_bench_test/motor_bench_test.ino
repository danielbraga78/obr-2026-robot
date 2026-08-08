#include <Arduino.h>

// Sketch de bancada para diagnosticar motores parados com multímetro.
// Objetivo: manter uma saída estável enquanto você mede, e dizer no monitor
// serial exatamente o que deveria estar acontecendo em cada pino.
//
// Monitor serial: 115200 baud, terminação "Nova linha" ou "Ambos NL & CR".
//
// Diferente do omni_wheels_test.ino, aqui nada muda sozinho: o estado só muda
// quando você manda um comando. É isso que permite medir com o ponteiro parado.

constexpr uint8_t kMotor1EnablePin = 2;
constexpr uint8_t kMotor1In1Pin = 22;
constexpr uint8_t kMotor1In2Pin = 23;

constexpr uint8_t kMotor2EnablePin = 3;
constexpr uint8_t kMotor2In1Pin = 24;
constexpr uint8_t kMotor2In2Pin = 25;

constexpr uint8_t kMotor3EnablePin = 4;
constexpr uint8_t kMotor3In1Pin = 26;
constexpr uint8_t kMotor3In2Pin = 27;

constexpr uint8_t kMotor4EnablePin = 5;
constexpr uint8_t kMotor4In1Pin = 28;
constexpr uint8_t kMotor4In2Pin = 29;

// STBY do TB6612FNG. Com ele em LOW ou flutuando o driver fica em standby e
// NENHUM motor recebe tensão, por mais correto que esteja o resto.
// Se o seu STBY está amarrado direto no 5 V, deixe kUseStbyPin = false.
constexpr bool kUseStbyPin = false;
constexpr uint8_t kStbyPin = 30;

constexpr uint8_t kMotorCount = 4;

struct MotorChannel {
  uint8_t enablePin;
  uint8_t in1Pin;
  uint8_t in2Pin;
  const char* name;
};

MotorChannel g_channels[kMotorCount] = {
  {kMotor1EnablePin, kMotor1In1Pin, kMotor1In2Pin, "M1 (Ponte A - FL)"},
  {kMotor2EnablePin, kMotor2In1Pin, kMotor2In2Pin, "M2 (Ponte A - RL)"},
  {kMotor3EnablePin, kMotor3In1Pin, kMotor3In2Pin, "M3 (Ponte B - FR)"},
  {kMotor4EnablePin, kMotor4In1Pin, kMotor4In2Pin, "M4 (Ponte B - RR)"},
};

uint8_t g_selected = 0;
int g_speed = 255;  // 255 = DC puro, leitura estável no multímetro
int g_direction = 0;  // 1 frente, -1 ré, 0 parado

void applyOutput() {
  for (uint8_t i = 0; i < kMotorCount; ++i) {
    const bool active = (i == g_selected) && (g_direction != 0);
    digitalWrite(g_channels[i].in1Pin, active && g_direction > 0 ? HIGH : LOW);
    digitalWrite(g_channels[i].in2Pin, active && g_direction < 0 ? HIGH : LOW);
    analogWrite(g_channels[i].enablePin, active ? g_speed : 0);
  }
}

void printExpectations() {
  const MotorChannel& motor = g_channels[g_selected];
  Serial.println();
  Serial.print(F("Motor selecionado: "));
  Serial.println(motor.name);
  Serial.print(F("  PWM (enable) no pino D"));
  Serial.print(motor.enablePin);
  Serial.print(F("  | IN1 no pino D"));
  Serial.print(motor.in1Pin);
  Serial.print(F("  | IN2 no pino D"));
  Serial.println(motor.in2Pin);

  if (g_direction == 0) {
    Serial.println(F("  Estado: PARADO"));
    Serial.println(F("  Esperado: IN1 ~0 V, IN2 ~0 V, PWM ~0 V, saida do motor ~0 V"));
  } else {
    Serial.print(F("  Estado: GIRANDO "));
    Serial.print(g_direction > 0 ? F("para FRENTE") : F("para TRAS"));
    Serial.print(F(" a PWM "));
    Serial.print(g_speed);
    Serial.print(F("/255 ("));
    Serial.print((g_speed * 100) / 255);
    Serial.println(F("%)"));

    Serial.print(F("  Esperado: IN1 ~"));
    Serial.print(g_direction > 0 ? F("5 V") : F("0 V"));
    Serial.print(F(", IN2 ~"));
    Serial.print(g_direction > 0 ? F("0 V") : F("5 V"));
    Serial.print(F(", PWM ~"));
    Serial.print((g_speed * 50) / 255 / 10.0, 1);
    Serial.println(F(" V (media do PWM)"));
    Serial.println(F("  Esperado entre as duas saidas do motor: ~tensao de VM"));
    Serial.println(F("  Se der ~0 V ali: cheque VM e STBY antes de qualquer outra coisa."));
  }
  Serial.println(F("  ---"));
  Serial.println(F("  Comandos: 1-4 motor | f frente | r re | s parar | + / - velocidade | ? ajuda"));
}

void printHelp() {
  Serial.println();
  Serial.println(F("=== Teste de bancada dos motores ==="));
  Serial.println(F("  1 2 3 4  seleciona o motor"));
  Serial.println(F("  f        gira para frente"));
  Serial.println(F("  r        gira para tras"));
  Serial.println(F("  s        para"));
  Serial.println(F("  +        aumenta a velocidade (25 em 25)"));
  Serial.println(F("  -        diminui a velocidade"));
  Serial.println(F("  ?        mostra esta ajuda"));
  Serial.println();
  Serial.println(F("Dica: use PWM 255 para medir. O multimetro mostra a MEDIA do"));
  Serial.println(F("PWM, entao valores intermediarios dao leituras baixas e isso"));
  Serial.println(F("e normal, nao e defeito."));

  if (kUseStbyPin) {
    Serial.print(F("STBY: pino D"));
    Serial.print(kStbyPin);
    Serial.println(F(" mantido em HIGH por este sketch."));
  } else {
    Serial.println(F("STBY: este sketch NAO controla o STBY."));
    Serial.println(F("      Ele precisa estar em 5 V por hardware, senao o driver"));
    Serial.println(F("      fica em standby e nenhum motor recebe tensao."));
    Serial.println(F("      Meca STBY -> GND: tem que dar ~5 V."));
  }
}

void handleCommand(char command) {
  switch (command) {
    case '1': case '2': case '3': case '4':
      g_selected = command - '1';
      break;
    case 'f': case 'F':
      g_direction = 1;
      break;
    case 'r': case 'R':
      g_direction = -1;
      break;
    case 's': case 'S':
      g_direction = 0;
      break;
    case '+':
      g_speed = min(255, g_speed + 25);
      break;
    case '-':
      g_speed = max(0, g_speed - 25);
      break;
    case '?':
      printHelp();
      break;
    default:
      return;  // ignora \r, \n e teclas desconhecidas
  }
  applyOutput();
  printExpectations();
}

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    ;  // aguarda o monitor no Mega/Leonardo
  }

  for (uint8_t i = 0; i < kMotorCount; ++i) {
    pinMode(g_channels[i].enablePin, OUTPUT);
    pinMode(g_channels[i].in1Pin, OUTPUT);
    pinMode(g_channels[i].in2Pin, OUTPUT);
  }

  if (kUseStbyPin) {
    pinMode(kStbyPin, OUTPUT);
    digitalWrite(kStbyPin, HIGH);
  }

  g_direction = 0;
  applyOutput();

  printHelp();
  printExpectations();
}

void loop() {
  if (Serial.available()) {
    handleCommand(static_cast<char>(Serial.read()));
  }
}
