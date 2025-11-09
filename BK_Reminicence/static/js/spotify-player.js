// static/js/spotify-player.js (VERSIÓN CORREGIDA - SIN DUPLICADOS)

document.addEventListener('DOMContentLoaded', () => {
    const playerBar = document.getElementById('spotify-player-bar');
    if (!playerBar) return;

    // --- Elementos de la UI ---
    const albumArtEl = document.getElementById('player-album-art');
    const trackNameEl = document.getElementById('player-track-name');
    const artistNameEl = document.getElementById('player-artist-name');
    const playPauseBtn = document.getElementById('player-play-pause-btn');
    const playPauseIcon = playPauseBtn.querySelector('i');
    const nextBtn = document.getElementById('player-next-btn');
    const prevBtn = document.getElementById('player-previous-btn');
    const timeCurrentEl = document.getElementById('player-time-current');
    const timeTotalEl = document.getElementById('player-time-total');
    const progressEl = document.getElementById('player-progress');
    
    let playbackInterval;

    // --- Funciones de Utilidad ---
    const getCookie = name => document.cookie.match(`(^|;)\\s*${name}\\s*=\\s*([^;]+)`)?.pop() || '';
    const csrftoken = getCookie('csrftoken');
    
    const formatTime = ms => {
        const totalSeconds = Math.floor(ms / 1000);
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        return `${minutes}:${seconds.toString().padStart(2, '0')}`;
    };

    // --- Función de API Request (CORREGIDA para soportar ambos formatos) ---
    const apiRequest = async (url, method = 'POST', body = null) => {
        const options = {
            method,
            headers: {
                'X-CSRFToken': csrftoken,
            },
        };
        
        if (body) {
            // Para el endpoint de start, usamos form-urlencoded
            if (url.includes('/start/')) {
                options.headers['Content-Type'] = 'application/x-www-form-urlencoded';
                options.body = new URLSearchParams(body);
            } else {
                // Para los demás endpoints, usamos JSON
                options.headers['Content-Type'] = 'application/json';
                options.body = JSON.stringify(body);
            }
        }
        
        const response = await fetch(url, options);
        if (response.status === 204) return { status: 'success' };
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(`API request failed: ${response.status} - ${JSON.stringify(errorData)}`);
        }
        return response.json();
    };

    // --- Lógica del Reproductor ---
    const updatePlayerUI = (data) => {
        if (!data || !data.item) {
            return;
        }
        
        const track = data.item;
        albumArtEl.src = track.album.images[0]?.url || 'https://via.placeholder.com/56';
        trackNameEl.textContent = track.name;
        artistNameEl.textContent = track.artists.map(a => a.name).join(', ');
        
        playPauseBtn.dataset.isPlaying = data.is_playing;
        playPauseIcon.className = data.is_playing ? 'fas fa-pause' : 'fas fa-play';

        timeCurrentEl.textContent = formatTime(data.progress_ms);
        timeTotalEl.textContent = formatTime(track.duration_ms);
        const progressPercent = (data.progress_ms / track.duration_ms) * 100;
        progressEl.style.width = `${progressPercent}%`;
    };

    const fetchCurrentPlayback = async () => {
        try {
            const response = await fetch('/spotify/player/current/', { method: 'GET' });
            if (!response.ok) return;
            const data = await response.json();
            updatePlayerUI(data);
        } catch (error) {
            console.error('Error fetching playback:', error);
        }
    };

    // --- Event Listeners para los Controles ---
    playPauseBtn.addEventListener('click', async () => {
        try {
            await apiRequest('/spotify/player/play-pause/', 'POST', { 
                is_playing: playPauseBtn.dataset.isPlaying 
            });
            setTimeout(fetchCurrentPlayback, 500);
        } catch (error) {
            console.error('Error en play/pause:', error);
        }
    });

    nextBtn.addEventListener('click', async () => {
        try {
            await apiRequest('/spotify/player/next/', 'POST');
            setTimeout(fetchCurrentPlayback, 500);
        } catch (error) {
            console.error('Error en next:', error);
        }
    });

    prevBtn.addEventListener('click', async () => {
        try {
            await apiRequest('/spotify/player/previous/', 'POST');
            setTimeout(fetchCurrentPlayback, 500);
        } catch (error) {
            console.error('Error en previous:', error);
        }
    });

   // Event Listener Delegado ÚNICO para Iniciar Reproducción
    document.body.addEventListener('click', async (event) => {
        // NUEVO: Ignorar clicks en enlaces
        if (event.target.closest('a')) {
            return; // Deja que el enlace funcione normalmente
        }
        
        // Busca cualquier elemento que tenga el atributo data-spotify-uri
        const clickableElement = event.target.closest('[data-spotify-uri]');
        
        if (clickableElement && clickableElement.dataset.spotifyUri) {
            const spotifyUri = clickableElement.dataset.spotifyUri;
            try {
                const response = await apiRequest('/spotify/player/start/', 'POST', { 
                    uri: spotifyUri 
                });
                
                console.log('Respuesta del servidor:', response);
                
                // Feedback visual
                clickableElement.style.opacity = '0.6';
                setTimeout(() => {
                    clickableElement.style.opacity = '1';
                    fetchCurrentPlayback();
                }, 300);
                
            } catch (error) {
                console.error('Error al iniciar reproducción:', error);
                alert('No se pudo iniciar la reproducción.\n\nAsegúrate de:\n1. Tener Spotify abierto en algún dispositivo\n2. Estar reproduciendo algo previamente\n3. Tener un plan Premium de Spotify');
            }
        }
    });
    // --- Iniciar ---
    fetchCurrentPlayback();
    playbackInterval = setInterval(fetchCurrentPlayback, 5000); // Cada 5 segundos
});