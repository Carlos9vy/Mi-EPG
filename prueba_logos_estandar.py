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

    # Leer canales solicitados
    with open(CANALES_FILE, 'r', encoding='utf-8') as f:
        whitelist = [line.strip() for line in f if line.strip()]

    # --- NUEVA LÓGICA: Filtrar solo lo que falta ---
    canales_pendientes = []
    for cid in whitelist:
        nombre_archivo = f"{cid}.png".replace(" ", "_").replace(":", "_")
        ruta_archivo = os.path.join(CARPETA_PRUEBA, nombre_archivo)
        if not os.path.exists(ruta_archivo):
            canales_pendientes.append(cid)
    
    if not canales_pendientes:
        print("¡Todo al día! No hay logos nuevos que descargar.")
        # Re-generamos la lista de URLs de todos modos por si acaso
    else:
        print(f"Detectados {len(canales_pendientes)} logos nuevos para procesar.")

    logos_dict = {}
    headers = {'User-Agent': 'Mozilla/5.0'}

    # Solo buscamos en el XML los que nos faltan
    for url in EPG_SOURCES:
        if len(logos_dict) == len(canales_pendientes): break
        try:
            print(f"Buscando faltantes en: {url.split('/')[-1]}")
            r = requests.get(url, headers=headers, timeout=45)
            xml_data = gzip.decompress(r.content) if r.content[:2] == b'\x1f\x8b' else r.content
            root = ET.fromstring(xml_data)
            
            for channel in root.findall('channel'):
                cid = channel.get('id')
                if cid in canales_pendientes and cid not in logos_dict:
                    icon = channel.find('icon')
                    if icon is not None:
                        src = icon.get('src')
                        if src:
                            logos_dict[cid] = src
                            print(f" -> Encontrado nuevo: {cid}")
        except: continue

    # Procesar descargas de los nuevos
    for cid, url_logo in logos_dict.items():
        nombre_archivo = f"{cid}.png".replace(" ", "_").replace(":", "_")
        ruta_final = os.path.join(CARPETA_PRUEBA, nombre_archivo)
        try:
            r_img = requests.get(url_logo, timeout=20, headers=headers)
            if r_img.status_code == 200:
                procesar_imagen_estandar(r_img.content, ruta_final)
        except: continue
    
    # ACTUALIZAR LISTA DE TXT (Con todos: viejos y nuevos)
    nuevas_urls = []
    for cid in whitelist:
        nombre_archivo = f"{cid}.png".replace(" ", "_").replace(":", "_")
        ruta_archivo = os.path.join(CARPETA_PRUEBA, nombre_archivo)
        if os.path.exists(ruta_archivo):
            url_raw = f"https://raw.githubusercontent.com/{REPO}/main/{CARPETA_PRUEBA}/{urllib.parse.quote(nombre_archivo)}"
            nuevas_urls.append(f"{cid} -> {url_raw}")

    with open(LISTA_PRUEBA, 'w', encoding='utf-8') as f:
        f.write("\n".join(nuevas_urls))
    
    print(f"Proceso finalizado. Total de logos en carpeta: {len(nuevas_urls)}")

if __name__ == "__main__":
    ejecutar()
