"""
main.py — Espectrofotómetro Casero (app móvil)
=================================================

App en Kivy (Python) para Android que hace lo mismo que el script
`analizar_espectro.py`, pero con una pantalla táctil en vez de la terminal:

    1. Eliges la foto del "blanco" y la foto de la "muestra".
    2. Escribes tu calibración (puntos conocidos, o los datos geométricos
       del CD si no tienes lámpara de referencia — ver la guía del montaje).
    3. Tocas "Analizar" y la app calcula la transmitancia T(λ) y la
       absorbancia A(λ), muestra la gráfica en pantalla y guarda los
       resultados (imagen + CSV) en el almacenamiento de la app.

Nota para quien está aprendiendo Python: casi toda la lógica de cálculo
(cargar_imagen, extraer_perfil, construir_calibracion,
construir_calibracion_geometrica) es la MISMA que ya conoces de
analizar_espectro.py — aquí solo cambia la "cara" (la interfaz), no las
matemáticas. Compáralos: verás que son prácticamente idénticos.

Cómo probarla en tu computador (antes de compilarla para Android):
    pip install kivy pillow numpy matplotlib plyer
    python main.py

Cómo conseguir el .apk para tu celular: ver GUIA_PUBLICAR_EN_PLAYSTORE.md
(usa un pipeline gratuito de GitHub Actions — no necesitas instalar
Android Studio ni el SDK de Android en tu computador).
"""

import os
import traceback
from pathlib import Path

import numpy as np
from PIL import Image as PILImage

import matplotlib
matplotlib.use("Agg")  # genera la gráfica como archivo, sin necesitar pantalla propia
import matplotlib.pyplot as plt

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image as KivyImage
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.metrics import dp

try:
    from plyer import filechooser
except Exception:  # plyer puede no estar disponible al probar en algunos entornos
    filechooser = None


# ---------------------------------------------------------------------------
# 1. Lógica de análisis — idéntica en espíritu a analizar_espectro.py
# ---------------------------------------------------------------------------

def cargar_imagen(ruta):
    img = PILImage.open(ruta).convert("RGB")
    return np.array(img)


def extraer_perfil(imagen_rgb, fila_inicio=None, fila_fin=None):
    alto, ancho, _ = imagen_rgb.shape
    if fila_inicio is None or fila_fin is None:
        fila_inicio = int(alto * 0.40)
        fila_fin = int(alto * 0.60)
    franja = imagen_rgb[fila_inicio:fila_fin, :, :].astype(np.float64)
    luminancia = 0.299 * franja[:, :, 0] + 0.587 * franja[:, :, 1] + 0.114 * franja[:, :, 2]
    return luminancia.mean(axis=0)


def construir_calibracion(puntos):
    """puntos: lista de (pixel, nm). Devuelve una función pixel -> nm."""
    if len(puntos) < 2:
        raise ValueError("Se necesitan al menos 2 puntos de calibración (pixel:nm).")
    pixeles = np.array([p[0] for p in puntos], dtype=np.float64)
    nm = np.array([p[1] for p in puntos], dtype=np.float64)
    grado = 1 if len(puntos) == 2 else 2
    coeficientes = np.polyfit(pixeles, nm, grado)
    return np.poly1d(coeficientes)


def parsear_calibracion(texto):
    """'180:436 410:546 460:577' -> [(180.0, 436.0), (410.0, 546.0), (460.0, 577.0)]"""
    puntos = []
    for token in texto.split():
        try:
            px_str, nm_str = token.split(":")
            puntos.append((float(px_str), float(nm_str)))
        except ValueError:
            raise ValueError(
                f"Formato inválido: '{token}'. Usa pixel:nm, por ejemplo 180:436, "
                "separando varios puntos con espacios."
            )
    return puntos


def construir_calibracion_geometrica(pixel_cero, mm_por_pixel, distancia_cm,
                                      paso_rejilla_nm=1600.0, orden=1):
    distancia_mm = distancia_cm * 10.0

    def pixel_a_nm(pixeles):
        pixeles = np.asarray(pixeles, dtype=np.float64)
        x_mm = (pixeles - pixel_cero) * mm_por_pixel
        theta = np.arctan(np.abs(x_mm) / distancia_mm)
        return paso_rejilla_nm * np.sin(theta) / orden

    return pixel_a_nm


def analizar(blanco_path, muestra_path, pixel_a_nm, salida_png, salida_csv):
    """Hace todo el cálculo y guarda la gráfica (PNG) y la tabla (CSV).
    Devuelve (lambda_max, a_max) o (None, None) si no se pudo estimar."""
    blanco_img = cargar_imagen(blanco_path)
    muestra_img = cargar_imagen(muestra_path)

    if blanco_img.shape[1] != muestra_img.shape[1]:
        ancho_comun = min(blanco_img.shape[1], muestra_img.shape[1])
        blanco_img = blanco_img[:, :ancho_comun, :]
        muestra_img = muestra_img[:, :ancho_comun, :]

    perfil_blanco = extraer_perfil(blanco_img)
    perfil_muestra = extraer_perfil(muestra_img)

    pixeles = np.arange(len(perfil_blanco))
    longitudes_onda = pixel_a_nm(pixeles)

    EPSILON = 1.0
    blanco_seguro = np.clip(perfil_blanco, EPSILON, None)
    transmitancia = perfil_muestra / blanco_seguro
    transmitancia = np.clip(transmitancia, 1e-4, 1.5)
    absorbancia = -np.log10(transmitancia)

    zona_valida = perfil_blanco > (perfil_blanco.max() * 0.05)

    lambda_max, a_max = None, None
    if zona_valida.any():
        idx_validos = np.where(zona_valida)[0]
        idx_max = idx_validos[np.argmax(absorbancia[idx_validos])]
        lambda_max = float(longitudes_onda[idx_max])
        a_max = float(absorbancia[idx_max])

    with open(salida_csv, "w") as f:
        f.write("longitud_onda_nm,transmitancia,absorbancia\n")
        for lam, t, a in zip(longitudes_onda, transmitancia, absorbancia):
            f.write(f"{lam:.2f},{t:.4f},{a:.4f}\n")

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(6, 7), dpi=130, sharex=True)
    ax1.plot(longitudes_onda, perfil_blanco, color="#888888", lw=1.2, label="Blanco")
    ax1.plot(longitudes_onda, perfil_muestra, color="#1b3a63", lw=1.2, label="Muestra")
    ax1.set_ylabel("Intensidad")
    ax1.legend(fontsize=8)
    ax1.grid(alpha=0.25)

    ax2.plot(longitudes_onda, transmitancia * 100, color="#2f6fb3", lw=1.2)
    ax2.set_ylabel("T (%)")
    ax2.grid(alpha=0.25)

    ax3.plot(longitudes_onda, absorbancia, color="#b33a2f", lw=1.2)
    if lambda_max is not None:
        ax3.axvline(lambda_max, color="#333333", ls="--", lw=1)
        ax3.annotate(f"λmáx≈{lambda_max:.0f}nm", (lambda_max, a_max),
                     textcoords="offset points", xytext=(6, 0), fontsize=8)
    ax3.set_ylabel("A")
    ax3.set_xlabel("Longitud de onda (nm)")
    ax3.grid(alpha=0.25)

    fig.tight_layout()
    fig.savefig(salida_png)
    plt.close(fig)

    return lambda_max, a_max


# ---------------------------------------------------------------------------
# 2. Interfaz (Kivy)
# ---------------------------------------------------------------------------

def mostrar_error(titulo, mensaje):
    popup = Popup(title=titulo,
                   content=Label(text=mensaje, text_size=(dp(280), None)),
                   size_hint=(0.85, 0.5))
    popup.open()


class PantallaPrincipal(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=dp(12), spacing=dp(8), **kwargs)

        self.blanco_path = None
        self.muestra_path = None

        scroll = ScrollView()
        contenido = BoxLayout(orientation="vertical", spacing=dp(10), size_hint_y=None)
        contenido.bind(minimum_height=contenido.setter("height"))

        contenido.add_widget(Label(text="[b]Espectrofotómetro casero[/b]", markup=True,
                                    font_size=dp(20), size_hint_y=None, height=dp(34)))

        # --- Sección 1: fotos ---
        contenido.add_widget(Label(text="1. Fotos", bold=True, size_hint_y=None, height=dp(26),
                                    halign="left"))
        self.btn_blanco = Button(text="Elegir foto del blanco...", size_hint_y=None, height=dp(44))
        self.btn_blanco.bind(on_release=self.elegir_blanco)
        contenido.add_widget(self.btn_blanco)
        self.lbl_blanco = Label(text="(sin elegir)", size_hint_y=None, height=dp(22))
        contenido.add_widget(self.lbl_blanco)

        self.btn_muestra = Button(text="Elegir foto de la muestra...", size_hint_y=None, height=dp(44))
        self.btn_muestra.bind(on_release=self.elegir_muestra)
        contenido.add_widget(self.btn_muestra)
        self.lbl_muestra = Label(text="(sin elegir)", size_hint_y=None, height=dp(22))
        contenido.add_widget(self.lbl_muestra)

        # --- Sección 2: calibración ---
        contenido.add_widget(Label(text="2. Calibración (llena SOLO una de las dos opciones)",
                                    bold=True, size_hint_y=None, height=dp(26)))

        contenido.add_widget(Label(text="Opción A — Puntos conocidos (pixel:nm, separados por espacio):",
                                    size_hint_y=None, height=dp(40), text_size=(dp(300), None)))
        self.input_puntos = TextInput(hint_text="ej: 180:436 410:546 460:577",
                                       multiline=False, size_hint_y=None, height=dp(44))
        contenido.add_widget(self.input_puntos)

        contenido.add_widget(Label(text="Opción B — Geometría del CD (sin lámpara):",
                                    size_hint_y=None, height=dp(26)))
        grid_geom = GridLayout(cols=2, size_hint_y=None, height=dp(44 * 3), spacing=dp(4))
        grid_geom.add_widget(Label(text="Píxel del orden cero:"))
        self.input_px0 = TextInput(multiline=False)
        grid_geom.add_widget(self.input_px0)
        grid_geom.add_widget(Label(text="mm por píxel:"))
        self.input_mmpx = TextInput(multiline=False)
        grid_geom.add_widget(self.input_mmpx)
        grid_geom.add_widget(Label(text="Distancia CD-cámara (cm):"))
        self.input_dist = TextInput(multiline=False)
        grid_geom.add_widget(self.input_dist)
        contenido.add_widget(grid_geom)

        # --- Botón analizar ---
        self.btn_analizar = Button(text="Analizar espectro", size_hint_y=None, height=dp(52),
                                    background_color=(0.11, 0.23, 0.39, 1))
        self.btn_analizar.bind(on_release=self.analizar_espectro)
        contenido.add_widget(self.btn_analizar)

        self.lbl_resultado = Label(text="", size_hint_y=None, height=dp(50), text_size=(dp(300), None))
        contenido.add_widget(self.lbl_resultado)

        self.img_resultado = KivyImage(size_hint_y=None, height=dp(420))
        contenido.add_widget(self.img_resultado)

        scroll.add_widget(contenido)
        self.add_widget(scroll)

    # -- selección de archivos --
    def elegir_blanco(self, instance):
        self._elegir_foto(self._set_blanco)

    def elegir_muestra(self, instance):
        self._elegir_foto(self._set_muestra)

    def _elegir_foto(self, callback):
        if filechooser is None:
            mostrar_error("Error", "El selector de archivos (plyer) no está disponible.")
            return
        filechooser.open_file(on_selection=lambda sel: Clock.schedule_once(lambda dt: callback(sel)))

    def _set_blanco(self, seleccion):
        if seleccion:
            self.blanco_path = seleccion[0]
            self.lbl_blanco.text = os.path.basename(self.blanco_path)

    def _set_muestra(self, seleccion):
        if seleccion:
            self.muestra_path = seleccion[0]
            self.lbl_muestra.text = os.path.basename(self.muestra_path)

    # -- calibración --
    def _construir_calibracion(self):
        texto_puntos = self.input_puntos.text.strip()
        if texto_puntos:
            puntos = parsear_calibracion(texto_puntos)
            return construir_calibracion(puntos)

        px0, mmpx, dist = self.input_px0.text.strip(), self.input_mmpx.text.strip(), self.input_dist.text.strip()
        if px0 and mmpx and dist:
            try:
                return construir_calibracion_geometrica(float(px0), float(mmpx), float(dist))
            except ValueError:
                raise ValueError("Los 3 datos de geometría deben ser números.")

        raise ValueError(
            "Llena la Opción A (puntos pixel:nm) o la Opción B (los 3 datos de geometría)."
        )

    # -- analizar --
    def analizar_espectro(self, instance):
        try:
            if not self.blanco_path or not self.muestra_path:
                raise ValueError("Primero elige la foto del blanco y la de la muestra.")

            pixel_a_nm = self._construir_calibracion()

            carpeta = App.get_running_app().user_data_dir
            salida_png = str(Path(carpeta) / "resultado_espectro.png")
            salida_csv = str(Path(carpeta) / "resultado_espectro.csv")

            lambda_max, a_max = analizar(self.blanco_path, self.muestra_path, pixel_a_nm,
                                          salida_png, salida_csv)

            if lambda_max is not None:
                self.lbl_resultado.text = (
                    f"λmáx ≈ {lambda_max:.1f} nm   |   A en λmáx ≈ {a_max:.3f}\n"
                    f"Guardado en: {carpeta}"
                )
            else:
                self.lbl_resultado.text = f"No se pudo estimar λmáx. Guardado en: {carpeta}"

            self.img_resultado.source = salida_png
            self.img_resultado.reload()

        except Exception as e:
            traceback.print_exc()
            mostrar_error("No se pudo analizar", str(e))


class EspectrofotometroApp(App):
    def build(self):
        self.title = "Espectrofotómetro casero"
        return PantallaPrincipal()


if __name__ == "__main__":
    EspectrofotometroApp().run()
