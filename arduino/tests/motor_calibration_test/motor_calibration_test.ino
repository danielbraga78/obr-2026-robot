#include <Arduino.h>
#include <ctype.h>
#include <errno.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

// Sketch independente para calibrar os motores da PCB com Arduino Mega 2560.
// Substitui temporariamente o firmware principal: regrave-o ao terminar.
// A ordem e os pinos espelham g_channels de robot_mega_pcb.ino.

constexpr uint8_t kMotorCount = 4;
constexpr uint8_t kMaxDuty = 255;
constexpr uint8_t kGainTestDuty = 200;
constexpr unsigned long kMeasurementDurationMs = 10000;
constexpr unsigned long kManualRunTimeoutMs = 30000;
constexpr size_t kLineCapacity = 48;
constexpr size_t kFieldCount = 4;

struct MotorChannel {
  uint8_t enablePin;
  uint8_t in1Pin;
  uint8_t in2Pin;
  const char* name;
};

// Ordem logica do firmware: frente esquerda, tras esquerda,
// frente direita, tras direita. Confirme os conectores na bancada.
constexpr MotorChannel kChannels[kMotorCount] = {
    {33, 29, 31, "M1 - J3 / ponte A canal A"},
    {23, 27, 25, "M2 - J2 / ponte A canal B"},
    {53, 49, 51, "M3 - J5 / ponte B canal A"},
    {43, 47, 45, "M4 - J4 / ponte B canal B"},
};

volatile uint8_t g_softPwmDuty[kMotorCount] = {0, 0, 0, 0};
volatile uint8_t* g_softPwmPort[kMotorCount] = {nullptr, nullptr, nullptr, nullptr};
uint8_t g_softPwmMask[kMotorCount] = {0, 0, 0, 0};
volatile uint8_t g_softPwmPhase = 0;

char g_line[kLineCapacity];
size_t g_lineLength = 0;
bool g_discardLine = false;

enum TestKind : uint8_t {
  TEST_NONE,
  TEST_GAIN,
  TEST_MAX_SPEED,
};

bool g_motorRunning = false;
bool g_timedTestRunning = false;
bool g_waitingForCount = false;
uint8_t g_testMotor = 0;
TestKind g_testKind = TEST_NONE;
unsigned long g_runStartedMs = 0;
unsigned long g_runDurationMs = 0;

uint8_t g_minDuty[kMotorCount] = {0, 0, 0, 0};
bool g_hasMinDuty[kMotorCount] = {false, false, false, false};
float g_gainTestTurns[kMotorCount] = {0, 0, 0, 0};
bool g_hasGainTest[kMotorCount] = {false, false, false, false};
float g_maxSpeedRpm[kMotorCount] = {0, 0, 0, 0};
bool g_hasMaxSpeed[kMotorCount] = {false, false, false, false};

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
    if (digitalPinHasPWM(kChannels[i].enablePin)) {
      continue;
    }
    g_softPwmPort[i] =
        portOutputRegister(digitalPinToPort(kChannels[i].enablePin));
    g_softPwmMask[i] = digitalPinToBitMask(kChannels[i].enablePin);
    if (g_softPwmPort[i] == nullptr || g_softPwmMask[i] == 0) {
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
  TCCR2A = _BV(WGM21);
  TCCR2B = _BV(CS21);
  OCR2A = 63;
  TIMSK2 = _BV(OCIE2A);
  interrupts();
}

void writeEnable(uint8_t motorIndex, uint8_t duty) {
  if (g_softPwmPort[motorIndex] != nullptr) {
    g_softPwmDuty[motorIndex] = duty;
    return;
  }
  analogWrite(kChannels[motorIndex].enablePin, duty);
}

void stopAllMotors() {
  for (uint8_t i = 0; i < kMotorCount; ++i) {
    writeEnable(i, 0);
    digitalWrite(kChannels[i].in1Pin, LOW);
    digitalWrite(kChannels[i].in2Pin, LOW);
  }
  g_motorRunning = false;
  g_timedTestRunning = false;
}

void cancelAndStop() {
  stopAllMotors();
  g_waitingForCount = false;
  g_testKind = TEST_NONE;
}

void setMotorSpeed(uint8_t motorIndex, int speed) {
  if (motorIndex >= kMotorCount) {
    return;
  }

  speed = constrain(speed, -static_cast<int>(kMaxDuty),
                    static_cast<int>(kMaxDuty));
  writeEnable(motorIndex, 0);

  if (speed == 0) {
    digitalWrite(kChannels[motorIndex].in1Pin, LOW);
    digitalWrite(kChannels[motorIndex].in2Pin, LOW);
    return;
  }

  const bool reverse = speed < 0;
  digitalWrite(kChannels[motorIndex].in1Pin, reverse ? HIGH : LOW);
  digitalWrite(kChannels[motorIndex].in2Pin, reverse ? LOW : HIGH);
  writeEnable(motorIndex, static_cast<uint8_t>(abs(speed)));
}

void startMotor(uint8_t motorIndex, int speed, TestKind kind,
                unsigned long durationMs) {
  stopAllMotors();
  g_waitingForCount = false;
  g_testKind = kind;
  g_testMotor = motorIndex;
  g_runStartedMs = millis();
  g_runDurationMs = durationMs;
  g_timedTestRunning = kind != TEST_NONE;
  g_motorRunning = true;
  setMotorSpeed(motorIndex, speed);
  Serial.print(F("GIRANDO "));
  Serial.print(kChannels[motorIndex].name);
  Serial.print(F(" | duty "));
  Serial.print(abs(speed));
  Serial.print(F("/255 | sentido "));
  Serial.println(speed < 0 ? F("re") : F("frente"));
}

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

bool parsePositiveTurns(const char* text, float& turns) {
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
  turns = parsed;
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

void printHelp() {
  Serial.println(F("\n=== Calibracao de motores - PCB / Mega 2560 ==="));
  Serial.println(F("Comandos (use Nova linha no Monitor Serial):"));
  Serial.println(F("  RUN,<motor 1-4>,<duty -255..255>  aciona manualmente"));
  Serial.println(F("  STOP                              para tudo"));
  Serial.println(F("  MIN,<motor 1-4>,<duty 1..255>    registra minimo medido"));
  Serial.println(F("  GAIN,<motor 1-4>                 teste de ganho a duty 200"));
  Serial.println(F("  MAX,<motor 1-4>                  teste de velocidade a duty 255"));
  Serial.println(F("  COUNT,<voltas>                   informa voltas contadas em 10 s"));
  Serial.println(F("  SUMMARY                          mostra tabela e constantes"));
  Serial.println(F("  RESET                            apaga dados desta sessao"));
  Serial.println(F("  HELP                             mostra esta ajuda"));
  Serial.println(F("RUN para automaticamente apos 30 s; testes param apos 10 s."));
  Serial.println(F("MIN: medir com o robo no chao. GAIN/MAX: suspender o robo."));
  Serial.println(F("Medicao de voltas e manual; nao ha encoder nesta rotina."));
}

void printValueOrDash(bool available, float value, uint8_t decimals) {
  if (!available) {
    Serial.print(F("--"));
  } else {
    Serial.print(value, decimals);
  }
}

void printSummary() {
  Serial.println(F("\nMotor | minimo duty | voltas @200/10s | RPM @255"));
  bool allMinDuty = true;
  bool allGainTests = true;
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
    allGainTests = allGainTests && g_hasGainTest[i];
    allMaxTests = allMaxTests && g_hasMaxSpeed[i];
  }

  if (allMinDuty && allGainTests) {
    float slowestTurns = g_gainTestTurns[0];
    for (uint8_t i = 1; i < kMotorCount; ++i) {
      if (g_gainTestTurns[i] < slowestTurns) {
        slowestTurns = g_gainTestTurns[i];
      }
    }

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
      Serial.print(slowestTurns / g_gainTestTurns[i], 3);
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
}

void handleCount(const char* text) {
  if (!g_waitingForCount) {
    Serial.println(F("ERRO: nenhum teste de 10 s aguardando COUNT."));
    return;
  }

  float turns = 0.0f;
  if (!parsePositiveTurns(text, turns)) {
    Serial.println(F("ERRO: COUNT exige voltas > 0, por exemplo COUNT,12.5."));
    return;
  }

  if (g_testKind == TEST_GAIN) {
    g_gainTestTurns[g_testMotor] = turns;
    g_hasGainTest[g_testMotor] = true;
    Serial.print(F("Voltas registradas para M"));
    Serial.print(g_testMotor + 1);
    Serial.println(F(" no teste de ganho."));
  } else if (g_testKind == TEST_MAX_SPEED) {
    g_maxSpeedRpm[g_testMotor] = turns * 6.0f;
    g_hasMaxSpeed[g_testMotor] = true;
    Serial.print(F("Velocidade maxima medida para M"));
    Serial.print(g_testMotor + 1);
    Serial.print(F(": "));
    Serial.print(g_maxSpeedRpm[g_testMotor], 1);
    Serial.println(F(" RPM."));
  }

  g_waitingForCount = false;
  g_testKind = TEST_NONE;
}

void handleCommand(char* line) {
  char* fields[kFieldCount];
  size_t count = 0;
  if (!splitFields(line, fields, count)) {
    Serial.println(F("ERRO: comando CSV invalido; use HELP."));
    return;
  }

  for (char* cursor = fields[0]; *cursor != '\0'; ++cursor) {
    *cursor = static_cast<char>(toupper(static_cast<unsigned char>(*cursor)));
  }

  if (strcmp(fields[0], "HELP") == 0 && count == 1) {
    printHelp();
    return;
  }
  if (strcmp(fields[0], "STOP") == 0 && count == 1) {
    cancelAndStop();
    Serial.println(F("Motores parados; teste pendente cancelado."));
    return;
  }
  if (strcmp(fields[0], "SUMMARY") == 0 && count == 1) {
    printSummary();
    return;
  }
  if (strcmp(fields[0], "RESET") == 0 && count == 1) {
    cancelAndStop();
    memset(g_minDuty, 0, sizeof(g_minDuty));
    memset(g_hasMinDuty, 0, sizeof(g_hasMinDuty));
    memset(g_gainTestTurns, 0, sizeof(g_gainTestTurns));
    memset(g_hasGainTest, 0, sizeof(g_hasGainTest));
    memset(g_maxSpeedRpm, 0, sizeof(g_maxSpeedRpm));
    memset(g_hasMaxSpeed, 0, sizeof(g_hasMaxSpeed));
    Serial.println(F("Dados de calibracao apagados."));
    return;
  }
  if (strcmp(fields[0], "COUNT") == 0 && count == 2) {
    handleCount(fields[1]);
    return;
  }

  if (strcmp(fields[0], "RUN") == 0 && count == 3) {
    if (g_timedTestRunning || g_waitingForCount) {
      Serial.println(F("ERRO: finalize o teste atual com COUNT ou STOP primeiro."));
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
    startMotor(motorIndex, static_cast<int>(duty), TEST_NONE,
               kManualRunTimeoutMs);
    return;
  }

  if (strcmp(fields[0], "MIN") == 0 && count == 3) {
    uint8_t motorIndex = 0;
    long duty = 0;
    if (!parseMotorId(fields[1], motorIndex) ||
        !parseLongValue(fields[2], duty) || duty < 1 ||
        duty > kMaxDuty) {
      Serial.println(F("ERRO: use MIN,<motor 1-4>,<duty 1..255>."));
      return;
    }
    g_minDuty[motorIndex] = static_cast<uint8_t>(duty);
    g_hasMinDuty[motorIndex] = true;
    Serial.print(F("Duty minimo registrado para M"));
    Serial.print(motorIndex + 1);
    Serial.print(F(": "));
    Serial.println(duty);
    return;
  }

  if ((strcmp(fields[0], "GAIN") == 0 ||
       strcmp(fields[0], "MAX") == 0) && count == 2) {
    if (g_timedTestRunning || g_waitingForCount) {
      Serial.println(F("ERRO: finalize o teste atual com COUNT ou STOP primeiro."));
      return;
    }
    uint8_t motorIndex = 0;
    if (!parseMotorId(fields[1], motorIndex)) {
      Serial.println(F("ERRO: motor deve ser 1, 2, 3 ou 4."));
      return;
    }
    const bool isGainTest = strcmp(fields[0], "GAIN") == 0;
    const uint8_t duty = isGainTest ? kGainTestDuty : kMaxDuty;
    startMotor(motorIndex, duty,
               isGainTest ? TEST_GAIN : TEST_MAX_SPEED,
               kMeasurementDurationMs);
    Serial.println(isGainTest
                       ? F("Conte as voltas completas em 10 s; o motor parara sozinho.")
                       : F("Conte as voltas em 10 s a duty maximo; o motor parara sozinho."));
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
  if (!g_motorRunning) {
    return;
  }
  if (millis() - g_runStartedMs < g_runDurationMs) {
    return;
  }

  const bool completedTimedTest = g_timedTestRunning;
  stopAllMotors();
  if (completedTimedTest) {
    g_waitingForCount = true;
    Serial.print(F("Teste de M"));
    Serial.print(g_testMotor + 1);
    Serial.println(F(" terminou. Envie COUNT,<voltas contadas>."));
  } else {
    Serial.println(F("Tempo maximo de acionamento atingido; motores parados."));
  }
}

void setup() {
  Serial.begin(115200);

  for (uint8_t i = 0; i < kMotorCount; ++i) {
    pinMode(kChannels[i].enablePin, OUTPUT);
    pinMode(kChannels[i].in1Pin, OUTPUT);
    pinMode(kChannels[i].in2Pin, OUTPUT);
    digitalWrite(kChannels[i].enablePin, LOW);
    digitalWrite(kChannels[i].in1Pin, LOW);
    digitalWrite(kChannels[i].in2Pin, LOW);
  }

  initSoftPwm();
  stopAllMotors();
  Serial.println(F("Calibrador iniciado: Arduino Mega 2560 + PCB TB6612FNG."));
  Serial.println(F("Confirme STBY em HIGH e GND comum antes de acionar."));
  printHelp();
}

void loop() {
  processSerial();
  handleRunTimeout();
}
