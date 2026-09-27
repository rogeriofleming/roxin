// O acervo do Roxin dentro do iPhone: abrir o .zip e guardar as músicas.
//
// POR QUE UM LEITOR DE ZIP ESCRITO À MÃO
// --------------------------------------
// O navegador não sabe abrir .zip sozinho (DecompressionStream faz gzip/deflate,
// não o formato de arquivo). Dava para puxar uma biblioteca, mas não precisa: o
// `empacotar.py` grava as músicas SEM COMPRESSÃO (ZIP_STORED), então extrair é
// copiar os bytes de um trecho do arquivo. O único item comprimido é o índice,
// que é texto — e para ele o DecompressionStream do próprio navegador resolve.
//
// ONDE AS MÚSICAS FICAM
// ---------------------
// No OPFS (Origin Private File System), que é o disco privado do app dentro do
// aparelho. Num web app instalado na tela de início do iPhone, esse espaço é
// isolado do Safari e NÃO é apagado pelo limite de 7 dias — que é justamente a
// dor que fez o Roger recusar o caminho do AltStore.

const RAIZ = 'acervo';

// ---------------------------------------------------------------- leitor de zip

const fimCentral = (b) => {
  // o "end of central directory" fica no fim do arquivo, depois de um comentário
  // de tamanho variável: procura-se a assinatura de trás para frente
  const v = new DataView(b.buffer, b.byteOffset, b.byteLength);
  for (let i = b.length - 22; i >= 0 && i > b.length - 22 - 65536; i--) {
    if (v.getUint32(i, true) === 0x06054b50) {
      return { entradas: v.getUint16(i + 10, true), inicio: v.getUint32(i + 16, true) };
    }
  }
  throw new Error('não parece um .zip (não achei o fim do índice)');
};

/** Lê a lista de arquivos de dentro do .zip, sem extrair nada ainda. */
export function lerIndiceZip(bytes) {
  const { entradas, inicio } = fimCentral(bytes);
  const v = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const td = new TextDecoder('utf-8');
  const itens = [];
  let p = inicio;
  for (let n = 0; n < entradas; n++) {
    if (v.getUint32(p, true) !== 0x02014b50) break;
    const metodo = v.getUint16(p + 10, true);
    const compr = v.getUint32(p + 20, true);
    const cru = v.getUint32(p + 24, true);
    const lnome = v.getUint16(p + 28, true);
    const lextra = v.getUint16(p + 30, true);
    const lcoment = v.getUint16(p + 32, true);
    const desloc = v.getUint32(p + 42, true);
    const nome = td.decode(bytes.subarray(p + 46, p + 46 + lnome));
    itens.push({ nome, metodo, compr, cru, desloc });
    p += 46 + lnome + lextra + lcoment;
  }
  return itens;
}

/** Devolve os bytes de UM arquivo de dentro do zip. */
export async function extrair(bytes, item) {
  const v = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  // o cabeçalho local repete nome e extra com tamanhos próprios: tem que ler daqui
  const lnome = v.getUint16(item.desloc + 26, true);
  const lextra = v.getUint16(item.desloc + 28, true);
  const ini = item.desloc + 30 + lnome + lextra;
  const cru = bytes.subarray(ini, ini + item.compr);
  if (item.metodo === 0) return cru;           // STORED: é só copiar
  if (item.metodo === 8) {                      // DEFLATE: o navegador faz
    const fluxo = new Blob([cru]).stream().pipeThrough(new DecompressionStream('deflate-raw'));
    return new Uint8Array(await new Response(fluxo).arrayBuffer());
  }
  throw new Error('compressão não suportada: ' + item.metodo);
}

// ------------------------------------------------------------------- o disco

async function pasta(caminho, criar = false) {
  let dir = await navigator.storage.getDirectory();
  for (const parte of caminho.split('/').filter(Boolean)) {
    dir = await dir.getDirectoryHandle(parte, { create: criar });
  }
  return dir;
}

async function gravar(caminho, bytes) {
  const partes = caminho.split('/');
  const nome = partes.pop();
  const dir = await pasta(partes.join('/'), true);
  const h = await dir.getFileHandle(nome, { create: true });
  const w = await h.createWritable();
  await w.write(bytes);
  await w.close();
}

async function ler(caminho) {
  const partes = caminho.split('/');
  const nome = partes.pop();
  const dir = await pasta(partes.join('/'));
  const h = await dir.getFileHandle(nome);
  return await h.getFile();
}

/** Quanto o aparelho deixa guardar, e quanto já está em uso. */
export async function espaco() {
  if (!navigator.storage?.estimate) return null;
  const e = await navigator.storage.estimate();
  return { usado: e.usage || 0, teto: e.quota || 0 };
}

/**
 * Pede ao sistema para NÃO apagar estes dados.
 * Num web app instalado na tela de início do iPhone o armazenamento já é
 * isolado do Safari, mas pedir não custa e ajuda no Android.
 */
export async function fincarPe() {
  try {
    if (navigator.storage?.persist) return await navigator.storage.persist();
  } catch (_) {}
  return false;
}

// ---------------------------------------------------------------- importação

/**
 * Traz um pacote .zip do Roxin para dentro do aparelho.
 * `aviso(feitas, total, nome)` é chamado a cada faixa, para a tela contar.
 */
export async function importarPacote(arquivo, aviso) {
  const bytes = new Uint8Array(await arquivo.arrayBuffer());
  const itens = lerIndiceZip(bytes);
  const oIndice = itens.find((i) => i.nome === 'roxin.json');
  if (!oIndice) throw new Error('não é um pacote do Roxin: falta o roxin.json');

  const ind = JSON.parse(new TextDecoder().decode(await extrair(bytes, oIndice)));
  const nome = (ind.pacote || arquivo.name.replace(/\.zip$/i, '')).replace(/[^\w\s-]+/g, '').trim() || 'pacote';

  // espaço: conferir ANTES, porque encher o disco no meio deixa acervo pela metade
  const e = await espaco();
  if (e && e.teto && e.usado + arquivo.size > e.teto) {
    throw new Error(`não cabe: o pacote tem ${mb(arquivo.size)} e só restam ${mb(e.teto - e.usado)}`);
  }

  const porNome = new Map(itens.map((i) => [i.nome, i]));
  const faixas = [];
  let n = 0;
  for (const f of ind.faixas || []) {
    const item = porNome.get(f.arquivo);
    if (!item) continue;                       // faixa que não veio não vira fantasma
    const destino = `${RAIZ}/${nome}/${f.arquivo}`;
    await gravar(destino, await extrair(bytes, item));
    let capa = null;
    if (f.capa && porNome.get(f.capa)) {
      capa = `${RAIZ}/${nome}/${f.capa}`;
      await gravar(capa, await extrair(bytes, porNome.get(f.capa)));
    }
    faixas.push({ titulo: f.titulo, arquivo: destino, capa, duracao: f.duracao || 0 });
    n++;
    aviso?.(n, (ind.faixas || []).length, f.titulo);
  }

  const listas = (ind.playlists || []).map((l) => ({ nome: l.nome, faixas: l.faixas }));
  await gravar(`${RAIZ}/${nome}/indice.json`,
    new TextEncoder().encode(JSON.stringify({ nome, gerado: ind.gerado, faixas, listas })));

  return { pacote: nome, faixas: n, capas: faixas.filter((f) => f.capa).length };
}

// ---------------------------------------------------------------- biblioteca

/** Junta todos os pacotes num acervo só. Importar de novo SOMA, não apaga. */
export async function carregarBiblioteca() {
  let raiz;
  try {
    raiz = await pasta(RAIZ);
  } catch (_) {
    return { faixas: [], listas: [], geradoEm: null };
  }
  const faixas = [];
  const listas = [];
  let maisNovo = null;

  for await (const [nomePacote, h] of raiz.entries()) {
    if (h.kind !== 'directory') continue;
    let ind;
    try {
      const f = await (await h.getFileHandle('indice.json')).getFile();
      ind = JSON.parse(await f.text());
    } catch (_) {
      continue;                                 // pacote pela metade: ignora, sem quebrar
    }
    const base = faixas.length;
    for (const fx of ind.faixas) faixas.push({ ...fx, pacote: nomePacote });
    for (const l of ind.listas || []) {
      const idx = (l.faixas || []).map((i) => base + i).filter((i) => i < faixas.length);
      if (idx.length) listas.push({ nome: l.nome, faixas: idx });
    }
    if (ind.gerado && (!maisNovo || ind.gerado > maisNovo)) maisNovo = ind.gerado;
  }

  listas.sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'));
  const todas = faixas.map((_, i) => i)
    .sort((a, b) => semAcento(faixas[a].titulo).localeCompare(semAcento(faixas[b].titulo), 'pt-BR'));
  return {
    faixas,
    listas: [{ nome: 'Todas as músicas', faixas: todas }, ...listas],
    geradoEm: maisNovo,
  };
}

/** Um endereço tocável para a faixa. Quem chamou precisa soltar depois. */
export async function urlDaFaixa(caminho) {
  return URL.createObjectURL(await ler(caminho));
}

export async function apagarPacote(nome) {
  const raiz = await pasta(RAIZ);
  await raiz.removeEntry(nome, { recursive: true });
}

// ------------------------------------------------------------------- apoio

export const semAcento = (t) =>
  (t || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

export const mmss = (s) => {
  s = Math.max(0, Math.floor(s || 0));
  return s ? `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}` : '--:--';
};

export const mb = (n) => {
  const u = ['B', 'KB', 'MB', 'GB', 'TB'];
  let i = 0;
  n = n || 0;
  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
  return `${n.toFixed(i ? 1 : 0)} ${u[i]}`;
};
