/* Agro-Colab - Servicio del modal de perfil de usuario: ver y editar información
   personal (nombre, correo, teléfono, dirección, contraseña) y consultar
   los árboles que el usuario tiene adoptados. Servicio orientado a objetos
   (PerfilService) con instancia expuesta como AgroColab.perfil. */

(function () {
  // Escapa datos antes de insertarlos como HTML (ver ui.escapar)
  const e = (valor) => window.AgroColab.ui.escapar(valor);
  const AgroColab = (window.AgroColab = window.AgroColab || {});
  const { auth, ui } = AgroColab;

  class PerfilService {
    constructor() {
      this.auth = auth;
      this.ui = ui;
    }

    abrir() {
      const sesion = this.auth.leerSesion();
      if (!sesion) return;

      const esComprador = sesion.rol === "comprador";
      document.getElementById("perfil-nombre").textContent = sesion.nombre;
      document.getElementById("perfil-rol").textContent = esComprador ? "Comprador" : "Agricultor";
      document.getElementById("perfil-avatar").textContent = (sesion.nombre || "?").trim().charAt(0).toUpperCase();
      // Solo el comprador adopta árboles: al agricultor no se le muestra esa sección
      document.getElementById("perfil-seccion-arboles").classList.toggle("hidden", !esComprador);
      document.getElementById("perfil-input-nombre").value = sesion.nombre || "";
      document.getElementById("perfil-input-email").value = sesion.email || "";
      document.getElementById("perfil-input-telefono").value = sesion.telefono || "";
      document.getElementById("perfil-input-direccion").value = sesion.direccion || "";
      document.getElementById("perfil-input-password").value = "";
      document.getElementById("perfil-input-password-actual").value = "";

      document.getElementById("modal-perfil").classList.remove("hidden");
      if (esComprador) this.cargarMisArboles();
    }

    pintarMisArboles(arboles) {
      const contenedor = document.getElementById("perfil-mis-arboles");
      if (!contenedor) return;

      if (!arboles.length) {
        contenedor.innerHTML = `
          <p class="tc-cuerpo-sm">
            Todavía no has adoptado ningún árbol.
            <a href="#vista-parcelas" class="perfil-enlace" data-accion="views.mostrarVista:parcelas|perfil.cerrar">Ver árboles disponibles</a>
          </p>`;
        return;
      }

      contenedor.innerHTML = arboles
        .map((arbol) => `
          <div class="perfil-arbol">
            <div class="perfil-arbol__foto">
              <img src="${e(arbol.imagen || "")}" alt="${e(arbol.nombre)}" data-si-falla="ocultar">
            </div>
            <div class="perfil-arbol__texto">
              <p class="perfil-arbol__nombre">${e(arbol.nombre)}</p>
              <p class="tc-cuerpo-sm">Plan ${e(arbol.plan || "-")} · ${e(arbol.estimacion_cosecha || "-")}</p>
            </div>
            <p class="perfil-arbol__precio">${this.ui.formatearMonto(arbol.precio_mensual_clp)}<small>/ mes</small></p>
          </div>`)
        .join("");
    }

    async cargarMisArboles() {
      const sesion = this.auth.leerSesion();
      const contenedor = document.getElementById("perfil-mis-arboles");
      if (!sesion || !contenedor) return;

      contenedor.innerHTML = '<p class="tc-cuerpo-sm">Cargando tus árboles...</p>';

      try {
        const data = await window.AgroColab.api.obtenerMisArboles(sesion.id);
        if (data && data.status === "success") {
          this.pintarMisArboles(data.arboles || []);
        } else {
          this.pintarMisArboles([]);
        }
      } catch (error) {
        contenedor.innerHTML = '<p class="tc-cuerpo-sm">No se pudieron cargar tus árboles adoptados.</p>';
      }
    }

    cerrar() {
      document.getElementById("modal-perfil").classList.add("hidden");
    }

    async eliminarCuenta() {
      const sesion = this.auth.leerSesion();
      if (!sesion) return;

      if (!(await AgroColab.dialogo.confirmar("Se borrarán para siempre tus datos personales, tus adopciones y tus pedidos. Esta acción no se puede deshacer.", { titulo: "¿Eliminar tu cuenta?", aceptar: "Eliminar mi cuenta", peligro: true }))) {
        return;
      }

      try {
        const data = await window.AgroColab.api.eliminarCuenta(sesion.email);
        if (data.status === "success") {
          AgroColab.dialogo.avisar(data.mensaje, { tipo: "exito", titulo: "Cuenta eliminada" });
          this.auth.eliminarSesion();
          this.cerrar();
          window.AgroColab.views.mostrarVista("login");
        } else {
          AgroColab.dialogo.avisar(data.mensaje || "No se pudo eliminar la cuenta.", { tipo: "error" });
        }
      } catch (error) {
        AgroColab.dialogo.avisar("No hay conexión con el servidor. Intenta nuevamente en unos segundos.", { tipo: "error" });
      }
    }

    async guardar(evento) {
      evento.preventDefault();

      const alerta = document.getElementById("alerta-perfil");
      const sesion = this.auth.leerSesion();
      if (!sesion) return;

      const nombre = document.getElementById("perfil-input-nombre").value.trim();
      const email = document.getElementById("perfil-input-email").value.trim();
      const telefono = document.getElementById("perfil-input-telefono").value.trim();
      const direccion = document.getElementById("perfil-input-direccion").value.trim();
      const password = document.getElementById("perfil-input-password").value;

      if (!nombre || !email) {
        this.ui.mostrarAlerta(alerta, "error", "Nombre y correo son obligatorios.");
        return;
      }

      const cambios = {
        nombre,
        email,
        telefono,
        direccion,
        password: password || undefined,
        password_actual: document.getElementById("perfil-input-password-actual").value || undefined
      };

      try {
        const data = await window.AgroColab.api.actualizarPerfil(cambios);

        if (data.status === "success") {
          this.auth.guardarSesion(data.user);
          window.AgroColab.views.pintarNavbar();
          this.ui.mostrarAlerta(alerta, "exito", "Perfil actualizado correctamente.");
          setTimeout(() => this.cerrar(), 1500);
        } else {
          this.ui.mostrarAlerta(alerta, "error", data.mensaje || "No se pudo actualizar el perfil.");
        }
      } catch (error) {
        this.ui.mostrarAlerta(alerta, "error", "Error de comunicación con el backend.");
      }
    }

    init() {
      document.getElementById("form-perfil").addEventListener("submit", (evento) => this.guardar(evento));
    }
  }

  const perfilService = new PerfilService();
  window.AgroColab.perfil = perfilService;
})();
