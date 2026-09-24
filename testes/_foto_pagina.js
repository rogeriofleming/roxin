#!/usr/bin/env node
/*
 * _foto_pagina.js — tira uma foto PNG COM CANAL ALFA de uma pagina local, num
 * Chrome de verdade. Serve ao teste_sombra_mini.py: e o alfa dos pixels da borda
 * que diz se a sombra do vidro cabe dentro da janela ou e cortada num quadrado.
 *
 *   node _foto_pagina.js <arquivo.html> <largura> <altura> <saida.png> [esperaMs]
 *
 * Dependencia: playwright-core de qualquer projetos/<x>/app/node_modules do cofre
 * (o mesmo caminho que a skill verificar-app-browser usa) + Chrome/Edge do sistema.
 */
const fs = require('fs');
const path = require('path');

const COFRE = 'D:/Claude Code/Claude Mestre v2';

function acharPlaywright() {
  try { return require('playwright-core'); } catch (_) {}
  const projetos = path.join(COFRE, 'projetos');
  if (fs.existsSync(projetos)) {
    for (const p of fs.readdirSync(projetos)) {
      for (const sub of ['app', '.']) {
        const nm = path.join(projetos, p, sub, 'node_modules', 'playwright-core');
        if (fs.existsSync(nm)) { try { return require(nm); } catch (_) {} }
      }
    }
  }
  console.error('ERRO: playwright-core nao encontrado no cofre.');
  process.exit(2);
}

function acharChrome() {
  const cands = [
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
    'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  ];
  for (const c of cands) if (fs.existsSync(c)) return c;
  console.error('ERRO: nem Chrome nem Edge encontrados.');
  process.exit(2);
}

const [arq, larg, alt, saida, espera] = process.argv.slice(2);
if (!arq || !larg || !alt || !saida) {
  console.error('Uso: node _foto_pagina.js <arquivo.html> <largura> <altura> <saida.png> [esperaMs]');
  process.exit(2);
}

(async () => {
  const { chromium } = acharPlaywright();
  const browser = await chromium.launch({
    executablePath: acharChrome(),
    args: ['--allow-file-access-from-files'],
  });
  const pag = await browser.newPage({
    viewport: { width: Number(larg), height: Number(alt) },
    deviceScaleFactor: 1,
  });
  const erros = [];
  pag.on('pageerror', e => erros.push(String(e)));
  await pag.goto(require('url').pathToFileURL(path.resolve(arq)).href);
  await pag.waitForTimeout(Number(espera || 600));
  await pag.screenshot({ path: saida, omitBackground: true });
  await browser.close();
  if (erros.length) console.log('erros de JS: ' + erros.join(' | '));
  console.log('foto: ' + saida);
})();
