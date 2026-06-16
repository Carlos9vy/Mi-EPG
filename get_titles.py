import requests
import xml.etree.ElementTree as ET
import gzip
import re
import json
import os

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

def extraer_plantilla_json():
    ids_ia_autorizados = set()
    titulos_unicos = set()
    titulos_ya_existentes = set()

    # 1. LEER LA BASE DE DATOS ACTUAL (Para omitir lo que ya está hecho)
    base_datos_real = "descripciones_ia.json"
    if os.path.exists(base_datos_real):
        try:
            with open(base_datos_real, "r", encoding="utf-8") as f_db:
                data_db = json.load(f_db)
                # Guardamos los títulos que ya tienen una sinopsis (que no estén vacías)
                for titulo, descripcion in data_db.items():
                    if descripcion.strip(): 
                        titulos_ya_existentes.add(titulo)
            print(f"🧠 Base de datos detectada: Se omitirán {len(titulos_ya_existentes)} títulos que ya tienen sinopsis.")
        except Exception as e:
            print(f"⚠️ No se pudo leer '{base_datos_real}' o está vacío. Se procesará todo. Extre: {e}")

    # 2. Leer tus 7 canales autorizados
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

            # Reparación rápida de ampersands peligrosos
            xml_text = re.sub(r'&(?!([a-zA-Z0-9]+|#[0-9]+|#x[a-fA-F0-9]+);)', '&amp;', xml_text)
            tree = ET.fromstring(xml_text.encode("utf-8"))
            
            for p in tree.findall("programme"):
                p_channel = p.get("channel")
                if p_channel and p_channel.strip() in ids_ia_autorizados:
                    title_elem = p.find("title")
                    if title_elem is not None and title_elem.text:
                        titulo_limpio = title_elem.text.strip()
                        
                        # ¡AQUÍ ESTÁ TU IDEA! Si el título ya existe en la base de datos, lo ignora por completo
                        if titulo_limpio and (titulo_limpio not in titulos_ya_existentes):
                            titulos_unicos.add(titulo_limpio)
                            
        except Exception:
            continue

    # 4. Crear el archivo borrador solo con las novedades
    output_file = "borrador_titulos.json"
    plantilla_json = {titulo: "" for titulo in sorted(titulos_unicos)}

    if plantilla_json:
        with open(output_file, "w", encoding="utf-8") as f_out:
            json.dump(plantilla_json, f_out, ensure_ascii=False, indent=4)
        print(f"\n🎉 ¡Filtrado completado! Se encontraron {len(plantilla_json)} títulos NUEVOS para rellenar.")
        print(f"📁 Archivo de novedades generado: '{output_file}'")
    else:
        print("\n😎 ¡Al día! Todos los programas en emisión ya tienen su sinopsis en la base de datos. Nada nuevo que agregar.")

if __name__ == "__main__":
    extraer_plantilla_json()
