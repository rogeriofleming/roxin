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
- Junta numa lista "Fora das playlists" o que não está em playlist nenhuma
- **Capinha quadrada** ao lado de cada música e no canto do player (ver abaixo)
- **Fila** ("tocar a seguir"): painel à direita, montado por clique direito
- **Miniplayer** sobreposto, que aparece quando o Roger sai do Roxin (opcional)
- **Capa cheia**: clicar na música que toca abre a capa grande, controles graúdos
- **Curadoria**: tirar, adicionar, criar, renomear, apagar playlist e reordenar arrastando
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
sentido depois dela.

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

## Baixar música (o Anzol embutido)

Botão **Baixar** no rodapé abre uma faixa discreta no topo: cola o link, escolhe
**MP3 192kbps** ou **Original (mais rápido)**, e o arquivo cai **direto em `D:\Music`**.
Ao terminar, a faixa entra na biblioteca **sem reabrir o app** — com duração medida e
capinha gerada — e, se a caixinha estiver marcada, também na playlist aberta.

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
