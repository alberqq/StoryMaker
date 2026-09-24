interface Props {
  texto?: string
}

/** La marca visual de algo que cambió respecto de la versión anterior. */
export function MarcaCambiado({ texto = 'cambiado' }: Props) {
  return <span className="marca-cambiado">{texto}</span>
}
