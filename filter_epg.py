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

def es_ingles(texto):
    if not texto: return False
    palabras_en = {'the', 'and', 'with', 'from', 'season', 'episode', 'series'}
    palabras_texto = set(re.findall(r'\b\w+\b', texto.lower()))
    return len(palabras_texto.intersection(palabras_en)) > 2

def remover_tildes(texto):
    if not texto: return ""
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').lower()

def similar(a, b):
    a, b = remover_tildes(a), remover_tildes(b)
    if a == b or a in b or b in a: return 1.0
    return SequenceMatcher(None, a, b).ratio()

def formatear_descripcion_quirurgica(texto):
    """
    Formatea el contenido extraído de <desc>.
    Solo añade punto a la primera línea si hay un salto de línea posterior.
    """
    if not texto: return ""
    
    # Limpiamos espacios basura al inicio/final pero mantenemos saltos internos
    texto = texto.strip()
    
    # Manejo de Series con código (S1 E3 | Título.)
    patron_code = r'([TS]\d+\s?[E]\d+)'
    match = re.search(patron_code, texto, re.IGNORECASE)
    
    if match:
        code = match.group().upper().strip()
        resto = texto.replace(match.group(), "").strip()
        resto = re.sub(r'^[:\-\s—]+', '', resto)
        
        if "\n" in resto:
            partes = resto.split("\n", 1)
            encabezado = partes[0].strip()
            # Si el encabezado no tiene punto, se lo ponemos
            if encabezado and not encabezado.endswith(('.', ':', '!', '?')):
                encabezado += "."
            return f"{code} | {encabezado}\n{partes[1].strip()}"
        else:
            if resto and not resto.endswith(('.', ':', '!', '?')):
                resto += "."
            return f"{code} | {resto}"

    # Manejo de Magacines/Otros (Primera línea sin código)
    if "\n" in texto:
        partes = texto.split("\n", 1)
        primera_linea = partes[0].strip()
        # Solo ponemos punto si es una línea corta (encabezado) y no tiene puntuación
        if primera_linea and not primera_linea.endswith(('.', ':', '!', '?')):
            primera_linea += "."
        return f"{primera_linea}\n{partes[1].strip()}"
    
    return texto

def buscar_en_tmdb(lista_titulos):
    if not TMDB_KEY or not lista_titulos: return None, None, None
    for titulo in lista_titulos:
        if not titulo: continue
        query = re.sub(r'\(.*?\)|\[.*?\]', '', titulo).replace('|', '').strip()
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
                    if es_ingles(t_desc): t_desc = ""
                    date = res.get('release_date') or res.get('first_air_date') or ""
                    year = date[:4] if len(date) >= 4 else ""
                    if t_title and similar(query, t_title) > 0.45:
                        cache_tmdb[query_norm] = (t_title, t_desc, year)
                        return t_title, t_desc, year
        except: continue
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
    new_root = ET.Element('tv', {'generator-info-name': 'EPG Pro v10 Final'})
    canales_procesados = set()
    programas_procesados = set()

    for url in EPG_SOURCES:
        url_tag = url.lower()
        try:
            r = requests.get(url, timeout=45)
            if r.status_code != 200: continue
            content = r.content
            if url.endswith(".gz") or content[:2] == b'\x1f\x8b':
                content = gzip.decompress(content)
            temp_root = ET.fromstring(content)

            for channel in temp_root.findall('channel'):
                cid = channel.get('id')
                if cid in whitelist and cid not in canales_procesados:
                    f_req = whitelist[cid]
                    if f_req and f_req not in url_tag: continue
                    new_root.append(channel)
                    canales_procesados.add(cid)

            for prog in temp_root.findall('programme'):
                pid = prog.get('channel')
                start_time = prog.get('start')
                prog_id = f"{pid}_{start_time}"
                
                if pid in whitelist and prog_id not in programas_procesados:
                    f_req = whitelist[pid]
                    if f_req and f_req not in url_tag: continue
                    
                    titulos_disponibles = [t.text for t in prog.findall('title') if t.text]
                    d_elem = prog.find('desc') # AQUÍ TRABAJAMOS ESPECÍFICAMENTE CON LA DESCRIPCIÓN
                    
                    if titulos_disponibles:
                        orig_desc = d_elem.text if d_elem is not None else ""
                        es_serie_original = re.search(r'[TS]\d+\s?[E]\d+', orig_desc, re.IGNORECASE)

                        if pid in tmdb_whitelist:
                            new_t, new_d, new_y = buscar_en_tmdb(titulos_disponibles)
                            if new_t:
                                main_title_elem = prog.find('title')
                                main_title_elem.text = f"{new_t} ({new_y})" if new_y else new_t
                                
                                tmdb_es_especifica = re.search(r'[TS]\d+\s?[E]\d+', new_d, re.IGNORECASE) if new_d else False
                                
                                if new_d:
                                    if tmdb_es_especifica:
                                        if d_elem is None: d_elem = ET.SubElement(prog, 'desc')
                                        d_elem.text = f"{new_d} [TMDB]"
                                    elif not es_serie_original:
                                        if d_elem is None: d_elem = ET.SubElement(prog, 'desc')
                                        d_elem.text = f"{new_d} [TMDB]"

                        # Aplicamos el formato solo al contenido de <desc>
                        if d_elem is not None and d_elem.text:
                            d_elem.text = formatear_descripcion_quirurgica(d_elem.text)

                    new_root.append(prog)
                    programas_procesados.add(prog_id)
            temp_root.clear()
        except: pass

    tree = ET.ElementTree(new_root)
    tree.write(OUTPUT_FILE, encoding='utf-8', xml_declaration=True)
    with gzip.open(OUTPUT_GZ, 'wb') as f:
        tree.write(f, encoding='utf-8', xml_declaration=True)
    print("EPG lista con corrección específica en descripciones.")

if __name__ == "__main__":
    filter_epg()
