# INTERIOR — NOVE MÓVEIS E OBJETOS

Mesma gramática chapada da vila: **preenchimento sólido, 2 a 3 tons por forma,
contorno preto puro de 1 px por forma, alfa só 0 ou 255**. Sem degradê, sem
brilho, sem sombra projetada, sem anti-aliasing.

---

## 1. ARQUIVOS

| Arquivo | Dimensão | Célula |
|---|---|---|
| `interior.png` | 144×144 | **48×48** · grade 3×3 |
| `cama.png` · `mesa_cadeiras.png` · `estante.png` · `tapete.png` · `janela.png` · `luminaria.png` · `armario.png` · `quadro.png` · `vaso_planta.png` | 48×48 | avulsos |
| `_preview.png` · `_maquete.png` | — | conferência, não são assets |

**30 cores.** Toda célula deixa margem em todos os lados — dá para fatiar de 48
em 48 sem raspar contorno.

Ordem na folha (linha por linha):

```
cama            mesa+cadeiras   estante
tapete          janela          luminária
armário         quadro          vaso com planta
```

---

## 2. AS DUAS REGRAS QUE SEGURAM A ESCALA

**Linha do chão em y 44** para tudo que fica no chão — cama, mesa, estante,
tapete, luminária, armário, vaso. Colando as células no mesmo piso, os sete
assentam sozinhos, sem ajuste por objeto. É isso que `_maquete.png` demonstra:
todas as células foram coladas em y 0 e mesmo assim nada flutua.

**Altura de parede fixa** para o que é pendurado: janela ocupa y 6–34, quadro
y 7–28. São as alturas certas em relação a uma personagem de ~45 px (a altura
das cientistas e da Lia).

Contra essa personagem de 45 px:

| | Altura acima do chão | Lê como |
|---|---|---|
| assento da cadeira | 14 px | coxa |
| tampo da mesa | 20 px | quadril |
| bancada do armário | 25 px | cintura |
| colchão | 18 px | quadril |
| topo da estante | 36 px | acima da cabeça |

---

## 3. A PALETA NÃO É NOVA

Sai inteira da vila — de propósito:

| Peça | De onde vem a cor |
|---|---|
| colcha da cama · cortina da janela | parede da **casa de tijolo** |
| verde da planta | telhado da **casa amarela** |
| terracota do vaso | telhado da **casa creme** |
| azul do armário | parede da **casa azul** |
| azul do tapete | porta da **casa creme** |
| creme, vidro, pedra | idênticos aos da vila |

É o que faz o dentro e o fora parecerem a mesma casa em vez de dois conjuntos
que por acaso dividem o estilo.

---

## 4. QUATRO DECISÕES QUE VALEM EXPLICAR

**O tapete é oval, não faixa reta.** Visto de lado, é a única peça que fica no
chão sem encostar em parede nenhuma — de retângulo reto ele lia como degrau ou
plataforma. A elipse tira a ambiguidade na hora.

**As folhas da planta são elipses inclinadas.** Disco redondo sem rotação vira
brócolis; a folha precisa apontar na direção do talo.

**A cortina da janela tem cor própria, não creme.** Creme sobre caixilho creme
sumia. O rosa é o mesmo da colcha — dois móveis do mesmo cômodo, amarrados.

**A colcha tem duas dobras largas, não listras.** Na primeira versão havia uma
listra a cada 5 px e a cama lia como colchão de circo.

---

## 5. INTEGRAÇÃO

- Escala só em **múltiplos inteiros**, filtro **nearest neighbor**.
- Nada tem chão embutido: o piso entra por baixo, encostando em y 45.
- Móveis de chão vão na camada à frente do piso; janela e quadro na camada da
  parede, atrás de tudo.
- O tapete deve ser desenhado **antes** da mesa — é o que a maquete faz.

Tudo gerado por código determinístico (`fonte/interior.py`) — dá para
re-renderizar trocando paleta, número de livros, cor de colcha ou altura de
bancada.
