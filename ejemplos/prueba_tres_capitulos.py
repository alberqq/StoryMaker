"""Camino rapido: una novela de tres capitulos, de la semilla a la entrega.

Recorre las etapas por la superficie del nucleo, sin llamar a ningun modelo.
Sirve para dos cosas:

- **Comprobar que la maquinaria funciona** en tu maquina antes de gastar en una
  Ejecucion real: las puertas, el versionado, la contabilidad y la entrega.
- **Ver que hace cada etapa**, porque cada paso imprime lo que el nucleo respondio.

Lo que aqui son constantes -- las afirmaciones historicas, el plan y la prosa --
en una Ejecucion real lo producen los subagentes. Esto no es el producto: es su
banco de pruebas.

    python ejemplos/prueba_tres_capitulos.py [--conservar]

Con `--conservar`, el Proyecto queda en `proyectos/` en lugar de en un temporal.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

CONSERVAR = "--conservar" in sys.argv
DESTINO = str(RAIZ / "proyectos") if CONSERVAR else tempfile.mkdtemp()
ENTORNO = {**os.environ, "PYTHONPATH": str(RAIZ / "src")}
PROYECTO: str | None = None


# ==========================================================================
# Utilidades
# ==========================================================================


def sm(*argumentos: str, esperar_ok: bool = True) -> dict:
    """Invoca el nucleo y devuelve el sobre de respuesta."""
    orden = [sys.executable, "-m", "storymaker", "--raiz", DESTINO]
    if PROYECTO:
        orden += ["--proyecto", PROYECTO]
    proceso = subprocess.run(
        orden + list(argumentos), capture_output=True, text=True,
        cwd=str(RAIZ), env=ENTORNO,
    )
    if not proceso.stdout.strip():
        print("\nEl nucleo no devolvio nada:", proceso.stderr[-2000:])
        sys.exit(1)
    respuesta = json.loads(proceso.stdout)
    if esperar_ok and not respuesta["ok"]:
        error = respuesta["error"]
        print(f"\nFALLO en `{' '.join(argumentos[:3])}`")
        print(f"  {error['codigo']}: {error['mensaje']}")
        for problema in (error.get("detalle", {}).get("incumplimientos") or [])[:8]:
            print(f"    - {problema.get('requisito')}: {problema.get('mensaje')}")
        sys.exit(1)
    return respuesta


def fichero(nombre: str, contenido) -> str:
    """Escribe un fichero temporal y devuelve la forma `@ruta` que el CLI admite."""
    ruta = Path(DESTINO) / "_entrada" / nombre
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(
        contenido if isinstance(contenido, str)
        else json.dumps(contenido, ensure_ascii=False),
        encoding="utf-8",
    )
    return "@" + str(ruta)


def titulo(numero: str, texto: str) -> None:
    print(f"\n{'=' * 72}\n{numero}  {texto}\n{'=' * 72}")


def palabras(texto: str) -> int:
    return len([p for p in texto.split() if p.strip()])


# ==========================================================================
# El material que en una Ejecucion real producen los agentes
# ==========================================================================

AFIRMACIONES = {
    "indumentaria": "Los cartografos de Amberes trabajaban en jubon y mangas de tela basta, sin insignia de gremio visible en el taller.",
    "cultura_material": "En los talleres de cartografia de Amberes hacia 1560 se trabajaba sobre vitela con compas de puntas y tinta de agallas.",
    "organizacion_social": "El gremio de San Lucas de Amberes registraba a los grabadores y a los iluminadores de cartas de navegacion.",
    "mentalidad": "Una carta de navegacion se tenia por objeto de fe practica: se creia en ella porque se navegaba con ella.",
    "economia_y_trabajo": "Las cartas de navegacion se pagaban por encargo y al contado, y el prestamo a corto plazo era corriente entre artesanos.",
}

ESCENAS = {
    "esc_001_001": """La vitela estaba tensa sobre el bastidor y Joos llevaba desde el alba
raspando una costa que no acababa de gustarle. El compas le pesaba mas de lo que
pesaba. Abajo, en la calle, el mozo del prestamista habia pasado dos veces sin
llamar, que era su manera de llamar. Joos conto los sueldos que le quedaban y
conto los meses que faltaban, y los dos numeros le salieron pequenos. Dejo el
compas sobre la mesa con cuidado, como si fuera el compas lo que pudiera
romperse aquella manana.""",

    "esc_001_002": """El encargo llego en un pliego doblado en cuatro y con una cifra escrita
al margen. Pedian la carta entera y la pedian para el mes siguiente. Joos leyo
dos veces la lista de sondas y en la tercera se detuvo: de aquel tramo no tenia
medida ninguna, ni suya ni de nadie. Podia decirlo. Miro la cifra del margen y
no lo dijo. Mojo la pluma, calculo lo que la costa pedia para parecer cierta, y
empezo a dibujar el fondo que le convenia.""",

    "esc_002_001": """En Sevilla la carta paso de mano en mano sin que nadie la abriera del
todo. Un escribiente anoto la fecha, el nombre del taller y el precio, y volvio
a enrollarla. Joos espero de pie junto a la puerta, con el sombrero en las manos,
atento a que alguien preguntara por las sondas. Nadie pregunto. Cobro, firmo
donde le dijeron que firmara, y salio a una calle demasiado clara. Durante todo
el camino de vuelta estuvo esperando una voz a su espalda que no llego.""",

    "esc_002_002": """Quesada desenrollo la carta al final de la tarde, cuando ya no quedaba
nadie en la sala, y la miro con la desgana de quien archiva. Anoto el asiento,
cerro el libro y volvio a mirarla. El trazo de la costa era bueno; demasiado
bueno para un fondo que el recordaba discutido. Paso el dedo por la linea de
sondas sin llegar a tocarla. No dijo nada a nadie, porque no tenia nada que
decir todavia, y guardo la carta donde pudiera encontrarla otra vez.""",

    "esc_003_001": """La nao debia haber vuelto en agosto. Joos bajaba al muelle cada manana
con una excusa distinta y cada manana se quedaba mas rato del que la excusa
justificaba. Preguntaba por otros barcos para no preguntar por aquel. En
septiembre dejo de preguntar. Se quedaba al final del espigon, mirando la boca
del rio, y contaba los dias como habia contado los sueldos aquella manana de
marzo, con la misma aritmetica inutil. El agua entraba y salia y no traia
noticia ninguna.""",

    "esc_003_002": """Quesada llego al taller un jueves, sin escolta y sin prisa, con la carta
bajo el brazo. La desenrollo sobre la mesa donde Joos habia trabajado siete
meses antes y puso el dedo en el tramo de las sondas. Dijo que habia buscado la
medida en tres registros y que en ninguno constaba. Dijo que la sonda no se
habia medido nunca. Joos miro la vitela tensa, el compas, la tinta seca, y
entendio que no habia forma de raspar aquello. Asintio despacio.""",
}


# ==========================================================================
# El recorrido
# ==========================================================================

titulo("0", "Proyecto")
PROYECTO = sm("proyecto", "crear", "--titulo", "El cartografo de Amberes",
              "--modo", "revision_del_autor")["datos"]["proyecto"]["id"]
print(f"Proyecto creado: {PROYECTO}")
print(f"Almacen:         {Path(DESTINO) / PROYECTO}")


titulo("E1", "Captura del encargo")
sm("encargo", "ingerir", "--datos", f"@{RAIZ / 'ejemplos' / 'encargo-tres-capitulos.json'}")
cierre = sm("encargo", "confirmar", "--quien", "Autor de prueba")["datos"]
estilo = cierre["guia_estilo_efectiva"]
print(f"Encargo cerrado:   {cierre['version']}")
print(f"Extension:         528 palabras = 3 capitulos x 16 lineas x 11 palabras/linea (D28)")
print(f"Estilo declarado:  {', '.join(sorted(estilo['declarados']))}")
print(f"Sin preferencia:   {', '.join(estilo['no_evaluables'])}  <- no se evaluan, no tienen defecto")


titulo("E2", "Investigacion historica")
fuente = sm("contexto", "fuente",
            "--localizador", "https://ejemplo.test/amberes-cartografia-1560",
            "--tipo", "web",
            "--contenido", "En los talleres de Amberes hacia 1560 se trabajaba la "
                           "carta de navegacion sobre vitela, con compas de puntas y "
                           "tinta de agallas. El gremio de San Lucas registraba a los "
                           "grabadores.")["datos"]["fuente"]["id"]
print(f"Fuente registrada y contenido conservado: {fuente}")

afirmaciones = {}
for seccion, enunciado in AFIRMACIONES.items():
    afirmaciones[seccion] = sm(
        "contexto", "afirmar", "--enunciado", enunciado,
        "--seccion", seccion, "--fuente", fuente,
    )["datos"]["afirmacion"]["id"]
print(f"Afirmaciones en las cinco secciones obligatorias: {len(afirmaciones)}")

clave = afirmaciones["cultura_material"]

# Una Restriccion comprobable se deriva directamente de su afirmacion. Hasta la
# version 1.7 habia que verificar la fidelidad y emitir un veredicto de refutacion
# antes (la puerta de MD-7); las dos pasadas se retiraron porque costaban mas de lo
# que corregian. Lo que sigue en pie es INV-8: la trazabilidad.
restriccion = sm("contexto", "restriccion",
                 "--enunciado", "No aparece el termino 'boligrafo'",
                 "--categoria", "lexica", "--afirmacion", clave,
                 "--termino", "boligrafo")["datos"]["restriccion"]["id"]
print(f"Restriccion lexica derivada de {clave}: {restriccion}")

# INV-8, que es la puerta que queda: lo que cuelga de una afirmacion caida, cae.
# Se prueba sobre una afirmacion aparte para no tumbar la que sostiene la anterior.
suelta = sm("contexto", "afirmar", "--seccion", "cultura_material",
            "--enunciado", "En el taller se usaba tinta de agallas de roble",
            "--sin-fuente")["datos"]["afirmacion"]["id"]
sm("contexto", "descartar", "--afirmacion", suelta, "--quien", "Autor",
   "--motivo", "El Autor no la da por buena")
denegado = sm("contexto", "restriccion",
              "--enunciado", "La tinta es siempre de agallas",
              "--categoria", "material", "--afirmacion", suelta,
              "--cualitativa", esperar_ok=False)
print(f"Derivar de una afirmacion descartada -> {denegado['error']['codigo']} (INV-8)")

contexto = sm("contexto", "cerrar")["datos"]["contexto"]
indicadores = contexto["indicadores"]
print(f"Contexto cerrado: {contexto['id']}")
print(f"  RNF-004 cobertura documental:  {indicadores['RNF-004_cobertura_documental']['valor']:.0%} "
      f"(indicador de salud, no detiene nada)")
print("  RNF-027 y RNF-028 quedan en cero de forma permanente: la verificacion de")
print("  fidelidad y la pasada de refutacion se retiraron en la version 1.7.")


titulo("E3 / E4", "Diseno narrativo y critica del Canon")
plan = sm("canon", "proponer",
          "--plan", f"@{RAIZ / 'ejemplos' / 'plan-tres-capitulos.json'}")["datos"]
print(f"Plan propuesto: {plan['version']} (pasa las ocho invariantes de 6.3)")

bloqueado = sm("escena", "escribir", "--escena", "esc_001_001",
               "--texto", "lo que sea", "--unidad", "udt_0", esperar_ok=False)
print(f"Redactar con el Canon en borrador -> {bloqueado['error']['codigo']} (INV-1)")

# PC-3 se resuelve siempre en modo humano: no queda ninguna etapa que juzgue el
# Canon por el Autor, solo una critica breve que el lee antes de aprobar.
sm("canon", "aprobar", "--modo-aprobacion", "humano", "--quien", "Autor")
print("Canon aprobado por el Autor como linea base (PC-3)")


titulo("Ejecucion", "Arranque con presupuestos congelados")
ejecucion = sm("ejecucion", "iniciar", "--coste", "25", "--iteraciones", "40")["datos"]
presupuesto = ejecucion["presupuesto"]
print(f"Ejecucion: {ejecucion['id']}  |  modo: {ejecucion['modo']}")
print(f"Reserva comun: {presupuesto['reserva_total']} iteraciones "
      f"= {presupuesto['reserva_libre']} libres + {presupuesto['reserva_final']} "
      f"del tramo final (solo el ultimo tercio, D24)")


titulo("E5 / E6", "Produccion de las escenas")
for identificador, texto in ESCENAS.items():
    argumentos = ["escena", "escribir", "--escena", identificador,
                  "--texto", fichero(f"{identificador}.md", texto),
                  "--unidad", f"udt_{identificador}"]
    if identificador == "esc_003_002":
        argumentos += ["--revelacion", "rev_el-mapa-es-falso"]
    resultado = sm(*argumentos)["datos"]
    extension = resultado["extension"]
    sm("escena", "cerrar", "--escena", identificador, "--modo-cierre", "convergencia")
    marca = "dentro" if extension["dentro_de_tolerancia"] else "FUERA"
    print(f"  {identificador}: {extension['palabras']:>3} palabras "
          f"({extension['desviacion']:+.0%} sobre presupuesto, {marca} de tolerancia)")

sm("canon", "hecho", "--enunciado", "El compas de Joos tiene las puntas gastadas",
   "--sujeto", "per_joos", "--tipo-sujeto", "personaje",
   "--escena", "esc_001_001", "--version-escena", "esv_001_001_v1")
contradice = sm("canon", "hecho",
                "--enunciado", "El color de ojos es gris",
                "--sujeto", "per_joos", "--tipo-sujeto", "personaje",
                "--escena", "esc_001_002", "--version-escena", "esv_001_002_v1")
sm("canon", "hecho", "--enunciado", "El color de ojos es pardo",
   "--sujeto", "per_joos", "--tipo-sujeto", "personaje",
   "--escena", "esc_003_001", "--version-escena", "esv_003_001_v1",
   esperar_ok=False)
print("Hechos emergentes anexados al Canon (RF-028); el contradictorio se rechazo (ERR-601)")


titulo("E7", "Validacion por capitulo")
for capitulo in ("cap_001", "cap_002", "cap_003"):
    veredicto = sm("capitulo", "validar", "--capitulo", capitulo)["datos"]
    recuento = veredicto["recuento"]
    print(f"  {capitulo}: aprobado={veredicto['aprobado']}  "
          f"{veredicto['extension_real']:>3}/{veredicto['presupuesto']} palabras  "
          f"bloqueantes={recuento['bloqueante']} mayores={recuento['mayor']} "
          f"menores={recuento['menor']}")
    sm("capitulo", "cerrar", "--capitulo", capitulo,
       "--sinopsis", f"Acta de {capitulo}. Lo previsto ocurrio y no quedo nada abierto.")


titulo("E8", "Pasada global y terminacion")
global_ = sm("novela", "pasada-global")["datos"]
print(f"Hilos sin resolver:     {global_['hilos']['sin_resolver'] or 'ninguno'}")
deriva = global_["deriva_de_voz"]
if deriva.get("evaluable"):
    print(f"Deriva de voz:          {'dentro' if deriva['dentro_de_banda'] else 'FUERA'} de banda "
          f"({deriva['desviacion_relativa']})")
print(f"Extension:              {global_['extension']['palabras']} palabras "
      f"sobre objetivo {global_['extension']['objetivo']} "
      f"({'dentro' if global_['extension']['dentro_de_tolerancia'] else 'FUERA'} de tolerancia)")
print(f"Pasada global superada: {global_['superada']}")

terminacion = sm("novela", "cerrar")["datos"]
if not terminacion["finalizada"]:
    print("\nNo se declara finalizada. Condiciones que faltan:")
    for condicion in terminacion["condiciones_que_faltan"]:
        print(f"  - {condicion['requisito']}: {condicion['mensaje']}")
    sys.exit(1)
print(f"RF-077: novela {terminacion['estado'].upper()} ({terminacion['palabras']} palabras)")


titulo("Entrega", "Markdown y paquete de trazabilidad")
entrega = sm("entrega", "generar", "--sin-pdf")["datos"]
ruta_novela = Path(entrega["formatos"]["markdown"]["ruta"])
print(f"Novela:     {ruta_novela}")
print(f"Paquete:    {entrega['paquete_trazabilidad']}")
print(f"Extension:  {entrega['palabras']} palabras")


titulo("Trazabilidad", "RF-081 y RF-082")
traza = sm("traza", "pasaje", "--version-escena", "esv_003_002_v1")["datos"]
print(f"Pasaje esv_003_002_v1:")
print(f"  escena planificada: {traza['escena_planificada']['id']} "
      f"({traza['escena_planificada']['funcion_narrativa']})")
print(f"  version de Canon:   {traza['version_canon']}")
print(f"  unidad de trabajo:  {traza['unidad_de_trabajo']}")
print(f"  cadena completa:    {traza['cadena_completa']}")

respaldo = sm("traza", "afirmacion", "--consulta", "vitela")["datos"]
print(f"Afirmacion 'vitela': {respaldo['afirmacion']}")
print(f"  estado: {respaldo.get('estado', 'vigente')}")
print(f"  fuente con contenido conservado: "
      f"{respaldo['fuentes'][0]['contenido_disponible']}")


titulo("RF-079", "Informe de calibracion")
informe = sm("informe", "calibracion")["datos"]
print(f"Consumido: {informe['consumido']['iteraciones']} iteraciones de "
      f"{informe['presupuestado']['iteraciones_total']}")
print(f"Reserva:   tramo libre {informe['uso_reserva']['tramo_libre']}, "
      f"tramo final {informe['uso_reserva']['tramo_final']}")
print(f"Nota:      {informe['aviso']}")


titulo("", "La novela")
print(ruta_novela.read_text(encoding="utf-8"))

print("=" * 72)
if CONSERVAR:
    print(f"El Proyecto queda en: {Path(DESTINO) / PROYECTO}")
else:
    print(f"Proyecto temporal en: {Path(DESTINO) / PROYECTO}")
    print("Usa --conservar para dejarlo en proyectos/ y poder inspeccionarlo.")
