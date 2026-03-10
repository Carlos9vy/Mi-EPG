import xml.etree.ElementTree as ET
import requests
import gzip
import io
import os

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
ARCHIVO_LOGOS = "lista_logos_canales.txt"

def extraer_logos():
    if not os.path.exists(CANALES_FILE):
        print("No se encontró canales.txt")
        return

    with open(CANALES_FILE, 'r', encoding='utf-8') as f:
        whitelist = set(line.strip() for line in f if line.strip())

    logos_encontrados = {}
    headers = {'User-Agent': 'Mozilla/5.0'}

    for url in EPG_SOURCES:
        try:
            print(f"Buscando logos en: {url}")
            r = requests.get(url, headers=headers, timeout=60)
            content = gzip.decompress(r.content) if (url.endswith(".gz") or r.content[:2] == b'\x1f\x8b') else r.content
            
            context = ET.iterparse(io.BytesIO(content), events=('end',))
            for event, elem in context:
                if elem.tag == 'channel':
                    cid = elem.get('id')
                    if cid in whitelist and cid not in logos_encontrados:
                        icon = elem.find('icon')
                        nombre = elem.findtext('display-name') or cid
                        if icon is not None:
                            url_logo = icon.get('src')
                            logos_encontrados[cid] = f"{cid} | ({nombre}) -> {url_logo}"
                    elem.clear()
        except Exception as e:
            print(f"Error en {url}: {e}")

    # Guardar resultados
    with open(ARCHIVO_LOGOS, 'w', encoding='utf-8') as f:
        f.write("LISTA DE LOGOS DE TUS CANALES\n")
        f.write("==============================\n\n")
        for cid in sorted(whitelist):
            if cid in logos_encontrados:
                f.write(f"{logos_encontrados[cid]}\n")
            else:
                f.write(f"{cid} | (Sin logo encontrado en las fuentes)\n")
    
    print(f"¡Hecho! Revisa {ARCHIVO_LOGOS}")

if __name__ == "__main__":
    extraer_logos()
