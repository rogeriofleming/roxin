# Roxin — identidade

Criada em 21/09/2026 para o player de música do Roger.

O app se chama **Roxin** — rouxinol e **roxo** na mesma palavra. O pássaro dá a forma
e o clima; o roxo dá a cor.

## A ideia

O rouxinol é um pássaro pequeno e discreto, de plumagem parda e cauda ruiva, que
**canta de madrugada**. É o bicho da poesia — Keats, Wilde, as mil referências ao
canto noturno. Isso dá a direção inteira: **não é um app colorido de dia, é um app
de noite alta**, onde o que importa é o som e não a imagem.

Daí as três decisões:

1. **O fundo é noite, não preto.** Preto puro é vazio; noite tem azul dentro.
2. **A cor de destaque é o roxo** que batiza o app — luminoso o bastante para brilhar
   no escuro, sem virar néon.
3. **A marca fala em serifa, a interface fala em sem-serifa.** O nome e os títulos
   têm ar literário; as listas e botões são limpos, para ler rápido.

## Paleta

| Uso | Cor | |
|---|---|---|
| Fundo (madrugada) | `#0f0c16` | roxo-noite, nunca preto puro |
| Painel (lateral, rodapé) | `#181425` | superfície um degrau acima do fundo |
| Divisões | `#272033` | linhas que separam sem gritar |
| Texto (pena) | `#e9e5ef` | branco com um véu lilás |
| Texto secundário | `#8f88a3` | contagens, durações, rótulos |
| **Destaque (roxo)** | `#a77cf0` | o Roxin — play, progresso, playlist aberta |
| Destaque em hover | `#bb97f6` | |
| Apoio (luar) | `#6d5f9e` | usado com parcimônia: barra de rolagem |

O roxo é a única cor saturada do app. Ele marca **só o que está acontecendo agora**:
o botão de tocar, o trecho já ouvido da faixa, a playlist selecionada, o modo ligado.
Se ele aparecer em tudo, deixa de significar alguma coisa.

## Tipografia

- **Marca e títulos de playlist**: Georgia (serifada) — o lado poético do bicho.
- **Interface**: Segoe UI — listas, botões, números. Legibilidade acima de estilo.
- Números de duração em `tabular-nums`, para as colunas alinharem.

## O símbolo

Silhueta de um rouxinol pousado, de perfil, olhando para a esquerda, com a cauda
longa e inclinada que é a marca registrada do bicho. A asa é um tom mais escuro do
roxo, o olho é vazado na cor do fundo.

Desenhado em **vetor, dentro do código** (`marca.py`), com `QPainterPath` — não é
arquivo de imagem. Consequência prática: escala para qualquer tamanho sem borrar,
serve de ícone da janela e de assinatura na lateral, e a cor pode mudar sem reexportar
nada. Foi verificado que continua legível a 16px.

## Aplicação no app

- **Lateral**: pássaro + "Roxin" em Georgia, no topo, acima das playlists
- **Janela**: ícone do pássaro em roxo sobre disco de noite
- **Títulos de playlist**: Georgia, 24px
- **Botão de tocar**: único elemento com fundo roxo cheio
- **Ícones de controle**: glifos geométricos monocromáticos — emoji foi evitado de
  propósito, porque o Windows os pinta coloridos e quebra a paleta
