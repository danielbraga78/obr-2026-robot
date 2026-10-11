#include <Arduino.h>

// true = PCB (docs/hardware/HARDWARE.md); false = montagem normal.
constexpr bool kUsePcbWiring = true;

// Montagem normal: TRIG A2, ECHO A3.
// PCB: J6.2/TRIG D44, J7.1/ECHO D46.
constexpr uint8_t kUltrasonicTrigPin = kUsePcbWiring ? 44 : A2;
constexpr uint8_t kUltrasonicEchoPin = kUsePcbWiring ? 46 : A3;
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
  Serial.print("Montagem: ");
  Serial.println(kUsePcbWiring ? "PCB" : "normal");
  Serial.print("TRIG = ");
  Serial.println(kUsePcbWiring ? "D44" : "A2");
  Serial.print("ECHO = ");
  Serial.println(kUsePcbWiring ? "D46" : "A3");
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
