/* Agro-Colab - Servicio del Agricultor: dashboard de árboles y formulario
   para publicar nuevos árboles.

   El nombre y la foto del árbol no se escriben libremente: la especie se
   elige de un catálogo cerrado y la foto se toma de la galería curada de esa
   especie, de modo que el catálogo nunca muestre imágenes ajenas al árbol. */

(function () {
  const AgroColab = (window.AgroColab = window.AgroColab || {});

  class AgricultorService {
    constructor() {
      const { api, ui, auth, config, catalogo } = AgroColab;
      this.api = api;
      this.ui = ui;
      this.auth = auth;
      this.config = config;
      this.catalogo = catalogo;
      this.arbolesAgricultor = [];
      this.formulario = { especie: "", identificador: "", foto: null };
      this.edicion = { especie: "", identificador: "", foto: null };
      this.arbolSuscriptoresActual = null;
    }

    /* ---------- Renderizar lista de árboles ---------- */

    renderizarListaArboles() {
      const container = document.getElementById("lista-arboles-agricultor");

      if (!this.arbolesAgricultor.length) {
        container.innerHTML = '<p class="text-stone-500 text-sm text-center py-8">No has publicado árboles todavía</p>';
        return;
      }

      container.innerHTML = this.arbolesAgricultor
        .map((arbol) => {
          const cuposLibres = arbol.cupos_totales - arbol.cupos_ocupados;
          const porcentaje = arbol.cupos_totales
            ? Math.round((arbol.cupos_ocupados / arbol.cupos_totales) * 100)
            : 0;
          const claseBarra = cuposLibres > 0 ? "bg-emerald-600" : "bg-amber-500";
          return `
        <div class="p-5 flex flex-col sm:flex-row sm:items-center gap-4">
          <div class="w-16 h-16 rounded-xl overflow-hidden bg-stone-200 flex-shrink-0">
            <img src="${arbol.imagen || "https://via.placeholder.com/150?text=Árbol"}" alt="${arbol.nombre}" class="w-full h-full object-cover">
          </div>
          <div class="flex-1">
            <div class="flex items-center gap-2 mb-1">
              <h4 class="font-bold text-stone-900">${arbol.nombre}</h4>
              <span class="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${arbol.tipo_suscripcion === "Exclusivo" ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-800"}">${arbol.tipo_suscripcion}</span>
            </div>
            <p class="text-xs text-stone-500 mb-1"><i class="fa-solid fa-location-dot text-rose-500 mr-1"></i>${arbol.ubicacion}</p>
            <p class="text-xs text-stone-500">Plan: <strong>${arbol.plan}</strong> · Cupos: <strong>${arbol.cupos_ocupados}/${arbol.cupos_totales}</strong> · <span class="${cuposLibres > 0 ? "text-emerald-600" : "text-red-500"}">${cuposLibres > 0 ? cuposLibres + " libres" : "Completo"}</span></p>
            <div class="w-full bg-stone-100 h-2 rounded-full overflow-hidden mt-2">
              <div class="${claseBarra} h-2 rounded-full" style="width: ${porcentaje}%"></div>
            </div>
          </div>
          <div class="text-right">
            <p class="font-black text-emerald-900">${this.ui.formatearMonto(arbol.precio_mensual_clp)}</p>
            <p class="text-[10px] text-stone-400">CLP / mes</p>
            <div class="mt-2 flex gap-2 justify-end flex-wrap">
              <button type="button" onclick="AgroColab.agricultor.abrirSuscriptores(${arbol.id})" class="text-emerald-600 hover:text-emerald-800 text-xs font-bold flex items-center gap-1">
                <i class="fa-solid fa-users"></i> Ver suscriptores (${arbol.cupos_ocupados})
              </button>
              <button type="button" onclick="AgroColab.agricultor.abrirEdicion(${arbol.id})" class="text-emerald-600 hover:text-emerald-800 text-xs font-bold flex items-center gap-1">
                <i class="fa-solid fa-pen"></i> Editar
              </button>
              <button type="button" onclick="AgroColab.agricultor.eliminarArbol(${arbol.id})" class="text-red-500 hover:text-red-700 text-xs font-bold flex items-center gap-1">
                <i class="fa-solid fa-trash"></i> Eliminar
              </button>
            </div>
          </div>
        </div>
      `;
        })
        .join("");
    }

    /* ---------- Editar árbol ---------- */

    abrirEdicion(arbolId) {
      const arbol = this.arbolesAgricultor.find((a) => a.id === arbolId);
      if (!arbol) return;

      document.getElementById("editar-arbol-id").value = arbol.id;
      document.getElementById("editar-ubicacion").value = arbol.ubicacion;
      document.getElementById("editar-plan").value = arbol.plan;
      document.getElementById("editar-tipo").value = arbol.tipo_suscripcion;
      document.getElementById("editar-cupos").value = arbol.cupos_totales;
      document.getElementById("editar-precio").value = arbol.precio_mensual_clp;
      document.getElementById("editar-cosecha").value = arbol.estimacion_cosecha;

      this.edicion.especie = arbol.especie || "";
      this.edicion.identificador = arbol.identificador || "";
      this.edicion.foto = null;

      const selectorEspecie = document.getElementById("editar-especie");
      this.catalogo.pintarSelect(selectorEspecie);
      selectorEspecie.value = this.edicion.especie;

      const especie = this.catalogo.porId(this.edicion.especie);
      this.edicion.foto = especie
        ? especie.fotos.find((foto) => foto.url === arbol.imagen) || null
        : null;

      document.getElementById("editar-identificador").value = this.edicion.identificador;

      this.pintarGaleriaEdicion();
      this.actualizarResumenNombre("editar");

      document.getElementById("modal-editar-arbol").classList.remove("hidden");
    }

    pintarGaleriaEdicion() {
      this.catalogo.pintarGaleria(
        document.getElementById("galeria-editar"),
        this.edicion.especie,
        (foto) => {
          this.edicion.foto = foto;
          this.catalogo.pintarCredito(document.getElementById("credito-editar"), foto);
        },
        this.edicion.foto ? this.edicion.foto.url : null
      );
    }

    cerrarEdicion() {
      document.getElementById("modal-editar-arbol").classList.add("hidden");
    }

    /* ---------- Guardar edición ---------- */

    async guardarEdicion(evento) {
      evento.preventDefault();

      const alerta = document.getElementById("alerta-editar-arbol");
      const arbolId = Number(document.getElementById("editar-arbol-id").value);

      if (!this.edicion.especie) {
        this.ui.mostrarAlerta(alerta, "error", "Selecciona la especie del árbol.");
        return;
      }

      if (!this.edicion.foto) {
        this.ui.mostrarAlerta(alerta, "error", "Elige la foto del árbol en la galería.");
        return;
      }

      const bodyData = {
        especie: this.edicion.especie,
        identificador: this.edicion.identificador,
        ubicacion: document.getElementById("editar-ubicacion").value.trim(),
        plan: document.getElementById("editar-plan").value,
        tipo_suscripcion: document.getElementById("editar-tipo").value,
        cupos_totales: Number(document.getElementById("editar-cupos").value),
        precio_mensual_clp: Number(document.getElementById("editar-precio").value),
        estimacion_cosecha: document.getElementById("editar-cosecha").value.trim(),
        imagen: this.edicion.foto.url,
        productor: this.auth.leerSesion().nombre
      };

      if (!bodyData.ubicacion || !bodyData.estimacion_cosecha) {
        this.ui.mostrarAlerta(alerta, "error", "Completa todos los campos obligatorios.");
        return;
      }

      try {
        const data = await this.api.actualizarArbol(arbolId, bodyData);
        if (data.status === "success") {
          this.ui.mostrarAlerta(alerta, "exito", data.mensaje);
          setTimeout(() => {
            this.cerrarEdicion();
            this.cargarArbolesAgricultor();
          }, 1500);
        } else {
          this.ui.mostrarAlerta(alerta, "error", data.mensaje || "No se pudo actualizar el árbol.");
        }
      } catch (error) {
        this.ui.mostrarAlerta(alerta, "error", "Error de comunicación con el backend.");
      }
    }

    /* ---------- Eliminar árbol ---------- */

    async eliminarArbol(arbolId) {
      if (!window.confirm("¿Estás seguro de eliminar este árbol? Esta acción no se puede deshacer.")) {
        return;
      }

      try {
        const data = await this.api.eliminarArbol(arbolId);
        if (data.status === "success") {
          window.alert(data.mensaje);
          await this.cargarArbolesAgricultor();
        } else {
          window.alert(data.mensaje || "No se pudo eliminar el árbol.");
        }
      } catch (error) {
        window.alert("Error de comunicación con el backend.");
      }
    }

    /* ---------- Estadísticas del dashboard ---------- */

    actualizarEstadisticas() {
      const totalArboles = this.arbolesAgricultor.length;
      const totalSuscriptores = this.arbolesAgricultor.reduce(
        (suma, a) => suma + (a.cupos_ocupados || 0),
        0
      );
      const ingresos = this.arbolesAgricultor.reduce(
        (suma, a) => suma + (a.precio_mensual_clp || 0) * (a.cupos_ocupados || 0),
        0
      );

      document.getElementById("stat-total-arboles").textContent = totalArboles;
      document.getElementById("stat-suscriptores").textContent = totalSuscriptores;
      document.getElementById("stat-ingresos").textContent = this.ui.formatearMonto(ingresos);
    }

    /* ---------- Cargar árboles del agricultor ---------- */

    async cargarArbolesAgricultor() {
      const container = document.getElementById("lista-arboles-agricultor");
      container.innerHTML = '<p class="text-stone-500 text-sm text-center py-8">Cargando tus árboles...</p>';

      try {
        const arboles = await this.api.obtenerArboles();
        const sesion = this.auth.leerSesion();
        this.arbolesAgricultor = sesion
          ? arboles.filter((a) => a.productor === sesion.nombre)
          : [];

        this.renderizarListaArboles();
        this.actualizarEstadisticas();
      } catch (error) {
        container.innerHTML = '<p class="text-red-500 text-sm text-center py-8">Error al cargar tus árboles</p>';
      }
    }

    /* ---------- Suscriptores ---------- */

    async abrirSuscriptores(arbolId) {
      const arbol = this.arbolesAgricultor.find((a) => a.id === arbolId);
      if (!arbol) return;

      this.arbolSuscriptoresActual = arbol;
      document.getElementById("suscriptores-arbol-nombre").textContent = arbol.nombre;
      document.getElementById("suscriptores-arbol-id").value = arbol.id;
      document.getElementById("suscriptores-contador").textContent = `${arbol.cupos_ocupados ?? 0} suscriptor${arbol.cupos_ocupados === 1 ? "" : "es"}`;
      document.getElementById("modal-suscriptores").classList.remove("hidden");
      await this.cargarSuscriptores(arbol.id);
    }

    cerrarSuscriptores() {
      document.getElementById("modal-suscriptores").classList.add("hidden");
      this.arbolSuscriptoresActual = null;
    }

    async cargarSuscriptores(arbolId) {
      const contenedor = document.getElementById("lista-suscriptores");
      contenedor.innerHTML = '<p class="text-stone-500 text-sm text-center py-8">Cargando suscriptores...</p>';

      try {
        const sesion = this.auth.leerSesion();
        const datos = await this.api.obtenerSuscriptores(sesion.id);
        if (!Array.isArray(datos)) {
          contenedor.innerHTML = `<p class="text-red-500 text-sm text-center py-8">${(datos && datos.mensaje) || "Error al cargar suscriptores"}</p>`;
          return;
        }
        const arbol = datos.find((a) => a.arbol_id === arbolId);

        if (!arbol) {
          contenedor.innerHTML = '<p class="text-red-500 text-sm text-center py-8">No se encontró el árbol en tu panel.</p>';
          return;
        }

        const suscriptores = arbol.suscriptores || [];

        if (!suscriptores.length) {
          contenedor.innerHTML = `
          <div class="text-center py-10">
            <div class="w-14 h-14 bg-stone-100 rounded-full flex items-center justify-center mx-auto mb-3">
              <i class="fa-solid fa-users text-stone-400 text-xl"></i>
            </div>
            <p class="text-sm font-bold text-stone-700">Todavía no hay suscriptores para este árbol</p>
            <p class="text-xs text-stone-500 mt-1">Cuando un comprador adopte este árbol aparecerá aquí.</p>
          </div>
        `;
          return;
        }

        contenedor.innerHTML = suscriptores
          .map((s) => {
            const iniciales = (s.nombre || "?")
              .split(" ")
              .map((parte) => parte.charAt(0))
              .slice(0, 2)
              .join("")
              .toUpperCase();
            return `
            <div class="flex flex-col sm:flex-row sm:items-center gap-3 p-4 bg-stone-50 rounded-xl border border-stone-200">
              <div class="w-10 h-10 bg-emerald-100 rounded-full flex items-center justify-center flex-shrink-0">
                <span class="text-xs font-black text-emerald-700">${iniciales}</span>
              </div>
              <div class="flex-1">
                <p class="font-bold text-sm text-stone-900">${s.nombre}</p>
                <p class="text-xs text-stone-500"><i class="fa-solid fa-envelope text-stone-400 mr-1"></i>${s.email}</p>
                <p class="text-xs text-stone-500">${s.telefono ? '<i class="fa-solid fa-phone text-stone-400 mr-1"></i>' + s.telefono : ''} ${s.direccion ? '<i class="fa-solid fa-location-dot text-stone-400 mr-1"></i>' + s.direccion : ''}</p>
                <p class="text-[10px] text-stone-400 mt-1">Suscrito el ${s.fecha_suscripcion}</p>
              </div>
              <div class="flex gap-2">
                <button type="button" onclick="AgroColab.agricultor.verPerfilUsuario(${s.usuario_id})" class="text-emerald-600 hover:text-emerald-800 text-xs font-bold flex items-center gap-1">
                  <i class="fa-solid fa-id-card"></i> Ver perfil
                </button>
                <button type="button" onclick="AgroColab.agricultor.expulsarSuscriptor(${s.suscripcion_id})" class="text-red-500 hover:text-red-700 text-xs font-bold flex items-center gap-1">
                  <i class="fa-solid fa-user-minus"></i> Expulsar
                </button>
              </div>
            </div>
          `;
          })
          .join("");
      } catch (error) {
        contenedor.innerHTML = '<p class="text-red-500 text-sm text-center py-8">Error al cargar suscriptores</p>';
      }
    }

    async verPerfilUsuario(usuarioId) {
      try {
        const usuario = await this.api.obtenerUsuario(usuarioId);
        if (usuario && usuario.id) {
          window.alert(
            `Perfil del usuario:\n\n` +
            `Nombre: ${usuario.nombre}\n` +
            `Email: ${usuario.email}\n` +
            `Teléfono: ${usuario.telefono || 'No registrado'}\n` +
            `Dirección: ${usuario.direccion || 'No registrada'}\n` +
            `Rol: ${usuario.rol}\n` +
            `Cuenta verificada: ${usuario.verificado ? 'Sí' : 'No'}`
          );
        } else {
          window.alert((usuario && usuario.mensaje) || "No se pudo cargar el perfil del usuario.");
        }
      } catch (error) {
        window.alert("Error al cargar el perfil del usuario.");
      }
    }

    async expulsarSuscriptor(suscripcionId) {
      if (!window.confirm("¿Estás seguro de expulsar a este suscriptor? Se liberará su cupo.")) {
        return;
      }

      try {
        const data = await this.api.expulsarSuscriptor(suscripcionId);
        if (data.status === "success") {
          window.alert(data.mensaje);
          if (this.arbolSuscriptoresActual) {
            await this.cargarSuscriptores(this.arbolSuscriptoresActual.id);
          }
          await this.cargarArbolesAgricultor();
        } else {
          window.alert(data.mensaje || "No se pudo expulsar al suscriptor.");
        }
      } catch (error) {
        window.alert("Error de comunicación con el backend.");
      }
    }

    /* ---------- Formulario de subida de árbol ---------- */

    mostrarFormulario() {
      document.getElementById("dashboard-agricultor").classList.add("hidden");
      document.getElementById("formulario-arbol").classList.remove("hidden");
    }

    mostrarDashboard() {
      document.getElementById("formulario-arbol").classList.add("hidden");
      document.getElementById("dashboard-agricultor").classList.remove("hidden");
    }

    /* Muestra cómo se verá el nombre del árbol con la especie y el identificador elegidos. */
    actualizarResumenNombre(contexto) {
      const destino = document.getElementById(
        contexto === "editar" ? "resumen-nombre-editar" : "resumen-nombre"
      );
      if (!destino) return;

      const objetoEdicion = contexto === "editar" ? this.edicion : this.formulario;
      const especie = this.catalogo.porId(objetoEdicion.especie);
      const identificador = document.getElementById(
        contexto === "editar" ? "editar-identificador" : "arbol-identificador"
      ).value.trim();

      if (!especie) {
        destino.innerHTML = '<span class="text-stone-400">El nombre se arma con la especie y el número del árbol.</span>';
        return;
      }

      const numero = identificador
        ? identificador.startsWith("#") ? identificador : "#" + identificador
        : "";

      destino.innerHTML =
        '<span class="text-emerald-800 font-bold">' + especie.nombre + "</span>" +
        (numero ? ' <span class="text-stone-600">' + numero + "</span>" : "") +
        '<span class="text-stone-400"> · se mostrará así en el catálogo</span>';
    }

    pintarGaleriaFormulario() {
      this.catalogo.pintarGaleria(
        document.getElementById("galeria-arbol"),
        this.formulario.especie,
        (foto) => {
          this.formulario.foto = foto;
          this.catalogo.pintarCredito(document.getElementById("credito-arbol"), foto);
        },
        this.formulario.foto ? this.formulario.foto.url : null
      );
    }

    alCambiarEspecie() {
      const selector = document.getElementById("arbol-especie");
      this.formulario.especie = selector.value;
      this.formulario.foto = null;

      const descripcion = document.getElementById("arbol-especie-descripcion");
      const especie = this.catalogo.porId(this.formulario.especie);
      descripcion.textContent = especie ? especie.descripcion : "";

      this.pintarGaleriaFormulario();
      this.catalogo.pintarCredito(document.getElementById("credito-arbol"), null);
      this.actualizarResumenNombre("formulario");
    }

    async subirArbol(evento) {
      evento.preventDefault();

      const alerta = document.getElementById("alerta-subir-arbol");
      const sesion = this.auth.leerSesion();

      if (!sesion) {
        this.ui.mostrarAlerta(alerta, "error", "Debes iniciar sesión para publicar un árbol.");
        return;
      }

      if (!this.formulario.especie) {
        this.ui.mostrarAlerta(alerta, "error", "Selecciona la especie del árbol.");
        return;
      }

      if (!this.formulario.foto) {
        this.ui.mostrarAlerta(alerta, "error", "Elige la foto del árbol en la galería.");
        return;
      }

      const bodyData = {
        especie: this.formulario.especie,
        identificador: document.getElementById("arbol-identificador").value.trim(),
        ubicacion: document.getElementById("arbol-ubicacion").value.trim(),
        plan: document.getElementById("arbol-plan").value,
        tipo_suscripcion: document.getElementById("arbol-tipo").value,
        cupos_totales: Number(document.getElementById("arbol-cupos").value),
        precio_mensual_clp: Number(document.getElementById("arbol-precio").value),
        estimacion_cosecha: document.getElementById("arbol-cosecha").value.trim(),
        imagen: this.formulario.foto.url,
        productor: sesion.nombre
      };

      if (!bodyData.ubicacion || !bodyData.estimacion_cosecha) {
        this.ui.mostrarAlerta(alerta, "error", "Completa todos los campos obligatorios.");
        return;
      }

      this.ui.mostrarAlerta(alerta, "info", "Publicando árbol...");

      try {
        const data = await this.api.subirArbol(bodyData);

        if (data.status === "success") {
          this.ui.mostrarAlerta(alerta, "exito", data.mensaje || "Árbol publicado correctamente.");
          document.getElementById("form-subir-arbol").reset();
          this.formulario.especie = "";
          this.formulario.identificador = "";
          this.formulario.foto = null;
          document.getElementById("arbol-especie-descripcion").textContent = "";
          document.getElementById("credito-arbol").innerHTML = "";
          this.pintarGaleriaFormulario();
          this.actualizarResumenNombre("formulario");
          setTimeout(() => {
            this.mostrarDashboard();
            this.cargarArbolesAgricultor();
          }, 1500);
        } else {
          this.ui.mostrarAlerta(alerta, "error", data.mensaje || "No se pudo publicar el árbol.");
        }
      } catch (error) {
        this.ui.mostrarAlerta(alerta, "error", "Error de comunicación con el backend.");
      }
    }

    /* ---------- Navbar ---------- */

    pintarNavbarAgricultor() {
      const sesion = this.auth.leerSesion();
      const contenedor = document.getElementById("nav-sesion-agricultor");
      if (!contenedor || !sesion) return;

      contenedor.innerHTML = `
        <span class="nav-chip nav-chip--clickeable" onclick="AgroColab.perfil.abrir()" title="Ver mi perfil">
          <span class="hidden sm:inline font-bold text-white">${sesion.nombre}</span>
          <span class="text-emerald-400 font-black uppercase">${sesion.rol}</span>
          <i class="fa-solid fa-tractor"></i>
        </span>`;
    }

    /* ---------- Inicialización ---------- */

    async init() {
      document.getElementById("btn-subir-arbol").addEventListener("click", () => this.mostrarFormulario());
      document.getElementById("btn-cancelar-arbol").addEventListener("click", () => this.mostrarDashboard());
      document.getElementById("form-subir-arbol").addEventListener("submit", (evento) => this.subirArbol(evento));
      document.getElementById("form-editar-arbol").addEventListener("submit", (evento) => this.guardarEdicion(evento));

      /* Catálogo de especies: selector + galería de fotos */
      document.getElementById("arbol-especie").addEventListener("change", () => this.alCambiarEspecie());
      document.getElementById("arbol-identificador").addEventListener("input", () => this.actualizarResumenNombre("formulario"));

      const selectorEdicion = document.getElementById("editar-especie");
      selectorEdicion.addEventListener("change", () => {
        this.edicion.especie = selectorEdicion.value;
        this.edicion.foto = null;
        this.pintarGaleriaEdicion();
        this.catalogo.pintarCredito(document.getElementById("credito-editar"), null);
        this.actualizarResumenNombre("editar");
      });
      document.getElementById("editar-identificador").addEventListener("input", () => this.actualizarResumenNombre("editar"));

      /* El catálogo se carga una vez y se pinta en los dos formularios */
      this.catalogo.cargar().then(() => {
        this.catalogo.pintarSelect(document.getElementById("arbol-especie"));
        this.catalogo.pintarSelect(selectorEdicion);
        this.pintarGaleriaFormulario();
        this.actualizarResumenNombre("formulario");
      });

      document.getElementById("btn-cerrar-sesion-agricultor").addEventListener("click", () => {
        this.auth.eliminarSesion();
        window.AgroColab.views.mostrarVista(this.config.VISTA_SIN_SESION);
      });
      this.pintarNavbarAgricultor();
    }

    async cargar() {
      return this.cargarArbolesAgricultor();
    }
  }

  const agricultorService = new AgricultorService();
  window.AgroColab.agricultor = agricultorService;
})();
