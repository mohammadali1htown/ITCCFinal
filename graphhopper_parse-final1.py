import tkinter as tk
from tkinter import ttk, messagebox
import requests
import urllib.parse
import threading

KEY = "c2ffa9e5-9a7c-4798-aa1d-ed78e4cc71c9"
GEOCODE_URL = "https://graphhopper.com/api/1/geocode?"
ROUTE_URL = "https://graphhopper.com/api/1/route?"

# ── Colors ────────────────────────────────────────────────────────────────────
BG       = "#F7F6F2"
CARD_BG  = "#FFFFFF"
ACCENT   = "#1D6FA4"
BTN_BG   = "#1D6FA4"
BTN_FG   = "#FFFFFF"
TXT      = "#1C1C1A"
MUTED    = "#6B6B67"
BORDER   = "#D3D1C7"
STEP_ALT = "#F1EFE8"
SUCCESS  = "#0F6E56"
ERROR    = "#A32D2D"
ERROR_BG = "#FCEBEB"

FONT_BODY  = ("Segoe UI", 10)
FONT_BOLD  = ("Segoe UI", 10, "bold")
FONT_TITLE = ("Segoe UI", 16, "bold")
FONT_SMALL = ("Segoe UI", 9)
FONT_MONO  = ("Consolas", 9)


def geocoding(location):
    url = GEOCODE_URL + urllib.parse.urlencode({"q": location, "limit": "1", "key": KEY})
    r = requests.get(url, timeout=10)
    data = r.json()
    if r.status_code == 200 and data.get("hits"):
        h = data["hits"][0]
        lat, lng = h["point"]["lat"], h["point"]["lng"]
        parts = [h.get("name",""), h.get("state",""), h.get("country","")]
        name = ", ".join(p for p in parts if p)
        return lat, lng, name
    raise ValueError(f"Location not found: {location}")


def get_route(orig_text, dest_text, vehicle):
    olat, olng, oname = geocoding(orig_text)
    dlat, dlng, dname = geocoding(dest_text)
    op = f"&point={olat}%2C{olng}"
    dp = f"&point={dlat}%2C{dlng}"
    url = ROUTE_URL + urllib.parse.urlencode({"key": KEY, "vehicle": vehicle}) + op + dp
    r = requests.get(url, timeout=10)
    data = r.json()
    if r.status_code != 200:
        raise ValueError(data.get("message", "Routing error"))
    path = data["paths"][0]
    miles = path["distance"] / 1000 / 1.61
    km    = path["distance"] / 1000
    total_sec = path["time"] // 1000
    hr  = total_sec // 3600
    mn  = (total_sec % 3600) // 60
    sec = total_sec % 60
    steps = [(s["text"], s["distance"]) for s in path["instructions"]]
    return oname, dname, miles, km, hr, mn, sec, steps


# ── App ───────────────────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Route Planner")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(520, 480)
        self._vehicle = tk.StringVar(value="car")
        self._build_ui()

    # ── Build UI ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        outer = tk.Frame(self, bg=BG)
        outer.pack(fill="both", expand=True, padx=24, pady=20)

        # Title
        tk.Label(outer, text="Route Planner", font=FONT_TITLE,
                 bg=BG, fg=TXT).pack(anchor="w")
        tk.Label(outer, text="Powered by GraphHopper", font=FONT_SMALL,
                 bg=BG, fg=MUTED).pack(anchor="w", pady=(0, 14))

        # Input card
        card = tk.Frame(outer, bg=CARD_BG, relief="flat",
                        highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", pady=(0, 10))
        inner = tk.Frame(card, bg=CARD_BG)
        inner.pack(fill="x", padx=16, pady=14)

        tk.Label(inner, text="Starting location", font=FONT_SMALL,
                 bg=CARD_BG, fg=MUTED).pack(anchor="w")
        self.orig_entry = ttk.Entry(inner, font=FONT_BODY)
        self.orig_entry.pack(fill="x", pady=(3, 10))
        self.orig_entry.insert(0, "e.g. Houston, TX")
        self.orig_entry.bind("<FocusIn>",  lambda e: self._clear(self.orig_entry, "e.g. Houston, TX"))
        self.orig_entry.bind("<FocusOut>", lambda e: self._restore(self.orig_entry, "e.g. Houston, TX"))

        tk.Label(inner, text="Destination", font=FONT_SMALL,
                 bg=CARD_BG, fg=MUTED).pack(anchor="w")
        self.dest_entry = ttk.Entry(inner, font=FONT_BODY)
        self.dest_entry.pack(fill="x", pady=(3, 12))
        self.dest_entry.insert(0, "e.g. Austin, TX")
        self.dest_entry.bind("<FocusIn>",  lambda e: self._clear(self.dest_entry, "e.g. Austin, TX"))
        self.dest_entry.bind("<FocusOut>", lambda e: self._restore(self.dest_entry, "e.g. Austin, TX"))

        tk.Label(inner, text="Vehicle", font=FONT_SMALL,
                 bg=CARD_BG, fg=MUTED).pack(anchor="w")
        vframe = tk.Frame(inner, bg=CARD_BG)
        vframe.pack(fill="x", pady=(4, 0))
        self._vbtns = {}
        for v, label in [("car","Car"), ("bike","Bike"), ("foot","Walking")]:
            b = tk.Button(vframe, text=label, font=FONT_BODY,
                          relief="flat", cursor="hand2", bd=0,
                          command=lambda v=v: self._select_vehicle(v))
            b.pack(side="left", padx=(0, 6))
            self._vbtns[v] = b
        self._refresh_vbtns()

        # Go button
        self.go_btn = tk.Button(outer, text="Get directions →",
                                font=FONT_BOLD, bg=BTN_BG, fg=BTN_FG,
                                relief="flat", cursor="hand2", bd=0,
                                pady=9, command=self._on_go)
        self.go_btn.pack(fill="x", pady=(0, 10))
        self.bind("<Return>", lambda e: self._on_go())

        # Status label
        self.status_lbl = tk.Label(outer, text="", font=FONT_SMALL,
                                   bg=BG, fg=MUTED)
        self.status_lbl.pack(anchor="w")

        # Results area (scrollable)
        results_frame = tk.Frame(outer, bg=BG)
        results_frame.pack(fill="both", expand=True, pady=(6, 0))

        self.canvas = tk.Canvas(results_frame, bg=BG, highlightthickness=0)
        vsb = ttk.Scrollbar(results_frame, orient="vertical",
                             command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.results_inner = tk.Frame(self.canvas, bg=BG)
        self._canvas_win = self.canvas.create_window(
            (0, 0), window=self.results_inner, anchor="nw")
        self.results_inner.bind("<Configure>", self._on_frame_resize)
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.canvas.bind_all("<MouseWheel>",
                             lambda e: self.canvas.yview_scroll(-1*(e.delta//120),"units"))

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _clear(self, entry, placeholder):
        if entry.get() == placeholder:
            entry.delete(0, "end")
            entry.config(foreground=TXT)

    def _restore(self, entry, placeholder):
        if entry.get() == "":
            entry.insert(0, placeholder)
            entry.config(foreground=MUTED)

    def _select_vehicle(self, v):
        self._vehicle.set(v)
        self._refresh_vbtns()

    def _refresh_vbtns(self):
        sel = self._vehicle.get()
        for v, btn in self._vbtns.items():
            if v == sel:
                btn.config(bg=ACCENT, fg="white",
                           relief="flat", padx=14, pady=5)
            else:
                btn.config(bg="#E8E6DF", fg=TXT,
                           relief="flat", padx=14, pady=5)

    def _on_frame_resize(self, _=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_resize(self, event):
        self.canvas.itemconfig(self._canvas_win, width=event.width)

    def _set_status(self, msg, color=MUTED):
        self.status_lbl.config(text=msg, fg=color)

    def _clear_results(self):
        for w in self.results_inner.winfo_children():
            w.destroy()

    # ── Routing logic ─────────────────────────────────────────────────────────
    def _on_go(self):
        orig = self.orig_entry.get().strip()
        dest = self.dest_entry.get().strip()
        placeholders = {"e.g. Houston, TX", "e.g. Austin, TX"}
        if not orig or orig in placeholders or not dest or dest in placeholders:
            messagebox.showwarning("Missing info",
                                   "Please enter both a starting location and a destination.")
            return
        self.go_btn.config(state="disabled", text="Finding route...")
        self._set_status("Geocoding locations...", MUTED)
        self._clear_results()
        threading.Thread(target=self._fetch,
                         args=(orig, dest, self._vehicle.get()),
                         daemon=True).start()

    def _fetch(self, orig, dest, vehicle):
        try:
            result = get_route(orig, dest, vehicle)
            self.after(0, self._show_results, result, vehicle)
        except Exception as e:
            self.after(0, self._show_error, str(e))
        finally:
            self.after(0, lambda: self.go_btn.config(
                state="normal", text="Get directions →"))

    def _show_error(self, msg):
        self._clear_results()
        self._set_status("")
        err_frame = tk.Frame(self.results_inner, bg=ERROR_BG,
                             highlightbackground=ERROR, highlightthickness=1)
        err_frame.pack(fill="x", pady=4)
        tk.Label(err_frame, text=f"Error: {msg}", font=FONT_BODY,
                 bg=ERROR_BG, fg=ERROR, wraplength=460,
                 justify="left", padx=12, pady=10).pack(anchor="w")

    def _show_results(self, result, vehicle):
        oname, dname, miles, km, hr, mn, sec, steps = result
        self._clear_results()
        self._set_status(f"{oname}  →  {dname}  ({vehicle})", SUCCESS)

        # Summary cards
        summary = tk.Frame(self.results_inner, bg=BG)
        summary.pack(fill="x", pady=(4, 10))
        summary.columnconfigure(0, weight=1)
        summary.columnconfigure(1, weight=1)

        for col, (label, val, sub) in enumerate([
            ("Distance", f"{miles:.1f} mi", f"{km:.1f} km"),
            ("Duration",
             f"{hr}h {mn:02d}m" if hr else f"{mn}m {sec:02d}s",
             vehicle.capitalize()),
        ]):
            mc = tk.Frame(summary, bg=STEP_ALT,
                          highlightbackground=BORDER, highlightthickness=1)
            mc.grid(row=0, column=col, sticky="ew",
                    padx=(0 if col else 0, 6 if col == 0 else 0))
            tk.Label(mc, text=label, font=FONT_SMALL, bg=STEP_ALT,
                     fg=MUTED).pack(anchor="w", padx=12, pady=(10,0))
            tk.Label(mc, text=val, font=("Segoe UI", 18, "bold"),
                     bg=STEP_ALT, fg=TXT).pack(anchor="w", padx=12)
            tk.Label(mc, text=sub, font=FONT_SMALL, bg=STEP_ALT,
                     fg=MUTED).pack(anchor="w", padx=12, pady=(0,10))

        # Steps card
        steps_card = tk.Frame(self.results_inner, bg=CARD_BG,
                              highlightbackground=BORDER, highlightthickness=1)
        steps_card.pack(fill="x")

        for i, (text, dist_m) in enumerate(steps):
            row_bg = STEP_ALT if i % 2 == 0 else CARD_BG
            row = tk.Frame(steps_card, bg=row_bg)
            row.pack(fill="x")

            num = tk.Label(row, text=str(i+1), font=FONT_SMALL,
                           bg=row_bg, fg=MUTED, width=3, anchor="center")
            num.pack(side="left", padx=(8,4), pady=8)

            body = tk.Frame(row, bg=row_bg)
            body.pack(side="left", fill="x", expand=True, pady=6)
            tk.Label(body, text=text, font=FONT_BODY, bg=row_bg,
                     fg=TXT, anchor="w", wraplength=360,
                     justify="left").pack(anchor="w")
            d_mi = dist_m / 1000 / 1.61
            d_km = dist_m / 1000
            tk.Label(body,
                     text=f"{d_mi:.1f} mi / {d_km:.1f} km",
                     font=FONT_SMALL, bg=row_bg, fg=MUTED).pack(anchor="w")

            if i < len(steps) - 1:
                tk.Frame(steps_card, bg=BORDER, height=1).pack(fill="x")

        self._on_frame_resize()


if __name__ == "__main__":
    app = App()
    app.mainloop()
