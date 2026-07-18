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
- **Modal tipo hoja inferior:** `.modal--sheet` es la variante de `.modal`
  que sube desde abajo (`transform: translateY` + clase `is-open`, ver
  `abrirHojaInferior()` en `app.js` — función compartida, no duplicar ese
  open/close en cada pantalla nueva). Se usa cuando hay muchas opciones o
  un formulario largo (scroll vertical vía `.inventory-sheet-form`). Para
  confirmaciones simples (sí/no) se sigue usando `.modal__dialog` centrado,
  como en `#delete-confirm-modal` / `#delete-product-modal`.
- **Catálogo de productos único:** `data.PRODUCTOS` es la ÚNICA lista de
  productos — Inventario (`/inventario`) y Mis Lazos (`/productos`) leen y
  escriben sobre el mismo registro (stock/costo/precio de un lado, nombre/
  imagen del otro). Nunca crear una segunda lista de productos "solo para
  esta pantalla".
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

- **Stack:** FastAPI (`main.py`) + Jinja2 (`templates/index.html`) +
  CSS/JS estático servidos desde `static/`. Sin build step: el CSS se
  escribe tal cual se sirve.
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
