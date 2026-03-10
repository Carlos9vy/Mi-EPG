import requests
import os

# --- CONFIGURACIÓN ---
API_KEY = "35808c87beebe2b0aaa71aeeccd1caf8" 
ID_SERIE_TMDB = "250307"     # ID CORRECTO de "The Pitt"
TEMPORADA = 1
# Estructura de tu servidor según tu ejemplo
URL_BASE = "http://series.tuxchannel.mx:80/series/the_pitt/s_01_e_"

def generar_m3u_series():
    # Consulta a TMDB en Español
    url_es = f"https://api.themoviedb.org/3/tv/{ID_SERIE_TMDB}/season/{TEMPORADA}?api_key={API_KEY}&language=es-ES"
    
    try:
        print(f"Generando lista de serie con ID {ID_SERIE_TMDB}...")
        response = requests.get(url_es)
        datos = response.json()

        if 'episodes' not in datos:
            print("Error: No se pudieron obtener los datos de la serie.")
            return

        with open("serie_the_pitt.m3u", "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n\n")
            
            for ep in datos['episodes']:
                num_ep = ep['episode_number']
                # Formato de número a dos dígitos (01, 02...)
                num_str = str(num_ep).zfill(2)
                
                titulo = ep['name'] or f"Episodio {num_ep}"
                sinopsis = ep['overview'] or "Sinopsis no disponible en español."
                
                # Limpiamos el texto para evitar errores en Smart TVs
                sinopsis = sinopsis.replace('"', "'").replace("\n", " ")
                
                # Imagen del episodio
                foto = f"https://image.tmdb.org/t/p/w500{ep['still_path']}" if ep['still_path'] else ""
                
                # Construcción de tu enlace .mkv
                link_video = f"{URL_BASE}{num_str}.mkv"
                
                # Formato con la etiqueta tvg-type="serie"
                f.write(f'#EXTINF:-1 tvg-type="serie" tvg-id="pitt-s01e{num_str}" tvg-logo="{foto}" group-title="The Pitt", {num_ep}. {titulo}\n')
                f.write(f'#EXTVODDESC: {sinopsis}\n')
                f.write(f'{link_video}\n\n')

        print(f"✅ ¡Hecho! Archivo generado con tvg-type='serie'.")

    except Exception as e:
        print(f"Error técnico: {e}")

if __name__ == "__main__":
    generar_m3u_series()
