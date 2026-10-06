/* Agro-Colab - Capa de comunicación con el backend (FastAPI) */

(function () {
  const AgroColab = (window.AgroColab = window.AgroColab || {});
  const { API_URL } = AgroColab.config;

  async function apiFetch(ruta, opciones = {}) {
    const respuesta = await fetch(`${API_URL}${ruta}`, {
      headers: { "Content-Type": "application/json" },
      ...opciones
    });
    return respuesta.json();
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
    }
  };
})();
