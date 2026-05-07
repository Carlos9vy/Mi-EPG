import xml.etree.ElementTree as ET
import requests
import os
import gzip
import io
import time
import re
import urllib.parse
import unicodedata
from datetime import datetime, timedelta
from difflib import SequenceMatcher

# --- CONFIGURACIÓN DE FUENTES (20 FUENTES) ---
EPG_SOURCES = [
    "https://iptv-epg.org/files/epg-ar.xml",
    "https://iptv-epg.org/files/epg-cl.xml",
    "https://iptv-epg.org/files/epg-co.xml",
    "https://iptv-epg.org/files/epg-ec.xml",
    "https://iptv-epg.org/files/epg-mx.xml",
    "https://iptv-epg.org/files/epg-pe.xml",
    "https://iptv-epg.org/files/epg-es.xml",
    "https://iptv-epg.org/files/epg-us.xml",
    "https://iptv-epg.org/files/epg-uy.xml",
    "https://iptv-epg.org/files/epg-ve.xml",
    "https://iptv-epg.org/files/epg-bo.xml",
    "https://iptv-epg.org/files/epg-cr.xml",
    "https://iptv-epg.org/files/epg-do.xml",
    "https://iptv-epg.org/files/epg-sv.xml",
    "https://iptv-epg.org/files/epg-gt.xml",
    "https://iptv-epg.org/files/epg-hn.xml",
    "https://iptv-epg.org/files/epg-py.xml",
    "https://iptv-epg.org/files/epg-pa.xml",
    "https://www.open-epg.com/generate/aYzuzNSenh.xml",
    "https://epgshare01.online/epgshare01/epg_ripper_SV1.xml.gz"
]

CANALES_FILE = "canales.txt"
SHIFT_FILE = "shift.txt"
TMDB_CHANNELS_FILE = "tmdb_channels.txt"
OUTPUT_FILE = "epg_reducida.xml"
OUTPUT_GZ = "epg_reducida.xml.gz"

TMDB_KEY = os.getenv('TMDB_API_KEY')
cache_tmdb = {}

# --- FUNCIONES DE LÓGICA ---

def remover_tildes(texto):
    if not texto: return ""
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').lower()

def similar(a, b):
    a, b = remover_tildes(a), remover_tildes(b)
    if a in b or b in a: return 1.0
    return SequenceMatcher(None, a, b).ratio()

def formatear_descripcion_serie(texto):
    if not texto: return ""
    patron_code = r'([TS]\d+\s?[E]\d+)'
    match = re.search(patron_code, texto, re.IGNORECASE)
    if match:
        code = match.group().strip()
        resto = texto.replace(code, "").strip()
        if resto:
            partes = re.split(r'\s\s+|\n', resto, 1)
            if len(partes) > 1:
                return f"{code} | {partes[0].strip()}. {partes[1].strip()}"
            else:
                return f"{code} | {resto}"
    return texto

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
    if not TMDB_KEY or not titulo_original: return None, None, None
    query = re.sub(r'\(.*?\)|\[.*?\]', '', titulo_original).replace('|', '').strip()
    query_norm = remover_tildes(query)
    if query_norm in cache_tmdb: return cache_tmdb[query_norm]
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        time.sleep(0.15)
        url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_KEY}&query={urllib.parse.quote(query)}&language=es-MX"
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            results = r.json().get('results', [])
            for res in results[:3]:
                t_title = res.get('title') or res.get('name', '')
                t_desc = res.get('overview', '')
                release_date = res.get('release_date') or res.get('first_air_date') or ""
                year = release_date[:4] if len(release_date) >= 4 else ""
                if not t_title or not t_desc: continue
                if "maze runner" in t_title.lower() and "maze runner" not in query.lower(): continue
                if similar(query, t_title) > 0.45:
                    cache_tmdb[query_norm] = (t_title, t_desc, year)
                    return t_title, t_desc, year
    except: pass
    return None, None, None

def filter_epg():
    if not os.path.exists(CANALES_FILE): return

    # Carga de canales con soporte para direccionamiento: id (fuente)
    whitelist = {}
    with open(CANALES_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            match = re.match(r'(.+?)\s*\((.+?)\)', line)
            if match:
                cid, fuente = match.groups()
                whitelist[cid.strip()] = fuente.strip().lower()
            else:
                whitelist[line] = None

    tmdb_whitelist = set(line.strip() for line in (open(TMDB_CHANNELS_FILE, 'r', encoding='utf-8') if os.path.exists(TMDB_CHANNELS_FILE) else []))

    shifts = {}
    if os.path.exists(SHIFT_FILE):
        for line in open(SHIFT_FILE, 'r', encoding='utf-8'):
            if ',' in line:
                cid, val = line.strip().split(',')
                shifts[cid.strip()] = val.strip()

    new_root = ET.Element('tv', {'generator-info-name': 'EPG Pro Ultra Hybrid v9'})
    canales_procesados = set()

    for url in EPG_SOURCES:
        url_tag = url.lower()
        try:
            print(f"Descargando: {url.split('/')[-1]}")
            r = requests.get(url, timeout=45)
            if r.status_code != 200: continue

            data = gzip.decompress(r.content) if (url.endswith(".gz") or r.content[:2] == b'\x1f\x8b') else r.content
            
            try:
                temp_root = ET.fromstring(data)
            except ET.ParseError:
                print(f"  Error XML en {url.split('/')[-1]}. Saltando.")
                continue

            # 1. Filtrar Canales
            for channel in temp_root.findall('channel'):
                cid = channel.get('id')
                if cid in whitelist and cid not in canales_procesados:
                    fuente_req = whitelist[cid]
                    if fuente_req and fuente_req not in url_tag: continue
                    
                    new_root.append(channel)
                    canales_procesados.add(cid)

            # 2. Filtrar Programas
            for prog in temp_root.findall('programme'):
                pid = prog.get('channel')
                if pid in whitelist:
                    fuente_req = whitelist[pid]
                    
                    # Si pedimos fuente específica y no es esta, saltar
                    if fuente_req and fuente_req not in url_tag: continue
                    
                    # Si ya lo procesamos en otra fuente y no es la específica pedida, saltar
                    if pid in canales_procesados and not (fuente_req and fuente_req in url_tag):
                        continue

                    if pid in shifts:
                        prog.set('start', apply_shift(prog.get('start'), shifts[pid]))
                        prog.set('stop', apply_shift(prog.get('stop'), shifts[pid]))

                    t_elem = prog.find('title')
                    d_elem = prog.find('desc')
                    
                    if t_elem is not None:
                        orig_title = t_elem.text
                        orig_desc = d_elem.text if d_elem is not None else ""

                        if pid in tmdb_whitelist:
                            new_t, new_d, new_y = buscar_en_tmdb(orig_title)
                            if new_t:
                                t_elem.text = f"{new_t} ({new_y})" if new_y else new_t
                                if not re.search(r'[TS]\d+\s?[E]\d+', orig_desc, re.IGNORECASE):
                                    if d_elem is None: d_elem = ET.SubElement(prog, 'desc')
                                    d_elem.text = f"{new_d} [TMDB]"
                        
                        if d_elem is not None and d_elem.text:
                            d_elem.text = formatear_descripcion_serie(d_elem.text)

                    for tag in ['credits', 'country', 'language', 'sub-title']:
                        extra = prog.find(tag)
                        if extra is not None: prog.remove(extra)
                    
                    new_root.append(prog)
            temp_root.clear()
        except Exception as e: print(f"  Error: {e}")

    tree = ET.ElementTree(new_root)
    tree.write(OUTPUT_FILE, encoding='utf-8', xml_declaration=True)
    with gzip.open(OUTPUT_GZ, 'wb') as f:
        tree.write(f, encoding='utf-8', xml_declaration=True)
    print("¡Proceso completado!")

if __name__ == "__main__":
    filter_epg()
