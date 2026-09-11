import requests
import xml.etree.ElementTree as ET
import gzip
import re
import json
import os
import unicodedata

# Las 21 fuentes de televisión
SOURCES = [
    "https://iptv-epg.org/files/epg-ar.xml", "https://iptv-epg.org/files/epg-cl.xml",
    "https://iptv-epg.org/files/epg-co.xml", "https://iptv-epg.org/files/epg-ec.xml",
    "https://iptv-epg.org/files/epg-mx.xml", "https://iptv-epg.org/files/epg-pe.xml",
    "https://iptv-epg.org/files/epg-es.xml", "https://iptv-epg.org/files/epg-us.xml",
    "https://iptv-epg.org/files/epg-uy.xml", "https://iptv-epg.org/files/epg-ve.xml",
    "https://iptv-epg.org/files/epg-bo.xml", "https://iptv-epg.org/files/epg-cr.xml",
    "https://iptv-epg.org/files/epg-do.xml", "https://iptv-epg.org/files/epg-sv.xml",
    "https://iptv-epg.org/files/epg-gt.xml", "https://iptv-epg.org/files/epg-hn.xml",
    "https://iptv-epg.org/files/epg-py.xml", "https://iptv-epg.org/files/epg-pa.xml",
    "https://github.com/Carlos9vy/mi-laboratorio-epg/raw/refs/heads/main/guia_laboratory.xml",
    "https://www.open-epg.com/generate/aYzuzNSenh.xml",
    "https://epgshare01.online/epgshare01/epg_ripper_SV1.xml.gz"
]

def normalizar_texto(texto):
    """
    Convierte el texto a minúsculas y quita tildes/espacios extras
    para detectar coincidencias exactas sin importar formato.
    """
    texto = texto.strip().lower()
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )

def extraer_plantilla_json():
    ids_ia_autorizados = set()
    titulos_nuevos = {}  # Guardará {titulo_normalizado: titulo_original}
    normalizados_existentes = set()

    # 1. LEER LA BASE DE DATOS ACTUAL (descripciones_ia.json)
    base_datos_real = "descripciones_ia.json"
    if os.path.exists(base_datos_real):
        try:
            with open(base_datos_real, "r", encoding="utf-8") as f_db:
                data_db = json.load(f_db)
                for titulo in data_db.keys():
                    if titulo and str(titulo).strip():
                        normalizados_existentes.add(normalizar_texto(str(titulo)))
            print(f"🧠 Base de datos detectada: Se omitirán {len(normalizados_existentes)} títulos que ya existen en descripciones_ia.json.")
        except Exception as e:
            print(f"⚠️ No se pudo leer '{base_datos_real}'. Error: {e}")

    # 2. Leer canales autorizados
    try:
        with open("canales_ia.txt", "r", encoding="utf-8") as f:
            for line in f:
                line_clean = line.strip()
                if line_clean:
                    ids_ia_autorizados.add(line_clean)
        print(f"📋 Cargados {len(ids_ia_autorizados)} canales desde canales_ia.txt")
    except FileNotFoundError:
        print("❌ Error: Necesitas tener el archivo 'canales_ia.txt' en la misma carpeta.")
        return

    if not ids_ia_autorizados:
        return

    # 3. Descargar y escanear canales internacionales
    print("🛰️ Escaneando guías para buscar programación nueva...")
    for url in SOURCES:
        try:
            r = requests.get(url, timeout=45)
            if url.endswith(".gz"):
                data = gzip.decompress(r.content)
                xml_text = data.decode("utf-8", errors="ignore")
            else:
                xml_text = r.text

            xml_text = re.sub(r'&(?!([a-zA-Z0-9]+|#[0-9]+|#x[a-fA-F0-9]+);)', '&amp;', xml_text)
            tree = ET.fromstring(xml_text.encode("utf-8"))
            
            for p in tree.findall("programme"):
                p_channel = p.get("channel")
                if p_channel and p_channel.strip() in ids_ia_autorizados:
                    title_elem = p.find("title")
                    if title_elem is not None and title_elem.text:
                        titulo_original = title_elem.text.strip()
                        titulo_norm = normalizar_texto(titulo_original)
                        
                        # VERIFICACIÓN: Si no está en descripciones_ia.json Y tampoco se ha agregado antes en este mismo escaneo
                        if titulo_norm and (titulo_norm not in normalizados_existentes) and (titulo_norm not in titulos_nuevos):
                            titulos_nuevos[titulo_norm] = titulo_original
                            
        except Exception:
            continue

    # 4. Crear el archivo borrador sólo con los títulos únicos que no existían
    output_file = "borrador_titulos.json"
    plantilla_json = {titulo_orig: "" for titulo_orig in sorted(titulos_nuevos.values())}

    with open(output_file, "w", encoding="utf-8") as f_out:
        json.dump(plantilla_json, f_out, ensure_ascii=False, indent=4)

    if plantilla_json:
        print(f"\n🎉 ¡Filtrado completado! Se encontraron {len(plantilla_json)} títulos NUEVOS para rellenar.")
        print(f"📁 Archivo de novedades generado: '{output_file}'")
    else:
        print("\n😎 ¡Al día! Todos los programas en emisión ya están registrados. Nada nuevo que agregar a borrador_titulos.json.")

if __name__ == "__main__":
    extraer_plantilla_json()
