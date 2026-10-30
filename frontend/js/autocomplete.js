/* Agro-Colab - Servicio de autocompletado de direcciones con Photon (OpenStreetMap).
   Muestra sugerencias de direcciones reales mientras el usuario escribe,
   sin usar la geolocalización del dispositivo. */

class AutocompleteService {
  constructor() {
    this.PHOTON_URL = "https://photon.komoot.io/api/";
    this.temporizador = null;
  }

  formatearDireccion(lugar) {
    const p = lugar.properties || {};
    const partes = [];

    if (p.name) partes.push(p.name);
    if (p.street && p.name !== p.street) partes.push(p.street);
    if (p.housenumber && p.street) partes[1] = `${p.street} ${p.housenumber}`;
    if (p.city) partes.push(p.city);
    if (p.state) partes.push(p.state);

    return partes.filter(Boolean).join(", ");
  }

  async buscarSugerencias(texto) {
    if (!texto || texto.length < 3) return [];

    try {
      const url = `${this.PHOTON_URL}?q=${encodeURIComponent(texto)}&limit=5`;
      const respuesta = await fetch(url);
      const datos = await respuesta.json();
      return datos.features || [];
    } catch (error) {
      return [];
    }
  }

  mostrarSugerencias(contenedor, lugares) {
    if (!lugares.length) {
      contenedor.classList.add("hidden");
      contenedor.innerHTML = "";
      return;
    }

    /* Los nombres vienen de OpenStreetMap, que cualquiera puede editar: se
       escapan para que no se pueda inyectar HTML a través de una dirección. */
    contenedor.innerHTML = lugares
      .map((lugar, indice) => {
        return `
          <button
            type="button"
            class="sugerencia-item"
            data-indice="${indice}"
            onclick="AgroColab.autocomplete.seleccionarDireccion(${indice}, '${contenedor.id}')"
          >
            <i class="fa-solid fa-location-dot text-emerald-600 mr-2"></i>
            <span>${window.AgroColab.ui.escapar(this.formatearDireccion(lugar))}</span>
          </button>
        `;
      })
      .join("");

    contenedor.classList.remove("hidden");
  }

  ocultarSugerencias(contenedor) {
    contenedor.classList.add("hidden");
    contenedor.innerHTML = "";
  }

  /* Función llamada desde el oninput del HTML. */
  async buscarDireccion(input) {
    const texto = input.value.trim();
    const contenedor = input.parentElement.querySelector(".sugerencias-lista");
    if (!contenedor) return;

    if (this.temporizador) clearTimeout(this.temporizador);

    if (texto.length < 3) {
      this.ocultarSugerencias(contenedor);
      return;
    }

    this.temporizador = setTimeout(async () => {
      const lugares = await this.buscarSugerencias(texto);
      this.mostrarSugerencias(contenedor, lugares);
    }, 350);
  }

  seleccionarDireccion(indice, contenedorId) {
    const contenedor = document.getElementById(contenedorId);
    if (!contenedor) return;

    const boton = contenedor.querySelector(`[data-indice="${indice}"]`);
    const texto = boton ? boton.textContent.trim() : "";
    if (!texto) return;

    const input = contenedor.parentElement.querySelector("input");
    if (input) {
      input.value = texto;
      this.ocultarSugerencias(contenedor);
    }
  }

  init() {
    /* Ocultar sugerencias al hacer clic fuera del input. */
    document.addEventListener("click", (evento) => {
      document.querySelectorAll(".sugerencias-lista").forEach((lista) => {
        if (!lista.parentElement.contains(evento.target)) {
          lista.classList.add("hidden");
        }
      });
    });
  }
}

const autocompleteService = new AutocompleteService();
window.AgroColab.autocomplete = autocompleteService;
