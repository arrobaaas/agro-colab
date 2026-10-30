/* Agro-Colab - Servicio del Agricultor: dashboard de árboles y formulario
   para publicar nuevos árboles.

   El nombre y la foto del árbol no se escriben libremente: la especie se
   elige de un catálogo cerrado y la foto se toma de la galería curada de esa
   especie, de modo que el catálogo nunca muestre imágenes ajenas al árbol. */

(function () {
  const AgroColab = (window.AgroColab = window.AgroColab || {});
  // Escapa datos antes de insertarlos como HTML (ver ui.escapar)
  const e = (valor) => window.AgroColab.ui.escapar(valor);

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
        container.innerHTML = `
          <div class="sm:col-span-2 lg:col-span-3 text-center py-14 px-6 bg-white rounded-3xl border border-dashed border-stone-300">
            <div class="w-16 h-16 mx-auto rounded-2xl bg-emerald-50 text-emerald-700 flex items-center justify-center text-2xl mb-4">
              <i class="fa-solid fa-seedling"></i>
            </div>
            <p class="text-lg font-extrabold text-stone-900">Todavía no publicas árboles</p>
            <p class="text-sm text-stone-500 mt-1 max-w-sm mx-auto">Publica tu primer árbol y empieza a recibir financiamiento directo de los compradores.</p>
            <button type="button" class="btn-hero btn-hero--primario mt-6" data-accion="agricultor.mostrarFormulario">
              <i class="fa-solid fa-plus"></i> Publicar mi primer árbol
            </button>
          </div>`;
        return;
      }

      container.innerHTML = this.arbolesAgricultor
        .map((arbol, indice) => {
          const ocupados = arbol.cupos_ocupados || 0;
          const totales = arbol.cupos_totales || 0;
          const libres = Math.max(0, totales - ocupados);
          const porcentaje = totales ? Math.round((ocupados / totales) * 100) : 0;
          const exclusivo = arbol.tipo_suscripcion === "Exclusivo";
          const ingreso = (arbol.precio_mensual_clp || 0) * ocupados;

          return `
          <article class="arbol-card" data-reveal="flip" data-tilt style="--reveal-delay:${(indice % 3) * 150}ms">
            <div class="arbol-card__media">
              <img src="${e(arbol.imagen || "")}" alt="${e(arbol.nombre)}" loading="lazy" data-si-falla="ocultar">
              <span class="arbol-card__plan">${e(arbol.plan)}</span>
              <span class="arbol-card__tipo ${exclusivo ? "arbol-card__tipo--exclusivo" : ""}">
                <i class="fa-solid ${exclusivo ? "fa-crown" : "fa-users"}"></i> ${e(arbol.tipo_suscripcion || "")}
              </span>
              <div class="arbol-card__titulo">
                ${arbol.especie_nombre ? `<p class="arbol-card__especie">${e(arbol.especie_nombre)}</p>` : ""}
                <h4>${e(arbol.nombre)}</h4>
              </div>
            </div>

            <div class="p-5 flex flex-col gap-4 flex-1">
              <p class="text-xs text-stone-600 truncate"><i class="fa-solid fa-location-dot text-rose-500 mr-1.5"></i>${e(arbol.ubicacion)}</p>

              <div>
                <div class="flex justify-between text-[11px] mb-1.5">
                  <span class="${libres ? "text-stone-500" : "text-amber-700 font-bold"}">${libres ? `${libres} cupo${libres === 1 ? "" : "s"} libre${libres === 1 ? "" : "s"}` : "Cupos completos"}</span>
                  <span class="font-bold text-stone-700">${ocupados}/${totales} · ${porcentaje}%</span>
                </div>
                <div class="h-1.5 rounded-full bg-stone-100 overflow-hidden">
                  <div class="h-full rounded-full ${libres ? "bg-emerald-500" : "bg-amber-500"}" style="width:${porcentaje}%"></div>
                </div>
              </div>

              <div class="grid grid-cols-2 gap-2">
                <div class="rounded-xl bg-stone-50 border border-stone-200 px-3 py-2">
                  <p class="text-[10px] uppercase tracking-wider font-bold text-stone-400">Precio / cupo</p>
                  <p class="text-sm font-extrabold text-stone-800">${this.ui.formatearMonto(arbol.precio_mensual_clp)}</p>
                </div>
                <div class="rounded-xl bg-emerald-50 border border-emerald-100 px-3 py-2">
                  <p class="text-[10px] uppercase tracking-wider font-bold text-emerald-700/70">Ingreso / mes</p>
                  <p class="text-sm font-extrabold text-emerald-900">${this.ui.formatearMonto(ingreso)}</p>
                </div>
              </div>

              <div class="mt-auto pt-4 border-t border-stone-100 flex items-center gap-2">
                <button type="button" class="accion-arbol flex-1" data-accion="agricultor.abrirSuscriptores" data-args='[${Number(arbol.id)}]'>
                  <i class="fa-solid fa-users"></i> Suscriptores <span class="accion-arbol__contador">${ocupados}</span>
                </button>
                <button type="button" class="accion-arbol accion-arbol--icono" data-accion="agricultor.abrirEdicion" data-args='[${Number(arbol.id)}]' title="Editar" aria-label="Editar ${e(arbol.nombre)}">
                  <i class="fa-solid fa-pen"></i>
                </button>
                <button type="button" class="accion-arbol accion-arbol--icono accion-arbol--peligro" data-accion="agricultor.eliminarArbol" data-args='[${Number(arbol.id)}]' title="Eliminar" aria-label="Eliminar ${e(arbol.nombre)}">
                  <i class="fa-solid fa-trash"></i>
                </button>
              </div>
            </div>
          </article>
        `;
        })
        .join("");

      if (AgroColab.efectos) AgroColab.efectos.observar(container);
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
      document.getElementById("editar-cosecha").value = this.kilosDeCosecha(arbol.estimacion_cosecha);

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
        estimacion_cosecha_kg: Number(document.getElementById("editar-cosecha").value),
        imagen: this.edicion.foto.url,
        productor: this.auth.leerSesion().nombre
      };

      if (!bodyData.ubicacion || !(bodyData.estimacion_cosecha_kg >= 1)) {
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
      const totalSuscriptores = this.arbolesAgricultor.reduce((suma, a) => suma + (a.cupos_ocupados || 0), 0);
      const totalCupos = this.arbolesAgricultor.reduce((suma, a) => suma + (a.cupos_totales || 0), 0);
      const ocupacion = totalCupos ? Math.round((totalSuscriptores / totalCupos) * 100) : 0;
      const ingresos = this.arbolesAgricultor.reduce(
        (suma, a) => suma + (a.precio_mensual_clp || 0) * (a.cupos_ocupados || 0),
        0
      );

      this.animarNumero("stat-total-arboles", totalArboles, (n) => String(n));
      this.animarNumero("stat-suscriptores", totalSuscriptores, (n) => String(n));
      this.animarNumero("stat-ocupacion", ocupacion, (n) => `${n}%`);
      this.animarNumero("stat-ingresos", ingresos, (n) => this.ui.formatearMonto(n));
      document.getElementById("stat-ocupacion-barra").style.width = `${ocupacion}%`;
    }

    /* Cuenta desde 0 hasta el valor final (o lo muestra directo si el
       usuario pidió reducir el movimiento). */
    animarNumero(id, valorFinal, formato) {
      const elemento = document.getElementById(id);
      if (!elemento) return;

      const efectos = AgroColab.efectos;
      if (!valorFinal || (efectos && efectos.reducirMovimiento)) {
        elemento.textContent = formato(valorFinal);
        return;
      }

      const duracion = 1100;
      const inicio = performance.now();
      const paso = (ahora) => {
        const avance = Math.min((ahora - inicio) / duracion, 1);
        const suavizado = 1 - Math.pow(1 - avance, 3);
        elemento.textContent = formato(Math.round(valorFinal * suavizado));
        if (avance < 1) requestAnimationFrame(paso);
      };
      requestAnimationFrame(paso);
    }

    async cargarArbolesAgricultor() {
      const container = document.getElementById("lista-arboles-agricultor");
      container.innerHTML = '<p class="sm:col-span-2 lg:col-span-3 text-stone-500 text-sm text-center py-8">Cargando tus árboles...</p>';

      try {
        const arboles = await this.api.obtenerArboles();
        const sesion = this.auth.leerSesion();
        // Por id: comparando el nombre se mezclaban agricultores homónimos y
        // se perdían los árboles al cambiar el nombre en el perfil
        this.arbolesAgricultor = sesion
          ? arboles.filter((a) => String(a.productor_id) === String(sesion.id))
          : [];

        this.renderizarListaArboles();
        this.actualizarEstadisticas();
      } catch (error) {
        container.innerHTML = '<p class="sm:col-span-2 lg:col-span-3 text-red-500 text-sm text-center py-8">Error al cargar tus árboles</p>';
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
          contenedor.innerHTML = `<p class="text-red-500 text-sm text-center py-8">${e((datos && datos.mensaje) || "Error al cargar suscriptores")}</p>`;
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
            <div class="canasta-item flex-col sm:flex-row sm:items-center">
              <span class="nav-usuario__avatar w-11 h-11 text-sm flex-shrink-0">${e(iniciales)}</span>
              <div class="flex-1">
                <p class="font-bold text-sm text-stone-900">${e(s.nombre)}</p>
                <p class="text-xs text-stone-500"><i class="fa-solid fa-envelope text-stone-400 mr-1"></i>${e(s.email)}</p>
                <p class="text-xs text-stone-500">${s.telefono ? '<i class="fa-solid fa-phone text-stone-400 mr-1"></i>' + e(s.telefono) : ''} ${s.direccion ? '<i class="fa-solid fa-location-dot text-stone-400 mr-1"></i>' + e(s.direccion) : ''}</p>
                <p class="text-[10px] text-stone-400 mt-1">Suscrito el ${e(s.fecha_suscripcion)}</p>
              </div>
              <div class="flex gap-2">
                <button type="button" data-accion="agricultor.verPerfilUsuario" data-args='[${Number(s.usuario_id)}]' class="text-emerald-600 hover:text-emerald-800 text-xs font-bold flex items-center gap-1">
                  <i class="fa-solid fa-id-card"></i> Ver perfil
                </button>
                <button type="button" data-accion="agricultor.expulsarSuscriptor" data-args='[${Number(s.suscripcion_id)}]' class="text-red-500 hover:text-red-700 text-xs font-bold flex items-center gap-1">
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
      this.cambiarSeccion("dashboard-agricultor", "formulario-arbol");
      this.pintarVistaPrevia();
    }

    /* Oculta una sección y muestra la otra con su animación de entrada. */
    cambiarSeccion(ocultarId, mostrarId) {
      const mostrar = document.getElementById(mostrarId);
      document.getElementById("vista-agricultor").classList.toggle("modo-formulario", mostrarId === "formulario-arbol");
      document.getElementById(ocultarId).classList.add("hidden");
      mostrar.classList.remove("hidden", "vista-seccion--entrando");
      void mostrar.offsetWidth; // reinicia la animación
      mostrar.classList.add("vista-seccion--entrando");
      window.scrollTo({ top: 0, behavior: "smooth" });
    }

    mostrarDashboard() {
      this.cambiarSeccion("formulario-arbol", "dashboard-agricultor");
    }

    /* ---------- Cosecha en kilos ---------- */

    /* Mismo texto que arma el backend (core.texto_cosecha) */
    textoCosecha(kilos) {
      const numero = Math.round(Number(kilos));
      return numero >= 1 ? `${numero.toLocaleString("es-CL")} kg anuales` : "—";
    }

    /* Número de kilos de un texto guardado: "1.200 kg anuales" -> 1200 */
    kilosDeCosecha(texto) {
      const coincidencia = String(texto || "").match(/[\d.]+/);
      return coincidencia ? Number(coincidencia[0].replace(/\./g, "")) || "" : "";
    }

    /* ---------- Vista previa en vivo del formulario ---------- */

    pintarVistaPrevia() {
      const contenedor = document.getElementById("vista-previa-arbol");
      if (!contenedor || !AgroColab.parcelas) return;

      const especie = this.catalogo.porId(this.formulario.especie);
      const identificador = document.getElementById("arbol-identificador").value.trim();
      const numero = identificador ? (identificador.startsWith("#") ? identificador : `#${identificador}`) : "";
      const cupos = Math.max(1, Number(document.getElementById("arbol-cupos").value) || 1);
      const sesion = this.auth.leerSesion();

      const arbol = {
        id: 0,
        nombre: especie ? `${especie.nombre}${numero ? " " + numero : ""}` : "Tu árbol",
        especie_nombre: especie ? especie.nombre : "Elige una especie",
        imagen: this.formulario.foto ? this.formulario.foto.url : "",
        plan: document.getElementById("arbol-plan").value,
        tipo_suscripcion: document.getElementById("arbol-tipo").value,
        ubicacion: document.getElementById("arbol-ubicacion").value.trim() || "Ubicación del huerto",
        estimacion_cosecha: this.textoCosecha(document.getElementById("arbol-cosecha").value),
        productor: sesion ? sesion.nombre : "",
        precio_mensual_clp: Number(document.getElementById("arbol-precio").value) || 0,
        cupos_totales: cupos,
        cupos_ocupados: 0
      };

      // Se reutiliza la tarjeta real del catálogo para que la vista previa sea fiel
      contenedor.innerHTML = AgroColab.parcelas.plantillaArbol(arbol, 0);
      const tarjeta = contenedor.querySelector("article");
      tarjeta.removeAttribute("data-reveal");
      tarjeta.querySelector("[data-suscribir-id]").setAttribute("disabled", "");
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
        '<span class="text-emerald-800 font-bold">' + e(especie.nombre) + "</span>" +
        (numero ? ' <span class="text-stone-600">' + e(numero) + "</span>" : "") +
        '<span class="text-stone-400"> · se mostrará así en el catálogo</span>';
    }

    pintarGaleriaFormulario() {
      this.catalogo.pintarGaleria(
        document.getElementById("galeria-arbol"),
        this.formulario.especie,
        (foto) => {
          this.formulario.foto = foto;
          this.catalogo.pintarCredito(document.getElementById("credito-arbol"), foto);
          this.pintarVistaPrevia();
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
        estimacion_cosecha_kg: Number(document.getElementById("arbol-cosecha").value),
        imagen: this.formulario.foto.url,
        productor: sesion.nombre
      };

      if (!bodyData.ubicacion || !(bodyData.estimacion_cosecha_kg >= 1)) {
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
      window.AgroColab.views.pintarNavbar();
    }

    /* ---------- Inicialización ---------- */

    async init() {
      document.getElementById("btn-subir-arbol").addEventListener("click", () => this.mostrarFormulario());
      document.getElementById("btn-cancelar-arbol").addEventListener("click", () => this.mostrarDashboard());
      const formularioArbol = document.getElementById("form-subir-arbol");
      formularioArbol.addEventListener("submit", (evento) => this.subirArbol(evento));
      formularioArbol.addEventListener("input", () => this.pintarVistaPrevia());
      formularioArbol.addEventListener("change", () => this.pintarVistaPrevia());
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

      this.pintarNavbarAgricultor();
    }

    async cargar() {
      const sesion = this.auth.leerSesion();
      const nombre = sesion && sesion.nombre ? sesion.nombre.split(" ")[0] : "agricultor";
      document.getElementById("agricultor-saludo").textContent = nombre;
      const fecha = new Date().toLocaleDateString("es-CL", {
        weekday: "long", day: "numeric", month: "long", year: "numeric"
      });
      document.getElementById("agricultor-fecha").textContent = fecha.charAt(0).toUpperCase() + fecha.slice(1);
      this.mostrarDashboardSinAnimar();
      return this.cargarArbolesAgricultor();
    }

    /* Al entrar a la vista siempre se parte en el panel, no en el formulario */
    mostrarDashboardSinAnimar() {
      document.getElementById("vista-agricultor").classList.remove("modo-formulario");
      document.getElementById("formulario-arbol").classList.add("hidden");
      document.getElementById("dashboard-agricultor").classList.remove("hidden");
    }
  }

  const agricultorService = new AgricultorService();
  window.AgroColab.agricultor = agricultorService;
})();
