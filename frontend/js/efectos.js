/* Agro-Colab - Servicio de efectos visuales (EfectosService), expuesto como
   AgroColab.efectos:
   - Aparición suave de los bloques marcados con data-reveal al entrar en
     pantalla durante el scroll.
   - Header que se esconde al bajar y vuelve a aparecer al subir.
   Si el usuario pidió reducir el movimiento en su sistema, no se anima nada. */

(function () {
  const AgroColab = (window.AgroColab = window.AgroColab || {});

  class EfectosService {
    constructor() {
      this.observador = null;
      this.ultimoScroll = 0;
      this.reducirMovimiento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    }

    /* ---------- Aparición al hacer scroll ---------- */

    iniciarReveal() {
      const elementos = document.querySelectorAll("[data-reveal]");

      if (this.reducirMovimiento || !("IntersectionObserver" in window)) {
        elementos.forEach((el) => el.removeAttribute("data-reveal"));
        return;
      }

      /* Solo con JS activo se ocultan los bloques: si este archivo falla, la
         página se ve completa igual. */
      document.documentElement.classList.add("js-reveal");

      this.observador = new IntersectionObserver(
        (entradas) => {
          entradas.forEach((entrada) => {
            if (!entrada.isIntersecting) return;
            const el = entrada.target;
            el.classList.add("revelado");
            this.observador.unobserve(el);

            /* Terminada la animación se quita el atributo para que las
               transiciones propias del elemento (hover) sigan funcionando. */
            const alTerminar = (evento) => {
              // transitionend también llega desde los hijos (hover de botones)
              if (evento.target !== el || evento.propertyName !== "transform") return;
              el.removeAttribute("data-reveal");
              el.classList.remove("revelado");
              el.removeEventListener("transitionend", alTerminar);
            };
            el.addEventListener("transitionend", alTerminar);
          });
        },
        { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
      );

      elementos.forEach((el) => this.observador.observe(el));
    }

    /* ---------- Header que se esconde al bajar ---------- */

    iniciarHeader() {
      const headers = document.querySelectorAll("header.sticky");
      if (!headers.length) return;

      let pendiente = false;

      window.addEventListener(
        "scroll",
        () => {
          if (pendiente) return;
          pendiente = true;

          window.requestAnimationFrame(() => {
            const actual = window.scrollY;
            const bajando = actual > this.ultimoScroll;

            headers.forEach((header) => {
              /* Cerca del inicio el header siempre se ve; más abajo se
                 esconde al bajar y reaparece apenas se sube. */
              header.classList.toggle("header--oculto", bajando && actual > 120);
              header.classList.toggle("header--con-scroll", actual > 10);
            });

            this.ultimoScroll = Math.max(actual, 0);
            pendiente = false;
          });
        },
        { passive: true }
      );
    }

    init() {
      this.iniciarReveal();
      this.iniciarHeader();
    }
  }

  const efectosService = new EfectosService();
  window.AgroColab.efectos = efectosService;
})();
