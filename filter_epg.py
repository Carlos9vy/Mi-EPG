import xml.etree.ElementTree as ET
import requests
import os
import gzip
import io
from datetime import datetime, timedelta

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
SHIFT_FILE = "shift.txt" # Nuevo archivo de configuración
OUTPUT_FILE = "epg_reducida.xml"
OUTPUT_GZ = "epg_reducida.xml.gz"
LOG_ERRORES = "errores_canales.txt"

def apply_shift(timestr, hours):
    if not timestr: return timestr
    try:
        # El formato XMLTV suele ser AAAAMMDDHHMMSS +HHMM
        fmt = "%Y%m%d%H%M%S %z"
        # Separar la fecha del offset para manejarlo más fácil
        dt = datetime.strptime(timestr, fmt)
        new_dt = dt + timedelta(hours=int(hours))
        return new_dt.strftime(fmt)
    except Exception:
        return timestr

def filter_epg():
    if not os.path.exists(CANALES_FILE): return

    with open(CANALES_FILE, 'r', encoding='utf-8') as f:
        whitelist = set(line.strip() for line in f if line.strip())
    
    # Cargar los ajustes de hora (shift)
    shifts = {}
    if os.path.exists(SHIFT_FILE):
        with open(SHIFT_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if ',' in line:
                    cid, val = line.strip().split(',')
                    shifts[cid] = val

    canales_encontrados = set()
    root = ET.Element('tv', {'generator-info-name': 'Generador EPG Pro con Shift', 'generator-info-url': 'https://github.com'})

    headers = {'User-Agent': 'Mozilla/5.0'}

    for url in EPG_SOURCES:
        try:
            print(f"Escaneando: {url}")
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
                        # --- APLICAR SHIFT AQUÍ ---
                        if pid in shifts:
                            elem.set('start', apply_shift(elem.get('start'), shifts[pid]))
                            elem.set('stop', apply_shift(elem.get('stop'), shifts[pid]))
                        
                        # Limpieza para Netcast
                        for extra in ['credits', 'country', 'language']:
                            target = elem.find(extra)
                            if target is not None: elem.remove(target)
                        root.append(elem)

        except Exception as e:
            print(f"Error en fuente: {e}")

    tree = ET.ElementTree(root)
    tree.write(OUTPUT_FILE, encoding='utf-8', xml_declaration=True)
    with gzip.open(OUTPUT_GZ, 'wb') as f:
        tree.write(f, encoding='utf-8', xml_declaration=True)

if __name__ == "__main__":
    filter_epg()
