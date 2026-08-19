from __future__ import annotations

import numpy as np
import pytest

import signallab as sl
from backend.app.blocks import make_context, python_block


def test_sources_are_reproducible_and_text_round_trips():
    first = sl.sources.random_bits(64, seed=17)
    second = sl.sources.random_bits(64, seed=17)
    assert first.dtype == np.int8
    assert np.array_equal(first, second)
    text = "Thông tin số"
    assert sl.sources.bits_to_text(sl.sources.text_to_bits(text)) == text


def test_discrete_source_normalizes_weights_and_validates_model():
    symbols = sl.sources.random_symbols(["A", "B"], [3, 1], 20_000, seed=4)
    assert 0.72 < np.mean(symbols == "A") < 0.78
    with pytest.raises(ValueError, match="positive finite"):
        sl.sources.random_symbols(["A", "B"], [1, 0], 10)


def test_signal_measurements_resampling_and_normalization():
    signal = np.asarray([1 + 1j, -1 - 1j])
    assert sl.signals.energy(signal) == pytest.approx(4)
    assert sl.signals.average_power(signal) == pytest.approx(2)
    normalized = sl.signals.normalize_power(signal, 0.5)
    assert sl.signals.average_power(normalized) == pytest.approx(0.5)
    upsampled = sl.signals.upsample([1, 2], 3)
    assert np.array_equal(upsampled, [1, 0, 0, 2, 0, 0])
    assert np.array_equal(sl.signals.downsample(upsampled, 3), [1, 2])


def test_filter_design_and_matched_filter_have_expected_shapes():
    taps = sl.filters.fir_lowpass(1_000, 8_000, num_taps=31)
    assert taps.shape == (31,)
    assert taps.sum() == pytest.approx(1, abs=1e-12)
    rrc = sl.filters.root_raised_cosine(0.35, 4, span_symbols=6)
    assert len(rrc) == 25
    assert np.sum(rrc**2) == pytest.approx(1)
    pulse = np.asarray([1.0, 2.0, 1.0])
    assert np.array_equal(sl.filters.matched_filter([1.0], pulse, mode="full"), pulse)


def test_modulators_round_trip_without_noise():
    bits = np.asarray([0, 1, 1, 0, 0, 0], dtype=np.int8)
    assert np.array_equal(sl.modulation.bpsk_demodulate(sl.modulation.bpsk_modulate(bits)), bits)
    assert np.array_equal(sl.modulation.qpsk_demodulate(sl.modulation.qpsk_modulate(bits)), bits)
    assert np.array_equal(sl.modulation.ook_demodulate(sl.modulation.ook_modulate(bits)), bits)
    psk8_bits = np.asarray(list(np.ndindex((2, 2, 2))), dtype=np.int8).reshape(-1)
    assert np.array_equal(sl.modulation.psk8_demodulate(sl.modulation.psk8_modulate(psk8_bits)), psk8_bits)
    qam16_bits = np.asarray(list(np.ndindex((2, 2, 2, 2))), dtype=np.int8).reshape(-1)
    assert np.array_equal(sl.modulation.qam16_demodulate(sl.modulation.qam16_modulate(qam16_bits)), qam16_bits)
    with pytest.raises(ValueError, match="even bit count"):
        sl.modulation.qpsk_modulate([0, 1, 0])
    with pytest.raises(ValueError, match="divisible by 3"):
        sl.modulation.psk8_modulate([0, 1])
    with pytest.raises(ValueError, match="divisible by 4"):
        sl.modulation.qam16_modulate([0, 1, 0])


def test_channels_are_reproducible_and_meet_statistical_targets():
    clean = np.ones(100_000)
    noisy_a = sl.channels.awgn(clean, 10, seed=8)
    noisy_b = sl.channels.awgn(clean, 10, seed=8)
    assert np.array_equal(noisy_a, noisy_b)
    assert sl.metrics.measured_snr_db(clean, noisy_a) == pytest.approx(10, abs=0.15)
    source = np.tile([0, 1], 50_000)
    output = sl.channels.binary_symmetric_channel(source, 0.2, seed=3)
    assert sl.metrics.ber(source, output) == pytest.approx(0.2, abs=0.01)


def test_coding_round_trips_and_hamming_corrects_every_single_bit_error():
    data = np.asarray([1, 1, 0, 1], dtype=np.int8)
    encoded = sl.coding.hamming74_encode(data)
    assert np.array_equal(encoded, [1, 1, 0, 1, 1, 0, 0])
    for position in range(7):
        corrupted = encoded.copy()
        corrupted[position] ^= 1
        assert np.array_equal(sl.coding.hamming74_decode(corrupted), data)
    repeated = sl.coding.repetition_encode(data, repeat=5)
    assert np.array_equal(sl.coding.repetition_decode(repeated, repeat=5), data)


def test_metrics_require_matching_vectors_and_measure_evm():
    assert sl.metrics.bit_errors([0, 1, 1], [0, 0, 1]) == 1
    assert sl.metrics.ber([0, 1, 1], [0, 0, 1]) == pytest.approx(1 / 3)
    assert sl.metrics.evm_rms([1, -1], [1.1, -0.9]) == pytest.approx(10)
    with pytest.raises(ValueError, match="match exactly"):
        sl.metrics.ber([0, 1], [0])


def test_python_block_preloads_signallab_scipy_and_numpy_aliases():
    code = """def process(signal, params):
    taps = sp.signal.windows.boxcar(1)
    return sl.filters.apply_fir(np.asarray(signal), taps, mode='same')
"""
    context = make_context(np, np.random.default_rng(1), 0, 1, "cpu")
    output = python_block({"in": np.asarray([1.0, 2.0])}, {}, context, code)["out"]
    assert np.array_equal(output, [1.0, 2.0])
