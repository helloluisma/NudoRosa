/*
 * Abre cualquier `.modal--sheet` con la animación de "subir desde
 * abajo". El cierre lo maneja initModalDismiss (backdrop, Escape o
 * [data-modal-close]), que ya es genérico para todos los .modal.
 */
function abrirHojaInferior(modal) {
    modal.hidden = false;
    modal.classList.remove("is-open");
    void modal.offsetWidth;
    requestAnimationFrame(() => modal.classList.add("is-open"));
}

/*
 * Menú emergente "Ver más": popover contextual estilo iOS.
 * Cada trigger [data-popover-trigger="x"] controla el panel
 * [data-popover="x"] correspondiente.
 */

function getOpenPopovers() {
    return document.querySelectorAll(".popover.is-open");
}

function closePopover(panel) {
    panel.classList.remove("is-open");
    panel.addEventListener(
        "transitionend",
        () => {
            if (!panel.classList.contains("is-open")) {
                panel.hidden = true;
            }
        },
        { once: true }
    );

    const trigger = document.querySelector(
        `[data-popover-trigger="${panel.dataset.popover}"]`
    );
    trigger?.setAttribute("aria-expanded", "false");

    const backdrop = document.querySelector(`[data-popover-backdrop="${panel.dataset.popover}"]`);
    if (backdrop) {
        backdrop.classList.remove("is-open");
        backdrop.hidden = true;
    }
}

function closeAllPopovers() {
    getOpenPopovers().forEach(closePopover);
}

function openPopover(trigger, panel) {
    panel.hidden = false;

    requestAnimationFrame(() => {
        panel.classList.add("is-open");
    });

    trigger.setAttribute("aria-expanded", "true");

    const backdrop = document.querySelector(`[data-popover-backdrop="${panel.dataset.popover}"]`);
    if (backdrop) {
        backdrop.hidden = false;
        requestAnimationFrame(() => backdrop.classList.add("is-open"));
    }
}

function togglePopover(trigger, panel) {
    const wasOpen = panel.classList.contains("is-open");

    closeAllPopovers();

    if (!wasOpen) {
        openPopover(trigger, panel);
    }
}

function initPopovers() {
    const triggers = document.querySelectorAll("[data-popover-trigger]");

    triggers.forEach((trigger) => {
        const panel = document.querySelector(
            `[data-popover="${trigger.dataset.popoverTrigger}"]`
        );

        if (!panel) return;

        trigger.addEventListener("click", (event) => {
            event.stopPropagation();
            togglePopover(trigger, panel);
        });

        panel.addEventListener("click", (event) => event.stopPropagation());
    });

    document.addEventListener("click", closeAllPopovers);

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") closeAllPopovers();
    });
}

document.addEventListener("DOMContentLoaded", initPopovers);


/*
 * Selector de rango de fechas de Ventas: comportamiento tipo
 * Booking/Airbnb. El primer clic define el inicio, el segundo el
 * final; el panel nunca se cierra solo. Solo se cierra con
 * "Ver ventas", "Cancelar", clic afuera o Escape — y al cerrarse
 * sin aplicar, descarta la selección y vuelve al rango vigente.
 */

function parseISODate(value) {
    if (!value) {
        return null;
    }

    const [year, month, day] = value.split("-").map(Number);

    if (!year || !month || !day) {
        return null;
    }

    return new Date(year, month - 1, day);
}

function formatISODate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");

    return `${year}-${month}-${day}`;
}

function normalizeDate(date) {
    return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

function sameDate(firstDate, secondDate) {
    return (
        firstDate &&
        secondDate &&
        firstDate.getFullYear() === secondDate.getFullYear() &&
        firstDate.getMonth() === secondDate.getMonth() &&
        firstDate.getDate() === secondDate.getDate()
    );
}

function isStrictlyBetween(date, start, end) {
    if (!start || !end) {
        return false;
    }

    const time = normalizeDate(date).getTime();
    const startTime = normalizeDate(start).getTime();
    const endTime = normalizeDate(end).getTime();

    return time > startTime && time < endTime;
}

function initDateRangePicker() {
    const trigger = document.querySelector("#open-date-range");
    const panel = document.querySelector("#date-range-panel");

    if (!trigger || !panel) {
        return;
    }

    const daysContainer = document.querySelector("#calendar-days");
    const monthLabel = document.querySelector("#calendar-month-label");
    const previousButton = document.querySelector("#calendar-prev");
    const nextButton = document.querySelector("#calendar-next");
    const cancelButton = document.querySelector("#cancel-date-range");
    const applyButton = document.querySelector("#apply-date-range");
    const startInput = document.querySelector("#fecha-inicio");
    const endInput = document.querySelector("#fecha-fin");
    const startLabel = document.querySelector("#range-start-label");
    const endLabel = document.querySelector("#range-end-label");
    const rangeLabel = document.querySelector("#date-range-label");
    const shortcuts = document.querySelectorAll("[data-range]");

    const monthFormatter = new Intl.DateTimeFormat("es-MX", {
        month: "long",
        year: "numeric",
    });

    const shortDateFormatter = new Intl.DateTimeFormat("es-MX", {
        day: "numeric",
        month: "short",
    });

    const today = normalizeDate(new Date());

    // Rango "vigente": el que representa la URL actual. Cancelar o
    // cerrar el panel sin aplicar siempre vuelve a este estado —
    // nunca se recuerda una selección a medio hacer.
    const committedStart = parseISODate(startInput?.value) || today;
    const committedEnd = parseISODate(endInput?.value) || today;

    let startDate = committedStart;
    let endDate = committedEnd;
    let visibleMonth = new Date(startDate.getFullYear(), startDate.getMonth(), 1);

    function describeRange(start, end) {
        if (!start) {
            return "Seleccionar periodo";
        }

        if (!end) {
            return `${shortDateFormatter.format(start)} — Elegir final`;
        }

        if (sameDate(start, end)) {
            return sameDate(start, today)
                ? `Hoy, ${shortDateFormatter.format(start)}`
                : shortDateFormatter.format(start);
        }

        return `${shortDateFormatter.format(start)} — ${shortDateFormatter.format(end)}`;
    }

    function buildDayButton(date, visibleMonthIndex) {
        const button = document.createElement("button");

        button.type = "button";
        button.className = "calendar-day";
        button.textContent = String(date.getDate());
        button.dataset.date = formatISODate(date);

        if (date.getMonth() !== visibleMonthIndex) {
            button.classList.add("calendar-day--muted");
        }

        if (sameDate(date, today)) {
            button.classList.add("calendar-day--today");
        }

        const isSingleDay = startDate && endDate && sameDate(startDate, endDate);

        if (isSingleDay) {
            if (sameDate(date, startDate)) {
                button.classList.add("calendar-day--single");
            }
        } else {
            if (sameDate(date, startDate)) {
                button.classList.add("calendar-day--range-start");
            }

            if (sameDate(date, endDate)) {
                button.classList.add("calendar-day--range-end");
            }

            if (isStrictlyBetween(date, startDate, endDate)) {
                button.classList.add("calendar-day--range");
            }
        }

        button.addEventListener("click", (event) => {
            event.stopPropagation();
            selectDate(date);
        });

        return button;
    }

    function renderCalendar() {
        daysContainer.innerHTML = "";
        monthLabel.textContent = monthFormatter.format(visibleMonth);

        const year = visibleMonth.getFullYear();
        const month = visibleMonth.getMonth();
        const firstDay = new Date(year, month, 1);
        const mondayOffset = (firstDay.getDay() + 6) % 7;
        const firstVisibleDate = new Date(year, month, 1 - mondayOffset);

        for (let index = 0; index < 42; index += 1) {
            const date = new Date(firstVisibleDate);
            date.setDate(firstVisibleDate.getDate() + index);

            daysContainer.appendChild(buildDayButton(date, month));
        }

        updateSelectionSummary();
    }

    function selectDate(date) {
        const selected = normalizeDate(date);

        // Sin inicio, o con un rango ya completo: este clic
        // arranca una selección nueva.
        if (!startDate || endDate) {
            startDate = selected;
            endDate = null;
        } else if (selected < startDate) {
            endDate = startDate;
            startDate = selected;
        } else {
            endDate = selected;
        }

        renderCalendar();
    }

    function updateSelectionSummary() {
        startLabel.textContent = startDate ? shortDateFormatter.format(startDate) : "Sin elegir";
        endLabel.textContent = endDate ? shortDateFormatter.format(endDate) : "Sin elegir";

        if (startInput) {
            startInput.value = startDate ? formatISODate(startDate) : "";
        }

        if (endInput) {
            endInput.value = endDate ? formatISODate(endDate) : "";
        }

        applyButton.disabled = !(startDate && endDate);
        rangeLabel.textContent = describeRange(startDate, endDate);
    }

    function setShortcutRange(type) {
        if (type === "today") {
            startDate = today;
            endDate = today;
        }

        if (type === "week") {
            const weekday = (today.getDay() + 6) % 7;

            startDate = new Date(today);
            startDate.setDate(today.getDate() - weekday);

            endDate = new Date(startDate);
            endDate.setDate(startDate.getDate() + 6);
        }

        if (type === "month") {
            startDate = new Date(today.getFullYear(), today.getMonth(), 1);
            endDate = new Date(today.getFullYear(), today.getMonth() + 1, 0);
        }

        visibleMonth = new Date(startDate.getFullYear(), startDate.getMonth(), 1);
        renderCalendar();
    }

    function openPanel() {
        panel.hidden = false;
        trigger.setAttribute("aria-expanded", "true");
    }

    function closePanel() {
        panel.hidden = true;
        trigger.setAttribute("aria-expanded", "false");

        // Cerrar sin aplicar descarta la edición en curso.
        startDate = committedStart;
        endDate = committedEnd;
        visibleMonth = new Date(startDate.getFullYear(), startDate.getMonth(), 1);
        renderCalendar();
    }

    function togglePanel() {
        if (panel.hidden) {
            openPanel();
        } else {
            closePanel();
        }
    }

    trigger.addEventListener("click", (event) => {
        event.stopPropagation();
        togglePanel();
    });

    previousButton.addEventListener("click", () => {
        visibleMonth.setMonth(visibleMonth.getMonth() - 1);
        renderCalendar();
    });

    nextButton.addEventListener("click", () => {
        visibleMonth.setMonth(visibleMonth.getMonth() + 1);
        renderCalendar();
    });

    shortcuts.forEach((button) => {
        button.addEventListener("click", () => setShortcutRange(button.dataset.range));
    });

    cancelButton.addEventListener("click", closePanel);

    document.addEventListener("click", (event) => {
        if (panel.hidden) {
            return;
        }

        if (panel.contains(event.target) || trigger.contains(event.target)) {
            return;
        }

        closePanel();
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !panel.hidden) {
            closePanel();
        }
    });

    window.addEventListener("pageshow", (event) => {
        // Si el navegador recupera esta pantalla con el botón
        // Atrás (bfcache) mostrando un rango aplicado, se descarta
        // y vuelve a /ventas con el día actual.
        const search = window.location.search;

        if (event.persisted && (search.includes("fecha_inicio=") || search.includes("fecha_fin="))) {
            window.location.replace("/ventas");
        }
    });

    renderCalendar();
}

document.addEventListener("DOMContentLoaded", initDateRangePicker);

/*
 * Buscador de lista en el cliente: filtra por texto (sin ir al
 * servidor). Se usa en "Todas las ventas" y en "Clientas".
 */
function initListSearch(inputSelector, listSelector, itemSelector, emptySelector) {
    const input = document.querySelector(inputSelector);
    const list = document.querySelector(listSelector);
    const emptyMessage = document.querySelector(emptySelector);

    if (!input || !list) {
        return;
    }

    const items = Array.from(list.querySelectorAll(itemSelector));

    input.addEventListener("input", () => {
        const query = input.value.trim().toLowerCase();
        let visibleCount = 0;

        items.forEach((item) => {
            const matches = item.textContent.toLowerCase().includes(query);

            item.hidden = !matches;

            if (matches) {
                visibleCount += 1;
            }
        });

        if (emptyMessage) {
            emptyMessage.hidden = visibleCount > 0;
        }
    });
}

function initSearchFilters() {
    initListSearch("#sales-search-input", "#all-sales-list", ".latest-sale", "#sales-search-empty");
    initListSearch("#client-search-input", "#client-list", ".client-row", "#client-search-empty");
}

document.addEventListener("DOMContentLoaded", initSearchFilters);

/*
 * Cierre genérico de cualquier .modal de la página: fondo, botón
 * [data-modal-close] o Escape. Un solo modal vive por pantalla, así
 * que no hace falta rastrear cuál está abierto.
 */
function initModalDismiss() {
    const modals = document.querySelectorAll(".modal");

    if (!modals.length) {
        return;
    }

    modals.forEach((modal) => {
        modal.querySelectorAll("[data-modal-close]").forEach((el) => {
            el.addEventListener("click", () => {
                modal.hidden = true;
            });
        });
    });

    document.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") {
            return;
        }

        modals.forEach((modal) => {
            modal.hidden = true;
        });
    });
}

document.addEventListener("DOMContentLoaded", initModalDismiss);

/*
 * Confirmación de eliminar clienta: "Sí" es un form real que
 * navega a la ruta de borrado; el cierre lo maneja initModalDismiss.
 */
function initDeleteConfirm() {
    const trigger = document.querySelector("#delete-client-button");
    const modal = document.querySelector("#delete-confirm-modal");

    if (!trigger || !modal) {
        return;
    }

    trigger.addEventListener("click", () => {
        modal.hidden = false;
    });
}

document.addEventListener("DOMContentLoaded", initDeleteConfirm);

/*
 * Historial de compras del perfil de clienta: solo se muestran las
 * primeras 3 tarjetas; "Ver todas" revela el resto sin recargar
 * la página (no hay una ruta de historial completo por clienta).
 */
function initPurchaseToggle() {
    const button = document.querySelector("#toggle-purchases");
    const extraItems = document.querySelectorAll(".purchase-card[data-extra]");

    if (!button || !extraItems.length) {
        return;
    }

    button.addEventListener("click", () => {
        const expand = button.dataset.expanded !== "true";

        extraItems.forEach((item) => {
            item.hidden = !expand;
        });

        button.dataset.expanded = expand ? "true" : "false";
        button.textContent = expand ? "Ver menos" : "Ver todas";
    });
}

document.addEventListener("DOMContentLoaded", initPurchaseToggle);

/*
 * Selector de avatar del formulario de clienta: 4 avatares
 * sugeridos + un círculo "Más" que abre una hoja inferior con
 * todos los avatares disponibles. Elegir cualquiera actualiza el
 * campo oculto que se envía con el formulario.
 */
function initAvatarSelector() {
    const suggestedItems = document.querySelectorAll(
        "#avatar-select-grid .avatar-select__item:not(.avatar-select__item--more)"
    );
    const moreItem = document.querySelector("#avatar-select-more");
    const moreImg = document.querySelector("#avatar-select-more-img");
    const morePlus = document.querySelector("#avatar-select-plus");
    const input = document.querySelector("#avatar-input");
    const modal = document.querySelector("#avatar-picker-modal");

    if (!moreItem || !input || !modal) {
        return;
    }

    function clearSelection() {
        suggestedItems.forEach((item) => item.classList.remove("is-selected"));
        moreItem.classList.remove("is-selected");
        modal.querySelectorAll(".avatar-sheet__option").forEach((option) => {
            option.classList.remove("is-selected");
        });
    }

    function markSheetOption(url) {
        const option = modal.querySelector(
            `.avatar-sheet__option[data-avatar-url="${url}"]`
        );
        option?.classList.add("is-selected");
    }

    function selectSuggested(item) {
        clearSelection();
        item.classList.add("is-selected");
        input.value = item.dataset.avatarUrl;
        moreImg.hidden = true;
        morePlus.hidden = false;
        markSheetOption(item.dataset.avatarUrl);
    }

    function selectCustom(url) {
        clearSelection();
        moreImg.src = url;
        moreImg.hidden = false;
        morePlus.hidden = true;
        moreItem.classList.add("is-selected");
        input.value = url;
        markSheetOption(url);
    }

    function openModal() {
        abrirHojaInferior(modal);
    }

    suggestedItems.forEach((item) => {
        item.addEventListener("click", () => selectSuggested(item));
    });

    moreItem.addEventListener("click", openModal);

    modal.querySelectorAll(".avatar-sheet__option").forEach((option) => {
        option.addEventListener("click", () => {
            const url = option.dataset.avatarUrl;
            const matchingItem = Array.from(suggestedItems).find(
                (item) => item.dataset.avatarUrl === url
            );

            if (matchingItem) {
                selectSuggested(matchingItem);
            } else {
                selectCustom(url);
            }

            modal.hidden = true;
        });
    });
}

document.addEventListener("DOMContentLoaded", initAvatarSelector);

/*
 * Inventario: cuadrícula de productos con ajuste de stock y alta
 * de producto nuevo, ambos como hojas inferiores que no recargan
 * la página (usan fetch() contra las rutas de main.py y actualizan
 * el DOM con la respuesta).
 */

const ICONO_CAMARA_INVENTARIO = `
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="color: var(--rosa);">
        <path d="M4 8.5A1.5 1.5 0 0 1 5.5 7h2l1-2h7l1 2h2A1.5 1.5 0 0 1 20 8.5v9A1.5 1.5 0 0 1 18.5 19h-13A1.5 1.5 0 0 1 4 17.5Z"></path>
        <circle cx="12" cy="12.5" r="3.4"></circle>
    </svg>
`;

/*
 * Helpers genéricos para cualquier acción sin recarga de página
 * (Inventario, Mis Lazos y Pedidos comparten estos dos): enviar un
 * formulario por fetch y mostrar el toast de éxito/error de la
 * página (cada pantalla trae su propio <div class="toast">, con
 * cualquier id — se busca por clase, no hace falta coordinar ids).
 */
async function enviarFormulario(url, formData) {
    const response = await fetch(url, { method: "POST", body: formData });
    const datos = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(datos.error || "Ocurrió un error. Intenta de nuevo.");
    }

    return datos;
}

let toastTimeoutId = null;

function mostrarToast(mensaje) {
    const toast = document.querySelector(".toast");

    if (!toast) {
        return;
    }

    clearTimeout(toastTimeoutId);
    toast.textContent = mensaje;
    toast.hidden = false;

    requestAnimationFrame(() => toast.classList.add("is-visible"));

    toastTimeoutId = setTimeout(() => {
        toast.classList.remove("is-visible");
        setTimeout(() => {
            toast.hidden = true;
        }, 220);
    }, 2200);
}

function actualizarTarjetaProducto(producto, estado) {
    const tarjeta = document.querySelector(`#inventory-card-${producto.id}`);

    if (!tarjeta) {
        return;
    }

    tarjeta.dataset.stock = producto.stock;
    tarjeta.dataset.costo = producto.costo_produccion;
    tarjeta.dataset.precio = producto.precio_publico;

    const stockText = tarjeta.querySelector('[data-role="stock-text"]');
    const pill = tarjeta.querySelector('[data-role="estado-pill"]');

    if (stockText) {
        stockText.textContent = `Stock: ${producto.stock}`;
    }

    if (pill) {
        pill.className = `pill ${estado.pill_class}`;
        pill.textContent = estado.etiqueta;
    }
}

/*
 * El "+" de Inventario y el de Mis Lazos crean el mismo producto
 * (misma ruta, mismo modal). Cada pantalla solo tiene UNA de las
 * dos cuadrículas en el DOM, así que se arma la tarjeta que
 * corresponda según cuál esté presente.
 */
function crearTarjetaProducto(producto, estado) {
    const inventoryGrid = document.querySelector("#inventory-grid");
    const bowsGrid = document.querySelector("#bows-grid");

    if (inventoryGrid) {
        crearTarjetaInventario(inventoryGrid, producto, estado);
    }

    if (bowsGrid) {
        crearTarjetaBowCard(bowsGrid, producto);
    }
}

function crearTarjetaInventario(grid, producto, estado) {
    const tarjeta = document.createElement("button");

    tarjeta.type = "button";
    tarjeta.className = "bow-card inventory-card";
    tarjeta.id = `inventory-card-${producto.id}`;
    tarjeta.dataset.productId = producto.id;
    tarjeta.dataset.nombre = producto.nombre;
    tarjeta.dataset.imagen = producto.imagen || "";
    tarjeta.dataset.stock = producto.stock;
    tarjeta.dataset.costo = producto.costo_produccion;
    tarjeta.dataset.precio = producto.precio_publico;

    tarjeta.innerHTML = `
        <div class="bow-card__image">
            ${producto.imagen ? `<img src="${producto.imagen}" alt="">` : `<span aria-hidden="true">🎀</span>`}
        </div>
        <strong></strong>
        <span class="inventory-card__meta">
            <span class="inventory-card__stock" data-role="stock-text">Stock: ${producto.stock}</span>
            <span class="pill ${estado.pill_class}" data-role="estado-pill">${estado.etiqueta}</span>
        </span>
    `;

    tarjeta.querySelector("strong").textContent = producto.nombre;

    grid.appendChild(tarjeta);
    initInventoryCard(tarjeta);
}

function crearTarjetaBowCard(grid, producto) {
    const tarjeta = document.createElement("button");

    tarjeta.type = "button";
    tarjeta.className = "bow-card";
    tarjeta.id = `bow-card-${producto.id}`;
    tarjeta.dataset.name = producto.nombre.toLowerCase();
    tarjeta.dataset.productId = producto.id;
    tarjeta.dataset.nombre = producto.nombre;
    tarjeta.dataset.imagen = producto.imagen || "";
    tarjeta.dataset.costo = producto.costo_produccion;
    tarjeta.dataset.precio = producto.precio_publico;
    tarjeta.dataset.stock = producto.stock;

    tarjeta.innerHTML = `
        <div class="bow-card__image">
            ${producto.imagen ? `<img src="${producto.imagen}" alt="">` : `<span aria-hidden="true">🎀</span>`}
        </div>
        <strong></strong>
    `;

    tarjeta.querySelector("strong").textContent = producto.nombre;

    grid.appendChild(tarjeta);
    initBowCard(tarjeta);
}

function abrirModalAjuste(tarjeta) {
    const modal = document.querySelector("#inventory-adjust-modal");

    if (!modal) {
        return;
    }

    const stock = Number(tarjeta.dataset.stock);
    const imagen = tarjeta.dataset.imagen;
    const productImage = document.querySelector("#adjust-product-image");
    const preview = document.querySelector("#adjust-preview");
    const error = document.querySelector("#adjust-error");

    document.querySelector("#adjust-product-id").value = tarjeta.dataset.productId;
    document.querySelector("#adjust-product-name").textContent = tarjeta.dataset.nombre;
    document.querySelector("#adjust-product-stock").textContent = `Stock actual: ${stock}`;
    document.querySelector("#adjust-cantidad").value = "";
    document.querySelector("#adjust-costo").value = tarjeta.dataset.costo;
    document.querySelector("#adjust-precio").value = tarjeta.dataset.precio;

    if (productImage) {
        productImage.innerHTML = imagen ? `<img src="${imagen}" alt="">` : ICONO_CAMARA_INVENTARIO;
    }

    preview.hidden = true;
    preview.textContent = "";
    error.hidden = true;
    error.textContent = "";

    modal.dataset.stockActual = String(stock);
    abrirHojaInferior(modal);
}

function initInventoryCard(tarjeta) {
    tarjeta.addEventListener("click", () => abrirModalAjuste(tarjeta));
}

function initInventoryGrid() {
    document.querySelectorAll(".inventory-card").forEach(initInventoryCard);
}

document.addEventListener("DOMContentLoaded", initInventoryGrid);

function initInventoryAdjustForm() {
    const form = document.querySelector("#adjust-form");
    const modal = document.querySelector("#inventory-adjust-modal");
    const cantidadInput = document.querySelector("#adjust-cantidad");
    const preview = document.querySelector("#adjust-preview");
    const error = document.querySelector("#adjust-error");

    if (!form || !modal) {
        return;
    }

    function actualizarVistaPrevia() {
        const cantidad = Number(cantidadInput.value);
        const stockActual = Number(modal.dataset.stockActual || 0);

        if (cantidadInput.value === "" || Number.isNaN(cantidad) || cantidad < 0) {
            preview.hidden = true;
            return;
        }

        preview.textContent = `Nuevo stock: ${stockActual + cantidad}`;
        preview.hidden = false;
    }

    cantidadInput.addEventListener("input", actualizarVistaPrevia);

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        error.hidden = true;

        const productoId = document.querySelector("#adjust-product-id").value;
        const formData = new FormData(form);

        try {
            const datos = await enviarFormulario(`/productos/${productoId}/ajustar`, formData);

            actualizarTarjetaProducto(datos.producto, datos.estado);
            modal.hidden = true;
            mostrarToast("Inventario actualizado ✓");
        } catch (err) {
            error.textContent = err.message;
            error.hidden = false;
        }
    });
}

document.addEventListener("DOMContentLoaded", initInventoryAdjustForm);

function initNewProductButton() {
    const modal = document.querySelector("#new-product-modal");
    const triggers = document.querySelectorAll("#new-product-button, #bows-empty-add");

    if (!modal || !triggers.length) {
        return;
    }

    triggers.forEach((trigger) => {
        trigger.addEventListener("click", () => {
            document.querySelector("#new-product-form").reset();
            document.querySelector("#new-product-preview").innerHTML = ICONO_CAMARA_INVENTARIO;
            document.querySelector("#new-product-error").hidden = true;
            abrirHojaInferior(modal);
        });
    });
}

document.addEventListener("DOMContentLoaded", initNewProductButton);

function initNewProductForm() {
    const form = document.querySelector("#new-product-form");
    const modal = document.querySelector("#new-product-modal");
    const error = document.querySelector("#new-product-error");
    const imagenInput = document.querySelector("#new-product-imagen-input");
    const preview = document.querySelector("#new-product-preview");

    if (!form || !modal) {
        return;
    }

    imagenInput.addEventListener("change", () => {
        const archivo = imagenInput.files[0];

        if (!archivo) {
            return;
        }

        const lector = new FileReader();

        lector.onload = () => {
            preview.innerHTML = `<img src="${lector.result}" alt="">`;
        };

        lector.readAsDataURL(archivo);
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        error.hidden = true;

        const formData = new FormData(form);

        try {
            const datos = await enviarFormulario("/productos/nuevo", formData);

            crearTarjetaProducto(datos.producto, datos.estado);
            modal.hidden = true;
            form.reset();
            preview.innerHTML = ICONO_CAMARA_INVENTARIO;
            mostrarToast("Producto agregado ✓");
        } catch (err) {
            error.textContent = err.message;
            error.hidden = false;
        }
    });
}

document.addEventListener("DOMContentLoaded", initNewProductForm);

/*
 * Mis Lazos: tocar una tarjeta abre "Editar producto" (nombre,
 * imagen, costo, precio y stock, todos editables) con una opción
 * de eliminar. Distinto de "Ajustar inventario" (que solo suma
 * stock) porque acá se está administrando el catálogo, no
 * reponiendo mercancía.
 */
function abrirModalEditarProducto(tarjeta) {
    const modal = document.querySelector("#edit-product-modal");

    if (!modal) {
        return;
    }

    const imagen = tarjeta.dataset.imagen;
    const preview = document.querySelector("#edit-product-preview");
    const error = document.querySelector("#edit-product-error");

    document.querySelector("#edit-product-id").value = tarjeta.dataset.productId;
    document.querySelector("#edit-product-nombre").value = tarjeta.dataset.nombre;
    document.querySelector("#edit-product-costo").value = tarjeta.dataset.costo;
    document.querySelector("#edit-product-precio").value = tarjeta.dataset.precio;
    document.querySelector("#edit-product-stock").value = tarjeta.dataset.stock;

    preview.innerHTML = imagen ? `<img src="${imagen}" alt="">` : ICONO_CAMARA_INVENTARIO;
    error.hidden = true;
    error.textContent = "";

    abrirHojaInferior(modal);
}

function initBowCard(tarjeta) {
    tarjeta.addEventListener("click", () => abrirModalEditarProducto(tarjeta));
}

function initBowsGrid() {
    document.querySelectorAll("#bows-grid .bow-card[data-product-id]").forEach(initBowCard);
}

document.addEventListener("DOMContentLoaded", initBowsGrid);

function actualizarTarjetaBowCard(producto) {
    const tarjeta = document.querySelector(`#bow-card-${producto.id}`);

    if (!tarjeta) {
        return;
    }

    tarjeta.dataset.name = producto.nombre.toLowerCase();
    tarjeta.dataset.nombre = producto.nombre;
    tarjeta.dataset.imagen = producto.imagen || "";
    tarjeta.dataset.costo = producto.costo_produccion;
    tarjeta.dataset.precio = producto.precio_publico;
    tarjeta.dataset.stock = producto.stock;

    const nombreEl = tarjeta.querySelector("strong");
    if (nombreEl) {
        nombreEl.textContent = producto.nombre;
    }

    const imagenContainer = tarjeta.querySelector(".bow-card__image");
    if (imagenContainer) {
        imagenContainer.innerHTML = producto.imagen
            ? `<img src="${producto.imagen}" alt="">`
            : `<span aria-hidden="true">🎀</span>`;
    }
}

function initEditProductForm() {
    const form = document.querySelector("#edit-product-form");
    const modal = document.querySelector("#edit-product-modal");
    const error = document.querySelector("#edit-product-error");
    const imagenInput = document.querySelector("#edit-product-imagen-input");
    const preview = document.querySelector("#edit-product-preview");

    if (!form || !modal) {
        return;
    }

    imagenInput.addEventListener("change", () => {
        const archivo = imagenInput.files[0];

        if (!archivo) {
            return;
        }

        const lector = new FileReader();

        lector.onload = () => {
            preview.innerHTML = `<img src="${lector.result}" alt="">`;
        };

        lector.readAsDataURL(archivo);
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        error.hidden = true;

        const productoId = document.querySelector("#edit-product-id").value;
        const formData = new FormData(form);

        try {
            const datos = await enviarFormulario(`/productos/${productoId}/editar`, formData);

            actualizarTarjetaBowCard(datos.producto);
            modal.hidden = true;
            mostrarToast("Producto actualizado ✓");
        } catch (err) {
            error.textContent = err.message;
            error.hidden = false;
        }
    });
}

document.addEventListener("DOMContentLoaded", initEditProductForm);

function initDeleteProduct() {
    const deleteButton = document.querySelector("#edit-product-delete");
    const confirmModal = document.querySelector("#delete-product-modal");
    const confirmButton = document.querySelector("#confirm-delete-product");
    const editModal = document.querySelector("#edit-product-modal");

    if (!deleteButton || !confirmModal || !confirmButton || !editModal) {
        return;
    }

    deleteButton.addEventListener("click", () => {
        const nombre = document.querySelector("#edit-product-nombre").value;

        document.querySelector("#delete-product-name").textContent = nombre;
        confirmModal.hidden = false;
    });

    confirmButton.addEventListener("click", async () => {
        const productoId = document.querySelector("#edit-product-id").value;

        try {
            await enviarFormulario(`/productos/${productoId}/eliminar`, new FormData());

            document.querySelector(`#bow-card-${productoId}`)?.remove();
            confirmModal.hidden = true;
            editModal.hidden = true;
            mostrarToast("Producto eliminado ✓");
        } catch (err) {
            confirmModal.hidden = true;
            mostrarToast(err.message);
        }
    });
}

document.addEventListener("DOMContentLoaded", initDeleteProduct);

/*
 * Venta: alta unificada en varios pasos (clienta → producto →
 * color → cantidad → entrega → pago → resumen), detalle con
 * avance de entrega / marcar pago / edición / cancelación, y
 * sincronizado de las listas de Pedidos y Cobros sin recargar la
 * página. Un mismo modal (#nueva-venta-modal) y un mismo detalle
 * (#venta-detalle-modal) se reutilizan desde Ventas, Pedidos,
 * Cobros y el botón central de la barra inferior — no duplicar
 * esta lógica en ninguna otra pantalla.
 * `VENTAS_DATA` (definida inline en pedidos.html / cobros.html) es
 * la misma lista ya filtrada que renderizó el servidor — se
 * mantiene sincronizada acá para no tener que volver a pedirla por
 * fetch cada vez que se abre un detalle.
 */

const nuevaVentaState = {
    clienteId: null,
    clienteNombre: "",
    clienteAvatar: "",
    productoId: null,
    productoNombre: "",
    productoImagen: "",
    productoPrecio: 0,
    productoStock: 0,
    color: "",
    cantidad: 1,
    entregaAhora: null,
    pagoAhora: null,
    fechaVencimiento: "",
};

const ventaEditState = {
    ventaId: null,
    cantidad: 1,
    stock: 0,
    color: "",
};

function formatoMoneda(valor) {
    return `$${Number(valor).toLocaleString("es")}`;
}

function irAPasoVenta(paso) {
    document.querySelectorAll("#venta-steps .pedido-steps__step").forEach((paso_) => {
        paso_.classList.toggle("is-active", paso_.dataset.step === paso);
    });
}

function actualizarQtyStepper(prefix, cantidad, stock) {
    const minus = document.querySelector(`#${prefix}-qty-minus`);
    const plus = document.querySelector(`#${prefix}-qty-plus`);
    const valueEl = document.querySelector(`#${prefix}-qty-value`);
    const stockEl = document.querySelector(`#${prefix}-qty-stock`);

    if (!valueEl) {
        return;
    }

    valueEl.textContent = cantidad;
    stockEl.textContent = `Stock disponible: ${stock}`;
    minus.disabled = cantidad <= 1;
    plus.disabled = cantidad >= stock;
}

function initQtyStepper(prefix, obtenerEstado, actualizarEstado) {
    const minus = document.querySelector(`#${prefix}-qty-minus`);
    const plus = document.querySelector(`#${prefix}-qty-plus`);

    if (!minus || !plus) {
        return;
    }

    minus.addEventListener("click", () => {
        const { cantidad, stock } = obtenerEstado();

        if (cantidad > 1) {
            actualizarEstado(cantidad - 1);
            actualizarQtyStepper(prefix, cantidad - 1, stock);
        }
    });

    plus.addEventListener("click", () => {
        const { cantidad, stock } = obtenerEstado();

        if (cantidad < stock) {
            actualizarEstado(cantidad + 1);
            actualizarQtyStepper(prefix, cantidad + 1, stock);
        }
    });
}

function initColorGrid(prefix, alSeleccionar) {
    const grid = document.querySelector(`#${prefix}-color-grid`);

    if (!grid) {
        return;
    }

    grid.querySelectorAll(".color-select__item").forEach((item) => {
        item.addEventListener("click", () => {
            grid.querySelectorAll(".color-select__item").forEach((otro) => {
                otro.classList.remove("is-selected");
            });

            item.classList.add("is-selected");
            alSeleccionar(item.dataset.color);
        });
    });
}

function normalizarTexto(valor) {
    return valor
        .toLowerCase()
        .normalize("NFD")
        .replace(/[̀-ͯ]/g, "");
}

function initVentaBuscarClienta() {
    const input = document.querySelector("#venta-buscar-clienta-input");
    const filas = document.querySelectorAll("#venta-clientas-resultados [data-client-row]");
    const vacio = document.querySelector("#venta-clientas-sin-resultados");

    if (!input) {
        return;
    }

    input.addEventListener("input", () => {
        const consulta = normalizarTexto(input.value.trim());
        let visibles = 0;

        filas.forEach((fila) => {
            const coincide = !consulta || normalizarTexto(fila.dataset.clientSearch || "").includes(consulta);
            fila.hidden = !coincide;

            if (coincide) {
                visibles += 1;
            }
        });

        if (vacio) {
            vacio.hidden = visibles !== 0;
        }
    });

    filas.forEach((fila) => {
        fila.addEventListener("click", () => {
            nuevaVentaState.clienteId = fila.dataset.clientId;
            nuevaVentaState.clienteNombre = fila.dataset.clientNombre;
            nuevaVentaState.clienteAvatar = fila.dataset.clientAvatar;

            const resumen = document.querySelector("#venta-resumen-clienta-seleccionada");

            resumen.innerHTML = fila.dataset.clientAvatar
                ? `<img src="${fila.dataset.clientAvatar}" alt="">`
                : "";

            resumen.insertAdjacentHTML("beforeend", "<span></span>");
            resumen.querySelector("span").textContent = `Clienta: ${fila.dataset.clientNombre}`;

            irAPasoVenta("producto");
        });
    });
}

function initVentaSeleccionarProducto() {
    document.querySelectorAll("#venta-steps [data-product-row]").forEach((fila) => {
        fila.addEventListener("click", () => {
            if (fila.disabled) {
                return;
            }

            nuevaVentaState.productoId = fila.dataset.productId;
            nuevaVentaState.productoNombre = fila.dataset.productNombre;
            nuevaVentaState.productoImagen = fila.dataset.productImagen;
            nuevaVentaState.productoPrecio = Number(fila.dataset.productPrecio);
            nuevaVentaState.productoStock = Number(fila.dataset.productStock);
            nuevaVentaState.color = "";
            nuevaVentaState.cantidad = 1;

            const resumen = document.querySelector("#venta-resumen-producto-seleccionado");

            resumen.innerHTML = fila.dataset.productImagen
                ? `<img src="${fila.dataset.productImagen}" alt="">`
                : "";

            resumen.insertAdjacentHTML("beforeend", "<span></span>");
            resumen.querySelector("span").textContent = `Producto: ${fila.dataset.productNombre}`;

            document.querySelectorAll("#venta-new-color-grid .color-select__item").forEach((item) => {
                item.classList.remove("is-selected");
            });

            irAPasoVenta("color");
        });
    });
}

function irAPasoVentaResumen() {
    document.querySelector("#venta-resumen-cliente-avatar").innerHTML = nuevaVentaState.clienteAvatar
        ? `<img src="${nuevaVentaState.clienteAvatar}" alt="">`
        : "";

    if (!nuevaVentaState.clienteAvatar) {
        document.querySelector("#venta-resumen-cliente-avatar").textContent = nuevaVentaState.clienteNombre.charAt(0);
    }

    document.querySelector("#venta-resumen-cliente").textContent = nuevaVentaState.clienteNombre;

    document.querySelector("#venta-resumen-producto-imagen").innerHTML = nuevaVentaState.productoImagen
        ? `<img src="${nuevaVentaState.productoImagen}" alt="">`
        : `<span aria-hidden="true">🎀</span>`;

    document.querySelector("#venta-resumen-producto").textContent = nuevaVentaState.productoNombre;
    document.querySelector("#venta-resumen-color").textContent = `${nuevaVentaState.color} · x${nuevaVentaState.cantidad}`;

    document.querySelector("#venta-resumen-cantidad").textContent = nuevaVentaState.cantidad;
    document.querySelector("#venta-resumen-precio-unitario").textContent = formatoMoneda(nuevaVentaState.productoPrecio);
    document.querySelector("#venta-resumen-total").textContent = formatoMoneda(
        nuevaVentaState.productoPrecio * nuevaVentaState.cantidad
    );

    document.querySelector("#venta-resumen-entrega").textContent =
        nuevaVentaState.entregaAhora === "entregado" ? "Entregado ahora" : "Pendiente de entrega";
    document.querySelector("#venta-resumen-pago").textContent =
        nuevaVentaState.pagoAhora === "pagado" ? "Pagado ahora" : "Pendiente de pago";

    const vencimientoRow = document.querySelector("#venta-resumen-vencimiento-row");
    if (nuevaVentaState.pagoAhora === "pendiente") {
        vencimientoRow.hidden = false;
        document.querySelector("#venta-resumen-vencimiento").textContent = nuevaVentaState.fechaVencimiento;
    } else {
        vencimientoRow.hidden = true;
    }

    irAPasoVenta("resumen");
}

function haySeleccionEnVenta() {
    return Boolean(nuevaVentaState.clienteId || nuevaVentaState.productoId || nuevaVentaState.color);
}

function reiniciarEstadoNuevaVenta() {
    nuevaVentaState.clienteId = null;
    nuevaVentaState.clienteNombre = "";
    nuevaVentaState.clienteAvatar = "";
    nuevaVentaState.productoId = null;
    nuevaVentaState.productoNombre = "";
    nuevaVentaState.productoImagen = "";
    nuevaVentaState.productoPrecio = 0;
    nuevaVentaState.productoStock = 0;
    nuevaVentaState.color = "";
    nuevaVentaState.cantidad = 1;
    nuevaVentaState.entregaAhora = null;
    nuevaVentaState.pagoAhora = null;
    nuevaVentaState.fechaVencimiento = "";

    const buscador = document.querySelector("#venta-buscar-clienta-input");
    if (buscador) {
        buscador.value = "";
    }

    document.querySelectorAll("#venta-clientas-resultados [data-client-row]").forEach((fila) => {
        fila.hidden = false;
    });

    const sinResultados = document.querySelector("#venta-clientas-sin-resultados");
    if (sinResultados) {
        sinResultados.hidden = true;
    }

    const notas = document.querySelector("#venta-nueva-notas");
    if (notas) {
        notas.value = "";
    }

    const error = document.querySelector("#venta-nueva-error");
    if (error) {
        error.hidden = true;
    }

    document.querySelectorAll("#venta-steps .color-select__item").forEach((item) => {
        item.classList.remove("is-selected");
    });

    document.querySelectorAll("#venta-entrega-opciones [data-entrega-opcion], #venta-pago-opciones [data-pago-opcion]").forEach((boton) => {
        boton.classList.remove("is-selected");
    });

    const vencimientoWrap = document.querySelector("#venta-vencimiento-wrap");
    if (vencimientoWrap) {
        vencimientoWrap.hidden = true;
    }

    const vencimientoInput = document.querySelector("#venta-vencimiento-input");
    if (vencimientoInput) {
        vencimientoInput.value = "";
    }

    const continuarPagoBtn = document.querySelector("#venta-ir-a-resumen-btn");
    if (continuarPagoBtn) {
        continuarPagoBtn.hidden = true;
    }

    irAPasoVenta("clienta");
}

function cerrarNuevaVentaModal(reiniciar) {
    const modal = document.querySelector("#nueva-venta-modal");
    if (modal) {
        modal.hidden = true;
    }

    if (reiniciar) {
        reiniciarEstadoNuevaVenta();
    }
}

function intentarCerrarNuevaVenta() {
    if (haySeleccionEnVenta()) {
        document.querySelector("#venta-descartar-modal").hidden = false;
    } else {
        cerrarNuevaVentaModal(true);
    }
}

function crearFilaVenta(venta) {
    const li = document.createElement("li");
    li.dataset.estado = venta.estado_entrega;

    const boton = document.createElement("button");
    boton.type = "button";
    boton.className = "list-row";
    boton.id = `pedido-card-${venta.id}`;
    boton.dataset.pedidoId = venta.id;

    boton.innerHTML = `
        <span class="list-row__avatar"></span>
        <span class="list-row__body">
            <strong></strong>
            <small></small>
        </span>
        <span class="list-row__meta">
            <strong></strong>
            <span class="pill"></span>
        </span>
        <span class="list-row__chevron" aria-hidden="true">›</span>
    `;

    boton.addEventListener("click", () => abrirDetalleVenta(venta.id));

    li.appendChild(boton);
    actualizarFilaVenta(li, venta);

    return li;
}

function actualizarFilaVenta(li, venta) {
    li.dataset.estado = venta.estado_entrega;

    const tarjeta = li.querySelector(".list-row");
    const avatar = tarjeta.querySelector(".list-row__avatar");

    avatar.innerHTML = venta.cliente.avatar
        ? `<img src="${venta.cliente.avatar}" alt="">`
        : "";

    if (!venta.cliente.avatar) {
        avatar.textContent = venta.cliente.nombre.charAt(0);
    }

    tarjeta.querySelector(".list-row__body strong").textContent =
        `#${venta.numero_venta} · ${venta.cliente.nombre} ${venta.cliente.apellido}`;
    tarjeta.querySelector(".list-row__body small").textContent = venta.fecha_creacion_texto;
    tarjeta.querySelector(".list-row__meta strong").textContent = formatoMoneda(venta.total);

    const pill = tarjeta.querySelector(".list-row__meta .pill");
    pill.className = `pill ${venta.estado_entrega_info.pill_class}`;
    pill.textContent = venta.estado_entrega_info.etiqueta;
}

function actualizarFilaCobro(row, venta) {
    row.querySelector(".list-row__body small").textContent = venta.estado_cobro.texto;
    row.querySelector(".list-row__meta strong").textContent = formatoMoneda(venta.total);

    const pill = row.querySelector(".list-row__meta .pill");
    pill.className = `pill ${venta.estado_cobro.pill_class}`;
    pill.textContent = venta.estado_cobro.etiqueta;
}

function reordenarListaPedidos() {
    const lista = document.querySelector("#pedidos-list");
    if (!lista) {
        return;
    }

    const filas = Array.from(lista.querySelectorAll(":scope > li[data-estado]"));

    filas.sort((a, b) => {
        const va = VENTAS_DATA.find((v) => String(v.id) === a.querySelector("[data-pedido-id]")?.dataset.pedidoId);
        const vb = VENTAS_DATA.find((v) => String(v.id) === b.querySelector("[data-pedido-id]")?.dataset.pedidoId);

        if (!va || !vb) {
            return 0;
        }

        if (va.estado_entrega_info.prioridad !== vb.estado_entrega_info.prioridad) {
            return va.estado_entrega_info.prioridad - vb.estado_entrega_info.prioridad;
        }

        return vb.fecha_creacion.localeCompare(va.fecha_creacion);
    });

    filas.forEach((fila) => lista.appendChild(fila));
}

function aplicarFiltroActivo() {
    document.querySelector(".pedidos-filters__btn.is-active")?.click();
}

function perteneceAPedidos(venta) {
    return venta.estado_entrega !== "entregado" && venta.estado_entrega !== "cancelado";
}

function perteneceACobros(venta) {
    return venta.estado_pago === "pendiente" && !venta.cancelada;
}

function actualizarVacioPedidos() {
    const lista = document.querySelector("#pedidos-list");
    const vacio = document.querySelector("#pedidos-empty");

    if (!lista || !vacio) {
        return;
    }

    vacio.hidden = lista.querySelectorAll(":scope > li[data-estado]").length > 0;
}

function actualizarVacioCobros() {
    const lista = document.querySelector("#cobros-list");
    const vacio = document.querySelector("#cobros-empty");

    if (!lista || !vacio) {
        return;
    }

    vacio.hidden = lista.querySelectorAll(":scope > li [data-venta-id]").length > 0;
}

function actualizarResumenCobros() {
    const totalEl = document.querySelector("#cobros-total-pendiente");
    const countEl = document.querySelector("#cobros-total-count");

    if (!totalEl || !countEl) {
        return;
    }

    const pendientes = VENTAS_DATA.filter((v) => v.estado_pago === "pendiente" && !v.cancelada);
    const total = pendientes.reduce((suma, v) => suma + v.total, 0);

    totalEl.textContent = formatoMoneda(total);
    countEl.textContent = `${pendientes.length} ${pendientes.length === 1 ? "cobro" : "cobros"}`;
}

function sincronizarVentaCreada(venta) {
    VENTAS_DATA.push(venta);

    const lista = document.querySelector("#pedidos-list");
    if (lista && perteneceAPedidos(venta)) {
        lista.appendChild(crearFilaVenta(venta));
        reordenarListaPedidos();
        aplicarFiltroActivo();
        actualizarVacioPedidos();
    }
}

function sincronizarVentaTrasAccion(venta) {
    const indice = VENTAS_DATA.findIndex((v) => v.id === venta.id);
    if (indice >= 0) {
        VENTAS_DATA[indice] = venta;
    }

    const filaPedido = document.querySelector(`#pedido-card-${venta.id}`)?.closest("li");
    if (filaPedido) {
        if (perteneceAPedidos(venta)) {
            actualizarFilaVenta(filaPedido, venta);
        } else {
            filaPedido.remove();
        }

        reordenarListaPedidos();
        aplicarFiltroActivo();
        actualizarVacioPedidos();
    }

    const filaCobro = document.querySelector(`[data-venta-id="${venta.id}"]`);
    if (filaCobro) {
        if (perteneceACobros(venta)) {
            actualizarFilaCobro(filaCobro, venta);
        } else {
            filaCobro.closest("li")?.remove();
        }

        actualizarVacioCobros();
        actualizarResumenCobros();
    }
}

function abrirDetalleVenta(ventaId) {
    const venta = VENTAS_DATA.find((v) => String(v.id) === String(ventaId));

    if (!venta) {
        return;
    }

    document.querySelector("#venta-detalle-numero").textContent = `Venta #${venta.numero_venta}`;
    document.querySelector("#venta-detalle-fecha").textContent = venta.fecha_creacion_texto;

    const entregaPill = document.querySelector("#venta-detalle-entrega-pill");
    entregaPill.className = `pill ${venta.estado_entrega_info.pill_class}`;
    entregaPill.textContent = venta.estado_entrega_info.etiqueta;

    const pagoPill = document.querySelector("#venta-detalle-pago-pill");
    pagoPill.className = `pill ${venta.estado_pago_info.pill_class}`;
    pagoPill.textContent = venta.estado_pago_info.etiqueta;

    const avatarEl = document.querySelector("#venta-detalle-cliente-avatar");
    avatarEl.innerHTML = venta.cliente.avatar ? `<img src="${venta.cliente.avatar}" alt="">` : "";
    if (!venta.cliente.avatar) {
        avatarEl.textContent = venta.cliente.nombre.charAt(0);
    }

    document.querySelector("#venta-detalle-cliente-nombre").textContent = `${venta.cliente.nombre} ${venta.cliente.apellido}`;
    document.querySelector("#venta-detalle-cliente-telefono").textContent = venta.cliente.telefono;

    const imgEl = document.querySelector("#venta-detalle-producto-imagen");
    imgEl.innerHTML = venta.producto.imagen
        ? `<img src="${venta.producto.imagen}" alt="">`
        : `<span aria-hidden="true">🎀</span>`;

    document.querySelector("#venta-detalle-producto-nombre").textContent = venta.producto.nombre;
    document.querySelector("#venta-detalle-producto-color").textContent = `${venta.color} · x${venta.cantidad}`;

    document.querySelector("#venta-detalle-precio-unitario").textContent = formatoMoneda(venta.precio_unitario);
    document.querySelector("#venta-detalle-cantidad-texto").textContent = venta.cantidad;
    document.querySelector("#venta-detalle-total").textContent = formatoMoneda(venta.total);

    const vencimientoRow = document.querySelector("#venta-detalle-vencimiento-row");
    if (venta.estado_pago === "pendiente" && venta.fecha_vencimiento_texto) {
        vencimientoRow.hidden = false;
        document.querySelector("#venta-detalle-vencimiento").textContent = venta.fecha_vencimiento_texto;
    } else {
        vencimientoRow.hidden = true;
    }

    const entregaFechaRow = document.querySelector("#venta-detalle-entrega-fecha-row");
    if (venta.fecha_entrega_texto) {
        entregaFechaRow.hidden = false;
        document.querySelector("#venta-detalle-entrega-fecha").textContent = venta.fecha_entrega_texto;
    } else {
        entregaFechaRow.hidden = true;
    }

    const pagoFechaRow = document.querySelector("#venta-detalle-pago-fecha-row");
    if (venta.fecha_pago_texto) {
        pagoFechaRow.hidden = false;
        document.querySelector("#venta-detalle-pago-fecha").textContent = venta.fecha_pago_texto;
    } else {
        pagoFechaRow.hidden = true;
    }

    const notasWrap = document.querySelector("#venta-detalle-notas-wrap");
    if (venta.notas) {
        document.querySelector("#venta-detalle-notas").textContent = venta.notas;
        notasWrap.hidden = false;
    } else {
        notasWrap.hidden = true;
    }

    document.querySelector("#venta-detalle-editar-error").hidden = true;

    ventaEditState.ventaId = venta.id;

    const editableWrap = document.querySelector("#venta-detalle-editable-wrap");
    editableWrap.hidden = !venta.editable;

    if (venta.editable) {
        document.querySelector("#venta-detalle-notas-input").value = venta.notas || "";

        ventaEditState.cantidad = venta.cantidad;
        ventaEditState.stock = venta.producto.stock + venta.cantidad;
        ventaEditState.color = venta.color;

        document.querySelectorAll("#ventaedit-color-grid .color-select__item").forEach((item) => {
            item.classList.toggle("is-selected", item.dataset.color === venta.color);
        });

        actualizarQtyStepper("ventaedit", ventaEditState.cantidad, ventaEditState.stock);
    }

    const avanzarBtn = document.querySelector("#venta-detalle-avanzar-btn");
    const avanzarTexto = document.querySelector("#venta-detalle-avanzar-texto");

    if (venta.siguiente_estado_entrega && !venta.cancelada) {
        avanzarBtn.hidden = false;
        avanzarTexto.textContent = `Marcar como ${venta.siguiente_estado_entrega_etiqueta}`;
    } else {
        avanzarBtn.hidden = true;
    }

    document.querySelector("#venta-detalle-pagar-btn").hidden = !(venta.estado_pago === "pendiente" && !venta.cancelada);
    document.querySelector("#venta-detalle-cancelar-btn").hidden = !venta.editable;

    abrirHojaInferior(document.querySelector("#venta-detalle-modal"));
}

function initVentaDetalleAcciones() {
    if (!document.querySelector("#venta-detalle-modal")) {
        return;
    }

    const guardarBtn = document.querySelector("#venta-detalle-guardar-btn");
    const avanzarBtn = document.querySelector("#venta-detalle-avanzar-btn");
    const pagarBtn = document.querySelector("#venta-detalle-pagar-btn");
    const cancelarBtn = document.querySelector("#venta-detalle-cancelar-btn");
    const confirmarCancelarBtn = document.querySelector("#venta-confirmar-cancelar-btn");

    guardarBtn?.addEventListener("click", async () => {
        const error = document.querySelector("#venta-detalle-editar-error");
        error.hidden = true;

        const colorSeleccionado = document.querySelector("#ventaedit-color-grid .color-select__item.is-selected");
        const formData = new FormData();
        formData.set("color", colorSeleccionado ? colorSeleccionado.dataset.color : ventaEditState.color);
        formData.set("cantidad", ventaEditState.cantidad);
        formData.set("notas", document.querySelector("#venta-detalle-notas-input").value);

        try {
            const datos = await enviarFormulario(`/ventas/${ventaEditState.ventaId}/editar`, formData);
            sincronizarVentaTrasAccion(datos.venta);
            document.querySelector("#venta-detalle-modal").hidden = true;
            mostrarToast("Venta actualizada ✓");
        } catch (err) {
            error.textContent = err.message;
            error.hidden = false;
        }
    });

    avanzarBtn?.addEventListener("click", async () => {
        const venta = VENTAS_DATA.find((v) => v.id === ventaEditState.ventaId);
        if (!venta || !venta.siguiente_estado_entrega) {
            return;
        }

        const formData = new FormData();
        formData.set("estado", venta.siguiente_estado_entrega);

        try {
            const datos = await enviarFormulario(`/ventas/${ventaEditState.ventaId}/entrega`, formData);
            sincronizarVentaTrasAccion(datos.venta);
            document.querySelector("#venta-detalle-modal").hidden = true;
            mostrarToast(`Venta marcada como ${datos.venta.estado_entrega_info.etiqueta} ✓`);
        } catch (err) {
            mostrarToast(err.message);
        }
    });

    pagarBtn?.addEventListener("click", async () => {
        try {
            const datos = await enviarFormulario(`/ventas/${ventaEditState.ventaId}/pago`, new FormData());
            sincronizarVentaTrasAccion(datos.venta);
            document.querySelector("#venta-detalle-modal").hidden = true;
            mostrarToast("Venta marcada como pagada ✓");
        } catch (err) {
            mostrarToast(err.message);
        }
    });

    cancelarBtn?.addEventListener("click", () => {
        document.querySelector("#cancelar-venta-numero").textContent =
            document.querySelector("#venta-detalle-numero").textContent;
        document.querySelector("#venta-cancelar-modal").hidden = false;
    });

    confirmarCancelarBtn?.addEventListener("click", async () => {
        try {
            const datos = await enviarFormulario(`/ventas/${ventaEditState.ventaId}/cancelar`, new FormData());
            sincronizarVentaTrasAccion(datos.venta);
            mostrarToast("Venta cancelada ✓");
        } catch (err) {
            mostrarToast(err.message);
        } finally {
            document.querySelector("#venta-cancelar-modal").hidden = true;
            document.querySelector("#venta-detalle-modal").hidden = true;
        }
    });

    initColorGrid("ventaedit", (color) => {
        ventaEditState.color = color;
    });

    initQtyStepper(
        "ventaedit",
        () => ({ cantidad: ventaEditState.cantidad, stock: ventaEditState.stock }),
        (cantidad) => { ventaEditState.cantidad = cantidad; },
    );
}

function initPedidosLista() {
    document.querySelectorAll("#pedidos-list [data-pedido-id]").forEach((tarjeta) => {
        tarjeta.addEventListener("click", () => abrirDetalleVenta(tarjeta.dataset.pedidoId));
    });
}

function initPedidosFiltros() {
    const botones = document.querySelectorAll(".pedidos-filters__btn");
    const vacio = document.querySelector("#pedidos-filtro-vacio");

    if (!botones.length) {
        return;
    }

    const grupos = {
        pendiente: ["pendiente"],
        preparacion: ["preparacion"],
        listo: ["listo"],
    };

    botones.forEach((boton) => {
        boton.addEventListener("click", () => {
            botones.forEach((b) => b.classList.remove("is-active"));
            boton.classList.add("is-active");

            const filtro = boton.dataset.filtro;
            const filas = document.querySelectorAll("#pedidos-list > li[data-estado]");
            let visibles = 0;

            filas.forEach((fila) => {
                const mostrar = filtro === "todos" || (grupos[filtro] || []).includes(fila.dataset.estado);
                fila.hidden = !mostrar;

                if (mostrar) {
                    visibles += 1;
                }
            });

            if (vacio) {
                vacio.hidden = !(visibles === 0 && filas.length > 0);
            }
        });
    });
}

function initCobrosLista() {
    document.querySelectorAll("#cobros-list [data-venta-id]").forEach((fila) => {
        fila.addEventListener("click", () => abrirDetalleVenta(fila.dataset.ventaId));
    });

    document.querySelectorAll("#cobros-list .cobro-whatsapp-btn").forEach((boton) => {
        boton.addEventListener("click", (evento) => evento.stopPropagation());
    });
}

function initNuevaVentaFlujo() {
    const modal = document.querySelector("#nueva-venta-modal");
    if (!modal) {
        return;
    }

    document.querySelectorAll("#new-order-button, #new-sale-button, #pedidos-empty-add").forEach((trigger) => {
        trigger.addEventListener("click", () => {
            reiniciarEstadoNuevaVenta();
            abrirHojaInferior(modal);
        });
    });

    modal.querySelector(".modal__backdrop")?.addEventListener("click", intentarCerrarNuevaVenta);

    document.querySelectorAll("#venta-steps [data-go-step]").forEach((boton) => {
        boton.addEventListener("click", () => irAPasoVenta(boton.dataset.goStep));
    });

    document.querySelector("#venta-registrar-clienta-btn")?.addEventListener("click", () => {
        window.location.href = `/clientes/nueva?volver_a=${modal.dataset.volverA}`;
    });

    initColorGrid("venta-new", (color) => {
        nuevaVentaState.color = color;
        nuevaVentaState.cantidad = 1;
        actualizarQtyStepper("venta-new", nuevaVentaState.cantidad, nuevaVentaState.productoStock);
        irAPasoVenta("cantidad");
    });

    initQtyStepper(
        "venta-new",
        () => ({ cantidad: nuevaVentaState.cantidad, stock: nuevaVentaState.productoStock }),
        (cantidad) => { nuevaVentaState.cantidad = cantidad; },
    );

    document.querySelector("#venta-ir-a-entrega-btn")?.addEventListener("click", () => irAPasoVenta("entrega"));

    document.querySelectorAll("#venta-entrega-opciones [data-entrega-opcion]").forEach((boton) => {
        boton.addEventListener("click", () => {
            document.querySelectorAll("#venta-entrega-opciones [data-entrega-opcion]").forEach((b) => {
                b.classList.remove("is-selected");
            });

            boton.classList.add("is-selected");
            nuevaVentaState.entregaAhora = boton.dataset.entregaOpcion;
            irAPasoVenta("pago");
        });
    });

    document.querySelectorAll("#venta-pago-opciones [data-pago-opcion]").forEach((boton) => {
        boton.addEventListener("click", () => {
            document.querySelectorAll("#venta-pago-opciones [data-pago-opcion]").forEach((b) => {
                b.classList.remove("is-selected");
            });

            boton.classList.add("is-selected");
            nuevaVentaState.pagoAhora = boton.dataset.pagoOpcion;

            const vencimientoWrap = document.querySelector("#venta-vencimiento-wrap");
            const input = document.querySelector("#venta-vencimiento-input");

            if (nuevaVentaState.pagoAhora === "pendiente") {
                vencimientoWrap.hidden = false;

                if (!input.value) {
                    const base = new Date();
                    base.setDate(base.getDate() + 5);
                    input.value = formatISODate(base);
                }

                nuevaVentaState.fechaVencimiento = input.value;
            } else {
                vencimientoWrap.hidden = true;
            }

            document.querySelector("#venta-ir-a-resumen-btn").hidden = false;
        });
    });

    document.querySelector("#venta-vencimiento-input")?.addEventListener("change", (evento) => {
        nuevaVentaState.fechaVencimiento = evento.target.value;
    });

    document.querySelector("#venta-ir-a-resumen-btn")?.addEventListener("click", irAPasoVentaResumen);

    document.querySelector("#venta-cancelar-nueva-btn")?.addEventListener("click", intentarCerrarNuevaVenta);

    document.querySelector("#venta-confirmar-descartar-btn")?.addEventListener("click", () => {
        document.querySelector("#venta-descartar-modal").hidden = true;
        cerrarNuevaVentaModal(true);
    });

    document.querySelector("#venta-guardar-btn")?.addEventListener("click", async () => {
        const error = document.querySelector("#venta-nueva-error");
        error.hidden = true;

        const formData = new FormData();
        formData.set("cliente_id", nuevaVentaState.clienteId);
        formData.set("producto_id", nuevaVentaState.productoId);
        formData.set("color", nuevaVentaState.color);
        formData.set("cantidad", nuevaVentaState.cantidad);
        formData.set("entrega_ahora", nuevaVentaState.entregaAhora === "entregado" ? "1" : "0");
        formData.set("pago_ahora", nuevaVentaState.pagoAhora === "pagado" ? "1" : "0");
        formData.set(
            "fecha_vencimiento_pago",
            nuevaVentaState.pagoAhora === "pendiente" ? nuevaVentaState.fechaVencimiento : ""
        );
        formData.set("notas", document.querySelector("#venta-nueva-notas").value);

        try {
            const datos = await enviarFormulario("/ventas/nueva", formData);
            cerrarNuevaVentaModal(true);

            if (document.querySelector("#pedidos-list")) {
                sincronizarVentaCreada(datos.venta);
                mostrarToast("Venta registrada ✓");
            } else {
                window.location.reload();
            }
        } catch (err) {
            error.textContent = err.message;
            error.hidden = false;
        }
    });
}

function initVolverDeNuevaClienta() {
    const params = new URLSearchParams(window.location.search);
    const clienteId = params.get("nueva_clienta");

    if (!clienteId) {
        return;
    }

    history.replaceState(null, "", window.location.pathname);

    const modal = document.querySelector("#nueva-venta-modal");
    const fila = document.querySelector(`#venta-clientas-resultados [data-client-id="${clienteId}"]`);

    if (!modal || !fila) {
        return;
    }

    reiniciarEstadoNuevaVenta();
    abrirHojaInferior(modal);
    fila.click();
}

function initAbrirNuevaVentaDesdeQuery() {
    const params = new URLSearchParams(window.location.search);

    if (params.get("abrir_nueva_venta") !== "1") {
        return;
    }

    history.replaceState(null, "", window.location.pathname);

    const modal = document.querySelector("#nueva-venta-modal");
    if (!modal) {
        return;
    }

    reiniciarEstadoNuevaVenta();
    abrirHojaInferior(modal);
}

function initBottomNavNuevaVenta() {
    const boton = document.querySelector("#bottom-nav-nueva-venta");
    if (!boton) {
        return;
    }

    boton.addEventListener("click", () => {
        const modal = document.querySelector("#nueva-venta-modal");

        if (modal) {
            reiniciarEstadoNuevaVenta();
            abrirHojaInferior(modal);
        } else {
            window.location.href = "/ventas?abrir_nueva_venta=1";
        }
    });
}

document.addEventListener("DOMContentLoaded", initBottomNavNuevaVenta);

function initVentas() {
    initNuevaVentaFlujo();
    initVentaDetalleAcciones();
    initVentaBuscarClienta();
    initVentaSeleccionarProducto();
    initPedidosLista();
    initPedidosFiltros();
    initCobrosLista();
    initAbrirNuevaVentaDesdeQuery();
    initVolverDeNuevaClienta();
}

document.addEventListener("DOMContentLoaded", initVentas);

/*
 * Configuración → Seguridad: editar nombre del administrador,
 * usuario y (opcionalmente) contraseña. Reutiliza abrirHojaInferior,
 * enviarFormulario y mostrarToast — ya genéricos.
 */
function initSeguridad() {
    const trigger = document.querySelector("#seguridad-row");
    const modal = document.querySelector("#seguridad-modal");

    if (!trigger || !modal) {
        return;
    }

    trigger.addEventListener("click", () => abrirHojaInferior(modal));

    document.querySelector("#seguridad-form")?.addEventListener("submit", async (event) => {
        event.preventDefault();

        const error = document.querySelector("#seguridad-error");
        error.hidden = true;

        const formData = new FormData(event.target);

        try {
            const datos = await enviarFormulario("/configuracion/seguridad", formData);

            document.querySelector("#seguridad-subtitulo").textContent = `Usuario: ${datos.usuario}`;
            document.querySelector("#seguridad-password").value = "";
            modal.hidden = true;
            mostrarToast("Seguridad actualizada ✓");
        } catch (err) {
            error.textContent = err.message;
            error.hidden = false;
        }
    });
}

document.addEventListener("DOMContentLoaded", initSeguridad);

/*
 * Progressive Web App: registro del Service Worker y tarjeta propia
 * de instalación (nunca el mini-infobar/alert() nativo del
 * navegador). El registro corre en toda pantalla —incluida
 * /login— porque Chrome necesita el Service Worker activo para
 * evaluar si el sitio es instalable, sin importar cuál haya sido la
 * primera página visitada.
 */
function registrarServiceWorker() {
    if (!("serviceWorker" in navigator)) {
        return;
    }

    window.addEventListener("load", () => {
        navigator.serviceWorker.register("/service-worker.js").catch(() => {
            // Sin Service Worker no hay instalación posible, pero el
            // resto de la app funciona igual — no es un error fatal.
        });
    });
}

registrarServiceWorker();

const PWA_SNOOZE_KEY = "nudorosa-instalar-pwa-cerrado-en";
const PWA_SNOOZE_DIAS = 7;

// Solo existe mientras el navegador no confirme o descarte la
// instalación: se limpia en cuanto se usa (ver instalarPWA) o cuando
// appinstalled avisa que ya se instaló.
let eventoInstalacionDiferido = null;

function appEstaInstalada() {
    return (
        window.matchMedia("(display-mode: standalone)").matches ||
        window.navigator.standalone === true
    );
}

function puedeMostrarTarjetaInstalacion() {
    const cerradoEn = Number(localStorage.getItem(PWA_SNOOZE_KEY));

    if (!cerradoEn) {
        return true;
    }

    const diasTranscurridos = (Date.now() - cerradoEn) / (1000 * 60 * 60 * 24);
    return diasTranscurridos >= PWA_SNOOZE_DIAS;
}

function mostrarFilaInstalarConfiguracion() {
    const fila = document.querySelector("#config-install-row");
    if (fila) {
        fila.hidden = false;
    }
}

function ocultarFilaInstalarConfiguracion() {
    const fila = document.querySelector("#config-install-row");
    if (fila) {
        fila.hidden = true;
    }
}

function mostrarTarjetaInstalacion() {
    document.querySelector("#install-pwa-modal")?.removeAttribute("hidden");
}

function ocultarTarjetaInstalacion() {
    const modal = document.querySelector("#install-pwa-modal");
    if (modal) {
        modal.hidden = true;
    }
}

function posponerInstalacion() {
    localStorage.setItem(PWA_SNOOZE_KEY, String(Date.now()));
    ocultarTarjetaInstalacion();
}

async function instalarPWA() {
    if (!eventoInstalacionDiferido) {
        return;
    }

    const evento = eventoInstalacionDiferido;
    evento.prompt();
    await evento.userChoice;

    // La respuesta ya llegó (aceptada o rechazada): el evento no se
    // puede reutilizar en ninguno de los dos casos.
    ocultarTarjetaInstalacion();
    eventoInstalacionDiferido = null;
    ocultarFilaInstalarConfiguracion();
}

function initInstalacionPWA() {
    // Ya instalada y corriendo en modo standalone: ni el aviso ni la
    // opción del menú tienen sentido.
    if (appEstaInstalada()) {
        return;
    }

    window.addEventListener("beforeinstallprompt", (event) => {
        // Evita el mini-infobar propio de Chrome — el aviso lo decide
        // esta app, con su propio diseño.
        event.preventDefault();
        eventoInstalacionDiferido = event;

        mostrarFilaInstalarConfiguracion();

        if (puedeMostrarTarjetaInstalacion()) {
            mostrarTarjetaInstalacion();
        }
    });

    window.addEventListener("appinstalled", () => {
        eventoInstalacionDiferido = null;
        ocultarTarjetaInstalacion();
        ocultarFilaInstalarConfiguracion();
        localStorage.removeItem(PWA_SNOOZE_KEY);
    });

    document.querySelector("#install-pwa-accept")?.addEventListener("click", instalarPWA);
    document.querySelector("#install-pwa-dismiss")?.addEventListener("click", posponerInstalacion);
    document.querySelector("#config-install-button")?.addEventListener("click", instalarPWA);

    // El fondo del modal no usa el cierre genérico ([data-modal-close]
    // en initModalDismiss): cerrar tocando afuera cuenta como "Ahora
    // no" y también debe respetar los 7 días de espera.
    document.querySelector("#install-pwa-modal .modal__backdrop")?.addEventListener("click", posponerInstalacion);
}

document.addEventListener("DOMContentLoaded", initInstalacionPWA);
