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
    if not texto: return ""
    texto = texto.strip()
    
    patron_code = r'([TS]\d+\s?[E]\d+)'
    match = re.search(patron_code, texto, re.IGNORECASE)
    
    if match:
        code = match.group().upper().strip()
        resto = texto.replace(match.group(), "").strip()
        resto = re.sub(r'^[:\-\s—]+', '', resto)
        
        if "\n" in resto:
            partes = resto.split("\n", 1)
            encabezado = partes[0].strip()
            if encabezado and not encabezado.endswith(('.', ':', '!', '?')):
                encabezado += "."
            return f"{code} | {encabezado}\n{partes[1].strip()}"
        else:
            if resto and not resto.endswith(('.', ':', '!', '?')):
                resto += "."
            return f"{code} | {resto}"

    if "\n" in texto:
        partes = texto.split("\n", 1)
        primera_linea = partes[0].strip()
        if primera_linea and not primera_linea.endswith(('.', ':', '!', '?')):
            primera_linea += "."
        return f"{primera_linea}\n{partes[1].strip()}"
    
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

    # CORRECCIÓN: Definimos los Headers para saltar bloqueos de seguridad
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    for url in EPG_SOURCES:
        url_tag = url.lower()
        nombre_archivo = url.split('/')[-1]
        try:
            # CORRECCIÓN: Agregamos headers y un timeout prudente de 30 segundos
            r = requests.get(url, headers=headers, timeout=30)
            if r.status_code != 200: 
                print(f"Saltando {nombre_archivo}: Error de estado {r.status_code}")
                continue
                
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

            # 2. Procesar Programas
            for prog in temp_root.findall('programme'):
                pid = prog.get('channel')
                start_time = prog.get('start')
                prog_id = f"{pid}_{start_time}"
                
                if pid in whitelist and prog_id not in programas_procesados:
                    f_req = whitelist[pid]
                    if f_req and f_req not in url_tag: continue
                    
                    d_elem = prog.find('desc')
                    if d_elem is not None and d_elem.text:
                        d_elem.text = formatear_descripcion_quirurgica(d_elem.text)

                    new_root.append(prog)
                    programas_procesados.add(prog_id)
            
            print(f"Fuente procesada con éxito: {nombre_archivo}")
            temp_root.clear()
            
        except Exception as e: 
            print(f"Error procesando fuente {nombre_archivo}: {e}")
            pass

    tree = ET.ElementTree(new_root)
    tree.write(OUTPUT_FILE, encoding='utf-8', xml_declaration=True)
    with gzip.open(OUTPUT_GZ, 'wb') as f:
        tree.write(f, encoding='utf-8', xml_declaration=True)
    print("EPG reducida generada con éxito combinando todas las fuentes.")

if __name__ == "__main__":
    filter_epg()
