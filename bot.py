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
    2. No repitas la misma información en varios ítems.
    3. Desglosa los precios claramente (Ida + Regreso = Total).

    Genera el reporte para Telegram en formato Markdown con la siguiente estructura exacta:

    🚨 **REPORTE PERSONALIZADO DE VUELOS** 🚨
    📌 **Ruta:** {ORIGEN} ➔ {DESTINO}
    📅 **Mejor fecha encontrada:** (Ej: 10 de Octubre al 14 de Octubre de 2026 - {DURACION_DIAS} días)

    1. 🛫 **VUELO DE IDA (Mejor tarifa y horario):**
       - **Aerolínea:** (Ej. Avianca / Wingo / LATAM)
       - **Horario:** (Ej. Mañana - 08:00 AM)
       - **Precio trayecto ida:** $XX.XXX COP

    2. 🛬 **VUELO DE REGRESO (Mejor tarifa y horario):**
       - **Aerolínea:** (Ej. Avianca / Wingo / LATAM)
       - **Horario:** (Ej. Tarde - 02:00 PM)
       - **Precio trayecto regreso:** $XX.XXX COP

    3. 💰 **PRECIO TOTAL ESTIMADO (Ida y Vuelta por persona):**
       - **$XX.XXX COP** (Suma exacta de ida + regreso)

    4. 🔗 **Enlaces para comprar / consultar:**
       - Agrega enlaces funcionales [Texto](URL) encontrados en la búsqueda.

    5. 💡 **Recomendación rápida:**
       - Breve nota (máximo 2 líneas) sobre si el precio es una oferta o si vale la pena esperar.

    Mantén el mensaje 100% claro, ordenado y sin contradicciones en las tarifas.
    """

    modelos = ['gemini-3.5-flash', 'gemini-2.5-flash', 'gemini-1.5-flash']
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
