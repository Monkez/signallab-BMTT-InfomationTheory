"""SignalLab educational DSP and digital-communications toolkit.

All public functions accept ordinary array-like inputs and return NumPy arrays
or Python scalars. Import modules explicitly for discoverability, for example::

    import signallab as sl
    bits = sl.sources.random_bits(1024)
    symbols = sl.modulation.bpsk_modulate(bits)
"""

from . import channels, coding, filters, metrics, modulation, signals, sources

__all__ = ["channels", "coding", "filters", "metrics", "modulation", "signals", "sources"]
__version__ = "0.1.0"
