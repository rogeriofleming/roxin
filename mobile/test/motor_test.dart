// Testes do motor do Roxin Mobile, sem aparelho e sem plugin.
//
//     flutter test
//
// Cada trava tem CONTROLE POSITIVO: uma versao quebrada de proposito que o teste
// tem que reprovar. Teste que so passa nao prova que olhou.
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as p;
import 'package:roxin/pacote.dart';

/// Monta um acervo de mentira no formato que o `empacotar.py` produz.
Future<Directory> acervoDeMentira({
  bool comCapa = true,
  bool faltarUmArquivo = false,
  bool indiceIlegivel = false,
  String? caminhoMalicioso,
}) async {
  final raiz = await Directory.systemTemp.createTemp('roxin_teste_');
  final pac = Directory(p.join(raiz.path, 'Ghibli melhores'));
  await Directory(p.join(pac.path, 'musicas')).create(recursive: true);
  await Directory(p.join(pac.path, 'capas')).create(recursive: true);

  final nomes = ['Chihiro - Uma Manhã.mp3', 'Totoro - Caminho.mp3', 'Kiki - Vôo.m4a'];
  final faixas = <Map<String, dynamic>>[];
  for (var i = 0; i < nomes.length; i++) {
    final rel = 'musicas/${nomes[i]}';
    final ehOUltimo = i == nomes.length - 1;
    if (!(faltarUmArquivo && ehOUltimo)) {
      await File(p.join(pac.path, 'musicas', nomes[i]))
          .writeAsBytes(List<int>.filled(64, i + 1));
    }
    String? capaRel;
    if (comCapa) {
      capaRel = 'capas/${p.basenameWithoutExtension(nomes[i])}.png';
      await File(p.join(pac.path, 'capas',
              '${p.basenameWithoutExtension(nomes[i])}.png'))
          .writeAsBytes([0x89, 0x50, 0x4E, 0x47]);
    }
    faixas.add({
      'arquivo': (caminhoMalicioso != null && i == 0) ? caminhoMalicioso : rel,
      'titulo': p.basenameWithoutExtension(nomes[i]),
      'duracao': 120 + i,
      'capa': capaRel,
    });
  }

  final ind = {
    'versao': 1,
    'gerado': '2026-09-27T12:40:00-03:00',
    'pacote': 'Ghibli melhores',
    'faixas': faixas,
    'playlists': [
      {'nome': 'Ghibli melhores', 'faixas': [0, 1, 2]}
    ],
  };
  await File(p.join(pac.path, 'roxin.json'))
      .writeAsString(indiceIlegivel ? '{isto nao e json' : jsonEncode(ind));
  return raiz;
}

void main() {
  group('a biblioteca lê o pacote', () {
    test('as 3 faixas entram, com título, duração e capa', () async {
      final raiz = await acervoDeMentira();
      final b = await Biblioteca.carregar(de: raiz);
      expect(b.faixas.length, 3);
      expect(b.faixas.map((f) => f.titulo), contains('Chihiro - Uma Manhã'));
      expect(b.faixas.first.duracao, 120);
      expect(b.faixas.every((f) => f.capa != null), isTrue);
      await raiz.delete(recursive: true);
    });

    test('a playlist do pacote aparece, e "Todas as músicas" vem no topo',
        () async {
      final raiz = await acervoDeMentira();
      final b = await Biblioteca.carregar(de: raiz);
      expect(b.playlists.first.nome, 'Todas as músicas');
      expect(b.playlists.map((l) => l.nome), contains('Ghibli melhores'));
      expect(b.playlists.first.faixas.length, 3);
      await raiz.delete(recursive: true);
    });

    test('"Todas as músicas" sai em ordem alfabética, como no app de mesa',
        () async {
      final raiz = await acervoDeMentira();
      final b = await Biblioteca.carregar(de: raiz);
      final titulos =
          b.playlists.first.faixas.map((i) => b.faixas[i].buscavel).toList();
      final ordenado = [...titulos]..sort();
      expect(titulos, ordenado);
      await raiz.delete(recursive: true);
    });

    test('CONTROLE: faixa que não chegou NÃO vira fantasma na lista', () async {
      final raiz = await acervoDeMentira(faltarUmArquivo: true);
      final b = await Biblioteca.carregar(de: raiz);
      expect(b.faixas.length, 2, reason: 'a 3a nao existe em disco');
      // e a playlist nao pode apontar para uma faixa que nao entrou
      for (final l in b.playlists) {
        for (final i in l.faixas) {
          expect(i, lessThan(b.faixas.length));
        }
      }
      await raiz.delete(recursive: true);
    });

    test('CONTROLE: índice ilegível não derruba a biblioteca inteira',
        () async {
      final raiz = await acervoDeMentira(indiceIlegivel: true);
      final b = await Biblioteca.carregar(de: raiz);
      expect(b.semNada, isTrue, reason: 'aquele pacote e ignorado, sem crash');
      await raiz.delete(recursive: true);
    });

    test('biblioteca vazia quando não há acervo', () async {
      final raiz = await Directory.systemTemp.createTemp('roxin_vazio_');
      final b = await Biblioteca.carregar(de: raiz);
      expect(b.semNada, isTrue);
      expect(b.faixas, isEmpty);
      await raiz.delete(recursive: true);
    });

    test('a data do pacote é lida (para a tela poder mostrar dado velho)',
        () async {
      final raiz = await acervoDeMentira();
      final b = await Biblioteca.carregar(de: raiz);
      expect(b.geradoEm, isNotNull);
      expect(b.geradoEm!.year, 2026);
      await raiz.delete(recursive: true);
    });
  });

  group('a trava de caminho', () {
    test('recusa caminho absoluto, do Windows e do Unix', () {
      expect(caminhoSuspeito(r'D:\Music\x.mp3'), isTrue);
      expect(caminhoSuspeito('/etc/passwd'), isTrue);
    });
    test('recusa subir de pasta com ..', () {
      expect(caminhoSuspeito('../../fora.mp3'), isTrue);
      expect(caminhoSuspeito('musicas/../../fora.mp3'), isTrue);
    });
    test('aceita o caminho relativo normal do pacote', () {
      expect(caminhoSuspeito('musicas/Chihiro - Uma Manhã.mp3'), isFalse);
      expect(caminhoSuspeito('capas/x.png'), isFalse);
    });
  });

  group('apoio', () {
    test('semAcento acha o que foi digitado sem acento', () {
      expect(semAcento('Coração'), 'coracao');
      expect(semAcento('Vôo às Águas'), 'voo as aguas');
    });
    test('mmss formata, e duração desconhecida não mente um número', () {
      expect(mmss(0), '--:--');
      expect(mmss(-5), '--:--');
      expect(mmss(61), '1:01');
      expect(mmss(3599), '59:59');
      expect(mmss(600), '10:00');
    });
  });
}
