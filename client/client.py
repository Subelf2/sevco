import tkinter as tk
from tkinter import messagebox
import threading
import hashlib

try:
    from crypto_utils import load_public_key, verify_participation_token, encrypt_vote
except ImportError:
    messagebox.showerror("Erreur", "crypto_utils introuvable.\nPlace crypto_utils.py dans le même dossier.")
    raise SystemExit

BASE_H = 480


class VoteApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Vote Sécurisé")
        self.resizable(True, True)
        self.minsize(400, 380)
        self.geometry("560x480")
        self.configure(padx=24, pady=20)

        self.public_key = load_public_key()
        self.session_data = None
        self.choice_var = tk.IntVar(value=-1)
        self._scalable = []

        self.bind("<Configure>", self._on_resize)
        self._build_step1()

    # ── Fonts ─────────────────────────────────────────────────────────────

    def _sizes(self):
        ratio = max(0.7, self.winfo_height() / BASE_H)
        return {
            "title": max(10, round(12 * ratio)),
            "body":  max(9,  round(11 * ratio)),
            "mono":  max(8,  round(9  * ratio)),
            "small": max(8,  round(10 * ratio)),
            "btn":   max(9,  round(10 * ratio)),
            "warn":  max(9,  round(11 * ratio)),
        }

    def _on_resize(self, event):
        if event.widget is not self:
            return
        self._apply_fonts()

    def _apply_fonts(self):
        """Applique les tailles courantes à tous les widgets enregistrés."""
        s = self._sizes()
        for widget, role in self._scalable:
            try:
                family = "Courier" if role == "mono" else ""
                widget.configure(font=(family, s[role]))
            except tk.TclError:
                pass

    def _track_widget(self, widget, role):
        self._scalable.append((widget, role))
        # Applique immédiatement la taille courante (corrige le resize à la transition)
        s = self._sizes()
        family = "Courier" if role == "mono" else ""
        try:
            widget.configure(font=(family, s[role]))
        except tk.TclError:
            pass
        return widget

    # ── Step 1 : saisie du token ──────────────────────────────────────────

    def _build_step1(self):
        self._scalable.clear()
        self.frame = tk.Frame(self)
        self.frame.pack(fill="both", expand=True)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(2, weight=1)

        self._track_widget(
            tk.Label(self.frame, text="Token de participation", anchor="w"),
            "title"
        ).grid(row=0, column=0, sticky="ew", pady=(0, 2))

        self._track_widget(
            tk.Label(self.frame, text="Colle ton token ci-dessous :", anchor="w", fg="gray"),
            "small"
        ).grid(row=1, column=0, sticky="ew", pady=(0, 4))

        self.token_text = tk.Text(self.frame, wrap="word")
        self.token_text.grid(row=2, column=0, sticky="nsew")
        self._track_widget(self.token_text, "mono")

        self.btn_verify = tk.Button(self.frame, text="Vérifier le token", command=self._verify_thread)
        self.btn_verify.grid(row=3, column=0, pady=(10, 0), sticky="ew")
        self._track_widget(self.btn_verify, "btn")

        self.status_lbl = tk.Label(self.frame, text="", fg="red", anchor="w")
        self.status_lbl.grid(row=4, column=0, sticky="ew", pady=(4, 0))
        self._track_widget(self.status_lbl, "small")

    def _verify_thread(self):
        self.btn_verify.config(state="disabled", text="Vérification…")
        self.status_lbl.config(text="")
        threading.Thread(target=self._do_verify, daemon=True).start()

    def _do_verify(self):
        token = self.token_text.get("1.0", "end").strip()
        if not token:
            self.after(0, lambda: self._set_status("Colle un token d'abord."))
            self.after(0, lambda: self.btn_verify.config(state="normal", text="Vérifier le token"))
            return
        try:
            data = verify_participation_token(token, self.public_key)
            self.session_data = data
            self.after(0, self._show_step2)
        except Exception:
            self.after(0, lambda: self._set_status("Token invalide ou corrompu."))
            self.after(0, lambda: self.btn_verify.config(state="normal", text="Vérifier le token"))

    # ── Step 2 : choix du candidat ────────────────────────────────────────

    def _show_step2(self):
        self.frame.destroy()
        self._scalable.clear()
        self.frame = tk.Frame(self)
        self.frame.pack(fill="both", expand=True)
        self.frame.columnconfigure(0, weight=1)

        sid = self.session_data["session_id"]
        candidates = self.session_data["candidates"]

        self._track_widget(
            tk.Label(self.frame, text=f"Session : {sid}", anchor="w", fg="gray"),
            "small"
        ).grid(row=0, column=0, sticky="ew")

        self._track_widget(
            tk.Label(self.frame, text="Choisis un candidat", anchor="w"),
            "title"
        ).grid(row=1, column=0, sticky="ew", pady=(8, 6))

        self.choice_var.set(-1)
        for i, name in enumerate(candidates):
            rb = tk.Radiobutton(self.frame, text=name, variable=self.choice_var, value=i, anchor="w")
            rb.grid(row=2 + i, column=0, sticky="ew", pady=2)
            self._track_widget(rb, "body")

        next_row = 2 + len(candidates)

        self.btn_vote = tk.Button(self.frame, text="Chiffrer mon vote", command=self._vote_thread)
        self.btn_vote.grid(row=next_row, column=0, pady=(12, 0), sticky="ew")
        self._track_widget(self.btn_vote, "btn")

        self.status_lbl = tk.Label(self.frame, text="", fg="red", anchor="w")
        self.status_lbl.grid(row=next_row + 1, column=0, sticky="ew", pady=(4, 0))
        self._track_widget(self.status_lbl, "small")

    def _vote_thread(self):
        if self.choice_var.get() == -1:
            self._set_status("Sélectionne un candidat.")
            return
        self.btn_vote.config(state="disabled", text="Chiffrement…")
        self.status_lbl.config(text="")
        threading.Thread(target=self._do_vote, daemon=True).start()

    def _do_vote(self):
        try:
            participation_id = self.session_data["participation_id"]
            choice = self.choice_var.get()
            vote_data = {
                "session_id": self.session_data["session_id"],
                "participation_id": participation_id,
                "choice": choice,
            }
            raw = f"{participation_id}|{choice}".encode()
            vote_hash = hashlib.sha256(raw).hexdigest()
            encrypted = encrypt_vote(vote_data, self.public_key)
            self.after(0, lambda: self._show_step3(encrypted, vote_hash))
        except Exception as e:
            self.after(0, lambda: self._set_status(f"Erreur : {e}"))
            self.after(0, lambda: self.btn_vote.config(state="normal", text="Chiffrer mon vote"))

    # ── Step 3 : token + contre-valeur ───────────────────────────────────

    def _show_step3(self, encrypted, vote_hash):
        self.frame.destroy()
        self._scalable.clear()
        self.frame = tk.Frame(self)
        self.frame.pack(fill="both", expand=True)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)  # zone token s'étire

        # ── Token ──
        self._track_widget(
            tk.Label(self.frame, text="Token de vote", anchor="w"),
            "title"
        ).grid(row=0, column=0, sticky="ew", pady=(0, 4))

        token_text = tk.Text(self.frame, wrap="word")
        token_text.insert("1.0", encrypted)
        token_text.config(state="disabled")
        token_text.grid(row=1, column=0, sticky="nsew")
        self._track_widget(token_text, "mono")

        # Boutons token — sur une seule ligne, bien espacés
        row_btn1 = tk.Frame(self.frame)
        row_btn1.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        row_btn1.columnconfigure((0, 1), weight=1)

        btn_copy_token = tk.Button(row_btn1, text="📋  Copier le token", command=lambda: self._copy(encrypted))
        btn_copy_token.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self._track_widget(btn_copy_token, "btn")

        btn_restart = tk.Button(row_btn1, text="← Recommencer", command=self._restart)
        btn_restart.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        self._track_widget(btn_restart, "btn")

        # ── Séparateur ──
        tk.Frame(self.frame, height=1, bg="#cccccc").grid(
            row=3, column=0, sticky="ew", pady=(14, 0)
        )

        # ── Bloc contre-valeur ──
        warn_frame = tk.Frame(self.frame, bg="#fff8e1", relief="flat", bd=0)
        warn_frame.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        warn_frame.columnconfigure(1, weight=1)

        # Pictogramme
        lbl_icon = tk.Label(warn_frame, text="⚠️", bg="#fff8e1")
        lbl_icon.grid(row=0, column=0, rowspan=2, padx=(10, 8), pady=10, sticky="n")
        self._track_widget(lbl_icon, "warn")

        lbl_warn_title = tk.Label(
            warn_frame,
            text="Note ta contre-valeur (important)",
            anchor="w", bg="#fff8e1", fg="#7a5c00"
        )
        lbl_warn_title.grid(row=0, column=1, sticky="ew", pady=(10, 2))
        self._track_widget(lbl_warn_title, "body")

        hash_text = tk.Text(self.frame, height=2, wrap="word")
        hash_text.insert("1.0", vote_hash)
        hash_text.config(state="disabled")
        hash_text.grid(row=5, column=0, sticky="ew", pady=(6, 0))
        self._track_widget(hash_text, "mono")

        btn_copy_hash = tk.Button(
            self.frame, text="📋  Copier la contre-valeur",
            command=lambda: self._copy(vote_hash)
        )
        btn_copy_hash.grid(row=6, column=0, sticky="ew", pady=(6, 0))
        self._track_widget(btn_copy_hash, "btn")

        self.status_lbl = tk.Label(self.frame, text="", fg="gray", anchor="w")
        self.status_lbl.grid(row=7, column=0, sticky="ew", pady=(4, 0))
        self._track_widget(self.status_lbl, "small")

    # ── Helpers ───────────────────────────────────────────────────────────

    def _copy(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        self._set_status("✅ Copié !")

    def _restart(self):
        self.frame.destroy()
        self.session_data = None
        self._build_step1()

    def _set_status(self, msg):
        self.status_lbl.config(text=msg)


if __name__ == "__main__":
    app = VoteApp()
    app.mainloop()