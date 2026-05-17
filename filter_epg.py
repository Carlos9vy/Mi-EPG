import requests
import xml.etree.ElementTree as ET
import gzip

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
    # Cargar tus IDs desde canales.txt (Limpieza estricta de saltos de línea invisibles)
    try:
        with open("canales.txt", "r", encoding="utf-8") as f:
            wanted_ids = set(line.strip().replace('\r', '').replace('\n', '') for line in f if line.strip())
        print(f"Cargados {len(wanted_ids)} IDs desde canales.txt")
    except FileNotFoundError:
        print("Error: No se encontró canales.txt")
        return

    missing_ids = wanted_ids.copy()
    new_root = ET.Element("tv", {"generator-info-name": "MiRobotEPG"})
    
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
                channel_id = c.get("id")
                if channel_id:
                    channel_id_clean = channel_id.strip()
                    if channel_id_clean in wanted_ids:
                        channels_found.append(c)
                        missing_ids.discard(channel_id_clean)
            
            # Buscar programas (Soporta validación limpia del atributo de canal)
            for p in tree.findall("programme"):
                p_channel = p.get("channel")
                if p_channel:
                    p_channel_clean = p_channel.strip()
                    if p_channel_clean in wanted_ids:
                        programmes_found.append(p)
                    
        except Exception as e:
            print(f"Omitiendo fuente {url} por error: {e}")

    # Unir todo en el nuevo XML sin duplicados
    unique_channels = {c.get("id").strip(): c for c in channels_found}.values()
    for c in unique_channels:
        new_root.append(c)
    for p in programmes_found:
        new_root.append(p)

    # 1. Guardar el archivo XML normal
    output_xml = "guia_personalizada.xml"
    tree_out = ET.ElementTree(new_root)
    tree_out.write(output_xml, encoding="utf-8", xml_declaration=True)
    print(f"¡Listo! Archivo {output_xml} generado.")

    # 2. Guardar el archivo XML comprimido (.gz)
    output_gz = "guia_personalizada.xml.gz"
    try:
        with open(output_xml, "rb") as f_in:
            with gzip.open(output_gz, "wb") as f_out:
                f_out.writelines(f_in)
        print(f"¡Listo! Archivo comprimido {output_gz} generado.")
    except Exception as e:
        print(f"Error al comprimir: {e}")

    # 3. Guardar el archivo de errores actualizado
    output_errors = "errores canales.txt"
    try:
        with open(output_errors, "w", encoding="utf-8") as f_err:
            if missing_ids:
                for missing_id in sorted(missing_ids):
                    f_err.write(f"{missing_id}\n")
                print(f"Se generó '{output_errors}' con {len(missing_ids)} errores restantes.")
            else:
                f_err.write("¡Felicidades! Todos los canales fueron encontrados con éxito.\n")
                print("Todos los canales coinciden perfectamente.")
    except Exception as e:
        print(f"Error al guardar errores: {e}")

if __name__ == "__main__":
    run()
