// =======================================================================
// MEJORAS HERMATRON V4.0: PREVISUALIZACIÓN Y BARRA ESPACIADORA
// =======================================================================

const VOCES = [
    // ElevenLabs Premium
    { id: 'pNInz6obpgDQGcFmaJgB', nombre: 'Adam (Profundo, Documental)', flag: '💎', region: 'ElevenLabs Premium' },
    { id: '21m00Tcm4TlvDq8ikWAM', nombre: 'Rachel (Calmada, Narrativa)', flag: '💎', region: 'ElevenLabs Premium' },
    { id: 'ErXwobaYiN019PkySvjV', nombre: 'Antoni (Dinámico, Profesional)', flag: '💎', region: 'ElevenLabs Premium' },
    { id: 'EXAVITQu4vr4xnSDxMaL', nombre: 'Bella (Suave, Atractiva)', flag: '💎', region: 'ElevenLabs Premium' },
    { id: 'VR6AewLTigWG4xSOukaG', nombre: 'Arnold (Fuerte, Épico)', flag: '💎', region: 'ElevenLabs Premium' },
    // Edge TTS - Masculinas
    { id: 'es-CO-GonzaloNeural', nombre: 'Gonzalo (Claro)', flag: '🇨🇴', region: 'Colombia ⭐' },
    { id: 'es-MX-JorgeNeural', nombre: 'Jorge (Realista)', flag: '🇲🇽', region: 'México' },
    { id: 'es-ES-AlvaroNeural', nombre: 'Álvaro (Profesional)', flag: '🇪🇸', region: 'España' },
    { id: 'es-AR-TomasNeural', nombre: 'Tomás (Dinámico)', flag: '🇦🇷', region: 'Argentina' },
    { id: 'es-US-AlonsoNeural', nombre: 'Alonso (Neutral)', flag: '🇺🇸', region: 'USA Español' },
    // Edge TTS - Femeninas
    { id: 'es-ES-LuciaNeural', nombre: 'Lucía (Clara)', flag: '🇪🇸', region: 'España' },
    { id: 'es-ES-ConchitaNeural', nombre: 'Conchita (Cálida)', flag: '🇪🇸', region: 'España' },
    { id: 'es-MX-LupeNeural', nombre: 'Lupe (Natural)', flag: '🇲🇽', region: 'México' },
];

// Variable global para detener audios previos
let audioMuestraActual = null;
let pollingInterval = null;
let proyectoActual = null;

function cargarPrevisualizacion(videoNombre, proyectoId) {
    const player = document.getElementById('main-player');
    const container = document.getElementById('preview-container');
    const titleEl = document.getElementById('current-video-title');
    
    // 1. Construir la URL correcta apuntando al puente de FastAPI
    const videoUrl = `/video_files/${videoNombre}`; 

    if (player) {
        // 2. Cambiar la fuente y CARGAR el video
        player.src = videoUrl;
        player.load(); 

        // 3. Mostrar el contenedor si estaba oculto
        if (container) container.style.display = 'block';

        // 4. Intentar reproducir automáticamente
        player.play().catch(error => {
            console.log("Autoplay bloqueado, esperando interacción del usuario.");
        });
    }

    // Actualizar título e info
    if (titleEl) {
        titleEl.innerText = `Reproduciendo: ${videoNombre}`;
    }
}

// Control total con la BARRA ESPACIADORA
document.addEventListener('keydown', (e) => {
    const player = document.getElementById('main-player');
    
    // Solo actúa si no estás escribiendo en un input o textarea
    if (e.code === 'Space' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
        e.preventDefault(); // Evita que la página salte hacia abajo
        if (player) {
            if (player.paused) {
                player.play();
            } else {
                player.pause();
            }
        }
    }
});

/* === CONFIGURAR VIDEO PLAYER === */
function configurarVideoPlayer() {
    const video = document.getElementById('previewVideo');
    if (!video) return;

    // Ocultar video wrap al inicio
    const videoWrap = document.getElementById('previewVideoWrap');
    if (videoWrap) videoWrap.style.display = 'none';

    // Controles nativos SIEMPRE activos
    video.controls = true;

    // Click en video = play/pausa
    video.addEventListener('click', () => {
        video.paused ? video.play() : video.pause();
    });

    // Actualizar icono flotante
    video.addEventListener('play', () => {
        const icon = document.getElementById('pauseOverlayIcon');
        if (icon) icon.textContent = '⏸️';
    });
    video.addEventListener('pause', () => {
        const icon = document.getElementById('pauseOverlayIcon');
        if (icon) icon.textContent = '▶️';
    });

    // Barra espaciadora global (solo si el foco esta en body)
    document.addEventListener('keydown', (e) => {
        if (e.code === 'Space' && e.target === document.body) {
            e.preventDefault();
            video.paused ? video.play() : video.pause();
        }
    });
}

/* === RENDERIZAR VOCES === */
function renderizarListaVoces() {
    console.log("Renderizando lista de voces...");
    const lista = document.getElementById('vozLista');
    if (!lista) {
        console.error("No se encontro el elemento vozLista");
        return;
    }

    const vozSeleccionada = document.getElementById('vozSeleccionada');
    const vozActual = vozSeleccionada ? vozSeleccionada.value : 'es-CO-GonzaloNeural';

    console.log("Voz actual:", vozActual);
    console.log("VOCES disponibles:", VOCES.length);

    try {
        const html = VOCES.map(v => `
            <div class="voz-item ${v.id === vozActual ? 'activo' : ''}" data-voz="${v.id}" onclick="seleccionarVoz('${v.id}')">
                <div class="voz-item-info">
                    <span class="voz-item-nombre">${v.flag} ${v.nombre}</span>
                    <span class="voz-item-region">${v.region}</span>
                </div>
                <button class="voz-btn-probar" onclick="event.stopPropagation(); probarVoz('${v.id}', this)" title="Escuchar muestra">▶️</button>
            </div>
        `).join('');
        lista.innerHTML = html;
        console.log("Voces renderizadas correctamente.");
    } catch (err) {
        console.error("Error al mapear voces:", err);
    }
}

function seleccionarVoz(vozId) {
    document.getElementById('vozSeleccionada').value = vozId;
    document.querySelectorAll('.voz-item').forEach(item => {
        item.classList.toggle('activo', item.dataset.voz === vozId);
    });
}

async function probarVoz(vozId, btnElement) {
    try {
        btnElement.textContent = '⏳';
        const response = await fetch('/api/video/probar-voz', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ voz: vozId })
        });
        
        if (!response.ok) throw new Error('Error: ' + response.status);
        
        const data = await response.json();
        // Stop previous sample if playing
        if (audioMuestraActual) {
            audioMuestraActual.pause();
            audioMuestraActual = null;
        }
        // Play new sample
        audioMuestraActual = new Audio(data.audio_url);
        audioMuestraActual.play().catch(err => {
            console.error('[VOZ] Playback error:', err);
            // Fallback: open in new tab
            window.open(data.audio_url, '_blank');
        });
        btnElement.textContent = '▶️';
    } catch (error) {
        console.error('[VOZ] Error:', error);
        showToast('Error al probar voz', 'error');
        btnElement.textContent = '▶️';
    }
}

async function seleccionarVoz(vozId) {
    document.getElementById('vozSeleccionada').value = vozId;
    document.querySelectorAll('.voz-item').forEach(item => {
        item.classList.toggle('activo', item.dataset.voz === vozId);
    });
    console.log("Voz seleccionada:", vozId);
}

function configurarRatio(ratio) {
    currentRatio = ratio;
    const preview = document.getElementById('previewVideo');
    if (preview) {
        preview.style.aspectRatio = ratio;
        preview.style.width = '100%';
    }
    document.querySelectorAll('.ratio-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.ratio === ratio);
    });
    document.getElementById('previewRatioBadge').textContent = ratio;
}

async function cargarVideoPreview(videoId) {
    const player = document.getElementById('previewVideo');
    const container = document.getElementById('previewVideoWrap');
    const placeholder = document.getElementById('previewPlaceholder');
    const loading = document.getElementById('previewLoading');
    const title = document.getElementById('previewVideoTitle');

    if (!player || !container) return;

    placeholder.style.display = 'none';
    loading.style.display = 'flex';

    try {
        const infoRes = await fetch(`/api/video/info/${videoId}`);
        if (!infoRes.ok) throw new Error('Video no encontrado');
        const info = await infoRes.json();

        player.src = `/video_files/${info.archivo}`;
        player.load();
        title.textContent = info.titulo || 'Video sin título';

        player.onloadeddata = () => {
            loading.style.display = 'none';
            container.style.display = 'block';
            player.play().catch(() => {});
        };

        player.onerror = () => {
            loading.style.display = 'none';
            showToast('Error cargando video', 'error');
        };

    } catch (e) {
        loading.style.display = 'none';
        console.error("Error cargando preview:", e);
        showToast('No se pudo cargar el video', 'error');
    }
}

function togglePausePreview() {
    const player = document.getElementById('previewVideo');
    const icon = document.getElementById('pauseOverlayIcon');
    if (!player) return;

    if (player.paused) {
        player.play();
        icon.textContent = '⏸️';
    } else {
        player.pause();
        icon.textContent = '▶️';
    }
}

async function verificarConexion() {
    try {
        const res = await fetch('/api/health');
        if (res.ok) {
            const data = await res.json();
            console.log("Conexión OK:", data);
            // Actualizar indicador de estado
            const statusDot = document.getElementById('connectionStatus');
            const statusText = document.getElementById('statusText');
            if (statusDot) statusDot.className = 'status-dot connected';
            if (statusText) statusText.textContent = `Conectado - ${data.model || ''}`;
        }
    } catch (e) {
        console.error("Error verificando conexión:", e);
        const statusDot = document.getElementById('connectionStatus');
        const statusText = document.getElementById('statusText');
        if (statusDot) statusDot.className = 'status-dot disconnected';
        if (statusText) statusText.textContent = 'Sin conexión';
    }
}

// Inicializar cuando el DOM carga
document.addEventListener('DOMContentLoaded', () => {
    console.log("Iniciando Hermatron Studio...");
    try {
        renderizarListaVoces();
    } catch (e) { console.error("Error renderizando voces:", e); }
    
    try {
        configurarVideoPlayer();
    } catch (e) { console.error("Error configurando player:", e); }
    
    try {
        verificarConexion();
    } catch (e) { console.error("Error verificando conexión:", e); }
    
    try {
        cargarGaleriaProyectos();
    } catch (e) { console.error("Error cargando galería:", e); }
});

function actualizarRatioPreview() {
    const selected = document.querySelector('input[name="ratio"]:checked');
    const badge = document.getElementById('previewRatioBadge');
    if (selected) badge.textContent = selected.value;
}

/* === PIPELINE: Analizar → Diseñar → Producir === */
async function crearVideoDesdeStudio() {
    console.log("Botón Crear Video presionado");
    const temaInput = document.getElementById('videoTema');
    const promptInput = document.getElementById('videoPrompt');
    const tema = temaInput ? temaInput.value.trim() : '';
    const prompt = promptInput ? promptInput.value.trim() : '';
    const voz = document.getElementById('vozSeleccionada')?.value || 'es-CO-GonzaloNeural';
    const estilo = 'cinematic'; 

    if (!tema || !prompt) {
        showToast('Completa el TEMA y la DESCRIPCIÓN', 'warning');
        if (!tema) temaInput?.focus();
        else promptInput?.focus();
        return;
    }

    const progresoDiv = document.getElementById('studioProgreso');
    const progresoFill = document.getElementById('progresoFill');
    const progresoPorcentaje = document.getElementById('progresoPorcentaje');
    const progresoEstado = document.getElementById('progresoEstado');
    const btnCrear = document.querySelector('.btn-crear-video-studio');

    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }

    progresoDiv.style.display = 'block';
    btnCrear.disabled = true;
    btnCrear.textContent = '🎬 Generando Video...';
    progresoEstado.innerHTML = `🚀 Iniciando proceso...`;
    progresoFill.style.width = '5%';
    progresoPorcentaje.textContent = '5%';
    progresoFill.style.background = '#007BFF';

    try {
        console.log("Enviando solicitud de pre-producción al servidor...");
        const response = await fetch('/api/video/pre-produccion', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                tema: tema,
                prompt: prompt,
                descripcion: prompt,
                voz: voz,
                estilo: estilo
            })
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || `Error: ${response.status}`);
        }

        const data = await response.json();
        console.log("Video creado:", data);
        proyectoActual = data.video_id;

        // Polling loop para checar el progreso
        pollingInterval = setInterval(async () => {
            try {
                const progRes = await fetch(`/api/video/progreso/${proyectoActual}`);
                if (!progRes.ok) return; // Ignorar errores de red temporales
                const progData = await progRes.json();
                
                let pct = progData.progreso || 10;
                progresoFill.style.width = pct + '%';
                progresoPorcentaje.textContent = pct + '%';

                if (pct < 30) {
                    progresoEstado.innerHTML = `🧠 Analizando y diseñando escenas...`;
                } else if (pct < 60) {
                    progresoFill.style.background = '#6f42c1';
                    progresoEstado.innerHTML = `📸 Generando imágenes de alta calidad...`;
                } else if (pct < 85) {
                    progresoFill.style.background = '#fd7e14';
                    progresoEstado.innerHTML = `🎙️ Sintetizando voz y audio...`;
                } else {
                    progresoFill.style.background = '#17a2b8';
                    progresoEstado.innerHTML = `🎬 Ensamblando escenas finales...`;
                }

                if (progData.estado === 'en_review') {
                    clearInterval(pollingInterval);
                    progresoFill.style.width = '100%';
                    progresoFill.style.background = '#007bff';
                    progresoPorcentaje.textContent = '100%';
                    progresoEstado.innerHTML = `✅ <strong>¡Bocetos listos! Revisa el Storyboard.</strong>`;
                    showToast('🎉 Storyboard generado', 'success');

                    await renderStoryboard(proyectoActual);

                    btnCrear.disabled = false;
                    btnCrear.textContent = '🎬 Crear Video Profesional';

                    setTimeout(() => {
                        progresoDiv.style.display = 'none';
                        progresoFill.style.background = '';
                    }, 3000);
                } else if (progData.estado === 'completado') {
                    clearInterval(pollingInterval);
                    progresoFill.style.width = '100%';
                    progresoFill.style.background = '#2ea043';
                    progresoPorcentaje.textContent = '100%';
                    progresoEstado.innerHTML = `✅ <strong>¡Video completado exitosamente!</strong>`;
                    showToast('🎉 ¡Video completado!', 'success');

                    await cargarVideoPreview(proyectoActual);
                    await cargarGaleriaProyectos();
                    
                    const listCreaciones = document.getElementById('galleryListCreaciones');
                    if (listCreaciones) listCreaciones.classList.remove('collapsed');
                    const headerCreaciones = listCreaciones.previousElementSibling;
                    if (headerCreaciones) headerCreaciones.classList.remove('collapsed-header');

                    btnCrear.disabled = false;
                    btnCrear.textContent = '🎬 Crear Video Profesional';

                    setTimeout(() => {
                        progresoDiv.style.display = 'none';
                        progresoFill.style.background = '';
                    }, 5000);
                } else if (progData.estado === 'error' || progData.error) {
                    clearInterval(pollingInterval);
                    throw new Error(progData.error || 'Error desconocido en el servidor');
                }

            } catch (err) {
                clearInterval(pollingInterval);
                console.error('Error polling:', err);
                showToast(`❌ Error: ${err.message}`, 'error');
                progresoEstado.innerHTML = `❌ <strong>Error:</strong> ${err.message}`;
                progresoFill.style.background = '#da3633';
                btnCrear.disabled = false;
                btnCrear.textContent = '🎬 Crear Video Profesional';
            }
        }, 2000);

    } catch (error) {
        console.error('Error iniciar pipeline:', error);
        showToast(`❌ ${error.message}`, 'error');
        progresoEstado.innerHTML = `❌ <strong>Error:</strong> ${error.message}`;
        progresoFill.style.background = '#da3633';
        btnCrear.disabled = false;
        btnCrear.textContent = '🎬 Crear Video Profesional';
    }
}

/* === CARGAR VIDEO EN PREVIEW === */
async function cargarVideoPreview(proyectoId) {
    try {
        const response = await fetch(`/api/video/estado/${proyectoId}`);
        if (!response.ok) throw new Error('Proyecto no encontrado');
        const data = await response.json();
        
        const archivoVideo = data.archivo_final || data.archivo;
        if (!archivoVideo) {
            showToast('⚠️ Video sin archivo generado', 'warning');
            return;
        }

        const placeholder = document.getElementById('previewPlaceholder');
        const videoWrap = document.getElementById('previewVideoWrap');
        const video = document.getElementById('previewVideo');
        const actions = document.getElementById('previewActions');
        const loading = document.getElementById('previewLoading');

        placeholder.style.display = 'none';
        loading.style.display = 'none';

        // Cargar video
        video.src = `/api/video/descargar/${archivoVideo}`;
        video.load();
        video.controls = true;

        // Mostrar
        videoWrap.style.display = 'block';

        // Ratio
        const ratio = document.querySelector('input[name="ratio"]:checked')?.value || '16:9';
        videoWrap.className = `preview-video-wrap ratio-${ratio.replace(':', '-')}`;

        // Info
        document.getElementById('videoInfoTema').textContent = data.tema || 'Sin título';
        document.getElementById('videoMetaFecha').textContent = `📅 ${data.creado_en || '-'}`;
        document.getElementById('videoMetaTamano').textContent = `📦 ${data.tamano || '-'}`;
        const numEscenas = data.escenas_disenadas ? data.escenas_disenadas.length : (data.escenas || 0);
        document.getElementById('videoMetaEscenas').textContent = `🎞️ ${numEscenas} escenas`;

        actions.style.display = 'block';
        proyectoActual = proyectoId;

    } catch (error) {
        console.error('Error cargando preview:', error);
        showToast('❌ Error cargando vista previa: ' + error.message, 'error');
    }
}

function reproducirPreview() {
    const video = document.getElementById('previewVideo');
    if (video && video.src) video.play();
}

function togglePausePreview() {
    const video = document.getElementById('previewVideo');
    const icon = document.getElementById('pauseOverlayIcon');
    if (!video || !video.src) return;

    if (video.paused) {
        video.play();
        icon.textContent = '⏸️';
    } else {
        video.pause();
        icon.textContent = '▶️';
    }
}

function descargarVideoActual() {
    if (!proyectoActual) return;
    fetch(`/api/video/estado/${proyectoActual}`)
        .then(r => r.json())
        .then(data => {
            const archivoVideo = data.archivo_final || data.archivo;
            if (archivoVideo) {
                const link = document.createElement('a');
                link.href = `/api/video/descargar/${archivoVideo}`;
                link.download = archivoVideo;
                link.click();
                showToast('⬇️ Descargando...', 'success');
            }
        });
}

function descargarIDMActual() {
    if (!proyectoActual) return;
    fetch(`/api/video/descargar-idm/${proyectoActual}`, { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.download_url) {
                const link = document.createElement('a');
                link.href = data.download_url;
                link.click();
                showToast('📥 Descarga con IDM iniciada', 'success');
            }
        });
}

async function eliminarVideoActual() {
    if (!proyectoActual) return;
    if (!confirm('¿Eliminar este video permanentemente?')) return;
    try {
        const response = await fetch(`/api/video/eliminar/${proyectoActual}`, { method: 'DELETE' });
        if (response.ok) {
            showToast('🗑️ Video eliminado', 'success');
            document.getElementById('previewPlaceholder').style.display = 'block';
            document.getElementById('previewVideoWrap').style.display = 'none';
            document.getElementById('previewActions').style.display = 'none';
            proyectoActual = null;
            await cargarGaleriaProyectos();
        }
    } catch (error) {
        showToast('❌ Error al eliminar', 'error');
    }
}

async function cargarGaleriaProyectos() {
    try {
        const response = await fetch('/api/video/proyectos');
        const data = await response.json();
        
        const creaciones = data.creaciones || [];
        const importados = data.importados || [];
        const otros = data.otros || [];

        const galleryListCreaciones = document.getElementById('galleryListCreaciones');
        const galleryListImportados = document.getElementById('galleryListImportados');
        const galleryListOtros = document.getElementById('galleryListOtros');

        // Actualizar estadísticas
        document.getElementById('statCreaciones').textContent = creaciones.length;
        document.getElementById('statImportados').textContent = importados.length;
        document.getElementById('statOtros').textContent = otros.length;

        // Renderizar Creaciones IA
        if (creaciones.length === 0) {
            galleryListCreaciones.innerHTML = `<div class="gallery-empty-small"><p>Sin creaciones</p></div>`;
        } else {
            galleryListCreaciones.innerHTML = creaciones.map(p => {
                const isActive = p.id === proyectoActual;
                return `
                    <div class="gallery-item ${isActive ? 'activo' : ''}" onclick="seleccionarProyecto('${p.id}')">
                        <div class="gallery-item-header">
                            <h4 class="gallery-item-title">${p.tema || 'Sin título'}</h4>
                            <span class="gallery-item-estado completado">IA</span>
                        </div>
                        <div class="gallery-item-meta">
                            <span>📅 ${p.creado_en?.substring(0, 10) || '-'}</span>
                            <span>📦 ${p.tamano}</span>
                        </div>
                    </div>
                `;
            }).join('');
        }

        // Renderizar Importados (MP4)
        if (importados.length === 0) {
            galleryListImportados.innerHTML = `<div class="gallery-empty-small"><p>Sin videos importados</p></div>`;
        } else {
            galleryListImportados.innerHTML = importados.map(p => {
                const isActive = p.id === proyectoActual;
                return `
                    <div class="gallery-item item-importado ${isActive ? 'activo' : ''}" onclick="seleccionarProyectoImportado('${p.id}', '${p.archivo}')">
                        <div class="gallery-item-header">
                            <h4 class="gallery-item-title">${p.tema || 'Sin título'}</h4>
                            <span class="gallery-item-estado importado">MP4</span>
                        </div>
                        <div class="gallery-item-meta">
                            <span>📅 ${p.creado_en?.substring(0, 10) || '-'}</span>
                            <span>📦 ${p.tamano}</span>
                        </div>
                    </div>
                `;
            }).join('');
        }

        // Renderizar Otros (MOV, AVI, MKV, etc)
        if (otros.length === 0) {
            galleryListOtros.innerHTML = `<div class="gallery-empty-small">
                <p>Sin archivos adicionales</p>
                <small>Archivos MOV, AVI, MKV, WebM, etc.</small>
            </div>`;
        } else {
            const iconos = { mov: '🎞️', avi: '🎞️', mkv: '🎞️', webm: '🌐', flv: '📺', wmv: '🪟' };
            galleryListOtros.innerHTML = otros.map(p => {
                const isActive = p.id === proyectoActual;
                const icono = iconos[p.tipo] || '📦';
                return `
                    <div class="gallery-item item-otro ${isActive ? 'activo' : ''}" onclick="seleccionarOtro('${p.archivo}', '${p.carpeta}')">
                        <div class="gallery-item-header">
                            <h4 class="gallery-item-title">${p.tema || 'Sin título'}</h4>
                            <span class="gallery-item-estado otro">${icono} ${p.tipo?.toUpperCase()}</span>
                        </div>
                        <div class="gallery-item-meta">
                            <span>📅 ${p.creado_en?.substring(0, 10) || '-'}</span>
                            <span>📦 ${p.tamano}</span>
                        </div>
                    </div>
                `;
            }).join('');
        }

    } catch (error) {
        console.error('Error cargando galería:', error);
    }
}

// Función para seleccionar un archivo "otro"
async function seleccionarOtro(archivo, carpeta) {
    proyectoActual = archivo;
    document.querySelectorAll('.gallery-item').forEach(item => item.classList.remove('activo'));
    event.currentTarget?.classList.add('activo');
    
    const placeholder = document.getElementById('previewPlaceholder');
    const videoWrap = document.getElementById('previewVideoWrap');
    const video = document.getElementById('previewVideo');
    const actions = document.getElementById('previewActions');

    placeholder.style.display = 'none';
    
    // Cargar desde la carpeta correcta
    if (carpeta === 'otros') {
        video.src = `/otros_files/${archivo}`;
    } else {
        video.src = `/video_files/${archivo}`;
    }
    
    video.load();
    videoWrap.style.display = 'block';

    document.getElementById('videoInfoTema').textContent = archivo;
    document.getElementById('videoMetaFecha').textContent = `📅 Archivo`;
    document.getElementById('videoMetaTamano').textContent = `📦 -`;
    document.getElementById('videoMetaEscenas').textContent = `🎬 Formato: ${archivo.split('.').pop()}`;

    actions.style.display = 'block';
}



async function seleccionarProyectoImportado(id, archivo) {
    proyectoActual = id;
    document.querySelectorAll('.gallery-item').forEach(item => item.classList.remove('activo'));
    // Encontrar el elemento clicado (un poco tricky con event)
    event.currentTarget?.classList.add('activo');
    
    // Simular carga de preview para un archivo suelto
    const placeholder = document.getElementById('previewPlaceholder');
    const videoWrap = document.getElementById('previewVideoWrap');
    const video = document.getElementById('previewVideo');
    const actions = document.getElementById('previewActions');

    placeholder.style.display = 'none';
    video.src = `/api/video/descargar/${archivo}`;
    video.load();
    videoWrap.style.display = 'block';

    document.getElementById('videoInfoTema').textContent = archivo;
    document.getElementById('videoMetaFecha').textContent = `📅 Archivo`;
    document.getElementById('videoMetaTamano').textContent = `📦 -`;
    document.getElementById('videoMetaEscenas').textContent = `🎬 Externo`;

    actions.style.display = 'block';
}

async function seleccionarProyecto(proyectoId) {
    proyectoActual = proyectoId;
    document.querySelectorAll('.gallery-item').forEach(item => item.classList.remove('activo'));
    event.currentTarget?.classList.add('activo');
    await cargarVideoPreview(proyectoId);
}

async function limpiarGaleria() {
    if (!confirm('¿Eliminar TODOS los videos y caché?')) return;
    try {
        const response = await fetch('/api/video/proyectos');
        const data = await response.json();
        const todos = [...(data.creaciones || []), ...(data.importados || [])];
        
        for (const p of todos) {
            await fetch(`/api/video/eliminar/${p.id}`, { method: 'DELETE' });
        }
        await fetch('/api/video/limpiar-cache', { method: 'POST' });
        showToast('🗑️ Galería y caché limpiados', 'success');
        cargarGaleriaProyectos();
        document.getElementById('previewPlaceholder').style.display = 'block';
        document.getElementById('previewVideoWrap').style.display = 'none';
        document.getElementById('previewActions').style.display = 'none';
        proyectoActual = null;
    } catch (error) {
        showToast('❌ Error al limpiar', 'error');
    }
}

async function limpiarCache() {
    if (!confirm('¿Limpiar archivos temporales (clips, escenas, metadata)?\nLos videos finales NO se eliminan.')) return;
    try {
        const res = await fetch('/api/video/limpiar-cache', { method: 'POST' });
        const data = await res.json();
        showToast(`🧹 Caché limpiada: ${data.eliminados} archivos (${data.espacio_liberado})`, 'success');
    } catch (error) {
        showToast('❌ Error limpiando caché', 'error');
    }
}

function showToast(mensaje, tipo = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${tipo}`;
    toast.textContent = mensaje;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Función para importar video local al Estudio (Universal Player)
function importarVideoLocalStudio(file) {
    if (!file) return;
    
    const placeholder = document.getElementById('previewPlaceholder');
    const videoWrap = document.getElementById('previewVideoWrap');
    const video = document.getElementById('previewVideo');
    const actions = document.getElementById('previewActions');
    const loading = document.getElementById('previewLoading');

    if (!video) return;

    // Crear URL temporal del archivo seleccionado
    const videoUrl = URL.createObjectURL(file);
    
    // Ocultar placeholders
    placeholder.style.display = 'none';
    if (loading) loading.style.display = 'none';

    // Configurar el video player del estudio
    video.src = videoUrl;
    video.load();
    video.controls = true;
    video.autoplay = true;

    // Mostrar el contenedor del video
    videoWrap.style.display = 'block';
    
    // Actualizar la barra de información con datos del archivo local
    document.getElementById('videoInfoTema').textContent = `📂 ${file.name}`;
    document.getElementById('videoMetaFecha').textContent = `📅 Archivo Local`;
    document.getElementById('videoMetaTamano').textContent = `📦 ${(file.size / (1024 * 1024)).toFixed(2)} MB`;
    document.getElementById('videoMetaEscenas').textContent = `🎬 Reproductor Externo`;

    // Mostrar botones de acción (aunque algunas como eliminar no aplicarán a archivos locales)
    actions.style.display = 'block';
    
    showToast('🎬 ¡Video externo cargado en el estudio!', 'success');
}

// Función para colapsar/expandir secciones de la galería
function toggleSeccionGaleria(id) {
    const el = document.getElementById(id);
    if (!el) return;
    
    el.classList.toggle('collapsed');
    
    // Rotar la flecha si el evento viene de un click
    if (window.event && window.event.currentTarget) {
        window.event.currentTarget.classList.toggle('collapsed-header');
    }
}

async function guardarEnPC() {
    if (!proyectoActual) return;
    
    const res = document.getElementById('exportResolution').value;
    showToast(`⚙️ Preparando exportación en ${res}p...`, 'info');
    
    try {
        const response = await fetch(`/api/video/exportar-pc`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                proyecto_id: proyectoActual,
                resolucion: res
            })
        });
        
        const data = await response.json();
        if (data.status === 'success') {
            showToast(`✅ Video guardado en: ${data.ruta}`, 'success');
        } else {
            showToast(`❌ Error: ${data.message}`, 'error');
        }
    } catch (error) {
        showToast('❌ Error de conexión al exportar', 'error');
    }
}

// ==========================================
// STORYBOARD EDITOR FUNCIONES
// ==========================================

async function renderStoryboard(proyectoId) {
    document.getElementById('previewPlaceholder').style.display = 'none';
    document.getElementById('previewVideoWrap').style.display = 'none';
    document.getElementById('previewActions').style.display = 'none';
    const container = document.getElementById('storyboardContainer');
    const grid = document.getElementById('storyboardGrid');
    
    container.style.display = 'block';
    grid.innerHTML = '<div class="spinner"></div> Cargando escenas...';

    try {
        const response = await fetch('/api/video/estado/' + proyectoId);
        const data = await response.json();
        
        grid.innerHTML = '';
        const escenas = data.escenas_disenadas || [];
        
        escenas.forEach(escena => {
            // Extraer solo la ruta relativa de la carpeta videos
            let relPath = escena.imagen_path ? escena.imagen_path.split('videos')[1] : null;
            if (relPath) relPath = relPath.replace(/\\/g, '/');
            const imgUrl = relPath ? '/video_files' + relPath : '';

            const card = document.createElement('div');
            card.className = 'storyboard-card';
            card.style.cssText = 'background: #1e1e24; border-radius: 8px; padding: 10px; border: 1px solid #333; display: flex; flex-direction: column; gap: 10px; position: relative;';
            card.innerHTML = `
                <div style="position: relative; width: 100%; aspect-ratio: 16/9; background: #000; border-radius: 4px; overflow: hidden;">
                    <img id="img-escena-${escena.numero}" src="${imgUrl}" style="width: 100%; height: 100%; object-fit: cover;">
                    <div id="overlay-escena-${escena.numero}" style="position: absolute; top:0; left:0; width:100%; height:100%; background: rgba(0,0,0,0.7); display:none; align-items:center; justify-content:center;">
                        <div class="spinner-small"></div>
                    </div>
                </div>
                <div>
                    <h4 style="margin:0; font-size: 0.9rem; color: #fff;">Escena ${escena.numero}</h4>
                    <p style="font-size: 0.8rem; color: #aaa; margin: 5px 0;">${escena.texto_narracion || ''}</p>
                </div>
                <textarea id="prompt-escena-${escena.numero}" style="font-size: 0.8rem; background: #111; color: #ddd; border: 1px solid #444; border-radius: 4px; padding: 5px; min-height: 60px;">${escena.descripcion_visual || ''}</textarea>
                <button class="btn btn-secondary btn-sm" onclick="regenerarImagen('${proyectoId}', ${escena.numero})">🔄 Regenerar Imagen</button>
            `;
            grid.appendChild(card);
        });
    } catch (e) {
        console.error(e);
        grid.innerHTML = '<p style="color: red;">Error al cargar storyboard.</p>';
    }
}

async function regenerarImagen(proyectoId, escenaNum) {
    const overlay = document.getElementById('overlay-escena-' + escenaNum);
    const imgEl = document.getElementById('img-escena-' + escenaNum);
    const promptInput = document.getElementById('prompt-escena-' + escenaNum).value;
    
    if (overlay) overlay.style.display = 'flex';
    
    try {
        const response = await fetch('/api/video/regenerar-imagen', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                proyecto_id: proyectoId,
                escena_num: escenaNum,
                prompt_visual: promptInput
            })
        });
        const data = await response.json();
        
        if (data.success && data.imagen_path) {
            let relPath = data.imagen_path.split('videos')[1];
            if (relPath) relPath = relPath.replace(/\\/g, '/');
            imgEl.src = '/video_files' + relPath + '?t=' + new Date().getTime();
            showToast('✅ Imagen regenerada con éxito', 'success');
        } else {
            showToast('❌ Error al regenerar la imagen', 'error');
        }
    } catch (e) {
        console.error(e);
        showToast('❌ Error de conexión', 'error');
    } finally {
        if (overlay) overlay.style.display = 'none';
    }
}

async function ensamblarVideoFinal() {
    if (!proyectoActual) return;
    
    document.getElementById('storyboardContainer').style.display = 'none';
    
    const progresoDiv = document.getElementById('studioProgreso');
    const progresoFill = document.getElementById('progresoFill');
    const progresoPorcentaje = document.getElementById('progresoPorcentaje');
    const progresoEstado = document.getElementById('progresoEstado');
    
    progresoDiv.style.display = 'block';
    progresoFill.style.width = '80%';
    progresoPorcentaje.textContent = '80%';
    progresoFill.style.background = '#fd7e14';
    progresoEstado.innerHTML = '🎙️ Generando Voz y Ensamblando el Video Final...';
    
    try {
        await fetch('/api/video/ensamblar', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ proyecto_id: proyectoActual })
        });
        
        // Retomar el polling
        if (pollingInterval) clearInterval(pollingInterval);
        pollingInterval = setInterval(async () => {
            try {
                const progRes = await fetch('/api/video/progreso/' + proyectoActual);
                if (!progRes.ok) return;
                const progData = await progRes.json();
                
                let pct = progData.progreso || 80;
                progresoFill.style.width = pct + '%';
                progresoPorcentaje.textContent = pct + '%';
                
                if (pct >= 90) {
                    progresoFill.style.background = '#17a2b8';
                    progresoEstado.innerHTML = '🎬 Combinando Imágenes, Audio y Subtítulos...';
                }
                
                if (progData.estado === 'completado') {
                    clearInterval(pollingInterval);
                    progresoFill.style.width = '100%';
                    progresoFill.style.background = '#2ea043';
                    progresoPorcentaje.textContent = '100%';
                    progresoEstado.innerHTML = '✅ <strong>¡Video finalizado!</strong>';
                    showToast('🎉 ¡Video Completado!', 'success');

                    await cargarVideoPreview(proyectoActual);
                    await cargarGaleriaProyectos();

                    setTimeout(() => {
                        progresoDiv.style.display = 'none';
                        progresoFill.style.background = '';
                    }, 5000);
                } else if (progData.estado === 'error') {
                    clearInterval(pollingInterval);
                    const errorMsg = progData.error || 'Falló al ensamblar.';
                    progresoEstado.innerHTML = '❌ <strong>Error:</strong> ' + errorMsg;
                    progresoFill.style.background = '#da3633';
                }
            } catch (err) {
                console.error(err);
            }
        }, 2000);
        
    } catch (e) {
        console.error(e);
        showToast('❌ Error iniciando ensamblaje', 'error');
    }
}
