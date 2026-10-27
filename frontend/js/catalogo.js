/* Agro-Colab - Servicio de catálogo de especies frutales y galería de imágenes.

   El backend expone un catálogo cerrado (GET /api/especies) con las especies
   disponibles y, para cada una, las fotos curadas que el agricultor puede usar.
   Este servicio se encarga de pintar el selector de especie y la galería de fotos,
   de modo que nunca se pueda publicar un árbol con un nombre o una foto ajenos
   a la especie declarada. */

class CatalogoService {
  constructor() {
    this.config = window.AgroColab.config;
    this.api = window.AgroColab.api;
    this.especies = [];
    this.cargado = false;
    this.errorCarga = null;
  }

  /* ---------- Carga del catálogo ---------- */

  async pedirCatalogo() {
    if (this.api && typeof this.api.obtenerEspecies === "function") {
      return this.api.obtenerEspecies();
    }

    const respuesta = await fetch(`${this.config.API_URL}/especies`, {
      headers: { "Content-Type": "application/json" }
    });
    if (!respuesta.ok) throw new Error("HTTP " + respuesta.status);
    return respuesta.json();
  }

  async cargar() {
    if (this.cargado) return this.especies;
    try {
      const datos = await this.pedirCatalogo();
      this.especies = Array.isArray(datos) ? datos : [];
      this.errorCarga = null;
    } catch (error) {
      this.especies = [];
      this.errorCarga = error;
      console.error("[Agro-Colab] No se pudo cargar el catálogo de especies:", error);
    }
    this.cargado = true;
    return this.especies;
  }

  porId(especieId) {
    return this.especies.find((especie) => especie.id === especieId) || null;
  }

  /* ---------- Selector de especie ---------- */

  pintarSelect(select) {
    if (!select) return;

    const valorActual = select.value;

    if (this.errorCarga) {
      select.innerHTML = '<option value="">No se pudo cargar el catálogo</option>';
      return;
    }

    select.innerHTML = '<option value="">Selecciona una especie...</option>';

    this.especies.forEach((especie) => {
      const opcion = document.createElement("option");
      opcion.value = especie.id;
      opcion.textContent = especie.emoji + " " + especie.nombre;
      select.appendChild(opcion);
    });

    if (valorActual && this.porId(valorActual)) {
      select.value = valorActual;
    }
  }

  /* ---------- Galería de fotos ---------- */

  pintarGaleria(contenedor, especieId, alElegir, urlSeleccionada) {
    if (!contenedor) return;

    const especie = this.porId(especieId);

    if (!especie) {
      contenedor.innerHTML =
        '<p class="text-stone-400 text-xs text-center py-6 col-span-3">' +
        (this.errorCarga
          ? "No se pudo cargar el catálogo. Revisa tu conexión y recarga la página."
          : "Elige una especie para ver sus fotos disponibles.") +
        "</p>";
      return;
    }

    contenedor.innerHTML = "";

    especie.fotos.forEach((foto) => {
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

      boton.addEventListener("click", () => {
        contenedor.querySelectorAll(".foto-opcion").forEach((otra) => {
          otra.classList.remove("foto-opcion--activa");
        });
        boton.classList.add("foto-opcion--activa");
        if (alElegir) alElegir(foto);
      });

      contenedor.appendChild(boton);
    });
  }

  /* ---------- Crédito de la foto seleccionada ---------- */

  pintarCredito(contenedor, foto) {
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
}

const catalogoService = new CatalogoService();
window.AgroColab.catalogo = catalogoService;
