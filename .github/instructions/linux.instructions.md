---
applyTo: "**/Dockerfile,**/*.service,**/*.timer,**/*.socket,**/*.mount,**/*.path,**/*.desktop,**/Makefile,**/*.mk,**/docker-compose.yml,**/compose.yml,**/compose.yaml"
---
# Linux / Build / Service Configuration

## Descoberta

Antes de alterar configuração Linux, descubra como o projeto é executado: systemd, shell, Docker/Compose, Make, desktop entry ou outro mecanismo.

Não altere comandos de inicialização sem verificar o ambiente-alvo.

## systemd

- Verifique dependências, usuário, diretório de trabalho, PATH, ambiente e permissões.
- Prefira caminhos absolutos quando o contexto exigir confiabilidade.
- Verifique se o serviço depende de rede, dispositivo ou montagem específica.
- Não use `Restart=always` para esconder uma falha de configuração.

## Docker / Compose

- Não adicione privilégios, volumes, devices ou capabilities sem necessidade.
- Preserve o comportamento e a segurança existentes.
- Verifique portas, redes, volumes, environment e healthchecks.

## Make e builds

- Não altere targets ou flags globais sem avaliar os demais targets.
- Não remova flags de compilação apenas para contornar um erro sem diagnosticar a causa.

## Validação

Sempre que possível, execute o mecanismo real de validação do projeto. Se o ambiente-alvo for diferente do ambiente atual, declare essa diferença.
