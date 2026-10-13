"""Exercises the microphone mixer's maths without any audio hardware.

The mixer runs inside PortAudio callbacks on a real device, which makes it
awkward to test the normal way: app.py is a script, so importing it would
build a QApplication and open a window. Instead this lifts the mixer section
straight out of app.py and runs it against stubs.

That means it tests the SHIPPING code, not a copy of it - if someone edits
app.py, this notices. The tradeoff is that it depends on the two marker lines
below still existing; it fails loudly rather than silently passing if they
move.

Run:  .venv\\Scripts\\python.exe tests\\test_mic_mixer.py
"""
import collections
import io
import os
import re
import sys
import threading
import warnings

import numpy as np

INICIO = "# ---- Sound into the microphone ----"
FIM = "mic_mixer = MicMixer()"

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(RAIZ, "app.py")


class SdStub:
    """Only what the mixer section touches at import time."""

    @staticmethod
    def query_devices():
        return [
            {"name": "Mic Falso", "max_input_channels": 2, "max_output_channels": 0,
             "hostapi": 0},
            {"name": "Cabo Falso", "max_input_channels": 0, "max_output_channels": 2,
             "hostapi": 0},
        ]

    @staticmethod
    def query_hostapis(_i):
        return {"name": "Windows WASAPI"}


def carregar():
    texto = io.open(APP, encoding="utf-8").read()
    if INICIO not in texto or FIM not in texto:
        raise SystemExit(
            "FALHA: nao achei a secao do mixer em app.py. Se ela foi "
            "renomeada, atualize INICIO/FIM neste arquivo."
        )
    corpo = texto[texto.index(INICIO):texto.index(FIM)]
    ns = {
        "np": np,
        "sd": SdStub,
        "collections": collections,
        "threading": threading,
        "re": re,
        "warnings": warnings,
        "AudioUtilities": None,  # so o caminho por id usa, e ele nao e testado aqui
        "log": lambda *_a, **_k: None,
        "config": {"settings": {}},
    }
    exec(compile(corpo, "app.py[mixer]", "exec"), ns)
    return ns


falhas = []


def checar(nome, condicao, detalhe=""):
    if condicao:
        print(f"  ok    {nome}")
    else:
        print(f"  FALHA {nome} {detalhe}")
        falhas.append(nome)


def main():
    ns = carregar()
    to_mix_shape = ns["to_mix_shape"]
    resample_linear = ns["resample_linear"]
    MicMixer = ns["MicMixer"]
    CH = ns["MIX_CHANNELS"]
    RATE = ns["MIX_SAMPLERATE"]
    CAP = ns["MIC_QUEUE_MAX_BLOCKS"]

    print("forma e canais")
    mono = np.full(100, 0.5, dtype=np.float32)
    saida = to_mix_shape(mono)
    checar("mono vira estereo", saida.shape == (100, CH), str(saida.shape))
    # The failure this guards against: averaging instead of duplicating, which
    # makes every mono clip quieter than every stereo one.
    checar("mono mantem amplitude", np.allclose(saida, 0.5), str(saida[0]))
    checar("float32", saida.dtype == np.float32, str(saida.dtype))

    seis = np.zeros((10, 6), dtype=np.float32)
    checar("excesso de canais e cortado", to_mix_shape(seis).shape == (10, CH))

    print("reamostragem")
    base = np.zeros((100, CH), dtype=np.float32)
    checar("mesma taxa nao toca nada", resample_linear(base, RATE, RATE) is base)
    metade = resample_linear(base, RATE // 2, RATE)
    checar("dobrar a taxa dobra o tamanho", len(metade) == 200, str(len(metade)))
    rampa = np.linspace(0.0, 1.0, 100, dtype=np.float32)[:, None]
    rampa = np.repeat(rampa, CH, axis=1)
    esticada = resample_linear(rampa, RATE // 2, RATE)
    checar("extremos preservados",
           abs(esticada[0, 0]) < 1e-6 and abs(esticada[-1, 0] - 1.0) < 1e-3,
           f"{esticada[0, 0]} .. {esticada[-1, 0]}")
    checar("vazio nao explode", len(resample_linear(base[:0], 100, RATE)) == 0)

    print("mixagem")
    m = MicMixer()
    m._output_stream = object()  # finge que esta rodando, sem abrir hardware
    frames = 64

    m._mic_blocks.append(np.full((frames, CH), 0.5, dtype=np.float32))
    m.feed_sound(np.full((frames, CH), 0.25, dtype=np.float32), RATE)
    out = np.zeros((frames, CH), dtype=np.float32)
    m._on_output(out, frames, None, None)
    checar("voz + som somam", np.allclose(out, 0.75), str(out[0]))

    m.stop()
    m._output_stream = object()
    m._mic_blocks.append(np.full((frames, CH), 0.9, dtype=np.float32))
    m.feed_sound(np.full((frames, CH), 0.9, dtype=np.float32), RATE)
    out = np.zeros((frames, CH), dtype=np.float32)
    m._on_output(out, frames, None, None)
    checar("estouro e ceifado em 1.0", np.allclose(out, 1.0), str(out.max()))

    m.stop()
    m._output_stream = object()
    m.feed_sound(np.full((frames, CH), 0.3, dtype=np.float32), RATE)
    out = np.zeros((frames, CH), dtype=np.float32)
    m._on_output(out, frames, None, None)
    # No mic data yet is the normal state for the first block or two; the mix
    # must still be produced, with silence where the voice would be.
    checar("sem microfone ainda, som sai sozinho", np.allclose(out, 0.3), str(out[0]))

    m.stop()
    m._output_stream = object()
    m.feed_sound(np.full((frames, CH), 0.2, dtype=np.float32), RATE)
    out = np.zeros((frames, CH), dtype=np.float32)
    m._on_output(out, frames, None, None)
    out2 = np.zeros((frames, CH), dtype=np.float32)
    m._on_output(out2, frames, None, None)
    checar("som terminado e descartado",
           np.allclose(out2, 0.0) and len(m._sounds) == 0, str(len(m._sounds)))

    print("limites da fila")
    m.stop()
    for _ in range(CAP + 5):
        m._on_input(np.zeros((frames, CH), dtype=np.float32), frames, None, None)
    # Unbounded growth here would mean latency that climbs forever instead of
    # a single dropped block.
    checar("fila nao cresce sem limite", len(m._mic_blocks) <= CAP,
           str(len(m._mic_blocks)))

    print("microfone mono")
    m.stop()
    m._output_stream = object()
    m._on_input(np.full(frames, 0.4, dtype=np.float32), frames, None, None)
    out = np.zeros((frames, CH), dtype=np.float32)
    m._on_output(out, frames, None, None)
    checar("microfone mono vira estereo", np.allclose(out, 0.4), str(out[0]))

    print("nome de dispositivo")
    desc = ns["device_description"]
    mesmo = ns["same_virtual_cable"]
    checar("descricao e o ultimo parenteses",
           desc("CABLE Input (VB-Audio Virtual Cable)") == "VB-Audio Virtual Cable",
           desc("CABLE Input (VB-Audio Virtual Cable)"))
    # Windows mostra "<nome amigavel> (<descricao do driver>)". Renomear muda
    # so a primeira parte, entao a descricao e o unico pedaco confiavel.
    checar("sobrevive a renomeacao",
           desc("CABLE Input (o app escreve aqui) (VB-Audio Virtual Cable)")
           == "VB-Audio Virtual Cable")
    checar("sem parenteses devolve vazio", desc("Microfone") == "")
    checar("nome vazio nao explode", desc("") == "" and desc(None) == "")

    print("guarda de realimentacao")
    a = "CABLE Input (o app escreve aqui) (VB-Audio Virtual Cable)"
    b = "CABLE Output (saida mixada) (VB-Audio Virtual Cable)"
    # Ler o que acabou de escrever sobe ate o clipe em menos de um segundo.
    checar("duas pontas do mesmo cabo sao detectadas", mesmo(a, b))
    checar("microfone de verdade passa",
           not mesmo("Microfone (fifine SC3)", a))
    checar("dois alto-falantes comuns passam",
           not mesmo("Alto-falantes (fifine SC3)", "Speakers (Realtek HD Audio)"))
    checar("descricao vazia nao casa com descricao vazia",
           not mesmo("Microfone", "Alto-falantes"))

    print("blocos de tamanhos diferentes")
    m.stop()
    m._output_stream = object()
    # PortAudio does not promise the callback always gets blocksize frames,
    # so the queue has to stitch partial blocks together.
    m._mic_blocks.append(np.full((20, CH), 0.1, dtype=np.float32))
    m._mic_blocks.append(np.full((20, CH), 0.2, dtype=np.float32))
    out = np.zeros((30, CH), dtype=np.float32)
    m._on_output(out, 30, None, None)
    certo = (np.allclose(out[:20], 0.1) and np.allclose(out[20:], 0.2)
             and len(m._mic_blocks) == 1 and len(m._mic_blocks[0]) == 10)
    checar("blocos parciais sao costurados", certo)
    m.stop()

    print()
    if falhas:
        print(f"{len(falhas)} FALHA(S): {', '.join(falhas)}")
        return 1
    print("todos os testes passaram")
    return 0


if __name__ == "__main__":
    sys.exit(main())
