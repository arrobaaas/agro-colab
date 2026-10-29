/* Agro-Colab - Servicio del Dashboard del Comprador: árboles adoptados (con
   su despacho de cosecha) y planes de abastecimiento contratados. Servicio
   orientado a objetos (DashboardService) con instancia expuesta como
   AgroColab.dashboard. */

(function () {
  const AgroColab = (window.AgroColab = window.AgroColab || {});
  const { api, auth, ui } = AgroColab;

  const FRECUENCIAS = { semanal: "Semanal", quincenal: "Quincenal", mensual: "Mensual" };

  class DashboardService {
    constructor() {
      this.api = api;
      this.auth = auth;
      this.ui = ui;
      this.arboles = [];
      this.pedidos = [];
    }

    /* Despacho registrado para la cosecha de un árbol (el más reciente) */
    despachoDeArbol(arbolId) {
      return this.pedidos.find((p) => p.tipo === "arbol" && String(p.arbol_id) === String(arbolId)) || null;
    }

    plantillaDestino(pedido) {
      const destino = pedido.tipo_destino === "comercial"
        ? `<i class="fa-solid fa-store text-amber-600 w-4"></i> ${pedido.razon_social || "Local comercial"}`
        : `<i class="fa-solid fa-house-chimney text-emerald-600 w-4"></i> Domicilio particular`;
      return `
        <li class="truncate">${destino}</li>
        <li class="truncate"><i class="fa-solid fa-location-dot text-rose-500 w-4"></i> ${pedido.direccion}, ${pedido.comuna}</li>
        <li><i class="fa-solid fa-calendar-days text-stone-400 w-4"></i> Despacho ${(FRECUENCIAS[pedido.frecuencia_entrega] || pedido.frecuencia_entrega || "").toLowerCase()}</li>`;
    }

    plantillaArbol(arbol) {
      const cuposTotales = arbol.cupos_totales || 0;
      const cuposOcupados = arbol.cupos_ocupados || 0;
      const porcentaje = cuposTotales ? Math.min(100, Math.round((cuposOcupados / cuposTotales) * 100)) : 0;
      // La suscripción del usuario siempre está activa; "completo" describe
      // los cupos del árbol, no el estado de su adopción.
      const cuposCompletos = cuposTotales > 0 && cuposOcupados >= cuposTotales;
      const exclusivo = arbol.tipo_suscripcion === "Exclusivo";
      const claseTipo = exclusivo ? "bg-amber-100 text-amber-800" : "bg-sky-100 text-sky-800";
      const despacho = this.despachoDeArbol(arbol.arbol_id);

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

            <div class="mt-4 p-3 rounded-2xl ${despacho ? "bg-emerald-50/60 border border-emerald-100" : "bg-stone-50 border border-dashed border-stone-300"}">
              <p class="text-[10px] uppercase tracking-wider font-bold ${despacho ? "text-emerald-800" : "text-stone-500"} mb-1.5">
                <i class="fa-solid fa-truck-fast mr-1"></i>${despacho ? `Despacho de la cosecha · ${despacho.codigo_seguimiento}` : "Despacho sin configurar"}
              </p>
              ${despacho
                ? `<ul class="space-y-1 text-xs text-stone-600">${this.plantillaDestino(despacho)}</ul>`
                : `<p class="text-xs text-stone-500">Indica dónde quieres recibir la cosecha de tu árbol.</p>`}
            </div>

            <div class="mt-5 pt-4 border-t border-stone-100 flex flex-wrap gap-2">
              <button type="button" class="px-4 py-2 rounded-xl bg-white border border-stone-300 text-stone-700 font-bold text-sm hover:bg-stone-50" onclick="AgroColab.dashboard.editarLogisticaArbol(${arbol.arbol_id})">
                <i class="fa-solid fa-truck-fast"></i> ${despacho ? "Modificar logística" : "Configurar despacho"}
              </button>
              <button type="button" class="px-4 py-2 rounded-xl bg-white border border-red-200 text-red-600 font-bold text-sm hover:bg-red-50 ml-auto" onclick="AgroColab.dashboard.cancelarSuscripcionArbol(${arbol.arbol_id})">
                <i class="fa-solid fa-xmark"></i> Cancelar suscripción
              </button>
            </div>
          </div>
        </article>
      `;
    }

    plantillaPlan(pedido) {
      const comercial = pedido.tipo_destino === "comercial";
      return `
        <article class="bg-white rounded-3xl border border-stone-200 shadow-sm p-5 flex flex-col">
          <div class="flex items-start gap-4">
            <div class="w-14 h-14 rounded-2xl flex items-center justify-center text-xl flex-shrink-0 ${comercial ? "bg-amber-50 text-amber-700" : "bg-emerald-50 text-emerald-700"}">
              <i class="fa-solid ${comercial ? "fa-store" : "fa-basket-shopping"}"></i>
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-start justify-between gap-2">
                <h3 class="font-black text-lg text-stone-900 leading-tight">${pedido.plan_nombre}</h3>
                <span class="text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded-full bg-emerald-600 text-white flex-shrink-0">
                  <i class="fa-solid fa-circle-check mr-1"></i>Activo
                </span>
              </div>
              <p class="text-xs text-stone-500 mt-0.5">Código <strong class="text-stone-700">${pedido.codigo_seguimiento}</strong>${pedido.fecha_registro ? ` · desde el ${pedido.fecha_registro.split(" ")[0]}` : ""}</p>
            </div>
          </div>

          <div class="mt-4 flex items-end justify-between gap-3">
            <div>
              <p class="text-2xl font-black text-emerald-900 leading-none">${this.ui.formatearMonto(pedido.monto_clp)}</p>
              <p class="text-[10px] text-stone-500 mt-1">CLP por entrega</p>
            </div>
            <span class="text-[11px] font-semibold text-emerald-800 bg-emerald-50 border border-emerald-100 px-3 py-1 rounded-full">
              <i class="fa-solid fa-route mr-1"></i>${pedido.estado_logistica || "En preparación"}
            </span>
          </div>

          <ul class="mt-4 p-3 rounded-2xl bg-stone-50 border border-stone-200 space-y-1 text-xs text-stone-600">
            ${this.plantillaDestino(pedido)}
          </ul>

          <div class="mt-5 pt-4 border-t border-stone-100 flex">
            <button type="button" class="px-4 py-2 rounded-xl bg-white border border-stone-300 text-stone-700 font-bold text-sm hover:bg-stone-50" onclick="AgroColab.dashboard.editarLogisticaPedido(${pedido.id})">
              <i class="fa-solid fa-truck-fast"></i> Modificar logística
            </button>
          </div>
        </article>
      `;
    }

    encabezadoSeccion(icono, titulo, cantidad) {
      return `
        <div class="md:col-span-2 flex items-center gap-3 mt-4 first:mt-0">
          <span class="w-9 h-9 rounded-xl bg-emerald-100 text-emerald-800 flex items-center justify-center"><i class="fa-solid ${icono}"></i></span>
          <h3 class="text-xl font-extrabold text-stone-900">${titulo}</h3>
          <span class="text-xs font-bold text-stone-500 bg-white border border-stone-200 px-2.5 py-0.5 rounded-full">${cantidad}</span>
        </div>`;
    }

    pintar() {
      const contenedor = document.getElementById("dashboard-comprador");
      if (!contenedor) return;

      const planes = this.pedidos.filter((p) => p.tipo !== "arbol");

      if (!this.arboles.length && !planes.length) {
        contenedor.innerHTML = `
        <div class="md:col-span-2 text-center py-12 bg-white rounded-3xl border border-stone-200">
          <div class="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <i class="fa-solid fa-tree text-emerald-700 text-2xl"></i>
          </div>
          <h3 class="text-lg font-black text-stone-900">Todavía no tienes árboles ni planes</h3>
          <p class="text-sm text-stone-500 mt-2">Adopta un árbol o contrata una canasta de abastecimiento.</p>
          <button type="button" class="btn-hero btn-hero--primario mt-6" onclick="AgroColab.views.mostrarVista('parcelas')">
            <i class="fa-solid fa-seedling"></i> Ir al catálogo
          </button>
        </div>`;
        return;
      }

      let html = "";
      if (this.arboles.length) {
        html += this.encabezadoSeccion("fa-tree", "Árboles adoptados", this.arboles.length);
        html += this.arboles.map((arbol) => this.plantillaArbol(arbol)).join("");
      }
      if (planes.length) {
        html += this.encabezadoSeccion("fa-basket-shopping", "Planes de abastecimiento", planes.length);
        html += planes.map((pedido) => this.plantillaPlan(pedido)).join("");
      }
      contenedor.innerHTML = html;
    }

    async cargar() {
      const sesion = auth.leerSesion();
      const contenedor = document.getElementById("dashboard-comprador");
      if (!sesion || !contenedor) return;

      contenedor.innerHTML = '<p class="md:col-span-2 text-stone-500 text-sm text-center py-8">Cargando tu panel...</p>';

      try {
        /* Los planes de abastecimiento se guardan como pedidos: antes el panel
           solo consultaba las suscripciones y los planes nunca aparecían. */
        const [datosArboles, pedidos] = await Promise.all([
          api.obtenerMisArboles(sesion.id),
          api.obtenerPedidos()
        ]);
        this.arboles = datosArboles && datosArboles.status === "success" ? (datosArboles.arboles || []) : [];
        this.pedidos = Array.isArray(pedidos) ? pedidos : [];
        this.pintar();
      } catch (error) {
        contenedor.innerHTML = '<p class="md:col-span-2 text-red-500 text-sm text-center py-8">No se pudo cargar tu panel.</p>';
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

    /* Modificar (o configurar por primera vez) el despacho de un árbol. */
    editarLogisticaArbol(arbolId) {
      const arbol = this.arboles.find((a) => String(a.arbol_id) === String(arbolId));
      if (!arbol) return;

      const despacho = this.despachoDeArbol(arbolId);
      if (despacho) {
        AgroColab.parcelas.abrirLogistica(null, despacho);
      } else {
        AgroColab.parcelas.abrirLogistica({
          id: arbol.arbol_id,
          nombre: arbol.nombre,
          precio: arbol.precio_mensual_clp,
          tipo: "arbol"
        });
      }
    }

    editarLogisticaPedido(pedidoId) {
      const pedido = this.pedidos.find((p) => String(p.id) === String(pedidoId));
      if (pedido) AgroColab.parcelas.abrirLogistica(null, pedido);
    }

    init() {}
  }

  const dashboardService = new DashboardService();
  window.AgroColab.dashboard = dashboardService;
})();
