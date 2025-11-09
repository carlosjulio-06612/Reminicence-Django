document.addEventListener('DOMContentLoaded', () => {
    const playerBar = document.getElementById('spotify-player-bar');
    if (!playerBar) return;

    const albumArtEl = document.getElementById('player-album-art');
    const trackNameEl = document.getElementById('player-track-name');
    const artistNameEl = document.getElementById('player-artist-name');
    const playPauseBtn = document.getElementById('player-play-pause-btn');
    const playPauseIcon = playPauseBtn.querySelector('i');
    const nextBtn = document.getElementById('player-next-btn');
    const prevBtn = document.getElementById('player-previous-btn');
    const shuffleBtn = document.getElementById('player-shuffle-btn');
    const repeatBtn = document.getElementById('player-repeat-btn');
    const timeCurrentEl = document.getElementById('player-time-current');
    const timeTotalEl = document.getElementById('player-time-total');
    const progressEl = document.getElementById('player-progress');
    const progressBarContainer = document.querySelector('.progress-bar');
    
    let currentTrackDuration = 0;

    const getCookie = name => document.cookie.match(`(^|;)\\s*${name}\\s*=\\s*([^;]+)`)?.pop() || '';
    const csrftoken = getCookie('csrftoken');
    
    const formatTime = ms => {
        if (isNaN(ms)) return '0:00';
        const totalSeconds = Math.floor(ms / 1000);
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        return `${minutes}:${seconds.toString().padStart(2, '0')}`;
    };

    const updateProgressUI = (progressMs, durationMs) => {
        timeCurrentEl.textContent = formatTime(progressMs);
        timeTotalEl.textContent = formatTime(durationMs);
        const progressPercent = (durationMs > 0) ? (progressMs / durationMs) * 100 : 0;
        progressEl.style.width = `${progressPercent}%`;
    };

    const apiRequest = async (url, method = 'POST', body = null) => {
        const options = {
            method,
            headers: {
                'X-CSRFToken': csrftoken,
                'Content-Type': 'application/json',
            },
        };
        if (body) {
            options.body = JSON.stringify(body);
        }
        
        const response = await fetch(url, options);
        if (!response.ok && response.status !== 204) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(`API request failed: ${response.status} - ${JSON.stringify(errorData)}`);
        }
        if (response.status === 204) return null;
        return response.json();
    };

    const updatePlayerUI = (data) => {
        if (!data || !data.item) {
            playPauseBtn.dataset.isPlaying = 'false';
            playPauseIcon.className = 'fas fa-play';
            return;
        }
        
        const track = data.item;
        albumArtEl.src = track.album.images[0]?.url || 'https://via.placeholder.com/56';
        trackNameEl.textContent = track.name;
        artistNameEl.textContent = track.artists.map(a => a.name).join(', ');
        
        playPauseBtn.dataset.isPlaying = data.is_playing;
        playPauseIcon.className = data.is_playing ? 'fas fa-pause' : 'fas fa-play';

        currentTrackDuration = track.duration_ms;
        updateProgressUI(data.progress_ms, track.duration_ms);

        if (shuffleBtn) {
            shuffleBtn.classList.toggle('active', data.shuffle_state);
            shuffleBtn.dataset.state = data.shuffle_state;
        }

        if (repeatBtn) {
            repeatBtn.classList.toggle('active', data.repeat_state !== 'off');
            repeatBtn.dataset.state = data.repeat_state;
        }
    };

    const fetchCurrentPlayback = async () => {
        try {
            const response = await fetch('/spotify/player/current/', { method: 'GET' });
            if (!response.ok || response.status === 204) {
                updatePlayerUI(null);
                return;
            }
            const data = await response.json();
            updatePlayerUI(data);
        } catch (error) {
            console.error('Error fetching playback:', error);
        }
    };

    const seekToPosition = async (event) => {
        if (!currentTrackDuration) return;
        const barWidth = progressBarContainer.offsetWidth;
        const clickX = event.offsetX;
        const seekPercentage = clickX / barWidth;
        const positionMs = Math.round(seekPercentage * currentTrackDuration);
        updateProgressUI(positionMs, currentTrackDuration);
        try {
            await apiRequest('/spotify/player/seek/', 'POST', { position_ms: positionMs });
            setTimeout(fetchCurrentPlayback, 300);
        } catch (error) {
            console.error('Error seeking:', error);
        }
    };

    const handleShuffle = async () => {
        const currentState = shuffleBtn.dataset.state === 'true';
        await apiRequest('/spotify/player/shuffle/', 'POST', { state: !currentState });
        setTimeout(fetchCurrentPlayback, 500);
    };

    const handleRepeat = async () => {
        const currentState = repeatBtn.dataset.state;
        let newState = 'context';
        if (currentState === 'context') newState = 'track';
        else if (currentState === 'track') newState = 'off';
        await apiRequest('/spotify/player/repeat/', 'POST', { state: newState });
        setTimeout(fetchCurrentPlayback, 500);
    };

    const handleTrackClick = async (event) => {
        const clickableElement = event.target.closest('[data-spotify-uri]');
        if (!clickableElement) return;

        const spotifyUri = clickableElement.dataset.spotifyUri;
        const contextElement = clickableElement.closest('[data-context-uri]');
        const artistTopTracksTable = clickableElement.closest('[data-artist-top-tracks="true"]');
        
        let body = {};

        if (artistTopTracksTable) {
            const allTrackElements = artistTopTracksTable.querySelectorAll('[data-spotify-uri]');
            const allUris = Array.from(allTrackElements).map(el => el.dataset.spotifyUri);
            const startIndex = allUris.indexOf(spotifyUri);
            const reorderedUris = [...allUris.slice(startIndex), ...allUris.slice(0, startIndex)];
            body = { uris: reorderedUris, uri: spotifyUri };
        } else if (contextElement) {
            body = { uri: spotifyUri, context_uri: contextElement.dataset.contextUri };
        } else {
            body = { uri: spotifyUri };
        }

        try {
            await apiRequest('/spotify/player/play/', 'POST', body);
            setTimeout(fetchCurrentPlayback, 500);
        } catch (error) {
            console.error('Error al iniciar reproducción:', error);
        }
    };
    
    playPauseBtn.addEventListener('click', async () => {
        const isPlaying = playPauseBtn.dataset.isPlaying === 'true';
        const url = isPlaying ? '/spotify/player/pause/' : '/spotify/player/play/';
        await apiRequest(url, 'POST');
        setTimeout(fetchCurrentPlayback, 500);
    });
    
    nextBtn.addEventListener('click', () => { apiRequest('/spotify/player/next/'); setTimeout(fetchCurrentPlayback, 500); });
    prevBtn.addEventListener('click', () => { apiRequest('/spotify/player/previous/'); setTimeout(fetchCurrentPlayback, 500); });
    if (shuffleBtn) shuffleBtn.addEventListener('click', handleShuffle);
    if (repeatBtn) repeatBtn.addEventListener('click', handleRepeat);
    if (progressBarContainer) progressBarContainer.addEventListener('click', seekToPosition);
    document.body.addEventListener('click', handleTrackClick);
    
    fetchCurrentPlayback();
    setInterval(fetchCurrentPlayback, 3000);
});