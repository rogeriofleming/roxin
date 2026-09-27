# Roxin Mobile (Android)

O player de música do Roger no celular. Toca o acervo **offline**, com o **PC desligado** —
foi o que ele pediu em 27/09/2026: *"eu mando as musicas pro celular pra poder ouvir off"* e
*"tem que funcionar com pc desligado"*.

Não há streaming, não há servidor, não há conta para criar. As músicas ficam **dentro do
aparelho**.

## Como a música chega no celular

```
   PC                          Google Drive              Celular
   ┌──────────────────┐                                  ┌──────────────────┐
   │ Mandar pro       │   você sobe        você baixa    │ Roxin            │
   │ celular.bat      │ ───  1 arquivo .zip  ──────────► │ "trazer músicas" │
   │ (escolhe a       │                                  │ e escolhe o .zip │
   │  playlist)       │                                  └──────────────────┘
   └──────────────────┘
```

1. **No PC:** duplo clique em `Mandar pro celular.bat`, escreve o nome da playlist.
   Sai um arquivo em `pacotes\Roxin_<playlist>.zip`.
2. **Sobe esse arquivo no Google Drive** (arrastar para o navegador serve).
3. **No celular:** abre o Drive, baixa o arquivo (vai para `Download`).
4. **No Roxin:** toca no ícone de trazer músicas, escolhe o `.zip`. Pronto.

Trazer um segundo pacote **soma** — não apaga o que já estava.

## Por que um `.zip` e não uma pasta

O app do Google Drive no Android **não baixa pasta**, só arquivo a arquivo (verificado em
27/09/2026). Pasta inteira só pelo navegador em modo desktop, e mesmo assim vem como ZIP.
Um arquivo só resolve isso sem ginástica.

## O que o app faz

- Playlists do PC, "Todas as músicas" em ordem alfabética
- Tocar, pausar, faixa anterior/próxima, e a **volta na própria playlist**
- **Tocar a seguir** (toque longo numa música)
- Busca por nome, funcionando mesmo digitando sem acento
- Capa na lista, no rodapé e no **palco** de capa cheia
- **Som com a tela apagada**, com controles na tela de bloqueio e no fone

## O que ainda não faz

- **iPhone** — depende de decidir os US$ 99/ano da Apple (ver `../PLANO_MOBILE_V1.md`, D1)
- **Baixar música pelo celular** (o Anzol) — fora da v1, por pedido dele em 27/09/2026
- **Editar playlist no celular** e devolver ao PC
- **Avisar sobre espaço antes de importar** — hoje ele avisa quando o erro acontece, e não
  deixa biblioteca pela metade, mas o aviso preventivo ainda não existe

## Para quem for mexer no código

```
lib/marca.dart    as cores do BRANDING.md e o pássaro (mesmo vetor do marca.py)
lib/pacote.dart   ler a biblioteca e importar o .zip
lib/player.dart   o motor: tocar, fila, volta na playlist
lib/main.dart     as telas
```

Testes do motor, sem aparelho:

```
flutter test
```

O ícone se refaz a partir da marca, nunca na mão:

```
python mobile/gerar_icone.py
```

### Ambiente de build (nesta máquina, em 27/09/2026)

Nada disso existia antes; foi tudo instalado fora do `C:`, que estava com 91% cheio.

```
D:\dev\flutter        Flutter 3.47.5 (stable)
D:\dev\jdk            Temurin JDK 17
D:\dev\android-sdk    platform-tools, android-36, build-tools 36.0.0
```

O build precisa das variáveis apontando para lá:

```powershell
$env:JAVA_HOME = "D:\dev\jdk"
$env:ANDROID_SDK_ROOT = "D:\dev\android-sdk"
D:\dev\flutter\bin\flutter.bat build apk --release
```

⚠️ **O `AndroidManifest.xml` não é o do template.** Ele usa `AudioServiceActivity` (não
`FlutterActivity`) e declara o serviço de mídia — é isso que faz o som sobreviver à tela
apagada. Rodar `flutter create` por cima **apaga essas mudanças**.
