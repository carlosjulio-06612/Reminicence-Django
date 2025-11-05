from django.core.management.base import BaseCommand
from applications.spotify_api.services import get_spotify_token, search_and_save_artist

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