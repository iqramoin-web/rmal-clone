"""Apply the Nov 2026 client feedback (RMAL_Website_Feedback_and_Action_Plan.pdf)
to the static mirror.

Reads the untouched mirror from _tools/orig-en and _tools/orig-ar and writes the
revised pages to en/ and ar/, so it can be re-run safely.

    python3 _tools/transform.py      (needs beautifulsoup4)

The Next.js runtime is removed on purpose: it drove the intro loader, the fade-ins
and the sticky "page flip" heroes the client asked to remove. rx/rx.js replaces the
few interactions that are still needed (header, menu, hero video → carousel).
"""
import copy
import re
import shutil
import urllib.parse
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString

ROOT = Path(__file__).resolve().parent.parent
MEDIA = "/api/media/file/"

T = {
    "en": {
        "gov": "Leadership & Governance",
        "gov_old": ["Sustainability & ESG"],
        "gov_eyebrow": "Board & Sustainability",
        "board_eyebrow": "The RMAL Board",
        "home": "Home",
        "contact": "Contact",
        "learn": "Learn more",
        "sound_on": "Sound on",
        "brands_intro": "From dining to fast casual, we bring world-class brands to the UAE and build our own from here. Each one is run by a team that knows how to turn great food into moments people come back for.",
        "feature": ("Our Brands", "World-class brands, and our own, made here.",
                    "From dining to fast casual: Wagamama, Trader Vic’s, Mazaj, Cupbop and Marco Pierre White.",
                    "Discover our brands"),
        "visit": "Visit website",
    },
    "ar": {
        "gov": "القيادة والحوكمة",
        "gov_old": ["الاستدامة والمسؤولية المؤسسية", "الاستدامة والحوكمة (ESG)", "الاستدامة والحوكمة"],
        "gov_eyebrow": "مجلس الإدارة والاستدامة",
        "board_eyebrow": "مجلس إدارة رمال",
        "home": "الرئيسية",
        "contact": "تواصل معنا",
        "learn": "اعرف المزيد",
        "sound_on": "تشغيل الصوت",
        "brands_intro": "من المطاعم إلى الوجبات السريعة غير الرسمية، نجلب إلى الإمارات علامات تجارية عالمية المستوى ونبني علاماتنا الخاصة من هنا. ويدير كل منها فريق يعرف كيف يحوّل الطعام الرائع إلى لحظات يعود إليها الناس.",
        "feature": ("علاماتنا التجارية", "علامات عالمية، وأخرى نصنعها هنا.",
                    "من المطاعم إلى الوجبات السريعة غير الرسمية: واغاماما، تريدر فيكس، مزاج، كب بوب وماركو بيير وايت.",
                    "اكتشف علاماتنا"),
        "visit": "زيارة الموقع",
    },
}

BRAND_LOGOS = {
    "wagamama": ("wagamama.png", ""),
    "trader-vics": ("Layer_1(2).svg", "rx-logo-tv"),
    "mazaj": ("mazaj.png", ""),
    "cupbop": ("cupbop.png", ""),
    "marco-pierre-white": ("marco-pierre-white.png", ""),
}

# Client-supplied navy logos (logos/) for the homepage strip: key, file, name
STRIP_LOGOS = [
    ("wagamama", "wagamama.png", "Wagamama"),
    ("mazaj", "mazaj.png", "Mazaj"),
    ("marco-pierre-white", "marco-pierre-white.png", "Marco Pierre White"),
    ("cupbop", "cupbop.png", "Cupbop"),
    ("drvn-coffee", "drvn-coffee.svg", "DRVN Coffee"),
]

# Service pillar photos. Franchise uses the full storefront so the Wagamama sign is not cut.
PILLAR_IMG = {
    "franchise-brand-operations": ("Global brand operations.jpg", "50% 15%"),
    "owned-homegrown-brands": ("Owned-and-homegrown-brands-1.jpg", "50% 40%"),
    "managed-services-advisory": ("pillar-4.png", "50% 50%"),  # placeholder until client photo
}

ANIM_PROPS = {"opacity", "transform", "clip-path", "filter", "mask-image", "-webkit-mask-image", "will-change"}


def media(name):
    return MEDIA + urllib.parse.quote(name, safe="()")


def classes(el):
    return el.get("class", []) if el and el.name else []


def swap_class(el, old, new):
    c = [x for x in classes(el) if x not in old]
    if new:
        c += new.split()
    el["class"] = c


def tag(soup, html):
    return BeautifulSoup(html, "html.parser").find()


def text_of(el):
    return " ".join(el.get_text(" ", strip=True).split()) if el else ""


# ------------------------------------------------------------------ global
def strip_runtime(soup):
    for s in soup.find_all("script"):
        if s.get("type") != "application/ld+json":
            s.decompose()
    for l in soup.find_all("link"):
        if l.get("as") == "script" or "modulepreload" in (l.get("rel") or []):
            l.decompose()
    loader = soup.select_one(".site-loader")
    if loader:
        loader.decompose()


def strip_entrance_styles(soup):
    for el in soup.find_all(style=True):
        keep = []
        for decl in el["style"].split(";"):
            if ":" not in decl:
                continue
            k = decl.split(":", 1)[0].strip().lower()
            if k not in ANIM_PROPS:
                keep.append(decl.strip())
        if keep:
            el["style"] = ";".join(keep)
        else:
            del el["style"]


def unstick(soup):
    # Sticky heroes created the layered "page flip" effect while scrolling.
    for el in soup.select(".sticky.top-0"):
        swap_class(el, {"sticky", "top-0", "z-0"}, "relative")


def remove_patterns(soup):
    for img in soup.find_all("img", src=True):
        if "/patterns/" in img["src"] or "/pillars/pattern" in img["src"]:
            parent = img.parent
            img.decompose()
            if parent and parent.name == "div" and not parent.find(True) and not text_of(parent):
                parent.decompose()


def rename_gov(soup, t):
    for node in soup.find_all(string=True):
        s = str(node).strip()
        if s in t["gov_old"]:
            node.replace_with(NavigableString(str(node).replace(s, t["gov"])))


def square_body_images(soup):
    for el in soup.find_all(class_=True):
        c = classes(el)
        new = []
        for x in c:
            m = re.fullmatch(r"aspect-\[(\d+)/(\d+)\]", x)
            if m and int(m.group(1)) < int(m.group(2)):  # portrait → square
                x = "aspect-square"
            new.append(x)
        el["class"] = new
    # decorative drop-shadow "frames" behind body images
    for el in soup.find_all(class_=lambda c: c and c.startswith("shadow-[")):
        if el.name == "div" and not el.find(True):
            el.decompose()


def restyle_ctas(soup):
    header = soup.find("header")
    for el in soup.find_all(["a", "span", "button"], class_=True):
        c = classes(el)
        if "inline-flex" in c and "border-solid" in c and "border" in c:
            is_pill = header is not None and el in header.find_all(el.name)
            for fill in el.find_all("span", class_="scale-x-0"):
                fill.decompose()
            el["class"] = [x for x in c if not re.match(r"^(border|px-|py-|hover:bg|hover:text|overflow-hidden)", x)]
            el["class"].append("rx-cta-pill" if is_pill else "rx-cta")
    for node in soup.find_all(string=re.compile("↗")):
        node.replace_with(NavigableString(str(node).replace("↗", "→")))


def frameless_cards(soup):
    # Board cards: drop the pseudo-element frame classes.
    for el in soup.find_all(class_="after:inset-0"):
        el["class"] = [x for x in classes(el) if not x.startswith("after:")]
    for el in soup.find_all(class_="h-[360px]"):
        swap_class(el, {"h-[360px]"}, "aspect-square")


def media_controls(soup, is_home):
    for v in soup.find_all("video"):
        if is_home and v.find_parent("section") and v.find_parent("section").find_previous("section") is None:
            continue
        v["controls"] = ""
        if v.has_attr("autoplay") and not is_home:
            del v["autoplay"]
    # React-driven play overlay buttons no longer do anything
    for b in soup.find_all("button", class_="backdrop-blur-[2px]"):
        b.decompose()


def drop_cookie_button(soup):
    for b in soup.find_all("button"):
        if text_of(b).lower() in ("cookie settings", "إعدادات ملفات تعريف الارتباط"):
            b.decompose()


def header_and_menu(soup, lang, t, solid):
    header = soup.find("header")
    if not header:
        return
    header["id"] = "rx-header"
    if solid:
        header["class"] = classes(header) + ["rx-solid"]
        header["data-solid"] = "1"
    header["class"] = classes(header) + ["rx-jhead"]
    nav = header.find("nav")
    logo = nav.find("a") if nav else None
    if logo:
        logo["class"] = classes(logo) + ["rx-logo"]
    btn = header.find("button")
    if btn and nav:
        nav.insert(0, btn.extract())  # menu button sits left of the centred logo
    if btn:
        btn["id"] = "rx-menu-btn"
        btn["aria-label"] = "Menu"
        btn["aria-expanded"] = "false"
    links = [(f"/{lang}", t["home"])]
    ul = header.find("ul")
    for a in (ul.find_all("a") if ul else []):
        links.append((a["href"], text_of(a)))
    links.append((f"/{lang}/contact", t["contact"]))
    other = "ar" if lang == "en" else "en"
    items = "".join(f'<a href="{h}">{x}</a>' for h, x in links)
    panel = tag(soup, f"""<div id="rx-menu" role="dialog" aria-label="Menu">
  <div class="rx-menu-top"><img src="/logo-dark.svg" alt="RMAL Hospitality" width="106" height="42">
  <button id="rx-menu-close" aria-label="Close">×</button></div>
  <nav>{items}</nav>
  <div class="rx-menu-foot"><a class="rx-lang" href="/{other}">{"عربي" if other == "ar" else "English"}</a>
  <span>+971 4395 0101</span></div>
</div>""")
    header.insert_after(panel)


def add_assets(soup):
    soup.head.append(tag(soup, '<link rel="stylesheet" href="/rx/rx.css">'))
    soup.body.append(tag(soup, '<script src="/rx/rx.js" defer></script>'))


# ------------------------------------------------------------------ pages
def page_head_from_hero(soup, lang):
    """Careers / Newsroom: no banner — start with the title."""
    hero = soup.find("section", id="hero")
    if not hero:
        return
    eyebrow = text_of(hero.find("p"))
    title = text_of(hero.find("h1"))
    if lang == "en" and title.endswith("With"):
        title += " RMAL"
    hero.replace_with(tag(soup, f"""<section class="rx-pagehead"><div class="mx-auto max-w-[1400px] px-4">
  <p class="font-body text-eyebrow font-semibold uppercase text-tertiary-500">{eyebrow}</p>
  <h1 class="font-heading text-primary-900">{title}</h1></div></section>"""))


def compact_banner(soup):
    hero = soup.find("section", id="hero")
    if hero:
        hero["class"] = [x for x in classes(hero) if not re.match(r"^(md:)?h-\[", x)] + ["rx-banner"]


def pillar_card(href, title, sub, desc, learn):
    key = href.rstrip("/").split("/")[-1]
    img, pos = PILLAR_IMG.get(key, ("pillar-4.png", "50% 50%"))
    d = f'<p class="rx-pcard-desc">{desc}</p>' if desc else ""
    return f"""<li class="rx-pcard">
  <a class="rx-pcard-ph" href="{href}"><img src="{media(img)}" alt="" loading="lazy" style="object-position:{pos}"><h3>{title}</h3></a>
  <p class="rx-pcard-sub">{sub}</p>{d}
  <a class="rx-link" href="{href}">{learn} →</a>
</li>"""


def rebuild_pillars(soup, ul, t, with_desc):
    cards = []
    for li in ul.find_all("li", recursive=False):
        a = li.find("a")
        h3 = a.find("h3")
        ps = [p for p in a.find_all("p") if text_of(p)]
        learn = next((text_of(s) for s in a.find_all("span") if text_of(s) and "→" not in text_of(s) and len(text_of(s)) < 30), t["learn"])
        learn = learn.capitalize() if learn.isupper() else learn
        cards.append(pillar_card(a["href"], text_of(h3), text_of(ps[0]) if ps else "",
                                 text_of(ps[1]) if with_desc and len(ps) > 1 else "", learn))
    ul.clear()
    ul["class"] = ["rx-pcards"]
    for c in cards:
        ul.append(tag(soup, c))


HOME = {
    "en": {
        "intro_eyebrow": "RMAL Hospitality PJSC",
        "brands": ("Our Brands", "A Growing Portfolio", "Explore our brands"),
        "careers": ("Careers", "Build Your Career",
                    "Learning and development, exposure to different brands and functions, and opportunities to take on new challenges are all part of building a career with us.",
                    "Join RMAL"),
        "contact": ("Start a Conversation",
                    "Whether you’re exploring an F&B opportunity, interested in our managed services, looking to join our team or simply want to get in touch, we’d be happy to hear from you.",
                    "Contact us"),
    },
    "ar": {
        "intro_eyebrow": "رمال للضيافة",
        "brands": ("علاماتنا التجارية", "محفظة متنامية", "استكشف علاماتنا"),
        "careers": ("الوظائف", "ابنِ مسيرتك المهنية",
                    "التعلّم والتطوير، والتعرّف على علامات تجارية ووظائف متنوعة، وفرص خوض تحديات جديدة؛ كلها جزء من بناء مسيرتك المهنية معنا.",
                    "انضم إلى رمال"),
        "contact": ("ابدأ محادثة",
                    "سواء كنت تستكشف فرصة في قطاع الأغذية والمشروبات، أو مهتماً بخدماتنا الإدارية، أو ترغب في الانضمام إلى فريقنا، يسعدنا أن نسمع منك.",
                    "تواصل معنا"),
    },
}


def centre_head(section):
    """Centred section title with a short rule underneath."""
    h2 = section.find("h2") if section else None
    head = h2.find_parent("div") if h2 else None
    if head:
        head["class"] = classes(head) + ["rx-chead"]
        wrap = head.find_parent("div")
        if wrap and wrap.find("a", class_="rx-cta"):
            wrap["class"] = classes(wrap) + ["rx-chead-wrap"]


def do_home(soup, lang, t):
    h = HOME[lang]
    soup.body["class"] = classes(soup.body) + ["rx-home"]
    main = soup.find("main")
    hero = main.find("section")
    video = hero.find("video")

    # The old hero copy becomes the centred intro under the logo strip.
    h1 = hero.find("h1")
    lines = [text_of(x) for x in h1.find_all("span", recursive=False) if text_of(x)] or [text_of(h1)]
    hero_p = text_of(h1.find_next("p"))
    cta = next((text_of(x).replace("→", "").strip() for x in hero.find_all("a")), "Discover RMAL")
    if cta.isupper():
        w = cta.split()
        cta = " ".join([w[0].capitalize()] + [x if x == "RMAL" else x.lower() for x in w[1:]])

    for div in hero.find_all("div", recursive=False):
        if not div.find("video"):
            div.decompose()
    if video.has_attr("loop"):
        del video["loop"]
    video["id"] = "rx-hero-video"
    video["preload"] = "auto"
    hero["class"] = [x for x in classes(hero) if not x.startswith(("h-[", "min-h-["))] + ["rx-hero", "rx-jhero"]
    slides = "".join(f'<img class="rx-slide" src="{media(f)}" alt="">' for f in ["hero-2.jpg", "hero-5.jpg", "hero-4.jpg", "hero-1.jpg"])
    hero.append(tag(soup, f'<div class="rx-slides">{slides}</div>'))
    hero.append(tag(soup, '<div class="rx-dots"></div>'))
    hero.append(tag(soup, f'<button class="rx-sound" type="button">{t["sound_on"]}</button>'))
    hero.append(tag(soup, '<a class="rx-scroll" href="#rx-intro" aria-label="Scroll"><span></span></a>'))

    strip = soup.find("section", id="brand-strip")
    if strip:
        swap_class(strip, {"bg-cream"}, "rx-bg-white")
        # Continuous logo carousel. The set is repeated so the -50% loop never shows a gap.
        def logo_set(hidden):
            aria = ' aria-hidden="true" tabindex="-1"' if hidden else ""
            return "".join(
                f'<li><a href="/{lang}/brands{"#" + k if k in BRAND_LOGOS else ""}"{aria}>'
                f'<img class="logo-{k}" src="/logos/{f}" alt="{"" if hidden else name}"></a></li>'
                for k, f, name in STRIP_LOGOS
            )
        track = logo_set(False) + logo_set(True) * 3
        strip.clear()
        strip.append(tag(soup, f'<div class="rx-marquee"><ul class="rx-marquee-track">{track}</ul></div>'))

    intro = tag(soup, f"""<section class="rx-jintro" id="rx-intro"><div class="rx-jwrap">
  <p class="rx-jeyebrow">{h["intro_eyebrow"]}</p>
  <h1 class="rx-jtitle">{"<br>".join(lines)}</h1><span class="rx-rule"></span>
  <p class="rx-jtext">{hero_p}</p>
  <a class="rx-link" href="/{lang}/about">{cta} →</a>
</div></section>""")
    strip.insert_after(intro)

    wwd = soup.find("section", id="what-we-do")
    if wwd:
        rebuild_pillars(soup, wwd.find("ul"), t, with_desc=False)
        centre_head(wwd)

    # Full-bleed image, then a centred title block (brands)
    e, ttl, link = h["brands"]
    feature = tag(soup, f"""<section class="rx-jfeature">
  <a class="rx-jfeature-ph" href="/{lang}/brands"><img src="{media('wagamama.jpg')}" alt="" loading="lazy"></a>
  <div class="rx-jwrap rx-jfeature-in">
    <p class="rx-jeyebrow">{e}</p>
    <h2 class="rx-jtitle">{ttl}</h2><span class="rx-rule"></span>
    <p class="rx-jtext">{t["brands_intro"]}</p>
    <a class="rx-link" href="/{lang}/brands">{link} →</a>
  </div></section>""")
    (wwd or intro).insert_after(feature)

    # Alternating image/text blocks: Heritage, National Talent, Careers
    about = soup.find("section", id="about")
    talent = soup.find("section", id="talent")
    anchor = feature
    for sec, bg in ((about, "rx-bg-cream"), (talent, "rx-bg-warm")):
        if sec:
            swap_class(sec, {"bg-cream"}, bg)
            sec["class"] = classes(sec) + ["rx-jblock"]
            anchor.insert_after(sec.extract())
            anchor = sec
    ce, ct, cx, cl = h["careers"]
    careers = tag(soup, f"""<section class="rx-jblock rx-jsplit rx-bg-cream">
  <div class="rx-jwrap rx-jsplit-in">
    <a class="rx-jsplit-ph" href="/{lang}/careers"><img src="{media('Build yur career as we build the business.jpg')}" alt="" loading="lazy"></a>
    <div class="rx-jsplit-text"><p class="rx-jeyebrow">{ce}</p><h2 class="rx-jtitle">{ct}</h2>
      <p class="rx-jtext">{cx}</p><a class="rx-link" href="/{lang}/careers">{cl} →</a></div>
  </div></section>""")
    anchor.insert_after(careers)

    news = soup.find("section", id="newsroom")
    if news:
        swap_class(news, {"bg-cream"}, "rx-bg-white")
        news["class"] = classes(news) + ["rx-jnews"]
        careers.insert_after(news.extract())
        centre_head(news)
        ttl, txt, link = h["contact"]
        news.insert_after(tag(soup, f"""<section class="rx-jcontact"><div class="rx-jwrap">
  <h2 class="rx-jtitle">{ttl}</h2><span class="rx-rule"></span>
  <p class="rx-jtext">{txt}</p>
  <a class="rx-link" href="/{lang}/contact">{link} →</a>
</div></section>"""))


def do_what_we_do(soup, t):
    compact_banner(soup)
    svc = soup.find("section", id="services")
    if svc:
        rebuild_pillars(soup, svc.find("ul"), t, with_desc=True)


def do_brands(soup, lang, t):
    compact_banner(soup)
    main = soup.find("main")
    for nav in main.find_all("nav"):
        if nav.find("a", href=re.compile("^#")):
            nav.decompose()  # brand-name ribbon
    hero = soup.find("section", id="hero")
    hero.insert_after(tag(soup, f"""<section class="rx-brands-intro"><div class="mx-auto max-w-[1400px] px-4">
  <p>{t["brands_intro"]}</p></div></section>"""))
    for key, (logo, lcls) in BRAND_LOGOS.items():
        sec = soup.find("section", id=key)
        if not sec:
            continue
        img = sec.find("img")
        eyebrow = sec.find("p", class_=lambda c: c and "text-eyebrow" in c)
        h2 = sec.find("h2")
        body = h2.find_next_sibling("div") if h2 else None
        cta_wrap = body.find_next_sibling("div") if body else None
        if body:
            for p in body.find_all("p"):
                if not text_of(p):
                    p.decompose()
        name = text_of(h2)
        card = tag(soup, f"""<article class="rx-brand-card">
  <img class="rx-brand-logo {lcls}" src="{media(logo)}" alt="{name}">
  <img class="rx-brand-photo" src="{img['src']}" alt="{img.get('alt', '')}" loading="lazy" style="{img.get('style', '')}">
  <div class="rx-brand-text"><div class="rx-brand-title"></div><div class="rx-brand-body"></div></div>
</article>""")
        title = card.find("div", class_="rx-brand-title")
        bodybox = card.find("div", class_="rx-brand-body")
        for el in (eyebrow, h2):
            if el:
                title.append(el.extract())
        if body:
            bodybox.append(body.extract())
        if cta_wrap:
            bodybox.append(cta_wrap.extract())
        sec.clear()
        sec["class"] = ["rx-brand-sec"]
        wrap = tag(soup, '<div class="mx-auto max-w-[1400px] px-4"></div>')
        wrap.append(card)
        sec.append(wrap)


def do_gov(soup, lang, t, board_html):
    compact_banner(soup)
    hero = soup.find("section", id="hero")
    p = hero.find("p")
    if p:
        p.string = t["gov_eyebrow"]
    h1 = hero.find("h1")
    if h1:
        h1.clear()
        h1.string = t["gov"]
    if soup.title:
        soup.title.string = re.sub(r"^[^|]+", t["gov"] + " ", soup.title.string)
    resp = soup.find("section", id="responsible-operations")
    if board_html and resp:
        board = BeautifulSoup(board_html, "html.parser").find("section")
        board["id"] = "board"
        swap_class(board, {"bg-cream"}, "rx-bg-white")
        eb = board.find("p")
        if eb:
            eb.string = t["board_eyebrow"]
        resp.insert_before(board)


# ------------------------------------------------------------------ run
def process(lang):
    t = T[lang]
    src = ROOT / "_tools" / f"orig-{lang}"
    dst = ROOT / lang
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

    files = sorted(dst.rglob("index.html"))
    # About first: its Board section is reused on the governance page.
    about = dst / "about" / "index.html"
    files.sort(key=lambda p: p != about)
    board_html = None

    for f in files:
        rel = f.parent.relative_to(dst).as_posix()
        rel = "" if rel == "." else rel
        soup = BeautifulSoup(f.read_text(encoding="utf-8"), "html.parser")
        is_home = rel == ""

        strip_runtime(soup)
        strip_entrance_styles(soup)
        unstick(soup)
        remove_patterns(soup)
        rename_gov(soup, t)
        restyle_ctas(soup)
        square_body_images(soup)
        frameless_cards(soup)
        media_controls(soup, is_home)
        drop_cookie_button(soup)

        if is_home:
            do_home(soup, lang, t)
        elif rel == "what-we-do":
            do_what_we_do(soup, t)
        elif rel == "brands":
            do_brands(soup, lang, t)
        elif rel == "esg":
            do_gov(soup, lang, t, board_html)
        elif rel in ("careers", "news"):
            page_head_from_hero(soup, lang)
        elif rel == "about":
            sec = soup.find("section", id="leadership")
            board_html = str(sec) if sec else None

        dark_top = is_home or soup.find("section", id="hero") is not None
        header_and_menu(soup, lang, t, solid=not dark_top)
        add_assets(soup)
        f.write_text(str(soup), encoding="utf-8")
        print(lang, "/" + rel)


if __name__ == "__main__":
    process("en")
    process("ar")
