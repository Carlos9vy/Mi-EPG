import xml.etree.ElementTree as ET
import requests
import os
import gzip

EPG_SOURCES = ["https://iptv-epg.org/files/epg-ztjwyq.xml"]
CANALES_FILE = "canales.txt"
OUTPUT_FILE = "epg_reducida.xml"
LOG_ERRORES = "errores_canales.txt"

def filter_epg():
    if not os.path.exists(CANALES_FILE):
        return

    with open(CANALES_FILE, 'r', encoding='utf-8') as f:
        whitelist = set(line.strip() for line in f if line.strip())
    
    # Creamos un conjunto para rastrear qué canales VAMOS ENCONTRANDO
    canales_encontrados = set()

    new_tv = ET.Element('tv', {
        'source-info-name': 'Mi EPG Personalizada',
        'source-info-url': 'https://iptv-epg.org'
    })

    headers = {'User-Agent': 'Mozilla/5.0'}

    for url in EPG_SOURCES:
        try:
            r = requests.get(url, headers=headers, timeout=60)
            r.raise_for_status()
            content = gzip.decompress(r.content) if (url.endswith(".gz") or r.content[:2] == b'\x1f\x8b') else r.content
            tree = ET.fromstring(content)
            
            for channel in tree.findall('channel'):
                cid = channel.get('id')
                if cid in whitelist:
                    new_tv.append(channel)
                    canales_encontrados.add(cid) # <--- Lo marcamos como encontrado
            
            for programme in tree.findall('programme'):
                if programme.get('channel') in whitelist:
                    new_tv.append(programme)

        except Exception as e:
            print(f"Error: {e}")

    # Guardar EPG
    final_tree = ET.ElementTree(new_tv)
    ET.indent(final_tree, space="  ", level=0)
    final_tree.write(OUTPUT_FILE, encoding='utf-8', xml_declaration=True)

    # --- Lógica de Notificación de Errores ---
    # Los que están en whitelist pero NO en canales_encontrados son los errores
    canales_con_error = whitelist - canales_encontrados

    with open(LOG_ERRORES, 'w', encoding='utf-8') as f:
        if canales_con_error:
            f.write("⚠️ CANALES NO ENCONTRADOS EN LAS FUENTES:\n")
            f.write("Revisa si el ID cambió o si hay un error de escritura.\n")
            f.write("==================================================\n\n")
            for canal in sorted(canales_con_error):
                f.write(f"- {canal}\n")
        else:
            f.write("✅ ¡Felicidades! Todos tus canales fueron encontrados correctamente.")

if __name__ == "__main__":
    filter_epg()
