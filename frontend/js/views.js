/* Agro-Colab - Router de vistas. Servicio orientado a objetos (ViewsService)
   con instancia expuesta como AgroColab.views. Todo ocurre en el mismo documento
   HTML: mostrar u ocultar la vista indicada, sin recargas ni navegaciones. */

(function () {
  const AgroColab = (window.AgroColab = window.AgroColab || {});
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
      window.scrollTo({ top: 0, behavior: "auto" });

      if (vista.alMostrar) vista.alMostrar();
      return true;
    }

    mostrarVistaPorRol(rol) {
      return this.mostrarVista(config.VISTAS_POR_ROL[rol] || config.VISTA_SIN_SESION);
    }

    vistaInicial() {
      const sesion = auth.leerSesion();
      return sesion ? config.VISTAS_POR_ROL[sesion.rol] || config.VISTA_SIN_SESION : config.VISTA_SIN_SESION;
    }

    pintarNavbar() {
      const sesion = auth.leerSesion();
      const contenedor = document.getElementById("nav-sesion");
      if (!contenedor || !sesion) return;

      const icono = sesion.rol === "agricultor" ? "fa-solid fa-tractor" : "fa-solid fa-user";
      contenedor.innerHTML = `
        <span class="nav-chip nav-chip--clickeable" onclick="AgroColab.perfil.abrir()" title="Ver mi perfil">
          <span class="hidden sm:inline font-bold text-white">${sesion.nombre}</span>
          <span class="text-emerald-400 font-black uppercase">${sesion.rol}</span>
          <i class="${icono}"></i>
        </span>`;
    }

    cerrarSesion() {
      auth.eliminarSesion();
      this.mostrarVista(config.VISTA_SIN_SESION);
    }

    init() {
      document.getElementById("btn-cerrar-sesion").addEventListener("click", () => this.cerrarSesion());
      this.pintarNavbar();
    }
  }

  const viewsService = new ViewsService();
  window.AgroColab.views = viewsService;
})();
