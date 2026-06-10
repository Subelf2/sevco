from crypto_utils import (
    load_public_key,
    verify_participation_token,
    encrypt_vote
)


def main():

    print("=== CLIENT DE VOTE ===\n")

    token = input("Colle ton token de participation :\n")

    public_key = load_public_key()

    try:
        data = verify_participation_token(token, public_key)

    except Exception:
        print("Token invalide ou corrompu.")
        return

    session_id = data["session_id"]
    candidates = data["candidates"]

    print(f"\nSession : {session_id}\n")

    for i, c in enumerate(candidates):
        print(f"{i+1}. {c}")

    try:
        choice = int(input("\nTon vote (numéro) : ")) - 1

        if choice < 0 or choice >= len(candidates):
            print("Choix invalide.")
            return

    except ValueError:
        print("Entrée invalide.")
        return

    vote_data = {
        "session_id": session_id,
        "participation_id": data["participation_id"],
        "choice": choice
    }

    encrypted_vote = encrypt_vote(vote_data, public_key)

    print("\n=== TOKEN DE VOTE ===\n")
    print(encrypted_vote)
    print("\nCopie ce token et envoie-le avec $vote")
    

if __name__ == "__main__":
    main()