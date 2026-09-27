# Roxin no iPhone, sem pagar a Apple

> Escrito em 27/09/2026, depois de ele pedir: *"da um jeito de funcionar no iphone sem
> pagar, só funcionar"* (27/09/2026).

Dá para pôr o Roxin no iPhone **sem os US$ 99/ano**. Funciona igual ao Android: toca
offline, com o PC desligado, som com a tela apagada.

**Mas tem um preço que não é em dinheiro, e ele vem antes de tudo o mais:**

> ⚠️ **App instalado com conta Apple gratuita para de abrir depois de 7 DIAS.**
> Não é falha do app nem do jeito de instalar — é regra da Apple para quem não paga.
> O app **não some** e **as músicas não somem**: ele só recusa abrir até ser renovado.
> Renovar leva menos de um minuto, e dá para ser automático (ver abaixo).

Os US$ 99/ano compram exatamente isto: o prazo vira **1 ano** em vez de 7 dias. Nada mais.

---

## O caminho, em três partes

```
  1. COMPILAR              2. ASSINAR               3. RENOVAR
  (já está feito)          (você, 1 vez)            (a cada 7 dias)

  Mac do GitHub            AltStore no PC           sozinho, pelo Wi-Fi
  → Roxin.ipa              + seu Apple ID grátis    de casa
```

**A parte 1 já está pronta e é de graça:** como o repositório do Roxin é público, o GitHub
empresta um Mac e compila sozinho. O arquivo `Roxin.ipa` sai pronto para baixar.

---

## Parte 1 — pegar o `Roxin.ipa`

Ele é gerado toda vez que o app muda. Para baixar:

1. Abra [github.com/rogeriofleming/roxin/actions](https://github.com/rogeriofleming/roxin/actions)
2. Clique no build mais recente com o ✅ verde
3. Lá embaixo, em **Artifacts**, baixe **`Roxin-iphone-ipa`**
4. Descompacte: dentro está o `Roxin.ipa`

*(Se eu já tiver baixado para você, o arquivo está aqui na pasta do Roxin.)*

## Parte 2 — instalar no iPhone

Você vai precisar de: o PC, o cabo do iPhone, e **seu Apple ID normal** (o mesmo da App
Store — não precisa criar nada, não precisa pagar).

**A escolha que importa** — duas ferramentas fazem isso, e a diferença é quem renova:

| | **AltStore** | **Sideloadly** |
|---|---|---|
| Renova sozinho | ✅ **sim**, pelo Wi-Fi de casa | ❌ não, na mão toda semana |
| Precisa do PC | só ligado na hora de renovar | toda vez, com cabo |
| Instalação | um pouco mais de passos | mais direta |

**Recomendo o AltStore**, pelo motivo óbvio: você não vai querer lembrar de reinstalar um
app toda semana.

### Com AltStore

1. No PC: baixe o **AltServer** em [altstore.io](https://altstore.io) e instale
2. Ligue o iPhone no cabo, destrave, e confie no computador
3. No AltServer (ícone perto do relógio) → **Install AltStore** → escolha seu iPhone
4. Ele pede seu **Apple ID e senha** — é a Apple que exige, para assinar em seu nome
5. No iPhone: **Ajustes → Geral → VPN e Gerenciamento → Confiar** no seu Apple ID
6. Abra o **AltStore** no iPhone → aba **My Apps** → botão **+** → escolha o `Roxin.ipa`

Pronto. O Roxin aparece na tela de início como qualquer app.

### A renovação automática (faça isto, é o que evita a dor de cabeça)

Deixe o **AltServer rodando no PC** e o iPhone **no Wi-Fi de casa**. O AltStore renova
sozinho quando você está em casa — na prática você nunca vê os 7 dias acontecerem.

> **Aqui está a tensão que eu preciso declarar, e não escondo:** você me disse *"tem que
> funcionar com pc desligado"* (27/09/2026). **Ouvir** funciona com o PC desligado, sempre —
> as músicas estão dentro do iPhone. Mas a **renovação** precisa do PC ligado uma vez por
> semana. É a consequência direta de não pagar. Se isso incomodar, existe o **SideStore**,
> que renova pelo próprio iPhone sem PC nenhum; é mais trabalhoso de configurar, e eu monto
> se você quiser.

## Parte 3 — pôr as músicas

Diferente do Android, o iPhone não tem pasta "Download" que outros apps enxergam. O caminho é
o app **Arquivos**:

1. No PC: `Mandar pro celular.bat` → escolha a playlist → sai o `.zip` na pasta `pacotes`
2. Suba esse `.zip` no **Google Drive**
3. No iPhone, abra o **Drive**, toque nos **⋯** do arquivo → **Abrir em** → **Salvar em Arquivos**
4. Salve em **No meu iPhone → Roxin**
5. Abra o Roxin e toque em **trazer músicas** — ele acha o pacote sozinho e mostra a lista

*(Se preferir, o botão também abre o seletor de arquivos comum e você escolhe de onde quiser.)*

---

## O que esperar, sem surpresa

| | |
|---|---|
| Tocar offline, modo avião | ✅ |
| Som com a tela bloqueada | ✅ (`UIBackgroundModes: audio` está no app) |
| Controles na tela de bloqueio | ✅ |
| App para de abrir em 7 dias | ⚠️ sim, até renovar — regra da Apple |
| Renovar sozinho | ✅ com AltServer ligado e no Wi-Fi de casa |
| Máximo de apps assim | 3 ao mesmo tempo (limite da conta grátis) |
| Custo | **R$ 0** |

## Honestidade sobre o que eu testei

O Android eu testei de ponta a ponta num aparelho Android 15: importei o pacote, toquei,
apaguei a tela e vi o som continuar.

**O iPhone eu não testei.** Não tenho iPhone nem Mac aqui — compilei, e o build confere
automaticamente se as chaves certas estão no app (o build **falha** se o áudio em segundo
plano sumir). Mas *"compila e tem as chaves certas"* não é o mesmo que *"eu vi tocar"*.
Quem vai fazer o primeiro teste real é você. Se algo não funcionar, me diga o que viu.
