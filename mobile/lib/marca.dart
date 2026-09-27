// A identidade do Roxin no celular.
//
// As cores sao as MESMAS do BRANDING.md do app de mesa -- nao ha paleta nova aqui.
// O passaro tambem nao foi redesenhado: os numeros abaixo sao os mesmos de
// `marca.py` (caminho_passaro / caminho_asa), canvas 100x100, so traduzidos de
// QPainterPath para Path. Vetor e nao imagem pelo mesmo motivo de la: escala para
// qualquer tamanho sem borrar e a cor muda sem reexportar nada.
import 'package:flutter/material.dart';

class Cores {
  static const noite = Color(0xFF0F0C16); // fundo: madrugada, nunca preto puro
  static const painel = Color(0xFF181425); // superficie um degrau acima
  static const divisao = Color(0xFF272033); // linhas que separam sem gritar
  static const pena = Color(0xFFE9E5EF); // texto
  static const penaFraca = Color(0xFF8F88A3); // duracoes, contagens, rotulos
  static const roxo = Color(0xFFA77CF0); // O Roxin: so o que acontece AGORA
  static const roxoClaro = Color(0xFFBB97F6); // toque
  static const luar = Color(0xFF6D5F9E); // apoio, com parcimonia
}

/// Georgia e Segoe UI nao existem no celular. Enquanto ele nao escolher as
/// substitutas (e uma troca, nao uma melhoria -- a marca muda de voz um pouco),
/// os titulos usam a serifada do sistema e a interface a sem-serifa do sistema.
const familiaSerifa = 'serif';

/// O rouxinol de perfil, pousado, olhando para a esquerda.
class Passaro extends CustomPainter {
  final Color cor;
  final Color? corAsa;
  final bool olho;
  const Passaro({this.cor = Cores.roxo, this.corAsa, this.olho = true});

  static Path corpo() {
    final p = Path();
    // bico: curto e encaixado na cabeca
    p.moveTo(11, 32);
    p.lineTo(26, 28.5);
    p.lineTo(26, 36.5);
    p.close();
    // cabeca + costas + cauda + peito, num traco so
    final c = Path();
    c.moveTo(25, 25);
    c.cubicTo(33, 15, 49, 20, 54, 34);
    c.cubicTo(59, 45, 66, 54, 74, 59);
    c.lineTo(95, 79); // cauda: ponta longa e inclinada, a marca do bicho
    c.lineTo(87, 83);
    c.cubicTo(73, 75, 62, 71, 52, 68);
    c.cubicTo(37, 64, 26, 54, 24, 43);
    c.cubicTo(23, 36, 22, 30, 25, 25);
    c.close();
    p.addPath(c, Offset.zero);
    return p;
  }

  static Path asa() {
    final a = Path();
    a.moveTo(33, 38);
    a.cubicTo(45, 36, 56, 45, 62, 58);
    a.cubicTo(52, 56, 40, 50, 33, 38);
    a.close();
    return a;
  }

  @override
  void paint(Canvas canvas, Size size) {
    canvas.save();
    canvas.scale(size.width / 100.0, size.height / 100.0);
    canvas.drawPath(corpo(), Paint()..color = cor);
    // a asa e um tom mais escuro do mesmo roxo (no Qt era darker(135))
    final escura = corAsa ??
        HSLColor.fromColor(cor)
            .withLightness(
                (HSLColor.fromColor(cor).lightness / 1.35).clamp(0.0, 1.0))
            .toColor();
    canvas.drawPath(asa(), Paint()..color = escura);
    if (olho) {
      canvas.drawCircle(const Offset(30, 30), 2.6, Paint()..color = Cores.noite);
    }
    canvas.restore();
  }

  @override
  bool shouldRepaint(Passaro old) =>
      old.cor != cor || old.corAsa != corAsa || old.olho != olho;
}

/// O passaro pronto para pôr na tela, no tamanho pedido.
class MarcaRoxin extends StatelessWidget {
  final double tam;
  final Color cor;
  const MarcaRoxin({super.key, this.tam = 28, this.cor = Cores.roxo});

  @override
  Widget build(BuildContext context) => SizedBox(
        width: tam,
        height: tam,
        child: CustomPaint(painter: Passaro(cor: cor)),
      );
}

/// O tema do app: escuro de madrugada, com o roxo aparecendo so no que importa.
ThemeData temaRoxin() {
  final base = ThemeData.dark(useMaterial3: true);
  return base.copyWith(
    scaffoldBackgroundColor: Cores.noite,
    colorScheme: base.colorScheme.copyWith(
      primary: Cores.roxo,
      secondary: Cores.roxoClaro,
      surface: Cores.painel,
      onSurface: Cores.pena,
    ),
    dividerColor: Cores.divisao,
    sliderTheme: base.sliderTheme.copyWith(
      activeTrackColor: Cores.roxo,
      inactiveTrackColor: Cores.divisao,
      thumbColor: Cores.roxo,
      trackHeight: 3,
      overlayShape: const RoundSliderOverlayShape(overlayRadius: 14),
      thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 6),
    ),
    snackBarTheme: base.snackBarTheme.copyWith(
      backgroundColor: Cores.painel,
      contentTextStyle: const TextStyle(color: Cores.pena),
      behavior: SnackBarBehavior.floating,
    ),
  );
}
