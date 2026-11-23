// Genera docs/guias/Manual_de_uso_e_instalacion.pdf desde manual.html, con el diseño del
// informe final.
//
// Uso, desde la raíz del repositorio:  node docs/guias/fuente/generar_manual.mjs
// Requisitos: Node 18+, Google Chrome, Chromium o Microsoft Edge, y pdftotext (poppler-utils;
// en Windows viene con Git for Windows). Si el navegador no se encuentra solo, indica su
// ruta en la variable CHROME.
//
// A diferencia del informe, todo sale en una sola impresión: la portada y el índice no
// avanzan el contador de páginas (counter-increment: page 0), así que el cuerpo se numera
// desde la sección 1 sin unir dos PDF. Pasos:
//   1. Lee del DOM las entradas del índice (títulos, figuras y tablas) que arma manual.html.
//   2. Imprime, busca en el texto del PDF la página de cada entrada y la escribe en
//      window.PAGINAS. Repite hasta que los números no cambien.
import { execFileSync, spawnSync } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const aqui = dirname(fileURLToPath(import.meta.url));
const raiz = resolve(aqui, "..", "..", "..");
const fuente = join(aqui, "manual.html");
const temporal = join(aqui, ".manual-generando.html"); // en la misma carpeta, por las rutas relativas
const destino = join(raiz, "docs", "guias", "Manual_de_uso_e_instalacion.pdf");
const perfil = mkdtempSync(join(tmpdir(), "manual-chrome-"));

function buscarNavegador() {
  if (process.env.CHROME) return process.env.CHROME;
  const candidatos = {
    win32: [
      join(process.env.PROGRAMFILES || "C:\\Program Files", "Google", "Chrome", "Application", "chrome.exe"),
      join(process.env["PROGRAMFILES(X86)"] || "C:\\Program Files (x86)", "Google", "Chrome", "Application", "chrome.exe"),
      join(process.env.LOCALAPPDATA || "", "Google", "Chrome", "Application", "chrome.exe"),
      join(process.env["PROGRAMFILES(X86)"] || "C:\\Program Files (x86)", "Microsoft", "Edge", "Application", "msedge.exe"),
    ],
    darwin: ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"],
  }[process.platform] || [];
  const encontrado = candidatos.find((ruta) => ruta && existsSync(ruta));
  if (encontrado) return encontrado;
  for (const nombre of ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]) {
    if (spawnSync(nombre, ["--version"]).status === 0) return nombre;
  }
  throw new Error("No se encontró Chrome, Chromium ni Edge. Indica su ruta en la variable CHROME.");
}

const navegador = buscarNavegador();
const base = [
  "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
  `--user-data-dir=${perfil}`, "--virtual-time-budget=15000", "--run-all-compositor-stages-before-draw",
];

function chrome(args) {
  const r = spawnSync(navegador, [...base, ...args], { encoding: "utf-8", maxBuffer: 64 * 1024 * 1024 });
  if (r.status !== 0) throw new Error(`El navegador terminó con error:\n${r.stderr}`);
  return r.stdout;
}

const imprimir = (html, pdf) => chrome(["--no-pdf-header-footer", `--print-to-pdf=${pdf}`, pathToFileURL(html).href]);

function textosPorPagina(pdf) {
  return execFileSync("pdftotext", ["-enc", "UTF-8", pdf, "-"], { maxBuffer: 64 * 1024 * 1024 })
    .toString("utf-8").split("\f").slice(0, -1);
}

const regex = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
function buscarPagina(textos, desde, buscar) {
  const figura = buscar.match(/^(Figura|Tabla) (\d+)\.$/);
  const re = figura
    ? new RegExp(`(^|\\n)\\s*${figura[1]} ${figura[2]}\\.\\s`)
    : new RegExp(`(^|\\n)\\s*(\\d+(\\.\\d+)?\\s+)?${regex(buscar).replace(/\s+/g, "\\s+")}\\s*(\\n|$)`);
  for (let i = desde; i < textos.length; i++) if (re.test(textos[i])) return i;
  return -1;
}

const html = readFileSync(fuente, "utf-8");
const conPaginas = (paginas) =>
  html.replace("</head>", `<script>window.PAGINAS = ${JSON.stringify(paginas)};</script>\n</head>`);

try {
  // ---------- 1. Entradas del índice ----------
  writeFileSync(temporal, conPaginas({}));
  const dom = chrome(["--dump-dom", pathToFileURL(temporal).href]);
  const atributo = dom.match(/data-entradas="([^"]*)"/);
  if (!atributo) throw new Error("manual.html no generó las entradas del índice (¿falló su script?).");
  const entradas = JSON.parse(atributo[1].replace(/&quot;/g, '"').replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">"));

  // Las referencias «Tabla N» y «Figura N» del texto tienen que existir
  const cuantas = (tipo) => entradas.filter((e) => e.buscar.startsWith(tipo)).length;
  for (const [, tipo, n] of html.matchAll(/class="ref">(Tabla|Figura) (\d+)</g)) {
    if (Number(n) > cuantas(tipo)) console.warn(`Atención: el texto cita ${tipo} ${n}, pero solo hay ${cuantas(tipo)}.`);
  }

  // ---------- 2. Páginas estables ----------
  const pdf = join(perfil, "manual.pdf");
  let paginas = {};
  let anterior = "";
  for (let intento = 1; intento <= 4; intento++) {
    writeFileSync(temporal, conPaginas(paginas));
    imprimir(temporal, pdf);
    const textos = textosPorPagina(pdf);
    // El cuerpo empieza en la primera página que dice «SECCIÓN 1» (el índice no lo dice)
    const inicio = textos.findIndex((t) => /SECCI[ÓO]N\s+1\b/i.test(t));
    if (inicio === -1) throw new Error("No se encontró el inicio del cuerpo («Sección 1») en el PDF.");
    const nuevas = {};
    const faltan = [];
    for (const e of entradas) {
      const i = buscarPagina(textos, inicio, e.buscar);
      if (i === -1) faltan.push(e.buscar); else nuevas[e.id] = String(i - inicio + 1);
    }
    if (faltan.length) console.warn("No se encontró en el PDF:", faltan.join(" | "));
    paginas = nuevas;
    const actual = JSON.stringify(paginas);
    if (actual === anterior) {
      writeFileSync(destino, readFileSync(pdf));
      console.log(`Escrito ${destino}`);
      console.log(`${textos.length} páginas: ${inicio} de portada e índice y ${textos.length - inicio} numeradas.`);
      break;
    }
    anterior = actual;
    if (intento === 4) throw new Error("Los números de página no se estabilizaron en 4 intentos.");
  }
} finally {
  rmSync(temporal, { force: true });
  rmSync(perfil, { recursive: true, force: true });
}
