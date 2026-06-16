import requests
import xml.etree.ElementTree as ET
import gzip
import re
import json
import os

# Las mismas fuentes para escanear las parrillas actuales
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

def extraer_plantilla_json():
    ids_ia_autorizados = set()
    titulos_unicos = set()

    # 1. Leer tus 7 canales desde tu archivo local
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

    # 2. Descargar y escanear canales
    print("🛰️ Escaneando guías internacionales para buscar tus programas...")
    for url in SOURCES:
        try:
            r = requests.get(url, timeout=45)
            if url.endswith(".gz"):
                data = gzip.decompress(r.content)
                xml_text = data.decode("utf-8", errors="ignore")
            else:
                xml_text = r.text

            # Limpieza de ampersands para evitar caídas
            xml_text = re.sub(r'&(?!([a-zA-Z0-9]+|#[0-9]+|#x[a-fA-F0-9]+);)', '&amp;', xml_text)
            tree = ET.fromstring(xml_text.encode("utf-8"))
            
            for p in tree.findall("programme"):
                p_channel = p.get("channel")
                if p_channel and p_channel.strip() in ids_ia_autorizados:
                    title_elem = p.find("title")
                    if title_elem is not None and title_elem.text:
                        titulo_limpio = title_elem.text.strip()
                        if titulo_limpio:
                            titulos_unicos.add(titulo_limpio)
                            
        except Exception:
            # Pasa silenciosamente si una fuente falla para no frenar el escaneo
            continue

    # 3. Crear el archivo borrador en formato JSON
    output_file = "borrador_titulos.json"
    
    # Armamos un diccionario vacío estructurado: {"Título": ""}
    plantilla_json = {titulo: "" for titulo in sorted(titulos_unicos)}

    if plantilla_json:
        with open(output_file, "w", encoding="utf-8") as f_out:
            json.dump(plantilla_json, f_out, ensure_ascii=False, indent=4)
        print(f"\n🎉 ¡Listo! Se encontraron {len(plantilla_json)} títulos únicos en la tele justo ahora.")
        print(f"📁 Archivo generado: '{output_file}'")
        print("💡 Ábrelo, escribe las sinopsis que quieras y luego pégalas en tu descripciones_ia.json")
    else:
        print("\n❌ No se detectaron programas transmitiéndose para tus 7 canales en este momento.")

if __name__ == "__main__":
    extraer_plantilla_json()
