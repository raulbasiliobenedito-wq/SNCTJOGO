/* ==========================================================================
   Echoes of Life — comportamento do site de apresentação
   --------------------------------------------------------------------------
   Nada aqui depende da internet: sem CDN, sem framework. O arquivo cuida de
     1. animar os sprites do jogo direto das folhas de arte de images/
     2. navegação (menu do celular, seção ativa, barra de progresso)
     3. aparição das seções ao rolar
     4. abas da seção "Jogar" e detecção do build web
   ========================================================================== */
(function () {
  'use strict';

  var semAnimacao = window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* 1. SPRITES ============================================================
     Cada entrada descreve UMA folha de arte do jogo do mesmo jeito que o
     Python descreve (ver Game._load_grid_sheet em game.py): tamanho do
     quadro, qual linha usar e quantos quadros essa linha tem.

     O número de colunas NÃO é fixo aqui: ele é medido da largura real do
     arquivo depois que a imagem carrega. Foi exatamente isso que quebrou o
     site anterior — a arte foi reexportada num tamanho diferente e todos os
     recortes continuaram apontando pras medidas antigas, então cada sprite
     aparecia cortado no lugar errado. Medindo o arquivo, reexportar a arte
     não quebra mais nada, desde que o tamanho do QUADRO continue o mesmo. */
  var FOLHAS = {
    lia:        { arquivo: 'player/player_sheet.png',  q: [64, 96], linha: 0, quadros: [1, 2, 3, 4], fps: 8 },
    lia_parada: { arquivo: 'player/player_sheet.png',  q: [64, 96], linha: 0, quadros: [0],          fps: 1 },
    joaquim:    { arquivo: 'npcs/seu_joaquim_idle.png', q: [48, 48], linha: 0, quadros: 6, fps: 8 },

    /* cientistas_idle.png: grade 8x5, 48x48, uma linha por cientista
       (a mesma ordem de NPC_SPRITE_ROWS em game.py) */
    curie:      { arquivo: 'npcs/cientistas_idle.png', q: [48, 48], linha: 0, quadros: 8, fps: 8 },
    lovelace:   { arquivo: 'npcs/cientistas_idle.png', q: [48, 48], linha: 1, quadros: 8, fps: 8 },
    johnson:    { arquivo: 'npcs/cientistas_idle.png', q: [48, 48], linha: 2, quadros: 8, fps: 8 },
    jaqueline:  { arquivo: 'npcs/cientistas_idle.png', q: [48, 48], linha: 3, quadros: 8, fps: 8 },
    franklin:   { arquivo: 'npcs/cientistas_idle.png', q: [48, 48], linha: 4, quadros: 8, fps: 8 },

    /* inimigos — linha 0 é "idle" em todas as folhas, menos o slime comum,
       cuja linha 0 não é usada nem pelo jogo (ver _load_slime_sprites) */
    slime:      { arquivo: 'enemies/slime_common.png',      q: [32, 32], linha: 1, quadros: 8, fps: 8 },
    cervo:      { arquivo: 'enemies/crystal_stag.png',      q: [40, 34], linha: 0, quadros: 8, fps: 8 },
    sombra:     { arquivo: 'enemies/dark_wraith.png',       q: [48, 48], linha: 0, quadros: 8, fps: 8 },
    estudante:  { arquivo: 'enemies/possessed_student.png', q: [48, 48], linha: 0, quadros: 8, fps: 8 },
    zelador:    { arquivo: 'enemies/janitor_guardian.png',  q: [64, 64], linha: 0, quadros: 8, fps: 8 },

    /* chefes */
    rei_slime:  { arquivo: 'enemies/slime_king.png',     q: [64, 64],   linha: 0, quadros: 8, fps: 7 },
    especime:   { arquivo: 'enemies/lab_specimen.png',   q: [56, 48],   linha: 0, quadros: 8, fps: 7 },
    bibliotecario: { arquivo: 'enemies/librarian_boss.png', q: [64, 64], linha: 0, quadros: 8, fps: 7 },
    dragao:     { arquivo: 'enemies/dragon.png',         q: [324, 265], linha: 0, quadros: 9, fps: 7 }
  };

  /* items.png: quadro 16x16, 4 colunas, uma linha por item — a mesma ordem
     de ITEM_DEFS["row"] em game.py. Ícone estático (primeiro quadro), igual
     ao que o HUD do jogo mostra no inventário. */
  function folhaDeItem(linha) {
    return { arquivo: 'items/items.png', q: [16, 16], linha: linha, quadros: [0], fps: 1 };
  }

  var BASE = '../images/';
  var cacheImagens = {};

  function carregarImagem(caminho) {
    if (!cacheImagens[caminho]) {
      cacheImagens[caminho] = new Promise(function (resolve, reject) {
        var img = new Image();
        img.onload = function () { resolve(img); };
        img.onerror = function () { reject(new Error(caminho)); };
        img.src = BASE + caminho;
      });
    }
    return cacheImagens[caminho];
  }

  function listaDeQuadros(folha, colunas) {
    var lista = typeof folha.quadros === 'number'
      ? Array.apply(null, { length: folha.quadros }).map(function (_, i) { return i; })
      : folha.quadros.slice();
    /* trava de segurança: nunca pedir uma coluna que não existe no arquivo */
    return lista.filter(function (i) { return i < colunas; });
  }

  function montarSprite(el) {
    var nome = el.dataset.sprite;
    var folha = FOLHAS[nome];
    if (!folha && /^item-\d+$/.test(nome || '')) {
      folha = folhaDeItem(parseInt(nome.split('-')[1], 10));
    }
    if (!folha) { el.hidden = true; return; }

    var escala = parseFloat(el.dataset.escala) || 2;

    carregarImagem(folha.arquivo).then(function (img) {
      var lq = folha.q[0], aq = folha.q[1];
      var colunas = Math.floor(img.naturalWidth / lq);
      var linhas = Math.floor(img.naturalHeight / aq);
      if (colunas < 1 || folha.linha >= linhas) { el.hidden = true; return; }

      var quadros = listaDeQuadros(folha, colunas);
      if (!quadros.length) { el.hidden = true; return; }

      el.style.width = (lq * escala) + 'px';
      el.style.height = (aq * escala) + 'px';
      el.style.backgroundImage = 'url("' + BASE + folha.arquivo + '")';
      el.style.backgroundSize = (img.naturalWidth * escala) + 'px ' +
                                (img.naturalHeight * escala) + 'px';

      var topo = -(folha.linha * aq * escala);
      var i = 0;
      function desenhar() {
        el.style.backgroundPosition = (-(quadros[i] * lq * escala)) + 'px ' + topo + 'px';
      }
      desenhar();

      /* Um quadro só, ou o visitante pediu menos animação: fica parado. */
      if (quadros.length < 2 || semAnimacao) { return; }
      setInterval(function () {
        i = (i + 1) % quadros.length;
        desenhar();
      }, 1000 / (folha.fps || 8));
    }).catch(function () {
      /* Arte faltando (ex.: alguém moveu a pasta images/): esconde o quadro
         em vez de deixar um retângulo vazio no meio do cartão. */
      el.hidden = true;
    });
  }

  document.querySelectorAll('[data-sprite]').forEach(montarSprite);

  /* 2. NAVEGAÇÃO ========================================================= */

  var barraMenu = document.getElementById('menu');
  var menuBotao = document.getElementById('menu-botao');
  if (menuBotao && barraMenu) {
    menuBotao.addEventListener('click', function () {
      var aberto = barraMenu.classList.toggle('aberto');
      menuBotao.setAttribute('aria-expanded', aberto ? 'true' : 'false');
    });
    barraMenu.addEventListener('click', function (e) {
      if (e.target.tagName === 'A') {
        barraMenu.classList.remove('aberto');
        menuBotao.setAttribute('aria-expanded', 'false');
      }
    });
  }

  var progresso = document.getElementById('progresso');
  var linksMenu = Array.prototype.slice.call(
    document.querySelectorAll('#menu a[href^="#"]'));
  var secoes = linksMenu.map(function (a) {
    return document.querySelector(a.getAttribute('href'));
  }).filter(Boolean);

  function aoRolar() {
    if (progresso) {
      var altura = document.documentElement.scrollHeight - window.innerHeight;
      var lido = altura > 0 ? (window.scrollY / altura) * 100 : 0;
      progresso.style.width = Math.min(100, Math.max(0, lido)) + '%';
    }
    /* seção ativa: a última cujo topo já passou de 40% da tela */
    var atual = null;
    var limite = window.innerHeight * 0.4;
    secoes.forEach(function (s) {
      if (s.getBoundingClientRect().top <= limite) { atual = s; }
    });
    linksMenu.forEach(function (a) {
      a.classList.toggle('ativo', atual && a.getAttribute('href') === '#' + atual.id);
    });
  }

  var agendado = false;
  window.addEventListener('scroll', function () {
    if (agendado) { return; }
    agendado = true;
    window.requestAnimationFrame(function () { aoRolar(); agendado = false; });
  }, { passive: true });
  aoRolar();

  /* 3. APARIÇÃO AO ROLAR ================================================= */

  var revelaveis = document.querySelectorAll('.revelar');
  if (semAnimacao || !('IntersectionObserver' in window)) {
    revelaveis.forEach(function (el) { el.classList.add('visivel'); });
  } else {
    var observador = new IntersectionObserver(function (entradas) {
      entradas.forEach(function (entrada) {
        if (entrada.isIntersecting) {
          entrada.target.classList.add('visivel');
          observador.unobserve(entrada.target);
        }
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.05 });
    revelaveis.forEach(function (el) { observador.observe(el); });
  }

  /* 4. SEÇÃO "JOGAR" ===================================================== */

  var abas = Array.prototype.slice.call(document.querySelectorAll('.aba'));
  abas.forEach(function (aba) {
    aba.addEventListener('click', function () {
      abas.forEach(function (outra) {
        var alvo = document.getElementById(outra.getAttribute('aria-controls'));
        var ativa = outra === aba;
        outra.setAttribute('aria-selected', ativa ? 'true' : 'false');
        if (alvo) { alvo.hidden = !ativa; }
      });
    });
  });

  /* Só troca o aviso pelo jogo se o build web existir de verdade. Abrindo o
     index.html direto (file://) o fetch abaixo é bloqueado pelo navegador —
     nesse caso o aviso com as instruções continua na tela, que é o
     comportamento certo por padrão. */
  var quadro = document.getElementById('quadro-jogo');
  var aviso = document.getElementById('aviso-jogo');
  /* Abrindo o arquivo direto (file://) o navegador bloqueia qualquer fetch e
     ainda escreve um erro vermelho no console — como nesse caso a resposta
     seria "não dá pra saber" de qualquer jeito, nem tentamos. */
  if (quadro && aviso && location.protocol !== 'file:') {
    fetch('jogo_web/index.html', { method: 'GET', cache: 'no-store' })
      .then(function (r) {
        if (!r.ok) { return; }
        quadro.src = 'jogo_web/index.html';
        quadro.style.display = 'block';
        aviso.style.display = 'none';
      })
      .catch(function () { /* sem build web ainda — mantém o aviso */ });
  }

  /* 5. PARALAXE SUAVE DA CAPA ============================================ */

  var fundoCapa = document.querySelector('.capa__fundo');
  if (fundoCapa && !semAnimacao) {
    window.addEventListener('scroll', function () {
      var y = window.scrollY;
      if (y > window.innerHeight) { return; }
      fundoCapa.style.transform = 'scale(1.08) translateY(' + (y * 0.18) + 'px)';
    }, { passive: true });
  }
})();
