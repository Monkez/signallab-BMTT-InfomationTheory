import catalogData from '../../../../samples/catalog.json'
import type { SampleProject } from './types'

export const sampleCatalog = catalogData as SampleProject[]

export const sampleCategories = ['All', 'Digital communications', 'Analog communications', 'Information theory', 'Python labs'] as const
