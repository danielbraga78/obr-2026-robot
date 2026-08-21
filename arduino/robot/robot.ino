#include <Arduino.h>
#include <Servo.h>

// Sketch único para o robô da OBR.
// Este arquivo é a variante para Arduino Uno/Nano.
//
// Este firmware assume uma base omnidirecional de 4 rodas com 4 motores independentes,
// operando com a mistura cinemática clássica de holonômica/X-drive:
//   FL = vx + vy + wz
//   FR = -vx + vy + wz
//   RL = -vx - vy + wz
//   RR = vx - vy + wz
//
// Se a geometria física do robô for diferente, este mapeamento deve ser ajustado.
//
// NOTA: Este firmware funciona com câmera USB/CSI como sensor de percepção.
// Obstáculos são detectados pelo Raspberry Pi via visão computacional.
// Sensores adicionais (ultrassônico, ToF, LiDAR) podem ser integrados no futuro.
//
// A variante Uno/Nano usa PWM nos pinos 3, 6, 9 e 10 para os sinais de enable dos motores.

constexpr uint8_t kMotor1EnablePin = 3;
constexpr uint8_t kMotor1In1Pin = 4;
constexpr uint8_t kMotor1In2Pin = 5;

constexpr uint8_t kMotor2EnablePin = 6;
constexpr uint8_t kMotor2In1Pin = 7;
constexpr uint8_t kMotor2In2Pin = 8;

constexpr uint8_t kMotor3EnablePin = 9;
constexpr uint8_t kMotor3In1Pin = A2;
constexpr uint8_t kMotor3In2Pin = 11;

constexpr uint8_t kMotor4EnablePin = 10;
constexpr uint8_t kMotor4In1Pin = A0;
constexpr uint8_t kMotor4In2Pin = A1;

constexpr uint8_t kServoPin = 2;

// Sensor ultrassônico HC-SR04 (opcional)
constexpr uint8_t kUltrasonicTrigPin = A4;
constexpr uint8_t kUltrasonicEchoPin = A5;
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

MotionCommand g_motionCommand = {0.0f, 0.0f, 0.0f, false};
unsigned long g_lastCommandMs = 0;
bool g_safetyStopActive = false;
bool g_watchdogTriggered = false;

// Sensor ultrassônico
bool g_ultrasonicEnabled = false;
unsigned long g_lastUltrasonicMeasureMs = 0;
constexpr unsigned long kUltrasonicMeasureIntervalMs = 100;  // 10 Hz

Servo g_gripperServo;
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
  if (speed != 0 && abs(speed) < kMinMotorSpeed) {
    speed = speed > 0 ? kMinMotorSpeed : -kMinMotorSpeed;
  }
  const bool reverse = speed < 0;
  const uint8_t pwmValue = static_cast<uint8_t>(abs(speed));

  digitalWrite(g_channels[motorIndex].in1Pin, reverse ? HIGH : LOW);
  digitalWrite(g_channels[motorIndex].in2Pin, reverse ? LOW : HIGH);
  analogWrite(g_channels[motorIndex].enablePin, pwmValue);
}

void stopAllMotors() {
  for (uint8_t i = 0; i < 4; ++i) {
    digitalWrite(g_channels[i].in1Pin, LOW);
    digitalWrite(g_channels[i].in2Pin, LOW);
    analogWrite(g_channels[i].enablePin, 0);
  }
}

void applyOmniMotion(float vx, float vy, float wz) {
  // Mapeamento físico do robô:
  // - Ponte H A: M1 (esquerdo frente) + M3 (esquerdo trás)
  // - Ponte H B: M2 (direito frente) + M4 (direito trás)
  // A cinemática é calculada motor a motor para suportar translação lateral,
  // diagonal e rotação sem depender de frente/trás.
  const float motor1 = vx + vy + wz;
  const float motor2 = vx - vy - wz;
  const float motor3 = vx - vy + wz;
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
  g_watchdogTriggered = false;
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
  const unsigned long now = millis();
  if (now - g_lastCommandMs > kWatchdogTimeoutMs) {
    if (!g_watchdogTriggered) {
      stopMotion();
      Serial.println("WATCHDOG");
      g_watchdogTriggered = true;
    }
    return;
  }

  if (g_watchdogTriggered) {
    g_watchdogTriggered = false;
  }
}

void handleCommand(const String& rawCommand) {
  String command = rawCommand;
  command.trim();
  command.toUpperCase();

  if (command == "EMERGENCY STOP" || command == "EMERGENCY_STOP") {
    g_safetyStopActive = true;
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

  if (command == "HEARTBEAT") {
    resetWatchdog();
    Serial.println("OK");
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
