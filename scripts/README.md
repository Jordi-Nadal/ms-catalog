# ms-catalog publisher

## Setup (una vez)

```bash
cd ms-catalog
git init
git remote add origin git@github.com:TU_USER/ms-catalog.git
git checkout -b gh-pages
```

En GitHub: Settings → Pages → Branch: `gh-pages` / root `/`

## Publicar un catálogo

```bash
# desde cualquier JSON o CSV con tus tracks:
python scripts/publish.py --input mis_tracks.json --push

# solo generar sin hacer push:
python scripts/publish.py --input mis_tracks.csv
```

## Schema de entrada

### JSON
```json
[
  {
    "artist": "Larry Heard",
    "title": "Can You Feel It",
    "style": "House",
    "youtube_id": "dQw4w9WgXcY",
    "bpm": 120,
    "key": "8A",
    "energy": 0.62,
    "duration_seconds": 480,
    "year": 1986,
    "label": "Trax Records",
    "tags": ["deep", "classic"]
  }
]
```

### CSV
```
artist,title,style,youtube_id,bpm,key,energy,duration_seconds,year,label,tags
Larry Heard,Can You Feel It,House,dQw4w9WgXcY,120,8A,0.62,480,1986,Trax Records,"deep,classic"
```

Campos obligatorios: `artist`, `title`, `style`  
Campos opcionales: todos los demás

## URL del catálogo en la app

Por defecto la app apunta a:
`https://TU_USER.github.io/ms-catalog`

Cambiar en `src/data.js` → `DEFAULT_CATALOG_URL`
