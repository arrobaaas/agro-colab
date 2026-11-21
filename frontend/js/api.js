/* Agro-Colab - Capa de comunicación con el backend (FastAPI).
   Servicio orientado a objetos: ApiService con instancia expuesta como
   AgroColab.api para mantener la interfaz usada por el resto de la app. */

var AgroColab = window.AgroColab || {};

/* Error de red o de tiempo: el servidor nunca respondió. Su mensaje ya está
   en lenguaje de usuario y se puede mostrar tal cual. */
class ErrorDeConexion extends Error {
  constructor(mensaje) {
    super(mensaje);
    this.name = "ErrorDeConexion";
  }
}
window.AgroColab.ErrorDeConexion = ErrorDeConexion;

/* Aviso de arranque en frío. En el plan gratuito de Render el servidor se
   duerme tras 15 minutos sin tráfico y la primera petición tarda hasta un
   minuto. Si alguna petición lleva más de RETARDO_MS sin respuesta, se muestra
   un aviso arriba de la pantalla, y se quita cuando terminan todas las lentas.
   Las peticiones rápidas nunca lo muestran. */
class AvisoServidorDespertando {
  constructor() {
    this.RETARDO_MS = 3500;
    this.lentas = 0;
    this.elemento = null;
  }

  /* Se llama al iniciar una petición; devuelve la función que la termina */
  empezar() {
    let contada = false;
    const temporizador = setTimeout(() => {
      contada = true;
      this.lentas += 1;
      this.actualizar();
    }, this.RETARDO_MS);
    return () => {
      clearTimeout(temporizador);
      if (contada) {
        this.lentas -= 1;
        this.actualizar();
      }
    };
  }

  crear() {
    const aviso = document.createElement("div");
    aviso.className = "aviso-servidor";
    aviso.setAttribute("role", "status");
    aviso.setAttribute("aria-live", "polite");
    aviso.hidden = true;

    const icono = document.createElement("i");
    icono.className = "fa-solid fa-circle-notch aviso-servidor__icono";
    icono.setAttribute("aria-hidden", "true");

    const texto = document.createElement("p");
    const titulo = document.createElement("strong");
    titulo.textContent = "Despertando el servidor…";
    texto.append(titulo, " Si es la primera visita en un rato, puede tardar hasta un minuto. No cierres la página.");

    aviso.append(icono, texto);
    document.body.appendChild(aviso);
    return aviso;
  }

  actualizar() {
    if (!document.body) return;
    if (!this.elemento) this.elemento = this.crear();
    this.elemento.hidden = this.lentas <= 0;
  }
}

class ApiService {
  constructor() {
    this.config = window.AgroColab.config;
    /* Render despierta en hasta un minuto tras estar inactivo: se espera un
       poco más que eso antes de rendirse, para no cortar un arranque normal. */
    this.TIEMPO_LIMITE_MS = 75000;
    this.avisoDespertando = new AvisoServidorDespertando();
  }

  /* Al abrir la página se despierta el servidor en segundo plano, mientras la
     persona lee la portada o escribe su correo: así el inicio de sesión no
     carga con la espera completa. Un fallo aquí no se muestra; la próxima
     petición real informará si el servidor sigue sin responder. */
  despertarServidor() {
    return this.apiFetch("/estado").catch(() => null);
  }

  /* El token ya no vale (venció o se cerró la sesión desde otro lado). Se
     borra la sesión local y se vuelve al inicio de sesión; quien llamó
     recibe igual la respuesta y muestra el mensaje del servidor. */
  sesionVencida() {
    const { auth, views, parcelas, config } = window.AgroColab;
    if (auth) auth.eliminarSesion();
    if (parcelas && parcelas.vaciarCarrito) parcelas.vaciarCarrito();
    if (views && views.mostrarVista) views.mostrarVista(config.VISTA_SIN_SESION);
  }

  async apiFetch(ruta, opciones = {}) {
    const headers = { "Content-Type": "application/json" };
    const sesion = window.AgroColab.auth ? window.AgroColab.auth.leerSesion() : null;
    if (sesion && sesion.token) {
      headers.Authorization = `Bearer ${sesion.token}`;
    }

    const controlador = new AbortController();
    const limite = setTimeout(() => controlador.abort(), this.TIEMPO_LIMITE_MS);
    const terminarAviso = this.avisoDespertando.empezar();
    let respuesta;
    let cuerpo = null;
    try {
      respuesta = await fetch(`${this.config.API_URL}${ruta}`, {
        ...opciones,
        headers,
        signal: controlador.signal
      });
      try {
        cuerpo = await respuesta.json();
      } catch (error) {
        cuerpo = null;
      }
    } catch (error) {
      /* fetch solo falla así cuando no hubo respuesta: sin red, servidor
         caído, CORS o tiempo agotado. Un 4xx o 5xx sí es una respuesta. */
      console.error(`[Agro-Colab] ${opciones.method || "GET"} ${ruta} no respondió:`, error);
      if (error.name === "AbortError") {
        throw new ErrorDeConexion("El servidor tardó demasiado en responder. Si es la primera visita del día, puede estar despertando: espera un momento e intenta nuevamente.");
      }
      throw new ErrorDeConexion("No hay conexión con el servidor. Revisa tu conexión a internet e intenta nuevamente.");
    } finally {
      clearTimeout(limite);
      terminarAviso();
    }

    // Solo cuenta como sesión vencida si se envió un token: en el login, un
    // 401 significa credenciales incorrectas
    if (respuesta.status === 401 && headers.Authorization && !/^\/(login|logout)\b/.test(ruta)) {
      this.sesionVencida();
    }

    /* Si la respuesta no es JSON (un 500 del servidor, una página de
       mantenimiento, etc.) se avisa con el código real en vez de un
       genérico "error de conexión". */
    if (cuerpo === null) {
      /* El código real queda en la consola; al usuario se le habla en su idioma */
      console.error(`[Agro-Colab] ${opciones.method || "GET"} ${ruta} respondió ${respuesta.status} sin JSON`);
      if (respuesta.ok) {
        throw new Error("Recibimos una respuesta que no esperábamos. Recarga la página e intenta nuevamente.");
      }
      throw new Error("El servidor tuvo un problema y no pudo completar la operación. Espera un momento e inténtalo de nuevo.");
    }

    /* Éxitos y errores traen status y mensaje en el cuerpo, con su código HTTP
       correcto (400, 401, 403, 404, 409, 422...). El resto de la app lee status. */
    return cuerpo;
  }

  login(email, password, rol) {
    return this.apiFetch("/login", {
      method: "POST",
      body: JSON.stringify({ email, password, rol })
    });
  }

  obtenerArboles() {
    return this.apiFetch("/arboles");
  }

  obtenerEspecies() {
    return this.apiFetch("/especies");
  }

  /* El usuario se identifica con el token de sesión (ver apiFetch); el
     parámetro sesion se mantiene por compatibilidad con quienes llaman. */
  /* Pasarela simulada: si el pago de un árbol se aprueba, el servidor
     confirma la adopción en la misma operación */
  pagar(datos) {
    return this.apiFetch("/pagos", { method: "POST", body: JSON.stringify(datos) });
  }

  /* Un solo cobro para toda la canasta: todo o nada */
  pagarCanasta(datos) {
    return this.apiFetch("/pagos/canasta", { method: "POST", body: JSON.stringify(datos) });
  }

  obtenerPagos() {
    return this.apiFetch("/pagos");
  }

  cancelarSuscripcion(sesion, treeId) {
    return this.apiFetch(`/arboles/${treeId}/suscripcion`, { method: "DELETE" });
  }

  crearPedido(pedido) {
    return this.apiFetch("/pedidos", { method: "POST", body: JSON.stringify(pedido) });
  }

  obtenerPedidos() {
    return this.apiFetch("/pedidos");
  }

  actualizarLogistica(pedidoId, datos) {
    return this.apiFetch(`/pedidos/${pedidoId}`, { method: "PUT", body: JSON.stringify(datos) });
  }

  cancelarPlan(pedidoId) {
    return this.apiFetch(`/pedidos/${pedidoId}`, { method: "DELETE" });
  }

  subirArbol(arbol) {
    return this.apiFetch("/arboles", { method: "POST", body: JSON.stringify(arbol) });
  }

  eliminarArbol(arbolId) {
    return this.apiFetch(`/arboles/${arbolId}`, { method: "DELETE" });
  }

  actualizarArbol(arbolId, arbol) {
    return this.apiFetch(`/arboles/${arbolId}`, { method: "PUT", body: JSON.stringify(arbol) });
  }

  actualizarPerfil(cambios) {
    return this.apiFetch("/perfil", { method: "PUT", body: JSON.stringify(cambios) });
  }

  registrarUsuario(datos) {
    return this.apiFetch("/register", { method: "POST", body: JSON.stringify(datos) });
  }

  recuperarContrasena(email) {
    return this.apiFetch("/recuperar-contrasena", { method: "POST", body: JSON.stringify({ email }) });
  }

  restablecerContrasena(email, codigo, password) {
    return this.apiFetch("/restablecer-contrasena", {
      method: "POST",
      body: JSON.stringify({ email, codigo, password })
    });
  }

  verificarCuenta(email, codigo, password) {
    return this.apiFetch("/verificar-cuenta", {
      method: "POST",
      body: JSON.stringify({ email, codigo, password })
    });
  }

  cerrarSesion() {
    return this.apiFetch("/logout", { method: "POST" });
  }

  reenviarCodigo(email) {
    return this.apiFetch("/reenviar-codigo", { method: "POST", body: JSON.stringify({ email }) });
  }

  /* La cuenta sale del token: el correo no viaja en la ruta */
  eliminarCuenta(password) {
    return this.apiFetch("/perfil", { method: "DELETE", body: JSON.stringify({ password }) });
  }

  exportarDatos() {
    return this.apiFetch("/perfil/exportar");
  }

  obtenerSuscriptores(productorId) {
    return this.apiFetch(`/mis-arboles/${productorId}/suscriptores`);
  }

  obtenerMisArboles(usuarioId) {
    return this.apiFetch(`/suscripciones/usuario/${usuarioId}`);
  }

  expulsarSuscriptor(suscripcionId) {
    return this.apiFetch(`/suscripciones/${suscripcionId}`, { method: "DELETE" });
  }

  obtenerUsuario(usuarioId) {
    return this.apiFetch(`/usuario/${usuarioId}`);
  }
}

const apiService = new ApiService();
window.AgroColab.api = apiService;
window.AgroColab.config = window.AgroColab.config || {};
