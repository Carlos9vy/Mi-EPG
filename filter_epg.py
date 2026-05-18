import requests
import xml.etree.ElementTree as ET
import gzip
from datetime import datetime, timedelta

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
    if "\n" in desc_text:
        lines = desc_text.split("\n")
        first_line = lines[0].strip()
        if first_line and not first_line.endswith(('.', '!', '?', ':', '-')):
            lines[0] = first_line + "."
        return "\n".join(lines)
    return desc_text

def apply_time_shift(time_str, hours_shift):
    """Suma o resta horas al formato de tiempo estándar de EPG (ej. 20260517002000 +0000)."""
    if not time_str or hours_shift == 0:
        return time_str
    try:
        # Formato común EPG: AAAAMMDDHHMMSS +/-HHMM
        parts = time_str.split()
        base_time = parts[0]
        tz = parts[1] if len(parts) > 1 else ""
        
        dt = datetime.strptime(base_time, "%Y%m%d%H%M%S")
        # Convertimos las horas (ej. 0.5 o -1.0) en minutos para ser exactos
        dt_shifted = dt + timedelta(minutes=int(hours_shift * 60))
        
        new_base_time = dt_shifted.strftime("%Y%m%d%H%M%S")
        return f"{new_base_time} {tz}".strip()
    except Exception:
        return time_str

def run():
    standard_wanted_ids = set()
    open_epg_wanted_ids = set()
    raw_lines_map = {} 
    shifts = {}

    # 1. Cargar el archivo shift.txt si existe
    try:
        with open("shift.txt", "r", encoding="utf-8") as f:
            for line in f:
                line_clean = line.strip()
                if line_clean and "," in line_clean:
                    cid, val = line_clean.split(",", 1)
                    try:
                        shifts[cid.strip()] = float(val.strip())
                    except ValueError:
                        print(f"Valor de shift inválido para el canal: {cid}")
        print(f"Cargados {len(shifts)} ajustes de hora desde shift.txt")
    except FileNotFoundError:
        print("No se encontró shift.txt. Se procesará sin ajustes horarios.")

    # 2. Cargar tus canales deseados desde canales.txt
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
            
            # Procesar programas, corregir descripciones y aplicar shifts horario
            for p in tree.findall("programme"):
                p_channel = p.get("channel")
                if p_channel:
                    p_channel_clean = p_channel.strip()
                    
                    is_match = (is_open_epg_url and p_channel_clean in all_clean_wanted) or \
                               (not is_open_epg_url and p_channel_clean in standard_wanted_ids)
                    
                    if is_match:
                        # --- MEJORA ESTÉTICA DE LA DESCRIPCIÓN ---
                        desc_element = p.find("desc")
                        if desc_element is not None and desc_element.text:
                            desc_element.text = fix_description(desc_element.text)
                        
                        # --- MEJORA AJUSTE HORARIO (TIME SHIFT) ---
                        if p_channel_clean in shifts:
                            shift_value = shifts[p_channel_clean]
                            start_time = p.get("start")
                            stop_time = p.get("stop")
                            
                            if start_time:
                                p.set("start", apply_time_shift(start_time, shift_value))
                            if stop_time:
                                p.set("stop", apply_time_shift(stop_time, shift_value))
                        
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
