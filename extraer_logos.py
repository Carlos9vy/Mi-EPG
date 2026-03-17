import xml.etree.ElementTree as ET
import requests
import gzip
import io
import os

# Las 9 fuentes de siempre
EPG_SOURCES = [
    "https://iptv-epg.org/files/epg-ztjwyq.xml",
    "https://www.open-epg.com/generate/aYzuzNSenh.xml",
    "https://iptv-epg.org/files/epg-bo.xml",
    "https://iptv-epg.org/files/epg-cr.xml",
    "https://iptv-epg.org/files/epg-do.xml",
    "https://iptv-epg.org/files/epg-sv.xml",
    "https://iptv-epg.org/files/epg-gt.xml",
    "https://iptv-epg.org/files/epg-hn.xml",
    "https://iptv-epg.org/files/epg-py.xml",
    "https://iptv-epg.org/files/epg-pa.xml",
    "https://www.open-epg.com/generate/aYzuzNSenh.xml.gz" 
]

CANALES_FILE = "canales.txt"
ARCHIVO_LOGOS = "lista_logos_canales.txt"

def extraer_logos():
    if not os.path.exists(CANALES_FILE):
        print(f"Error: No se encontró {CANALES_FILE}")
        return

    # 1. Leer canales.txt manteniendo el orden original
    with open(CANALES_FILE, 'r', encoding='utf-8') as f:
        # Usamos una lista para el orden y un set para búsquedas rápidas
        lista_ordenada = [line.strip() for line in f if line.strip()]
        whitelist = set(lista_ordenada)

    # Diccionario temporal para guardar el logo de cada ID encontrado
    logos_db = {}
    headers = {'User-Agent': 'Mozilla/5.0'}

    # 2. Buscar en las fuentes
    for url in EPG_SOURCES:
        try:
            print(f"Buscando logos en: {url.split('/')[-1]}")
            r = requests.get(url, headers=headers, timeout=60)
            content = gzip.decompress(r.content) if (url.endswith(".gz") or r.content[:2] == b'\x1f\x8b') else r.content
            
            # Escaneo secuencial para no perder datos
            context = ET.iterparse(io.BytesIO(content), events=('end',))
            for event, elem in context:
                if elem.tag == 'channel':
                    cid = elem.get('id')
                    if cid in whitelist and cid not in logos_db:
                        icon = elem.find('icon')
                        if icon is not None:
                            url_logo = icon.get('src')
                            logos_db[cid] = url_logo
                    elem.clear()
        except Exception as e:
            print(f"Error en fuente {url}: {e}")

    # 3. Guardar resultados respetando el orden de canales.txt
    with open(ARCHIVO_LOGOS, 'w', encoding='utf-8') as f:
        f.write("REPORTE DE LOGOS (ORDENADO SEGÚN CANALES.TXT)\n")
        f.write("=============================================\n\n")
        
        for canal_id in lista_ordenada:
            if canal_id in logos_db:
                f.write(f"{canal_id} -> {logos_db[canal_id]}\n")
            else:
                f.write(f"{canal_id} -> (Sin logo encontrado)\n")
    
    print(f"¡Hecho! El archivo {ARCHIVO_LOGOS} ha sido generado.")

if __name__ == "__main__":
    extraer_logos()
