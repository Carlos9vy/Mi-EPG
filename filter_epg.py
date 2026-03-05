import xml.etree.ElementTree as ET
import requests
import os

# 1. Configura aquí todas las URLs de EPG que quieras usar
EPG_SOURCES = [
    "https://iptv-epg.org/files/epg-ztjwyq.xml",
    "https://iptv-epg.org/files/epg-bo.xml",
    "https://iptv-epg.org/files/epg-py.xml" # El script puede adaptarse si son .gz
]

CANALES_FILE = "canales.txt"
OUTPUT_FILE = "epg_reducida.xml"

def filter_epg():
    # Cargar lista de IDs que queremos (la "whitelist")
    if not os.path.exists(CANALES_FILE):
        print(f"Error: No se encuentra el archivo {CANALES_FILE}")
        return

    with open(CANALES_FILE, 'r') as f:
        whitelist = set(line.strip() for line in f if line.strip())

    # Iniciar el archivo de salida
    with open(OUTPUT_FILE, 'wb') as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(b'<tv>\n')

        # Procesar cada fuente
        for url in EPG_SOURCES:
            print(f"Procesando fuente: {url}")
            try:
                # Descarga con stream para no saturar RAM
                response = requests.get(url, stream=True, timeout=30)
                response.raise_for_status()
                
                # Iterparse lee el XML sobre la marcha
                context = ET.iterparse(response.raw, events=('end',))
                
                for event, elem in context:
                    # Si es un canal de nuestra lista, lo guardamos
                    if elem.tag == 'channel':
                        if elem.get('id') in whitelist:
                            f.write(ET.tostring(elem, encoding='utf-8'))
                            f.write(b'\n')
                    
                    # Si es un programa de nuestra lista, lo guardamos
                    elif elem.tag == 'programme':
                        if elem.get('channel') in whitelist:
                            f.write(ET.tostring(elem, encoding='utf-8'))
                            f.write(b'\n')
                    
                    # Limpiar el elemento de la memoria después de procesarlo
                    elem.clear()
                
                print(f"Fuente {url} procesada con éxito.")

            except Exception as e:
                print(f"Error al procesar {url}: {e}")

        f.write(b'</tv>')
    print(f"\n¡Listo! EPG consolidada guardada en {OUTPUT_FILE}")

if __name__ == "__main__":
    filter_epg()
