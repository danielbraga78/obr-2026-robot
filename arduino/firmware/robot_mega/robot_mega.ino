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
constexpr int kMinMotorSpeed = 30;
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
  const float frontLeft = vx + vy + wz;
  const float frontRight = -vx + vy + wz;
  const float rearLeft = -vx - vy + wz;
  const float rearRight = vx - vy + wz;

  const float maxAbs = max(max(abs(frontLeft), abs(frontRight)), max(abs(rearLeft), abs(rearRight)));
  const float scale = (maxAbs > kMaxMotorSpeed) ? (kMaxMotorSpeed / maxAbs) : 1.0f;

  const int fl = static_cast<int>(frontLeft * scale);
  const int fr = static_cast<int>(frontRight * scale);
  const int rl = static_cast<int>(rearLeft * scale);
  const int rr = static_cast<int>(rearRight * scale);

  if (g_safetyStopActive) {
    stopAllMotors();
    return;
  }

  // Ordem lógica: motor 0 = frente esquerdo, motor 1 = trás esquerdo,
  // motor 2 = frente direito, motor 3 = trás direito.
  // Os motores da esquerda ficam na Ponte A e os da direita na Ponte B.
  setMotorSpeed(0, fl);
  setMotorSpeed(1, rl);
  setMotorSpeed(2, fr);
  setMotorSpeed(3, rr);
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

unsigned long measureUltrasonic() {
  // Dispara o sensor
  digitalWrite(kUltrasonicTrigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(kUltrasonicTrigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(kUltrasonicTrigPin, LOW);
  
  // Aguarda o echo
  unsigned long duration = pulseIn(kUltrasonicEchoPin, HIGH, kUltrasonicTimeoutUs);
  return duration;
}

void handleUltrasonic() {
  if (!g_ultrasonicEnabled) {
    return;
  }
  
  unsigned long now = millis();
  if (now - g_lastUltrasonicMeasureMs < kUltrasonicMeasureIntervalMs) {
    return;
  }
  
  g_lastUltrasonicMeasureMs = now;
  
  unsigned long duration = measureUltrasonic();
  
  // Converter para centímetros: distância = (duração em microssegundos * velocidade do som) / 2
  // Velocidade do som: ~343 m/s = 0.0343 cm/us
  // Fórmula: cm = (duration * 0.0343) / 2 = duration * 0.01715
  if (duration > 0 && duration < kUltrasonicTimeoutUs) {
    float distanceCm = duration * 0.01715f;
    
    // Validar range razoável (2cm a 400cm)
    if (distanceCm >= 2.0f && distanceCm <= 400.0f) {
      Serial.print("DIST,");
      Serial.println(distanceCm, 1);
    }
  }
}

void handleWatchdog() {
  if (millis() - g_lastCommandMs > kWatchdogTimeoutMs) {
    stopMotion();
    Serial.println("WATCHDOG");
    g_lastCommandMs = millis();
  }
}

void handleCommand(const String& rawCommand) {
  String command = rawCommand;
  command.trim();
  command.toUpperCase();

  if (command == "STOP") {
    stopMotion();
    Serial.println("OK");
    return;
  }

  if (command.startsWith("MOVE,")) {
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
      const String angleToken = command.substring(separator + 1);
      const int angle = angleToken.toInt();
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
          Serial.println("OK");
          return;
        } else if (state == "OFF") {
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
    String command = Serial.readStringUntil('\n');
    handleCommand(command);
  }

  handleWatchdog();
  handleUltrasonic();

  if (g_motionCommand.active) {
    applyOmniMotion(g_motionCommand.vx, g_motionCommand.vy, g_motionCommand.wz);
  } else {
    stopAllMotors();
  }

  delay(10);
}
