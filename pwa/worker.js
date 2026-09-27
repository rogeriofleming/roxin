/**
 * Serve o Roxin PWA.
 *
 * Os cabecalhos abaixo nao sao enfeite: sem os dois primeiros o navegador NAO
 * habilita o armazenamento isolado que o app usa para guardar as musicas, e sem
 * o Content-Type certo o iPhone recusa o manifest e o app nao fica instalavel.
 */
export default {
  async fetch(pedido, env) {
    const r = await env.ARQUIVOS.fetch(pedido);
    const h = new Headers(r.headers);

    // NAO ha COOP/COEP aqui de proposito: eles servem a SharedArrayBuffer, que
    // este app nao usa, e require-corp e conhecido por atrapalhar blob: e midia.
    // O armazenamento do OPFS nao depende deles. Fica so o CORP, que e barato.
    h.set('Cross-Origin-Resource-Policy', 'same-origin');

    // basico de seguranca: o app nao carrega nada de fora
    h.set('X-Content-Type-Options', 'nosniff');
    h.set('Referrer-Policy', 'no-referrer');
    h.set('Content-Security-Policy', [
      "default-src 'self'",
      "script-src 'self'",
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' blob: data:",
      "media-src 'self' blob:",
      "connect-src 'self'",
      "frame-ancestors 'none'",
      "base-uri 'none'",
    ].join('; '));

    const u = new URL(pedido.url);
    if (u.pathname.endsWith('manifest.json')) {
      h.set('Content-Type', 'application/manifest+json; charset=utf-8');
    }
    // o service worker nao pode ficar velho em cache, senao o app nunca atualiza
    if (u.pathname.endsWith('sw.js')) h.set('Cache-Control', 'no-cache');

    return new Response(r.body, { status: r.status, headers: h });
  },
};
