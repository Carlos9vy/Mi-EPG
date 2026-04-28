import xml.etree.ElementTree as ET
import requests
import gzip
import io
import os
import urllib.parse
from PIL import Image

# Configuración
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
ANCHO, ALTO = 400, 225

def procesar_imagen_estandar(contenido_img, ruta_destino):
    try:
        img = Image.open(io.BytesIO(contenido_img)).convert("RGBA")
        img.thumbnail((ANCHO, ALTO), Image.Resampling.LANCZOS)
        lienzo = Image.new("RGBA", (ANCHO, ALTO), (0, 0, 0, 0))
        offset = ((ANCHO - img.width) // 2, (ALTO - img.height) // 2)
        lienzo.paste(img, offset, img)
        lienzo.save(ruta_destino, "PNG")
        return True
    except:
        return False

def ejecutar_prueba():
    if not os.path.exists(CARPETA_PRUEBA):
        os.makedirs(CARPETA_PRUEBA)
    with open(os.path.join(CARPETA_PRUEBA, ".keep"), "w") as f:
        f.write("keep")

    if not os.path.exists(CANALES_FILE):
        print(f"ERROR: No se encontró {CANALES_FILE}")
        return

    with open(CANALES_FILE, 'r', encoding='utf-8') as f:
        whitelist = [line.strip() for line in f if line.strip()]

    logos_dict = {}
    for url in EPG_SOURCES:
        try:
            r = requests.get(url, timeout=25)
            content = gzip.decompress(r.content) if r.content[:2] == b'\x1f\x8b' else r.content
            context = ET.iterparse(io.BytesIO(content), events=('end',))
            for _, elem in context:
                if elem.tag == 'channel':
                    cid = elem.get('id')
                    if cid in whitelist and cid not in logos_dict:
                        icon = elem.find('icon')
                        if icon is not None:
                            logos_dict[cid] = icon.get('src')
                elem.clear()
        except:
            continue

    nuevas_urls = []
    conteo_exito = 0
    for cid in whitelist:
        if cid in logos_dict:
            nombre_limpio = "".join([c if c.isalnum() or c in "._-" else "_" for c in cid])
            nombre_archivo = f"{nombre_limpio}_std.png"
            ruta_final = os.path.join(CARPETA_PRUEBA, nombre_archivo)
            
            try:
                r_img = requests.get(logos_dict[cid], timeout=15)
                if r_img.status_code == 200:
                    if procesar_imagen_estandar(r_img.content, ruta_final):
                        # LINEA CORREGIDA (Sin cortes)
                        url_raw = f"https://raw.githubusercontent.com/{REPO}/main/{CARPETA_PRUEBA}/{urllib.parse.quote(nombre_archivo)}"
                        nuevas_urls.append(f"{cid} -> {url_raw}\n")
                        conteo_exito += 1
            except:
                continue
    
    with open(LISTA_PRUEBA, 'w', encoding='utf-8') as f:
        f.writelines(nuevas_urls)
    
    print(f"--- REPORTE FINAL ---")
    print(f"Canales cargados: {len(whitelist)}")
    print(f"Logos encontrados: {len(logos_dict)}")
    print(f"Logos procesados: {conteo_exito}")

if __name__ == "__main__":
    ejecutar_prueba()
