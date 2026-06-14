```python
readme_content = """# Discovote: End-to-End Verifiable Electronic Voting Protocol via Discord

Discovote is an end-to-end (E2E) verifiable electronic voting protocol prototype inspired by the **Belenios** framework. It leverages **Discord** as a public Bulletin Board and communication channel for election management, while using a **local Tkinter desktop application** to perform zero-knowledge proof (ZKP) generations and verifiable encryption directly on the voter's machine. 

This architecture guarantees complete voter privacy, prevents election authorities from seeing cleartext votes, provides individual verifiability, and eliminates complex web hosting infrastructures (DNS, domain names, SSL/TLS certificate authorities).

---

## 1. System Architecture & Components

The system is organized into decoupled modules that communicate securely via Discord messages, file attachments, and a shared SQLite state database (`belenios.db`).

* **`shared.py`**: The cryptographic and database foundation. Contains the parameters for ElGamal and RSA, ZKP generation/verification functions, and the hybrid encryption layer.
* **`bot_server.py`**: Actively manages the ballot box and election state. It acts as the public Bulletin Board. It audits client ZKPs before accepting ballots and handles homomorphic aggregation.
* **`client_app.py`**: A secure local Python Tkinter UI application. It runs completely offline/locally on the voter's computer to guarantee true end-to-end encryption. It encrypts votes and compiles proofs into a `ballot.json` file.
* **`bot_credentials.py`**: The Registration Authority. Validates voter eligibility, generates cryptographic credentials, encrypts them with the client's constant RSA public key, and delivers them via secure Discord Direct Messages (DMs).
* **`bot_authority_1.py`, `_2.py`, `_3.py`**: Three distinct Decryption Authorities. Each holds a shard of the election's master private key. They must independently compute and submit partial decryptions with Chaum-Pedersen ZKPs to tally the results.

---

## 2. Cryptographic Specifications

* **Asymmetric Homomorphic Encryption**: Exponential ElGamal over a prime field ($P = 107$, $G = 2$ for toy simulation) to enable homomorphic addition. Ballots are encrypted as vectors representing candidates (`[1, 0, 0, 0]`).
* **Zero-Knowledge Proofs (ZKP)**:
    * **Disjunctive Proofs (CDS Protocol)**: Proves that each encrypted slot in the ballot vector is exactly a `0` or a `1` without revealing which is which.
    * **Unitary Sum Proof**: Proves that the homomorphic sum of the vector slots equals exactly `1`, preventing malicious voters from voting for multiple candidates simultaneously.
    * **Chaum-Pedersen Proof**: Used by the Decryption Authorities during the tally phase to prove that their partial decryptions are honest and derived from their respective private keys.
* **Transport-Layer Hybrid Encryption (E2EE)**:
    * All voting credentials sent by the registration bot are encrypted with the **Client's constant RSA Public Key**.
    * All final ballot files submitted to Discord are encrypted with the **Server's constant RSA Public Key**.
    * Large payloads are handled via **Hybrid Encryption**: an ephemeral AES-256 key (Fernet) encrypts the JSON payload, and the AES key is wrapped inside an RSA-2048 envelope using OAEP padding with SHA-256.

---

## 3. Prerequisites & Installation

### Dependencies
The project requires Python 3.8+ and the following standard packages:
* `discord.py` (v2.0+)
* `cryptography` (for RSA and AES Fernet operations)

### Installation
Install the necessary modules using `pip`:

```

```text
README.md successfully generated.

```bash
pip install discord.py cryptography

```

---

## 4. Step-by-Step Demonstration Guide

Follow this guide to execute a complete, verifiable election from scratch.

### Step 1: Clean State Setup

If you have run previous simulations, wipe old states to avoid cryptographic key or database schema mismatches:

```bash
# Delete old database and secret files if they exist
rm -f belenios.db secrets_Auth1.json secrets_Auth2.json secrets_Auth3.json

```

### Step 2: Launch the Infrastructure

Open five distinct terminal windows and launch each component:

```bash
python bot_server.py
python bot_credentials.py
python bot_authority_1.py
python bot_authority_2.py
python bot_authority_3.py

```

*(Ensure you have replaced the placeholder tokens inside each file with your actual Discord Bot tokens).*

### Step 3: Initialize the Election

In an administrative or public channel on your Discord server, use the Server Bot to create a new election specifying the candidates:

```text
!server init GeneralElection Alice Bob Charlie Dave

```

*The server will record the election status as `WAITING`.*

### Step 4: Distributed Key Generation (DKG)

Each Decryption Authority must now generate its key pair and join the election. Run the following commands sequentially:

```text
!auth1 join GeneralElection
!auth2 join GeneralElection
!auth3 join GeneralElection

```

*Each authority writes its private key shard to a local file (`secrets_AuthX.json`) and publishes its public shard to the database.*

### Step 5: Open the Polls

Instruct the Server Bot to combine the public shards ($H = h_1 \cdot h_2 \cdot h_3 \pmod P$) and open the election:

```text
!server open GeneralElection

```

*The status is now upgraded to `OPEN`. Jeton generation is now unlocked.*

### Step 6: Issue Voter Credentials

Register an eligible voter and securely generate their smart participation token. Execute:

```text
!id add GeneralElection @VoterUsername

```

*The Credential Bot will securely generate a 12-character private credential, package it with the candidates and master public key, encrypt it using the constant Client RSA Public Key, and send the cipher block to the user via Direct Message (DM).*

### Step 7: Local Vote Encryption (Client App)

1. The voter launches the offline desktop application:
```bash
python client_app.py

```


2. Paste the encrypted Base64 block received in DMs into **Step 1** of the UI and click **Decrypt and Verify Token**.
3. The app uses the local constant `CLIENT_RSA_PRIV` key to unlock the token and displays the candidate list (`Alice`, `Bob`, `Charlie`, `Dave`).
4. Select a candidate (e.g., `Bob`) and click **Encrypt My Vote**. The application computes the ElGamal ciphertexts, generates the slot ZKPs, wraps the package inside a master structure containing the election metadata, and performs a **Hybrid Encryption** targeting the Server's constant RSA Public Key.
5. Click **Save ballot.json** and select a folder. The application will also display your unique **Tracking Hash** (e.g., `e3b0c44298fc1c14`).

### Step 8: Casting the Ballot on Discord

Go back to the Discord server, drag and drop the newly created `ballot.json` file into the channel text bar, type the following command as the comment/caption, and send it:

```text
!server process_vote

```

*The Server Bot intercepts the payload, decrypts it using its constant `SERVER_RSA_PRIV` key, verifies that the credential has not voted yet, audits the disjunctive ZKPs for all slots, checks the unitary sum proof, and stores the ballot. The voter receives a confirmation DM with their tracking hash.*

### Step 9: Closing the Urn

Once all voters have submitted their ballots, close the ballot box to trigger the homomorphic multiplication of the ciphertexts:

```text
!server close GeneralElection

```

*The Server Bot multiplies the $C_1$ and $C_2$ coordinates of all valid ballots for each candidate slot independently.*

### Step 10: Decentralized Decryption

The Server Bot cannot decrypt the results alone. Each authority must perform a partial decryption on the aggregated $C_1$ values using their private key shard:

```text
!auth1 decrypt GeneralElection
!auth2 decrypt GeneralElection
!auth3 decrypt GeneralElection

```

*Each authority computes $D_i = C_{1\_total}^{x_i}$ along with a Chaum-Pedersen correctness proof and uploads it to the database.*

### Step 11: Final Tally & Verifiability

Execute the final compilation command:

```text
!server tally GeneralElection

```

*The Server Bot verifies the ZKP of each authority. If valid, it combines the decryptions ($D_{total} = D_1 \cdot D_2 \cdot D_3$), calculates the plaintext points ($G^{Score} = C_{2\_total} \cdot D_{total}^{-1}$), and runs a discrete logarithm brute force to output the certified final scores.*

To verify individual inclusion, any user can inspect the public urn tracking sheet by running:

```text
!server public_urn GeneralElection

```

---

## 5. Security Property Analysis Framework

When drafting your academic report based on this prototype, use the following matrix as defined in section 4 of the guidelines:

| Property | Status | Mechanism / Assumption |
| --- | --- | --- |
| **Eligibility** | **Satisfied** | Cryptographic check against `cred_public` table and strict `has_voted` Boolean constraints. |
| **Authentication** | **Satisfied** | Relies on the security of Discord's OAuth2 accounts and private DM channels for initial token dispatch. |
| **Fairness** | **Satisfied** | Guaranteed by distributed ElGamal encryption. No partial results can be leaked until all 3 authorities execute `!authX decrypt`. |
| **Integrity** | **Satisfied** | Recomputation of the homomorphic sum and strict enforcement of client ZKPs (`verify_client_zkp_01` and `verify_client_zkp_sum`) prevents adversarial data tampering. |
| **Individual Verifiability** | **Satisfied** | Voters can audit the presence of their locally generated tracking hash inside the bulletin board via `!server public_urn`. |
| **Universal Verifiability** | **Partially Satisfied** | Anyone can check authority ZKPs, but the database administrator is assumed honest regarding initial voter list inflation. |
| **Robusteness** | **Partially Satisfied** | Current protocol requires a $3/3$ threshold. If one authority disappears, the election freezes (requires Shamir Threshold scheme for $t/n$ mitigation). |
| **Coercion Resistance** | **Not Satisfied** | The randomization value $r$ is generated and known by the client application, meaning a receipt can technically be produced. |

---

## 6. Known Configuration Limits

* **Static Cryptographic Keys**: As per design specification constraints, the RSA public and private key pairs (`SERVER_RSA_PUB`, `CLIENT_RSA_PUB`, etc.) are held constant across executions. They are stored inside static `.pem` files generated automatically upon first initialization to ensure cross-process communication consistency. A production deployment would require an ephemeral Key-Exchange Layer (e.g., Diffie-Hellman) or a formal Public Key Infrastructure (PKI).
"""

with open("README.md", "w", encoding="utf-8") as f:
f.write(readme_content)

print("README.md successfully generated.")

```
Votre fichier Markdown (README) est prêt
[file-tag: code-generated-file-0-1781467590049311202]

Voici le fichier `README.md` complet pour votre projet "Discovote". Il a été rédigé en anglais pour s'aligner parfaitement avec le code source et les commandes du projet, tout en respectant scrupuleusement les consignes de votre document (section 5.2 du cahier des charges).

Ce document comprend :
1. **L'architecture et les composants :** Une explication du rôle de chaque fichier Python.
2. **Les spécifications cryptographiques :** La description du chiffrement ElGamal, des preuves ZKP et du chiffrement hybride RSA/AES.
3. **Les prérequis et l'installation :** Les instructions pour installer les dépendances nécessaires (`discord.py`, `cryptography`).
4. **Le guide de démonstration étape par étape :** Un script clair et reproductible illustrant une élection complète de bout en bout (comme exigé pour la soutenance), de l'initialisation jusqu'au dépouillement final.
5. **Le cadre d'analyse des propriétés de sécurité :** Un tableau reprenant les propriétés exigées dans le document, pour aider à la lecture du projet.

Vous pouvez placer ce fichier directement à la racine de votre dossier de code source pour finaliser votre livrable. Si vous avez besoin d'autres ajustements pour la soutenance, n'hésitez pas !

```
