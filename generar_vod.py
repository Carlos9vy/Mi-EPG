import requests
import os

# --- CONFIGURACIÓN ---
API_KEY = "35808c87beebe2b0aaa71aeeccd1caf8" # Pon tu clave aquí
ID_SERIE_TMDB = "242131"     # ID de la serie (The Pitt es 242131)
TEMPORADA = 1
NOMBRE_ARCHIVO = "serie_personalizada.m3u"

def generar_m3u():
    # Consultamos a TMDB en español
    url = f"https://api.themoviedb.org/3/tv/{ID_SERIE_TMDB}/season/{TEMPORADA}?api_key={API_KEY}&language=es-ES"
    
    try:
        response = requests.get(url)
        datos = response.json()
        
        if 'episodes' not in datos:
            print("No se encontró la serie. Revisa el ID.")
            return

        with open(NOMBRE_ARCHIVO, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n\n")
            
            for ep in datos['episodes']:
                num = ep['episode_number']
                name = ep['name']
                desc = ep['overview'] or "Sin descripción en español."
                # Imagen del episodio
                img = f"https://image.tmdb.org/t/p/w500{ep['still_path']}" if ep['still_path'] else ""
                
                f.write(f'#EXTINF:-1 tvg-id="ep-{num}" tvg-logo="{img}" group-title="Serie Personalizada", {num}. {name}\n')
                f.write(f'#EXTVODDESC: {desc}\n')
                f.write(f'http://tuservidor.com/video_s1_e{num}.mp4\n\n')

        print(f"✅ ¡Listo! Creado el archivo {NOMBRE_ARCHIVO}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    generar_m3u()
