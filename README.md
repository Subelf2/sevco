# SEVCO - Encrypted End-to-End Voting Protocol

A cryptographic voting system built on Discord that prevents single-authority manipulation and allows voters to verify their ballots.

## Table of Contents

- [What is SEVCO?](#what-is-sevco)
- [Setup](#setup)
- [Quick Start](#quick-start)
- [Full Walkthrough](#full-walkthrough)
- [Ballot Verification](#ballot-verification)

---

## What is SEVCO?

SEVCO uses threshold cryptography to implement a verifiable voting protocol:

- **End-to-end encrypted**: Votes are encrypted on your machine. Discord never sees the plaintext ballot.
- **Threshold decryption**: 3 authorities each hold 1/3 of the decryption key. No single authority can decrypt votes alone.
- **Verifiable**: Every voter gets a tracking hash to confirm their ballot is in the urn.
- **Cryptographically sound**: Uses zero-knowledge proofs (ZKP) to prevent forged ballots.

### Architecture

- **5 Discord bots**: Server (election manager), Credentials (voter registration), and 3 Authorities (threshold holders)
- **Local voting app**: Python GUI that encrypts your vote without exposing it to Discord
- **Database**: Stores encrypted ballots in a secure urn

---

## Setup

### Requirements

- Python 3.8+
- Discord server (free)
- 5 terminal windows

### Installation

```bash
git clone https://github.com/Subelf2/sevco.git
cd sevco
python -m venv venv

# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate

pip install -r requirements.txt
```

### Configure Discord Bots

1. Go to https://discord.com/developers/applications
2. Create 5 applications (or use the same one with different bot tokens)
3. Add a Bot to each application and copy its token
4. Create `.env` at the project root:

```env
DISCORD_TOKEN_SERVER=your_token_here
DISCORD_TOKEN_CREDENTIALS=your_token_here
DISCORD_TOKEN_AUTH1=your_token_here
DISCORD_TOKEN_AUTH2=your_token_here
DISCORD_TOKEN_AUTH3=your_token_here
```

---

## Quick Start

Open 5 terminals and run:

```bash
# Terminal 1
python bot_server.py

# Terminal 2
python bot_credentials.py

# Terminals 3, 4, 5
python bot_authority_1.py
python bot_authority_2.py
python bot_authority_3.py
```

On Discord:

```
!server init TestElection Alice Bob Charlie
!auth1 join TestElection
!auth2 join TestElection
!auth3 join TestElection
!server open TestElection
!id add TestElection @you
```

The bot sends you a voting token in DM. Open a 6th terminal:

```bash
python client_app.py
```

Paste the token, select a candidate, save `ballot.json`. Back on Discord:

```
!server process_vote
```

(Drag-drop the file, then send the command)

Close the election:

```
!server close TestElection
!auth1 decrypt TestElection
!auth2 decrypt TestElection
!auth3 decrypt TestElection
!server tally TestElection
```

Done. Results appear.

---

## Full Walkthrough

### Step 0: Clean Up

If you ran this before, remove old test files:

```bash
rm -f belenios.db secrets_Auth*.json *_rsa.pem
```

### Step 1: Start the Infrastructure

Launch all 5 bots in separate terminals:

```bash
python bot_server.py
python bot_credentials.py
python bot_authority_1.py
python bot_authority_2.py
python bot_authority_3.py
```

Wait until all bots show "online" on Discord.

### Step 2: Create the Election

```
!server init MyElection Alice Bob Charlie
```

### Step 3: Authorities Join

Each authority holds 1/3 of the decryption key. None can decrypt alone.

```
!auth1 join MyElection
!auth2 join MyElection
!auth3 join MyElection
```

### Step 4: Open Voting

```
!server open MyElection
```

### Step 5: Register a Voter

```
!id add MyElection @yourname
```

The Credentials bot sends you a **voting token** (encrypted blob) via DM. Save it.

### Step 6: Cast Your Vote

```bash
python client_app.py
```

- Paste the voting token
- Click "Decrypt and Verify Token"
- Select your candidate
- Click "Encrypt My Vote"
- Click "Save ballot.json" to your desktop
- **Note the tracking hash displayed**

### Step 7: Submit the Ballot

Go back to Discord. Drag-drop `ballot.json` into a text channel:

```
!server process_vote
```

The server verifies the ballot cryptographically and adds it to the encrypted urn.

### Step 8: Close the Urn

```
!server close MyElection
```

### Step 9: Decrypt

Each authority decrypts their share:

```
!auth1 decrypt MyElection
!auth2 decrypt MyElection
!auth3 decrypt MyElection
```

### Step 10: Tally Results

```
!server tally MyElection
```

Results appear. Election complete.

---

## Ballot Verification

At any time, verify your ballot was recorded:

```
!server public_urn MyElection
```

Look for your tracking hash from Step 6. If it's there, your ballot made it into the urn.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Bots won't start | Check `.env` tokens are valid. Verify dependencies: `pip install -r requirements.txt` |
| "Token expired" error | Regenerate tokens on https://discord.com/developers/applications |
| `client_app.py` won't start | Install tkinter: `pip install tkinter` (usually included with Python) |

---

## References

This project implements the **Belenios** voting protocol.

- Belenios docs: https://www.belenios.org/
- ZKP cryptography: https://en.wikipedia.org/wiki/Zero-knowledge_proof

---

**Vote responsibly.**
