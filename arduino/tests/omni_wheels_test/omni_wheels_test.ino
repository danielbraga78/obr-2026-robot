
#include <Arduino.h>

// Sketch independente para testar rodas omnidirecionais no Arduino Mega.
// Objetivo: validar o funcionamento dos 4 motores sem depender do Raspberry.

// true = PCB; false = montagem normal. Na PCB os enables usam PWM por software.
constexpr bool kUsePcbWiring = true;

constexpr int kMaxMotorSpeed = 200;
constexpr int kTestDurationMs = 2000;
constexpr int kMotorAllSpeed = 150;
constexpr uint8_t kLeftBridgeMotorCount = 2;
constexpr uint8_t kRightBridgeMotorCount = 2;

struct MotorChannel {
  uint8_t enablePin;
  uint8_t in1Pin;
  uint8_t in2Pin;
};

MotorChannel g_pcbChannels[4] = {
  {33, 29, 31}, {23, 27, 25}, {53, 49, 51}, {43, 47, 45},
};

MotorChannel g_normalChannels[4] = {
  {5, 28, 29}, {3, 25, 24}, {4, 26, 27}, {2, 22, 23},
};

MotorChannel g_channels[4] = {
  {0, 0, 0}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0},
};

volatile uint8_t g_softPwmDuty[4] = {0, 0, 0, 0};
volatile uint8_t* g_softPwmPort[4] = {nullptr, nullptr, nullptr, nullptr};
uint8_t g_softPwmMask[4] = {0, 0, 0, 0};
volatile uint8_t g_softPwmPhase = 0;

ISR(TIMER2_COMPA_vect) {
  const uint8_t phase = g_softPwmPhase++;
  for (uint8_t i = 0; i < 4; ++i) {
    if (g_softPwmPort[i] == nullptr) continue;
    if (phase == 0 && g_softPwmDuty[i] != 0) *g_softPwmPort[i] |= g_softPwmMask[i];
    if (phase == 0 && g_softPwmDuty[i] == 0) *g_softPwmPort[i] &= ~g_softPwmMask[i];
    if (phase >= g_softPwmDuty[i]) *g_softPwmPort[i] &= ~g_softPwmMask[i];
  }
}

void initSoftPwm() {
  bool active = false;
  for (uint8_t i = 0; i < 4; ++i) {
    if (digitalPinHasPWM(g_channels[i].enablePin)) continue;
    g_softPwmPort[i] = portOutputRegister(digitalPinToPort(g_channels[i].enablePin));
    g_softPwmMask[i] = digitalPinToBitMask(g_channels[i].enablePin);
    active = true;
  }
  if (!active) return;
  noInterrupts();
  TCCR2A = _BV(WGM21); TCCR2B = _BV(CS21); OCR2A = 63; TIMSK2 = _BV(OCIE2A);
  interrupts();
}

void writeEnable(uint8_t motorIndex, uint8_t duty) {
  if (g_softPwmPort[motorIndex] != nullptr) g_softPwmDuty[motorIndex] = duty;
  else analogWrite(g_channels[motorIndex].enablePin, duty);
}

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
    writeEnable(i, 0);
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
  writeEnable(motorIndex, pwmValue);
}

void runBridgeMotors(const char* bridgeName, const uint8_t* motorIndices, uint8_t count, int speed) {
  Serial.println();
  Serial.print("[TEST] ");
  Serial.print(bridgeName);
  Serial.print(" | velocidade ");
  Serial.println(speed);
  for (uint8_t i = 0; i < count; ++i) {
    setMotorSpeed(motorIndices[i], speed);
  }
  delay(kTestDurationMs);
  stopAllMotors();
  delay(1000);
}

void runBridgeA(int speed) {
  const uint8_t leftMotorIndices[kLeftBridgeMotorCount] = {0, 1};
  runBridgeMotors("Ponte A (esquerda)", leftMotorIndices, kLeftBridgeMotorCount, speed);
}

void runBridgeB(int speed) {
  const uint8_t rightMotorIndices[kRightBridgeMotorCount] = {2, 3};
  runBridgeMotors("Ponte B (direita)", rightMotorIndices, kRightBridgeMotorCount, speed);
}

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    ;
  }

  for (uint8_t i = 0; i < 4; ++i) {
    g_channels[i] = kUsePcbWiring ? g_pcbChannels[i] : g_normalChannels[i];
  }

  initMotors();
  initSoftPwm();
  Serial.println("Teste de motores iniciado.");
  Serial.println("A Ponte A (esquerda) e a Ponte B (direita) giram separadamente por 2 segundos.");
}

void loop() {
  runBridgeA(kMotorAllSpeed);
  runBridgeA(-kMotorAllSpeed);
  runBridgeB(kMotorAllSpeed);
  runBridgeB(-kMotorAllSpeed);

  Serial.println("Ciclo completo finalizado. Reiniciando...\n");
  delay(1000);
}
