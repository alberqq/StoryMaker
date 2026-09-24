import fsd from '@feature-sliced/steiger-plugin'
import { defineConfig } from 'steiger'

// Steiger informa y no bloquea (spec §8): el script `estructura` termina en verde aunque
// haya hallazgos, y la CI publica su salida junto al informe de G1.
export default defineConfig([...fsd.configs.recommended])
