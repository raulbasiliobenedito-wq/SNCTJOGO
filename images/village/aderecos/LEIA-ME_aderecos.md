# ADEREÇOS DE VILA — DOZE PEÇAS

Mesma gramática chapada das casas, do interior e do chão: **preenchimento
sólido, 2 a 3 tons por forma, contorno preto puro de 1 px por forma, alfa só 0
ou 255**. Fundo 100% transparente, sem chão embutido.

---

## 1. ARQUIVOS

| Arquivo | Dimensão | Célula |
|---|---|---|
| `aderecos.png` | 256×192 | **64×64** · grade 4×3 |
| 12 PNGs avulsos | 64×64 | |
| `_preview.png` · `_maquete_vila.png` | — | conferência, não são assets |

**29 cores.** Grade:

```
arvore_verde   arvore_outono   arvore_pequena   poste
banco          poco            placa            canteiro
arbusto_a      arbusto_b       cerca            cerca_ponta
```

---

## 2. A LINHA DE BASE É A MESMA DE TUDO

**A última linha pintada é y 62** — idêntica à das casas da vila. Um quadro de
64×64 cobre exatamente **2×2 tiles de chão**, então:

```
posição_y = topo_do_terreno − 63
```

vale para casa, árvore, poste e banco sem exceção. `_maquete_vila.png` é a prova:
duas casas, dez adereços e o tileset de chão colados com essa única conta, sem
ajuste manual em nenhum deles.

---

## 3. A CERCA É O ÚNICO QUADRO QUE VAI DE BORDA A BORDA

Os travessões tocam **x 0 e x 63 e não levam tampa preta nas pontas** — é a ponta
aberta que faz a cerca correr sem emenda quando o quadro se repete.
`cerca_ponta` fecha a fileira com o mourão terminal. Ordem de uso:

```
cerca · cerca · cerca · cerca_ponta
```

Espelhando `cerca_ponta` você fecha o outro lado.

---

## 4. QUATRO DECISÕES QUE VALEM EXPLICAR

**A copa é a UNIÃO dos lobos, com um contorno só.** Contornar lobo a lobo faria
uma teia preta dentro da folhagem. O que separa os lobos por dentro é o **arco
escuro na base de cada um** — é assim que copa de livro infantil se lê.

**A árvore de outono tem 6 lobos pequenos, não 1 grande.** Com um lobo central
grande, o arco escuro da base dele atravessava a copa inteira e lia como emenda,
não como moita.

**Os montantes do encosto do banco descem até o chão e viram as pernas de trás.**
É essa continuidade que faz ler como banco: na primeira versão o encosto flutuava
atrás de um assento claro demais e o conjunto lia como mesa com uma tábua
encostada.

**A haste das flores do canteiro é curta.** Com 12 px de talo elas liam como
pirulito no arame; com 6 px e duas folhinhas, leem como flor.

---

## 5. INTEGRAÇÃO

- Escala só em **múltiplos inteiros**, filtro **nearest neighbor**.
- Camadas sugeridas, de trás para a frente: árvores grandes → casas → cerca,
  poste, poço, placa → arbustos, canteiro, banco.
- O lampião é tom sólido, sem bloom. Se quiser luz de verdade, some um halo em
  camada aditiva **por cima**, no motor — não dentro do sprite, senão ele deixa
  de casar com o resto do estilo.
- Árvores e arbustos não têm sombra projetada: se o jogo usar sombra, ponha uma
  elipse escura em camada separada, na linha do terreno.

Tudo gerado por código determinístico (`fonte/props.py`); a maquete sai de
`fonte/_vila_mock.py`.
