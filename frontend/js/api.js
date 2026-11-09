/* Agro-Colab - Capa de comunicación con el backend (FastAPI).
   Servicio orientado a objetos: ApiService con instancia expuesta como
   AgroColab.api para mantener la interfaz usada por el resto de la app. */

var AgroColab = window.AgroColab || {};

class ApiService {
  constructor() {
    this.config = window.AgroColab.config;
  }

  async apiFetch(ruta, opciones = {}) {
    const headers = { "Content-Type": "application/json" };
    const sesion = window.AgroColab.auth ? window.AgroColab.auth.leerSesion() : null;
    if (sesion && sesion.token) {
      headers.Authorization = `Bearer ${sesion.token}`;
    }

    const respuesta = await fetch(`${this.config.API_URL}${ruta}`, {
      ...opciones,
      headers
    });

    let cuerpo = null;
    try {
      cuerpo = await respuesta.json();
    } catch (error) {
      cuerpo = null;
    }

    /* Si la respuesta no es JSON (un 500 del servidor, una página de
       mantenimiento, etc.) se avisa con el código real en vez de un
       genérico "error de conexión". */
    if (cuerpo === null) {
      if (respuesta.ok) {
        throw new Error("El servidor devolvió una respuesta inesperada.");
      }
      throw new Error(
        `El servidor respondió ${respuesta.status}` +
        `${respuesta.statusText ? " " + respuesta.statusText : ""}. ` +
        "Espera un momento e inténtalo de nuevo."
      );
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

  verificarCuenta(email, codigo) {
    return this.apiFetch("/verificar-cuenta", {
      method: "POST",
      body: JSON.stringify({ email, codigo })
    });
  }

  reenviarCodigo(email) {
    return this.apiFetch("/reenviar-codigo", { method: "POST", body: JSON.stringify({ email }) });
  }

  /* La cuenta sale del token: el correo no viaja en la ruta */
  /* Exige la contraseña actual: con solo el token no se borra la cuenta */
  eliminarCuenta(password) {
    return this.apiFetch("/perfil", { method: "DELETE", body: JSON.stringify({ password }) });
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
