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
    except: return False

def ejecutar_prueba():
    if not os.path.exists(CARPETA_PRUEBA): os.makedirs(CARPETA_PRUEBA)

    if not os.path.exists(CANALES_FILE):
        print("ERROR: canales.txt no encontrado.")
        return

    # Cargamos canales y creamos una versión "limpia" para comparar
    with open(CANALES_FILE, 'r', encoding='utf-8') as f:
        original_channels = [line.strip() for line in f if line.strip()]
    
    # Diccionario: { "id_limpio": "ID_Original" }
    whitelist_clean = {c.lower().replace(" ", ""): c for c in original_channels}
    
    logos_dict = {} # Guardará { "ID_Original": "URL_Logo" }
    headers = {'User-Agent': 'Mozilla/5.0'}

    print(f"--- Iniciando búsqueda flexible para {len(original_channels)} canales ---")

    for url in EPG_SOURCES:
        try:
            r = requests.get(url, headers=headers, timeout=30)
            content = gzip.decompress(r.content) if r.content[:2] == b'\x1f\x8b' else r.content
            context = ET.iterparse(io.BytesIO(content), events=('end',))
            for _, elem in context:
                if elem.tag == 'channel':
                    xml_id = elem.get('id')
                    if xml_id:
                        # Limpiamos el ID que viene del XML para comparar
                        xml_id_clean = xml_id.lower().replace(" ", "")
                        
                        if xml_id_clean in whitelist_clean:
                            id_real = whitelist_clean[xml_id_clean]
                            if id_real not in logos_dict:
                                icon = elem.find('icon')
                                if icon is not None:
                                    src = icon.get('src')
                                    if src:
                                        logos_dict[id_real] = src
                                        print(f"  [OK] Encontrado: {id_real}")
                elem.clear()
        except: continue

    nuevas_urls = []
    exitos = 0
    
    print(f"--- Iniciando descarga de {len(logos_dict)} logos ---")
    for cid in original_channels:
        if cid in logos_dict:
            nombre_archivo = "".join([c if c.isalnum() or c in "._-" else "_" for c in cid]) + ".png"
            ruta_final = os.path.join(CARPETA_PRUEBA, nombre_archivo)
            
            try:
                r_img = requests.get(logos_dict[cid], timeout=15, headers=headers)
                if r_img.status_code == 200:
                    if procesar_imagen_estandar(r_img.content, ruta_final):
                        url_raw = f"https://raw.githubusercontent.com/{REPO}/main/{CARPETA_PRUEBA}/{urllib.parse.quote(nombre_archivo)}"
                        nuevas_urls.append(f"{cid} -> {url_raw}")
                        exitos += 1
            except: continue
    
    if nuevas_urls:
        with open(LISTA_PRUEBA, 'w', encoding='utf-8') as f:
            f.write("\n".join(nuevas_urls))
        print(f"\nFINALIZADO: {exitos} logos generados en '{CARPETA_PRUEBA}'")
    else:
        print("\nERROR: No se encontró ningún match. Revisa si los IDs en canales.txt coinciden con las fuentes.")

if __name__ == "__main__":
    ejecutar_prueba()
