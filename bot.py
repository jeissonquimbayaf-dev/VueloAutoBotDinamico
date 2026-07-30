import os
import time
import requests
from google import genai
from googlesearch import search

# 1. Cargar credenciales
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# 2. Configuración dinámica enviada desde GitHub Actions
ORIGEN = os.environ.get("ORIGEN", "Bogotá (BOG)")
DESTINO = os.environ.get("DESTINO", "Santa Marta (SMR)")
FECHA_INICIO = os.environ.get("FECHA_INICIO", "mediados de agosto de 2026")
FECHA_FIN = os.environ.get("FECHA_FIN", "mediados de septiembre de 2026")
DURACION_DIAS = os.environ.get("DURACION_DIAS", "4")

# 3. Inicializar cliente de Gemini
client = genai.Client(api_key=GEMINI_API_KEY)

def buscar_vuelos():
    # Consultas optimizadas para Google Search
    queries = [
        f"vuelos baratos {ORIGEN} a {DESTINO} {FECHA_INICIO} {FECHA_FIN} precios ofertas",
        f"google flights {ORIGEN} {DESTINO} {FECHA_INICIO} {FECHA_FIN}"
    ]
    resultados = []
    
    try:
        for q in queries:
            # googlesearch busca directamente en Google (advanced=True trae título y snippet)
            results = list(search(q, num_results=4, advanced=True, lang="es"))
            for r in results:
                resultados.append(f"- [{r.title}]({r.url}): {r.description}")
    except Exception as e:
        print(f"Error en la búsqueda web con Google: {e}")
        
    return "\n".join(resultados)

def enviar_alerta():
    info_web = buscar_vuelos()

    prompt = f"""
    Basándote en la siguiente información recopilada en tiempo real directamente desde Google Search:
    {info_web}

    Tu objetivo es analizar y estructurar LA MEJOR oferta de vuelo dentro del rango solicitado por el usuario.

    Parámetros de búsqueda:
    - Ruta: {ORIGEN} -> {DESTINO} -> {ORIGEN}
    - Rango de fechas permitido: Entre {FECHA_INICIO} y {FECHA_FIN}
    - Duración del viaje: Aproximadamente {DURACION_DIAS} días.

    REGLAS DE FORMATO ESTRICTAS:
    1. Selecciona la MEJOR FECHA sugerida en el rango.
    2. Coloca enlaces DIRECTOS tomados de los resultados de Google en cada trayecto.
    3. Asegúrate de que las tarifas de ida y regreso coincidan con la suma total.

    Genera el reporte para Telegram en formato Markdown con la siguiente estructura exacta:

    🚨 **REPORTE PERSONALIZADO DE VUELOS (Google Search)** 🚨
    📌 **Ruta:** {ORIGEN} ➔ {DESTINO}
    📅 **Mejor fecha encontrada:** (Ej: 10 de Octubre al 14 de Octubre de 2026 - {DURACION_DIAS} días)

    1. 🛫 **VUELO DE IDA:**
       - **Aerolínea y Horario:** (Ej. Avianca / 08:00 AM)
       - **Precio trayecto ida:** $XX.XXX COP
       - 🔗 **Oferta / Fuente Ida:** [Ver tarifa de ida en la fuente](URL_EXACTA_DE_GOOGLE)

    2. 🛬 **VUELO DE REGRESO:**
       - **Aerolínea y Horario:** (Ej. Avianca / 02:00 PM)
       - **Precio trayecto regreso:** $XX.XXX COP
       - 🔗 **Oferta / Fuente Regreso:** [Ver tarifa de regreso en la fuente](URL_EXACTA_DE_GOOGLE)

    3. 💰 **PRECIO TOTAL ESTIMADO:**
       - **$XX.XXX COP** (Suma exacta de ida + regreso)

    4. 🔍 **BÚSQUEDA DIRECTA EN GOOGLE FLIGHTS:**
       - 🔗 [Abrir matriz completa en Google Flights](https://www.google.com/travel/flights)

    5. 💡 **Recomendación rápida:**
       - Breve análisis de la tarifa encontrada.

    Mantén el mensaje 100% claro, preciso y estructurado.
    """

    modelos = ['gemini-3.5-flash-lite', 'gemini-3.5-flash']
    max_intentos = 3

    for modelo in modelos:
        print(f"Intentando generar respuesta con modelo: {modelo}")
        for intento in range(max_intentos):
            try:
                response = client.models.generate_content(
                    model=modelo,
                    contents=prompt
                )
                mensaje = response.text

                url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
                payload = {
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": mensaje,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": False
                }
                r = requests.post(url, json=payload)
                r.raise_for_status()
                print("Mensaje enviado con éxito a Telegram.")
                return

            except Exception as e:
                err_msg = str(e)
                print(f"Intento {intento + 1} con {modelo} falló: {err_msg}")
                if ("503" in err_msg or "429" in err_msg) and intento < max_intentos - 1:
                    time.sleep(15)
                else:
                    break

    raise Exception("No se pudo completar la solicitud.")

if __name__ == "__main__":
    enviar_alerta()
