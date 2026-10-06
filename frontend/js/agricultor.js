/* Agro-Colab - Vista del Agricultor: dashboard de árboles y formulario
   para publicar nuevos árboles. */

(function () {
  const AgroColab = (window.AgroColab = window.AgroColab || {});
  const { api, ui, auth, config } = AgroColab;

  let arbolesAgricultor = [];

  /* ---------- Renderizar lista de árboles ---------- */

  function renderizarListaArboles() {
    const container = document.getElementById("lista-arboles-agricultor");

    if (!arbolesAgricultor.length) {
      container.innerHTML = '<p class="text-stone-500 text-sm text-center py-8">No has publicado árboles todavía</p>';
      return;
    }

    container.innerHTML = arbolesAgricultor
      .map(function (arbol) {
        const cuposLibres = arbol.cupos_totales - arbol.cupos_ocupados;
        return `
        <div class="p-5 flex flex-col sm:flex-row sm:items-center gap-4">
          <div class="w-16 h-16 rounded-xl overflow-hidden bg-stone-200 flex-shrink-0">
            <img src="${arbol.imagen || "https://via.placeholder.com/150?text=Árbol"}" alt="${arbol.nombre}" class="w-full h-full object-cover">
          </div>
          <div class="flex-1">
            <div class="flex items-center gap-2 mb-1">
              <h4 class="font-bold text-stone-900">${arbol.nombre}</h4>
              <span class="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${arbol.tipo_suscripcion === "Exclusivo" ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-800"}">${arbol.tipo_suscripcion}</span>
            </div>
            <p class="text-xs text-stone-500 mb-1"><i class="fa-solid fa-location-dot text-rose-500 mr-1"></i>${arbol.ubicacion}</p>
            <p class="text-xs text-stone-500">Plan: <strong>${arbol.plan}</strong> · Cupos: <strong>${arbol.cupos_ocupados}/${arbol.cupos_totales}</strong> · <span class="${cuposLibres > 0 ? "text-emerald-600" : "text-red-500"}">${cuposLibres > 0 ? cuposLibres + " libres" : "Completo"}</span></p>
          </div>
          <div class="text-right">
            <p class="font-black text-emerald-900">${ui.formatearMonto(arbol.precio_mensual_clp)}</p>
            <p class="text-[10px] text-stone-400">CLP / mes</p>
            <div class="mt-2 flex gap-2 justify-end">
              <button type="button" onclick="AgroColab.agricultor.abrirEdicion(${arbol.id})" class="text-emerald-600 hover:text-emerald-800 text-xs font-bold flex items-center gap-1">
                <i class="fa-solid fa-pen"></i> Editar
              </button>
              <button type="button" onclick="AgroColab.agricultor.eliminarArbol(${arbol.id})" class="text-red-500 hover:text-red-700 text-xs font-bold flex items-center gap-1">
                <i class="fa-solid fa-trash"></i> Eliminar
              </button>
            </div>
          </div>
        </div>
      `;
      })
      .join("");
  }

  /* ---------- Editar árbol ---------- */

  function abrirEdicion(arbolId) {
    const arbol = arbolesAgricultor.find(a => a.id === arbolId);
    if (!arbol) return;

    document.getElementById("editar-arbol-id").value = arbol.id;
    document.getElementById("editar-nombre").value = arbol.nombre;
    document.getElementById("editar-ubicacion").value = arbol.ubicacion;
    document.getElementById("editar-plan").value = arbol.plan;
    document.getElementById("editar-tipo").value = arbol.tipo_suscripcion;
    document.getElementById("editar-cupos").value = arbol.cupos_totales;
    document.getElementById("editar-precio").value = arbol.precio_mensual_clp;
    document.getElementById("editar-cosecha").value = arbol.estimacion_cosecha;
    document.getElementById("editar-imagen").value = arbol.imagen || "";

    document.getElementById("modal-editar-arbol").classList.remove("hidden");
  }

  function cerrarEdicion() {
    document.getElementById("modal-editar-arbol").classList.add("hidden");
  }

  async function guardarEdicion(evento) {
    evento.preventDefault();

    const alerta = document.getElementById("alerta-editar-arbol");
    const arbolId = Number(document.getElementById("editar-arbol-id").value);

    const bodyData = {
      nombre: document.getElementById("editar-nombre").value.trim(),
      ubicacion: document.getElementById("editar-ubicacion").value.trim(),
      plan: document.getElementById("editar-plan").value,
      tipo_suscripcion: document.getElementById("editar-tipo").value,
      cupos_totales: Number(document.getElementById("editar-cupos").value),
      precio_mensual_clp: Number(document.getElementById("editar-precio").value),
      estimacion_cosecha: document.getElementById("editar-cosecha").value.trim(),
      imagen: document.getElementById("editar-imagen").value.trim() || "https://via.placeholder.com/150?text=Árbol",
      productor: auth.leerSesion().nombre
    };

    if (!bodyData.nombre || !bodyData.ubicacion || !bodyData.estimacion_cosecha) {
      ui.mostrarAlerta(alerta, "error", "Completa todos los campos obligatorios.");
      return;
    }

    try {
      const data = await api.actualizarArbol(arbolId, bodyData);
      if (data.status === "success") {
        ui.mostrarAlerta(alerta, "exito", data.mensaje);
        setTimeout(function() {
          cerrarEdicion();
          cargarArbolesAgricultor();
        }, 1500);
      } else {
        ui.mostrarAlerta(alerta, "error", data.mensaje || "No se pudo actualizar el árbol.");
      }
    } catch (error) {
      ui.mostrarAlerta(alerta, "error", "Error de comunicación con el backend.");
    }
  }

  /* ---------- Eliminar árbol ---------- */

  async function eliminarArbol(arbolId) {
    if (!window.confirm("¿Estás seguro de eliminar este árbol? Esta acción no se puede deshacer.")) {
      return;
    }

    try {
      const data = await api.eliminarArbol(arbolId);
      if (data.status === "success") {
        window.alert(data.mensaje);
        cargarArbolesAgricultor();
      } else {
        window.alert(data.mensaje || "No se pudo eliminar el árbol.");
      }
    } catch (error) {
      window.alert("Error de comunicación con el backend.");
    }
  }

  /* ---------- Estadísticas del dashboard ---------- */

  function actualizarEstadisticas() {
    const totalArboles = arbolesAgricultor.length;
    const totalSuscriptores = arbolesAgricultor.reduce(function (suma, a) {
      return suma + a.cupos_ocupados;
    }, 0);
    const ingresos = arbolesAgricultor.reduce(function (suma, a) {
      return suma + a.precio_mensual_clp * a.cupos_ocupados;
    }, 0);

    document.getElementById("stat-total-arboles").textContent = totalArboles;
    document.getElementById("stat-suscriptores").textContent = totalSuscriptores;
    document.getElementById("stat-ingresos").textContent = ui.formatearMonto(ingresos);
  }

  /* ---------- Cargar árboles del agricultor ---------- */

  async function cargarArbolesAgricultor() {
    const container = document.getElementById("lista-arboles-agricultor");
    container.innerHTML = '<p class="text-stone-500 text-sm text-center py-8">Cargando tus árboles...</p>';

    try {
      const arboles = await api.obtenerArboles();
      const sesion = auth.leerSesion();
      arbolesAgricultor = sesion
        ? arboles.filter(function (a) {
            return a.productor === sesion.nombre;
          })
        : [];

      renderizarListaArboles();
      actualizarEstadisticas();
    } catch (error) {
      container.innerHTML = '<p class="text-red-500 text-sm text-center py-8">Error al cargar tus árboles</p>';
    }
  }

  /* ---------- Formulario de subida de árbol ---------- */

  function mostrarFormulario() {
    document.getElementById("dashboard-agricultor").classList.add("hidden");
    document.getElementById("formulario-arbol").classList.remove("hidden");
  }

  function mostrarDashboard() {
    document.getElementById("formulario-arbol").classList.add("hidden");
    document.getElementById("dashboard-agricultor").classList.remove("hidden");
  }

  function leerImagenBase64(archivo) {
    return new Promise(function(resolve, reject) {
      const lector = new FileReader();
      lector.onload = function(e) {
        resolve(e.target.result);
      };
      lector.onerror = function(e) {
        reject(e);
      };
      lector.readAsDataURL(archivo);
    });
  }

  async function subirArbol(evento) {
    evento.preventDefault();

    const alerta = document.getElementById("alerta-subir-arbol");
    const sesion = auth.leerSesion();

    if (!sesion) {
      ui.mostrarAlerta(alerta, "error", "Debes iniciar sesión para publicar un árbol.");
      return;
    }

    const archivoImagen = document.getElementById("arbol-imagen").files[0];
    let imagenBase64 = "https://via.placeholder.com/150?text=Árbol";

    if (archivoImagen) {
      if (archivoImagen.size > 2 * 1024 * 1024) {
        ui.mostrarAlerta(alerta, "error", "La imagen no puede superar 2MB.");
        return;
      }
      try {
        imagenBase64 = await leerImagenBase64(archivoImagen);
      } catch (error) {
        ui.mostrarAlerta(alerta, "error", "No se pudo leer la imagen.");
        return;
      }
    }

    const bodyData = {
      nombre: document.getElementById("arbol-nombre").value.trim(),
      ubicacion: document.getElementById("arbol-ubicacion").value.trim(),
      plan: document.getElementById("arbol-plan").value,
      tipo_suscripcion: document.getElementById("arbol-tipo").value,
      cupos_totales: Number(document.getElementById("arbol-cupos").value),
      precio_mensual_clp: Number(document.getElementById("arbol-precio").value),
      estimacion_cosecha: document.getElementById("arbol-cosecha").value.trim(),
      imagen: imagenBase64,
      productor: sesion.nombre
    };

    if (!bodyData.nombre || !bodyData.ubicacion || !bodyData.estimacion_cosecha) {
      ui.mostrarAlerta(alerta, "error", "Completa todos los campos obligatorios.");
      return;
    }

    ui.mostrarAlerta(alerta, "info", "Publicando árbol...");

    try {
      const data = await api.subirArbol(bodyData);

      if (data.status === "success") {
        ui.mostrarAlerta(alerta, "exito", data.mensaje || "Árbol publicado correctamente.");
        document.getElementById("form-subir-arbol").reset();
        setTimeout(function () {
          mostrarDashboard();
          cargarArbolesAgricultor();
        }, 1500);
      } else {
        ui.mostrarAlerta(alerta, "error", data.mensaje || "No se pudo publicar el árbol.");
      }
    } catch (error) {
      ui.mostrarAlerta(alerta, "error", "Error de comunicación con el backend.");
    }
  }

  /* ---------- Inicialización ---------- */

  function pintarNavbarAgricultor() {
    const sesion = auth.leerSesion();
    const contenedor = document.getElementById("nav-sesion-agricultor");
    if (!contenedor || !sesion) return;

    contenedor.innerHTML = `
      <span class="nav-chip nav-chip--clickeable" onclick="AgroColab.perfil.abrir()" title="Ver mi perfil">
        <span class="hidden sm:inline font-bold text-white">${sesion.nombre}</span>
        <span class="text-emerald-400 font-black uppercase">${sesion.rol}</span>
        <i class="fa-solid fa-tractor"></i>
      </span>`;
  }

  function init() {
    document.getElementById("btn-subir-arbol").addEventListener("click", mostrarFormulario);
    document.getElementById("btn-cancelar-arbol").addEventListener("click", mostrarDashboard);
    document.getElementById("form-subir-arbol").addEventListener("submit", subirArbol);
    document.getElementById("form-editar-arbol").addEventListener("submit", guardarEdicion);
    document.getElementById("btn-cerrar-sesion-agricultor").addEventListener("click", function () {
      auth.eliminarSesion();
      window.AgroColab.views.mostrarVista(config.VISTA_SIN_SESION);
    });
    pintarNavbarAgricultor();
  }

  function cargar() {
    return cargarArbolesAgricultor();
  }

  AgroColab.agricultor = { init, cargar, eliminarArbol, abrirEdicion, cerrarEdicion };
})();
