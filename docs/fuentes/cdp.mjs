// Cliente mínimo del protocolo DevTools de Chrome, por tubería (--remote-debugging-pipe).
// Funciona con Node 18 o superior y no necesita dependencias.
import { spawn } from "node:child_process";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

export async function abrirChrome({ ancho = 1440, alto = 900 } = {}) {
  const perfil = mkdtempSync(join(tmpdir(), "cdp-"));
  const proceso = spawn("google-chrome", [
    "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
    "--hide-scrollbars", `--user-data-dir=${perfil}`, "--remote-debugging-pipe",
    `--window-size=${ancho},${alto}`, "about:blank",
  ], { stdio: ["ignore", "ignore", "ignore", "pipe", "pipe"] });
  const escritura = proceso.stdio[3];
  const lectura = proceso.stdio[4];
  const receptores = [];
  let resto = Buffer.alloc(0);
  lectura.on("data", (trozo) => {
    resto = Buffer.concat([resto, trozo]);
    let fin;
    while ((fin = resto.indexOf(0)) !== -1) {
      const msg = JSON.parse(resto.subarray(0, fin).toString());
      resto = resto.subarray(fin + 1);
      receptores.forEach((f) => f(msg));
    }
  });
  let sesion = null;
  let id = 0;
  const pendientes = new Map();
  const oyentes = [];
  receptores.push((msg) => {
    if (msg.id && pendientes.has(msg.id)) {
      const { resolve, reject } = pendientes.get(msg.id);
      pendientes.delete(msg.id);
      msg.error ? reject(new Error(JSON.stringify(msg.error))) : resolve(msg.result);
    } else if (msg.method && msg.sessionId === sesion) {
      oyentes.forEach((f) => f(msg));
    }
  });
  const crudo = (method, params = {}, sessionId) => new Promise((resolve, reject) => {
    const n = ++id;
    pendientes.set(n, { resolve, reject });
    escritura.write(JSON.stringify({ id: n, method, params, ...(sessionId ? { sessionId } : {}) }) + "\0");
  });
  const { targetInfos } = await crudo("Target.getTargets");
  const pagina = targetInfos.find((o) => o.type === "page");
  ({ sessionId: sesion } = await crudo("Target.attachToTarget", { targetId: pagina.targetId, flatten: true }));
  const enviar = (method, params = {}) => crudo(method, params, sesion);
  await enviar("Page.enable");
  await enviar("Runtime.enable");
  await enviar("Emulation.setDeviceMetricsOverride", { width: ancho, height: alto, deviceScaleFactor: 1, mobile: false });
  const errores = [];
  oyentes.push((m) => {
    if (m.method === "Runtime.exceptionThrown") errores.push(m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text);
  });

  const esperarCarga = () => new Promise((r) => {
    const f = (m) => { if (m.method === "Page.loadEventFired") { oyentes.splice(oyentes.indexOf(f), 1); r(); } };
    oyentes.push(f);
  });

  return {
    enviar,
    errores,
    async ir(url) { const c = esperarCarga(); await enviar("Page.navigate", { url }); await c; },
    async recargar() { const c = esperarCarga(); await enviar("Page.reload", {}); await c; },
    async evaluar(expr) {
      const r = await enviar("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true });
      if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
      return r.result.value;
    },
    async esperar(expr, ms = 15000) {
      const fin = Date.now() + ms;
      while (Date.now() < fin) {
        try { if (await this.evaluar(expr)) return; } catch {}
        await new Promise((r) => setTimeout(r, 150));
      }
      throw new Error(`Tiempo agotado esperando: ${expr}`);
    },
    pausa: (ms) => new Promise((r) => setTimeout(r, ms)),
    async captura(ruta, { completa = false } = {}) {
      const { writeFileSync } = await import("node:fs");
      const params = { format: "png" };
      if (completa) params.captureBeyondViewport = true;
      const r = await enviar("Page.captureScreenshot", params);
      writeFileSync(ruta, Buffer.from(r.data, "base64"));
    },
    async pdf(ruta, opciones) {
      const { writeFileSync } = await import("node:fs");
      const r = await enviar("Page.printToPDF", opciones);
      writeFileSync(ruta, Buffer.from(r.data, "base64"));
    },
    cerrar() { proceso.kill(); },
  };
}
