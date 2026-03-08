import xml.etree.ElementTree as ET
import requests
import os
import gzip

EPG_SOURCES = [
    "https://iptv-epg.org/files/epg-ztjwyq.xml",
    "https://iptv-epg.org/files/epg-bo.xml",
    "https://iptv-epg.org/files/epg-cr.xml",
    "https://iptv-epg.org/files/epg-do.xml",
    "https://iptv-epg.org/files/epg-sv.xml",
    "https://iptv-epg.org/files/epg-gt.xml",
    "https://iptv-epg.org/files/epg-hn.xml",
    "https://iptv-epg.org/files/epg-py.xml",
    "https://iptv-epg.org/files/epg-pa.xml"
]

CANALES_FILE = "canales.txt"
OUTPUT_FILE = "epg_reducida.xml"
OUTPUT_GZ = "epg_reducida.xml.gz"
LOG_ERRORES = "errores_canales.txt"

def filter_epg():
    if not os.path.exists(CANALES_FILE): return

    with open(CANALES_FILE, 'r', encoding='utf-8') as f:
        whitelist = set(line.strip() for line in f if line.strip())
    
    canales_encontrados = set()
    new_tv = ET.Element('tv', {'source-info-name': 'EPG Optimizada LG Netcast'})

    headers = {'User-Agent': 'Mozilla/5.0'}

    for url in EPG_SOURCES:
        try:
            r = requests.get(url, headers=headers, timeout=60)
            content = gzip.decompress(r.content) if (url.endswith(".gz") or r.content[:2] == b'\x1f\x8b') else r.content
            tree = ET.fromstring(content)
            
            for channel in tree.findall('channel'):
                cid = channel.get('id')
                if cid in whitelist and cid not in canales_encontrados:
                    new_tv.append(channel)
                    canales_encontrados.add(cid)
            
            for programme in tree.findall('programme'):
                if programme.get('channel') in whitelist:
                    # OPTIMIZACIÓN: Quitamos etiquetas pesadas que Netcast no suele usar
                    for tag in ['credits', 'country', 'date', 'language']:
                        elem = programme.find(tag)
                        if elem is not None: programme.remove(elem)
                    new_tv.append(programme)
        except Exception as e:
            print(f"Error: {e}")

    # 1. Guardar XML normal
    final_tree = ET.ElementTree(new_tv)
    final_tree.write(OUTPUT_FILE, encoding='utf-8', xml_declaration=True)

    # 2. Guardar versión GZIP (La que mejor le va a LG Netcast)
    with gzip.open(OUTPUT_GZ, 'wb') as f:
        final_tree.write(f, encoding='utf-8', xml_declaration=True)

    # 3. Reporte de errores
    canales_con_error = whitelist - canales_encontrados
    with open(LOG_ERRORES, 'w', encoding='utf-8') as f:
        if canales_con_error:
            f.write("⚠️ NO ENCONTRADOS:\n")
            for c in sorted(canales_con_error): f.write(f"- {c}\n")
        else:
            f.write("✅ Todo OK.")

if __name__ == "__main__":
    filter_epg()
