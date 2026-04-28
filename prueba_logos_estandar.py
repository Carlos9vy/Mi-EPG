import xml.etree.ElementTree as ET
import requests
import gzip
import io
import os
import urllib.parse
from PIL import Image

# Configuración de prueba
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
    "https://iptv-epg.org/files/epg-pa.xml",
    "https://www.open-epg.com/generate/aYzuzNSenh.xml.gz" 
]

CANALES_FILE = "canales.txt"
CARPETA_PRUEBA = "logos_estandar" # Carpeta nueva
LISTA_PRUEBA = "urls_estandarizadas.txt" # Archivo nuevo
REPO = os.getenv('GITHUB_REPOSITORY')

# Tamaño estándar 16:9
ANCHO, ALTO = 400, 225

def procesar_imagen_estandar(contenido_img, ruta_destino):
    try:
        img = Image.open(io.BytesIO(contenido_img)).convert("RGBA")
        # Mantener proporción (Fit)
        img.thumbnail((ANCHO, ALTO), Image.Resampling.LANCZOS)
        # Crear lienzo transparente exacto
        lienzo = Image.new("RGBA", (ANCHO, ALTO), (0, 0, 0, 0))
        # Centrar la imagen en el molde
        offset = ((ANCHO - img.width) // 2, (ALTO - img.height) // 2)
        lienzo.paste(img, offset, img)
        lienzo.save(ruta_destino, "PNG")
        return True
    except:
        return False

def ejecutar_prueba():
    if not os.path.exists(CANALES_FILE): return
    if not os.path.exists(CARPETA_PRUEBA): os.makedirs(CARPETA_PRUEBA)

    with open(CANALES_FILE, 'r', encoding='utf-8') as f:
        whitelist = [line.strip() for line in f if line.strip()]

    logos_dict = {}
    headers = {'User-Agent': 'Mozilla/5.0'}

    # Buscar URLs
    for url in EPG_SOURCES:
        try:
            print(f"Buscando logos en: {url.split('/')[-1]}")
            r = requests.get(url, headers=headers, timeout=30)
            content = gzip.decompress(r.content) if (url.endswith(".gz") or r.content[:2] == b'\x1f\x8b') else r.content
            context = ET.iterparse(io.BytesIO(content), events=('end',))
            for event, elem in context:
                if elem.tag == 'channel':
                    cid = elem.get('id')
                    if cid in whitelist and cid not in logos_dict:
                        icon = elem.find('icon')
                        if icon is not None:
                            logos_dict[cid] = icon.get('src')
                elem.clear()
        except: continue

    # Descargar y Normalizar
    nuevas_urls = []
    for cid in whitelist:
        if cid in logos_dict:
            nombre_archivo = f"{cid}_std.png".replace(" ", "_") # Sufijo _std para diferenciar
            ruta_final = os.path.join(CARPETA_PRUEBA, nombre_archivo)
            
            try:
                print(f"Normalizando: {cid}")
                r_img = requests.get(logos_dict[cid], timeout=10)
                if r_img.status_code == 200:
                    if procesar_imagen_estandar(r_img.content, ruta_final):
                        url_raw = f"https://raw.githubusercontent.com/{REPO}/main/{CARPETA_PRUEBA}/{urllib.parse.quote(nombre_archivo)}"
                        nuevas_urls.append(f"{cid} -> {url_raw}\n")
            except: continue
    
    with open(LISTA_PRUEBA, 'w', encoding='utf-8') as f:
        f.writelines(nuevas_urls)
    print(f"Prueba completada. Revisa la carpeta {CARPETA_PRUEBA}")

if __name__ == "__main__":
    ejecutar_prueba()
