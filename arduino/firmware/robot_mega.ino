#include <Arduino.h>
#include <Servo.h>

// Sketch para Arduino Mega 2560 — mapeamento de pinos sugerido

constexpr uint8_t kMotor1EnablePin = 2;   // PWM (Mega)
constexpr uint8_t kMotor1In1Pin = 22;
constexpr uint8_t kMotor1In2Pin = 23;

constexpr uint8_t kMotor2EnablePin = 3;   // PWM (Mega)
constexpr uint8_t kMotor2In1Pin = 24;
constexpr uint8_t kMotor2In2Pin = 25;

constexpr uint8_t kMotor3EnablePin = 4;   // PWM (Mega)
constexpr uint8_t kMotor3In1Pin = 26;
constexpr uint8_t kMotor3In2Pin = 27;

constexpr uint8_t kMotor4EnablePin = 5;   // PWM (Mega)
constexpr uint8_t kMotor4In1Pin = 28;     // A4 mapped to digital 28
constexpr uint8_t kMotor4In2Pin = 29;     // A5 mapped to digital 29

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

MotionCommand g_motionCommand = {0.0f, 0.0f, 0.0f, false};
unsigned long g_lastCommandMs = 0;
bool g_safetyStopActive = false;

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

  setMotorSpeed(0, fl);
  setMotorSpeed(1, fr);
  setMotorSpeed(2, rl);
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
