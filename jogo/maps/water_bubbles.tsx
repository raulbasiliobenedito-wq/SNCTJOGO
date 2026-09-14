<?xml version="1.0" encoding="UTF-8"?>
<!-- Bolhas subindo da água (GrassLand). Confirmado com o Raul em
     2026-09-11: arquivo 160x32, 5 quadros de 32x32 em fileira horizontal.
     Pinte o tile 0 (o único com animação) espalhado sobre a água, em cima
     de water_surface.tsx — pensado pra tocar em sequência com
     water_bubbles_gone.tsx (bolha sobe aqui, "estoura" lá), mas são dois
     tilesets/loops independentes por enquanto: o Tiled não anima um tile
     usando quadros de OUTRO tileset. Se quiser as duas fases bem seguidas
     numa animação só de verdade, dá pra juntar os dois arquivos num só no
     Aseprite (concatenar os quadros lado a lado) que eu refaço o .tsx. -->
<tileset version="1.10" tiledversion="1.12.2" name="water_bubbles" tilewidth="32" tileheight="32" tilecount="5" columns="5">
 <image source="../images/new_tilesets/Multi_Platformer_Tileset_Free/GrassLand/Props/Animated/GrassLand_WaterBubbles.png" width="160" height="32"/>
 <tile id="0">
  <animation>
   <frame tileid="0" duration="120"/>
   <frame tileid="1" duration="120"/>
   <frame tileid="2" duration="120"/>
   <frame tileid="3" duration="120"/>
   <frame tileid="4" duration="120"/>
  </animation>
 </tile>
</tileset>
