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

    try {
        cargarPersonajes();
    } catch (e) { console.error("Error cargando personajes al iniciar:", e); }

    try {
        cargarEscenografias();
    } catch (e) { console.error("Error cargando escenografías al iniciar:", e); }
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
        console.log("Iniciando Pre-Producción (CapCut Flow)...");
        const ratio = document.querySelector('input[name="ratio"]:checked')?.value || '16:9';
        
        const bgmPath = document.getElementById('bgmPathSelected')?.value || null;

        // Fase 1: Enviar solicitud de pre-producción (solo genera guion e imágenes)
        const response = await fetch('/api/video/pre-produccion', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                tema: tema,
                prompt: prompt,
                voz: voz,
                estilo: estilo,
                formato: ratio,
                bgm_path: bgmPath
            })
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || `Error: ${response.status}`);
        }

        const data = await response.json();
        proyectoActual = data.video_id;

        // Polling loop para checar las fases
        pollingInterval = setInterval(async () => {
            try {
                const progRes = await fetch(`/api/video/progreso/${proyectoActual}`);
                if (!progRes.ok) return;
                const progData = await progRes.json();
                
                let pct = progData.progreso || 10;
                progresoFill.style.width = pct + '%';
                progresoPorcentaje.textContent = pct + '%';

                // Mensajes de fase estilo CapCut
                if (progData.mensaje_estado) {
                    progresoEstado.innerHTML = progData.mensaje_estado;
                } else {
                    if (progData.estado === 'generando_imagenes' || pct < 80) {
                        progresoEstado.innerHTML = `📸 <strong>Fase 1:</strong> Creando imágenes multimedia...`;
                    } else if (pct >= 80 && pct < 90) {
                        progresoEstado.innerHTML = `🎙️ <strong>Fase 2:</strong> Creando la voz superpuesta...`;
                    } else if (pct >= 90 && pct < 100) {
                        progresoEstado.innerHTML = `🎞️ <strong>Fase 3:</strong> Ensamblando escenas y video...`;
                    }
                }

                // Colores de la barra
                if (pct < 80) {
                    progresoFill.style.background = '#6f42c1';
                } else if (pct >= 80 && pct < 90) {
                    progresoFill.style.background = '#fd7e14';
                } else {
                    progresoFill.style.background = '#17a2b8';
                }
                
                // Si el servidor indica que el video está completado
                if (progData.estado === 'completado' || pct >= 100) {
                    console.log("¡Video finalizado! Cargando en la interfaz...");
                    clearInterval(pollingInterval);
                    pollingInterval = null;
                    
                    progresoFill.style.width = '100%';
                    progresoFill.style.background = '#2ea043';
                    progresoEstado.innerHTML = `✅ ¡Video Creado Exitosamente!`;
                    
                    setTimeout(async () => {
                        progresoDiv.style.display = 'none';
                        await cargarVideoPreview(proyectoActual);
                        await cargarGaleriaProyectos();
                        renderStoryboard(proyectoActual);
                    }, 1500);
                }

                if (progData.estado === 'error') {
                    clearInterval(pollingInterval);
                    throw new Error(progData.error || 'Error en pre-producción');
                }
            } catch (err) {
                console.error(err);
                clearInterval(pollingInterval);
                showToast(`❌ Error: ${err.message}`, 'error');
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

    // Mostrar botones de acción
    actions.style.display = 'block';

    // Botón para editar storyboard
    const btnEditId = 'btnEditStoryboardFromPreview';
    let btnEdit = document.getElementById(btnEditId);
    if (!btnEdit) {
        btnEdit = document.createElement('button');
        btnEdit.id = btnEditId;
        btnEdit.className = 'btn btn-secondary';
        btnEdit.style.cssText = 'width: 100%; margin-top: 10px; background: #6f42c1; color: white; border: none; font-size: 0.8rem; border-radius: 8px; padding: 10px; font-weight: 700; cursor: pointer;';
        btnEdit.innerHTML = '🎨 Editar Escenas (Cambiar imágenes)';
        actions.appendChild(btnEdit);
    }
    btnEdit.onclick = () => renderStoryboard(proyectoActual);
    
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
    const container = document.getElementById('storyboardContainer');
    const grid = document.getElementById('storyboardGrid');
    
    // Configurar botones de exportación
    const btnEnsamblar = container.querySelector('.btn-success');
    if (btnEnsamblar) {
        btnEnsamblar.style.display = 'block';
        btnEnsamblar.innerHTML = '🎬 Renderizar Video Final';
        btnEnsamblar.onclick = ensamblarVideoFinal;
    }

    // Asegurar que el progreso se oculte
    const progresoDiv = document.getElementById('studioProgreso');
    if (progresoDiv) progresoDiv.style.display = 'none';

    container.style.display = 'block';
    grid.innerHTML = '<div class="spinner"></div> Cargando escenas...';

    try {
        const response = await fetch('/api/video/estado/' + proyectoId);
        const data = await response.json();
        
        grid.innerHTML = '';
        const escenas = data.escenas_disenadas || [];
        const ratio = data.formato || '16:9';

        escenas.forEach(escena => {
            // Limpieza de rutas para compatibilidad entre Windows/Linux
            let relPath = escena.imagen_path ? (escena.imagen_path.includes('videos') ? escena.imagen_path.split('videos')[1] : escena.imagen_path) : null;
            if (relPath) relPath = relPath.replace(/\\/g, '/');
            const imgUrl = relPath ? '/video_files' + relPath : '';
            
            // Generar opciones del select de personajes de referencia
            const selectedCharName = escena.personaje_ref || '';
            let charOptions = `<option value="" ${!selectedCharName ? 'selected' : ''}>🔮 Auto-detectar Personaje (Default)</option>`;
            if (window.personajes && window.personajes.length > 0) {
                window.personajes.forEach(p => {
                    const isSelected = selectedCharName === p.nombre;
                    charOptions += `<option value="${p.nombre}" ${isSelected ? 'selected' : ''}>👤 ${p.nombre}</option>`;
                });
            }

            // Generar opciones del select de escenografías de referencia
            const selectedEscName = escena.escenografia_ref || '';
            let escOptions = `<option value="" ${!selectedEscName ? 'selected' : ''}>🌍 Auto-detectar Fondo (Default)</option>`;
            if (window.escenografias && window.escenografias.length > 0) {
                window.escenografias.forEach(esc => {
                    const isEscSelected = selectedEscName === esc.nombre;
                    escOptions += `<option value="${esc.nombre}" ${isEscSelected ? 'selected' : ''}>🏞️ ${esc.nombre}</option>`;
                });
            }

            const card = document.createElement('div');
            card.className = 'storyboard-card-new';
            card.innerHTML = `
                <div class="sc-header">
                    <span>🎬 Escena ${escena.numero}</span>
                </div>
                <div class="sc-image-wrap" style="aspect-ratio: ${ratio.replace(':', '/')};">
                    <img id="img-escena-${escena.numero}" src="${imgUrl}" 
                         onclick="window.open('${imgUrl}', '_blank')"
                         onerror="this.src='https://via.placeholder.com/400x700?text=Cargar+imagen+de+escena'"
                         loading="lazy">
                    <button class="btn-regenerar-mini" title="Regenerar esta imagen con IA" onclick="regenerarImagenOpciones('${proyectoId}', ${escena.numero})">
                        🔄
                    </button>
                    <div id="overlay-escena-${escena.numero}" class="sc-overlay">
                        <div class="spinner-small"></div>
                        <span>Procesando...</span>
                    </div>
                    <div class="sc-caption-preview">${escena.texto_narracion || ''}</div>
                </div>
                <div class="sc-content">
                    <p class="sc-narration">${escena.texto_narracion || ''}</p>
                    <div class="sc-prompt-box">
                        <label>AI Art Prompt</label>
                        <textarea id="prompt-escena-${escena.numero}">${escena.descripcion_visual || ''}</textarea>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 10px;">
                        <div class="sc-character-select">
                            <label style="font-size: 0.7rem; color: var(--texto-secundario); font-weight: 600; display: block; margin-bottom: 2px;">👤 Personaje:</label>
                            <select id="char-select-${escena.numero}" class="select-sm" style="width: 100%; background: var(--fondo-terciario); color: var(--texto); border: 1px solid var(--borde); padding: 4px; border-radius: 4px; font-size: 0.75rem;" onchange="actualizarReferenciasEscena('${proyectoId}', ${escena.numero})">
                                ${charOptions}
                            </select>
                        </div>
                        <div class="sc-scene-select">
                            <label style="font-size: 0.7rem; color: var(--texto-secundario); font-weight: 600; display: block; margin-bottom: 2px;">🏞️ Escenario:</label>
                            <select id="esc-select-${escena.numero}" class="select-sm" style="width: 100%; background: var(--fondo-terciario); color: var(--texto); border: 1px solid var(--borde); padding: 4px; border-radius: 4px; font-size: 0.75rem;" onchange="actualizarReferenciasEscena('${proyectoId}', ${escena.numero})">
                                ${escOptions}
                            </select>
                        </div>
                    </div>

                    <div style="margin-top: 10px; border-top: 1px dashed var(--borde); padding-top: 8px;">
                        <label style="font-size: 0.7rem; color: var(--texto-secundario); font-weight: 600; display: block; margin-bottom: 4px;">📁 Cargar Imagen Propia:</label>
                        <input type="file" accept="image/*" style="font-size: 0.75rem; width: 100%; color: var(--texto-secundario);" onchange="subirImagenPropiaEscena('${proyectoId}', ${escena.numero}, this.files[0])">
                    </div>
                </div>
                <div id="alternativas-${escena.numero}" class="sc-alternativas"></div>
            `;
            grid.appendChild(card);
        });
    } catch (e) {
        console.error(e);
        grid.innerHTML = '<p style="color: red;">Error al cargar storyboard.</p>';
    }
}

async function regenerarImagenOpciones(proyectoId, escenaNum) {
    const overlay = document.getElementById('overlay-escena-' + escenaNum);
    const alternativasDiv = document.getElementById('alternativas-' + escenaNum);
    const promptInput = document.getElementById('prompt-escena-' + escenaNum).value;
    
    if (overlay) overlay.style.display = 'flex';
    alternativasDiv.style.display = 'none';
    alternativasDiv.innerHTML = '';
    
    try {
        // Pedimos 2 alternativas al servidor (vía Celery)
        const response = await fetch('/api/video/regenerar-imagen', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                proyecto_id: proyectoId,
                escena_num: escenaNum,
                prompt_visual: promptInput,
                cantidad: 2
            })
        });
        const data = await response.json();
        
        if (data.success && data.result) {
            const opciones = data.result.opciones;
            
            alternativasDiv.style.display = 'flex';
            opciones.forEach((opt, i) => {
                // Convertir ruta absoluta a URL relativa
                let relPath = opt.split('videos')[1].replace(/\\/g, '/');
                const imgUrl = '/video_files' + relPath;
                
                const optDiv = document.createElement('div');
                optDiv.style.cssText = 'flex: 1; cursor: pointer; border: 2px solid #333; border-radius: 8px; overflow: hidden; transition: all 0.2s; position: relative;';
                optDiv.innerHTML = `
                    <img src="${imgUrl}" style="width: 100%; aspect-ratio: 16/9; object-fit: cover;">
                    <div style="position: absolute; bottom: 0; left: 0; width: 100%; background: rgba(0,0,0,0.8); color: #fff; font-size: 0.7rem; text-align: center; padding: 5px;">Opción ${i+1}</div>
                `;
                optDiv.onclick = () => seleccionarAlternativa(proyectoId, escenaNum, opt);
                alternativasDiv.appendChild(optDiv);
            });
            
            if (overlay) overlay.style.display = 'none';
            showToast('🎨 ¡Opciones listas!', 'success');
        } else {
            if (overlay) overlay.style.display = 'none';
            showToast('❌ Error generando alternativas', 'error');
        }
    } catch (e) {
        console.error(e);
        showToast('❌ Error de red', 'error');
        if (overlay) overlay.style.display = 'none';
    }
}

async function seleccionarAlternativa(proyectoId, escenaNum, pathImg) {
    try {
        const response = await fetch('/api/video/seleccionar-imagen', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                proyecto_id: proyectoId,
                escena_num: escenaNum,
                imagen_path: pathImg
            })
        });
        const data = await response.json();
        if (data.success) {
            let relPath = pathImg.split('videos')[1].replace(/\\/g, '/');
            document.getElementById('img-escena-' + escenaNum).src = '/video_files' + relPath + '?t=' + new Date().getTime();
            document.getElementById('alternativas-' + escenaNum).style.display = 'none';
            showToast('✅ Imagen actualizada', 'success');
        }
    } catch (e) {
        showToast('❌ Error al seleccionar', 'error');
    }
}

async function ensamblarVideoFinal() {
    if (!proyectoActual) return;
    
    const res = document.getElementById('exportResolution').value;
    showToast(`🎬 Renderizando video en ${res}p...`, 'info');
    
    // Mostrar progreso final sin ocultar Storyboard
    // document.getElementById('storyboardContainer').style.display = 'none';
    
    const progresoDiv = document.getElementById('studioProgreso');
    const progresoFill = document.getElementById('progresoFill');
    const progresoPorcentaje = document.getElementById('progresoPorcentaje');
    const progresoEstado = document.getElementById('progresoEstado');
    
    progresoDiv.style.display = 'block';
    progresoFill.style.width = '10%';
    progresoPorcentaje.textContent = '10%';
    progresoFill.style.background = '#fd7e14';
    progresoEstado.innerHTML = '🎙️ <strong>Creando la voz superpuesta...</strong>';
    
    try {
        await fetch('/api/video/ensamblar', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ 
                proyecto_id: proyectoActual,
                resolucion: res 
            })
        });
        
        if (pollingInterval) clearInterval(pollingInterval);
        
        pollingInterval = setInterval(async () => {
            try {
                const progRes = await fetch('/api/video/progreso/' + proyectoActual);
                if (!progRes.ok) return;
                const progData = await progRes.json();
                
                let pct = progData.progreso || 10;
                progresoFill.style.width = pct + '%';
                progresoPorcentaje.textContent = pct + '%';
                
                // Mensajes de fase final CapCut Style
                if (progData.mensaje_estado) {
                    progresoEstado.innerHTML = progData.mensaje_estado;
                } else {
                    if (pct < 35) {
                        progresoEstado.innerHTML = '🎙️ <strong>Creando la voz superpuesta...</strong>';
                    } else if (pct < 65) {
                        progresoEstado.innerHTML = '📝 <strong>Creando subtítulos...</strong>';
                    } else {
                        progresoEstado.innerHTML = '🎞️ <strong>Creando el video...</strong>';
                    }
                }

                // Colores de la barra
                if (pct < 35) {
                    progresoFill.style.background = '#fd7e14';
                } else if (pct < 65) {
                    progresoFill.style.background = '#17a2b8';
                } else {
                    progresoFill.style.background = '#2ea043';
                }
                
                if (progData.estado === 'completado') {
                    clearInterval(pollingInterval);
                    pollingInterval = null;
                    
                    progresoFill.style.width = '100%';
                    progresoFill.style.background = '#2ea043';
                    progresoPorcentaje.textContent = '100%';
                    progresoEstado.innerHTML = '✅ ¡Video Finalizado!';
                    showToast('🎉 ¡Tu video está listo!', 'success');

                    await cargarVideoPreview(proyectoActual);
                    await cargarGaleriaProyectos();

                    setTimeout(() => {
                        progresoDiv.style.display = 'none';
                        progresoFill.style.background = '';
                    }, 3000);
                } else if (progData.estado === 'error') {
                    clearInterval(pollingInterval);
                    pollingInterval = null;
                    showToast('❌ Error en el renderizado final', 'error');
                    progresoEstado.innerHTML = '❌ <strong>Error:</strong> ' + (progData.error || 'Fallo');
                    progresoFill.style.background = '#da3633';
                }
            } catch (err) {
                console.error(err);
            }
        }, 2000);
        
    } catch (e) {
        console.error(e);
        showToast('❌ Error al iniciar ensamble', 'error');
    }
}

// ==========================================
// CONTROL DE MÚSICA DE FONDO (BGM)
// ==========================================

async function subirMusicaDeFondo(file) {
    if (!file) return;
    
    const formData = new FormData();
    formData.append('archivo', file);
    
    showToast('📤 Subiendo música de fondo...', 'info');
    
    try {
        const response = await fetch('/api/video/subir-musica', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        if (data.status === 'success') {
            document.getElementById('bgmPathSelected').value = data.bgm_path;
            document.getElementById('bgmFileName').textContent = data.nombre;
            document.getElementById('btnRemoveBgm').style.display = 'inline-block';
            showToast('🎵 Música subida y seleccionada', 'success');
        } else {
            showToast('❌ Error al subir música', 'error');
        }
    } catch (error) {
        showToast('❌ Error de conexión al subir música', 'error');
    }
}

function removerMusicaDeFondo() {
    document.getElementById('bgmPathSelected').value = '';
    document.getElementById('bgmFileName').textContent = 'Sin música';
    document.getElementById('btnRemoveBgm').style.display = 'none';
    document.getElementById('bgmFileInput').value = '';
    showToast('🎵 Música de fondo removida', 'info');
}

// ==========================================
// GESTIÓN DE ELENCO DE PERSONAJES
// ==========================================

window.personajes = [];

async function cargarPersonajes() {
    try {
        const response = await fetch('/api/personajes');
        const data = await response.json();
        window.personajes = data.personajes || [];
        renderCharacterList();
    } catch (error) {
        console.error("Error cargando personajes:", error);
    }
}

window.escenografias = [];

async function cargarEscenografias() {
    try {
        const response = await fetch('/api/escenografias');
        const data = await response.json();
        window.escenografias = data.escenografias || [];
        
        // Renderizar en la biblioteca si el grid existe
        const grid = document.getElementById('gridEscenarios');
        if (grid) {
            if (window.escenografias.length === 0) {
                grid.innerHTML = `
                    <div style="grid-column: 1/-1; text-align: center; padding: 40px; background: rgba(255,255,255,0.02); border: 1px dashed var(--borde); border-radius: 12px; color: var(--texto-secundario);">
                        <div style="font-size: 2.5rem; margin-bottom: 10px;">🏞️</div>
                        <p style="margin: 0; font-size: 0.95rem; font-weight: 500;">No hay escenarios personalizados registrados.</p>
                        <p style="margin: 5px 0 0 0; font-size: 0.8rem; color: rgba(255,255,255,0.3);">Usa el panel de la izquierda para registrar tu primer escenario.</p>
                    </div>
                `;
                return;
            }

            grid.innerHTML = '';
            window.escenografias.forEach(esc => {
                const card = document.createElement('div');
                card.className = 'card-escenario';
                card.style.cssText = `
                    background: #1c1c24;
                    border: 1px solid var(--borde);
                    border-radius: 12px;
                    overflow: hidden;
                    transition: transform 0.2s, border-color 0.2s;
                `;

                const photoUrl = esc.imagen_path || 'https://via.placeholder.com/300x160?text=🏞️+Sin+Imagen';

                card.innerHTML = `
                    <div class="card-img-wrap" style="position:relative; height:150px; overflow:hidden; background:#000;">
                        <img class="card-img" src="${photoUrl}" style="width:100%; height:100%; object-fit:cover;" onerror="this.src='https://via.placeholder.com/300x160?text=🏞️+Escenario'">
                        <div class="card-labels" style="position:absolute; bottom:8px; left:8px; display:flex; gap:4px; flex-wrap:wrap;">
                            <span class="badge-tag" style="background:rgba(0,0,0,0.6); padding:2px 6px; border-radius:4px; font-size:0.68rem; color:#fff;">🌦️ ${esc.clima.toUpperCase()}</span>
                            <span class="badge-tag" style="background:rgba(0,0,0,0.6); padding:2px 6px; border-radius:4px; font-size:0.68rem; color:#fff;">⏰ ${esc.hora_dia.toUpperCase()}</span>
                            <span class="badge-tag" style="background:rgba(0,0,0,0.6); padding:2px 6px; border-radius:4px; font-size:0.68rem; color:#fff;">🪨 ${esc.material_suelo.toUpperCase()}</span>
                        </div>
                    </div>
                    <div class="card-body" style="padding:15px; display:flex; flex-direction:column; gap:8px;">
                        <h4 class="card-title" style="margin:0; font-size:0.95rem; color:#fff; font-weight:600;">${esc.nombre}</h4>
                        <p class="card-desc" style="margin:0; font-size:0.8rem; color:var(--texto-secundario); display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; min-height:34px;">${esc.descripcion}</p>
                        <div class="card-footer" style="margin-top:5px;">
                            <button type="button" class="btn btn-sm btn-danger" style="font-size:0.75rem; padding: 4px 10px; width:100%;" onclick="eliminarEscenografia('${esc.nombre}')">🗑️ Eliminar</button>
                        </div>
                    </div>
                `;
                grid.appendChild(card);
            });
        }
    } catch (error) {
        console.error("Error cargando escenografías:", error);
    }
}

function renderCharacterList() {
    const listDiv = document.getElementById('characterList');
    if (!listDiv) return;

    if (window.personajes.length === 0) {
        listDiv.innerHTML = `
            <div style="font-size: 0.8rem; color: var(--texto-secundario); text-align: center; padding: 10px; background: var(--fondo-terciario); border-radius: 6px; border: 1px dashed var(--borde);">
                Sin personajes registrados
            </div>
        `;
        return;
    }

    // Cargar voces disponibles (una sola vez)
    if (!window._vocesDisponibles) {
        fetch('/api/voces').then(r => r.json()).then(data => {
            window._vocesDisponibles = data.voces || [];
            renderCharacterList(); // Re-render con voces
        }).catch(() => {
            window._vocesDisponibles = [];
        });
        return;
    }

    const voces = window._vocesDisponibles;

    listDiv.innerHTML = '';
    window.personajes.forEach(p => {
        const vozActual = p.voz_edge_tts || 'es-MX-JorgeNeural';
        const card = document.createElement('div');
        card.style.cssText = `
            background: var(--fondo-terciario);
            border: 1px solid var(--borde);
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 4px;
            transition: border-color 0.2s;
        `;

        const photoUrl = p.imagen_path || 'https://via.placeholder.com/40?text=👤';

        // Construir opciones del selector de voz
        const opcionesVoz = voces.map(v =>
            `<option value="${v.id}" ${v.id === vozActual ? 'selected' : ''}>${v.nombre}</option>`
        ).join('');

        card.innerHTML = `
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
                <img src="${photoUrl}" style="width:36px; height:36px; border-radius:50%; object-fit:cover; border:2px solid var(--borde);" onerror="this.src='https://via.placeholder.com/36?text=👤'">
                <div style="flex:1; overflow:hidden;">
                    <span style="display:block; color:var(--texto); font-size:0.85rem; font-weight:600;">${p.nombre}</span>
                    <span style="font-size:0.68rem; color:var(--texto-secundario); display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${p.descripcion_fisica}</span>
                </div>
                <button type="button" style="padding:2px 6px; font-size:0.7rem; background:transparent; border:1px solid var(--borde); border-radius:4px; color:var(--texto-secundario); cursor:pointer;" onclick="eliminarPersonaje('${p.nombre}')" title="Eliminar">✕</button>
            </div>

            <!-- 🎙️ Selector de Voz -->
            <div style="display:flex; align-items:center; gap:6px;">
                <span style="font-size:0.7rem; color:var(--texto-secundario); white-space:nowrap;">🎙️ Voz:</span>
                <select id="voz_${p.nombre.replace(/\s/g,'_')}"
                        onchange="actualizarVozPersonaje('${p.nombre}', this.value)"
                        style="flex:1; font-size:0.72rem; padding:3px 6px;
                               background:var(--fondo-secundario); color:var(--texto);
                               border:1px solid var(--borde); border-radius:4px; cursor:pointer;">
                    ${opcionesVoz}
                </select>
                <button type="button" title="Escuchar preview"
                        onclick="probarVoz('${p.nombre}', '${vozActual}')"
                        style="padding:3px 7px; font-size:0.75rem; background:var(--acento);
                               color:white; border:none; border-radius:4px; cursor:pointer;">▶</button>
            </div>
        `;
        listDiv.appendChild(card);
    });
}

function abrirModalNuevoPersonaje() {
    document.getElementById('modalPersonaje').style.display = 'flex';
}

function cerrarModalPersonaje() {
    document.getElementById('modalPersonaje').style.display = 'none';
    document.getElementById('formPersonaje').reset();
}

async function guardarPersonaje(event) {
    event.preventDefault();
    
    const nombre = document.getElementById('charName').value.trim();
    const descripcion = document.getElementById('charDesc').value.trim();
    const prompt = document.getElementById('charPrompt').value.trim();
    const imagenFile = document.getElementById('charImage').files[0];
    
    if (!nombre || !descripcion || !prompt) {
        showToast('Por favor completa todos los campos requeridos', 'warning');
        return;
    }
    
    const formData = new FormData();
    formData.append('nombre', nombre);
    formData.append('descripcion_fisica', descripcion);
    formData.append('prompt_referencia', prompt);
    if (imagenFile) {
        formData.append('imagen', imagenFile);
    }
    
    showToast('💾 Guardando personaje...', 'info');
    
    try {
        const response = await fetch('/api/personajes', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        if (response.ok) {
            showToast(`✅ Personaje ${nombre} guardado`, 'success');
            cerrarModalPersonaje();
            await cargarPersonajes();
        } else {
            showToast('❌ Error guardando personaje', 'error');
        }
    } catch (error) {
        showToast('❌ Error de red al guardar personaje', 'error');
    }
}

async function eliminarPersonaje(nombre) {
    if (!confirm(`¿Seguro que deseas eliminar a ${nombre}?`)) return;
    
    showToast('🗑️ Eliminando personaje...', 'info');
    
    try {
        const response = await fetch(`/api/personajes/${nombre}`, {
            method: 'DELETE'
        });
        if (response.ok) {
            showToast(`✅ Personaje ${nombre} eliminado`, 'success');
            await cargarPersonajes();
        } else {
            showToast('❌ Error al eliminar', 'error');
        }
    } catch (error) {
        showToast('❌ Error de red', 'error');
    }
}

async function seleccionarPersonajeReferencia(proyectoId, escenaNum, value) {
    if (value === 'ia') {
        // Si elige IA, volvemos a regenerar la imagen (usando la IA)
        regenerarImagenOpciones(proyectoId, escenaNum);
        return;
    }
    
    // Mostrar overlay de cargando
    const overlay = document.getElementById(`overlay-escena-${escenaNum}`);
    if (overlay) overlay.classList.add('active');
    
    try {
        const response = await fetch('/api/video/seleccionar-imagen', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                proyecto_id: proyectoId,
                escena_num: escenaNum,
                imagen_path: value
            })
        });
        const data = await response.json();
        if (data.success) {
            showToast('✅ Imagen de referencia aplicada', 'success');
            // Recargar imagen en el preview del DOM
            let relPath = value.replace(/\\/g, '/');
            document.getElementById('img-escena-' + escenaNum).src = relPath + '?t=' + new Date().getTime();
        } else {
            showToast('❌ Error aplicando referencia', 'error');
        }
    } catch (error) {
        showToast('❌ Error de conexión', 'error');
    } finally {
        if (overlay) overlay.classList.remove('active');
    }
}

// Actualizar referencias asignadas (Personaje + Escenario)
async function actualizarReferenciasEscena(proyectoId, escenaNum) {
    const charVal = document.getElementById(`char-select-${escenaNum}`).value;
    const escVal = document.getElementById(`esc-select-${escenaNum}`).value;
    
    try {
        const response = await fetch('/api/video/asignar-referencias', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                proyecto_id: proyectoId,
                escena_num: escenaNum,
                personaje_ref: charVal || null,
                escenografia_ref: escVal || null
            })
        });
        const data = await response.json();
        if (data.success) {
            showToast('🎯 Coherencia vinculada con éxito. Las regeneraciones heredarán este diseño.', 'success');
        }
    } catch (error) {
        showToast('❌ Error de conexión al guardar referencias', 'error');
    }
}

// Carga directa de imagen propia para la toma
async function subirImagenPropiaEscena(proyectoId, escenaNum, file) {
    if (!file) return;
    
    const overlay = document.getElementById(`overlay-escena-${escenaNum}`);
    if (overlay) overlay.classList.add('active');
    
    const formData = new FormData();
    formData.append('proyecto_id', proyectoId);
    formData.append('escena_num', escenaNum);
    formData.append('imagen', file);
    
    try {
        const response = await fetch('/api/video/subir-imagen-escena', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        if (data.success) {
            showToast('📁 Imagen de escena cargada con éxito', 'success');
            // Actualizar previsualización en el DOM
            document.getElementById(`img-escena-${escenaNum}`).src = data.imagen_path + '?t=' + new Date().getTime();
        } else {
            showToast('❌ Error subiendo la imagen propia', 'error');
        }
    } finally {
        if (overlay) overlay.classList.remove('active');
    }
}

// =======================================================================
// ADMINISTRACIÓN DE ESCENARIOS INTEGRADA EN EL VIDEO STUDIO
// =======================================================================
let generatedScenaryBlob = null;

// Pre-generar fondo con Pollinations IA (Gratis)
async function preGenerarFondoIA() {
    const btn = document.getElementById('btnGenFondo');
    const desc = document.getElementById('scDesc').value.trim();
    const clima = document.getElementById('scClima').value;
    const hora = document.getElementById('scHora').value;
    const suelo = document.getElementById('scSuelo').value;
    const preview = document.getElementById('previewGenImg');

    if (!desc) {
        showToast("Escribe una descripción en el formulario para guiar a la IA", "warning");
        return;
    }

    if (btn) {
        btn.innerText = "🎨 Generando fondo...";
        btn.disabled = true;
    }

    try {
        const promptFull = `3d animation style, Pixar style, detailed background scenery of ${desc}. Weather: ${clima}, time of day: ${hora}, ground material: ${suelo}, consistent visual scenery backdrop, clean environment, beautiful masterwork, 4k resolution`;
        const promptCod = encodeURIComponent(promptFull);
        const seed = Math.floor(Math.random() * 99999);
        const url = `https://image.pollinations.ai/prompt/${promptCod}?width=1024&height=576&nologo=true&seed=${seed}&model=flux`;

        const response = await fetch(url);
        if (!response.ok) throw new Error("Falla al contactar a la IA");
        const blob = await response.blob();

        generatedScenaryBlob = blob;

        const objectURL = URL.createObjectURL(blob);
        if (preview) {
            preview.src = objectURL;
            preview.style.display = "block";
        }

        showToast("✨ Fondo pre-generado con éxito", "success");

    } catch (e) {
        console.error("Error pre-generando fondo:", e);
        showToast("No se pudo conectar con el motor de IA de Pollinations", "error");
    } finally {
        if (btn) {
            btn.innerText = "🎨 Pre-generar con IA";
            btn.disabled = false;
        }
    }
}

// Guardar o Editar escenografía
async function guardarEscenografia(event) {
    event.preventDefault();

    const form = document.getElementById('formEscenario');
    const nombre = document.getElementById('scName').value.trim();
    const descripcion = document.getElementById('scDesc').value.trim();
    const clima = document.getElementById('scClima').value;
    const hora_dia = document.getElementById('scHora').value;
    const material_suelo = document.getElementById('scSuelo').value;
    const inputImagen = document.getElementById('scImage');
    const preview = document.getElementById('previewGenImg');

    const formData = new FormData();
    formData.append('nombre', nombre);
    formData.append('descripcion', descripcion);
    formData.append('clima', clima);
    formData.append('hora_dia', hora_dia);
    formData.append('material_suelo', material_suelo);

    if (inputImagen && inputImagen.files.length > 0) {
        formData.append('imagen', inputImagen.files[0]);
    } else if (generatedScenaryBlob) {
        const file = new File([generatedScenaryBlob], `${nombre.replace(/\s/g, '_')}_ia.jpg`, { type: 'image/jpeg' });
        formData.append('imagen', file);
    }

    try {
        const res = await fetch('/api/escenografias', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();

        if (data.status === 'success') {
            showToast(data.message, 'success');
            if (form) form.reset();
            generatedScenaryBlob = null;
            if (preview) preview.style.display = 'none';
            cargarEscenografias();
        } else {
            showToast(data.message || 'Error al guardar', 'error');
        }

    } catch (e) {
        console.error("Error al guardar escenario:", e);
        showToast("Error de conexión al guardar el escenario", "error");
    }
}

// Eliminar escenografía
async function eliminarEscenografia(nombre) {
    if (!confirm(`¿Eliminar definitivamente el escenario '${nombre}'?`)) return;

    try {
        const res = await fetch(`/api/escenografias/${encodeURIComponent(nombre)}`, {
            method: 'DELETE'
        });
        const data = await res.json();

        if (data.status === 'success') {
            showToast(data.message, 'success');
            cargarEscenografias();
        } else {
            showToast(data.message || 'Error al eliminar', 'error');
        }

    } catch (e) {
        console.error("Error al eliminar escenario:", e);
        showToast("Error de conexión al eliminar el escenario", "error");
    }
}
