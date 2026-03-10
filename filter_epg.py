import xml.etree.ElementTree as ET
import requests
import os
import gzip
import io

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
    
    # Creamos la raíz del XML
    root = ET.Element('tv', {'generator-info-name': 'Generador EPG Pro', 'generator-info-url': 'https://github.com'})

    headers = {'User-Agent': 'Mozilla/5.0'}

    for url in EPG_SOURCES:
        try:
            print(f"Escaneando a fondo: {url}")
            r = requests.get(url, headers=headers, timeout=60)
            r.raise_for_status()
            
            content = gzip.decompress(r.content) if (url.endswith(".gz") or r.content[:2] == b'\x1f\x8b') else r.content
            
            # Usamos iterparse para no saltarnos ninguna línea por pesada que sea
            context = ET.iterparse(io.BytesIO(content), events=('start', 'end'))
            
            for event, elem in context:
                # Al encontrar el final de una etiqueta...
                if event == 'end':
                    # Si es un CANAL
                    if elem.tag == 'channel':
                        cid = elem.get('id')
                        if cid in whitelist and cid not in canales_encontrados:
                            root.append(elem)
                            canales_encontrados.add(cid)
                    
                    # Si es un PROGRAMA
                    elif elem.tag == 'programme':
                        pid = elem.get('channel')
                        if pid in whitelist:
                            # Limpieza rápida para que LG Netcast no se sature
                            for extra in ['credits', 'country', 'language']:
                                target = elem.find(extra)
                                if target is not None: elem.remove(target)
                            root.append(elem)
                    
                    # Importante: No limpiar 'elem' aquí porque lo acabamos de añadir a 'root'
                    # Solo lo removemos del árbol temporal de lectura para ahorrar RAM
                    # (Pero en este caso, al ser filtrado, lo mantenemos en memoria root)

        except Exception as e:
            print(f"Error crítico leyendo fuente: {e}")

    # Guardado final (XML y GZ)
    tree = ET.ElementTree(root)
    tree.write(OUTPUT_FILE, encoding='utf-8', xml_declaration=True)
    with gzip.open(OUTPUT_GZ, 'wb') as f:
        tree.write(f, encoding='utf-8', xml_declaration=True)

    # Reporte de canales que el código NO pudo encontrar
    faltantes = whitelist - canales_encontrados
    with open(LOG_ERRORES, 'w', encoding='utf-8') as f:
        if faltantes:
            f.write("⚠️ ESTOS CANALES NO SE LEYERON (REVISA EL ID):\n")
            for c in sorted(faltantes): f.write(f"- {c}\n")
        else:
            f.write("✅ ¡Éxito! Se leyó toda la información de tu lista.")

if __name__ == "__main__":
    filter_epg()
