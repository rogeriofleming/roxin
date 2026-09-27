# Roxin Mobile — plano v1 (Android + iPhone)

> **Escrito em:** 27/09/2026 · **Estado:** plano pronto, aguarda as respostas da F0
> **Propósito deste arquivo:** é o mapa de retomada. Sessão que cair, limite que estourar,
> outra máquina que assumir — lê isto, confere os checkboxes e continua de onde parou.
> **Nenhuma linha de código antes deste plano estar commitado.**
>
> **O que o Roger cravou em 27/09/2026, e que moldou o plano inteiro** (fala dele, literal):
> 1. *"tenho iphone e android, os dois"* (27/09/2026)
> 2. *"eu mando as musicas pro celular pra poder ouvir off"* (27/09/2026) → **offline, arquivos no aparelho**
> 3. *"tem que funcionar com pc desligado"* (27/09/2026)
>
> ⚠️ **Tudo o que NÃO estiver entre aspas com data neste arquivo é dedução minha.** As
> recomendações da F0, a divisão de fases e a escolha de Flutter são propostas minhas, abertas
> a ele derrubar.

---

## 1. Objetivo

O Roger abre o Roxin no celular — **com o PC desligado e o avião sem sinal** — e ouve as
playlists dele, com a mesma cara do app de mesa: fundo de madrugada, pássaro roxo, capa,
palco. Som continua com a **tela bloqueada** e os controles aparecem na tela de bloqueio.

**Mensurável:** tocar 1 hora seguida, tela apagada, modo avião, sem o app ser morto pelo
sistema · playlist com 238 faixas (Ghibli) abre em < 1 s · 0 faixa faltando contra o pacote
gerado no PC.

## 2. Diagnóstico — o que existe e o que não existe

| | Hoje (PC) | No celular |
|---|---|---|
| Interface | PySide6 / Qt Widgets, 2223 linhas | **não existe** — Qt não vai para iPhone de forma sã |
| Som | QtMultimedia (`QMediaPlayer`) | **não existe** |
| Acervo | `D:\Music`, **1392 faixas, 18 GB** (medido 27/09/2026) | não cabe inteiro, e não deve ir inteiro |
| Playlists | 13 `.m3u` em `D:\Music\Playlists` | **quebram**: `.m3u` guarda **caminho absoluto do PC** |
| Capas | `%LOCALAPPDATA%\Roxin\capas` (832 de 1154 em 25/09) | fora do acervo — precisa viajar junto |
| Durações | `duracoes.json` | idem, e evita o celular abrir 1392 arquivos |
| Marca | `marca.py` (vetor em `QPainterPath`), Georgia + Segoe UI | **as duas fontes não existem** em Android/iOS |

**O que as três falas dele eliminaram, e por quê** — registrado para ninguém re-propor:

- ❌ **PWA** (o caminho mais barato): no iPhone, uma PWA **não lê a pasta de música do
  aparelho**, e há relato consistente de desenvolvedores de que o áudio morre ~30 s depois de
  pausado com a tela bloqueada (não testado por mim no aparelho dele). *Offline + iPhone* mata a PWA.
- ❌ **Servidor em casa** (Navidrome, Cloudflare Tunnel, o Roxin servindo o acervo): *"tem que
  funcionar com pc desligado"* (27/09/2026) mata todos.
- ❌ **Acervo no R2 e streaming**: seria ~US$ 0,12/mês e funcionaria com o PC desligado — mas é
  streaming, não offline, e gasta dados móveis. Contra *"pra poder ouvir off"* (27/09/2026).
- ❌ **Qt for Android / Kivy / BeeWare** (levar o Python): promete reaproveitar código e não
  cumpre — QtMultimedia no Android é frágil e o iOS exige a mesma conta paga do caminho nativo.

**O que sobrou:** app nativo de verdade, um código para os dois sistemas.

## 2b. O que já existe (reaproveitar)

| Peça | Onde | Como entra |
|---|---|---|
| **Identidade fechada** | `BRANDING.md` | vira os tokens do app mobile, sem re-decidir nada |
| **O pássaro em vetor** | `marca.py` + `docs/gerar_marca.py` | exportar **SVG** e desenhar em Dart — o vetor já existe, não se redesenha |
| **Comportamento já construído** | `Musica.pyw` — `carregar()`, a volta da playlist, `lista_tocando`, ordem alfabética, fila "tocar a seguir" | o mobile **copia o comportamento** do app de mesa, não reinventa |
| **Capas e durações** | `%LOCALAPPDATA%\Roxin\capas`, `duracoes.json` | entram no pacote — o celular não recalcula nada |
| **O verificador** | `conferir_playlists.py` | é a base do teste do pacote (nasceu do estrago de 27/09) |
| **Nomes de arquivo limpos** | `limpar()`, `sem_acento()` | mesma normalização dos dois lados, senão a playlist não casa |

## 3. Arquitetura (recomendação minha)

```
PC (quando ligado)                           Celular (sempre)
+------------------------+                   +------------------------+
| Roxin de mesa          |                   | Roxin Mobile (Flutter) |
|                        |    Wi-Fi local    |                        |
|  empacotar.py  --------+------------------>|  pasta Roxin/          |
|   . faixas escolhidas  |  (HTTP temporario |   . musicas/*.mp3      |
|   . capas              |   na rede de casa)|   . capas/*.jpg        |
|   . roxin.json         |                   |   . roxin.json         |
|     (indice portatil)  |                   |                        |
+------------------------+                   |  just_audio +          |
                                             |  audio_service         |
   PC desligado = so nao da pra SINCRONIZAR  |  (tela bloqueada, fone,|
   Ouvir continua funcionando sempre.        |   CarPlay/Android Auto)|
                                             +------------------------+
```

**Flutter** (Dart), com `just_audio` para tocar + `audio_service` para o som sobreviver à tela
apagada e pôr os controles na tela de bloqueio. É o par maduro e testado para player de música.

**O custo, declarado junto:** Flutter é um framework novo no mundo dele — Dart, SDK, build. A
fábrica web é vanilla por decisão registrada, e isso **continua valendo lá**; o Flutter fica
**preso ao repo do Roxin** e não encosta nos apps Cloudflare. A alternativa de não usar
framework seria escrever **duas vezes** (Kotlin + Swift), que é pior por todo lado.

**A sincronização por Wi-Fi da casa, não por cabo — proposta minha.** O Roxin do PC sobe um
servidor HTTP temporário na rede local e o celular baixa o pacote. Motivo: no iPhone, copiar
5 GB pelo app Arquivos com cabo no Windows é lento e irritante; e o Wi-Fi funciona **igual**
nos dois aparelhos. *Isto não fere o "pc desligado" dele* (27/09/2026): o PC só precisa estar
ligado para **sincronizar**, nunca para **ouvir**. Cabo continua existindo como plano B.

## 4. F0 — o que é dele responder

### Cravado ✅ — fala dele, não re-perguntar
- [x] *"eu mando as musicas pro celular pra poder ouvir off"* (27/09/2026) → offline, no aparelho
- [x] *"tem que funcionar com pc desligado"* (27/09/2026)
- [x] *"tenho iphone e android, os dois"* (27/09/2026)

### Proposto por mim, aguardando ✅ ou ❌ dele
- [ ] O app mobile **veste a marca** do `BRANDING.md` (não inventa paleta) — dedução minha a
      partir de o Roxin já ter identidade fechada; ele ainda não se manifestou sobre isso

### Aberto — cada uma com a minha recomendação

| # | Pergunta | Minha recomendação | Por quê |
|---|---|---|---|
| D1 | **iPhone: pagar US$ 99/ano à Apple, ou reinstalar o app a cada 7 dias?** | **Começar pelo Android e resolver isto depois** | O Android custa **zero** (instala o APK direto, sem loja, sem taxa). Resolver os US$ 99 depois de o app existir e ele ter usado é escolher com informação, não com promessa. O sideload que chegou ao Brasil em 2026 **não livra da taxa** — continua exigindo o Developer Program |
| D2 | **Quanto do acervo vai para o celular?** | **Playlists escolhidas, não os 18 GB** | "Ghibli melhores" tem 1h40 (~230 MB). Na minha proposta, ele marca no PC quais listas viajam. 18 GB inteiros é possível, mas come o aparelho e a sincronização leva horas |
| D3 | **Como as músicas chegam no celular hoje?** (pergunta de fato, não de gosto) | — | Muda a F3: se já existe um caminho que funciona no iPhone dele, a Ponte pode se apoiar nele em vez de inventar |
| D4 | **Baixar música pelo celular (o Anzol)?** | **Fora da v1** | `yt-dlp` não roda no iPhone. Faria o app nascer torto nos dois sistemas para servir um só |

## 5. Funcionalidades

### v1
1. Ler a pasta `Roxin/` do aparelho e montar a biblioteca a partir do `roxin.json`
2. Playlists (as mesmas do PC), "Todas as músicas" e "Fora das playlists", em ordem alfabética
3. Tocar, pausar, anterior/próxima, **volta na própria playlist** (mesmo comportamento do PC)
4. Fila "tocar a seguir"
5. Busca por nome de arquivo (igual ao PC)
6. Capa na lista, no rodapé e no **palco** de capa cheia
7. **Som com a tela bloqueada** + controles de bloqueio/fone/carro
8. Sincronizar pelo Wi-Fi de casa, com relatório do que entrou e do que faltou

### Fora da v1 — proposta minha de escopo, não fazer sem pedido novo
- Baixar música dentro do app (Anzol) — D4
- **O miniplayer de vidro líquido**: no PC ele é uma janela flutuante sobre o desktop; no
  celular não existe desktop. O equivalente é o rodapé + os controles da tela bloqueada
- Buscar capa na web pelo celular (a capa vem pronta no pacote)
- Editar playlist no celular e devolver ao PC (sincronização de mão dupla — é outro problema,
  e é onde apps de música costumam perder dados)
- Equalizador, letra, scrobble, rádio

## 6. O CORAÇÃO — o Pacote Roxin ⛔

**O que é:** `empacotar.py`, no PC, pega as playlists escolhidas e produz uma pasta portátil:

```
Roxin/
  roxin.json          <- o indice: faixas, playlists, duracoes, qual capa e de quem
  musicas/            <- os arquivos, com nome normalizado
  capas/              <- so as capas das faixas que viajaram
```

**Por que ISTO é o coração, e não o player:** tocar um MP3 é problema resolvido por biblioteca.
O que mata o app é o índice errado — e o cofre já pagou por isso. Em 27/09/2026, 29 arquivos
renomeados quebraram **17 entradas em 8 playlists** dele, *caladas*, porque `.m3u` guarda
caminho absoluto. Um pacote com índice torto reproduz o mesmo dano silencioso no celular,
onde é ainda mais difícil de ver.

**Regra dura do pacote:** o `roxin.json` referencia faixa por **caminho relativo**, nunca
absoluto. Nada de `D:\Music` dentro dele.

### Casos-teste que fecham o gate (para ele conferir na mão)
| # | Caso | Resultado exigido |
|---|---|---|
| 1 | Empacotar "Ghibli melhores" (27 faixas, 1h40) | 27 arquivos, 27 capas, `roxin.json` com 27 entradas · **0 faltando** |
| 2 | Rodar `conferir_playlists.py` contra o pacote | **0 entradas quebradas** |
| 3 | Faixa com acento, `&`, `#` e parênteses no nome | chega tocável e com o nome certo na tela |
| 4 | Mesma faixa em 2 playlists | **1 arquivo só** no pacote, referenciado 2× — o pacote não duplica bytes |
| 5 | Faixa sem capa | entra com o pássaro, **não** some da lista |
| 6 | Empacotar 2× seguidas | o 2º reaproveita o que já está lá, e diz o que mudou |
| 7 | SHA256 de cada faixa do pacote × original | **idêntico** — o pacote não re-codifica nada |

⛔ **Gate: sem os 7 verdes e sem ele aprovar, não existe tela nenhuma.**

## 7. Fases

### P1 — Pesquisa: a entrada dos arquivos no iPhone e o som em segundo plano
> 🧠 Modelo: **Sonnet** (pesquisa é volume de leitura)
- [ ] Como um app iOS recebe arquivos do usuário e os lê depois: `UIFileSharingEnabled`,
      `LSSupportsOpeningDocumentsInPlace`, o que aparece no app Arquivos, e o que sobrevive a
      atualização do app
- [ ] Android: `READ_MEDIA_AUDIO` × Storage Access Framework — qual dá acesso estável a uma
      pasta grande sem pedir permissão a cada abertura
- [ ] `audio_service`: o que é preciso para o sistema **não matar** o app com a tela apagada, nos dois
- [ ] Limites reais: 5–10 GB dentro da sandbox do app, e o que o iOS faz quando o espaço aperta
- [ ] **Entrega:** checklist acionável para quem implementa a F2 e a F3

### F1 — BACK · O Pacote (o coração) ⛔
> 🧠 Modelo: **Opus em `/fable-mode`** — errar aqui estraga o acervo dele
- [ ] `empacotar.py`: lê os `.m3u`, resolve capas e durações, normaliza nomes, escreve `roxin.json`
- [ ] **Só lê** `D:\Music` — nunca renomeia, nunca move, nunca apaga (lei do filtro, 27/09/2026)
- [ ] Testes dos 7 casos do §6, com controle positivo (teste que falha quando deveria)
- [ ] Gate: ele confere e aprova
- [ ] Commit

### F2 — BACK · O motor do app (sem tela bonita)
> 🧠 Modelo: **Opus em `/fable-mode`**
- [ ] Projeto Flutter, lê o `roxin.json`, monta biblioteca e playlists
- [ ] `just_audio` + `audio_service`: tocar, fila, volta na playlist, tela bloqueada
- [ ] Testes de motor (ordem, volta, fila, faixa faltando, índice corrompido)
- [ ] Interface crua de propósito — **tela feia é regra desta fase**
- [ ] Commit

### F3 — BACK · A Ponte (sincronização por Wi-Fi)
> 🧠 Modelo: **Opus**
- [ ] No PC: servidor HTTP temporário, na rede local, com código de pareamento
- [ ] No celular: baixar, verificar (tamanho + hash) e relatar o que entrou e o que faltou
- [ ] Retomar sincronização interrompida sem recomeçar do zero
- [ ] Plano B por cabo documentado nos dois sistemas
- [ ] Commit

### F4 — FRONT · Direção (Opus) — **uma tela só**
> 🧠 Modelo: **Opus** propõe, ele aprova
- [ ] Tokens a partir do `BRANDING.md` (cores exatas já existem)
- [ ] **Fontes**: Georgia e Segoe UI não existem no celular → escolher e **embutir** uma serifada
      de voz literária e uma sem-serifa legível. *Custo declarado: a marca muda de voz um
      pouco — é a mesma paleta, não é a mesma letra.* Amostra para ele antes de seguir
- [ ] O pássaro exportado em SVG a partir de `marca.py`
- [ ] **A tela da lista**, pronta e aprovada por ele num aparelho real
- [ ] Commit

### F5 — FRONT · Réplica (Sonnet)
> 🧠 Modelo: **Sonnet** — volume sobre padrão já aprovado
- [ ] Palco, fila, playlists, busca, ajustes, tela de sincronização
- [ ] **PROIBIDO** inventar componente fora dos tokens da F4
- [ ] Commit

### F6 — FULL · Android no aparelho dele
> 🧠 Modelo: **Opus em `/fable-mode`**
- [ ] APK assinado, instalado no aparelho dele (custo zero, sem loja)
- [ ] Jornada real: sincronizar → modo avião → tocar 1 h com a tela apagada
- [ ] Controles de bloqueio e fone conferidos
- [ ] Commit

### F7 — FULL · iPhone (depende da D1)
> 🧠 Modelo: **Opus em `/fable-mode`**
- [ ] **Bloqueado até a D1 ser respondida** (US$ 99/ano ou reinstalar a cada 7 dias)
- [ ] Build de iOS **sem Mac**, pela nuvem (Codemagic tem faixa grátis mensal, suficiente para
      builds esporádicos de app pequeno)
- [ ] Mesma jornada real da F6, no iPhone dele
- [ ] Commit

## 8. Caminho crítico e responsáveis

| Etapa | Quem | Esforço | Modelo |
|---|---|---|---|
| D1–D4 | responder é com ele | minutos | — |
| P1 pesquisa | máquina | curto | Sonnet |
| F1 pacote ⛔ | máquina + **gate com ele** | médio | Opus fable |
| F2 motor | máquina | **o maior** | Opus fable |
| F3 ponte | máquina | médio | Opus |
| F4 direção | máquina + **aprovação dele** | médio | Opus |
| F5 réplica | máquina | médio | Sonnet |
| F6 Android | máquina + **o aparelho dele** | curto | Opus fable |
| F7 iPhone | depende da D1 + máquina | curto | Opus fable |

**O que a máquina não faz sozinha** (constatação técnica minha): responder D1–D4, aprovar o
gate da F1, aprovar a tela da F4 e usar os aparelhos nas F6/F7 — aparelho físico não se testa
por script. O resto anda sem ele.

## 9. Paleta e tipografia

Proposta: **vestir a marca do `BRANDING.md`** — o Roxin já tem identidade fechada, e app com
marca própria não inventa paleta.

| Uso | Cor |
|---|---|
| Fundo (madrugada) | `#0f0c16` |
| Painel | `#181425` |
| Divisões | `#272033` |
| Texto | `#e9e5ef` |
| Texto secundário | `#8f88a3` |
| **Destaque (roxo)** | `#a77cf0` |
| Destaque em toque | `#bb97f6` |
| Apoio (luar) | `#6d5f9e` |

A regra do roxo escrita no `BRANDING.md` continua: **marca só o que está acontecendo agora**.
E a dos ícones continua: **glifo desenhado, nunca emoji**.

⚠️ **A tipografia é a única coisa que muda, e é uma troca, não uma melhoria:** Georgia e Segoe
UI não existem nos celulares. Embutir uma serifada e uma sem-serifa próximas — o app fica com
a mesma cor e um timbre de letra um pouco diferente. Amostra para ele na F4.

## 9b. Critérios de PRONTO (binários)

- [ ] Os 7 casos do pacote, verdes, com controle positivo
- [ ] `conferir_playlists.py` contra o pacote: **0 quebradas**
- [ ] SHA256 de cada faixa: idêntico ao original (o pacote não re-codifica)
- [ ] Tocar **1 hora**, tela apagada, **modo avião**, sem o app morrer
- [ ] Controles na tela de bloqueio: aparecem e funcionam (play, pausa, próxima)
- [ ] Playlist de 238 faixas abre em **< 1 s**
- [ ] 0 erro em tempo de execução na jornada completa
- [ ] **Ele usando no aparelho dele e dizendo que está aprovado** — construído/no ar ≠ aprovado

## 10. Pré-mortem — é dezembro de 2026 e o app fracassou. Por quê?

| Causa provável | O que a cobre |
|---|---|
| **O som para sozinho com a tela apagada** (o sistema mata o app) | P1 investiga antes · F2 implementa `audio_service` · critério de pronto exige 1 h real |
| **A playlist chega quebrada no celular** — repetindo o dano de 27/09 | F1 é o coração com gate ⛔ e 7 casos-teste · `conferir_playlists.py` |
| **Sincronizar é tão chato que ele desiste** (cabo, horas, travando) | F3 é fase própria, por Wi-Fi, com retomada e relatório · D2 limita o volume |
| **O iPhone fica de fora** porque a conta cara / os 7 dias travam | D1 respondida cedo · Android primeiro, custo zero, entrega valor sem depender da Apple |
| **Fica com cara de outro app** — some o Roxin, sobra um player genérico | F4 é direção antes de réplica, com aprovação dele · veste a marca · pássaro em SVG do vetor original |
| **O Flutter vira um peso** que ninguém mantém | Preso ao repo do Roxin, sem encostar na fábrica web · o app de mesa continua sendo a fonte da verdade |

## 11. Riscos × plano B

| Risco | Plano B |
|---|---|
| `audio_service` não segura o som no iOS do jeito que promete | O Android entrega sozinho (F6 não depende do iPhone). No iPhone, plano B honesto é um cliente pronto tocando os arquivos — perde a cara do Roxin, mantém a música |
| Apple recusa a conta / o sideload brasileiro muda de regra | Android continua de pé. iPhone espera, sem travar nada |
| 18 GB não couberem no aparelho | D2 já resolve: viaja a playlist escolhida, não o acervo |
| Wi-Fi da casa não cooperar com a Ponte | Cabo, documentado nos dois sistemas na F3 |
| Playlist editada no PC e o celular ficar velho calado | O app mostra **a data do pacote** na tela de sincronização — dado velho que se anuncia não engana |

## Anexo — o que NÃO sobrevive à travessia

| Do PC | No celular |
|---|---|
| Miniplayer de vidro líquido (WebGL sobre o desktop) | não existe → rodapé + controles de bloqueio |
| Aba do Anzol (`yt-dlp`) | fora da v1 (D4) |
| Georgia / Segoe UI | fontes embutidas (F4) |
| `.m3u` de caminho absoluto | `roxin.json` de caminho relativo |
| `%LOCALAPPDATA%\Roxin\capas` | `Roxin/capas/` dentro do pacote |
