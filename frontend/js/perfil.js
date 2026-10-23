/* Agro-Colab - Modal de perfil de usuario: ver y editar información
   personal (nombre, correo, teléfono, dirección, contraseña) y consultar
   los árboles que el usuario tiene adoptados. */

(function () {
  const AgroColab = (window.AgroColab = window.AgroColab || {});
  const { auth, ui } = AgroColab;

  function abrir() {
    const sesion = auth.leerSesion();
    if (!sesion) return;

    document.getElementById("perfil-nombre").textContent = sesion.nombre;
    document.getElementById("perfil-rol").textContent = sesion.rol;
    document.getElementById("perfil-input-nombre").value = sesion.nombre || "";
    document.getElementById("perfil-input-email").value = sesion.email || "";
    document.getElementById("perfil-input-telefono").value = sesion.telefono || "";
    document.getElementById("perfil-input-direccion").value = sesion.direccion || "";
    document.getElementById("perfil-input-password").value = "";

    document.getElementById("modal-perfil").classList.remove("hidden");
    cargarMisArboles();
  }

  /* ---------- Árboles adoptados ---------- */

  function pintarMisArboles(arboles) {
    const contenedor = document.getElementById("perfil-mis-arboles");
    if (!contenedor) return;

    if (!arboles.length) {
      contenedor.innerHTML =
        '<p class="text-stone-500 text-xs text-center py-6 bg-stone-50 rounded-xl border border-stone-200">' +
        "Todavía no has adoptado ningún árbol. " +
        '<a href="#vista-parcelas" onclick="AgroColab.views.mostrarVista(\'parcelas\'); AgroColab.perfil.cerrar(); return false;" class="text-emerald-700 font-bold underline">Ver los árboles disponibles</a>' +
        "</p>";
      return;
    }

    contenedor.innerHTML = arboles
      .map(function (arbol) {
        return `
          <div class="flex items-center gap-3 p-3 bg-stone-50 rounded-xl border border-stone-200">
            <div class="w-14 h-14 rounded-lg overflow-hidden bg-stone-200 flex-shrink-0">
              <img src="${arbol.imagen}" alt="${arbol.nombre}" class="w-full h-full object-cover">
            </div>
            <div class="flex-1 min-w-0">
              <p class="font-bold text-sm text-stone-900 truncate">${arbol.nombre}</p>
              <p class="text-[11px] text-stone-500 truncate">
                <i class="fa-solid fa-location-dot text-rose-500 mr-1"></i>${arbol.ubicacion}
              </p>
              <p class="text-[11px] text-stone-500">
                Plan <strong>${arbol.plan}</strong> · Cosecha <strong>${arbol.estimacion_cosecha}</strong>
              </p>
            </div>
            <div class="text-right flex-shrink-0">
              <p class="font-black text-emerald-900 text-sm">${AgroColab.ui.formatearMonto(arbol.precio_mensual_clp)}</p>
              <p class="text-[10px] text-stone-400">CLP / mes</p>
              <p class="text-[10px] text-stone-500 mt-1">${arbol.cupos_ocupados}/${arbol.cupos_totales} copartícipes</p>
            </div>
          </div>`;
      })
      .join("");
  }

  async function cargarMisArboles() {
    const sesion = auth.leerSesion();
    const contenedor = document.getElementById("perfil-mis-arboles");
    if (!sesion || !contenedor) return;

    contenedor.innerHTML =
      '<p class="text-stone-500 text-xs text-center py-6">Cargando tus árboles...</p>';

    try {
      const data = await AgroColab.api.obtenerMisArboles(sesion.id);
      if (data && data.status === "success") {
        pintarMisArboles(data.arboles || []);
      } else {
        pintarMisArboles([]);
      }
    } catch (error) {
      contenedor.innerHTML =
        '<p class="text-red-500 text-xs text-center py-6">No se pudieron cargar tus árboles adoptados.</p>';
    }
  }

  function cerrar() {
    document.getElementById("modal-perfil").classList.add("hidden");
  }

  async function eliminarCuenta() {
    const sesion = auth.leerSesion();
    if (!sesion) return;

    if (!window.confirm("¿Estás seguro de eliminar tu cuenta? Esta acción es IRREVERSIBLE y borrará todos tus datos personales, suscripciones y pedidos.")) {
      return;
    }

    try {
      const data = await AgroColab.api.eliminarCuenta(sesion.email);
      if (data.status === "success") {
        window.alert(data.mensaje);
        auth.eliminarSesion();
        cerrar();
        window.AgroColab.views.mostrarVista("login");
      } else {
        window.alert(data.mensaje || "No se pudo eliminar la cuenta.");
      }
    } catch (error) {
      window.alert("Error de comunicación con el backend.");
    }
  }

  async function guardar(evento) {
    evento.preventDefault();

    const alerta = document.getElementById("alerta-perfil");
    const sesion = auth.leerSesion();
    if (!sesion) return;

    const nombre = document.getElementById("perfil-input-nombre").value.trim();
    const email = document.getElementById("perfil-input-email").value.trim();
    const telefono = document.getElementById("perfil-input-telefono").value.trim();
    const direccion = document.getElementById("perfil-input-direccion").value.trim();
    const password = document.getElementById("perfil-input-password").value;

    if (!nombre || !email) {
      ui.mostrarAlerta(alerta, "error", "Nombre y correo son obligatorios.");
      return;
    }

    const cambios = {
      nombre,
      email,
      telefono,
      direccion,
      password: password || undefined
    };

    try {
      const data = await AgroColab.api.actualizarPerfil(cambios);

      if (data.status === "success") {
        auth.guardarSesion(data.user);
        ui.mostrarAlerta(alerta, "exito", "Perfil actualizado correctamente.");
        setTimeout(cerrar, 1500);
      } else {
        ui.mostrarAlerta(alerta, "error", data.mensaje || "No se pudo actualizar el perfil.");
      }
    } catch (error) {
      ui.mostrarAlerta(alerta, "error", "Error de comunicación con el backend.");
    }
  }

  function init() {
    document.getElementById("form-perfil").addEventListener("submit", guardar);
  }

  AgroColab.perfil = { init, abrir, cerrar, eliminarCuenta };
})();
