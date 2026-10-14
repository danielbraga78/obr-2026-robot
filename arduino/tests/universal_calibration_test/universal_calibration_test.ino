#include <Arduino.h>
#include <Servo.h>
#include <ctype.h>
#include <errno.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

// ===========================================================================
// Teste universal de calibracao - Arduino Mega 2560
// ===========================================================================
//
// Substitui, num unico sketch, os antigos testes de bancada:
//   motor_bench_test, motor_calibration_test, omni_wheels_test,
//   omni_wheels_random_individual_test e ultrasonic_test.
//
// Tudo e comandado pelo Monitor Serial (115200 baud, final de linha
// "Nova linha"). Nada se move sozinho: cada teste so roda quando voce manda e
// todo acionamento tem um teto de tempo. Substitui temporariamente o firmware
// do robo: regrave robot_mega_pcb.ino ao terminar.
//
// O que ele faz:
//   - Motores: identificar conector/roda, duty minimo, ganho, velocidade
//     maxima, pontes A/B e sequencia dos quatro motores.
//   - Giro: mede quanto tempo e em qual duty o robo faz 90 graus.
//   - Sensores: HC-SR04 (leitura, monitor continuo e estatistica) e as
//     entradas analogicas reservadas A6/A7 (J15).
//   - Servo da garra.
//
// Ver docs/calibration/CALIBRACAO_MOTORES.md para o procedimento.

// true = PCB (docs/hardware/HARDWARE.md); false = montagem em protoboard.
constexpr bool kUsePcbWiring = true;

// Sentido fisico do wz positivo da mistura omni (vx + vy + wz). Confirme na
// bancada com TURN,+,150,500 e ajuste aqui: so afeta os apelidos H/A.
constexpr bool kPositiveWzIsClockwise = true;

constexpr uint8_t kMotorCount = 4;
constexpr uint8_t kMaxDuty = 255;
constexpr uint8_t kGainTestDuty = 200;
constexpr uint8_t kDefaultSeqDuty = 150;
constexpr unsigned long kMeasurementDurationMs = 10000;
constexpr unsigned long kManualRunTimeoutMs = 30000;
constexpr unsigned long kSeqStepMs = 1500;
constexpr unsigned long kBridgeStepMs = 2000;
constexpr unsigned long kTurnMinMs = 50;
constexpr unsigned long kTurnMaxMs = 30000;
constexpr unsigned long kUltrasonicWatchMs = 250;
constexpr unsigned long kUltrasonicTimeoutUs = 23000;  // ~4 m
constexpr uint8_t kUltrasonicStatMaxSamples = 50;
constexpr uint8_t kFirmwareMinDuty = 110;  // valor padrao de robot_mega_pcb.ino
constexpr size_t kLineCapacity = 48;
constexpr size_t kFieldCount = 4;

struct MotorChannel {
  uint8_t enablePin;
  uint8_t in1Pin;
  uint8_t in2Pin;
  const char* name;
};

// Ordem logica do firmware: frente esquerda, tras esquerda, frente direita,
// tras direita. A PCB numera os conectores de J2 a J5 sem dizer qual roda e
// qual: use SEQ para conferir na bancada.
constexpr MotorChannel kPcbChannels[kMotorCount] = {
    {33, 29, 31, "M1 - J3 / ponte A canal A"},
    {23, 27, 25, "M2 - J2 / ponte A canal B"},
    {53, 49, 51, "M3 - J5 / ponte B canal A"},
    {43, 47, 45, "M4 - J4 / ponte B canal B"},
};

constexpr MotorChannel kBreadboardChannels[kMotorCount] = {
    {5, 28, 29, "M1 - protoboard / frente esquerda"},
    {3, 25, 24, "M2 - protoboard / tras esquerda"},
    {4, 26, 27, "M3 - protoboard / frente direita"},
    {2, 22, 23, "M4 - protoboard / tras direita"},
};

// Na PCB os enables caem em D33, D23, D53 e D43, que nao tem PWM por hardware
// no Mega: o PWM e gerado por software (Timer2), como no firmware da PCB.
constexpr uint8_t kUltrasonicTrigPin = kUsePcbWiring ? 44 : A2;
constexpr uint8_t kUltrasonicEchoPin = kUsePcbWiring ? 46 : A3;
constexpr uint8_t kServoPin = kUsePcbWiring ? 50 : 44;
constexpr int kServoOpenAngle = 20;
constexpr int kServoClosedAngle = 110;
constexpr uint8_t kAnalogPinA = A6;  // J15.2
constexpr uint8_t kAnalogPinB = A7;  // J15.1

MotorChannel g_channels[kMotorCount];

volatile uint8_t g_softPwmDuty[kMotorCount] = {0, 0, 0, 0};
volatile uint8_t* g_softPwmPort[kMotorCount] = {nullptr, nullptr, nullptr,
                                                nullptr};
uint8_t g_softPwmMask[kMotorCount] = {0, 0, 0, 0};
volatile uint8_t g_softPwmPhase = 0;

char g_line[kLineCapacity];
size_t g_lineLength = 0;
bool g_discardLine = false;

enum RunMode : uint8_t {
  RUN_NONE,
  RUN_MANUAL,
  RUN_GAIN,
  RUN_MAX,
  RUN_SEQ,
  RUN_BRIDGE,
  RUN_TURN_TIMED,
  RUN_TURN_STOPWATCH,
  RUN_TURN_AUTO,
};

enum Pending : uint8_t {
  PEND_NONE,
  PEND_COUNT_GAIN,
  PEND_COUNT_MAX,
  PEND_ANGLE,
};

RunMode g_run = RUN_NONE;
Pending g_pending = PEND_NONE;
uint8_t g_testMotor = 0;
unsigned long g_runStartedMs = 0;
unsigned long g_runDurationMs = 0;

// SEQ (motor a motor) e BRIDGE (ponte A ou B).
uint8_t g_seqStep = 0;
uint8_t g_seqDuty = kDefaultSeqDuty;
uint8_t g_bridgeFirstMotor = 0;
uint8_t g_bridgeStep = 0;

// Giro: ultimo giro executado e tabela de tempo para 90 graus por sentido
// (indice 0 = wz positivo, 1 = wz negativo).
int8_t g_lastTurnDir = 1;
uint8_t g_lastTurnDuty = 0;
unsigned long g_lastTurnMs = 0;
bool g_hasTurn[2] = {false, false};
uint8_t g_turnDuty[2] = {0, 0};
float g_turnMs90[2] = {0.0f, 0.0f};

// Dados de calibracao desta sessao.
uint8_t g_minDuty[kMotorCount] = {0, 0, 0, 0};
bool g_hasMinDuty[kMotorCount] = {false, false, false, false};
float g_gainTestTurns[kMotorCount] = {0, 0, 0, 0};
bool g_hasGainTest[kMotorCount] = {false, false, false, false};
float g_maxSpeedRpm[kMotorCount] = {0, 0, 0, 0};
bool g_hasMaxSpeed[kMotorCount] = {false, false, false, false};
float g_gain[kMotorCount] = {1.0f, 1.0f, 1.0f, 1.0f};
bool g_hasAllGains = false;

// Se ligado, os giros usam o duty minimo e o ganho medidos (ou o minimo padrao
// do firmware), reproduzindo o que o robo faz. Desligado, usa duty cru.
bool g_applyCalibration = true;

bool g_ultrasonicWatch = false;
unsigned long g_lastUltrasonicMs = 0;

Servo g_servo;
bool g_servoAttached = false;

ISR(TIMER2_COMPA_vect) {
  const uint8_t phase = g_softPwmPhase++;
  for (uint8_t i = 0; i < kMotorCount; ++i) {
    volatile uint8_t* port = g_softPwmPort[i];
    if (port == nullptr) {
      continue;
    }
    if (phase == 0) {
      if (g_softPwmDuty[i] != 0) {
        *port |= g_softPwmMask[i];
      } else {
        *port &= static_cast<uint8_t>(~g_softPwmMask[i]);
      }
    } else if (phase >= g_softPwmDuty[i]) {
      *port &= static_cast<uint8_t>(~g_softPwmMask[i]);
    }
  }
}

void initSoftPwm() {
  bool softPwmNeeded = false;
  for (uint8_t i = 0; i < kMotorCount; ++i) {
    if (digitalPinHasPWM(g_channels[i].enablePin)) {
      continue;
    }
    g_softPwmPort[i] =
        portOutputRegister(digitalPinToPort(g_channels[i].enablePin));
    g_softPwmMask[i] = digitalPinToBitMask(g_channels[i].enablePin);
    if (g_softPwmPort[i] == nullptr || g_softPwmMask[i] == 0) {
      g_softPwmPort[i] = nullptr;
      Serial.print(F("ERRO: nao foi possivel configurar PWM no motor "));
      Serial.println(i + 1);
      continue;
    }
    softPwmNeeded = true;
  }

  if (!softPwmNeeded) {
    return;
  }

  noInterrupts();
  TCCR2A = _BV(WGM21);  // CTC
  TCCR2B = _BV(CS21);   // prescaler 8 -> 2 MHz
  OCR2A = 63;           // 31,25 kHz -> 122 Hz de PWM
  TIMSK2 = _BV(OCIE2A);
  interrupts();
}

void writeEnable(uint8_t motorIndex, uint8_t duty) {
  if (g_softPwmPort[motorIndex] != nullptr) {
    g_softPwmDuty[motorIndex] = duty;
    return;
  }
  analogWrite(g_channels[motorIndex].enablePin, duty);
}

// ---------------------------------------------------------------------------
// Motores
// ---------------------------------------------------------------------------

void stopAllMotors() {
  for (uint8_t i = 0; i < kMotorCount; ++i) {
    writeEnable(i, 0);
    digitalWrite(g_channels[i].in1Pin, LOW);
    digitalWrite(g_channels[i].in2Pin, LOW);
  }
  g_run = RUN_NONE;
}

void cancelAndStop() {
  stopAllMotors();
  g_pending = PEND_NONE;
}

// Duty cru: ignora ganho e minimo, para medir o motor como ele e.
void setMotorRaw(uint8_t motorIndex, int speed) {
  if (motorIndex >= kMotorCount) {
    return;
  }

  speed = constrain(speed, -static_cast<int>(kMaxDuty),
                    static_cast<int>(kMaxDuty));
  writeEnable(motorIndex, 0);

  if (speed == 0) {
    digitalWrite(g_channels[motorIndex].in1Pin, LOW);
    digitalWrite(g_channels[motorIndex].in2Pin, LOW);
    return;
  }

  const bool reverse = speed < 0;
  digitalWrite(g_channels[motorIndex].in1Pin, reverse ? HIGH : LOW);
  digitalWrite(g_channels[motorIndex].in2Pin, reverse ? LOW : HIGH);
  writeEnable(motorIndex, static_cast<uint8_t>(abs(speed)));
}

uint8_t effectiveMinDuty(uint8_t motorIndex) {
  if (!g_applyCalibration) {
    return 0;
  }
  return g_hasMinDuty[motorIndex] ? g_minDuty[motorIndex] : kFirmwareMinDuty;
}

float effectiveGain(uint8_t motorIndex) {
  return (g_applyCalibration && g_hasAllGains) ? g_gain[motorIndex] : 1.0f;
}

// Mesma regra de dutyForSpeed() do firmware: ganho primeiro, depois o minimo.
uint8_t dutyForSpeed(uint8_t motorIndex, int magnitude) {
  if (magnitude <= 0) {
    return 0;
  }
  long duty = lround(magnitude * effectiveGain(motorIndex));
  if (duty < effectiveMinDuty(motorIndex)) {
    return 0;
  }
  if (duty > kMaxDuty) {
    duty = kMaxDuty;
  }
  return static_cast<uint8_t>(duty);
}

void setMotorCalibrated(uint8_t motorIndex, int speed) {
  const uint8_t duty = dutyForSpeed(motorIndex, abs(speed));
  setMotorRaw(motorIndex, speed < 0 ? -static_cast<int>(duty)
                                    : static_cast<int>(duty));
}

void updateGains() {
  g_hasAllGains = true;
  float slowest = 0.0f;
  for (uint8_t i = 0; i < kMotorCount; ++i) {
    if (!g_hasGainTest[i]) {
      g_hasAllGains = false;
      return;
    }
    if (i == 0 || g_gainTestTurns[i] < slowest) {
      slowest = g_gainTestTurns[i];
    }
  }
  for (uint8_t i = 0; i < kMotorCount; ++i) {
    g_gain[i] = slowest / g_gainTestTurns[i];
  }
}

void beginRun(RunMode mode, unsigned long durationMs) {
  stopAllMotors();
  if (g_pending != PEND_NONE) {
    Serial.println(F("Aviso: medicao pendente anterior descartada."));
    g_pending = PEND_NONE;
  }
  g_run = mode;
  g_runStartedMs = millis();
  g_runDurationMs = durationMs;
}

void printMotorStart(uint8_t motorIndex, int speed) {
  Serial.print(F("GIRANDO "));
  Serial.print(g_channels[motorIndex].name);
  Serial.print(F(" | duty "));
  Serial.print(abs(speed));
  Serial.print(F("/255 | sentido "));
  Serial.println(speed < 0 ? F("re") : F("frente"));
}

void startMotor(uint8_t motorIndex, int speed, RunMode mode,
                unsigned long durationMs) {
  beginRun(mode, durationMs);
  g_testMotor = motorIndex;
  setMotorRaw(motorIndex, speed);
  printMotorStart(motorIndex, speed);
}

// SEQ: cada motor 1,5 s para frente e 1,5 s para tras, em duty cru.
void applySeqStep() {
  stopAllMotors();
  g_run = RUN_SEQ;
  g_runStartedMs = millis();
  g_runDurationMs = kSeqStepMs;
  const uint8_t motorIndex = g_seqStep / 2;
  const int speed = (g_seqStep % 2 == 0) ? g_seqDuty : -static_cast<int>(g_seqDuty);
  g_testMotor = motorIndex;
  setMotorRaw(motorIndex, speed);
  Serial.print(F("[SEQ "));
  Serial.print(g_seqStep + 1);
  Serial.print(F("/8] "));
  printMotorStart(motorIndex, speed);
}

// BRIDGE: dois motores da mesma ponte, para frente e para tras, em duty cru.
void applyBridgeStep() {
  stopAllMotors();
  g_run = RUN_BRIDGE;
  g_runStartedMs = millis();
  g_runDurationMs = kBridgeStepMs;
  const int speed = (g_bridgeStep % 2 == 0) ? g_seqDuty : -static_cast<int>(g_seqDuty);
  setMotorRaw(g_bridgeFirstMotor, speed);
  setMotorRaw(g_bridgeFirstMotor + 1, speed);
  Serial.print(F("[PONTE "));
  Serial.print(g_bridgeFirstMotor == 0 ? 'A' : 'B');
  Serial.print(F("] M"));
  Serial.print(g_bridgeFirstMotor + 1);
  Serial.print(F("+M"));
  Serial.print(g_bridgeFirstMotor + 2);
  Serial.print(F(" | duty "));
  Serial.print(g_seqDuty);
  Serial.print(F(" | "));
  Serial.println(speed < 0 ? F("re") : F("frente"));
}

// ---------------------------------------------------------------------------
// Giro de 90 graus
// ---------------------------------------------------------------------------
//
// Gira sobre o proprio eixo com a mistura omni do firmware (vx = vy = 0):
// M1 = +wz, M2 = -wz, M3 = +wz, M4 = -wz. O robo nao tem giroscopio nesta
// rotina: o angulo e informado por voce com ANGLE, ou medido por cronometro
// com TURNT + STOP.

uint8_t turnIndex(int8_t direction) { return direction > 0 ? 0 : 1; }

const __FlashStringHelper* turnLabel(int8_t direction) {
  const bool clockwise = (direction > 0) == kPositiveWzIsClockwise;
  return clockwise ? F("horario") : F("anti-horario");
}

void applyRotation(int8_t direction, uint8_t duty) {
  const int wz = direction * static_cast<int>(duty);
  setMotorCalibrated(0, wz);
  setMotorCalibrated(1, -wz);
  setMotorCalibrated(2, wz);
  setMotorCalibrated(3, -wz);

  for (uint8_t i = 0; i < kMotorCount; ++i) {
    if (dutyForSpeed(i, duty) == 0) {
      Serial.print(F("AVISO: M"));
      Serial.print(i + 1);
      Serial.print(F(" fica parado: duty "));
      Serial.print(duty);
      Serial.print(F(" abaixo do minimo "));
      Serial.println(effectiveMinDuty(i));
    }
  }
}

void startTurn(int8_t direction, uint8_t duty, unsigned long durationMs,
               RunMode mode) {
  beginRun(mode, durationMs);
  g_lastTurnDir = direction;
  g_lastTurnDuty = duty;
  g_lastTurnMs = durationMs;
  applyRotation(direction, duty);
  Serial.print(F("GIRO "));
  Serial.print(turnLabel(direction));
  Serial.print(F(" (wz "));
  Serial.print(direction > 0 ? '+' : '-');
  Serial.print(F(") | duty "));
  Serial.print(duty);
  Serial.print(F(" | calibracao "));
  Serial.print(g_applyCalibration ? F("ligada") : F("desligada"));
  if (mode == RUN_TURN_STOPWATCH) {
    Serial.println(F(" | CRONOMETRO: envie STOP quando completar 90 graus."));
  } else {
    Serial.print(F(" | "));
    Serial.print(durationMs);
    Serial.println(F(" ms"));
  }
}

void printTurnTable() {
  Serial.println(F("\nGiro de 90 graus: sentido | duty | tempo (ms) | graus/s"));
  bool any = false;
  for (uint8_t i = 0; i < 2; ++i) {
    if (!g_hasTurn[i]) {
      continue;
    }
    any = true;
    const int8_t direction = (i == 0) ? 1 : -1;
    Serial.print(turnLabel(direction));
    Serial.print(F(" (wz "));
    Serial.print(direction > 0 ? '+' : '-');
    Serial.print(F(") | "));
    Serial.print(g_turnDuty[i]);
    Serial.print(F(" | "));
    Serial.print(g_turnMs90[i], 0);
    Serial.print(F(" | "));
    Serial.println(90000.0f / g_turnMs90[i], 1);
  }
  if (!any) {
    Serial.println(F("(sem medicoes: use TURN + ANGLE ou TURNT + STOP)"));
  }
}

void recordTurn(int8_t direction, uint8_t duty, float ms90) {
  const uint8_t index = turnIndex(direction);
  g_hasTurn[index] = true;
  g_turnDuty[index] = duty;
  g_turnMs90[index] = ms90;
  Serial.print(F("Para 90 graus ("));
  Serial.print(turnLabel(direction));
  Serial.print(F("): duty "));
  Serial.print(duty);
  Serial.print(F(" -> "));
  Serial.print(ms90, 0);
  Serial.print(F(" ms ("));
  Serial.print(90000.0f / ms90, 1);
  Serial.println(F(" graus/s)."));
  Serial.println(F("Valide com TURN90,<sentido>; refine com ANGLE,<graus>."));
}

// ---------------------------------------------------------------------------
// Sensores
// ---------------------------------------------------------------------------

unsigned long measureUltrasonicUs() {
  digitalWrite(kUltrasonicTrigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(kUltrasonicTrigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(kUltrasonicTrigPin, LOW);
  return pulseIn(kUltrasonicEchoPin, HIGH, kUltrasonicTimeoutUs);
}

void printUltrasonicReading() {
  const unsigned long duration = measureUltrasonicUs();
  if (duration == 0) {
    Serial.println(F("HC-SR04: sem eco (timeout)"));
    return;
  }
  Serial.print(F("HC-SR04: "));
  Serial.print(duration);
  Serial.print(F(" us | "));
  Serial.print(duration / 58.0f, 1);
  Serial.println(F(" cm"));
}

void printUltrasonicStats(uint8_t samples) {
  unsigned long minUs = 0;
  unsigned long maxUs = 0;
  unsigned long sumUs = 0;
  uint8_t valid = 0;
  for (uint8_t i = 0; i < samples; ++i) {
    const unsigned long duration = measureUltrasonicUs();
    if (duration != 0) {
      if (valid == 0 || duration < minUs) minUs = duration;
      if (valid == 0 || duration > maxUs) maxUs = duration;
      sumUs += duration;
      ++valid;
    }
    delay(60);  // deixa o eco anterior morrer antes do proximo disparo
  }

  Serial.print(F("HC-SR04 "));
  Serial.print(samples);
  Serial.print(F(" amostras: "));
  Serial.print(valid);
  Serial.print(F(" validas, "));
  Serial.print(samples - valid);
  Serial.println(F(" sem eco."));
  if (valid == 0) {
    return;
  }
  Serial.print(F("  min "));
  Serial.print(minUs / 58.0f, 1);
  Serial.print(F(" cm | media "));
  Serial.print((sumUs / static_cast<float>(valid)) / 58.0f, 1);
  Serial.print(F(" cm | max "));
  Serial.print(maxUs / 58.0f, 1);
  Serial.println(F(" cm"));
}

void printAnalogReadings() {
  const int a = analogRead(kAnalogPinA);
  const int b = analogRead(kAnalogPinB);
  Serial.print(F("A6 (J15.2): "));
  Serial.print(a);
  Serial.print(F(" = "));
  Serial.print(a * 5.0f / 1023.0f, 2);
  Serial.println(F(" V"));
  Serial.print(F("A7 (J15.1): "));
  Serial.print(b);
  Serial.print(F(" = "));
  Serial.print(b * 5.0f / 1023.0f, 2);
  Serial.println(F(" V"));
}

void moveServo(int angle) {
  angle = constrain(angle, kServoOpenAngle, kServoClosedAngle);
  if (!g_servoAttached) {
    g_servo.attach(kServoPin);
    g_servoAttached = true;
  }
  g_servo.write(angle);
  Serial.print(F("Servo da garra em "));
  Serial.print(angle);
  Serial.print(F(" graus (faixa "));
  Serial.print(kServoOpenAngle);
  Serial.print(F(".."));
  Serial.print(kServoClosedAngle);
  Serial.println(F(")."));
}

// ---------------------------------------------------------------------------
// Parsing
// ---------------------------------------------------------------------------

char* trimWhitespace(char* text) {
  while (*text != '\0' && isspace(static_cast<unsigned char>(*text))) {
    ++text;
  }
  char* end = text + strlen(text);
  while (end > text && isspace(static_cast<unsigned char>(end[-1]))) {
    *--end = '\0';
  }
  return text;
}

bool splitFields(char* line, char* fields[kFieldCount], size_t& count) {
  count = 0;
  fields[count++] = line;
  for (char* cursor = line; *cursor != '\0'; ++cursor) {
    if (*cursor != ',') {
      continue;
    }
    *cursor = '\0';
    if (count >= kFieldCount) {
      return false;
    }
    fields[count++] = cursor + 1;
  }

  for (size_t i = 0; i < count; ++i) {
    fields[i] = trimWhitespace(fields[i]);
    if (fields[i][0] == '\0') {
      return false;
    }
  }
  return true;
}

bool parseLongValue(const char* text, long& value) {
  errno = 0;
  char* end = nullptr;
  const long parsed = strtol(text, &end, 10);
  if (text == end || errno == ERANGE) {
    return false;
  }
  while (*end != '\0' && isspace(static_cast<unsigned char>(*end))) {
    ++end;
  }
  if (*end != '\0') {
    return false;
  }
  value = parsed;
  return true;
}

bool parsePositiveFloat(const char* text, float& value) {
  errno = 0;
  char* end = nullptr;
  const float parsed = strtof(text, &end);
  if (text == end || errno == ERANGE || isnan(parsed) || isinf(parsed) ||
      parsed <= 0.0f || parsed > 100000.0f) {
    return false;
  }
  while (*end != '\0' && isspace(static_cast<unsigned char>(*end))) {
    ++end;
  }
  if (*end != '\0') {
    return false;
  }
  value = parsed;
  return true;
}

bool parseMotorId(const char* text, uint8_t& motorIndex) {
  long id = 0;
  if (!parseLongValue(text, id) || id < 1 || id > kMotorCount) {
    return false;
  }
  motorIndex = static_cast<uint8_t>(id - 1);
  return true;
}

bool parseDuty(const char* text, uint8_t& duty) {
  long value = 0;
  if (!parseLongValue(text, value) || value < 1 || value > kMaxDuty) {
    return false;
  }
  duty = static_cast<uint8_t>(value);
  return true;
}

// Sentido do giro: "+" / "-" (sinal do wz) ou "H" / "A" (horario /
// anti-horario, conforme kPositiveWzIsClockwise).
bool parseDirection(const char* text, int8_t& direction) {
  if (strlen(text) != 1) {
    return false;
  }
  switch (toupper(static_cast<unsigned char>(text[0]))) {
    case '+':
      direction = 1;
      return true;
    case '-':
      direction = -1;
      return true;
    case 'H':
      direction = kPositiveWzIsClockwise ? 1 : -1;
      return true;
    case 'A':
      direction = kPositiveWzIsClockwise ? -1 : 1;
      return true;
    default:
      return false;
  }
}

void toUpperInPlace(char* text) {
  for (; *text != '\0'; ++text) {
    *text = static_cast<char>(toupper(static_cast<unsigned char>(*text)));
  }
}

bool parseOnOff(const char* text, bool& value) {
  if (strcmp(text, "ON") == 0) {
    value = true;
    return true;
  }
  if (strcmp(text, "OFF") == 0) {
    value = false;
    return true;
  }
  return false;
}

// ---------------------------------------------------------------------------
// Saida
// ---------------------------------------------------------------------------

void printHelp() {
  Serial.println(F("\n=== Teste universal de calibracao - Mega 2560 ==="));
  Serial.print(F("Montagem: "));
  Serial.println(kUsePcbWiring ? F("PCB") : F("protoboard"));
  Serial.println(F("Comandos (Nova linha no Monitor Serial; motor 1-4):"));
  Serial.println(F("-- Geral"));
  Serial.println(F("  HELP | STATUS | SUMMARY | RESET"));
  Serial.println(F("  STOP                         para tudo (e fecha o cronometro)"));
  Serial.println(F("-- Motores (duty cru)"));
  Serial.println(F("  RUN,<motor>,<duty -255..255>  aciona (para sozinho em 30 s)"));
  Serial.println(F("  SEQ[,<duty>]                 M1..M4, frente e re, 1,5 s cada"));
  Serial.println(F("  BRIDGE,<A|B>[,<duty>]        ponte A (M1+M2) ou B (M3+M4)"));
  Serial.println(F("  MIN,<motor>,<duty>           registra duty minimo medido"));
  Serial.println(F("  GAIN,<motor>                 10 s a duty 200 -> COUNT,<voltas>"));
  Serial.println(F("  MAX,<motor>                  10 s a duty 255 -> COUNT,<voltas>"));
  Serial.println(F("  COUNT,<voltas>               voltas contadas no teste de 10 s"));
  Serial.println(F("-- Giro de 90 graus (robo no chao)"));
  Serial.println(F("  TURN,<+|-|H|A>,<duty>,<ms>   gira por tempo fixo; depois informe"));
  Serial.println(F("  ANGLE,<graus>                angulo girado -> tempo para 90"));
  Serial.println(F("  TURNT,<+|-|H|A>,<duty>       gira ate o STOP: tempo de 90 = cronometro"));
  Serial.println(F("  TURN90,<+|-|H|A>             repete o giro de 90 medido"));
  Serial.println(F("  TURNS                        tabela de giros medidos"));
  Serial.println(F("  APPLY,<ON|OFF>               giros usam minimo/ganho medidos"));
  Serial.println(F("-- Sensores e garra"));
  Serial.println(F("  US                           uma leitura do HC-SR04"));
  Serial.println(F("  USWATCH,<ON|OFF>             leitura continua (250 ms)"));
  Serial.println(F("  USSTAT,<1..50>               min/media/max de N leituras"));
  Serial.println(F("  ANALOG                       entradas A6 e A7 (J15)"));
  Serial.println(F("  SERVO,<OPEN|CLOSE|20..110>   garra"));
  Serial.println(F("MIN: medir com o robo no chao. GAIN/MAX: suspender o robo."));
  Serial.println(F("Medicao de voltas e de angulo e manual; nao ha encoder nem IMU."));
}

void printValueOrDash(bool available, float value, uint8_t decimals) {
  if (!available) {
    Serial.print(F("--"));
  } else {
    Serial.print(value, decimals);
  }
}

void printStatus() {
  Serial.println(F("\n--- Estado ---"));
  Serial.print(F("Montagem: "));
  Serial.println(kUsePcbWiring ? F("PCB") : F("protoboard"));
  for (uint8_t i = 0; i < kMotorCount; ++i) {
    Serial.print(g_channels[i].name);
    Serial.print(F(" | EN D"));
    Serial.print(g_channels[i].enablePin);
    Serial.print(g_softPwmPort[i] != nullptr ? F(" [PWM software]") : F(" [PWM hardware]"));
    Serial.print(F(" | IN1 D"));
    Serial.print(g_channels[i].in1Pin);
    Serial.print(F(" | IN2 D"));
    Serial.println(g_channels[i].in2Pin);
  }
  Serial.print(F("HC-SR04: TRIG D"));
  Serial.print(kUltrasonicTrigPin);
  Serial.print(F(" | ECHO D"));
  Serial.println(kUltrasonicEchoPin);
  Serial.print(F("Servo: D"));
  Serial.println(kServoPin);
  Serial.print(F("Calibracao nos giros: "));
  Serial.println(g_applyCalibration ? F("ligada") : F("desligada"));
  Serial.print(F("Teste em andamento: "));
  Serial.println(g_run == RUN_NONE ? F("nenhum") : F("sim (STOP para encerrar)"));
  Serial.print(F("Medicao pendente: "));
  switch (g_pending) {
    case PEND_COUNT_GAIN:
    case PEND_COUNT_MAX:
      Serial.println(F("COUNT,<voltas>"));
      break;
    case PEND_ANGLE:
      Serial.println(F("ANGLE,<graus>"));
      break;
    default:
      Serial.println(F("nenhuma"));
      break;
  }
}

void printSummary() {
  Serial.println(F("\nMotor | minimo duty | voltas @200/10s | RPM @255"));
  bool allMinDuty = true;
  bool allMaxTests = true;
  for (uint8_t i = 0; i < kMotorCount; ++i) {
    Serial.print(i + 1);
    Serial.print(F("     | "));
    if (g_hasMinDuty[i]) {
      Serial.print(g_minDuty[i]);
    } else {
      Serial.print(F("--"));
      allMinDuty = false;
    }
    Serial.print(F("           | "));
    printValueOrDash(g_hasGainTest[i], g_gainTestTurns[i], 2);
    Serial.print(F("             | "));
    printValueOrDash(g_hasMaxSpeed[i], g_maxSpeedRpm[i], 1);
    Serial.println();
    allMaxTests = allMaxTests && g_hasMaxSpeed[i];
  }

  if (allMinDuty && g_hasAllGains) {
    Serial.println(F("\nCopie para robot_mega_pcb.ino:"));
    Serial.print(F("constexpr uint8_t kMotorMinDuty[4] = {"));
    for (uint8_t i = 0; i < kMotorCount; ++i) {
      if (i != 0) Serial.print(F(", "));
      Serial.print(g_minDuty[i]);
    }
    Serial.println(F("};"));
    Serial.print(F("constexpr float kMotorGain[4] = {"));
    for (uint8_t i = 0; i < kMotorCount; ++i) {
      if (i != 0) Serial.print(F(", "));
      Serial.print(g_gain[i], 3);
      Serial.print('f');
    }
    Serial.println(F("};"));
    Serial.println(F("O motor mais lento recebe ganho 1.000; os demais ficam <= 1."));
  } else {
    Serial.println(F("\nConstantes ainda incompletas: registre MIN e GAIN nos 4 motores."));
  }

  if (allMaxTests) {
    Serial.println(F("RPM @ duty 255 medido nos quatro motores; limite eletrico continua 255."));
  } else {
    Serial.println(F("MAX e opcional: complete MAX nos quatro para comparar RPM a duty 255."));
  }

  printTurnTable();
}

void resetData() {
  cancelAndStop();
  memset(g_minDuty, 0, sizeof(g_minDuty));
  memset(g_hasMinDuty, 0, sizeof(g_hasMinDuty));
  memset(g_gainTestTurns, 0, sizeof(g_gainTestTurns));
  memset(g_hasGainTest, 0, sizeof(g_hasGainTest));
  memset(g_maxSpeedRpm, 0, sizeof(g_maxSpeedRpm));
  memset(g_hasMaxSpeed, 0, sizeof(g_hasMaxSpeed));
  for (uint8_t i = 0; i < kMotorCount; ++i) {
    g_gain[i] = 1.0f;
  }
  g_hasAllGains = false;
  g_hasTurn[0] = g_hasTurn[1] = false;
  g_turnDuty[0] = g_turnDuty[1] = 0;
  g_turnMs90[0] = g_turnMs90[1] = 0.0f;
}

// ---------------------------------------------------------------------------
// Comandos
// ---------------------------------------------------------------------------

void handleCount(const char* text) {
  if (g_pending != PEND_COUNT_GAIN && g_pending != PEND_COUNT_MAX) {
    Serial.println(F("ERRO: nenhum teste de 10 s aguardando COUNT."));
    return;
  }

  float turns = 0.0f;
  if (!parsePositiveFloat(text, turns)) {
    Serial.println(F("ERRO: COUNT exige voltas > 0, por exemplo COUNT,12.5."));
    return;
  }

  if (g_pending == PEND_COUNT_GAIN) {
    g_gainTestTurns[g_testMotor] = turns;
    g_hasGainTest[g_testMotor] = true;
    updateGains();
    Serial.print(F("Voltas registradas para M"));
    Serial.print(g_testMotor + 1);
    Serial.println(F(" no teste de ganho."));
  } else {
    g_maxSpeedRpm[g_testMotor] = turns * 6.0f;
    g_hasMaxSpeed[g_testMotor] = true;
    Serial.print(F("Velocidade maxima medida para M"));
    Serial.print(g_testMotor + 1);
    Serial.print(F(": "));
    Serial.print(g_maxSpeedRpm[g_testMotor], 1);
    Serial.println(F(" RPM."));
  }
  g_pending = PEND_NONE;
}

void handleAngle(const char* text) {
  if (g_pending != PEND_ANGLE) {
    Serial.println(F("ERRO: nenhum giro aguardando ANGLE (rode TURN ou TURN90)."));
    return;
  }

  float degrees = 0.0f;
  if (!parsePositiveFloat(text, degrees) || degrees > 3600.0f) {
    Serial.println(F("ERRO: ANGLE exige graus > 0, por exemplo ANGLE,82."));
    return;
  }

  Serial.print(F("Giro de "));
  Serial.print(degrees, 1);
  Serial.print(F(" graus em "));
  Serial.print(g_lastTurnMs);
  Serial.print(F(" ms a duty "));
  Serial.print(g_lastTurnDuty);
  Serial.print(F(" = "));
  Serial.print(degrees * 1000.0f / g_lastTurnMs, 1);
  Serial.println(F(" graus/s."));
  recordTurn(g_lastTurnDir, g_lastTurnDuty, 90.0f * g_lastTurnMs / degrees);
  g_pending = PEND_NONE;
}

bool rejectIfBusy() {
  if (g_run == RUN_NONE) {
    return false;
  }
  Serial.println(F("ERRO: ha um teste em andamento; aguarde ou use STOP."));
  return true;
}

void handleStop() {
  if (g_run == RUN_TURN_STOPWATCH) {
    const unsigned long elapsed = millis() - g_runStartedMs;
    const int8_t direction = g_lastTurnDir;
    const uint8_t duty = g_lastTurnDuty;
    cancelAndStop();
    Serial.print(F("Cronometro: "));
    Serial.print(elapsed);
    Serial.println(F(" ms."));
    if (elapsed >= kTurnMinMs) {
      recordTurn(direction, duty, static_cast<float>(elapsed));
    }
    return;
  }
  g_ultrasonicWatch = false;
  cancelAndStop();
  Serial.println(F("Motores parados; teste pendente cancelado."));
}

void handleCommand(char* line) {
  char* fields[kFieldCount];
  size_t count = 0;
  if (!splitFields(line, fields, count)) {
    Serial.println(F("ERRO: comando CSV invalido; use HELP."));
    return;
  }

  toUpperInPlace(fields[0]);
  const char* name = fields[0];

  // Comandos sem argumento.
  if (count == 1) {
    if (strcmp(name, "HELP") == 0) {
      printHelp();
    } else if (strcmp(name, "STATUS") == 0) {
      printStatus();
    } else if (strcmp(name, "STOP") == 0) {
      handleStop();
    } else if (strcmp(name, "SUMMARY") == 0) {
      printSummary();
    } else if (strcmp(name, "TURNS") == 0) {
      printTurnTable();
    } else if (strcmp(name, "RESET") == 0) {
      resetData();
      Serial.println(F("Dados de calibracao apagados."));
    } else if (strcmp(name, "US") == 0) {
      printUltrasonicReading();
    } else if (strcmp(name, "ANALOG") == 0) {
      printAnalogReadings();
    } else if (strcmp(name, "SEQ") == 0) {
      if (rejectIfBusy()) return;
      g_seqDuty = kDefaultSeqDuty;
      g_seqStep = 0;
      beginRun(RUN_SEQ, kSeqStepMs);
      applySeqStep();
    } else {
      Serial.println(F("ERRO: comando desconhecido ou argumentos invalidos; use HELP."));
    }
    return;
  }

  if (strcmp(name, "COUNT") == 0 && count == 2) {
    handleCount(fields[1]);
    return;
  }
  if (strcmp(name, "ANGLE") == 0 && count == 2) {
    handleAngle(fields[1]);
    return;
  }

  if (strcmp(name, "APPLY") == 0 && count == 2) {
    bool enabled = true;
    toUpperInPlace(fields[1]);
    if (!parseOnOff(fields[1], enabled)) {
      Serial.println(F("ERRO: use APPLY,ON ou APPLY,OFF."));
      return;
    }
    g_applyCalibration = enabled;
    Serial.print(F("Calibracao nos giros: "));
    Serial.println(enabled ? F("ligada (minimo/ganho medidos, senao minimo 110).")
                           : F("desligada (duty cru)."));
    return;
  }

  if (strcmp(name, "USWATCH") == 0 && count == 2) {
    toUpperInPlace(fields[1]);
    bool enabled = false;
    if (!parseOnOff(fields[1], enabled)) {
      Serial.println(F("ERRO: use USWATCH,ON ou USWATCH,OFF."));
      return;
    }
    g_ultrasonicWatch = enabled;
    g_lastUltrasonicMs = 0;
    Serial.println(enabled ? F("Monitor do HC-SR04 ligado; STOP ou USWATCH,OFF encerra.")
                           : F("Monitor do HC-SR04 desligado."));
    return;
  }

  if (strcmp(name, "USSTAT") == 0 && count == 2) {
    long samples = 0;
    if (!parseLongValue(fields[1], samples) || samples < 1 ||
        samples > kUltrasonicStatMaxSamples) {
      Serial.println(F("ERRO: use USSTAT,<1..50>."));
      return;
    }
    if (rejectIfBusy()) return;
    printUltrasonicStats(static_cast<uint8_t>(samples));
    return;
  }

  if (strcmp(name, "SERVO") == 0 && count == 2) {
    toUpperInPlace(fields[1]);
    long angle = 0;
    if (strcmp(fields[1], "OPEN") == 0) {
      moveServo(kServoOpenAngle);
    } else if (strcmp(fields[1], "CLOSE") == 0) {
      moveServo(kServoClosedAngle);
    } else if (parseLongValue(fields[1], angle)) {
      moveServo(static_cast<int>(angle));
    } else {
      Serial.println(F("ERRO: use SERVO,OPEN, SERVO,CLOSE ou SERVO,<20..110>."));
    }
    return;
  }

  if (strcmp(name, "RUN") == 0 && count == 3) {
    if (g_run != RUN_NONE && g_run != RUN_MANUAL) {
      rejectIfBusy();
      return;
    }
    uint8_t motorIndex = 0;
    long duty = 0;
    if (!parseMotorId(fields[1], motorIndex) ||
        !parseLongValue(fields[2], duty) || duty < -kMaxDuty ||
        duty > kMaxDuty) {
      Serial.println(F("ERRO: use RUN,<motor 1-4>,<-255..255>."));
      return;
    }
    if (duty == 0) {
      cancelAndStop();
      Serial.println(F("Motores parados."));
      return;
    }
    startMotor(motorIndex, static_cast<int>(duty), RUN_MANUAL,
               kManualRunTimeoutMs);
    return;
  }

  if (strcmp(name, "MIN") == 0 && count == 3) {
    uint8_t motorIndex = 0;
    uint8_t duty = 0;
    if (!parseMotorId(fields[1], motorIndex) || !parseDuty(fields[2], duty)) {
      Serial.println(F("ERRO: use MIN,<motor 1-4>,<duty 1..255>."));
      return;
    }
    g_minDuty[motorIndex] = duty;
    g_hasMinDuty[motorIndex] = true;
    Serial.print(F("Duty minimo registrado para M"));
    Serial.print(motorIndex + 1);
    Serial.print(F(": "));
    Serial.println(duty);
    return;
  }

  if ((strcmp(name, "GAIN") == 0 || strcmp(name, "MAX") == 0) && count == 2) {
    if (rejectIfBusy()) return;
    uint8_t motorIndex = 0;
    if (!parseMotorId(fields[1], motorIndex)) {
      Serial.println(F("ERRO: motor deve ser 1, 2, 3 ou 4."));
      return;
    }
    const bool isGainTest = strcmp(name, "GAIN") == 0;
    startMotor(motorIndex, isGainTest ? kGainTestDuty : kMaxDuty,
               isGainTest ? RUN_GAIN : RUN_MAX, kMeasurementDurationMs);
    Serial.println(isGainTest
                       ? F("Conte as voltas completas em 10 s; o motor parara sozinho.")
                       : F("Conte as voltas em 10 s a duty maximo; o motor parara sozinho."));
    return;
  }

  if (strcmp(name, "SEQ") == 0 && count == 2) {
    if (rejectIfBusy()) return;
    uint8_t duty = 0;
    if (!parseDuty(fields[1], duty)) {
      Serial.println(F("ERRO: use SEQ,<duty 1..255>."));
      return;
    }
    g_seqDuty = duty;
    g_seqStep = 0;
    beginRun(RUN_SEQ, kSeqStepMs);
    applySeqStep();
    return;
  }

  if (strcmp(name, "BRIDGE") == 0 && (count == 2 || count == 3)) {
    if (rejectIfBusy()) return;
    const char side = static_cast<char>(toupper(static_cast<unsigned char>(fields[1][0])));
    uint8_t duty = kDefaultSeqDuty;
    if (strlen(fields[1]) != 1 || (side != 'A' && side != 'B') ||
        (count == 3 && !parseDuty(fields[2], duty))) {
      Serial.println(F("ERRO: use BRIDGE,<A|B>[,<duty 1..255>]."));
      return;
    }
    g_seqDuty = duty;
    g_bridgeFirstMotor = (side == 'A') ? 0 : 2;
    g_bridgeStep = 0;
    beginRun(RUN_BRIDGE, kBridgeStepMs);
    applyBridgeStep();
    return;
  }

  if (strcmp(name, "TURN") == 0 && count == 4) {
    if (rejectIfBusy()) return;
    int8_t direction = 1;
    uint8_t duty = 0;
    long durationMs = 0;
    if (!parseDirection(fields[1], direction) || !parseDuty(fields[2], duty) ||
        !parseLongValue(fields[3], durationMs) ||
        durationMs < static_cast<long>(kTurnMinMs) ||
        durationMs > static_cast<long>(kTurnMaxMs)) {
      Serial.println(F("ERRO: use TURN,<+|-|H|A>,<duty 1..255>,<ms 50..30000>."));
      return;
    }
    startTurn(direction, duty, static_cast<unsigned long>(durationMs),
              RUN_TURN_TIMED);
    return;
  }

  if (strcmp(name, "TURNT") == 0 && count == 3) {
    if (rejectIfBusy()) return;
    int8_t direction = 1;
    uint8_t duty = 0;
    if (!parseDirection(fields[1], direction) || !parseDuty(fields[2], duty)) {
      Serial.println(F("ERRO: use TURNT,<+|-|H|A>,<duty 1..255>."));
      return;
    }
    startTurn(direction, duty, kTurnMaxMs, RUN_TURN_STOPWATCH);
    return;
  }

  if (strcmp(name, "TURN90") == 0 && count == 2) {
    if (rejectIfBusy()) return;
    int8_t direction = 1;
    if (!parseDirection(fields[1], direction)) {
      Serial.println(F("ERRO: use TURN90,<+|-|H|A>."));
      return;
    }
    const uint8_t index = turnIndex(direction);
    if (!g_hasTurn[index]) {
      Serial.println(F("ERRO: sem medicao nesse sentido; use TURN + ANGLE ou TURNT + STOP."));
      return;
    }
    startTurn(direction, g_turnDuty[index],
              static_cast<unsigned long>(g_turnMs90[index] + 0.5f),
              RUN_TURN_AUTO);
    return;
  }

  Serial.println(F("ERRO: comando desconhecido ou argumentos invalidos; use HELP."));
}

void processSerial() {
  while (Serial.available() > 0) {
    const char value = static_cast<char>(Serial.read());
    if (value == '\r') {
      continue;
    }
    if (value == '\n') {
      if (g_discardLine) {
        Serial.println(F("ERRO: linha muito longa; motores parados."));
        g_discardLine = false;
      } else if (g_lineLength > 0) {
        g_line[g_lineLength] = '\0';
        handleCommand(g_line);
      }
      g_lineLength = 0;
      continue;
    }
    if (g_discardLine) {
      continue;
    }
    if (g_lineLength >= sizeof(g_line) - 1) {
      cancelAndStop();
      g_discardLine = true;
      g_lineLength = 0;
      continue;
    }
    g_line[g_lineLength++] = value;
  }
}

void handleRunTimeout() {
  if (g_run == RUN_NONE) {
    return;
  }
  if (millis() - g_runStartedMs < g_runDurationMs) {
    return;
  }

  switch (g_run) {
    case RUN_MANUAL:
      stopAllMotors();
      Serial.println(F("Tempo maximo de acionamento atingido; motores parados."));
      break;

    case RUN_GAIN:
    case RUN_MAX:
      g_pending = (g_run == RUN_GAIN) ? PEND_COUNT_GAIN : PEND_COUNT_MAX;
      stopAllMotors();
      Serial.print(F("Teste de M"));
      Serial.print(g_testMotor + 1);
      Serial.println(F(" terminou. Envie COUNT,<voltas contadas>."));
      break;

    case RUN_SEQ:
      ++g_seqStep;
      if (g_seqStep < kMotorCount * 2) {
        applySeqStep();
      } else {
        stopAllMotors();
        Serial.println(F("Sequencia concluida. Confira qual roda girou em cada passo."));
      }
      break;

    case RUN_BRIDGE:
      ++g_bridgeStep;
      if (g_bridgeStep < 2) {
        applyBridgeStep();
      } else {
        stopAllMotors();
        Serial.println(F("Teste de ponte concluido."));
      }
      break;

    case RUN_TURN_TIMED:
    case RUN_TURN_AUTO:
      stopAllMotors();
      g_pending = PEND_ANGLE;
      Serial.print(F("Giro de "));
      Serial.print(g_lastTurnMs);
      Serial.println(F(" ms terminou. Envie ANGLE,<graus girados> para calcular o tempo de 90."));
      break;

    case RUN_TURN_STOPWATCH:
      stopAllMotors();
      Serial.println(F("Cronometro estourou 30 s; motores parados, nada registrado."));
      break;

    default:
      stopAllMotors();
      break;
  }
}

void handleUltrasonicWatch() {
  if (!g_ultrasonicWatch) {
    return;
  }
  const unsigned long now = millis();
  if (g_lastUltrasonicMs != 0 && now - g_lastUltrasonicMs < kUltrasonicWatchMs) {
    return;
  }
  g_lastUltrasonicMs = now == 0 ? 1 : now;
  printUltrasonicReading();
}

void setup() {
  Serial.begin(115200);

  for (uint8_t i = 0; i < kMotorCount; ++i) {
    g_channels[i] = kUsePcbWiring ? kPcbChannels[i] : kBreadboardChannels[i];
    pinMode(g_channels[i].enablePin, OUTPUT);
    pinMode(g_channels[i].in1Pin, OUTPUT);
    pinMode(g_channels[i].in2Pin, OUTPUT);
    digitalWrite(g_channels[i].enablePin, LOW);
    digitalWrite(g_channels[i].in1Pin, LOW);
    digitalWrite(g_channels[i].in2Pin, LOW);
  }

  pinMode(kUltrasonicTrigPin, OUTPUT);
  pinMode(kUltrasonicEchoPin, INPUT);
  digitalWrite(kUltrasonicTrigPin, LOW);

  initSoftPwm();
  stopAllMotors();
  Serial.println(F("Teste universal iniciado: Arduino Mega 2560."));
  Serial.println(F("Confirme STBY em HIGH e GND comum antes de acionar."));
  printHelp();
}

void loop() {
  processSerial();
  handleRunTimeout();
  handleUltrasonicWatch();
}
