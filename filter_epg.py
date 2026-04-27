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
        # Formato XMLTV: AAAAMMDDHHMMSS +HHMM
        base_time = timestr[:14] 
        offset = timestr[15:]    
        
        dt = datetime.strptime(base_time, "%Y%m%d%H%M%S")
        
        # Convertimos las horas (decimales) a minutos
        total_minutes = float(hours_val) * 60
        new_dt = dt + timedelta(minutes=int(total_minutes))
        
        return new_dt.strftime("%Y%m%d%H%M%S") + " " + offset
    except Exception as e:
        print(f"Error ajustando tiempo: {e}")
        return timestr

def filter_epg():
    if not os.path.exists(CANALES_FILE):
        print(f"Error: No se encuentra {CANALES_FILE}")
        return

    # 1. Cargar lista de canales (Whitelist)
    with open(CANALES_FILE, 'r', encoding='utf-8') as f:
        whitelist = set(line.strip() for line in f if line.strip())
    
    # 2. Cargar ajustes de hora (Shift)
    shifts = {}
    if os.path.exists(SHIFT_FILE):
        with open(SHIFT_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if ',' in line:
                    parts = line.strip().split(',')
                    if len(parts) == 2:
                        cid, val = parts
                        shifts[cid.strip()] = val.strip()

    canales_encontrados = set()
    root = ET.Element('tv', {
        'generator-info-name': 'Generador EPG Pro Optimizado', 
        'generator-info-url': 'https://github.com'
    })

    headers = {'User-Agent': 'Mozilla/5.0'}

    # 3. Procesar cada fuente
    for url in EPG_SOURCES:
        try:
            print(f"Escaneando fuente: {url}")
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
                        # --- A. APLICAR SHIFT ---
                        if pid in shifts:
                            elem.set('start', apply_shift(elem.get('start'), shifts[pid]))
                            elem.set('stop', apply_shift(elem.get('stop'), shifts[pid]))
                        
                        # --- B. CORREGIR TEXTOS PEGADOS ---
                        title_elem = elem.find('title')
                        category_elem = elem.find('category')
                        desc_elem = elem.find('desc')

                        # Separar Título de lo que sigue
                        if title_elem is not None and title_elem.text:
                            t_text = title_elem.text.strip()
                            if not t_text.endswith((' ', '.', ':', '-', '|')):
                                title_elem.text = t_text + " | "

                        # Separar Categoría de la Descripción
                        if category_elem is not None and category_elem.text:
                            c_text = category_elem.text.strip()
                            if not c_text.endswith((' ', '.', ':', '-', '|')):
                                category_elem.text = c_text + " | "

                        # --- C. LIMPIEZA DE MEMORIA (Netcast) ---
                        # Eliminamos lo que más pesa y menos se usa
                        for extra in ['credits', 'country', 'language', 'sub-title']:
                            target = elem.find(extra)
                            if target is not None: 
                                elem.remove(target)
                        
                        root.append(elem)

        except Exception as e:
            print(f"Error en fuente {url}: {e}")

    # 4. Guardar resultados
    print("Guardando archivos finales...")
    tree = ET.ElementTree(root)
    tree.write(OUTPUT_FILE, encoding='utf-8', xml_declaration=True)
    
    with gzip.open(OUTPUT_GZ, 'wb') as f:
        tree.write(f, encoding='utf-8', xml_declaration=True)

    # 5. Reporte de faltantes
    faltantes = whitelist - canales_encontrados
    with open(LOG_ERRORES, 'w', encoding='utf-8') as f:
        if faltantes:
            f.write("⚠️ CANALES NO ENCONTRADOS:\n")
            for c in sorted(faltantes): f.write(f"- {c}\n")
        else:
            f.write("✅ ¡Éxito! Guía completa.")
    print("¡Listo!")

if __name__ == "__main__":
    filter_epg()
