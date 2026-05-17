import xml.etree.ElementTree as ET
import requests
import os
import gzip
import io
import re
import copy
import time # Necesario para generar el marcador de tiempo único

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
    "https://epgshare01.online/epgshare01/epg_ripper_SV1.xml.gz" # Tu URL original intacta
]

CANALES_FILE = "canales.txt"
OUTPUT_FILE = "epg_reducida.xml"
OUTPUT_GZ = "epg_reducida.xml.gz"

def obtener_etiqueta_fuente(url):
    url_low = url.lower()
    if "iptv-epg.org" in url_low:
        return "iptv-epg"
    elif "open-epg.com" in url_low:
        return "open-epg"
    elif "epgshare01.online" in url_low:
        return "epgshare01"
    return "fuente"

def formatear_descripcion_quirurgica(texto):
    if not texto: return ""
    texto = texto.strip()
    
    # 1. Manejo de Series con códigos tipo S1 E3 o T1 E2
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

    # 2. Formato de barras para saltos de línea (como en Antena 3)
    if "\n" in texto:
        partes = [p.strip() for p in texto.split("\n") if p.strip()]
        if len(partes) >= 2:
            subtitulo = partes[0]
            cuerpo = " ".join(partes[1:])
            if subtitulo and not subtitulo.endswith(('.', ':', '!', '?')):
                return f"{subtitulo} | {cuerpo}"
            return f"{subtitulo} {cuerpo}"

    # 3. Texto plano de una sola línea
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

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Cache-Control': 'no-cache', # Le dice al servidor que no queremos datos cacheados
        'Pragma': 'no-cache'
    }

    for url in EPG_SOURCES:
        etiqueta_actual = obtener_etiqueta_fuente(url)
        nombre_archivo = url.split('/')[-1]
        
        # TRUCO DE CONTROL: Le inyectamos un número único a la URL para destruir la caché vieja
        url_con_anti_cache = f"{url}?t={int(time.time())}"
        
        try:
            r = requests.get(url_con_anti_cache, headers=headers, timeout=45)
            if r.status_code != 200: 
                print(f"Saltando {nombre_archivo}: Error {r.status_code}")
                continue
                
            content = r.content
            if url.endswith(".gz") or content[:2] == b'\x1f\x8b':
                content = gzip.decompress(content)
            
            context = ET.iterparse(io.BytesIO(content), events=('start', 'end'))
            context = iter(context)
            event, root_fuente = next(context)
            
            contador = 0
            for event, elem in context:
                if event == 'end':
                    if elem.tag == 'channel':
                        cid = elem.get('id')
                        if cid in whitelist and cid not in canales_procesados:
                            f_req = whitelist[cid]
                            if f_req and f_req != etiqueta_actual: 
                                continue
                            
                            clon_canal = copy.deepcopy(elem)
                            new_root.append(clon_canal)
                            canales_procesados.add(cid)

                    elif elem.tag == 'programme':
                        pid = elem.get('channel')
                        start_time = elem.get('start')
                        prog_id = f"{pid}_{start_time}"
                        
                        if pid in whitelist and prog_id not in programas_procesados:
                            f_req = whitelist[pid]
                            if f_req and f_req != etiqueta_actual: 
                                continue
                            
                            clon_prog = copy.deepcopy(elem)
                            
                            d_elem = clon_prog.find('desc')
                            if d_elem is not None and d_elem.text:
                                d_elem.text = formatear_descripcion_quirurgica(d_elem.text)

                            new_root.append(clon_prog)
                            programas_processed_check = programas_procesados.add(prog_id)
                    
                    contador += 1
                    if contador % 10000 == 0:
                        root_fuente.clear()
            
            print(f"Fuente procesada con éxito forzando datos nuevos: {nombre_archivo}")
            
        except Exception as e: 
            print(f"Error procesando fuente {nombre_archivo}: {e}")
            pass

    tree = ET.ElementTree(new_root)
    tree.write(OUTPUT_FILE, encoding='utf-8', xml_declaration=True)
    with gzip.open(OUTPUT_GZ, 'wb') as f:
        tree.write(f, encoding='utf-8', xml_declaration=True)
    print("EPG reducida generada con éxito rompiendo la caché de internet.")

if __name__ == "__main__":
    filter_epg()
