from rest_framework import serializers
from ..models import (
    Artists,
    Albums,
    Songs,
    Genres,
    Playlist,
    PlaylistSong,
    UserFavoriteSong,
    UserFavoriteArtist
)
from django.contrib.auth.models import User


# ===================================================================
# ===== SERIALIZERS BÁSICOS =========================================
# ===================================================================

class GenreSerializer(serializers.ModelSerializer):
    """Serializer para géneros musicales"""
    
    class Meta:
        model = Genres
        fields = ['genre_id', 'name', 'description', 'spotify_id']


class ArtistSerializer(serializers.ModelSerializer):
    """Serializer para artistas"""
    
    class Meta:
        model = Artists
        fields = [
            'artist_id',
            'name',
            'country',
            'biography',
            'spotify_id',
            'image_url',
            'popularity',
            'followers',
            'data_source',
            'formation_year',
            'artist_type',
            'spotify_url',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['artist_id', 'created_at', 'updated_at']


class ArtistMinimalSerializer(serializers.ModelSerializer):
    """Serializer mínimo para artistas (para listas)"""
    
    class Meta:
        model = Artists
        fields = ['artist_id', 'name', 'image_url', 'spotify_id']


class AlbumSerializer(serializers.ModelSerializer):
    """Serializer para álbumes"""
    artist = ArtistMinimalSerializer(read_only=True)
    
    class Meta:
        model = Albums
        fields = [
            'album_id',
            'artist',
            'title',
            'release_date',
            'spotify_id',
            'spotify_url',
            'cover_image_url',
            'total_tracks',
            'data_source',
            'release_year',
            'record_label',
            'album_type',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['album_id', 'created_at', 'updated_at']


class AlbumMinimalSerializer(serializers.ModelSerializer):
    """Serializer mínimo para álbumes"""
    
    class Meta:
        model = Albums
        fields = ['album_id', 'title', 'cover_image_url', 'spotify_id']


class SongSerializer(serializers.ModelSerializer):
    """Serializer completo para canciones"""
    album = AlbumMinimalSerializer(read_only=True)
    artist_name = serializers.CharField(source='album.artist.name', read_only=True)
    artist_id = serializers.IntegerField(source='album.artist.artist_id', read_only=True)
    genres = GenreSerializer(many=True, read_only=True)
    
    class Meta:
        model = Songs
        fields = [
            'song_id',
            'album',
            'artist_name',
            'artist_id',
            'title',
            'duration',
            'spotify_id',
            'spotify_url',
            'preview_url',
            'isrc',
            'popularity',
            'data_source',
            'genres',
            'track_number',
            'disc_number',
            'composer',
            'lyrics',
            'explicit_content',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['song_id', 'created_at', 'updated_at']


class SongMinimalSerializer(serializers.ModelSerializer):
    """Serializer mínimo para canciones (para listas)"""
    artist_name = serializers.CharField(source='album.artist.name', read_only=True)
    album_title = serializers.CharField(source='album.title', read_only=True)
    album_cover = serializers.URLField(source='album.cover_image_url', read_only=True)
    
    class Meta:
        model = Songs
        fields = [
            'song_id',
            'title',
            'artist_name',
            'album_title',
            'album_cover',
            'duration',
            'spotify_id',
            'preview_url',
            'explicit_content'
        ]


# ===================================================================
# ===== SERIALIZERS DE PLAYLISTS ====================================
# ===================================================================

class PlaylistSongSerializer(serializers.ModelSerializer):
    """Serializer para canciones dentro de una playlist"""
    song = SongMinimalSerializer(read_only=True)
    
    class Meta:
        model = PlaylistSong
        fields = ['song', 'position', 'date_added']


class PlaylistSerializer(serializers.ModelSerializer):
    """Serializer completo para playlists"""
    user = serializers.StringRelatedField(read_only=True)
    songs_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Playlist
        fields = [
            'playlist_id',
            'user',
            'name',
            'description',
            'status',
            'cover_image_url',
            'spotify_id',
            'spotify_snapshot_id',
            'is_synced_with_spotify',
            'last_sync_date',
            'songs_count',
            'creation_date',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'playlist_id',
            'user',
            'spotify_id',
            'spotify_snapshot_id',
            'is_synced_with_spotify',
            'last_sync_date',
            'creation_date',
            'created_at',
            'updated_at'
        ]
    
    def get_songs_count(self, obj):
        return obj.songs.count()


class PlaylistDetailSerializer(PlaylistSerializer):
    """Serializer detallado para playlist con canciones"""
    songs = serializers.SerializerMethodField()
    
    class Meta(PlaylistSerializer.Meta):
        fields = PlaylistSerializer.Meta.fields + ['songs']
    
    def get_songs(self, obj):
        playlist_songs = PlaylistSong.objects.filter(playlist=obj).select_related(
            'song',
            'song__album',
            'song__album__artist'
        ).order_by('position')
        return PlaylistSongSerializer(playlist_songs, many=True).data


class PlaylistCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear playlists"""
    
    class Meta:
        model = Playlist
        fields = ['name', 'description', 'status']
    
    def create(self, validated_data):
        # El usuario se asigna en la vista
        return Playlist.objects.create(**validated_data)


class PlaylistUpdateSerializer(serializers.ModelSerializer):
    """Serializer para actualizar playlists"""
    
    class Meta:
        model = Playlist
        fields = ['name', 'description', 'status', 'cover_image_url']


class AddSongToPlaylistSerializer(serializers.Serializer):
    """Serializer para agregar canción a playlist"""
    song_id = serializers.IntegerField()
    position = serializers.IntegerField(required=False, allow_null=True)
    
    def validate_song_id(self, value):
        try:
            Songs.objects.get(song_id=value)
        except Songs.DoesNotExist:
            raise serializers.ValidationError("La canción no existe")
        return value


# ===================================================================
# ===== SERIALIZERS DE FAVORITOS ====================================
# ===================================================================

class FavoriteSongSerializer(serializers.ModelSerializer):
    """Serializer para canciones favoritas"""
    song = SongMinimalSerializer(read_only=True)
    
    class Meta:
        model = UserFavoriteSong
        fields = ['song', 'favorited_at']


class FavoriteArtistSerializer(serializers.ModelSerializer):
    """Serializer para artistas favoritos"""
    artist = ArtistMinimalSerializer(read_only=True)
    
    class Meta:
        model = UserFavoriteArtist
        fields = ['artist', 'favorited_at']


# ===================================================================
# ===== SERIALIZERS DE BÚSQUEDA (SPOTIFY) ===========================
# ===================================================================

class SpotifyTrackSerializer(serializers.Serializer):
    """Serializer para tracks de Spotify (búsqueda)"""
    id = serializers.CharField()
    name = serializers.CharField()
    artists = serializers.ListField(child=serializers.DictField())
    album = serializers.DictField()
    duration_ms = serializers.IntegerField()
    preview_url = serializers.URLField(allow_null=True)
    external_urls = serializers.DictField()
    uri = serializers.CharField()
    popularity = serializers.IntegerField(required=False)
    explicit = serializers.BooleanField(required=False)


class SpotifyArtistSerializer(serializers.Serializer):
    """Serializer para artistas de Spotify (búsqueda)"""
    id = serializers.CharField()
    name = serializers.CharField()
    images = serializers.ListField(child=serializers.DictField(), required=False)
    genres = serializers.ListField(child=serializers.CharField(), required=False)
    popularity = serializers.IntegerField(required=False)
    followers = serializers.DictField(required=False)
    external_urls = serializers.DictField()
    uri = serializers.CharField()


class SpotifyAlbumSerializer(serializers.Serializer):
    """Serializer para álbumes de Spotify (búsqueda)"""
    id = serializers.CharField()
    name = serializers.CharField()
    artists = serializers.ListField(child=serializers.DictField())
    images = serializers.ListField(child=serializers.DictField(), required=False)
    release_date = serializers.CharField()
    total_tracks = serializers.IntegerField()
    album_type = serializers.CharField()
    external_urls = serializers.DictField()
    uri = serializers.CharField()


class SpotifyPlaylistSerializer(serializers.Serializer):
    """Serializer para playlists de Spotify"""
    id = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    images = serializers.ListField(child=serializers.DictField(), required=False)
    tracks = serializers.DictField()
    owner = serializers.DictField()
    external_urls = serializers.DictField()
    uri = serializers.CharField()
    snapshot_id = serializers.CharField()


class SpotifySearchResultSerializer(serializers.Serializer):
    """Serializer para resultados de búsqueda completos"""
    tracks = SpotifyTrackSerializer(many=True, required=False)
    artists = SpotifyArtistSerializer(many=True, required=False)
    albums = SpotifyAlbumSerializer(many=True, required=False)
    playlists = SpotifyPlaylistSerializer(many=True, required=False)


# ===================================================================
# ===== SERIALIZERS DE SINCRONIZACIÓN ===============================
# ===================================================================

class SyncStatusSerializer(serializers.Serializer):
    """Serializer para estado de sincronización"""
    is_syncing = serializers.BooleanField()
    last_sync = serializers.DateTimeField(allow_null=True)
    playlists_synced = serializers.IntegerField()
    message = serializers.CharField()