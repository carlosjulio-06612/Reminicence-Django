import requests
import base64
from django.core.management.base import BaseCommand
from applications.music.models import Artists
from BK_Reminicence.settings.base import *

# --- Funciones de la API ---

def get_spotify_token():
    client_id = get_secret("SPOTIFY_CLIENT_ID")
    client_secret = get_secret("SPOTIFY_CLIENT_SECRET")
    
    auth_string = f"{client_id}:{client_secret}"
    auth_bytes = auth_string.encode("utf-8")
    auth_base64 = base64.b64encode(auth_bytes).decode("utf-8")
    
    url = "https://accounts.spotify.com/api/token"
    headers = {"Authorization": f"Basic {auth_base64}", "Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "client_credentials"}
    
    response = requests.post(url, headers=headers, data=data)
    
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        raise Exception(f"Error al obtener el token: {response.json()}")

def search_and_save_artist(artist_name, access_token):
    # Usa el nombre de tu modelo (Artist o Artists)
    if Artists.objects.filter(name__iexact=artist_name).exists():
        print(f"INFO: El artista '{artist_name}' ya existe en la base de datos.")
        return Artists.objects.get(name__iexact=artist_name)

    print(f"INFO: Buscando a '{artist_name}' en Spotify...")
    search_url = "https://api.spotify.com/v1/search"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"q": artist_name, "type": "artist", "limit": 1}
    
    response = requests.get(search_url, headers=headers, params=params)
    
    if response.status_code != 200 or not response.json()['artists']['items']:
        print(f"ERROR: No se pudo encontrar a '{artist_name}' en Spotify.")
        return None

    artist_data = response.json()['artists']['items'][0]
    print(f"INFO: Artista encontrado: {artist_data['name']}")
    
    new_artist = Artists( # Usa el nombre de tu modelo
        name=artist_data.get('name'),
        spotify_id=artist_data.get('id'),
        image_url=artist_data['images'][0]['url'] if artist_data.get('images') else None,
        popularity=artist_data.get('popularity'),
        followers=artist_data['followers'].get('total') if artist_data.get('followers') else 0,
        data_source='spotify'
    )

    try:
        new_artist.save()
        print(f"SUCCESS: ¡Artista '{new_artist.name}' guardado en la base de datos con ID: {new_artist.artist_id}!") # O el nombre de tu PK
        return new_artist
    except Exception as e:
        print(f"ERROR: Error al guardar el artista: {e}")
        return None

# --- Clase del Comando de Django ---

class Command(BaseCommand):
    help = 'Busca un artista en Spotify y lo guarda en la base de datos.'

    def add_arguments(self, parser):
        parser.add_argument('artist_name', type=str, help='El nombre del artista a buscar.')

    def handle(self, *args, **options):
        artist_name = options['artist_name']
        self.stdout.write(f"Iniciando proceso para '{artist_name}'...")
        
        try:
            token = get_spotify_token()
            self.stdout.write(self.style.SUCCESS("Token de Spotify obtenido exitosamente."))
            
            search_and_save_artist(artist_name, token)

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Ha ocurrido un error: {e}"))