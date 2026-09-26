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

    crearPedido(pedido) {
      return apiFetch("/pedidos", { method: "POST", body: JSON.stringify(pedido) });
    },

    obtenerPedidos() {
      return apiFetch("/pedidos");
    }
  };
})();
