#!/usr/bin/env python3
"""Build the Spanish (ES) subset: /es/ hub + 3 priority spokes.

Reuses the same template + fleet imagery as EN. Spanish prose is inlined here
to keep one source of truth. Run after deploy.sh to mirror EN changes to ES.

Outputs:
    site/es/index.html
    site/es/alquiler-de-yates-marbella/index.html
    site/es/alquiler-barcos-puerto-banus/index.html
    site/es/alquiler-barcos-sin-licencia-marbella/index.html
"""
from __future__ import annotations
import json, pathlib, html, re
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parents[1]
TEMPLATE = (ROOT / "templates" / "page.html.template").read_text()
CONFIG = json.loads((ROOT / "config" / "keyword_map.json").read_text())
SITE = CONFIG["site"]
SITE_DIR = ROOT / "site"

def jsonld_org():
    return {
        "@context":"https://schema.org","@type":["LocalBusiness","Organization"],
        "@id":SITE['base_url']+"/#org","name":SITE['name'],
        "url":SITE['base_url']+"/","logo":SITE['base_url']+"/og-image.jpg",
        "telephone":SITE['phone_e164'],"email":SITE['email'],
        "areaServed":SITE['departure_ports'],
        "sameAs":[u for u in [SITE.get('instagram_url'), SITE.get('facebook_url')] if u],
        "priceRange":f"€{SITE['price_anchor_low_2h']}–€{SITE['price_anchor_fullday_8h']}",
        "address":{"@type":"PostalAddress","addressLocality":"Marbella","addressRegion":"Andalucía","postalCode":"29602","addressCountry":"ES"},
        "geo":{"@type":"GeoCoordinates","latitude":SITE['geo_lat'],"longitude":SITE['geo_lng']},
        "foundingDate":str(SITE.get('founded_year',2025)),
    }

def hero_local(slug_key):
    """Return (src, srcset, alt) by reusing the EN fleet image map."""
    HEROES = {
        "hub": ("/img/boats/mangusta-80/hero-1600.jpg",
                ["/img/boats/mangusta-80/hero-600.jpg 600w","/img/boats/mangusta-80/hero-900.jpg 900w","/img/boats/mangusta-80/hero-1200.jpg 1200w","/img/boats/mangusta-80/hero-1600.jpg 1600w"],
                "Mangusta 80 navegando frente a La Concha — Marbella"),
        "yates": ("/img/boats/azimut-39/hero-1600.jpg",
                  ["/img/boats/azimut-39/hero-600.jpg 600w","/img/boats/azimut-39/hero-900.jpg 900w","/img/boats/azimut-39/hero-1200.jpg 1200w","/img/boats/azimut-39/hero-1600.jpg 1600w"],
                  "Yate Azimut 39 navegando frente a la montaña La Concha en Marbella"),
        "banus": ("/img/boats/astondoa-40/lifestyle-1200.jpg",
                  ["/img/boats/astondoa-40/lifestyle-600.jpg 600w","/img/boats/astondoa-40/lifestyle-900.jpg 900w","/img/boats/astondoa-40/lifestyle-1200.jpg 1200w"],
                  "Yate Astondoa 40 en Puerto Banús, Marbella"),
        "sin_licencia": ("/img/boats/astondoa-40/hero-1600.jpg",
                  ["/img/boats/astondoa-40/hero-600.jpg 600w","/img/boats/astondoa-40/hero-900.jpg 900w","/img/boats/astondoa-40/hero-1200.jpg 1200w","/img/boats/astondoa-40/hero-1600.jpg 1600w"],
                  "Yate Astondoa 40 con patrón incluido — alquiler de barcos sin licencia Marbella"),
    }
    return HEROES[slug_key]

# Each page: (slug, key, title, meta, h1, sub, eyebrow, body_html, en_alt_path)
PAGES = [
    # ---- HUB ----
    ("",  "hub",
     "Alquiler de barcos en Marbella 2026: Yates desde €749",
     "Alquiler de barcos en Marbella desde €749/2h en nuestros yates a motor de 12,5 m (Astondoa 40 y Azimut 39). Salida desde Puerto Banús — patrón, combustible, bebidas, snacks e IVA incluidos.",
     "Alquiler de barcos en Marbella",
     "Nuestra flota de yates a motor desde Puerto Banús — patrón, bebidas (cerveza · vino blanco · cava) e IVA incluidos.",
     "Marbella · Costa del Sol",
     None,  # body built below
     "/"),
    ("alquiler-de-yates-marbella",  "yates",
     "Alquiler de yates en Marbella 2026: Yates a motor con patrón desde €749",
     "Alquiler de yates en Marbella desde €749/2h en nuestros yates a motor de 12,5 m. Patrón, combustible, bebidas y IVA incluidos. Salida desde Puerto Banús — reserva por WhatsApp.",
     "Alquiler de yates en Marbella",
     "Yates a motor de 12,5 m con patrón incluido — Astondoa 40 y Azimut 39, listos en Puerto Banús.",
     "Yates · Marbella",
     None,
     "/yacht-charter-marbella/"),
    ("alquiler-barcos-puerto-banus",  "banus",
     "Alquiler de barcos en Puerto Banús 2026 — desde €749/2h",
     "Alquiler de barcos en Puerto Banús desde €749 para 2 horas. Nuestros yates a motor de 12,5 m (Astondoa 40 y Azimut 39) — patrón, bebidas y combustible incluidos.",
     "Alquiler de barcos en Puerto Banús",
     "Salida desde el muelle más profundo de Marbella, con patrón y bebidas a bordo.",
     "Puerto Banús · Marbella",
     None,
     "/boat-rental-puerto-banus/"),
    ("alquiler-barcos-sin-licencia-marbella",  "sin_licencia",
     "Alquiler de barcos sin licencia en Marbella — con patrón desde €749",
     "Alquiler de barcos sin licencia en Marbella: nuestra flota va con patrón profesional, así que tú no necesitas titulación. Desde €749/2h con todo incluido.",
     "Alquiler de barcos sin licencia en Marbella",
     "No necesitas titulación: nuestros yates llevan patrón profesional incluido.",
     "Sin licencia · Marbella",
     None,
     "/boat-rental-no-license-marbella/"),
]

# ---------- Body HTML for each (ES content) ----------
def body_hub():
    return '''<p>Operamos dos yates a motor de 12,5 metros en Marbella — el <strong>Astondoa 40</strong> y el <strong>Azimut 39</strong>, ambos con salida desde <strong>Puerto Banús</strong> y con patrón profesional, combustible, bebidas, snacks, seguro e IVA incluidos. Los precios arrancan en <strong>€749 por 2 horas</strong> y llegan hasta <strong>€2.299 por un día completo de 8 horas</strong>.</p>

<h2>Precios de alquiler de barcos en Marbella 2026</h2>
<p>Misma flota, misma tripulación, precio transparente por hora. Sin recargo de temporada alta, sin recargo de levante, sin tasas portuarias añadidas en el muelle.</p>
<table>
<thead><tr><th>Duración</th><th>Precio</th><th>Qué incluye</th></tr></thead>
<tbody>
<tr><td>2 horas</td><td><strong>€749</strong></td><td>Vuelta rápida por la Milla de Oro, una parada de baño</td></tr>
<tr><td>4 horas</td><td>€1.299</td><td>Medio día — comida y baño cómodos</td></tr>
<tr><td>6 horas</td><td>€1.799</td><td>Dos paradas de baño, paddleboard, día completo</td></tr>
<tr><td>8 horas</td><td><strong>€2.299</strong></td><td>Día completo — itinerarios hasta Sotogrande o Cabopino</td></tr>
</tbody>
</table>
<p>Tarifa por hora completa y detalle por barco en <a href="/boats/">/boats/</a>. Compara el <a href="/boats/astondoa-40/">Astondoa 40</a> (9 invitados, fabricado en España, estilo clásico mediterráneo) con el <a href="/boats/azimut-39/">Azimut 39</a> (11 invitados, flybridge italiano, líneas modernas).</p>

<h2>¿Astondoa o Azimut?</h2>
<p>Ambos barcos miden lo mismo (12,5 m), tienen el mismo precio (€749 → €2.299) y salen del mismo puerto (Puerto Banús). En qué se diferencian:</p>
<ul>
<li><strong><a href="/boats/astondoa-40/">Astondoa 40</a></strong> — fabricado en Cádiz, interior clásico en teca y crema, hasta <strong>9 invitados</strong>. El "Fufi" que ves en nuestras fotos. Ideal para parejas y grupos hasta 8 que buscan un toque mediterráneo local.</li>
<li><strong><a href="/boats/azimut-39/">Azimut 39</a></strong> — flybridge italiano, líneas modernas, hasta <strong>11 invitados</strong>. La opción para grupos más grandes (9+) o quien quiera disfrutar de la cubierta superior con tumbonas al sol.</li>
</ul>

<h2>Salidas desde Puerto Banús</h2>
<p>Toda nuestra flota atraca en <strong>Puerto Banús</strong> — el puerto más profundo y emblemático de la Costa del Sol. Te enviamos el número de pantalán y amarre 24 horas antes. Aparcamiento subterráneo a 5 minutos del muelle. Para más detalle, consulta nuestra <a href="/boats/">guía de la flota</a>.</p>

<h2>Qué incluye cada alquiler</h2>
<ul>
<li>Patrón con titulación profesional para toda la duración</li>
<li>Bebidas a bordo: agua, refrescos, cerveza, vino blanco y cava</li>
<li>Snacks ligeros (fruta, patatas, almendras, galletas)</li>
<li>Combustible para la ruta costera estándar</li>
<li>Seguro y equipo de seguridad completo (chalecos, bengalas, botiquín)</li>
<li>IVA español (21%) — sin sorpresas al pagar</li>
<li>Equipo de snorkel y juguetes inflables (donut, paddleboard)</li>
</ul>
<p>Comida cocinada, bebidas premium, DJ y tender a chiringuito son extras que puedes añadir al reservar.</p>

<h2>Reserva en 60 segundos</h2>
<p>Escríbenos por WhatsApp con tu fecha, número de invitados y presupuesto aproximado. Te respondemos con cotización al momento, sin compromiso. Pago del 30% al reservar, 70% el día de la salida. Cancelación gratuita hasta 7 días antes. Cancelación por mal tiempo siempre con reembolso del 100%.</p>

<h2>Preguntas frecuentes</h2>
<details><summary>¿Cuánto cuesta alquilar un barco en Marbella?</summary><p>El alquiler de barcos en Marbella en nuestra flota arranca en €749 por 2 horas y llega hasta €2.299 por un día completo de 8 horas. Mismo precio en cualquier temporada. Cada alquiler incluye patrón con titulación, combustible, bebidas, seguro e IVA. Para grupos grandes (11 invitados en el Azimut 39), el coste por persona baja a unos €70 para 2 horas.</p></details>
<details><summary>¿Dónde sale el barco?</summary><p>Toda nuestra flota sale desde Puerto Banús — el puerto deportivo más profundo de Marbella y con la mayor concentración de yates de la Costa del Sol. Te enviamos el número de pantalán y amarre 24 horas antes de la salida.</p></details>
<details><summary>¿Necesito licencia náutica?</summary><p>No. Nuestros barcos llevan patrón con titulación profesional incluido. Tú y tus invitados sois pasajeros — no necesitas certificación ninguna, solo DNI o pasaporte para subir a bordo.</p></details>
<details><summary>¿Qué pasa si hace mal tiempo?</summary><p>El patrón confirma la noche anterior. Si el viento previsto supera la fuerza 4-5 (~20+ nudos) o el estado del mar hace el viaje incómodo, se reprograma sin coste o se hace reembolso del 100%. Lluvia ligera por sí sola no es motivo de cancelación en la Costa del Sol.</p></details>
'''

def body_yates():
    return '''<p>El alquiler de yates en Marbella significa subir a uno de nuestros yates a motor de 12,5 metros con flybridge, conducido por un patrón profesional desde Puerto Banús. Patrón, combustible, bebidas (cerveza, vino blanco, cava), seguro e IVA incluidos. <strong>Desde €749 por 2 horas.</strong></p>

<h2>Nuestros yates a motor</h2>
<ul>
<li><a href="/boats/azimut-39/"><strong>Azimut 39</strong></a> — yate italiano con flybridge, 12,5 m, hasta 11 invitados. Líneas modernas, dos cubiertas, segundo puesto de mando arriba.</li>
<li><a href="/boats/astondoa-40/"><strong>Astondoa 40</strong></a> — yate español clásico, 12,5 m, hasta 9 invitados. Interior en teca y crema. El "Fufi" del muelle de Puerto Banús.</li>
<li><a href="/boats/mangusta-80/"><strong>Mangusta 80</strong></a> — la nave insignia de la flota. 24 m italianos con moto de agua incluida y patrón + tripulación. Desde €4.719 por 4 horas. Charter de lujo.</li>
</ul>

<h2>Precios por hora</h2>
<table>
<thead><tr><th>Duración</th><th>Astondoa 40 / Azimut 39</th><th>Mangusta 80 (mínimo 4h)</th></tr></thead>
<tbody>
<tr><td>2 h</td><td><strong>€749</strong></td><td>—</td></tr>
<tr><td>4 h</td><td>€1.299</td><td><strong>€4.719</strong></td></tr>
<tr><td>6 h</td><td>€1.799</td><td>€6.500+</td></tr>
<tr><td>8 h</td><td><strong>€2.299</strong></td><td>€9.000+</td></tr>
</tbody>
</table>
<p>Todos los precios incluyen patrón, combustible, bebidas, snacks, seguro e IVA. Para el detalle del Mangusta 80 (24 m con moto de agua), consulta su <a href="/boats/mangusta-80/">página específica</a>.</p>

<h2>Itinerario típico de medio día</h2>
<ol>
<li><strong>11:00</strong> Embarque en Puerto Banús, bebida de bienvenida.</li>
<li><strong>11:30</strong> Salimos rumbo oeste por la Milla de Oro.</li>
<li><strong>12:30</strong> Fondeamos en Cala del Faro o Río Verde para baño y snorkel.</li>
<li><strong>14:00</strong> Comida a bordo (BYO o catering opcional).</li>
<li><strong>15:00</strong> Regreso a Puerto Banús con vistas a La Concha.</li>
</ol>

<h2>Qué incluye</h2>
<ul>
<li>Patrón con titulación PER o superior</li>
<li>Combustible para la ruta costera estándar</li>
<li>Bebidas: agua, refrescos, cerveza, vino blanco y cava</li>
<li>Snacks ligeros</li>
<li>Snorkel, donut hinchable, paddleboard</li>
<li>Toallas para cada invitado</li>
<li>Seguro a terceros y daños propios</li>
<li>IVA español 21%</li>
</ul>

<h2>Cómo reservar</h2>
<p>Mándanos un WhatsApp con fecha, número de invitados y preferencia de barco. Respondemos en menos de 5 minutos con cotización exacta y disponibilidad. Sin coste hasta que confirmas — depósito del 30% al reservar, resto el día de la salida.</p>

<h2>Preguntas frecuentes</h2>
<details><summary>¿Cuánto cuesta alquilar un yate en Marbella?</summary><p>El alquiler de yates en Marbella en nuestra flota arranca en €749 por 2 horas en el Astondoa 40 o Azimut 39 (12,5 m, hasta 11 invitados). Un día completo de 8 horas cuesta €2.299. Para el Mangusta 80 (24 m de lujo, con moto de agua), desde €4.719 por 4 horas.</p></details>
<details><summary>¿Necesito licencia para alquilar?</summary><p>No. Todos nuestros yates van con patrón profesional incluido. Solo necesitas DNI o pasaporte para subir a bordo.</p></details>
<details><summary>¿Cuántos invitados puedo llevar?</summary><p>El Astondoa 40 admite hasta 9 invitados, el Azimut 39 hasta 11, y el Mangusta 80 hasta 12.</p></details>
<details><summary>¿Se puede pernoctar?</summary><p>Sí en yates de 12 m o más. El charter nocturno empieza en €1.200 y se cotiza por WhatsApp.</p></details>
'''

def body_banus():
    return '''<p>Puerto Banús es la marina más emblemática de la Costa del Sol y la base de nuestra flota. Salimos desde aquí cada día con yates a motor de 12,5 m (Astondoa 40 y Azimut 39) — desde <strong>€749 por 2 horas</strong>, patrón, bebidas, combustible y todo incluido.</p>

<h2>Por qué salir desde Puerto Banús</h2>
<p>Tres motivos prácticos:</p>
<ul>
<li><strong>Profundidad y tamaño.</strong> Puerto Banús tiene 915 amarres y la bocana más profunda de la zona — único puerto local capaz de acoger yates de más de 30 metros como nuestro Mangusta 80.</li>
<li><strong>Concentración de flota.</strong> Aquí amarran el 60% de los charters disponibles entre Estepona y Cabopino. Todos nuestros barcos están aquí.</li>
<li><strong>Infraestructura.</strong> Repostaje, agua, electricidad, chandlers, restaurantes a 5 minutos del pantalán — todo Marbella charter en un solo punto.</li>
</ul>

<h2>Dónde encontrar el barco</h2>
<p>Puerto Banús se organiza en 8 pantalanes paralelos numerados del 1 al 8 desde oeste a este. Nuestros yates atracan habitualmente en:</p>
<ul>
<li><strong>Pantalán 1</strong> — Mangusta 80 (superyate)</li>
<li><strong>Pantalanes 2-3</strong> — Astondoa 40 y Azimut 39 (yates de 12,5 m)</li>
</ul>
<p>Te enviamos el pantalán y amarre exacto 24 horas antes. Llega 15 minutos antes — los charters mediterráneos salen puntuales.</p>

<h2>Aparcamiento y logística</h2>
<p><strong>Aparcamiento Puerto Banús</strong> (subterráneo, 1.200 plazas) — €2/hora, €18/día. Se llena los sábados de verano a partir de las 11:00, así que llega 30 minutos antes. El aparcamiento gratuito en la calle al oeste de la marina nunca funciona en julio-agosto.</p>
<p><strong>Comida antes de embarcar:</strong> Antonio's Beach Club (tapas), Picasso (cocina española, servicio rápido), o un bocadillo del SuperSol en Calle Ribera.</p>

<h2>Precios por hora desde Puerto Banús</h2>
<table>
<thead><tr><th>Duración</th><th>Astondoa 40 / Azimut 39</th></tr></thead>
<tbody>
<tr><td>2 horas</td><td><strong>€749</strong></td></tr>
<tr><td>4 horas</td><td>€1.299</td></tr>
<tr><td>6 horas</td><td>€1.799</td></tr>
<tr><td>8 horas</td><td><strong>€2.299</strong></td></tr>
</tbody>
</table>
<p>Mangusta 80 (mínimo 4h): desde €4.719. Ver <a href="/boats/mangusta-80/">página del barco</a>.</p>

<h2>Itinerarios típicos desde Puerto Banús</h2>
<p><strong>Oeste:</strong> Estepona, fondeo en Cala del Faro para baño, regreso al atardecer.</p>
<p><strong>Este:</strong> Milla de Oro, baño en Río Verde, parada en Cabopino para comida.</p>
<p><strong>Atardecer 2h:</strong> Lento por la Milla de Oro, fondeo breve frente a Nikki Beach, regreso con el sol cayendo tras La Concha.</p>

<h2>Preguntas frecuentes</h2>
<details><summary>¿Cuánto cuesta alquilar un barco en Puerto Banús?</summary><p>Desde €749 por 2 horas en nuestro Astondoa 40 o Azimut 39, hasta €2.299 por un día completo. Todo incluido: patrón, combustible, bebidas, IVA.</p></details>
<details><summary>¿Dónde aparco?</summary><p>Aparcamiento subterráneo Puerto Banús (€2/hora, €18/día). Llega 30 minutos antes en verano.</p></details>
<details><summary>¿Se puede dormir a bordo?</summary><p>Sí en barcos de 12 m o más. Charter nocturno desde €1.200, se cotiza por WhatsApp.</p></details>
'''

def body_sin_licencia():
    return '''<p>El truco más rápido: <strong>no necesitas licencia náutica</strong> para alquilar un barco en Marbella si reservas uno de nuestros yates con patrón profesional incluido. Desde <strong>€749 por 2 horas</strong>, todo cubierto: patrón, combustible, bebidas, seguro, IVA.</p>

<h2>Las dos opciones reales en Marbella</h2>
<h3>1. Reserva con patrón (lo que hacemos nosotros)</h3>
<p>El patrón conduce el barco. Tú y tus invitados sois pasajeros, así que <strong>no necesitas licencia náutica</strong>. Sólo necesitas DNI o pasaporte. Desde €749/2h en nuestra flota (<a href="/boats/astondoa-40/">Astondoa 40</a> o <a href="/boats/azimut-39/">Azimut 39</a>) — el 95% de los alquileres en Marbella funcionan así.</p>

<h3>2. Pequeña embarcación sin titulación (5 m / 15 cv)</h3>
<p>La ley española permite conducir embarcaciones de hasta 5 metros con motor de hasta 15 cv sin licencia, dentro de 2 millas náuticas de la costa, en horario diurno y con conductor mayor de 18 años. Hay operadores que alquilan estos barcos en Cabopino, pero <strong>nosotros no operamos esta categoría</strong> — preferimos garantizar la experiencia con patrón.</p>

<h2>Por qué pagar el patrón vale la pena</h2>
<ul>
<li><strong>Cero papeleo:</strong> sólo subes a bordo y disfrutas.</li>
<li><strong>Conoce la costa:</strong> nuestros patrones saben dónde está el agua más calmada, los mejores fondeos, los chiringuitos donde se puede atracar.</li>
<li><strong>Maniobras complicadas:</strong> entrar a Puerto Banús un sábado de agosto no es trivial. El patrón lo resuelve.</li>
<li><strong>Más diversión, menos estrés:</strong> tú con cava en la mano, no con el manual del barco.</li>
</ul>

<h2>Reglas de embarcaciones sin licencia en España</h2>
<p>Si prefieres conducir tú mismo, las reglas estatales son:</p>
<ul>
<li>Eslora máxima del casco: <strong>5 metros</strong> (motor) o 6 m (vela)</li>
<li>Potencia máxima del motor: <strong>15 caballos</strong></li>
<li>Distancia máxima desde costa: <strong>2 millas náuticas</strong></li>
<li>Sólo horario diurno (hasta la puesta de sol)</li>
<li>Conductor con 18 años cumplidos y DNI/pasaporte</li>
<li>Sin sobrepasar el límite de alcohol en sangre del conducir</li>
</ul>

<h2>Qué incluye nuestro alquiler con patrón</h2>
<ul>
<li>Patrón con titulación PER (Patrón de Embarcaciones de Recreo) o superior</li>
<li>Combustible para la ruta costera estándar</li>
<li>Bebidas: agua, refrescos, cerveza, vino blanco y cava</li>
<li>Snacks ligeros</li>
<li>Snorkel, donut hinchable, paddleboard, toallas</li>
<li>Seguro completo a terceros y daños propios</li>
<li>IVA español (21%) — sin sorpresas en el muelle</li>
</ul>

<h2>Precios</h2>
<table>
<thead><tr><th>Duración</th><th>Yate con patrón</th></tr></thead>
<tbody>
<tr><td>2 horas</td><td><strong>€749</strong></td></tr>
<tr><td>4 horas</td><td>€1.299</td></tr>
<tr><td>6 horas</td><td>€1.799</td></tr>
<tr><td>8 horas</td><td><strong>€2.299</strong></td></tr>
</tbody>
</table>

<h2>Preguntas frecuentes</h2>
<details><summary>¿De verdad puedo alquilar un barco sin licencia en Marbella?</summary><p>Sí — con dos opciones. Reserva un yate con patrón profesional (nuestra flota, desde €749/2h) y eres pasajero, sin ningún requisito de licencia. O alquila una embarcación pequeña (hasta 5 m / 15 cv) en operadores especializados, sin titulación pero con limitaciones (2 NM de costa, sólo de día).</p></details>
<details><summary>¿Hace falta saber navegar?</summary><p>No con nuestros barcos — el patrón conduce. Sólo te sientas, disfrutas y das instrucciones del tipo "un baño más antes de volver".</p></details>
<details><summary>¿Cuántos puedo llevar?</summary><p>Astondoa 40 hasta 9 invitados, Azimut 39 hasta 11, Mangusta 80 hasta 12.</p></details>
<details><summary>¿Puedo conducir un rato?</summary><p>Sí, durante tramos seguros y bajo supervisión del patrón. Es una práctica habitual y los patrones suelen estar encantados de que pruebes el timón.</p></details>
'''

BODY_MAP = {"hub": body_hub, "yates": body_yates, "banus": body_banus, "sin_licencia": body_sin_licencia}

def render_es(slug, key, title, meta, h1, sub, eyebrow, body, en_alt):
    url = f"{SITE['base_url']}/es/{slug + '/' if slug else ''}"
    en_url = SITE['base_url'] + en_alt
    hero_src, hero_srcset_list, hero_alt = hero_local(key)
    hero_srcset = ", ".join(hero_srcset_list)
    body_html = body or BODY_MAP[key]()

    # Breadcrumbs
    breadcrumbs = '<nav class="breadcrumbs"><a href="/es/">Inicio</a>' + (f' › <span>{html.escape(h1)}</span>' if slug else '') + '</nav>'

    # JSON-LD
    jsonld = [jsonld_org(), {
        "@context":"https://schema.org","@type":"WebPage",
        "name": title, "url": url, "inLanguage":"es",
        "isPartOf":{"@id":SITE['base_url']+"/#org"},
    }, {
        "@context":"https://schema.org","@type":"BreadcrumbList",
        "itemListElement":[
            {"@type":"ListItem","position":1,"name":"Inicio","item":SITE['base_url']+"/es/"},
        ] + ([{"@type":"ListItem","position":2,"name":h1,"item":url}] if slug else []),
    }]

    repl = {
        "{{HREFLANG}}": "",  # injected below as hreflang block
        "{{HERO_IMG}}": hero_src,
        "{{HERO_SRCSET}}": html.escape(hero_srcset),
        "{{HERO_ALT}}": html.escape(hero_alt),
        "{{HERO_EYEBROW}}": f'<span class="eyebrow">{html.escape(eyebrow)}</span>',
        "{{HERO_H1}}": html.escape(h1),
        "{{HERO_SUB}}": html.escape(sub),
        "{{TITLE}}": html.escape(title),
        "{{META_DESCRIPTION}}": html.escape(meta),
        "{{CANONICAL_URL}}": url,
        "{{OG_TYPE}}": "website",
        "{{CSS_HREF}}": "/styles.css",
        "{{JSONLD}}": json.dumps(jsonld, ensure_ascii=False),
        "{{PRICE_LOW}}": str(SITE['price_anchor_low_2h']),
        "{{PRICE_LABEL}}": "2h con patrón",
        "{{BOOK_PITCH}}": "Cotización al instante desde Puerto Banús, Marbella Marina, Cabopino, Estepona y Sotogrande.",
        "{{BOAT_GRID}}": "",
        "{{BREADCRUMBS}}": breadcrumbs,
        "{{BODY_HTML}}": body_html,
        "{{VIDEO_SECTION}}": "",
        "{{GUESTS_SECTION}}": "",
        "{{WHATSAPP_E164_NOPLUS}}": SITE['whatsapp_e164'].lstrip("+"),
        "{{PHONE_E164}}": SITE['phone_e164'],
        "{{PHONE_DISPLAY}}": SITE['phone_display'],
        "{{EMAIL}}": SITE['email'],
        "{{AFFILIATE_LINK}}": SITE['affiliate_link'],
        "{{INSTAGRAM_URL}}": SITE.get('instagram_url',''),
        "{{INSTAGRAM_HANDLE}}": SITE.get('instagram_handle',''),
        "{{FACEBOOK_URL}}": SITE.get('facebook_url',''),
        "{{FACEBOOK_LABEL}}": SITE.get('facebook_label','Facebook'),
    }
    out = TEMPLATE
    for k, v in repl.items():
        out = out.replace(k, v)

    # Inject hreflang + change <html lang="en"> to "es"
    out = out.replace('<html lang="en">', '<html lang="es">')
    hreflang = (
        f'<link rel="alternate" hreflang="en" href="{en_url}">\n'
        f'<link rel="alternate" hreflang="es" href="{url}">\n'
        f'<link rel="alternate" hreflang="x-default" href="{en_url}">\n'
    )
    out = out.replace('<link rel="canonical"', hreflang + '<link rel="canonical"', 1)

    # Translate the visible chrome bits (header nav, footer, book-card, trust strip)
    NAV_REPLACE = {
        '>Our Fleet<':'>Nuestra flota<',
        '>Yachts<':'>Yates<',
        '>Catamarans<':'>Catamaranes<',
        '>Puerto Banús<':'>Puerto Banús<',
        '>Guide<':'>Guía<',
        'aria-label="Menu"':'aria-label="Menú"',
        'aria-label="Primary"':'aria-label="Principal"',
        'aria-label="Call us"':'aria-label="Llámanos"',
        '>WhatsApp<':'>WhatsApp<',
        'Book on WhatsApp':'Reservar por WhatsApp',
        'See boats':'Ver barcos',
        'Skipper, fuel &amp; VAT included':'Patrón, combustible e IVA incluidos',
        'Beer, white wine &amp; cava on board':'Cerveza, vino blanco y cava a bordo',
        'WhatsApp reply in &lt;5 min':'Respuesta WhatsApp en &lt;5 min',
        'Year-round on the Costa del Sol':'Todo el año en la Costa del Sol',
        '2h skippered':'2h con patrón',
        'From <strong>':'Desde <strong>',
        'All charters include':'Todo alquiler incluye',
        'Licensed skipper &amp; fuel':'Patrón con titulación y combustible',
        'Drinks: water, soft drinks, beer, white wine, cava':'Bebidas: agua, refrescos, cerveza, vino blanco, cava',
        'Light snacks':'Snacks ligeros',
        'Insurance &amp; safety equipment':'Seguro y equipo de seguridad',
        'Snorkel gear &amp; inflatables':'Snorkel e inflables',
        'VAT 21% — no surprises':'IVA 21% — sin sorpresas',
        '💬 Message on WhatsApp':'💬 Escribir por WhatsApp',
        'Avg reply &lt; 5 min · No deposit until you confirm':'Respuesta media &lt;5 min · Sin pago hasta confirmar',
        '📞 Call ':'📞 Llamar ',
        'Browse 60+ boats on Click&amp;Boat':'Explorar 60+ barcos en Click&amp;Boat',
        '>Boats<':'>Barcos<',
        'Our fleet':'Nuestra flota',
        'Yacht charter':'Alquiler de yates',
        'Catamaran rental':'Alquiler de catamaranes',
        'Fishing boats':'Barcos de pesca',
        'Luxury yachts':'Yates de lujo',
        'No-license boats':'Barcos sin licencia',
        'Jet ski rental':'Alquiler de moto de agua',
        '>Ports &amp; trips<':'>Puertos y rutas<',
        'Sunset cruises':'Crucero al atardecer',
        'Boat parties':'Fiestas en barco',
        '>Guides<':'>Guías<',
        'Pricing 2026':'Precios 2026',
        'License rules':'Normativa de licencia',
        'Best month':'Mejor mes',
        'Which port?':'¿Qué puerto?',
        'Gibraltar by boat':'Gibraltar en barco',
        '>Contact<':'>Contacto<',
        'Independent local guide to renting boats, yachts and catamarans on the Costa del Sol.':
            'Guía local independiente para el alquiler de barcos, yates y catamaranes en la Costa del Sol.',
        '© 2026 Boat Rental Marbella. Independent affiliate guide — links to operators may pay commission. <a href="/">Home</a>':
            '© 2026 Boat Rental Marbella. <a href="/es/">Inicio</a>',
        '💬 Book on WhatsApp':'💬 Reservar por WhatsApp',
        '/blog/how-much-does-it-cost-to-rent-a-boat-in-marbella/':'/blog/how-much-does-it-cost-to-rent-a-boat-in-marbella/',
    }
    for en_s, es_s in NAV_REPLACE.items():
        out = out.replace(en_s, es_s)

    return out, url

def main():
    es_root = SITE_DIR / "es"
    es_root.mkdir(parents=True, exist_ok=True)
    for slug, key, title, meta, h1, sub, eyebrow, body, en_alt in PAGES:
        html_out, url = render_es(slug, key, title, meta, h1, sub, eyebrow, body, en_alt)
        out_dir = es_root / slug if slug else es_root
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(html_out)
        print(f"  ✓ es/{slug or '(hub)'} → {url}")

if __name__ == "__main__":
    main()
