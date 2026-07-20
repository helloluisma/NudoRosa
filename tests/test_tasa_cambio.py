"""
Tests de services/tasa_cambio.py.

La consulta HTTP real al BCV se aísla con mocks de httpx.get (nunca
tocan la red), así que estos tests son deterministas y no dependen de
que bcv.org.ve esté arriba. El HTML de ejemplo replica la estructura
real verificada contra el sitio (div#dolar > strong.strong-tb +
"Fecha Valor:" + span.date-display-single) — ver el docstring de
_extraer_tasa_html en services/tasa_cambio.py.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import Mock, patch

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base
from models import TasaCambio
from services import ErrorNegocio, tasa_cambio

HTML_BCV_VALIDO = """
<div id="dolar" class="col-sm-12 col-xs-12 ">
  <div class="field-content">
    <div class="row recuadrotsmc">
      <div class="col-sm-6 col-xs-6"><span> USD</span></div>
      <div class="col-sm-6 col-xs-6 centrado textp"><strong class="strong-tb">123,45670000</strong></div>
    </div>
  </div>
</div>
<div class="pull-right dinpro center">
Fecha Valor: <span class="date-display-single" property="dc:date" datatype="xsd:dateTime" content="2026-07-21T00:00:00-04:00">Martes, 21 Julio 2026</span>
</div>
"""


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    sesion = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    try:
        yield sesion
    finally:
        sesion.close()


def _respuesta_mock(texto):
    respuesta = Mock(spec=httpx.Response)
    respuesta.text = texto
    respuesta.raise_for_status = Mock()
    return respuesta


class TestExtraerTasaHtml:
    def test_parsea_tasa_y_fecha_del_html_real_del_bcv(self):
        tasa, fecha_vigencia = tasa_cambio._extraer_tasa_html(HTML_BCV_VALIDO)

        assert tasa == Decimal("123.45670000")
        assert fecha_vigencia == date(2026, 7, 21)

    def test_html_sin_bloque_dolar_levanta_error(self):
        with pytest.raises(tasa_cambio.ErrorConsultaBCV):
            tasa_cambio._extraer_tasa_html("<html><body>el bcv cambió su página</body></html>")

    def test_valor_no_numerico_levanta_error(self):
        html = HTML_BCV_VALIDO.replace("123,45670000", "N/D")

        with pytest.raises(tasa_cambio.ErrorConsultaBCV):
            tasa_cambio._extraer_tasa_html(html)

    def test_valor_cero_levanta_error(self):
        html = HTML_BCV_VALIDO.replace("123,45670000", "0,00")

        with pytest.raises(tasa_cambio.ErrorConsultaBCV):
            tasa_cambio._extraer_tasa_html(html)


class TestActualizarTasaAutomatica:
    @patch("services.tasa_cambio.httpx.get")
    def test_actualizacion_exitosa_guarda_nueva_tasa(self, mock_get, db):
        mock_get.return_value = _respuesta_mock(HTML_BCV_VALIDO)

        resultado = tasa_cambio.actualizar_tasa_automatica(db)

        assert resultado["ok"] is True
        assert resultado["tasa"] == pytest.approx(123.4567)
        assert resultado["fecha_vigencia"] == "2026-07-21"
        assert resultado["mensaje"] == "Tasa BCV actualizada correctamente."

        activa = tasa_cambio.obtener_tasa_activa(db)
        assert activa is not None
        assert activa.tasa_bolivares == Decimal("123.45670000")
        assert activa.fuente == "BCV"
        assert activa.actualizada_automaticamente is True
        assert activa.activa is True

    @patch("services.tasa_cambio.httpx.get")
    def test_error_de_conexion_no_modifica_tasa_anterior(self, mock_get, db):
        tasa_cambio._guardar_nueva_tasa(
            db, Decimal("100.00"), date(2026, 7, 1), fuente="BCV", actualizada_automaticamente=True
        )
        mock_get.side_effect = httpx.ConnectError("no se pudo conectar")

        resultado = tasa_cambio.actualizar_tasa_automatica(db)

        assert resultado["ok"] is False
        assert resultado["mensaje"] == "No se pudo consultar el BCV. Se mantiene la tasa anterior."
        assert resultado["tasa"] == 100.0

        activa = tasa_cambio.obtener_tasa_activa(db)
        assert activa.tasa_bolivares == Decimal("100.00")
        assert db.query(TasaCambio).count() == 1

    @patch("services.tasa_cambio.httpx.get")
    def test_timeout_no_modifica_tasa_anterior(self, mock_get, db):
        tasa_cambio._guardar_nueva_tasa(
            db, Decimal("100.00"), date(2026, 7, 1), fuente="BCV", actualizada_automaticamente=True
        )
        mock_get.side_effect = httpx.TimeoutException("tiempo agotado")

        resultado = tasa_cambio.actualizar_tasa_automatica(db)

        assert resultado["ok"] is False
        activa = tasa_cambio.obtener_tasa_activa(db)
        assert activa.tasa_bolivares == Decimal("100.00")

    @patch("services.tasa_cambio.httpx.get")
    def test_respuesta_invalida_no_modifica_tasa_anterior(self, mock_get, db):
        tasa_cambio._guardar_nueva_tasa(
            db, Decimal("100.00"), date(2026, 7, 1), fuente="BCV", actualizada_automaticamente=True
        )
        mock_get.return_value = _respuesta_mock("<html>el bcv cambió su página</html>")

        resultado = tasa_cambio.actualizar_tasa_automatica(db)

        assert resultado["ok"] is False
        assert resultado["mensaje"] == "No se pudo consultar el BCV. Se mantiene la tasa anterior."

        activa = tasa_cambio.obtener_tasa_activa(db)
        assert activa.tasa_bolivares == Decimal("100.00")
        assert db.query(TasaCambio).count() == 1

    @patch("services.tasa_cambio.httpx.get")
    def test_sin_tasa_previa_y_bcv_falla_no_queda_ninguna_tasa_activa(self, mock_get, db):
        # Nunca se guarda un cero ni se inventa un valor de arranque.
        mock_get.side_effect = httpx.ConnectError("no se pudo conectar")

        resultado = tasa_cambio.actualizar_tasa_automatica(db)

        assert resultado["ok"] is False
        assert resultado["tasa"] is None
        assert tasa_cambio.obtener_tasa_activa(db) is None


class TestGuardarTasaManual:
    def test_guarda_tasa_manual_valida(self, db):
        resultado = tasa_cambio.guardar_tasa_manual(db, Decimal("150.75"))

        assert resultado["ok"] is True
        assert resultado["tasa"] == 150.75

        activa = tasa_cambio.obtener_tasa_activa(db)
        assert activa.fuente == "MANUAL"
        assert activa.actualizada_automaticamente is False

    def test_tasa_manual_cero_levanta_error_negocio(self, db):
        with pytest.raises(ErrorNegocio):
            tasa_cambio.guardar_tasa_manual(db, Decimal("0"))

    def test_tasa_manual_negativa_levanta_error_negocio(self, db):
        with pytest.raises(ErrorNegocio):
            tasa_cambio.guardar_tasa_manual(db, Decimal("-10"))

    def test_tasa_manual_desactiva_la_anterior_sin_borrarla(self, db):
        tasa_cambio._guardar_nueva_tasa(
            db, Decimal("100.00"), date(2026, 7, 1), fuente="BCV", actualizada_automaticamente=True
        )

        tasa_cambio.guardar_tasa_manual(db, Decimal("150.75"))

        activas = db.query(TasaCambio).filter(TasaCambio.activa.is_(True)).all()
        assert len(activas) == 1
        assert activas[0].tasa_bolivares == Decimal("150.75")
        assert db.query(TasaCambio).count() == 2


class TestConversionYFormato:
    def test_convertir_usd_a_bolivares(self):
        assert tasa_cambio.convertir_usd_a_bolivares(100, Decimal("50")) == Decimal("5000.00")

    def test_convertir_usd_a_bolivares_sin_tasa_devuelve_none(self):
        assert tasa_cambio.convertir_usd_a_bolivares(100, None) is None

    def test_convertir_redondea_a_dos_decimales(self):
        assert tasa_cambio.convertir_usd_a_bolivares(1, Decimal("33.333")) == Decimal("33.33")

    def test_formatear_usd(self):
        assert tasa_cambio.formatear_usd(150) == "$150,00"
        assert tasa_cambio.formatear_usd(1210) == "$1.210,00"

    def test_formatear_bolivares(self):
        assert tasa_cambio.formatear_bolivares(Decimal("1210.74")) == "Bs. 1.210,74"

    def test_formatear_bolivares_sin_tasa_no_muestra_cero(self):
        assert tasa_cambio.formatear_bolivares(None) == "—"
