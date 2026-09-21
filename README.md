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
| `duracoes.json` | durações já medidas, para as faixas que não vêm de playlist |
| `BRANDING.md` | a identidade visual e o porquê de cada decisão |

## Rodar

Precisa de Python 3.11+ e `pip install PySide6`.

```
pythonw Musica.pyw
```

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
