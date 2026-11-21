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
      // Render puede estar dormido: se lo despierta antes de que haga falta
      window.AgroColab.api.despertarServidor();
      this.acciones.init();

      /* Cada módulo arranca por separado: si uno falla, el resto de la
         aplicación sigue funcionando y el error queda en la consola. */
      const modulos = {
        parcelas: this.parcelas, agricultor: this.agricultor, perfil: this.perfil,
        login: this.login, autocomplete: this.autocomplete, dashboard: this.dashboard,
        pago: window.AgroColab.pago, recuperacion: window.AgroColab.recuperacion,
        admin: window.AgroColab.admin, views: this.views, efectos: this.efectos,
        constelacion: this.constelacion
      };
      Object.entries(modulos).forEach(([nombre, modulo]) => {
        try {
          modulo.init();
        } catch (error) {
          console.error(`[Agro-Colab] El módulo "${nombre}" no pudo iniciar:`, error);
        }
      });

      this.views.mostrarVista(this.views.vistaInicial());
    });
  }
}

/* Última red: una promesa rechazada que nadie atendió. Se registra siempre y
   se avisa al usuario como máximo una vez cada 10 segundos, para no tapar la
   pantalla de diálogos si el error se repite. */
let ultimoAvisoGlobal = 0;
window.addEventListener("unhandledrejection", (evento) => {
  console.error("[Agro-Colab] Error sin manejar:", evento.reason);
  const ahora = Date.now();
  if (ahora - ultimoAvisoGlobal < 10000 || !window.AgroColab.dialogo) return;
  ultimoAvisoGlobal = ahora;
  const ErrorDeConexion = window.AgroColab.ErrorDeConexion;
  const conexion = Boolean(ErrorDeConexion) && evento.reason instanceof ErrorDeConexion;
  window.AgroColab.dialogo.avisar(
    conexion ? evento.reason.message : "Algo salió mal. Si el problema continúa, recarga la página.",
    { tipo: "error" }
  );
});

const appService = new AppService();
window.AgroColab.app = appService;

/* Sin esta llamada no se conectaba ningún evento (carro, filtros, salir,
   formularios) ni se restauraba la sesión al recargar la página. */
appService.init();
