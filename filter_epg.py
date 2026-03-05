import xml.etree.ElementTree as ET
import requests
import os
import gzip

# Configuración
EPG_SOURCES = ["https://iptv-epg.org/files/epg-ztjwyq.xml"]
CANALES_FILE = "canales.txt"
OUTPUT_FILE = "epg_reducida.xml"

def filter_epg():
    if not os.path.exists(CANALES_FILE):
        print("Error: No existe canales.txt")
        return

    # 1. Leer los IDs de canales.txt
    with open(CANALES_FILE, 'r', encoding='utf-8') as f:
        whitelist = set(line.strip() for line in f if line.strip())
    
    print(f"Buscando {len(whitelist)} canales en las fuentes...")

    # 2. Crear la estructura del nuevo XML
    new_tv = ET.Element('tv', {
        'source-info-name': 'Mi EPG Personalizada',
        'source-info-url': 'https://iptv-epg.org'
    })

    headers = {'User-Agent': 'Mozilla/5.0'}

    for url in EPG_SOURCES:
        try:
            print(f"Descargando: {url}")
            r = requests.get(url, headers=headers, timeout=60)
            r.raise_for_status()
            
            # Descomprimir si es necesario
            content = gzip.decompress(r.content) if (url.endswith(".gz") or r.content[:2] == b'\x1f\x8b') else r.content
            
            # 3. Parsear el XML completo
            tree = ET.fromstring(content)
            
            # 4. Filtrar canales
            for channel in tree.findall('channel'):
                if channel.get('id') in whitelist:
                    new_tv.append(channel)
            
            # 5. Filtrar programas
            for programme in tree.findall('programme'):
                if programme.get('channel') in whitelist:
                    new_tv.append(programme)

        except Exception as e:
            print(f"Error procesando {url}: {e}")

    # 6. Guardar el resultado final
    final_tree = ET.ElementTree(new_tv)
    ET.indent(final_tree, space="  ", level=0) # Para que se vea bonito y ordenado
    final_tree.write(OUTPUT_FILE, encoding='utf-8', xml_declaration=True)
    
    print(f"¡Hecho! Archivo {OUTPUT_FILE} generado con toda la información.")

if __name__ == "__main__":
    filter_epg()
