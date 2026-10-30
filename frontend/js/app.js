/* Agro-Colab - Servicio de aplicación: punto de entrada. Inicializa los
   servicios y muestra siempre el login al abrir la app. */

class AppService {
  constructor() {
    this.views = window.AgroColab.views;
    this.parcelas = window.AgroColab.parcelas;
    this.agricultor = window.AgroColab.agricultor;
    this.perfil = window.AgroColab.perfil;
    this.login = window.AgroColab.login;
    this.autocomplete = window.AgroColab.autocomplete;
    this.dashboard = window.AgroColab.dashboard;
    this.acciones = window.AgroColab.acciones;
    this.efectos = window.AgroColab.efectos;
  }

  init() {
    document.addEventListener("DOMContentLoaded", () => {
      /* Cada visita parte en el login: no se reutiliza una sesión guardada
         (por ejemplo, la de una cuenta de demostración que quedó abierta). */
      window.AgroColab.auth.eliminarSesion();
      this.acciones.init();

      this.parcelas.init();
      this.agricultor.init();
      this.perfil.init();
      this.login.init();
      this.autocomplete.init();
      this.dashboard.init();
      this.views.init();
      this.efectos.init();

      this.views.mostrarVista(this.views.vistaInicial());
    });
  }
}

const appService = new AppService();
window.AgroColab.app = appService;

/* Sin esta llamada no se conectaba ningún evento (carro, filtros, salir,
   formularios) ni se restauraba la sesión al recargar la página. */
appService.init();
