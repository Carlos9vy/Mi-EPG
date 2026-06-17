import requests
import xml.etree.ElementTree as ET
import gzip
import re
import json
import os

# Las fuentes de televisión
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
    "https://github.com/Carlos9vy/mi-laboratorio-epg/raw/refs/heads/main/guia_laboratory.xml",
    "https://www.open-epg.com/generate/aYzuzNSenh.xml",
    "https://epgshare01.online/epgshare01/epg_ripper_SV1.xml.gz"
]

def extraer_plantilla_json():
    lista_ids_ordenadas = []
    titulos_por_canal_nuevos = {}
    titulos_por_canal_existentes = {}
    db_titulos_puros = {}

    # 1. Leer tus canales autorizados preservando el orden exacto del archivo
    try:
        with open("canales_ia.txt", "r", encoding="utf-8") as f:
            for line in f:
                line_clean = line.strip()
                if line_clean and line_clean not in lista_ids_ordenadas:
                    lista_ids_ordenadas.append(line_clean)
                    # Inicializamos los contenedores para este canal
                    titulos_por_canal_nuevos[line_clean] = set()
                    titulos_por_canal_existentes[line_clean] = {}
        print(f"📋 Cargados {len(lista_ids_ordenadas)} canales en orden desde canales_ia.txt")
    except FileNotFoundError:
        print("❌ Error: Necesitas tener el archivo 'canales_ia.txt' en la misma carpeta.")
        return

    if not lista_ids_ordenadas:
        return

    # 2. LEER LA BASE DE DATOS ACTUAL (Extraer datos puros ignorando encabezados viejos)
    base_datos_real = "descripciones_ia.json"
    if os.path.exists(base_datos_real):
        try:
            with open(base_datos_real, "r", encoding="utf-8") as f_db:
                data_db = json.load(f_db)
                for titulo, descripcion in data_db.items():
                    # Ignoramos cualquier encabezado previo para no ensuciar la lectura
                    if not (titulo.startswith("====== CANAL:") or descripcion == "----------------------------------------"):
                        db_titulos_puros[titulo] = descripcion
            print(f"🧠 Base de datos detectada: Leyendo {len(db_titulos_puros)} títulos existentes.")
        except Exception as e:
            print(f"⚠️ No se pudo leer '{base_datos_real}'. Se procesará como nueva. Error: {e}")

    # 3. Descargar y escanear canales internacionales
    print("🛰️ Escaneando guías para buscar programación y clasificar canales...")
    for url in SOURCES:
        try:
            r = requests.get(url, timeout=45)
            if url.endswith(".gz"):
                data = gzip.decompress(r.content)
                xml_text = data.decode("utf-8", errors="ignore")
            else:
                xml_text = r.text

            xml_text = re.sub(r'&(?!([a-zA-Z0-9]+|#[0-9]+|#x[a-fA-F0-9]+);)', '&amp;', xml_text)
            tree = ET.fromstring(xml_text.encode("utf-8"))
            
            for p in tree.findall("programme"):
                p_channel = p.get("channel")
                if p_channel:
                    p_channel_clean = p_channel.strip()
                    
                    if p_channel_clean in lista_ids_ordenadas:
                        title_elem = p.find("title")
                        if title_elem is not None and title_elem.text:
                            titulo_limpio = title_elem.text.strip()
                            
                            if titulo_limpio:
                                # Caso A: El título ya tiene descripción en la DB
                                if titulo_limpio in db_titulos_puros and db_titulos_puros[titulo_limpio].strip():
                                    titulos_por_canal_existentes[p_channel_clean][titulo_limpio] = db_titulos_puros[titulo_limpio]
                                # Caso B: Es un título nuevo (vacío o no registrado)
                                else:
                                    titulos_por_canal_nuevos[p_channel_clean].add(titulo_limpio)
                            
        except Exception:
            continue

    # 4. REORGANIZAR Y AGRUPAR LA BASE DE DATOS REAL (descripciones_ia.json)
    db_reorganizada = {}
    for canal_id in lista_ids_ordenadas:
        dicc_existente = titulos_por_canal_existentes[canal_id]
        
        # Si este canal tiene descripciones guardadas, le creamos su bloque visual ordenado
        if dicc_existente:
            encabezado_seguro = f"====== CANAL: {canal_id} ======"
            db_reorganizada[encabezado_seguro] = "----------------------------------------"
            
            # Ordenamos alfabéticamente los títulos guardados de este canal
            for t in sorted(dicc_existente.keys()):
                db_reorganizada[t] = dicc_existente[t]

    # Guardar la Base de Datos ya pulida y acomodada
    with open(base_datos_real, "w", encoding="utf-8") as f_db_out:
        json.dump(db_reorganizada, f_db_out, ensure_ascii=False, indent=4)
    print(f"✨ ¡Base de datos '{base_datos_real}' reordenada y separada por ID con éxito!")

    # 5. CONSTRUIR EL BORRADOR SÓLO CON LAS NOVEDADES
    plantilla_borrador = {}
    total_novedades = 0

    for canal_id in lista_ids_ordenadas:
        set_nuevos = titulos_por_canal_nuevos[canal_id]
        # Nos aseguramos de eliminar del borrador cosas que por error se marquen como nuevas pero ya existan
        titulos_del_canal = sorted([t for t in set_nuevos if t not in db_reorganizada])
        
        if titulos_del_canal:
            encabezado_seguro = f"====== CANAL: {canal_id} ======"
            plantilla_borrador[encabezado_seguro] = "----------------------------------------"
            
            for t in titulos_del_canal:
                plantilla_borrador[t] = ""
                total_novedades += 1

    # Guardar el archivo borrador estructurado
    output_file = "borrador_titulos.json"
    if total_novedades > 0:
        with open(output_file, "w", encoding="utf-8") as f_out:
            json.dump(plantilla_borrador, f_out, ensure_ascii=False, indent=4)
        print(f"🎉 ¡Filtrado completado! Se encontraron {total_novedades} títulos NUEVOS.")
        print(f"📁 Borrador de novedades generado: '{output_file}'")
    else:
        # Si no hay novedades, borramos el archivo borrador anterior para evitar confusiones
        if os.path.exists(output_file):
            os.remove(output_file)
        print("\n😎 ¡Al día! Todos los programas en emisión ya están organizados en la base de datos.")

if __name__ == "__main__":
    extraer_plantilla_json()
