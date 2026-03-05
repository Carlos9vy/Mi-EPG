import xml.etree.ElementTree as ET
import requests
import gzip
import io

URL_FUENTE = "https://iptv-epg.org/files/epg-ztjwyq.xml"
ARCHIVO_SALIDA = "lista_todos_los_ids.txt"

def extraer_todos_los_ids():
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        print(f"Leyendo fuente original...")
        r = requests.get(URL_FUENTE, headers=headers, timeout=60)
        content = gzip.decompress(r.content) if (URL_FUENTE.endswith(".gz") or r.content[:2] == b'\x1f\x8b') else r.content
        context = ET.iterparse(io.BytesIO(content), events=('end',))
        
        # Usamos una lista simple para mantener el orden de aparición
        lineas = []
        for event, elem in context:
            if elem.tag == 'channel':
                canal_id = elem.get('id')
                nombre = elem.findtext('display-name') or "Sin nombre"
                if canal_id:
                    # Guardamos el ID y el nombre tal cual aparecen
                    lineas.append(f"{canal_id}  |  ({nombre})")
                elem.clear()

        with open(ARCHIVO_SALIDA, 'w', encoding='utf-8') as f:
            f.write("LISTA DE IDS DISPONIBLES (ORDEN ORIGINAL POR PAÍSES)\n")
            f.write("==================================================\n\n")
            # Escribimos directamente la lista sin usar sorted()
            for linea in lineas:
                f.write(f"{linea}\n")
        
        print(f"¡Hecho! Lista guardada en orden original.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    extraer_todos_los_ids()
