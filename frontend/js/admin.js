/* Agro-Colab - Panel de administración (AdminService), expuesto como
   AgroColab.admin. Lista todas las cuentas con búsqueda y filtro por tipo,
   y abre el detalle de cada una: sus árboles publicados (agricultor) o
   adoptados (comprador), un formulario para corregir sus datos y la opción
   de eliminarla. El backend vuelve a comprobar todo: el panel solo funciona
   con una sesión de administrador (routers/admin.py). */

(function () {
  const AgroColab = (window.AgroColab = window.AgroColab || {});
  // Escapa datos antes de insertarlos como HTML (ver ui.escapar)
  const e = (valor) => window.AgroColab.ui.escapar(valor);
  const { api, ui } = AgroColab;

  const ROLES = { comprador: "Comprador", agricultor: "Agricultor", administrador: "Administrador" };

  class AdminService {
    constructor() {
      this.usuarios = [];
      this.seleccionado = null;
    }

    async cargar() {
      const contenedor = document.getElementById("admin-usuarios");
      try {
        const data = await api.apiFetch("/admin/usuarios");
        if (data.status !== "success") {
          contenedor.innerHTML = `<p class="tc-cuerpo-sm" style="padding:2rem 0">${e(data.mensaje || "No se pudieron cargar las cuentas.")}</p>`;
          return;
        }
        this.usuarios = data.usuarios || [];
        this.pintarResumen();
        this.filtrar();
      } catch (error) {
        contenedor.innerHTML = '<p class="tc-cuerpo-sm" style="padding:2rem 0">No hay conexión con el servidor. Intenta nuevamente en unos segundos.</p>';
      }
    }

    pintarResumen() {
      const contar = (rol) => this.usuarios.filter((u) => u.rol === rol).length;
      document.getElementById("admin-total").textContent = this.usuarios.length;
      document.getElementById("admin-compradores").textContent = contar("comprador");
      document.getElementById("admin-agricultores").textContent = contar("agricultor");
      document.getElementById("admin-arboles").textContent = this.usuarios.reduce((total, u) => total + u.arboles_publicados, 0);
    }

    /* Se llama al escribir en el buscador o al cambiar el filtro de tipo */
    filtrar() {
      const texto = document.getElementById("admin-buscar").value.trim().toLowerCase();
      const rol = document.getElementById("admin-rol").value;
      const visibles = this.usuarios.filter((u) =>
        (!rol || u.rol === rol) &&
        (!texto || u.nombre.toLowerCase().includes(texto) || u.email.toLowerCase().includes(texto))
      );
      document.getElementById("admin-contador").textContent =
        visibles.length === this.usuarios.length ? `${visibles.length} cuentas` : `${visibles.length} de ${this.usuarios.length}`;
      this.pintarTabla(visibles);
    }

    actividad(usuario) {
      if (usuario.rol === "agricultor") {
        return `${usuario.arboles_publicados} ${usuario.arboles_publicados === 1 ? "árbol publicado" : "árboles publicados"}`;
      }
      if (usuario.rol === "comprador") {
        return `${usuario.adopciones} ${usuario.adopciones === 1 ? "adopción" : "adopciones"} · ${usuario.pedidos} ${usuario.pedidos === 1 ? "pedido" : "pedidos"}`;
      }
      return "-";
    }

    pintarTabla(usuarios) {
      const contenedor = document.getElementById("admin-usuarios");
      if (!usuarios.length) {
        contenedor.innerHTML = '<p class="tc-cuerpo-sm" style="padding:2rem 0">Ninguna cuenta coincide con la búsqueda.</p>';
        return;
      }
      contenedor.innerHTML = `
        <div class="admin-tabla">
          <table class="tc-tabla">
            <thead>
              <tr><th>Persona</th><th>Tipo</th><th>Estado</th><th>Actividad</th><th><span class="sr-only">Acciones</span></th></tr>
            </thead>
            <tbody>
              ${usuarios.map((u) => `
                <tr>
                  <td>
                    <span class="admin-persona">${e(u.nombre)}</span>
                    <span class="admin-correo">${e(u.email)}</span>
                  </td>
                  <td><span class="admin-rol-etiqueta admin-rol-etiqueta--${e(u.rol)}">${e(ROLES[u.rol] || u.rol)}</span></td>
                  <td>${u.verificado ? "Verificada" : '<span class="admin-pendiente">Sin verificar</span>'}</td>
                  <td>${e(this.actividad(u))}</td>
                  <td class="admin-acciones">
                    <button type="button" class="tc-enlace" data-accion="admin.abrir" data-args="[${Number(u.id)}]">
                      ${u.protegida ? "Ver" : "Ver y editar"}
                    </button>
                  </td>
                </tr>`).join("")}
            </tbody>
          </table>
        </div>`;
    }

    plantillaArbol(arbol) {
      const cupos = `${arbol.cupos_ocupados}/${arbol.cupos_totales} cupos`;
      return `
        <div class="perfil-arbol">
          <div class="perfil-arbol__foto">
            <img src="${e(arbol.imagen || "")}" alt="${e(arbol.nombre)}" data-si-falla="ocultar">
          </div>
          <div class="perfil-arbol__texto">
            <p class="perfil-arbol__nombre">${e(arbol.nombre)}</p>
            <p class="tc-cuerpo-sm">Plan ${e(arbol.plan || "-")} · ${e(cupos)} · ${e(arbol.ubicacion || "")}</p>
          </div>
          <p class="perfil-arbol__precio">${ui.formatearMonto(arbol.precio_mensual_clp)}<small>/ mes</small></p>
        </div>`;
    }

    pintarArboles(usuario, arboles, adoptados) {
      const titulo = document.getElementById("admin-usuario-titulo-arboles");
      const contenedor = document.getElementById("admin-usuario-arboles");
      const seccion = contenedor.closest("section");
      seccion.classList.toggle("hidden", usuario.rol === "administrador");

      const esAgricultor = usuario.rol === "agricultor";
      const lista = esAgricultor ? arboles : adoptados;
      titulo.textContent = esAgricultor ? `Árboles publicados (${lista.length})` : `Árboles adoptados (${lista.length})`;
      contenedor.innerHTML = lista.length
        ? lista.map((arbol) => this.plantillaArbol(arbol)).join("")
        : `<p class="tc-cuerpo-sm">${esAgricultor ? "Todavía no publica árboles." : "Todavía no adopta árboles."}</p>`;
    }

    async abrir(usuarioId) {
      try {
        const data = await api.apiFetch(`/admin/usuarios/${Number(usuarioId)}`);
        if (data.status !== "success") {
          AgroColab.dialogo.avisar(data.mensaje || "No se pudo cargar la cuenta.", { tipo: "error" });
          return;
        }
        const usuario = data.usuario;
        this.seleccionado = usuario;

        document.getElementById("admin-usuario-avatar").textContent = (usuario.nombre || "?").trim().charAt(0).toUpperCase();
        document.getElementById("admin-usuario-rol").textContent = ROLES[usuario.rol] || usuario.rol;
        document.getElementById("admin-usuario-nombre").textContent = usuario.nombre;
        this.pintarArboles(usuario, data.arboles || [], data.adoptados || []);

        document.getElementById("admin-input-nombre").value = usuario.nombre || "";
        document.getElementById("admin-input-email").value = usuario.email || "";
        document.getElementById("admin-input-telefono").value = usuario.telefono || "";
        document.getElementById("admin-input-direccion").value = usuario.direccion || "";
        document.getElementById("admin-input-password").value = "";
        document.getElementById("admin-input-verificado").checked = Boolean(usuario.verificado);
        ui.ocultarAlerta(document.getElementById("alerta-admin-usuario"));

        // Las cuentas demo y de administrador solo se ven
        const aviso = document.getElementById("admin-usuario-protegida");
        aviso.textContent = usuario.rol === "administrador"
          ? "Esta es una cuenta de administrador: no se modifica desde el panel. Cada administrador edita sus datos desde su perfil."
          : "Esta es una cuenta de demostración: sus credenciales son públicas, por eso no se puede modificar ni eliminar.";
        aviso.classList.toggle("hidden", !usuario.protegida);
        document.getElementById("form-admin-usuario").classList.toggle("hidden", usuario.protegida);
        document.getElementById("admin-usuario-peligro").classList.toggle("hidden", usuario.protegida);

        document.getElementById("modal-admin-usuario").classList.remove("hidden");
      } catch (error) {
        AgroColab.dialogo.avisar("No hay conexión con el servidor. Intenta nuevamente en unos segundos.", { tipo: "error" });
      }
    }

    cerrar() {
      document.getElementById("modal-admin-usuario").classList.add("hidden");
      this.seleccionado = null;
    }

    async guardar(evento) {
      evento.preventDefault();
      const usuario = this.seleccionado;
      if (!usuario) return;
      const alerta = document.getElementById("alerta-admin-usuario");
      const password = document.getElementById("admin-input-password").value;

      if (password && !(await AgroColab.dialogo.confirmar(
        "La persona tendrá que usar la nueva contraseña y se cerrarán sus sesiones abiertas. Comunícasela por un medio seguro.",
        { titulo: "¿Cambiar su contraseña?", aceptar: "Cambiar contraseña" }
      ))) {
        return;
      }

      const cambios = {
        nombre: document.getElementById("admin-input-nombre").value.trim(),
        email: document.getElementById("admin-input-email").value.trim(),
        telefono: document.getElementById("admin-input-telefono").value.trim(),
        direccion: document.getElementById("admin-input-direccion").value.trim(),
        verificado: document.getElementById("admin-input-verificado").checked,
        password: password || undefined
      };

      try {
        const data = await api.apiFetch(`/admin/usuarios/${Number(usuario.id)}`, {
          method: "PUT",
          body: JSON.stringify(cambios)
        });
        if (data.status === "success") {
          ui.mostrarAlerta(alerta, "exito", data.mensaje);
          document.getElementById("admin-usuario-nombre").textContent = cambios.nombre;
          document.getElementById("admin-input-password").value = "";
          await this.cargar();
        } else {
          ui.mostrarAlerta(alerta, "error", data.mensaje || "No se pudo actualizar la cuenta.");
        }
      } catch (error) {
        ui.mostrarAlerta(alerta, "error", "No hay conexión con el servidor. Intenta nuevamente en unos segundos.");
      }
    }

    async eliminar() {
      const usuario = this.seleccionado;
      if (!usuario) return;

      const detalle = usuario.rol === "agricultor"
        ? "Se borrarán sus datos y sus árboles publicados, y sus suscriptores perderán el cupo."
        : "Se borrarán sus datos, sus adopciones y sus pedidos.";
      if (!(await AgroColab.dialogo.confirmar(`${detalle} Esta acción no se puede deshacer.`, {
        titulo: `¿Eliminar la cuenta de ${usuario.nombre}?`,
        aceptar: "Eliminar cuenta",
        peligro: true
      }))) {
        return;
      }

      try {
        const data = await api.apiFetch(`/admin/usuarios/${Number(usuario.id)}`, { method: "DELETE" });
        if (data.status === "success") {
          this.cerrar();
          AgroColab.dialogo.avisar(data.mensaje, { tipo: "exito", titulo: "Cuenta eliminada" });
          await this.cargar();
        } else {
          AgroColab.dialogo.avisar(data.mensaje || "No se pudo eliminar la cuenta.", { tipo: "error" });
        }
      } catch (error) {
        AgroColab.dialogo.avisar("No hay conexión con el servidor. Intenta nuevamente en unos segundos.", { tipo: "error" });
      }
    }

    init() {
      document.getElementById("form-admin-usuario").addEventListener("submit", (evento) => this.guardar(evento));
    }
  }

  window.AgroColab.admin = new AdminService();
})();
