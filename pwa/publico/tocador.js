// O tocador do Roxin — a parte que decide se isto funciona no iPhone.
//
// AS REGRAS DO iOS QUE ESTÃO CODIFICADAS AQUI (e por que):
//
// 1. UM ÚNICO elemento <audio>, criado uma vez e reaproveitado para sempre.
//    O iOS só deixa tocar um elemento que foi "destravado" por um toque do dedo.
//    Criar um <audio> novo a cada faixa perde esse destravamento e a próxima
//    música simplesmente não sai — sem erro nenhum na tela.
//
// 2. <audio>, nunca <video> e nunca Web Audio. No iOS, elemento de vídeo tem
//    restrição de tela bloqueada embutida (a sessão é interrompida assim que a
//    tela apaga, antes de qualquer script rodar). Elemento de áudio, não.
//
// 3. A faixa seguinte entra trocando o `src` do MESMO elemento e chamando play()
//    de dentro do evento 'ended' — que o iOS aceita como continuação do gesto
//    original.
//
// 4. A sessão de mídia é atualizada SEMPRE (título, capa, estado e posição), que
//    é o que desenha os controles na tela de bloqueio.

import { urlDaFaixa, semAcento } from './acervo.js';

export class Tocador extends EventTarget {
  constructor() {
    super();
    // regra 1: este elemento nasce aqui e nunca é trocado
    this.som = new Audio();
    this.som.preload = 'auto';
    this.som.setAttribute('playsinline', '');
    this.som.crossOrigin = 'anonymous';
    // O elemento entra NO DOM. Um Audio() solto em memoria toca, mas no iOS o
    // elemento que o sistema enxerga e o que esta na pagina -- e e dele que
    // dependem a continuidade com a tela apagada e os controles de bloqueio.
    // (Descoberto em 27/09/2026: sem isto nem `document.querySelector('audio')`
    // achava o tocador, o que ja diz que o navegador tambem nao o via direito.)
    this.som.id = 'tocador';
    this.som.setAttribute('aria-hidden', 'true');
    this.som.style.display = 'none';
    document.body.appendChild(this.som);

    this.biblioteca = { faixas: [], listas: [], geradoEm: null };
    this.listaAberta = 0;
    this.listaTocando = null;
    this.ordem = [];
    this.posicao = -1;
    this._url = null;
    this._destravado = false;

    this.som.addEventListener('ended', () => this.proxima(true));
    this.som.addEventListener('timeupdate', () => {
      this._posicaoNaSessao();
      this._avisar();
    });
    for (const ev of ['play', 'pause', 'loadedmetadata']) {
      this.som.addEventListener(ev, () => {
        this._estadoNaSessao();
        this._avisar();
      });
    }
    this.som.addEventListener('error', () => {
      this.dispatchEvent(new CustomEvent('erro', {
        detail: 'não consegui tocar esta faixa',
      }));
    });

    this._ligarControlesDoSistema();
  }

  _avisar() { this.dispatchEvent(new Event('mudou')); }

  get atual() {
    return this.posicao >= 0 && this.posicao < this.ordem.length
      ? this.biblioteca.faixas[this.ordem[this.posicao]]
      : null;
  }
  get tocando() { return !this.som.paused && !this.som.ended; }

  get faixasDaTela() {
    const l = this.biblioteca.listas[this.listaAberta];
    return l ? l.faixas.map((i) => this.biblioteca.faixas[i]) : [];
  }

  /**
   * O PRIMEIRO play tem que sair de dentro de um toque do dedo. Depois disso o
   * iOS libera o elemento e as trocas seguintes podem ser automáticas.
   */
  async tocarDaTela(n) {
    const lista = this.biblioteca.listas[this.listaAberta];
    if (!lista || n < 0 || n >= lista.faixas.length) return;
    this.ordem = [...lista.faixas];
    this.listaTocando = lista.nome;
    await this._irPara(n);
  }

  async _irPara(n, seguirTocando = true) {
    if (!this.ordem.length) return;
    // a lista dá a volta nela mesma, como no app de mesa
    this.posicao = ((n % this.ordem.length) + this.ordem.length) % this.ordem.length;
    const faixa = this.atual;
    if (!faixa) return;

    if (this._url) URL.revokeObjectURL(this._url);
    this._url = await urlDaFaixa(faixa.arquivo);
    this.som.src = this._url;          // regra 3: mesmo elemento, src novo
    this._metadadosNaSessao(faixa);
    if (seguirTocando) {
      try {
        await this.som.play();
        this._destravado = true;
      } catch (e) {
        this.dispatchEvent(new CustomEvent('erro', {
          detail: 'o iPhone recusou tocar sem um toque na tela',
        }));
      }
    }
    this._avisar();
  }

  async alternar() {
    if (this.tocando) this.som.pause();
    else {
      try { await this.som.play(); this._destravado = true; } catch (_) {}
    }
  }

  proxima(automatico = false) { return this._irPara(this.posicao + 1, true); }

  anterior() {
    // antes de 3 s volta uma faixa; depois, volta ao início desta
    if (this.som.currentTime > 3) { this.som.currentTime = 0; return Promise.resolve(); }
    return this._irPara(this.posicao - 1, true);
  }

  irPara(seg) { this.som.currentTime = seg; }

  /** "Tocar a seguir": entra na frente da fila sem morar na playlist. */
  aSeguir(indiceNaBiblioteca) {
    if (this.posicao < 0) return;
    this.ordem.splice(this.posicao + 1, 0, indiceNaBiblioteca);
    this._avisar();
  }

  buscar(texto) {
    const q = semAcento(texto.trim());
    if (!q) return this.faixasDaTela;
    return this.faixasDaTela.filter((f) => semAcento(f.titulo).includes(q));
  }

  // --------------------------------------------- a sessão de mídia do sistema

  _ligarControlesDoSistema() {
    if (!('mediaSession' in navigator)) return;
    const ms = navigator.mediaSession;
    ms.setActionHandler('play', () => this.alternar());
    ms.setActionHandler('pause', () => this.alternar());
    ms.setActionHandler('nexttrack', () => this.proxima());
    ms.setActionHandler('previoustrack', () => this.anterior());
    ms.setActionHandler('seekto', (d) => {
      if (d.seekTime != null) this.irPara(d.seekTime);
    });
    ms.setActionHandler('seekforward', () => this.irPara(this.som.currentTime + 10));
    ms.setActionHandler('seekbackward', () => this.irPara(this.som.currentTime - 10));
  }

  async _metadadosNaSessao(faixa) {
    if (!('mediaSession' in navigator)) return;
    const arte = [];
    if (faixa.capa) {
      try {
        const u = await urlDaFaixa(faixa.capa);
        arte.push({ src: u, sizes: '512x512', type: 'image/png' });
      } catch (_) {}
    }
    navigator.mediaSession.metadata = new MediaMetadata({
      title: faixa.titulo,
      artist: this.listaTocando || 'Roxin',
      album: 'Roxin',
      artwork: arte,
    });
  }

  _estadoNaSessao() {
    if ('mediaSession' in navigator) {
      navigator.mediaSession.playbackState = this.tocando ? 'playing' : 'paused';
    }
  }

  _posicaoNaSessao() {
    if (!('mediaSession' in navigator) || !navigator.mediaSession.setPositionState) return;
    const d = this.som.duration;
    if (!isFinite(d) || d <= 0) return;
    try {
      navigator.mediaSession.setPositionState({
        duration: d,
        playbackRate: this.som.playbackRate || 1,
        position: Math.min(this.som.currentTime, d),
      });
    } catch (_) {}
  }
}
