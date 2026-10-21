/* Agro-Colab - Capa de comunicación con el backend (FastAPI) */

(function () {
  const AgroColab = (window.AgroColab = window.AgroColab || {});
  const { API_URL } = AgroColab.config;

  async function apiFetch(ruta, opciones = {}) {
    const respuesta = await fetch(`${API_URL}${ruta}`, {
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

  AgroColab.api = {
    login(email, password, rol) {
      return apiFetch("/login", {
        method: "POST",
        body: JSON.stringify({ email, password, rol })
      });
    },

    obtenerArboles() {
      return apiFetch("/arboles");
    },

    obtenerEspecies() {
      return apiFetch("/especies");
    },

    suscribirArbol(userName, treeId) {
      return apiFetch("/suscribir", {
        method: "POST",
        body: JSON.stringify({ user_name: userName, tree_id: treeId })
      });
    },

    cancelarSuscripcion(userName, treeId) {
      return apiFetch("/cancelar-suscripcion", {
        method: "POST",
        body: JSON.stringify({ user_name: userName, tree_id: treeId })
      });
    },

    crearPedido(pedido) {
      return apiFetch("/pedidos", { method: "POST", body: JSON.stringify(pedido) });
    },

    obtenerPedidos() {
      return apiFetch("/pedidos");
    },

    subirArbol(arbol) {
      return apiFetch("/arboles", { method: "POST", body: JSON.stringify(arbol) });
    },

    eliminarArbol(arbolId) {
      return apiFetch(`/arboles/${arbolId}`, { method: "DELETE" });
    },

    actualizarArbol(arbolId, arbol) {
      return apiFetch(`/arboles/${arbolId}`, { method: "PUT", body: JSON.stringify(arbol) });
    },

    actualizarPerfil(cambios) {
      return apiFetch("/perfil", { method: "PUT", body: JSON.stringify(cambios) });
    },

    registrarUsuario(datos) {
      return apiFetch("/register", { method: "POST", body: JSON.stringify(datos) });
    },

    verificarCuenta(email, codigo) {
      return apiFetch("/verificar-cuenta", {
        method: "POST",
        body: JSON.stringify({ email, codigo })
      });
    },

    eliminarCuenta(email) {
      return apiFetch(`/usuario/${encodeURIComponent(email)}`, { method: "DELETE" });
    },

    obtenerSuscriptores(productorId) {
      return apiFetch(`/mis-arboles/${productorId}/suscriptores`);
    },

    expulsarSuscriptor(suscripcionId) {
      return apiFetch(`/suscripciones/${suscripcionId}`, { method: "DELETE" });
    },

    obtenerUsuario(usuarioId) {
      return apiFetch(`/usuario/${usuarioId}`);
    }
  };
})();
