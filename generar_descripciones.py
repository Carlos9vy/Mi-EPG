import os
import json
from datetime import datetime, timedelta
from google import genai

# Cliente de Gemini mediante la API Key de GitHub Secrets
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

PATH_BORRADOR = "borrador_titulos.json"
PATH_DESCRIPCIONES = "descripciones_ia.json"

def cargar_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def guardar_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        # json.dump elimina cualquier duplicado de clave automáticamente al guardar
        json.dump(data, f, ensure_ascii=False, indent=4)

def limpiar_historial_antiguo(descripciones_ia):
    """
    Conserva únicamente las entradas guardadas dentro de los últimos 7 días.
    Y normaliza la estructura del diccionario.
    """
    limite_fecha = datetime.now() - timedelta(days=7)
    descripciones_limpias = {}

    for titulo, contenido in descripciones_ia.items():
        # Elimina espacios extras al inicio/final para evitar falsos duplicados
        titulo_limpio = titulo.strip()

        if isinstance(contenido, dict) and "fecha_registro" in contenido:
            try:
                fecha_item = datetime.strptime(contenido["fecha_registro"], "%Y-%m-%d")
                if fecha_item >= limite_fecha:
                    descripciones_limpias[titulo_limpio] = contenido
            except ValueError:
                descripciones_limpias[titulo_limpio] = contenido
        else:
            # Soporte de retrocompatibilidad para textos planos
            descripciones_limpias[titulo_limpio] = contenido

    return descripciones_limpias

def obtener_descripciones_gemini(titulos_pendientes):
    if not titulos_pendientes:
        return {}

    lote_tamano = 40
    nuevas_descripciones = {}

    for i in range(0, len(titulos_pendientes), lote_tamano):
        lote = titulos_pendientes[i:i + lote_tamano]
        
        prompt = f"""
        Eres un experto en guías de programación de TV (EPG) en español.
        Genera una descripción precisa de 4 a 5 líneas para cada uno de los siguientes títulos de programas o eventos deportivos:
        {json.dumps(lote, ensure_ascii=False)}

        Instrucciones estrictas:
        1. Devuelve ÚNICAMENTE un objeto JSON válido donde la clave sea el título exacto proporcionado y el valor sea la descripción generada.
        2. No incluyas texto introductorio, ni bloques de código markdown antes o después del JSON.
        """

        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )

            texto_respuesta = response.text.strip()
            if texto_respuesta.startswith("```json"):
                texto_respuesta = texto_respuesta[7:-3].strip()
            elif texto_respuesta.startswith("```"):
                texto_respuesta = texto_respuesta[3:-3].strip()

            datos_generados = json.loads(texto_respuesta)
            nuevas_descripciones.update(datos_generados)
        except Exception as e:
            print(f"Error al procesar el lote {i}: {e}")

    return nuevas_descripciones

def main():
    borrador = cargar_json(PATH_BORRADOR)
    descripciones_actuales = cargar_json(PATH_DESCRIPCIONES)

    # 1. Depurar el archivo manteniendo solo los últimos 7 días
    # Esto elimina automáticamente cualquier duplicado que pudiera existir
    descripciones_limpias = limpiar_historial_antiguo(descripciones_actuales)

    # Convertir a lista y limpiar nombres si borrador es dict o list
    if isinstance(borrador, dict):
        titulos_borrador = [t.strip() for t in borrador.keys()]
    else:
        titulos_borrador = [t.strip() for t in borrador]

    # Eliminar duplicados dentro del mismo borrador actual
    titulos_unicos_borrador = list(set(titulos_borrador))

    # 2. VERIFICACIÓN: Filtrar y omitir completamente los títulos que ya existen en descripciones_ia.json
    titulos_pendientes = [
        titulo for titulo in titulos_unicos_borrador 
        if titulo not in descripciones_limpias
    ]

    print(f"Títulos únicos en borrador: {len(titulos_unicos_borrador)}")
    print(f"Títulos que ya existían y se OMITEN: {len(titulos_unicos_borrador) - len(titulos_pendientes)}")
    print(f"Títulos NUEVOS a procesar con Gemini: {len(titulos_pendientes)}")

    if titulos_pendientes:
        # 3. Consultar la API solo para los títulos nuevos
        nuevas = obtener_descripciones_gemini(titulos_pendientes)
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")

        for titulo, desc in nuevas.items():
            descripciones_limpias[titulo.strip()] = {
                "descripcion": desc,
                "fecha_registro": fecha_hoy
            }

    # 4. Guardar archivo consolidado (sin duplicados)
    guardar_json(PATH_DESCRIPCIONES, descripciones_limpias)
    print("Archivo descripciones_ia.json actualizado y depurado correctamente.")

if __name__ == "__main__":
    main()
