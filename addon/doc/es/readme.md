# Native Speech Generation para NVDA

**Autor:** Muhammad Gagah [muha.aku@gmail.com](mailto:muha.aku@gmail.com)

Native Speech Generation es un complemento para NVDA que integra **Google Gemini AI** para generar voz de alta calidad y sonido natural directamente en NVDA. Proporciona una interfaz limpia y totalmente accesible para convertir texto en audio, admitiendo tanto **narración de un solo hablante** como **diálogos dinámicos de varios hablantes**.

Este complemento está diseñado para flujos de trabajo fluidos, interacción centrada en la accesibilidad y un control de voz flexible adecuado para narración, diálogos y producción de contenido de audio.

---

## Características

### Generación de voz de alta calidad
* **Elija entre:**
    * **Gemini Flash:** Calidad estándar, generación rápida, baja latencia.
    * **Gemini Pro:** Premium, voces más realistas (modelo de pago).

### Modos de hablante único y múltiple
* **Narración de hablante único** para conversión de texto a voz estándar.
* **Modo multihablante (2 hablantes)** para diálogos con voces distintas.

### Control de voz avanzado
* **Asignación de nombres a los hablantes:** Asigne nombres personalizados (ej. *Juan*, *María*) en el modo multihablante. La IA asigna automáticamente las voces según los nombres en el guion.
* **Instrucciones de estilo:** Proporcione indicaciones como *"Habla en un tono alegre"* o *"Narra con calma"* para guiar el habla.
* **Control de temperatura:** Ajuste la variación y creatividad de la salida:
    * Valores bajos → voz más estable y predecible.
    * Valores altos → voz más expresiva y variada.

---

## Requisitos
* NVDA (se recomienda la versión más reciente).
* Conexión a internet activa.
* Una **clave de API de Google Gemini** válida.

---

## Instalación
1. Descargue el paquete desde la [página de versiones (Releases)](https://github.com/MuhammadGagah/native-speech-generation/releases).
2. Instálelo como cualquier complemento de NVDA.
3. Reinicie NVDA cuando se le solicite.

---

## Configuración de la clave de API (Requerido)
1. Cree una clave en [Google AI Studio](https://aistudio.google.com/apikey).
2. Vaya a: **Menú NVDA → Herramientas → Native Speech Generation**.
3. Haga clic en **"Configuración de clave API"**.
4. Pegue su clave en el campo **GEMINI API Key**.
5. Haga clic en **Aceptar**.

---

## Cómo usar
Abra el diálogo usando:
* **NVDA+Control+Mayús+G**, o
* **Menú NVDA → Herramientas → Native Speech Generation**

### Elementos de la interfaz
* **Texto a convertir:** Ingrese o pegue su texto.
* **Instrucciones de estilo:** (Opcional) Guía para el tono o emoción.
* **Seleccionar modelo:** Flash o Pro.
* **Modo de hablante:** Único o Multihablante (2).

---

## Generación de voz

### Modo de hablante único
1. Seleccione **Hablante único**.
2. Elija una voz, ingrese el texto y haga clic en **Generar voz**.

### Modo multihablante
1. Seleccione **Multihablante (2)**.
2. Asigne un nombre y voz a cada hablante.
3. Formatee el texto así:
   `Alicia: Hola Roberto, ¿cómo estás?`
   `Roberto: ¡Muy bien! El clima es genial.`

---

## Hablar con IA (Modo en vivo)
1. Haga clic en **Hablar con IA**.
2. **Iniciar conversación:** Comience a hablar por el micrófono.
3. **Conexión con Google Search:** Marque esta casilla para información en tiempo real.

---

## Gestos de entrada
Personalizables en: **Menú NVDA → Preferencias → Gestos de entrada**.
* Predeterminado: **NVDA+Control+Mayús+G**

---

## Contribuciones
* Reporte errores en la sección de **Issues**.
* Envíe mejoras mediante **Pull Requests**.

**Contacto:** [muha.aku@gmail.com](mailto:muha.aku@gmail.com) | [GitHub](https://github.com/MuhammadGagah)