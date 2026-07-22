# CLAUDE.md

Esta es la guía principal del proyecto **Nudo Rosa**. Debe leerse **siempre**, por
completo, antes de modificar cualquier archivo. Las reglas de aquí tienen
prioridad sobre cualquier suposición genérica: si algo en el código parece
contradecir esta guía, la guía manda — y si hace falta romperla, se pregunta
antes, no se decide en silencio.

---

# Identidad del proyecto

- **Nombre:** Nudo Rosa by Ivanna
- **Objetivo:** app de gestión para un negocio artesanal de lazos/accesorios
  (Nudo Rosa). Centraliza ventas, clientas, inventario de diseños y cobros en
  un panel único, con un resumen diario y una tarjeta de progreso a modo de
  gamificación.
- **Público objetivo:** Ivanna y su equipo, usando la app principalmente
  **desde el celular**, en el día a día del negocio (no es una herramienta de
  escritorio ni un sitio de marketing).

---

# Filosofía

- **Mobile First:** todo se diseña primero para pantalla de celular. Nada se
  diseña "para escritorio" y se adapta después — es al revés.
- **PWA / app, no página web:** la interfaz debe sentirse como una app nativa
  de iOS/Android (barra inferior fija, tarjetas, transiciones táctiles), no
  como un sitio con scroll infinito de contenido.
- **Código limpio:** cualquier desarrollador debe poder leer el CSS o el HTML
  y entender qué hace cada bloque sin tener que adivinar.
- **CSS mantenible:** una sola fuente de verdad por valor (color, espaciado,
  radio, tamaño). Si un número se repite tres veces, es una variable.

---

# Diseño

La identidad visual de Nudo Rosa **ya está definida y no se toca sin
autorización explícita del usuario**:

- **No cambiar colores.** Toda la paleta vive en `:root` dentro de
  `static/css/styles.css` (`--vino`, `--rosa-fuerte`, `--rosa`,
  `--rosa-claro`, `--rosa-palido`, `--crema`, `--blanco`, `--texto-suave`,
  `--amarillo`, `--fondo-app`). Un color nuevo se agrega como variable nueva,
  nunca como valor hexadecimal suelto en una regla.
- **No cambiar la tipografía.** La fuente es `Nunito` (variable, pesos
  200–900), cargada desde Google Fonts en `templates/index.html` y expuesta
  como `--font-principal`.
- **No cambiar ilustraciones.** Los PNG/SVG en `static/images/` son arte de
  marca. No se reemplazan, recortan ni regeneran sin que el usuario lo pida.
- **No cambiar iconografía.** Mismo criterio que las ilustraciones — íconos
  de `static/images/` (carrito, caja, dinero, etc.) se mantienen tal cual.
- **Iconos de campos de formulario:** los inputs (nombre, teléfono, fecha,
  dirección, email, etc.) usan íconos de línea fina inline (`<svg>` con
  `stroke="currentColor"`, sin relleno, clase `.field-icon`), color
  `var(--rosa)`, ~19px. No son parte de la iconografía de marca — es un
  patrón propio del formulario, ya usado en `cliente_nueva.html`. Reutilizar
  ese mismo estilo de ícono para cualquier campo nuevo, en vez de emojis o
  íconos dentro de un círculo de color.
- Cualquier ajuste "de diseño" que sí esté permitido (tamaños, espaciados,
  layout) debe verse como una evolución del mismo sistema visual, no como un
  rediseño.
- **Excepción deliberada — íconos de servicios de terceros:** el botón de
  recordatorio de WhatsApp en Cobros (`.cobro-whatsapp-btn`) usa el verde de
  marca de WhatsApp (`#25d366`), no la paleta de Nudo Rosa. Es intencional:
  un ícono de WhatsApp en rosa dejaría de reconocerse como "abre WhatsApp".
  Esta excepción aplica solo a íconos de apps externas reconocibles, no es
  una puerta para meter colores nuevos en componentes propios de la app.

---

# Layout

- La aplicación **siempre se adapta al ancho disponible**. No existe una
  versión "de escritorio" separada: hay un único layout fluido.
- **No usar anchos fijos** (`width: 390px`, `max-width: 430px`, etc.) en
  contenedores estructurales. Usar `width: 100%` y reservar `max-width`
  solo para evitar que algo crezca de forma absurda en monitores muy anchos
  (hoy ese techo es `--app-max-width: 1024px`, compartido por `.app` y
  `.bottom-nav` — nunca se define ese número dos veces).
- Aprovechar el espacio disponible: si hay lugar para que un grid gane
  columnas o una tarjeta crezca, debe crecer (`repeat(auto-fit,
  minmax(...))` antes que breakpoints manuales).
- Evitar espacios vacíos innecesarios: antes de simplemente estirar un
  elemento para llenar espacio, evaluar si un reflow (por ejemplo, pasar de
  apilado a lado a lado) aprovecha mejor el ancho.
- Breakpoints (`@media`) son la excepción, no la regla. Antes de agregar
  uno, preguntar si `clamp()`, `min()`, `auto-fit` o variables resuelven el
  problema sin él. Hoy el proyecto tiene **un solo breakpoint real**
  (`min-width: 768px`, para reordenar progreso/resumen lado a lado).

---

# CSS

Todo vive en `static/css/styles.css`, organizado en **11 secciones
numeradas y comentadas** (Variables, Reset, Layout general, Header, Tarjeta
de bienvenida, Menú principal, Tarjeta de progreso, Resumen del día, Barra
inferior, Utilidades, Responsive). Un cambio nuevo va en la sección que le
corresponde por tema, no al final del archivo.

Reglas:

- **No duplicar reglas ni selectores.** Si `.menu-card` ya está definido más
  arriba, no se vuelve a abrir `.menu-card { }` en otro lugar del archivo.
  Antes de escribir una regla, buscar (`grep`) si el selector ya existe.
- **Eliminar código muerto.** Selectores que no coinciden con nada del HTML
  actual, clases sin usar, comentarios de una edición anterior ("antes
  era...", "ELIMINAR ESTA LÍNEA") — se borran, no se dejan comentados.
- **Eliminar propiedades innecesarias.** No repetir `box-sizing: border-box`
  en un componente cuando ya está en el reset global (`*`). No fijar un
  `object-fit` o `overflow` que el elemento nunca necesitó.
- **Estructura consistente:** mismo orden de propiedades dentro de una regla
  (posicionamiento → tamaño → espaciado → borde/fondo → tipografía → efectos)
  y mismo estilo de comentario de sección (`/* ===... */`) en todo el
  archivo.
- **Usar variables siempre que sea posible:**
  - Espaciado fijo (cosas que no deben crecer, como el tamaño de un badge):
    `--space-1` a `--space-8` (4/8/12/16/20/24/32px).
  - Espaciado estructural (paddings/gaps de contenedores, tarjetas, grid):
    `--space-2-fl` a `--space-8-fl` — se quedan igual en todo el rango de
    teléfono y crecen solos después, sin breakpoints. Ver el comentario en
    `:root` para el patrón (`N(vw) ≈ mínimo / 4.3`).
  - Radios de borde repetidos: `--radius-s/m/l/xl/xxl`.
  - Antes de escribir un `clamp()` nuevo a mano, revisar si ya existe una
    variable de espaciado que sirva.

**Componentes reutilizables ya resueltos** (revisar antes de crear uno
nuevo parecido):

- **Selector de avatar** (`cliente_nueva.html` + sección "REGISTRAR
  CLIENTA / FORMULARIOS" de `styles.css`): `.avatar-select__grid` muestra
  4 avatares sugeridos + un círculo "Más"; `.avatar-sheet` es la hoja
  inferior (bottom sheet) que lista TODOS los avatares disponibles. La
  lista completa nunca se escribe a mano — `main.py` la arma leyendo
  `static/images/avatar/*.png` con `_listar_avatares()` (los archivos son
  `1.png`…`36.png`, pero la numeración no es correlativa — p. ej. no
  existe `35.png` — por eso siempre se lee del disco, nunca se asume un
  rango). Cualquier pantalla nueva que necesite "elegir una imagen de una
  lista grande" reutiliza este patrón (grid de sugeridos + hoja inferior),
  no un `<select>` ni un modal centrado nuevo. Las 7 clientas de muestra en
  `data.py` ya tienen un avatar real asignado (no `""`) para que el diseño
  se vea acomodado — si se agrega una clienta de prueba nueva, asignarle
  también un avatar en vez de dejarlo vacío.
- **Selector de imagen de producto** (`_nuevo_producto_modal.html` +
  `productos.html`, sección "INVENTARIO" de `styles.css`): mismo patrón que
  el selector de avatar de arriba, pero con la tarjeta cuadrada de
  `.bow-card__image` en vez de un círculo — una foto de lazo no debe
  recortarse como si fuera una cara. `.product-image-select__grid` muestra
  TODAS las imágenes reutilizables de `static/images/producto/`, armadas
  leyendo el disco con `_listar_imagenes_producto_predeterminadas()` en
  `main.py` (nunca a mano), excluyendo los archivos `producto_<id>.<ext>`
  que genera una subida — esos son fotos de un producto puntual, no
  diseños reutilizables. Elegir una imagen del grid guarda la ruta
  directo, sin volver a subir el archivo; subir un archivo nuevo limpia la
  selección del grid y viceversa (`initSelectorImagenProducto()` en
  `app.js`, compartida entre Nuevo y Editar producto — no duplicar esa
  lógica por pantalla).
- **Modal tipo hoja inferior:** `.modal--sheet` es la variante de `.modal`
  que sube desde abajo (`transform: translateY` + clase `is-open`, ver
  `abrirHojaInferior()` en `app.js` — función compartida, no duplicar ese
  open/close en cada pantalla nueva). Se usa cuando hay muchas opciones o
  un formulario largo (scroll vertical vía `.inventory-sheet-form`). Para
  confirmaciones simples (sí/no) se sigue usando `.modal__dialog` centrado,
  como en `#delete-confirm-modal` / `#delete-product-modal`.
- **Catálogo de productos único:** la tabla `productos` (`models.Producto`,
  vía `services/productos.py`) es la ÚNICA fuente de productos —
  Inventario (`/inventario`) y Mis Lazos (`/productos`) leen y escriben
  sobre el mismo registro (stock/costo/precio de un lado, nombre/imagen
  del otro). Nunca crear una segunda lista de productos "solo para esta
  pantalla". `data.py` ya no es la fuente en runtime — solo alimenta
  `seed.py` para cargar datos de muestra la primera vez (ver "Backend y
  persistencia de datos").
- **Tarjeta de producto:** `.bow-card` + `.bow-card__image` (sección 12,
  "CATÁLOGO DE PRODUCTOS") es el componente para "imagen + nombre" de un
  producto. Siempre es un `<button>` (nunca `<a>`: tocarlo abre un modal,
  no navega) — por eso `.bow-card` ya trae su propio reset de apariencia
  nativa. Inventario le agrega la clase `.inventory-card` solo como gancho
  de JS (para diferenciar su handler de tocar del de Mis Lazos), sin CSS
  propia.
- **Modal "Nuevo producto":** vive una sola vez en
  `templates/_nuevo_producto_modal.html` y se incluye con `{% include %}`
  en `inventario.html` y `productos.html` — el "+" de ambos encabezados
  abre exactamente el mismo modal/ruta (`POST /productos/nuevo`). Si se
  agrega una tercera pantalla que cree productos, se reutiliza el mismo
  include, no se copia el HTML.
- **Estados calculados en Python, no en Jinja:** `_estado_producto()` y
  `_estado_cobro()` en `main.py` devuelven ya armado
  `{etiqueta, pill_class, ...}` a partir del stock o la fecha de
  vencimiento. Las plantillas solo pintan `{{ x.estado.pill_class }}` —
  nunca repetir el umbral (`stock <= 5`, "5 días de gracia") con un
  `{% if %}` en el template, porque entonces existen dos fuentes de verdad
  para la misma regla de negocio.
- **Botones de guardar — dos estilos, no confundir:**
  `.client-form__submit` es el botón premium (degradado rosa + lazo
  `lazosencillo.png`), usado por los modales de Inventario/Mis Lazos
  ("Guardar ajuste", "Guardar producto", "Guardar cambios" de producto).
  `.client-form__submit-image` es distinto y es solo para
  `cliente_nueva.html`: envuelve las imágenes de marca
  `guardarclienta.svg` / `guardarcambios.svg`, que ya traen el texto y el
  color dibujados adentro — no ponerles texto ni ícono encima.
- **Confirmar eliminación:** reutilizar `.confirm-modal__yes` (acción
  destructiva) + `.confirm-modal__no` (cancelar), como en
  `#delete-confirm-modal` (clienta) y `#delete-product-modal` (producto).
- **Toast de éxito:** `.toast` / `#producto-toast` + `mostrarToastInventario()`
  en `app.js` es el mensaje flotante reutilizable para confirmar una acción
  sin recargar la página (crear/editar/eliminar producto, ajustar stock).
- **Encabezado de pantallas de listado:** Ventas, Clientas, Inventario, Mis
  Lazos y Cobros usan todos `_flat_header.html` + `.sales-screen`.
  `.sales-screen` **no tiene fondo propio** (se le quitó el degradado que
  tenía): toda la app comparte el único fondo (`--fondo-app` del `body`).
  No volver a agregarle un `background` a `.sales-screen` — eso es
  exactamente el "doble fondo" que se corrigió.
- **Preguntas de "Mis materiales" en el formulario de producto:**
  `templates/_materiales_producto_campos.html` es el único lugar donde
  viven las 5 preguntas (lazos por metro de tela, lazos por barra de
  silicón, cantidad de ganchos, ¿usa hilo?, minutos de elaboración) — se
  incluye con `{% set form_prefix = "..." %}` + `{% include %}` en
  `_nuevo_producto_modal.html` y en el modal de edición de
  `productos.html`, igual que el patrón de `_flat_header.html` para
  armar ids únicos por copia. Reemplazan el campo manual "Costo de
  producción" que existía antes — no se vuelve a agregar un input de
  costo a mano en el formulario de producto (ver "Costo de elaboración
  (Mis materiales)" más abajo).

---

# HTML

Vive en `templates/index.html` (Jinja2, servido por FastAPI en `main.py`).

- **Mantener las clases existentes.** El CSS depende de ellas por nombre
  (`.menu-card`, `.progress-card`, `.bottom-nav__item`, etc.). No renombrar
  una clase para "prolijidad" sin actualizar el CSS a la vez, y no hacerlo
  si no aporta valor real.
- **No romper compatibilidad.** Los bloques `{{ url_for(...) }}` y las
  variables de contexto (`nombre`, `estrellas`, `nivel`) vienen de
  `main.py` — un cambio de nombre ahí exige el cambio correspondiente en el
  handler de FastAPI.
- **Estructura limpia:** cada etiqueta que se abre se cierra donde
  corresponde. Antes de dar por terminado un cambio en el HTML, verificar
  que no queden `<div>` sin cerrar ni etiquetas de cierre sueltas (es un
  error real que ya pasó en este proyecto y rompe el layout de forma
  silenciosa en algunos navegadores).

---

# JavaScript

Vive en `static/js/app.js`.

- **Código modular.** Cada interacción (clicks del menú, futuras
  validaciones, llamadas a la API) en su propia función con un nombre que
  diga qué hace — no todo suelto al nivel superior del archivo.
- **Evitar lógica duplicada.** Si dos handlers hacen casi lo mismo, se
  extrae una función compartida.
- **Funciones pequeñas.** Si una función hace más de una cosa (por ejemplo
  "leer el DOM" + "formatear" + "pintar"), se separa.

---

# Backend y persistencia de datos

- **Capas:** los modelos ORM viven en `models.py`, la configuración de
  conexión en `database.py`, y toda la lógica de negocio (crear, editar,
  listar, calcular) en `services/` — un archivo por dominio
  (`clientas.py`, `productos.py`, `pedidos.py`, `inventario.py`,
  `colores.py`, `resumen.py`, `seguridad.py`). Las rutas de `main.py`
  nunca escriben en el ORM directamente: siempre llaman a la función de
  `services/` correspondiente, que hace `db.add()` + `db.commit()` +
  `db.refresh()`. Antes de agregar una función nueva de negocio, revisar
  si el archivo de `services/` del dominio ya tiene algo parecido.
- **No existe una tabla "ventas" separada:** una venta completada es un
  `Pedido` con `estado_entrega=ENTREGADO` y `estado_pago=PAGADO` (ver
  `services/pedidos.py`). Pedidos, Cobros y Ventas son la misma fila
  vista con distintos filtros — nunca se duplica el dato en otra tabla.
- **Motor de base de datos — SQLite en local, PostgreSQL en producción,
  automático:** `database.py` lee `DATABASE_URL` del entorno. Si existe
  (Render la entrega al conectar una base PostgreSQL), se usa esa base,
  normalizando el prefijo viejo `postgres://` a `postgresql://`. Si no
  existe (desarrollo local), cae a un archivo SQLite (`nudorosa.db` en
  la raíz, no versionado). Cambiar de motor entre ambientes es una
  variable de entorno, nunca una rama de código a mano ni un `if`
  agregado fuera de `database.py`.
  - **Por qué:** el filesystem de un servicio web en Render es efímero
    — se reinicia en cada deploy y, en el plan free, cada vez que el
    servicio despierta de una siesta por inactividad. Un archivo SQLite
    guardado ahí se borra en cualquiera de esos reinicios (así se
    perdían productos y clientas después de cerrar sesión). PostgreSQL
    corre en un servicio aparte con disco persistente propio.
  - En Render hace falta configurar `DATABASE_URL` (connection string
    de la base PostgreSQL) y `SECRET_KEY` (ver el punto siguiente) como
    variables de entorno del servicio web.
- **`SECRET_KEY` de sesión:** `main.py` lo lee de la variable de entorno
  `SECRET_KEY`, con un valor aleatorio como respaldo solo para
  desarrollo local. En producción tiene que ser un valor fijo: si
  cambia entre arranques del proceso, todas las cookies de sesión
  firmadas antes quedan inválidas y se fuerza el logout de todo el
  mundo — en Render eso pasaba en cada deploy o siesta del plan free.
- **Migraciones con Alembic, no edición manual del esquema:** cualquier
  cambio a un modelo en `models.py` (columna nueva, tabla nueva, índice)
  necesita una migración
  (`alembic revision --autogenerate -m "..."` seguido de
  `alembic upgrade head`). `_aplicar_migraciones()` en el `lifespan` de
  `main.py` corre `alembic upgrade head` en cada arranque del proceso —
  nunca `Base.metadata.create_all()` (esa llamada solo crea tablas que
  todavía no existen, nunca modifica una tabla existente; así se rompió
  `pedidos.tasa_bcv_aplicada` en producción una vez).
  - **`alembic/env.py` adopta bases preexistentes, con cuidado:** si una
    base ya tiene todas las tablas del esquema inicial pero no existe
    `alembic_version` (por ejemplo, una base creada con `create_all()` de
    antes de que este proyecto usara Alembic), `_bootstrap_baseline_si_hace_falta`
    registra (stamp) la revisión inicial sin ejecutar su DDL, para que
    Alembic corra solo lo que falte hacia head — nunca vuelve a intentar
    crear una tabla que ya existe. Esa función lee la conexión ANTES de
    que Alembic abra su propia transacción; el `try/finally` con
    `connection.commit()` al final no es opcional — sin él, esa lectura
    deja una transacción implícita abierta que absorbe la migración real
    en un SAVEPOINT y la revierte entera al cerrar la conexión (pasó en
    producción: el log decía "Migración completada" y no quedaba nada
    guardado). Si se toca este archivo, no quitar ese commit.
  - **Migraciones por la conexión directa, no la pooled:** si existe
    `DATABASE_URL_UNPOOLED` en el entorno, `env.py` la usa en vez de
    `DATABASE_URL` para migrar — Neon lo documenta así: PgBouncer en modo
    transacción no sostiene bien una migración de varias sentencias
    dependientes entre sí. La app en runtime sigue usando `DATABASE_URL`
    (pooled) sin cambios; esto es solo para Alembic. Si la variable no
    existe, cae a `DATABASE_URL` sin romper nada (SQLite local, o
    cualquier Postgres sin pooler de por medio).
- **Enums como texto:** los `Enum` de `models.py` se guardan con
  `native_enum=False` (columna `VARCHAR`, no el tipo `ENUM` nativo de
  cada motor) — es más portable entre SQLite y PostgreSQL. No cambiar a
  `native_enum=True` sin migrar el esquema en ambos motores.
- **Carga de datos de muestra:** `seed.py` migra los datos de ejemplo de
  `data.py` (los mismos que se usaron para maquetar la UI) hacia la
  base real. Es idempotente — se puede correr varias veces sin duplicar
  nada, cada sección se salta si su tabla ya tiene filas. Se corre a
  mano (`./.venv/Scripts/python.exe seed.py`), nunca automáticamente al
  arrancar la app.
- **Tasa de cambio BCV** (`services/tasa_cambio.py`, `models.TasaCambio`):
  historial completo, nunca se sobreescribe una fila — solo una queda
  `activa=True` por moneda, y `obtener_tasa_activa()` es la única forma de
  leerla. `actualizar_tasa_automatica()` consulta bcv.org.ve en vivo (el
  selector exacto está documentado en el propio archivo — un rediseño del
  sitio del BCV puede romper el parseo); si la consulta falla, NUNCA toca
  la tasa activa ni guarda cero, solo informa el error y mantiene la
  última tasa válida. `convertir_usd_a_bolivares()`, `formatear_usd()` y
  `formatear_bolivares()` son la única fuente de verdad para armar texto
  de moneda (formato venezolano: punto de miles, coma decimal, ej.
  `Bs. 1.210,74`) — `app.js` tiene el mismo formato replicado a propósito
  (`formatoMoneda()` / `formatoBolivares()`, ahí no hay acceso a Python),
  así que cualquier cambio de formato tiene que actualizar los dos lados.
  - **Cuándo se congela la tasa de un pedido:** `Pedido.tasa_bcv_aplicada`
    / `total_bolivares` se escriben al crear el pedido, pero ese valor
    inicial NO es la fuente de verdad mientras sigue pendiente de pago —
    `main.py::_venta_enriquecida` recalcula el equivalente en bolívares
    con la tasa BCV vigente en cada lectura. Recién se congelan de verdad
    al marcar el pedido como pagado
    (`services/pedidos.py::marcar_pago`): ahí se fija la tasa de ESE
    momento y nunca más se toca, sin importar cuánto cambie después la
    tasa BCV — por eso `editar_pedido()` nunca modifica estas dos
    columnas. Una tasa BCV nueva solo puede afectar: precios actuales de
    productos, ventas nuevas, y pedidos todavía pendientes de pago.
- **Costo de elaboración — "Mis materiales"** (`services/materiales.py`,
  `models.Material`): el costo de un lazo (`Producto.costo_produccion`)
  ya no se carga a mano — se calcula solo a partir de 4 materiales fijos
  (tela, silicón, gancho, hilo — siempre esas 4 filas, sembradas una vez
  por `asegurar_materiales_iniciales()` en el `lifespan`, nunca se crean
  ni borran desde la UI) más el % de "pequeños materiales" y el valor de
  la hora de trabajo de `Configuracion`. Todo el cálculo corre en
  **bolívares** (así los compra Ivanna) y recién al final se convierte a
  dólares con la tasa BCV vigente (`materiales.convertir_bolivares_a_usd`,
  inverso de `tasa_cambio.convertir_usd_a_bolivares`) — el dólar sigue
  siendo la fuente de verdad para `precio_publico`/`ganancia_total`.
  - **Rendimiento: por producto o por material, según cuál varía.**
    Cuántos lazos salen de un metro de tela o de una barra de silicón
    depende de CADA producto (`Producto.lazos_por_metro_tela` /
    `lazos_por_barra_silicon`) — cuántos ganchos trae un paquete o
    cuántos lazos rinde un carrete de hilo es una constante del
    material (`Material.rendimiento`, solo en gancho/hilo — ver
    `METADATA_MATERIAL`), no cambia de un producto a otro.
  - **Vivo mientras no se vendió, congelado al vender:** igual patrón
    que la tasa BCV. `Producto.costo_produccion` se recalcula
    (`materiales.recalcular_costo_producto` /
    `recalcular_productos_con_materiales`) cada vez que cambia el
    precio de un material, el % de pequeños materiales, la hora de
    trabajo, la tasa BCV, o se guarda el producto — así que siempre
    refleja el costo actual. Al vender, `services/pedidos.py::crear_pedido`
    copia ese valor a `PedidoItem.costo_unitario`/`costo_subtotal` y
    `Pedido.costo_total`/`ganancia_total`, que ya NO se vuelven a tocar
    (reutiliza el mecanismo de "congelar al pagar" que ya existía para
    la tasa BCV, sin columnas nuevas en `Pedido`).
  - **`minutos_elaboracion IS NOT NULL` es la señal de "este producto usa
    la calculadora".** Un producto creado antes de esta funcionalidad
    (los 5 campos en `NULL`) sigue mostrando su `costo_produccion`
    manual tal cual, sin romperse — nunca se le inventa un valor.
    "Ajustar inventario" (`services/productos.py::ajustar_producto`)
    respeta esto: si el producto ya usa materiales, ignora el costo
    manual del formulario y recalcula en vivo en su lugar.
  - **`Numeric`, no `Integer`, en las columnas de costo/ganancia.** Un
    costo convertido desde bolívares casi siempre cae en centavos —
    guardarlo en un `Integer` (como sigue siendo `precio_publico`, en
    dólares enteros) redondeaba varios lazos a costo $0. Por eso
    `Producto.costo_produccion`, `PedidoItem.costo_unitario`/
    `costo_subtotal`, `Pedido.costo_total`/`ganancia_total` y
    `MovimientoInventario.costo_unitario` son `Numeric`, migrados desde
    `Integer` con `alembic/versions/2222c866c6b8_...py` (usa
    `batch_alter_table` para que también funcione en SQLite, que no
    soporta `ALTER COLUMN TYPE` directo).
    - **Trampa ya encontrada:** `json.dumps`/`JSONResponse` no sabe
      serializar `Decimal` — cualquier valor que salga de estas
      columnas hacia una respuesta JSON (no hacia una plantilla Jinja,
      ahí `formatear_usd`/`formatear_bolivares` ya aceptan `Decimal`)
      tiene que cruzar a `float()` antes (ver `_venta_enriquecida` en
      `main.py`). Olvidarlo tira "Internal Server Error" recién al
      completar una venta de un producto con costo calculado — no al
      crear el producto, porque ahí `_serializar_producto` ya
      convierte todo a `float`.
  - **Dólar arriba, bolívares abajo, siempre** (mismo criterio que el
    resto de la app): el formulario de producto muestra "Lo que costó
    hacerlo" con el dólar como valor principal
    (`formatear_usd`/`.materiales-costo-preview strong`) y el bolívar
    como referencia chica debajo — nunca al revés, aunque el cálculo
    interno sea en bolívares.

---

# Antes de modificar cualquier archivo

1. **Leer este archivo completo.**
2. Analizar el archivo que se va a tocar:
   - ¿Hay código duplicado cerca de lo que voy a cambiar?
   - ¿Hay reglas CSS repetidas para el mismo selector?
   - ¿Ya existe un componente reutilizable que resuelve esto? (revisar las
     11 secciones de `styles.css` y los bloques de `index.html` antes de
     crear uno nuevo — no crear `.card-nueva` si `.menu-card` o
     `.summary-card` ya resuelven el patrón).
   - ¿El cambio es consistente con el resto del diseño (espaciados,
     radios, colores) o introduce un valor suelto?
3. Si el cambio es grande (refactor, nueva sección, cambio de estrategia de
   layout), explicar el plan antes de escribir código.

---

# Al terminar cada tarea

- **Optimizar:** revisar que no haya quedado ningún valor fijo, breakpoint o
  duplicado que se podría haber evitado con una variable existente.
- **Limpiar código:** borrar estilos o marcado que quedaron sin uso durante
  el cambio (versiones anteriores, pruebas, selectores muertos).
- **Revisar consistencia:** el componente nuevo debe verse como parte de la
  misma familia visual (mismos radios, misma escala de espaciado, mismo
  tono de sombra) que el resto de la app.
- **No dejar código temporal:** nada de `console.log` de debug, estilos de
  prueba (`outline: red`), ni archivos sueltos fuera de su lugar.
- **No dejar comentarios innecesarios.** Un comentario solo se justifica
  cuando explica un *porqué* no obvio (una restricción, un bug evitado, una
  fórmula) — nunca para describir lo que el código ya dice por sí solo.
- Verificar visualmente el resultado en al menos un ancho de teléfono
  (~390px) y un ancho grande (~1024px+) antes de dar la tarea por
  terminada.

---

# Referencia rápida

- **Stack:** FastAPI (`main.py`) + SQLAlchemy/Alembic (`database.py`,
  `models.py`, `services/` — ver "Backend y persistencia de datos") +
  Jinja2 (`templates/index.html`) + CSS/JS estático servidos desde
  `static/`. Sin build step: el CSS se escribe tal cual se sirve.
- **Base de datos:** SQLite en local (`nudorosa.db`) o PostgreSQL en
  producción según exista `DATABASE_URL` en el entorno — automático,
  ver "Backend y persistencia de datos". En producción, `DATABASE_URL`
  (pooled) es para la app; `DATABASE_URL_UNPOOLED` (directa, opcional) es
  para que Alembic migre sin pasar por el pooler.
- **Correr en local:** `./.venv/Scripts/python.exe -m uvicorn main:app
  --port 8000`.
- **Ancho de referencia de diseño:** ~390px (celular medio) como base;
  fluido desde 320px hasta el techo de `--app-max-width` (1024px).
- **Errores ya detectados y corregidos que no deben repetirse:**
  - `aspect-ratio` fijo en una tarjeta cuyo contenido crece con `clamp()`
    puede desbordar la tarjeta en anchos intermedios — si el contenido
    escala, la altura debe ser automática, no forzada por ratio.
  - Una clase de CSS que asume un elemento contenedor (`.algo img`) no
    hace nada si `.algo` es directamente la etiqueta `<img>` en el HTML.
    Siempre confirmar la estructura real antes de escribir el selector.
