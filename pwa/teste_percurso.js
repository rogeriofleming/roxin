/**
 * Prova o percurso inteiro do Roxin PWA num navegador de verdade.
 *
 *   node teste_percurso.js [url]
 *
 * NAO e "abriu a pagina". E: importar o .zip de VERDADE (o mesmo que o Roger vai
 * baixar do Drive), conferir que as 27 faixas entraram, mandar tocar e MEDIR que
 * o audio avancou. Cada passo cobra um numero, nao uma impressao.
 *
 * O Chrome nao e o iPhone -- o que passa aqui ainda precisa passar no aparelho
 * dele. Mas o que falha aqui nao teria chance nenhuma la.
 */
const path = require('path');
const fs = require('fs');

// mesma busca do verificar.js do cofre: nada pra instalar
function acharPlaywright() {
  try { return require('playwright-core'); } catch (_) {}
  const cofre = 'D:/Claude Code/Claude Mestre v2/projetos';
  for (const p of fs.readdirSync(cofre)) {
    for (const sub of ['app', '']) {
      const nm = path.join(cofre, p, sub, 'node_modules', 'playwright-core');
      if (fs.existsSync(nm)) { try { return require(nm); } catch (_) {} }
    }
  }
  throw new Error('playwright-core nao encontrado');
}

function acharChrome() {
  for (const c of [
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
  ]) if (fs.existsSync(c)) return c;
  throw new Error('Chrome/Edge nao encontrado');
}

const URL_ALVO = process.argv[2] || 'https://roxin.rogeriofleming.com.br/';
const PACOTE = 'D:/Player Musica/pacotes/Roxin_Ghibli-melhores.zip';

const verdes = [];
const vermelhos = [];
function checa(ok, titulo, detalhe = '') {
  (ok ? verdes : vermelhos).push(titulo);
  console.log(`  ${ok ? 'OK   ' : 'FALHA'} ${titulo}${!ok && detalhe ? '  -- ' + detalhe : ''}`);
  return ok;
}

(async () => {
  const { chromium } = acharPlaywright();
  const browser = await chromium.launch({
    executablePath: acharChrome(),
    headless: true,
    // sem isto o Chrome headless recusa tocar audio sem clique, e o teste
    // reprovaria por politica do navegador, nao por defeito do app
    args: ['--autoplay-policy=no-user-gesture-required', '--mute-audio'],
  });
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const pag = await ctx.newPage();
  const errosJS = [];
  pag.on('pageerror', (e) => errosJS.push(String(e)));
  pag.on('console', (m) => { if (m.type() === 'error') errosJS.push(m.text()); });

  console.log(`\nAlvo: ${URL_ALVO}`);
  console.log(`Pacote: ${path.basename(PACOTE)} (${(fs.statSync(PACOTE).size / 1048576).toFixed(1)} MB)\n`);

  console.log('1. A casa abre');
  await pag.goto(URL_ALVO, { waitUntil: 'networkidle' });
  checa(await pag.locator('#vazio').isVisible(), 'a tela de boas-vindas aparece');
  checa((await pag.locator('h1').textContent()).includes('Roxin'), 'o nome esta na tela');
  const temSW = await pag.evaluate(() => 'serviceWorker' in navigator);
  checa(temSW, 'o navegador aceita service worker (necessario pro offline)');

  console.log('\n2. Trazer o pacote de verdade');
  await pag.setInputFiles('#arquivo', PACOTE);
  await pag.waitForSelector('#lista .faixa', { timeout: 120000 });
  const n = await pag.locator('#lista .faixa').count();
  checa(n === 27, `as 27 faixas entraram`, `entraram ${n}`);
  const comCapa = await pag.evaluate(() =>
    [...document.querySelectorAll('#lista .faixa img')].filter((i) => i.src && i.src.startsWith('blob:')).length);
  checa(comCapa === 27, 'as 27 capas entraram', `entraram ${comCapa}`);
  const primeiro = await pag.locator('#lista .faixa .nome').first().textContent();
  checa(/chihiro/i.test(primeiro), 'a lista sai em ordem alfabetica', primeiro);
  checa(await pag.locator('#lista .faixa .dur').first().textContent() !== '--:--',
    'a duracao veio do indice, nao ficou em branco');

  console.log('\n3. Guardado DENTRO do aparelho (OPFS)');
  const noDisco = await pag.evaluate(async () => {
    const raiz = await navigator.storage.getDirectory();
    const acervo = await raiz.getDirectoryHandle('acervo');
    let pacotes = 0, arquivos = 0;
    for await (const [, h] of acervo.entries()) {
      if (h.kind !== 'directory') continue;
      pacotes++;
      const mus = await h.getDirectoryHandle('musicas');
      for await (const _ of mus.entries()) arquivos++;
    }
    const e = await navigator.storage.estimate();
    return { pacotes, arquivos, usado: e.usage, teto: e.quota };
  });
  checa(noDisco.pacotes === 1, 'um pacote gravado', String(noDisco.pacotes));
  checa(noDisco.arquivos === 27, 'as 27 musicas estao no disco do app', String(noDisco.arquivos));
  checa(noDisco.usado > 90 * 1048576, 'ocupou o tamanho esperado (~99 MB)',
    `${(noDisco.usado / 1048576).toFixed(1)} MB`);
  console.log(`       (teto deste navegador: ${(noDisco.teto / 1073741824).toFixed(1)} GB)`);

  console.log('\n4. Tocar');
  await pag.locator('#lista .faixa').first().click();
  await pag.waitForTimeout(2500);
  const t1 = await pag.evaluate(() => {
    const a = document.querySelector('audio');
    return a ? { t: a.currentTime, pausado: a.paused, dur: a.duration, src: a.src.slice(0, 5) } : null;
  });
  checa(!!t1, 'existe um elemento de audio');
  checa(t1 && t1.src === 'blob:', 'toca do arquivo guardado no aparelho, nao da internet');
  checa(t1 && !t1.pausado, 'comecou a tocar');
  await pag.waitForTimeout(3000);
  const t2 = await pag.evaluate(() => document.querySelector('audio').currentTime);
  checa(t2 > t1.t + 2, 'o tempo AVANCOU (som de verdade, nao so estado)',
    `${t1.t.toFixed(1)}s -> ${t2.toFixed(1)}s`);
  checa(await pag.locator('#rodape').isVisible(), 'o rodape com a faixa aparece');
  const nomeRodape = await pag.locator('#rNome').textContent();
  checa(nomeRodape === primeiro, 'o rodape mostra a faixa certa', `${nomeRodape} x ${primeiro}`);

  console.log('\n5. Os controles do sistema (o que vira tela de bloqueio)');
  const ms = await pag.evaluate(() => {
    const m = navigator.mediaSession;
    return {
      estado: m.playbackState,
      titulo: m.metadata?.title || null,
      artista: m.metadata?.artist || null,
      capas: m.metadata?.artwork?.length || 0,
    };
  });
  checa(ms.estado === 'playing', 'o sistema sabe que esta tocando', ms.estado);
  checa(!!ms.titulo, 'o titulo foi publicado pro sistema', String(ms.titulo));
  checa(ms.artista === 'Todas as músicas', 'publica de que LISTA a faixa saiu', String(ms.artista));
  checa(ms.capas > 0, 'a capa foi publicada (aparece na tela de bloqueio)');

  console.log('\n6. Pular faixa e a volta da lista');
  await pag.locator('#btProxima').click();
  await pag.waitForTimeout(2000);
  const depois = await pag.locator('#rNome').textContent();
  checa(depois !== primeiro, 'passou para a proxima', `${primeiro} -> ${depois}`);
  const tocandoAinda = await pag.evaluate(() => !document.querySelector('audio').paused);
  checa(tocandoAinda, 'continuou tocando depois de pular');

  console.log('\n7. Trocar de lista');
  await pag.locator('#trocar').click();
  await pag.waitForTimeout(600);
  const listas = await pag.locator('.itemLista b').allTextContents();
  checa(listas.length >= 2, 'as listas aparecem', listas.join(' | '));
  checa(listas[0] === 'Todas as músicas', '"Todas as músicas" vem primeiro', listas[0]);
  checa(listas.includes('Ghibli melhores'), 'a playlist do pacote esta la', listas.join(' | '));
  await pag.keyboard.press('Escape');

  console.log('\n8. Nada quebrado');
  // O Cloudflare injeta um script INLINE de analytics, e o nosso CSP o bloqueia --
  // o que e o CSP funcionando, nao defeito. So que ignorar "toda violacao de
  // inline" as cegas esconderia um script NOSSO quebrado no futuro. Entao a
  // dispensa e condicionada: so vale porque se prova que o nosso HTML tem ZERO
  // script inline.
  const inlineNossos = await pag.evaluate(() =>
    [...document.querySelectorAll('script')]
      .filter((s) => !s.src && !s.textContent.includes('contentDocument')).length);
  checa(inlineNossos === 0, 'o nosso HTML nao tem script inline nenhum', String(inlineNossos));
  const nossos = errosJS.filter((e) =>
    !/cloudflare|beacon|challenge/i.test(e) &&
    !(inlineNossos === 0 && /Executing inline script violates/i.test(e)));
  checa(nossos.length === 0, 'nenhum erro de JS nosso', nossos.slice(0, 3).join(' | '));
  if (errosJS.some((e) => /Executing inline script violates/i.test(e))) {
    console.log('       (o CSP barrou o beacon injetado pelo Cloudflare -- esperado)');
  }

  console.log('\n9. Sobrevive a fechar e abrir (o acervo fica)');
  await pag.reload({ waitUntil: 'networkidle' });
  await pag.waitForSelector('#lista .faixa', { timeout: 30000 });
  const depoisDoReload = await pag.locator('#lista .faixa').count();
  checa(depoisDoReload === 27, 'as 27 continuam la depois de reabrir', String(depoisDoReload));

  await browser.close();

  console.log('\n' + '-'.repeat(60));
  console.log(`  ${verdes.length} verdes, ${vermelhos.length} vermelhos`);
  if (vermelhos.length) {
    console.log('\n  FALHOU:');
    vermelhos.forEach((t) => console.log('   - ' + t));
  }
  process.exit(vermelhos.length ? 1 : 0);
})().catch((e) => {
  console.error('\nERRO NO TESTE:', e.message);
  process.exit(2);
});
