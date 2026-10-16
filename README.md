# Espectrofotómetro Casero — app móvil

App en Python (Kivy) para analizar las fotos del espectrofotómetro casero
directamente desde el celular: calcula transmitancia T(λ) y absorbancia A(λ)
comparando una foto del blanco contra una foto de la muestra.

## Probarla en tu computador (sin Android)

```bash
pip install -r requirements.txt
python main.py
```

## Conseguir el .apk para tu celular (sin instalar Android Studio)

Este repositorio ya trae un flujo de GitHub Actions (`.github/workflows/build.yml`)
que compila el APK automáticamente en la nube cada vez que subes cambios a
la rama `main`. Pasos:

1. Ve a la pestaña **Actions** del repositorio → espera a que termine el
   flujo "Build APK" (puede tardar 15–30 minutos la primera vez).
2. Entra al resultado (run) terminado → en "Artifacts" descarga
   `espectrofotometro-apk`.
3. Pasa el .apk a tu celular e instálalo (puede que tengas que habilitar
   "Instalar apps de orígenes desconocidos" en los ajustes de Android).

## Estructura

- `main.py` — toda la app (interfaz + la misma lógica de análisis de
  `analizar_espectro.py`).
- `buildozer.spec` — configuración para compilar a Android.
- `.github/workflows/build.yml` — compila el .apk automáticamente en GitHub.
- `privacy_policy.md` — política de privacidad exigida por Google Play.
- `ficha_play_store.md` — textos listos para la ficha de la tienda.
