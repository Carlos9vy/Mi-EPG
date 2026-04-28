import xml.etree.ElementTree as ET
import requests
import gzip
import io
import os
import urllib.parse
from PIL import Image

# Fuentes
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

CANALES_FILE = "canales.txt"
CARPETA_PRUEBA = "logos_estandar"
LISTA_PRUEBA = "urls_estandarizadas.txt"
REPO = os.getenv('GITHUB_REPOSITORY')

def procesar_imagen_estandar(contenido_img, ruta_destino):
    try:
        img = Image.open(io.BytesIO(contenido_img)).convert("RGBA")
        img.thumbnail((400, 225), Image.Resampling.LANCZOS)
        lienzo = Image.new("RGBA", (400, 225), (0, 0, 0, 0))
        offset = ((400 - img.width) // 2, (225 - img.height) // 2)
        lienzo.paste(img, offset, img)
        lienzo.save(ruta_destino, "PNG")
        return True
    except: return False

def ejecutar():
    if not os.path.exists(CARPETA_PRUEBA): os.makedirs(CARPETA_PRUEBA)
    if not os.path.exists(CANALES_FILE): return

    # Leer canales con limpieza total
    with open(CANALES_FILE, 'r', encoding='utf-8') as f:
        whitelist = [line.strip() for line in f if line.strip()]

    logos_dict = {}
    headers = {'User-Agent': 'Mozilla/5.0'}

    for url in EPG_SOURCES:
        try:
            print(f"Descargando fuente: {url.split('/')[-1]}")
            r = requests.get(url, headers=headers, timeout=45)
            # Descompresión manual para asegurar integridad
            if url.endswith(".gz") or r.content[:2] == b'\x1f\x8b':
                xml_data = gzip.decompress(r.content)
            else:
                xml_data = r.content
            
            # USAR EL MÉTODO TRADICIONAL (Más lento pero no falla)
            root = ET.fromstring(xml_data)
            
            for channel in root.findall('channel'):
                cid = channel.get('id')
                if cid in whitelist and cid not in logos_dict:
                    icon = channel.find('icon')
                    if icon is not None:
                        src = icon.get('src')
                        if src:
                            logos_dict[cid] = src
                            print(f" -> ¡LOGRADO!: {cid}")
        except Exception as e:
            print(f" -> Error en fuente {url.split('/')[-1]}: {e}")
            continue

    nuevas_urls = []
    print(f"--- Total de logos listos para procesar: {len(logos_dict)} ---")

    for cid in whitelist:
        if cid in logos_dict:
            nombre_archivo = f"{cid}.png".replace(" ", "_").replace(":", "_")
            ruta_final = os.path.join(CARPETA_PRUEBA, nombre_archivo)
            try:
                r_img = requests.get(logos_dict[cid], timeout=20, headers=headers)
                if r_img.status_code == 200:
                    if procesar_imagen_estandar(r_img.content, ruta_final):
                        url_raw = f"https://raw.githubusercontent.com/{REPO}/main/{CARPETA_PRUEBA}/{urllib.parse.quote(nombre_archivo)}"
                        nuevas_urls.append(f"{cid} -> {url_raw}")
            except: continue
    
    if nuevas_urls:
        with open(LISTA_PRUEBA, 'w', encoding='utf-8') as f:
            f.write("\n".join(nuevas_urls))
        print(f"FINALIZADO: {len(nuevas_urls)} logos creados con éxito.")
    else:
        print("FINALIZADO: No se pudo generar nada.")

if __name__ == "__main__":
    ejecutar()
