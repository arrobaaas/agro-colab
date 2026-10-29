/* Agro-Colab - Servicio de parcelas: adopción de árboles, planes de
   abastecimiento, canasta, logística y pago. Servicio orientado a objetos
   (ParcelasService) con instancia expuesta como AgroColab.parcelas. */

(function () {
  const AgroColab = (window.AgroColab = window.AgroColab || {});
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
      this.itemLogisticaActual = null;
      this.carrito = [];
      this.arbolParaAdoptar = null;
    }

    /* ---------- Plan y destino de despacho ---------- */

    mostrarPlanActual() {
      document.getElementById("log-plan-nombre").textContent = this.planActual.nombre;
      document.getElementById("log-plan-precio").textContent = `${this.ui.formatearMonto(this.planActual.precio)} CLP`;
    }

    seleccionarPlan(boton) {
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
        tipo: "plan"
      };
      this.agregarAlCarrito(item);
      this.itemLogisticaActual = item;

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

      document.querySelectorAll("[data-linea]").forEach(function (boton) {
        const activo = boton.dataset.linea === linea;
        boton.classList.toggle("nav-link--activo", activo);
        boton.setAttribute("aria-selected", activo ? "true" : "false");
      });

      const destino = scrollTo || (esAdopcion ? "seccion-adopcion" : "seccion-abastecimiento");
      document.getElementById(destino).scrollIntoView({ behavior: "smooth" });
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
        monto_clp: this.planActual.precio,
        cliente_id: sesion ? sesion.id : null,
        cliente_nombre: document.getElementById("dest-nombre").value.trim(),
        telefono: document.getElementById("dest-tel").value.trim(),
        email: document.getElementById("dest-email").value.trim(),
        tipo_destino: this.destinoSeleccionado,
        razon_social: esComercial ? document.getElementById("com-razon").value.trim() : null,
        rut: esComercial ? document.getElementById("com-rut").value.trim() : null,
        direccion: document.getElementById("dest-direccion").value.trim(),
        comuna: document.getElementById("dest-comuna").value.trim(),
        frecuencia_entrega: document.getElementById("dest-frecuencia").value
      };

      if (esComercial && (!bodyData.razon_social || !bodyData.rut)) {
        this.ui.mostrarAlerta(alerta, "errorGrande", "Completa la razón social y el RUT para el despacho comercial.");
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
              <span class="text-sm font-bold">${data.mensaje}</span>
            </div>
            <p class="text-stone-600">Destino: <strong>${bodyData.direccion}, ${bodyData.comuna}</strong> (${bodyData.tipo_destino.toUpperCase()}) | Frecuencia: <strong>${bodyData.frecuencia_entrega}</strong>.</p>
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
          container.innerHTML = `<p class="md:col-span-3 text-center text-stone-500 text-sm py-10">No hay árboles disponibles para el Plan ${this.planAdopcionSeleccionado}.</p>`;
          return;
        }

        visibles.forEach((arbol) => {
          container.insertAdjacentHTML("beforeend", this.plantillaArbol(arbol));
        });
      } catch (error) {
        container.innerHTML = `<div class="col-span-3 p-4 bg-red-50 text-red-700 text-xs rounded-xl">Error al conectar con la API (${this.config.API_URL}).</div>`;
      }
    }

    plantillaArbol(arbol) {
      const cuposTotales = arbol.cupos_totales || 0;
      const cuposLibres = Math.max(0, cuposTotales - (arbol.cupos_ocupados || 0));
      const porcentaje = cuposTotales ? Math.round(((cuposTotales - cuposLibres) / cuposTotales) * 100) : 100;
      const disponible = cuposLibres > 0;
      const exclusivo = arbol.tipo_suscripcion === "Exclusivo";
      const textoCupos = disponible
        ? `${cuposLibres} de ${cuposTotales} cupo${cuposTotales === 1 ? "" : "s"} libre${cuposLibres === 1 ? "" : "s"}`
        : "Sin cupos disponibles";

      /* Se devuelve la tarjeta completa, con su <article> exterior. Antes se
         devolvía solo el innerHTML: se perdía el envoltorio y la foto y los
         datos quedaban como celdas sueltas de la grilla. */
      return `
        <article class="arbol-card group">
          <div class="arbol-card__media">
            <img src="${arbol.imagen || ""}" alt="${arbol.nombre}" loading="lazy" onerror="this.style.display='none'">
            <span class="arbol-card__plan">${arbol.plan}</span>
            <span class="arbol-card__tipo ${exclusivo ? "arbol-card__tipo--exclusivo" : ""}">
              <i class="fa-solid ${exclusivo ? "fa-crown" : "fa-users"}"></i> ${arbol.tipo_suscripcion || ""}
            </span>
            <div class="arbol-card__titulo">
              ${arbol.especie_nombre ? `<p class="arbol-card__especie">${arbol.especie_nombre}</p>` : ""}
              <h4>${arbol.nombre}</h4>
            </div>
          </div>

          <div class="p-5 flex flex-col gap-4 flex-1">
            <ul class="space-y-1.5 text-xs text-stone-600">
              <li class="flex items-center gap-2 truncate"><i class="fa-solid fa-location-dot text-rose-500 w-4 text-center"></i> ${arbol.ubicacion}</li>
              <li class="flex items-center gap-2"><i class="fa-solid fa-scale-balanced text-emerald-600 w-4 text-center"></i> Cosecha estimada: <strong class="text-stone-800">${arbol.estimacion_cosecha}</strong></li>
              ${arbol.productor ? `<li class="flex items-center gap-2 truncate"><i class="fa-solid fa-tractor text-amber-600 w-4 text-center"></i> ${arbol.productor}</li>` : ""}
            </ul>

            <div>
              <div class="flex justify-between text-[11px] mb-1.5">
                <span class="${disponible ? "text-stone-500" : "text-rose-600 font-bold"}">${textoCupos}</span>
                <span class="font-bold text-stone-700">${porcentaje}% adoptado</span>
              </div>
              <div class="h-1.5 rounded-full bg-stone-100 overflow-hidden">
                <div class="h-full rounded-full ${disponible ? "bg-emerald-500" : "bg-rose-400"}" style="width: ${porcentaje}%"></div>
              </div>
            </div>

            <div class="mt-auto pt-4 border-t border-stone-100 flex items-center justify-between gap-3">
              <div>
                <p class="text-xl font-black text-emerald-900 leading-none">${this.ui.formatearMonto(arbol.precio_mensual_clp)}</p>
                <p class="text-[10px] text-stone-500 mt-1">CLP por mes</p>
              </div>
              <button type="button" class="btn-suscribir ${disponible ? "btn-suscribir--activo" : "btn-suscribir--bloqueado"}" data-suscribir-id="${arbol.id}" ${disponible ? "" : "disabled"}>
                <i class="fa-solid ${disponible ? "fa-cart-plus" : "fa-lock"}"></i> ${disponible ? "Adoptar" : "Completo"}
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
        if (!arbol) { window.alert("No se encontró el árbol."); return; }

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
          window.alert(`Ya tienes una suscripción activa para "${arbol.nombre}". No puedes adoptar más de una vez.`);
          return;
        }

        this.abrirModalConfirmacionArbol(arbol);
      } catch (error) {
        window.alert("Error de comunicación con el backend");
      }
    }

    /* Agregar un árbol ya validado a la canasta (estado pendiente de pago). */
    agregarItemAlArbol(arbol) {
      const item = {
        id: arbol.id,
        nombre: arbol.nombre,
        descripcion: `Árbol adoptado - Plan ${arbol.plan}`,
        precio: arbol.precio_mensual_clp,
        estado: "pendiente",
        tipo: "arbol"
      };
      this.agregarAlCarrito(item);
      this.itemLogisticaActual = item;
      this.cargarArboles();
    }

    /* Respuesta del modal de confirmación de adopción ("Sí" -> agregar / "No" -> cerrar). */
    confirmarAdopcion() {
      const arbol = this.arbolParaAdoptar;
      this.cerrarModalConfirmacionArbol();
      if (!arbol) return;
      this.agregarItemAlArbol(arbol);
    }

    /* ---------- Modal de confirmación de adopción ---------- */

    abrirModalConfirmacionArbol(arbol) {
      this.arbolParaAdoptar = arbol;
      const modal = document.getElementById("modal-confirmacion-adopcion");
      const titulo = document.getElementById("modal-confirmacion-titulo");
      const texto = document.getElementById("modal-confirmacion-texto");
      if (titulo) titulo.textContent = "¿Estás seguro de adoptar este árbol?";
      if (texto) texto.textContent = `¿Estás seguro de que quieres adoptar el árbol "${arbol ? arbol.nombre : ""}"?`;
      if (modal) modal.classList.remove("hidden");
    }

    cerrarModalConfirmacionArbol() {
      const modal = document.getElementById("modal-confirmacion-adopcion");
      if (modal) modal.classList.add("hidden");
      this.arbolParaAdoptar = null;
    }

    /* Pago desde la canasta: ejecuta la suscripción del árbol y abre la logística. */
    async pagarSuscripcion(index) {
      const item = this.carrito[index];
      if (!item) return;

      const sesion = auth.leerSesion();
      if (!sesion) return;

      try {
        if (item.tipo !== "plan") {
          const data = await api.suscribirArbol(sesion, item.id);
          if (data.status !== "success") {
            window.alert(data.mensaje || "No se pudo completar el pago.");
            return;
          }
        }

        // El producto comprado se elimina de la canasta y la canasta vuelve a estar vacía.
        this.quitarDelCarrito(index);

        this.abrirLogistica();
      } catch (error) {
        window.alert("Error de comunicación con el backend");
      }
    }

    /* ---------- Arranque de la vista ---------- */

    init() {
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
      document.getElementById("seccion-parcelas").scrollIntoView({ behavior: "smooth" });
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
      modal.classList.remove("hidden");
      this.renderizarCanasta();
    }

    cerrarCanasta() {
      document.getElementById("modal-canasta").classList.add("hidden");
    }

    agregarAlCarrito(item) {
      this.carrito.push(item);
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

      if (this.carrito.length === 0) {
        contenido.innerHTML = '<p class="text-stone-500 text-sm text-center py-8">Tu canasta está vacía</p>';
        return;
      }

      let html = '<div class="space-y-4">';
      this.carrito.forEach(function (item, index) {
        const esComprado = item.estado === "comprado";
        html += `
          <div class="flex justify-between items-center p-4 bg-stone-50 rounded-xl border ${esComprado ? 'border-emerald-200 bg-emerald-50/50' : 'border-stone-200'}">
            <div>
              <div class="flex items-center gap-2">
                <p class="font-bold text-sm text-stone-900">${item.nombre}</p>
                ${esComprado ? '<span class="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">Comprado</span>' : ''}
              </div>
              <p class="text-xs text-stone-500">${item.descripcion}</p>
            </div>
            <div class="flex items-center gap-3">
              <span class="font-black text-emerald-900">${this.ui.formatearMonto(item.precio)} CLP</span>
              ${esComprado
                ? `
                  <button type="button" onclick="AgroColab.parcelas.cancelarCompra(${index})" class="text-red-500 hover:text-red-700 text-sm font-bold">Cancelar</button>
                `
                : `<button type="button" onclick="AgroColab.parcelas.quitarDelCarrito(${index})" class="text-red-500 hover:text-red-700 text-sm font-bold">Quitar</button>`
              }
              ${!esComprado && (item.tipo === "arbol" || item.tipo === "plan") ? `
                <button type="button" onclick="AgroColab.parcelas.pagarSuscripcion(${index})" class="px-4 py-2 rounded-xl bg-emerald-600 text-white font-bold text-sm">Pagar</button>
              ` : ""}
            </div>
          </div>
        `;
      });
      html += '</div>';
      contenido.innerHTML = html;
    }

    quitarDelCarrito(index) {
      this.carrito.splice(index, 1);
      this.actualizarContadorCanasta();
      this.renderizarCanasta();
    }

    async cancelarCompra(index) {
      const item = this.carrito[index];
      if (!item) return;

      if (window.confirm(`¿Estás seguro de cancelar "${item.nombre}"?`)) {
        // Si es un árbol, cancelar la suscripción en el backend
        if (item.tipo === "arbol") {
          try {
            const sesion = auth.leerSesion();
            const data = await api.cancelarSuscripcion(sesion, item.id);
            if (data.status === "success") {
              window.alert(data.mensaje);
              await this.cargarArboles();
            } else {
              window.alert(data.mensaje || "No se pudo cancelar la suscripción.");
              return;
            }
          } catch (error) {
            console.error("Error al cancelar:", error);
            window.alert("Error de comunicación con el backend");
            return;
          }
        }

        this.carrito.splice(index, 1);
        this.actualizarContadorCanasta();
        this.renderizarCanasta();
      }
    }

    /* ---------- Modal de Logística (al suscribirse) ---------- */

    abrirLogistica() {
      const modal = document.getElementById("modal-logistica");
      modal.classList.remove("hidden");
    }

    cerrarLogistica() {
      document.getElementById("modal-logistica").classList.add("hidden");
    }

    /* ---------- Modificar la logística desde la canasta ---------- */

    editarLogistica(index) {
      const item = this.carrito[index];
      if (!item) return;

      this.abrirLogistica();

      const sesion = auth.leerSesion();

      const radioPart = document.querySelector('input[name="modal_tipo_dest"][value="particular"]');
      const radioCom = document.querySelector('input[name="modal_tipo_dest"][value="comercial"]');
      const cardPart = document.getElementById("modal-card-part");
      const cardCom = document.getElementById("modal-card-com");
      const bloqueCom = document.getElementById("modal-bloque-comercial");

      const esComercial = item.tipoDestino === "comercial";
      if (esComercial) {
        if (radioCom) radioCom.checked = true;
        if (radioPart) radioPart.checked = false;
        cardCom.className = "destino-card destino-card--activo-comercial";
        cardPart.className = "destino-card destino-card--inactivo";
        bloqueCom.classList.remove("hidden");
      } else {
        if (radioPart) radioPart.checked = true;
        if (radioCom) radioCom.checked = false;
        cardPart.className = "destino-card destino-card--activo-particular";
        cardCom.className = "destino-card destino-card--inactivo";
        bloqueCom.classList.add("hidden");
      }

      document.getElementById("modal-dest-nombre").value =
        (item.contacto && item.contacto.nombre) || (sesion && sesion.nombre) || "";
      document.getElementById("modal-dest-tel").value =
        (item.contacto && item.contacto.tel) || (sesion && sesion.telefono) || "";
      document.getElementById("modal-dest-email").value =
        (item.contacto && item.contacto.email) || (sesion && sesion.email) || "";
      document.getElementById("modal-dest-direccion").value = item.direccion || "";
      document.getElementById("modal-dest-comuna").value = item.comuna || "";
      document.getElementById("modal-dest-frecuencia").value = item.frecuencia || "quincenal";

      if (esComercial) {
        document.getElementById("modal-com-razon").value = item.razonSocial || "";
        document.getElementById("modal-com-rut").value = item.rut || "";
      }
    }

    async enviarLogisticaModal(evento) {
      evento.preventDefault();

      const alerta = document.getElementById("modal-alerta-logistica");
      const formulario = document.getElementById("form-modal-logistica");
      const esComercial = document.querySelector('input[name="modal_tipo_dest"]:checked').value === "comercial";
      const sesion = auth.leerSesion();

      const bodyData = {
        plan_nombre: this.planActual.nombre,
        monto_clp: this.planActual.precio,
        cliente_id: sesion ? sesion.id : null,
        cliente_nombre: document.getElementById("modal-dest-nombre").value.trim(),
        telefono: document.getElementById("modal-dest-tel").value.trim(),
        email: document.getElementById("modal-dest-email").value.trim(),
        tipo_destino: esComercial ? "comercial" : "particular",
        razon_social: esComercial ? document.getElementById("modal-com-razon").value.trim() : null,
        rut: esComercial ? document.getElementById("modal-com-rut").value.trim() : null,
        direccion: document.getElementById("modal-dest-direccion").value.trim(),
        comuna: document.getElementById("modal-dest-comuna").value.trim(),
        frecuencia_entrega: document.getElementById("modal-dest-frecuencia").value
      };

      if (esComercial && (!bodyData.razon_social || !bodyData.rut)) {
        this.ui.mostrarAlerta(alerta, "error", "Completa la razón social y el RUT para el despacho comercial.");
        return;
      }

      this.ui.mostrarAlerta(alerta, "info", "Registrando tu pedido...");

      try {
        const data = await this.api.crearPedido(bodyData);

        if (data.status === "success") {
          alerta.className = "alerta alerta--exito-lg";
          alerta.innerHTML = `
            <div class="flex items-center gap-2 mb-1">
              <i class="fa-solid fa-circle-check text-emerald-600 text-base"></i>
              <span class="text-sm font-bold">${data.mensaje}</span>
            </div>
            <p class="text-stone-600">Destino: <strong>${bodyData.direccion}, ${bodyData.comuna}</strong> (${bodyData.tipo_destino.toUpperCase()}) | Frecuencia: <strong>${bodyData.frecuencia_entrega}</strong>.</p>
          `;
          formulario.reset();

          // Guardar los datos de entrega en el item del carrito para poder
          // reutilizarlos al modificar la logística.
          if (this.itemLogisticaActual) {
            this.itemLogisticaActual.direccion = bodyData.direccion;
            this.itemLogisticaActual.comuna = bodyData.comuna;
            this.itemLogisticaActual.frecuencia = bodyData.frecuencia_entrega;
            this.itemLogisticaActual.tipoDestino = bodyData.tipo_destino;
            this.itemLogisticaActual.contacto = {
              nombre: bodyData.cliente_nombre,
              tel: bodyData.telefono,
              email: bodyData.email
            };
          }

          setTimeout(() => {
            this.cerrarLogistica();
            AgroColab.views.mostrarVista("dashboard-comprador");
          }, 2000);
        } else {
          this.ui.mostrarAlerta(alerta, "error", data.mensaje || "No se pudo registrar la solicitud logística.");
        }
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
