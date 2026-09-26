/* Agro-Colab - Vista de parcelas: adopción de árboles, planes de abastecimiento
   y logística. Es la vista que ve el usuario después de entrar, según su rol.

   Dos líneas de producto independientes:
     - Adopción:      se compra un cupo de un árbol (Básico/Intermedio/Premium).
     - Abastecimiento: se contrata una canasta de cosecha (Dúo/Familiar/B2B). */

(function () {
  const AgroColab = (window.AgroColab = window.AgroColab || {});
  const { api, ui, auth, config } = AgroColab;

  const PLAN_ABASTECIMIENTO_INICIAL = { nombre: "Canasta Huerto Esencial", precio: 19900 };

  let planActual = { ...PLAN_ABASTECIMIENTO_INICIAL };
  let destinoSeleccionado = "particular";
  let planAdopcionSeleccionado = "todos";

  /* ---------- Plan y destino de despacho ---------- */

  function mostrarPlanActual() {
    document.getElementById("log-plan-nombre").textContent = planActual.nombre;
    document.getElementById("log-plan-precio").textContent = `${ui.formatearMonto(planActual.precio)} CLP`;
  }

  function seleccionarPlan(boton) {
    planActual = {
      nombre: boton.dataset.planNombre,
      precio: Number(boton.dataset.planPrecio)
    };

    document.getElementById("dest-frecuencia").value = boton.dataset.planFrecuencia;
    cambiarDestino(boton.dataset.planDestino);
    mostrarPlanActual();
    auth.guardarPlan(planActual);

    document.getElementById("seccion-logistica").scrollIntoView({ behavior: "smooth" });
  }

  function cambiarDestino(tipo) {
    destinoSeleccionado = tipo;

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

  /* ---------- Envío del pedido logístico ---------- */

  async function enviarLogistica(evento) {
    evento.preventDefault();

    const alerta = document.getElementById("alerta-logistica");
    const formulario = document.getElementById("form-logistica-principal");
    const esComercial = destinoSeleccionado === "comercial";

    const bodyData = {
      plan_nombre: planActual.nombre,
      monto_clp: planActual.precio,
      cliente_nombre: document.getElementById("dest-nombre").value.trim(),
      telefono: document.getElementById("dest-tel").value.trim(),
      email: document.getElementById("dest-email").value.trim(),
      tipo_destino: destinoSeleccionado,
      razon_social: esComercial ? document.getElementById("com-razon").value.trim() : null,
      rut: esComercial ? document.getElementById("com-rut").value.trim() : null,
      direccion: document.getElementById("dest-direccion").value.trim(),
      comuna: document.getElementById("dest-comuna").value.trim(),
      frecuencia_entrega: document.getElementById("dest-frecuencia").value
    };

    if (esComercial && (!bodyData.razon_social || !bodyData.rut)) {
      ui.mostrarAlerta(
        alerta,
        "errorGrande",
        "Completa la razón social y el RUT para el despacho comercial."
      );
      return;
    }

    ui.mostrarAlerta(alerta, "infoGrande", "Registrando tu pedido...");

    try {
      const data = await api.crearPedido(bodyData);

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
        cambiarDestino(destinoSeleccionado);
      } else {
        ui.mostrarAlerta(alerta, "errorGrande", data.mensaje || "No se pudo registrar la solicitud logística.");
      }
    } catch (error) {
      ui.mostrarAlerta(
        alerta,
        "errorGrande",
        `Error: backend inaccesible en ${config.API_URL}. Revisa que Uvicorn esté activo.`
      );
    }
  }

  /* ---------- Catálogo de parcelas ---------- */

  function plantillaArbol(arbol) {
    const cuposLibres = arbol.cupos_totales - arbol.cupos_ocupados;
    const porcentaje = (arbol.cupos_ocupados / arbol.cupos_totales) * 100;
    const claseInscripcion =
      arbol.tipo_suscripcion === "Exclusivo"
        ? "badge-suscripcion badge-suscripcion--exclusivo"
        : "badge-suscripcion badge-suscripcion--compartido";

    return `
      <div class="arbol-card">
        <div>
          <div class="relative h-44 w-full overflow-hidden bg-stone-200">
            <img src="${arbol.imagen}" alt="${arbol.nombre}" class="w-full h-full object-cover">
            <span class="${claseInscripcion}">${arbol.tipo_suscripcion}</span>
            <span class="badge-productor">👨‍🌾 ${arbol.productor}</span>
          </div>
          <div class="p-5">
            <h4 class="font-black text-lg text-stone-900 mb-1">${arbol.nombre}</h4>
            <p class="text-xs text-stone-500 mb-4 flex items-center gap-1">
              <i class="fa-solid fa-location-dot text-rose-500"></i> ${arbol.ubicacion}
            </p>
            <div class="space-y-2 text-xs text-stone-600 mb-4">
              <div class="dato-arbol">
                <span class="text-stone-500">Plan de adopción:</span>
                <span class="font-bold text-stone-800">${arbol.plan}</span>
              </div>
              <div class="dato-arbol">
                <span class="text-stone-500">Cosecha proyectada:</span>
                <span class="font-bold text-stone-800">${arbol.estimacion_cosecha}</span>
              </div>
              <div class="dato-arbol">
                <span class="text-stone-500">Participación:</span>
                <span class="font-bold text-stone-800">${arbol.cupos_ocupados} / ${arbol.cupos_totales} suscriptores</span>
              </div>
              <div class="pt-1">
                <div class="w-full bg-stone-100 h-2 rounded-full overflow-hidden">
                  <div class="bg-emerald-600 h-2 rounded-full" style="width: ${porcentaje}%"></div>
                </div>
              </div>
            </div>
            <p class="text-2xl font-black text-stone-900">
              ${ui.formatearMonto(arbol.precio_mensual_clp)} <span class="text-xs font-normal text-stone-500">/ mes</span>
            </p>
          </div>
        </div>
        <div class="p-5 pt-0">
          <button
            type="button"
            class="btn-suscribir ${cuposLibres > 0 ? "btn-suscribir--activo" : "btn-suscribir--bloqueado"}"
            data-suscribir-id="${arbol.id}"
            ${cuposLibres === 0 ? "disabled" : ""}
          >
            ${cuposLibres > 0 ? "Suscribirse al cultivo" : "Capacidad Completa"}
          </button>
        </div>
      </div>
    `;
  }

  /* ---------- Filtro por plan de adopción ---------- */

  function actualizarFiltroActivo() {
    const texto = document.getElementById("filtro-activo-texto");

    if (texto) {
      texto.textContent =
        planAdopcionSeleccionado === "todos"
          ? "Mostrando los 3 planes de adopción. Selecciona un plan arriba para filtrar."
          : `Mostrando solo árboles del Plan ${planAdopcionSeleccionado}.`;
    }

    document
      .querySelectorAll("#grid-planes-adopcion [data-plan-adopcion]")
      .forEach(function (boton) {
        const activo = boton.dataset.planAdopcion === planAdopcionSeleccionado;
        boton.closest(".plan-adopcion-card").classList.toggle("plan-adopcion-card--activo", activo);
      });
  }

  function seleccionarPlanAdopcion(plan) {
    /* Volver a pulsar el plan ya activo lo desactiva, para volver a ver todo. */
    planAdopcionSeleccionado =
      planAdopcionSeleccionado === plan ? "todos" : plan;

    actualizarFiltroActivo();
    cargarArboles();
    document.getElementById("seccion-parcelas").scrollIntoView({ behavior: "smooth" });
  }

  async function cargarArboles() {
    const container = document.getElementById("tree-container");

    try {
      const arboles = await api.obtenerArboles();
      container.innerHTML = "";

      if (!arboles.length) {
        container.innerHTML = `<p class="text-stone-500 text-sm">No hay parcelas disponibles por ahora.</p>`;
        return;
      }

      const visibles =
        planAdopcionSeleccionado === "todos"
          ? arboles
          : arboles.filter((arbol) => arbol.plan === planAdopcionSeleccionado);

      if (!visibles.length) {
        container.innerHTML = `<p class="text-stone-500 text-sm">No hay árboles disponibles para el Plan ${planAdopcionSeleccionado}.</p>`;
        return;
      }

      visibles.forEach(function (arbol) {
        container.insertAdjacentHTML("beforeend", plantillaArbol(arbol));
      });
    } catch (error) {
      container.innerHTML = `<div class="col-span-3 p-4 bg-red-50 text-red-700 text-xs rounded-xl">Error al conectar con la API (${config.API_URL}).</div>`;
    }
  }

  /* Dentro de esta vista siempre hay sesión, así que no se pide el nombre. */
  async function suscribirse(treeId) {
    const sesion = auth.leerSesion();
    if (!sesion) return;

    try {
      const data = await api.suscribirArbol(sesion.nombre, treeId);
      window.alert(data.mensaje);
      cargarArboles();
    } catch (error) {
      window.alert("Error de comunicación con el backend");
    }
  }

  /* ---------- Arranque de la vista ---------- */

  function init() {
    const planGuardado = auth.leerPlan();
    if (planGuardado && planGuardado.nombre) {
      planActual = planGuardado;
    }

    document.getElementById("grid-planes-adopcion").addEventListener("click", function (evento) {
      const boton = evento.target.closest("[data-plan-adopcion]");
      if (boton) seleccionarPlanAdopcion(boton.dataset.planAdopcion);
    });

    document.getElementById("grid-planes").addEventListener("click", function (evento) {
      const boton = evento.target.closest("[data-plan-nombre]");
      if (boton) seleccionarPlan(boton);
    });

    document.getElementById("form-logistica-principal")
      .querySelectorAll('input[name="tipo_dest"]')
      .forEach(function (radio) {
        radio.addEventListener("change", function () {
          cambiarDestino(radio.value);
        });
      });

    document.getElementById("form-logistica-principal").addEventListener("submit", enviarLogistica);

    document.getElementById("tree-container").addEventListener("click", function (evento) {
      const boton = evento.target.closest("[data-suscribir-id]");
      if (boton && !boton.disabled) {
        suscribirse(Number(boton.dataset.suscribirId));
      }
    });

    document.getElementById("btn-actualizar-arboles").addEventListener("click", cargarArboles);

    mostrarPlanActual();
    cambiarDestino(destinoSeleccionado);
    actualizarFiltroActivo();
  }

  /* Se ejecuta cada vez que la vista entra en pantalla. */
  function cargar() {
    return cargarArboles();
  }

  AgroColab.parcelas = { init, cargar };
})();
