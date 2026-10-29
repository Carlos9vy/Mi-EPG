import requests
import xml.etree.ElementTree as ET
import gzip
import json
from datetime import datetime, timedelta
from xml.sax.saxutils import escape

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
    "https://github.com/Carlos9vy/mi-laboratorio-epg/raw/refs/heads/main/guia_laboratorio.xml",
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
        parts = time_str.split()
        base_time = parts[0]
        tz = parts[1] if len(parts) > 1 else ""
        
        dt = datetime.strptime(base_time, "%Y%m%d%H%M%S")
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
    
    # Mapeos para el módulo de inyección local de base de datos
    allowed_ia_channels = set()
    database_descriptions = {}

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

    # 2. Cargar canales permitidos para inyección desde canales_ia.txt
    try:
        with open("canales_ia.txt", "r", encoding="utf-8") as f:
            for line in f:
                line_clean = line.strip()
                if line_clean:
                    allowed_ia_channels.add(line_clean)
        print(f"📦 Módulo Local: Cargados {len(allowed_ia_channels)} canales permitidos desde canales_ia.txt")
    except FileNotFoundError:
        print("⚠️ Advertencia: No se encontró canales_ia.txt. No se inyectarán descripciones.")

    # 3. Cargar diccionario de descripciones fijas desde descripciones_ia.json
    try:
        with open("descripciones_ia.json", "r", encoding="utf-8") as f:
            database_descriptions = json.load(f)
        print(f"📖 Base de datos cargada con éxito. Registros disponibles: {len(database_descriptions)}")
    except FileNotFoundError:
        print("⚠️ Advertencia: No se encontró descripciones_ia.json. No se realizarán reemplazos.")
    except json.JSONDecodeError:
        print("❌ Error: descripciones_ia.json tiene un formato JSON inválido.")

    # 4. Cargar tus canales deseados desde canales.txt
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
    inserted_descriptions_count = 0

    for url in SOURCES:
        is_open_epg_url = "open-epg.com" in url
        try:
            print(f"Descargando fuente: {url}")
            # Timeout optimizado a 15 segundos para evitar cuelgues del runner
            r = requests.get(url, timeout=15)
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
            
            # Procesar programas, corregir descripciones, aplicar shifts e inyectar JSON
            for p in tree.findall("programme"):
                p_channel = p.get("channel")
                if p_channel:
                    p_channel_clean = p_channel.strip()
                    
                    is_match = (is_open_epg_url and p_channel_clean in all_clean_wanted) or \
                               (not is_open_epg_url and p_channel_clean in standard_wanted_ids)
                    
                    if is_match:
                        # --- MEJORA ESTÉTICA O INYECCIÓN DE LA DESCRIPCIÓN ---
                        desc_element = p.find("desc")
                        p_title_element = p.find("title")
                        p_title = p_title_element.text.strip() if (p_title_element is not None and p_title_element.text) else ""

                        # Si no existe la etiqueta desc, o existe pero está vacía
                        is_desc_empty = (desc_element is not None and not str(desc_element.text).strip()) or (desc_element is None)

                        if is_desc_empty and p_channel_clean in allowed_ia_channels and p_title in database_descriptions:
                            raw_db_desc = database_descriptions[p_title]
                            safe_db_desc = escape(raw_db_desc)
                            
                            if desc_element is None:
                                desc_element = ET.SubElement(p, "desc", {"lang": "es"})
                            
                            desc_element.text = fix_description(safe_db_desc)
                            inserted_descriptions_count += 1
                        elif desc_element is not None and desc_element.text:
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
                    
        except requests.exceptions.Timeout:
            print(f"⚠️ Aviso: La fuente {url} tardó demasiado en responder (Timeout). Saltando...")
            continue
        except Exception as e:
            print(f"Error procesando {url}: {e}")

    # Mensaje de confirmación del módulo de base de datos local
    if inserted_descriptions_count > 0:
        print(f"🎉 Módulo Local completado. Se insertaron {inserted_descriptions_count} descripciones guardadas.")

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
