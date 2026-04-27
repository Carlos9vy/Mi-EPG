import xml.etree.ElementTree as ET
import requests
import os
import gzip
import io
from datetime import datetime, timedelta

# Configuración de archivos y fuentes
EPG_SOURCES = [
    "https://iptv-epg.org/files/epg-ztjwyq.xml",
    "https://www.open-epg.com/generate/aYzuzNSenh.xml",
    "https://iptv-epg.org/files/epg-bo.xml",
    "https://iptv-epg.org/files/epg-cr.xml",
    "https://iptv-epg.org/files/epg-do.xml",
    "https://iptv-epg.org/files/epg-sv.xml",
    "https://iptv-epg.org/files/epg-gt.xml",
    "https://iptv-epg.org/files/epg-hn.xml",
    "https://iptv-epg.org/files/epg-py.xml",
    "https://iptv-epg.org/files/epg-pa.xml",
    "https://epgshare01.online/epgshare01/epg_ripper_SV1.xml.gz" 
]

CANALES_FILE = "canales.txt"
SHIFT_FILE = "shift.txt"
OUTPUT_FILE = "epg_reducida.xml"
OUTPUT_GZ = "epg_reducida.xml.gz"
LOG_ERRORES = "errores_canales.txt"

def apply_shift(timestr, hours_val):
    """Ajusta la hora permitiendo decimales (ej: 1.5 para 1h 30min)"""
    if not timestr or len(timestr) < 14: 
        return timestr
    try:
        base_time = timestr[:14] 
        offset = timestr[15:]    
        dt = datetime.strptime(base_time, "%Y%m%d%H%M%S")
        total_minutes = float(hours_val) * 60
        new_dt = dt + timedelta(minutes=int(total_minutes))
        return new_dt.strftime("%Y%m%d%H%M%S") + " " + offset
    except Exception:
        return timestr

def filter_epg():
    if not os.path.exists(CANALES_FILE):
        return

    # 1. Cargar lista de canales y shifts
    with open(CANALES_FILE, 'r', encoding='utf-8') as f:
        whitelist = set(line.strip() for line in f if line.strip())
    
    shifts = {}
    if os.path.exists(SHIFT_FILE):
        with open(SHIFT_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if ',' in line:
                    cid, val = line.strip().split(',')
                    shifts[cid.strip()] = val.strip()

    canales_encontrados = set()
    root = ET.Element('tv', {'generator-info-name': 'EPG Clean Space', 'generator-info-url': 'https://github.com'})

    headers = {'User-Agent': 'Mozilla/5.0'}

    # 2. Procesar fuentes
    for url in EPG_SOURCES:
        try:
            print(f"Leyendo: {url}")
            r = requests.get(url, headers=headers, timeout=60)
            r.raise_for_status()
            content = gzip.decompress(r.content) if (url.endswith(".gz") or r.content[:2] == b'\x1f\x8b') else r.content
            context = ET.iterparse(io.BytesIO(content), events=('end',))
            
            for event, elem in context:
                if elem.tag == 'channel':
                    cid = elem.get('id')
                    if cid in whitelist and cid not in canales_encontrados:
                        root.append(elem)
                        canales_encontrados.add(cid)
                
                elif elem.tag == 'programme':
                    pid = elem.get('channel')
                    if pid in whitelist:
                        # --- SHIFT ---
                        if pid in shifts:
                            elem.set('start', apply_shift(elem.get('start'), shifts[pid]))
                            elem.set('stop', apply_shift(elem.get('stop'), shifts[pid]))
                        
                        # --- CORRECCIÓN DE ESPACIOS (Sin barras |) ---
                        title = elem.find('title')
                        category = elem.find('category')
                        desc = elem.find('desc')

                        # Añadir espacio al título si no tiene puntuación final
                        if title is not None and title.text:
                            text = title.text.strip()
                            if not text.endswith((' ', '.', ':', '-', '!', '?')):
                                title.text = text + " "

                        # Añadir espacio a la categoría si existe
                        if category is not None and category.text:
                            text = category.text.strip()
                            if not text.endswith((' ', '.', ':', '-')):
                                category.text = text + " "

                        # --- LIMPIEZA DE ETIQUETAS PESADAS ---
                        for extra in ['credits', 'country', 'language', 'sub-title']:
                            target = elem.find(extra)
                            if target is not None: elem.remove(target)
                        
                        root.append(elem)

        except Exception as e:
            print(f"Error: {e}")

    # 3. Guardar
    tree = ET.ElementTree(root)
    tree.write(OUTPUT_FILE, encoding='utf-8', xml_declaration=True)
    with gzip.open(OUTPUT_GZ, 'wb') as f:
        tree.write(f, encoding='utf-8', xml_declaration=True)

    # 4. Log de faltantes
    faltantes = whitelist - canales_encontrados
    with open(LOG_ERRORES, 'w', encoding='utf-8') as f:
        f.write("⚠️ Faltantes:\n" + "\n".join(sorted(faltantes)) if faltantes else "✅ Todo OK")

if __name__ == "__main__":
    filter_epg()
