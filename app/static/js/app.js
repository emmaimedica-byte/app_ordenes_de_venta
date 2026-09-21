function actualizarTemporizadores() {
    const elementos = document.querySelectorAll('.badge-tiempo[data-iso]');
    const ahora = new Date();

    elementos.forEach(el => {
        const isoFecha = el.getAttribute('data-iso');
        if (!isoFecha) return;

        const fechaOrden = new Date(isoFecha);
        const diffMs = ahora - fechaOrden;
        const diffHoras = diffMs / (1000 * 60 * 60);

        el.className = 'badge-tiempo text-xs px-2 py-0.5 rounded-full transition-colors duration-300 ';

        if (diffHoras < 4) {
            const mins = Math.max(0, Math.floor(diffMs / (1000 * 60)));
            el.innerText = `⏱️ ${mins} min`;
            el.className += 'bg-green-100 text-green-800 border border-green-300';
        } else if (diffHoras < 24) {
            const hrs = Math.floor(diffHoras);
            el.innerText = `⏳ ${hrs} hrs`;
            el.className += 'bg-amber-100 text-amber-800 border border-amber-400';
        } else {
            const dias = Math.floor(diffHoras / 24);
            el.innerText = `🚨 ${dias} día(s)`;
            el.className += 'bg-red-100 text-red-800 font-bold border border-red-500';
        }
    });
}

setInterval(actualizarTemporizadores, 10000);
document.addEventListener("DOMContentLoaded", actualizarTemporizadores);