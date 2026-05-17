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

# --- CONFIGURACIÓN DE FUENTES ---
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
cache_tmdb = {}

def remover_tildes(texto):
    if not texto: return ""
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').lower()

def similar(a, b):
    a, b = remover_tildes(a), remover_tildes(b)
    if a == b or a in b or b in a: return 1.0
    return SequenceMatcher(None, a, b).ratio()

def formatear_descripcion_serie(texto):
    """
    Formato: S1 E3 | Título del capítulo.
    Mantiene el salto de línea para la sinopsis.
    """
    if not texto: return ""
    
    # Patrón para detectar códigos de temporada/episodio
    patron_code = r'([TS]\d+\s?[E]\d+)'
    match = re.search(patron_code, texto, re.IGNORECASE)
    
    if match:
        code = match.group().upper().strip()
        # Extraemos el resto y limpiamos basura como el guion largo (—)
        resto = texto.replace(match.group(), "").strip()
        resto = re.sub(r'^[:\-\s—]+', '', resto)
        
        # Si hay un salto de línea en la fuente original, lo respetamos
        if "\n" in resto:
            partes = resto.split("\n", 1)
            titulo_capitulo = partes[0].strip().replace(":", ".")
            sinopsis = partes[1].strip()
            # Retornamos con el punto después del título del capítulo y el salto de línea
            return f"{code} | {titulo_capitulo}.\n{sinopsis}"
        else:
            # Si no hay salto, solo aplicamos punto y barra
            resto = resto.replace(":", ".")
            return f"{code} | {resto}."
            
    return texto

def buscar_en_tmdb(titulo_original):
    if not TMDB_KEY or not titulo_original: return None, None, None
    query = re.sub(r'\(.*?\)|\[.*?\]', '', titulo_original).replace('|', '').strip()
    query_norm = remover_tildes(query)
    
    if query_norm in cache_tmdb: return cache_tmdb[query_norm]
    
    try:
        time.sleep(0.2)
        url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_KEY}&query={urllib.parse.quote(query)}&language=es-MX"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            results = r.json().get('results', [])
            for res in results[:3]:
                t_title = res.get('title') or res.get('name', '')
                t_desc = res.get('overview', '')
                date = res.get('release_date') or res.get('first_air_date') or ""
                year = date[:4] if len(date) >= 4 else ""
                if t_title and similar(query, t_title) > 0.45:
                    cache_tmdb[query_norm] = (t_title, t_desc, year)
                    return t_title, t_desc, year
    except: pass
    return None, None, None

def filter_epg():
    if not os.path.exists(CANALES_FILE): 
        print(f"Error: No se encuentra {CANALES_FILE}")
        return
    
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
    
    new_root = ET.Element('tv', {'generator-info-name': 'EPG Pro v10 Final'})
    canales_procesados = set()
    programas_procesados = set()

    for url in EPG_SOURCES:
        url_tag = url.lower()
        try:
            print(f"Descargando: {url.split('/')[-1]}")
            r = requests.get(url, timeout=45)
            if r.status_code != 200: continue
            
            content = r.content
            if url.endswith(".gz") or content[:2] == b'\x1f\x8b':
                content = gzip.decompress(content)
            
            try:
                temp_root = ET.fromstring(content)
            except: continue

            # Procesar canales
            for channel in temp_root.findall('channel'):
                cid = channel.get('id')
                if cid in whitelist and cid not in canales_procesados:
                    f_req = whitelist[cid]
                    if f_req and f_req not in url_tag: continue
                    new_root.append(channel)
                    canales_procesados.add(cid)

            # Procesar programas
            for prog in temp_root.findall('programme'):
                pid = prog.get('channel')
                start_time = prog.get('start')
                
                # Evitar duplicados si el programa ya se procesó para este canal/hora
                prog_id = f"{pid}_{start_time}"
                
                if pid in whitelist and prog_id not in programas_procesados:
                    f_req = whitelist[pid]
                    if f_req and f_req not in url_tag: continue
                    
                    t_elem = prog.find('title')
                    d_elem = prog.find('desc')
                    
                    if t_elem is not None:
                        orig_title = t_elem.text
                        orig_desc = d_elem.text if d_elem is not None else ""
                        
                        # Detectar si es una serie con episodio detallado
                        es_serie = re.search(r'[TS]\d+\s?[E]\d+', orig_desc, re.IGNORECASE)

                        # LÓGICA TMDB
                        if pid in tmdb_whitelist:
                            new_t, new_d, new_y = buscar_en_tmdb(orig_title)
                            if new_t:
                                # Agregamos año al título
                                t_elem.text = f"{new_t} ({new_y})" if new_y else new_t
                                # Solo usamos descripción de TMDB si la original está vacía o no es episodio específico
                                if not es_serie or not orig_desc:
                                    if d_elem is None: d_elem = ET.SubElement(prog, 'desc')
                                    d_elem.text = f"{new_d} [TMDB]"

                        # APLICAR FORMATEO DE SERIE (Punto, Barra y Salto de línea)
                        if d_elem is not None and d_elem.text:
                            d_elem.text = formatear_descripcion_serie(d_elem.text)

                    new_root.append(prog)
                    programas_procesados.add(prog_id)
            
            temp_root.clear()
        except Exception as e:
            print(f"Error procesando {url}: {e}")

    # Guardado final
    print(f"Guardando archivos en {OUTPUT_FILE}...")
    tree = ET.ElementTree(new_root)
    tree.write(OUTPUT_FILE, encoding='utf-8', xml_declaration=True)
    
    with gzip.open(OUTPUT_GZ, 'wb') as f:
        tree.write(f, encoding='utf-8', xml_declaration=True)
    
    print("¡Proceso completado con éxito!")

if __name__ == "__main__":
    filter_epg()
