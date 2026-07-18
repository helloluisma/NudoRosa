class ErrorNegocio(Exception):
    """Violación de una regla de negocio (stock insuficiente, estado
    inválido, etc.) — las rutas la traducen a un 422 con el mensaje
    tal cual, nunca a un 500."""
