import xml.etree.ElementTree as ET
import requests
import os
import gzip

# 1. Lista completa de fuentes (9 en total)
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
LOG_ERRORES = "errores_canales.txt"

def filter_epg():
    if not os.path.exists(CANALES_FILE):
        print(f"Error: No se encontró {CANALES_FILE}")
        return

    # Leer los canales que quieres filtrar
    with open(CANALES_FILE, 'r', encoding='utf-8') as f:
        whitelist = set(line.strip() for line in f if line.strip())
    
    # Conjunto para saber qué canales sí encontramos entre todas las fuentes
    canales_encontrados = set()

    # Estructura raíz del nuevo XML
    new_tv = ET.Element('tv', {
        'source-info-name': 'Mi EPG Personalizada Multi-Fuente',
        'source-info-url': 'https://iptv-epg.org'
    })

    headers = {'User-Agent': 'Mozilla/5.0'}

    # Procesar cada fuente
    for url in EPG_SOURCES:
        try:
            print(f"Procesando: {url}")
            r = requests.get(url, headers=headers, timeout=60)
            r.raise_for_status()
            
            # Descomprimir si la fuente viene en .gz
            content = gzip.decompress(r.content) if (url.endswith(".gz") or r.content[:2] == b'\x1f\x8b') else r.content
            
            # Parsear el XML de la fuente actual
            tree = ET.fromstring(content)
            
            # Buscar canales
            for channel in tree.findall('channel'):
                cid = channel.get('id')
                if cid in whitelist:
                    # Solo lo añadimos si no lo habíamos añadido de una fuente anterior
                    if cid not in canales_encontrados:
                        new_tv.append(channel)
                        canales_encontrados.add(cid)
            
            # Buscar programas
            for programme in tree.findall('programme'):
                pid = programme.get('channel')
                if pid in whitelist:
                    new_tv.append(programme)

        except Exception as e:
            print(f"Error en fuente {url}: {e}")

    # 2. Guardar el archivo XML final
    final_tree = ET.ElementTree(new_tv)
    ET.indent(final_tree, space="  ", level=0)
    final_tree.write(OUTPUT_FILE, encoding='utf-8', xml_declaration=True)

    # 3. Lógica de reporte de errores (Canales no encontrados)
    canales_con_error = whitelist - canales_encontrados

    with open(LOG_ERRORES, 'w', encoding='utf-8') as f:
        if canales_con_error:
            f.write("⚠️ CANALES NO ENCONTRADOS EN NINGUNA FUENTE:\n")
            f.write("Copia estos IDs y búscalos con el robot extractor si es necesario.\n")
            f.write("==============================================================\n\n")
            for canal in sorted(canales_con_error):
                f.write(f"- {canal}\n")
            print(f"Atención: {len(canales_con_error)} canales no se encontraron.")
        else:
            f.write("✅ ¡Excelente! Todos los canales de tu lista están en las fuentes.")
            print("¡Todos los canales encontrados con éxito!")

if __name__ == "__main__":
    filter_epg()
