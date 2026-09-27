/**
 * Fotografa o Roxin PWA sem abrir janela na tela do Roger.
 *
 *   node fotografar.js
 *
 * Roda com --headless=new: a regra do cofre e que o que for visual acontece em
 * segundo plano, nunca roubando a tela dele.
 */
const fs = require('fs');
const path = require('path');

function pw() {
  try { return require('playwright-core'); } catch (_) {}
  const c = 'D:/Claude Code/Claude Mestre v2/projetos';
  for (const p of fs.readdirSync(c)) {
    for (const s of ['app', '']) {
      const nm = path.join(c, p, s, 'node_modules', 'playwright-core');
      if (fs.existsSync(nm)) { try { return require(nm); } catch (_) {} }
    }
  }
  throw new Error('playwright-core nao encontrado');
}

function chrome() {
  for (const c of [
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
  ]) if (fs.existsSync(c)) return c;
  throw new Error('navegador nao encontrado');
}

(async () => {
  const { chromium } = pw();
  const b = await chromium.launch({
    executablePath: chrome(),
    headless: true,
    args: ['--headless=new', '--autoplay-policy=no-user-gesture-required', '--mute-audio'],
  });
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
  const p = await ctx.newPage();
  await p.goto('https://roxin.rogeriofleming.com.br/', { waitUntil: 'networkidle' });
  await p.screenshot({ path: 'D:/Player Musica/tmp/pwa_vazio.png' });
  await p.setInputFiles('#arquivo', 'D:/Player Musica/pacotes/Roxin_Ghibli-melhores.zip');
  await p.waitForSelector('#lista .faixa', { timeout: 120000 });
  await p.locator('#lista .faixa').first().click();
  await p.waitForTimeout(2500);
  await p.screenshot({ path: 'D:/Player Musica/tmp/pwa_tocando.png' });
  await b.close();
  console.log('fotos salvas em tmp/');
})();
