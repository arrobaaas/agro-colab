/* Agro-Colab - Dashboard del Comprador: estado del árbol adoptado,
   avance de coparticipación y cosecha estimada. */

(function () {
  const AgroColab = (window.AgroColab = window.AgroColab || {});
  const { api, auth, ui } = AgroColab;

  let arboles = [];

  function pintar(arboles) {
    const contenedor = document.getElementById("dashboard-comprador");
    if (!contenedor) return;

    if (!arboles.length) {
      contenedor.innerHTML = `
        <div class="text-center py-12 bg-white rounded-3xl border border-stone-200">
          <div class="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <i class="fa-solid fa-tree-canopy text-emerald-700 text-2xl"></i>
          </div>
          <h3 class="text-lg font-black text-stone-900">Todavía no has adoptado ningún árbol</h3>
          <p class="text-sm text-stone-500 mt-2">Explora el catálogo y adopta el árbol que financiarás.</p>
          <button type="button" class="btn-submit mt-6" onclick="AgroColab.views.mostrarVista('parcelas')">
            <i class="fa-solid fa-seedling"></i> Ver árboles disponibles
          </button>
        </div>`;
      return;
    }

    contenedor.innerHTML = arboles
      .map(function (arbol) {
        const cuposTotales = arbol.cupos_totales || 0;
        const cuposOcupados = arbol.cupos_ocupados || 0;
        const activa = cuposOcupados < cuposTotales;
        const porcentaje = cuposTotales ? Math.round((cuposOcupados / cuposTotales) * 100) : 0;
        const claseBadge = activa ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800";
        const claseEstado = activa ? "text-emerald-700" : "text-amber-700";
        const etiqueta = activa ? "Suscripción activa" : "Suscripción completa";
        const estado = activa ? "Activo" : "Completo";

        return `
          <div class="bg-white rounded-3xl border border-stone-200 p-5">
            <div class="flex items-center gap-4">
              <div class="w-20 h-20 rounded-2xl overflow-hidden bg-stone-200 flex-shrink-0">
                <img src="${arbol.imagen}" alt="${arbol.nombre}" class="w-full h-full object-cover">
              </div>
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                  <h3 class="font-black text-lg text-stone-900 truncate">${arbol.nombre}</h3>
                  <span class="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${claseBadge}">${etiqueta}</span>
                </div>
                <p class="text-xs text-stone-500 mt-1">
                  <i class="fa-solid fa-location-dot text-rose-500 mr-1"></i>${arbol.ubicacion}
                </p>
                <p class="text-xs text-stone-500">
                  Plan <strong>${arbol.plan}</strong> · Cosecha <strong>${arbol.estimacion_cosecha}</strong>
                </p>
              </div>
              <div class="text-right flex-shrink-0">
                <p class="font-black text-emerald-900">${ui.formatearMonto(arbol.precio_mensual_clp)} <span class="text-[10px] font-normal text-stone-500">CLP / mes</span></p>
                <p class="text-[10px] text-stone-500 mt-1">${cuposOcupados}/${cuposTotales} coparticipantes</p>
              </div>
            </div>

            <div class="mt-4">
              <div class="flex items-center justify-between text-[11px] text-stone-500 mb-1">
                <span>Avance de coparticipación</span>
                <span class="font-bold text-stone-700">${porcentaje}%</span>
              </div>
              <div class="w-full bg-stone-100 h-2 rounded-full overflow-hidden">
                <div class="bg-emerald-600 h-2 rounded-full" style="width: ${porcentaje}%"></div>
              </div>
            </div>

            <p class="text-[11px] text-stone-500 mt-3">
              Estado de la adopción: <strong class="${claseEstado}">${estado}</strong> · Cosecha estimada: <strong>${arbol.estimacion_cosecha}</strong>
            </p>

            <div class="mt-4 flex flex-wrap gap-2">
              <button type="button" class="btn-submit" onclick="AgroColab.dashboard.cancelarSuscripcionArbol(${arbol.arbol_id})">
                <i class="fa-solid fa-user-x"></i> Cancelar suscripción
              </button>
              <button type="button" class="px-4 py-2 rounded-xl bg-white border border-stone-300 text-stone-700 font-bold text-sm" onclick="AgroColab.views.mostrarVista('parcelas')">
                <i class="fa-solid fa-leaf"></i> Ver catálogo
              </button>
            </div>
          </div>
        `;
      })
      .join("");
  }

  async function cargar() {
    const sesion = auth.leerSesion();
    const contenedor = document.getElementById("dashboard-comprador");
    if (!sesion || !contenedor) return;

    contenedor.innerHTML = '<p class="text-stone-500 text-sm text-center py-8">Cargando tu panel de adopción...</p>';

    try {
      const data = await api.obtenerMisArboles(sesion.id);
      arboles = data && data.status === "success" ? (data.arboles || []) : [];
      pintar(arboles);
    } catch (error) {
      contenedor.innerHTML = '<p class="text-red-500 text-sm text-center py-8">No se pudo cargar tu panel de adopción.</p>';
    }
  }

  async function cancelarSuscripcionArbol(arbolId) {
    const data = await api.cancelarSuscripcion(auth.leerSesion(), arbolId);
    if (data.status === "success") {
      await cargar();
      return data;
    }
    return data;
  }

  function init() {}

  AgroColab.dashboard = { init, cargar, pintar, cancelarSuscripcionArbol };
})();
