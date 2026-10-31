/* Agro-Colab - Servicio de aplicación: punto de entrada. Inicializa los
   servicios y muestra el login, o la vista del rol si la pestaña ya tenía
   una sesión abierta. */

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
    this.constelacion = window.AgroColab.constelacion;
    this.efectos = window.AgroColab.efectos;
  }

  init() {
    document.addEventListener("DOMContentLoaded", () => {
      /* La sesión dura lo que dure la pestaña (ver auth.js): una visita
         nueva parte en el login, pero ir a Privacidad y volver no la cierra */
      window.AgroColab.auth.limpiarSesionAntigua();
      this.acciones.init();

      this.parcelas.init();
      this.agricultor.init();
      this.perfil.init();
      this.login.init();
      this.autocomplete.init();
      this.dashboard.init();
      window.AgroColab.pago.init();
      window.AgroColab.recuperacion.init();
      window.AgroColab.admin.init();
      this.views.init();
      this.efectos.init();
      this.constelacion.init();

      this.views.mostrarVista(this.views.vistaInicial());
    });
  }
}

const appService = new AppService();
window.AgroColab.app = appService;

/* Sin esta llamada no se conectaba ningún evento (carro, filtros, salir,
   formularios) ni se restauraba la sesión al recargar la página. */
appService.init();
