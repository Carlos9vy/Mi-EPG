import xml.etree.ElementTree as ET
import requests
import gzip
import io
from datetime import datetime

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

ARCHIVO_REPORTE = "reporte_fechas_epg.txt"

def formato_fecha(xml_date):
    # Formato típico EPG: 20260307000000 +0000
    try:
        return datetime.strptime(xml_date[:14], "%Y%m%d%H%M%S")
    except:
        return None

def analizar_fuentes():
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    with open(ARCHIVO_REPORTE, 'w', encoding='utf-8') as f:
        f.write("REPORTE DE COBERTURA DE DÍAS POR FUENTE\n")
        f.write("========================================\n\n")

        for i, url in enumerate(EPG_SOURCES, start=1):
            print(f"Analizando fechas de Fuente {i}...")
            try:
                r = requests.get(url, headers=headers, timeout=60)
                content = gzip.decompress(r.content) if (url.endswith(".gz") or r.content[:2] == b'\x1f\x8b') else r.content
                context = ET.iterparse(io.BytesIO(content), events=('end',))
                
                fechas = []
                for event, elem in context:
                    if elem.tag == 'programme':
                        start = elem.get('start')
                        if start:
                            d = formato_fecha(start)
                            if d: fechas.append(d)
                    elem.clear()

                if fechas:
                    primera = min(fechas)
                    ultima = max(fechas)
                    duracion = ultima - primera
                    
                    f.write(f"--- FUENTE {i} ({url.split('/')[-1]}) ---\n")
                    f.write(f"Inicia:  {primera.strftime('%d/%m/%Y %H:%M')}\n")
                    f.write(f"Finaliza: {ultima.strftime('%d/%m/%Y %H:%M')}\n")
                    f.write(f"Total días de programación: {duracion.days} días y {duracion.seconds // 3600} horas\n")
                    f.write("-" * 40 + "\n\n")
                else:
                    f.write(f"--- FUENTE {i}: No se encontraron programas ---\n\n")

            except Exception as e:
                f.write(f"--- FUENTE {i}: Error al analizar ({e}) ---\n\n")

    print(f"¡Análisis completo! Revisa {ARCHIVO_REPORTE}")

if __name__ == "__main__":
    analizar_fuentes()
