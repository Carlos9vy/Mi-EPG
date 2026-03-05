import xml.etree.ElementTree as ET
import requests
import os

EPG_SOURCES = ["https://iptv-epg.org/files/epg-ztjwyq.xml"]
CANALES_FILE = "canales.txt"
OUTPUT_FILE = "epg_reducida.xml"

def filter_epg():
    if not os.path.exists(CANALES_FILE):
        print("Error: No existe canales.txt")
        return

    with open(CANALES_FILE, 'r') as f:
        whitelist = set(line.strip() for line in f if line.strip())
    
    print(f"Buscando estos {len(whitelist)} canales: {whitelist}")

    with open(OUTPUT_FILE, 'wb') as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(b'<tv>\n')

        for url in EPG_SOURCES:
            print(f"Descargando de: {url}")
            try:
                r = requests.get(url, stream=True)
                # Usamos iterparse para no cargar todo en RAM
                context = ET.iterparse(r.raw, events=('end',))
                
                encontrados_id = 0
                encontrados_prog = 0

                for event, elem in context:
                    if elem.tag == 'channel':
                        canal_id = elem.get('id')
                        if canal_id in whitelist:
                            f.write(ET.tostring(elem, encoding='utf-8'))
                            f.write(b'\n')
                            encontrados_id += 1
                    
                    elif elem.tag == 'programme':
                        prog_id = elem.get('channel')
                        if prog_id in whitelist:
                            f.write(ET.tostring(elem, encoding='utf-8'))
                            f.write(b'\n')
                            encontrados_prog += 1
                    
                    elem.clear()
                
                print(f"Resultado: {encontrados_id} canales y {encontrados_prog} programas hallados.")

            except Exception as e:
                print(f"Error procesando URL: {e}")

        f.write(b'</tv>')

if __name__ == "__main__":
    filter_epg()
