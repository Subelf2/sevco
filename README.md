# SEVCO - Protocole de Vote Électronique Sécurisé

Bienvenue dans **SEVCO**, un système de vote cryptographique de bout en bout basé sur Discord. Ce projet permet des élections sécurisées où aucune autorité unique ne peut tricher et où chaque électeur peut vérifier son vote.

## 📋 Table des matières

- [Qu'est-ce que SEVCO ?](#quest-ce-que-sevco-)
- [Installation des dépendances](#installation-des-dépendances)
- [Guide de démarrage rapide](#guide-de-démarrage-rapide)
- [Démonstration complète étape par étape](#démonstration-complète-étape-par-étape)
- [Vérifiabilité individuelle](#vérifiabilité-individuelle)

---

## Qu'est-ce que SEVCO ?

SEVCO est un protocole de vote électronique qui garantit :

- **Sécurité** : Les votes sont chiffrés de bout en bout, même Discord ne peut pas les lire
- **Intégrité** : Aucune autorité unique ne peut manipuler l'élection (distribution du pouvoir en 3)
- **Vérifiabilité** : Chaque électeur peut vérifier que son vote a été enregistré correctement
- **Transparence** : Le système utilise la cryptographie à preuve sans connaissance (ZKP)

### Comment ça marche ?

1. **Bots Discord** : Coordonnent l'élection et vérifient les mathématiques cryptographiques
2. **3 Autorités** : Détiennent chacune 1/3 de la clé de déchiffrement finale
3. **Client local** : Application Python pour chiffrer votre vote en privé, sans que Discord ne le voie
4. **Base de données** : Stocke les votes chiffrés dans une urne sécurisée

---

## Installation des dépendances

### Prérequis système

- **Python 3.8+** installé sur votre ordinateur
- **Git** pour cloner le projet
- Un **serveur Discord** (gratuit) pour tester

### Étape 1 : Cloner le projet

```bash
git clone https://github.com/Subelf2/sevco.git
cd sevco
```

### Étape 2 : Créer un environnement virtuel (recommandé)

```bash
# Créer l'environnement virtuel
python -m venv venv

# Activer l'environnement
# Sur macOS/Linux :
source venv/bin/activate

# Sur Windows :
venv\Scripts\activate
```

### Étape 3 : Installer les dépendances

```bash
pip install -r requirements.txt
```

### Étape 4 : Configurer les bots Discord

Pour que les bots fonctionnent, vous devez créer une **application Discord** et obtenir les tokens :

1. Allez sur https://discord.com/developers/applications
2. Cliquez sur "New Application"
3. Allez dans l'onglet "Bot" et cliquez "Add Bot"
4. Copiez le token
5. Créez un fichier `.env` à la racine du projet :

```env
DISCORD_TOKEN_SERVER=votre_token_ici
DISCORD_TOKEN_CREDENTIALS=votre_token_ici
DISCORD_TOKEN_AUTH1=votre_token_ici
DISCORD_TOKEN_AUTH2=votre_token_ici
DISCORD_TOKEN_AUTH3=votre_token_ici
```

> **Astuce** : Vous pouvez créer plusieurs applications ou utiliser la même avec des tokens différents. Chaque bot a besoin d'un token valide.

---

## Guide de démarrage rapide

Si vous êtes pressé, voici le minimum pour faire un test :

### 1. Lancez les 5 bots (dans 5 terminaux différents)

```bash
# Terminal 1
python bot_server.py

# Terminal 2
python bot_credentials.py

# Terminal 3
python bot_authority_1.py

# Terminal 4
python bot_authority_2.py

# Terminal 5
python bot_authority_3.py
```

### 2. Sur Discord, créez une élection

```
!server init MaTestElection Alice Bob Charlie
```

### 3. Les autorités rejoignent

```
!auth1 join MaTestElection
!auth2 join MaTestElection
!auth3 join MaTestElection
```

### 4. Ouvrez le vote

```
!server open MaTestElection
```

### 5. Ajoutez un électeur (vous-même)

```
!id add MaTestElection @VotrePseudo
```

Le bot vous envoie un message privé avec votre **Jeton de Vote** (un long bloc de texte).

### 6. Votez avec l'application locale

```bash
# Dans un 6ème terminal
python client_app.py
```

Une fenêtre s'ouvre. Collez votre Jeton de Vote et suivez les instructions.

### 7. Terminez l'élection

Sur Discord :
```
!server close MaTestElection
!auth1 decrypt MaTestElection
!auth2 decrypt MaTestElection
!auth3 decrypt MaTestElection
!server tally MaTestElection
```

Voilà ! Les résultats s'affichent. 🎉

---

## Démonstration complète étape par étape

### Étape 0 : Nettoyage (première fois ou test précédent)

Supprimez les anciens fichiers de test s'ils existent :

```bash
rm -f belenios.db secrets_Auth1.json secrets_Auth2.json secrets_Auth3.json server_rsa.pem client_rsa.pem
```

### Étape 1 : Allumer l'infrastructure

Ouvrez **5 terminaux différents** et lancez-les un par un :

```bash
python bot_server.py
python bot_credentials.py
python bot_authority_1.py
python bot_authority_2.py
python bot_authority_3.py
```

Vos bots devraient maintenant apparaître "En ligne" sur votre serveur Discord. ✅

### Étape 2 : Créer l'élection

Sur votre serveur Discord, tapez :

```
!server init MonElection Alice Bob Charlie
```

Cette commande crée une élection appelée "MonElection" avec 3 candidats.

### Étape 3 : Les Autorités rejoignent (Sécurité)

Pour garantir qu'une seule personne ne puisse pas tricher, le pouvoir de dépouillement est divisé en 3. Chaque bot "Autorité" doit rejoindre l'élection :

```
!auth1 join MonElection
!auth2 join MonElection
!auth3 join MonElection
```

**Pourquoi 3 autorités ?** Aucune d'elles ne peut déchiffrer les votes seule. Il faut les 3 ensemble pour voir le résultat.

### Étape 4 : Ouvrir les votes

Maintenant que la sécurité est en place, le serveur ouvre l'élection :

```
!server open MonElection
```

### Étape 5 : Inscrire un électeur

Le système distribue une "carte d'électeur" secrète. Mentionnez l'utilisateur Discord qui a le droit de voter :

```
!id add MonElection @VotrePseudo
```

Le Bot d'Identification vous envoie un **Message Privé** contenant un gros bloc de texte chiffré. C'est votre **Jeton de Vote**.

> **Important** : Ce token ne doit jamais être partagé. Il vous permet de voter de manière sécurisée.

### Étape 6 : Voter (Sur votre ordinateur)

Pour que Discord ne voie jamais votre vote en clair, le vote se fait sur une **application externe** :

```bash
python client_app.py
```

Une fenêtre graphique s'ouvre. Suivez ces étapes :

1. **Collez** le Jeton de Vote reçu en Message Privé
2. Cliquez sur **"Decrypt and Verify Token"**
3. **Choisissez** votre candidat (Alice, Bob ou Charlie)
4. Cliquez sur **"Encrypt My Vote"**
5. Cliquez sur **"Save ballot.json"** et enregistrez le fichier sur votre Bureau
6. **Notez** le "Tracking Hash" (numéro de suivi) affiché à l'écran !

### Étape 7 : Déposer le vote dans l'urne

Retournez sur Discord. **Glissez-déposez** votre fichier `ballot.json` dans le salon textuel et envoyez :

```
!server process_vote
```

Le Serveur va vérifier les mathématiques complexes de votre fichier et le placer dans l'urne. ✅

### Étape 8 : Fermer l'urne

Une fois que tout le monde a voté, clôturez l'élection :

```
!server close MonElection
```

### Étape 9 : Le Dépouillement

Le Serveur ne peut pas lire les votes seul. Il faut demander aux 3 Autorités d'utiliser leurs clés secrètes :

```
!auth1 decrypt MonElection
!auth2 decrypt MonElection
!auth3 decrypt MonElection
```

Chaque autorité effectue une partie du déchiffrement.

### Étape 10 : Les Résultats !

Une fois que les 3 autorités ont fait leur travail, compilez les résultats finaux :

```
!server tally MonElection
```

Les résultats s'affichent ! 🎉

---

## Vérifiabilité individuelle

L'une des grandes forces de SEVCO : **chacun peut vérifier que son vote a été enregistré**.

À tout moment, n'importe quel électeur peut demander au serveur d'afficher tous les **Numéros de Suivi** présents dans l'urne :

```
!server public_urn MonElection
```

Cherchez-y le numéro que l'application locale vous avait donné à l'étape 6 !

Si votre Tracking Hash y figure, c'est que votre vote a bien été enregistré. ✅

---

## Dépannage

### Les bots ne se lancent pas

- Vérifiez que les **tokens Discord** sont corrects dans `.env`
- Vérifiez que les **dépendances** sont installées : `pip install -r requirements.txt`
- Vérifiez votre **connexion Internet**

### Erreur "token expired"

Régénérez vos tokens sur https://discord.com/developers/applications

### L'application client_app.py ne démarre pas

Assurez-vous que le module graphique est installé :

```bash
pip install tkinter
```

(Tkinter est généralement inclus avec Python)

---

## Pour en savoir plus

Ce projet implémente le protocole **Belenios**, un système de vote électronique académique et sécurisé.

- Documentation Belenios : https://www.belenios.org/
- Cryptographie ZKP : https://fr.wikipedia.org/wiki/Preuve_%C3%A0_divulgation_nulle_de_connaissance

---

**Bon vote ! 🗳️**
