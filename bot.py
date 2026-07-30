import os
import time
import requests
from google import genai
from ddgs import DDGS

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
    queries = [
        f"vuelos {ORIGEN} a {DESTINO} ofertas {FECHA_INICIO} {FECHA_FIN} horarios",
        f"google flights {ORIGEN} {DESTINO} {FECHA_INICIO} {FECHA_FIN}"
    ]
    resultados = []
    try:
        with DDGS() as ddgs:
            for q in queries:
                results = list(ddgs.text(q, max_results=4))
                for r in results:
                    resultados.append(f"- [{r['title']}]({r['href']}): {r['body']}")
    except Exception as e:
        print(f"Error en la búsqueda web: {e}")
    return "\n".join(resultados)

def enviar_alerta():
    info_web = buscar_vuelos()

    prompt = f"""
  Basándote en la siguiente información recopilada en tiempo real:
    {info_web}

    Tu objetivo es encontrar LA MEJOR combinación de fechas dentro del rango solicitado por el usuario.

    Parámetros de búsqueda:
    - Ruta: {ORIGEN} -> {DESTINO} -> {ORIGEN}
    - Rango de fechas permitido: Entre {FECHA_INICIO} y {FECHA_FIN}
    - Duración del viaje: Aproximadamente {DURACION_DIAS} días.

    REGLAS DE FORMATO ESTRICTAS:
    1. Selecciona la MEJOR FECHA recomendada dentro del rango.
    2. En los enlaces, NO uses textos genéricos como "haz clic aquí". Usa las URLs EXACTAS tomadas de la información recibida (`info_web`) donde se mencione cada oferta o aerolínea.
    3. Si la búsqueda no te da un link directo por trayecto, incluye el enlace de la fuente donde leíste esa tarifa.

    Genera el reporte para Telegram en formato Markdown con la siguiente estructura exacta:

    🚨 **REPORTE PERSONALIZADO DE VUELOS** 🚨
    📌 **Ruta:** {ORIGEN} ➔ {DESTINO}
    📅 **Mejor fecha encontrada:** (Ej: 10 de Octubre al 14 de Octubre de 2026 - {DURACION_DIAS} días)

    1. 🛫 **VUELO DE IDA:**
       - **Aerolínea y Horario:** (Ej. Avianca / 08:00 AM)
       - **Precio trayecto ida:** $XX.XXX COP
       - 🔗 **Link fuente / consulta ida:** [Ver oferta / disponibilidad de ida](URL_ENCONTRADA_O_FUENTE)

    2. 🛬 **VUELO DE REGRESO:**
       - **Aerolínea y Horario:** (Ej. Avianca / 02:00 PM)
       - **Precio trayecto regreso:** $XX.XXX COP
       - 🔗 **Link fuente / consulta regreso:** [Ver oferta / disponibilidad de regreso](URL_ENCONTRADA_O_FUENTE)

    3. 💰 **PRECIO TOTAL ESTIMADO:**
       - **$XX.XXX COP** (Suma exacta de ida + regreso)

    4. 🔍 **BÚSQUEDA DIRECTA EN GOOGLE FLIGHTS:**
       - 🔗 [Abrir matriz completa de vuelos para esta ruta en Google Flights](https://www.google.com/travel/flights)

    5. 💡 **Recomendación rápida:**
       - Breve nota sobre la tarifa encontrada.

    Mantén el mensaje 100% claro y ordenado.
    """

    max_intentos = 3
    for intento in range(max_intentos):
        try:
            response = client.models.generate_content(
                model='gemini-3.5-flash-lite',
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
            break

        except Exception as e:
            print(f"Intento {intento + 1} falló con error: {e}")
            if "429" in str(e) and intento < max_intentos - 1:
                time.sleep(20)
            else:
                raise e

if __name__ == "__main__":
    enviar_alerta()
