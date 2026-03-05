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

    # Cargamos canales y limpiamos espacios o líneas vacías
    with open(CANALES_FILE, 'r') as f:
        whitelist = set(line.strip() for line in f if line.strip())
    
    print(f"Lista de búsqueda: {whitelist}")

    with open(OUTPUT_FILE, 'wb') as f:
        # Escribimos la cabecera idéntica a la original
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(b'<tv source-info-name="IPTV-EPG.org" source-info-url="https://iptv-epg.org">\n')

        headers = {'User-Agent': 'Mozilla/5.0'}

        for url in EPG_SOURCES:
            print(f"Conectando a: {url}")
            try:
                # Quitamos el stream=True momentáneamente para asegurar descarga completa
                r = requests.get(url, headers=headers, timeout=60)
                r.raise_for_status()
                
                # Usamos iterparse sobre el contenido descargado
                import io
                content = io.BytesIO(r.content)
                context = ET.iterparse(content, events=('end',))
                
                c_count = 0
                p_count = 0

                for event, elem in context:
                    # Filtro de canales
                    if elem.tag == 'channel':
                        cid = elem.get('id')
                        if cid in whitelist:
                            f.write(ET.tostring(elem, encoding='utf-8'))
                            f.write(b'\n')
                            c_count += 1
                    
                    # Filtro de programas (la guía)
                    elif elem.tag == 'programme':
                        pid = elem.get('channel')
                        if pid in whitelist:
                            f.write(ET.tostring(elem, encoding='utf-8'))
                            f.write(b'\n')
                            p_count += 1
                    
                    # Importante: liberar memoria
                    elem.clear()
                
                print(f"Encontrados: {c_count} canales y {p_count} programas.")

            except Exception as e:
                print(f"Error procesando: {e}")

        f.write(b'</tv>')

if __name__ == "__main__":
    filter_epg()
