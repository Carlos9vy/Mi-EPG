import xml.etree.ElementTree as ET
import requests
import gzip
import io
import os
import urllib.parse
import time
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
CARPETA_PRUEBA = "logos_estandar"
LISTA_PRUEBA = "urls_estandarizadas.txt"
REPO = os.getenv('GITHUB_REPOSITORY')

# Tamaño estándar 16:9 para evitar deformaciones
ANCHO, ALTO = 400, 225

def procesar_imagen_estandar(contenido_img, ruta_destino):
    try:
        img = Image.open(io.BytesIO(contenido_img)).convert("RGBA")
        # Mantener proporción sin estirar (Fit)
        img.thumbnail((ANCHO, ALTO), Image.Resampling.LANCZOS)
        # Crear lienzo transparente exacto
        lienzo = Image.new("RGBA", (ANCHO, ALTO), (0, 0, 0, 0))
        # Centrar la imagen en el lienzo
        offset = ((ANCHO - img.width) // 2, (ALTO - img.height) // 2)
        lienzo.paste(img, offset, img)
        lienzo.save(ruta_destino, "PNG")
        return True
    except Exception as e:
        print(f"Error procesando imagen: {e}")
        return False

def ejecutar_prueba():
    if not os.path.exists(CANALES_FILE):
        print(f"Error: No existe el archivo {CANALES_FILE}")
        return
        
    if not os.path.exists(CARPETA_PRUEBA):
        os.makedirs(CARPETA_PRUEBA)

    with open(CANALES_FILE, 'r', encoding='utf-8') as f:
        whitelist = [line.strip() for line in f if line.strip()]

    logos_dict = {}
    headers = {'User-Agent': 'Mozilla/5.0'}

    # 1. Buscar URLs en las fuentes EPG
    for url in EPG_SOURCES:
        try:
            print(f"Escaneando logos en: {url.split('/')[-1]}")
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

    # 2. Descargar, Normalizar y Generar lista
    nuevas_urls = []
    conteo_exito = 0
    
    for cid in whitelist:
        if cid in logos_dict:
            # Limpiar nombre de archivo (evitar espacios y caracteres raros)
            nombre_limpio = "".join([c if c.isalnum() or c in "._-" else "_" for c in cid])
            nombre_archivo = f"{nombre_limpio}_std.png"
            ruta_final = os.path.join(CARPETA_PRUEBA, nombre_archivo)
            
            try:
                print(f"Procesando: {cid}")
                r_img = requests.get(logos_dict[cid], timeout=15)
                if r_img.status_code == 200:
                    if procesar_imagen_estandar(r_img.content, ruta_final):
                        url_raw = f"https://raw.githubusercontent.com/{REPO}/main/{CARPETA_PRUEBA}/{urllib.parse.quote(nombre_archivo)}"
                        nuevas_urls.append(f"{cid} -> {url_raw}\n")
                        conteo_exito += 1
            except Exception as e:
                print(f"Falla en {cid}: {e}")
                continue
    
    # Escribir el archivo de texto
    with open(LISTA_PRUEBA, 'w', encoding='utf-8') as f:
        f.writelines(nuevas_urls)
    
    print(f"\n--- REPORTE DE EJECUCIÓN ---")
    print(f"Canales en lista: {len(whitelist)}")
    print(f"Logos encontrados en fuentes: {len(logos_dict)}")
    print(f"Logos procesados y guardados: {conteo_exito}")
    print(f"Archivo de URLs listo: {os.path.exists(LISTA_PRUEBA)}")

if __name__ == "__main__":
    ejecutar_prueba()
