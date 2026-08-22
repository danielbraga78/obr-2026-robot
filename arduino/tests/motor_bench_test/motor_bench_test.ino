#include <Arduino.h>

// Sketch de bancada para diagnosticar motores com multímetro e para levantar
// os números da calibração (ver arduino/CALIBRACAO_MOTORES.md).
//
// Monitor serial: 115200 baud, terminação "Nova linha" ou "Ambos NL & CR".
//
// Diferente do omni_wheels_test.ino, aqui nada muda sozinho: o estado só muda
// quando você manda um comando. É isso que permite medir com o ponteiro parado.

// ===========================================================================
// Qual montagem está no robô
// ===========================================================================
// true  = PCB (conexoes_arduino_com_pcb.md), usado pelo robot_mega_pcb.ino
// false = protoboard, usado pelo robot_mega.ino
constexpr bool kUsePcbWiring = true;

struct MotorChannel {
  uint8_t enablePin;
  uint8_t in1Pin;
  uint8_t in2Pin;
  const char* name;
};

constexpr uint8_t kMotorCount = 4;

// Na PCB os enables caem em D33, D23, D53 e D43, e nenhum desses pinos tem PWM
// por hardware no Mega — que só o oferece em 2 a 13 e 44 a 46. Por isso este
// sketch gera o PWM por software nesses canais; sem isso, analogWrite viraria
// digitalWrite e as leituras de velocidade seriam todas 0 V ou tensão cheia.
MotorChannel g_pcbChannels[kMotorCount] = {
  {33, 29, 31, "M1 (Ponte A canal A - conector J3)"},
  {23, 27, 25, "M2 (Ponte A canal B - conector J2)"},
  {53, 49, 51, "M3 (Ponte B canal A - conector J5)"},
  {43, 47, 45, "M4 (Ponte B canal B - conector J4)"},
};

MotorChannel g_breadboardChannels[kMotorCount] = {
  {5, 28, 29, "M1 (protoboard - frente esquerda)"},
  {3, 25, 24, "M2 (protoboard - tras esquerda)"},
  {4, 26, 27, "M3 (protoboard - frente direita)"},
  {2, 22, 23, "M4 (protoboard - tras direita)"},
};

MotorChannel g_channels[kMotorCount];

// STBY do TB6612FNG. Com ele em LOW ou flutuando o driver fica em standby e
// NENHUM motor recebe tensão, por mais correto que esteja o resto.
// Na PCB o STBY vai no jumper comum, então este sketch não o controla.
constexpr bool kUseStbyPin = false;
constexpr uint8_t kStbyPin = 30;

// Tensão do VM, só para o sketch conseguir estimar o que você vai medir.
constexpr float kMotorSupplyVolts = 6.0f;
constexpr float kLogicVolts = 5.0f;

// ===========================================================================
// PWM por software (mesma técnica do robot_mega_pcb.ino)
// ===========================================================================
volatile uint8_t g_softPwmDuty[kMotorCount] = {0, 0, 0, 0};
volatile uint8_t* g_softPwmPort[kMotorCount] = {nullptr, nullptr, nullptr, nullptr};
uint8_t g_softPwmMask[kMotorCount] = {0, 0, 0, 0};
volatile uint8_t g_softPwmPhase = 0;
bool g_softPwmActive = false;

uint8_t g_selected = 0;
int g_speed = 255;    // 255 = saída contínua, leitura estável no multímetro
int g_direction = 0;  // 1 frente, -1 ré, 0 parado

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
        *port &= ~g_softPwmMask[i];
      }
    } else if (phase >= g_softPwmDuty[i]) {
      *port &= ~g_softPwmMask[i];
    }
  }
}

void initSoftPwm() {
  for (uint8_t i = 0; i < kMotorCount; ++i) {
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

void applyOutput() {
  for (uint8_t i = 0; i < kMotorCount; ++i) {
    const bool active = (i == g_selected) && (g_direction != 0);
    digitalWrite(g_channels[i].in1Pin, active && g_direction > 0 ? HIGH : LOW);
    digitalWrite(g_channels[i].in2Pin, active && g_direction < 0 ? HIGH : LOW);
    writeEnable(i, active ? static_cast<uint8_t>(g_speed) : 0);
  }
}

void printExpectations() {
  const MotorChannel& motor = g_channels[g_selected];
  Serial.println();
  Serial.print(F("Motor selecionado: "));
  Serial.println(motor.name);
  Serial.print(F("  PWM (enable) no pino D"));
  Serial.print(motor.enablePin);
  if (g_softPwmPort[g_selected] != nullptr) {
    Serial.print(F(" [PWM por software]"));
  }
  Serial.print(F("  | IN1 no pino D"));
  Serial.print(motor.in1Pin);
  Serial.print(F("  | IN2 no pino D"));
  Serial.println(motor.in2Pin);

  if (g_direction == 0) {
    Serial.println(F("  Estado: PARADO"));
    Serial.println(F("  Esperado: IN1 ~0 V, IN2 ~0 V, PWM ~0 V, saida do motor ~0 V"));
  } else {
    Serial.print(F("  Estado: GIRANDO "));
    Serial.print(g_direction > 0 ? F("para FRENTE") : F("para TRAS"));
    Serial.print(F(" com duty "));
    Serial.print(g_speed);
    Serial.print(F("/255 ("));
    Serial.print((g_speed * 100) / 255);
    Serial.println(F("%)"));

    Serial.print(F("  Esperado: IN1 ~"));
    Serial.print(g_direction > 0 ? kLogicVolts : 0.0f, 1);
    Serial.print(F(" V, IN2 ~"));
    Serial.print(g_direction > 0 ? 0.0f : kLogicVolts, 1);
    Serial.print(F(" V, PWM ~"));
    Serial.print(kLogicVolts * g_speed / 255.0f, 1);
    Serial.println(F(" V (media do PWM)"));

    Serial.print(F("  Esperado entre as duas saidas do motor: ~"));
    Serial.print(kMotorSupplyVolts * g_speed / 255.0f, 1);
    Serial.println(F(" V"));
    Serial.println(F("  Se der ~0 V ali: cheque VM e STBY antes de qualquer outra coisa."));
  }
  Serial.println(F("  ---"));
  Serial.println(F("  Comandos: 1-4 motor | f frente | r re | s parar | + / - duty | ? ajuda"));
}

void printHelp() {
  Serial.println();
  Serial.println(F("=== Teste de bancada dos motores ==="));
  Serial.print(F("Montagem: "));
  Serial.println(kUsePcbWiring ? F("PCB") : F("protoboard"));
  Serial.println(F("  1 2 3 4  seleciona o motor"));
  Serial.println(F("  f        gira para frente"));
  Serial.println(F("  r        gira para tras"));
  Serial.println(F("  s        para"));
  Serial.println(F("  +        aumenta o duty (5 em 5)"));
  Serial.println(F("  -        diminui o duty"));
  Serial.println(F("  ?        mostra esta ajuda"));
  Serial.println();
  Serial.println(F("Para medir com multimetro: use duty 255. O multimetro mostra"));
  Serial.println(F("a MEDIA do PWM, entao valores intermediarios dao leituras"));
  Serial.println(F("baixas e isso e normal, nao e defeito."));
  Serial.println();
  Serial.println(F("Para calibrar (ver arduino/CALIBRACAO_MOTORES.md):"));
  Serial.println(F("  1. Qual conector e qual roda: rode cada motor e observe."));
  Serial.println(F("  2. Duty minimo: com o robo NO CHAO, suba de 5 em 5 ate a"));
  Serial.println(F("     roda girar continuamente. No ar o valor sai errado."));
  Serial.println(F("  3. Ganho relativo: marque as rodas com fita, rode os quatro"));
  Serial.println(F("     no mesmo duty e conte as voltas em 10 s."));

  if (kUseStbyPin) {
    Serial.print(F("STBY: pino D"));
    Serial.print(kStbyPin);
    Serial.println(F(" mantido em HIGH por este sketch."));
  } else {
    Serial.println();
    Serial.println(F("STBY: este sketch NAO controla o STBY."));
    Serial.println(F("      Ele precisa estar em 5 V por hardware, senao o driver"));
    Serial.println(F("      fica em standby e nenhum motor recebe tensao."));
    Serial.println(F("      Na PCB ele vai no jumper comum."));
    Serial.println(F("      Meca STBY -> GND: tem que dar ~5 V."));
  }
}

void handleCommand(char command) {
  switch (command) {
    case '1': case '2': case '3': case '4':
      g_selected = command - '1';
      break;
    case 'f': case 'F':
      g_direction = 1;
      break;
    case 'r': case 'R':
      g_direction = -1;
      break;
    case 's': case 'S':
      g_direction = 0;
      break;
    case '+':
      g_speed = min(255, g_speed + 5);
      break;
    case '-':
      g_speed = max(0, g_speed - 5);
      break;
    case '?':
      printHelp();
      break;
    default:
      return;  // ignora \r, \n e teclas desconhecidas
  }
  applyOutput();
  printExpectations();
}

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    ;  // aguarda o monitor no Mega/Leonardo
  }

  for (uint8_t i = 0; i < kMotorCount; ++i) {
    g_channels[i] = kUsePcbWiring ? g_pcbChannels[i] : g_breadboardChannels[i];
  }

  for (uint8_t i = 0; i < kMotorCount; ++i) {
    pinMode(g_channels[i].enablePin, OUTPUT);
    pinMode(g_channels[i].in1Pin, OUTPUT);
    pinMode(g_channels[i].in2Pin, OUTPUT);
    digitalWrite(g_channels[i].enablePin, LOW);
  }

  initSoftPwm();

  if (kUseStbyPin) {
    pinMode(kStbyPin, OUTPUT);
    digitalWrite(kStbyPin, HIGH);
  }

  g_direction = 0;
  applyOutput();

  printHelp();
  printExpectations();
}

void loop() {
  if (Serial.available()) {
    handleCommand(static_cast<char>(Serial.read()));
  }
}
