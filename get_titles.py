import requests
import xml.etree.ElementTree as ET
import gzip
import re
import json
import os

# Las fuentes de televisión
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
    # Usamos una lista para preservar el orden exacto en que los escribiste
    lista_ids_ordenadas = []
    titulos_por_canal = {}
    titulos_ya_existentes = set()

    # 1. LEER LA BASE DE DATOS ACTUAL (Omitir lo que ya está hecho)
    base_datos_real = "descripciones_ia.json"
    if os.path.exists(base_datos_real):
        try:
            with open(base_datos_real, "r", encoding="utf-8") as f_db:
                data_db = json.load(f_db)
                for titulo, descripcion in data_db.items():
                    if descripcion.strip(): 
                        titulos_ya_existentes.add(titulo)
            print(f"🧠 Base de datos detectada: Se omitirán {len(titulos_ya_existentes)} títulos con sinopsis.")
        except Exception as e:
            print(f"⚠️ No se pudo leer '{base_datos_real}'. Se procesará todo. Error: {e}")

    # 2. Leer tus canales autorizados preservando el orden exacto del archivo
    try:
        with open("canales_ia.txt", "r", encoding="utf-8") as f:
            for line in f:
                line_clean = line.strip()
                if line_clean and line_clean not in lista_ids_ordenadas:
                    lista_ids_ordenadas.append(line_clean)
                    # Inicializamos el contenedor de títulos para este canal
                    titulos_por_canal[line_clean] = set()
        print(f"📋 Cargados {len(lista_ids_ordenadas)} canales en orden desde canales_ia.txt")
    except FileNotFoundError:
        print("❌ Error: Necesitas tener el archivo 'canales_ia.txt' en la misma carpeta.")
        return

    if not lista_ids_ordenadas:
        return

    # 3. Descargar y escanear canales
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
                if p_channel:
                    p_channel_clean = p_channel.strip()
                    # Si el canal está en nuestra lista ordenada, extraemos su título
                    if p_channel_clean in titulos_por_canal:
                        title_elem = p.find("title")
                        if title_elem is not None and title_elem.text:
                            titulo_limpio = title_elem.text.strip()
                            
                            if titulo_limpio and (titulo_limpio not in titulos_ya_existentes):
                                titulos_por_canal[p_channel_clean].add(titulo_limpio)
                            
        except Exception:
            continue

    # 4. Construir la plantilla final en el orden de canales_ia.txt
    plantilla_final = {}
    total_novedades = 0

    for canal_id in lista_ids_ordenadas:
        titulos_del_canal = sorted(list(titulos_por_canal[canal_id]))
        
        # Si el canal tiene títulos nuevos, le creamos su encabezado "comentario" seguro
        if titulos_del_canal:
            encabezado_seguro = f"====== CANAL: {canal_id} ======"
            plantilla_final[encabezado_seguro] = "----------------------------------------"
            
            for t in titulos_del_canal:
                plantilla_final[t] = ""
                total_novedades += 1

    # 5. Guardar el archivo borrador estructurado
    output_file = "borrador_titulos.json"
    if total_novedades > 0:
        with open(output_file, "w", encoding="utf-8") as f_out:
            json.dump(plantilla_final, f_out, ensure_ascii=False, indent=4)
        print(f"\n🎉 ¡Filtrado completado! Se encontraron {total_novedades} títulos nuevos.")
        print(f"📁 Borrador ordenado generado con éxito: '{output_file}'")
    else:
        print("\n😎 ¡Al día! No se encontraron programas nuevos en las grillas de tus canales.")

if __name__ == "__main__":
    extraer_plantilla_json()
