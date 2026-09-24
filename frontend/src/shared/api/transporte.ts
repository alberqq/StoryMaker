// GENERADO por `npm run tipos` desde el OpenAPI de FastAPI. NO SE EDITA A MANO.
// Si un tipo no encaja, el cambio va en el modelo de respuesta del backend, y se regenera.
export interface paths {
    "/api/novelas": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Listar
         * @description Una tarjeta por carpeta de `proyectos/`. No hay registro global: el directorio lo es.
         */
        get: operations["listar_api_novelas_get"];
        put?: never;
        /**
         * Encargar
         * @description Escribe el encargo en la carpeta de la novela y lanza `storymaker nueva`.
         */
        post: operations["encargar_api_novelas_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/novelas/{nombre}/panel": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Panel */
        get: operations["panel_api_novelas__nombre__panel_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/novelas/{nombre}/gate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Gate */
        get: operations["gate_api_novelas__nombre__gate_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/novelas/{nombre}/fases/{fase}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Salida
         * @description La salida de una fase por su nombre castellano: `encargo`, `investigacion`, …
         */
        get: operations["salida_api_novelas__nombre__fases__fase__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/novelas/{nombre}/intentos/{capitulo_version}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Intento
         * @description El texto de un intento de capítulo, con sus incidencias.
         */
        get: operations["intento_api_novelas__nombre__intentos__capitulo_version__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/novelas/{nombre}/registros/{registro}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Registro
         * @description El final del registro de un proceso lanzado desde la interfaz.
         */
        get: operations["registro_api_novelas__nombre__registros__registro__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/novelas/{nombre}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Ficha
         * @description Fase, gate abierto si lo hay, y las versiones publicadas con fecha y puntuación.
         */
        get: operations["ficha_api_novelas__nombre__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/novelas/{nombre}/versiones/{numero}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Version
         * @description El manifiesto de una versión, sus capítulos en orden y el bloque de paratexto.
         */
        get: operations["version_api_novelas__nombre__versiones__numero__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/novelas/{nombre}/versiones/{numero}/capitulos/{orden}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Capitulo
         * @description El texto del capítulo **tal como esa versión lo fija**.
         *
         *     Se pide por versión y no «el último»: un capítulo no regenerado se comparte entre
         *     versiones, y uno regenerado tiene texto distinto en cada una.
         */
        get: operations["capitulo_api_novelas__nombre__versiones__numero__capitulos__orden__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/novelas/{nombre}/versiones/{numero}/personajes": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Personajes
         * @description Fichas de personajes y lugares, con los capítulos **de esa versión** en que aparecen.
         *
         *     La ficha cuelga de una versión y no de la novela: el canon es vivo, pero «los capítulos
         *     en los que aparece» solo tiene respuesta dentro de un manifiesto.
         */
        get: operations["personajes_api_novelas__nombre__versiones__numero__personajes_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/novelas/{nombre}/versiones/{numero}/pdf": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Pdf
         * @description El PDF que `publish` imprimió junto al fichero de la novela, para descargarlo.
         */
        get: operations["pdf_api_novelas__nombre__versiones__numero__pdf_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/novelas/{nombre}/versiones/{a}/diff/{b}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Diferencias
         * @description Qué capítulos cambian entre dos versiones. Un `JOIN`, no un diff de texto.
         */
        get: operations["diferencias_api_novelas__nombre__versiones__a__diff__b__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/encargos/validar": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Validar */
        post: operations["validar_api_encargos_validar_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/novelas/{nombre}/continuar": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Continuar */
        post: operations["continuar_api_novelas__nombre__continuar_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/novelas/{nombre}/decisiones": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Decidir
         * @description Lanza `storymaker decidir`. La interfaz nunca envía `editar` (arq. §16.5).
         */
        post: operations["decidir_api_novelas__nombre__decisiones_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/novelas/{nombre}/reintentar": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Reintentar
         * @description Lanza `storymaker reintentar`, que decide él mismo si procede.
         */
        post: operations["reintentar_api_novelas__nombre__reintentar_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/novelas/{nombre}/desbloquear": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Desbloquear
         * @description Rompe el cerrojo **solo si su proceso ha muerto**.
         */
        post: operations["desbloquear_api_novelas__nombre__desbloquear_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/novelas/{nombre}/hechos/{hecho_id}/descartar": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Descartar
         * @description Quita un hecho del corpus antes del sello, con el cerrojo tomado y trazado.
         *
         *     Queda en `edicion_humana` —el enunciado como `antes`, nada como `despues`— y en
         *     `audit_log`, igual que cualquier otra intervención del Autor.
         */
        post: operations["descartar_api_novelas__nombre__hechos__hecho_id__descartar_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/novelas/{nombre}/ediciones": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Editar
         * @description Edición humana directa de una fila, con el cerrojo tomado mientras se escribe.
         */
        post: operations["editar_api_novelas__nombre__ediciones_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/ejemplos": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Ejemplos
         * @description Los briefs de `ejemplos/`, ya leídos, para partir de uno en el encargo.
         */
        get: operations["ejemplos_api_ejemplos_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/novelas/{nombre}/cambios": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Pedir Cambio
         * @description Recibe la petición, propone candidatos y deja el gate abierto.
         *
         *     Rechaza si la novela está ocupada: una petición que llegara mientras corre una
         *     invocación escribiría sobre el mismo checkpoint, y eso es lo que el cerrojo existe para
         *     impedir.
         */
        post: operations["pedir_cambio_api_novelas__nombre__cambios_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/salud": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Salud
         * @description Lo mínimo para saber que el servidor está en pie. No abre ninguna novela.
         */
        get: operations["salud_salud_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** AcuseDeCambio */
        AcuseDeCambio: {
            /** Peticion */
            peticion: string;
            /** Gate Abierto */
            gate_abierto: number;
            /** Candidatos */
            candidatos: components["schemas"]["CandidatoDeCambio"][];
            /** Nota */
            nota: string;
        };
        /** Anclaje */
        Anclaje: {
            /** Tipo Vinculo */
            tipo_vinculo: string;
            /** Descripcion */
            descripcion: string;
        };
        /** Arco */
        Arco: {
            /** Tipo */
            tipo: string;
            /** Estado Inicial */
            estado_inicial?: string | null;
            /** Estado Final */
            estado_final?: string | null;
            /** Hitos */
            hitos: components["schemas"]["Hito"][];
        };
        /** AvisoDeLaTrama */
        AvisoDeLaTrama: {
            /** Validador */
            validador: string;
            /** Grave */
            grave: boolean;
            /** Mensaje */
            mensaje: string;
            /** Ubicacion */
            ubicacion?: string | null;
        };
        /** Beat */
        Beat: {
            /** Orden */
            orden: number;
            /** Accion */
            accion: string;
            /** Cambio De Valor */
            cambio_de_valor?: string | null;
        };
        /**
         * Candidato
         * @description Una fila que la búsqueda propuso. Aprobar el gate eligiéndola envía
         *     `<objeto>:<fila_id> <campo>=<valor>` (spec §4.6).
         *
         *     `objeto` y `fila_id` faltan solo en peticiones registradas antes de guardarlos: esas no
         *     se pueden elegir.
         */
        Candidato: {
            /** Objeto */
            objeto?: ("hecho" | "personaje" | "escenario" | "glosario") | null;
            /** Fila Id */
            fila_id?: number | null;
            /** Campo */
            campo?: string | null;
            /** Valor */
            valor: string;
            /** Descripcion */
            descripcion: string;
            /** Capitulos A Regenerar */
            capitulos_a_regenerar: number[];
            /** Capitulos A Revisar */
            capitulos_a_revisar: number[];
            /** Coste */
            coste: string;
        };
        /** CandidatoDeCambio */
        CandidatoDeCambio: {
            /** Objeto */
            objeto: string;
            /** Fila Id */
            fila_id: number;
            /** Descripcion */
            descripcion: string;
            /** Distancia */
            distancia: number;
            /** Capitulos A Regenerar */
            capitulos_a_regenerar: number[];
            /** Capitulos A Revisar */
            capitulos_a_revisar: number[];
            /** Coste */
            coste: string;
        };
        /** CapituloCambiado */
        CapituloCambiado: {
            /** Capitulo */
            capitulo: number;
            /** Estado */
            estado: string;
        };
        /** CapituloDeEscaleta */
        CapituloDeEscaleta: {
            /** Numero */
            numero: number;
            /** Titulo */
            titulo?: string | null;
            /** Funcion */
            funcion?: string | null;
            /** Gancho */
            gancho?: string | null;
            /** Escenas */
            escenas: components["schemas"]["Escena"][];
        };
        /** CapituloDelManifiesto */
        CapituloDelManifiesto: {
            /** Id */
            id: number;
            /** Numero */
            numero: number;
            /** Titulo */
            titulo?: string | null;
            /** Palabras */
            palabras: number;
            /** Resumen */
            resumen?: string | null;
        };
        /** CapituloDelPanel */
        CapituloDelPanel: {
            /** Numero */
            numero: number;
            /** Titulo */
            titulo?: string | null;
            /**
             * Estado
             * @enum {string}
             */
            estado: "pendiente" | "en_curso" | "aprobado" | "invalidado" | "descartado";
            /** Intentos */
            intentos: number;
            /** Palabras */
            palabras?: number | null;
        };
        /** CapituloEscrito */
        CapituloEscrito: {
            /** Numero */
            numero: number;
            /** Titulo */
            titulo?: string | null;
            /** Intentos */
            intentos: components["schemas"]["Intento"][];
        };
        /** Consumo */
        Consumo: {
            /** Tokens In */
            tokens_in: number;
            /** Tokens Out */
            tokens_out: number;
            /** Coste Usd */
            coste_usd: number;
        };
        /**
         * Conversacion
         * @description La entrevista de Intake hasta ahora: lo que se contó, lo que se respondió, lo cerrado.
         */
        Conversacion: {
            /** Descripcion */
            descripcion?: string | null;
            /** Rondas */
            rondas: string[];
            /** Brief */
            brief?: {
                [key: string]: unknown;
            } | null;
        };
        /** Criterio */
        Criterio: {
            /** Criterio */
            criterio: string;
            /** Valor */
            valor: number;
        };
        /**
         * CuerpoDeCambio
         * @description Lo que envía el lector: qué quiere cambiar y desde dónde lo pide.
         *
         *     El fragmento es lo que hace resoluble la petición: «se llama Nala, no Toby» no dice qué
         *     perro, y el pasaje seleccionado sí. Por eso entra en la búsqueda semántica junto al texto.
         */
        CuerpoDeCambio: {
            /** Texto */
            texto: string;
            /**
             * Fragmento
             * @default
             */
            fragmento: string;
            /** Capitulo */
            capitulo?: number | null;
            /** Version */
            version?: number | null;
        };
        /** CuerpoDeDecision */
        CuerpoDeDecision: {
            /** Decision */
            decision: string;
            /**
             * Comentario
             * @default
             */
            comentario: string;
        };
        /** CuerpoDeDescarte */
        CuerpoDeDescarte: {
            /**
             * Motivo
             * @default
             */
            motivo: string;
        };
        /** CuerpoDeEdicion */
        CuerpoDeEdicion: {
            /**
             * Objeto
             * @enum {string}
             */
            objeto: "hecho" | "personaje" | "escenario" | "glosario";
            /** Fila Id */
            fila_id: number;
            /** Campo */
            campo: string;
            /** Valor */
            valor: string;
            /**
             * Motivo
             * @default
             */
            motivo: string;
        };
        /** CuerpoDeEncargo */
        CuerpoDeEncargo: {
            /** Encargo */
            encargo: {
                [key: string]: unknown;
            };
        };
        /** CuerpoDeNovela */
        CuerpoDeNovela: {
            /** Encargo */
            encargo: {
                [key: string]: unknown;
            };
            /**
             * Nombre
             * @default
             */
            nombre: string;
            /**
             * Batch
             * @default false
             */
            batch: boolean;
            /**
             * Investigacion
             * @default estandar
             * @enum {string}
             */
            investigacion: "estandar" | "exhaustiva";
        };
        /** DatoDelEncargo */
        DatoDelEncargo: {
            /** Id */
            id: number;
            /** Tipo */
            tipo: string;
            /** Valor */
            valor: string;
            /** Origen */
            origen: string;
            /** Obligatorio */
            obligatorio: boolean;
        };
        /** Decision */
        Decision: {
            /** Gate Id */
            gate_id: number;
            /** Estado */
            estado: string;
            /** Decision */
            decision?: string | null;
            /** Comentario */
            comentario?: string | null;
            /** Decidido En */
            decidido_en?: string | null;
        };
        /** Diferencias */
        Diferencias: {
            /** Version A */
            version_a: number;
            /** Version B */
            version_b: number;
            /** Cambios */
            cambios: components["schemas"]["CapituloCambiado"][];
            /** Resumen */
            resumen: string;
        };
        /** EdicionHumana */
        EdicionHumana: {
            /** Tabla */
            tabla: string;
            /** Fila Id */
            fila_id: number;
            /** Campo */
            campo: string;
            /** Antes */
            antes?: string | null;
            /** Despues */
            despues?: string | null;
            /** Motivo */
            motivo?: string | null;
        };
        /** Ejecucion */
        Ejecucion: {
            /** Id */
            id: number;
            /** Fase */
            fase: string;
            /** Estado */
            estado: string;
            /** Inicio */
            inicio: string;
            /** Fin */
            fin?: string | null;
            /** Tokens In */
            tokens_in: number;
            /** Tokens Out */
            tokens_out: number;
            /** Coste Usd */
            coste_usd: number;
            /** Modelo */
            modelo?: string | null;
        };
        /** Ejemplo */
        Ejemplo: {
            /** Nombre */
            nombre: string;
            /** Encargo */
            encargo: {
                [key: string]: unknown;
            };
        };
        /** Entidad */
        Entidad: {
            /** Tipo */
            tipo: string;
            /** Nombre */
            nombre: string;
            /** Nombre Epoca */
            nombre_epoca?: string | null;
            /** Fecha Inicio */
            fecha_inicio?: string | null;
            /** Fecha Fin */
            fecha_fin?: string | null;
        };
        /** ErrorDeCampo */
        ErrorDeCampo: {
            /** Campo */
            campo: string;
            /** Mensaje */
            mensaje: string;
        };
        /** Escena */
        Escena: {
            /** Orden */
            orden: number;
            /** Escenario */
            escenario?: string | null;
            /** Fecha Narrativa */
            fecha_narrativa?: string | null;
            /** Punto De Vista */
            punto_de_vista?: string | null;
            /** Objetivo */
            objetivo?: string | null;
            /** Conflicto */
            conflicto?: string | null;
            /** Resultado */
            resultado?: string | null;
            /** Personajes */
            personajes: string[];
            /** Beats */
            beats: components["schemas"]["Beat"][];
            /** Anclajes */
            anclajes: components["schemas"]["Anclaje"][];
        };
        /** Escenario */
        Escenario: {
            /** Id */
            id: number;
            /** Nombre */
            nombre: string;
            /** Lugar */
            lugar?: string | null;
            /** Nombre Epoca */
            nombre_epoca?: string | null;
            /** Descripcion */
            descripcion?: string | null;
        };
        /** FaseDelPanel */
        FaseDelPanel: {
            /** Fase */
            fase: string;
            /**
             * Estado
             * @enum {string}
             */
            estado: "pendiente" | "en_curso" | "esperando_gate" | "completada" | "fallida" | "aparcada" | "abortada";
            /** Deducida */
            deducida: boolean;
            /** Tiene Salida */
            tiene_salida: boolean;
            /** Ejecuciones */
            ejecuciones: components["schemas"]["Ejecucion"][];
            /** Tokens In */
            tokens_in: number;
            /** Tokens Out */
            tokens_out: number;
            /** Coste Usd */
            coste_usd: number;
            /** Inicio */
            inicio?: string | null;
            /** Fin */
            fin?: string | null;
        };
        /** FichaConHistorial */
        FichaConHistorial: {
            /** Nombre */
            nombre: string;
            /** Titulo */
            titulo: string;
            /** Fase */
            fase: string;
            /** Versiones */
            versiones: number;
            /** Gate Abierto */
            gate_abierto?: number | null;
            /**
             * Ocupada
             * @default false
             */
            ocupada: boolean;
            /** Historial */
            historial: components["schemas"]["VersionPublicada"][];
        };
        /** FichaEscenario */
        FichaEscenario: {
            /** Id */
            id: number;
            /** Nombre */
            nombre: string;
            /** Lugar */
            lugar?: string | null;
            /** Lugar De Epoca */
            lugar_de_epoca?: string | null;
            /** Descripcion */
            descripcion?: string | null;
            /** Capitulos */
            capitulos: number[];
        };
        /** FichaPersonaje */
        FichaPersonaje: {
            /** Id */
            id: number;
            /** Nombre */
            nombre: string;
            /** Tipo */
            tipo: string;
            /** Estatus */
            estatus: string;
            /** Rasgos */
            rasgos: string[];
            /** Es Homenajeado */
            es_homenajeado: boolean;
            /** Relacion Con Homenajeado */
            relacion_con_homenajeado?: string | null;
            /** Capitulos */
            capitulos: number[];
        };
        /** Fichas */
        Fichas: {
            /** Personajes */
            personajes: components["schemas"]["FichaPersonaje"][];
            /** Escenarios */
            escenarios: components["schemas"]["FichaEscenario"][];
        };
        /** FilaEditable */
        FilaEditable: {
            /**
             * Objeto
             * @enum {string}
             */
            objeto: "hecho" | "personaje" | "escenario" | "glosario";
            /** Fila Id */
            fila_id: number;
            /** Etiqueta */
            etiqueta: string;
            /** Campos */
            campos: {
                [key: string]: string | null;
            };
            /** Editable */
            editable: boolean;
        };
        /** Fuente */
        Fuente: {
            /** Titulo */
            titulo?: string | null;
            /** Url */
            url?: string | null;
            /** Autor */
            autor?: string | null;
            /** Fecha */
            fecha?: string | null;
            /** Fiabilidad */
            fiabilidad?: string | null;
        };
        /** GateDeNovela */
        GateDeNovela: {
            /** Id */
            id: number;
            /** Fase */
            fase: string;
            /** Abierto En */
            abierto_en?: string | null;
            /** Recuentos */
            recuentos: components["schemas"]["Recuento"][];
            /** Preguntas */
            preguntas: string[];
            peticion?: components["schemas"]["PeticionDeRegeneracion"] | null;
            conversacion?: components["schemas"]["Conversacion"] | null;
            /** Editables */
            editables: components["schemas"]["FilaEditable"][];
            /** Corpus Sellado */
            corpus_sellado: boolean;
            /** Decisiones */
            decisiones: string[];
            trama?: components["schemas"]["RevisionDeLaTrama"] | null;
        };
        /** GatePendiente */
        GatePendiente: {
            /** Id */
            id: number;
            /** Fase */
            fase: string;
            /** Abierto En */
            abierto_en?: string | null;
        };
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /** Hecha */
        Hecha: {
            /** Nombre */
            nombre: string;
            /** Mensaje */
            mensaje: string;
        };
        /** Hecho */
        Hecho: {
            /** Id */
            id: number;
            /** Enunciado */
            enunciado: string;
            /** Estado */
            estado: string;
            /** Dimension */
            dimension: string;
            /** Origen */
            origen: string;
            /** Respaldo */
            respaldo: string;
            /** Firmeza */
            firmeza: string;
            /** No Lo Dice La Cita */
            no_lo_dice_la_cita?: string | null;
            /** Cita */
            cita?: string | null;
            /** Motivo Respaldo */
            motivo_respaldo?: string | null;
            /** Fuentes */
            fuentes: components["schemas"]["Fuente"][];
        };
        /** Hito */
        Hito: {
            /** Orden */
            orden: number;
            /** Descripcion */
            descripcion: string;
        };
        /** HuecoDeLaTrama */
        HuecoDeLaTrama: {
            /** Pregunta */
            pregunta: string;
            /** Dimension */
            dimension: string;
            /** Resultado */
            resultado?: string | null;
            /** Enunciado */
            enunciado?: string | null;
            /** Capitulo */
            capitulo?: number | null;
            /** Escena */
            escena?: number | null;
        };
        /** Incidencia */
        Incidencia: {
            /** Validador */
            validador: string;
            /** Severidad */
            severidad: string;
            /** Ubicacion */
            ubicacion?: string | null;
            /** Mensaje */
            mensaje: string;
            /** Propuesta */
            propuesta?: string | null;
        };
        /** IncidenciaReciente */
        IncidenciaReciente: {
            /** Capitulo */
            capitulo?: number | null;
            /** Validador */
            validador: string;
            /** Severidad */
            severidad: string;
            /** Mensaje */
            mensaje: string;
        };
        /** Intento */
        Intento: {
            /** Id */
            id: number;
            /** Intento */
            intento: number;
            /** Estado */
            estado: string;
            /** Palabras */
            palabras: number;
            /** Creado En */
            creado_en: string;
            /** Incidencias */
            incidencias: components["schemas"]["Incidencia"][];
        };
        /** Lanzada */
        Lanzada: {
            /** Nombre */
            nombre: string;
            /** Registro */
            registro: string;
            /** Mensaje */
            mensaje: string;
        };
        /** Licencia */
        Licencia: {
            /** Alteracion */
            alteracion: string;
            /** Justificacion */
            justificacion: string;
        };
        /** LicenciaDelCanon */
        LicenciaDelCanon: {
            /** Alteracion */
            alteracion: string;
            /** Justificacion */
            justificacion: string;
            /** Declarada */
            declarada: boolean;
        };
        /** Manifiesto */
        Manifiesto: {
            /** Brief Hash */
            brief_hash?: string | null;
            /** Sello Corpus Hash */
            sello_corpus_hash?: string | null;
            /** Embeddings */
            embeddings?: string | null;
        };
        /** ManifiestoPublicado */
        ManifiestoPublicado: {
            /** Brief Hash */
            brief_hash: string;
            /** Sello Corpus Hash */
            sello_corpus_hash: string;
            /** Modelos */
            modelos: string;
            /** Embeddings */
            embeddings: string;
            /** Sdk Version */
            sdk_version?: string | null;
            /** Gates Enabled */
            gates_enabled: boolean;
            /** Creado En */
            creado_en: string;
        };
        /** Obra */
        Obra: {
            /** Titulo */
            titulo?: string | null;
            /** Premisa */
            premisa?: string | null;
            /** Tema */
            tema?: string | null;
            /** Genero */
            genero?: string | null;
            /** Voz */
            voz?: string | null;
            /** Estilo */
            estilo?: {
                [key: string]: unknown;
            } | null;
            /** N Capitulos */
            n_capitulos: number;
            /** Palabras Por Capitulo */
            palabras_por_capitulo: number;
        };
        /** Panel */
        Panel: {
            /** Nombre */
            nombre: string;
            /** Titulo */
            titulo: string;
            /** Homenajeado */
            homenajeado?: string | null;
            /** Fase */
            fase: string;
            /**
             * Estado
             * @enum {string}
             */
            estado: "en_marcha" | "arrancando" | "detenida" | "esperando_autor" | "aparcada" | "fallida" | "terminada" | "en_pausa";
            gate?: components["schemas"]["GatePendiente"] | null;
            /** Capitulos Aprobados */
            capitulos_aprobados: number;
            /** Capitulos Total */
            capitulos_total: number;
            /** Coste Usd */
            coste_usd: number;
            /** Versiones */
            versiones: number;
            /** Actualizada */
            actualizada?: string | null;
            /** Fases */
            fases: components["schemas"]["FaseDelPanel"][];
            /** Capitulos */
            capitulos: components["schemas"]["CapituloDelPanel"][];
            /** Actividad */
            actividad: components["schemas"]["Suceso"][];
            /** Incidencias */
            incidencias: components["schemas"]["IncidenciaReciente"][];
            consumo: components["schemas"]["Consumo"];
            proceso: components["schemas"]["Proceso"];
            /** Registros */
            registros: string[];
            /** Versiones Publicadas */
            versiones_publicadas: components["schemas"]["VersionDelPanel"][];
            /** Trabajando En */
            trabajando_en?: string | null;
        };
        /**
         * Paratexto
         * @description Con lo que se arma la portada: título, dedicatoria y nota del autor.
         */
        Paratexto: {
            /** Titulo */
            titulo: string;
            /** Homenajeado */
            homenajeado?: string | null;
            /** Ocasion */
            ocasion?: string | null;
            /** Licencias */
            licencias: components["schemas"]["Licencia"][];
        };
        /** Personaje */
        Personaje: {
            /** Id */
            id: number;
            /** Nombre */
            nombre: string;
            /** Tipo */
            tipo: string;
            /** Rasgos */
            rasgos: string[];
            /** Objetivo */
            objetivo?: string | null;
            /** Miedo */
            miedo?: string | null;
            /** Voz */
            voz?: string | null;
            /** Estatus */
            estatus?: string | null;
            /** Es Homenajeado */
            es_homenajeado: boolean;
            /** Arcos */
            arcos: components["schemas"]["Arco"][];
        };
        /** Peticion */
        Peticion: {
            /** Momento */
            momento: string;
            /** Texto */
            texto: string;
            /** Fragmento */
            fragmento?: string | null;
            /** Capitulo */
            capitulo?: number | null;
        };
        /** PeticionDeRegeneracion */
        PeticionDeRegeneracion: {
            /** Texto */
            texto: string;
            /** Fragmento */
            fragmento?: string | null;
            /** Capitulo */
            capitulo?: number | null;
            /** Version */
            version?: number | null;
            /** Candidatos */
            candidatos: components["schemas"]["Candidato"][];
        };
        /** Proceso */
        Proceso: {
            /** Cerrojo */
            cerrojo: boolean;
            /** Pid */
            pid?: number | null;
            /** Vivo */
            vivo: boolean;
        };
        /** Recuento */
        Recuento: {
            /** Etiqueta */
            etiqueta: string;
            /** Valor */
            valor: number;
        };
        /** Relacion */
        Relacion: {
            /** A */
            a: string;
            /** B */
            b: string;
            /** Tipo */
            tipo: string;
            /** Intensidad */
            intensidad?: number | null;
        };
        /**
         * RevisionDeLaTrama
         * @description Lo que encontró la revisión de la escaleta, para decidir si se rehace.
         */
        RevisionDeLaTrama: {
            /** Avisos */
            avisos: components["schemas"]["AvisoDeLaTrama"][];
            /** Huecos */
            huecos: components["schemas"]["HuecoDeLaTrama"][];
            /** Inventados */
            inventados: number;
            /** Escenas Poco Firmes */
            escenas_poco_firmes: string[];
        };
        /** Rubrica */
        Rubrica: {
            /** Media */
            media: number;
            /** Criterios */
            criterios: components["schemas"]["Criterio"][];
        };
        /** SalidaDeFase */
        SalidaDeFase: {
            /** Fase */
            fase: string;
            /** Ejecuciones */
            ejecuciones: components["schemas"]["Ejecucion"][];
            /** Decisiones */
            decisiones: components["schemas"]["Decision"][];
            encargo?: components["schemas"]["SalidaEncargo"] | null;
            investigacion?: components["schemas"]["SalidaInvestigacion"] | null;
            trama?: components["schemas"]["SalidaTrama"] | null;
            escritura?: components["schemas"]["SalidaEscritura"] | null;
            publicacion?: components["schemas"]["SalidaPublicacion"] | null;
            regeneracion?: components["schemas"]["SalidaRegeneracion"] | null;
        };
        /** SalidaEncargo */
        SalidaEncargo: {
            /** Encargo */
            encargo?: {
                [key: string]: unknown;
            } | null;
            /** Brief */
            brief?: {
                [key: string]: unknown;
            } | null;
            /** Datos */
            datos: components["schemas"]["DatoDelEncargo"][];
            /** Cuarentena */
            cuarentena: components["schemas"]["TextoEnCuarentena"][];
        };
        /** SalidaEscritura */
        SalidaEscritura: {
            /** Capitulos */
            capitulos: components["schemas"]["CapituloEscrito"][];
        };
        /** SalidaInvestigacion */
        SalidaInvestigacion: {
            /** Hechos */
            hechos: components["schemas"]["Hecho"][];
            /** Recuento */
            recuento: {
                [key: string]: number;
            };
            /** Entidades */
            entidades: components["schemas"]["Entidad"][];
            sello?: components["schemas"]["Sello"] | null;
        };
        /** SalidaPublicacion */
        SalidaPublicacion: {
            /** Versiones */
            versiones: components["schemas"]["VersionConManifiesto"][];
            /** Rubricas */
            rubricas: components["schemas"]["Rubrica"][];
        };
        /** SalidaRegeneracion */
        SalidaRegeneracion: {
            /** Peticiones */
            peticiones: components["schemas"]["Peticion"][];
            /** Ediciones */
            ediciones: components["schemas"]["EdicionHumana"][];
        };
        /** SalidaTrama */
        SalidaTrama: {
            obra?: components["schemas"]["Obra"] | null;
            /** Personajes */
            personajes: components["schemas"]["Personaje"][];
            /** Relaciones */
            relaciones: components["schemas"]["Relacion"][];
            /** Escenarios */
            escenarios: components["schemas"]["Escenario"][];
            /** Licencias */
            licencias: components["schemas"]["LicenciaDelCanon"][];
            /** Glosario */
            glosario: components["schemas"]["TerminoGlosario"][];
            /** Escaleta */
            escaleta: components["schemas"]["CapituloDeEscaleta"][];
        };
        /** Sello */
        Sello: {
            /** Hash */
            hash: string;
            /** Calculado En */
            calculado_en: string;
        };
        /** Suceso */
        Suceso: {
            /** Momento */
            momento: string;
            /**
             * Tipo
             * @enum {string}
             */
            tipo: "fase" | "capitulo" | "gate" | "edicion" | "accion" | "peticion";
            /** Texto */
            texto: string;
            /** Detalle */
            detalle?: string | null;
        };
        /** TarjetaNovela */
        TarjetaNovela: {
            /** Nombre */
            nombre: string;
            /** Titulo */
            titulo: string;
            /** Homenajeado */
            homenajeado?: string | null;
            /** Fase */
            fase: string;
            /**
             * Estado
             * @enum {string}
             */
            estado: "en_marcha" | "arrancando" | "detenida" | "esperando_autor" | "aparcada" | "fallida" | "terminada" | "en_pausa";
            gate?: components["schemas"]["GatePendiente"] | null;
            /** Capitulos Aprobados */
            capitulos_aprobados: number;
            /** Capitulos Total */
            capitulos_total: number;
            /** Coste Usd */
            coste_usd: number;
            /** Versiones */
            versiones: number;
            /** Actualizada */
            actualizada?: string | null;
        };
        /** TerminoGlosario */
        TerminoGlosario: {
            /** Termino */
            termino: string;
            /** Significado */
            significado: string;
            /** Registro */
            registro?: string | null;
        };
        /** TextoDeCapitulo */
        TextoDeCapitulo: {
            /** Orden */
            orden: number;
            /** Titulo */
            titulo?: string | null;
            /** Texto */
            texto: string;
            /** Palabras */
            palabras: number;
            /** Total */
            total: number;
        };
        /** TextoDeIntento */
        TextoDeIntento: {
            /** Id */
            id: number;
            /** Capitulo */
            capitulo: number;
            /** Intento */
            intento: number;
            /** Estado */
            estado: string;
            /** Palabras */
            palabras: number;
            /** Texto */
            texto: string;
            /** Incidencias */
            incidencias: components["schemas"]["Incidencia"][];
            /** Tokens De Contexto */
            tokens_de_contexto?: number | null;
        };
        /** TextoEnCuarentena */
        TextoEnCuarentena: {
            /** Texto */
            texto: string;
            /** Recibido En */
            recibido_en: string;
            /** Procesado En */
            procesado_en?: string | null;
        };
        /** Validacion */
        Validacion: {
            /** Valido */
            valido: boolean;
            /** Errores */
            errores: components["schemas"]["ErrorDeCampo"][];
            /** Nombre Sugerido */
            nombre_sugerido?: string | null;
        };
        /** ValidationError */
        ValidationError: {
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
            /** Input */
            input?: unknown;
            /** Context */
            ctx?: Record<string, never>;
        };
        /** VersionConManifiesto */
        VersionConManifiesto: {
            /** Numero */
            numero: number;
            /** Creada En */
            creada_en: string;
            /** Capitulos */
            capitulos: number;
            manifiesto?: components["schemas"]["ManifiestoPublicado"] | null;
        };
        /** VersionDeNovela */
        VersionDeNovela: {
            /** Numero */
            numero: number;
            /** Anterior */
            anterior?: number | null;
            /** Capitulos */
            capitulos: components["schemas"]["CapituloDelManifiesto"][];
            paratexto: components["schemas"]["Paratexto"];
            manifiesto: components["schemas"]["Manifiesto"];
        };
        /** VersionDelPanel */
        VersionDelPanel: {
            /** Numero */
            numero: number;
            /** Creada En */
            creada_en: string;
            /**
             * Pdf
             * @default false
             */
            pdf: boolean;
        };
        /** VersionPublicada */
        VersionPublicada: {
            /** Numero */
            numero: number;
            /** Creada En */
            creada_en: string;
            /** Puntuacion */
            puntuacion?: number | null;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    listar_api_novelas_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TarjetaNovela"][];
                };
            };
        };
    };
    encargar_api_novelas_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CuerpoDeNovela"];
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Lanzada"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    panel_api_novelas__nombre__panel_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                nombre: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Panel"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    gate_api_novelas__nombre__gate_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                nombre: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["GateDeNovela"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    salida_api_novelas__nombre__fases__fase__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                nombre: string;
                fase: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SalidaDeFase"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    intento_api_novelas__nombre__intentos__capitulo_version__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                nombre: string;
                capitulo_version: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TextoDeIntento"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    registro_api_novelas__nombre__registros__registro__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                nombre: string;
                registro: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    ficha_api_novelas__nombre__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                nombre: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FichaConHistorial"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    version_api_novelas__nombre__versiones__numero__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                nombre: string;
                numero: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["VersionDeNovela"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    capitulo_api_novelas__nombre__versiones__numero__capitulos__orden__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                nombre: string;
                numero: number;
                orden: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TextoDeCapitulo"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    personajes_api_novelas__nombre__versiones__numero__personajes_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                nombre: string;
                numero: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Fichas"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    pdf_api_novelas__nombre__versiones__numero__pdf_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                nombre: string;
                numero: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/pdf": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    diferencias_api_novelas__nombre__versiones__a__diff__b__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                nombre: string;
                a: number;
                b: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Diferencias"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    validar_api_encargos_validar_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CuerpoDeEncargo"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Validacion"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    continuar_api_novelas__nombre__continuar_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                nombre: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Lanzada"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    decidir_api_novelas__nombre__decisiones_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                nombre: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CuerpoDeDecision"];
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Lanzada"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    reintentar_api_novelas__nombre__reintentar_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                nombre: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Lanzada"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    desbloquear_api_novelas__nombre__desbloquear_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                nombre: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Hecha"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    descartar_api_novelas__nombre__hechos__hecho_id__descartar_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                nombre: string;
                hecho_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CuerpoDeDescarte"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Hecha"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    editar_api_novelas__nombre__ediciones_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                nombre: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CuerpoDeEdicion"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Hecha"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    ejemplos_api_ejemplos_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Ejemplo"][];
                };
            };
        };
    };
    pedir_cambio_api_novelas__nombre__cambios_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                nombre: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CuerpoDeCambio"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AcuseDeCambio"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    salud_salud_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: string;
                    };
                };
            };
        };
    };
}
