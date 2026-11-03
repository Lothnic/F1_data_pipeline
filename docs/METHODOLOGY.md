# Methodology and interview discussion

## Question

How well can grid position, driver and constructor predict classified finishing position over the available history? This is a retrospective supervised-learning experiment with a pre-race feature set. It does not predict lap times or betting outcomes.

## Data and quality

The default path joins Jolpica bulk CSV session entries, race sessions, rounds, seasons, teams and drivers, then refreshes the latest selected season with paginated API results. The archive includes practice/qualifying and unclassified entries: only race sessions with a non-null classified position enter this analysis. Missing grid slots map to zero; missing status descriptions become Unknown. The bulk archive is cached as downloaded; fresh downloads are checked against the published SHA-256 hash. Normalized rows preserve season, round, driver and classified position; historic shared drives may contain multiple entries for one driver in a race. Validation rejects duplicate identities, missing required fields and invalid numeric values. The 2024 run contained 479 entries; field sizes can vary, so do not assume exactly 20 entries for every race. Sprint points are excluded, and the points chart is not an official championship standings reconstruction.

## Evaluation design

Sort `(season, round)` event keys and train on the earliest 75%; evaluate on all entries in later rounds. Holding out entire races prevents splitting competitors from the same race across training and test sets. One-hot encoding and grid scaling are fitted only on training rows. Unknown test identities are ignored by the encoder. Only grid, driver and constructor are predictors; points, status and finishing position are excluded. Grid zero is treated as the rear of the training field. Predictions are clipped to the training field's position range.

The baseline predicts grid position. Ridge regression uses fixed regularization of 10, with no tuning against the test set. Mean absolute error measures the average absolute position error. The model predicts a continuous position independently for each driver, so multiple drivers can receive the same prediction; this is not a constrained race-order model.

## Interpretation

On 2024 rounds 19–24, MAE was 3.13 versus 3.60 for the grid baseline, roughly a 13% reduction. This result is descriptive of one held-out block. Driver and team effects may capture car performance and cannot establish causal driver skill. Retirements, penalties, weather, strategy and safety cars create outcomes absent from these predictors. Classified position includes retirements and is not equivalent to pace.

## What to discuss in an interview

Explain why a random driver-row split would be optimistic, why a baseline matters, and why final points and retirement status would leak the outcome. Discuss the tradeoff between a simple interpretable regression and a model that enforces unique finishing positions. Demonstrate the source cache, a failing quality check, and the saved predictions rather than claiming production readiness.

## Next experiments

The default data range now spans all available seasons with explicit season-round keys. Next, add rolling validation and recent-era training windows: fixed driver/team effects over decades are a weak modeling assumption. Report variation in error across races, compare against driver/team historical baselines, and evaluate an out-of-time season. Consider separate retirement and ranking models. Fit all preprocessing within each training fold. Reserve a final untouched season before model selection. Add dataset manifests and atomic publication before scheduling production ingestion.

## Coverage and freshness

The API seasons list determines the latest year dynamically. Only returned results enter the analysis. The latest requested season is refreshed; the historical bulk archive is reused unless `--refresh` is passed. The alternative `--source api` path uses cached paginated JSON. `season_coverage.csv` and `manifest.json` show exactly what was included. Failures abort the run rather than silently skipping a season. Partial caches can resume subsequent runs. All-history MAE is not directly comparable to the 2024 reference, because eras, entrants and holdout periods differ.

## Full-history evaluation result

The verified 1950–2026 run contains 1,168 races and 26,291 classified result entries through round 19 of 2026. On the chronological holdout, ridge MAE was 4.07 versus 3.77 for grid position: the model loses to the baseline. Do not present the 2024 improvement as evidence of universal performance. Changing scoring systems, team identities, car reliability and field sizes make historical pooling a difficult domain shift problem. The next experiment should use rolling recent-season windows and compare against the same baseline, with an untouched final-season test.
