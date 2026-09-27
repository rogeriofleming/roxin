# Roxin Mobile — prompts por fase

> Escrito em 27/09/2026, irmão do `PLANO_MOBILE_V1.md`.
> **Um prompt por fase, autocontido.** Copiar o bloco inteiro e colar numa sessão nova.
> Cada prompt diz: o modelo, o que ler antes, o escopo, o que é **PROIBIDO** e o critério de pronto.
>
> ✅ **F0 fechada em 27/09/2026.** Respostas dele: Anzol fora da v1 · transporte pelo **Google
> Drive** · a **seleção das músicas é dele** · **Android primeiro**. A F7 (iPhone) segue parada
> até ele resolver os US$ 99/ano, e não bloqueia nenhuma outra fase.

---

## P1 — Pesquisa: o Android (arquivo do Drive + som em segundo plano)
**Modelo: Sonnet**

```
Leia antes: D:\Player Musica\PLANO_MOBILE_V1.md (secoes 2, 3 e a fase P1).

ANDROID PRIMEIRO -- ele disse em 27/09/2026: "faz o Android funcionar primeiro".
O iOS e o ultimo item e nao bloqueia nada.

Voce vai pesquisar, nao implementar. Quatro perguntas, com fonte para cada resposta:

1. Android: como um app le um .zip que o Google Drive largou em Download/. READ_MEDIA_AUDIO
   x Storage Access Framework x seletor de arquivo -- qual da acesso estavel sem pedir
   permissao a cada abertura, e o que mudou do Android 11 para ca.
2. Android: audio_service. O que e preciso para o sistema NAO matar o app com a tela apagada,
   incluindo o que a otimizacao de bateria dos fabricantes faz. Erros conhecidos e como se
   detecta cada um.
3. Espaco: o que acontece ao desempacotar um .zip grande com o aparelho quase cheio, e como
   se checa espaco livre ANTES de comecar.
4. (por ultimo, sem travar) iOS: UIFileSharingEnabled, LSSupportsOpeningDocumentsInPlace, e
   como um .zip baixado do Drive entra na pasta do app.

Entrega: um documento em D:\Player Musica\PESQUISA_MOBILE.md terminando em CHECKLIST
ACIONAVEL para quem implementa a F2 e a F3 — item por item, verificavel.
Marque o que voce NAO conseguiu confirmar como nao confirmado. Nao preencha lacuna com
suposicao apresentada como fato.

PROIBIDO: escrever codigo, criar projeto Flutter, instalar SDK, tocar em D:\Music.
Pronto quando: as 4 perguntas tem resposta com fonte, e o checklist existe.
```

---

## F1 — O Pacote Roxin (o coração) ⛔
**Modelo: Opus, em `/fable-mode`**

```
Leia antes:
  D:\Player Musica\PLANO_MOBILE_V1.md (secao 6 inteira — e o coracao)
  D:\Player Musica\Musica.pyw (funcoes carregar(), limpar(), sem_acento(), cache_duracoes())
  D:\Player Musica\conferir_playlists.py

Construa empacotar.py: le as playlists .m3u que ELE escolher em D:\Music\Playlists e produz
UM ARQUIVO Roxin_<playlist>.zip contendo musicas/, capas/ e roxin.json (indice com CAMINHO
RELATIVO, nunca absoluto).

Por que .zip e nao pasta (verificado em 27/09/2026): o app do Google Drive no Android nao
baixa PASTA, so arquivo a arquivo. Um arquivo unico ele baixa direto para Download/.
Ele escolhe as playlists -- "Eu escolho quais musicas eu vou mandar" (27/09/2026); o script
nao decide nada por ele.

LEI DESTA FASE, paga com erro real em 27/09/2026 (29 arquivos dele renomeados, 17 entradas
de playlist quebradas): este script SO LE D:\Music. Nunca renomeia, nunca move, nunca apaga,
nunca reescreve um .m3u. Qualquer escrita acontece dentro da pasta Roxin/ de saida.

Escreva os 7 testes da tabela do §6 do plano, cada um com CONTROLE POSITIVO (uma versao
que tem que FALHAR, provando que o teste enxerga o defeito). Teste que so passa nao prova nada.

PROIBIDO: desenhar qualquer tela, criar o projeto Flutter, instalar Flutter/Dart,
escrever em D:\Music, tocar no app de mesa (Musica.pyw).
Pronto quando: os 7 testes verdes com controle positivo, conferir_playlists.py aponta
0 entradas quebradas contra o pacote, e o Roger olhou e aprovou. Sem a aprovacao dele,
NAO comece a F2.
```

---

## F2 — O motor do app (sem tela bonita)
**Modelo: Opus, em `/fable-mode`**

```
Leia antes:
  D:\Player Musica\PLANO_MOBILE_V1.md (secoes 3, 5 e a fase F2)
  D:\Player Musica\PESQUISA_MOBILE.md (o checklist da P1)
  D:\Player Musica\Musica.pyw (o comportamento a copiar: volta da playlist, lista_tocando,
    ordem alfabetica, fila "tocar a seguir")

Este prompt e INVALIDO sem o gate da F1 aprovado. Confirme que os 7 testes do pacote estao
verdes antes de escrever a primeira linha.

Crie o projeto Flutter em D:\Player Musica\mobile\. Motor:
  - ler roxin.json e montar biblioteca + playlists
  - just_audio para tocar; audio_service para sobreviver a tela apagada e pintar os
    controles de bloqueio
  - tocar/pausar/anterior/proxima, fila "tocar a seguir", e a VOLTA na propria playlist
    com o mesmo comportamento do app de mesa (a volta recompoe a ordem; faixa posta em
    "tocar a seguir" nao vira moradora da playlist)
  - testes de motor: ordem, volta, fila, faixa faltando, roxin.json corrompido

A tela desta fase e crua DE PROPOSITO — lista preta com texto branco resolve.

PROIBIDO: aplicar paleta, fontes, animacao ou o passaro (isso e F4/F5). PROIBIDO inventar
comportamento que o app de mesa nao tem. PROIBIDO tocar em D:\Music.
Pronto quando: os testes de motor passam e o app toca uma playlist de ponta a ponta num
emulador, com a fila e a volta funcionando.
```

---

## F3 — A importação do pacote (pelo Drive)
**Modelo: Opus**

```
Leia antes: PLANO_MOBILE_V1.md (secao 3 e a fase F3) + PESQUISA_MOBILE.md.

O transporte e o Google Drive -- "Eu vou baixar as musicas pelo Drive" (27/09/2026). NAO
existe servidor na rede local, nao existe pareamento, nao existe cabo. Ele sobe o .zip no
Drive com a mao dele; o app so precisa saber IMPORTAR o que o Drive deixou em Download/.

No celular:
  - escolher o .zip, desempacotar na pasta do app
  - VERIFICAR (contagem + tamanho + hash do roxin.json) e RELATAR o que entrou e o que faltou
  - importar um 2o pacote SOMA a biblioteca, nao apaga a anterior
  - importacao interrompida nao deixa biblioteca pela metade: ou entra tudo, ou nada
  - checar espaco livre ANTES de desempacotar, e avisar em vez de falhar no meio

PROIBIDO: subir qualquer musica para a internet, abrir porta no roteador, pedir a conta do
Google dele ou integrar com a API do Drive (ele baixa na mao -- e mais simples e nao pede
credencial nenhuma). PROIBIDO mexer no motor da F2 alem do necessario para ligar a importacao.
Pronto quando: o pacote de "Ghibli melhores" (27 faixas) atravessa PC -> Drive -> celular
e a biblioteca no aparelho tem as 27, com relatorio de 0 faltando.
```

---

## F4 — Direção visual (uma tela só)
**Modelo: Opus**

```
Leia antes:
  D:\Player Musica\BRANDING.md (a identidade — as cores ja estao decididas la)
  D:\Player Musica\marca.py (o passaro em vetor)
  D:\Player Musica\PLANO_MOBILE_V1.md (secao 9)

Entregue TRES coisas, nesta ordem:
  1. Tokens (cores do BRANDING.md, espacos, raios, tempos de animacao)
  2. Amostra de TIPOGRAFIA: Georgia e Segoe UI nao existem no celular. Escolha uma serifada
     de voz literaria e uma sem-serifa legivel, embutidas no app, e mostre ao Roger uma
     amostra lado a lado com o app de mesa. Declare o custo na mesma frase: a marca muda
     de voz um pouco. Ele decide antes de seguir.
  3. O passaro exportado em SVG a partir de marca.py (docs/gerar_marca.py ja faz o caminho)
  4. UMA tela pronta: a LISTA de musicas, com capinha, duracao e o rodape tocando.

PROIBIDO: fazer as outras telas (isso e a F5). PROIBIDO emoji como icone — glifo desenhado,
regra do BRANDING.md. PROIBIDO inventar cor fora da paleta do BRANDING.md.
Pronto quando: o Roger viu a tela da lista num aparelho real e aprovou. Sem essa aprovacao,
a F5 nao comeca — o motivo de separar direcao de replica e nao refazer 10 telas.
```

---

## F5 — Réplica das demais telas
**Modelo: Sonnet**

```
Leia antes: os tokens e a tela-referencia aprovados na F4 + PLANO_MOBILE_V1.md (secao 5).
Este prompt e INVALIDO sem a tela da F4 aprovada — anexe qual e a tela de referencia.

Construa, na paridade exata da tela-referencia: palco de capa cheia, fila, playlists,
busca, ajustes e a tela de sincronizacao (que mostra A DATA DO PACOTE — dado velho tem
que se anunciar).

PROIBIDO inventar componente, cor, fonte, espaco ou animacao fora dos tokens da F4.
Duvida de estilo: pergunta, nao inventa.
PROIBIDO mexer no motor (F2) ou na importacao do pacote (F3).
Pronto quando: todas as telas da v1 existem e nenhuma usa nada fora dos tokens.
```

---

## F6 — Android no aparelho dele
**Modelo: Opus, em `/fable-mode`**

```
Leia antes: PLANO_MOBILE_V1.md (secao 9b, os criterios de pronto).

Gere o APK assinado e entregue a ele instalavel (custo zero, sem loja, sem taxa).
Depois, a jornada real, no aparelho dele:
  gerar o pacote no PC -> ele sobe no Drive -> baixa no celular -> importar -> modo aviao ->
  tocar 1 HORA com a tela apagada -> conferir os controles de bloqueio e do fone.

Reporte o que aconteceu de verdade. Se o som parou aos 20 minutos, o relato e "parou aos
20 minutos", nao "funcionou". Teste verde e deploy feito provam o codigo; quem fecha o
produto e ele usando.

PROIBIDO: dizer "pronto" sem a hora corrida de verdade. PROIBIDO instalar coisa no aparelho
dele sem ele saber. PROIBIDO matar processo que voce nao subiu nesta maquina.
Pronto quando: todos os itens do §9b do plano estao marcados e ele disse que esta aprovado.
```

---

## F7 — iPhone
**Modelo: Opus, em `/fable-mode`**

```
Este prompt e INVALIDO enquanto a D1 nao for respondida. Anexe a resposta dele sobre
US$ 99/ano x reinstalar a cada 7 dias antes de comecar.

Leia antes: PLANO_MOBILE_V1.md (fase F7 e secao 11) + PESQUISA_MOBILE.md.

Build de iOS sem Mac, pela nuvem (Codemagic tem faixa gratis mensal). Instale no iPhone
dele pelo caminho que a resposta da D1 definir. Depois, a MESMA jornada real da F6.

Se o som nao segurar com a tela apagada no iOS, PARE e conte — nao tente remendar com
gambiarra que mantem o app acordado a forca (gasta bateria e o sistema derruba de qualquer
jeito). O plano B esta no §11 do plano.

PROIBIDO: publicar qualquer coisa na App Store. PROIBIDO gastar dinheiro sem ele ter
respondido a D1.
Pronto quando: os criterios do §9b valem tambem no iPhone, ou existe um relato honesto de
qual deles nao vale e por que.
```
