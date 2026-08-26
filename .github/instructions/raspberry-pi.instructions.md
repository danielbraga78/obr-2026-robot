---
applyTo: "**/*.py,**/*.service,**/*.timer,**/systemd/**,**/requirements.txt,**/pyproject.toml"
---
# Raspberry Pi / Linux Services / Python

## Contexto do dispositivo

Antes de alterar código que interage com Raspberry Pi, descubra no projeto, quando disponível:

- modelo/arquitetura;
- sistema operacional;
- versão do Python;
- bibliotecas de GPIO/câmera;
- serviços relacionados;
- como o processo é iniciado no boot.

Não invente a disponibilidade de `/dev/video*`, GPIO, câmera, serial, I2C ou SPI.

## Inicialização e serviços

- Verifique ordem de inicialização e dependências entre serviços.
- Em systemd, valide `ExecStart`, `WorkingDirectory`, `User`, `Group`, permissões, `After`, `Requires` e `WantedBy` conforme o caso.
- Não use reinícios agressivos como solução permanente para um processo que falha por configuração incorreta.
- Evite iniciar processos duplicados.

## Câmera

- Não presuma que a câmera está disponível só porque uma biblioteca foi importada.
- Verifique enumeração do dispositivo, permissões, backend e formato/resolução suportados.
- Quando um programa depende de câmera no boot, considere corrida entre driver, serviço, dispositivo e aplicação.

## GPIO e hardware

- Verifique modo de numeração e biblioteca usada.
- Não altere pinos sem localizar sua definição.
- Garanta estados seguros de inicialização e limpeza.
- Se o programa controlar motores, inclua comportamento seguro quando ocorrer exceção ou encerramento.

## Execução e diagnóstico

- Diferencie erro do Python, erro do serviço, erro de permissão, erro de dispositivo e erro de lógica.
- Não transforme exceções em "sucesso".
- Quando possível, valide com logs do processo e estado do serviço.

## Limitação de ambiente

Se o Copilot não tiver acesso ao Raspberry Pi real, não declare que GPIO, câmera, serial, serviço ou boot funcionaram. Declare exatamente o que foi validado no ambiente disponível.
