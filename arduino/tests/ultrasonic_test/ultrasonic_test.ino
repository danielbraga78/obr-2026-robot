#include <Arduino.h>

// Pinagem do HC-SR04 para Arduino Mega
constexpr uint8_t kUltrasonicTrigPin = A2;
constexpr uint8_t kUltrasonicEchoPin = A3;
constexpr unsigned long kUltrasonicTimeoutUs = 100000;  // Timeout para ~4m

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    ; // Aguarda inicialização da porta serial
  }

  pinMode(kUltrasonicTrigPin, OUTPUT);
  pinMode(kUltrasonicEchoPin, INPUT);
  digitalWrite(kUltrasonicTrigPin, LOW);

  Serial.println("Ultrasonic Test - HC-SR04");
  Serial.println("TRIG = A2, ECHO = A3");
  Serial.println();
}

unsigned long measureUltrasonic() {
  digitalWrite(kUltrasonicTrigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(kUltrasonicTrigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(kUltrasonicTrigPin, LOW);

  unsigned long duration = pulseIn(kUltrasonicEchoPin, HIGH, kUltrasonicTimeoutUs);
  return duration;
}

void loop() {
    unsigned long duration = measureUltrasonic();
  if (duration == 0) {
    Serial.println("No echo received (timeout)");
  } else {
    float distanceCm = duration / 58.0f;
    Serial.print("Duration: ");
    Serial.print(duration);
    Serial.print(" us, Distance: ");
    Serial.print(distanceCm, 1);
    Serial.println(" cm");
  }

  delay(250);
}
