/* Agro-Colab - Capa de comunicación con el backend (FastAPI).
   Servicio orientado a objetos: ApiService con instancia expuesta como
   AgroColab.api para mantener la interfaz usada por el resto de la app. */

var AgroColab = window.AgroColab || {};

class ApiService {
  constructor() {
    this.config = window.AgroColab.config;
  }

  async apiFetch(ruta, opciones = {}) {
    const respuesta = await fetch(`${this.config.API_URL}${ruta}`, {
      headers: { "Content-Type": "application/json" },
      ...opciones
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

  suscribirArbol(sesion, treeId) {
    return this.apiFetch("/suscribir", {
      method: "POST",
      body: JSON.stringify({
        user_id: sesion ? sesion.id : null,
        user_name: sesion ? sesion.nombre : null,
        email: sesion ? sesion.email : null,
        tree_id: treeId
      })
    });
  }

  cancelarSuscripcion(sesion, treeId) {
    return this.apiFetch("/cancelar-suscripcion", {
      method: "POST",
      body: JSON.stringify({
        user_id: sesion ? sesion.id : null,
        user_name: sesion ? sesion.nombre : null,
        tree_id: treeId
      })
    });
  }

  crearPedido(pedido) {
    return this.apiFetch("/pedidos", { method: "POST", body: JSON.stringify(pedido) });
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

  verificarCuenta(email, codigo) {
    return this.apiFetch("/verificar-cuenta", {
      method: "POST",
      body: JSON.stringify({ email, codigo })
    });
  }

  eliminarCuenta(email) {
    return this.apiFetch(`/usuario/${encodeURIComponent(email)}`, { method: "DELETE" });
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
