# RedAfrik — Exemples de requêtes API

Toutes les requêtes utilisent `curl`. L'API est servie sous le préfixe `/api/`.

- Index des endpoints : `GET /api/`
- Documentation interactive (Swagger UI) : `GET /api/docs/`
- Schéma OpenAPI : `GET /api/schema/`

## Conventions

- **Authentification** : header `Authorization: Bearer <access_token>`
- **Erreurs** : toutes les réponses d'erreur ont la forme
  `{"erreur": {"detail": "..."}}` (globale) ou `{"erreur": {"champ": ["..."]}}` (validation)
- **Pagination** : les listes renvoient `{"count", "next", "previous", "results"}`
  (paramètre `?page=` et `?page_size=`)

---

## 1. Authentification

### Inscription (retourne directement les jetons)

```bash
curl -X POST http://localhost:8000/api/auth/inscription/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "amina",
    "email": "amina@example.com",
    "mot_de_passe": "MotDePasse!123",
    "mot_de_passe_confirmation": "MotDePasse!123"
  }'
```

```json
{
  "utilisateur": {"id": 1, "username": "amina", "karma": 0, "...": "..."},
  "access": "eyJhbGciOi...",
  "refresh": "eyJhbGciOi..."
}
```

### Connexion

```bash
curl -X POST http://localhost:8000/api/auth/connexion/ \
  -H "Content-Type: application/json" \
  -d '{"username": "amina", "password": "MotDePasse!123"}'
```

### Rafraîchir le jeton d'accès

```bash
curl -X POST http://localhost:8000/api/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "eyJhbGciOi..."}'
```

### Déconnexion (révoque le jeton de rafraîchissement)

```bash
curl -X POST http://localhost:8000/api/auth/deconnexion/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"refresh": "eyJhbGciOi..."}'
```

### Vérification de l'adresse e-mail

```bash
# Valider le lien reçu par e-mail (sans authentification)
curl -X POST http://localhost:8000/api/auth/verifier-email/<jeton>/

# Renvoyer un nouveau lien (utilisateur connecté)
curl -X POST http://localhost:8000/api/auth/verifier-email/ \
  -H "Authorization: Bearer <access_token>"
```

### Réinitialisation du mot de passe

```bash
# Demander un lien (réponse neutre : ne révèle pas l'existence du compte)
curl -X POST http://localhost:8000/api/auth/reinitialiser-mdp/ \
  -H "Content-Type: application/json" \
  -d '{"email": "vous@exemple.com"}'

# Appliquer le nouveau mot de passe avec le jeton reçu par e-mail
curl -X POST http://localhost:8000/api/auth/reinitialiser-mdp/confirmer/ \
  -H "Content-Type: application/json" \
  -d '{"jeton": "<jeton>", "nouveau_mot_de_passe": "NouveauMdp123!", "confirmation": "NouveauMdp123!"}'
```

---

## 2. Utilisateurs

```bash
# Profil de l'utilisateur connecté
curl http://localhost:8000/api/utilisateurs/moi/ \
  -H "Authorization: Bearer <access_token>"

# Mettre à jour sa bio et son avatar
curl -X PATCH http://localhost:8000/api/utilisateurs/profil/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"bio": "Passionnée de tech à Dakar.", "avatar_url": "https://exemple.com/avatar.jpg"}'

# Classement public des utilisateurs par karma
curl http://localhost:8000/api/utilisateurs/

# Profil public d'un utilisateur (id numérique)
curl http://localhost:8000/api/utilisateurs/42/

# Communautés suivies par l'utilisateur connecté
curl http://localhost:8000/api/utilisateurs/abonnements/ \
  -H "Authorization: Bearer <access_token>"

# Changer son mot de passe (ancien mot de passe requis)
curl -X POST http://localhost:8000/api/utilisateurs/mdp/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"ancien_mot_de_passe": "AncienMdp123!", "nouveau_mot_de_passe": "NouveauMdp123!", "confirmation": "NouveauMdp123!"}'

# Supprimer définitivement son compte (mot de passe requis)
curl -X DELETE http://localhost:8000/api/utilisateurs/supprimer-compte/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"mot_de_passe": "NouveauMdp123!"}'
```

---

## 3. Communautés

```bash
# Créer une communauté (le créateur devient administrateur)
curl -X POST http://localhost:8000/api/communautes/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "nom": "tech-afrique",
    "description": "L'innovation technologique vue d'Afrique.",
    "image_url": "https://exemple.com/couverture.jpg"
  }'

# Lister les communautés (recherche)
curl "http://localhost:8000/api/communautes/?search=tech"

# Communautés tendances (classées par abonnés)
curl http://localhost:8000/api/communautes/tendances/

# Détail d'une communauté (abonnés, est_abonne)
curl http://localhost:8000/api/communautes/tech-afrique/

# S'abonner
curl -X POST http://localhost:8000/api/communautes/tech-afrique/abonner/ \
  -H "Authorization: Bearer <access_token>"

# Se désabonner
curl -X DELETE http://localhost:8000/api/communautes/tech-afrique/abonner/ \
  -H "Authorization: Bearer <access_token>"

# Modifier (créateur ou administrateur uniquement)
curl -X PATCH http://localhost:8000/api/communautes/tech-afrique/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"description": "Nouvelle description."}'
```

---

## 4. Publications

```bash
# Publier un post texte
curl -X POST http://localhost:8000/api/posts/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "titre": "L'Afrique et l'IA : les défis de 2026",
    "contenu": "Analyse détaillée...",
    "communaute": "tech-afrique"
  }'

# Publier un post lien
curl -X POST http://localhost:8000/api/posts/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "titre": "Rapport sur le numérique africain",
    "url_externe": "https://exemple.com/rapport.pdf",
    "communaute": "tech-afrique"
  }'

# Feed récents (par défaut)
curl "http://localhost:8000/api/posts/?communaute=tech-afrique"

# Feed trié par popularité (score)
curl "http://localhost:8000/api/posts/?tri=populaire"

# Posts d'un auteur donné (page profil)
curl "http://localhost:8000/api/posts/?auteur=42"

# Recherche dans les titres et contenus
curl "http://localhost:8000/api/posts/?search=IA"

# Modifier (auteur ou modérateur)
curl -X PATCH http://localhost:8000/api/posts/1/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"titre": "Nouveau titre"}'

# Supprimer (auteur ou modérateur)
curl -X DELETE http://localhost:8000/api/posts/1/ \
  -H "Authorization: Bearer <access_token>"
```

---

## 5. Votes

```bash
# Voter +1 sur un post
curl -X POST http://localhost:8000/api/posts/1/vote/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"valeur": 1}'
# -> {"valeur": 1, "score": 5}

# Changer son vote (-1) : le score est recalculé
curl -X POST http://localhost:8000/api/posts/1/vote/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"valeur": -1}'

# Retirer son vote
curl -X DELETE http://localhost:8000/api/posts/1/vote/ \
  -H "Authorization: Bearer <access_token>"

# Vote sur un commentaire (même principe)
curl -X POST http://localhost:8000/api/commentaires/10/vote/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"valeur": 1}'
```

Chaque vote met à jour le **score** du post/commentaire (signal Django) et le
**karma** de l'auteur. Un utilisateur ne vote qu'une fois par contenu.

---

## 6. Commentaires

```bash
# Arborescence complète des commentaires d'un post
curl "http://localhost:8000/api/commentaires/?post=1"

# Commenter
curl -X POST http://localhost:8000/api/commentaires/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"contenu": "Très bonne analyse !", "post": 1}'

# Répondre à un commentaire (imbrication)
curl -X POST http://localhost:8000/api/commentaires/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"contenu": "Je suis d'accord.", "post": 1, "commentaire_parent": 10}'

# Modifier / supprimer (auteur ou modérateur)
curl -X DELETE http://localhost:8000/api/commentaires/10/ \
  -H "Authorization: Bearer <access_token>"
```

---

## 7. Modération

```bash
# Lister les modérateurs d'une communauté (modérateurs requis)
curl http://localhost:8000/api/moderateurs/?communaute=tech-afrique \
  -H "Authorization: Bearer <access_token>"

# Nommer un modérateur (administrateurs requis)
curl -X POST http://localhost:8000/api/moderateurs/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "utilisateur": 2,
    "communaute": "tech-afrique",
    "role": "moderateur"
  }'

# Changer le rôle (administrateurs requis)
curl -X PATCH http://localhost:8000/api/moderateurs/1/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"role": "administrateur"}'

# Démettre (administrateurs requis)
curl -X DELETE http://localhost:8000/api/moderateurs/1/ \
  -H "Authorization: Bearer <access_token>"

# Signaler un post
curl -X POST http://localhost:8000/api/signalements/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"post": 1, "raison": "Contenu inapproprié."}'

# Signaler un commentaire
curl -X POST http://localhost:8000/api/signalements/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"commentaire": 10, "raison": "Spam."}'

# Lister les signalements d'une communauté (modérateurs requis)
curl "http://localhost:8000/api/signalements/?communaute=tech-afrique&statut=en_attente" \
  -H "Authorization: Bearer <access_token>"

# Résoudre / rejeter un signalement (modérateurs requis)
curl -X POST http://localhost:8000/api/signalements/3/traiter/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"statut": "resolu"}'

# Supprimer un signalement (modérateurs requis)
curl -X DELETE http://localhost:8000/api/signalements/3/ \
  -H "Authorization: Bearer <access_token>"
```

---

## Exemple de parcours complet

```bash
BASE=http://localhost:8000/api

# 1. Inscription de deux utilisateurs
TOKEN_ALI=$(curl -s -X POST $BASE/auth/inscription/ -H "Content-Type: application/json" \
  -d '{"username":"ali","email":"ali@example.com","mot_de_passe":"MotDePasse!123","mot_de_passe_confirmation":"MotDePasse!123"}' \
  | jq -r .access)
TOKEN_FATOU=$(curl -s -X POST $BASE/auth/inscription/ -H "Content-Type: application/json" \
  -d '{"username":"fatou","email":"fatou@example.com","mot_de_passe":"MotDePasse!123","mot_de_passe_confirmation":"MotDePasse!123"}' \
  | jq -r .access)

# 2. Ali crée une communauté et publie un post
curl -s -X POST $BASE/communautes/ -H "Authorization: Bearer $TOKEN_ALI" -H "Content-Type: application/json" \
  -d '{"nom":"culture","description":"Cultures africaines"}'
POST_ID=$(curl -s -X POST $BASE/posts/ -H "Authorization: Bearer $TOKEN_ALI" -H "Content-Type: application/json" \
  -d '{"titre":"Le festival de Dakar","contenu":"Retour sur l'édition 2026.","communaute":"culture"}' | jq -r .id)

# 3. Fatou s'abonne, vote et commente
curl -s -X POST $BASE/communautes/culture/abonner/ -H "Authorization: Bearer $TOKEN_FATOU"
curl -s -X POST $BASE/posts/$POST_ID/vote/ -H "Authorization: Bearer $TOKEN_FATOU" -H "Content-Type: application/json" \
  -d '{"valeur":1}'
curl -s -X POST $BASE/commentaires/ -H "Authorization: Bearer $TOKEN_FATOU" -H "Content-Type: application/json" \
  -d "{\"contenu\":\"Super article !\",\"post\":$POST_ID}"

# 4. Le feed populaire
curl -s "$BASE/posts/?communaute=culture&tri=populaire" | jq '.results[] | {titre, score, karma_auteur: .auteur.karma}'
```

## Limites de débit (sécurité)

| Scope | Limite | Endpoints concernés |
|---|---|---|
| `inscription` | 5/minute | `/api/auth/inscription/` |
| `connexion` | 10/minute | `/api/auth/connexion/` |
| `anonymous` | 60/minute | tous les endpoints anonymes |
| `user` | 300/minute | tous les endpoints authentifiés |

En cas de dépassement : `429 Too Many Requests` au format `{"erreur": {"detail": "..."}}`.
