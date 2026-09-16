"""Etapas del arnes, una por modulo.

Cada modulo aqui es la mitad determinista de una etapa: recibe lo que un
subagente propone, lo valida contra esquema e invariantes, lo versiona, lo
contabiliza y lo persiste. La mitad no determinista -- generar, criticar, juzgar
-- vive en `.claude/agents/`, y no escribe estado.
"""
