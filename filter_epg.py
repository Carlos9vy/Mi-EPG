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

def fix_description(desc_text):
    """Mejora la estética de la descripción añadiendo un punto antes del salto de línea."""
    if not desc_text:
        return ""
    
    # Validamos si la descripción contiene saltos de línea
    if "\n" in desc_text:
        # Dividimos por líneas para analizar el 'título' del episodio
        lines = desc_text.split("\n")
        first_line = lines[0].strip()
        
        # Si la primera línea tiene texto y no termina en un signo de puntuación común
        if first_line and not first_line.endswith(('.', '!', '?', ':', '-')):
            lines[0] = first_line + "."
            
        # Volvemos a unir respetando el salto de línea original
        return "\n".join(lines)
        
    return desc_text

def run():
    standard_wanted_ids = set()
    open_epg_wanted_ids = set()
    raw_lines_map = {} 

    try:
        with open("canales.txt", "r", encoding="utf-8") as f:
            for line in f:
                line_clean = line.strip()
                if not line_clean:
                    continue
                
                if "(open-epg.com)" in line_clean:
                    id_clean = line_clean.replace("(open-epg.com)", "").strip()
                    open_epg_wanted_ids.add(id_clean)
                    raw_lines_map[id_clean] = line_clean
                else:
                    standard_wanted_ids.add(line_clean)
                    raw_lines_map[line_clean] = line_clean
                    
        print(f"Cargados canales. Estándar: {len(standard_wanted_ids)}, Open-EPG: {len(open_epg_wanted_ids)}")
    except FileNotFoundError:
        print("Error: No se encontró canales.txt")
        return

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
            
            # Procesar canales
            for c in tree.findall("channel"):
                xml_id = c.get("id")
                if xml_id:
                    xml_id_clean = xml_id.strip()
                    if is_open_epg_url:
                        if xml_id_clean in all_clean_wanted:
                            channels_found.append(c)
                            missing_clean_ids.discard(xml_id_clean)
                    else:
                        if xml_id_clean in standard_wanted_ids:
                            channels_found.append(c)
                            missing_clean_ids.discard(xml_id_clean)
            
            # Procesar programas y corregir descripciones
            for p in tree.findall("programme"):
                p_channel = p.get("channel")
                if p_channel:
                    p_channel_clean = p_channel.strip()
                    
                    # Verificar si el programa pertenece a nuestra lista de interés
                    is_match = (is_open_epg_url and p_channel_clean in all_clean_wanted) or \
                               (not is_open_epg_url and p_channel_clean in standard_wanted_ids)
                    
                    if is_match:
                        # Buscamos la etiqueta <desc> dentro del programa
                        desc_element = p.find("desc")
                        if desc_element is not None and desc_element.text:
                            # Aplicamos la mejora estética al texto de la descripción
                            desc_element.text = fix_description(desc_element.text)
                        
                        programmes_found.append(p)
                    
        except Exception as e:
            print(f"Error procesando {url}: {e}")

    # Unir canales sin duplicados
    unique_channels = {c.get("id").strip(): c for c in channels_found}.values()
    for c in unique_channels:
        new_root.append(c)
    for p in programmes_found:
        new_root.append(p)

    # Guardar archivos
    output_xml = "guia_personalizada.xml"
    ET.ElementTree(new_root).write(output_xml, encoding="utf-8", xml_declaration=True)

    try:
        with open(output_xml, "rb") as f_in, gzip.open("guia_personalizada.xml.gz", "wb") as f_out:
            f_out.writelines(f_in)
    except Exception as e:
        print(f"Error al comprimir: {e}")

    # Reporte de errores
    output_errors = "errores canales.txt"
    with open(output_errors, "w", encoding="utf-8") as f_err:
        if missing_clean_ids:
            for missing_id in sorted(missing_clean_ids):
                f_err.write(f"{raw_lines_map[missing_id]}\n")
            print(f"Proceso concluido. Errores guardados en '{output_errors}'.")
        else:
            f_err.write("¡Felicidades! Todos los canales fueron encontrados con éxito.\n")
            print("¡Éxito total!")

if __name__ == "__main__":
    run()
