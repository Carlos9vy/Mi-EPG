import xml.etree.ElementTree as ET
import requests
import os
import gzip
import io
import time
import re
import urllib.parse
from datetime import datetime, timedelta
from difflib import SequenceMatcher

# Fuentes
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
TMDB_CHANNELS_FILE = "tmdb_channels.txt"
OUTPUT_FILE = "epg_reducida.xml"
OUTPUT_GZ = "epg_reducida.xml.gz"

TMDB_KEY = os.getenv('TMDB_API_KEY')
cache_tmdb = {}

def similar(a, b):
    """Compara si una cadena está contenida en la otra o viceversa para mayor flexibilidad"""
    a, b = a.lower(), b.lower()
    if a in b or b in a: return 1.0 # Si una contiene a la otra, es match perfecto para nosotros
    return SequenceMatcher(None, a, b).ratio()

def apply_shift(timestr, hours_val):
    if not timestr or len(timestr) < 14: return timestr
    try:
        base_time = timestr[:14] 
        offset = timestr[15:]    
        dt = datetime.strptime(base_time, "%Y%m%d%H%M%S")
        total_minutes = float(hours_val) * 60
        new_dt = dt + timedelta(minutes=int(total_minutes))
        return new_dt.strftime("%Y%m%d%H%M%S") + " " + offset
    except: return timestr

def buscar_en_tmdb(titulo_original):
    if not TMDB_KEY or not titulo_original: return None, None
    
    # Limpieza: quitar (2024), [HD], etc.
    query = re.sub(r'\(.*?\)|\[.*?\]', '', titulo_original).replace('|', '').strip()
    if query in cache_tmdb: return cache_tmdb[query]
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        time.sleep(0.1)
        # Usamos search/multi para capturar tanto series como películas
        url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_KEY}&query={urllib.parse.quote(query)}&language=es-MX"
        r = requests.get(url, headers=headers, timeout=10)
        
        if r.status_code == 200:
            results = r.json().get('results')
            if results:
                # Buscamos el mejor match en los primeros 3 resultados
                for res in results[:3]:
                    tmdb_title = res.get('title') or res.get('name')
                    tmdb_desc = res.get('overview')
                    
                    if tmdb_title and tmdb_desc and len(tmdb_desc) > 20:
                        # Si el título se parece al menos un 50% o uno contiene al otro
                        if similar(query, tmdb_title) > 0.5:
                            data = (tmdb_title, tmdb_desc)
                            cache_tmdb[query] = data
                            return data
    except: pass
    return None, None

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

    tmdb_whitelist = set()
    if os.path.exists(TMDB_CHANNELS_FILE):
        with open(TMDB_CHANNELS_FILE, 'r', encoding='utf-8') as f:
            tmdb_whitelist = set(line.strip() for line in f if line.strip())

    canales_encontrados = set()
    root = ET.Element('tv', {'generator-info-name': 'EPG Pro Ultra v3', 'generator-info-url': 'https://github.com'})

    for url in EPG_SOURCES:
        try:
            print(f"Leyendo fuente: {url}")
            r = requests.get(url, timeout=60)
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
                        if pid in shifts:
                            elem.set('start', apply_shift(elem.get('start'), shifts[pid]))
                            elem.set('stop', apply_shift(elem.get('stop'), shifts[pid]))
                        
                        title_elem = elem.find('title')
                        desc_elem = elem.find('desc')
                        
                        # LÓGICA DE SUSTITUCIÓN
                        if pid in tmdb_whitelist and title_elem is not None:
                            original_title = title_elem.text
                            original_desc = desc_elem.text if desc_elem is not None else ""
                            
                            # Forzamos búsqueda si la descripción es corta o genérica
                            if len(original_desc) < 100 or original_desc.strip().lower() == original_title.strip().lower():
                                oficial_title, oficial_desc = buscar_en_tmdb(original_title)
                                if oficial_desc:
                                    title_elem.text = oficial_title
                                    if desc_elem is None:
                                        desc_elem = ET.SubElement(elem, 'desc')
                                    desc_elem.text = oficial_desc + " [TMDB]"
                        
                        # Limpieza
                        for extra in ['credits', 'country', 'language', 'sub-title']:
                            target = elem.find(extra)
                            if target is not None: elem.remove(target)
                        
                        root.append(elem)
        except Exception as e:
            print(f" Error: {e}")

    tree = ET.ElementTree(root)
    tree.write(OUTPUT_FILE, encoding='utf-8', xml_declaration=True)
    with gzip.open(OUTPUT_GZ, 'wb') as f:
        tree.write(f, encoding='utf-8', xml_declaration=True)

if __name__ == "__main__":
    filter_epg()
