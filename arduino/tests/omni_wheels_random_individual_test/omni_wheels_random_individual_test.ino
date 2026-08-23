#include <Arduino.h>

// Sketch independente para testar os 4 motores individualmente e de forma aleatória.
// Funciona sem depender do Raspberry Pi ou do firmware principal.

// true = PCB; false = montagem normal. Na PCB os enables usam PWM por software.
constexpr bool kUsePcbWiring = true;

constexpr int kMaxMotorSpeed = 180;
constexpr unsigned long kRunDurationMs = 3200;
constexpr unsigned long kPauseDurationMs = 800;

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

  for (uint8_t i = 0; i < 4; ++i) {
    g_channels[i] = kUsePcbWiring ? g_pcbChannels[i] : g_normalChannels[i];
  }

  randomSeed(analogRead(A0));
  initMotors();
  initSoftPwm();

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
