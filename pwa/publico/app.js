// A tela do Roxin no celular.
import { carregarBiblioteca, importarPacote, urlDaFaixa, espaco, fincarPe, mmss, mb, semAcento }
  from './acervo.js';
import { Tocador } from './tocador.js';

const $ = (id) => document.getElementById(id);
const tocador = new Tocador();
let busca = '';
const capasAbertas = new Map();   // caminho -> URL, para não recriar a cada pintura

// ------------------------------------------------------------------- partida

async function comecar() {
  await fincarPe();                 // pede ao sistema para não apagar o acervo
  tocador.biblioteca = await carregarBiblioteca();
  tocador.addEventListener('mudou', pintar);
  tocador.addEventListener('erro', (e) => recado(e.detail));
  ligarBotoes();
  await mostrarEspaco();
  pintar();

  if ('serviceWorker' in navigator) {
    try { await navigator.serviceWorker.register('sw.js'); } catch (_) {}
  }
}

function ligarBotoes() {
  $('btPrimeiro').onclick = () => $('arquivo').click();
  $('btTrazer').onclick = () => $('arquivo').click();
  $('arquivo').onchange = async (e) => {
    const f = e.target.files?.[0];
    e.target.value = '';            // deixa escolher o mesmo arquivo de novo
    if (f) await trazer(f);
  };
  $('btTocar').onclick = () => tocador.alternar();
  $('btProxima').onclick = () => tocador.proxima();
  $('btAnterior').onclick = () => tocador.anterior();
  $('trocar').onclick = abrirListas;
  $('btBusca').onclick = () => {
    const q = prompt('Buscar música:', busca);
    if (q !== null) { busca = q; pintar(); }
  };
  $('barra').onclick = (ev) => {
    const d = tocador.som.duration;
    if (!isFinite(d) || d <= 0) return;
    const r = $('barra').getBoundingClientRect();
    tocador.irPara(((ev.clientX - r.left) / r.width) * d);
  };
}

// ---------------------------------------------------------------- importação

async function trazer(arquivo) {
  const d = $('dImport');
  $('pImport').value = 0;
  $('tImport').textContent = 'abrindo o pacote…';
  d.showModal();
  try {
    const r = await importarPacote(arquivo, (feitas, total, nome) => {
      $('pImport').value = total ? (feitas / total) * 100 : 0;
      $('tImport').textContent = `${feitas} de ${total} — ${nome}`;
    });
    tocador.biblioteca = await carregarBiblioteca();
    d.close();
    recado(`${r.pacote}: ${r.faixas} músicas, ${r.capas} capas`);
  } catch (e) {
    d.close();
    recado(e.message || 'não consegui abrir esse pacote');
  }
  await mostrarEspaco();
  pintar();
}

async function mostrarEspaco() {
  const e = await espaco();
  if (!e || !e.teto) return;
  $('espaco').textContent = `cabe ${mb(e.teto - e.usado)} neste aparelho`;
}

// ------------------------------------------------------------------- pintura

function pintar() {
  const vazio = !tocador.biblioteca.faixas.length;
  $('vazio').hidden = !vazio;
  $('cabeca').hidden = vazio;
  $('lista').hidden = vazio;
  $('rodape').hidden = !tocador.atual;
  if (vazio) return;

  const lista = tocador.biblioteca.listas[tocador.listaAberta];
  $('nomeLista').textContent = lista.nome;
  const alvo = busca.trim() ? tocador.buscar(busca) : tocador.faixasDaTela;
  $('contaLista').textContent = busca.trim()
    ? `${alvo.length} de ${lista.faixas.length} — “${busca}”`
    : `${lista.faixas.length} músicas`;

  pintarLista(alvo);
  pintarRodape();
}

function pintarLista(faixas) {
  const caixa = $('lista');
  caixa.textContent = '';
  const tocandoAgora = tocador.atual?.arquivo;
  for (const f of faixas) {
    const el = document.createElement('div');
    el.className = 'faixa' + (f.arquivo === tocandoAgora ? ' tocando' : '');
    const img = document.createElement('img');
    img.className = 'capinha';
    img.alt = '';
    porCapa(img, f);
    const nome = document.createElement('div');
    nome.className = 'nome';
    nome.textContent = f.titulo;
    const dur = document.createElement('div');
    dur.className = 'dur';
    dur.textContent = mmss(f.duracao);
    el.append(img, nome, dur);
    // o play nasce DENTRO do toque do dedo: é o que o iOS exige
    el.onclick = () => tocador.tocarDaTela(tocador.faixasDaTela.indexOf(f));
    caixa.append(el);
  }
}

async function porCapa(img, faixa) {
  if (!faixa.capa) { img.removeAttribute('src'); return; }
  if (capasAbertas.has(faixa.capa)) { img.src = capasAbertas.get(faixa.capa); return; }
  try {
    const u = await urlDaFaixa(faixa.capa);
    capasAbertas.set(faixa.capa, u);
    img.src = u;
  } catch (_) {}
}

function pintarRodape() {
  const f = tocador.atual;
  if (!f) return;
  $('rNome').textContent = f.titulo;
  $('rLista').textContent = tocador.listaTocando || '';
  porCapa($('rCapa'), f);
  $('btTocar').textContent = tocador.tocando ? '⏸' : '▶';
  const d = tocador.som.duration;
  const p = isFinite(d) && d > 0 ? (tocador.som.currentTime / d) * 100 : 0;
  $('barraCheia').style.width = p + '%';
}

function abrirListas() {
  const box = $('listasBox');
  box.textContent = '';
  tocador.biblioteca.listas.forEach((l, i) => {
    const el = document.createElement('div');
    el.className = 'itemLista' + (i === tocador.listaAberta ? ' aberta' : '');
    const b = document.createElement('b');
    b.textContent = l.nome;
    const s = document.createElement('span');
    s.textContent = l.faixas.length;
    el.append(b, s);
    el.onclick = () => {
      tocador.listaAberta = i;
      busca = '';
      $('dListas').close();
      pintar();
    };
    box.append(el);
  });
  $('dListas').showModal();
}

let sumir;
function recado(txt) {
  const a = $('aviso');
  a.textContent = txt;
  a.hidden = false;
  clearTimeout(sumir);
  sumir = setTimeout(() => { a.hidden = true; }, 3800);
}

comecar();
