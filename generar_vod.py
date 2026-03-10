import requests
import os

# --- CONFIGURACIÓN ---
API_KEY = "35808c87beebe2b0aaa71aeeccd1caf8" 
ID_SERIE_TMDB = "242131"     # ID de "The Pitt"
TEMPORADA = 1
# Estructura de tu servidor
URL_BASE = "http://series.tuxchannel.mx:80/series/the_pitt/s_01_e_"

def generar_m3u_real():
    # Consultas a TMDB (Español e Inglés de respaldo)
    url_es = f"https://api.themoviedb.org/3/tv/{ID_SERIE_TMDB}/season/{TEMPORADA}?api_key={API_KEY}&language=es-ES"
    url_en = f"https://api.themoviedb.org/3/tv/{ID_SERIE_TMDB}/season/{TEMPORADA}?api_key={API_KEY}&language=en-US"
    
    try:
        print("Obteniendo metadatos de TMDB...")
        res_es = requests.get(url_es).json()
        res_en = requests.get(url_en).json()

        if 'episodes' not in res_es:
            print("Error: No se encontró la información de la serie.")
            return

        with open("serie_the_pitt.m3u", "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            f.write(f"#PLAYLIST: The Pitt - Temporada {TEMPORADA}\n\n")
            
            for i, ep_es in enumerate(res_es['episodes']):
                ep_en = res_en['episodes'][i]
                
                num_ep = ep_es['episode_number']
                # Formatear el número a dos dígitos (01, 02...)
                num_str = str(num_ep).zfill(2)
                
                # Título: Prioridad español, si no inglés
                titulo = ep_es['name'] if ep_es['name'] else ep_en['name']
                
                # Sinopsis: Prioridad español, si no inglés
                sinopsis = ep_es['overview']
                if not sinopsis or sinopsis == "":
                    sinopsis = ep_en['overview']
                if not sinopsis:
                    sinopsis = "Sinopsis pendiente de actualización en TMDB."

                # Limpiar texto para evitar que rompa el M3U en Smart TVs antiguas
                sinopsis = sinopsis.replace('"', "'").replace("\n", " ")
                
                # Imagen del episodio
                foto = f"https://image.tmdb.org/t/p/w500{ep_es['still_path']}" if ep_es['still_path'] else ""
                
                # Construcción del link real según tu formato
                link_video = f"{URL_BASE}{num_str}.mkv"
                
                # Escribir en el archivo
                f.write(f'#EXTINF:-1 tvg-id="pitt-s01e{num_str}" tvg-logo="{foto}" group-title="The Pitt", {num_ep}. {titulo}\n')
                f.write(f'#EXTVODDESC: {sinopsis}\n')
                f.write(f'{link_video}\n\n')

        print(f"✅ ¡Éxito! Archivo 'serie_the_pitt.m3u' generado con {len(res_es['episodes'])} episodios.")

    except Exception as e:
        print(f"Error al generar el archivo: {e}")

if __name__ == "__main__":
    generar_m3u_real()
