#include <Arduino.h>
#include <Servo.h>

// ===========================================================================
// Sketch para Arduino Mega 2560 com a PCB (HARDWARE.md, secao "Montagem com a PCB customizada")
// ===========================================================================
//
// Variante do robot_mega.ino para a placa. O sketch original continua valido
// para a montagem em protoboard e nao deve ser apagado: os dois mapeamentos
// nao tem um unico pino em comum.
//
// A diferenca que obriga um sketch separado: os enables das pontes H estao em
// D23, D33, D43 e D53, e nenhum desses pinos tem PWM por hardware no Mega
// (so 2 a 13 e 44 a 46 tem). analogWrite neles nao falha, mas vira
// digitalWrite: os motores so teriam liga e desliga. Por isso o PWM aqui e
// gerado por software, com uma interrupcao de timer que chaveia os pinos e
// produz a tensao media desejada.
//
// PROTOCOLO: identico ao robot_mega.ino, mais os comandos CAL de calibracao.

// Pinagem de HARDWARE.md, com a topologia conferida contra o
// netlist do Fritzing. Nenhum destes pinos de enable tem PWM de hardware.
//
// --- Ponte H A: J3 (Motor 1) e J2 (Motor 2) -------------------------------
constexpr uint8_t kBridgeAChannelAEnablePin = 33;  // PWMA (soft PWM) -> J3
constexpr uint8_t kBridgeAChannelAIn1Pin = 29;     // AIN1
constexpr uint8_t kBridgeAChannelAIn2Pin = 31;     // AIN2

constexpr uint8_t kBridgeAChannelBEnablePin = 23;  // PWMB (soft PWM) -> J2
constexpr uint8_t kBridgeAChannelBIn1Pin = 27;     // BIN1
constexpr uint8_t kBridgeAChannelBIn2Pin = 25;     // BIN2

// --- Ponte H B: J5 (Motor 3) e J4 (Motor 4) -------------------------------
constexpr uint8_t kBridgeBChannelAEnablePin = 53;  // PWMA (soft PWM) -> J5
constexpr uint8_t kBridgeBChannelAIn1Pin = 49;     // AIN1
constexpr uint8_t kBridgeBChannelAIn2Pin = 51;     // AIN2

constexpr uint8_t kBridgeBChannelBEnablePin = 43;  // PWMB (soft PWM) -> J4
constexpr uint8_t kBridgeBChannelBIn1Pin = 47;     // BIN1
constexpr uint8_t kBridgeBChannelBIn2Pin = 45;     // BIN2

// Servo da garra: J8 na placa. J9 (D48) e J12 (D52) ficam livres.
constexpr uint8_t kServoPin = 50;

// Ultrassonico HC-SR04, ligado atravessando dois conectores de dois pinos:
//
//   J7 pino 2 -> VCC       J7 pino 1 -> ECHO/D46
//   J6 pino 2 -> TRIG/D44  J6 pino 1 -> GND
//
// A netlist do Fritzing nomeia explicitamente TRIG em D44 e ECHO em D46.
constexpr uint8_t kUltrasonicTrigPin = 44;
constexpr uint8_t kUltrasonicEchoPin = 46;
constexpr unsigned long kUltrasonicTimeoutUs = 23000;  // ~4 m

constexpr unsigned long kWatchdogTimeoutMs = 1000;
// O modo de calibracao suspende o watchdog para o motor girar continuamente.
// Sem um teto, um cabo solto deixaria a roda girando indefinidamente.
constexpr unsigned long kCalibrationTimeoutMs = 30000;
constexpr unsigned long kSerialBaudrate = 115200;
constexpr int kMaxMotorSpeed = 255;
constexpr int kServoOpenAngle = 20;
constexpr int kServoClosedAngle = 110;

// ===========================================================================
// Calibracao dos motores
// ===========================================================================
//
// Dois numeros por motor, medidos na bancada com os comandos CAL:
//
//   kMotorMinDuty  duty em que aquela roda comeca a girar com carga. Abaixo
//                  dele o comando vai a zero: uma roda que nao gira e melhor
//                  parada do que recebendo um valor que ela nao cumpre.
//   kMotorGain     ganho relativo, para que o mesmo comando produza a mesma
//                  velocidade nas quatro rodas. E o que faz o robo andar reto
//                  e o que torna a mistura omni fiel.
//
// O ganho NAO deve compensar a zona morta somando um offset. A mistura omni
// assume velocidade proporcional ao comando; deslocar a origem quebraria essa
// proporcao. Quem trata a zona morta e o fit_to_motor_deadband do Raspberry,
// que reduz o avanco ate a curva pedida caber na faixa util dos motores.
//
// Ordem: 0 = frente esquerda, 1 = tras esquerda, 2 = frente direita,
//        3 = tras direita.
//
// Ver arduino/CALIBRACAO_MOTORES.md para o procedimento.
constexpr uint8_t kMotorMinDuty[4] = {110, 110, 110, 110};
constexpr float kMotorGain[4] = {1.0f, 1.0f, 1.0f, 1.0f};

// ===========================================================================
// PWM por software
// ===========================================================================
//
// Timer2 em CTC dispara a 31,25 kHz. Cada canal conta 256 passos, entao a
// frequencia de PWM fica em 122 Hz — bem dentro do que o TB6612FNG aceita e
// suficiente para a inercia dos motores, que enxergam a tensao media.
//
// Custo: cerca de 8% da CPU. A escrita e feita direto no registrador da porta
// porque digitalWrite (uns 5 us) nao caberia nos 32 us entre interrupcoes.
//
// Efeito colateral conhecido: pulseIn conta ciclos com as interrupcoes ligadas,
// entao a medida do ultrassonico sai cerca de 8% maior enquanto o PWM por
// software esta ativo. O fator 0.01715 abaixo compensa isso quando aferido com
// o sensor apontado para um alvo em distancia conhecida.

volatile uint8_t g_softPwmDuty[4] = {0, 0, 0, 0};
volatile uint8_t* g_softPwmPort[4] = {nullptr, nullptr, nullptr, nullptr};
uint8_t g_softPwmMask[4] = {0, 0, 0, 0};
volatile uint8_t g_softPwmPhase = 0;
bool g_softPwmActive = false;

struct MotionCommand {
  float vx;
  float vy;
  float wz;
  bool active;
};

struct MotorChannel {
  uint8_t enablePin;
  uint8_t in1Pin;
  uint8_t in2Pin;
};

MotionCommand g_motionCommand = {0.0f, 0.0f, 0.0f, false};
unsigned long g_lastCommandMs = 0;
bool g_safetyStopActive = false;
bool g_calibrationMode = false;
unsigned long g_calibrationStartedMs = 0;

bool g_ultrasonicEnabled = false;
unsigned long g_lastUltrasonicMeasureMs = 0;
constexpr unsigned long kUltrasonicMeasureIntervalMs = 100;  // 10 Hz

Servo g_gripperServo;

// Indice logico -> conector da placa. Qual conector leva qual roda ainda
// precisa ser conferido na bancada com os comandos CAL.
MotorChannel g_channels[4] = {
    {kBridgeAChannelAEnablePin, kBridgeAChannelAIn1Pin, kBridgeAChannelAIn2Pin},  // 0: J3 (Motor 1)
    {kBridgeAChannelBEnablePin, kBridgeAChannelBIn1Pin, kBridgeAChannelBIn2Pin},  // 1: J2 (Motor 2)
    {kBridgeBChannelAEnablePin, kBridgeBChannelAIn1Pin, kBridgeBChannelAIn2Pin},  // 2: J5 (Motor 3)
    {kBridgeBChannelBEnablePin, kBridgeBChannelBIn1Pin, kBridgeBChannelBIn2Pin},  // 3: J4 (Motor 4)
};

ISR(TIMER2_COMPA_vect) {
  const uint8_t phase = g_softPwmPhase++;
  for (uint8_t i = 0; i < 4; ++i) {
    volatile uint8_t* port = g_softPwmPort[i];
    if (port == nullptr) {
      continue;
    }
    if (phase == 0) {
      if (g_softPwmDuty[i] != 0) {
        *port |= g_softPwmMask[i];
      } else {
        *port &= ~g_softPwmMask[i];
      }
    } else if (phase >= g_softPwmDuty[i]) {
      *port &= ~g_softPwmMask[i];
    }
  }
}

void initSoftPwm() {
  // Registra apenas os enables sem PWM de hardware. Se algum dia esses pinos
  // forem levados para a faixa 2-13 por jumper, o canal passa a usar
  // analogWrite sozinho, sem mais nenhuma mudanca no codigo.
  for (uint8_t i = 0; i < 4; ++i) {
    if (digitalPinHasPWM(g_channels[i].enablePin)) {
      continue;
    }
    g_softPwmPort[i] = portOutputRegister(digitalPinToPort(g_channels[i].enablePin));
    g_softPwmMask[i] = digitalPinToBitMask(g_channels[i].enablePin);
    g_softPwmActive = true;
  }

  if (!g_softPwmActive) {
    return;
  }

  noInterrupts();
  TCCR2A = _BV(WGM21);  // CTC
  TCCR2B = _BV(CS21);   // prescaler 8 -> 2 MHz
  OCR2A = 63;           // 2 MHz / 64 = 31,25 kHz -> 122 Hz de PWM
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

void initMotors() {
  for (uint8_t i = 0; i < 4; ++i) {
    pinMode(g_channels[i].enablePin, OUTPUT);
    pinMode(g_channels[i].in1Pin, OUTPUT);
    pinMode(g_channels[i].in2Pin, OUTPUT);
    digitalWrite(g_channels[i].enablePin, LOW);
    digitalWrite(g_channels[i].in1Pin, LOW);
    digitalWrite(g_channels[i].in2Pin, LOW);
  }
  initSoftPwm();
}

uint8_t dutyForSpeed(uint8_t motorIndex, int magnitude) {
  if (magnitude <= 0) {
    return 0;
  }
  long duty = lround(magnitude * kMotorGain[motorIndex]);
  if (duty < kMotorMinDuty[motorIndex]) {
    return 0;  // nao gira: parar e mais honesto que fingir
  }
  if (duty > kMaxMotorSpeed) {
    duty = kMaxMotorSpeed;
  }
  return static_cast<uint8_t>(duty);
}

void setMotorSpeed(uint8_t motorIndex, int speed) {
  if (motorIndex >= 4) {
    return;
  }

  speed = constrain(speed, -kMaxMotorSpeed, kMaxMotorSpeed);
  const bool reverse = speed < 0;
  const uint8_t duty = dutyForSpeed(motorIndex, abs(speed));

  digitalWrite(g_channels[motorIndex].in1Pin, reverse ? HIGH : LOW);
  digitalWrite(g_channels[motorIndex].in2Pin, reverse ? LOW : HIGH);
  writeEnable(motorIndex, duty);
}

void setMotorRawDuty(uint8_t motorIndex, int duty) {
  // Usado so pela calibracao: ignora ganho e minimo, para medir o motor cru.
  if (motorIndex >= 4) {
    return;
  }
  const bool reverse = duty < 0;
  const uint8_t magnitude = static_cast<uint8_t>(constrain(abs(duty), 0, kMaxMotorSpeed));
  digitalWrite(g_channels[motorIndex].in1Pin, reverse ? HIGH : LOW);
  digitalWrite(g_channels[motorIndex].in2Pin, reverse ? LOW : HIGH);
  writeEnable(motorIndex, magnitude);
}

void stopAllMotors() {
  for (uint8_t i = 0; i < 4; ++i) {
    digitalWrite(g_channels[i].in1Pin, LOW);
    digitalWrite(g_channels[i].in2Pin, LOW);
    writeEnable(i, 0);
  }
}

void applyOmniMotion(float vx, float vy, float wz) {
  const float frontLeft = vx + vy + wz;
  const float frontRight = -vx + vy + wz;
  const float rearLeft = -vx - vy + wz;
  const float rearRight = vx - vy + wz;

  const float maxAbs = max(max(abs(frontLeft), abs(frontRight)), max(abs(rearLeft), abs(rearRight)));
  const float scale = (maxAbs > kMaxMotorSpeed) ? (kMaxMotorSpeed / maxAbs) : 1.0f;

  if (g_safetyStopActive) {
    stopAllMotors();
    return;
  }

  // Ordem logica: 0 = frente esquerda, 1 = tras esquerda, 2 = frente direita,
  // 3 = tras direita. CONFERIR NA BANCADA com o motor_bench_test: a PCB numera
  // os conectores de J2 a J5 sem dizer qual roda e qual.
  setMotorSpeed(0, static_cast<int>(frontLeft * scale));
  setMotorSpeed(1, static_cast<int>(rearLeft * scale));
  setMotorSpeed(2, static_cast<int>(frontRight * scale));
  setMotorSpeed(3, static_cast<int>(rearRight * scale));
}

void stopMotion() {
  g_motionCommand.active = false;
  g_motionCommand.vx = 0.0f;
  g_motionCommand.vy = 0.0f;
  g_motionCommand.wz = 0.0f;
  stopAllMotors();
}

void initGripper() {
  g_gripperServo.attach(kServoPin);
  g_gripperServo.write(kServoOpenAngle);
}

void openGripper() {
  g_gripperServo.write(kServoOpenAngle);
}

void closeGripper() {
  g_gripperServo.write(kServoClosedAngle);
}

void resetWatchdog() {
  g_lastCommandMs = millis();
}

void initUltrasonic() {
  pinMode(kUltrasonicTrigPin, OUTPUT);
  pinMode(kUltrasonicEchoPin, INPUT);
  digitalWrite(kUltrasonicTrigPin, LOW);
}

unsigned long measureUltrasonic() {
  digitalWrite(kUltrasonicTrigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(kUltrasonicTrigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(kUltrasonicTrigPin, LOW);

  return pulseIn(kUltrasonicEchoPin, HIGH, kUltrasonicTimeoutUs);
}

void handleUltrasonic() {
  if (!g_ultrasonicEnabled) {
    return;
  }

  const unsigned long now = millis();
  if (now - g_lastUltrasonicMeasureMs < kUltrasonicMeasureIntervalMs) {
    return;
  }
  g_lastUltrasonicMeasureMs = now;

  const unsigned long duration = measureUltrasonic();
  if (duration > 0 && duration < kUltrasonicTimeoutUs) {
    const float distanceCm = duration * 0.01715f;
    if (distanceCm >= 2.0f && distanceCm <= 400.0f) {
      Serial.print("DIST,");
      Serial.println(distanceCm, 1);
    }
  }
}

void handleWatchdog() {
  if (g_calibrationMode) {
    // Durante a calibracao o motor precisa girar continuamente, mas nao para
    // sempre: passado o teto, o modo se encerra sozinho.
    if (millis() - g_calibrationStartedMs > kCalibrationTimeoutMs) {
      g_calibrationMode = false;
      stopMotion();
      resetWatchdog();
      Serial.println("CAL_TIMEOUT");
    }
    return;
  }
  if (millis() - g_lastCommandMs > kWatchdogTimeoutMs) {
    stopMotion();
    Serial.println("WATCHDOG");
    g_lastCommandMs = millis();
  }
}

void printCalibrationTable() {
  Serial.println("CAL_TABLE motor,minDuty,gain");
  for (uint8_t i = 0; i < 4; ++i) {
    Serial.print("CAL_TABLE ");
    Serial.print(i);
    Serial.print(',');
    Serial.print(kMotorMinDuty[i]);
    Serial.print(',');
    Serial.println(kMotorGain[i], 3);
  }
}

bool handleCalibrationCommand(const String& command) {
  // CAL            -> mostra a tabela atual
  // CAL,ON | OFF   -> entra/sai do modo (suspende o watchdog)
  // CAL,<m>,<duty> -> aciona um motor com duty cru, de -255 a 255
  if (command == "CAL") {
    printCalibrationTable();
    return true;
  }

  if (command == "CAL,ON") {
    g_calibrationMode = true;
    g_calibrationStartedMs = millis();
    stopMotion();
    Serial.println("CAL_ON");
    return true;
  }

  if (command == "CAL,OFF") {
    g_calibrationMode = false;
    stopMotion();
    resetWatchdog();
    Serial.println("CAL_OFF");
    return true;
  }

  if (!command.startsWith("CAL,")) {
    return false;
  }

  const int firstComma = command.indexOf(',');
  const int secondComma = command.indexOf(',', firstComma + 1);
  if (secondComma <= firstComma) {
    return false;
  }

  if (!g_calibrationMode) {
    Serial.println("CAL_OFF");  // acionar motor sem entrar no modo seria surpresa
    return true;
  }

  const int motorIndex = command.substring(firstComma + 1, secondComma).toInt();
  const int duty = command.substring(secondComma + 1).toInt();
  if (motorIndex < 0 || motorIndex > 3) {
    Serial.println("ERROR");
    return true;
  }

  g_motionCommand.active = false;
  stopAllMotors();
  g_calibrationStartedMs = millis();  // cada comando renova o teto de tempo
  setMotorRawDuty(static_cast<uint8_t>(motorIndex), duty);
  Serial.print("CAL_RUN ");
  Serial.print(motorIndex);
  Serial.print(',');
  Serial.println(duty);
  return true;
}

void handleCommand(const String& rawCommand) {
  String command = rawCommand;
  command.trim();
  command.toUpperCase();

  if (command == "EMERGENCY STOP" || command == "EMERGENCY_STOP") {
    g_safetyStopActive = true;
    g_calibrationMode = false;
    stopMotion();
    Serial.println("EMERGENCY_LOCKED");
    return;
  }

  if (command == "EMERGENCY RELEASE" || command == "EMERGENCY_RELEASE") {
    g_safetyStopActive = false;
    stopMotion();
    Serial.println("EMERGENCY_RELEASED");
    return;
  }

  if (command == "STOP") {
    stopMotion();
    Serial.println("OK");
    return;
  }

  if (command.startsWith("CAL")) {
    if (handleCalibrationCommand(command)) {
      return;
    }
  }

  if (command.startsWith("MOVE,")) {
    if (g_safetyStopActive) {
      stopMotion();
      Serial.println("EMERGENCY_LOCKED");
      return;
    }
    const int firstComma = command.indexOf(',');
    const int secondComma = command.indexOf(',', firstComma + 1);
    const int thirdComma = command.indexOf(',', secondComma + 1);

    if (firstComma > 0 && secondComma > firstComma && thirdComma > secondComma) {
      g_motionCommand.vx = command.substring(firstComma + 1, secondComma).toFloat();
      g_motionCommand.vy = command.substring(secondComma + 1, thirdComma).toFloat();
      g_motionCommand.wz = command.substring(thirdComma + 1).toFloat();
      g_motionCommand.active = true;
      g_calibrationMode = false;
      resetWatchdog();
      Serial.println("OK");
      return;
    }
  }

  if (command == "GRAB") {
    closeGripper();
    resetWatchdog();
    Serial.println("BALL_CAPTURED");
    return;
  }

  if (command == "RELEASE") {
    openGripper();
    resetWatchdog();
    Serial.println("BALL_DROPPED");
    return;
  }

  if (command.startsWith("SERVO,")) {
    const int separator = command.indexOf(',');
    if (separator > 0) {
      const int angle = command.substring(separator + 1).toInt();
      g_gripperServo.write(constrain(angle, kServoOpenAngle, kServoClosedAngle));
      Serial.println("OK");
      return;
    }
  }

  if (command == "PING") {
    resetWatchdog();
    Serial.println("PONG");
    return;
  }

  if (command == "HEARTBEAT") {
    resetWatchdog();
    Serial.println("OK");
    return;
  }

  if (command.startsWith("SENSOR,")) {
    // Formato: SENSOR,<nome>,<on|off>
    const int comma1 = command.indexOf(',');
    const int comma2 = command.indexOf(',', comma1 + 1);
    if (comma1 > 0 && comma2 > comma1) {
      const String sensor = command.substring(comma1 + 1, comma2);
      const String state = command.substring(comma2 + 1);
      if (sensor == "ULTRASONIC") {
        if (state == "ON") {
          g_ultrasonicEnabled = true;
          g_lastUltrasonicMeasureMs = millis();
          Serial.println("OK");
          return;
        }
        if (state == "OFF") {
          g_ultrasonicEnabled = false;
          Serial.println("OK");
          return;
        }
      }
    }
  }

  Serial.println("ERROR");
}

void setup() {
  Serial.begin(kSerialBaudrate);
  initMotors();
  initGripper();
  initUltrasonic();
  stopMotion();
  Serial.println("READY");
}

void loop() {
  if (Serial.available()) {
    const String command = Serial.readStringUntil('\n');
    handleCommand(command);
  }

  handleWatchdog();
  handleUltrasonic();

  if (g_calibrationMode) {
    delay(10);
    return;  // a calibracao mantem o duty cru que foi pedido
  }

  if (g_motionCommand.active) {
    applyOmniMotion(g_motionCommand.vx, g_motionCommand.vy, g_motionCommand.wz);
  } else {
    stopAllMotors();
  }

  delay(10);
}
