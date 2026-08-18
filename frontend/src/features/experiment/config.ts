import type { SimulationConfig } from '../../types'

export const defaultSimulationConfig: SimulationConfig = {
  mode: 'specific_steps',
  trials: 100,
  max_frames: 1,
  min_frames: 1,
  min_errors: 0,
  snr_db_start: -2,
  snr_db_stop: 10,
  snr_db_step: 2,
  snr_db_points: [0],
  workers: 0,
  seed: 2026,
  device: 'auto',
  chunk_size: 10,
}

export function snrPointCount(config: SimulationConfig) {
  if (config.mode === 'specific_steps') return 1
  return Math.max(1, Math.floor((config.snr_db_stop - config.snr_db_start) / config.snr_db_step + 1e-9) + 1)
}

export function validateSimulationConfig(config: SimulationConfig) {
  if (!['specific_steps', 'ber_benchmark'].includes(config.mode)) return 'Choose a valid experiment mode.'
  if (!Number.isFinite(config.snr_db_start) || !Number.isFinite(config.snr_db_stop)) return 'SNR start and stop must be finite numbers.'
  if (!Number.isFinite(config.snr_db_step) || config.snr_db_step <= 0) return 'SNR step must be greater than 0.'
  if (config.snr_db_stop < config.snr_db_start) return 'SNR stop must be greater than or equal to start.'
  if (snrPointCount(config) > 10_000) return 'The SNR sweep is too large; use at most 10,000 points.'
  if (!Number.isInteger(config.max_frames) || config.max_frames < 1) return 'Max frames must be a positive integer.'
  if (!Number.isInteger(config.min_frames) || config.min_frames < 1) return 'Min frames must be a positive integer.'
  if (config.min_frames > config.max_frames) return 'Min frames cannot exceed max frames.'
  if (!Number.isInteger(config.min_errors) || config.min_errors < 0) return 'Min errors must be a non-negative integer.'
  if (!Number.isInteger(config.workers) || config.workers < 0 || config.workers > 256) return 'Workers must be an integer from 0 to 256.'
  if (!Number.isInteger(config.chunk_size) || config.chunk_size < 1) return 'Chunk size must be a positive integer.'
  if (!Number.isInteger(config.seed) || config.seed < 0 || config.seed > 0xffffffff) return 'Seed must be an integer from 0 to 4,294,967,295.'
  return ''
}
