# Cancionero en GitHub Pages

Este proyecto carga las canciones desde archivos de texto en `songs/`.

## Fuente actual

- `cancioner.txt.txt` es la fuente base.
- `songs/index.json` contiene el indice.
- Cada cancion se guarda como `songs/NNN-titulo.txt`.

## Publicar en GitHub Pages

1. Subi todo el contenido del proyecto a un repo (rama `main`).
2. En GitHub: `Settings` > `Pages`.
3. Elegi `Deploy from a branch`.
4. Selecciona `main` + carpeta `/ (root)`.
5. Espera 1-3 minutos y abre la URL del sitio.

## Nota

Si actualizas `cancioner.txt.txt`, hay que regenerar `songs/`.
