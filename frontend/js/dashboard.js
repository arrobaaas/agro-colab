/* Agro-Colab - Servicio del Dashboard del Comprador: estado del árbol adoptado,
   avance de coparticipación y cosecha estimada. Servicio orientado a objetos
   (DashboardService) con instancia expuesta como AgroColab.dashboard. */

(function () {
  const AgroColab = (window.AgroColab = window.AgroColab || {});
  const { api, auth, ui } = AgroColab;

  class DashboardService {
    constructor() {
      this.api = api;
      this.auth = auth;
      this.ui = ui;
      this.arboles = [];
    }

    pintar(arboles) {
      const contenedor = document.getElementById("dashboard-comprador");
      if (!contenedor) return;

      if (!arboles.length) {
        contenedor.innerHTML = `
        <div class="md:col-span-2 text-center py-12 bg-white rounded-3xl border border-stone-200">
          <div class="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <i class="fa-solid fa-tree text-emerald-700 text-2xl"></i>
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
        .map((arbol) => {
          const cuposTotales = arbol.cupos_totales || 0;
          const cuposOcupados = arbol.cupos_ocupados || 0;
          const porcentaje = cuposTotales ? Math.min(100, Math.round((cuposOcupados / cuposTotales) * 100)) : 0;
          // La suscripción del usuario siempre está activa; "completo" describe
          // los cupos del árbol, no el estado de su adopción.
          const cuposCompletos = cuposTotales > 0 && cuposOcupados >= cuposTotales;
          const exclusivo = arbol.tipo_suscripcion === "Exclusivo";
          const claseTipo = exclusivo ? "bg-amber-100 text-amber-800" : "bg-sky-100 text-sky-800";

          return `
          <article class="bg-white rounded-3xl border border-stone-200 shadow-sm overflow-hidden flex flex-col">
            <div class="relative h-36 bg-stone-200">
              <img src="${arbol.imagen || ""}" alt="${arbol.nombre}" class="w-full h-full object-cover" onerror="this.style.display='none'">
              <span class="absolute top-3 left-3 text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded-full bg-emerald-600 text-white shadow">
                <i class="fa-solid fa-circle-check mr-1"></i>Suscripción activa
              </span>
              ${arbol.tipo_suscripcion ? `<span class="absolute top-3 right-3 text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded-full ${claseTipo}">${arbol.tipo_suscripcion}</span>` : ""}
            </div>

            <div class="p-5 flex-1 flex flex-col">
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                  <h3 class="font-black text-lg text-stone-900 truncate">${arbol.nombre}</h3>
                  ${arbol.especie_nombre ? `<p class="text-xs text-stone-500">${arbol.especie_nombre}</p>` : ""}
                </div>
                <div class="text-right flex-shrink-0">
                  <p class="font-black text-emerald-900 leading-tight">${this.ui.formatearMonto(arbol.precio_mensual_clp)}</p>
                  <p class="text-[10px] text-stone-500">CLP / mes</p>
                </div>
              </div>

              <ul class="mt-3 space-y-1 text-xs text-stone-600">
                <li class="truncate"><i class="fa-solid fa-location-dot text-rose-500 w-4"></i> ${arbol.ubicacion || "Ubicación no informada"}</li>
                ${arbol.productor ? `<li class="truncate"><i class="fa-solid fa-user-tie text-stone-400 w-4"></i> Productor: <strong>${arbol.productor}</strong></li>` : ""}
                <li><i class="fa-solid fa-seedling text-emerald-600 w-4"></i> Plan <strong>${arbol.plan || "-"}</strong> · Cosecha estimada <strong>${arbol.estimacion_cosecha || "-"}</strong></li>
                ${arbol.fecha_suscripcion ? `<li><i class="fa-solid fa-calendar-check text-stone-400 w-4"></i> Adoptado el ${arbol.fecha_suscripcion}</li>` : ""}
              </ul>

              <div class="mt-4">
                <div class="flex items-center justify-between text-[11px] text-stone-500 mb-1">
                  <span>Coparticipantes</span>
                  <span class="font-bold ${cuposCompletos ? "text-amber-700" : "text-stone-700"}">
                    ${cuposOcupados}/${cuposTotales}${cuposCompletos ? " · cupos completos" : ""}
                  </span>
                </div>
                <div class="w-full bg-stone-100 h-2 rounded-full overflow-hidden">
                  <div class="${cuposCompletos ? "bg-amber-500" : "bg-emerald-600"} h-2 rounded-full" style="width: ${porcentaje}%"></div>
                </div>
              </div>

              <div class="mt-5 pt-4 border-t border-stone-100 flex flex-wrap gap-2">
                <button type="button" class="px-4 py-2 rounded-xl bg-white border border-stone-300 text-stone-700 font-bold text-sm hover:bg-stone-50" onclick="AgroColab.dashboard.editarLogisticaArbol(${arbol.arbol_id})">
                  <i class="fa-solid fa-truck-fast"></i> Modificar logística
                </button>
                <button type="button" class="px-4 py-2 rounded-xl bg-white border border-red-200 text-red-600 font-bold text-sm hover:bg-red-50 ml-auto" onclick="AgroColab.dashboard.cancelarSuscripcionArbol(${arbol.arbol_id})">
                  <i class="fa-solid fa-xmark"></i> Cancelar suscripción
                </button>
              </div>
            </div>
          </article>
        `;
        })
        .join("");
    }

    async cargar() {
      const sesion = auth.leerSesion();
      const contenedor = document.getElementById("dashboard-comprador");
      if (!sesion || !contenedor) return;

      contenedor.innerHTML = '<p class="md:col-span-2 text-stone-500 text-sm text-center py-8">Cargando tu panel de adopción...</p>';

      try {
        const data = await api.obtenerMisArboles(sesion.id);
        this.arboles = data && data.status === "success" ? (data.arboles || []) : [];
        this.pintar(this.arboles);
      } catch (error) {
        contenedor.innerHTML = '<p class="md:col-span-2 text-red-500 text-sm text-center py-8">No se pudo cargar tu panel de adopción.</p>';
      }
    }

    async cancelarSuscripcionArbol(arbolId) {
      const arbol = this.arboles.find((a) => String(a.arbol_id) === String(arbolId));
      const nombre = arbol ? arbol.nombre : "este árbol";
      if (!window.confirm(`¿Cancelar tu suscripción a ${nombre}? Se liberará tu cupo.`)) return null;

      try {
        const data = await api.cancelarSuscripcion(auth.leerSesion(), arbolId);
        if (data.status === "success") {
          await this.cargar();
        } else {
          window.alert(data.mensaje || "No se pudo cancelar la suscripción.");
        }
        return data;
      } catch (error) {
        window.alert("No se pudo cancelar la suscripción. Intenta nuevamente.");
        return null;
      }
    }

    /* Modificar la logística del árbol adoptado desde el panel. */
    editarLogisticaArbol(arbolId) {
      const arbol = this.arboles.find((a) => String(a.arbol_id) === String(arbolId));
      if (!arbol) return;

      AgroColab.parcelas.abrirLogistica();

      const sesion = auth.leerSesion();
      const radioPart = document.querySelector('input[name="modal_tipo_dest"][value="particular"]');
      const radioCom = document.querySelector('input[name="modal_tipo_dest"][value="comercial"]');

      // El panel no guarda el destino previo: se parte siempre desde "particular"
      if (radioPart) radioPart.checked = true;
      if (radioCom) radioCom.checked = false;
      document.getElementById("modal-card-part").className = "destino-card destino-card--activo-particular";
      document.getElementById("modal-card-com").className = "destino-card destino-card--inactivo";
      document.getElementById("modal-bloque-comercial").classList.add("hidden");

      document.getElementById("modal-dest-nombre").value = (sesion && sesion.nombre) || "";
      document.getElementById("modal-dest-tel").value = (sesion && sesion.telefono) || "";
      document.getElementById("modal-dest-email").value = (sesion && sesion.email) || "";
      document.getElementById("modal-dest-direccion").value = (sesion && sesion.direccion) || arbol.ubicacion || "";
      document.getElementById("modal-dest-comuna").value = "";
      document.getElementById("modal-dest-frecuencia").value = "quincenal";
    }

    init() {}
  }

  const dashboardService = new DashboardService();
  window.AgroColab.dashboard = dashboardService;
})();
