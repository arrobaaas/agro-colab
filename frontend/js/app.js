/* Agro-Colab - Servicio de aplicación: punto de entrada. Decide qué vista se
   muestra al abrir la app: login si no hay sesión, o la vista del rol si ya
   estaba conectado. */

class AppService {
  constructor() {
    this.views = window.AgroColab.views;
    this.parcelas = window.AgroColab.parcelas;
    this.agricultor = window.AgroColab.agricultor;
    this.perfil = window.AgroColab.perfil;
    this.login = window.AgroColab.login;
    this.autocomplete = window.AgroColab.autocomplete;
    this.dashboard = window.AgroColab.dashboard;
  }

  init() {
    document.addEventListener("DOMContentLoaded", () => {
      this.parcelas.init();
      this.agricultor.init();
      this.perfil.init();
      this.login.init();
      this.autocomplete.init();
      this.dashboard.init();
      this.views.init();

      this.views.mostrarVista(this.views.vistaInicial());
    });
  }
}

const appService = new AppService();
window.AgroColab.app = appService;

/* Sin esta llamada no se conectaba ningún evento (carro, filtros, salir,
   formularios) ni se restauraba la sesión al recargar la página. */
appService.init();
