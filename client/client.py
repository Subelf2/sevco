import tkinter as tk
from tkinter import messagebox
import threading

try:
    from crypto_utils import load_public_key, verify_participation_token, encrypt_vote
except ImportError:
    messagebox.showerror("Erreur", "crypto_utils introuvable.\nPlace crypto_utils.py dans le même dossier.")
    raise SystemExit

BASE_H = 420  # hauteur de référence pour le calcul de police


class VoteApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Vote Sécurisé")
        self.resizable(True, True)
        self.minsize(360, 300)
        self.geometry("540x420")
        self.configure(padx=24, pady=20)

        self.public_key = load_public_key()
        self.session_data = None
        self.choice_var = tk.IntVar(value=-1)

        # Tous les widgets à rescaler sont enregistrés ici
        # sous la forme (widget, role) où role ∈ {title, body, mono, small, btn}
        self._scalable = []

        self.bind("<Configure>", self._on_resize)
        self._build_step1()

    # ── Fonts ─────────────────────────────────────────────────────────────

    def _sizes(self):
        """Retourne les tailles de police selon la hauteur courante."""
        ratio = self.winfo_height() / BASE_H
        return {
            "title": max(10, round(11 * ratio)),
            "body":  max(9,  round(10 * ratio)),
            "mono":  max(8,  round(9  * ratio)),
            "small": max(8,  round(9  * ratio)),
            "btn":   max(9,  round(10 * ratio)),
        }

    def _font(self, role, bold=False):
        s = self._sizes()
        return ("Courier" if role == "mono" else "", s[role], "bold" if bold else "")

    def _on_resize(self, event):
        if event.widget is not self:
            return
        s = self._sizes()
        for widget, role in self._scalable:
            try:
                family = "Courier" if role == "mono" else ""
                widget.configure(font=(family, s[role]))
            except tk.TclError:
                pass  # widget détruit

    def _register_for_scaling(self, widget, role):
        self._scalable.append((widget, role))
        return widget

    # ── Step 1 : saisie du token ──────────────────────────────────────────

    def _build_step1(self):
        self._scalable.clear()
        self.frame = tk.Frame(self)
        self.frame.pack(fill="both", expand=True)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(2, weight=1)  # textarea s'étire

        lbl_title = tk.Label(self.frame, text="Token de participation", anchor="w")
        lbl_title.grid(row=0, column=0, sticky="ew", pady=(0, 2))
        self._register_for_scaling(lbl_title, "title")

        lbl_sub = tk.Label(self.frame, text="Colle ton token ci-dessous :", anchor="w", fg="gray")
        lbl_sub.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        self._register_for_scaling(lbl_sub, "small")

        self.token_text = tk.Text(self.frame, font=("Courier", 9), wrap="word")
        self.token_text.grid(row=2, column=0, sticky="nsew")
        self._register_for_scaling(self.token_text, "mono")

        self.btn_verify = tk.Button(self.frame, text="Vérifier le token", command=self._verify_thread, bg="darkgray")
        self.btn_verify.grid(row=3, column=0, pady=(10, 0), sticky="ew")
        self._register_for_scaling(self.btn_verify, "btn")

        self.status_lbl = tk.Label(self.frame, text="", fg="red", anchor="w")
        self.status_lbl.grid(row=4, column=0, sticky="ew", pady=(4, 0))
        self._register_for_scaling(self.status_lbl, "small")

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

        lbl_sid = tk.Label(self.frame, text=f"Session : {sid}", anchor="w", fg="gray")
        lbl_sid.grid(row=0, column=0, sticky="ew")
        self._register_for_scaling(lbl_sid, "small")

        lbl_title = tk.Label(self.frame, text="Choisis un candidat", anchor="w")
        lbl_title.grid(row=1, column=0, sticky="ew", pady=(8, 6))
        self._register_for_scaling(lbl_title, "title")

        self.choice_var.set(-1)
        for i, name in enumerate(candidates):
            rb = tk.Radiobutton(self.frame, text=name, variable=self.choice_var, value=i, anchor="w")
            rb.grid(row=2 + i, column=0, sticky="ew", pady=2)
            self._register_for_scaling(rb, "body")

        next_row = 2 + len(candidates)

        self.btn_vote = tk.Button(self.frame, text="Chiffrer mon vote", command=self._vote_thread)
        self.btn_vote.grid(row=next_row, column=0, pady=(12, 0), sticky="ew")
        self._register_for_scaling(self.btn_vote, "btn")

        self.status_lbl = tk.Label(self.frame, text="", fg="red", anchor="w")
        self.status_lbl.grid(row=next_row + 1, column=0, sticky="ew", pady=(4, 0))
        self._register_for_scaling(self.status_lbl, "small")

    def _vote_thread(self):
        if self.choice_var.get() == -1:
            self._set_status("Sélectionne un candidat.")
            return
        self.btn_vote.config(state="disabled", text="Chiffrement…")
        self.status_lbl.config(text="")
        threading.Thread(target=self._do_vote, daemon=True).start()

    def _do_vote(self):
        try:
            vote_data = {
                "session_id": self.session_data["session_id"],
                "participation_id": self.session_data["participation_id"],
                "choice": self.choice_var.get(),
            }
            encrypted = encrypt_vote(vote_data, self.public_key)
            self.after(0, lambda: self._show_step3(encrypted))
        except Exception as e:
            self.after(0, lambda: self._set_status(f"Erreur : {e}"))
            self.after(0, lambda: self.btn_vote.config(state="normal", text="Chiffrer mon vote"))

    # ── Step 3 : affichage du token de vote ──────────────────────────────

    def _show_step3(self, encrypted):
        self.frame.destroy()
        self._scalable.clear()
        self.frame = tk.Frame(self)
        self.frame.pack(fill="both", expand=True)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(2, weight=1)  # textarea s'étire

        lbl_title = tk.Label(self.frame, text="Token de vote", anchor="w")
        lbl_title.grid(row=0, column=0, sticky="ew")
        self._register_for_scaling(lbl_title, "title")

        lbl_sub = tk.Label(self.frame, text="Copie ce token et envoie-le avec $vote", anchor="w", fg="gray")
        lbl_sub.grid(row=1, column=0, sticky="ew", pady=(2, 6))
        self._register_for_scaling(lbl_sub, "small")

        result_text = tk.Text(self.frame, font=("Courier", 9), wrap="word")
        result_text.insert("1.0", encrypted)
        result_text.config(state="disabled")
        result_text.grid(row=2, column=0, sticky="nsew")
        self._register_for_scaling(result_text, "mono")

        btn_frame = tk.Frame(self.frame)
        btn_frame.grid(row=3, column=0, pady=(10, 0), sticky="ew")
        btn_frame.columnconfigure((0, 1), weight=1)

        btn_copy = tk.Button(btn_frame, text="📋 Copier", command=lambda: self._copy(encrypted))
        btn_copy.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self._register_for_scaling(btn_copy, "btn")

        btn_restart = tk.Button(btn_frame, text="← Recommencer", command=self._restart)
        btn_restart.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        self._register_for_scaling(btn_restart, "btn")

        self.status_lbl = tk.Label(self.frame, text="", fg="gray", anchor="w")
        self.status_lbl.grid(row=4, column=0, sticky="ew", pady=(6, 0))
        self._register_for_scaling(self.status_lbl, "small")

    def _copy(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        self._set_status("✅ Copié !")

    def _restart(self):
        self.frame.destroy()
        self.session_data = None
        self._build_step1()

    # ── Helpers ───────────────────────────────────────────────────────────

    def _set_status(self, msg):
        self.status_lbl.config(text=msg)


if __name__ == "__main__":
    app = VoteApp()
    app.mainloop()