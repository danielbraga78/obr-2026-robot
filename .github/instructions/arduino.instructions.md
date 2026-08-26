---
applyTo: "**/*.ino,**/*.cpp,**/*.h"
---
# Arduino / Embedded C++

## Hardware primeiro

Antes de alterar firmware, identifique no código:

- placa/MCU;
- pinos usados;
- sensores/atuadores;
- alimentação e interfaces;
- protocolos seriais/I2C/SPI;
- bibliotecas e versões relevantes, quando disponíveis.

Não invente pinagem.

## Loop e temporização

- Não use `delay()` para resolver problemas de sincronização sem verificar o efeito sobre sensores, motores, comunicação e responsividade.
- Quando houver várias tarefas concorrentes, avalie `millis()`/timers ou outra estratégia compatível com a arquitetura existente.
- Não bloqueie o loop principal sem necessidade.

## Estado e sensores

- Trate leituras inválidas, perda de sinal, saturação e valores fora do esperado.
- Verifique unidades e conversões.
- Confirme se o sensor precisa de tempo de estabilização e se isso é tratado corretamente.
- Não presuma que uma leitura única representa o estado real quando o hardware exige filtragem/debounce.

## Serial, I2C e comunicação

- Valide framing, delimitadores, tamanho e timeout quando houver protocolo próprio.
- Não faça parsing parcial e depois considere a mensagem válida.
- Em I2C/SPI/UART, confirme endereço, baud rate, modo e inicialização conforme o projeto.

## Motores e atuadores

- Considere limites, estado inicial, failsafe e parada segura.
- Uma instrução para motor deve deixar claro o que acontece quando o comando desaparece ou chega inválido.
- Não aumente potência, velocidade ou frequência sem verificar limites elétricos e térmicos relevantes.

## Validação

Se o Copilot não tiver acesso ao hardware físico, ele deve distinguir claramente entre "código compilado" e "comportamento do dispositivo confirmado".
