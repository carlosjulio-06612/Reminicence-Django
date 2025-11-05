from django.db import models
from django.conf import settings



class Artists(models.Model):
    artist_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    country = models.CharField(max_length=50, blank=True, null=True)
    biography = models.TextField(blank=True, null=True)
    spotify_id = models.CharField(unique=True, max_length=50, blank=True, null=True)
    image_url = models.URLField(max_length=500, blank=True, null=True)
    popularity = models.IntegerField(blank=True, null=True)
    followers = models.IntegerField(blank=True, null=True)
    data_source = models.CharField(max_length=20)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'artists'
        verbose_name_plural = 'Artists' 

    def __str__(self) -> str:
        return str(self.name)

class Albums(models.Model):
    album_id = models.AutoField(primary_key=True)
    artist = models.ForeignKey(Artists, on_delete=models.CASCADE, related_name='albums')
    title = models.CharField(max_length=150)
    release_date = models.DateField(blank=True, null=True)
    cover_image_url = models.URLField(max_length=500, blank=True, null=True) # Corregido a URLField
    spotify_id = models.CharField(unique=True, max_length=50, blank=True, null=True)
    spotify_url = models.CharField(max_length=255, blank=True, null=True)
    cover_image_url = models.CharField(max_length=500, blank=True, null=True)
    total_tracks = models.IntegerField(blank=True, null=True)
    data_source = models.CharField(max_length=20)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'albums'

    def __str__(self):
        return self.title

class Genres(models.Model):
    genre_id = models.AutoField(primary_key=True)
    name = models.CharField(unique=True, max_length=50)
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'genres'

    def __str__(self):
        return self.name

class Songs(models.Model):
    song_id = models.AutoField(primary_key=True)
    album = models.ForeignKey(Albums, on_delete=models.CASCADE, related_name='songs')
    title = models.CharField(max_length=150)
    duration = models.IntegerField() 
    preview_url = models.URLField(max_length=500, blank=True, null=True) # Corregido a URLField
    spotify_id = models.CharField(unique=True, max_length=50, blank=True, null=True)
    spotify_url = models.CharField(max_length=255, blank=True, null=True)
    preview_url = models.CharField(max_length=500, blank=True, null=True)
    isrc = models.CharField(max_length=20, blank=True, null=True)
    popularity = models.IntegerField(blank=True, null=True)
    data_source = models.CharField(max_length=20)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    genres = models.ManyToManyField(Genres, through='SongGenre', related_name='songs')

    class Meta:
        managed = False
        db_table = 'songs'

    def __str__(self):
        return self.title


class Playlist(models.Model):
    playlist_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='playlists')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    
    # Relación Muchos a Muchos
    songs = models.ManyToManyField(Songs, through='PlaylistSong', related_name='playlists')

    class Meta:
        managed = False
        db_table = 'playlists'
        unique_together = (('name', 'user'),)

    def __str__(self):
        return self.name


class SongGenre(models.Model):
    song = models.OneToOneField(Songs, on_delete=models.CASCADE, primary_key=True)
    genre = models.ForeignKey(Genres, on_delete=models.CASCADE)

    class Meta:
        managed = False
        db_table = 'song_genres'
        unique_together = (('song', 'genre'),)

class PlaylistSong(models.Model):
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE)
    song = models.ForeignKey(Songs, on_delete=models.CASCADE)
    position = models.IntegerField()
    date_added = models.DateTimeField()
    added_by_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'playlist_songs'
        unique_together = (('playlist', 'song'),) # La PK real
        ordering = ['position'] # Ordenar por posición

class UserFavoriteSong(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    song = models.ForeignKey(Songs, on_delete=models.CASCADE)
    favorited_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'user_favorite_songs'
        unique_together = (('user', 'song'),)

class UserFavoriteArtist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    artist = models.ForeignKey(Artists, on_delete=models.CASCADE)
    favorited_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'user_favorite_artists'
        unique_together = (('user', 'artist'),)
        
class Devices(models.Model):
    device_id = models.AutoField(primary_key=True)
    device_name = models.CharField(max_length=100, blank=True, null=True)
    device_type = models.CharField(max_length=30)
    operating_system = models.CharField(max_length=50, blank=True, null=True)
    browser = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'devices'

class PlaybackHistory(models.Model):
    playback_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    song = models.ForeignKey(Songs, on_delete=models.CASCADE)
    device = models.ForeignKey(Devices, on_delete=models.CASCADE)
    playback_date = models.DateTimeField()
    completed = models.BooleanField()
    playback_duration = models.IntegerField(blank=True, null=True)
    rating = models.IntegerField(blank=True, null=True)
    skipped = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'playback_history'