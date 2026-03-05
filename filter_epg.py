import xml.etree.ElementTree as ET
import requests
import os
import gzip
import io

EPG_SOURCES = [
    "https://iptv-epg.org/files/epg-ztjwyq.xml"
]

CANALES_FILE = "canales.txt"
OUTPUT_FILE = "epg_reducida.xml"

def filter_epg():
    if not os.path.exists(CANALES_FILE):
        print("Error: No existe canales.txt")
        return

    with open(CANALES_FILE, 'r', encoding='utf-8') as f:
        whitelist = set(line.strip() for line in f if line.strip())
    
    print(f"Buscando {len(whitelist)} canales.")

    with open(OUTPUT_FILE, 'wb') as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(b'<tv source-info-name="Mi EPG Personalizada">\n')

        headers = {'User-Agent': 'Mozilla/5.0'}

        for url in EPG_SOURCES:
            try:
                r = requests.get(url, headers=headers, timeout=60)
                r.raise_for_status()
                
                content = gzip.decompress(r.content) if (url.endswith(".gz") or r.content[:2] == b'\x1f\x8b') else r.content

                # Usamos iterparse pero recuperamos el objeto completo
                context = ET.iterparse(io.BytesIO(content), events=('end',))
                
                for event, elem in context:
                    if elem.tag == 'channel' and elem.get('id') in whitelist:
                        # Forzamos la escritura completa del nodo
                        f.write(ET.tostring(elem, encoding='utf-8', method='xml'))
                        f.write(b'\n')
                    
                    elif elem.tag == 'programme' and elem.get('channel') in whitelist:
                        # Forzamos la escritura completa del nodo
                        f.write(ET.tostring(elem, encoding='utf-8', method='xml'))
                        f.write(b'\n')
                    
                    # No limpiamos el elemento inmediatamente para asegurar que se procesen los hijos
                    # elem.clear() <- Quitamos esto de aquí dentro para probar
                
            except Exception as e:
                print(f"Error: {e}")

        f.write(b'</tv>')
    print("¡EPG Generada con éxito!")

if __name__ == "__main__":
    filter_epg()
