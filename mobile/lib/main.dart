// Roxin no celular.
//
// Toca o acervo do Roger OFFLINE, com o PC desligado -- foi o que ele pediu em
// 27/09/2026 ("eu mando as musicas pro celular pra poder ouvir off", "tem que
// funcionar com pc desligado"). As musicas chegam num .zip gerado no PC por
// empacotar.py, que ele sobe no Drive e baixa no aparelho.
import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:just_audio_background/just_audio_background.dart';
import 'package:permission_handler/permission_handler.dart';

import 'marca.dart';
import 'pacote.dart';
import 'player.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // isto e o que faz o som sobreviver a tela apagada e pintar os controles na
  // tela de bloqueio. Sem isso o app viraria um player que morre no bolso.
  await JustAudioBackground.init(
    androidNotificationChannelId: 'br.com.rogeriofleming.roxin.canal',
    androidNotificationChannelName: 'Roxin',
    androidNotificationOngoing: true,
    androidStopForegroundOnPause: false,
  );
  // No Android 13+ a permissao de notificacao e pedida em tempo de execucao.
  // Medido em 27/09/2026 num aparelho virtual: sem ela o app fica com
  // importance=NONE, NAO existe notificacao de midia -- e sem notificacao de
  // midia nao ha controle na tela de bloqueio, que e o motivo de o app existir.
  // Declarar no AndroidManifest nao basta; tem que PEDIR.
  await Permission.notification.request();
  runApp(const RoxinApp());
}

class RoxinApp extends StatelessWidget {
  const RoxinApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'Roxin',
        debugShowCheckedModeBanner: false,
        theme: temaRoxin(),
        home: const TelaCasa(),
      );
}

class TelaCasa extends StatefulWidget {
  const TelaCasa({super.key});
  @override
  State<TelaCasa> createState() => _TelaCasaState();
}

class _TelaCasaState extends State<TelaCasa> {
  final motor = Motor();
  String busca = '';
  bool carregando = true;

  @override
  void initState() {
    super.initState();
    motor.addListener(_mudou);
    _abrir();
  }

  void _mudou() => setState(() {});

  Future<void> _abrir() async {
    await motor.recarregar();
    if (mounted) setState(() => carregando = false);
  }

  @override
  void dispose() {
    motor.removeListener(_mudou);
    motor.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (carregando) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator(color: Cores.roxo)),
      );
    }
    if (motor.biblioteca.semNada) return _vazio();

    final lista = motor.biblioteca.playlists[motor.listaAberta];
    final todas = motor.faixasDaTela;
    final alvo = busca.trim().isEmpty
        ? todas
        : todas
            .where((f) => f.buscavel.contains(semAcento(busca.trim())))
            .toList();

    return Scaffold(
      appBar: AppBar(
        backgroundColor: Cores.painel,
        elevation: 0,
        titleSpacing: 12,
        title: InkWell(
          onTap: _trocarLista,
          child: Row(
            children: [
              const MarcaRoxin(tam: 26),
              const SizedBox(width: 10),
              Flexible(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      lista.nome,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontFamily: familiaSerifa,
                        fontSize: 19,
                        color: Cores.pena,
                      ),
                    ),
                    Text('${lista.faixas.length} músicas',
                        style: const TextStyle(
                            fontSize: 11.5, color: Cores.penaFraca)),
                  ],
                ),
              ),
              const Icon(Icons.expand_more, color: Cores.penaFraca, size: 20),
            ],
          ),
        ),
        actions: [
          IconButton(
            tooltip: 'Buscar',
            icon: const Icon(Icons.search, color: Cores.penaFraca),
            onPressed: _buscar,
          ),
          IconButton(
            tooltip: 'Trazer músicas',
            icon: const Icon(Icons.library_add_outlined, color: Cores.penaFraca),
            onPressed: _importar,
          ),
        ],
      ),
      body: Column(
        children: [
          if (busca.trim().isNotEmpty)
            Container(
              width: double.infinity,
              color: Cores.painel,
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              child: Row(children: [
                Expanded(
                  child: Text('“$busca” — ${alvo.length} de ${todas.length}',
                      style: const TextStyle(
                          color: Cores.penaFraca, fontSize: 12.5)),
                ),
                GestureDetector(
                  onTap: () => setState(() => busca = ''),
                  child: const Text('limpar',
                      style: TextStyle(color: Cores.roxo, fontSize: 12.5)),
                ),
              ]),
            ),
          Expanded(
            child: alvo.isEmpty
                ? const Center(
                    child: Text('nada com esse nome',
                        style: TextStyle(color: Cores.penaFraca)))
                : ListView.builder(
                    itemCount: alvo.length,
                    itemBuilder: (_, i) => _linha(alvo[i], i),
                  ),
          ),
        ],
      ),
      bottomNavigationBar: motor.atual == null ? null : _rodape(),
    );
  }

  Widget _linha(Faixa f, int i) {
    final tocandoEsta = motor.atual?.caminho == f.caminho;
    return InkWell(
      onTap: () => motor.tocarDaTela(motor.faixasDaTela.indexOf(f)),
      onLongPress: () => _menuFaixa(f),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
        child: Row(
          children: [
            _capinha(f, 40),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                f.titulo,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: 14.5,
                  color: tocandoEsta ? Cores.roxo : Cores.pena,
                ),
              ),
            ),
            const SizedBox(width: 8),
            Text(mmss(f.duracao),
                style: const TextStyle(
                    color: Cores.penaFraca,
                    fontSize: 12.5,
                    fontFeatures: [FontFeature.tabularFigures()])),
          ],
        ),
      ),
    );
  }

  Widget _capinha(Faixa f, double lado) {
    if (f.capa == null) {
      return Container(
        width: lado,
        height: lado,
        decoration: BoxDecoration(
          color: Cores.painel,
          borderRadius: BorderRadius.circular(lado * 0.14),
        ),
        padding: EdgeInsets.all(lado * 0.17),
        child: const MarcaRoxin(tam: 1000, cor: Cores.luar),
      );
    }
    return ClipRRect(
      borderRadius: BorderRadius.circular(lado * 0.14),
      child: Image.file(File(f.capa!),
          width: lado, height: lado, fit: BoxFit.cover, gaplessPlayback: true),
    );
  }

  Widget _rodape() {
    final f = motor.atual!;
    return GestureDetector(
      onTap: () => Navigator.of(context).push(MaterialPageRoute(
          builder: (_) => Palco(motor: motor), fullscreenDialog: true)),
      child: Container(
        decoration: const BoxDecoration(
          color: Cores.painel,
          border: Border(top: BorderSide(color: Cores.divisao)),
        ),
        padding: const EdgeInsets.fromLTRB(10, 8, 6, 10),
        child: SafeArea(
          top: false,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              StreamBuilder<Duration>(
                stream: motor.som.positionStream,
                builder: (_, s) {
                  final pos = s.data ?? Duration.zero;
                  final tot = motor.som.duration ?? Duration.zero;
                  final v = tot.inMilliseconds == 0
                      ? 0.0
                      : (pos.inMilliseconds / tot.inMilliseconds)
                          .clamp(0.0, 1.0);
                  return LinearProgressIndicator(
                    value: v,
                    minHeight: 2,
                    backgroundColor: Cores.divisao,
                    valueColor:
                        const AlwaysStoppedAnimation<Color>(Cores.roxo),
                  );
                },
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  _capinha(f, 46),
                  const SizedBox(width: 11),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(f.titulo,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                                color: Cores.pena, fontSize: 13.5)),
                        // de que LISTA a faixa saiu -- nao a que esta na tela
                        Text(motor.listaTocando ?? '',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                                color: Cores.penaFraca, fontSize: 11)),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: Icon(
                        motor.tocando ? Icons.pause : Icons.play_arrow,
                        color: Cores.roxo, size: 30),
                    onPressed: motor.alternar,
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ------------------------------------------------------------- acoes

  void _trocarLista() {
    showModalBottomSheet(
      context: context,
      backgroundColor: Cores.painel,
      builder: (_) => SafeArea(
        child: ListView(
          shrinkWrap: true,
          children: [
            for (var i = 0; i < motor.biblioteca.playlists.length; i++)
              ListTile(
                leading: Icon(
                    i == motor.listaAberta
                        ? Icons.play_circle_fill
                        : Icons.queue_music,
                    color: i == motor.listaAberta
                        ? Cores.roxo
                        : Cores.penaFraca),
                title: Text(motor.biblioteca.playlists[i].nome,
                    style: TextStyle(
                        fontFamily: familiaSerifa,
                        color: i == motor.listaAberta
                            ? Cores.roxo
                            : Cores.pena)),
                trailing: Text(
                    '${motor.biblioteca.playlists[i].faixas.length}',
                    style: const TextStyle(color: Cores.penaFraca)),
                onTap: () {
                  setState(() => motor.listaAberta = i);
                  Navigator.pop(context);
                },
              ),
          ],
        ),
      ),
    );
  }

  void _menuFaixa(Faixa f) {
    showModalBottomSheet(
      context: context,
      backgroundColor: Cores.painel,
      builder: (_) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 6),
            child: Text(f.titulo,
                style: const TextStyle(
                    color: Cores.pena, fontFamily: familiaSerifa)),
          ),
          ListTile(
            leading: const Icon(Icons.playlist_play, color: Cores.roxo),
            title: const Text('Tocar a seguir',
                style: TextStyle(color: Cores.pena)),
            onTap: () {
              motor.aSeguir(f);
              Navigator.pop(context);
              _recado('“${f.titulo}” toca depois desta');
            },
          ),
        ]),
      ),
    );
  }

  Future<void> _buscar() async {
    final ctrl = TextEditingController(text: busca);
    final r = await showDialog<String>(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: Cores.painel,
        title: const Text('Buscar', style: TextStyle(color: Cores.pena)),
        content: TextField(
          controller: ctrl,
          autofocus: true,
          style: const TextStyle(color: Cores.pena),
          decoration: const InputDecoration(hintText: 'nome da música'),
          onSubmitted: (v) => Navigator.pop(context, v),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context, ''),
              child: const Text('limpar')),
          TextButton(
              onPressed: () => Navigator.pop(context, ctrl.text),
              child: const Text('buscar')),
        ],
      ),
    );
    if (r != null) setState(() => busca = r);
  }

  Widget _vazio() => Scaffold(
        body: SafeArea(
          child: Center(
            child: Padding(
              padding: const EdgeInsets.all(32),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const MarcaRoxin(tam: 86),
                  const SizedBox(height: 22),
                  const Text('Roxin',
                      style: TextStyle(
                          fontFamily: familiaSerifa,
                          fontSize: 30,
                          color: Cores.pena)),
                  const SizedBox(height: 14),
                  const Text(
                    'Nenhuma música aqui ainda.\n\n'
                    'No PC, gere o pacote da playlist, suba no Drive e baixe '
                    'aqui no celular. Depois toque no botão abaixo e escolha '
                    'o arquivo .zip que o Drive salvou.',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Cores.penaFraca, height: 1.5),
                  ),
                  const SizedBox(height: 26),
                  FilledButton.icon(
                    style: FilledButton.styleFrom(
                        backgroundColor: Cores.roxo,
                        foregroundColor: Cores.noite),
                    onPressed: _importar,
                    icon: const Icon(Icons.folder_open),
                    label: const Text('Escolher o pacote'),
                  ),
                ],
              ),
            ),
          ),
        ),
      );

  Future<void> _importar() async {
    // Antes de abrir o seletor: o pacote ja esta na pasta do app? No iPhone esse
    // e o caminho natural (Drive -> Salvar em Arquivos -> No meu iPhone ->
    // Roxin), e achar sozinho poupa o Roger de caçar arquivo no seletor.
    final aqui = await pacotesLargadosAqui();
    String? caminho;
    if (aqui.isNotEmpty && mounted) {
      caminho = await showDialog<String>(
        context: context,
        builder: (_) => AlertDialog(
          backgroundColor: Cores.painel,
          title: const Text('Achei um pacote aqui',
              style: TextStyle(color: Cores.pena, fontFamily: familiaSerifa)),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              for (final f in aqui.take(5))
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.inventory_2_outlined,
                      color: Cores.roxo),
                  title: Text(f.uri.pathSegments.last,
                      style: const TextStyle(
                          color: Cores.pena, fontSize: 13.5)),
                  onTap: () => Navigator.pop(context, f.path),
                ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, ''),
              child: const Text('procurar outro'),
            ),
          ],
        ),
      );
      if (caminho == null) return; // fechou o diálogo: não faz nada
    }
    if (caminho == null || caminho.isEmpty) {
      // file_picker 13: pickFile() e estatico e devolve PlatformFile? direto
      // (a 11.x usava FilePicker.platform.pickFiles e um FilePickerResult).
      final escolhido = await FilePicker.pickFile();
      caminho = escolhido?.path;
    }
    if (caminho == null || caminho.isEmpty) return;   // desistiu de escolher
    final alvo = caminho;                             // daqui pra frente nao e nulo
    if (!alvo.toLowerCase().endsWith('.zip')) {
      _recado('Isso não é um pacote .zip do Roxin');
      return;
    }
    if (!mounted) return;
    final rel = await showDialog<Relatorio>(
      context: context,
      barrierDismissible: false,
      builder: (_) => _DialogoImportando(caminho: alvo),
    );
    if (rel == null) return;
    await motor.recarregar();
    if (!mounted) return;
    if (rel.bom) {
      _recado('${rel.pacote}: ${rel.faixas} músicas, ${rel.capas} capas');
    } else {
      showDialog(
        context: context,
        builder: (_) => AlertDialog(
          backgroundColor: Cores.painel,
          title: const Text('Não entrou inteiro',
              style: TextStyle(color: Cores.pena)),
          content: Text(
            'Entraram ${rel.faixas} músicas.\n'
            '${rel.faltando > 0 ? "Faltaram ${rel.faltando}.\n" : ""}'
            '${rel.problemas.take(6).join("\n")}',
            style: const TextStyle(color: Cores.penaFraca),
          ),
          actions: [
            TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('entendi'))
          ],
        ),
      );
    }
  }

  void _recado(String t) => ScaffoldMessenger.of(context)
      .showSnackBar(SnackBar(content: Text(t)));
}

/// Mostra o progresso de verdade -- contando faixa por faixa, nao uma roda girando
/// que não diz nada.
class _DialogoImportando extends StatefulWidget {
  final String caminho;
  const _DialogoImportando({required this.caminho});
  @override
  State<_DialogoImportando> createState() => _DialogoImportandoState();
}

class _DialogoImportandoState extends State<_DialogoImportando> {
  int feitas = 0, total = 0;

  @override
  void initState() {
    super.initState();
    _correr();
  }

  Future<void> _correr() async {
    final rel = await importarPacote(widget.caminho, progresso: (f, t) {
      if (mounted) {
        setState(() {
          feitas = f;
          total = t;
        });
      }
    });
    if (mounted) Navigator.pop(context, rel);
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
        backgroundColor: Cores.painel,
        title: const Text('Trazendo as músicas',
            style: TextStyle(color: Cores.pena, fontFamily: familiaSerifa)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            LinearProgressIndicator(
              value: total == 0 ? null : feitas / total,
              backgroundColor: Cores.divisao,
              valueColor: const AlwaysStoppedAnimation<Color>(Cores.roxo),
            ),
            const SizedBox(height: 12),
            Text(total == 0 ? 'abrindo o pacote…' : '$feitas de $total',
                style: const TextStyle(color: Cores.penaFraca)),
          ],
        ),
      );
}

/// O palco: a capa grande, como no app de mesa.
class Palco extends StatefulWidget {
  final Motor motor;
  const Palco({super.key, required this.motor});
  @override
  State<Palco> createState() => _PalcoState();
}

class _PalcoState extends State<Palco> {
  @override
  void initState() {
    super.initState();
    widget.motor.addListener(_m);
  }

  void _m() => setState(() {});

  @override
  void dispose() {
    widget.motor.removeListener(_m);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final m = widget.motor;
    final f = m.atual;
    if (f == null) return const Scaffold();
    final lado = MediaQuery.of(context).size.width * 0.78;
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.expand_more, color: Cores.penaFraca),
          onPressed: () => Navigator.pop(context),
        ),
        title: Text(m.listaTocando ?? '',
            style: const TextStyle(color: Cores.penaFraca, fontSize: 12.5)),
        centerTitle: true,
      ),
      body: SafeArea(
        child: Column(
          children: [
            const Spacer(),
            if (f.capa != null)
              ClipRRect(
                borderRadius: BorderRadius.circular(16),
                child: Image.file(File(f.capa!),
                    width: lado, height: lado, fit: BoxFit.cover),
              )
            else
              Container(
                width: lado,
                height: lado,
                decoration: BoxDecoration(
                    color: Cores.painel,
                    borderRadius: BorderRadius.circular(16)),
                padding: EdgeInsets.all(lado * 0.22),
                child: const MarcaRoxin(tam: 1000, cor: Cores.luar),
              ),
            const SizedBox(height: 28),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 28),
              child: Text(f.titulo,
                  textAlign: TextAlign.center,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                      fontFamily: familiaSerifa,
                      fontSize: 21,
                      color: Cores.pena)),
            ),
            const Spacer(),
            StreamBuilder<Duration>(
              stream: m.som.positionStream,
              builder: (_, s) {
                final pos = s.data ?? Duration.zero;
                final tot = m.som.duration ?? Duration(seconds: f.duracao);
                final max = tot.inMilliseconds.toDouble();
                return Column(children: [
                  Slider(
                    value: max == 0
                        ? 0
                        : pos.inMilliseconds.toDouble().clamp(0, max),
                    max: max == 0 ? 1 : max,
                    onChanged: (v) =>
                        m.irPara(Duration(milliseconds: v.round())),
                  ),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 26),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(mmss(pos.inSeconds),
                            style: const TextStyle(
                                color: Cores.penaFraca, fontSize: 12)),
                        Text(mmss(tot.inSeconds),
                            style: const TextStyle(
                                color: Cores.penaFraca, fontSize: 12)),
                      ],
                    ),
                  ),
                ]);
              },
            ),
            const SizedBox(height: 10),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                IconButton(
                    iconSize: 34,
                    icon: const Icon(Icons.skip_previous, color: Cores.pena),
                    onPressed: m.anterior),
                const SizedBox(width: 18),
                Container(
                  decoration: const BoxDecoration(
                      color: Cores.roxo, shape: BoxShape.circle),
                  child: IconButton(
                    iconSize: 40,
                    icon: Icon(m.tocando ? Icons.pause : Icons.play_arrow,
                        color: Cores.noite),
                    onPressed: m.alternar,
                  ),
                ),
                const SizedBox(width: 18),
                IconButton(
                    iconSize: 34,
                    icon: const Icon(Icons.skip_next, color: Cores.pena),
                    onPressed: m.proxima),
              ],
            ),
            const SizedBox(height: 26),
          ],
        ),
      ),
    );
  }
}
