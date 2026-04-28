import xml.etree.ElementTree as ET
import requests
import gzip
import io
import os
import urllib.parse
from PIL import Image

# Fuentes originales
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

    # LEER Y LIMPIAR CANALES (QUITANDO \r y espacios)
    with open(CANALES_FILE, 'rb') as f:
        content = f.read().decode('utf-8-sig', errors='ignore')
        whitelist = [line.strip().replace('\r', '') for line in content.split('\n') if line.strip()]

    print(f"Cargados {len(whitelist)} canales. Ejemplo del primero: '{whitelist[0]}'")

    logos_dict = {}
    headers = {'User-Agent': 'Mozilla/5.0'}

    for url in EPG_SOURCES:
        try:
            print(f"Escaneando fuente: {url.split('/')[-1]}")
            r = requests.get(url, headers=headers, timeout=30)
            xml_content = gzip.decompress(r.content) if r.content[:2] == b'\x1f\x8b' else r.content
            
            # Usamos iterparse para ser eficientes
            context = ET.iterparse(io.BytesIO(xml_content), events=('end',))
            for _, elem in context:
                if elem.tag == 'channel':
                    xml_id = elem.get('id')
                    # COMPARACIÓN DIRECTA (Como en tus robots viejos)
                    if xml_id in whitelist and xml_id not in logos_dict:
                        icon = elem.find('icon')
                        if icon is not None:
                            src = icon.get('src')
                            if src:
                                logos_dict[xml_id] = src
                                print(f" -> MATCH: {xml_id}")
                elem.clear()
        except: continue

    nuevas_urls = []
    print(f"Total encontrados: {len(logos_dict)}. Iniciando descargas...")

    for cid in whitelist:
        if cid in logos_dict:
            nombre_archivo = f"{cid}.png".replace(" ", "_").replace(":", "_")
            ruta_final = os.path.join(CARPETA_PRUEBA, nombre_archivo)
            try:
                r_img = requests.get(logos_dict[cid], timeout=15)
                if r_img.status_code == 200 and procesar_imagen_estandar(r_img.content, ruta_final):
                    url_raw = f"https://raw.githubusercontent.com/{REPO}/main/{CARPETA_PRUEBA}/{urllib.parse.quote(nombre_archivo)}"
                    nuevas_urls.append(f"{cid} -> {url_raw}")
            except: continue
    
    if nuevas_urls:
        with open(LISTA_PRUEBA, 'w', encoding='utf-8') as f:
            f.write("\n".join(nuevas_urls))
        print(f"FINAL: {len(nuevas_urls)} logos creados.")
    else:
        print("FINAL: No se generó nada.")

if __name__ == "__main__":
    ejecutar()
