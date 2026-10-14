# Funcionamento e movimentos de um robô com rodas Mecanum

O esquema apresenta seis formas de movimentação de um robô equipado com quatro rodas Mecanum. Como essas rodas possuem roletes inclinados, o robô pode avançar, deslocar-se lateralmente e na diagonal, além de girar sobre si mesmo ou ao redor de um ponto fora de seu centro.

![Diagrama dos seis movimentos com rodas Mecanum](diagrama-movimentos-mecanum.jpg)

## 1. Como interpretar o esquema

- **Setas azuis:** indicam o sentido de acionamento de cada roda. As setas para cima e para baixo representam sentidos opostos.
- **Setas vermelhas:** indicam o movimento resultante do robô ou o sentido da rotação.
- **Rodas esmaecidas:** representam as rodas que ficam sem acionamento naquele movimento.
- **Eixo X:** representa a direção horizontal do desenho. Para a direita é o sentido positivo de X.
- **Eixo Y:** representa a direção vertical do desenho. Para cima é o sentido positivo de Y.

Neste documento, considera-se a frente do robô voltada para o topo do desenho.

## 2. Os seis tipos de movimentação

### 2.1. Deslocamento para frente

**Acionamento:** as quatro rodas são movimentadas no mesmo sentido, indicado pelas setas azuis para cima.

**Resultado:** o robô avança em linha reta no sentido positivo do eixo Y, sem rotação intencional.

**Aplicação:** percorrer um trecho reto, como ao seguir uma linha no chão.

### 2.2. Deslocamento lateral para a direita

**Acionamento:** a roda dianteira esquerda e a traseira direita são acionadas em um sentido; a dianteira direita e a traseira esquerda, no sentido oposto.

**Resultado:** o robô desloca-se para a direita, no sentido positivo do eixo X, mantendo aproximadamente a mesma orientação frontal. Esse movimento é chamado de *strafe*.

**Aplicação:** alinhar-se com um objeto ou passar por um espaço estreito sem precisar virar a frente do robô.

### 2.3. Deslocamento diagonal para frente e para a direita

**Acionamento mostrado no esquema:** a roda dianteira esquerda e a traseira direita são acionadas; as outras duas ficam sem acionamento.

**Resultado:** o robô avança e desloca-se para a direita ao mesmo tempo.

**Aplicação:** aproximar-se de um alvo localizado à frente e deslocado para um dos lados.

### 2.4. Rotação ao redor de um ponto à direita

**Acionamento mostrado no esquema:** as duas rodas do lado esquerdo são acionadas para frente, enquanto as duas rodas do lado direito ficam paradas.

**Resultado:** o robô descreve uma curva em torno de um ponto situado à sua direita, indicado pelo ponto vermelho. Esse ponto fica fora do centro do robô.

**Aplicação:** realizar uma curva ampla ou contornar uma posição mantendo um lado do robô como referência.

### 2.5. Rotação sobre o próprio centro

**Acionamento:** as duas rodas do lado esquerdo são acionadas para frente e as duas do lado direito para trás.

**Resultado:** o robô gira em torno do próprio centro, sem deslocamento linear significativo. No esquema, a rotação é no sentido horário.

**Aplicação:** mudar rapidamente a orientação em locais apertados.

### 2.6. Rotação ao redor de um ponto atrás do robô

**Acionamento mostrado no esquema:** as duas rodas dianteiras são acionadas em sentidos opostos, enquanto as duas rodas traseiras ficam paradas.

**Resultado:** o robô gira em torno de um ponto situado atrás dele, representado pelo ponto vermelho. Como esse ponto não coincide com o centro, o movimento difere do giro sobre o próprio eixo.

**Aplicação:** orientar a parte dianteira ao redor de uma posição traseira de referência.

## 3. Resumo dos sentidos das rodas

Abreviações usadas:

- **DE:** dianteira esquerda.
- **DD:** dianteira direita.
- **TE:** traseira esquerda.
- **TD:** traseira direita.
- **↑ / ↓:** sentidos opostos de acionamento, conforme representados no desenho.
- **Parada:** roda sem acionamento.

| Movimento | DE | DD | TE | TD |
|---|---:|---:|---:|---:|
| Para frente | ↑ | ↑ | ↑ | ↑ |
| Para a direita | ↑ | ↓ | ↓ | ↑ |
| Diagonal para frente e direita | ↑ | Parada | Parada | ↑ |
| Giro com ponto à direita | ↑ | Parada | ↑ | Parada |
| Giro sobre o centro | ↑ | ↓ | ↑ | ↓ |
| Giro com ponto atrás | ↑ | ↓ | Parada | Parada |

A tabela segue a configuração ilustrada. Os sentidos reais podem mudar conforme a montagem das rodas, a orientação dos roletes e a polaridade dos motores.

## 4. Por que as rodas Mecanum permitem esses movimentos?

Uma roda convencional empurra o robô principalmente na direção em que rola. Já a roda Mecanum utiliza pequenos roletes inclinados, que permitem gerar componentes de força em direções diferentes.

Ao combinar o acionamento das quatro rodas, o controlador pode produzir três componentes de movimento no plano:

1. **Translação no eixo X:** deslocamento para a esquerda ou para a direita.
2. **Translação no eixo Y:** deslocamento para frente ou para trás.
3. **Rotação:** mudança da orientação do robô.

Esses componentes podem ser combinados. Por exemplo, o robô pode avançar enquanto se desloca lateralmente ou pode deslocar-se e girar ao mesmo tempo.

## 5. Cuidados ao implementar no robô

As setas do diagrama não devem ser convertidas diretamente em comandos elétricos sem antes verificar a montagem. A orientação dos roletes, a posição de cada roda e a polaridade dos motores influenciam o resultado.

Procedimento recomendado:

1. Identifique as rodas dianteira esquerda, dianteira direita, traseira esquerda e traseira direita.
2. Acione cada motor individualmente em baixa velocidade e confirme o sentido real de rotação.
3. Teste cada movimento separadamente, começando pelo deslocamento para frente.
4. Se o robô andar na direção errada, confira a polaridade e o mapeamento dos motores antes de alterar a lógica de movimento.
5. Valide as rotações observando se o ponto de giro está na posição esperada.

**Importante:** a tabela descreve a configuração mostrada na imagem. Em um robô real, é necessário validar experimentalmente os sentidos de acionamento antes de utilizá-los no código.
