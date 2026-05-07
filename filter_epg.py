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

# --- TUS 20 FUENTES ---
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
TMDB_CHANNELS_FILE = "tmdb_channels.txt"
OUTPUT_FILE = "epg_reducida.xml"
OUTPUT_GZ = "epg_reducida.xml.gz"
TMDB_KEY = os.getenv('TMDB_API_KEY')

def formatear_descripcion_serie(texto):
    if not texto: return ""
    
    # Buscamos S1 E3, T2 E10, etc.
    patron_code = r'([TS]\d+\s?[E]\d+)'
    match = re.search(patron_code, texto, re.IGNORECASE)
    
    if match:
        code = match.group().strip()
        # Quitamos el código y limpiamos guiones extra al inicio
        resto = texto.replace(code, "").strip()
        resto = re.sub(r'^[—\-\s]+', '', resto)
        
        if resto:
            # Dividimos por el salto de línea para procesar solo la primera parte
            partes = resto.split('\n', 1)
            titulo_capitulo = partes[0].strip()
            
            # Agregamos el punto si no lo tiene
            if titulo_capitulo and not titulo_capitulo.endswith('.'):
                titulo_capitulo += "."
            
            # Si hay una descripción debajo, mantenemos el salto de línea (\n)
            if len(partes) > 1:
                return f"{code} | {titulo_capitulo}\n{partes[1].strip()}"
            else:
                return f"{code} | {titulo_capitulo}"
                
    return texto

def buscar_en_tmdb(titulo_original):
    if not TMDB_KEY or not titulo_original: return None, None, None
    query = re.sub(r'\(.*?\)|\[.*?\]', '', titulo_original).replace('|', '').strip()
    try:
        url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_KEY}&query={urllib.parse.quote(query)}&language=es-MX"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            results = r.json().get('results', [])
            for res in results[:1]:
                t_title = res.get('title') or res.get('name', '')
                t_desc = res.get('overview', '')
                date = res.get('release_date') or res.get('first_air_date') or ""
                year = date[:4] if len(date) >= 4 else ""
                return t_title, t_desc, year
    except: pass
    return None, None, None

def filter_epg():
    if not os.path.exists(CANALES_FILE): return
    
    whitelist = {}
    with open(CANALES_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            match = re.match(r'(.+?)\s*\((.+?)\)', line)
            if match:
                cid, f_req = match.groups()
                whitelist[cid.strip()] = f_req.strip().lower()
            else:
                whitelist[line] = None

    tmdb_whitelist = set(line.strip() for line in (open(TMDB_CHANNELS_FILE, 'r', encoding='utf-8') if os.path.exists(TMDB_CHANNELS_FILE) else []))
    
    new_root = ET.Element('tv', {'generator-info-name': 'EPG Pro v12 Final-Style'})
    canales_procesados = set()
    canales_con_programas = set()

    for url in EPG_SOURCES:
        url_tag = url.lower()
        try:
            print(f"Descargando: {url.split('/')[-1]}")
            r = requests.get(url, timeout=45)
            if r.status_code != 200: continue
            data = gzip.decompress(r.content) if (url.endswith(".gz") or r.content[:2] == b'\x1f\x8b') else r.content
            temp_root = ET.fromstring(data)

            for channel in temp_root.findall('channel'):
                cid = channel.get('id')
                if cid in whitelist and cid not in canales_procesados:
                    f_req = whitelist[cid]
                    if f_req and f_req not in url_tag: continue
                    new_root.append(channel)
                    canales_procesados.add(cid)

            for prog in temp_root.findall('programme'):
                pid = prog.get('channel')
                if pid in whitelist:
                    f_req = whitelist[pid]
                    if f_req:
                        if f_req not in url_tag: continue
                    elif pid in canales_con_programas:
                        continue
                    
                    t_elem = prog.find('title')
                    d_elem = prog.find('desc')
                    
                    if t_elem is not None:
                        orig_title = t_elem.text
                        if pid in tmdb_whitelist:
                            new_t, new_d, new_y = buscar_en_tmdb(orig_title)
                            if new_t:
                                t_elem.text = f"{new_t} ({new_y})" if new_y else new_t
                                if d_elem is None: d_elem = ET.SubElement(prog, 'desc')
                                if not d_elem.text or "[TMDB]" not in d_elem.text:
                                    d_elem.text = f"{new_d} [TMDB]"

                        if d_elem is not None and d_elem.text:
                            d_elem.text = formatear_descripcion_serie(d_elem.text)

                    new_root.append(prog)
                    canales_con_programas.add(pid)
            
            temp_root.clear()
        except: pass

    tree = ET.ElementTree(new_root)
    tree.write(OUTPUT_FILE, encoding='utf-8', xml_declaration=True)
    with gzip.open(OUTPUT_GZ, 'wb') as f:
        tree.write(f, encoding='utf-8', xml_declaration=True)
    print("Hecho.")

if __name__ == "__main__":
    filter_epg()
