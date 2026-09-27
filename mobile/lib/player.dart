// O motor: tocar, fila, e a volta na propria playlist.
//
// O comportamento aqui COPIA o do app de mesa, de proposito -- nao e lugar de
// inventar regra nova:
//   . a playlist da a volta nela mesma (LoopMode.all)
//   . "tocar a seguir" entra na frente sem virar moradora da playlist
//   . o rodape diz de que LISTA a faixa veio, nao a lista que esta na tela
//
// O som sobrevive a tela apagada por just_audio_background, que publica a sessao
// de midia do sistema (tela de bloqueio, fone, carro). Sem isso o Android mata o
// processo assim que a tela apaga e o app viraria um player de mentira.
import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:just_audio/just_audio.dart';
// MediaItem vem daqui: e o que descreve a faixa para a tela de bloqueio
import 'package:just_audio_background/just_audio_background.dart';

import 'pacote.dart';

class Motor extends ChangeNotifier {
  final AudioPlayer _som = AudioPlayer();

  Biblioteca biblioteca = Biblioteca.vazia;
  int listaAberta = 0; // indice em biblioteca.playlists (o que esta na TELA)
  String? listaTocando; // de que lista saiu o que esta tocando
  List<int> _ordem = const []; // indices de faixa, na ordem em que vao tocar
  int _posicao = -1; // onde estamos em _ordem

  AudioPlayer get som => _som;
  bool get tocando => _som.playing;
  Faixa? get atual =>
      (_posicao >= 0 && _posicao < _ordem.length) ? biblioteca.faixas[_ordem[_posicao]] : null;

  Motor() {
    _som.setLoopMode(LoopMode.all);
    _som.currentIndexStream.listen((i) {
      if (i != null && i != _posicao) {
        _posicao = i;
        notifyListeners();
      }
    });
    _som.playerStateStream.listen((_) => notifyListeners());
  }

  Future<void> recarregar() async {
    biblioteca = await Biblioteca.carregar();
    if (listaAberta >= biblioteca.playlists.length) listaAberta = 0;
    notifyListeners();
  }

  List<Faixa> get faixasDaTela {
    if (biblioteca.playlists.isEmpty) return const [];
    final l = biblioteca.playlists[listaAberta];
    return [for (final i in l.faixas) biblioteca.faixas[i]];
  }

  /// Toca a faixa na posicao `n` da lista que esta na tela.
  Future<void> tocarDaTela(int n) async {
    if (biblioteca.playlists.isEmpty) return;
    final lista = biblioteca.playlists[listaAberta];
    if (n < 0 || n >= lista.faixas.length) return;
    _ordem = List<int>.from(lista.faixas);
    listaTocando = lista.nome;
    await _som.setAudioSources(_fontes(_ordem), initialIndex: n);
    _posicao = n;
    await _som.play();
    notifyListeners();
  }

  // just_audio 0.10 aposentou o ConcatenatingAudioSource: agora a fila e uma
  // lista simples entregue ao player por setAudioSources.
  List<AudioSource> _fontes(List<int> indices) =>
      [for (final i in indices) _item(biblioteca.faixas[i])];

  AudioSource _item(Faixa f) => AudioSource.file(
        f.caminho,
        tag: MediaItem(
          id: f.caminho,
          title: f.titulo,
          album: listaTocando ?? 'Roxin',
          artUri: f.capa == null ? null : Uri.file(f.capa!),
        ),
      );

  /// "Tocar a seguir": entra na frente da fila SEM virar moradora da playlist --
  /// quando a lista der a volta, ela nao aparece de novo.
  Future<void> aSeguir(Faixa f) async {
    final idx = biblioteca.faixas.indexOf(f);
    if (idx < 0) return;
    if (_posicao >= 0 && _som.sequence.isNotEmpty) {
      await _som.insertAudioSource(_posicao + 1, _item(f));
      notifyListeners();
    } else {
      await tocarFaixa(f);
    }
  }

  Future<void> tocarFaixa(Faixa f) async {
    final n = faixasDaTela.indexOf(f);
    if (n >= 0) return tocarDaTela(n);
    _ordem = [biblioteca.faixas.indexOf(f)];
    await _som.setAudioSources(_fontes(_ordem));
    _posicao = 0;
    await _som.play();
    notifyListeners();
  }

  Future<void> alternar() =>
      _som.playing ? _som.pause() : _som.play();
  Future<void> proxima() => _som.seekToNext();
  Future<void> anterior() async {
    // antes de 3 s, "anterior" volta de faixa; depois, volta ao inicio desta --
    // e o que todo player faz, e o que o dedo espera
    if ((_som.position.inSeconds) > 3) {
      await _som.seek(Duration.zero);
    } else {
      await _som.seekToPrevious();
    }
  }

  Future<void> irPara(Duration d) => _som.seek(d);
  Future<void> volume(double v) => _som.setVolume(v.clamp(0.0, 1.0));

  @override
  void dispose() {
    _som.dispose();
    super.dispose();
  }
}
