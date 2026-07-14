// static/escenografias.js
// Panel de Escenografías Consistentes para Hermatron

let generatedBlob = null; // Guardará el blob de la imagen generada por IA

document.addEventListener('DOMContentLoaded', () => {
    cargarEscenografias();
});

// Cargar la lista de escenarios
async function cargarEscenografias() {
    const grid = document.getElementById('gridEscenarios');
    if (!grid) return;

    try {
        const res = await fetch('/api/escenografias');
        const data = await res.json();
        const lista = data.escenografias || [];

        if (lista.length === 0) {
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
        lista.forEach(esc => {
            const card = document.createElement('div');
            card.className = 'card-escenario';

            const photoUrl = esc.imagen_path || 'https://via.placeholder.com/300x160?text=🏞️+Sin+Imagen';

            card.innerHTML = `
                <div class="card-img-wrap">
                    <img class="card-img" src="${photoUrl}" onerror="this.src='https://via.placeholder.com/300x160?text=🏞️+Escenario'">
                    <div class="card-labels">
                        <span class="badge-tag">🌦️ ${esc.clima.toUpperCase()}</span>
                        <span class="badge-tag">⏰ ${esc.hora_dia.toUpperCase()}</span>
                        <span class="badge-tag">🪨 ${esc.material_suelo.toUpperCase()}</span>
                    </div>
                </div>
                <div class="card-body">
                    <h4 class="card-title">${esc.nombre}</h4>
                    <p class="card-desc">${esc.descripcion}</p>
                    <div class="card-footer">
                        <button type="button" class="btn btn-sm btn-danger" style="font-size:0.75rem; padding: 4px 10px;" onclick="eliminarEscenografia('${esc.nombre}')">🗑️ Eliminar</button>
                    </div>
                </div>
            `;
            grid.appendChild(card);
        });

    } catch (e) {
        console.error("Error al cargar escenografías:", e);
        showToast("Error al cargar la lista de escenarios", "error");
    }
}

// Pre-generar un fondo con Pollinations IA (Gratis)
async function preGenerarFondoIA() {
    const btn = document.getElementById('btnGenFondo');
    const name = document.getElementById('scName').value.trim();
    const desc = document.getElementById('scDesc').value.trim();
    const clima = document.getElementById('scClima').value;
    const hora = document.getElementById('scHora').value;
    const suelo = document.getElementById('scSuelo').value;
    const preview = document.getElementById('previewGenImg');

    if (!desc) {
        showToast("Escribe una descripción en el formulario para guiar a la IA", "warning");
        return;
    }

    btn.innerText = "🎨 Generando fondo...";
    btn.disabled = true;

    try {
        // Optimizar y construir el prompt en inglés para Pollinations
        const promptFull = `3d animation style, Pixar style, detailed background scenery of ${desc}. Clima: ${clima}, time of day: ${hora}, ground material: ${suelo}, consistent visual scenery backdrop, clean environment, beautiful masterwork, 4k resolution`;
        const promptCod = encodeURIComponent(promptFull);
        const seed = Math.floor(Math.random() * 99999);
        const url = `https://image.pollinations.ai/prompt/${promptCod}?width=1024&height=576&nologo=true&seed=${seed}&model=flux`;

        // Descargar la imagen de Pollinations como un Blob
        const response = await fetch(url);
        if (!response.ok) throw new Error("Falla al contactar a la IA");
        const blob = await response.blob();

        generatedBlob = blob; // Guardar el archivo generado en memoria

        // Crear una URL local para previsualizar en el formulario
        const objectURL = URL.createObjectURL(blob);
        preview.src = objectURL;
        preview.style.display = "block";

        showToast("✨ Fondo pre-generado con éxito", "success");

    } catch (e) {
        console.error("Error pre-generando fondo:", e);
        showToast("No se pudo conectar con el motor de IA de Pollinations", "error");
    } finally {
        btn.innerText = "🎨 Pre-generar con IA";
        btn.disabled = false;
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

    const formData = new FormData();
    formData.append('nombre', nombre);
    formData.append('descripcion', descripcion);
    formData.append('clima', clima);
    formData.append('hora_dia', hora_dia);
    formData.append('material_suelo', material_suelo);

    // Prioridad 1: Si subió un archivo físico
    if (inputImagen.files.length > 0) {
        formData.append('imagen', inputImagen.files[0]);
    }
    // Prioridad 2: Si generó una con la IA
    else if (generatedBlob) {
        const file = new File([generatedBlob], `${nombre.replace(/\s/g, '_')}_ia.jpg`, { type: 'image/jpeg' });
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
            form.reset();
            generatedBlob = null;
            document.getElementById('previewGenImg').style.display = 'none';
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

// Toast helper
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    if (!toast) return;

    toast.innerText = message;
    
    // Asignar colores según el tipo
    toast.style.borderColor = 'var(--borde)';
    if (type === 'success') toast.style.borderColor = '#10b981';
    else if (type === 'error') toast.style.borderColor = '#ef4444';
    else if (type === 'warning') toast.style.borderColor = '#f59e0b';

    toast.classList.add('show');
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}
