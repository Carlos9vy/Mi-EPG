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

# Recuperar la API KEY de TMDB desde los Secrets de GitHub
TMDB_KEY = os.getenv('TMDB_API_KEY')

def apply_shift(timestr, hours_val):
    if not timestr or len(timestr) < 14: return timestr
    try:
        base_time = timestr[:14] 
        offset = timestr[15:]    
        dt = datetime.strptime(base_time, "%Y%m%d%H%M%S")
        total_minutes = float(hours_val) * 60
        new_dt = dt + timedelta(minutes=int(total_minutes))
        return new_dt.strftime("%Y%m%d%H%M%S") + " " + offset
    except:
        return timestr

def buscar_en_tmdb(titulo):
    """Busca la descripción de un programa en TMDB (Películas o Series)"""
    if not TMDB_KEY or not titulo:
        return None
    
    # Limpiar el título de caracteres que usamos para separar
    query = titulo.replace('|', '').strip()
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        # 1. Intentar buscar como Película
        url_movie = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_KEY}&query={query}&language=es-MX"
        r = requests.get(url_movie, headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data.get('results'):
                return data['results'][0].get('overview')
        
        # 2. Si no hay resultados, intentar como Serie (TV)
        url_tv = f"https://api.themoviedb.org/3/search/tv?api_key={TMDB_KEY}&query={query}&language=es-MX"
        r = requests.get(url_tv, headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data.get('results'):
                return data['results'][0].get('overview')
    except Exception as e:
        print(f"Error consultando TMDB: {e}")
        return None
    return None

def filter_epg():
    if not os.path.exists(CANALES_FILE): return

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
    root = ET.Element('tv', {'generator-info-name': 'EPG Pro + TMDB Experiment', 'generator-info-url': 'https://github.com'})

    for url in EPG_SOURCES:
        try:
            print(f"Procesando: {url}")
            r = requests.get(url, timeout=60)
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
                        # 1. Aplicar Shift
                        if pid in shifts:
                            elem.set('start', apply_shift(elem.get('start'), shifts[pid]))
                            elem.set('stop', apply_shift(elem.get('stop'), shifts[pid]))
                        
                        # 2. Obtener elementos
                        title_elem = elem.find('title')
                        category_elem = elem.find('category')
                        desc_elem = elem.find('desc')

                        # 3. EXPERIMENTO HBO.CO + TMDB
                        if pid == "HBO.co" and title_elem is not None:
                            info_tmdb = buscar_en_tmdb(title_elem.text)
                            if info_tmdb:
                                if desc_elem is None:
                                    desc_elem = ET.SubElement(elem, 'desc')
                                desc_elem.text = info_tmdb + " [TMDB]"

                        # 4. Corrección de Espacios
                        if title_elem is not None and title_elem.text:
                            t_text = title_elem.text.strip()
                            if not t_text.endswith((' ', '.', ':', '-', '!', '?')):
                                title_elem.text = t_text + " "

                        if category_elem is not None and category_elem.text:
                            c_text = category_elem.text.strip()
                            if not c_text.endswith((' ', '.', ':', '-')):
                                category_elem.text = c_text + " "

                        # 5. Limpieza para LG Netcast
                        for extra in ['credits', 'country', 'language', 'sub-title']:
                            target = elem.find(extra)
                            if target is not None: elem.remove(target)
                        
                        root.append(elem)

        except Exception as e:
            print(f"Falla en fuente {url}: {e}")

    # Guardar
    tree = ET.ElementTree(root)
    tree.write(OUTPUT_FILE, encoding='utf-8', xml_declaration=True)
    with gzip.open(OUTPUT_GZ, 'wb') as f:
        tree.write(f, encoding='utf-8', xml_declaration=True)

    faltantes = whitelist - canales_encontrados
    with open(LOG_ERRORES, 'w', encoding='utf-8') as f:
        f.write("⚠️ Faltantes:\n" + "\n".join(sorted(faltantes)) if faltantes else "✅ Éxito")

if __name__ == "__main__":
    filter_epg()
