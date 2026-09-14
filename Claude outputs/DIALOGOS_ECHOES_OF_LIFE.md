# Diálogos de *Echoes of Life* — reescrita completa

Documento de proposta. **Nada foi alterado no código.** Tudo aqui é texto pronto
pra colar, mais a única mudança técnica que ele exige.

Lido em 13/09/2026 a partir de `jogo/game_data.py`, `jogo/cutscene.py`,
`jogo/dialogue.py`, `jogo/interactions.py`, `jogo/level.py`, `jogo/game.py` e
`jogo/maps/vila.tmx`, na versão que está na sua pasta (a refatoração em `jogo/`
ainda não está no GitHub).

---

## 1. O diagnóstico

Você está certo: **a Lia é muda no jogo inteiro, menos na cutscene do hospital.**

| Onde | Como está hoje |
| --- | --- |
| Cutscene do hospital | ✅ Já é conversa de verdade — 6 falas alternando Mãe e Lia |
| 6 moradores da vila | ❌ Monólogo. A Lia nunca responde |
| 5 cientistas | ❌ Monólogo de uma fala só, formato currículo |
| Fragmentos de pesquisa | ❌ Um fato solto, sem reação |
| Achados das salas | ❌ Fala da Lia, mas descritiva ("um frasco rachado...") |

E tem um problema de escrita por baixo disso: **as cientistas se apresentam como
verbete de enciclopédia.** "Calculei à mão as trajetórias que levaram naves ao
espaço. Confie na sua própria conta." Isso é uma legenda de museu, não uma
pessoa falando com uma menina de 12 anos. O fato está lá, mas ninguém conversa.

O bom é que **o motor já faz tudo que precisa.** A `IntroCutscene` guarda
`BEATS = ((falante, texto), ...)` e chama `dialogue_box.start(falante, texto)` a
cada [E]. A caixa já desenha o nome de quem fala. Ou seja: conversa alternada já
funciona no jogo — só nunca foi usada fora da cutscene.

---

## 2. Quanto texto cabe de verdade

Medi rodando a `DialogueBox` de verdade, sem chutar:

- Caixa: **1228 × 318 px**, faixa útil de texto **1088 px de largura por 86 px de altura**
- A fonte encolhe sozinha (17 → 15 → 13 → 11 px) pra fala não vazar a moldura

| Tamanho da fala | Resultado |
| --- | --- |
| até ~180 caracteres | 3 linhas, fonte cheia (17 px) — **ideal** |
| até ~220 caracteres | 4 linhas, fonte cheia (17 px) — **limite confortável** |
| ~260 caracteres | 4 linhas, fonte cai pra 15 px |
| ~300 caracteres | 4 linhas, fonte cai pra 13 px — começa a cansar |
| acima de 340 | 5 linhas em 13 px |

A revelação é de **0,65 caractere por quadro = ~39 caracteres por segundo**. Uma
fala de 200 caracteres leva **5 segundos** pra terminar de aparecer.

**A regra que eu segui:** falas longas, sim — mas longas em *quantidade de
falas*, não em tamanho de balão. Nenhum beat deste documento passa de 220
caracteres. Uma conversa de 8 beats curtos tem muito mais presença que 2 balões
gigantes, e não obriga ninguém a esperar 9 segundos olhando texto aparecer.

---

## 3. A mudança de código (8 linhas)

Hoje `NPC_DIALOGUES[nome]` é uma string ou uma tupla de strings, e
`interactions.py` guarda **um falante só** pra toda a fila:

```python
# interactions.py — como está
self._npc_dialogue_speaker = npc["name"]
self._npc_dialogue_queue = list(text[1:])
self.game.dialogue.start(npc["name"], text[0])
...
next_text = self._npc_dialogue_queue.pop(0)
self.game.dialogue.start(self._npc_dialogue_speaker, next_text)
```

Pra alternar quem fala, a fila passa a guardar **pares `(falante, texto)`** — o
mesmo formato que a `IntroCutscene` já usa:

```python
# interactions.py — talk_to_npc
beats = NPC_DIALOGUES.get(npc["name"])
if isinstance(beats, str):
    # compatibilidade: fala única vira uma conversa de um beat só
    beats = ((npc["name"], beats),)
if beats:
    self._npc_dialogue_queue = list(beats[1:])
    self.game.dialogue.start(*beats[0])
return True

# interactions.py — update_dialogue
if self._npc_dialogue_queue:
    self.game.dialogue.start(*self._npc_dialogue_queue.pop(0))
else:
    self.game.dialogue.close()
```

`self._npc_dialogue_speaker` deixa de existir. O ramo `isinstance(beats, str)`
mantém funcionando qualquer diálogo que você escreva como string solta.

**Opcional, mesma fila:** os fragmentos de pesquisa e os achados das salas
(`game.py`, `_collect_research` e `_collect_artifacts`) também chamam
`dialogue.start` uma vez só. Enfileirando do mesmo jeito, eles ganham a reação
da Lia — ver §8.

---

## 4. Como cada um fala

### Lia
Tem uns 12 anos e está carregando uma coisa grande sozinha. Isso define tudo:

- **Fala curto.** Frases de 4 a 10 palavras. Quem responde comprido é adulto.
- **Pergunta mais do que afirma.** É a personagem mais curiosa do jogo; a
  curiosidade dela é a mecânica da história.
- **Desconversa quando chegam perto do assunto da mãe.** Não por birra — porque
  falar em voz alta torna real. Ela só diz a palavra "câncer" **duas vezes no
  jogo inteiro**, e as duas importam (§5).
- **Não é sábia.** Nunca fecha uma cena com lição. Quem dá lição são os adultos;
  ela recebe, rebate ou fica quieta.
- **Nunca agradece formalmente.** "Tá anotado", "beleza", "tá" — é criança.

### Os moradores da vila
Gente simples, calor humano, frase curta. Falam com a Lia como quem viu ela
crescer. Nenhum deles explica mecânica de jogo como se fosse manual: explicam
como quem dá um toque prático ("já tentei e já caí duas vezes").

### As cientistas
A regra que mudou tudo: **elas não se apresentam.** Ninguém chega dizendo o
próprio currículo. Elas reagem ao que a Lia está fazendo ali, ela pergunta, e o
fato histórico aparece **dentro da resposta**, como quem conta uma coisa que
viveu. O nome delas já está na caixa de diálogo — não precisa repetir na fala.

Cada uma também está no **começo** da área dela (conferi no `.tmx`: Franklin em
x=171, Johnson em x=198, Curie em x=250, Lovelace em x=250, Jaqueline em x=264).
Elas não são prêmio de fim de fase: são a pessoa que a Lia encontra **antes** da
parte difícil. Escrevi as falas com isso em mente — são um empurrão na entrada,
não um parabéns na saída.

---

## 5. O arco: quem sabe, e quando

Esse é o fio que amarra os diálogos todos. Hoje ele não existe.

| Momento | O que a Lia diz sobre a mãe |
| --- | --- |
| Hospital | Ouve. Pergunta se tem cura. Não processou ainda |
| Seu Joaquim, Bento, Dona Marta | **Não fala nada.** Desconversa três vezes seguidas |
| **Sra. Amélia** (fim da vila) | **Diz em voz alta pela primeira vez.** "É. Câncer." |
| Franklin (Fase 1) | Não fala. Ainda é cedo, e ela mal conhece a mulher |
| Johnson (Fase 2) | Não fala — mas admite que está com medo de ter errado |
| Curie (Fase 2) | Chega perto. Pergunta por que alguém anota o que descobriu |
| Lovelace (Fase 2) | Chega mais perto: procura resposta "que ainda não existe" |
| **Jaqueline** (Fase 3) | **Diz a segunda vez.** E aí ouve a única resposta honesta |

As três recusas da vila são de propósito. Elas fazem a cena da Sra. Amélia
funcionar — é a quarta vez que perguntam, e é a vez em que ela cede.

---

## 6. Cutscene do hospital

Substitui `IntroCutscene.BEATS` em `jogo/cutscene.py`. De 6 para 10 beats.

O que mudou: a mãe **hesita** antes de dizer (hoje ela solta a informação de
primeira, o que soa ensaiado); a Lia faz a pergunta que uma criança faria de
verdade ("mas vai passar, né?") em vez da pergunta adulta ("isso tem cura?"); e
a cena fecha com a Lia devolvendo a frase pra mãe, o que dá o tom do jogo
inteiro — ninguém procura sozinho.

> **Mãe** — Lia. Vem cá, senta aqui um pouquinho comigo.
>
> **Lia** — Sua voz tá esquisita.
>
> **Mãe** — Tá, né. Os médicos acharam uma coisa em mim, filha. Chama câncer.
>
> **Lia** — ...
>
> **Mãe** — Vou fazer tratamento. E vão ter dias em que eu não vou estar muito boa. Preferi você saber por mim.
>
> **Lia** — Mas vai passar, né, mãe?
>
> **Mãe** — Eu não sei. Ninguém sabe ainda. Tem gente estudando isso agora, nesse minuto — em laboratório, em universidade, em centro de pesquisa.
>
> **Lia** — Então alguém pode descobrir.
>
> **Mãe** — Pode. E muita gente vai tentar e errar antes. Todo experimento pode falhar, Lia. Levanta e tenta de novo — isso vale pra ciência e vale pra vida.
>
> **Lia** — Então é isso que eu vou fazer. Vou atrás de cada pista que existir por aí.
>
> **Mãe** — Você não precisa carregar isso sozinha.
>
> **Lia** — Você também não.

> **Nota:** o brilho coral aparece no último beat (`self.index == len(BEATS) - 1`,
> em `cutscene.py`). Com a lista nova, ele cai em "Você também não." — que é o
> lugar certo: a primeira vez que o coral aparece é junto da decisão dela.

---

## 7. A vila

Ordem real em que a Lia encontra cada um, conferida no `vila.tmx`:
Joaquim (x=180) → Bento (x=1704) → Dona Marta (x=1855) → *slime* (x=2964) →
Cadu (x=3332) → Zeca (x=5454) → Sra. Amélia (x=6529).

### Seu Joaquim — x=180, logo no primeiro passo
Ensina **mover, pular e [E]**. Hoje ele ensina F e Q também, o que atropela o
Cadu e o Zeca — o `PLANO_VILA.md` já diz que o tutorial passou a ser distribuído,
mas a fala dele não acompanhou. Tirei F e Q daqui.

> **Seu Joaquim** — Lia! Cedo pra tá de pé, hein. Vai pra onde com essa cara de missão?
>
> **Lia** — Até a escola. Preciso de uma coisa lá.
>
> **Seu Joaquim** — Escola hoje. Tá certo. Então leva um conselho de graça: a estrada daqui pra lá não tá mais tão mansa quanto era.
>
> **Lia** — Como assim?
>
> **Seu Joaquim** — Apareceu bicho. Nada do outro mundo, mas é bom saber se mexer. Seta pra andar, espaço pra pular.
>
> **Lia** — E se alguém quiser conversar?
>
> **Seu Joaquim** — Chega perto e aperta E. Ninguém aqui morde. Vai com Deus, menina.

### Bento — x=1704, o amigo
A primeira recusa. Ele é o único que não faz drama — e por isso a cena dói mais.

> **Bento** — Lia! Achei que você não ia sair hoje.
>
> **Lia** — Ia sim. Só demorei.
>
> **Bento** — Joga bola depois? Tá todo mundo lá no campinho.
>
> **Lia** — Hoje não dá.
>
> **Bento** — ...Tá. Você tá indo pra algum lugar importante, né? Dá pra ver na sua cara.
>
> **Lia** — Dá tanto assim?
>
> **Bento** — Dá. Vai lá. Eu seguro a sua vaga no time.

### Dona Marta — x=1855, y=61 (na janela, acima da rua)
A segunda recusa — mas essa quase quebra a Lia, porque fala da mãe sem saber.

> **Dona Marta** — Bom dia, flor! Olha o tamanho que você tá.
>
> **Lia** — Bom dia, dona Marta.
>
> **Dona Marta** — Sua mãe fala de você toda vez que eu passo lá. Todinha vez.
>
> **Lia** — Fala o quê?
>
> **Dona Marta** — "A Lia perguntou isso. A Lia quis saber aquilo." Com um orgulho que dá gosto de ouvir.
>
> **Lia** — ...
>
> **Dona Marta** — Se você for pra algum canto hoje, vai sabendo disso, viu?

### Cadu — x=3332, depois do slime
Ensina o **ataque [F]**.

> ⚠️ **Achei um problema de posição:** o slime está em x=2964 e o Cadu em
> x=3332. A Lia **passa pelo bicho antes** de receber a explicação. Escrevi a
> fala assumindo isso (ele pergunta se ela já passou), então funciona do jeito
> que está. Mas se você quiser o tutorial antes do obstáculo, é só mover o Cadu
> pra uns x=2700 no Tiled — aí a primeira fala dele vira "tem um bichinho ali
> na frente".

> **Cadu** — Psiu! Lia! Você passou pelo bichinho de geleia ali atrás?
>
> **Lia** — Passei. Ele quase encostou em mim.
>
> **Cadu** — Fugiu do quintal do meu avô, esse aí. Não morde forte, mas gruda no caminho da gente.
>
> **Lia** — E como é que eu tiro ele da frente?
>
> **Cadu** — Aperta F quando ele chegar perto. Ele se assusta e abre espaço. Não precisa judiar, é só pra ele entender.
>
> **Lia** — F. Beleza.
>
> **Cadu** — Se aparecer mais, faz igual. Dizem que tem uns bem maiores lá pra frente.

### Zeca — x=5454, na beira do buraco
Ensina a **investida [Q]**. A fala dele planta, sem perceber, a frase da mãe.

> **Zeca** — Ô Lia, para aí. Tá vendo esse buraco?
>
> **Lia** — Tô. É largo.
>
> **Zeca** — Largo demais pra pular normal. Eu já tentei e já caí. Duas vezes.
>
> **Lia** — E como você passou?
>
> **Zeca** — Aperta Q correndo. Você dispara e passa reto por cima antes de perceber.
>
> **Lia** — E se eu apertar na hora errada?
>
> **Zeca** — Aí você cai igual eu caí. Mas cair também ensina, né? Vai lá.

### Sra. Amélia — x=6529, a última antes da estrada
A cena mais importante da vila. É aqui que a Lia diz em voz alta pela primeira
vez. Hoje são 3 falas onde só a Amélia fala; viram 10.

> **Sra. Amélia** — Lia. Vem cá um instantinho, minha filha.
>
> **Lia** — Oi, dona Amélia.
>
> **Sra. Amélia** — Eu não sei se é da minha conta. Mas me falaram uma coisa da sua mãe e eu não consegui dormir direito ontem.
>
> **Lia** — ...
>
> **Sra. Amélia** — É verdade mesmo, filha?
>
> **Lia** — É. Câncer. Os médicos falaram essa semana.
>
> **Sra. Amélia** — Sinto muito. Sinto muito mesmo, meu bem.
>
> **Lia** — Todo mundo fala isso.
>
> **Sra. Amélia** — Porque não tem outra coisa pra falar. A gente fica sem palavra.
>
> **Lia** — Eu não quero palavra. Eu quero saber se dá pra fazer alguma coisa.
>
> **Sra. Amélia** — E dá?
>
> **Lia** — Eu não sei ainda. É isso que eu vou descobrir.
>
> **Sra. Amélia** — Então vai. Mas passa aqui na volta, ouviu? Nem que seja pra dizer que não achou nada.

---

## 8. As cientistas

Nenhuma delas se apresenta. O fato histórico sai no meio da conversa.

### Rosalind Franklin — Fase 1, Escola · *olhar*

> **Rosalind Franklin** — Você é a primeira pessoa a entrar aqui em semanas. E foi direto pro canto mais escuro da sala.
>
> **Lia** — É que tem uma coisa brilhando ali. Ninguém mais viu?
>
> **Rosalind Franklin** — Viram. Só não olharam. É diferente.
>
> **Lia** — Qual é a diferença?
>
> **Rosalind Franklin** — Eu passei dias fotografando uma coisa que ninguém conseguia enxergar. Raio X, fibra de DNA, uma exposição de cada vez.
>
> **Lia** — Dias numa foto só?
>
> **Rosalind Franklin** — Uma delas levou mais de sessenta horas de exposição. A de número 51 foi a que finalmente mostrou a forma.
>
> **Lia** — Sessenta horas esperando uma foto.
>
> **Rosalind Franklin** — Olhar com atenção é trabalho, Lia, não é talento. Vai fundo no que os outros acharam que não valia a pena.

### Katherine Johnson — Fase 2, corredor · *confiar na própria conta*

> **Katherine Johnson** — Você parou. Por quê?
>
> **Lia** — Porque eu acho que errei o caminho. Devia ter voltado lá atrás.
>
> **Katherine Johnson** — Você fez a conta ou você chutou?
>
> **Lia** — ...Fiz a conta.
>
> **Katherine Johnson** — Então confia nela. Eu calculei à mão a trajetória de uma cápsula que levava um homem pro espaço e trazia ele de volta.
>
> **Lia** — À mão? Não tinha computador?
>
> **Katherine Johnson** — Tinha. E antes de subir, o astronauta pediu que eu conferisse os números da máquina. Ele não confiava mais em mim que na máquina — ele confiava na conta.
>
> **Lia** — ...
>
> **Katherine Johnson** — Refaz a sua e segue em frente.

### Marie Curie — Fase 2, laboratório · *método e preço*

> **Marie Curie** — Cuidado com o que está naquele tanque. Não porque é monstro. Porque ninguém entende ainda.
>
> **Lia** — A senhora trabalha com coisa perigosa?
>
> **Marie Curie** — Trabalhei. Tratei toneladas de minério pra tirar um décimo de grama de rádio. Anos mexendo com uma coisa que brilhava sozinha.
>
> **Lia** — E era perigoso?
>
> **Marie Curie** — Era. Eu não sabia ainda o quanto.
>
> **Lia** — Se a senhora soubesse, teria parado?
>
> **Marie Curie** — Não sei. Mas teria anotado tudo do mesmo jeito, pra que a próxima pessoa soubesse.
>
> **Lia** — É por isso que a senhora escrevia tanto?
>
> **Marie Curie** — É por isso que qualquer um escreve. O que eu descubro só serve se atravessar até você.

### Ada Lovelace — Fase 2, biblioteca · *imaginar antes*

> **Ada Lovelace** — Esses livros todos, e você entrou procurando um só. Qual?
>
> **Lia** — Um que explique uma coisa que ainda não tem explicação.
>
> **Ada Lovelace** — Ah. Esse é o tipo mais difícil. Costuma não estar escrito ainda.
>
> **Lia** — E aí, o que se faz?
>
> **Ada Lovelace** — Escreve. Eu descrevi como uma máquina poderia calcular uma sequência de números antes de existir máquina capaz de rodar aquilo.
>
> **Lia** — A senhora escreveu instrução pra uma coisa que não existia?
>
> **Ada Lovelace** — Alguém tem que imaginar primeiro. Se a resposta que você procura ainda não existe, pode ser que ela esteja esperando alguém escrever.

### Jaqueline Goes de Jesus — Fase 3 · *ninguém descobre sozinho*

A segunda e última vez que a Lia diz em voz alta. E a única resposta
verdadeiramente honesta que ela recebe no jogo inteiro.

> **Jaqueline Goes de Jesus** — Você vem descendo desde a superfície, não vem? Dá pra ver no rosto.
>
> **Lia** — Venho. Faz tempo.
>
> **Jaqueline Goes de Jesus** — Procurando o quê?
>
> **Lia** — Alguma coisa que ajude a minha mãe. Ela está doente.
>
> **Jaqueline Goes de Jesus** — ...Entendi.
>
> **Lia** — A senhora ia dizer que não funciona assim, né?
>
> **Jaqueline Goes de Jesus** — Ia dizer que não funciona sozinho. Quando o vírus chegou no Brasil, a gente sequenciou o genoma dele em dois dias.
>
> **Lia** — Dois dias?
>
> **Jaqueline Goes de Jesus** — Dois dias em cima de anos de gente que veio antes e publicou o que sabia. E foi equipe, não fui eu. É sempre assim que anda.
>
> **Lia** — E se ninguém achar a resposta a tempo?
>
> **Jaqueline Goes de Jesus** — Aí alguém acha depois, por causa do que a gente tentou. Continua perguntando, Lia. E conta pra alguém o que você achar.

> **Cuidado deliberado:** Jaqueline Goes de Jesus é uma cientista viva. Mantive
> as falas dela **só** no que é público e documentado (o sequenciamento do
> genoma do SARS-CoV-2 no Brasil em 2020, em ~48 h, por uma equipe) e em
> encorajamento genérico. Ela **não** diz nada sobre câncer, não dá conselho
> médico e não promete nada. A resposta dela à pergunta da Lia é honesta
> justamente por não prometer.

---

## 9. Falas de repetição

Hoje, falar duas vezes com o mesmo NPC repete a conversa inteira — o que
atrapalha quem só quer conferir a tecla. Proposta: uma fala curta de repetição
por personagem, usada da segunda vez em diante.

| Personagem | Repetição |
| --- | --- |
| Seu Joaquim | "Seta pra andar, espaço pra pular. E volta pra contar, menina." |
| Bento | "Tua vaga tá guardada, viu?" |
| Dona Marta | "Toda vez, Lia. Ela fala de você toda vez." |
| Cadu | "F quando ele chegar perto. Ele abre espaço sozinho." |
| Zeca | "Q correndo. E se cair, cair também ensina." |
| Sra. Amélia | "Passa aqui na volta, minha filha. Nem que seja pra dizer que não achou." |
| Rosalind Franklin | "Olhe de novo. Tem sempre uma coisa que a primeira olhada perdeu." |
| Katherine Johnson | "Refaz a conta. E confia nela." |
| Marie Curie | "Anote o que você vir. Serve pra próxima pessoa." |
| Ada Lovelace | "Se não está escrito, escreva." |
| Jaqueline Goes de Jesus | "Continua perguntando. E conta pra alguém." |

Custo: mais um dicionário `NPC_REPEAT` e três linhas em `talk_to_npc` (um
`set()` de quem já foi visitado).

---

## 10. Fragmentos de pesquisa e achados

### Fragmentos (`SCIENCE_FACTS`)
O fato em si está bom e é factualmente correto — não mexi em nenhum. O que falta
é a Lia estar ali. Com a mesma fila da §3, cada fragmento vira dois beats:

| Fragmento | Reação da Lia (beat novo, depois do fato) |
| --- | --- |
| Curiosidade | "Dois. A mesma pessoa. Ela devia ter feito muita pergunta." |
| Observação | "Ela lutava por ciência e por gente ao mesmo tempo." |
| Hipótese | "Primeira. Alguém sempre tem que ser a primeira." |
| Experimento | "Isso foi no ano que eu nasci quase. E já ajudou tanta gente." |
| Registro | "Cuidar também é método, então." |
| Método | "Ela programou uma máquina que nem existia ainda." |
| Dados | "Conta feita à mão. E funcionou." |
| Análise | "Primeira de novo. Quantas vezes alguém teve que ser a primeira?" |
| Testes | "Foi ela que tirou a foto. Eu li sobre isso na escola." |
| Resultados | "Genética. Talvez seja por aí." |
| Cura | "Nitrogênio não cura ninguém. Mas alimentou muita gente." |
| Pesquisa completa | "Juntas. Sempre juntas. Acho que é isso que a minha mãe quis dizer." |

O último beat fecha o jogo inteiro amarrando na frase da mãe.

### Achados das salas (`ROOM_LORE`)
Já usam a Lia como falante, mas o texto é descrição neutra. Proposta: a descrição
continua, e ela reage.

**Amostra do Espécime 07**
> **Lia** — Um frasco rachado, ainda quente. A etiqueta diz "ESPÉCIME 07 — NÃO REMOVER DO TANQUE".
>
> **Lia** — Alguém removeu mesmo assim. E depois foi embora sem fechar a porta.

**Página Arrancada**
> **Lia** — Uma página solta, arrancada na pressa. A letra muda no meio da frase.
>
> **Lia** — Como se quem escrevia tivesse parado de ser humano no meio da palavra.

---

## 11. Como fica no código

Formato final de `NPC_DIALOGUES` em `jogo/game_data.py` — tupla de pares
`(falante, texto)`:

```python
NPC_DIALOGUES = {
    "Bento": (
        ("Bento", "Lia! Achei que você não ia sair hoje."),
        ("Lia", "Ia sim. Só demorei."),
        ("Bento", "Joga bola depois? Tá todo mundo lá no campinho."),
        ("Lia", "Hoje não dá."),
        ("Bento", "...Tá. Você tá indo pra algum lugar importante, né? Dá pra ver na sua cara."),
        ("Lia", "Dá tanto assim?"),
        ("Bento", "Dá. Vai lá. Eu seguro a sua vaga no time."),
    ),
    # ... idem pros outros 10
}
```

E `IntroCutscene.BEATS` em `jogo/cutscene.py` já é exatamente esse formato — só
trocar o conteúdo.

**Ordem sugerida de aplicação**, uma coisa por vez, testando entre cada:

1. `cutscene.py` — só troca de texto, zero risco, dá pra ver na hora
2. As 8 linhas de `interactions.py` (§3)
3. `NPC_DIALOGUES` da vila (6 personagens)
4. `NPC_DIALOGUES` das cientistas (5)
5. Falas de repetição (§9) — opcional
6. Fila nos fragmentos e achados (§10) — opcional

---

## 12. Verificação

Extraí as **114 falas** deste documento e passei cada uma pela `DialogueBox`
real do jogo, headless, com a fonte e a moldura de verdade:

| Checagem | Resultado |
| --- | --- |
| Falas que estouram a moldura | **0** |
| Falas que forçam a fonte a encolher | **0** — todas as 114 cabem em 17 px |
| Fala mais longa | 153 caracteres (Katherine Johnson), dentro do limite de 220 |
| Tempo de revelação | média 1,4 s por fala; a mais longa, 3,9 s |

Sobre os fatos: conferi cada um contra o que é público. Ajustei um só — a
Rosalind Franklin dizia "cem horas" e "cinquenta e uma fotos até sair a certa".
O número que as fontes repetem é a **exposição de mais de 60 horas** da Foto 51,
e o "51" é a etiqueta da imagem no caderno de laboratório, não a contagem de
tentativas. Reescrevi pro que dá pra afirmar.

---

## 13. O que eu não decidi sozinho

- **Não mudei nenhum fato científico.** Os 12 fragmentos e os fatos dentro das
  falas das cientistas continuam os que já estavam no jogo. Confirmei que cada
  um bate com o que é público sobre cada uma delas.
- **Não mexi na posição de ninguém** no Tiled. Só apontei o caso do Cadu (§7).
- **Não escrevi fala de chefe nem de vitória** — você não pediu, e isso mexe em
  outro sistema (`PHASES["dialogues"]`, hoje vazio nas três fases). Se quiser,
  eu faço numa próxima rodada.
- **O nome do falante dos fragmentos** hoje é "Ciência Delas". Mantive. Se
  preferir o nome da cientista em cada um, é um campo a mais na tabela.
- **Idade da Lia.** Escrevi ela com ~12 anos, que é o que o Bento (jogar bola),
  o "menina" do Joaquim e o "flor" da dona Marta sugerem. Se ela for mais velha
  na sua cabeça, me diz que eu reescrevo o registro dela — muda bastante.
