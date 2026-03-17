import xml.etree.ElementTree as ET
import requests
import gzip
import io

# Las 9 fuentes en orden
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
    "https://iptv-epg.org/files/epg-pa.xml"
]

ARCHIVO_SALIDA = "lista_todos_los_ids.txt"

def extraer_todos_los_ids():
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    with open(ARCHIVO_SALIDA, 'w', encoding='utf-8') as f:
        f.write("REPORTE DE IDS DISPONIBLES POR FUENTE\n")
        f.write("====================================\n\n")

        # Recorremos cada URL con su índice (1, 2, 3...)
        for i, url in enumerate(EPG_SOURCES, start=1):
            print(f"Procesando Fuente {i}: {url}")
            
            # Escribimos el encabezado para esta URL
            f.write(f"--- ID URL {i} ({url}) ---\n")
            
            try:
                r = requests.get(url, headers=headers, timeout=60)
                r.raise_for_status()
                
                content = gzip.decompress(r.content) if (url.endswith(".gz") or r.content[:2] == b'\x1f\x8b') else r.content
                context = ET.iterparse(io.BytesIO(content), events=('end',))
                
                contador = 0
                for event, elem in context:
                    if elem.tag == 'channel':
                        canal_id = elem.get('id')
                        nombre = elem.findtext('display-name') or "Sin nombre"
                        if canal_id:
                            f.write(f"{canal_id}  |  ({nombre})\n")
                            contador += 1
                        elem.clear()
                
                f.write(f"\nTotal canales encontrados en Fuente {i}: {contador}\n")
                f.write("-" * 50 + "\n\n")
                
            except Exception as e:
                f.write(f"Error al procesar esta fuente: {e}\n\n")
    
    print(f"¡Hecho! El archivo {ARCHIVO_SALIDA} ha sido organizado por fuentes.")

if __name__ == "__main__":
    extraer_todos_los_ids()
