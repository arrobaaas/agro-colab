/* Agro-Colab - Router de vistas. Todo ocurre en el mismo documento HTML:
   mostrar u ocultar la vista indicada, sin recargas ni navegaciones. */

(function () {
  const AgroColab = (window.AgroColab = window.AgroColab || {});
  const { auth, config } = AgroColab;

  /* Registro de vistas. "alMostrar" se ejecuta cada vez que la vista entra
     en pantalla (carga de datos, por ejemplo). */
  const VISTAS = {
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
    agricultor: {
      selector: "#vista-agricultor",
      requiereSesion: true,
      roles: ["agricultor"],
      alMostrar: () => AgroColab.agricultor.cargar()
    }
  };

  let vistaActual = null;

  function elementos() {
    return Array.from(document.querySelectorAll("[data-vista]"));
  }

  function mostrarVista(nombre) {
    const vista = VISTAS[nombre];

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
      return mostrarVista(config.VISTA_SIN_SESION);
    }

    elementos().forEach(function (elemento) {
      elemento.classList.toggle("hidden", elemento.dataset.vista !== nombre);
    });

    vistaActual = nombre;
    window.scrollTo({ top: 0, behavior: "auto" });

    if (vista.alMostrar) vista.alMostrar();
    return true;
  }

  function mostrarVistaPorRol(rol) {
    return mostrarVista(config.VISTAS_POR_ROL[rol] || config.VISTA_SIN_SESION);
  }

  /* Sin sesión se ve el login; con sesión, la vista de su rol. */
  function vistaInicial() {
    const sesion = auth.leerSesion();
    return sesion ? config.VISTAS_POR_ROL[sesion.rol] || config.VISTA_SIN_SESION : config.VISTA_SIN_SESION;
  }

  function pintarNavbar() {
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

  function cerrarSesion() {
    auth.eliminarSesion();
    mostrarVista(config.VISTA_SIN_SESION);
  }

  function init() {
    document.getElementById("btn-cerrar-sesion").addEventListener("click", cerrarSesion);
    pintarNavbar();
  }

  AgroColab.views = {
    VISTAS,
    init,
    mostrarVista,
    mostrarVistaPorRol,
    vistaInicial,
    pintarNavbar,
    cerrarSesion,
    get actual() {
      return vistaActual;
    }
  };
})();
