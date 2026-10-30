/* Agro-Colab - Árbol 3D de la portada (ConstelacionService), expuesto como
   AgroColab.constelacion.

   Un árbol volumétrico hecho de partículas triangulares en la paleta de la
   marca: copa formada por varias esferas, tronco, ramas, raíces y un anillo
   de suelo. Gira lentamente con perspectiva real (lo lejano se ve más chico y
   tenue), se inclina hacia el mouse y la copa se mece con el "viento".
   Solo se anima mientras está en pantalla; con "reducir movimiento" se dibuja
   una vez, quieto. */

(function () {
  const AgroColab = (window.AgroColab = window.AgroColab || {});

  const COLORES_COPA = ["#34d399", "#10b981", "#6ee7b7", "#2dd4bf", "#a3e635", "#15846e", "#fbbf24"];
  const PESOS_COPA = [6, 5, 3, 2, 2, 2, 1.5];
  const COLORES_MADERA = ["#15846e", "#0f766e", "#34d399", "#d97706"];
  const PESOS_MADERA = [4, 3, 1, 1];

  // Lóbulos de la copa: [x, y, z, radio] en el espacio del árbol (y hacia arriba)
  const LOBULOS = [
    [0, 0.42, 0, 0.42],
    [-0.36, 0.3, 0.1, 0.27],
    [0.36, 0.32, -0.08, 0.28],
    [0.05, 0.3, 0.36, 0.26],
    [-0.04, 0.3, -0.36, 0.26],
    [0, 0.78, 0, 0.28]
  ];

  class ConstelacionService {
    constructor() {
      this.canvas = null;
      this.contexto = null;
      this.particulas = [];
      this.visible = false;
      this.cuadro = null;
      this.giro = 0.6;
      this.inclinacionObjetivo = { x: 0, y: 0 };
      this.inclinacion = { x: 0, y: 0 };
      this.ultimoTiempo = 0;
      this.reducirMovimiento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    }

    elegir(colores, pesos) {
      const total = pesos.reduce((a, b) => a + b, 0);
      let r = Math.random() * total;
      for (let i = 0; i < colores.length; i++) {
        r -= pesos[i];
        if (r <= 0) return colores[i];
      }
      return colores[0];
    }

    /* Punto al azar dentro de una esfera, con más densidad cerca de la
       superficie para que se lea el volumen */
    puntoEnEsfera(cx, cy, cz, radio) {
      const u = Math.random() * 2 - 1;
      const angulo = Math.random() * Math.PI * 2;
      const anillo = Math.sqrt(1 - u * u);
      const r = radio * Math.pow(Math.random(), 0.35);
      return [cx + r * anillo * Math.cos(angulo), cy + r * u, cz + r * anillo * Math.sin(angulo)];
    }

    agregar(x, y, z, color, tamano, opacidad, tipo) {
      this.particulas.push({
        x, y, z, color, tamano, opacidad, tipo,
        angulo: Math.random() * Math.PI * 2,
        fase: Math.random() * Math.PI * 2
      });
    }

    crearArbol() {
      this.particulas = [];

      // Copa
      for (let i = 0; i < 1500; i++) {
        const [cx, cy, cz, radio] = LOBULOS[Math.floor(Math.random() * LOBULOS.length)];
        const [x, y, z] = this.puntoEnEsfera(cx, cy, cz, radio);
        this.agregar(x, y, z, this.elegir(COLORES_COPA, PESOS_COPA), 2.2 + Math.random() * 2.6, 0.55 + Math.random() * 0.45, "copa");
      }

      // Tronco: cilindro que se angosta hacia arriba
      for (let i = 0; i < 260; i++) {
        const t = Math.random();
        const y = -0.62 + t * 0.78;
        const radio = 0.085 - t * 0.04;
        const angulo = Math.random() * Math.PI * 2;
        const r = radio * Math.sqrt(Math.random());
        this.agregar(Math.cos(angulo) * r, y, Math.sin(angulo) * r, this.elegir(COLORES_MADERA, PESOS_MADERA), 1.8 + Math.random() * 1.8, 0.75, "tronco");
      }

      // Ramas: del tronco a cada lóbulo lateral
      LOBULOS.slice(1).forEach(([lx, ly, lz]) => {
        for (let i = 0; i < 45; i++) {
          const t = Math.random();
          const curva = Math.sin(t * Math.PI) * 0.05;
          this.agregar(
            lx * t * 0.8 + (Math.random() - 0.5) * 0.025,
            0.08 + (ly - 0.08) * t + curva,
            lz * t * 0.8 + (Math.random() - 0.5) * 0.025,
            this.elegir(COLORES_MADERA, PESOS_MADERA), 1.6 + Math.random() * 1.4, 0.7, "rama"
          );
        }
      });

      // Raíces: se abren a ras de suelo
      for (let raiz = 0; raiz < 7; raiz++) {
        const direccion = (raiz / 7) * Math.PI * 2 + Math.random() * 0.4;
        const largo = 0.22 + Math.random() * 0.14;
        for (let i = 0; i < 22; i++) {
          const t = Math.random();
          this.agregar(
            Math.cos(direccion) * largo * t,
            -0.62 - Math.sin(t * Math.PI) * 0.03,
            Math.sin(direccion) * largo * t,
            this.elegir(COLORES_MADERA, PESOS_MADERA), 1.5 + Math.random() * 1.3, 0.6, "raiz"
          );
        }
      }

      // Anillo de suelo tenue
      for (let i = 0; i < 220; i++) {
        const angulo = Math.random() * Math.PI * 2;
        const r = 0.45 + Math.random() * 0.35;
        this.agregar(Math.cos(angulo) * r, -0.64, Math.sin(angulo) * r, this.elegir(COLORES_COPA, PESOS_COPA), 1.4 + Math.random() * 1.2, 0.18 + Math.random() * 0.2, "suelo");
      }

      // Partículas sueltas alrededor, a distintas profundidades
      for (let i = 0; i < 160; i++) {
        this.agregar((Math.random() - 0.5) * 2.4, (Math.random() - 0.4) * 2, (Math.random() - 0.5) * 2.4,
          this.elegir(COLORES_COPA, PESOS_COPA), 1.4 + Math.random() * 1.6, 0.15 + Math.random() * 0.2, "ambiente");
      }
    }

    ajustarTamano() {
      const caja = this.canvas.getBoundingClientRect();
      const densidad = Math.min(window.devicePixelRatio || 1, 2);
      this.ancho = caja.width;
      this.alto = caja.height;
      this.canvas.width = Math.round(caja.width * densidad);
      this.canvas.height = Math.round(caja.height * densidad);
      this.contexto.setTransform(densidad, 0, 0, densidad, 0, 0);
    }

    dibujar(tiempo) {
      const ctx = this.contexto;
      const delta = this.ultimoTiempo ? Math.min(tiempo - this.ultimoTiempo, 50) : 16;
      this.ultimoTiempo = tiempo;

      if (!this.reducirMovimiento) {
        this.giro += delta * 0.00018;
        // La inclinación sigue al mouse con suavidad
        this.inclinacion.x += (this.inclinacionObjetivo.x - this.inclinacion.x) * 0.06;
        this.inclinacion.y += (this.inclinacionObjetivo.y - this.inclinacion.y) * 0.06;
      }

      const yaw = this.giro + this.inclinacion.x;
      const pitch = -0.32 + this.inclinacion.y;
      const cosY = Math.cos(yaw), sinY = Math.sin(yaw);
      const cosX = Math.cos(pitch), sinX = Math.sin(pitch);
      const escala = Math.min(this.ancho, this.alto) * 0.5;
      const camara = 3.4;
      const centroX = this.ancho / 2;
      const centroY = this.alto * 0.56;
      const viento = this.reducirMovimiento ? 0 : tiempo * 0.0007;

      const proyectadas = [];
      for (const p of this.particulas) {
        let x = p.x, y = p.y, z = p.z;

        // La copa se mece: más arriba, más movimiento
        if (p.tipo === "copa" || p.tipo === "ambiente") {
          const fuerza = Math.max(0, y + 0.1) * 0.035;
          x += Math.sin(viento + p.fase) * fuerza;
          z += Math.cos(viento * 0.8 + p.fase) * fuerza;
        }

        // Rotación (eje Y y luego eje X) y perspectiva
        const x1 = x * cosY - z * sinY;
        const z1 = x * sinY + z * cosY;
        const y2 = y * cosX - z1 * sinX;
        const z2 = y * sinX + z1 * cosX;
        const perspectiva = camara / (camara - z2);

        proyectadas.push({
          p,
          sx: centroX + x1 * escala * perspectiva,
          sy: centroY - y2 * escala * perspectiva,
          profundidad: z2,
          perspectiva
        });
      }

      // De atrás hacia adelante, para que lo cercano tape a lo lejano
      proyectadas.sort((a, b) => a.profundidad - b.profundidad);

      ctx.clearRect(0, 0, this.ancho, this.alto);
      ctx.lineWidth = 1.1;
      for (const { p, sx, sy, profundidad, perspectiva } of proyectadas) {
        // Lo lejano se ve más tenue: profundidad -1 (atrás) a 1 (adelante)
        const luz = 0.35 + 0.65 * Math.min(Math.max((profundidad + 1) / 2, 0), 1);
        const r = p.tamano * perspectiva;
        const angulo = p.angulo + (this.reducirMovimiento ? 0 : tiempo * 0.0004);

        ctx.globalAlpha = p.opacidad * luz;
        ctx.strokeStyle = p.color;
        ctx.beginPath();
        for (let k = 0; k < 3; k++) {
          const a = angulo + (k * Math.PI * 2) / 3;
          const px = sx + Math.cos(a) * r;
          const py = sy + Math.sin(a) * r;
          if (k === 0) ctx.moveTo(px, py);
          else ctx.lineTo(px, py);
        }
        ctx.closePath();
        ctx.stroke();
      }
      ctx.globalAlpha = 1;
    }

    animar(tiempo) {
      if (!this.visible) {
        this.cuadro = null;
        return;
      }
      this.dibujar(tiempo);
      this.cuadro = requestAnimationFrame((t) => this.animar(t));
    }

    arrancar() {
      if (this.reducirMovimiento || this.cuadro || !this.visible) return;
      this.ultimoTiempo = 0;
      this.cuadro = requestAnimationFrame((t) => this.animar(t));
    }

    init() {
      this.canvas = document.getElementById("constelacion");
      if (!this.canvas || !this.canvas.getContext) return;
      this.contexto = this.canvas.getContext("2d");
      this.crearArbol();
      this.ajustarTamano();
      this.dibujar(0);

      window.addEventListener("resize", () => {
        this.ajustarTamano();
        this.dibujar(performance.now());
      }, { passive: true });

      // El árbol se inclina hacia donde está el mouse
      const zona = this.canvas.parentElement;
      zona.addEventListener("pointermove", (evento) => {
        const caja = zona.getBoundingClientRect();
        const nx = (evento.clientX - caja.left) / caja.width - 0.5;
        const ny = (evento.clientY - caja.top) / caja.height - 0.5;
        this.inclinacionObjetivo = { x: nx * 0.9, y: ny * 0.45 };
      }, { passive: true });
      zona.addEventListener("pointerleave", () => {
        this.inclinacionObjetivo = { x: 0, y: 0 };
      });

      /* Solo se anima mientras está en pantalla (y la vista no está oculta) */
      if ("IntersectionObserver" in window) {
        new IntersectionObserver((entradas) => {
          this.visible = entradas[0].isIntersecting;
          if (this.visible) {
            // Al volver a mostrarse la vista, el canvas pudo tener tamaño 0
            if (!this.ancho) this.ajustarTamano();
            this.dibujar(performance.now());
            this.arrancar();
          }
        }).observe(this.canvas);
      }
    }
  }

  const constelacion = new ConstelacionService();
  AgroColab.constelacion = constelacion;
})();
