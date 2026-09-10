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
        json.dump(data, f, ensure_ascii=False, indent=4)

def limpiar_historial_antiguo(descripciones_ia):
    """
    Conserva las entradas guardadas en los últimos 7 días y MANTIENE 
    las descripciones de formato antiguo (texto plano) asignándoles la fecha de hoy.
    """
    limite_fecha = datetime.now() - timedelta(days=7)
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    descripciones_limpias = {}

    for titulo, contenido in descripciones_ia.items():
        titulo_limpio = titulo.strip()

        # Si ya tiene la estructura con fecha_registro
        if isinstance(contenido, dict) and "fecha_registro" in contenido:
            try:
                fecha_item = datetime.strptime(contenido["fecha_registro"], "%Y-%m-%d")
                if fecha_item >= limite_fecha:
                    descripciones_limpias[titulo_limpio] = contenido
            except ValueError:
                descripciones_limpias[titulo_limpio] = contenido
        
        # Si es un texto plano (formato anterior) o un diccionario con "descripcion", le asignamos fecha de hoy
        elif isinstance(contenido, str) and contenido.strip():
            descripciones_limpias[titulo_limpio] = {
                "descripcion": contenido,
                "fecha_registro": fecha_hoy
            }
        elif isinstance(contenido, dict) and "descripcion" in contenido:
            descripciones_limpias[titulo_limpio] = {
                "descripcion": contenido["descripcion"],
                "fecha_registro": fecha_hoy
            }

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

    # 1. Depurar el archivo reconociendo el formato antiguo
    descripciones_limpias = limpiar_historial_antiguo(descripciones_actuales)

    # Cargar títulos del borrador
    if isinstance(borrador, dict):
        titulos_borrador = [t.strip() for t in borrador.keys()]
    else:
        titulos_borrador = [t.strip() for t in borrador]

    titulos_unicos_borrador = list(set(titulos_borrador))

    # 2. Filtrar únicamente los títulos que realmente NO tienen descripción válida
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
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")

        for titulo, desc in nuevas.items():
            # Si el valor retornado es directamente un string o dict
            texto_desc = desc.get("descripcion", desc) if isinstance(desc, dict) else desc
            descripciones_limpias[titulo.strip()] = {
                "descripcion": texto_desc,
                "fecha_registro": fecha_hoy
            }

    # 4. Guardar archivo consolidado
    guardar_json(PATH_DESCRIPCIONES, descripciones_limpias)
    print("Archivo descripciones_ia.json actualizado correctamente.")

if __name__ == "__main__":
    main()
