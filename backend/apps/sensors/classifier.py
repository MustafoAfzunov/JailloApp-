"""Rule-based vibration classifier (mudflow / earthquake / vehicle / noise).

These are starting heuristics. Calibrate the thresholds against real geophone data, or replace
`classify` with a trained TinyML / scikit-learn model - the rest of the system only needs the
label and confidence it returns.
"""
from dataclasses import dataclass
from statistics import mean

NOISE_FLOOR = 0.05  # rms below this is background noise
MUDFLOW_MIN_RMS = 0.30  # rms that counts as a strong rumble
MUDFLOW_BAND_HZ = (10.0, 100.0)
EARTHQUAKE_MAX_HZ = 8.0
EDGE_TRUST_CONFIDENCE = 0.85  # trust an on-device model at or above this


@dataclass
class Classification:
    label: str
    confidence: float
    sustained: int = 0
    rising: bool = False


def features_from_samples(samples, sample_rate_hz):
    """Return (rms, dominant_freq_hz) from raw geophone samples."""
    import numpy as np

    x = np.asarray(samples, dtype=float)
    x = x - x.mean()
    rms = float(np.sqrt(np.mean(x**2)))
    if len(x) < 8 or not sample_rate_hz:
        return rms, None
    spectrum = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    freqs = np.fft.rfftfreq(len(x), d=1.0 / sample_rate_hz)
    spectrum[0] = 0.0
    return rms, float(freqs[int(np.argmax(spectrum))])


def classify(rms, freq, prev_rms, edge_label=None, edge_conf=None) -> Classification:
    """Classify one reading using the node's recent history.

    prev_rms: rms values of the node's previous readings in the last ~2 minutes.
    """
    if rms is None or rms < NOISE_FLOOR:
        return Classification("noise", 0.9)

    strong = rms >= MUDFLOW_MIN_RMS
    sustained = 1 + sum(1 for r in prev_rms if r >= MUDFLOW_MIN_RMS) if strong else 0
    rising = len(prev_rms) >= 2 and rms >= 1.3 * mean(prev_rms)

    if edge_label == "mudflow" and (edge_conf or 0) >= EDGE_TRUST_CONFIDENCE and strong:
        return Classification("mudflow", round(min(0.99, edge_conf), 2), sustained, rising)

    if freq is not None and freq < EARTHQUAKE_MAX_HZ and rms >= 0.15:
        return Classification("earthquake", round(min(0.95, 0.5 + rms), 2), sustained, rising)

    in_band = freq is None or MUDFLOW_BAND_HZ[0] <= freq <= MUDFLOW_BAND_HZ[1]
    if in_band and strong and (sustained >= 3 or rising):
        conf = 0.5 + 0.25 * min(1.0, rms) + 0.15 * min(sustained, 5) / 5 + (0.1 if rising else 0.0)
        return Classification("mudflow", round(min(0.99, conf), 2), sustained, rising)

    if in_band:
        return Classification("vehicle", 0.7 if sustained <= 1 else 0.6, sustained, rising)
    return Classification("noise", 0.6, sustained, rising)
