import requests
import xml.etree.ElementTree as ET
import gzip

# Fuentes originales
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
    "https://www.open-epg.com/generate/aYzuzNSenh.xml",
    "https://epgshare01.online/epgshare01/epg_ripper_SV1.xml.gz"
]

def run():
    # Diccionarios para clasificar tus canales solicitados
    standard_wanted_ids = set()
    open_epg_wanted_ids = set()
    
    # Guardamos cómo escribiste originalmente la línea para el reporte de errores
    raw_lines_map = {} 

    try:
        with open("canales.txt", "r", encoding="utf-8") as f:
            for line in f:
                line_clean = line.strip()
                if not line_clean:
                    continue
                
                # Si la línea contiene la etiqueta de open-epg
                if "(open-epg.com)" in line_clean:
                    # Extrae el ID quitando el fragmento "(open-epg.com)" y limpiando espacios
                    id_clean = line_clean.replace("(open-epg.com)", "").strip()
                    open_epg_wanted_ids.add(id_clean)
                    raw_lines_map[id_clean] = line_clean
                else:
                    standard_wanted_ids.add(line_clean)
                    raw_lines_map[line_clean] = line_clean
                    
        print(f"Cargados canales. Estándar: {len(standard_wanted_ids)}, Exclusivos Open-EPG: {len(open_epg_wanted_ids)}")
    except FileNotFoundError:
        print("Error: No se encontró canales.txt")
        return

    # Unificar todos los IDs limpios que el robot debe encontrar a lo largo del proceso
    all_clean_wanted = standard_wanted_ids.union(open_epg_wanted_ids)
    missing_clean_ids = all_clean_wanted.copy()

    new_root = ET.Element("tv", {"generator-info-name": "MiRobotEPG"})
    channels_found = []
    programmes_found = []

    for url in SOURCES:
        is_open_epg_url = "open-epg.com" in url
        
        try:
            print(f"Descargando fuente: {url}")
            r = requests.get(url, timeout=60)
            data = r.content
            
            if url.endswith(".gz"):
                data = gzip.decompress(data)
            
            tree = ET.fromstring(data)
            
            # Procesar canales de la fuente actual
            for c in tree.findall("channel"):
                xml_id = c.get("id")
                if xml_id:
                    xml_id_clean = xml_id.strip()
                    
                    # Decisión inteligente del robot:
                    if is_open_epg_url:
                        # Si es la fuente Open-EPG, busca tanto sus exclusivos como los estándar por si acaso
                        if xml_id_clean in all_clean_wanted:
                            channels_found.append(c)
                            missing_clean_ids.discard(xml_id_clean)
                    else:
                        # Si es cualquier otra fuente, ignora los exclusivos de Open-EPG
                        if xml_id_clean in standard_wanted_ids:
                            channels_found.append(c)
                            missing_clean_ids.discard(xml_id_clean)
            
            # Procesar programas de la fuente actual
            for p in tree.findall("programme"):
                p_channel = p.get("channel")
                if p_channel:
                    p_channel_clean = p_channel.strip()
                    
                    if is_open_epg_url:
                        if p_channel_clean in all_clean_wanted:
                            programmes_found.append(p)
                    else:
                        if p_channel_clean in standard_wanted_ids:
                            programmes_found.append(p)
                    
        except Exception as e:
            print(f"Error procesando {url}: {e}")

    # Unir canales evitando duplicados en el XML final
    unique_channels = {c.get("id").strip(): c for c in channels_found}.values()
    for c in unique_channels:
        new_root.append(c)
    for p in programmes_found:
        new_root.append(p)

    # 1. Guardar archivo XML normal
    output_xml = "guia_personalizada.xml"
    ET.ElementTree(new_root).write(output_xml, encoding="utf-8", xml_declaration=True)

    # 2. Guardar archivo comprimido (.gz)
    try:
        with open(output_xml, "rb") as f_in, gzip.open("guia_personalizada.xml.gz", "wb") as f_out:
            f_out.writelines(f_in)
    except Exception as e:
        print(f"Error al comprimir: {e}")

    # 3. Guardar el archivo de errores mostrando el formato original con el que escribiste
    output_errors = "errores canales.txt"
    with open(output_errors, "w", encoding="utf-8") as f_err:
        if missing_clean_ids:
            for missing_id in sorted(missing_clean_ids):
                # Escribe el error usando tu formato original guardado en el mapa
                f_err.write(f"{raw_lines_map[missing_id]}\n")
            print(f"Proceso concluido. Quedaron {len(missing_clean_ids)} IDs con error.")
        else:
            f_err.write("¡Felicidades! Todos los canales fueron encontrados con éxito.\n")
            print("¡Éxito total!")

if __name__ == "__main__":
    run()
