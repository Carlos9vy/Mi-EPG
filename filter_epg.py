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
    a, b = str(a).lower(), str(b).lower()
    if a in b or b in a: return 1.0
    return SequenceMatcher(None, a, b).ratio()

def apply_shift(timestr, hours_val):
    if not timestr or len(timestr) < 14: return timestr
    try:
        base_time = timestr[:14] 
        offset = timestr[15:]    
        dt = datetime.strptime(base_time, "%Y%m%d%H%M%S")
        new_dt = dt + timedelta(minutes=int(float(hours_val) * 60))
        return new_dt.strftime("%Y%m%d%H%M%S") + " " + offset
    except: return timestr

def buscar_en_tmdb(titulo_original):
    if not TMDB_KEY or not titulo_original: return None, None
    query = re.sub(r'\(.*?\)|\[.*?\]', '', titulo_original).replace('|', '').strip()
    if query in cache_tmdb: return cache_tmdb[query]
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        time.sleep(0.15)
        url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_KEY}&query={urllib.parse.quote(query)}&language=es-MX"
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            results = r.json().get('results')
            for res in results[:3]:
                t_title = res.get('title') or res.get('name')
                t_desc = res.get('overview')
                if t_title and t_desc and len(t_desc) > 10:
                    if similar(query, t_title) > 0.4: # Bajamos el umbral para asegurar que entre
                        cache_tmdb[query] = (t_title, t_desc)
                        return t_title, t_desc
    except: pass
    return None, None

def filter_epg():
    if not os.path.exists(CANALES_FILE): return

    # Cargar archivos de configuración con limpieza de espacios
    with open(CANALES_FILE, 'r', encoding='utf-8') as f:
        whitelist = [line.strip() for line in f if line.strip()]
    
    tmdb_whitelist = []
    if os.path.exists(TMDB_CHANNELS_FILE):
        with open(TMDB_CHANNELS_FILE, 'r', encoding='utf-8') as f:
            tmdb_whitelist = [line.strip() for line in f if line.strip()]

    shifts = {}
    if os.path.exists(SHIFT_FILE):
        with open(SHIFT_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if ',' in line:
                    cid, val = line.strip().split(',')
                    shifts[cid.strip()] = val.strip()

    # Nodo raíz de la nueva EPG
    new_root = ET.Element('tv', {'generator-info-name': 'EPG Pro Ultra v4'})
    canales_procesados = set()

    for url in EPG_SOURCES:
        try:
            print(f"Procesando: {url.split('/')[-1]}")
            r = requests.get(url, timeout=60)
            data = gzip.decompress(r.content) if (url.endswith(".gz") or r.content[:2] == b'\x1f\x8b') else r.content
            
            # CARGA COMPLETA EN MEMORIA (Evita errores de guardado)
            temp_root = ET.fromstring(data)

            # 1. Copiar Canales
            for channel in temp_root.findall('channel'):
                cid = channel.get('id')
                if cid in whitelist and cid not in canales_procesados:
                    new_root.append(channel)
                    canales_procesados.add(cid)

            # 2. Copiar y Modificar Programas
            for prog in temp_root.findall('programme'):
                pid = prog.get('channel')
                if pid in whitelist:
                    # Ajuste de hora
                    if pid in shifts:
                        prog.set('start', apply_shift(prog.get('start'), shifts[pid]))
                        prog.set('stop', apply_shift(prog.get('stop'), shifts[pid]))

                    # Lógica TMDB
                    if pid in tmdb_whitelist:
                        t_elem = prog.find('title')
                        d_elem = prog.find('desc')
                        
                        orig_title = t_elem.text if t_elem is not None else ""
                        orig_desc = d_elem.text if d_elem is not None else ""

                        # Si la descripción es corta o nula, buscamos
                        if len(orig_desc) < 150: 
                            new_t, new_d = buscar_en_tmdb(orig_title)
                            if new_d:
                                if t_elem is not None: t_elem.text = new_t
                                if d_elem is None: d_elem = ET.SubElement(prog, 'desc')
                                d_elem.text = new_d + " [TMDB]"
                    
                    # Limpieza de etiquetas basura
                    for tag in ['credits', 'country', 'language', 'sub-title']:
                        extra = prog.find(tag)
                        if extra is not None: prog.remove(extra)
                    
                    new_root.append(prog)
            
            # Limpiar memoria de la fuente actual
            temp_root.clear()

        except Exception as e:
            print(f" Error: {e}")

    # Guardar archivos
    tree = ET.ElementTree(new_root)
    tree.write(OUTPUT_FILE, encoding='utf-8', xml_declaration=True)
    with gzip.open(OUTPUT_GZ, 'wb') as f:
        tree.write(f, encoding='utf-8', xml_declaration=True)
    print("¡EPG finalizada con éxito!")

if __name__ == "__main__":
    filter_epg()
