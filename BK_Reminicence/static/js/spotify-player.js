let webPlaybackDeviceId = null;
let currentPlayerState = null;
let progressInterval = null;

window.onSpotifyWebPlaybackSDKReady = () => {
    const player = new Spotify.Player({
        name: 'Reminiscence Web Player',
        getOAuthToken: cb => { cb(window.spotifyAccessToken); },
        volume: 0.5
    });

    // Guardar player globalmente
    window.spotifyPlayer = player;

    player.addListener('ready', ({ device_id }) => {
        console.log('Reproductor web listo con ID:', device_id);
        webPlaybackDeviceId = device_id;
        
        // Transferir reproducción al nuevo dispositivo automáticamente
        transferPlaybackToWeb(device_id);
    });

    player.addListener('not_ready', ({ device_id }) => {
        console.log('Reproductor no disponible:', device_id);
        webPlaybackDeviceId = null;
    });
    
    player.addListener('player_state_changed', state => {
        if (!state) {
            document.getElementById('player-track-name').textContent = 'Selecciona una canción';
            document.getElementById('player-artist-name').textContent = '...';
            stopProgressUpdate();
            return;
        }
        
        currentPlayerState = state;
        updatePlayerUIFromSDK(state);
        
        // Actualizar progreso solo si está reproduciendo
        if (!state.paused) {
            startProgressUpdate();
        } else {
            stopProgressUpdate();
        }
    });

    // Manejar errores
    player.addListener('initialization_error', ({ message }) => {
        console.error('Error de inicialización:', message);
    });

    player.addListener('authentication_error', ({ message }) => {
        console.error('Error de autenticación:', message);
        alert('Error de autenticación con Spotify. Por favor, vuelve a iniciar sesión.');
    });

    player.addListener('account_error', ({ message }) => {
        console.error('Error de cuenta:', message);
        alert('Se requiere Spotify Premium para usar el reproductor web.');
    });

    player.addListener('playback_error', ({ message }) => {
        console.error('Error de reproducción:', message);
    });

    player.connect().then(success => {
        if (success) {
            console.log('Conexión exitosa con Spotify Web Playback SDK');
        }
    });
};

// Función para transferir reproducción al reproductor web
const transferPlaybackToWeb = async (deviceId) => {
    try {
        const response = await fetch('https://api.spotify.com/v1/me/player', {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${window.spotifyAccessToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                device_ids: [deviceId],
                play: false // No iniciar reproducción automáticamente
            })
        });
        
        if (response.ok) {
            console.log('Reproducción transferida al reproductor web');
        }
    } catch (error) {
        console.error('Error al transferir reproducción:', error);
    }
};

// Actualizar UI desde el estado del SDK
const updatePlayerUIFromSDK = (state) => {
    const track = state.track_window.current_track;
    const albumArtEl = document.getElementById('player-album-art');
    const trackNameEl = document.getElementById('player-track-name');
    const artistNameEl = document.getElementById('player-artist-name');
    const playPauseBtn = document.getElementById('player-play-pause-btn');
    const playPauseIcon = playPauseBtn.querySelector('i');
    const shuffleBtn = document.getElementById('player-shuffle-btn');
    const repeatBtn = document.getElementById('player-repeat-btn');
    const timeTotalEl = document.getElementById('player-time-total');

    albumArtEl.src = track.album.images[0]?.url || 'https://via.placeholder.com/56';
    trackNameEl.textContent = track.name;
    artistNameEl.textContent = track.artists.map(a => a.name).join(', ');
    
    playPauseBtn.dataset.isPlaying = !state.paused;
    playPauseIcon.className = state.paused ? 'fas fa-play' : 'fas fa-pause';

    shuffleBtn?.classList.toggle('active', state.shuffle);
    shuffleBtn.dataset.state = state.shuffle;

    const repeatMode = ['off', 'context', 'track'][state.repeat_mode];
    repeatBtn?.classList.toggle('active', repeatMode !== 'off');
    repeatBtn.dataset.state = repeatMode;
    
    timeTotalEl.textContent = formatTime(state.duration);
    
    // Actualizar progreso inmediatamente
    updateProgress(state.position, state.duration);
};

// Formatear tiempo en milisegundos a MM:SS
const formatTime = ms => {
    if (isNaN(ms)) return '0:00';
    const totalSeconds = Math.floor(ms / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
};

// Actualizar barra de progreso
const updateProgress = (positionMs, durationMs) => {
    const timeCurrentEl = document.getElementById('player-time-current');
    const progressEl = document.getElementById('player-progress');
    
    timeCurrentEl.textContent = formatTime(positionMs);
    const progressPercent = (durationMs > 0) ? (positionMs / durationMs) * 100 : 0;
    progressEl.style.width = `${Math.min(progressPercent, 100)}%`;
};

// Iniciar actualización automática del progreso
const startProgressUpdate = () => {
    stopProgressUpdate();
    progressInterval = setInterval(() => {
        if (currentPlayerState && !currentPlayerState.paused) {
            currentPlayerState.position += 1000; // Incrementar 1 segundo
            updateProgress(currentPlayerState.position, currentPlayerState.duration);
        }
    }, 1000);
};

// Detener actualización del progreso
const stopProgressUpdate = () => {
    if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
    }
};

// Obtener CSRF token
const getCookie = name => document.cookie.match(`(^|;)\\s*${name}\\s*=\\s*([^;]+)`)?.pop() || '';

// Realizar petición a la API
const apiRequest = async (url, method = 'POST', body = {}) => {
    const csrftoken = getCookie('csrftoken');
    
    if (webPlaybackDeviceId) {
        body.device_id = webPlaybackDeviceId;
    }
    
    const options = {
        method,
        headers: {
            'X-CSRFToken': csrftoken,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(body)
    };
    
    try {
        const response = await fetch(url, options);
        if (!response.ok && response.status !== 204) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `API request failed: ${response.status}`);
        }
        return response;
    } catch (error) {
        console.error('Error en apiRequest:', error);
        throw error;
    }
};

// Manejar click en canciones
const handleTrackClick = async (event) => {
    const clickableElement = event.target.closest('[data-spotify-uri]');
    if (!clickableElement) return;

    if (!webPlaybackDeviceId) {
        alert("El reproductor web no está listo. Por favor, asegúrate de tener Spotify Premium e inténtalo de nuevo en un momento.");
        return;
    }

    const spotifyUri = clickableElement.dataset.spotifyUri;
    const contextElement = clickableElement.closest('[data-context-uri]');
    const artistTopTracksTable = clickableElement.closest('[data-artist-top-tracks="true"]');
    let body = {};

    if (artistTopTracksTable) {
        const allUris = Array.from(artistTopTracksTable.querySelectorAll('[data-spotify-uri]'))
            .map(el => el.dataset.spotifyUri);
        const startIndex = allUris.indexOf(spotifyUri);
        body.uris = [...allUris.slice(startIndex), ...allUris.slice(0, startIndex)];
    } else if (contextElement) {
        body.context_uri = contextElement.dataset.contextUri;
        body.uri = spotifyUri;
    } else {
        body.uri = spotifyUri;
    }
    
    try {
        await apiRequest('/spotify/player/play/', 'POST', body);
    } catch (error) {
        alert('Error al reproducir: ' + error.message);
    }
};

// Funciones para el modal de cola
const openQueueModal = async () => {
    const modal = document.getElementById('queue-modal');
    modal.classList.remove('hidden');
    await updateQueueDisplay();
};

const closeQueueModal = () => {
    const modal = document.getElementById('queue-modal');
    modal.classList.add('hidden');
};

// Actualizar visualización de la cola
const updateQueueDisplay = async () => {
    try {
        const response = await fetch('https://api.spotify.com/v1/me/player/queue', {
            headers: {
                'Authorization': `Bearer ${window.spotifyAccessToken}`
            }
        });

        if (!response.ok) {
            throw new Error('No se pudo obtener la cola');
        }

        const data = await response.json();
        
        // Actualizar "Reproduciendo ahora"
        if (data.currently_playing) {
            const track = data.currently_playing;
            document.getElementById('queue-now-playing').innerHTML = `
                <img src="${track.album?.images[0]?.url || 'https://via.placeholder.com/48'}" alt="Album art">
                <div class="queue-track-info">
                    <span class="queue-track-name">${track.name}</span>
                    <span class="queue-track-artist">${track.artists.map(a => a.name).join(', ')}</span>
                </div>
                <span class="queue-track-duration">${formatTime(track.duration_ms)}</span>
            `;
        }

        // Actualizar "Siguiente"
        const queueContainer = document.getElementById('queue-next-tracks');
        if (data.queue && data.queue.length > 0) {
            queueContainer.innerHTML = data.queue.map((track, index) => `
                <div class="queue-track-item" onclick="playFromQueue('${track.uri}', ${index})">
                    <img src="${track.album?.images[0]?.url || 'https://via.placeholder.com/48'}" alt="Album art">
                    <div class="queue-track-info">
                        <span class="queue-track-name">${track.name}</span>
                        <span class="queue-track-artist">${track.artists.map(a => a.name).join(', ')}</span>
                    </div>
                    <span class="queue-track-duration">${formatTime(track.duration_ms)}</span>
                </div>
            `).join('');
        } else {
            queueContainer.innerHTML = `
                <div class="queue-empty">
                    <i class="fas fa-music"></i>
                    <p>No hay canciones en la cola</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error al obtener cola:', error);
        document.getElementById('queue-next-tracks').innerHTML = `
            <div class="queue-empty">
                <i class="fas fa-exclamation-circle"></i>
                <p>No se pudo cargar la cola</p>
            </div>
        `;
    }
};

// Reproducir desde una posición específica de la cola
const playFromQueue = async (uri, skipCount) => {
    try {
        const modalContent = document.querySelector('.queue-modal-content');
        modalContent.classList.add('loading');
        
        // Saltar las canciones necesarias
        for (let i = 0; i < skipCount + 1; i++) {
            await window.spotifyPlayer.nextTrack();
            // Pequeña pausa entre saltos para evitar rate limiting
            if (i < skipCount) {
                await new Promise(resolve => setTimeout(resolve, 300));
            }
        }
        
        // Esperar un poco antes de actualizar la UI
        await new Promise(resolve => setTimeout(resolve, 800));
        
        // Actualizar la cola
        await updateQueueDisplay();
        
        modalContent.classList.remove('loading');
        
    } catch (error) {
        console.error('Error al reproducir desde cola:', error);
        document.querySelector('.queue-modal-content').classList.remove('loading');
        alert('No se pudo reproducir esta canción');
    }
};

// Hacer funciones globales
window.openQueueModal = openQueueModal;
window.closeQueueModal = closeQueueModal;
window.playFromQueue = playFromQueue;

// Event listeners cuando el DOM está listo
document.addEventListener('DOMContentLoaded', () => {
    // Play/Pause
    document.getElementById('player-play-pause-btn').addEventListener('click', async () => {
        const isPlaying = document.getElementById('player-play-pause-btn').dataset.isPlaying === 'true';
        try {
            if (isPlaying) {
                await window.spotifyPlayer.pause();
            } else {
                await window.spotifyPlayer.resume();
            }
        } catch (error) {
            console.error('Error al cambiar play/pause:', error);
        }
    });

    // Siguiente canción
    document.getElementById('player-next-btn').addEventListener('click', async () => {
        try {
            await window.spotifyPlayer.nextTrack();
        } catch (error) {
            console.error('Error al pasar a siguiente canción:', error);
        }
    });

    // Canción anterior
    document.getElementById('player-previous-btn').addEventListener('click', async () => {
        try {
            await window.spotifyPlayer.previousTrack();
        } catch (error) {
            console.error('Error al volver a canción anterior:', error);
        }
    });
    
    // Shuffle
    document.getElementById('player-shuffle-btn').addEventListener('click', async (e) => {
        const currentState = e.currentTarget.dataset.state === 'true';
        try {
            await apiRequest('/spotify/player/shuffle/', 'POST', { state: !currentState });
        } catch (error) {
            console.error('Error al cambiar shuffle:', error);
        }
    });

    // Repeat
    document.getElementById('player-repeat-btn').addEventListener('click', async (e) => {
        let newState = 'context';
        if (e.currentTarget.dataset.state === 'context') newState = 'track';
        else if (e.currentTarget.dataset.state === 'track') newState = 'off';
        
        try {
            await apiRequest('/spotify/player/repeat/', 'POST', { state: newState });
        } catch (error) {
            console.error('Error al cambiar repeat:', error);
        }
    });

    // Seek en la barra de progreso
    document.querySelector('.progress-bar').addEventListener('click', async (event) => {
        const progressBar = event.currentTarget;
        if (!currentPlayerState) return;
        
        const durationMs = currentPlayerState.duration;
        const clickX = event.offsetX;
        const barWidth = progressBar.offsetWidth;
        const positionMs = Math.round((clickX / barWidth) * durationMs);
        
        try {
            await window.spotifyPlayer.seek(positionMs);
        } catch (error) {
            console.error('Error al buscar posición:', error);
        }
    });

    // Control de volumen
    const volumeSlider = document.querySelector('.volume-bar');
    const volumeProgress = volumeSlider.querySelector('.progress');
    const volumeButton = document.querySelector('[title="Volumen"]');
    
    // Habilitar botón de volumen
    if (volumeButton) {
        volumeButton.disabled = false;
    }
    
    let currentVolume = 0.7; // Volumen inicial 70%
    
    // Click en la barra de volumen
    volumeSlider.addEventListener('click', async (event) => {
        const clickX = event.offsetX;
        const barWidth = volumeSlider.offsetWidth;
        const volume = clickX / barWidth;
        
        try {
            await window.spotifyPlayer.setVolume(volume);
            currentVolume = volume;
            volumeProgress.style.width = `${volume * 100}%`;
            updateVolumeIcon(volume);
        } catch (error) {
            console.error('Error al cambiar volumen:', error);
        }
    });
    
    // Click en el botón de volumen (mute/unmute)
    if (volumeButton) {
        volumeButton.addEventListener('click', async () => {
            try {
                if (currentVolume > 0) {
                    // Mutear
                    await window.spotifyPlayer.setVolume(0);
                    volumeProgress.style.width = '0%';
                    updateVolumeIcon(0);
                    volumeButton.dataset.previousVolume = currentVolume;
                    currentVolume = 0;
                } else {
                    // Desmutear
                    const previousVolume = parseFloat(volumeButton.dataset.previousVolume) || 0.7;
                    await window.spotifyPlayer.setVolume(previousVolume);
                    currentVolume = previousVolume;
                    volumeProgress.style.width = `${previousVolume * 100}%`;
                    updateVolumeIcon(previousVolume);
                }
            } catch (error) {
                console.error('Error al cambiar mute:', error);
            }
        });
    }
    
    // Actualizar ícono de volumen según el nivel
    const updateVolumeIcon = (volume) => {
        const icon = volumeButton.querySelector('i');
        if (volume === 0) {
            icon.className = 'fas fa-volume-mute';
        } else if (volume < 0.5) {
            icon.className = 'fas fa-volume-down';
        } else {
            icon.className = 'fas fa-volume-up';
        }
    };
    
    // Inicializar volumen
    updateVolumeIcon(currentVolume);
    
    // Click en canciones/tracks
    document.body.addEventListener('click', handleTrackClick);
    
    // Botón de cola de reproducción
    const queueButton = document.querySelector('[title="Cola de reproducción"]');
    if (queueButton) {
        queueButton.disabled = false;
        queueButton.addEventListener('click', openQueueModal);
    }
    
    // Cerrar modal al hacer clic en el overlay
    const queueOverlay = document.querySelector('.queue-modal-overlay');
    if (queueOverlay) {
        queueOverlay.addEventListener('click', closeQueueModal);
    }
    
    // Cerrar modal con tecla Escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeQueueModal();
        }
    });
});