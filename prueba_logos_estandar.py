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
    except Exception as e:
        print(f"      [!] Error Pillow: {e}")
        return False

def ejecutar_prueba():
    if not os.path.exists(CARPETA_PRUEBA): os.makedirs(CARPETA_PRUEBA)

    if not os.path.exists(CANALES_FILE):
        print(f"ERROR FATAL: No se encuentra {CANALES_FILE}")
        return

    with open(CANALES_FILE, 'r', encoding='utf-8') as f:
        whitelist = [line.strip() for line in f if line.strip()]
    
    print(f"--- PASO 1: Cargados {len(whitelist)} IDs de canales.txt ---")
    for c in whitelist: print(f"  ID a buscar: '{c}'")

    logos_dict = {}
    headers = {'User-Agent': 'Mozilla/5.0'}

    for url in EPG_SOURCES:
        try:
            print(f"--- PASO 2: Escaneando {url.split('/')[-1]} ---")
            r = requests.get(url, headers=headers, timeout=30)
            content = gzip.decompress(r.content) if r.content[:2] == b'\x1f\x8b' else r.content
            context = ET.iterparse(io.BytesIO(content), events=('end',))
            for _, elem in context:
                if elem.tag == 'channel':
                    cid = elem.get('id')
                    if cid in whitelist and cid not in logos_dict:
                        icon = elem.find('icon')
                        if icon is not None:
                            src = icon.get('src')
                            logos_dict[cid] = src
                            print(f"    [OK] Logo encontrado para: {cid}")
                elem.clear()
        except Exception as e:
            print(f"    [X] Error en fuente: {e}")

    print(f"--- PASO 3: Descargando {len(logos_dict)} logos encontrados ---")
    nuevas_urls = []
    for cid in whitelist:
        if cid in logos_dict:
            nombre_archivo = f"{cid}.png".replace(" ", "_")
            ruta_final = os.path.join(CARPETA_PRUEBA, nombre_archivo)
            
            try:
                print(f"    -> Descargando imagen para {cid} desde {logos_dict[cid][:50]}...")
                r_img = requests.get(logos_dict[cid], timeout=15)
                if r_img.status_code == 200:
                    if procesar_imagen_estandar(r_img.content, ruta_final):
                        url_raw = f"https://raw.githubusercontent.com/{REPO}/main/{CARPETA_PRUEBA}/{urllib.parse.quote(nombre_archivo)}"
                        nuevas_urls.append(f"{cid} -> {url_raw}")
                        print(f"       [EXITO] Imagen guardada y URL generada.")
                else:
                    print(f"       [FALLO] HTTP {r_img.status_code}")
            except Exception as e:
                print(f"       [ERROR] {e}")
    
    if nuevas_urls:
        with open(LISTA_PRUEBA, 'w', encoding='utf-8') as f:
            f.write("\n".join(nuevas_urls))
        print(f"\nFIN: Se generaron {len(nuevas_urls)} URLs correctamente.")
    else:
        print("\nFIN: No se generó nada. Revisa los pasos anteriores para ver donde falló.")

if __name__ == "__main__":
    ejecutar_prueba()
