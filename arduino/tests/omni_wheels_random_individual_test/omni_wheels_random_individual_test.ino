#include <Arduino.h>

// Sketch independente para testar os 4 motores individualmente e de forma aleatória.
// Funciona sem depender do Raspberry Pi ou do firmware principal.

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

constexpr int kMaxMotorSpeed = 180;
constexpr unsigned long kRunDurationMs = 3200;
constexpr unsigned long kPauseDurationMs = 800;

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

void runSingleMotorTest(const char* bridgeName, uint8_t motorIndex) {
  const int direction = random(0, 2) == 0 ? -1 : 1;
  const int speed = random(120, kMaxMotorSpeed + 1);
  const int finalSpeed = speed * direction;

  Serial.print("[TEST] ");
  Serial.print(bridgeName);
  Serial.print(" | motor ");
  Serial.print(motorIndex + 1);
  Serial.print(" | direcao ");
  Serial.print(direction > 0 ? "frente" : "tras");
  Serial.print(" | velocidade ");
  Serial.println(abs(finalSpeed));

  stopAllMotors();
  setMotorSpeed(motorIndex, finalSpeed);
  delay(kRunDurationMs);
  stopAllMotors();
  delay(kPauseDurationMs);
}

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    ;
  }

  randomSeed(analogRead(A0));
  initMotors();

  Serial.println("Teste individual dos motores iniciado.");
  Serial.println("Cada ciclo ativa um motor aleatorio da Ponte A ou da Ponte B por 3.2s e pausa por 0.8s.");
}

void loop() {
  if (random(0, 2) == 0) {
    const uint8_t motorIndex = static_cast<uint8_t>(random(0, 2));
    runSingleMotorTest("Ponte A (esquerda)", motorIndex);
  } else {
    const uint8_t motorIndex = static_cast<uint8_t>(random(2, 4));
    runSingleMotorTest("Ponte B (direita)", motorIndex);
  }
}
