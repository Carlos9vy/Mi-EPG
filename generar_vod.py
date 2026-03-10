import requests
import os

# --- CONFIGURACIÓN ---
API_KEY = "TU_API_KEY_AQUI" # Pon aquí tu clave de TMDB
ID_SERIE_TMDB = "242131"     # ID de la serie "The Pitt"
TEMPORADA = 1
URL_BASE_VIDEO = "https://tu-servidor.com/videos/thepitt/s01e" # Ejemplo de base de tus links

def obtener_datos_serie():
    url = f"https://api.themoviedb.org/3/tv/{ID_SERIE_TMDB}/season/{TEMPORADA}?api_key={API_KEY}&language=es-ES"
    
    response = requests.get(url)
    if response.status_code != 200:
        print("Error al conectar con TMDB")
        return

    datos = response.json()
    episodios = datos['episodes']
    
    with open("serie_the_pitt.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n\n")
        
        for ep in episodios:
            n_ep = ep['episode_number']
            titulo = ep['name']
            sinopsis = ep['overview'] or "Sin descripción disponible."
            poster = f"https://image.tmdb.org/t/p/w500{ep['still_path']}"
            
            # Formato compatible con SmartOne (Netcast)
            f.write(f'#EXTINF:-1 tvg-id="pitt-{TEMPORADA}x{n_ep}" tvg-logo="{poster}" group-title="The Pitt", {n_ep}. {titulo}\n')
            f.write(f'#EXTVODDESC: {sinopsis}\n')
            # Aquí generamos el link (ejemplo: s01e01.mp4, s01e02.mp4...)
            f.write(f'{URL_BASE_VIDEO}{str(n_ep).zfill(2)}.mp4\n\n')

    print("✅ Archivo serie_the_pitt.m3u generado con éxito.")

if __name__ == "__main__":
    obtener_datos_serie()
