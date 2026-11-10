/* Agro-Colab - Servicio de parcelas: adopción de árboles, planes de
   abastecimiento, canasta, logística y pago. Servicio orientado a objetos
   (ParcelasService) con instancia expuesta como AgroColab.parcelas. */

(function () {
  const AgroColab = (window.AgroColab = window.AgroColab || {});
  // Escapa datos antes de insertarlos como HTML (ver ui.escapar)
  const e = (valor) => window.AgroColab.ui.escapar(valor);
  const { api, ui, auth, config } = AgroColab;

  const PLAN_ABASTECIMIENTO_INICIAL = { nombre: "Canasta Huerto Esencial", precio: 19900 };

  class ParcelasService {
    constructor() {
      this.config = config;
      this.api = api;
      this.ui = ui;
      this.auth = auth;
      this.planActual = { ...PLAN_ABASTECIMIENTO_INICIAL };
      this.destinoSeleccionado = "particular";
      this.planAdopcionSeleccionado = "todos";
      this.itemsLogistica = [];
      this.pedidoEditando = null;
      this.carrito = [];
      this.arbolParaAdoptar = null;
    }

    /* ---------- Plan y destino de despacho ---------- */

    mostrarPlanActual() {
      document.getElementById("log-plan-nombre").textContent = this.planActual.nombre;
      document.getElementById("log-plan-precio").textContent = `${this.ui.formatearMonto(this.planActual.precio)} CLP`;
    }

    seleccionarPlan(boton) {
      /* El plan B2B exige razón social y RUT, y la cuenta demo no admite datos
         comerciales: se avisa antes de sumarlo, no después de pagarlo */
      const sesion = auth.leerSesion();
      const esDemo = sesion && (this.config.cuentasDemo || []).includes(sesion.email);
      if (esDemo && boton.dataset.planDestino === "comercial") {
        AgroColab.dialogo.avisar(
          "El plan comercial pide razón social y RUT, y esta cuenta de demostración la comparten todos los visitantes. Para probarlo, crea tu propia cuenta de comprador.",
          { titulo: "No disponible en la cuenta demo" }
        );
        return;
      }

      this.planActual = {
        nombre: boton.dataset.planNombre,
        precio: Number(boton.dataset.planPrecio)
      };

      document.getElementById("dest-frecuencia").value = boton.dataset.planFrecuencia;
      this.cambiarDestino(boton.dataset.planDestino);
      this.mostrarPlanActual();
      auth.guardarPlan(this.planActual);

      // Agregar al carrito como pendiente de pago (flujo canasta -> Pagar -> Logistica)
      const item = {
        id: this.planActual.nombre,
        nombre: this.planActual.nombre,
        descripcion: `Plan de abastecimiento - ${boton.dataset.planFrecuencia}`,
        precio: this.planActual.precio,
        estado: "pendiente",
        tipo: "plan",
        destino: boton.dataset.planDestino,
        frecuencia: boton.dataset.planFrecuencia
      };
      this.agregarAlCarrito(item);

      this.abrirCanasta();
    }

    cambiarDestino(tipo) {
      this.destinoSeleccionado = tipo;

      const cardPart = document.getElementById("card-part");
      const cardCom = document.getElementById("card-com");
      const bloqueCom = document.getElementById("bloque-comercial");

      if (tipo === "particular") {
        document.getElementById("radio-part").checked = true;
        cardPart.className = "destino-card destino-card--activo-particular";
        cardCom.className = "destino-card destino-card--inactivo";
        bloqueCom.classList.add("hidden");
      } else {
        document.getElementById("radio-com").checked = true;
        cardCom.className = "destino-card destino-card--activo-comercial";
        cardPart.className = "destino-card destino-card--inactivo";
        bloqueCom.classList.remove("hidden");
      }
    }

    /* ---------- Selector de línea: Adopción vs Abastecimiento ---------- */

    establecerLinea(linea, scrollTo) {
      if (linea !== "adopcion" && linea !== "abastecimiento") return;

      const esAdopcion = linea === "adopcion";

      document.getElementById("seccion-adopcion").classList.toggle("hidden", !esAdopcion);
      document.getElementById("seccion-parcelas").classList.toggle("hidden", !esAdopcion);
      document.getElementById("seccion-abastecimiento").classList.toggle("hidden", esAdopcion);
      document.getElementById("seccion-logistica").classList.toggle("hidden", esAdopcion);

      const destino = scrollTo || (esAdopcion ? "seccion-adopcion" : "seccion-abastecimiento");
      this.irASeccion(destino);
    }

    /* Lleva al título de la sección y no a su borde: las secciones tienen
       6-8,5 rem de relleno arriba y quedaba una franja vacía. Al bajar, el
       header se esconde, así que basta un margen chico; al subir reaparece y
       se deja su alto libre. */
    irASeccion(id) {
      const seccion = document.getElementById(id);
      if (!seccion) return;
      const titulo = seccion.querySelector(".tc-encabezado") || seccion;
      const destino = titulo.getBoundingClientRect().top + window.scrollY;
      const header = document.querySelector("#vista-parcelas header");
      const margen = destino < window.scrollY && header ? header.offsetHeight + 24 : 24;
      window.scrollTo({ top: Math.max(destino - margen, 0), behavior: "smooth" });
    }

    /* ---------- Envío del pedido logístico ---------- */

    async enviarLogistica(evento) {
      evento.preventDefault();

      const alerta = document.getElementById("alerta-logistica");
      const formulario = document.getElementById("form-logistica-principal");
      const esComercial = this.destinoSeleccionado === "comercial";
      const sesion = auth.leerSesion();

      const bodyData = {
        plan_nombre: this.planActual.nombre,
        tipo_destino: this.destinoSeleccionado,
        razon_social: esComercial ? document.getElementById("com-razon").value.trim() : null,
        rut: esComercial ? document.getElementById("com-rut").value.trim() : null,
        direccion: document.getElementById("dest-direccion").value.trim(),
        comuna: document.getElementById("dest-comuna").value.trim(),
        codigo_postal: document.getElementById("dest-postal").value.trim(),
        telefono_codigo: document.getElementById("dest-codigo-pais").value,
        telefono: document.getElementById("dest-celular").value.trim(),
        frecuencia_entrega: document.getElementById("dest-frecuencia").value
      };

      if (esComercial && (!bodyData.razon_social || !bodyData.rut)) {
        this.ui.mostrarAlerta(alerta, "errorGrande", "Completa la razón social y el RUT para el despacho comercial.");
        return;
      }
      if (esComercial && !this.rutValido(bodyData.rut)) {
        this.ui.mostrarAlerta(alerta, "errorGrande", "El RUT de la empresa no es válido. Revisa el dígito verificador (ej: 76.123.456-0).");
        return;
      }

      this.ui.mostrarAlerta(alerta, "infoGrande", "Registrando tu pedido...");

      try {
        const data = await this.api.crearPedido(bodyData);

        if (data.status === "success") {
          alerta.className = "alerta alerta--exito-lg";
          alerta.innerHTML = `
            <div class="flex items-center gap-2 mb-1">
              <i class="fa-solid fa-circle-check text-emerald-600 text-base"></i>
              <span class="text-sm font-bold">${e(data.mensaje)}</span>
            </div>
            <p class="text-stone-600">Destino: <strong>${e(bodyData.direccion)}, ${e(bodyData.comuna)}</strong> (${e(bodyData.tipo_destino.toUpperCase())}) | Frecuencia: <strong>${e(bodyData.frecuencia_entrega)}</strong>.</p>
          `;
          formulario.reset();
          this.cambiarDestino(this.destinoSeleccionado);
        } else {
          this.ui.mostrarAlerta(alerta, "errorGrande", data.mensaje || "No se pudo registrar la solicitud logística.");
        }
      } catch (error) {
        this.ui.mostrarAlerta(
          alerta,
          "errorGrande",
          `Error: backend inaccesible en ${this.config.API_URL}. Revisa que Uvicorn esté activo.`
        );
      }
    }

    /* ---------- Catálogo de parcelas ---------- */

    async cargarArboles() {
      const container = document.getElementById("tree-container");

      try {
        const arboles = await this.api.obtenerArboles();
        container.innerHTML = "";

        if (!arboles.length) {
          container.innerHTML = `<p class="md:col-span-3 text-center text-stone-500 text-sm py-10">No hay árboles disponibles por ahora.</p>`;
          return;
        }

        const visibles =
          this.planAdopcionSeleccionado === "todos"
            ? arboles
            : arboles.filter((arbol) => arbol.plan === this.planAdopcionSeleccionado);

        if (!visibles.length) {
          container.innerHTML = `<p class="md:col-span-3 text-center text-stone-500 text-sm py-10">No hay árboles disponibles para el Plan ${e(this.planAdopcionSeleccionado)}.</p>`;
          return;
        }

        visibles.forEach((arbol, indice) => {
          container.insertAdjacentHTML("beforeend", this.plantillaArbol(arbol, indice));
        });
        if (AgroColab.efectos) AgroColab.efectos.observar(container);
      } catch (error) {
        container.innerHTML = `<div class="col-span-3 p-4 bg-red-50 text-red-700 text-xs rounded-xl">Error al conectar con la API (${this.config.API_URL}).</div>`;
      }
    }

    plantillaArbol(arbol, indice = 0) {
      const cuposTotales = arbol.cupos_totales || 0;
      const cuposLibres = Math.max(0, cuposTotales - (arbol.cupos_ocupados || 0));
      const porcentaje = cuposTotales ? Math.round(((cuposTotales - cuposLibres) / cuposTotales) * 100) : 100;
      const disponible = cuposLibres > 0;
      const exclusivo = arbol.tipo_suscripcion === "Exclusivo";
      const textoCupos = disponible
        ? `${cuposLibres} cupo${cuposLibres === 1 ? "" : "s"} libre${cuposLibres === 1 ? "" : "s"} de ${cuposTotales}`
        : "Sin cupos disponibles";

      /* Se devuelve la tarjeta completa, con su <article> exterior. Antes se
         devolvía solo el innerHTML: se perdía el envoltorio y la foto y los
         datos quedaban como celdas sueltas de la grilla. */
      return `
        <article class="tc-arbol" data-reveal="flip" style="--reveal-delay:${(indice % 3) * 80}ms">
          <div class="tc-arbol__foto">
            <img src="${e(arbol.imagen || "")}" alt="${e(arbol.nombre)}" loading="lazy" data-si-falla="ocultar">
            ${arbol.es_demo ? `<span class="tc-arbol__insignia">Demostración</span>` : ""}
          </div>
          <div class="tc-arbol__cuerpo">
            <p class="tc-etiqueta tc-etiqueta--verde tc-arbol__categoria" title="${e(arbol.especie_nombre || "Árbol frutal")} · Plan ${e(arbol.plan)}${exclusivo ? " · Exclusivo" : ""}">
              ${e(arbol.especie_nombre || "Árbol frutal")} · Plan ${e(arbol.plan)}
            </p>
            <h3 class="tc-arbol__nombre">${e(arbol.nombre)}</h3>
            <ul class="tc-meta">
              <li>${e(arbol.ubicacion)}</li>
              <li>Cosecha estimada <strong>${e(arbol.estimacion_cosecha)}</strong></li>
              ${arbol.productor ? `<li>Productor <strong>${e(arbol.productor)}</strong></li>` : ""}
            </ul>

            <div class="tc-barra ${disponible ? "" : "tc-barra--llena"}"><div style="width:${porcentaje}%"></div></div>
            <p class="tc-barra__texto"><span>${e(textoCupos)}</span></p>

            <div class="tc-arbol__pie">
              <p class="tc-precio">${this.ui.formatearMonto(arbol.precio_mensual_clp)}<small>CLP / mes</small></p>
              <button type="button" class="tc-boton tc-arbol__adoptar ${disponible ? "" : "tc-boton--contorno"}" data-suscribir-id="${Number(arbol.id)}" ${disponible ? "" : "disabled"}>
                ${disponible ? "Adoptar" : "Completo"}
              </button>
            </div>
          </div>
        </article>
      `;
    }

    /* Dentro de esta vista siempre hay sesión, así que no se pide el nombre.
       El clic en el botón del árbol solo suma el cupo a la canasta como pendiente
       de pago. La suscripción real se ejecuta cuando el comprador presiona
       "Pagar" desde la canasta. */
    async agregarAlCarritoArbol(treeId) {
      const sesion = auth.leerSesion();
      if (!sesion) return;

      try {
        const datos = await api.obtenerArboles();
        const arbol = (datos || []).find(function (a) { return a.id === treeId; });
        if (!arbol) { AgroColab.dialogo.avisar("Este árbol ya no está disponible en el catálogo.", { tipo: "error", titulo: "Árbol no encontrado" }); return; }

        // Un mismo usuario no puede adoptar más de una vez el mismo árbol.
        const existente = this.carrito.find(function (c) {
          return c && c.tipo === "arbol" && c.id === arbol.id;
        });
        const enCarrito = existente && (existente.estado === "pendiente" || existente.estado === "comprado");

        let yaSuscripto = Boolean(enCarrito);
        if (!yaSuscripto) {
          try {
            const data = await api.obtenerMisArboles(sesion.id);
            const lista = (data && data.arboles) || [];
            yaSuscripto = lista.some(function (a) { return a && a.arbol_id === arbol.id; });
          } catch (error) { /* el backend validará al momento del pago */ }
        }
        if (yaSuscripto) {
          AgroColab.dialogo.avisar(`Ya tienes un cupo en ${arbol.nombre}. Cada persona puede adoptar un mismo árbol una sola vez; puedes verlo en tu panel o elegir otro árbol del catálogo.`, { titulo: "Ya adoptaste este árbol" });
          return;
        }

        this.abrirModalConfirmacionArbol(arbol);
      } catch (error) {
        AgroColab.dialogo.avisar("No hay conexión con el servidor. Intenta nuevamente en unos segundos.", { tipo: "error" });
      }
    }

    /* Agregar un árbol ya validado a la canasta (estado pendiente de pago). */
    agregarItemAlArbol(arbol) {
      const item = {
        id: arbol.id,
        nombre: arbol.nombre,
        descripcion: `Árbol adoptado - Plan ${arbol.plan}`,
        precio: arbol.precio_mensual_clp,
        imagen: arbol.imagen,
        estado: "pendiente",
        tipo: "arbol"
      };
      this.agregarAlCarrito(item);
      this.cargarArboles();
    }

    /* Respuesta del modal de confirmación de adopción ("Sí" -> agregar / "No" -> cerrar). */
    confirmarAdopcion() {
      const arbol = this.arbolParaAdoptar;
      this.cerrarModalConfirmacionArbol();
      if (!arbol) return;
      this.agregarItemAlArbol(arbol);
      // Se abre la canasta para que se vea que el árbol llegó
      this.abrirCanasta();
    }

    /* ---------- Modal de confirmación de adopción ---------- */

    abrirModalConfirmacionArbol(arbol) {
      this.arbolParaAdoptar = arbol;
      const modal = document.getElementById("modal-confirmacion-adopcion");
      if (!modal || !arbol) return;

      const imagen = document.getElementById("confirmacion-imagen");
      imagen.style.display = "";
      imagen.src = arbol.imagen || "";
      imagen.alt = arbol.nombre;
      document.getElementById("modal-confirmacion-titulo").textContent = arbol.nombre;
      document.getElementById("confirmacion-especie").textContent =
        [arbol.especie_nombre, arbol.productor ? `Productor: ${arbol.productor}` : ""].filter(Boolean).join(" · ");
      document.getElementById("confirmacion-precio").innerHTML =
        `${this.ui.formatearMonto(arbol.precio_mensual_clp)} <span class="text-sm font-medium text-stone-500">CLP / mes</span>`;
      document.getElementById("confirmacion-plan").textContent = `Plan ${arbol.plan}`;

      const cuposLibres = Math.max(0, (arbol.cupos_totales || 0) - (arbol.cupos_ocupados || 0));
      const exclusivo = arbol.tipo_suscripcion === "Exclusivo";
      const detalles = [
        ["fa-location-dot text-rose-500", "Ubicación", arbol.ubicacion],
        ["fa-scale-balanced text-emerald-600", "Cosecha estimada", arbol.estimacion_cosecha],
        [exclusivo ? "fa-crown text-amber-500" : "fa-users text-emerald-600", "Tipo", exclusivo ? "Exclusivo" : `Compartido (${arbol.cupos_totales})`],
        ["fa-ticket text-emerald-600", "Cupos libres", `${cuposLibres} de ${arbol.cupos_totales}`]
      ];
      document.getElementById("confirmacion-detalles").innerHTML = detalles
        .map(([icono, etiqueta, valor]) => `
          <div class="confirmacion-dato">
            <p class="text-[10px] uppercase tracking-wider font-bold text-stone-400"><i class="fa-solid ${icono} mr-1"></i>${e(etiqueta)}</p>
            <p class="text-sm font-bold text-stone-800 mt-1 leading-snug">${e(valor || "-")}</p>
          </div>`)
        .join("");

      modal.classList.remove("hidden");
    }

    cerrarModalConfirmacionArbol() {
      const modal = document.getElementById("modal-confirmacion-adopcion");
      if (modal) modal.classList.add("hidden");
      this.arbolParaAdoptar = null;
    }

    /* Productos de la canasta que faltan por pagar, y los ya pagados que
       esperan su despacho */
    porPagar() {
      return this.carrito.filter((item) => item.estado !== "comprado" && !item.pago_id
        && (item.tipo === "arbol" || item.tipo === "plan"));
    }

    porDespachar() {
      return this.carrito.filter((item) => item.estado !== "comprado" && item.pago_id);
    }

    /* Un solo pago para toda la canasta. El servidor lo cobra todo o nada:
       si un árbol se quedó sin cupo, no se cobra ningún producto. Con el
       pago aprobado se abre un solo formulario de despacho para todo. */
    async pagarCanasta() {
      const items = this.porPagar();
      if (!items.length || !auth.leerSesion()) return;

      this.cerrarCanasta();
      const respuesta = await AgroColab.pago.cobrar(items);
      if (!respuesta) {
        this.abrirCanasta();
        return;
      }

      // Cada producto guarda su pago: el pedido de un plan se enlaza con él
      items.forEach((item, i) => {
        item.pago_id = respuesta.pagos[i].id;
      });
      this.guardarCarrito();
      this.renderizarCanasta();
      this.completarDespacho();
    }

    /* Lo pagado queda en la canasta, marcado como pagado, hasta registrar
       su despacho: si se cierra el formulario, se retoma desde aquí. */
    completarDespacho() {
      const items = this.porDespachar();
      if (!items.length) return;
      this.cerrarCanasta();
      this.abrirLogistica(items);
    }

    /* ---------- Arranque de la vista ---------- */

    init() {
      this.carrito = auth.leerCarrito();
      this.actualizarContadorCanasta();
      const planGuardado = auth.leerPlan();
      if (planGuardado && planGuardado.nombre) {
        this.planActual = planGuardado;
      }

      document.getElementById("grid-planes-adopcion").addEventListener("click", (evento) => {
        const boton = evento.target.closest("[data-plan-adopcion]");
        if (boton) this.seleccionarPlanAdopcion(boton.dataset.planAdopcion);
      });

      document.getElementById("grid-planes").addEventListener("click", (evento) => {
        const boton = evento.target.closest("[data-plan-nombre]");
        if (boton) this.seleccionarPlan(boton);
      });

      document.getElementById("form-logistica-principal")
        .querySelectorAll('input[name="tipo_dest"]')
        .forEach((radio) => {
          radio.addEventListener("change", () => {
            this.cambiarDestino(radio.value);
          });
        });

      document.querySelectorAll('input[name="modal_tipo_dest"]').forEach((radio) => {
        radio.addEventListener("change", () => this.cambiarDestinoModal(radio.value));
      });

      document.getElementById("form-logistica-principal").addEventListener("submit", (evento) => {
        evento.preventDefault();
        this.enviarLogistica(evento);
      });

      document.getElementById("tree-container").addEventListener("click", (evento) => {
        const boton = evento.target.closest("[data-suscribir-id]");
        if (boton && !boton.disabled) {
          AgroColab.parcelas.agregarAlCarritoArbol(Number(boton.dataset.suscribirId));
        }
      });

      document.getElementById("btn-actualizar-arboles").addEventListener("click", () => this.cargarArboles());
      document.getElementById("form-modal-logistica").addEventListener("submit", (evento) => {
        evento.preventDefault();
        this.enviarLogisticaModal(evento);
      });

      this.mostrarPlanActual();
      this.cambiarDestino(this.destinoSeleccionado);
      this.actualizarFiltroActivo();
    }

    seleccionarPlanAdopcion(plan) {
      /* Volver a pulsar el plan ya activo lo desactiva, para volver a ver todo. */
      this.planAdopcionSeleccionado = this.planAdopcionSeleccionado === plan ? "todos" : plan;

      this.actualizarFiltroActivo();
      this.cargarArboles();
      this.irASeccion("seccion-parcelas");
    }

    actualizarFiltroActivo() {
      const plan = this.planAdopcionSeleccionado;

      document.querySelectorAll("[data-plan-adopcion]").forEach((boton) => {
        const tarjeta = boton.closest(".plan-adopcion-card");
        if (tarjeta) tarjeta.classList.toggle("plan-adopcion-card--activo", boton.dataset.planAdopcion === plan);
      });

      const texto = document.getElementById("filtro-activo-texto");
      if (texto) {
        texto.textContent = plan === "todos"
          ? "Mostrando los 3 planes de adopción. Selecciona un plan arriba para filtrar."
          : `Mostrando solo el Plan ${plan}. Vuelve a pulsar el plan para ver todos.`;
      }
    }

    /* ---------- Canasta / Mis compras ---------- */

    abrirCanasta() {
      const modal = document.getElementById("modal-canasta");
      modal.classList.remove("hidden", "cerrando");
      this.animarCanasta = true;
      this.renderizarCanasta();
    }

    /* Se anima la salida antes de ocultar: así no desaparece de golpe. */
    cerrarCanasta() {
      const modal = document.getElementById("modal-canasta");
      if (!modal || modal.classList.contains("hidden") || modal.classList.contains("cerrando")) return;
      modal.classList.add("cerrando");
      window.setTimeout(() => {
        modal.classList.add("hidden");
        modal.classList.remove("cerrando");
      }, 300);
    }

    /* La canasta se guarda en la pestaña (auth.guardarCarrito) para no
       perderla al ir a Privacidad o Términos y volver */
    guardarCarrito() {
      auth.guardarCarrito(this.carrito);
    }

    vaciarCarrito() {
      this.carrito = [];
      this.actualizarContadorCanasta();
    }

    agregarAlCarrito(item) {
      this.carrito.push(item);
      this.guardarCarrito();
      this.actualizarContadorCanasta();
      this.renderizarCanasta();
    }

    actualizarContadorCanasta() {
      const contador = document.getElementById("canasta-contador");
      if (!contador) return;
      if (this.carrito.length > 0) {
        contador.textContent = this.carrito.length;
        contador.classList.remove("hidden");
      } else {
        contador.classList.add("hidden");
      }
    }

    renderizarCanasta() {
      const contenido = document.getElementById("canasta-contenido");
      const pie = document.getElementById("canasta-pie");
      const resumen = document.getElementById("canasta-resumen");

      /* Los ítems entran en cascada solo al abrir, no en cada cambio */
      const animar = this.animarCanasta;
      this.animarCanasta = false;

      if (this.carrito.length === 0) {
        resumen.textContent = "Tus árboles y planes";
        pie.classList.add("hidden");
        contenido.innerHTML = `
          <div class="text-center py-14">
            <div class="w-20 h-20 mx-auto rounded-full bg-emerald-50 text-emerald-700 flex items-center justify-center text-3xl mb-5">
              <i class="fa-solid fa-seedling"></i>
            </div>
            <p class="font-extrabold text-stone-900 text-lg">Tu canasta está vacía</p>
            <p class="text-sm text-stone-500 mt-1 max-w-xs mx-auto">Adopta un árbol o elige una canasta de abastecimiento para empezar.</p>
            <button type="button" class="btn-hero btn-hero--primario mt-6" data-accion="parcelas.cerrarCanasta|parcelas.establecerLinea:adopcion">
              <i class="fa-solid fa-tree"></i> Explorar árboles
            </button>
          </div>`;
        return;
      }

      const pendientes = this.carrito.filter((item) => item.estado !== "comprado" && !item.pago_id);
      const totalPendiente = pendientes.reduce((total, item) => total + (Number(item.precio) || 0), 0);
      resumen.textContent = `${this.carrito.length} producto${this.carrito.length === 1 ? "" : "s"} · ${pendientes.length} por pagar`;

      contenido.innerHTML = `<div class="space-y-3">${this.carrito
        .map((item, index) => {
          const comprado = item.estado === "comprado";
          const miniatura = item.imagen
            ? `<img src="${e(item.imagen)}" alt="" class="w-full h-full object-cover" data-si-falla="quitar">`
            : `<i class="fa-solid ${item.tipo === "plan" ? "fa-basket-shopping" : "fa-tree"}"></i>`;
          const accion = comprado
            ? `<button type="button" class="canasta-accion canasta-accion--peligro" data-accion="parcelas.cancelarCompra" data-args='[${Number(index)}]'>Cancelar</button>`
            : item.pago_id
              ? ""
              : `<button type="button" class="canasta-accion" data-accion="parcelas.quitarDelCarrito" data-args='[${Number(index)}]'>Quitar</button>`;
          const pagado = !comprado && Boolean(item.pago_id);

          return `
            <article class="canasta-item ${animar ? "canasta-item--entrando" : ""}" style="animation-delay:${0.15 + index * 0.07}s">
              <div class="canasta-item__miniatura">${miniatura}</div>
              <div class="flex-1 min-w-0">
                <div class="flex items-start justify-between gap-2">
                  <p class="font-bold text-sm text-stone-900 truncate">${e(item.nombre)}</p>
                  <span class="canasta-estado ${comprado ? "canasta-estado--comprado" : ""}">
                    <i class="fa-solid ${comprado || pagado ? "fa-circle-check" : "fa-clock"}"></i> ${comprado ? "Comprado" : pagado ? "Pagado" : "Por pagar"}
                  </span>
                </div>
                <p class="text-xs text-stone-500 truncate mt-0.5">${e(item.descripcion)}</p>
                <div class="flex items-center justify-between gap-2 mt-3">
                  <p class="font-extrabold text-emerald-900">${this.ui.formatearMonto(item.precio)} <span class="text-[10px] font-medium text-stone-500">CLP${item.tipo === "arbol" ? " / mes" : ""}</span></p>
                  <div class="flex items-center gap-2">${accion}</div>
                </div>
              </div>
            </article>`;
        })
        .join("")}</div>`;

      const porDespachar = this.porDespachar().length;
      const botonPrincipal = pendientes.length
        ? `<button type="button" class="tc-boton canasta-pagar" data-accion="parcelas.pagarCanasta">
             <i class="fa-solid fa-lock"></i> Pagar ${pendientes.length === 1 ? "" : `${pendientes.length} productos · `}${this.ui.formatearMonto(totalPendiente)}
           </button>`
        : porDespachar
          ? `<button type="button" class="tc-boton canasta-pagar" data-accion="parcelas.completarDespacho">
               <i class="fa-solid fa-truck-fast"></i> Completar despacho
             </button>`
          : "";

      pie.classList.remove("hidden");
      pie.innerHTML = `
        <div class="flex items-end justify-between gap-3">
          <div>
            <p class="text-xs uppercase tracking-wider font-bold text-stone-500">Total por pagar</p>
            <p class="text-2xl font-extrabold text-emerald-900 leading-tight">${this.ui.formatearMonto(totalPendiente)} <span class="text-xs font-medium text-stone-500">CLP</span></p>
          </div>
          <button type="button" class="tc-enlace" data-accion="parcelas.cerrarCanasta">
            Seguir explorando <i class="fa-solid fa-arrow-right"></i>
          </button>
        </div>
        ${botonPrincipal}
        ${!pendientes.length && porDespachar ? `<p class="canasta-aviso">Ya pagaste: falta indicar dónde recibir ${porDespachar === 1 ? "este producto" : "estos productos"}.</p>` : ""}`;
    }

    quitarDelCarrito(index) {
      this.carrito.splice(index, 1);
      this.guardarCarrito();
      this.actualizarContadorCanasta();
      this.renderizarCanasta();
    }

    async cancelarCompra(index) {
      const item = this.carrito[index];
      if (!item) return;

      if (await AgroColab.dialogo.confirmar(`${item.nombre} saldrá de tu canasta${item.tipo === "arbol" ? " y su cupo quedará libre para otro comprador" : ""}.`, { titulo: "¿Cancelar este producto?", aceptar: "Cancelar", cancelar: "Mantener", peligro: true })) {
        // Si es un árbol, cancelar la suscripción en el backend
        if (item.tipo === "arbol") {
          try {
            const sesion = auth.leerSesion();
            const data = await api.cancelarSuscripcion(sesion, item.id);
            if (data.status === "success") {
              AgroColab.dialogo.avisar(data.mensaje, { tipo: "exito", titulo: "Adopción cancelada" });
              await this.cargarArboles();
            } else {
              AgroColab.dialogo.avisar(data.mensaje || "No se pudo cancelar la suscripción.", { tipo: "error" });
              return;
            }
          } catch (error) {
            console.error("Error al cancelar:", error);
            AgroColab.dialogo.avisar("No hay conexión con el servidor. Intenta nuevamente en unos segundos.", { tipo: "error" });
            return;
          }
        }

        this.carrito.splice(index, 1);
        this.guardarCarrito();
        this.actualizarContadorCanasta();
        this.renderizarCanasta();
      }
    }

    /* ---------- RUT de empresa ---------- */

    /* Valida el RUT con su dígito verificador (módulo 11), igual que el
       backend: "ansdjnjasdhjadh" o un RUT inventado no pasan. */
    rutValido(valor) {
      const limpio = String(valor || "").replace(/[.\-\s]/g, "").toUpperCase();
      const cuerpo = limpio.slice(0, -1);
      const dv = limpio.slice(-1);
      if (!/^\d{7,8}$/.test(cuerpo) || !/^[0-9K]$/.test(dv)) return false;

      let suma = 0;
      let factor = 2;
      for (const digito of cuerpo.split("").reverse()) {
        suma += Number(digito) * factor;
        factor = factor === 7 ? 2 : factor + 1;
      }
      const resto = 11 - (suma % 11);
      const esperado = resto === 11 ? "0" : resto === 10 ? "K" : String(resto);
      return dv === esperado;
    }

    /* Da formato mientras se escribe (76123456k -> 76.123.456-K) y avisa si
       el dígito verificador no corresponde. Se llama desde data-al-escribir. */
    formatearCampoRut(input) {
      const limpio = input.value.replace(/[^0-9kK]/g, "").toUpperCase().slice(0, 9);
      let formateado = limpio;
      if (limpio.length > 1) {
        const cuerpo = limpio.slice(0, -1).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
        formateado = `${cuerpo}-${limpio.slice(-1)}`;
      }
      input.value = formateado;

      const ayuda = input.parentElement.querySelector("[data-ayuda-rut]");
      const completo = limpio.length >= 8;
      const valido = this.rutValido(formateado);
      input.classList.toggle("input--invalido", completo && !valido);
      if (ayuda) {
        ayuda.className = `campo-ayuda ${completo ? (valido ? "campo-ayuda--ok" : "campo-ayuda--error") : ""}`;
        ayuda.textContent = !completo
          ? "Con dígito verificador, ej: 76.123.456-0"
          : valido ? "RUT válido" : "El dígito verificador no corresponde a este RUT";
      }
    }

    /* ---------- Modal de Logística ---------- */

    /* Abre el formulario de despacho en uno de dos modos:
       - Crear: items son lo pagado (uno o varios productos de la canasta, o
         un árbol desde el panel). Un mismo destino sirve para todos.
       - Editar: desde el panel, pedido es el despacho que ya existe. */
    abrirLogistica(items = null, pedido = null) {
      this.itemsLogistica = items ? (Array.isArray(items) ? items : [items]) : [];
      this.pedidoEditando = pedido;

      const varios = this.itemsLogistica.length > 1;
      const item = varios ? null : this.itemsLogistica[0] || null;
      const total = this.itemsLogistica.reduce((suma, i) => suma + (Number(i.precio) || 0), 0);
      const esArbol = Boolean(item && item.tipo === "arbol") || Boolean(pedido && pedido.tipo === "arbol");

      document.getElementById("form-modal-logistica").reset();
      const alerta = document.getElementById("modal-alerta-logistica");
      alerta.className = "hidden";
      alerta.innerHTML = "";

      document.getElementById("modal-log-titulo").textContent = pedido
        ? "Modificar logística"
        : esArbol ? "¿Dónde recibes la cosecha de tu árbol?" : "¿Dónde deseas recibir los productos?";
      document.getElementById("modal-log-subtitulo").textContent = pedido
        ? "Cambia dónde y cada cuánto recibes este despacho."
        : varios
          ? "Tu compra ya está pagada. Indica una sola vez dónde quieres recibir todo."
          : esArbol
            ? "Tu adopción ya está pagada. Indica dónde quieres recibir la cosecha."
            : "Último paso para completar tu compra: indica dónde quieres recibirla.";
      document.getElementById("modal-log-etiqueta").textContent = pedido
        ? `Pedido ${pedido.codigo_seguimiento}:`
        : varios ? "Tu compra:" : esArbol ? "Árbol adoptado:" : "Plan en configuración:";
      document.getElementById("modal-log-plan-nombre").textContent =
        pedido ? pedido.plan_nombre
          : varios ? `${this.itemsLogistica.length} productos`
            : item ? item.nombre : this.planActual.nombre;
      document.getElementById("modal-log-plan-precio").textContent =
        `${this.ui.formatearMonto(pedido ? pedido.monto_clp : item || varios ? total : this.planActual.precio)} CLP`;
      document.querySelector("#modal-log-boton span").textContent =
        pedido ? "Guardar cambios" : "Confirmar destino y registrar pedido";

      // Si algo de lo comprado exige despacho comercial (plan B2B), se parte
      // con ese tipo: el servidor lo exige igual
      const comercial = this.itemsLogistica.some((i) => i.destino === "comercial");
      this.cambiarDestinoModal((pedido && pedido.tipo_destino) || (comercial ? "comercial" : "particular"));

      const conFrecuencia = this.itemsLogistica.find((i) => i.frecuencia);
      document.getElementById("modal-dest-frecuencia").value =
        (pedido && pedido.frecuencia_entrega) || (conFrecuencia && conFrecuencia.frecuencia) || "quincenal";

      if (pedido) {
        document.getElementById("modal-dest-direccion").value = pedido.direccion || "";
        document.getElementById("modal-dest-comuna").value = pedido.comuna || "";
        document.getElementById("modal-dest-postal").value = pedido.codigo_postal || "";
        document.getElementById("modal-dest-codigo-pais").value = pedido.telefono_codigo || "+56";
        document.getElementById("modal-dest-celular").value = pedido.telefono || "";
        document.getElementById("modal-com-razon").value = pedido.razon_social || "";
        document.getElementById("modal-com-rut").value = pedido.rut || "";
      }

      document.getElementById("modal-logistica").classList.remove("hidden");
    }

    /* Lo pagado sigue en la canasta como «Pagado» hasta registrar su
       despacho: cerrar el formulario no lo pierde. */
    cerrarLogistica() {
      document.getElementById("modal-logistica").classList.add("hidden");
      this.pedidoEditando = null;
      this.itemsLogistica = [];
      this.actualizarContadorCanasta();
      this.renderizarCanasta();
    }

    /* Marca el tipo de destino en el modal y muestra los datos comerciales
       solo cuando corresponden. */
    cambiarDestinoModal(tipo) {
      const esComercial = tipo === "comercial";
      const radio = document.querySelector(`input[name="modal_tipo_dest"][value="${esComercial ? "comercial" : "particular"}"]`);
      if (radio) radio.checked = true;
      document.getElementById("modal-card-part").className =
        `destino-card ${esComercial ? "destino-card--inactivo" : "destino-card--activo-particular"}`;
      document.getElementById("modal-card-com").className =
        `destino-card ${esComercial ? "destino-card--activo-comercial" : "destino-card--inactivo"}`;
      document.getElementById("modal-bloque-comercial").classList.toggle("hidden", !esComercial);
    }

    async enviarLogisticaModal(evento) {
      evento.preventDefault();

      const alerta = document.getElementById("modal-alerta-logistica");
      const esComercial = document.querySelector('input[name="modal_tipo_dest"]:checked').value === "comercial";

      const datos = {
        tipo_destino: esComercial ? "comercial" : "particular",
        razon_social: esComercial ? document.getElementById("modal-com-razon").value.trim() : null,
        rut: esComercial ? document.getElementById("modal-com-rut").value.trim() : null,
        direccion: document.getElementById("modal-dest-direccion").value.trim(),
        comuna: document.getElementById("modal-dest-comuna").value.trim(),
        codigo_postal: document.getElementById("modal-dest-postal").value.trim(),
        telefono_codigo: document.getElementById("modal-dest-codigo-pais").value,
        telefono: document.getElementById("modal-dest-celular").value.trim(),
        frecuencia_entrega: document.getElementById("modal-dest-frecuencia").value
      };

      if (esComercial && (!datos.razon_social || !datos.rut)) {
        this.ui.mostrarAlerta(alerta, "error", "Completa la razón social y el RUT para el despacho comercial.");
        return;
      }
      if (esComercial && !this.rutValido(datos.rut)) {
        this.ui.mostrarAlerta(alerta, "error", "El RUT de la empresa no es válido. Revisa el dígito verificador (ej: 76.123.456-0).");
        return;
      }

      const editando = this.pedidoEditando;
      this.ui.mostrarAlerta(alerta, "info", editando ? "Guardando cambios..." : "Registrando tu pedido...");

      try {
        let data;
        if (editando) {
          data = await this.api.actualizarLogistica(editando.id, datos);
        } else {
          /* Un pedido por producto pagado, todos al mismo destino. Lo que
             queda registrado sale de la canasta; si uno falla, sigue en ella
             como pagado para reintentarlo. */
          const items = this.itemsLogistica;
          const fallos = [];
          for (const item of items) {
            const esArbol = item.tipo === "arbol";
            const respuesta = await this.api.crearPedido({
              ...datos,
              pago_id: esArbol ? null : item.pago_id,
              plan_nombre: esArbol ? `Cosecha de ${item.nombre}` : item.nombre,
              tipo: esArbol ? "arbol" : "abastecimiento",
              arbol_id: esArbol ? item.id : null
            });
            if (respuesta.status === "success") {
              data = respuesta;
              this.carrito = this.carrito.filter((c) => c !== item);
            } else {
              fallos.push({ item, mensaje: respuesta.mensaje });
            }
          }
          this.guardarCarrito();
          this.itemsLogistica = fallos.map((f) => f.item);

          if (fallos.length) {
            const detalle = fallos.map((f) => `${f.item.nombre}: ${f.mensaje || "no se pudo registrar"}`).join(" · ");
            this.ui.mostrarAlerta(alerta, "error", fallos.length === items.length
              ? detalle
              : `Se registraron ${items.length - fallos.length} de ${items.length} despachos. Falta: ${detalle}`);
            return;
          }
          if (items.length > 1) data = { ...data, mensaje: `Se registraron los ${items.length} despachos.` };
        }

        if (data.status !== "success") {
          this.ui.mostrarAlerta(alerta, "error", data.mensaje || "No se pudo guardar la logística.");
          return;
        }

        alerta.className = "alerta alerta--exito-lg";
        alerta.innerHTML = `
          <div class="flex items-center gap-2 mb-1">
            <i class="fa-solid fa-circle-check text-emerald-600 text-base"></i>
            <span class="text-sm font-bold">${e(data.mensaje)}</span>
          </div>
          <p class="text-stone-600">Destino: <strong>${e(datos.direccion)}, ${e(datos.comuna)}</strong> (${e(datos.tipo_destino)}) · Frecuencia: <strong>${e(datos.frecuencia_entrega)}</strong>.</p>
        `;

        setTimeout(() => {
          this.cerrarLogistica();
          if (AgroColab.views.vistaActual === "dashboard-comprador") {
            AgroColab.dashboard.cargar();
          } else {
            AgroColab.views.mostrarVista("dashboard-comprador");
          }
        }, 1500);
      } catch (error) {
        this.ui.mostrarAlerta(alerta, "error", "Error de comunicación con el backend.");
      }
    }

    /* Se ejecuta cada vez que la vista entra en pantalla. */
    async cargar() {
      return this.cargarArboles();
    }
  }

  AgroColab.parcelas = new ParcelasService();
})();
