import type { SimulationConfig } from '../../types'

export const defaultSimulationConfig: SimulationConfig = {
  trials: 100,
  max_frames: 100,
  min_frames: 20,
  min_errors: 100,
  snr_db_start: -2,
  snr_db_stop: 10,
  snr_db_step: 2,
  workers: 0,
  seed: 2026,
  device: 'auto',
  chunk_size: 10,
}

export function snrPointCount(config: SimulationConfig) {
  return Math.max(1, Math.floor((config.snr_db_stop - config.snr_db_start) / config.snr_db_step + 1e-9) + 1)
}
