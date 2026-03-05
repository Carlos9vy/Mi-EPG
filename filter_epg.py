import xml.etree.ElementTree as ET
import requests
import os
import gzip
import io

# 1. Agrega aquí todas las URLs que necesites
EPG_SOURCES = [
    "https://iptv-epg.org/files/epg-ztjwyq.xml",
    "https://iptv-epg.org/files/epg-bo.xml",
    "https://iptv-epg.org/files/epg-py.xml" # Ejemplo de fuente comprimida
]

CANALES_FILE = "canales.txt"
OUTPUT_FILE = "epg_reducida.xml"

def filter_epg():
    if not os.path.exists(CANALES_FILE):
        print("Error: No existe canales.txt")
        return

    # Leer canales y limpiar espacios
    with open(CANALES_FILE, 'r', encoding='utf-8') as f:
        whitelist = set(line.strip() for line in f if line.strip())
    
    print(f"Buscando {len(whitelist)} canales en {len(EPG_SOURCES)} fuentes.")

    with open(OUTPUT_FILE, 'wb') as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(b'<tv source-info-name="Mi EPG Personalizada">\n')

        headers = {'User-Agent': 'Mozilla/5.0'}

        for url in EPG_SOURCES:
            print(f"--- Procesando: {url} ---")
            try:
                r = requests.get(url, headers=headers, timeout=60)
                r.raise_for_status()
                
                # Detectar si el archivo está comprimido en GZIP
                if url.endswith(".gz") or r.content[:2] == b'\x1f\x8b':
                    content = gzip.decompress(r.content)
                else:
                    content = r.content

                context = ET.iterparse(io.BytesIO(content), events=('end',))
                
                c_count = 0
                p_count = 0

                for event, elem in context:
                    if elem.tag == 'channel':
                        if elem.get('id') in whitelist:
                            f.write(ET.tostring(elem, encoding='utf-8'))
                            f.write(b'\n')
                            c_count += 1
                    
                    elif elem.tag == 'programme':
                        if elem.get('channel') in whitelist:
                            f.write(ET.tostring(elem, encoding='utf-8'))
                            f.write(b'\n')
                            p_count += 1
                    
                    elem.clear() # Liberar memoria RAM
                
                print(f"Logrado: {c_count} canales y {p_count} programas.")

            except Exception as e:
                print(f"Error en esta fuente: {e}")

        f.write(b'</tv>')
    print("\n¡Proceso finalizado con éxito!")

if __name__ == "__main__":
    filter_epg()
