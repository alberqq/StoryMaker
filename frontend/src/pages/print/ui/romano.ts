const SIMBOLOS: [number, string][] = [
  [1000, 'M'],
  [900, 'CM'],
  [500, 'D'],
  [400, 'CD'],
  [100, 'C'],
  [90, 'XC'],
  [50, 'L'],
  [40, 'XL'],
  [10, 'X'],
  [9, 'IX'],
  [5, 'V'],
  [4, 'IV'],
  [1, 'I'],
]

/** Un número en romanos, como se numeran los capítulos de un libro. */
export function romano(numero: number): string {
  let resto = Math.max(0, Math.floor(numero))
  let salida = ''
  for (const [valor, simbolo] of SIMBOLOS) {
    while (resto >= valor) {
      salida += simbolo
      resto -= valor
    }
  }
  return salida || String(numero)
}
