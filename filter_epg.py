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
OUTPUT_FILE = "epg_reducida.xml"
OUTPUT_GZ = "epg_reducida.xml.gz"

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
    
    # Texto simple sin saltos
    if texto and not texto.endswith(('.', ':', '!', '?')):
        texto += "."
    return texto

def filter_epg():
    if not os.path.exists(CANALES_FILE): 
        print(f"Error: No se encuentra el archivo {CANALES_FILE}")
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

            # 1. Procesar Canales
            for channel in temp_root.findall('channel'):
                cid = channel.get('id')
                if cid in whitelist and cid not in canales_procesados:
                    f_req = whitelist[cid]
                    if f_req and f_req not in url_tag: continue
                    new_root.append(channel)
                    canales_procesados.add(cid)

            # 2. Procesar Programas (Descripciones)
            for prog in temp_root.findall('programme'):
                pid = prog.get('channel')
                start_time = prog.get('start')
                prog_id = f"{pid}_{start_time}"
                
                if pid in whitelist and prog_id not in programas_processed_check := prog_id in programas_procesados:
                    if prog_id in programas_procesados: continue
                    f_req = whitelist[pid]
                    if f_req and f_req not in url_tag: continue
                    
                    d_elem = prog.find('desc')
                    
                    # Formateamos quirúrgicamente la descripción original de la fuente
                    if d_elem is not None and d_elem.text:
                        d_elem.text = formatear_descripcion_quirurgica(d_elem.text)

                    new_root.append(prog)
                    programas_procesados.add(prog_id)
            temp_root.clear()
        except Exception as e: 
            print(f"Error procesando fuente {url.split('/')[-1]}: {e}")
            pass

    tree = ET.ElementTree(new_root)
    tree.write(OUTPUT_FILE, encoding='utf-8', xml_declaration=True)
    with gzip.open(OUTPUT_GZ, 'wb') as f:
        tree.write(f, encoding='utf-8', xml_declaration=True)
    print("EPG procesada con éxito sin TMDB.")

if __name__ == "__main__":
    filter_epg()
