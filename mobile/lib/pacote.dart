// A biblioteca do celular: ler os pacotes importados e importar um novo.
//
// O pacote e um .zip gerado no PC por `empacotar.py`, com musicas/, capas/ e um
// roxin.json de CAMINHO RELATIVO. O caminho relativo e a razao de existir do
// pacote: o .m3u do PC guarda caminho absoluto (D:\Music\...), que aqui nao
// existe -- em 27/09/2026, 29 arquivos renomeados no PC quebraram 17 entradas de
// playlist em silencio, e o mesmo dano no celular seria ainda mais dificil de ver.
//
// Cada pacote mora na sua pasta dentro de acervo/. A biblioteca e a UNIAO delas,
// entao importar um segundo pacote SOMA, nunca apaga o que ja estava.
import 'dart:convert';
import 'dart:io';

import 'package:archive/archive_io.dart';
import 'package:crypto/crypto.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

class Faixa {
  final String titulo;
  final String caminho; // absoluto, no aparelho
  final String? capa; // absoluto, no aparelho
  final int duracao; // segundos; 0 = desconhecida
  final String pacote;

  const Faixa({
    required this.titulo,
    required this.caminho,
    required this.duracao,
    required this.pacote,
    this.capa,
  });

  /// Para a busca funcionar digitando sem acento, como no app de mesa.
  String get buscavel => semAcento(titulo);
}

class Playlist {
  final String nome;
  final List<int> faixas; // indices na lista da biblioteca
  const Playlist(this.nome, this.faixas);
}

class Biblioteca {
  final List<Faixa> faixas;
  final List<Playlist> playlists;
  final DateTime? geradoEm; // data do pacote mais recente
  const Biblioteca(this.faixas, this.playlists, this.geradoEm);

  static const vazia = Biblioteca([], [], null);
  bool get semNada => faixas.isEmpty;

  /// Nomes das listas na ordem em que aparecem na tela: as de verdade em ordem
  /// alfabetica, e "Todas as músicas" no topo (mesma escolha do app de mesa --
  /// sem isso o acervo inteiro se disfarça da primeira playlist).
  /// `de` existe para o TESTE poder montar uma biblioteca de mentira sem
  /// depender do aparelho (path_provider e plugin, nao roda em teste puro).
  static Future<Biblioteca> carregar({Directory? de}) async {
    final raiz = de ?? await pastaAcervo();
    if (!await raiz.exists()) return vazia;

    final faixas = <Faixa>[];
    final listas = <Playlist>[];
    DateTime? maisNovo;

    final pastas = (await raiz.list().toList()).whereType<Directory>().toList()
      ..sort((a, b) => p.basename(a.path).toLowerCase().compareTo(
          p.basename(b.path).toLowerCase()));

    for (final dir in pastas) {
      final indice = File(p.join(dir.path, 'roxin.json'));
      if (!await indice.exists()) continue; // pasta pela metade: ignora
      Map<String, dynamic> ind;
      try {
        ind = jsonDecode(await indice.readAsString()) as Map<String, dynamic>;
      } catch (_) {
        continue; // indice ilegivel nao derruba a biblioteca inteira
      }
      final nomePacote = p.basename(dir.path);
      final base = faixas.length;
      for (final f in (ind['faixas'] as List? ?? const [])) {
        final rel = f['arquivo'] as String?;
        if (rel == null) continue;
        final arq = File(p.join(dir.path, rel.replaceAll('/', p.separator)));
        if (!await arq.exists()) continue; // faixa que nao chegou nao vira fantasma
        final capaRel = f['capa'] as String?;
        String? capa;
        if (capaRel != null) {
          final c = File(p.join(dir.path, capaRel.replaceAll('/', p.separator)));
          if (await c.exists()) capa = c.path;
        }
        faixas.add(Faixa(
          titulo: (f['titulo'] as String?) ?? p.basenameWithoutExtension(rel),
          caminho: arq.path,
          capa: capa,
          duracao: (f['duracao'] as num?)?.toInt() ?? 0,
          pacote: nomePacote,
        ));
      }
      for (final l in (ind['playlists'] as List? ?? const [])) {
        final nome = (l['nome'] as String?) ?? nomePacote;
        final idx = <int>[];
        for (final n in (l['faixas'] as List? ?? const [])) {
          final i = (n as num).toInt();
          // o indice do pacote conta de 0; aqui soma o deslocamento da biblioteca
          if (i >= 0 && base + i < faixas.length) idx.add(base + i);
        }
        if (idx.isNotEmpty) listas.add(Playlist(nome, idx));
      }
      final quando = DateTime.tryParse((ind['gerado'] as String?) ?? '');
      if (quando != null && (maisNovo == null || quando.isAfter(maisNovo))) {
        maisNovo = quando;
      }
    }

    listas.sort((a, b) => a.nome.toLowerCase().compareTo(b.nome.toLowerCase()));
    final todas = List<int>.generate(faixas.length, (i) => i)
      ..sort((a, b) => faixas[a].buscavel.compareTo(faixas[b].buscavel));
    return Biblioteca(
      faixas,
      [Playlist('Todas as músicas', todas), ...listas],
      maisNovo,
    );
  }

  static Future<Directory> pastaAcervo() async {
    final base = await getApplicationSupportDirectory();
    return Directory(p.join(base.path, 'acervo'));
  }
}

/// O que aconteceu numa importacao -- para a tela CONTAR, nunca so dizer "ok".
class Relatorio {
  final String pacote;
  final int faixas;
  final int capas;
  final int faltando;
  final List<String> problemas;
  const Relatorio({
    required this.pacote,
    required this.faixas,
    required this.capas,
    required this.faltando,
    required this.problemas,
  });
  bool get bom => problemas.isEmpty && faltando == 0 && faixas > 0;
}

/// Importa um .zip do Roxin. Extrai para uma pasta temporaria e so promove no
/// fim: importacao interrompida nao deixa biblioteca pela metade.
Future<Relatorio> importarPacote(
  String zipPath, {
  void Function(int feitas, int total)? progresso,
}) async {
  final problemas = <String>[];
  final arquivo = File(zipPath);
  if (!await arquivo.exists()) {
    return Relatorio(
        pacote: p.basename(zipPath),
        faixas: 0,
        capas: 0,
        faltando: 0,
        problemas: ['o arquivo não está mais lá']);
  }

  // ATENCAO, divida honesta: checar espaco livre ANTES de extrair pede API
  // nativa (StatFs) e portanto um plugin a mais. Ainda NAO foi feito. Por
  // enquanto o que existe e o tratamento do erro: se o aparelho encher no meio,
  // a extracao morre dentro do try, a pasta .parcial e apagada e a tela mostra
  // o motivo -- a biblioteca nao fica pela metade. Falta o aviso preventivo.
  final raiz = await Biblioteca.pastaAcervo();
  await raiz.create(recursive: true);

  final zip = ZipDecoder().decodeBuffer(InputFileStream(zipPath));
  final entradas = {for (final e in zip.files) e.name: e};
  final indiceBruto = entradas['roxin.json'];
  if (indiceBruto == null) {
    return Relatorio(
        pacote: p.basename(zipPath),
        faixas: 0,
        capas: 0,
        faltando: 0,
        problemas: ['não é um pacote do Roxin: falta o roxin.json']);
  }

  final ind = jsonDecode(
      utf8.decode(indiceBruto.content as List<int>)) as Map<String, dynamic>;
  final listaFaixas = (ind['faixas'] as List? ?? const []);
  final nome = _nomePasta(ind, zipPath);

  final destino = Directory(p.join(raiz.path, nome));
  final parcial = Directory(p.join(raiz.path, '.$nome.parcial'));
  if (await parcial.exists()) await parcial.delete(recursive: true);
  await parcial.create(recursive: true);

  int copiadas = 0, capas = 0, faltando = 0;
  try {
    for (final f in listaFaixas) {
      final rel = f['arquivo'] as String?;
      if (rel == null) continue;
      // caminho absoluto no indice seria invasao de pasta: recusa, nao conserta
      if (caminhoSuspeito(rel)) {
        problemas.add('caminho inválido no índice: $rel');
        continue;
      }
      final dentro = entradas[rel];
      if (dentro == null) {
        faltando++;
        continue;
      }
      final bytes = dentro.content as List<int>;
      final esperado = (f['sha256'] as String?) ?? '';
      if (esperado.isNotEmpty &&
          sha256.convert(bytes).toString() != esperado) {
        problemas.add('${p.basename(rel)}: conteúdo diferente do índice');
        continue;
      }
      await _escrever(p.join(parcial.path, rel), bytes);
      copiadas++;
      final capaRel = f['capa'] as String?;
      if (capaRel != null && !caminhoSuspeito(capaRel)) {
        final c = entradas[capaRel];
        if (c != null) {
          await _escrever(p.join(parcial.path, capaRel), c.content as List<int>);
          capas++;
        }
      }
      progresso?.call(copiadas, listaFaixas.length);
    }
    await _escrever(p.join(parcial.path, 'roxin.json'),
        utf8.encode(jsonEncode(ind)));

    if (problemas.isEmpty && copiadas > 0) {
      if (await destino.exists()) await destino.delete(recursive: true);
      await parcial.rename(destino.path);
    } else {
      await parcial.delete(recursive: true); // ou entra tudo, ou nada
    }
  } catch (e) {
    final txt = e.toString();
    problemas.add(txt.contains('space') || txt.contains('ENOSPC')
        ? 'o aparelho ficou sem espaço no meio da importação'
        : 'falhou ao gravar: $e');
    if (await parcial.exists()) await parcial.delete(recursive: true);
  }

  return Relatorio(
    pacote: nome,
    faixas: copiadas,
    capas: capas,
    faltando: faltando,
    problemas: problemas,
  );
}

String _nomePasta(Map<String, dynamic> ind, String zipPath) {
  final bruto = (ind['pacote'] as String?)?.trim();
  final base = (bruto == null || bruto.isEmpty)
      ? p.basenameWithoutExtension(zipPath)
      : bruto;
  final limpo = base.replaceAll(RegExp(r'[^\w\s\-]+'), '').trim();
  return limpo.isEmpty ? 'pacote' : limpo;
}

/// Recusa caminho que tente sair da pasta do pacote (o classico "../../").
bool caminhoSuspeito(String rel) =>
    rel.startsWith('/') ||
    rel.contains('..') ||
    RegExp(r'^[A-Za-z]:').hasMatch(rel);

Future<void> _escrever(String caminho, List<int> bytes) async {
  final f = File(caminho);
  await f.parent.create(recursive: true);
  await f.writeAsBytes(bytes, flush: false);
}

/// Pacotes .zip largados DENTRO da pasta do app.
///
/// Existe por causa do iPhone: la nao ha pasta "Download" compartilhada como no
/// Android. O caminho natural e o app Arquivos -- no Drive, "Salvar em
/// Arquivos" -> "No meu iPhone" -> Roxin. Com UIFileSharingEnabled ligado no
/// Info.plist, essa pasta e esta aqui embaixo, e o app acha o pacote sozinho,
/// sem o Roger ter que caçar arquivo no seletor.
Future<List<File>> pacotesLargadosAqui() async {
  try {
    final docs = await getApplicationDocumentsDirectory();
    if (!await docs.exists()) return const [];
    final achados = <File>[];
    await for (final e in docs.list()) {
      if (e is File && e.path.toLowerCase().endsWith('.zip')) achados.add(e);
    }
    achados.sort((a, b) => b.statSync().modified.compareTo(a.statSync().modified));
    return achados;
  } catch (_) {
    return const [];
  }
}

Future<bool> apagarPacote(String nome) async {
  final raiz = await Biblioteca.pastaAcervo();
  final d = Directory(p.join(raiz.path, nome));
  if (!await d.exists()) return false;
  await d.delete(recursive: true);
  return true;
}

String semAcento(String t) {
  const de = 'áàâãäéèêëíìîïóòôõöúùûüçñÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇÑ';
  const para = 'aaaaaeeeeiiiiooooouuuucnAAAAAEEEEIIIIOOOOOUUUUCN';
  final b = StringBuffer();
  for (final c in t.split('')) {
    final i = de.indexOf(c);
    b.write(i >= 0 ? para[i] : c);
  }
  return b.toString().toLowerCase();
}

String mmss(int seg) {
  if (seg <= 0) return '--:--';
  final m = seg ~/ 60, s = seg % 60;
  return '$m:${s.toString().padLeft(2, '0')}';
}
