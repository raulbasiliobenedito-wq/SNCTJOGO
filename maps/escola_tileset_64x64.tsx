<?xml version="1.0" encoding="UTF-8"?>
<!-- 256x480 com tiles de 32x32 = 8 colunas x 15 linhas = 120 tiles.
     tilecount="480" (sobra da época em que os tiles eram 64x64) fazia este
     tileset declarar os GIDs 1..480, invadindo as faixas de fase3_pesquisa
     (121-280), aderecos_vila (281-292) e chao_vila (293-308) em
     fase1_escola.tmx. Não quebrava por acidente (TiledMap._tileset_for_gid
     itera reversed()), mas qualquer tileset novo importado depois cairia em
     309-480, seria resolvido pra este atlas de 120 tiles e estouraria em
     subsurface(). Ver também a trava em TiledMap._load_tileset. -->
<tileset version="1.10" tiledversion="1.12.2" name="escola_tileset_64x64" tilewidth="32" tileheight="32" tilecount="120" columns="8">
 <image source="escola_tileset_TILED_64x64_FINAL.png" width="256" height="480"/>
</tileset>
