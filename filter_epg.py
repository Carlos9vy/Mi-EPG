import xml.etree.ElementTree as ET
import requests
import os
import gzip
import re
import urllib.parse
import unicodedata
from datetime import datetime, timedelta

# --- CONFIGURACIÓN ---
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
    patron_code = r'([TS]\d+\s?[E]\d+)'
    match = re.search(patron_code, texto, re.IGNORECASE)
    if match:
        code = match.group().strip()
        resto = texto.replace(code, "").strip()
        resto = re.sub(r'^[—\-\s]+', '', resto)
        if resto:
            partes = resto.split('\n', 1)
            titulo_capitulo = partes[0].strip()
            if titulo_capitulo and not titulo_capitulo.endswith('.'):
                titulo_capitulo += "."
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
            if results:
                res = results[0]
                t_title = res.get('title') or res.get('name', '')
                t_desc = res.get('overview', '')
                date = res.get('release_date') or res.get('first_air_date') or ""
                year = date[:4] if len(date) >= 4 else ""
                return t_title, t_desc, year
    except: pass
    return None, None, None

def filter_epg():
    if not os.path.exists(CANALES_FILE):
        print("ERROR: No existe canales.txt")
        return
    
    # Cargar lista de canales
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
    
    print(f"INFO: {len(whitelist)} canales cargados desde canales.txt")
    
    tmdb_list = []
    if os.path.exists(TMDB_CHANNELS_FILE):
        with open(TMDB_CHANNELS_FILE, 'r', encoding='utf-8') as f:
            tmdb_list = [l.strip() for l in f if l.strip()]

    new_root = ET.Element('tv', {'generator-info-name': 'EPG_Carlos_v14'})
    canales_agregados = set()
    programas_agregados = set() # Control para no repetir programas del mismo canal

    for url in EPG_SOURCES:
        print(f"--- Procesando: {url.split('/')[-1]} ---")
        try:
            r = requests.get(url, timeout=60)
            if r.status_code != 200:
                print(f"Error {r.status_code}")
                continue
            
            content = r.content
            if url.endswith(".gz") or content[:2] == b'\x1f\x8b':
                content = gzip.decompress(content)
            
            temp_root = ET.fromstring(content)
            
            # Canales
            for channel in temp_root.findall('channel'):
                cid = channel.get('id')
                if cid in whitelist and cid not in canales_agregados:
                    f_req = whitelist[cid]
                    if f_req and f_req not in url.lower(): continue
                    new_root.append(channel)
                    canales_agregados.add(cid)

            # Programas
            count = 0
            for prog in temp_root.findall('programme'):
                pid = prog.get('channel')
                if pid in whitelist:
                    f_req = whitelist[pid]
                    # Si ya tenemos programas para este canal, solo aceptamos más si es la fuente específica
                    if pid in programas_agregados and not f_req:
                        continue
                    if f_req and f_req not in url.lower():
                        continue
                    
                    # Aplicar TMDB y Formato
                    t_elem = prog.find('title')
                    d_elem = prog.find('desc')
                    if t_elem is not None:
                        if pid in tmdb_list:
                            nt, nd, ny = buscar_en_tmdb(t_elem.text)
                            if nt:
                                t_elem.text = f"{nt} ({ny})" if ny else nt
                                if d_elem is None: d_elem = ET.SubElement(prog, 'desc')
                                d_elem.text = f"{nd} [TMDB]"
                        
                        if d_elem is not None and d_elem.text:
                            d_elem.text = formatear_descripcion_serie(d_elem.text)

                    new_root.append(prog)
                    programas_agregados.add(pid)
                    count += 1
            print(f"Agregados {count} programas.")

        except Exception as e:
            print(f"Error en fuente: {e}")

    # Guardar
    ET.ElementTree(new_root).write(OUTPUT_FILE, encoding='utf-8', xml_declaration=True)
    with gzip.open(OUTPUT_GZ, 'wb') as f:
        f.write(ET.tostring(new_root, encoding='utf-8'))
    
    print(f"FIN: {len(canales_agregados)} canales con guía.")

if __name__ == "__main__":
    filter_epg()
