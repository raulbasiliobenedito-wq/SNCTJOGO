<?xml version="1.0" encoding="UTF-8"?>
<!-- Brilho animado da superfície da água (GrassLand). Confirmado com o Raul
     em 2026-09-11: arquivo 320x32, 5 quadros de 64x32 em fileira horizontal.
     Pinte o tile 0 (o único com animação, ver <tile id="0">) na borda de
     cima de qualquer área de água — mesmo esquema de água/lava animada da
     Fase 3 (ver fase3_pesquisa.tsx), sem precisar de nenhum código novo. -->
<tileset version="1.10" tiledversion="1.12.2" name="water_surface" tilewidth="64" tileheight="32" tilecount="5" columns="5">
 <image source="../images/new_tilesets/Multi_Platformer_Tileset_Free/GrassLand/Props/Animated/GrassLand_WaterSurfaceAnim.png" width="320" height="32"/>
 <tile id="0">
  <animation>
   <frame tileid="0" duration="150"/>
   <frame tileid="1" duration="150"/>
   <frame tileid="2" duration="150"/>
   <frame tileid="3" duration="150"/>
   <frame tileid="4" duration="150"/>
  </animation>
 </tile>
</tileset>
