# CoreWeave Entropy Engine

A private GlacierEQ R&D prototype for **calibrated entropy-drift detection in infrastructure telemetry**.

## Implemented mechanism

The engine now has an explicit two-phase lifecycle:

1. collect enough observations for each metric;
2. explicitly calibrate an entropy baseline;
3. continue ingesting telemetry;
4. compare current distribution entropy with the frozen calibration value;
5. emit an entropy-drift signal when configured relative or absolute thresholds are crossed.

For near-zero baseline entropy, the detector uses an absolute-change threshold rather than inventing an unstable relative percentage.

## Truth boundary

This repository does **not** claim:

- that this mechanism is universally novel;
- that it predicts hardware or cluster failure;
- a calibrated failure probability;
- a time-to-failure estimate;
- CoreWeave affiliation or production deployment;
- reduced downtime or improved availability.

The previous source described the prototype as something "no one has built" and converted entropy trends into a `FAILURE_LIKELY` prediction with a synthetic time horizon. Repository evidence did not support those claims. The repaired mechanism emits only what the code can establish: **distribution entropy changed relative to an explicit baseline**.

## Verification

```bash
python -m unittest discover -s tests -v
python src/entropy_engine.py
```

CI targets the actual default branch, `master`.

## Promotion gates

Any future failure-prediction claim requires a separate evidence program:

- labeled normal and failure telemetry;
- train/calibration/evaluation separation;
- baseline methods and ablations;
- precision, recall, false-positive rate, and lead-time measurements;
- calibration analysis for any probability claim;
- reproducible runtime receipts;
- evidence that the mechanism changes an operational decision safely.

Until then this remains an entropy-drift experiment, not a failure predictor.
