import tkinter as tk
from tkinter import ttk, messagebox
import os
import io
import json
import urllib.parse
import urllib.request

# Pillow is used only for automatic car/photo images.
# If Pillow is not installed, the app still runs with generated placeholders.
try:
    from PIL import Image, ImageTk, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# ============================================================
# BMW INDIA - DATA
# ============================================================

cars = {
    "SUV": [
        ("BMW X1", 50.09),
        ("BMW X3", 72.50),
        ("BMW X5", 95.40),
        ("BMW X7", 128)
    ],
    "Sedan": [
        ("BMW 3 Series", 60),
        ("BMW 5 Series", 68),
        ("BMW 7 Series", 170)
    ],
    "Sports": [
        ("BMW M4", 153),
        ("BMW M5", 175)
    ],
    "Electric": [
        ("BMW i4", 72),
        ("BMW iX", 120)
    ],
    "Coupe": [
        ("BMW 2 Series Coupe", 43),
        ("BMW 4 Series", 72)
    ]
}

colors = ["Black", "Blue", "White", "Red"]

accessories = {
    "No Accessories": 0,
    "Exhaust": 2,
    "Sports Kit": 3,
    "Turbo Kit": 10
}

cart = []
wishlist = []
order_history = []
username = ""
content_frame = None

# Automatic image cache. No manual image downloading is required.
IMAGE_DIR = os.path.join(os.path.expanduser("~"), ".bmw_india_gui", "images")
os.makedirs(IMAGE_DIR, exist_ok=True)
image_cache = {}
image_requests = {}


# ============================================================
# THEME
# ============================================================

BG = "#0b0d10"
PANEL = "#12161b"
CARD = "#181d23"
CARD_2 = "#20262e"
TEXT = "#f4f5f7"
MUTED = "#9da5af"
WHITE = "#ffffff"
BMW_BLUE = "#0879d1"
BMW_BLUE_2 = "#075ca0"
SUCCESS = "#28c76f"
DANGER = "#ef5350"
GOLD = "#d8b15a"

FONT = "Segoe UI"


# ============================================================
# AUTOMATIC IMAGE SYSTEM
# ============================================================

def safe_filename(text):
    return "".join(c if c.isalnum() else "_" for c in text).strip("_")


def image_path_for(query, size):
    return os.path.join(IMAGE_DIR, f"{safe_filename(query)}_{size[0]}x{size[1]}.jpg")


def make_placeholder(query, size=(420, 240)):
    """Generate a stylish placeholder without requiring any manual assets."""
    if not PIL_AVAILABLE:
        return None

    img = Image.new("RGB", size, "#171c22")
    draw = ImageDraw.Draw(img)
    w, h = size

    # Abstract BMW-like showroom background
    for x in range(0, w, 18):
        shade = 20 + int(18 * x / max(w, 1))
        draw.rectangle([x, 0, x + 18, h], fill=(shade, shade + 3, shade + 7))

    draw.ellipse((w * .34, h * .20, w * .66, h * .78), outline=(35, 120, 205), width=5)
    draw.ellipse((w * .405, h * .265, w * .595, h * .715), outline=(245, 245, 245), width=2)
    draw.text((18, h - 35), query, fill="white")

    return ImageTk.PhotoImage(img)


def create_logo(size=(120, 120)):
    """Create a BMW-inspired circular logo locally, so no logo file is needed."""
    if not PIL_AVAILABLE:
        return None

    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    w, h = size
    cx, cy = w // 2, h // 2
    r = min(w, h) // 2 - 5

    draw.ellipse((cx-r, cy-r, cx+r, cy+r), fill="white", outline="#333840", width=max(2, r//15))
    r2 = int(r * .72)
    draw.ellipse((cx-r2, cy-r2, cx+r2, cy+r2), fill="#101318", outline="#d9dce0", width=max(2, r//18))

    # Four blue/white quadrants
    rr = int(r2 * .78)
    draw.pieslice((cx-rr, cy-rr, cx+rr, cy+rr), 0, 90, fill="#0879d1")
    draw.pieslice((cx-rr, cy-rr, cx+rr, cy+rr), 90, 180, fill="white")
    draw.pieslice((cx-rr, cy-rr, cx+rr, cy+rr), 180, 270, fill="#0879d1")
    draw.pieslice((cx-rr, cy-rr, cx+rr, cy+rr), 270, 360, fill="white")

    # Inner ring
    draw.ellipse((cx-rr, cy-rr, cx+rr, cy+rr), outline="#20252b", width=max(1, r//30))
    return ImageTk.PhotoImage(img)


def download_wikimedia_image(query, size):
    """
    Automatically searches Wikimedia Commons and downloads a thumbnail.
    This means the user does NOT need to collect or add car pictures manually.
    """
    path = image_path_for(query, size)

    if os.path.exists(path) and os.path.getsize(path) > 1000:
        return path

    try:
        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": "6",
            "gsrlimit": "8",
            "prop": "imageinfo",
            "iiprop": "url",
            "iiurlwidth": str(max(size[0], 700)),
            "format": "json",
            "origin": "*"
        }
        url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "BMWIndiaStudentGUI/1.0"})
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))

        pages = data.get("query", {}).get("pages", {})
        candidates = []
        for page in pages.values():
            info = (page.get("imageinfo") or [{}])[0]
            thumb = info.get("thumburl") or info.get("url")
            title = page.get("title", "").lower()
            if thumb and ("bmw" in title or "car" in title or "automobile" in title):
                candidates.append(thumb)

        if not candidates:
            for page in pages.values():
                info = (page.get("imageinfo") or [{}])[0]
                if info.get("thumburl") or info.get("url"):
                    candidates.append(info.get("thumburl") or info.get("url"))

        if not candidates:
            return None

        img_url = candidates[0]
        req2 = urllib.request.Request(img_url, headers={"User-Agent": "BMWIndiaStudentGUI/1.0"})
        with urllib.request.urlopen(req2, timeout=10) as response:
            raw = response.read()

        if PIL_AVAILABLE:
            img = Image.open(io.BytesIO(raw)).convert("RGB")
            img.thumbnail(size, Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", size, "#11151a")
            x = (size[0] - img.width) // 2
            y = (size[1] - img.height) // 2
            canvas.paste(img, (x, y))
            canvas.save(path, "JPEG", quality=88)
            return path

    except Exception:
        return None

    return None


def get_photo(query, size=(420, 240)):
    """Return cached photo; first use triggers automatic download."""
    key = f"{query}|{size}"
    if key in image_cache:
        return image_cache[key]

    path = image_path_for(query, size)
    try:
        if os.path.exists(path) and PIL_AVAILABLE:
            img = Image.open(path).convert("RGB")
            img.thumbnail(size, Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", size, "#11151a")
            canvas.paste(img, ((size[0]-img.width)//2, (size[1]-img.height)//2))
            photo = ImageTk.PhotoImage(canvas)
            image_cache[key] = photo
            return photo
    except Exception:
        pass

    # Download in a background thread so the GUI never freezes.
    if key not in image_requests:
        image_requests[key] = True
        def worker():
            path2 = download_wikimedia_image(query, size)
            def finish():
                if path2 and PIL_AVAILABLE:
                    try:
                        img = Image.open(path2).convert("RGB")
                        img.thumbnail(size, Image.Resampling.LANCZOS)
                        canvas = Image.new("RGB", size, "#11151a")
                        canvas.paste(img, ((size[0]-img.width)//2, (size[1]-img.height)//2))
                        image_cache[key] = ImageTk.PhotoImage(canvas)
                    except Exception:
                        image_cache[key] = make_placeholder(query, size)
                else:
                    image_cache[key] = make_placeholder(query, size)
                image_requests.pop(key, None)
                refresh_image_listeners(key)
            try:
                root.after(0, finish)
            except Exception:
                pass

        import threading
        threading.Thread(target=worker, daemon=True).start()

    return make_placeholder(query, size)


image_listeners = {}


def listen_for_image(key, callback):
    image_listeners.setdefault(key, []).append(callback)


def refresh_image_listeners(key):
    for callback in image_listeners.pop(key, []):
        try:
            callback(image_cache.get(key))
        except Exception:
            pass


# ============================================================
# GENERAL UI HELPERS
# ============================================================

def clear_window():
    for widget in root.winfo_children():
        widget.destroy()


def make_label(parent, text, size=12, bold=False, color=TEXT, **kwargs):
    return tk.Label(
        parent,
        text=text,
        font=(FONT, size, "bold" if bold else "normal"),
        fg=color,
        bg=kwargs.pop("bg", parent.cget("bg") if "bg" in parent.keys() else BG),
        **kwargs
    )


def button(parent, text, command, width=18, primary=False, **kwargs):
    bg = BMW_BLUE if primary else CARD_2
    active = BMW_BLUE_2 if primary else "#2a323c"
    return tk.Button(
        parent,
        text=text,
        command=command,
        width=width,
        height=kwargs.pop("height", 1),
        font=(FONT, 10, "bold"),
        fg=WHITE,
        bg=bg,
        activebackground=active,
        activeforeground=WHITE,
        relief="flat",
        bd=0,
        cursor="hand2",
        padx=12,
        pady=8,
        **kwargs
    )


def title_bar(parent, heading, subtitle="", icon="◉"):
    bar = tk.Frame(parent, bg=BG)
    bar.pack(fill="x", padx=28, pady=(22, 14))

    make_label(bar, icon, 25, True, BMW_BLUE, bg=BG).pack(side="left", padx=(0, 12))
    text_box = tk.Frame(bar, bg=BG)
    text_box.pack(side="left", fill="x", expand=True)
    make_label(text_box, heading, 21, True, TEXT, bg=BG).pack(anchor="w")
    if subtitle:
        make_label(text_box, subtitle, 10, False, MUTED, bg=BG).pack(anchor="w", pady=(3, 0))
    return bar


def style_combobox(combo):
    combo.configure(
        font=(FONT, 11),
        state="readonly"
    )


def set_window(window, title, geometry):
    # Pages are rendered inside the main application window.
    # No extra Toplevel/sliding windows are created.
    if window is root:
        root.title(title)
        root.geometry(geometry)
        root.configure(bg=BG)
        root.minsize(980, 650)
    else:
        window.configure(bg=BG)


# ============================================================
# LOGIN
# ============================================================

def login_screen():
    clear_window()
    root.geometry("980x680")

    outer = tk.Frame(root, bg=BG)
    outer.pack(fill="both", expand=True)

    # Hero side
    hero = tk.Frame(outer, bg="#080a0d", width=510)
    hero.pack(side="left", fill="both")
    hero.pack_propagate(False)

    logo = create_logo((150, 150))
    if logo:
        lbl = tk.Label(hero, image=logo, bg="#080a0d")
        lbl.image = logo
        lbl.pack(pady=(70, 18))

    make_label(hero, "BMW", 38, True, WHITE, bg="#080a0d").pack()
    make_label(hero, "SHEER DRIVING PLEASURE", 11, True, BMW_BLUE, bg="#080a0d").pack(pady=(2, 18))
    make_label(
        hero,
        "Your digital BMW showroom\nfor cars, services and experiences.",
        13, False, MUTED, bg="#080a0d", justify="center"
    ).pack()

    # Login card
    right = tk.Frame(outer, bg=BG)
    right.pack(side="right", fill="both", expand=True)

    card = tk.Frame(right, bg=PANEL, padx=45, pady=35)
    card.place(relx=.5, rely=.5, anchor="center", relwidth=.78, relheight=.72)

    make_label(card, "WELCOME BACK", 22, True, TEXT, bg=PANEL).pack(anchor="w")
    make_label(card, "Sign in to BMW India", 11, False, MUTED, bg=PANEL).pack(anchor="w", pady=(5, 25))

    make_label(card, "USERNAME", 9, True, MUTED, bg=PANEL).pack(anchor="w")
    username_entry = tk.Entry(
        card, font=(FONT, 12), bg=CARD_2, fg=TEXT, insertbackground=WHITE,
        relief="flat", bd=0
    )
    username_entry.pack(fill="x", ipady=10, pady=(5, 18))
    username_entry.insert(0, "Vedant")

    make_label(card, "PASSWORD", 9, True, MUTED, bg=PANEL).pack(anchor="w")
    password_entry = tk.Entry(
        card, font=(FONT, 12), bg=CARD_2, fg=TEXT, insertbackground=WHITE,
        relief="flat", bd=0, show="*"
    )
    password_entry.pack(fill="x", ipady=10, pady=(5, 22))
    password_entry.insert(0, "1611")

    def login():
        global username
        if username_entry.get() == "Vedant" and password_entry.get() == "1611":
            username = username_entry.get()
            dashboard()
        else:
            messagebox.showerror("Login Failed", "Invalid Username or Password!")

    button(card, "LOGIN  →", login, width=24, primary=True).pack(fill="x")
    make_label(
        card, "Demo login • Username: Vedant • Password: 1611",
        8, False, MUTED, bg=PANEL
    ).pack(anchor="w", pady=(14, 0))

    username_entry.focus_set()
    password_entry.bind("<Return>", lambda e: login())


# ============================================================
# DASHBOARD
# ============================================================

def open_page():
    """Clear the main content area and return a fresh page frame."""
    global content_frame
    if content_frame is None:
        return root
    for widget in content_frame.winfo_children():
        widget.destroy()
    page = tk.Frame(content_frame, bg=BG)
    page.pack(fill="both", expand=True)
    return page


def page_back():
    dashboard()


def dashboard():
    global content_frame
    clear_window()
    root.geometry("1180x800")

    # Top navigation
    top = tk.Frame(root, bg="#080a0d", height=75)
    top.pack(fill="x")
    top.pack_propagate(False)

    logo = create_logo((54, 54))
    if logo:
        lbl = tk.Label(top, image=logo, bg="#080a0d")
        lbl.image = logo
        lbl.pack(side="left", padx=(24, 12), pady=10)

    brand = tk.Frame(top, bg="#080a0d")
    brand.pack(side="left", pady=12)
    make_label(brand, "BMW INDIA", 17, True, WHITE, bg="#080a0d").pack(anchor="w")
    make_label(brand, "DIGITAL SHOWROOM", 8, True, BMW_BLUE, bg="#080a0d").pack(anchor="w")

    make_label(top, f"Welcome, {username}", 10, False, MUTED, bg="#080a0d").pack(side="right", padx=25)

    body = tk.Frame(root, bg=BG)
    body.pack(fill="both", expand=True)

    # Left sidebar
    sidebar = tk.Frame(body, bg=PANEL, width=220)
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)

    make_label(sidebar, "MENU", 9, True, MUTED, bg=PANEL).pack(anchor="w", padx=22, pady=(25, 10))

    buttons = [
        ("🚘", "View Cars", view_cars),
        ("♡", "Wishlist", wishlist_window),
        ("🛒", "Cart", cart_window),
        ("👤", "Profile", profile_window),
        ("⚙", "Admin Panel", admin_panel),
        ("🔧", "Service Centers", service_centers),
        ("🆘", "Highway Help", highway_help),
        ("⚠", "Accident Help", accident_help),
        ("?", "Help & Support", help_support),
        ("☎", "Customer Care", customer_care),
        ("★", "BMW Events", bmw_events),
        ("▣", "Book Test Drive", test_drive),
        ("🏁", "BMW Motorsport", motorsport),
        ("💼", "BMW Careers", careers),
    ]

    for icon, text, command in buttons:
        b = tk.Button(
            sidebar, text=f"{icon}   {text}", command=command,
            anchor="w", font=(FONT, 9, "bold"), fg=TEXT, bg=PANEL,
            activebackground=CARD_2, activeforeground=WHITE,
            relief="flat", bd=0, cursor="hand2", padx=20, pady=8
        )
        b.pack(fill="x", padx=8, pady=1)

    button(sidebar, "LOG OUT", logout, width=16, primary=False).pack(side="bottom", pady=22)

    # Main content
    content = tk.Frame(body, bg=BG)
    content.pack(side="right", fill="both", expand=True)
    content_frame = content

    title_bar(content, "BMW EXPERIENCE", "Explore the range, configure a car and access BMW services.", "✦")

    hero = tk.Frame(content, bg="#101820", height=205)
    hero.pack(fill="x", padx=28, pady=10)
    hero.pack_propagate(False)

    # Hero image - automatically obtained from Wikimedia
    hero_photo = get_photo("BMW car showroom", (420, 205))
    image_label = tk.Label(hero, image=hero_photo, bg="#101820")
    image_label.image = hero_photo
    image_label.pack(side="right", fill="y")

    copy = tk.Frame(hero, bg="#101820")
    copy.pack(side="left", fill="both", expand=True, padx=28, pady=22)
    make_label(copy, "THE ULTIMATE", 10, True, BMW_BLUE, bg="#101820").pack(anchor="w")
    make_label(copy, "BMW COLLECTION", 25, True, WHITE, bg="#101820").pack(anchor="w", pady=(2, 4))
    make_label(
        copy,
        "Choose your model. Personalise it.\\nMake it yours.",
        11, False, MUTED, bg="#101820", justify="left"
    ).pack(anchor="w", pady=(0, 15))
    button(copy, "EXPLORE CARS  →", view_cars, width=18, primary=True).pack(anchor="w")

    # Quick cards
    make_label(content, "QUICK ACCESS", 10, True, MUTED, bg=BG).pack(anchor="w", padx=28, pady=(20, 8))

    quick = tk.Frame(content, bg=BG)
    quick.pack(fill="x", padx=28)

    cards = [
        ("🚘", "BMW MODELS", "Explore the range", view_cars),
        ("🛠", "ROAD ASSIST", "Help when you need it", highway_help),
        ("▣", "TEST DRIVE", "Book a drive", test_drive),
        ("🏁", "MOTORSPORT", "Performance & racing", motorsport),
    ]

    for icon, heading, sub, cmd in cards:
        c = tk.Frame(quick, bg=CARD, width=175, height=115)
        c.pack(side="left", fill="both", expand=True, padx=(0, 10))
        c.pack_propagate(False)
        make_label(c, icon, 25, False, BMW_BLUE, bg=CARD).pack(anchor="w", padx=15, pady=(13, 0))
        make_label(c, heading, 10, True, TEXT, bg=CARD).pack(anchor="w", padx=15, pady=(3, 0))
        make_label(c, sub, 8, False, MUTED, bg=CARD).pack(anchor="w", padx=15)
        c.bind("<Button-1>", lambda e, f=cmd: f())
        for child in c.winfo_children():
            child.bind("<Button-1>", lambda e, f=cmd: f())


# ============================================================
# CAR SHOWROOM
# ============================================================

def view_cars():
    window = open_page()
    set_window(window, "BMW Cars", "1120x720")

    title_bar(window, "BMW MODEL RANGE", "Select a segment and configure your BMW.", "🚘")

    top = tk.Frame(window, bg=BG)
    top.pack(fill="x", padx=28)

    make_label(top, "SEGMENT", 9, True, MUTED, bg=BG).pack(side="left")
    segment_var = tk.StringVar(value="SUV")
    segment_menu = ttk.Combobox(top, textvariable=segment_var, values=list(cars.keys()), width=16)
    style_combobox(segment_menu)
    segment_menu.pack(side="left", padx=10)

    main = tk.Frame(window, bg=BG)
    main.pack(fill="both", expand=True, padx=28, pady=18)

    # Left: models
    model_panel = tk.Frame(main, bg=PANEL, width=560)
    model_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))
    model_panel.pack_propagate(False)

    make_label(model_panel, "CHOOSE YOUR BMW", 11, True, TEXT, bg=PANEL).pack(anchor="w", padx=20, pady=(20, 10))

    model_canvas = tk.Canvas(model_panel, bg=PANEL, highlightthickness=0)
    scrollbar = ttk.Scrollbar(model_panel, orient="vertical", command=model_canvas.yview)
    model_frame = tk.Frame(model_canvas, bg=PANEL)
    model_window_id = model_canvas.create_window((0, 0), window=model_frame, anchor="nw")
    model_canvas.configure(yscrollcommand=scrollbar.set)
    model_canvas.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=5)
    scrollbar.pack(side="right", fill="y", pady=5)

    # Keep the embedded frame as wide as the canvas. Without this, Tkinter
    # can give the frame a width of only a few pixels, making the
    # "CHOOSE YOUR BMW" cards appear empty/clipped.
    def resize_model_frame(event):
        model_canvas.itemconfigure(model_window_id, width=event.width)

    model_canvas.bind("<Configure>", resize_model_frame)
    model_frame.bind("<Configure>", lambda e: model_canvas.configure(scrollregion=model_canvas.bbox("all")))

    # Mouse-wheel scrolling for the model list (Windows + Linux + macOS).
    def wheel_scroll(event):
        if event.delta:
            model_canvas.yview_scroll(int(-event.delta / 120), "units")
        elif getattr(event, "num", None) == 4:
            model_canvas.yview_scroll(-3, "units")
        elif getattr(event, "num", None) == 5:
            model_canvas.yview_scroll(3, "units")

    model_canvas.bind("<MouseWheel>", wheel_scroll)
    model_canvas.bind("<Button-4>", wheel_scroll)
    model_canvas.bind("<Button-5>", wheel_scroll)
    model_frame.bind("<MouseWheel>", wheel_scroll)

    # Right: configuration — built as a scrollable panel with a sticky action bar.
    # This keeps ADD TO CART and VIEW CART visible even when the window is short.
    config_outer = tk.Frame(main, bg=PANEL, width=410)
    config_outer.pack(side="right", fill="both")
    config_outer.pack_propagate(False)

    config_canvas = tk.Canvas(config_outer, bg=PANEL, highlightthickness=0)
    config_scroll = ttk.Scrollbar(config_outer, orient="vertical", command=config_canvas.yview)
    config_canvas.configure(yscrollcommand=config_scroll.set)
    config_canvas.pack(side="left", fill="both", expand=True)
    config_scroll.pack(side="right", fill="y")

    config = tk.Frame(config_canvas, bg=PANEL)
    config_window_id = config_canvas.create_window((0, 0), window=config, anchor="nw")

    def resize_config(event):
        config_canvas.itemconfigure(config_window_id, width=event.width)

    config_canvas.bind("<Configure>", resize_config)
    config.bind("<Configure>", lambda e: config_canvas.configure(scrollregion=config_canvas.bbox("all")))

    def config_wheel(event):
        if event.delta:
            config_canvas.yview_scroll(int(-event.delta / 120), "units")
        elif getattr(event, "num", None) == 4:
            config_canvas.yview_scroll(-3, "units")
        elif getattr(event, "num", None) == 5:
            config_canvas.yview_scroll(3, "units")

    config_canvas.bind("<MouseWheel>", config_wheel)
    config_canvas.bind("<Button-4>", config_wheel)
    config_canvas.bind("<Button-5>", config_wheel)
    config.bind("<MouseWheel>", config_wheel)

    photo_label = tk.Label(config, bg=PANEL)
    photo_label.pack(fill="x", padx=12, pady=(18, 8))

    car_var = tk.StringVar()
    color_var = tk.StringVar(value="Black")
    accessory_var = tk.StringVar(value="No Accessories")
    price_var = tk.StringVar(value="₹0 Lakhs")

    make_label(config, "MODEL", 8, True, MUTED, bg=PANEL).pack(anchor="w", padx=24)
    selected_label = make_label(config, "", 18, True, TEXT, bg=PANEL)
    selected_label.pack(anchor="w", padx=24, pady=(2, 4))

    config_badge = make_label(config, "", 9, True, BMW_BLUE, bg=PANEL)
    config_badge.pack(anchor="w", padx=24, pady=(0, 8))

    def visual_query():
        name = car_var.get() or "BMW car"
        color = color_var.get()
        accessory = accessory_var.get()
        if accessory == "No Accessories":
            return f"{name} BMW {color}"
        return f"{name} BMW {color} {accessory}"

    def update_photo(query, photo=None):
        if photo:
            photo_label.configure(image=photo)
            photo_label.image = photo

    def update_car_visual(*args):
        query = visual_query()
        photo = get_photo(query, (350, 200))
        photo_label.configure(image=photo)
        photo_label.image = photo
        key = f"{query}|{(350, 200)}"
        listen_for_image(key, lambda p: update_photo(query, p))

        config_badge.configure(text=f"{color_var.get()}  •  {accessory_var.get()}")
        update_price()

    def select_car(name):
        car_var.set(name)
        selected_label.configure(text=name)
        update_car_visual()
        config_canvas.yview_moveto(0)

    def update_price(*args):
        selected = car_var.get()
        segment = segment_var.get()
        price = 0
        for name, value in cars[segment]:
            if name == selected:
                price = value
                break
        price += accessories[accessory_var.get()]
        price_var.set(f"₹{price:g} Lakhs")

    def update_models(*args):
        for child in model_frame.winfo_children():
            child.destroy()

        segment = segment_var.get()
        for name, price in cars[segment]:
            card = tk.Frame(model_frame, bg=CARD, height=78)
            card.pack(fill="x", padx=8, pady=5)
            card.pack_propagate(False)

            small = get_photo(name + " BMW", (120, 68))
            pic = tk.Label(card, image=small, bg=CARD)
            pic.image = small
            pic.pack(side="left", padx=5)

            info = tk.Frame(card, bg=CARD)
            info.pack(side="left", fill="both", expand=True)
            make_label(info, name, 10, True, TEXT, bg=CARD).pack(anchor="w", pady=(12, 0))
            make_label(info, f"From ₹{price:g} Lakhs", 8, False, MUTED, bg=CARD).pack(anchor="w")

            for widget in (card, pic, info):
                widget.bind("<Button-1>", lambda e, n=name: select_car(n))

        select_car(cars[segment][0][0])

    make_label(config, "COLOR", 8, True, MUTED, bg=PANEL).pack(anchor="w", padx=24)
    color_menu = ttk.Combobox(config, textvariable=color_var, values=colors, width=28)
    style_combobox(color_menu)
    color_menu.pack(fill="x", padx=24, pady=(4, 12))

    make_label(config, "ACCESSORIES", 8, True, MUTED, bg=PANEL).pack(anchor="w", padx=24)
    accessory_menu = ttk.Combobox(config, textvariable=accessory_var, values=list(accessories.keys()), width=28)
    style_combobox(accessory_menu)
    accessory_menu.pack(fill="x", padx=24, pady=(4, 12))
    accessory_menu.bind("<<ComboboxSelected>>", update_car_visual)
    color_menu.bind("<<ComboboxSelected>>", update_car_visual)

    price_card = tk.Frame(config, bg=CARD_2)
    price_card.pack(fill="x", padx=24, pady=(8, 15))
    make_label(price_card, "CONFIGURED PRICE", 8, True, MUTED, bg=CARD_2).pack(anchor="w", padx=14, pady=(10, 0))
    price_label = tk.Label(price_card, textvariable=price_var, font=(FONT, 19, "bold"), fg=WHITE, bg=CARD_2)
    price_label.pack(anchor="w", padx=14, pady=(1, 10))

    def add_car_to_cart():
        selected_car = car_var.get()
        selected_segment = segment_var.get()
        selected_color = color_var.get()
        selected_accessory = accessory_var.get()

        price = 0
        for car_name, car_price in cars[selected_segment]:
            if car_name == selected_car:
                price = car_price
                break
        price += accessories[selected_accessory]
        cart.append((selected_car, price, selected_color, selected_accessory))
        messagebox.showinfo("Cart", f"{selected_car} added to Cart!\n\n{selected_color} • {selected_accessory}\n₹{price:g} Lakhs")

    def add_car_to_wishlist():
        selected_car = car_var.get()
        selected_segment = segment_var.get()
        selected_color = color_var.get()
        selected_accessory = accessory_var.get()

        price = 0
        for car_name, car_price in cars[selected_segment]:
            if car_name == selected_car:
                price = car_price
                break
        price += accessories[selected_accessory]
        wishlist.append((selected_car, price, selected_color, selected_accessory))
        messagebox.showinfo("Wishlist", f"{selected_car} saved to Wishlist!")

    # Sticky action bar at the bottom of the right panel.
    actions = tk.Frame(config_outer, bg="#0f1318", height=104)
    actions.pack(side="bottom", fill="x")
    actions.pack_propagate(False)

    cart_count = tk.StringVar(value="0")
    def refresh_cart_count():
        cart_count.set(str(len(cart)))

    def open_cart_and_refresh():
        refresh_cart_count()
        cart_window()

    button(actions, "🛒 VIEW CART", open_cart_and_refresh, width=13).pack(side="left", padx=(12, 5), pady=(10, 5))
    button(actions, "♡ WISHLIST", add_car_to_wishlist, width=13).pack(side="left", padx=5, pady=(10, 5))
    button(actions, "ADD TO CART  →", add_car_to_cart, width=16, primary=True).pack(side="left", padx=5, pady=(10, 5))
    make_label(actions, "Items in cart: 0", 8, False, MUTED, bg="#0f1318", textvariable=cart_count).pack(anchor="w", padx=14, pady=(0, 5))

    segment_menu.bind("<<ComboboxSelected>>", update_models)
    update_models()



# ============================================================
# WISHLIST
# ============================================================

def wishlist_window():
    window = open_page()
    set_window(window, "Wishlist", "850x600")
    title_bar(window, "MY WISHLIST", "Cars saved for later.", "♡")

    body = tk.Frame(window, bg=BG)
    body.pack(fill="both", expand=True, padx=28, pady=5)

    listbox = tk.Listbox(
        body, width=75, height=16, bg=CARD, fg=TEXT,
        selectbackground=BMW_BLUE, selectforeground=WHITE,
        font=(FONT, 11), relief="flat", bd=0
    )
    listbox.pack(fill="both", expand=True, pady=8)

    def refresh():
        listbox.delete(0, tk.END)
        for item in wishlist:
            listbox.insert(tk.END, f"  {item[0]}   |   {item[2]}   |   {item[3]}   |   ₹{item[1]:g} Lakhs")
        if not wishlist:
            listbox.insert(tk.END, "  Your wishlist is empty.")

    def remove():
        selected = listbox.curselection()
        if selected and wishlist:
            wishlist.pop(selected[0])
            refresh()
        else:
            messagebox.showwarning("Wishlist", "Please select a car.")

    def move_to_cart():
        selected = listbox.curselection()
        if selected and wishlist:
            cart.append(wishlist.pop(selected[0]))
            refresh()
            messagebox.showinfo("Cart", "Car moved to Cart!")
        else:
            messagebox.showwarning("Wishlist", "Please select a car.")

    controls = tk.Frame(body, bg=BG)
    controls.pack(fill="x", pady=8)
    button(controls, "REMOVE", remove).pack(side="left", padx=(0, 8))
    button(controls, "MOVE TO CART  →", move_to_cart, primary=True).pack(side="left")
    refresh()


# ============================================================
# CART + PURCHASE
# ============================================================

def cart_window():
    window = open_page()
    set_window(window, "Cart", "900x620")
    title_bar(window, "MY CART", "Review your selected BMW before purchase.", "🛒")

    body = tk.Frame(window, bg=BG)
    body.pack(fill="both", expand=True, padx=28)

    listbox = tk.Listbox(
        body, width=80, height=15, bg=CARD, fg=TEXT,
        selectbackground=BMW_BLUE, selectforeground=WHITE,
        font=(FONT, 11), relief="flat", bd=0
    )
    listbox.pack(fill="both", expand=True, pady=10)

    total_var = tk.StringVar(value="Total: ₹0 Lakhs")
    tk.Label(body, textvariable=total_var, font=(FONT, 16, "bold"), fg=WHITE, bg=BG).pack(anchor="e", pady=5)

    def refresh():
        listbox.delete(0, tk.END)
        total = 0
        for item in cart:
            total += item[1]
            listbox.insert(tk.END, f"  {item[0]}   |   {item[2]}   |   {item[3]}   |   ₹{item[1]:g} Lakhs")
        total_var.set(f"Total: ₹{total:g} Lakhs")
        if not cart:
            listbox.insert(tk.END, "  Your cart is empty.")

    def remove():
        selected = listbox.curselection()
        if selected and cart:
            cart.pop(selected[0])
            refresh()
        else:
            messagebox.showwarning("Cart", "Please select a car.")

    def buy():
        selected = listbox.curselection()
        if not selected or not cart:
            messagebox.showwarning("Cart", "Please select a car.")
            return
        buy_car(cart[selected[0]], selected[0], refresh)

    controls = tk.Frame(body, bg=BG)
    controls.pack(fill="x", pady=8)
    button(controls, "REMOVE", remove).pack(side="left", padx=(0, 8))
    button(controls, "PROCEED TO BUY  →", buy, primary=True).pack(side="left")
    refresh()


def buy_car(car, index, refresh):
    window = open_page()
    set_window(window, "Purchase", "650x700")
    title_bar(window, "BMW PURCHASE", "Complete your vehicle configuration.", "✓")

    # Automatically show the exact model image
    photo = get_photo(car[0] + " BMW", (430, 220))
    image = tk.Label(window, image=photo, bg=BG)
    image.image = photo
    image.pack(pady=(0, 8))

    info = tk.Frame(window, bg=CARD)
    info.pack(fill="x", padx=28, pady=8)
    make_label(info, car[0], 17, True, TEXT, bg=CARD).pack(anchor="w", padx=18, pady=(14, 3))
    make_label(
        info, f"Color: {car[2]}   •   Accessory: {car[3]}   •   ₹{car[1]:g} Lakhs",
        9, False, MUTED, bg=CARD
    ).pack(anchor="w", padx=18, pady=(0, 14))

    form = tk.Frame(window, bg=BG)
    form.pack(fill="x", padx=28, pady=8)

    def field(label, variable, values):
        make_label(form, label, 8, True, MUTED, bg=BG).pack(anchor="w", pady=(7, 3))
        combo = ttk.Combobox(form, textvariable=variable, values=values, width=35)
        style_combobox(combo)
        combo.pack(anchor="w")
        return combo

    city_var = tk.StringVar(value="Ahmedabad")
    cities = {"Ahmedabad": 5, "Mumbai": 7, "Delhi": 9, "Bangalore": 8, "Pan India": 10}
    field("DELIVERY CITY", city_var, list(cities.keys()))

    insurance_var = tk.StringVar(value="Basic")
    field("INSURANCE", insurance_var, ["Basic", "Premium"])

    payment_var = tk.StringVar(value="Full Payment")
    field("PAYMENT", payment_var, ["Full Payment", "EMI"])

    down_payment_entry = tk.Entry(
        form, font=(FONT, 11), bg=CARD_2, fg=TEXT, insertbackground=WHITE,
        relief="flat", bd=0
    )

    def update_payment(*args):
        if payment_var.get() == "EMI":
            make_label(form, "DOWN PAYMENT (₹ LAKHS)", 8, True, MUTED, bg=BG).pack(anchor="w", pady=(7, 3))
            down_payment_entry.pack(anchor="w", fill="x", ipady=8)
            down_payment_entry.delete(0, tk.END)
        else:
            down_payment_entry.pack_forget()

    payment_var.trace_add("write", update_payment)

    def confirm():
        insurance_price = 3 if insurance_var.get() == "Premium" else 1
        total = car[1] + insurance_price

        if payment_var.get() == "EMI":
            try:
                down_payment = float(down_payment_entry.get())
            except ValueError:
                messagebox.showerror("Error", "Enter valid down payment.")
                return
            if down_payment < total * 0.20:
                messagebox.showerror("EMI", "Minimum 20% down payment required.")
                return

        order = {
            "car": car[0],
            "price": total,
            "color": car[2],
            "accessory": car[3],
            "insurance": insurance_var.get(),
            "city": city_var.get(),
            "payment": payment_var.get()
        }
        order_history.append(order)
        cart.pop(index)

        messagebox.showinfo(
            "Order Confirmed",
            f"BMW {car[0]} purchased successfully!\n\n"
            f"Total Price: ₹{total:g} Lakhs\n"
            f"Delivery: {cities[city_var.get()]} Days"
        )
        dashboard()

    button(window, "CONFIRM PURCHASE  ✓", confirm, width=28, primary=True).pack(pady=18)


# ============================================================
# PROFILE
# ============================================================

def profile_window():
    window = open_page()
    set_window(window, "Profile", "650x650")
    title_bar(window, "MY PROFILE", "Account and recent order information.", "👤")

    card = tk.Frame(window, bg=PANEL)
    card.pack(fill="x", padx=28, pady=10)

    make_label(card, "ACCOUNT", 8, True, MUTED, bg=PANEL).pack(anchor="w", padx=20, pady=(18, 3))
    make_label(card, username, 21, True, TEXT, bg=PANEL).pack(anchor="w", padx=20, pady=(0, 18))

    if order_history:
        order = order_history[-1]
        details = (
            f"Car: {order['car']}\n"
            f"Color: {order['color']}\n"
            f"Accessory: {order['accessory']}\n"
            f"Insurance: {order['insurance']}\n"
            f"City: {order['city']}\n"
            f"Payment: {order['payment']}\n"
            f"Price: ₹{order['price']:g} Lakhs"
        )
        make_label(window, "LAST ORDER", 9, True, MUTED, bg=BG).pack(anchor="w", padx=28, pady=(18, 5))
        card2 = tk.Frame(window, bg=CARD)
        card2.pack(fill="x", padx=28)
        make_label(card2, details, 11, False, TEXT, bg=CARD, justify="left").pack(anchor="w", padx=18, pady=18)
    else:
        make_label(window, "No orders found.", 12, False, MUTED, bg=BG).pack(pady=35)


# ============================================================
# ADMIN
# ============================================================

def admin_panel():
    window = open_page()
    set_window(window, "Admin Panel", "650x520")
    title_bar(window, "ADMIN PANEL", "BMW India management dashboard.", "⚙")

    # Dashboard cards with visual icons
    stats = tk.Frame(window, bg=BG)
    stats.pack(fill="x", padx=28, pady=12)

    for icon, heading, value in [
        ("🚘", "CARS SOLD", "10"),
        ("₹", "TOTAL SALES", "₹15 Cr"),
        ("👥", "REGISTERED USERS", "150")
    ]:
        c = tk.Frame(stats, bg=CARD)
        c.pack(side="left", fill="both", expand=True, padx=5)
        make_label(c, icon, 23, False, BMW_BLUE, bg=CARD).pack(pady=(15, 2))
        make_label(c, heading, 8, True, MUTED, bg=CARD).pack()
        make_label(c, value, 17, True, WHITE, bg=CARD).pack(pady=(2, 15))

    button(window, "VIEW SALES REPORT", lambda: messagebox.showinfo(
        "Sales Report", "Total Cars Sold: 10\nTotal Sales: ₹15 Crore"
    ), width=28, primary=True).pack(pady=8)

    button(window, "REGISTERED USERS", lambda: messagebox.showinfo(
        "Users", "Registered Users: 150"
    ), width=28).pack(pady=8)


# ============================================================
# SERVICES
# ============================================================

def service_centers():
    window = open_page()
    set_window(window, "BMW Service Centers", "700x520")
    title_bar(window, "BMW SERVICE CENTERS", "Find BMW service support by city.", "🔧")

    places = [
        ("Ahmedabad", "SG Highway", "BMW service & maintenance"),
        ("Mumbai", "Andheri", "BMW service & maintenance"),
        ("Delhi", "Connaught Place", "BMW service & maintenance"),
        ("Bangalore", "MG Road", "BMW service & maintenance")
    ]

    for city, location, desc in places:
        c = tk.Frame(window, bg=CARD)
        c.pack(fill="x", padx=28, pady=5)
        make_label(c, "⌖", 23, False, BMW_BLUE, bg=CARD).pack(side="left", padx=15, pady=10)
        info = tk.Frame(c, bg=CARD)
        info.pack(side="left")
        make_label(info, city, 11, True, TEXT, bg=CARD).pack(anchor="w", pady=(8, 0))
        make_label(info, f"{location}  •  {desc}", 8, False, MUTED, bg=CARD).pack(anchor="w", pady=(0, 8))


def highway_help():
    window = open_page()
    set_window(window, "Highway Help", "650x540")
    title_bar(window, "HIGHWAY HELP", "Roadside assistance options.", "🆘")

    options = [
        ("🛞", "Flat Tyre", "Technician will reach you within 30 minutes."),
        ("🔋", "Battery Problem", "Battery support has been dispatched."),
        ("⛽", "Out of Fuel", "Fuel tanker has been dispatched.")
    ]

    for icon, name, msg in options:
        c = tk.Frame(window, bg=CARD)
        c.pack(fill="x", padx=28, pady=6)
        make_label(c, icon, 25, False, BMW_BLUE, bg=CARD).pack(side="left", padx=16, pady=13)
        make_label(c, name, 11, True, TEXT, bg=CARD).pack(side="left")
        button(c, "REQUEST", lambda m=msg: messagebox.showinfo("Highway Help", m), width=10, primary=True).pack(side="right", padx=12)


def accident_help():
    window = open_page()
    set_window(window, "Accident Help", "650x540")
    title_bar(window, "ACCIDENT HELP", "Emergency and insurance support.", "⚠")

    options = {
        "Emergency Assistance": "Emergency assistance has been contacted.",
        "Insurance Claim": "Insurance claim support has been initiated.",
        "Tow Truck": "Tow truck has been dispatched."
    }

    for name, message in options.items():
        button(window, "⚠  " + name, lambda m=message: messagebox.showinfo("Accident Help", m),
               width=30, primary=(name == "Emergency Assistance")).pack(pady=9)


def help_support():
    window = open_page()
    set_window(window, "Help & Support", "650x470")
    title_bar(window, "HELP & SUPPORT", "Tell us what you need help with.", "?")

    make_label(window, "DESCRIBE YOUR ISSUE", 9, True, MUTED, bg=BG).pack(anchor="w", padx=40, pady=(15, 5))
    entry = tk.Entry(window, width=55, font=(FONT, 11), bg=CARD_2, fg=TEXT, insertbackground=WHITE, relief="flat")
    entry.pack(padx=40, ipady=12, fill="x")

    def submit():
        if entry.get().strip():
            messagebox.showinfo("Support", "Your issue has been recorded.\nOur support team will contact you.")
            dashboard()
        else:
            messagebox.showwarning("Support", "Please enter your issue.")

    button(window, "SUBMIT REQUEST  →", submit, width=24, primary=True).pack(pady=22)


def customer_care():
    messagebox.showinfo(
        "BMW Customer Care",
        "☎  Phone: 1800-102-2269\n\n"
        "✉  Email: customercare@bmw.in\n\n"
        "◷  Timing: 9 AM - 8 PM"
    )


# ============================================================
# EVENTS
# ============================================================

def bmw_events():
    window = open_page()
    set_window(window, "BMW Events", "750x600")
    title_bar(window, "BMW EVENTS", "Experiences, track days and owner events.", "★")

    events = {
        "Auto Expo 2026": "Delhi\nEntry Fee: ₹5000",
        "Track Day": "Mumbai Race Track\nEntry Fee: ₹15000\nRacing License Required",
        "Owners Meet": "Ahmedabad\nBMW Owners Event",
        "Electric Future Summit": "Bangalore\nFree Entry\nRegistration Required"
    }

    for event, details in events.items():
        c = tk.Frame(window, bg=CARD)
        c.pack(fill="x", padx=28, pady=6)
        make_label(c, "★", 22, False, GOLD, bg=CARD).pack(side="left", padx=15, pady=12)
        make_label(c, event, 11, True, TEXT, bg=CARD).pack(side="left")
        button(c, "VIEW", lambda e=event, d=details: messagebox.showinfo(e, d), width=9).pack(side="right", padx=12)


# ============================================================
# TEST DRIVE
# ============================================================

def test_drive():
    window = open_page()
    set_window(window, "Book Test Drive", "700x700")
    title_bar(window, "BOOK A TEST DRIVE", "Choose your city, model and preferred slot.", "▣")

    # Dynamic model image
    image = tk.Label(window, bg=BG)
    image.pack(pady=(0, 10))

    city_var = tk.StringVar(value="Ahmedabad")
    model_var = tk.StringVar(value="BMW X1")
    date_var = tk.StringVar(value="Tomorrow")
    time_var = tk.StringVar(value="10 AM")

    def update_model_image(*args):
        photo = get_photo(model_var.get() + " BMW", (350, 180))
        image.configure(image=photo)
        image.image = photo

    form = tk.Frame(window, bg=BG)
    form.pack(fill="x", padx=55)

    def field(label, var, values):
        make_label(form, label, 8, True, MUTED, bg=BG).pack(anchor="w", pady=(7, 3))
        combo = ttk.Combobox(form, textvariable=var, values=values, width=35)
        style_combobox(combo)
        combo.pack(anchor="w")
        return combo

    field("CITY", city_var, ["Ahmedabad", "Mumbai", "Delhi", "Bangalore"])
    model_combo = field("MODEL", model_var, ["BMW X1", "BMW 3 Series", "BMW M4", "BMW i4"])
    field("DATE", date_var, ["Tomorrow", "Day After Tomorrow", "Weekend"])
    field("TIME", time_var, ["10 AM", "1 PM", "4 PM"])

    model_combo.bind("<<ComboboxSelected>>", update_model_image)

    license_var = tk.BooleanVar()
    tk.Checkbutton(
        form, text="I have a valid driving license",
        variable=license_var, bg=BG, fg=TEXT,
        activebackground=BG, activeforeground=WHITE,
        selectcolor=CARD_2, font=(FONT, 10)
    ).pack(anchor="w", pady=18)

    def book():
        if license_var.get():
            messagebox.showinfo(
                "Test Drive",
                "Test Drive Booked!\n\n"
                f"City: {city_var.get()}\nModel: {model_var.get()}\n"
                f"Date: {date_var.get()}\nTime: {time_var.get()}"
            )
            dashboard()
        else:
            messagebox.showwarning("Test Drive", "A valid driving license is required.")

    button(window, "BOOK TEST DRIVE  ✓", book, width=27, primary=True).pack()
    update_model_image()


# ============================================================
# MOTORSPORT
# ============================================================

def motorsport():
    window = open_page()
    set_window(window, "BMW Motorsport", "850x650")
    title_bar(window, "BMW MOTORSPORT", "Performance, racing and engineering.", "🏁")

    hero = get_photo("BMW motorsport racing car", (760, 190))
    image = tk.Label(window, image=hero, bg=BG)
    image.image = hero
    image.pack(padx=28, pady=(0, 12))

    information = {
        "Racing Categories": "GT Racing\nTouring Car Racing\nFormula Racing\nEndurance Racing",
        "Championship Records": "BMW has participated in international touring, GT and endurance championships.",
        "Motorsport History": "BMW Motorsport was established to develop high-performance racing cars and technology.",
        "Global Participation": "BMW participates in racing events across Europe, America and other regions.",
        "Racing Technology": "Aerodynamics\nLightweight Materials\nHigh-performance Engines\nAdvanced Suspension",
        "Rivals": "Mercedes-AMG\nAudi Sport\nPorsche"
    }

    grid = tk.Frame(window, bg=BG)
    grid.pack(fill="both", expand=True, padx=28)
    for i, (name, details) in enumerate(information.items()):
        c = tk.Frame(grid, bg=CARD)
        c.grid(row=i//2, column=i%2, sticky="nsew", padx=5, pady=5)
        make_label(c, "🏁", 20, False, BMW_BLUE, bg=CARD).pack(side="left", padx=12, pady=12)
        button(c, name, lambda n=name, d=details: messagebox.showinfo(n, d), width=24).pack(side="left", padx=5)
    grid.grid_columnconfigure(0, weight=1)
    grid.grid_columnconfigure(1, weight=1)


# ============================================================
# CAREERS
# ============================================================

def careers():
    window = open_page()
    set_window(window, "BMW Careers", "800x650")
    title_bar(window, "BMW CAREERS", "Explore opportunities across BMW.", "💼")

    hero = get_photo("BMW factory workers engineering", (740, 170))
    image = tk.Label(window, image=hero, bg=BG)
    image.image = hero
    image.pack(padx=28, pady=(0, 12))

    jobs = {
        "Internship": "Students pursuing graduation or post-graduation",
        "Engineering": "Engineering degree with relevant technical skills",
        "Design": "Design degree and creative skills",
        "Sales & Marketing": "Marketing, business or communication skills",
        "After-Sales / Service": "Automobile or technical background"
    }

    def apply(role, eligibility):
        messagebox.showinfo(
            "Application",
            f"Position: {role}\n\nEligibility: {eligibility}\n\n"
            "Application submitted successfully!"
        )

    for role, eligibility in jobs.items():
        c = tk.Frame(window, bg=CARD)
        c.pack(fill="x", padx=28, pady=4)
        make_label(c, "▸", 18, True, BMW_BLUE, bg=CARD).pack(side="left", padx=15)
        make_label(c, role, 10, True, TEXT, bg=CARD).pack(side="left")
        button(c, "APPLY", lambda r=role, e=eligibility: apply(r, e), width=9, primary=True).pack(side="right", padx=12, pady=8)


# ============================================================
# LOGOUT + START
# ============================================================

def logout():
    global cart, wishlist, order_history
    answer = messagebox.askyesno("Logout", "Are you sure you want to logout?")
    if answer:
        cart = []
        wishlist = []
        order_history = []
        login_screen()


root = tk.Tk()
root.title("BMW INDIA")
root.geometry("980x680")
root.configure(bg=BG)

# ttk styling
style = ttk.Style()
try:
    style.theme_use("clam")
except Exception:
    pass

style.configure(
    "TCombobox",
    fieldbackground=CARD_2,
    background=CARD_2,
    foreground=TEXT,
    arrowcolor=WHITE,
    borderwidth=0,
    padding=6
)
style.map("TCombobox", fieldbackground=[("readonly", CARD_2)], foreground=[("readonly", TEXT)])

login_screen()
root.mainloop()
