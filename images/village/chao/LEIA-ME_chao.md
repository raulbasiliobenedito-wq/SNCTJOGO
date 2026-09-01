# TILESET DE CHÃO — GRAMA, TERRA E CAMINHO

16 tiles de **32×32** numa grade 4×4. **15 cores.** Totalmente **opacos** — tile
de chão com transparência abre fresta na emenda; o que é decoração vai por cima,
como sprite separado.

---

## 1. GRADE (`chao.png`, 128×128)

| | col 0 | col 1 | col 2 | col 3 |
|---|---|---|---|---|
| **lin 0** | `grama_esq` | `grama_meio` | `grama_dir` | `grama_sozinha` |
| **lin 1** | `terra_esq` | `terra_meio` | `terra_dir` | `terra_pedras` |
| **lin 2** | `trans_grama_caminho` | `caminho_meio` | `trans_caminho_grama` | `caminho_pedras` |
| **lin 3** | `grama_flores` | `grama_pedrinhas` | `grama_tufo` | `grama_pedra` |

- **Linha 0** é a superfície. `_esq` e `_dir` têm a lateral preta de plataforma;
  `_sozinha` tem as duas, para plataforma de 1 tile de largura.
- **Linha 1** é o miolo, que emenda nos **dois eixos** — empilhe à vontade.
- **Linha 2** é a rua. As duas transições encaixam de um lado no tile de grama e
  do outro no de caminho.
- **Linha 3** são variações da superfície: trocam por `grama_meio` em qualquer
  posição, sem ajuste.

---

## 2. COMO A EMENDA É GARANTIDA

Não é "testada no olho". Todo o relevo sai de **somas de senos de frequência
inteira** no período do tile: `sin(2π·f·x/32)` com `f` inteiro vale exatamente o
mesmo em x=32 e em x=0, então a coluna 31 continua na coluna 0 do próximo tile
**por construção**. O miolo de terra usa o mesmo truque também em y.

O gerador roda um **teste automático** a cada build. Ele não usa tolerância
inventada: compara o salto de cor na emenda com o **maior salto que já existe
entre colunas vizinhas dentro do próprio tile**. Se a emenda não for pior que o
miolo, ela é literalmente indistinguível. Saída do build atual:

```
grama_meio  -> grama_meio           x   salto 124  vs miolo 170   OK
terra_meio  -> terra_meio           x   salto  40  vs miolo  40   OK
terra_meio  -> terra_meio           y   salto  40  vs miolo  74   OK
grama_meio  -> terra_meio           y   salto  40  vs miolo 208   OK
... (11 pares testados, todos OK)
```

Esse teste pegou um erro real: a "língueta" de grama tinha fase `.21` e nascia
**em cima da emenda**, subindo 4 px entre a última e a primeira coluna. Com fase
zero o seno vale 0 em x=0 e em x=31, e a língueta nunca cai na costura.

---

## 3. DUAS REGRAS DE PLATFORMER QUE VALEM MAIS QUE O DESENHO

**Topo reto.** A tentação é ondular a linha de cima da grama. Não se faz: essa
linha é a **colisão**, e personagem andando sobre topo ondulado balança 2 px por
tile e parece bug. Toda a irregularidade foi para a fronteira grama/terra, que
fica embaixo e não afeta o andar. **O caminho usa a mesma linha de topo** — trocar
grama por terra batida no meio da rua não muda a altura do chão.

**Contorno preto só onde há silhueta:** topo do chão, laterais expostas de
plataforma, fronteira grama/terra e pedra grande. Contorno em volta do tile
inteiro viraria uma grade preta no chão todo.

---

## 4. TRÊS COISAS QUE PRECISARAM SER REFEITAS

**Pedra pequena não leva contorno.** Com raio menor que 3 px o anel preto tem
mais pixel que o miolo e a pedra lê como retângulo vazado. Aparecia espalhada
pela terra inteira no primeiro teste de cena.

**A fronteira grama/terra é costurada.** Cada coluna marcava um pixel preto em
`y = fronteira(x)`; onde a língueta caía 3 px de uma coluna para a outra, os
pixels ficavam soltos e a borda lia como pente de dentes soltos. Agora o preto
desce pela coluna **mais rasa** — que ali é terra — e fecha o contorno sem comer
grama.

**Pedra que atravessa a emenda só serve em tile que sempre se repete.** Num tile
de variação, usado salteado, a metade que atravessa vira meia pedra órfã
encostada num vizinho que não tem a outra metade. Toda pedra de tile de variação
ficou inteira dentro do quadro.

---

## 5. INTEGRAÇÃO

- Escala só em **múltiplos inteiros**, filtro **nearest neighbor**.
- Colisão: o topo sólido é **y 0** de qualquer tile da linha 0 ou 2.
- Ordem de uso numa rua: `grama_meio` → `trans_grama_caminho` → `caminho_meio`
  (quantos quiser, com `caminho_pedras` salteado) → `trans_caminho_grama` →
  `grama_meio`.
- Variações da linha 3: use 1 a cada 4 ou 5 tiles. Mais que isso e o olho começa
  a ver o padrão em vez da variação.
- As casas da vila assentam em **y 62** do quadro delas; alinhe esse valor com o
  topo do tile de chão e elas encostam sem flutuar.

`_teste.png` é uma cena de 14×6 tiles montada pelo próprio gerador — é onde
emenda ruim aparece. `_preview.png` é a folha ampliada 5×. Nenhum dos dois é
asset.

Tudo gerado por código determinístico (`fonte/ground.py`).
