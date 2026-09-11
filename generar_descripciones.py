import os
import json
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
        json.dump(data, f, ensure_ascii=False, indent=4)

def normalizar_formato_sencillo(descripciones_ia):
    """
    Convierte cualquier entrada previa con 'fecha_registro' al formato sencillo: "Título": "Texto".
    """
    descripciones_sencillas = {}

    for titulo, contenido in descripciones_ia.items():
        titulo_limpio = titulo.strip()

        # Si viene en el formato con diccionario/fecha, extrae solo el texto de la descripción
        if isinstance(contenido, dict):
            texto = contenido.get("descripcion", "")
            if texto:
                descripciones_sencillas[titulo_limpio] = texto
        elif isinstance(contenido, str) and contenido.strip():
            descripciones_sencillas[titulo_limpio] = contenido.strip()

    return descripciones_sencillas

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
        1. Devuelve ÚNICAMENTE un objeto JSON válido donde la clave sea el título exacto proporcionado y el valor sea la descripción generada en texto plano.
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

    # 1. Convertir automáticamente el contenido existente de descripciones_ia.json a texto sencillo
    descripciones_limpias = normalizar_formato_sencillo(descripciones_actuales)

    # Cargar títulos del borrador
    if isinstance(borrador, dict):
        titulos_borrador = [t.strip() for t in borrador.keys()]
    else:
        titulos_borrador = [t.strip() for t in borrador]

    titulos_unicos_borrador = list(set(titulos_borrador))

    # 2. Filtrar títulos que aún no tienen descripción
    titulos_pendientes = [
        titulo for titulo in titulos_unicos_borrador 
        if titulo not in descripciones_limpias or not descripciones_limpias[titulo]
    ]

    print(f"Títulos únicos en borrador: {len(titulos_unicos_borrador)}")
    print(f"Títulos que ya existen con descripción: {len(titulos_unicos_borrador) - len(titulos_pendientes)}")
    print(f"Títulos NUEVOS a procesar con Gemini: {len(titulos_pendientes)}")

    if titulos_pendientes:
        # 3. Consultar Gemini para los nuevos
        nuevas = obtener_descripciones_gemini(titulos_pendientes)

        for titulo, desc in nuevas.items():
            texto_desc = desc.get("descripcion", desc) if isinstance(desc, dict) else desc
            descripciones_limpias[titulo.strip()] = texto_desc

    # 4. Guardar forzando la estructura plana "Título": "Descripción"
    guardar_json(PATH_DESCRIPCIONES, descripciones_limpias)
    print("Archivo descripciones_ia.json actualizado al formato sencillo correctamente.")

if __name__ == "__main__":
    main()
