/* Agro-Colab - Autocompletado de direcciones con Photon (OpenStreetMap).
   Muestra sugerencias de direcciones reales mientras el usuario escribe,
   sin usar la geolocalización del dispositivo. */

(function () {
  const AgroColab = (window.AgroColab = window.AgroColab || {});

  const PHOTON_URL = "https://photon.komoot.io/api/";
  let temporizador = null;

  function formatearDireccion(lugar) {
    const p = lugar.properties || {};
    const partes = [];

    if (p.name) partes.push(p.name);
    if (p.street && p.name !== p.street) partes.push(p.street);
    if (p.housenumber && p.street) partes[1] = `${p.street} ${p.housenumber}`;
    if (p.city) partes.push(p.city);
    if (p.state) partes.push(p.state);

    return partes.filter(Boolean).join(", ");
  }

  async function buscarSugerencias(texto) {
    if (!texto || texto.length < 3) return [];

    try {
      const url = `${PHOTON_URL}?q=${encodeURIComponent(texto)}&limit=5`;
      const respuesta = await fetch(url);
      const datos = await respuesta.json();
      return datos.features || [];
    } catch (error) {
      return [];
    }
  }

  function mostrarSugerencias(contenedor, lugares) {
    if (!lugares.length) {
      contenedor.classList.add("hidden");
      contenedor.innerHTML = "";
      return;
    }

    contenedor.innerHTML = lugares
      .map(function (lugar, indice) {
        return `
          <button
            type="button"
            class="sugerencia-item"
            data-indice="${indice}"
            onclick="AgroColab.autocomplete.seleccionarDireccion(${indice}, '${contenedor.id}')"
          >
            <i class="fa-solid fa-location-dot text-emerald-600 mr-2"></i>
            <span>${formatearDireccion(lugar)}</span>
          </button>
        `;
      })
      .join("");

    contenedor.classList.remove("hidden");
  }

  function ocultarSugerencias(contenedor) {
    contenedor.classList.add("hidden");
    contenedor.innerHTML = "";
  }

  /* Función llamada desde el oninput del HTML. */
  async function buscarDireccion(input) {
    const texto = input.value.trim();
    const contenedor = input.parentElement.querySelector(".sugerencias-lista");
    if (!contenedor) return;

    if (temporizador) clearTimeout(temporizador);

    if (texto.length < 3) {
      ocultarSugerencias(contenedor);
      return;
    }

    temporizador = setTimeout(async function () {
      const lugares = await buscarSugerencias(texto);
      mostrarSugerencias(contenedor, lugares);
    }, 350);
  }

  function seleccionarDireccion(indice, contenedorId) {
    const contenedor = document.getElementById(contenedorId);
    if (!contenedor) return;

    const boton = contenedor.querySelector(`[data-indice="${indice}"]`);
    const texto = boton ? boton.textContent.trim() : "";
    if (!texto) return;

    const input = contenedor.parentElement.querySelector("input");
    if (input) {
      input.value = texto;
      ocultarSugerencias(contenedor);
    }
  }

  function init() {
    /* Ocultar sugerencias al hacer clic fuera del input. */
    document.addEventListener("click", function (evento) {
      document.querySelectorAll(".sugerencias-lista").forEach(function (lista) {
        if (!lista.parentElement.contains(evento.target)) {
          lista.classList.add("hidden");
        }
      });
    });
  }

  AgroColab.autocomplete = { init, buscarDireccion, seleccionarDireccion };
})();
