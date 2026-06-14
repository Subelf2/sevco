Étape 1 : Nettoyage de printemps
Si vous avez déjà fait des tests auparavant, supprimez les anciens fichiers pour repartir à zéro. Dans votre dossier, supprimez (s'ils existent) :
belenios.db, secrets_Auth1.json, secrets_Auth2.json, secrets_Auth3.json, server_rsa.pem, client_rsa.pem.

Étape 2 : Allumer l'infrastructure
Ouvrez 5 terminaux différents (un pour chaque bot) et lancez-les un par un :

Bash
python bot_server.py
python bot_credentials.py
python bot_authority_1.py
python bot_authority_2.py
python bot_authority_3.py
Vos bots devraient maintenant apparaître "En ligne" sur votre serveur Discord.

Étape 3 : Créer l'élection
Sur votre serveur Discord, tapez cette commande pour créer une élection avec vos candidats :

Plaintext
!server init MonElection Alice Bob Charlie
Étape 4 : Les Autorités rejoignent (Sécurité)
Pour garantir qu'une seule personne ne puisse pas tricher, le pouvoir de dépouillement est divisé en 3. Chaque bot "Autorité" doit rejoindre l'élection :

Plaintext
!auth1 join MonElection
!auth2 join MonElection
!auth3 join MonElection
Étape 5 : Ouvrir les votes
Maintenant que la sécurité est en place, le serveur peut ouvrir l'élection :

Plaintext
!server open MonElection
Étape 6 : Inscrire un électeur
Le système a besoin de distribuer une "carte d'électeur" secrète. Mentionnez l'utilisateur Discord qui a le droit de voter (par exemple, vous-même) :

Plaintext
!id add MonElection @VotrePseudo
Le Bot d'Identification va vous envoyer un Message Privé contenant un gros bloc de texte chiffré. C'est votre Jeton de Vote.

Étape 7 : Voter (Sur votre ordinateur)
Pour que Discord ne voie jamais votre vote en clair, le vote se fait sur une application externe.

Lancez l'application locale depuis un terminal :

Bash
python client_app.py
Dans la fenêtre qui s'ouvre, collez le gros bloc de texte reçu en Message Privé.

Cliquez sur Decrypt and Verify Token.

Choisissez votre candidat (Alice, Bob ou Charlie) et cliquez sur Encrypt My Vote.

Cliquez sur Save ballot.json et enregistrez le fichier sur votre Bureau. Gardez un œil sur le Numéro de Suivi (Tracking Hash) affiché !

Étape 8 : Déposer le vote dans l'urne
Retournez sur Discord. Glissez-déposez votre fichier ballot.json dans le salon textuel et accompagnez-le de cette commande avant de l'envoyer :

Plaintext
!server process_vote
Le Serveur va vérifier les mathématiques complexes (ZKP) de votre fichier et l'insérer dans l'urne.

Étape 9 : Fermer l'urne
Une fois que tout le monde a voté, clôturez l'élection :

Plaintext
!server close MonElection
Étape 10 : Le Dépouillement
Le Serveur ne peut pas lire les votes seul. Il faut demander aux 3 Autorités d'utiliser leurs clés secrètes pour lancer le déchiffrement :

Plaintext
!auth1 decrypt MonElection
!auth2 decrypt MonElection
!auth3 decrypt MonElection
Étape 11 : Les Résultats !
Une fois que les 3 autorités ont fait leur travail, demandez au serveur de compiler les résultats finaux :

Plaintext
!server tally MonElection
Félicitations, vous venez de réaliser une élection cryptographique de bout en bout !

🔍 3. Vérifiabilité Individuelle
À tout moment, n'importe quel électeur peut vérifier que son vote n'a pas été perdu ou supprimé en demandant au serveur d'afficher tous les Numéros de Suivi présents dans l'urne :

Plaintext
!server public_urn MonElection
Cherchez-y le numéro que l'application locale vous avait donné à l'Étape 7 !
