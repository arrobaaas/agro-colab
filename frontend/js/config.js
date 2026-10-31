/* Agro-Colab - Servicio de configuración global del frontend. */

var AgroColab = window.AgroColab || {};

class ConfigService {
  constructor() {
    this.API_URL = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
      ? "http://127.0.0.1:8000/api"
      : "https://agro-colab.onrender.com/api";

    this.claveSesion = "agrocolab_sesion";
    this.clavePlan = "agrocolab_plan";
    this.claveCarrito = "agrocolab_carrito";
    this.claveVista = "agrocolab_vista";

    /* Vista que se muestra cuando no hay sesión o el rol no tiene acceso. */
    this.VISTA_SIN_SESION = "login";

    /* Vista que ve cada rol.
       Por ahora comprador y agricultor comparten la vista de parcelas.
       Cuando exista la vista del productor, se separa aquí:
         comprador: "parcelas",
         agricultor: "mis-parcelas" */
    this.VISTAS_POR_ROL = {
      comprador: "parcelas",
      agricultor: "agricultor",
      administrador: "admin"
    };
  }
}

const configService = new ConfigService();
window.AgroColab.config = configService;
