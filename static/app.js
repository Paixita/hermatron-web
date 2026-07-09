/* HERMATRON v3.0 - JavaScript de la Aplicación */

// Estado global
let audioHabilitado = false;
let enviando = false;
let modoActual = "general";
let conversacionActual = "default";
let modosDisponibles = [];
let panelAbierto = null;
let imagenesSubidas = [];
let audioPausado = false;
let calidadAudio = "edge-tts";

// Variables para elementos DOM (se inicializan en DOMContentLoaded)
let chatContainer, userInput, sendBtn, audioPlayer, audioToggle, typingIndicator;
let statusText, connectionStatus, toastContainer, modoSelector, sidePanel;
let panelContent, panelTitle, statusModel;
let GROQ_MODEL = '';

// Inicialización
document.addEventListener('DOMContentLoaded', async () => {
    // Capturar elementos del DOM aquí, después de que cargan
    chatContainer = document.getElementById('chatContainer');
    userInput = document.getElementById('userInput');
    sendBtn = document.getElementById('sendBtn');
    audioPlayer = document.getElementById('audioPlayer');
    audioToggle = document.getElementById('audioToggle');
    typingIndicator = document.getElementById('typingIndicator');
    statusText = document.getElementById('statusText');
    connectionStatus = document.getElementById('connectionStatus');
    toastContainer = document.getElementById('toastContainer');
    modoSelector = document.getElementById('modoSelector');
    sidePanel = document.getElementById('sidePanel');
    panelContent = document.getElementById('panelContent');
    panelTitle = document.getElementById('panelTitle');
    statusModel = document.getElementById('statusModel');
    
    console.log("✅ [INIT] Elementos DOM inicializados");
    console.log("   statusText:", !!statusText);
    console.log("   connectionStatus:", !!connectionStatus);
    
    await cargarModos();
    verificarConexion();
    await cargarConversaciones();
    await cargarUltimosMensajes();
    
    // Estado inicial del audio: DESACTIVADO
    audioHabilitado = false;
    actualizarEstadoAudioUI();
    
    // Cerrar selector de audio al hacer clic fuera
    document.addEventListener('click', (e) => {
        const selector = document.getElementById('audioQualitySelector');
        const toggle = document.getElementById('audioToggle');
        if (selector && selector.style.display === 'flex' && 
            !selector.contains(e.target) && !toggle.contains(e.target)) {
            selector.style.display = 'none';
        }
    });
    
    // Agregar botón de video después de 1 segundo
    setTimeout(() => {
        const inputActions = document.querySelector('.input-actions');
        if (inputActions && !document.getElementById('btnVideoRapido')) {
            const btnVideo = document.createElement('button');
            btnVideo.className = 'btn-icon';
            btnVideo.id = 'btnVideoRapido';
            btnVideo.innerHTML = '🎬';
            btnVideo.title = 'Crear Video rápidamente';
            btnVideo.onclick = () => abrirModalVideo();
            const audioToggle = document.getElementById('audioToggle');
            inputActions.insertBefore(btnVideo, audioToggle);
        }
    }, 1000);
});


// ================================================================
// CONVERSACIONES
// ================================================================
function limpiarChatUI() {
    document.querySelectorAll('.mensaje').forEach(el => el.remove());
    document.getElementById('welcomeMessage').style.display = 'flex';
}

async function cargarConversaciones() {
    try {
        const response = await fetch('/api/conversaciones');
        const data = await response.json();
        const list = document.getElementById('conversacionesList');
        if (!list) return;
        
        list.innerHTML = data.conversaciones.map(c => `
            <div class="conversacion-item ${c.id === conversacionActual ? 'activo' : ''}" onclick="seleccionarConversacion('${c.id}')">
                <span>💬 ${c.titulo}</span>
                <button class="btn-delete-conv" onclick="borrarConversacion(event, '${c.id}')" title="Eliminar">🗑️</button>
            </div>
        `).join('');
    } catch (e) { console.error('Error cargando conversaciones', e); }
}

async function seleccionarConversacion(id) {
    conversacionActual = id;
    cargarConversaciones();
    limpiarChatUI();
    await cargarUltimosMensajes();
}

function nuevaConversacion() {
    conversacionActual = "conv_" + Date.now();
    cargarConversaciones();
    limpiarChatUI();
}

async function borrarConversacion(e, id) {
    e.stopPropagation();
    if (!confirm('¿Eliminar esta conversación?')) return;
    try {
        await fetch(`/api/conversaciones/${id}`, {method: 'DELETE'});
        if (conversacionActual === id) {
            nuevaConversacion();
        } else {
            cargarConversaciones();
        }
    } catch (err) { console.error(err); }
}

// Cargar modos disponibles
async function cargarModos() {
    try {
        const response = await fetch('/api/modos');
        const data = await response.json();
        modosDisponibles = data.modos;
        renderModosSelector();
    } catch (error) {
        console.error('Error cargando modos:', error);
        // Modos por defecto si falla la API
        modosDisponibles = [
            { id: 'general', nombre: 'General', icono: '🅷', color: '#007BFF', descripcion: 'Asistente creativo multiusos' },
            { id: 'guionista', nombre: 'Guionista', icono: '🎬', color: '#9B59B6', descripcion: 'Experto en guiones para YouTube' },
            { id: 'seo', nombre: 'SEO YouTube', icono: '📈', color: '#2ECC71', descripcion: 'Optimización para YouTube' },
            { id: 'programador', nombre: 'Programador', icono: '💻', color: '#E74C3C', descripcion: 'Experto en código' },
            { id: 'creativo', nombre: 'Creativo', icono: '🎨', color: '#F39C12', descripcion: 'Ideas innovadoras' },
            { id: 'estratega', nombre: 'Estratega', icono: '🧠', color: '#1ABC9C', descripcion: 'Estrategias de crecimiento' }
        ];
        renderModosSelector();
    }
}

// Renderizar selector de modos
function renderModosSelector() {
    modoSelector.innerHTML = modosDisponibles.map(modo => `
        <button class="modo-btn ${modo.id === modoActual ? 'activo' : ''}"
                data-modo="${modo.id}"
                onclick="cambiarModo('${modo.id}')"
                style="--modo-color: ${modo.color}">
            <span class="modo-icono">${modo.icono}</span>
            <span class="modo-nombre">${modo.nombre}</span>
        </button>
    `).join('');
}

// Cambiar modo
function cambiarModo(modo) {
    modoActual = modo;
    const infoModo = modosDisponibles.find(m => m.id === modo);
    if (!infoModo) return;

    // Actualizar UI
    document.querySelectorAll('.modo-btn').forEach(btn => {
        btn.classList.toggle('activo', btn.dataset.modo === modo);
    });

    // Actualizar info del modo actual
    document.getElementById('modoActualIcono').textContent = infoModo.icono;
    document.getElementById('modoActualNombre').textContent = infoModo.nombre;
    document.getElementById('modoActualDesc').textContent = infoModo.descripcion;

    // Actualizar mensaje de bienvenida
    document.getElementById('welcomeIcon').textContent = infoModo.icono;
    document.getElementById('welcomeTitle').textContent = `¡Modo ${infoModo.nombre} activado!`;
    document.getElementById('welcomeText').textContent = infoModo.descripcion;

    showToast(`${infoModo.icono} Modo cambiado a: ${infoModo.nombre}`, 'success');
}

// Cargar plantillas
async function cargarPlantillas() {
    try {
        const response = await fetch('/api/plantillas');
        const data = await response.json();

        panelContent.innerHTML = `
            <div class="plantillas-list">
                ${data.plantillas.map(p => `
                    <div class="plantilla-item" onclick="mostrarFormularioPlantilla('${p.id}')">
                        <h4>${p.nombre}</h4>
                        <p>${p.descripcion}</p>
                    </div>
                `).join('')}
            </div>
            <div id="formularioPlantilla" style="display:none; margin-top: 16px;">
                <input type="text" id="plantillaTema" placeholder="Tema del contenido..." class="input-plantilla">
                <button class="btn btn-primary" onclick="usarPlantilla()" style="margin-top: 8px; width: 100%;">Generar</button>
            </div>
            <div id="resultadoPlantilla" style="margin-top: 16px;"></div>
        `;
    } catch (error) {
        panelContent.innerHTML = '<p class="error">Error cargando plantillas</p>';
    }
}

let plantillaSeleccionada = null;

function mostrarFormularioPlantilla(tipo) {
    plantillaSeleccionada = tipo;
    document.getElementById('formularioPlantilla').style.display = 'block';
    document.getElementById('plantillaTema').focus();
}

async function usarPlantilla() {
    const tema = document.getElementById('plantillaTema').value.trim();
    if (!tema || !plantillaSeleccionada) {
        showToast('⚠️ Ingresa un tema', 'warning');
        return;
    }

    document.getElementById('resultadoPlantilla').innerHTML = '<div class="loading-spinner"></div> Generando...';

    try {
        const response = await fetch('/api/plantilla', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                tipo: plantillaSeleccionada,
                tema: tema
            })
        });

        const data = await response.json();
        document.getElementById('resultadoPlantilla').innerHTML = `
            <div class="resultado-plantilla">
                <h4>✅ Resultado</h4>
                <div class="resultado-content">${formatearRespuesta(data.resultado)}</div>
                <button class="btn btn-secondary" onclick="copiarResultado(this)" style="margin-top: 8px;">📋 Copiar resultado</button>
            </div>
        `;
    } catch (error) {
        document.getElementById('resultadoPlantilla').innerHTML = `<p class="error">Error: ${error.message}</p>`;
    }
}

function copiarResultado(boton) {
    const contenido = boton.previousElementSibling.textContent;
    navigator.clipboard.writeText(contenido).then(() => {
        boton.textContent = '✅ ¡Copiado!';
        setTimeout(() => boton.textContent = '📋 Copiar resultado', 2000);
    });
}

// Cargar panel de exportación
async function cargarExportPanel() {
    panelContent.innerHTML = `
        <div class="export-opciones">
            <h4>Exportar Historial</h4>
            <div class="export-btns">
                <button class="btn btn-primary" onclick="exportarHistorial('json')">📄 Exportar JSON</button>
                <button class="btn btn-primary" onclick="exportarHistorial('csv')">📊 Exportar CSV</button>
            </div>
            <hr style="margin: 16px 0; border-color: var(--borde);">
            <h4>Exportar por Modo</h4>
            <div class="export-modos">
                ${modosDisponibles.map(m => `
                    <button class="btn btn-secondary" onclick="exportarPorModo('${m.id}', 'json')">
                        ${m.icono} ${m.nombre} (JSON)
                    </button>
                `).join('')}
            </div>
        </div>
        <div id="exportResultado" style="margin-top: 16px;"></div>
    `;
}

async function exportarHistorial(formato) {
    document.getElementById('exportResultado').innerHTML = '<div class="loading-spinner"></div> Exportando...';

    try {
        const response = await fetch('/api/exportar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ formato: formato })
        });

        const data = await response.json();
        document.getElementById('exportResultado').innerHTML = `
            <div class="toast success">
                ✅ Exportado: ${data.registros} registros<br>
                Archivo: ${data.archivo}
            </div>
            <a href="/api/exports/${data.archivo}" class="btn btn-secondary" download style="margin-top: 8px; display: block; text-align: center; text-decoration: none;">
                ⬇️ Descargar
            </a>
        `;
    } catch (error) {
        document.getElementById('exportResultado').innerHTML = `<p class="error">Error: ${error.message}</p>`;
    }
}

async function exportarPorModo(modo, formato) {
    document.getElementById('exportResultado').innerHTML = '<div class="loading-spinner"></div> Exportando...';

    try {
        const response = await fetch('/api/exportar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ formato: formato, modo: modo })
        });

        const data = await response.json();
        document.getElementById('exportResultado').innerHTML = `
            <div class="toast success">
                ✅ Exportado modo '${modo}': ${data.registros} registros<br>
                Archivo: ${data.archivo}
            </div>
            <a href="/api/exports/${data.archivo}" class="btn btn-secondary" download style="margin-top: 8px; display: block; text-align: center; text-decoration: none;">
                ⬇️ Descargar
            </a>
        `;
    } catch (error) {
        document.getElementById('exportResultado').innerHTML = `<p class="error">Error: ${error.message}</p>`;
    }
}

// Limpiar memoria - Modal personalizado
function limpiarMemoria() {
    // Crear modal de confirmación personalizado (reemplaza confirm() del navegador)
    const overlay = document.createElement('div');
    overlay.id = 'modalLimpiarOverlay';
    overlay.style.cssText = `
        position: fixed; top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(0,0,0,0.7); backdrop-filter: blur(8px);
        display: flex; align-items: center; justify-content: center;
        z-index: 9999; animation: fadeIn 0.2s ease;
    `;

    overlay.innerHTML = `
        <div style="
            background: #1a1a2e; border: 1px solid rgba(239,68,68,0.3);
            border-radius: 16px; padding: 32px; max-width: 420px; width: 90%;
            text-align: center; box-shadow: 0 20px 60px rgba(0,0,0,0.5), 0 0 40px rgba(239,68,68,0.1);
            animation: slideIn 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
        ">
            <div style="font-size: 3rem; margin-bottom: 16px;">⚠️</div>
            <h3 style="color: #fafafa; margin: 0 0 8px; font-size: 1.3rem;">¿Eliminar toda la conversación?</h3>
            <p style="color: #a1a1aa; font-size: 0.9rem; margin: 0 0 24px; line-height: 1.5;">
                Esto borrará <strong style="color: #ef4444;">permanentemente</strong> todo el historial de chat y la caché de audio.
            </p>
            <div style="display: flex; gap: 12px; justify-content: center;">
                <button id="btnCancelarLimpiar" style="
                    padding: 10px 24px; border-radius: 8px; font-size: 0.95rem; font-weight: 600;
                    cursor: pointer; border: 1px solid rgba(255,255,255,0.1);
                    background: #27272a; color: #fafafa; transition: all 0.2s;
                " onmouseover="this.style.background='#3f3f46'" onmouseout="this.style.background='#27272a'">
                    Cancelar
                </button>
                <button id="btnConfirmarLimpiar" style="
                    padding: 10px 24px; border-radius: 8px; font-size: 0.95rem; font-weight: 600;
                    cursor: pointer; border: none;
                    background: #ef4444; color: white; transition: all 0.2s;
                " onmouseover="this.style.background='#dc2626'" onmouseout="this.style.background='#ef4444'">
                    🗑️ Sí, eliminar todo
                </button>
            </div>
        </div>
    `;

    document.body.appendChild(overlay);

    // Cerrar con click en overlay oscuro
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) overlay.remove();
    });

    // Botón cancelar
    document.getElementById('btnCancelarLimpiar').addEventListener('click', () => {
        overlay.remove();
    });

    // Botón confirmar
    document.getElementById('btnConfirmarLimpiar').addEventListener('click', async () => {
        const btn = document.getElementById('btnConfirmarLimpiar');
        btn.textContent = '⏳ Eliminando...';
        btn.disabled = true;

        try {
            const response = await fetch('/api/limpiar', { method: 'POST' });

            if (response.ok) {
                overlay.remove();
                showToast('🗑️ Historial ELIMINADO completamente', 'success');
                
                // Limpiar el chat visual
                const chatContainer = document.getElementById('chatMessages');
                if (chatContainer) chatContainer.innerHTML = '';

                // Recargar la página para empezar fresco
                setTimeout(() => {
                    window.location.reload();
                }, 1200);
            } else {
                throw new Error('Error al limpiar');
            }
        } catch (error) {
            console.error('Error limpiando memoria:', error);
            overlay.remove();
            showToast('❌ Error al limpiar historial', 'error');
        }
    });

    // Cerrar con Escape
    const escHandler = (e) => {
        if (e.key === 'Escape') {
            overlay.remove();
            document.removeEventListener('keydown', escHandler);
        }
    };
    document.addEventListener('keydown', escHandler);
}

// Mostrar toast notification
function showToast(mensaje, tipo = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${tipo}`;
    toast.textContent = mensaje;

    toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ================================================================
// FUNCIONES DE MANEJO DE IMÁGENES
// ================================================================

// Wrapper global para el input onchange
window.handleImageUpload = async function(files) {
    console.log('[Imágenes] handleImageUpload llamado, archivos:', files?.length);
    await manejarImagenes(files);
};

// Manejar imágenes subidas
async function manejarImagenes(files) {
    console.log('[Imágenes] manejarImagenes llamado');
    
    if (!files || files.length === 0) {
        console.log('[Imágenes] No hay archivos');
        return;
    }
    
    console.log('[Imágenes] Archivos seleccionados:', files.length);
    
    const maxImagenes = 7;
    const remaining = maxImagenes - imagenesSubidas.length;
    
    if (remaining <= 0) {
        showToast('⚠️ Máximo 7 imágenes permitidas', 'warning');
        return;
    }
    
    const filesArray = Array.from(files).slice(0, remaining);
    console.log(`[Imágenes] Procesando ${filesArray.length} archivo(s)`);
    
    let procesadas = 0;
    
    for (const file of filesArray) {
        console.log(`[Imágenes] Archivo: ${file.name} (${file.type}, ${(file.size/1024).toFixed(1)} KB)`);
        
        if (!file.type.startsWith('image/')) {
            showToast(`⚠️ ${file.name} no es una imagen`, 'warning');
            continue;
        }
        
        try {
            // Usar alta calidad para mejores resultados en visión
            const base64 = await convertirABase64(file, true);
            
            // Detectar resolución para mostrar al usuario
            const img = new Image();
            await new Promise((resolve, reject) => {
                img.onload = resolve;
                img.onerror = reject;
                img.src = base64;
            });
            
            const resolucion = `${img.width}x${img.height}`;
            const es4K = img.width >= 3840 || img.height >= 2160;
            const es2K = img.width >= 2560 || img.height >= 1440;
            const esFullHD = img.width >= 1920 || img.height >= 1080;
            
            let etiquetaResolucion = '';
            if (es4K) etiquetaResolucion = '4K �高清';
            else if (es2K) etiquetaResolucion = '2K 🖥️';
            else if (esFullHD) etiquetaResolucion = 'FullHD 📺';
            
            console.log(`[Imágenes] ✅ Convertida: ${resolucion} ${etiquetaResolucion} - ${base64.length} chars`);
            
            imagenesSubidas.push({
                data: base64,
                name: file.name,
                size: file.size,
                width: img.width,
                height: img.height,
                resolucion: resolucion,
                etiqueta: etiquetaResolucion
            });
            procesadas++;
        } catch (error) {
            console.error('[Imágenes] Error:', error);
            showToast(`❌ Error al procesar ${file.name}`, 'error');
        }
    }
    
    console.log(`[Imágenes] Procesadas: ${procesadas}, Total: ${imagenesSubidas.length}`);
    
    // ACTUALIZAR PREVIEW CON INFO DE RESOLUCIÓN
    actualizarPreviewImagenes();
    
    if (procesadas > 0) {
        const infoResolucion = imagenesSubidas.length > 0 
            ? ` (${imagenesSubidas.map(i => i.etiqueta || 'HD').join(', ')})`
            : '';
        showToast(`🖼️ ${imagenesSubidas.length} imagen(es) lista(s)${infoResolucion} - ¡Ya puedes enviar!`, 'success');
    }
    
    // Limpiar el input
    setTimeout(() => {
        const input = document.getElementById('imageUpload');
        if (input) input.value = '';
    }, 100);
}

// Convertir archivo a base64 con ALTA CALIDAD para 4K/2K/1920
function convertirABase64(file, altaCalidad = true) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => {
            const img = new Image();
            img.onload = () => {
                const canvas = document.createElement('canvas');
                let width = img.width;
                let height = img.height;
                
                // Detectar resolución y ajustar calidad
                const es4K = width >= 3840 || height >= 2160;
                const es2K = width >= 2560 || height >= 1440;
                const esAltaRes = width >= 1920 || height >= 1080;
                
                // Configuración de redimensionamiento por resolución
                let max_size;
                let quality;
                
                if (altaCalidad && es4K) {
                    // Para 4K: mantener hasta 2048px con alta calidad
                    max_size = 2048;
                    quality = 0.85;
                    console.log('[Imágenes] Detectada resolución 4K - Procesando en alta calidad');
                } else if (altaCalidad && es2K) {
                    // Para 2K: mantener hasta 1600px
                    max_size = 1600;
                    quality = 0.8;
                    console.log('[Imágenes] Detectada resolución 2K - Procesando en alta calidad');
                } else if (altaCalidad && esAltaRes) {
                    // Para FullHD: mantener hasta 1200px
                    max_size = 1200;
                    quality = 0.75;
                    console.log('[Imágenes] Detectada resolución FullHD - Procesando en alta calidad');
                } else {
                    // Para imágenes menores: mantener resolución original con calidad alta
                    max_size = Math.max(width, height);
                    quality = 0.9;
                }

                // Calcular nuevas dimensiones manteniendo aspect ratio
                if (width > height) {
                    if (width > max_size) {
                        height *= max_size / width;
                        width = max_size;
                    }
                } else {
                    if (height > max_size) {
                        width *= max_size / height;
                        height = max_size;
                    }
                }

                canvas.width = width;
                canvas.height = height;
                
                // Usar escalado de alta calidad
                const ctx = canvas.getContext('2d');
                ctx.imageSmoothingEnabled = true;
                ctx.imageSmoothingQuality = 'high';
                ctx.drawImage(img, 0, 0, width, height);
                
                // Exportar como PNG para mayor calidad o JPEG con calidad óptima
                const esPNG = file.type === 'image/png' || file.name.toLowerCase().endsWith('.png');
                const dataUrl = esPNG 
                    ? canvas.toDataURL('image/png', 1.0)
                    : canvas.toDataURL('image/jpeg', quality);
                
                console.log(`[Imágenes] Resolución original: ${img.width}x${img.height}, ` +
                    `Procesada: ${Math.round(width)}x${Math.round(height)}, ` +
                    `Calidad: ${Math.round(quality * 100)}%, Tamaño: ${dataUrl.length} chars`);
                
                resolve(dataUrl);
            };
            img.onerror = reject;
            img.src = e.target.result;
        };
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

// Actualizar preview de imágenes
function actualizarPreviewImagenes() {
    const container = document.getElementById('imagePreviewContainer');
    const grid = document.getElementById('imagePreviewGrid');
    
    if (imagenesSubidas.length === 0) {
        container.style.display = 'none';
        return;
    }
    
    container.style.display = 'block';
    grid.innerHTML = '';
    
    imagenesSubidas.forEach((img, index) => {
        const imgDiv = document.createElement('div');
        imgDiv.className = 'image-preview-item';
        
        // Determinar badge de resolución
        const resolucionBadge = img.etiqueta 
            ? `<span class="resolucion-badge">${img.etiqueta}</span>` 
            : '';
        
        imgDiv.innerHTML = `
            <img src="${img.data}" alt="Imagen ${index + 1}">
            ${resolucionBadge}
            <button class="btn-remove-image" onclick="eliminarImagenIndividual(${index})" title="Eliminar imagen">✕</button>
        `;
        grid.appendChild(imgDiv);
    });
}

// Eliminar imagen individual
function eliminarImagenIndividual(index) {
    const imgEliminada = imagenesSubidas[index];
    imagenesSubidas.splice(index, 1);
    actualizarPreviewImagenes();
    showToast(`🗑️ Imagen eliminada: ${imgEliminada?.name || 'imagen'}`, 'info');
}

// Limpiar todas las imágenes
function limpiarImagenes() {
    imagenesSubidas = [];
    actualizarPreviewImagenes();
    document.getElementById('imageUpload').value = '';
}

// ================================================================
// FUNCIONES DE VIDEO
// ================================================================

let videoActual = null;
let videoPollingInterval = null;

// Abrir modal de crear video
function abrirModalVideo() {
    document.getElementById('modalCrearVideo').style.display = 'flex';
    document.getElementById('videoTema').value = '';
    document.getElementById('videoPrompt').value = '';
    document.getElementById('videoDescripcion').value = '';
    document.getElementById('videoTema').focus();
}

// Cerrar modal de crear video
function cerrarModalVideo() {
    document.getElementById('modalCrearVideo').style.display = 'none';
}

// NOTE: togglePanel is defined in the core functions section below


// Iniciar creación de video PRO
async function iniciarCreacionVideoPremium() {
    const tema = document.getElementById('videoTema').value.trim();
    const prompt = document.getElementById('videoPrompt').value.trim();
    const descripcion = document.getElementById('videoDescripcion').value.trim();
    const voz = document.getElementById('videoVoz').value;
    const estilo = document.getElementById('videoEstilo').value;

    if (!tema || !prompt) {
        showToast('⚠️ Completa el Título y el Guion/Descripción', 'warning');
        return;
    }

    cerrarModalVideo();
    showToast('🎬 Iniciando producción de video PRO...', 'info');

    try {
        const response = await fetch('/api/video/crear', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                tema: tema,
                prompt: prompt,
                descripcion: descripcion,
                voz: voz,
                estilo: estilo
            })
        });

        if (!response.ok) {
            throw new Error(`Error ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        videoActual = data.video_id;

        // Agregar mensaje al chat
        agregarMensajeAlChat('user', `🎬 Produciendo video PRO: ${tema}`);
        agregarMensajeAlChat('agente',
            `🎬 **Producción de Video Iniciada**\n\n` +
            `📋 Obra: ${tema}\n` +
            `🎙️ Voz Seleccionada: ${voz}\n` +
            `🎨 Estilo Visual: ${estilo}\n` +
            `🆔 ID: ${data.video_id}\n` +
            `⏳ Estado: ${data.estado}\n\n` +
            `El video se está generando con MoviePy e IA Gratuita. Puedes ver el progreso abajo.`,
            true
        );

        // Iniciar polling de progreso
        iniciarPollingVideo(data.video_id);

        // Mostrar tarjeta de video en el chat
        mostrarTarjetaVideo(data.video_id, tema, data.estado);

    } catch (error) {
        console.error('Error creando video:', error);
        agregarMensajeAlChat('agente', `❌ Error creando video: ${error.message}`);
        showToast('❌ Error al producir video', 'error');
    }
}

// Iniciar polling para verificar progreso del video
function iniciarPollingVideo(videoId) {
    // Limpiar polling anterior si existe
    if (videoPollingInterval) {
        clearInterval(videoPollingInterval);
    }

    videoPollingInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/video/progreso/${videoId}`);
            if (!response.ok) return;

            const data = await response.json();

            // Actualizar tarjeta de video
            actualizarTarjetaVideo(videoId, data);

            // Si completó o hubo error, detener polling
            if (data.estado === 'completado' || data.estado === 'error') {
                clearInterval(videoPollingInterval);
                videoPollingInterval = null;

                if (data.estado === 'completado') {
                    showToast('🎉 ¡Video completado!', 'success');
                    mostrarVistaPreviaVideo(videoId);
                } else {
                    showToast('❌ Error al crear el video', 'error');
                }
            }
        } catch (error) {
            console.error('Error en polling:', error);
        }
    }, 3000); // Cada 3 segundos
}

// Mostrar tarjeta de video en el chat
function mostrarTarjetaVideo(videoId, tema, estado) {
    const tarjetaDiv = document.createElement('div');
    tarjetaDiv.className = 'mensaje agente';
    tarjetaDiv.id = `video-card-${videoId}`;

    tarjetaDiv.innerHTML = `
        <div class="video-card">
            <div class="video-card-header">
                <span class="video-icon">🎬</span>
                <div class="video-card-info">
                    <h4>${tema}</h4>
                    <span class="video-id-badge">${videoId}</span>
                </div>
            </div>
            <div class="video-progress-container">
                <div class="video-progress-bar">
                    <div class="video-progress-fill" id="progress-${videoId}" style="width: 0%"></div>
                </div>
                <span class="video-progress-text" id="progress-text-${videoId}">0%</span>
            </div>
            <div class="video-estado" id="estado-${videoId}">
                <span class="estado-badge estado-${estado}">${estado}</span>
            </div>
            <div class="video-acciones" id="acciones-${videoId}" style="display: none;">
                <!-- Se llena cuando se completa -->
            </div>
        </div>
    `;

    chatContainer.appendChild(tarjetaDiv);
    scrollToBottom();
}

// Actualizar tarjeta de video con progreso
function actualizarTarjetaVideo(videoId, data) {
    const progressFill = document.getElementById(`progress-${videoId}`);
    const progressText = document.getElementById(`progress-text-${videoId}`);
    const estadoEl = document.getElementById(`estado-${videoId}`);
    const accionesEl = document.getElementById(`acciones-${videoId}`);

    if (progressFill) {
        progressFill.style.width = `${data.progreso}%`;
    }
    if (progressText) {
        progressText.textContent = `${data.progreso}%`;
    }

    if (estadoEl) {
        estadoEl.innerHTML = `<span class="estado-badge estado-${data.estado}">${data.estado}</span>`;
    }

    // Si completó, mostrar acciones
    if (data.estado === 'completado' && accionesEl) {
        accionesEl.style.display = 'flex';
        accionesEl.innerHTML = `
            <button class="btn btn-primary btn-sm" onclick="mostrarVistaPreviaVideo('${videoId}')">
                👁️ Ver Video
            </button>
            <button class="btn btn-success btn-sm" onclick="descargarVideo('${videoId}')">
                ⬇️ Descargar
            </button>
            <button class="btn btn-idm btn-sm" onclick="descargarConIDM('${videoId}')">
                📥 IDM
            </button>
            <button class="btn btn-danger btn-sm" onclick="eliminarVideo('${videoId}')">
                🗑️ Eliminar
            </button>
        `;
    }

    // Si hubo error, mostrar botón de reintentar/eliminar
    if (data.estado === 'error' && accionesEl) {
        accionesEl.style.display = 'flex';
        accionesEl.innerHTML = `
            <button class="btn btn-danger btn-sm" onclick="eliminarVideo('${videoId}')">
                🗑️ Eliminar
            </button>
            <span class="video-error">${data.error || 'Error desconocido'}</span>
        `;
    }

    scrollToBottom();
}

// Mostrar vista previa del video
async function mostrarVistaPreviaVideo(videoId) {
    try {
        const response = await fetch(`/api/video/estado/${videoId}`);
        if (!response.ok) throw new Error('Video no encontrado');

        const data = await response.json();
        const previewPanel = document.getElementById('videoPreviewPanel');
        const previewContent = document.getElementById('videoPreviewContent');

        if (!data.archivo) {
            previewContent.innerHTML = '<p class="error">Video no disponible aún</p>';
            previewPanel.style.display = 'flex';
            return;
        }

        const videoUrl = `/api/video/descargar/${data.archivo}`;

        previewContent.innerHTML = `
            <div class="video-preview">
                <div class="video-preview-info">
                    <h4>🎬 ${data.tema}</h4>
                    <div class="video-meta">
                        <span>📅 ${data.creado_en}</span>
                        ${data.duracion ? `<span>⏱️ ${data.duracion}s</span>` : ''}
                        ${data.tamano ? `<span>📦 ${data.tamano}</span>` : ''}
                        <span>🎞️ ${data.escenas} escenas</span>
                    </div>
                </div>

                <div class="video-player-container">
                    <video controls class="video-player" preload="metadata">
                        <source src="${videoUrl}" type="video/mp4">
                        Tu navegador no soporta video HTML5.
                    </video>
                </div>

                <div class="video-acciones-preview">
                    <button class="btn btn-primary" onclick="descargarVideo('${videoId}')">
                        ⬇️ Descargar Video
                    </button>
                    <button class="btn btn-idm" onclick="descargarConIDM('${videoId}')">
                        📥 Descargar con IDM
                    </button>
                    <button class="btn btn-danger" onclick="eliminarVideo('${videoId}')">
                        🗑️ Eliminar Video
                    </button>
                </div>

                <div class="video-quality-check">
                    <h5>¿El video quedó bien?</h5>
                    <div class="quality-actions">
                        <button class="btn btn-success btn-sm" onclick="aprobarVideo('${videoId}')">
                            ✅ Sí, está perfecto
                        </button>
                        <button class="btn btn-warning btn-sm" onclick="eliminarVideo('${videoId}', true)">
                            🔄 No, crear otro
                        </button>
                    </div>
                </div>
            </div>
        `;

        previewPanel.style.display = 'flex';

    } catch (error) {
        console.error('Error mostrando vista previa:', error);
        showToast('❌ Error al cargar vista previa', 'error');
    }
}

// Cerrar vista previa de video
function cerrarVideoPreview() {
    document.getElementById('videoPreviewPanel').style.display = 'none';
}

// Función para importar y reproducir CUALQUIER video local (Universal Player)
function importarVideoLocal(file) {
    if (!file) return;
    
    const previewPanel = document.getElementById('videoPreviewPanel');
    const previewContent = document.getElementById('videoPreviewContent');
    
    if (!previewPanel || !previewContent) return;
    
    // Crear una URL temporal para el archivo local
    const videoUrl = URL.createObjectURL(file);
    const fileName = file.name;
    const fileSize = (file.size / (1024 * 1024)).toFixed(2) + ' MB';
    const fileType = file.type || 'video/mp4';
    
    previewContent.innerHTML = `
        <div class="video-preview">
            <div class="video-preview-info">
                <h4 style="color: var(--accent-primary); display: flex; align-items: center; gap: 8px;">
                    <span>📂</span> ${fileName}
                </h4>
                <div class="video-meta" style="margin-bottom: 15px;">
                    <span class="meta-tag" style="background: rgba(255,255,255,0.05); padding: 4px 8px; border-radius: 4px; font-size: 0.8rem;">📦 ${fileSize}</span>
                    <span class="meta-tag" style="background: rgba(111, 66, 193, 0.2); color: #a855f7; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem;">🎬 Reproductor Universal</span>
                </div>
            </div>

            <div class="video-player-container" style="background: #000; border-radius: 12px; overflow: hidden; aspect-ratio: 16/9; border: 1px solid var(--borde); box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
                <video controls class="video-player" style="width: 100%; height: 100%;" autoplay>
                    <source src="${videoUrl}" type="${fileType}">
                    Tu navegador no soporta video HTML5.
                </video>
            </div>

            <div class="video-acciones-preview" style="margin-top: 20px; display: flex; flex-direction: column; gap: 10px;">
                <p style="font-size: 0.85rem; color: var(--texto-secundario); text-align: center; font-style: italic;">
                    "Previsualizando archivo externo en el entorno de Hermatron"
                </p>
                <button class="btn btn-secondary" onclick="cerrarVideoPreview()" style="width: 100%; padding: 12px;">
                    ✕ Cerrar Reproductor
                </button>
            </div>
        </div>
    `;
    
    previewPanel.style.display = 'flex';
    showToast('🎬 ¡Video cargado en el reproductor universal!', 'success');
}

// Descargar video
async function descargarVideo(videoId) {
    try {
        const response = await fetch(`/api/video/estado/${videoId}`);
        const data = await response.json();

        if (!data.archivo) {
            showToast('❌ Video no disponible', 'error');
            return;
        }

        // Descargar directamente
        const link = document.createElement('a');
        link.href = `/api/video/descargar/${data.archivo}`;
        link.download = data.archivo;
        link.click();

        showToast('⬇️ Descargando video...', 'success');
    } catch (error) {
        console.error('Error descargando:', error);
        showToast('❌ Error al descargar', 'error');
    }
}

// Descargar con IDM
async function descargarConIDM(videoId) {
    try {
        const response = await fetch(`/api/video/descargar-idm/${videoId}`, {
            method: 'POST'
        });
        const data = await response.json();

        if (data.download_url) {
            // Opción 1: Abrir URL directa (IDM la intercepta)
            showToast('📥 Preparando descarga con IDM...', 'success');

            // Crear enlace temporal y hacer clic
            const link = document.createElement('a');
            link.href = data.download_url;
            link.download = '';
            link.style.display = 'none';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);

            // Mostrar instrucciones
            showToast('💡 Si IDM no inicia, ejecuta el archivo .bat descargado', 'warning');
        }
    } catch (error) {
        console.error('Error con IDM:', error);
        showToast('❌ Error al conectar con IDM', 'error');
    }
}

// Eliminar video
async function eliminarVideo(videoId, recrear = false) {
    const mensaje = recrear
        ? '¿Eliminar este video para crear uno nuevo?'
        : '¿Estás seguro de que quieres eliminar este video?';

    if (!confirm(mensaje)) return;

    try {
        const response = await fetch(`/api/video/eliminar/${videoId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showToast('🗑️ Video eliminado', 'success');

            // Ocultar tarjeta del chat
            const card = document.getElementById(`video-card-${videoId}`);
            if (card) card.remove();

            // Cerrar vista previa
            cerrarVideoPreview();

            // Si quiere recrear, abrir modal
            if (recrear) {
                abrirModalVideo();
            }
        } else {
            throw new Error('Error al eliminar');
        }
    } catch (error) {
        console.error('Error eliminando video:', error);
        showToast('❌ Error al eliminar video', 'error');
    }
}

// Aprobar video (feedback positivo)
function aprobarVideo(videoId) {
    showToast('✅ ¡Video aprobado! Excelente calidad', 'success');
    cerrarVideoPreview();
}

// ================================================================
// FUNCIONES CORE DEL CHAT (RESTAURADAS)
// ================================================================

// Verificar conexión con el servidor
async function verificarConexion() {
    try {
        const response = await fetch('/api/health');
        const data = await response.json();

        if (data.status === 'healthy') {
            if (connectionStatus) connectionStatus.className = 'status-dot connected';
            if (statusText) statusText.textContent = 'Conectado';
            if (statusModel) {
                GROQ_MODEL = data.model || '';
                statusModel.textContent = data.model || '';
            }
        } else {
            if (connectionStatus) connectionStatus.className = 'status-dot disconnected';
            if (statusText) statusText.textContent = 'Error';
        }
    } catch (error) {
        console.error('Error verificando conexión:', error);
        if (connectionStatus) connectionStatus.className = 'status-dot disconnected';
        if (statusText) statusText.textContent = 'Sin conexión';
    }
}

// Cargar últimos mensajes del historial
async function cargarUltimosMensajes() {
    try {
        const response = await fetch('/api/memoria');
        const data = await response.json();

        if (data.ultimos_mensajes && data.ultimos_mensajes.length > 0) {
            // Ocultar mensaje de bienvenida
            const welcomeMsg = document.getElementById('welcomeMessage');
            if (welcomeMsg) welcomeMsg.style.display = 'none';

            for (const msg of data.ultimos_mensajes) {
                agregarMensajeAlChat(msg.role === 'user' ? 'user' : 'agente', msg.content, false);
            }
            scrollToBottom();
        }
    } catch (error) {
        console.error('Error cargando historial:', error);
    }
}

// Auto-resize del textarea
function autoResize(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 200) + 'px';
}

// Manejar teclas
function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        enviar();
    }
}

// Scroll al final del chat
function scrollToBottom() {
    if (chatContainer) {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
}

// Formatear respuesta con markdown básico
function formatearRespuesta(texto) {
    if (!texto) return '';

    // Escapar HTML
    let html = texto
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    // Imágenes ![alt](url)
    html = html.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<div class="mensaje-imagen"><img src="$2" alt="$1" onclick="window.open(\'$2\', \'_blank\')"></div>');

    // Bloques de código (```)
    html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (match, lang, code) => {
        const id = 'code-' + Math.random().toString(36).substr(2, 9);
        return `<div class="code-block-container">
            <div class="code-block-header">
                <span class="code-lang">${lang || 'código'}</span>
                <button class="btn-copy-code" onclick="window.copiarCodigo(this, '${id}')">📋 Copiar</button>
            </div>
            <pre><code id="${id}" class="language-${lang || 'text'}">${code.trim()}</code></pre>
        </div>`;
    });

    // Código inline (`)
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Negrita (**texto**)
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // Itálica (*texto*)
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // Enlaces [texto](url)
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');

    // Listas con -
    html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');

    // Listas numeradas
    html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');

    // Headers
    html = html.replace(/^### (.+)$/gm, '<h4>$1</h4>');
    html = html.replace(/^## (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^# (.+)$/gm, '<h2>$1</h2>');

    // Saltos de línea
    html = html.replace(/\n/g, '<br>');

    return html;
}

// Agregar mensaje al chat
function agregarMensajeAlChat(rol, contenido, animar = true) {
    // Ocultar bienvenida
    const welcomeMsg = document.getElementById('welcomeMessage');
    if (welcomeMsg) welcomeMsg.style.display = 'none';

    const msgDiv = document.createElement('div');
    msgDiv.className = `mensaje ${rol}`;

    if (animar) {
        msgDiv.style.opacity = '0';
        msgDiv.style.transform = 'translateY(10px)';
    }

    const avatarIcon = rol === 'user' ? '👤' : '🅷';
    const nombreRol = rol === 'user' ? 'Tú' : 'HERMATRON';

    msgDiv.innerHTML = `
        <div class="mensaje-header">
            <span class="mensaje-avatar">${avatarIcon}</span>
            <span class="mensaje-nombre">${nombreRol}</span>
        </div>
        <div class="mensaje-contenido">${formatearRespuesta(contenido)}</div>
    `;

    chatContainer.appendChild(msgDiv);

    if (animar) {
        requestAnimationFrame(() => {
            msgDiv.style.transition = 'opacity 0.3s, transform 0.3s';
            msgDiv.style.opacity = '1';
            msgDiv.style.transform = 'translateY(0)';
        });
    }

    scrollToBottom();
}

// Toggle panel lateral
function togglePanel(tipo) {
    if (!tipo || panelAbierto === tipo) {
        sidePanel.style.display = 'none';
        panelAbierto = null;
        return;
    }

    panelAbierto = tipo;
    sidePanel.style.display = 'flex';

    if (tipo === 'plantillasPanel') {
        panelTitle.textContent = '📋 Plantillas Predefinidas';
        cargarPlantillas();
    } else if (tipo === 'exportPanel') {
        panelTitle.textContent = '💾 Exportar Historial';
        cargarExportPanel();
    } else if (tipo === 'configPanel') {
        panelTitle.textContent = '⚙️ Configuración';
        document.getElementById('modalConfig').style.display = 'flex';
        sidePanel.style.display = 'none';
        panelAbierto = null;
    } else if (tipo === 'videoPanel') {
        abrirModalVideo();
        sidePanel.style.display = 'none';
        panelAbierto = null;
    }
}

// Cerrar modal config
function cerrarModalConfig() {
    document.getElementById('modalConfig').style.display = 'none';
}

// Guardar configuración de voz
function guardarConfigVoz() {
    const voz = document.getElementById('configVoz')?.value;
    if (voz) {
        localStorage.setItem('hermatron_voz', voz);
        showToast('🎙️ Voz actualizada', 'success');
    }
}

// Guardar calidad de imagen
function guardarCalidadImg() {
    const calidad = document.querySelector('input[name="calidadImg"]:checked')?.value;
    if (calidad) {
        localStorage.setItem('hermatron_calidad_img', calidad);
        showToast('🖼️ Calidad de imagen actualizada', 'success');
    }
}

// Cambiar tema
function cambiarTema(tema) {
    document.body.className = tema === 'oscuro' ? '' : `tema-${tema}`;
    document.querySelectorAll('.tema-btn').forEach(btn => {
        btn.classList.toggle('activo', btn.dataset.tema === tema);
    });
    localStorage.setItem('hermatron_tema', tema);
}

// Toggle audio
function toggleAudio() {
    audioHabilitado = !audioHabilitado;
    actualizarEstadoAudioUI();
    showToast(audioHabilitado ? '🔊 Audio activado' : '🔇 Audio desactivado', 'info');
}

// Actualizar UI del estado de audio
function actualizarEstadoAudioUI() {
    const toggle = document.getElementById('audioToggle');
    if (toggle) {
        toggle.textContent = audioHabilitado ? '🔊' : '🔇';
        toggle.classList.toggle('active', audioHabilitado);
    }
}

// Toggle selector de audio
function toggleAudioSelector(event) {
    event.stopPropagation();
    const selector = document.getElementById('audioQualitySelector');
    if (selector) {
        selector.style.display = selector.style.display === 'none' ? 'flex' : 'none';
    }
}

// Cambiar calidad de audio
function cambiarCalidadAudio(calidad) {
    calidadAudio = calidad;
    document.querySelectorAll('.quality-option').forEach(opt => {
        opt.classList.toggle('active', opt.dataset.quality === calidad);
    });
    const selector = document.getElementById('audioQualitySelector');
    if (selector) selector.style.display = 'none';

    const nombres = { 'edge-tts': 'Jorge (México)', 'elevenlabs': 'Adam (ElevenLabs)', 'local': 'Local (Windows)' };
    showToast(`🎙️ Voz cambiada a: ${nombres[calidad] || calidad}`, 'success');
}

// Cerrar audio player
function cerrarAudioPlayer() {
    const player = document.getElementById('audioPlayerFlotante');
    const audio = document.getElementById('audioPlayer');
    if (audio) audio.pause();
    if (player) player.style.display = 'none';
}

// Toggle pause audio
function togglePauseAudio() {
    const audio = document.getElementById('audioPlayer');
    const btn = document.getElementById('btnPauseAudio');
    const status = document.getElementById('audioStatus');
    if (!audio) return;

    if (audio.paused) {
        audio.play();
        audioPausado = false;
        if (btn) btn.textContent = '⏸️ Pausar';
        if (status) status.textContent = 'Reproduciendo...';
    } else {
        audio.pause();
        audioPausado = true;
        if (btn) btn.textContent = '▶️ Continuar';
        if (status) status.textContent = 'Pausado';
    }
}

// ================================================================
// FUNCIÓN PRINCIPAL: ENVIAR MENSAJE
// ================================================================
async function enviar() {
    if (grabacionActiva) detenerDictado();
    const texto = userInput.value.trim();
    if ((!texto && imagenesSubidas.length === 0) || enviando) return;

    enviando = true;
    if (sendBtn) sendBtn.disabled = true;
    if (typingIndicator) typingIndicator.textContent = 'HERMATRON está pensando...';

    // Mostrar mensaje del usuario
    const textoMostrar = texto || '🖼️ [Imagen enviada para análisis]';
    agregarMensajeAlChat('user', textoMostrar);

    // Limpiar input
    userInput.value = '';
    autoResize(userInput);

    try {
        let data;

        if (imagenesSubidas.length > 0) {
            // ===== MODO VISIÓN (con imágenes) =====
            console.log(`[ENVIAR] Modo VISIÓN - ${imagenesSubidas.length} imágenes`);

            const formData = new FormData();
            formData.append('prompt', texto || 'Analiza esta imagen y describe todo lo que ves.');
            formData.append('modo', modoActual);
            formData.append('generar_audio', audioHabilitado ? 'true' : 'false');
            formData.append('calidad_audio', calidadAudio);

            // Enviar cada imagen como un campo separado
            for (const img of imagenesSubidas) {
                formData.append('imagenes', img.data);
            }

            const response = await fetch('/api/chat-con-imagenes', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `Error ${response.status}`);
            }

            data = await response.json();

            // Limpiar imágenes después de enviar
            limpiarImagenes();

        } else {
            // ===== MODO TEXTO NORMAL =====
            console.log('[ENVIAR] Modo TEXTO');

            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    prompt: texto,
                    modo: modoActual,
                    generar_audio: audioHabilitado,
                    calidad_audio: calidadAudio,
                    voz_id: null
                })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `Error ${response.status}`);
            }

            data = await response.json();
        }

        // Mostrar respuesta
        agregarMensajeAlChat('agente', data.respuesta);

        // Reproducir audio si se generó
        if (data.audio_generado && data.audio_id) {
            const audioPlayer = document.getElementById('audioPlayer');
            const audioFlotante = document.getElementById('audioPlayerFlotante');
            if (audioPlayer && audioFlotante) {
                audioPlayer.src = `/api/audio/${data.audio_id}`;
                audioFlotante.style.display = 'flex';
                audioPlayer.play().catch(e => console.warn('Autoplay blocked:', e));
            }
        }

    } catch (error) {
        console.error('[ENVIAR] Error:', error);
        agregarMensajeAlChat('agente', `❌ Error: ${error.message}`);
        showToast(`❌ ${error.message}`, 'error');
    } finally {
        enviando = false;
        if (sendBtn) sendBtn.disabled = false;
        if (typingIndicator) typingIndicator.textContent = '';
    }
}

// Función especial solicitada: Nano Banana
async function crearNanoBanana() {
    if (enviando) return;
    
    showToast('🍌 Preparando tu Nano Banana...', 'info');
    
    // Prompt optimizado para la creación de la Nano Banana
    const prompt = "Genera una imagen de un 'Nano Banana'. Sé creativo: que sea una banana pequeña con estilo nanotecnológico, circuitos brillantes o aspecto futurista, alta resolución, estilo cinematográfico.";
    
    // Inyectar en el input y disparar el envío
    const userInput = document.getElementById('userInput');
    if (userInput) {
        userInput.value = prompt;
        // Esperar un momento para que el usuario vea el texto (efecto visual)
        setTimeout(async () => {
            await enviar();
        }, 300);
    }
}

// ==========================================
// SISTEMA DE DICTADO (VOZ A TEXTO)
// ==========================================
let recognition = null;
let grabacionActiva = false;

function toggleDictado() {
    if (grabacionActiva) {
        detenerDictado();
        return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        showToast('❌ Tu navegador no soporta dictado por voz.', 'error');
        return;
    }

    if (!recognition) {
        recognition = new SpeechRecognition();
        recognition.lang = 'es-ES';
        recognition.continuous = true;
        recognition.interimResults = true;

        recognition.onresult = (event) => {
            let transcript = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                transcript += event.results[i][0].transcript;
            }
            userInput.value = transcript;
            autoResize(userInput);
        };

        recognition.onerror = (event) => {
            console.error('Error dictado:', event.error);
            if (event.error !== 'no-speech') {
                detenerDictado();
            }
            if (event.error === 'not-allowed') {
                showToast('❌ Permiso de micrófono denegado.', 'error');
            }
        };

        recognition.onend = () => {
            if (grabacionActiva) {
                try { recognition.start(); } catch(e) {}
            }
        };
    }

    try {
        recognition.start();
        grabacionActiva = true;
        document.getElementById('btnMic').classList.add('grabando');
        showToast('🎤 Escuchando...', 'info');
    } catch (e) {
        console.warn('Error al iniciar dictado:', e);
    }
}

function detenerDictado() {
    grabacionActiva = false;
    if (recognition) {
        recognition.stop();
    }
    const btnMic = document.getElementById('btnMic');
    if (btnMic) btnMic.classList.remove('grabando');
    showToast('✅ Dictado finalizado', 'success');
}
