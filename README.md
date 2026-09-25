# Roxin

Player de música de mesa, feito para o acervo local do Roger em `D:\Music`.

Nasceu de um problema concreto: 1152 músicas baixadas do YouTube, com tags de
metadados inúteis (`Unknown`, `youtu.be`, nomes de canal no lugar do artista) e
players que ou não liam as playlists, ou enchiam a tela de informação que não
interessa. O Roxin lê o **nome do arquivo**, que é a única fonte confiável nesse
acervo, e mostra **só nome e duração**.

## O que ele faz

- Lê as playlists `.m3u` de `D:\Music\Playlists` e tudo que houver em `D:\Music`
- Toca **mp3 e m4a** (AAC) usando os codecs do próprio Windows, via QtMultimedia
- Busca que **ignora acento** — "coracao" encontra *Coração de Aço*
- Aleatório, repetir, barra de progresso clicável, volume
- A playlist **dá a volta nela mesma**: acabou a última, volta para a primeira
- Junta numa lista "Fora das playlists" o que não está em playlist nenhuma
- **Capinha quadrada** ao lado de cada música e no canto do player (ver abaixo)
- **Fila** ("tocar a seguir"): painel à direita, montado por clique direito
- **Miniplayer** sobreposto, que aparece quando o Roger sai do Roxin (opcional)
- **Capa cheia**: clicar na música que toca abre a capa grande, controles graúdos
- **Curadoria**: tirar, adicionar, criar, renomear, apagar playlist e reordenar arrastando
  — *tirar* acontece **direto, sem caixa de confirmação** (pedido dele em 25/09/2026): o
  `.m3u` antigo é copiado para `backup_playlists` a cada reescrita, então a pergunta só
  atrapalhava. Continua perguntando só para **apagar a playlist inteira**.
- **Baixar música de um link** — o motor do Anzol embutido (botão "Baixar")

### Teclado

| Tecla | |
|---|---|
| `Espaço` | tocar / pausar |
| `Ctrl+F` | ir para a busca |
| `Enter` | tocar a faixa selecionada |
| `←` `→` | faixa anterior / próxima |

## Arquivos

| | |
|---|---|
| `Musica.pyw` | o app inteiro: dados, interface e player |
| `marca.py` | identidade: paleta, o pássaro em vetor, e a pintura da barra de título |
| `roxin.ico` | ícone com 7 tamanhos (16 a 256px), gerado a partir do vetor |
| `capas.py` | monta o cache de capinhas a partir da imagem embutida nas músicas |
| `mini_vidro.py` | a janelinha do miniplayer: janela Qt transparente que hospeda a página |
| `mini_pagina.py` | o vidro líquido do miniplayer (HTML + WebGL) e a **margem da sombra** |
| `anzol/nucleo.py` | motor de download (yt-dlp), do Anzol — **com o `LICENSE`, que a MIT exige** |
| `buscar_capas.py` | procura capa quadrada de verdade na busca pública da Apple |
| `duracoes.json` | durações já medidas, para as faixas que não vêm de playlist |
| `BRANDING.md` | a identidade visual e o porquê de cada decisão |

## Fila ("tocar a seguir")

Clique direito numa música → *Tocar a seguir* / *Pôr no fim da fila*. A fila abre
num painel próprio à direita (escolha dele, 21/09/2026), com capinha e nome; clique
direito dentro dela dá *Tocar agora*, *Subir para o topo* e *Tirar da fila*.

É **temporária de propósito**: fechou o Roxin, zera. Não há arquivo de fila.

O avanço passa pela fila em **todos** os caminhos, porque tanto o botão "próxima"
quanto o fim da música chamam `_pula(1)` — é lá que a fila é consultada. A faixa que
sai da fila entra na `ordem` logo depois da atual, então "anterior" continua fazendo
sentido depois dela — mas **só até a lista dar a volta**: ao completar o ciclo a
`ordem` é recomposta a partir de `ordem_base`, senão a faixa enfileirada uma vez
viraria moradora da playlist e voltaria a tocar em toda volta.

## O que está tocando × o que está na tela (conserto de 25/09/2026)

O Roger relatou: *"toquei a última música da playlist e ele começou a rodar música de
fora"*. Era verdade, por **dois** caminhos — e nenhum deles era o loop, que sempre
deu a volta certa:

1. **`"Todas as músicas"` vinha na ordem de leitura do disco** — isto é, playlist por
   playlist. No acervo dele as 83 primeiras faixas dessa lista *eram* a playlist
   `Brasil`, na mesma ordem. Como é a lista que o Roxin abre por padrão, dar play nela
   era indistinguível de tocar a `Brasil`… até a 84ª faixa, quando entrava
   `ABRETE CORAZON`, da `Cerimonia`. Agora as duas listas virtuais saem em **ordem
   alfabética**, e o acervo não se disfarça mais de playlist.
2. **O rodapé mostrava o nome da lista que estava NA TELA**, não a de onde a faixa
   tocando veio (`self.listas[self.lista_idx][0]`). Tocando do acervo e clicando numa
   playlist só para olhar, o rodapé passava a dizer o nome dela — a mentira que fecha
   a impressão de "saí da playlist". Agora existe `self.lista_tocando`, gravado no
   play, e é ele que o rodapé e o palco mostram.

O que **não** era defeito: `_pula(1)` sempre deu a volta na `ordem`. O que faltava era
o player saber **de qual lista** a música que toca veio — não havia esse conceito.

Regressão: `python testes/teste_loop_playlist.py` (10 asserções, offscreen, com
acervo falso e o sinal `EndOfMedia` simulado na mão).

## Miniplayer sobreposto

Botão **Mini** no rodapé (a preferência fica em `ajustes.json`, junto do cache).
Ligado, a janelinha aparece no canto de baixo à direita **quando o Roxin perde o foco
ou é minimizado**, e desmancha quando ele volta — que foi o pedido. Traz capa, nome,
progresso e os três controles.

Detalhes que o fazem se comportar:

| | |
|---|---|
| `Qt.Tool` | não aparece na barra de tarefas nem duplica o app no Alt+Tab |
| `WindowStaysOnTopHint` | fica sobre os outros programas |
| `WA_ShowWithoutActivating` | aparece **sem roubar o foco** de onde ele está digitando |
| `WA_TranslucentBackground` | sem isso o canto arredondado mostra o retângulo preto |
| `FramelessWindowHint` | não tem barra de título — o arraste é feito na mão, e a posição fica guardada |

O gatilho é o `changeEvent` da janela principal (`ActivationChange` e
`WindowStateChange`). `_decide_mini(aqui=...)` aceita o estado por parâmetro **para
poder ser testado** sem depender do foco real da máquina.

### A sombra e a margem invisível (conserto de 24/09/2026)

O Roger viu **um quadrado de sombra** em volta da janelinha arredondada. A causa: a
janela é transparente, mas o Windows **não desenha nada fora dela** — a sombra do
vidro é um `box-shadow` desenhado DENTRO da janela, e a sombra antiga (`0 20px 50px`)
pedia ~70px de espaço embaixo dentro de uma margem transparente de **14px**. O resto
era cortado em linha reta: o quadrado.

A regra que ficou (em `mini_pagina.py`, medida no Chrome — a spec fala em `blur/2`, o
que **não** bate com o que o motor desenha):

> **deslocamento + blur ≤ MARGEM**

Hoje: margem **30px** e sombra `0 6px 20px` + `0 2px 5px`. A janela tem **460×134**
para um vidro de **400×74**.

**Custo declarado:** a moldura invisível cresceu de 14 para 30px de cada lado, e ela
**engole clique** — quem clicar nela não clica no que está atrás. Foi o preço de a
sombra caber.

Quem trava isso: `python testes/teste_sombra_mini.py` — ele fotografa a página num
Chrome de verdade **com canal alfa** e reprova se o pixel da borda não for
transparente. Antes do conserto: alfa 62 embaixo e 26 nas laterais. Depois: 1 e 0.

O lugar guardado em `ajustes.json` passou a ser o canto do **vidro** (chave
`mini_lugar_vidro`), não o da janela — assim, se a margem mudar de novo, a janelinha
fica onde ele deixou. Travado por `python testes/teste_mini_lugar.py`.

## Capa cheia (o palco)

Clicar na música que toca abre a capa grande. A capa ocupa até **62% da altura** da
janela, e o que sobra é de nome, barra e controles — ela é a única peça que cede.

**O volume fica EM PÉ, à direita da capa** (pedido de 24/09/2026). Antes era uma linha
deitada abaixo dos controles, e essa linha entrava na conta da altura: em janela baixa
a capa encolhia para caber. Medido na janela mínima (720×460): a capa foi de **172px
para 222px**. Um espaçador da mesma largura da coluna, do lado esquerdo, é o contrapeso
que mantém a capa no centro da janela.

O **valor** do volume mora num lugar só: o slider do rodapé, que é quem fala com a
saída de áudio. O do palco é espelho — como os toggles de aleatório e repetir.
Travado por `python testes/teste_volume_palco.py`.

## Baixar música (o Anzol embutido)

Botão **Baixar** no rodapé abre uma faixa discreta no topo: cola o link, escolhe
**MP3 192kbps** ou **Original (mais rápido)**, e o arquivo cai **direto em `D:\Music`**.
Ao terminar, a faixa entra na biblioteca **sem reabrir o app** — com duração medida e
capinha buscada pelo id do vídeo (ver *Capas*) — e, se a caixinha estiver marcada, também
na playlist aberta.

⚠️ **Conserto de 24/09/2026 (s.341):** a tela dizia **"Não deu certo."** em arquivo grande,
com o download inteiro no disco. Ela listava os status "em andamento" (`iniciando`,
`baixando`, `convertendo`) e caía em erro para qualquer outro — mas o núcleo do Anzol nunca
escreve `convertendo`: ele escreve **`processando`** e **`cancelando`**. Em arquivo pequeno
a conclusão chegava dentro dos 400 ms do relógio e ninguém via a fase. Agora a lista é a dos
status de **FIM** (`concluido`, `erro`, `cancelado`) e todo o resto é trabalho em andamento —
vocabulário novo no motor não vira mais erro falso. Prova: `testes/teste_pescaria.py`,
**12/12** no código de hoje contra **6/12** no antigo. A lei geral ficou no cofre, em
`sistema/conhecimentos/contrato_de_estado_entre_camadas.md`.

O motor é o **[Anzol](https://github.com/SkotAlexsander/anzol)**, do **Alex Skot**, licença
MIT: só o `nucleo.py` (a interface Flask/pywebview dele não é usada, a tela é Qt). O
`LICENSE` mora em `anzol/` e **não se apaga** — é condição da licença. O Roger falou com
o Alex e tem permissão de uso.

Por que a faixa nova entra "na mão" em vez de recarregar a biblioteca: `carregar()`
renumera todas as faixas, e a fila, a ordem de tocar e o "tocando" guardam **índice** —
recarregar sem remapear bagunçaria as três. Inserir só a faixa nova é mais seguro.

⚠️ **`yt-dlp` envelhece** e é ele que sabe conversar com cada site. Quando parar de
baixar, não é defeito do Roxin: `pip install -U yt-dlp`. Como o app roda pelo fonte
(ver abaixo), basta atualizar o pacote — não precisa reconstruir nada.

## Capas

Medido em 21/09/2026: **529 das 1152** músicas têm imagem embutida (96% dos mp3,
1% dos m4a). E quase nenhuma é capa de álbum — são **thumbnails do YouTube**, em
16:9 (400×225 na maioria), às vezes com legenda queimada ou logo de canal. Só 3
arquivos do acervo têm imagem quadrada.

Por isso a capinha é uma **moldura quadrada** e a imagem se **encaixa dentro**
(`KeepAspectRatio`), sem cortar: cortar em quadrado decepava a arte. Quem não tem
capa recebe o pássaro da marca esmaecido.

O app não lê tag em tempo de tela — isso seguraria a lista de 1152 faixas. As
miniaturas vivem num cache em `%LOCALAPPDATA%\Roxin\capas` (PNG de 160px, nome =
md5 do nome do arquivo). Na **primeira abertura numa máquina nova** o app percebe o
cache vazio e o gera em segundo plano (19s medidos para 529), repintando quando
termina — sem isso, no notebook tudo apareceria sem capa. Para refazer à mão:

```
python capas.py --forcar
```

### Capa do que foi baixado do YouTube (24/09/2026)

O que sai do Anzol nasce **sem imagem embutida**: o yt-dlp só guarda a miniatura se
mandarem, e o motor não manda. Mas o nome do arquivo termina em `[<id>]`, e com o id a
miniatura se busca direto (`i.ytimg.com`, só leitura, sem chave). O app faz isso sozinho
ao fim de cada download, em thread própria — no relógio da pescaria, que bate a cada
400 ms, a janela congelaria esperando a rede. Para o acervo antigo:

```
python capas.py --youtube
```

Ordem das miniaturas: `maxresdefault` (1280×720) e, se o vídeo não tiver, `mqdefault`
(320×180). `hqdefault` e `sddefault` ficam de fora de propósito — vêm com **tarja preta**
em cima e embaixo, que viraria borda preta dentro da capa.

⚠️ **Esta imagem é CORTADA em quadrado, pelo centro** — e isso é o **oposto** do que a
seção acima diz sobre a capa embutida. As duas decisões convivem de propósito, com escopos
diferentes:

| Origem da imagem | O que se faz | Quando foi decidido |
|---|---|---|
| **embutida no arquivo** (o acervo antigo) | encaixa inteira na moldura, **sem cortar** | 21/09/2026 — cortar decepava a arte de 529 imagens que já estavam lá |
| **buscada na web** pelo id (download novo) | **corta quadrado do centro** ao gravar no cache | 24/09/2026 — decisão do Roger, com o custo do corte cego na mesa |

Se um dia as duas tiverem de virar uma só, a pergunta é a mesma: vale mais o alinhamento
da grade ou a integridade de cada arte? Hoje a resposta é diferente para cada origem.

### Capa que não está no arquivo

`buscar_capas.py` procura o que falta na busca pública da Apple (sem chave, só
leitura). O casamento é por **nome de arquivo**, que erra: "Ellie Goulding – Love Me
Like You Do" voltava como "Ella Langley – you look like you love me". Por isso há um
filtro que exige o **artista** conferir, e o resultado **não vai direto para o app** —
fica em `%LOCALAPPDATA%\Roxin\propostas` com um HTML de conferência
(`conferir_capas.html`), separando "artista confere" de "só o título bate".
Depois de conferir:

```
python buscar_capas.py --aprovar
```

## Rodar

Precisa de Python 3.11+ e `pip install PySide6`.

```
pythonw Musica.pyw
```

## Como o app roda hoje (e por que não é mais pelo `.exe`)

Pelo atalho **`Roxin.lnk`** (também no Desktop e no Menu Iniciar), que chama
`pythonw Musica.pyw`. Ou seja: **o app roda o fonte** — mudança no código vale na próxima
abertura, sem reconstruir nada.

Isso não foi escolha estética. Medido em 21/09/2026: o **Smart App Control** do Windows
está ativo nesta máquina (`VerifiedAndReputablePolicyState: 1`) e **bloqueia o `.exe`
recém-gerado** por falta de reputação — *"Uma política de Controle de Aplicativo bloqueou
este arquivo"*. O `.exe` antigo abre; o novo, não. O atalho contorna isso porque o
`pythonw.exe` já tem reputação, e de bônus dispensa o rebuild a cada mudança.

## Gerar o executável

O `.exe` existe por um motivo específico: rodando por `pythonw.exe`, o Windows
identifica o programa como **Python** — o ícone e o nome erram na barra de tarefas,
e fixar não resolve. Com binário próprio, o processo passa a se chamar `Roxin`.

```
pyinstaller --noconfirm --clean --windowed --name Roxin --icon roxin.ico \
  --add-data "duracoes.json;." --add-data "roxin.ico;." Musica.pyw
```

Sai em `dist/Roxin/` (~134 MB, por causa do Qt). Não vai para o repositório.

## Notas de implementação

- **Caminhos**: `recurso()` resolve os arquivos tanto rodando solto quanto dentro
  do `.exe` (onde o PyInstaller descompacta em `sys._MEIPASS`).
- **Barra de título**: pintada na cor do app via `DwmSetWindowAttribute`; sem isso
  ela herda a cor de destaque do Windows. Falha em silêncio em versão antiga.
- **Identidade no Windows**: `SetCurrentProcessExplicitAppUserModelID` separa a
  janela do agrupamento do Python na barra de tarefas.
- **Ícones de controle**: glifos geométricos, não emoji — o Windows pinta emoji
  colorido e isso quebra a paleta.
