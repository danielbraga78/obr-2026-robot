#include <Arduino.h>

// Sketch independente para testar rodas omnidirecionais no Arduino Mega.
// Objetivo: validar o funcionamento dos 4 motores sem depender do Raspberry.

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

constexpr int kMaxMotorSpeed = 200;
constexpr int kTestDurationMs = 2000;

struct MotorChannel {
  uint8_t enablePin;
  uint8_t in1Pin;
  uint8_t in2Pin;
};

MotorChannel g_channels[4] = {
  {kMotor1EnablePin, kMotor1In1Pin, kMotor1In2Pin},
  {kMotor2EnablePin, kMotor2In1Pin, kMotor2In2Pin},
  {kMotor3EnablePin, kMotor3In1Pin, kMotor3In2Pin},
  {kMotor4EnablePin, kMotor4In1Pin, kMotor4In2Pin},
};

void initMotors() {
  for (uint8_t i = 0; i < 4; ++i) {
    pinMode(g_channels[i].enablePin, OUTPUT);
    pinMode(g_channels[i].in1Pin, OUTPUT);
    pinMode(g_channels[i].in2Pin, OUTPUT);
  }
  stopAllMotors();
}

void stopAllMotors() {
  for (uint8_t i = 0; i < 4; ++i) {
    digitalWrite(g_channels[i].in1Pin, LOW);
    digitalWrite(g_channels[i].in2Pin, LOW);
    analogWrite(g_channels[i].enablePin, 0);
  }
}

void setMotorSpeed(uint8_t motorIndex, int speed) {
  if (motorIndex >= 4) {
    return;
  }

  speed = constrain(speed, -kMaxMotorSpeed, kMaxMotorSpeed);
  const bool reverse = speed < 0;
  const uint8_t pwmValue = static_cast<uint8_t>(abs(speed));

  digitalWrite(g_channels[motorIndex].in1Pin, reverse ? HIGH : LOW);
  digitalWrite(g_channels[motorIndex].in2Pin, reverse ? LOW : HIGH);
  analogWrite(g_channels[motorIndex].enablePin, pwmValue);
}

void runSequence(const char* name, int fl, int fr, int rl, int rr) {
  Serial.println();
  Serial.print("[TEST] ");
  Serial.println(name);
  setMotorSpeed(0, fl);
  setMotorSpeed(1, fr);
  setMotorSpeed(2, rl);
  setMotorSpeed(3, rr);
  delay(kTestDurationMs);
  stopAllMotors();
  delay(1000);
}

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    ;
  }

  initMotors();
  Serial.println("Teste de rodas omnidirecionais iniciado.");
  Serial.println("Cada sequência roda por 2 segundos e para por 1 segundo.");
}

void loop() {
  runSequence("Frente", 150, 150, 150, 150);
  runSequence("Tras", -150, -150, -150, -150);
  runSequence("Direita", 150, -150, -150, 150);
  runSequence("Esquerda", -150, 150, 150, -150);
  runSequence("RotacaoHorario", 150, -150, 150, -150);
  runSequence("RotacaoAntiHorario", -150, 150, -150, 150);
  runSequence("Parada", 0, 0, 0, 0);

  Serial.println("Ciclo completo finalizado. Reiniciando...\n");
  delay(1000);
}
