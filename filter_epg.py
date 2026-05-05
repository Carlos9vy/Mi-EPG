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

def validar_descripciones(desc_orig, desc_tmdb):
    """Compara si ambas descripciones comparten palabras clave importantes"""
    if not desc_orig or not desc_tmdb: return False
    
    # Limpiamos y sacamos palabras de más de 4 letras
    palabras_orig = set(re.findall(r'\w{5,}', desc_orig.lower()))
    palabras_tmdb = set(re.findall(r'\w{5,}', desc_tmdb.lower()))
    
    if not palabras_orig: return True # Si el original no tiene descripción, dejamos pasar
    
    # Vemos cuántas palabras coinciden
    coincidencias = palabras_orig.intersection(palabras_tmdb)
    
    # Si comparten al menos 2 palabras clave, es muy probable que sea la misma película
    return len(coincidencias) >= 2

def apply_shift(timestr, hours_val):
    if not timestr or len(timestr) < 14: return timestr
    try:
        base_time = timestr[:14] 
        offset = timestr[15:]    
        dt = datetime.strptime(base_time, "%Y%m%d%H%M%S")
        new_dt = dt + timedelta(minutes=int(float(hours_val) * 60))
        return new_dt.strftime("%Y%m%d%H%M%S") + " " + offset
    except: return timestr

def buscar_en_tmdb(titulo_original, desc_original=""):
    if not TMDB_KEY or not titulo_original: return None, None
    query = re.sub(r'\(.*?\)|\[.*?\]', '', titulo_original).replace('|', '').strip()
    if query in cache_tmdb: return cache_tmdb[query]
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        time.sleep(0.1)
        url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_KEY}&query={urllib.parse.quote(query)}&language=es-MX"
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            results = r.json().get('results', [])
            for res in results[:3]: # Analizamos los 3 primeros para buscar el match de descripción
                t_title = res.get('title') or res.get('name', '')
                t_desc = res.get('overview', '')
                
                if not t_title or not t_desc: continue

                # VALIDACIÓN 1: El título debe parecerse
                titulos_parecidos = similar(query, t_title) > 0.4
                
                # VALIDACIÓN 2: Las descripciones deben hablar de lo mismo
                descripciones_coinciden = validar_descripciones(desc_original, t_desc)

                if titulos_parecidos and descripciones_coinciden:
                    # Filtro extra: Si el original NO dice Maze Runner, el resultado NO debe decir Maze Runner
                    if "maze runner" in t_title.lower() and "maze runner" not in query.lower():
                        continue
                        
                    cache_tmdb[query] = (t_title, t_desc)
                    return t_title, t_desc
    except: pass
    return None, None

def filter_epg():
    if not os.path.exists(CANALES_FILE): return

    with open(CANALES_FILE, 'r', encoding='utf-8') as f:
        whitelist = set(line.strip() for line in f if line.strip())
    
    tmdb_whitelist = set()
    if os.path.exists(TMDB_CHANNELS_FILE):
        with open(TMDB_CHANNELS_FILE, 'r', encoding='utf-8') as f:
            tmdb_whitelist = set(line.strip() for line in f if line.strip())

    shifts = {}
    if os.path.exists(SHIFT_FILE):
        with open(SHIFT_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if ',' in line:
                    cid, val = line.strip().split(',')
                    shifts[cid.strip()] = val.strip()

    new_root = ET.Element('tv', {'generator-info-name': 'EPG Pro Ultra Validated'})
    canales_procesados = set()

    for url in EPG_SOURCES:
        try:
            print(f"Leyendo: {url.split('/')[-1]}")
            r = requests.get(url, timeout=60)
            data = gzip.decompress(r.content) if (url.endswith(".gz") or r.content[:2] == b'\x1f\x8b') else r.content
            temp_root = ET.fromstring(data)

            for channel in temp_root.findall('channel'):
                cid = channel.get('id')
                if cid in whitelist and cid not in canales_procesados:
                    new_root.append(channel)
                    canales_procesados.add(cid)

            for prog in temp_root.findall('programme'):
                pid = prog.get('channel')
                if pid in whitelist:
                    if pid in shifts:
                        prog.set('start', apply_shift(prog.get('start'), shifts[pid]))
                        prog.set('stop', apply_shift(prog.get('stop'), shifts[pid]))

                    if pid in tmdb_whitelist:
                        t_elem = prog.find('title')
                        d_elem = prog.find('desc')
                        
                        if t_elem is not None and t_elem.text:
                            orig_title = t_elem.text
                            orig_desc = d_elem.text if d_elem is not None else ""
                            
                            # Enviamos título Y descripción para validar
                            new_t, new_d = buscar_en_tmdb(orig_title, orig_desc)
                            
                            if new_d:
                                t_elem.text = new_t
                                if d_elem is None: d_elem = ET.SubElement(prog, 'desc')
                                d_elem.text = new_d + " [TMDB]"

                    for tag in ['credits', 'country', 'language', 'sub-title']:
                        extra = prog.find(tag)
                        if extra is not None: prog.remove(extra)
                    
                    new_root.append(prog)
            
            temp_root.clear()
        except Exception as e:
            print(f"Error: {e}")

    tree = ET.ElementTree(new_root)
    tree.write(OUTPUT_FILE, encoding='utf-8', xml_declaration=True)
    with gzip.open(OUTPUT_GZ, 'wb') as f:
        tree.write(f, encoding='utf-8', xml_declaration=True)
    print("Finalizado con validación cruzada.")

if __name__ == "__main__":
    filter_epg()
