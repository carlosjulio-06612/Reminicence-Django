async function testPlayback() {
    console.log("▶️ Iniciando prueba de reproducción...");
    
    // El URI de una canción muy conocida
    const testUri = 'spotify:track:0VjIjW4GlUZAMYd2vXMi3b'; // Blinding Lights - The Weeknd
    
    // Obtenemos el token CSRF de las cookies
    const csrftoken = document.cookie.match(`(^|;)\\s*csrftoken\\s*=\\s*([^;]+)`)?.pop() || '';

    if (!csrftoken) {
        console.error("❌ No se encontró el token CSRF. Asegúrate de haber iniciado sesión.");
        return;
    }
    
    try {
        const response = await fetch('/spotify/player/start/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrftoken,
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({ 'uri': testUri })
        });

        if (response.ok) {
            console.log("✅ ¡Éxito! La solicitud al backend fue enviada correctamente. Revisa tu altavoz de Spotify.");
        } else {
            const errorData = await response.json();
            console.error("❌ Fallo en la solicitud al backend. Estado:", response.status);
            console.error("Detalles del error:", errorData);
        }
    } catch (error) {
        console.error("❌ Error de red o al ejecutar la solicitud.", error);
    }
}

// Ejecutamos la función de prueba
testPlayback();