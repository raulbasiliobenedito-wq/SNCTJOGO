# VILA — QUATRO FACHADAS DE CASA

Frente de casa, vista frontal, estilo chapado — o mesmo do briefing dos sprites
de efeito: **preenchimento sólido, 2 a 3 tons por forma, contorno preto puro de
1 px, alfa só 0 ou 255**. Sem degradê, sem brilho, sem sombra projetada, sem
anti-aliasing. Fundo 100% transparente, **sem chão nem grama embutidos**.

---

## 1. ARQUIVOS

| Arquivo | Dimensão | Célula |
|---|---|---|
| `vila_casas_completo.png` | 256×128 | **64×64** · linha 0 = frentes, linha 1 = fundos |
| `vila_casas.png` | 256×64 | **64×64** · 4 frentes em fileira |
| `vila_casas_fundo.png` | 256×64 | **64×64** · os 4 fundos, na mesma ordem |
| `casa_*_fundo.png` | 64×64 | fundos avulsos |
| `casa_tijolo.png` · `casa_amarela.png` · `casa_azul.png` · `casa_creme.png` | 64×64 | avulsas |
| `_preview.png` | — | conferência sobre xadrez, não é asset |

**44 cores** no conjunto todo (frentes + fundos). Alfa verificado: só 0 e 255, nenhum pixel semitransparente.
Cada casa deixa 1 px de margem em todos os lados da célula — dá para fatiar a
folha em 64 em 64 sem raspar contorno.

---

## 2. O QUE FAZ AS QUATRO PARECEREM DA MESMA VILA

Todas repetem a mesma pilha vertical, sempre nas mesmas linhas:

```
y 5–19   chaminé
y 5–27   telhado (beiral saliente 5 px além da parede dos dois lados)
y 25–27  testeira creme  ← a peça que amarra o conjunto
y 26–57  parede
y 33–44  janelas
y 34–57  porta
y 58–61  degrau
```

**Creme da testeira, vidro, cortina e pedra do degrau são idênticos nas quatro.**
Só parede, telhado e porta trocam de cor. É esse fio comum que impede que quatro
paletas diferentes leiam como quatro jogos diferentes.

**O beiral saliente é o que faz ler como casa e não como caixa.** Se o telhado
parasse na largura da parede, a silhueta viraria um retângulo com um triângulo em
cima. Os 5 px de avanço de cada lado criam o degrau na silhueta que o olho
reconhece como telhado antes de ver qualquer detalhe interno.

---

## 3. COMO CADA UMA SE DIFERENCIA

| | Parede | Telhado | Porta | Assinatura |
|---|---|---|---|---|
| **Tijolo** | vermelho quente, fiadas alternadas | duas águas, marrom | verde-petróleo | a única com textura de junta |
| **Amarela** | amarelo suave, tábua horizontal | duas águas, verde | vermelha | **óculo redondo no frontão** |
| **Azul** | azul-cinza, tábua vertical | **quatro águas** (cumeeira reta) | mostarda | **uma janela larga** com montante, porta deslocada |
| **Creme** | creme liso com embasamento | duas águas, terracota | azul | **toldo listrado** sobre a porta |

Cada uma muda em **três eixos ao mesmo tempo** — cor, textura de parede e um
elemento exclusivo. Mudar só a cor daria quatro reskins da mesma casa; o jogador
percebe repetição de forma muito mais rápido que repetição de cor.

---

## 4. DETALHES QUE VALEM SABER

**A bandeira da porta é meia-lua, não círculo.** Na primeira versão era um disco
inteiro e a porta lia como espelho oval. Meio disco apoiado na travessa é o que
diz "vidro da porta".

**O almofadado da porta é vazado, não cheio.** Em porta de 10 px de largura, dois
painéis sólidos viram duas listras. Um retângulo só de contorno mantém a leitura
de madeira trabalhada.

**As cortinas têm sanefa + dois panos com dobra.** O pano tem 2 px e desce até
~80% do vidro, com uma coluna interna em tom mais escuro. Sem essa coluna o pano
vira um bloco branco e a janela parece tapada.

**O contorno preto é por forma, não só na silhueta.** É o que separa a janela da
parede e o telhado da parede sem precisar de sombra — que o estilo proíbe.

---

## 5. INTEGRAÇÃO

- Escala só em **múltiplos inteiros**, filtro **nearest neighbor**.
- São props de fundo: a base útil (linha do chão) é **y 62**. Alinhe esse valor
  com o topo do seu tile de terreno e a casa assenta sem flutuar.
- Sem chão embutido de propósito — o terreno entra por trás, com o degrau
  encostando nele.

---

## 6. OS FUNDOS

Mesma linha de telhado, mesma testeira, mesma parede, mesma base em **y 62**.
Trocando a célula da frente pela do fundo a casa não muda de tamanho nem de cor —
é literalmente a mesma casa virada.

O problema real de um fundo de casa não é tirar a porta; é **não parecer uma
frente sem porta**. Cinco recursos resolvem isso:

1. **Assimetria.** Fachada é simétrica e formal; fundo é irregular. Cada casa tem
   a janela numa posição diferente e fora do centro. É o sinal mais forte de todos
   — o olho lê antes de identificar qualquer objeto.
2. **Chaminé do outro lado.** Na frente ela está à direita; no fundo, à esquerda.
   A silhueta espelha e o jogador entende "é a mesma casa, virada".
3. **Calha descendo até o chão.** Peça que só existe no fundo de uma casa.
4. **Janela de serviço:** menor, **sem cortina**, com caixilho em cruz. Cortina é
   coisa de fachada; vidro dividido lê como área de serviço.
5. **Trambolho encostado.** Ninguém encosta lenha na frente de casa.

| | Janela | Trambolho | Extra |
|---|---|---|---|
| **Tijolo** | à direita | pilha de lenha | grelha de ventilação no frontão |
| **Amarela** | à esquerda | **varal com roupa** (3 peças, uma na cor da porta da frente) | — |
| **Azul** | centro-esquerda | barril + caixote | — |
| **Creme** | à direita | **escada encostada** | grelha no frontão |

Duas notas de execução:

**A escada é montada linha a linha, não como segmento com espessura.** Assim o
degrau sai perfeitamente horizontal e o vão fica com 4×3 px — grande o bastante
para sobreviver ao contorno preto de 1 px. Na primeira versão o vão tinha 3 px, o
preto fechava o buraco e a escada virava um tronco.

**A pilha de lenha tem um contorno só, para a pilha inteira.** Se cada tora
levasse contorno próprio, num diâmetro de 4 px o preto comeria a tora.

---

## 7. RUA COMPLETA

Frente e fundo compartilham a linha de base **y 62** e a linha de beiral **y 25**,
então dá para montar uma rua de mão dupla: fundos na camada de trás, frentes na
da frente, ambos assentando no mesmo tile de terreno.

Espelhando horizontalmente as de duas águas a chaminé troca de lado e você ganha
mais 6 variações de graça — só o toldo, o óculo e o varal ficam simétricos demais
para valer o espelho.

---

Tudo gerado por código determinístico (`fonte/houses.py`, `fonte/houses_back.py`) — dá para re-renderizar
trocando paleta, textura de parede, formato de telhado ou número de janelas.
