# Methodology and interview discussion

## Question

How well can grid position, driver and constructor predict classified finishing position within one season? This is a retrospective supervised-learning experiment with a pre-race feature set. It does not predict lap times or betting outcomes.

## Data and quality

Jolpica supplies paginated race results, cached as unmodified JSON. Normalized rows identify a driver within a round. Validation rejects duplicate identities, missing required fields and invalid numeric values. The 2024 run contained 479 entries; field sizes can vary, so do not assume exactly 20 entries for every race. Sprint points are excluded, and the points chart is not an official championship standings reconstruction.

## Evaluation design

Sort rounds and train on the earliest 75%; evaluate on all entries in later rounds. Holding out entire races prevents splitting competitors from the same race across training and test sets. One-hot encoding and grid scaling are fitted only on training rows. Unknown test identities are ignored by the encoder. Only grid, driver and constructor are predictors; points, status and finishing position are excluded. Grid zero is treated as the rear of the training field. Predictions are clipped to the training field's position range.

The baseline predicts grid position. Ridge regression uses fixed regularization of 10, with no tuning against the test set. Mean absolute error measures the average absolute position error. The model predicts a continuous position independently for each driver, so multiple drivers can receive the same prediction; this is not a constrained race-order model.

## Interpretation

On 2024 rounds 19–24, MAE was 3.13 versus 3.60 for the grid baseline, roughly a 13% reduction. This result is descriptive of one held-out block. Driver and team effects may capture car performance and cannot establish causal driver skill. Retirements, penalties, weather, strategy and safety cars create outcomes absent from these predictors. Classified position includes retirements and is not equivalent to pace.

## What to discuss in an interview

Explain why a random driver-row split would be optimistic, why a baseline matters, and why final points and retirement status would leak the outcome. Discuss the tradeoff between a simple interpretable regression and a model that enforces unique finishing positions. Demonstrate the source cache, a failing quality check, and the saved predictions rather than claiming production readiness.

## Next experiments

Use multiple seasons with explicit season-round keys and rolling validation. Report variation in error across races, compare against driver/team historical baselines, and evaluate an out-of-time season. Consider separate retirement and ranking models. Fit all preprocessing within each training fold. Reserve a final untouched season before model selection. Add dataset manifests and atomic publication before scheduling production ingestion.
