from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import os

app = Flask(__name__)

conversaciones = {}

SERVICIOS = [
    {"nombre": "Corte completo", "precio": 25000},
    {"nombre": "Corte con barba", "precio": 30000},
]
BARBEROS = 2
HORA_APERTURA = 9
HORA_CIERRE = 20
ALMUERZO_INICIO = 12
ALMUERZO_FIN = 14

citas = []


def formato_precio(precio):
    return f"${precio:,}".replace(",", ".")


def hora_disponible(hora):
    if hora < HORA_APERTURA or hora >= HORA_CIERRE:
        return False
    if ALMUERZO_INICIO <= hora < ALMUERZO_FIN:
        return False
    ocupadas = sum(1 for c in citas if c["hora"] == hora)
    return ocupadas < BARBEROS


def horarios_disponibles():
    slots = []
    for h in range(HORA_APERTURA, HORA_CIERRE):
        if hora_disponible(h):
            slots.append(h)
    return slots[:6]


def formato_hora(h):
    if h == 12:
        return "12:00 pm"
    elif h > 12:
        return f"{h-12}:00 pm"
    else:
        return f"{h}:00 am"


def procesar_mensaje(numero, mensaje):
    msg = mensaje.strip().lower()

    if numero not in conversaciones:
        conversaciones[numero] = {"estado": "idle", "datos": {}}

    conv = conversaciones[numero]
    estado = conv["estado"]
    datos = conv["datos"]

    if estado == "idle":
        if any(p in msg for p in ["servicio", "precio", "cuanto", "cuánto", "ofrecen", "tienen"]):
            return (
                "En Barbería La Gloria ofrecemos:\n\n"
                f"✂ Corte completo — ${25000:,}\n"
                f"✂ Corte con barba — ${30000:,}\n\n"
                "¿Te gustaría agendar una cita? 😊"
            )
        if any(p in msg for p in ["hora", "horario", "atienden", "abren", "cierran"]):
            return (
                "Atendemos de lunes a sábado:\n\n"
                "🕘 9:00 am – 12:00 pm\n"
                "🍽 Almuerzo: 12:00 pm – 2:00 pm\n"
                "🕑 2:00 pm – 8:00 pm\n\n"
                "Contamos con 2 barberos disponibles.\n"
                "¿Quieres agendar una cita?"
            )
        if any(p in msg for p in ["agenda", "cita", "reserva", "turno", "quiero"]):
            conv["estado"] = "pedir_nombre"
            return "¡Con gusto! Para agendar tu cita necesito algunos datos.\n\n¿Cuál es tu nombre?"
        if any(p in msg for p in ["hola", "buenas", "buenos", "hey", "buen"]):
            return (
                "¡Hola! Bienvenido a *Barbería La Gloria* 💈\n\n"
                "Puedo ayudarte con:\n"
                "• Ver servicios y precios\n"
                "• Agendar una cita\n"
                "• Consultar horarios\n\n"
                "¿En qué te puedo ayudar?"
            )
        return (
            "¡Hola! Soy el asistente de *Barbería La Gloria* 💈\n\n"
            "Puedo ayudarte a:\n"
            "• Agendar citas\n"
            "• Ver precios y servicios\n"
            "• Consultar horarios\n\n"
            "¿Qué necesitas?"
        )

    if estado == "pedir_nombre":
        datos["nombre"] = mensaje.strip().title()
        conv["estado"] = "pedir_servicio"
        return (
            f"Perfecto, {datos['nombre']} 👋\n\n"
            "¿Qué servicio deseas?\n\n"
            f"1️⃣ Corte completo — $25.000\n"
            f"2️⃣ Corte con barba — $30.000\n\n"
            "Responde con 1 o 2."
        )

    if estado == "pedir_servicio":
        if msg == "1" or "completo" in msg:
            datos["servicio"] = SERVICIOS[0]
        elif msg == "2" or "barba" in msg:
            datos["servicio"] = SERVICIOS[1]
        else:
            return "Por favor responde con 1 o 2 para elegir el servicio 😊"

        slots = horarios_disponibles()
        datos["slots"] = slots
        conv["estado"] = "pedir_hora"

        lista = "\n".join([f"{i+1}. {formato_hora(h)}" for i, h in enumerate(slots)])
        return (
            f"Excelente, *{datos['servicio']['nombre']}* ✅\n\n"
            f"Horarios disponibles:\n\n{lista}\n\n"
            "Elige el número del horario que prefieres."
        )

    if estado == "pedir_hora":
        try:
            idx = int(msg) - 1
            if idx < 0 or idx >= len(datos["slots"]):
                raise ValueError
        except ValueError:
            return f"Por favor elige un número del 1 al {len(datos['slots'])} 😊"

        hora = datos["slots"][idx]
        citas.append({
            "nombre": datos["nombre"],
            "servicio": datos["servicio"]["nombre"],
            "hora": hora,
            "numero": numero
        })

        nombre = datos["nombre"]
        servicio = datos["servicio"]
        conv["estado"] = "idle"
        conv["datos"] = {}

        return (
            f"✅ *¡Cita confirmada!*\n\n"
            f"👤 {nombre}\n"
            f"✂ {servicio['nombre']}\n"
            f"🕐 {formato_hora(hora)}\n"
            f"💰 ${servicio['precio']:,}\n\n"
            "¡Te esperamos en Barbería La Gloria!\n"
            "Si necesitas cancelar escríbenos aquí 💈"
        )

    return "No entendí tu mensaje. ¿En qué te puedo ayudar? 😊"


@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    numero = request.form.get("From", "")
    mensaje = request.form.get("Body", "")
    respuesta = procesar_mensaje(numero, mensaje)
    twiml = MessagingResponse()
    twiml.message(respuesta)
    return str(twiml)


@app.route("/")
def index():
    return "Agente Barbería La Gloria funcionando ✅"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
