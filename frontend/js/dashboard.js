/* Agro-Colab - Servicio del Dashboard del Comprador: árboles adoptados (con
   su despacho de cosecha) y planes de abastecimiento contratados. Servicio
   orientado a objetos (DashboardService) con instancia expuesta como
   AgroColab.dashboard. */

(function () {
  const AgroColab = (window.AgroColab = window.AgroColab || {});
  // Escapa datos antes de insertarlos como HTML (ver ui.escapar)
  const e = (valor) => window.AgroColab.ui.escapar(valor);
  const { api, auth, ui } = AgroColab;

  const FRECUENCIAS = { semanal: "Semanal", quincenal: "Quincenal", mensual: "Mensual" };

  class DashboardService {
    constructor() {
      this.api = api;
      this.auth = auth;
      this.ui = ui;
      this.arboles = [];
      this.pedidos = [];
      this.pagos = [];
    }

    /* Despacho registrado para la cosecha de un árbol (el más reciente) */
    despachoDeArbol(arbolId) {
      return this.pedidos.find((p) => p.tipo === "arbol" && String(p.arbol_id) === String(arbolId)) || null;
    }

    /* Texto del destino de un despacho, para la grilla de datos */
    datosDestino(pedido) {
      const destino = pedido.tipo_destino === "comercial"
        ? `Comercial · ${e(pedido.razon_social || "Local")}`
        : "Domicilio particular";
      return `
        <div><dt>Destino</dt><dd>${destino}</dd></div>
        <div><dt>Dirección</dt><dd>${e(pedido.direccion)}, ${e(pedido.comuna)}</dd></div>
        <div><dt>Frecuencia</dt><dd>${e(FRECUENCIAS[pedido.frecuencia_entrega] || pedido.frecuencia_entrega || "")}</dd></div>
        ${pedido.rut ? `<div><dt>RUT</dt><dd>${e(pedido.rut)}</dd></div>` : ""}`;
    }

    plantillaArbol(arbol) {
      const cuposTotales = arbol.cupos_totales || 0;
      const cuposOcupados = arbol.cupos_ocupados || 0;
      const porcentaje = cuposTotales ? Math.min(100, Math.round((cuposOcupados / cuposTotales) * 100)) : 0;
      // La suscripción del usuario siempre está activa; "completo" describe
      // los cupos del árbol, no el estado de su adopción.
      const cuposCompletos = cuposTotales > 0 && cuposOcupados >= cuposTotales;
      const despacho = this.despachoDeArbol(arbol.arbol_id);

      return `
        <article class="tc-item" data-reveal>
          <div class="tc-item__foto">
            <img src="${e(arbol.imagen || "")}" alt="${e(arbol.nombre)}" data-si-falla="ocultar">
          </div>
          <div>
            <div class="tc-item__cabecera">
              <div>
                <p class="tc-etiqueta tc-etiqueta--verde">${e(arbol.especie_nombre || "Árbol frutal")} · Plan ${e(arbol.plan || "-")}</p>
                <h3 class="tc-item__nombre">${e(arbol.nombre)}</h3>
              </div>
              <span class="tc-estado">Suscripción activa</span>
            </div>

            <dl class="tc-datos-item">
              <div><dt>Aporte mensual</dt><dd>${this.ui.formatearMonto(arbol.precio_mensual_clp)} CLP</dd></div>
              <div><dt>Cosecha estimada</dt><dd>${e(arbol.estimacion_cosecha || "-")}</dd></div>
              <div><dt>Ubicación</dt><dd>${e(arbol.ubicacion || "-")}</dd></div>
              ${arbol.productor ? `<div><dt>Productor</dt><dd>${e(arbol.productor)}</dd></div>` : ""}
              <div><dt>Tipo</dt><dd>${e(arbol.tipo_suscripcion || "-")}</dd></div>
              ${arbol.fecha_suscripcion ? `<div><dt>Adoptado el</dt><dd>${e(arbol.fecha_suscripcion)}</dd></div>` : ""}
            </dl>

            <div class="tc-barra ${cuposCompletos ? "tc-barra--llena" : ""}"><div style="width:${porcentaje}%"></div></div>
            <p class="tc-barra__texto"><span>Coparticipantes</span><span>${cuposOcupados}/${cuposTotales}${cuposCompletos ? " · cupos completos" : ""}</span></p>

            <div class="tc-despacho ${despacho ? "" : "tc-despacho--vacio"}">
              <p class="tc-etiqueta ${despacho ? "tc-etiqueta--verde" : "tc-etiqueta--gris"}">
                ${despacho ? `Despacho de la cosecha · ${e(despacho.codigo_seguimiento)}` : "Despacho sin configurar"}
              </p>
              ${despacho
                ? `<dl class="tc-datos-item" style="margin-top:1rem">${this.datosDestino(despacho)}</dl>`
                : `<p class="tc-cuerpo-sm" style="margin-top:.5rem">Indica dónde quieres recibir la cosecha de tu árbol.</p>`}
            </div>

            <div class="tc-item__acciones">
              <button type="button" class="tc-enlace" data-accion="dashboard.editarLogisticaArbol" data-args='[${Number(arbol.arbol_id)}]'>
                ${despacho ? "Modificar logística" : "Configurar despacho"} <i class="fa-solid fa-arrow-right"></i>
              </button>
              <button type="button" class="tc-enlace tc-enlace--peligro" data-accion="dashboard.cancelarSuscripcionArbol" data-args='[${Number(arbol.arbol_id)}]'>
                Cancelar suscripción
              </button>
            </div>
          </div>
        </article>
      `;
    }

    plantillaPlan(pedido) {
      const comercial = pedido.tipo_destino === "comercial";
      return `
        <article class="tc-item" data-reveal>
          <div class="tc-item__foto tc-item__icono">
            <i class="fa-solid ${comercial ? "fa-store" : "fa-basket-shopping"}"></i>
            <span>${e(pedido.codigo_seguimiento)}</span>
          </div>
          <div>
            <div class="tc-item__cabecera">
              <div>
                <p class="tc-etiqueta">Plan de abastecimiento${pedido.fecha_registro ? ` · Desde el ${e(pedido.fecha_registro.split(" ")[0])}` : ""}</p>
                <h3 class="tc-item__nombre">${e(pedido.plan_nombre)}</h3>
              </div>
              <span class="tc-estado">Activo</span>
            </div>

            <dl class="tc-datos-item">
              <div><dt>Monto por entrega</dt><dd>${this.ui.formatearMonto(pedido.monto_clp)} CLP</dd></div>
              <div><dt>Estado</dt><dd>${e(pedido.estado_logistica || "En preparación")}</dd></div>
              ${this.datosDestino(pedido)}
            </dl>

            <div class="tc-item__acciones">
              <button type="button" class="tc-enlace" data-accion="dashboard.editarLogisticaPedido" data-args='[${Number(pedido.id)}]'>
                Modificar logística <i class="fa-solid fa-arrow-right"></i>
              </button>
              <button type="button" class="tc-enlace tc-enlace--peligro" data-accion="dashboard.cancelarPlan" data-args='[${Number(pedido.id)}]'>
                Cancelar plan
              </button>
            </div>
          </div>
        </article>
      `;
    }

    /* Comprobantes de la pasarela simulada, aprobados y rechazados */
    plantillaPagos() {
      if (!this.pagos.length) return "";
      return `
        ${this.encabezadoSeccion("Historial de pagos", this.pagos.length)}
        <div class="tc-pagos" data-reveal>
          ${this.pagos
            .map((pago) => {
              const aprobado = pago.estado === "aprobado";
              return `
              <div class="tc-pago">
                <p class="tc-pago__concepto">${e(pago.concepto)}</p>
                <p class="tc-pago__monto">${this.ui.formatearMonto(pago.monto_clp)} CLP</p>
                <p class="tc-pago__meta">
                  ${e(pago.fecha || "")} · ${e(pago.marca)} •••• ${e(pago.ultimos4)} ·
                  ${aprobado ? `Autorización ${e(pago.codigo_autorizacion)}` : e(pago.motivo_rechazo || "Rechazado")} · ${e(pago.transaccion)}
                </p>
                <span class="tc-pago__estado ${aprobado ? "" : "tc-pago__estado--rechazado"}">${aprobado ? "Aprobado" : "Rechazado"}</span>
              </div>`;
            })
            .join("")}
        </div>`;
    }

    encabezadoSeccion(titulo, cantidad) {
      return `
        <div class="tc-panel-seccion" data-reveal="left">
          <h2 class="tc-titulo-sm">${e(titulo)}</h2>
          <span class="tc-contador">${String(cantidad).padStart(2, "0")}</span>
        </div>`;
    }

    pintar() {
      const contenedor = document.getElementById("dashboard-comprador");
      if (!contenedor) return;

      const planes = this.pedidos.filter((p) => p.tipo !== "arbol");

      if (!this.arboles.length && !planes.length) {
        contenedor.innerHTML = `
        <div class="tc-vacio" data-reveal>
          <p class="tc-etiqueta tc-etiqueta--gris">Aún vacío</p>
          <h2 class="tc-titulo-sm" style="margin-top:1rem">Todavía no tienes árboles ni planes.</h2>
          <p class="tc-cuerpo-sm" style="margin:1rem auto 0;max-width:26rem">Adopta un árbol o contrata una canasta de abastecimiento para verlos aquí.</p>
          <div style="margin-top:2.5rem">
            <button type="button" class="tc-boton" data-accion="views.mostrarVista" data-args='["parcelas"]'>Ir al catálogo</button>
          </div>
        </div>`;
      } else {
        let html = "";
        if (this.arboles.length) {
          html += this.encabezadoSeccion("Árboles adoptados", this.arboles.length);
          html += this.arboles.map((arbol) => this.plantillaArbol(arbol)).join("");
        }
        if (planes.length) {
          html += this.encabezadoSeccion("Planes de abastecimiento", planes.length);
          html += planes.map((pedido) => this.plantillaPlan(pedido)).join("");
        }
        contenedor.innerHTML = html + this.plantillaPagos();
      }

      if (AgroColab.efectos) AgroColab.efectos.observar(contenedor);
    }

    async cargar() {
      const sesion = auth.leerSesion();
      const contenedor = document.getElementById("dashboard-comprador");
      if (!sesion || !contenedor) return;

      const saludo = document.getElementById("panel-saludo");
      if (saludo) saludo.textContent = (sesion.nombre || "").split(" ")[0] || "bienvenido";

      contenedor.innerHTML = '<p class="tc-cuerpo-sm">Cargando tu panel...</p>';

      try {
        /* Los planes de abastecimiento se guardan como pedidos: antes el panel
           solo consultaba las suscripciones y los planes nunca aparecían. */
        const [datosArboles, pedidos, datosPagos] = await Promise.all([
          api.obtenerMisArboles(sesion.id),
          api.obtenerPedidos(),
          api.obtenerPagos().catch(() => null)
        ]);
        this.pagos = datosPagos && datosPagos.status === "success" ? (datosPagos.pagos || []) : [];
        this.arboles = datosArboles && datosArboles.status === "success" ? (datosArboles.arboles || []) : [];
        this.pedidos = Array.isArray(pedidos) ? pedidos : [];
        this.pintar();
      } catch (error) {
        contenedor.innerHTML = '<p class="tc-cuerpo-sm">No se pudo cargar tu panel. Intenta nuevamente.</p>';
      }
    }

    async cancelarSuscripcionArbol(arbolId) {
      const arbol = this.arboles.find((a) => String(a.arbol_id) === String(arbolId));
      const nombre = arbol ? arbol.nombre : "este árbol";
      if (!(await AgroColab.dialogo.confirmar(`Tu cupo en ${nombre} quedará libre para otro comprador.`, { titulo: "¿Cancelar tu adopción?", aceptar: "Cancelar adopción", cancelar: "Mantener", peligro: true }))) return null;

      try {
        const data = await api.cancelarSuscripcion(auth.leerSesion(), arbolId);
        if (data.status === "success") {
          await this.cargar();
        } else {
          AgroColab.dialogo.avisar(data.mensaje || "No se pudo cancelar la suscripción.", { tipo: "error" });
        }
        return data;
      } catch (error) {
        AgroColab.dialogo.avisar("No se pudo cancelar la suscripción. Intenta nuevamente.", { tipo: "error" });
        return null;
      }
    }

    async cancelarPlan(pedidoId) {
      const pedido = this.pedidos.find((p) => String(p.id) === String(pedidoId));
      if (!pedido) return;
      if (!(await AgroColab.dialogo.confirmar(`Dejarás de recibir los despachos de ${pedido.plan_nombre} (${pedido.codigo_seguimiento}).`, { titulo: "¿Cancelar este plan?", aceptar: "Cancelar plan", cancelar: "Mantener", peligro: true }))) return;

      try {
        const data = await api.cancelarPlan(pedidoId);
        if (data.status === "success") {
          await this.cargar();
        } else {
          AgroColab.dialogo.avisar(data.mensaje || "No se pudo cancelar el plan.", { tipo: "error" });
        }
      } catch (error) {
        AgroColab.dialogo.avisar("No se pudo cancelar el plan. Intenta nuevamente.", { tipo: "error" });
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
