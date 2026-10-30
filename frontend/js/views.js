/* Agro-Colab - Router de vistas. Servicio orientado a objetos (ViewsService)
   con instancia expuesta como AgroColab.views. Todo ocurre en el mismo documento
   HTML: mostrar u ocultar la vista indicada, sin recargas ni navegaciones. */

(function () {
  const AgroColab = (window.AgroColab = window.AgroColab || {});
  // Escapa datos antes de insertarlos como HTML (ver ui.escapar)
  const e = (valor) => window.AgroColab.ui.escapar(valor);
  const { auth, config } = AgroColab;

  class ViewsService {
    constructor() {
      this.config = config;
      this.vistas = {
        login: {
          selector: "#vista-login",
          requiereSesion: false
        },
        parcelas: {
          selector: "#vista-parcelas",
          requiereSesion: true,
          roles: ["comprador"],
          alMostrar: () => AgroColab.parcelas.cargar()
        },
        "dashboard-comprador": {
          selector: "#vista-dashboard-comprador",
          requiereSesion: true,
          roles: ["comprador"],
          alMostrar: () => AgroColab.dashboard.cargar()
        },
        agricultor: {
          selector: "#vista-agricultor",
          requiereSesion: true,
          roles: ["agricultor"],
          alMostrar: () => AgroColab.agricultor.cargar()
        }
      };
      this.vistaActual = null;
    }

    elementos() {
      return Array.from(document.querySelectorAll("[data-vista]"));
    }

    mostrarVista(nombre) {
      const vista = this.vistas[nombre];

      if (!vista) {
        console.error(`Agro-Colab: vista desconocida "${nombre}"`);
        return false;
      }

      const sesion = auth.leerSesion();

      /* Guard: la vista pide sesión y no la hay, o el rol no tiene acceso. */
      const sinAcceso =
        (vista.requiereSesion && !sesion) || (sesion && vista.roles && !vista.roles.includes(sesion.rol));

      if (sinAcceso) {
        if (nombre === config.VISTA_SIN_SESION) return false;
        return this.mostrarVista(config.VISTA_SIN_SESION);
      }

      document.querySelectorAll("[data-vista]").forEach((elemento) => {
        elemento.classList.toggle("hidden", elemento.dataset.vista !== nombre);
      });

      /* Cerrar cualquier modal abierto antes de cambiar de vista. */
      try {
        if (document.getElementById("modal-canasta")) AgroColab.parcelas.cerrarCanasta();
        if (document.getElementById("modal-logistica")) AgroColab.parcelas.cerrarLogistica();
        if (document.getElementById("modal-confirmacion-adopcion")) AgroColab.parcelas.cerrarModalConfirmacionArbol();
      } catch (error) { /* los modales son opcionales según la vista */ }

      this.vistaActual = nombre;
      if (nombre !== config.VISTA_SIN_SESION) auth.guardarVista(nombre);
      window.scrollTo({ top: 0, behavior: "auto" });

      if (vista.alMostrar) vista.alMostrar();
      return true;
    }

    mostrarVistaPorRol(rol) {
      return this.mostrarVista(config.VISTAS_POR_ROL[rol] || config.VISTA_SIN_SESION);
    }

    vistaInicial() {
      const sesion = auth.leerSesion();
      if (!sesion) return config.VISTA_SIN_SESION;

      // Si la pestaña venía de otra vista permitida para el rol, se vuelve a ella
      const anterior = auth.leerVista();
      const vista = anterior && this.vistas[anterior];
      if (vista && (!vista.roles || vista.roles.includes(sesion.rol))) return anterior;

      return config.VISTAS_POR_ROL[sesion.rol] || config.VISTA_SIN_SESION;
    }

    /* Pinta el usuario en todos los headers (catálogo, panel y agricultor).
       Antes se buscaba un único id repetido en dos vistas y el panel del
       comprador quedaba vacío. */
    pintarNavbar() {
      const sesion = auth.leerSesion();
      const contenedores = document.querySelectorAll("[data-nav-sesion]");
      if (!sesion) {
        contenedores.forEach((contenedor) => (contenedor.innerHTML = ""));
        return;
      }

      const inicial = (sesion.nombre || "?").trim().charAt(0).toUpperCase();
      contenedores.forEach((contenedor) => {
        contenedor.innerHTML = `
          <button type="button" class="nav-usuario" data-accion="perfil.abrir" title="Ver mi perfil">
            <span class="nav-usuario__avatar">${e(inicial)}</span>
            <span class="hidden md:flex flex-col text-left leading-tight">
              <span class="text-xs font-bold text-white">${e(sesion.nombre)}</span>
              <span class="text-[10px] text-emerald-300 capitalize">${e(sesion.rol)}</span>
            </span>
          </button>`;
      });
    }

    cerrarSesion() {
      auth.eliminarSesion();
      if (AgroColab.parcelas) AgroColab.parcelas.vaciarCarrito();
      this.mostrarVista(config.VISTA_SIN_SESION);
    }

    init() {
      document.querySelectorAll("[data-cerrar-sesion]").forEach((boton) => {
        boton.addEventListener("click", () => this.cerrarSesion());
      });
      this.pintarNavbar();
    }
  }

  const viewsService = new ViewsService();
  window.AgroColab.views = viewsService;
})();
