# -*- coding: utf-8 -*-
"""A pagina do miniplayer: LIQUID GLASS em WebGL, com o shader e a calibracao do
cofre (skill liquid-glass, assets/liquid-glass-webgl.html + references/tecnica.md).

Por que WebGL e nao o filtro SVG: o `backdrop-filter: url(#lente)` e ESTATICO —
so deforma quando o fundo muda ou o elemento se move. A propria skill diz isso na
secao 6 e aponta o caminho do movimento: o shader validado em 25/07/2026. O Roger
viu a versao SVG e disse "o vidro ta bom, o liquido nao existe" — era literalmente
verdade.

Calibracao aprovada por ele ("ficou foda"), copiada da tecnica.md e NAO mexer sem
ele pedir: lente 0 (desligada), aberracao 0 (desligada), blur do fundo 10px, fluxo
35 no teto, velocidade 1.20, onda do mouse 8 (sutil), rippleLight 0.08, DPR 1.25,
sem nenhum brilho fixo seguindo o cursor ("nao e luz, e a agua que precisa se mexer").

Gotcha de performance registrado na skill e respeitado aqui: NUNCA chamar
getBoundingClientRect() em handler de alta frequencia — o canvas cobre a janela
inteira, entao a posicao local do ponteiro sai de offsetX/offsetY, sem tocar o DOM.
"""

# A margem transparente e a MESMA coisa em tres lugares (CSS, shader e tamanho da
# janela em mini_vidro.py). Por isso o numero mora aqui, uma vez so.
#
# REGRA DA SOMBRA (o quadrado que o Roger via, consertado em 24/09/2026): a janela
# e transparente, mas o Windows NAO desenha nada fora dela — a sombra que pedir mais
# espaco do que esta margem e cortada em linha reta na borda, e o corte aparece como
# um quadrado escuro em volta do vidro arredondado. MEDIDO no Chrome (nao deduzido da
# spec, que fala de B/2): um box-shadow `0 Ypx Bpx` alcanca cerca de B para os lados e
# Y + B para baixo. Logo, a conta que o teste cobra:
#
#     deslocamento + blur  <=  MARGEM
#
# A sombra antiga era `0 20px 50px`: pedia 70px embaixo dentro de 14px de folga.
# Medido antes do conserto: alfa 62 na borda de baixo e 26 nas laterais (o quadrado).
# Quem trava isto e `testes/teste_sombra_mini.py`.
#
# Custo declarado de aumentar a margem: a janela fica maior do que o vidro que se ve
# (460x134 para um vidro de 400x74), e essa moldura invisivel engole clique — quem
# clicar nela nao clica no que esta atras. Foi o preco de nao ver o quadrado.
MARGEM = 30

_TEMPLATE = r"""<!doctype html>
<meta charset="utf-8">
<style>
  :root{
    --pena:#e9e5ef; --roxo:#a77cf0; --noite:#0f0c16;
    --raio:18px;
    --margem:__MARGEM__px;  /* espaco transparente para a sombra caber */
    --borda:rgba(255,255,255,.22);
    --topo:rgba(255,255,255,.55);
  }
  html,body{margin:0;height:100%;background:transparent;overflow:hidden;
    font-family:"Segoe UI","Yu Gothic UI",sans-serif;
    -webkit-user-select:none;user-select:none}

  /* o vidro: o canvas roda o shader; quando WebGL falta, a reserva e o
     backdrop-filter da versao CSS da skill (estatico, mas nao feio) */
  #vidro{position:fixed;inset:0;border-radius:var(--raio);display:block}
  #reserva{position:fixed;inset:var(--margem);border-radius:var(--raio);display:none;
    background:rgba(167,124,240,.20);
    -webkit-backdrop-filter:blur(10px) saturate(1.7);
    backdrop-filter:blur(10px) saturate(1.7)}
  .semwebgl #vidro{display:none}
  .semwebgl #reserva{display:block}

  /* moldura de vidro (camada 4 da skill: e ela que da volume de lente) */
  #moldura{position:fixed;inset:var(--margem);border-radius:var(--raio);pointer-events:none;
    border:1px solid var(--borda);
    box-shadow:inset 0 1px 1px var(--topo),
               inset 0 -1px 1px rgba(255,255,255,.12),
               inset 0 0 22px rgba(255,255,255,.08),
               /* as duas de fora CABEM na margem (ver a REGRA DA SOMBRA acima):
                  6+20 = 26 e 2+5 = 7, ambas <= 30, com folga */
               0 6px 20px rgba(0,0,0,.50),
               0 2px 5px rgba(0,0,0,.30)}

  #conteudo{position:fixed;inset:var(--margem);display:flex;align-items:center;gap:12px;
    padding:0 12px;box-sizing:border-box}

  #capa{width:50px;height:50px;border-radius:9px;object-fit:cover;flex:0 0 auto;
    box-shadow:0 2px 10px rgba(0,0,0,.45);background:rgba(255,255,255,.06)}
  .meio{flex:1 1 auto;min-width:0;display:flex;flex-direction:column;gap:6px}
  #nome{color:var(--pena);font-size:13px;white-space:nowrap;overflow:hidden;
    text-overflow:ellipsis;text-shadow:0 1px 4px rgba(0,0,0,.6)}
  #trilha{height:4px;border-radius:2px;background:rgba(255,255,255,.24);cursor:pointer}
  #cheio{height:100%;width:0;border-radius:2px;background:var(--roxo);
    transition:width .18s linear}

  .ctrl{display:flex;align-items:center;gap:5px;flex:0 0 auto}
  button{border:none;background:transparent;cursor:pointer;padding:0;
    width:28px;height:28px;border-radius:14px;display:grid;place-items:center;
    transition:background .16s cubic-bezier(.4,0,.2,1), transform .16s cubic-bezier(.4,0,.2,1)}
  button:hover{background:rgba(255,255,255,.18)}
  button:active{transform:scale(.88)}
  button svg{width:15px;height:15px;fill:var(--pena);
    filter:drop-shadow(0 1px 2px rgba(0,0,0,.5))}
  #toc{width:32px;height:32px;border-radius:16px;background:var(--roxo)}
  #toc:hover{background:#bb97f6}
  #toc svg{fill:var(--noite);width:14px;height:14px;filter:none}
  #volta svg{width:13px;height:13px}
</style>

<canvas id="vidro"></canvas>
<div id="reserva"></div>
<div id="moldura"></div>

<div id="conteudo">
  <img id="capa" alt="">
  <div class="meio">
    <div id="nome">—</div>
    <div id="trilha"><div id="cheio"></div></div>
  </div>
  <div class="ctrl">
    <button id="volta" title="Voltar para o Roxin">
      <svg viewBox="0 0 16 16"><path d="M7.2 1.8 2.4 6.6l4.8 4.8v-3h5.2v-3H7.2z"/><path d="M1.6 12.6h12.8v1.6H1.6z"/></svg>
    </button>
    <button id="ant" title="Anterior">
      <svg viewBox="0 0 16 16"><path d="M4 2h2v12H4zM14 2v12L6.5 8z"/></svg>
    </button>
    <button id="toc" title="Tocar / pausar">
      <svg id="icone" viewBox="0 0 16 16"><path d="M4 2l10 6-10 6z"/></svg>
    </button>
    <button id="prox" title="Próxima">
      <svg viewBox="0 0 16 16"><path d="M10 2h2v12h-2zM2 2l7.5 6L2 14z"/></svg>
    </button>
  </div>
</div>

<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<script>
// ---------------------------------------------------------------- ponte
var ponte = null;
window.addEventListener("load", function () {
  if (typeof QWebChannel === "undefined") return;
  new QWebChannel(qt.webChannelTransport, function (canal) {
    ponte = canal.objects.ponte;
    ponte.pronto();
  });
});

function liga(id, fn){
  document.getElementById(id).addEventListener("click", function(e){
    e.stopPropagation(); if (ponte) fn();
  });
}
liga("volta", function(){ ponte.voltar(); });
liga("ant",   function(){ ponte.anterior(); });
liga("toc",   function(){ ponte.tocar(); });
liga("prox",  function(){ ponte.proxima(); });

document.getElementById("trilha").addEventListener("pointerdown", function(e){
  e.stopPropagation();
  var r = this.getBoundingClientRect();     // clique isolado: aqui pode
  if (ponte) ponte.buscar(Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)));
});

// arrastar a janelinha (nao ha barra de titulo; o WebEngine come o mouse)
var arrastando = false;
document.getElementById("conteudo").addEventListener("pointerdown", function(e){
  if (e.target.closest("button") || e.target.closest("#trilha")) return;
  arrastando = true;
  if (ponte) ponte.pegar(e.screenX, e.screenY);
});
document.addEventListener("pointermove", function(e){
  if (arrastando && ponte) ponte.arrastar(e.screenX, e.screenY);
});
document.addEventListener("pointerup", function(){
  if (!arrastando) return;
  arrastando = false;
  if (ponte) ponte.soltar();
});

// ---------------------------------------------------------------- o vidro liquido
// Shader e parametros do cofre (skill liquid-glass). Calibracao aprovada:
// lente 0, aberracao 0, blur 10, fluxo 35, velocidade 1.20, onda 8, DPR 1.25.
var VS = `attribute vec2 aPos; varying vec2 vUV;
  void main(){ vUV = aPos*0.5 + 0.5; vUV.y = 1.0 - vUV.y;
               gl_Position = vec4(aPos, 0.0, 1.0); }`;

var FS = `
  precision highp float;
  varying vec2 vUV;
  uniform sampler2D uTexBlur;
  uniform vec2 uRectSize, uViewport;
  uniform float uRadius, uFalloff, uDispScale, uAberration;
  uniform float uTime, uFlowStrength, uFlowScale, uFlowSpeed;
  uniform vec2 uSplatPos[10];
  uniform float uSplatTime[10];
  uniform float uRippleStrength;
  uniform float uMargem;

  float sdRoundRect(vec2 p, vec2 b, float r){
    vec2 q = abs(p) - b + r;
    return min(max(q.x, q.y), 0.0) + length(max(q, 0.0)) - r;
  }
  float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1,311.7)))*43758.5453123); }
  float vnoise(vec2 p){
    vec2 i = floor(p), f = fract(p);
    float a = hash(i), b = hash(i+vec2(1.0,0.0)), c = hash(i+vec2(0.0,1.0)), d = hash(i+vec2(1.0,1.0));
    vec2 u = f*f*(3.0-2.0*f);
    return mix(a,b,u.x) + (c-a)*u.y*(1.0-u.x) + (d-b)*u.x*u.y;
  }
  float fbm(vec2 p){
    float v=0.0, amp=0.55;
    for(int i=0;i<3;i++){ v += amp*vnoise(p); p = p*2.05 + 11.0; amp*=0.5; }
    return v;
  }
  void main(){
    vec2 localPx = vUV * uRectSize;
    vec2 halfSize = uRectSize * 0.5;
    vec2 p = localPx - halfSize;
    // o vidro para antes da borda da janela: a margem transparente e onde a
    // sombra externa cai, e e ela que tira o "quadrado" em volta
    float d = sdRoundRect(p, halfSize - vec2(uMargem), uRadius);
    float aa = 1.5;
    float mask = smoothstep(aa, -aa, d);
    if (mask < 0.01) discard;

    float edgeDist = clamp(-d, 0.0, uFalloff);
    float lens = 1.0 - smoothstep(0.0, uFalloff, edgeDist);
    vec2 dir = length(p) > 0.001 ? normalize(p) : vec2(0.0);

    vec2 flowUV = localPx * uFlowScale;
    float nx = fbm(flowUV + vec2(uTime*uFlowSpeed, -uTime*uFlowSpeed*0.6));
    float ny = fbm(flowUV + vec2(-uTime*uFlowSpeed*0.7, uTime*uFlowSpeed) + 40.0);
    vec2 flowPx = (vec2(nx, ny) - 0.5) * 2.0 * uFlowStrength;

    vec2 ripplePx = vec2(0.0);
    float rippleLight = 0.0;
    for (int i = 0; i < 10; i++){
      float age = uTime - uSplatTime[i];
      float active = step(0.0, age) * step(age, 2.4);
      float dist = length(localPx - uSplatPos[i]);
      float radius = age * 170.0;
      float ring = exp(-pow((dist - radius) / 24.0, 2.0));
      float decay = exp(-age * 1.4);
      float amp = ring * decay * active;
      vec2 outDir = dist > 0.001 ? (localPx - uSplatPos[i]) / dist : vec2(0.0);
      ripplePx += outDir * amp * uRippleStrength;
      rippleLight += amp;
    }

    vec2 dispPx  = dir * lens * uDispScale + flowPx + ripplePx;
    vec2 aberrPx = dir * lens * uAberration + flowPx * 0.25 + ripplePx * 0.4;
    vec2 dispUV  = dispPx  / uViewport;
    vec2 aberrUV = aberrPx / uViewport;
    vec2 screenUV = localPx / uViewport;

    vec3 col;
    col.r = texture2D(uTexBlur, screenUV + dispUV + aberrUV).r;
    col.g = texture2D(uTexBlur, screenUV + dispUV).g;
    col.b = texture2D(uTexBlur, screenUV + dispUV - aberrUV).b;

    // tinta da marca: o vidro do Roxin e roxo, nao um espelho do fundo
    // "menos transparente e mais roxo": a tinta da marca pesa mais que o fundo,
    // e a noite entra atras para o vidro ter corpo em vez de ser um espelho
    col = mix(col, vec3(0.459, 0.302, 0.722), 0.44);   // #754db8: mais um tom abaixo
    col = mix(col, vec3(0.078, 0.051, 0.125), 0.32);   // e mais noite ainda atras
    // sem brilho na crista da onda: ele pediu para tirar a luz do mouse.
    // A deformacao continua (e agua, nao lampada).

    float rim = smoothstep(2.5, -2.5, d) - smoothstep(2.5, -2.5, d + 3.0);
    col += rim * (0.35 + 0.45 * (1.0 - vUV.y));

    // alpha < 1: o vidro deixa passar o que esta atras DE VERDADE, nao so a foto
    gl_FragColor = vec4(col, mask * 0.94);
  }`;

var cv = document.getElementById("vidro");
var gl = cv.getContext("webgl", {alpha: true, premultipliedAlpha: false, antialias: false});
var prog = null, locs = {}, tex = null, temTextura = false;
var DPR = 1.25;                     // calibracao aprovada
var splatPos = new Float32Array(20);
var splatTime = new Float32Array(10);
for (var i = 0; i < 10; i++) splatTime[i] = -999;
var proxSplat = 0, t0 = performance.now();

function compilar(tipo, fonte){
  var s = gl.createShader(tipo);
  gl.shaderSource(s, fonte); gl.compileShader(s);
  if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
    console.log("shader: " + gl.getShaderInfoLog(s));
    return null;
  }
  return s;
}

function iniciar(){
  if (!gl) { document.documentElement.className = "semwebgl"; return false; }
  var vs = compilar(gl.VERTEX_SHADER, VS), fs = compilar(gl.FRAGMENT_SHADER, FS);
  if (!vs || !fs) { document.documentElement.className = "semwebgl"; return false; }
  prog = gl.createProgram();
  gl.attachShader(prog, vs); gl.attachShader(prog, fs); gl.linkProgram(prog);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
    document.documentElement.className = "semwebgl"; return false;
  }
  gl.useProgram(prog);
  var buf = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1, 1,-1, -1,1, 1,1]), gl.STATIC_DRAW);
  var aPos = gl.getAttribLocation(prog, "aPos");
  gl.enableVertexAttribArray(aPos);
  gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, 0, 0);
  ["uTexBlur","uRectSize","uViewport","uRadius","uFalloff","uDispScale","uAberration",
   "uTime","uFlowStrength","uFlowScale","uFlowSpeed","uSplatPos","uSplatTime",
   "uRippleStrength","uMargem"].forEach(function(n){ locs[n] = gl.getUniformLocation(prog, n); });
  tex = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, tex);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.enable(gl.BLEND);
  gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
  redimensionar();
  requestAnimationFrame(quadro);
  return true;
}

function redimensionar(){
  if (!gl) return;
  cv.width  = Math.round(window.innerWidth  * DPR);   // buffer, em pixels de verdade
  cv.height = Math.round(window.innerHeight * DPR);
  cv.style.width  = window.innerWidth  + "px";        // e o tamanho na tela: sem
  cv.style.height = window.innerHeight + "px";        // isto o canvas fica DPR vezes
  gl.viewport(0, 0, cv.width, cv.height);             // maior e sai do lugar
}
window.addEventListener("resize", redimensionar);

// a foto do desktop entra como textura, com o blur de 10px da calibracao
function poeFundo(uri){
  if (!gl || !uri) return;
  var img = new Image();
  img.onload = function(){
    var c = document.createElement("canvas");
    c.width = cv.width; c.height = cv.height;
    var ctx = c.getContext("2d");
    // A calibracao aprovada usa blur 10px, mas ela foi feita num HERO grande.
    // Aqui a janelinha tem 400x74 e o fundo costuma ser texto fino: com 10px o
    // fundo vira mingau uniforme e deslocar mingau NAO aparece (medido: shader a
    // 60fps e duas capturas identicas). 4px deixa estrutura para a onda torcer.
    ctx.filter = "blur(6px)";
    ctx.drawImage(img, 0, 0, c.width, c.height);
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, 0);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, c);
    temTextura = true;
    window.__fundo = c;          // so para o teste conseguir olhar a textura
  };
  img.src = uri;
}

// onda empurrada pelo mouse. offsetX/offsetY NAO forcam layout (o gotcha da skill
// era chamar getBoundingClientRect aqui).
document.addEventListener("pointermove", function(e){
  if (!gl) return;
  splatPos[proxSplat*2]   = e.offsetX;
  splatPos[proxSplat*2+1] = e.offsetY;
  splatTime[proxSplat] = (performance.now() - t0) / 1000;
  proxSplat = (proxSplat + 1) % 10;
}, {passive: true});

var quadros = 0;
function quadro(){
  requestAnimationFrame(quadro);
  if (!gl || !prog || !temTextura) return;
  quadros++;
  var t = (performance.now() - t0) / 1000;
  gl.clearColor(0, 0, 0, 0);
  gl.clear(gl.COLOR_BUFFER_BIT);
  gl.activeTexture(gl.TEXTURE0);
  gl.bindTexture(gl.TEXTURE_2D, tex);
  gl.uniform1i(locs.uTexBlur, 0);
  gl.uniform2f(locs.uRectSize, cv.width, cv.height);
  gl.uniform2f(locs.uViewport, cv.width, cv.height);
  gl.uniform1f(locs.uRadius, 18 * DPR);
  gl.uniform1f(locs.uMargem, __MARGEM__ * DPR);
  gl.uniform1f(locs.uFalloff, 26 * DPR);
  gl.uniform1f(locs.uDispScale, 0.0);        // lente desligada (aprovado)
  gl.uniform1f(locs.uAberration, 9.0 * DPR);  // um pouco, a pedido dele
  gl.uniform1f(locs.uTime, t);
  gl.uniform1f(locs.uFlowStrength, 50 * DPR);   // subiu: ele pediu mais deformacao
  gl.uniform1f(locs.uFlowScale, 0.012 / DPR);
  gl.uniform1f(locs.uFlowSpeed, 1.20);
  gl.uniform1f(locs.uRippleStrength, 8 * DPR);
  gl.uniform2fv(locs.uSplatPos, splatPos);
  gl.uniform1fv(locs.uSplatTime, splatTime);
  gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
}

iniciar();

// ---------------------------------------------------------------- do Python
window.atualizar = function (d) {
  if (d.nome !== undefined) {
    var n = document.getElementById("nome");
    n.textContent = d.nome; n.title = d.nome;
  }
  if (d.capa !== undefined) document.getElementById("capa").src = d.capa;
  if (d.pct  !== undefined) document.getElementById("cheio").style.width = (d.pct * 100) + "%";
  if (d.tocando !== undefined) {
    document.getElementById("icone").innerHTML = d.tocando
      ? '<path d="M3.5 2h3.2v12H3.5zM9.3 2h3.2v12H9.3z"/>'
      : '<path d="M4 2l10 6-10 6z"/>';
  }
  if (d.atras !== undefined) poeFundo(d.atras);
};
window.temVidro = function(){ return !!(gl && prog && temTextura); };
window.quantosQuadros = function(){ return quadros; };
window.dumpFundo = function(){ return window.__fundo ? window.__fundo.toDataURL("image/png") : ""; };
</script>
"""

PAGINA = _TEMPLATE.replace("__MARGEM__", str(MARGEM))
