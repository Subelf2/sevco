import tkinter as tk
from tkinter import filedialog
import threading
import hashlib
import json
import os

try:
    from shared import encrypt_vector, hash_credential, hybrid_encrypt, hybrid_decrypt, CLIENT_RSA_PRIV, SERVER_RSA_PUB
except ImportError:
    import tkinter.messagebox as mb
    mb.showerror("Error", "shared.py not found. Ensure it is in the same directory.")
    raise SystemExit

BASE_H = 480

class VoteApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Secure Voting Client")
        self.geometry("600x550")
        self.minsize(450, 400)
        self.configure(padx=24, pady=20)

        self.session_data = None
        self.choice_var = tk.IntVar(value=-1)
        self._scalable = []

        self.bind("<Configure>", self._on_resize)
        self._build_step1()

    def _sizes(self):
        ratio = max(0.7, self.winfo_height() / BASE_H)
        return {
            "title": max(10, round(12 * ratio)),
            "body":  max(9,  round(11 * ratio)),
            "mono":  max(8,  round(9  * ratio)),
            "small": max(8,  round(10 * ratio)),
            "btn":   max(9,  round(10 * ratio)),
        }

    def _on_resize(self, event):
        if event.widget is self:
            self._apply_fonts()

    def _apply_fonts(self):
        s = self._sizes()
        for widget, role in self._scalable:
            try:
                family = "Courier" if role == "mono" else ""
                widget.configure(font=(family, s[role]))
            except tk.TclError:
                pass

    def _track_widget(self, widget, role):
        self._scalable.append((widget, role))
        s = self._sizes()
        family = "Courier" if role == "mono" else ""
        try:
            widget.configure(font=(family, s[role]))
        except tk.TclError:
            pass
        return widget

    # ── Step 1: Token Input ───────────────────────────────────────────────
    def _build_step1(self):
        self._scalable.clear()
        self.frame = tk.Frame(self)
        self.frame.pack(fill="both", expand=True)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(2, weight=1)

        self._track_widget(tk.Label(self.frame, text="Encrypted Participation Token", anchor="w"), "title").grid(row=0, column=0, sticky="ew", pady=(0, 2))
        self._track_widget(tk.Label(self.frame, text="Paste the encrypted block received from the Election Server:", anchor="w", fg="gray"), "small").grid(row=1, column=0, sticky="ew", pady=(0, 4))

        self.token_text = tk.Text(self.frame, wrap="word")
        self.token_text.grid(row=2, column=0, sticky="nsew")
        self._track_widget(self.token_text, "mono")

        self.btn_verify = tk.Button(self.frame, text="Decrypt and Verify Token", command=self._verify_thread)
        self.btn_verify.grid(row=3, column=0, pady=(10, 0), sticky="ew")
        self._track_widget(self.btn_verify, "btn")

        self.status_lbl = tk.Label(self.frame, text="", fg="red", anchor="w")
        self.status_lbl.grid(row=4, column=0, sticky="ew", pady=(4, 0))
        self._track_widget(self.status_lbl, "small")

    def _verify_thread(self):
        self.btn_verify.config(state="disabled", text="Decrypting via RSA...")
        self.status_lbl.config(text="")
        threading.Thread(target=self._do_verify, daemon=True).start()

    def _do_verify(self):
        encrypted_token = self.token_text.get("1.0", "end").strip()
        if not encrypted_token:
            self.after(0, lambda: self._set_status("Please paste the token first."))
            self.after(0, lambda: self.btn_verify.config(state="normal", text="Decrypt and Verify Token"))
            return
        try:
            # Decrypt the hybrid package using Client's Private RSA Key
            decrypted_json_str = hybrid_decrypt(encrypted_token, CLIENT_RSA_PRIV)
            data = json.loads(decrypted_json_str)
            
            required_keys = ["election", "candidates", "pub_key", "priv_cred"]
            if not all(k in data for k in required_keys):
                raise ValueError("Missing fields in token.")

            self.session_data = data
            self.after(0, self._show_step2)
        except Exception:
            self.after(0, lambda: self._set_status("Invalid or corrupted token (RSA Decryption Failed)."))
            self.after(0, lambda: self.btn_verify.config(state="normal", text="Decrypt and Verify Token"))

    # ── Step 2: Candidate Selection ───────────────────────────────────────
    def _show_step2(self):
        self.frame.destroy()
        self._scalable.clear()
        self.frame = tk.Frame(self)
        self.frame.pack(fill="both", expand=True)
        self.frame.columnconfigure(0, weight=1)

        election_name = self.session_data["election"]
        candidates = self.session_data["candidates"]

        self._track_widget(tk.Label(self.frame, text=f"Election: {election_name}", anchor="w", fg="gray"), "small").grid(row=0, column=0, sticky="ew")
        self._track_widget(tk.Label(self.frame, text="Choose a candidate", anchor="w"), "title").grid(row=1, column=0, sticky="ew", pady=(8, 6))

        self.choice_var.set(-1)
        for i, name in enumerate(candidates):
            rb = tk.Radiobutton(self.frame, text=name, variable=self.choice_var, value=i, anchor="w")
            rb.grid(row=2 + i, column=0, sticky="ew", pady=2)
            self._track_widget(rb, "body")

        next_row = 2 + len(candidates)
        self.btn_vote = tk.Button(self.frame, text="Encrypt My Vote", command=self._vote_thread)
        self.btn_vote.grid(row=next_row, column=0, pady=(12, 0), sticky="ew")
        self._track_widget(self.btn_vote, "btn")

        self.status_lbl = tk.Label(self.frame, text="", fg="red", anchor="w")
        self.status_lbl.grid(row=next_row + 1, column=0, sticky="ew", pady=(4, 0))
        self._track_widget(self.status_lbl, "small")

    def _vote_thread(self):
        if self.choice_var.get() == -1:
            self._set_status("Please select a candidate.")
            return
        self.btn_vote.config(state="disabled", text="Generating ZKPs & Encrypting...")
        self.status_lbl.config(text="")
        threading.Thread(target=self._do_vote, daemon=True).start()

    def _do_vote(self):
        try:
            chosen_index = self.choice_var.get()
            candidates = self.session_data["candidates"]
            chosen_name = candidates[chosen_index]
            pub_key = self.session_data["pub_key"]
            
            # ElGamal encryption and ZKP Generation
            encrypted_payload = encrypt_vector(chosen_name, candidates, pub_key)
            
            pub_cred = hash_credential(self.session_data["priv_cred"])
            master_payload = {
                "election_name": self.session_data["election"],
                "pub_cred": pub_cred,
                "vector": encrypted_payload["vector"],
                "zkp_sum": encrypted_payload["zkp_sum"]
            }
            
            payload_json = json.dumps(master_payload)
            tracking_number = hashlib.sha256(payload_json.encode('utf-8')).hexdigest()[:16]
            
            # Final Hybrid Encryption using Server's Public RSA Key
            encrypted_ballot_str = hybrid_encrypt(payload_json, SERVER_RSA_PUB)
            
            self.after(0, lambda: self._show_step3(encrypted_ballot_str, tracking_number))
        except Exception as e:
            self.after(0, lambda: self._set_status(f"Error: {e}"))
            self.after(0, lambda: self.btn_vote.config(state="normal", text="Encrypt My Vote"))

    # ── Step 3: Result & Submission Instructions ──────────────────────────
    def _show_step3(self, encrypted_ballot_str, tracking_number):
        self.frame.destroy()
        self._scalable.clear()
        self.frame = tk.Frame(self)
        self.frame.pack(fill="both", expand=True)
        self.frame.columnconfigure(0, weight=1)

        self._track_widget(tk.Label(self.frame, text="Encryption Complete!", anchor="w", fg="green"), "title").grid(row=0, column=0, sticky="ew", pady=(0, 4))
        self._track_widget(tk.Label(self.frame, text="1. Save your encrypted ballot file:", anchor="w"), "body").grid(row=1, column=0, sticky="ew", pady=(10, 2))
        
        btn_save = tk.Button(self.frame, text="Save ballot.json", command=lambda: self._save_file(encrypted_ballot_str))
        btn_save.grid(row=2, column=0, sticky="w")
        self._track_widget(btn_save, "btn")

        self._track_widget(tk.Label(self.frame, text="2. Send to the Server Bot on Discord:", anchor="w"), "body").grid(row=3, column=0, sticky="ew", pady=(15, 2))
        self._track_widget(tk.Label(self.frame, text="Upload the ballot.json file and paste this exact command:", anchor="w", fg="gray"), "small").grid(row=4, column=0, sticky="ew")

        discord_cmd = "!server process_vote"
        cmd_entry = tk.Entry(self.frame)
        cmd_entry.insert(0, discord_cmd)
        cmd_entry.config(state="readonly")
        cmd_entry.grid(row=5, column=0, sticky="ew", pady=(4, 10))
        self._track_widget(cmd_entry, "mono")

        self._track_widget(tk.Label(self.frame, text=f"Your Tracking Hash:\n{tracking_number}", anchor="w", fg="#7a5c00"), "small").grid(row=6, column=0, sticky="ew", pady=(10, 2))

        btn_restart = tk.Button(self.frame, text="Start Over", command=self._restart)
        btn_restart.grid(row=7, column=0, sticky="w", pady=(20, 0))
        self._track_widget(btn_restart, "btn")

        self.status_lbl = tk.Label(self.frame, text="", fg="gray", anchor="w")
        self.status_lbl.grid(row=8, column=0, sticky="ew", pady=(10, 0))
        self._track_widget(self.status_lbl, "small")

    def _save_file(self, content_str):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfile="ballot.json",
            title="Save your encrypted ballot",
            filetypes=[("JSON Files", "*.json")]
        )
        if file_path:
            with open(file_path, "w") as f:
                f.write(content_str)
            self._set_status(f"Saved: {os.path.basename(file_path)}")

    def _restart(self):
        self.frame.destroy()
        self.session_data = None
        self._build_step1()

    def _set_status(self, msg):
        self.status_lbl.config(text=msg)

if __name__ == "__main__":
    app = VoteApp()
    app.mainloop()