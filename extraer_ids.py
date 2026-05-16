import xml.etree.ElementTree as ET
import requests
import gzip
import io

# --- LAS 20 FUENTES COMPLETAS EN ORDEN ---
EPG_SOURCES = [
    "https://iptv-epg.org/files/epg-ar.xml",
    "https://iptv-epg.org/files/epg-cl.xml",
    "https://iptv-epg.org/files/epg-co.xml",
    "https://iptv-epg.org/files/epg-ec.xml",
    "https://iptv-epg.org/files/epg-mx.xml",
    "https://iptv-epg.org/files/epg-pe.xml",
    "https://iptv-epg.org/files/epg-es.xml",
    "https://iptv-epg.org/files/epg-us.xml",
    "https://iptv-epg.org/files/epg-uy.xml",
    "https://iptv-epg.org/files/epg-ve.xml",
    "https://iptv-epg.org/files/epg-bo.xml",
    "https://iptv-epg.org/files/epg-cr.xml",
    "https://iptv-epg.org/files/epg-do.xml",
    "https://iptv-epg.org/files/epg-sv.xml",
    "https://iptv-epg.org/files/epg-gt.xml",
    "https://iptv-epg.org/files/epg-hn.xml",
    "https://iptv-epg.org/files/epg-py.xml",
    "https://iptv-epg.org/files/epg-pa.xml",
    "https://www.open-epg.com/generate/aYzuzNSenh.xml",
    "https://epgshare01.online/epgshare01/epg_ripper_SV1.xml.gz"
]

ARCHIVO_SALIDA = "lista_todos_los_ids.txt"

def obtener_etiqueta_fuente(url):
    url_low = url.lower()
    if "iptv-epg.org" in url_low:
        return "iptv-epg"
    elif "open-epg.com" in url_low:
        return "open-epg"
    elif "epgshare01.online" in url_low:
        return "epgshare01"
    return "fuente"

def extraer_todos_los_ids():
    # Fingimos ser un navegador real para que no nos bloqueen
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    with open(ARCHIVO_SALIDA, 'w', encoding='utf-8') as f:
        f.write("REPORTE DE IDS DISPONIBLES POR FUENTE\n")
        f.write("====================================\n\n")

        for i, url in enumerate(EPG_SOURCES, start=1):
            print(f"Procesando Fuente {i}/{len(EPG_SOURCES)}: {url.split('/')[-1]}")
            f.write(f"Fuente {i}: {url}\n")
            etiqueta = obtener_etiqueta_fuente(url)
            
            try:
                # CORRECCIÓN: Pasamos los headers y reducimos el timeout a 15 segundos
                r = requests.get(url, headers=headers, timeout=15)
                r.raise_for_status()
                
                content = gzip.decompress(r.content) if (url.endswith(".gz") or r.content[:2] == b'\x1f\x8b') else r.content
                context = ET.iterparse(io.BytesIO(content), events=('end',))
                
                contador = 0
                for event, elem in context:
                    if elem.tag == 'channel':
                        canal_id = elem.get('id')
                        if canal_id:
                            f.write(f"{canal_id.strip()} ({etiqueta})\n")
                            contador += 1
                        elem.clear()
                
                f.write(f"\nTotal canales encontrados en Fuente {i}: {contador}\n")
                f.write("-" * 50 + "\n\n")
                
            except Exception as e:
                # Si una fuente falla o tarda más de 15 segundos, se escribe el error y se salta a la siguiente
                f.write(f"Error o Tiempo Límite excedido en esta fuente: {e}\n\n")
                print(f"Saltando Fuente {i} por error: {e}")
    
    print(f"¡Hecho! Lista generada en {ARCHIVO_SALIDA}")

if __name__ == "__main__":
    extraer_todos_los_ids()
