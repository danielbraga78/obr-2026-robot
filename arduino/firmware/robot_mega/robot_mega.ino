#include <Arduino.h>
#include <Servo.h>

// Sketch para Arduino Mega 2560 — mapeamento de pinos sugerido

// Ponte H A: motores da esquerda (frontal e traseiro)
constexpr uint8_t kBridgeAChannelAEnablePin = 2;   // PWM (Mega)
constexpr uint8_t kBridgeAChannelAIn1Pin = 22;
constexpr uint8_t kBridgeAChannelAIn2Pin = 23;

constexpr uint8_t kBridgeAChannelBEnablePin = 3;   // PWM (Mega)
constexpr uint8_t kBridgeAChannelBIn1Pin = 25;
constexpr uint8_t kBridgeAChannelBIn2Pin = 24;

// Ponte H B: motores da direita (frontal e traseiro)
constexpr uint8_t kBridgeBChannelAEnablePin = 4;   // PWM (Mega)
constexpr uint8_t kBridgeBChannelAIn1Pin = 26;
constexpr uint8_t kBridgeBChannelAIn2Pin = 27;

constexpr uint8_t kBridgeBChannelBEnablePin = 5;   // PWM (Mega)
constexpr uint8_t kBridgeBChannelBIn1Pin = 28;     // A4 mapped to digital 28
constexpr uint8_t kBridgeBChannelBIn2Pin = 29;     // A5 mapped to digital 29

constexpr uint8_t kServoPin = 44; // use a high-numbered PWM/servo pin

// Sensor ultrassônico HC-SR04 (opcional)
constexpr uint8_t kUltrasonicTrigPin = A2;
constexpr uint8_t kUltrasonicEchoPin = A3;
constexpr unsigned long kUltrasonicTimeoutUs = 23000;  // Timeout para ~4m

constexpr unsigned long kWatchdogTimeoutMs = 1000;
constexpr unsigned long kSerialBaudrate = 115200;
constexpr int kMaxMotorSpeed = 255;
constexpr int kMinMotorSpeed = 110;
constexpr int kServoOpenAngle = 20;
constexpr int kServoClosedAngle = 110;

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

struct HBridge {
  MotorChannel channelA;
  MotorChannel channelB;
};

MotionCommand g_motionCommand = {0.0f, 0.0f, 0.0f, false};
unsigned long g_lastCommandMs = 0;
bool g_safetyStopActive = false;

// Sensor ultrassônico
bool g_ultrasonicEnabled = false;
unsigned long g_lastUltrasonicMeasureMs = 0;
constexpr unsigned long kUltrasonicMeasureIntervalMs = 100;  // 10 Hz
constexpr size_t kSerialLineCapacity = 96;
char g_usbLine[kSerialLineCapacity];
char g_uartLine[kSerialLineCapacity];
size_t g_usbLineLength = 0;
size_t g_uartLineLength = 0;
Stream* g_activeControlPort = &Serial;
Stream* g_ultrasonicOutputPort = nullptr;
bool g_ultrasonicWaitingForEcho = false;
bool g_ultrasonicEchoStarted = false;
unsigned long g_ultrasonicTriggerUs = 0;
unsigned long g_ultrasonicEchoRiseUs = 0;

Servo g_gripperServo;
HBridge g_bridgeA = {
    {kBridgeAChannelAEnablePin, kBridgeAChannelAIn1Pin, kBridgeAChannelAIn2Pin},
    {kBridgeAChannelBEnablePin, kBridgeAChannelBIn1Pin, kBridgeAChannelBIn2Pin},
};
HBridge g_bridgeB = {
    {kBridgeBChannelAEnablePin, kBridgeBChannelAIn1Pin, kBridgeBChannelAIn2Pin},
    {kBridgeBChannelBEnablePin, kBridgeBChannelBIn1Pin, kBridgeBChannelBIn2Pin},
};

MotorChannel* getMotorChannel(uint8_t motorIndex) {
  switch (motorIndex) {
    case 0:
      return &g_bridgeA.channelA;
    case 1:
      return &g_bridgeA.channelB;
    case 2:
      return &g_bridgeB.channelA;
    case 3:
      return &g_bridgeB.channelB;
    default:
      return nullptr;
  }
}

void initMotors() {
  const MotorChannel* channels[4] = {
      &g_bridgeA.channelA,
      &g_bridgeA.channelB,
      &g_bridgeB.channelA,
      &g_bridgeB.channelB,
  };

  for (uint8_t i = 0; i < 4; ++i) {
    pinMode(channels[i]->enablePin, OUTPUT);
    pinMode(channels[i]->in1Pin, OUTPUT);
    pinMode(channels[i]->in2Pin, OUTPUT);
  }
  for (uint8_t i = 0; i < 4; ++i) {
    digitalWrite(channels[i]->in1Pin, LOW);
    digitalWrite(channels[i]->in2Pin, LOW);
    analogWrite(channels[i]->enablePin, 0);
  }
}

void setMotorSpeed(uint8_t motorIndex, int speed) {
  MotorChannel* channel = getMotorChannel(motorIndex);
  if (channel == nullptr) {
    return;
  }

  speed = constrain(speed, -kMaxMotorSpeed, kMaxMotorSpeed);
  // Abaixo do minimo a roda nao vence o atrito. Elevar ao minimo era pior que
  // parar: pedia 110 a uma roda que deveria estar quase parada, o que destruia
  // o diferencial nas curvas fechadas e deixava a malha de controle aberta.
  // Quem ajusta o comando para caber nesta faixa e o fit_to_motor_deadband do
  // Raspberry; aqui fica so a rede de seguranca.
  if (abs(speed) < kMinMotorSpeed) {
    speed = 0;
  }
  const bool reverse = speed < 0;
  const uint8_t pwmValue = static_cast<uint8_t>(abs(speed));

  digitalWrite(channel->in1Pin, reverse ? HIGH : LOW);
  digitalWrite(channel->in2Pin, reverse ? LOW : HIGH);
  analogWrite(channel->enablePin, pwmValue);
}

void stopAllMotors() {
  const MotorChannel* channels[4] = {
      &g_bridgeA.channelA,
      &g_bridgeA.channelB,
      &g_bridgeB.channelA,
      &g_bridgeB.channelB,
  };

  for (uint8_t i = 0; i < 4; ++i) {
    digitalWrite(channels[i]->in1Pin, LOW);
    digitalWrite(channels[i]->in2Pin, LOW);
    analogWrite(channels[i]->enablePin, 0);
  }
}

void applyOmniMotion(float vx, float vy, float wz) {
  // Mecanum (movimentos-robo-rodas-mecanum.md): vx > 0 avanca, vy > 0 desloca
  // para a direita e wz > 0 gira no sentido horario (esquerda contra direita).
  const float motor1 = vx + vy + wz;
  const float motor2 = vx - vy + wz;
  const float motor3 = vx - vy - wz;
  const float motor4 = vx + vy - wz;

  const float maxAbs = max(max(abs(motor1), abs(motor2)), max(abs(motor3), abs(motor4)));
  const float scale = (maxAbs > kMaxMotorSpeed) ? (kMaxMotorSpeed / maxAbs) : 1.0f;

  const int m1 = static_cast<int>(motor1 * scale);
  const int m2 = static_cast<int>(motor2 * scale);
  const int m3 = static_cast<int>(motor3 * scale);
  const int m4 = static_cast<int>(motor4 * scale);

  if (g_safetyStopActive) {
    stopAllMotors();
    return;
  }

  // Ordem lógica: motor 0 = frente esquerdo, motor 1 = trás esquerdo,
  // motor 2 = frente direito, motor 3 = trás direito.
  // Os motores da esquerda ficam na Ponte A e os da direita na Ponte B.
  setMotorSpeed(0, m1);
  setMotorSpeed(1, m2);
  setMotorSpeed(2, m3);
  setMotorSpeed(3, m4);
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

void setGripperAngle(int angle) {
  g_gripperServo.write(constrain(angle, kServoOpenAngle, kServoClosedAngle));
}

void resetWatchdog() {
  g_lastCommandMs = millis();
}

void initUltrasonic() {
  pinMode(kUltrasonicTrigPin, OUTPUT);
  pinMode(kUltrasonicEchoPin, INPUT);
  digitalWrite(kUltrasonicTrigPin, LOW);
}

void startUltrasonicMeasurement() {
  digitalWrite(kUltrasonicTrigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(kUltrasonicTrigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(kUltrasonicTrigPin, LOW);
  g_ultrasonicTriggerUs = micros();
  g_ultrasonicWaitingForEcho = true;
  g_ultrasonicEchoStarted = false;
}

void handleUltrasonic() {
  if (!g_ultrasonicEnabled) {
    return;
  }
  
  if (!g_ultrasonicWaitingForEcho) {
    const unsigned long now = millis();
    if (now - g_lastUltrasonicMeasureMs >= kUltrasonicMeasureIntervalMs) {
      g_lastUltrasonicMeasureMs = now;
      startUltrasonicMeasurement();
    }
    return;
  }

  const unsigned long nowUs = micros();
  const bool echoHigh = digitalRead(kUltrasonicEchoPin) == HIGH;
  if (!g_ultrasonicEchoStarted && echoHigh) {
    g_ultrasonicEchoStarted = true;
    g_ultrasonicEchoRiseUs = nowUs;
  } else if (g_ultrasonicEchoStarted && !echoHigh) {
    const unsigned long duration = nowUs - g_ultrasonicEchoRiseUs;
    g_ultrasonicWaitingForEcho = false;
    if (duration < kUltrasonicTimeoutUs) {
      const float distanceCm = duration * 0.01715f;
      if (distanceCm >= 2.0f && distanceCm <= 400.0f && g_ultrasonicOutputPort != nullptr) {
        g_ultrasonicOutputPort->print("DIST,");
        g_ultrasonicOutputPort->println(distanceCm, 1);
      }
    }
  } else if (nowUs - g_ultrasonicTriggerUs >= kUltrasonicTimeoutUs) {
    g_ultrasonicWaitingForEcho = false;
  }
}

void handleWatchdog() {
  if (millis() - g_lastCommandMs > kWatchdogTimeoutMs) {
    stopMotion();
    g_activeControlPort->println("WATCHDOG");
    g_lastCommandMs = millis();
  }
}

void handleCommand(const String& rawCommand, Stream& reply) {
  g_activeControlPort = &reply;
  String command = rawCommand;
  command.trim();
  command.toUpperCase();

  if (command == "EMERGENCY STOP" || command == "EMERGENCY_STOP") {
    g_safetyStopActive = true;
    stopMotion();
    reply.println("EMERGENCY_LOCKED");
    return;
  }

  if (command == "EMERGENCY RELEASE" || command == "EMERGENCY_RELEASE") {
    g_safetyStopActive = false;
    stopMotion();
    reply.println("EMERGENCY_RELEASED");
    return;
  }

  if (command == "STOP") {
    stopMotion();
    reply.println("OK");
    return;
  }

  if (command.startsWith("MOVE,")) {
    if (g_safetyStopActive) {
      stopMotion();
      reply.println("EMERGENCY_LOCKED");
      return;
    }
    const int firstComma = command.indexOf(',');
    const int secondComma = command.indexOf(',', firstComma + 1);
    const int thirdComma = command.indexOf(',', secondComma + 1);

    if (firstComma > 0 && secondComma > firstComma && thirdComma > secondComma) {
      const String vxToken = command.substring(firstComma + 1, secondComma);
      const String vyToken = command.substring(secondComma + 1, thirdComma);
      const String wzToken = command.substring(thirdComma + 1);

      g_motionCommand.vx = vxToken.toFloat();
      g_motionCommand.vy = vyToken.toFloat();
      g_motionCommand.wz = wzToken.toFloat();
      g_motionCommand.active = true;
      resetWatchdog();
      reply.println("OK");
      return;
    }
  }

  if (command == "GRAB") {
    closeGripper();
    resetWatchdog();
    reply.println("BALL_CAPTURED");
    return;
  }

  if (command == "RELEASE") {
    openGripper();
    resetWatchdog();
    reply.println("BALL_DROPPED");
    return;
  }

  if (command.startsWith("SERVO,")) {
    const int separator = command.indexOf(',');
    if (separator > 0) {
      const String angleToken = command.substring(separator + 1);
      const int angle = angleToken.toInt();
      g_gripperServo.write(constrain(angle, kServoOpenAngle, kServoClosedAngle));
      reply.println("OK");
      return;
    }
  }

  if (command == "PING") {
    resetWatchdog();
    reply.println("PONG");
    return;
  }

  if (command == "HEARTBEAT") {
    resetWatchdog();
    reply.println("OK");
    return;
  }

  if (command.startsWith("SENSOR,")) {
    // Formato: SENSOR,<nome>,<on|off>
    // Exemplo: SENSOR,ULTRASONIC,ON
    int comma1 = command.indexOf(',');
    int comma2 = command.indexOf(',', comma1 + 1);
    
    if (comma1 > 0 && comma2 > comma1) {
      String sensor = command.substring(comma1 + 1, comma2);
      String state = command.substring(comma2 + 1);
      
      if (sensor == "ULTRASONIC") {
        if (state == "ON") {
          g_ultrasonicEnabled = true;
          g_lastUltrasonicMeasureMs = millis();
          g_ultrasonicOutputPort = &reply;
          reply.println("OK");
          return;
        } else if (state == "OFF") {
          g_ultrasonicEnabled = false;
          g_ultrasonicWaitingForEcho = false;
          g_ultrasonicOutputPort = nullptr;
          reply.println("OK");
          return;
        }
      }
    }
  }

  reply.println("ERROR");
}

void processSerialPort(Stream& port, char* line, size_t& length) {
  while (port.available() > 0) {
    const char value = static_cast<char>(port.read());
    if (value == '\r') {
      continue;
    }
    if (value == '\n') {
      line[length] = '\0';
      if (length > 0) {
        handleCommand(String(line), port);
      }
      length = 0;
      continue;
    }
    if (length + 1 >= kSerialLineCapacity) {
      length = 0;
      port.println("ERROR");
      continue;
    }
    line[length++] = value;
  }
}

void setup() {
  Serial.begin(kSerialBaudrate);
  Serial1.begin(kSerialBaudrate);
  initMotors();
  initGripper();
  initUltrasonic();
  stopMotion();
  Serial.println("READY");
  Serial1.println("READY");
}

void loop() {
  processSerialPort(Serial, g_usbLine, g_usbLineLength);
  processSerialPort(Serial1, g_uartLine, g_uartLineLength);
  handleWatchdog();
  handleUltrasonic();

  if (g_motionCommand.active) {
    applyOmniMotion(g_motionCommand.vx, g_motionCommand.vy, g_motionCommand.wz);
  } else {
    stopAllMotors();
  }

  delayMicroseconds(50);
}
