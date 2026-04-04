# Native Speech Generation para NVDA

**Autor:** Muhammad Gagah [muha.aku@gmail.com](mailto:muha.aku@gmail.com)

Native Speech Generation es un complemento para NVDA que integra **Google Gemini AI** para generar voz natural y de alta calidad directamente desde NVDA.
Ofrece una interfaz limpia y totalmente accesible para convertir texto en audio, con soporte tanto para **narración de un solo hablante** como para **diálogos dinámicos con varios hablantes**.

Este complemento está pensado para ofrecer un flujo de trabajo fluido, una interacción centrada en la accesibilidad y un control flexible de la voz, ideal para narración, diálogos y producción de contenido de audio.

---

## Características

### Generación de voz de alta calidad

* Elige entre:
  * **Gemini Flash**: calidad estándar, generación rápida y baja latencia.
  * **Gemini Pro**: calidad premium y voces más realistas (modelo de pago).

### Modos de hablante único y múltiple

* **Narración de un solo hablante** para conversión de texto a voz estándar.
* **Modo multihablante (2 hablantes)** para diálogos con voces diferenciadas.

### Control de voz avanzado

* **Nombres de los hablantes**
  Asigna nombres personalizados (por ejemplo, *Juan* o *María*) en el modo multihablante.
  La IA asigna las voces automáticamente según los nombres usados en el guion.
* **Instrucciones de estilo**
  Puedes dar indicaciones como *"Habla con un tono alegre"* o *"Narra con calma"* para orientar la interpretación.
* **Control de temperatura**
  Ajusta la variación y la creatividad del resultado:
  * Valores más bajos -> voz más estable y predecible.
  * Valores más altos -> voz más expresiva y variada.

### Interfaz accesible y clara

* Totalmente accesible con lectores de pantalla.
* Las opciones avanzadas están dentro de un panel desplegable para que el diálogo principal se mantenga simple y enfocado.

### Flujo de trabajo fluido

* El audio se reproduce automáticamente después de la generación.
* El audio generado puede reproducirse de nuevo o guardarse como archivo `.wav` de alta calidad.
* Está diseñado para reducir al mínimo la fricción durante la generación y la reproducción repetidas.

### Carga inteligente de voces y caché

* Las voces disponibles se obtienen dinámicamente desde la API de Gemini.
* Los datos de voz se almacenan en caché durante **24 horas** para reducir llamadas a la API y acelerar el inicio.

### Hablar con IA (conversación en vivo)

* **Chat de voz en tiempo real**: mantén una conversación hablada natural y de baja latencia con Gemini.
* **Grounding con Google Search**: permite que la IA acceda a información en tiempo real desde la web durante la conversación.
* **Interrumpible**: puedes interrumpir a la IA en cualquier momento hablando o pulsando "Detener conversación".
* **Personalizable**: usa la voz y las instrucciones de estilo que hayas seleccionado.
* **Control del nivel de razonamiento**: elige entre `Sin razonamiento`, `Bajo`, `Medio` o `Alto` según la profundidad de razonamiento que necesites.
* **Continuidad tras la reconexión**: el contexto reciente de la conversación se restaura automáticamente después de reconectar, sin necesidad de un interruptor de memoria independiente.
* **Streaming más estable**: reconexión mejorada (backoff + retry) y búfer de audio adaptativo para mayor resistencia en redes inestables.

---

## Requisitos

* NVDA (se recomienda la versión más reciente).
* Conexión activa a Internet.
* Una **clave de API de Google Gemini** válida.

---

## Instalación

1. Descarga el paquete más reciente del complemento desde la
   **página de versiones:**
   [https://github.com/MuhammadGagah/native-speech-generation/releases](https://github.com/MuhammadGagah/native-speech-generation/releases)
2. Instálalo como cualquier complemento estándar de NVDA.
3. Reinicia NVDA cuando se te solicite.

---

## Configuración de la clave de API (obligatoria)

1. Crea una clave de API en **Google AI Studio**:
   [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Abre NVDA y ve a:
   **Menú de NVDA -> Herramientas -> Native Speech Generation**
3. Haz clic en **"Configuración de la clave API"**.
4. Esto abre la configuración de NVDA directamente en la categoría *Native Speech Generation*.
5. Pega tu **clave de API de Gemini** en el campo *GEMINI API Key*.
6. Haz clic en **Aceptar** para guardar.

Las claves guardadas se almacenan de forma segura mediante **Windows DPAPI**, por lo que el valor cifrado no puede descifrarse en otro equipo con Windows ni en otra cuenta de usuario.

Para entornos avanzados o gestionados, también puedes proporcionar la clave mediante la variable de entorno **`GEMINI_API_KEY`**. El complemento la usará automáticamente cuando no haya una clave guardada disponible.

---

## Cómo usar

Abre el diálogo usando:

* **NVDA+Control+Shift+G**, o
* **Menú de NVDA -> Herramientas -> Native Speech Generation**

### Elementos principales de la interfaz

* **Texto a convertir**
  Escribe o pega el texto que quieras convertir en voz.
* **Instrucciones de estilo (opcional)**
  Añade indicaciones sobre tono, emoción o forma de hablar.
* **Seleccionar modelo**
  * Flash (calidad estándar)
  * Pro (alta calidad)
* **Modo de hablante**
  * Un solo hablante
  * Multihablante (2)

---

## Generación de voz

### Modo de hablante único

1. Selecciona **Un solo hablante**.
2. Elige una voz en la lista *Seleccionar voz*.
3. Introduce tu texto.
4. Añade instrucciones de estilo si lo deseas.
5. Haz clic en **Generar voz**.
6. El audio se reproducirá automáticamente cuando termine la generación.

---

### Modo multihablante

1. Selecciona **Multihablante (2)**.
2. Para cada hablante:
   * Introduce un **nombre de hablante** único.
   * Elige una **voz** distinta.
3. Da formato al texto para que cada línea comience con el nombre del hablante seguido de dos puntos.

**Ejemplo:**

```
Alicia: Hola, Bob. ¿Cómo estás hoy?
Bob: ¡Muy bien, Alicia! Hace un tiempo fantástico.
```

4. Haz clic en **Generar voz**.
   Las voces se asignarán automáticamente según los nombres de los hablantes.

---

## Hablar con IA (modo en vivo)

Disfruta de una conversación de voz bidireccional y natural con Gemini.

1. Configura la **Voz** y las **Instrucciones de estilo** que quieras en el diálogo principal.
   *(Nota: Hablar con IA actualmente solo admite el modo de un solo hablante).*
2. Haz clic en **Hablar con IA**.
3. En la nueva ventana:
   * **Iniciar conversación**: inicia la sesión. Habla por tu micrófono.
   * **Detener conversación**: finaliza la sesión.
   * **Grounding con Google Search**: marca esta casilla para permitir que Gemini busque respuestas en la web (por ejemplo, noticias o el clima actual).
     * *Nota: esta casilla se oculta mientras la conversación está activa. Detén la conversación para cambiarla.*
   * **Nivel de razonamiento**: elige entre `Sin razonamiento`, `Bajo`, `Medio` o `Alto`.
   * **Micrófono**: silencia o activa tu micrófono.
   * **Volumen**: ajusta el volumen de reproducción de la IA.

---

## Configuración avanzada

* Activa **Configuración avanzada (temperatura)** para mostrar el control deslizante.
* **Rango de temperatura**:
  * `0.0` -> resultado más determinista y estable.
  * `1.0` -> equilibrio predeterminado.
  * `2.0` -> resultado más creativo y variado.

---

## Resumen de botones

* **Generar voz** - Inicia la generación de voz.
* **Reproducir** - Vuelve a reproducir el último audio generado.
* **Hablar con IA** - Abre la interfaz de conversación de voz en tiempo real.
* **Guardar audio** - Guarda el último audio como archivo `.wav`.
* **Configuración de la clave API** - Abre la configuración del complemento en los ajustes de NVDA.
* **Ver voces en AI Studio** - Abre Google AI Studio en el navegador.
* **Cerrar** - Cierra el diálogo (o pulsa `Escape`).

---

## Gestos de entrada

Personalizable desde:
**Menú de NVDA -> Preferencias -> Gestos de entrada -> Native Speech Generation**

Gesto predeterminado:

* **NVDA+Control+Shift+G** - Abrir el diálogo de Native Speech Generation.

---

## Guía de desarrollo y contribución

Si quieres desarrollar o modificar este complemento, sigue los pasos siguientes.

### Configuración del entorno

* **Python de 32 bits (se recomienda 3.11.9)**
  [https://www.python.org/downloads/release/python-3119/](https://www.python.org/downloads/release/python-3119/)
* **SCons 4.9.1 o superior**

  ```
  pip install scons
  ```
* **Herramientas GNU Gettext** (opcional, recomendado para localización)
  * Normalmente vienen preinstaladas en Linux/Cygwin.
  * Windows: [https://gnuwin32.sourceforge.net/downlinks/gettext.php](https://gnuwin32.sourceforge.net/downlinks/gettext.php)
* **Markdown 3.8+** (para conversión de documentación)

  ```
  pip install markdown
  ```

### Dependencias adicionales

Instala las dependencias de audio de Talk With AI directamente en la ruta de bibliotecas del complemento:

```
python.exe -m pip install google-genai pyaudio --target "D:/myAdd-on/Native-Speech-Generation/addon/globalPlugins/NativeSpeechGeneration/lib"
```

Ajusta la ruta según tu directorio local del código fuente del complemento.

Para la implementación actual de Talk With AI basada solo en audio, no necesitas `opencv-python`, `pillow` ni `mss`.

Después, copia lo siguiente desde tu instalación de Python a:

```
addon/globalPlugins/NativeSpeechGeneration/lib
```

* Carpeta `zoneinfo`
* Archivo `secrets.py`

---

## Contribuir

Las contribuciones, sugerencias y reportes de errores son muy bienvenidos.

* Abre un **Issue** para reportar errores o solicitar funciones.
* Envía un **Pull Request** para contribuir con código.

**Contacto**

* Email: `muha.aku@gmail.com`
* GitHub: [https://github.com/MuhammadGagah](https://github.com/MuhammadGagah)
