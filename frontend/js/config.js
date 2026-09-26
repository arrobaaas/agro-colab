/* Agro-Colab - Configuración global del frontend */

(function () {
  const AgroColab = (window.AgroColab = window.AgroColab || {});

  AgroColab.config = {
    API_URL: "http://127.0.0.1:8000/api",

    CLAVE_SESION: "agrocolab_sesion",
    CLAVE_PLAN: "agrocolab_plan",

    /* Vista que se muestra cuando no hay sesión o el rol no tiene acceso. */
    VISTA_SIN_SESION: "login",

    /* Vista que ve cada rol.
       Por ahora comprador y agricultor comparten la vista de parcelas.
       Cuando exista la vista del productor, se separa aquí:
         comprador: "parcelas",
         agricultor: "mis-parcelas" */
    VISTAS_POR_ROL: {
      comprador: "parcelas",
      agricultor: "parcelas"
    }
  };
})();
