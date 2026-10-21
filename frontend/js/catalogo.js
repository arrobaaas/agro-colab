/* Agro-Colab - Catálogo de especies frutales y galería de imágenes.

   El backend expone un catálogo cerrado (GET /api/especies) con las especies
   disponibles y, para cada una, las fotos curadas que el agricultor puede usar.
   Este módulo se encarga de pintar el selector de especie y la galería de fotos,
   de modo que nunca se pueda publicar un árbol con un nombre o una foto ajenos
   a la especie declarada. */

(function () {
  const AgroColab = (window.AgroColab = window.AgroColab || {});
  const { config } = AgroColab;

  let especies = [];
  let cargado = false;
  let errorCarga = null;

  /* ---------- Carga del catálogo ---------- */

  /* Pide el catálogo a la API. Se usa api.obtenerEspecies() cuando existe, y si
     el navegador tiene cacheada una versión anterior de api.js (que no lo tenía)
     se hace el request directo, para que un archivo viejo en caché no deje el
     formulario sin opciones. */
  async function pedirCatalogo() {
    if (AgroColab.api && typeof AgroColab.api.obtenerEspecies === "function") {
      return AgroColab.api.obtenerEspecies();
    }

    const respuesta = await fetch(`${config.API_URL}/especies`, {
      headers: { "Content-Type": "application/json" }
    });
    if (!respuesta.ok) throw new Error("HTTP " + respuesta.status);
    return respuesta.json();
  }

  async function cargar() {
    if (cargado) return especies;
    try {
      const datos = await pedirCatalogo();
      especies = Array.isArray(datos) ? datos : [];
      errorCarga = null;
    } catch (error) {
      especies = [];
      errorCarga = error;
      console.error("[Agro-Colab] No se pudo cargar el catálogo de especies:", error);
    }
    cargado = true;
    return especies;
  }

  function listar() {
    return especies;
  }

  function porId(especieId) {
    return especies.find(function (especie) {
      return especie.id === especieId;
    }) || null;
  }

  /* ---------- Selector de especie ---------- */

  function pintarSelect(select) {
    if (!select) return;

    const valorActual = select.value;

    if (errorCarga) {
      select.innerHTML = '<option value="">No se pudo cargar el catálogo</option>';
      return;
    }

    select.innerHTML = '<option value="">Selecciona una especie...</option>';

    especies.forEach(function (especie) {
      const opcion = document.createElement("option");
      opcion.value = especie.id;
      opcion.textContent = especie.emoji + " " + especie.nombre;
      select.appendChild(opcion);
    });

    if (valorActual && porId(valorActual)) {
      select.value = valorActual;
    }
  }

  /* ---------- Galería de fotos ---------- */

  function pintarGaleria(contenedor, especieId, alElegir, urlSeleccionada) {
    if (!contenedor) return;

    const especie = porId(especieId);

    if (!especie) {
      contenedor.innerHTML =
        '<p class="text-stone-400 text-xs text-center py-6 col-span-3">' +
        (errorCarga
          ? "No se pudo cargar el catálogo. Revisa tu conexión y recarga la página."
          : "Elige una especie para ver sus fotos disponibles.") +
        "</p>";
      return;
    }

    contenedor.innerHTML = "";

    especie.fotos.forEach(function (foto) {
      const boton = document.createElement("button");
      boton.type = "button";
      boton.className = "foto-opcion";
      boton.dataset.url = foto.url;
      boton.setAttribute("aria-label", foto.titulo);

      if (urlSeleccionada && urlSeleccionada === foto.url) {
        boton.classList.add("foto-opcion--activa");
      }

      boton.innerHTML =
        '<img src="' + foto.url + '" alt="' + foto.titulo + '" loading="lazy" class="w-full h-full object-cover">';

      boton.addEventListener("click", function () {
        contenedor.querySelectorAll(".foto-opcion").forEach(function (otra) {
          otra.classList.remove("foto-opcion--activa");
        });
        boton.classList.add("foto-opcion--activa");
        if (alElegir) alElegir(foto);
      });

      contenedor.appendChild(boton);
    });
  }

  /* ---------- Crédito de la foto seleccionada ---------- */

  function pintarCredito(contenedor, foto) {
    if (!contenedor) return;

    if (!foto) {
      contenedor.innerHTML = "";
      return;
    }

    contenedor.innerHTML =
      '<i class="fa-solid fa-camera text-stone-400 mr-1"></i>' +
      "Foto: " + foto.autor + " · " + foto.licencia + " · " +
      '<a href="' + foto.fuente + '" target="_blank" rel="noopener" class="underline hover:text-emerald-700">Wikimedia Commons</a>';
  }

  AgroColab.catalogo = {
    cargar,
    listar,
    porId,
    pintarSelect,
    pintarGaleria,
    pintarCredito
  };
})();
