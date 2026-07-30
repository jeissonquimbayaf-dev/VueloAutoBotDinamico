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

    Tu objetivo es analizar ofertas de vuelo con los siguientes parámetros especificados por el usuario:
    - Ruta: {ORIGEN} -> {DESTINO} -> {ORIGEN}
    - Rango de fechas buscado: Entre {FECHA_INICIO} y {FECHA_FIN}
    - Duración del viaje: Aproximadamente {DURACION_DIAS} días.

    Genera un reporte conciso para Telegram en formato Markdown con la siguiente estructura exacta:

    🚨 **REPORTE PERSONALIZADO DE VUELOS** 🚨
    📌 **Ruta:** {ORIGEN} ➔ {DESTINO}

    1. ✈️ **Opción más económica encontrada:**
       - **Fechas sugeridas:** (Específica las fechas exactas o estimadas dentro de la ventana de {FECHA_INICIO} a {FECHA_FIN} para un viaje de {DURACION_DIAS} días)
       - **Horarios:** (Salida y regreso estimados o franja horaria)
       - **Aerolínea y Precio:** (Aerolínea - Precio aprox. en COP)

    2. 📊 **Resumen de tarifas y horarios alternativos:**
    La mejor tarifa y precio y horario del mejor precio del vuelo de ida (con la aerolínea conseguida)
    La mejor tarifa y precio horario del mejor precio del vuelo de regreso (con la aerolínea conseguida)

       
    3. 🔗 **Enlaces para consultar / comprar:**
    4. Un aviso sobre restricciones comunes (tarifas básicas, equipaje no incluido, etc.).
    5. 💡 **Tendencia/Recomendación:**


Mantén un tono conciso, claro, servicial y orientado al ahorro.

    Mantén el mensaje ordenado, fácil de leer y con enlaces funcionales.
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
