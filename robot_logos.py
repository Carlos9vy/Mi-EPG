import os
import shutil
from PIL import Image

# --- CONFIGURACIÓN ---
CARPETA_ORIGEN = "logos"
CARPETA_DESTINO = "logos_estandar"
ARCHIVO_URLS = "urls_estandarizadas.txt"

# Detección automática del repositorio en GitHub para la URL Raw
USUARIO_REPO = os.getenv("GITHUB_REPOSITORY", "TU_USUARIO/TU_REPO")
URL_BASE_GITHUB = f"https://raw.githubusercontent.com/{USUARIO_REPO}/main/{CARPETA_DESTINO}/"

# Tamaño estándar global para IPTV (Ancho, Alto)
TAMANO_ESTANDAR = (400, 225)

def limpiar_y_preparar_entorno():
    """Borra el contenido previo de la carpeta de destino y el archivo de texto si ya existen."""
    print("🧹 Limpiando residuos de ejecuciones anteriores...")
    
    # Eliminar carpeta de destino vieja si existe (La carpeta origen 'logos' NO se toca)
    if os.path.exists(CARPETA_DESTINO):
        shutil.rmtree(CARPETA_DESTINO)
        print(f"✔ Carpeta antigua '{CARPETA_DESTINO}' eliminada de raíz.")
    
    # Volver a crear la carpeta de destino vacía
    os.makedirs(CARPETA_DESTINO, exist_ok=True)
    
    # Eliminar el archivo de texto viejo si existe
    if os.path.exists(ARCHIVO_URLS):
        os.remove(ARCHIVO_URLS)
        print(f"✔ Archivo antiguo '{ARCHIVO_URLS}' eliminado.")

def estandarizar_logos():
    # Validar si la carpeta de origen existe o está vacía
    if not os.path.exists(CARPETA_ORIGEN) or not os.listdir(CARPETA_ORIGEN):
        print(f"⚠ La carpeta de origen '{CARPETA_ORIGEN}' no existe o está vacía. Proceso detenido.")
        return

    # Ejecutar la limpieza justo antes de empezar a procesar
    limpiar_y_preparar_entorno()

    # Abrir el nuevo archivo de texto en modo escritura
    with open(ARCHIVO_URLS, "w", encoding="utf-8") as f_urls:
        
        # Ordenar alfabéticamente los logos de origen
        archivos = sorted(os.listdir(CARPETA_ORIGEN))
        
        for archivo in archivos:
            # Filtrar formatos de imagen compatibles
            if archivo.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp')):
                ruta_origen = os.path.join(CARPETA_ORIGEN, archivo)
                
                # Forzar formato de salida a PNG para soportar transparencias
                nombre_base = os.path.splitext(archivo)[0]
                nuevo_nombre = f"{nombre_base}.png"
                ruta_destino = os.path.join(CARPETA_DESTINO, nuevo_nombre)
                
                try:
                    with Image.open(ruta_origen) as img:
                        # Convertir a RGBA para canales de transparencia completos
                        img = img.convert("RGBA")
                        
                        # Recortar espacios vacíos (arriba, abajo, izquierda y derecha)
                        # getbbox() analiza los píxeles no transparentes (o no uniformes) y devuelve los límites (izq, sup, der, inf)
                        caja_recorte = img.getbbox()
                        if caja_recorte:
                            img = img.crop(caja_recorte)
                        
                        # Cambiar tamaño de forma proporcional (Filtro Lanczos de alta nitidez)
                        img.thumbnail(TAMANO_ESTANDAR, Image.Resampling.LANCZOS)
                        
                        # Crear lienzo nuevo transparente de 400x225
                        lienzo_nuevo = Image.new("RGBA", TAMANO_ESTANDAR, (0, 0, 0, 0))
                        
                        # Calcular coordenadas para centrar perfectamente el logo ya recortado
                        posicion_x = (TAMANO_ESTANDAR[0] - img.size[0]) // 2
                        posicion_y = (TAMANO_ESTANDAR[1] - img.size[1]) // 2
                        
                        # Pegar usando el canal alfa del propio logo como máscara
                        lienzo_nuevo.paste(img, (posicion_x, posicion_y), img)
                        
                        # Guardar el archivo PNG optimizado en peso
                        lienzo_nuevo.save(ruta_destino, "PNG", optimize=True)
                    
                    # Codificar URL formateando los espacios vacíos como '%20'
                    url_logo = f"{URL_BASE_GITHUB}{nuevo_nombre}".replace(" ", "%20")
                    
                    # Escribir línea en formato estándar: NombreCanal = URL
                    f_urls.write(f"{nombre_base} = {url_logo}\n")
                    print(f"✔ Procesado y recortado: {nuevo_nombre}")
                    
                except Exception as e:
                    print(f"❌ Error al procesar {archivo}: {e}")

if __name__ == "__main__":
    print("=== INICIANDO ROBOT DE OPTIMIZACIÓN Y RECORTE DE LOGOS ===")
    estandarizar_logos()
    print("=== PROCESO FINALIZADO CON ÉXITO ===")
