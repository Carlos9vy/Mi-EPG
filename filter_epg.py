import requests
import xml.etree.ElementTree as ET
import gzip
import io

# Fuentes originales
SOURCES = [
    "https://iptv-epg.org/files/epg-ar.xml", "https://iptv-epg.org/files/epg-cl.xml",
    "https://iptv-epg.org/files/epg-co.xml", "https://iptv-epg.org/files/epg-ec.xml",
    "https://iptv-epg.org/files/epg-mx.xml", "https://iptv-epg.org/files/epg-pe.xml",
    "https://iptv-epg.org/files/epg-es.xml", "https://iptv-epg.org/files/epg-us.xml",
    "https://iptv-epg.org/files/epg-uy.xml", "https://iptv-epg.org/files/epg-ve.xml",
    "https://iptv-epg.org/files/epg-bo.xml", "https://iptv-epg.org/files/epg-cr.xml",
    "https://iptv-epg.org/files/epg-do.xml", "https://iptv-epg.org/files/epg-sv.xml",
    "https://iptv-epg.org/files/epg-gt.xml", "https://iptv-epg.org/files/epg-hn.xml",
    "https://iptv-epg.org/files/epg-py.xml", "https://iptv-epg.org/files/epg-pa.xml",
    "https://www.open-epg.com/generate/aYzuzNSenh.xml",
    "https://epgshare01.online/epgshare01/epg_ripper_SV1.xml.gz"
]

def run():
    # Cargar tus IDs desde canales.txt
    try:
        with open("canales.txt", "r", encoding="utf-8") as f:
            wanted_ids = set(line.strip() for line in f if line.strip())
        print(f"Cargados {len(wanted_ids)} IDs desde canales.txt")
    except FileNotFoundError:
        print("Error: No se encontró canales.txt")
        return

    # Elementos raíz para el nuevo XML
    new_root = ET.Element("tv", {"generator-info-name": "MiRobotEPG"})
    
    # Listas para organizar el XML final (primero canales, luego programas)
    channels_found = []
    programmes_found = []

    for url in SOURCES:
        try:
            print(f"Descargando: {url}")
            r = requests.get(url, timeout=60)
            data = r.content
            
            if url.endswith(".gz"):
                data = gzip.decompress(data)
            
            # Parsear XML
            tree = ET.fromstring(data)
            
            # Buscar canales
            for c in tree.findall("channel"):
                if c.get("id") in wanted_ids:
                    channels_found.append(c)
            
            # Buscar programas
            for p in tree.findall("programme"):
                if p.get("channel") in wanted_ids:
                    programmes_found.append(p)
                    
        except Exception as e:
            print(f"Omitiendo fuente {url} por error: {e}")

    # Unir todo en el nuevo XML (evitando duplicados de canales)
    unique_channels = {c.get("id"): c for c in channels_found}.values()
    for c in unique_channels:
        new_root.append(c)
    for p in programmes_found:
        new_root.append(p)

    # Guardar el archivo final
    output_file = "guia_personalizada.xml"
    tree_out = ET.ElementTree(new_root)
    tree_out.write(output_file, encoding="utf-8", xml_declaration=True)
    print(f"¡Listo! Archivo {output_file} generado con éxito.")

if __name__ == "__main__":
    run()
