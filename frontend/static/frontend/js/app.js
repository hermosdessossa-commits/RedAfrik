/* ==========================================================================
   RedAfrik — Application web (SPA)
   JavaScript vanilla, aucune dépendance externe, aucun tracker.
   L'échappement HTML est systématique pour toute donnée utilisateur.
   ========================================================================== */

"use strict";

const API = "/api/";

/* --- État global --------------------------------------------------------- */

const etat = {
  jetons: null,
  utilisateur: null,
  communautes: [],
  tri: "recents",
  recherche: null,
  postEdition: null,
  statutFiltre: "en_attente",
  moderationNom: null,
};

/* --- Stockage local (jetons + thème) -------------------------------------- */

function chargerJetons() {
  try {
    etat.jetons = JSON.parse(localStorage.getItem("redafrik.jetons") || "null");
  } catch {
    etat.jetons = null;
  }
}

function sauvegarderJetons() {
  if (etat.jetons) {
    localStorage.setItem("redafrik.jetons", JSON.stringify(etat.jetons));
  } else {
    localStorage.removeItem("redafrik.jetons");
  }
}

/* --- Utilitaires ----------------------------------------------------------- */

function echapper(valeur) {
  return String(valeur ?? "").replace(/[&<>"']/g, (caractere) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[caractere]));
}

function tempsRelatif(iso) {
  if (!iso) return "";
  const delta = (Date.now() - new Date(iso).getTime()) / 1000;
  if (delta < 60) return "à l'instant";
  const minutes = Math.floor(delta / 60);
  if (minutes < 60) return minutes + " min";
  const heures = Math.floor(minutes / 60);
  if (heures < 24) return heures + " h";
  const jours = Math.floor(heures / 24);
  if (jours < 30) return jours + " j";
  const mois = Math.floor(jours / 30);
  if (mois < 12) return mois + " mois";
  return Math.floor(mois / 12) + " ans";
}

function formaterNombre(nombre) {
  const n = Number(nombre) || 0;
  if (Math.abs(n) >= 1000) return (n / 1000).toFixed(1).replace(".", ",") + " k";
  return String(n);
}

function initiale(nom) {
  return (nom || "?").trim().charAt(0).toUpperCase();
}

function toast(message, type = "info") {
  const conteneur = document.getElementById("toasts");
  const element = document.createElement("div");
  element.className = "toast " + type;
  element.textContent = message;
  conteneur.appendChild(element);
  setTimeout(() => element.remove(), 4200);
}

function erreurMessage(donnees) {
  const erreur = (donnees && donnees.erreur) || {};
  if (erreur.detail) return erreur.detail;
  const champs = Object.values(erreur).flat().join("\n");
  return champs || "Une erreur est survenue.";
}

/* --- Client API ------------------------------------------------------------- */

class ErreurApi extends Error {
  constructor(message, statut, donnees) {
    super(message);
    this.statut = statut;
    this.donnees = donnees;
  }
}

async function requete(chemin, options = {}) {
  const opts = { ...options, headers: { ...(options.headers || {}) } };
  if (options.body !== undefined && !(options.body instanceof FormData)) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(options.body);
  }
  if (etat.jetons) {
    opts.headers["Authorization"] = "Bearer " + etat.jetons.access;
  }

  let reponse;
  try {
    reponse = await fetch(API + chemin, opts);
  } catch {
    // Serveur injoignable (arrêté, réseau coupé) : erreur explicite
    throw new ErreurApi(
      "Serveur indisponible. Vérifiez votre connexion et réessayez.",
      0,
      {}
    );
  }

  // Jeton expiré : une seule tentative de rafraîchissement puis nouvelle requête
  if (
    reponse.status === 401 &&
    etat.jetons &&
    etat.jetons.refresh &&
    !opts._retry &&
    !opts._sansRafraichissement
  ) {
    const rafraichi = await rafraichirJetons();
    if (rafraichi) {
      opts.headers["Authorization"] = "Bearer " + etat.jetons.access;
      opts._retry = true;
      return requete(chemin, opts);
    }
    deconnecter(false);
    return Promise.reject(
      new ErreurApi("Session expirée. Veuillez vous reconnecter.", 401, {})
    );
  }

  const donnees = await reponse.json().catch(() => ({}));
  if (!reponse.ok) {
    throw new ErreurApi(erreurMessage(donnees), reponse.status, donnees);
  }
  return donnees;
}

let rafraichissementEnCours = null;

async function rafraichirJetons() {
  // Une seule requête de refresh à la fois : avec la rotation des jetons, le
  // premier rafraîchissement révoque l'ancien refresh, les suivants échoueraient.
  if (rafraichissementEnCours) return rafraichissementEnCours;
  rafraichissementEnCours = (async () => {
    try {
      const reponse = await fetch(API + "auth/refresh/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh: etat.jetons.refresh }),
      });
      if (!reponse.ok) return false;
      const donnees = await reponse.json();
      // ROTATE_REFRESH_TOKENS : l'API émet aussi un nouveau refresh
      etat.jetons.access = donnees.access;
      if (donnees.refresh) etat.jetons.refresh = donnees.refresh;
      sauvegarderJetons();
      return true;
    } catch {
      return false;
    }
  })();
  try {
    return await rafraichissementEnCours;
  } finally {
    rafraichissementEnCours = null;
  }
}

/* --- Connexion / déconnexion ------------------------------------------------ */

async function chargerUtilisateur() {
  if (!etat.jetons) {
    etat.utilisateur = null;
    return null;
  }
  try {
    const donnees = await requete("utilisateurs/moi/");
    etat.utilisateur = donnees;
    return donnees;
  } catch (erreur) {
    if (erreur instanceof ErreurApi && erreur.statut === 401) {
      deconnecter(false);
    }
    return null;
  }
}

function connecter(jetons) {
  etat.jetons = jetons;
  sauvegarderJetons();
  return chargerUtilisateur();
}

async function deconnecter(informer = true) {
  const refresh = etat.jetons && etat.jetons.refresh;
  // Révocation d'abord, PENDANT que le jeton est encore en mémoire : sans
  // en-tête Bearer, la déconnexion est refusée (401) et le refresh resterait
  // valide 7 jours. _sansRafraichissement évite toute boucle de retry.
  if (refresh) {
    try {
      await requete("auth/deconnexion/", {
        method: "POST",
        body: { refresh },
        _sansRafraichissement: true,
      });
    } catch {
      // Jeton déjà révoqué ou serveur injoignable : la déconnexion locale suffit.
    }
  }
  etat.jetons = null;
  etat.utilisateur = null;
  sauvegarderJetons();
  if (informer) toast("Vous êtes déconnecté.");
  rendreBarreActions();
  naviguer();
}

/* --- Routage ------------------------------------------------------------------ */

// Si l'URL a été ouverte sans fragment (ex : /c/tech-afrique), convertit le
// chemin en fragment afin que le routage interne fonctionne au rechargement.
function normaliserChemin() {
  if (!location.pathname || location.pathname === "/") return;
  const chemin = location.pathname.replace(/\/+$/, "") || "/";
  history.replaceState(null, "", "/#" + chemin + location.search);
}

function naviguer() {
  const hash = location.hash.slice(1) || "/";
  fermerMenuMobile();
  window.scrollTo({ top: 0 });

  if (hash.startsWith("/c/")) return rendreCommunaute(decodeURIComponent(hash.slice(3)));
  if (hash.startsWith("/p/")) return rendrePost(decodeURIComponent(hash.slice(3)));
  if (hash.startsWith("/u/")) return rendreProfil(decodeURIComponent(hash.slice(3)));
  if (hash.startsWith("/m/")) return rendreModeration(decodeURIComponent(hash.slice(3)));
  if (hash.startsWith("/reinitialiser-mdp/"))
    return rendreReinitialiserMotDePasse(decodeURIComponent(hash.slice("/reinitialiser-mdp/".length)));
  if (hash.startsWith("/verifier-email/"))
    return rendreVerifierEmail(decodeURIComponent(hash.slice("/verifier-email/".length)));
  if (hash === "/reinitialiser-mdp") return rendreReinitialiserMotDePasse(null);
  if (hash === "/populaire") return rendreFlux("populaire");
  if (hash === "/tendances") return rendreTendances();
  if (hash === "/abonnements") return rendreAbonnements();
  if (hash !== "/") return rendreIntrouvable();
  return rendreFlux("accueil");
}

function marquerLienActif() {
  document.querySelectorAll(".lien-nav").forEach((lien) => {
    const nom = lien.dataset.nom;
    const actif =
      (nom === "accueil" && (!location.hash || location.hash === "#/")) ||
      (location.hash || "").includes(nom === "accueil" ? "/c/" : "/" + nom);
    lien.classList.toggle("actif", Boolean(actif));
  });
}

/* --- Rendu : flux de posts ------------------------------------------------------- */

function cartePost(post) {
  const vote = Number(post.vote_actuel) || 0;
  const estAuteur = etat.utilisateur && etat.utilisateur.id === post.auteur.id;
  const actionsAuteur = estAuteur
    ? `
      <button class="bouton-icone-texte" data-action="editer-post" data-id="${post.id}">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04a1 1 0 0 0 0-1.41l-2.34-2.34a1 1 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg>
        Modifier
      </button>
      <button class="bouton-icone-texte danger" data-action="supprimer-post" data-id="${post.id}">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M6 19a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
        Supprimer
      </button>`
    : "";
  const contenu =
    post.contenu
      ? `<div class="post-contenu">${echapper(post.contenu)}</div>`
      : "";
  const image = post.image_url
    ? `<img class="post-image" src="${echapper(post.image_url)}" alt="${echapper(post.titre)}" loading="lazy">`
    : "";
  const lien = post.url_externe
    ? `<a class="post-lien" href="${echapper(post.url_externe)}" target="_blank" rel="noopener noreferrer">
         ${echapper(post.url_externe)}</a>`
    : "";

  return `
  <article class="carte post" data-id="${post.id}">
    <div class="rail-vote">
      <button class="bouton-vote positif ${vote === 1 ? "actif" : ""}" data-action="vote" data-type="post" data-id="${post.id}" data-valeur="1" aria-label="Vote positif">
        <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M12 4 20 12h-5v8H9v-8H4z"/></svg>
      </button>
      <div class="score" data-champ="score">${formaterNombre(post.score)}</div>
      <button class="bouton-vote negatif ${vote === -1 ? "actif" : ""}" data-action="vote" data-type="post" data-id="${post.id}" data-valeur="-1" aria-label="Vote négatif">
        <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M12 20 4 12h5V4h6v8h5z"/></svg>
      </button>
    </div>
    <div class="post-corps">
      <div class="post-meta">
        <a class="lien-communaute-petit" href="#/c/${encodeURIComponent(post.communaute)}">r/${echapper(post.communaute)}</a>
        <span class="point">•</span>
        <span>Publié par <a href="#/u/${post.auteur.id}">u/${echapper(post.auteur.username)}</a></span>
        <span class="point">•</span>
        <span>${tempsRelatif(post.date_creation)}</span>
      </div>
      <h2 class="post-titre"><a href="#/p/${post.id}">${echapper(post.titre)}</a></h2>
      ${contenu}
      ${image}
      ${lien}
      <div class="post-actions">
        <button class="bouton-icone-texte" data-action="commenter" data-id="${post.id}">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M12 3C6.48 3 2 6.94 2 11.8c0 2.64 1.35 5 3.45 6.56-.1.8-.42 2.06-1.09 3.17 0 0 2.2-.32 4.1-1.5.42.12.86.18 1.54.18 5.52 0 10-3.94 10-8.8S17.52 3 12 3z"/></svg>
          ${formaterNombre(post.nombre_commentaires)} commentaires
        </button>
        <button class="bouton-icone-texte" data-action="signaler" data-type="post" data-id="${post.id}">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M14.4 6 14 4H5v17h2v-7h5.6l.4 2h7V6z"/></svg>
          Signaler
        </button>
        ${actionsAuteur}
      </div>
    </div>
  </article>`;
}

async function rendreFlux(type) {
  marquerLienActif();
  const conteneur = document.getElementById("contenu");
  conteneur.innerHTML = `<div class="carte chargement">Chargement…</div>`;
  etat.tri = type === "populaire" ? "populaire" : "recents";

  try {
    let parametres = "?page_size=10" + (etat.recherche ? "&search=" + encodeURIComponent(etat.recherche) : "");
    if (etat.tri === "populaire") parametres += "&tri=populaire";
    const donnees = await requete("posts/" + parametres);
    await chargerCommunautes();

    const titres = { accueil: "Accueil", populaire: "Populaire" };
    conteneur.innerHTML = `
      <div class="carte entete-feed">
        <h1 class="titre-feed">${titres[type]}</h1>
        <button class="onglet ${etat.tri === "recents" ? "actif" : ""}" data-action="tri" data-valeur="recents">Récents</button>
        <button class="onglet ${etat.tri === "populaire" ? "actif" : ""}" data-action="tri" data-valeur="populaire">Populaires</button>
      </div>
      ${donnees.results.length ? donnees.results.map(cartePost).join("") : etatVide("Aucun post pour le moment.", "Soyez le premier à partager avec la communauté.")}
      ${boutonChargerPlus(donnees.next)}`;
  } catch (erreur) {
    conteneur.innerHTML = etatVide("Impossible de charger le flux.", erreur.message);
  }
}

function etatVide(titre, texte) {
  return `<div class="carte etat-vide"><strong>${echapper(titre)}</strong>${echapper(texte)}</div>`;
}

/* --- Sécurité du compte : pages de réinitialisation et de vérification ------ */

function rendreReinitialiserMotDePasse(jeton) {
  const conteneur = document.getElementById("contenu");
  if (!jeton) {
    conteneur.innerHTML = `
      <div class="carte entete-feed"><h1 class="titre-feed">Réinitialiser mon mot de passe</h1></div>
      <div class="carte">
        <form data-action="form-demande-reset" class="formulaire-compte">
          <label>Adresse e-mail<input name="email" type="email" required autocomplete="email" placeholder="vous@exemple.com"></label>
          <div class="modale-erreur" hidden></div>
          <button class="bouton bouton-principal bouton-plein" type="submit">Envoyer le lien</button>
        </form>
        <p class="note-compte">Un lien valable 1 heure vous sera envoyé par e-mail.</p>
      </div>`;
    return;
  }
  conteneur.innerHTML = `
    <div class="carte entete-feed"><h1 class="titre-feed">Choisir un nouveau mot de passe</h1></div>
    <div class="carte">
      <form data-action="form-confirmation-reset" data-jeton="${echapper(jeton)}" class="formulaire-compte">
        <label>Nouveau mot de passe<input name="nouveau_mot_de_passe" type="password" required autocomplete="new-password"></label>
        <label>Confirmation<input name="confirmation" type="password" required autocomplete="new-password"></label>
        <div class="modale-erreur" hidden></div>
        <button class="bouton bouton-principal bouton-plein" type="submit">Enregistrer</button>
      </form>
    </div>`;
}

function rendreVerifierEmail(jeton) {
  const conteneur = document.getElementById("contenu");
  conteneur.innerHTML = `<div class="carte chargement">Vérification en cours…</div>`;
  requete("auth/verifier-email/" + encodeURIComponent(jeton) + "/", { method: "POST" })
    .then(() => {
      conteneur.innerHTML = `
        <div class="carte etat-vide">
          <strong>Adresse e-mail vérifiée</strong>
          Merci ! Votre compte est désormais entièrement actif.
        </div>
        <div class="carte pagination"><a class="bouton" href="#/">← Retour à l'accueil</a></div>`;
      if (etat.utilisateur) {
        etat.utilisateur.email_verifie = true;
        rendreBarreActions();
      }
    })
    .catch((erreur) => {
      conteneur.innerHTML = `
        <div class="carte etat-vide">
          <strong>Lien invalide ou expiré</strong>
          ${echapper(erreur.message)}
        </div>
        <div class="carte pagination"><a class="bouton" href="#/">← Retour à l'accueil</a></div>`;
    });
}

function rendreIntrouvable() {
  marquerLienActif();
  const conteneur = document.getElementById("contenu");
  conteneur.innerHTML = `
    <div class="carte etat-vide">
      <strong>Page introuvable</strong>
      L'adresse demandée n'existe pas ou a été déplacée.
    </div>
    <div class="carte pagination">
      <a class="bouton" href="#/">← Retour à l'accueil</a>
    </div>`;
}

function boutonChargerPlus(nextUrl) {
  if (!nextUrl) return "";
  return `<div class="charger-plus"><button class="bouton" data-action="suite" data-suite="${echapper(nextUrl)}">Charger plus</button></div>`;
}

/* --- Rendu : tendances ------------------------------------------------------- */

async function rendreTendances() {
  marquerLienActif();
  const conteneur = document.getElementById("contenu");
  conteneur.innerHTML = `<div class="carte chargement">Chargement…</div>`;
  try {
    const donnees = await requete("communautes/tendances/?page_size=20");
    conteneur.innerHTML = `
      <div class="carte entete-feed"><h1 class="titre-feed">Communautés tendances</h1></div>
      ${donnees.results.map(carteCommunaute).join("") || etatVide("Aucune communauté pour le moment.", "Créez la première !")}`;
  } catch (erreur) {
    conteneur.innerHTML = etatVide("Impossible de charger les tendances.", erreur.message);
  }
}

function carteCommunaute(c) {
  return `
  <article class="carte en-tete-communaute" data-id="${c.id}">
    <div class="infos">
      <div class="communaute-nom"><a href="#/c/${encodeURIComponent(c.nom)}">r/${echapper(c.nom)}</a></div>
      <div class="communaute-stats">${formaterNombre(c.nombre_abonnes)} abonnés · ${formaterNombre(c.nombre_posts)} posts</div>
      <div class="communaute-description">${echapper(c.description)}</div>
    </div>
    <div class="communaute-actions">
      ${boutonAbonnement(c)}
    </div>
  </article>`;
}

/* --- Rendu : abonnements ------------------------------------------------------- */

async function rendreAbonnements() {
  marquerLienActif();
  const conteneur = document.getElementById("contenu");
  if (!etat.utilisateur) {
    conteneur.innerHTML = etatVide("Connexion requise", "Connectez-vous pour voir vos abonnements.");
    ouvrirModale("connexion");
    return;
  }
  conteneur.innerHTML = `<div class="carte chargement">Chargement…</div>`;
  try {
    const donnees = await requete("utilisateurs/abonnements/");
    const noms = donnees.abonnements;
    const communautes = (await chargerCommunautes()).filter((c) => noms.includes(c.nom));
    conteneur.innerHTML = `
      <div class="carte entete-feed"><h1 class="titre-feed">Mes abonnements</h1></div>
      ${communautes.map(carteCommunaute).join("") || etatVide("Aucun abonnement.", "Explorez les communautés et abonnez-vous !")}`;
  } catch (erreur) {
    conteneur.innerHTML = etatVide("Impossible de charger vos abonnements.", erreur.message);
  }
}

/* --- Rendu : communauté ---------------------------------------------------------- */

async function rendreCommunaute(nom) {
  marquerLienActif();
  const conteneur = document.getElementById("contenu");
  conteneur.innerHTML = `<div class="carte chargement">Chargement…</div>`;
  try {
    const [communaute, posts] = await Promise.all([
      requete("communautes/" + encodeURIComponent(nom) + "/"),
      requete("posts/?communaute=" + encodeURIComponent(nom) + "&page_size=10&tri=" + etat.tri),
    ]);
    conteneur.innerHTML = `
      ${enTeteCommunaute(communaute)}
      <div class="carte entete-feed">
        <h1 class="titre-feed">Publications</h1>
        <button class="onglet ${etat.tri === "recents" ? "actif" : ""}" data-action="tri" data-valeur="recents">Récents</button>
        <button class="onglet ${etat.tri === "populaire" ? "actif" : ""}" data-action="tri" data-valeur="populaire">Populaires</button>
      </div>
      ${posts.results.length ? posts.results.map(cartePost).join("") : etatVide("Aucun post dans cette communauté.", "Publiez le premier !")}
      ${boutonChargerPlus(posts.next)}`;
  } catch (erreur) {
    conteneur.innerHTML = etatVide("Communauté introuvable.", erreur.message);
  }
}

function enTeteCommunaute(c) {
  const creation = c.date_creation ? new Date(c.date_creation).toLocaleDateString("fr-FR", { year: "numeric", month: "long" }) : "";
  return `
  <article class="carte en-tete-communaute">
    <div class="infos">
      <div class="communaute-nom">r/${echapper(c.nom)}</div>
      <div class="communaute-stats">
        ${formaterNombre(c.nombre_abonnes)} abonnés · ${formaterNombre(c.nombre_posts)} publications
        ${c.createur ? `· créée par <a href="#/u/${c.createur.id}">u/${echapper(c.createur.username)}</a>` : ""}
        ${creation ? ` · ${creation}` : ""}
      </div>
      <div class="communaute-description">${echapper(c.description)}</div>
    </div>
    <div class="communaute-actions">
      ${boutonAbonnement(c)}
      ${c.est_moderateur ? `<a class="bouton" href="#/m/${encodeURIComponent(c.nom)}">Modération</a>` : ""}
      <a class="bouton" href="#/" data-action="publier-ici" data-communaute="${encodeURIComponent(c.nom)}">Créer un post</a>
    </div>
  </article>`;
}

function boutonAbonnement(c) {
  const abonne = Boolean(c.est_abonne);
  return `<button class="bouton ${abonne ? "bouton-abonne" : "bouton-principal"}" data-action="abonner" data-nom="${encodeURIComponent(c.nom)}" data-abonne="${abonne}">
    ${abonne ? "Abonné ✓" : "S'abonner"}</button>`;
}

/* --- Rendu : page de post ------------------------------------------------------------ */

async function rendrePost(id) {
  marquerLienActif();
  const conteneur = document.getElementById("contenu");
  conteneur.innerHTML = `<div class="carte chargement">Chargement…</div>`;
  try {
    const [post, commentaires] = await Promise.all([
      requete("posts/" + id + "/"),
      requete("commentaires/?post=" + id + "&page_size=100"),
    ]);
    conteneur.innerHTML = `
      ${cartePost(post).replace('<article class="carte post"', '<article class="carte post post-page"')}
      <section class="carte commentaires-section">
        <div class="post-corps" style="padding-bottom: 0">
          <h2 class="titre-feed">Commentaires (${formaterNombre(post.nombre_commentaires)})</h2>
          ${formulaireCommentaire(id)}
        </div>
        <div class="post-corps" id="arbre-commentaires">
          ${commentaires.results.length ? arbreCommentaires(commentaires.results, id) : etatVide("Aucun commentaire", "Soyez le premier à réagir.")}
        </div>
      </section>`;
  } catch (erreur) {
    conteneur.innerHTML = etatVide("Publication introuvable.", erreur.message);
  }
}

function formulaireCommentaire(postId) {
  return `
  <form class="formulaire-reponse" data-action="form-commentaire" data-post="${postId}">
    <textarea name="contenu" rows="3" placeholder="Votre commentaire…" required></textarea>
    <button class="bouton bouton-principal" type="submit">Commenter</button>
  </form>`;
}

function arbreCommentaires(commentaires, postId) {
  return commentaires.map((commentaire) => carteCommentaire(commentaire, postId)).join("");
}

function carteCommentaire(c, postId) {
  const vote = Number(c.vote_actuel) || 0;
  const reponses = c.reponses && c.reponses.length ? arbreCommentaires(c.reponses, postId) : "";
  const estAuteur = etat.utilisateur && etat.utilisateur.id === c.auteur.id;
  const actionsAuteur = estAuteur
    ? `
      <button class="bouton-icone-texte" data-action="editer-commentaire" data-id="${c.id}">Modifier</button>
      <button class="bouton-icone-texte danger" data-action="supprimer-commentaire" data-id="${c.id}">Supprimer</button>`
    : "";
  return `
  <div class="commentaire" data-id="${c.id}">
    <div class="commentaire-rail">
      <button class="bouton-vote positif ${vote === 1 ? "actif" : ""}" data-action="vote" data-type="commentaire" data-id="${c.id}" data-valeur="1" aria-label="Vote positif">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M12 4 20 12h-5v8H9v-8H4z"/></svg>
      </button>
      <div class="score" data-champ="score">${formaterNombre(c.score)}</div>
      <button class="bouton-vote negatif ${vote === -1 ? "actif" : ""}" data-action="vote" data-type="commentaire" data-id="${c.id}" data-valeur="-1" aria-label="Vote négatif">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M12 20 4 12h5V4h6v8h5z"/></svg>
      </button>
    </div>
    <div class="commentaire-corps">
      <div class="commentaire-entete">
        <span class="avatar" style="width:22px;height:22px;font-size:0.65rem">${echapper(initiale(c.auteur.username))}</span>
        <a class="commentaire-auteur" href="#/u/${c.auteur.id}">u/${echapper(c.auteur.username)}</a>
        <span>· ${tempsRelatif(c.date_creation)}</span>
      </div>
      <div class="commentaire-texte">${echapper(c.contenu)}</div>
      <div class="post-actions">
        <button class="bouton-icone-texte" data-action="repondre" data-id="${c.id}">
          <svg viewBox="0 0 24 24" width="15" height="15" fill="currentColor"><path d="M10 9V5l-7 7 7 7v-4.1c5 0 8.5 1.6 11 5.1-1-5-4-10-11-11z"/></svg>
          Répondre
        </button>
        <button class="bouton-icone-texte" data-action="signaler" data-type="commentaire" data-id="${c.id}">
          <svg viewBox="0 0 24 24" width="15" height="15" fill="currentColor"><path d="M14.4 6 14 4H5v17h2v-7h5.6l.4 2h7V6z"/></svg>
          Signaler
        </button>
        ${actionsAuteur}
      </div>
      <div class="commentaire-reponses" data-zone="reponses">
        ${reponses}
      </div>
    </div>
  </div>`;
}

/* --- Rendu : modération ------------------------------------------------------- */

async function rendreModeration(nom) {
  marquerLienActif();
  const conteneur = document.getElementById("contenu");
  conteneur.innerHTML = `<div class="carte chargement">Chargement…</div>`;
  etat.moderationNom = nom;
  try {
    const communaute = await requete("communautes/" + encodeURIComponent(nom) + "/");
    if (!communaute.est_moderateur) {
      conteneur.innerHTML = etatVide(
        "Accès refusé",
        "Vous devez être modérateur de cette communauté pour accéder au panneau de modération."
      );
      return;
    }
    const signalements = await requete(
      "signalements/?communaute=" + encodeURIComponent(nom) +
      (etat.statutFiltre ? "&statut=" + etat.statutFiltre : "")
    );
    let moderateurs = { results: [] };
    if (communaute.est_administrateur) {
      moderateurs = await requete("moderateurs/?communaute=" + encodeURIComponent(nom));
    }
    conteneur.innerHTML = `
      <article class="carte en-tete-communaute">
        <div class="infos">
          <div class="communaute-nom">r/${echapper(nom)} — Modération</div>
          <div class="communaute-description">Gestion des signalements et des modérateurs de la communauté.</div>
        </div>
        <div class="communaute-actions">
          <a class="bouton" href="#/c/${encodeURIComponent(nom)}">← Voir la communauté</a>
        </div>
      </article>
      <div class="carte entete-feed">
        <h1 class="titre-feed">Signalements</h1>
        <button class="onglet ${etat.statutFiltre === "en_attente" ? "actif" : ""}" data-action="filtre-signalement" data-valeur="en_attente">En attente</button>
        <button class="onglet ${etat.statutFiltre === "" ? "actif" : ""}" data-action="filtre-signalement" data-valeur="">Tous</button>
        <button class="onglet ${etat.statutFiltre === "resolu" ? "actif" : ""}" data-action="filtre-signalement" data-valeur="resolu">Résolus</button>
        <button class="onglet ${etat.statutFiltre === "rejete" ? "actif" : ""}" data-action="filtre-signalement" data-valeur="rejete">Rejetés</button>
      </div>
      ${signalements.results.length ? signalements.results.map(carteSignalement).join("") : etatVide("Aucun signalement", "Rien à modérer pour le moment.")}
      ${communaute.est_administrateur ? `
        <div class="carte entete-feed"><h1 class="titre-feed">Modérateurs</h1></div>
        ${moderateurs.results.length ? moderateurs.results.map(carteModerateur).join("") : etatVide("Aucun modérateur", "")}
        <button class="bouton bouton-principal bouton-plein" data-action="nommer-moderateur" data-nom="${encodeURIComponent(nom)}">+ Nommer un modérateur</button>` : ""}`;
  } catch (erreur) {
    conteneur.innerHTML = etatVide("Panneau indisponible.", erreur.message);
  }
}

function carteSignalement(s) {
  const typeCible = s.post ? "post" : "commentaire";
  const idCible = s.post || s.commentaire;
  const libelles = { en_attente: "En attente", resolu: "Résolu", rejete: "Rejeté" };
  const actions = s.statut === "en_attente"
    ? `<button class="bouton bouton-principal" data-action="traiter-signalement" data-id="${s.id}" data-statut="resolu">Résoudre</button>
       <button class="bouton" data-action="traiter-signalement" data-id="${s.id}" data-statut="rejete">Rejeter</button>`
    : "";
  return `
  <article class="carte signalement" data-id="${s.id}">
    <div class="post-corps">
      <div class="post-meta">
        <span class="pastille-statut ${s.statut}">${libelles[s.statut]}</span>
        <span>•</span>
        <span>${typeCible} #${idCible} signalé par u/${echapper(s.utilisateur.username)}</span>
        <span>•</span>
        <span>${tempsRelatif(s.date_creation)}</span>
      </div>
      <div class="commentaire-texte">${echapper(s.raison)}</div>
      <div class="post-actions">
        ${actions}
        <button class="bouton-icone-texte danger" data-action="supprimer-signalement" data-id="${s.id}">Supprimer le signalement</button>
      </div>
    </div>
  </article>`;
}

function carteModerateur(m) {
  const estMoi = etat.utilisateur && etat.utilisateur.id === m.utilisateur;
  const libellesRole = { moderateur: "Modérateur", administrateur: "Administrateur" };
  return `
  <article class="carte" data-id="${m.id}">
    <div class="post-corps">
      <div class="post-meta">
        <a href="#/u/${m.utilisateur}">u/${echapper(m.utilisateur_detail.username)}</a>
        <span>•</span>
        <span>${libellesRole[m.role] || m.role}</span>
        ${estMoi ? `<span>•</span><span>(vous)</span>` : ""}
      </div>
      ${estMoi ? "" : `
      <div class="post-actions">
        <button class="bouton" data-action="changer-role-moderateur" data-id="${m.id}" data-role="${m.role === "administrateur" ? "moderateur" : "administrateur"}">
          ${m.role === "administrateur" ? "Rétrograder" : "Promouvoir administrateur"}
        </button>
        <button class="bouton-icone-texte danger" data-action="demettre-moderateur" data-id="${m.id}">Démettre</button>
      </div>`}
    </div>
  </article>`;
}

function modaleNommerModerateur() {
  return modaleEnveloppe(
    "Nommer un modérateur",
    `
    <form data-action="form-moderateur">
      <label>Nom d'utilisateur<input name="nom_utilisateur" required placeholder="ex : amina"></label>
      <label>Rôle
        <select name="role">
          <option value="moderateur">Modérateur</option>
          <option value="administrateur">Administrateur</option>
        </select>
      </label>
      <div class="modale-erreur" hidden></div>
      <button class="bouton bouton-principal bouton-plein" type="submit">Nommer</button>
    </form>`,
    "nommer-moderateur"
  );
}

/* --- Rendu : profil ---------------------------------------------------------------- */

async function rendreProfil(id) {
  marquerLienActif();
  const conteneur = document.getElementById("contenu");
  conteneur.innerHTML = `<div class="carte chargement">Chargement…</div>`;
  try {
    const [utilisateur, posts] = await Promise.all([
      requete("utilisateurs/" + id + "/"),
      requete("posts/?auteur=" + encodeURIComponent(id) + "&page_size=10"),
    ]);
    const estMoi = etat.utilisateur && etat.utilisateur.id === utilisateur.id;
    conteneur.innerHTML = `
    <article class="carte en-tete-communaute">
      <span class="avatar" style="width:56px;height:56px;font-size:1.4rem">${echapper(initiale(utilisateur.username))}</span>
      <div class="infos">
        <div class="communaute-nom">u/${echapper(utilisateur.username)}</div>
        <div class="communaute-stats">
          ${formaterNombre(utilisateur.karma)} karma ·
          ${formaterNombre(utilisateur.nombre_posts)} posts ·
          ${formaterNombre(utilisateur.nombre_commentaires)} commentaires ·
          inscrit·e ${new Date(utilisateur.date_creation).toLocaleDateString("fr-FR", { year: "numeric", month: "long" })}
        </div>
        <div class="communaute-description">${echapper(utilisateur.bio) || "Aucune biographie pour le moment."}</div>
      </div>
      ${estMoi ? `<div class="communaute-actions">
        <button class="bouton" data-action="modifier-profil">Modifier mon profil</button>
      </div>` : ""}
    </article>
    <div class="carte entete-feed">
      <h1 class="titre-feed">Publications de u/${echapper(utilisateur.username)}</h1>
    </div>
    ${posts.results.length ? posts.results.map(cartePost).join("") : etatVide("Aucune publication.", "Cette personne n'a encore rien publié.")}
    ${boutonChargerPlus(posts.next)}`;
  } catch (erreur) {
    conteneur.innerHTML = etatVide("Utilisateur introuvable.", erreur.message);
  }
}

/* --- Communautés (sidebar) -------------------------------------------------------------- */

async function chargerCommunautes() {
  if (etat.communautes.length) return etat.communautes;
  try {
    const donnees = await requete("communautes/?page_size=50&ordering=nom");
    etat.communautes = donnees.results;
    rendreListeCommunautes();
    return etat.communautes;
  } catch {
    return [];
  }
}

function rendreListeCommunautes() {
  const conteneur = document.getElementById("liste-communautes");
  conteneur.innerHTML = etat.communautes
    .map(
      (c) => `
      <a class="lien-communaute" href="#/c/${encodeURIComponent(c.nom)}">
        <span class="pastille">${echapper(initiale(c.nom))}</span> r/${echapper(c.nom)}
      </a>`
    )
    .join("");
}

/* --- Barre d'actions (header) -------------------------------------------------------------- */

function rendreBarreActions() {
  const zone = document.getElementById("zone-actions");
  if (!etat.utilisateur) {
    zone.innerHTML = `
      <button class="bouton" data-action="connexion">Connexion</button>
      <button class="bouton bouton-principal" data-action="inscription">Inscription</button>`;
    return;
  }
  const utilisateur = etat.utilisateur;
  const badgeVerification = utilisateur.email_verifie
    ? ""
    : `
    <div class="menu-avertissement">
      <span>Adresse e-mail non vérifiée</span>
      <button class="bouton" data-action="renvoyer-verification">Renvoyer le lien</button>
    </div>`;
  zone.innerHTML = `
    <button class="bouton bouton-principal" data-action="nouveau-post">Créer un post</button>
    <div class="menu-utilisateur">
      <button class="bouton" data-action="menu-utilisateur">
        <span class="avatar">${echapper(initiale(utilisateur.username))}</span>
        <span>${echapper(utilisateur.username)}</span>
      </button>
      <div class="menu-utilisateur-contenu" hidden>
        <div class="menu-entete">
          <span class="avatar">${echapper(initiale(utilisateur.username))}</span>
          <div>
            <div style="font-weight:700">u/${echapper(utilisateur.username)}</div>
            <div class="karma-badge">${formaterNombre(utilisateur.karma)} karma</div>
          </div>
        </div>
        ${badgeVerification}
        <a href="#/u/${utilisateur.id}" data-action="profil">Mon profil</a>
        <a href="#/abonnements" data-action="mes-abonnements">Mes abonnements</a>
        <button data-action="modifier-mot-de-passe">Changer mon mot de passe</button>
        <button class="danger" data-action="supprimer-compte">Supprimer mon compte</button>
        <button data-action="deconnexion">Déconnexion</button>
      </div>
    </div>`;
}

/* --- Modales ------------------------------------------------------------------------------ */

function ouvrirModale(nom) {
  const conteneur = document.getElementById("modales");
  const modales = {
    connexion: modaleConnexion(),
    inscription: modaleInscription(),
    "nouveau-post": etat.utilisateur ? modaleNouveauPost() : modaleConnexion(),
    "nouvelle-communaute": etat.utilisateur ? modaleNouvelleCommunaute() : modaleConnexion(),
    signalement: modaleSignalement(),
    "edition-post": etat.utilisateur && etat.postEdition ? modaleEditionPost() : modaleConnexion(),
    profil: etat.utilisateur ? modaleProfil() : modaleConnexion(),
    "nommer-moderateur": etat.utilisateur ? modaleNommerModerateur() : modaleConnexion(),
    "mot-de-passe": etat.utilisateur ? modaleMotDePasse() : modaleConnexion(),
    "supprimer-compte": etat.utilisateur ? modaleSupprimerCompte() : modaleConnexion(),
  };
  const besoinConnexion =
    (nom === "nouveau-post" || nom === "nouvelle-communaute") && !etat.utilisateur;
  conteneur.innerHTML = `<div id="modale-voile" class="modale-voile">${modales[nom] || ""}</div>`;
  document.getElementById("modale-voile").addEventListener("click", (e) => {
    if (e.target.id === "modale-voile") fermerModale();
  });
  const champ = conteneur.querySelector("input, textarea, select");
  if (champ) champ.focus();
  return !besoinConnexion;
}

function fermerModale() {
  document.getElementById("modales").innerHTML = "";
}

function modaleEnveloppe(titre, corps, nom) {
  return `
  <div class="modale" id="modale-voile-interne" role="dialog" aria-modal="true" aria-label="${echapper(titre)}">
    <div class="modale-titre">${echapper(titre)}</div>
    ${corps}
    <div class="modale-actions">
      <button class="bouton" data-action="fermer-modale">Annuler</button>
    </div>
  </div>`;
}

function modaleConnexion() {
  return modaleEnveloppe(
    "Connexion",
    `
    <form data-action="form-connexion">
      <label>Nom d'utilisateur<input name="username" required autocomplete="username"></label>
      <label>Mot de passe<input name="password" type="password" required autocomplete="current-password"></label>
      <div class="modale-erreur" hidden></div>
      <button class="bouton bouton-principal bouton-plein" type="submit">Se connecter</button>
    </form>
    <p class="lien-basculer">Pas encore de compte ? <a href="#" data-action="bascule-inscription">Inscrivez-vous</a></p>
    <p class="lien-basculer">Mot de passe oublié ? <a href="#/reinitialiser-mdp" data-action="aller-reinitialiser">Réinitialisez-le</a></p>`,
    "connexion"
  );
}

function modaleInscription() {
  return modaleEnveloppe(
    "Créer un compte",
    `
    <form data-action="form-inscription">
      <label>Nom d'utilisateur<input name="username" required autocomplete="username" minlength="3"></label>
      <label>Adresse e-mail<input name="email" type="email" required autocomplete="email"></label>
      <label>Mot de passe<input name="mot_de_passe" type="password" required autocomplete="new-password"></label>
      <label>Confirmation<input name="mot_de_passe_confirmation" type="password" required autocomplete="new-password"></label>
      <div class="modale-erreur" hidden></div>
      <button class="bouton bouton-principal bouton-plein" type="submit">Créer mon compte</button>
    </form>
    <p class="lien-basculer">Déjà inscrit·e ? <a href="#" data-action="bascule-connexion">Connectez-vous</a></p>`,
    "inscription"
  );
}

function modaleNouveauPost() {
  const options = etat.communautes.map((c) => `<option value="${echapper(c.nom)}">r/${echapper(c.nom)}</option>`).join("");
  const choixCommunaute = etat.communautes.length
    ? `<select name="communaute" required>${options}</select>`
    : `<div class="modale-vide">
        <span>Aucune communauté n'existe encore.</span>
        <button class="bouton bouton-principal bouton-plein" type="button" data-action="aller-creer-communaute">Créer une communauté</button>
      </div>`;
  return modaleEnveloppe(
    "Créer un post",
    `
    <form data-action="form-post">
      <label>Titre<input name="titre" maxlength="300" required placeholder="Titre de votre publication"></label>
      <label>Communauté
        ${choixCommunaute}
      </label>
      <div class="separateur-choix-type">
        <button type="button" class="choix-type actif" data-action="type-post" data-type="texte">Texte</button>
        <button type="button" class="choix-type" data-action="type-post" data-type="lien">Lien</button>
        <button type="button" class="choix-type" data-action="type-post" data-type="image">Image</button>
      </div>
      <label id="champ-contenu-post">Contenu
        <textarea name="contenu" placeholder="Votre contenu…"></textarea>
      </label>
      <div class="modale-erreur" hidden></div>
      <button class="bouton bouton-principal bouton-plein" type="submit" ${etat.communautes.length ? "" : "disabled"}>Publier</button>
    </form>`,
    "nouveau-post"
  );
}

function modaleNouvelleCommunaute() {
  return modaleEnveloppe(
    "Créer une communauté",
    `
    <form data-action="form-communaute">
      <label>Nom (sans espaces, minuscules)
        <input name="nom" pattern="[a-z0-9-_]{2,50}" required placeholder="tech-afrique">
        <span class="champ-aide">L'identifiant unique, ex : r/tech-afrique</span>
      </label>
      <label>Description<textarea name="description" placeholder="De quoi parle cette communauté ?"></textarea></label>
      <label>Image de couverture (URL)<input name="image_url" type="url" placeholder="https://…"></label>
      <div class="modale-erreur" hidden></div>
      <button class="bouton bouton-principal bouton-plein" type="submit">Créer la communauté</button>
    </form>`,
    "nouvelle-communaute"
  );
}

function modaleSignalement() {
  return modaleEnveloppe(
    "Signaler un contenu",
    `
    <form data-action="form-signalement">
      <input type="hidden" name="cible_type">
      <input type="hidden" name="cible_id">
      <label>Raison du signalement
        <textarea name="raison" required placeholder="Décrivez le problème (spam, harcèlement, contenu inapproprié…)"></textarea>
      </label>
      <div class="modale-erreur" hidden></div>
      <button class="bouton bouton-principal bouton-plein" type="submit">Envoyer le signalement</button>
    </form>`,
    "signalement"
  );
}

function modaleEditionPost() {
  const post = etat.postEdition;
  return modaleEnveloppe(
    "Modifier la publication",
    `
    <form data-action="form-edition-post">
      <input type="hidden" name="id" value="${post.id}">
      <label>Titre<input name="titre" maxlength="300" required value="${echapper(post.titre)}"></label>
      <label>Contenu
        <textarea name="contenu" rows="4" placeholder="Texte de la publication…">${echapper(post.contenu)}</textarea>
      </label>
      <label>Lien externe (URL)<input name="url_externe" type="url" value="${echapper(post.url_externe)}" placeholder="https://…"></label>
      <label>URL de l'image<input name="image_url" type="url" value="${echapper(post.image_url)}" placeholder="https://…"></label>
      <div class="modale-erreur" hidden></div>
      <button class="bouton bouton-principal bouton-plein" type="submit">Enregistrer</button>
    </form>`,
    "edition-post"
  );
}

function modaleProfil() {
  const u = etat.utilisateur || {};
  return modaleEnveloppe(
    "Modifier mon profil",
    `
    <form data-action="form-profil">
      <label>Nom d'utilisateur<input name="username" required minlength="3" value="${echapper(u.username || "")}"></label>
      <label>Adresse e-mail<input name="email" type="email" required value="${echapper(u.email || "")}"></label>
      <label>Biographie
        <textarea name="bio" rows="4" placeholder="Parlez de vous…">${echapper(u.bio || "")}</textarea>
      </label>
      <label>URL de l'avatar<input name="avatar_url" type="url" value="${echapper(u.avatar_url || "")}" placeholder="https://…"></label>
      <div class="modale-erreur" hidden></div>
      <button class="bouton bouton-principal bouton-plein" type="submit">Enregistrer</button>
    </form>`,
    "profil"
  );
}

function modaleMotDePasse() {
  return modaleEnveloppe(
    "Changer mon mot de passe",
    `
    <form data-action="form-mot-de-passe">
      <label>Mot de passe actuel<input name="ancien_mot_de_passe" type="password" required autocomplete="current-password"></label>
      <label>Nouveau mot de passe<input name="nouveau_mot_de_passe" type="password" required autocomplete="new-password"></label>
      <label>Confirmation<input name="confirmation" type="password" required autocomplete="new-password"></label>
      <div class="modale-erreur" hidden></div>
      <button class="bouton bouton-principal bouton-plein" type="submit">Enregistrer</button>
    </form>`,
    "mot-de-passe"
  );
}

function modaleSupprimerCompte() {
  return modaleEnveloppe(
    "Supprimer mon compte",
    `
    <form data-action="form-supprimer-compte">
      <div class="modale-avertissement">
        Cette action est définitive : vos publications, commentaires et
        communautés seront supprimés. Saisissez votre mot de passe pour confirmer.
      </div>
      <label>Mot de passe<input name="mot_de_passe" type="password" required autocomplete="current-password"></label>
      <div class="modale-erreur" hidden></div>
      <button class="bouton bouton-principal bouton-plein" type="submit">Supprimer définitivement</button>
    </form>`,
    "supprimer-compte"
  );
}

/* --- Actions ------------------------------------------------------------------------------- */

async function voter(type, id, valeur) {
  if (!exigerConnexion()) return;
  try {
    const donnees = await requete(type + "s/" + id + "/vote/", {
      method: "POST",
      body: { valeur },
    });
    const carte = document.querySelector(
      `.commentaire[data-id="${id}"] .score, .post[data-id="${id}"] .score`
    );
    if (carte) carte.textContent = formaterNombre(donnees.score);
    const zone = document.querySelector(`[data-action="vote"][data-type="${type}"][data-id="${id}"]`).closest(".rail-vote, .commentaire-rail");
    if (zone) {
      zone.querySelectorAll(".bouton-vote").forEach((b) => b.classList.remove("actif"));
      const actif = zone.querySelector(`[data-valeur="${valeur}"]`);
      if (actif) actif.classList.add("actif");
    }
  } catch (erreur) {
    toast(erreur.message, "erreur");
  }
}

async function abonner(nom) {
  if (!exigerConnexion()) return;
  const bouton = document.querySelector(`[data-action="abonner"][data-nom="${encodeURIComponent(nom)}"]`);
  try {
    if (bouton.dataset.abonne === "true") {
      await requete("communautes/" + encodeURIComponent(nom) + "/abonner/", { method: "DELETE" });
      toast("Désabonné de r/" + nom);
    } else {
      await requete("communautes/" + encodeURIComponent(nom) + "/abonner/", { method: "POST" });
      toast("Abonné à r/" + nom + " ✓", "succes");
    }
    // Recharge la communauté pour rafraîchir l'état (est_abonne, compteurs)
    naviguer();
  } catch (erreur) {
    toast(erreur.message, "erreur");
  }
}

async function editerPost(id) {
  if (!exigerConnexion()) return;
  try {
    etat.postEdition = await requete("posts/" + id + "/");
    ouvrirModale("edition-post");
  } catch (erreur) {
    toast(erreur.message, "erreur");
  }
}

async function supprimerPost(id) {
  if (!confirm("Supprimer définitivement cette publication ? Cette action est irréversible.")) return;
  try {
    await requete("posts/" + id + "/", { method: "DELETE" });
    toast("Publication supprimée.");
    location.hash = "#/";
  } catch (erreur) {
    toast(erreur.message, "erreur");
  }
}

function editerCommentaire(id) {
  if (!exigerConnexion()) return;
  const commentaire = document.querySelector(`.commentaire[data-id="${id}"]`);
  if (!commentaire) return;
  const zone = commentaire.querySelector(".commentaire-texte");
  if (!zone) return;
  const ancien = zone.textContent;
  zone.innerHTML = `
    <form class="formulaire-reponse" data-action="form-edition-commentaire" data-id="${id}">
      <textarea name="contenu" rows="2" required>${echapper(ancien)}</textarea>
      <div class="ligne-boutons">
        <button class="bouton bouton-principal" type="submit">Enregistrer</button>
        <button class="bouton" type="button" data-action="annuler-edition-commentaire">Annuler</button>
      </div>
    </form>`;
  zone.querySelector("textarea").focus();
}

async function supprimerCommentaire(id) {
  if (!confirm("Supprimer définitivement ce commentaire ?")) return;
  try {
    await requete("commentaires/" + id + "/", { method: "DELETE" });
    toast("Commentaire supprimé.");
    naviguer();
  } catch (erreur) {
    toast(erreur.message, "erreur");
  }
}

async function traiterSignalement(id, statut) {
  try {
    await requete("signalements/" + id + "/traiter/", {
      method: "POST",
      body: { statut },
    });
    toast(statut === "resolu" ? "Signalement résolu." : "Signalement rejeté.", "succes");
    naviguer();
  } catch (erreur) {
    toast(erreur.message, "erreur");
  }
}

async function supprimerSignalement(id) {
  if (!confirm("Supprimer définitivement ce signalement ?")) return;
  try {
    await requete("signalements/" + id + "/", { method: "DELETE" });
    toast("Signalement supprimé.");
    naviguer();
  } catch (erreur) {
    toast(erreur.message, "erreur");
  }
}

async function changerRoleModerateur(id, role) {
  try {
    await requete("moderateurs/" + id + "/", { method: "PATCH", body: { role } });
    toast("Rôle mis à jour.", "succes");
    naviguer();
  } catch (erreur) {
    toast(erreur.message, "erreur");
  }
}

async function demettreModerateur(id) {
  if (!confirm("Démettre ce modérateur ?")) return;
  try {
    await requete("moderateurs/" + id + "/", { method: "DELETE" });
    toast("Modérateur démis.", "succes");
    naviguer();
  } catch (erreur) {
    toast(erreur.message, "erreur");
  }
}

async function soumettreModerateur(form) {
  const donnees = new FormData(form);
  const nomSaisi = donnees.get("nom_utilisateur").trim();
  try {
    const resultats = await requete("utilisateurs/?search=" + encodeURIComponent(nomSaisi) + "&page_size=5");
    const utilisateur = resultats.results.find(
      (u) => u.username.toLowerCase() === nomSaisi.toLowerCase()
    );
    if (!utilisateur) {
      throw new ErreurApi("Aucun utilisateur trouvé avec ce nom d'utilisateur.", 404, {});
    }
    await requete("moderateurs/", {
      method: "POST",
      body: {
        utilisateur: utilisateur.id,
        communaute: etat.moderationNom,
        role: donnees.get("role"),
      },
    });
    toast("Modérateur nommé.", "succes");
    fermerModale();
    naviguer();
  } catch (erreur) {
    afficherErreurFormulaire(form, erreur.message);
  }
}

function exigerConnexion() {
  if (etat.utilisateur) return true;
  ouvrirModale("connexion");
  toast("Connectez-vous pour continuer.");
  return false;
}

/* --- Soumissions de formulaires -------------------------------------------------------------- */

async function soumettreConnexion(form) {
  const donnees = new FormData(form);
  try {
    const reponse = await requete("auth/connexion/", {
      method: "POST",
      body: {
        username: donnees.get("username"),
        password: donnees.get("password"),
      },
    });
    await connecter({ access: reponse.access, refresh: reponse.refresh });
    toast("Bienvenue sur RedAfrik !", "succes");
    fermerModale();
    rendreBarreActions();
    naviguer();
  } catch (erreur) {
    afficherErreurFormulaire(form, erreur.message);
  }
}

async function soumettreInscription(form) {
  const donnees = new FormData(form);
  try {
    const reponse = await requete("auth/inscription/", {
      method: "POST",
      body: {
        username: donnees.get("username"),
        email: donnees.get("email"),
        mot_de_passe: donnees.get("mot_de_passe"),
        mot_de_passe_confirmation: donnees.get("mot_de_passe_confirmation"),
      },
    });
    await connecter({ access: reponse.access, refresh: reponse.refresh });
    toast("Compte créé. Bienvenue !", "succes");
    fermerModale();
    rendreBarreActions();
    naviguer();
  } catch (erreur) {
    afficherErreurFormulaire(form, erreur.message);
  }
}

async function soumettrePost(form) {
  const donnees = new FormData(form);
  // Seul le champ correspondant au type choisi (texte/lien/image) est rempli
  const corps = {
    titre: donnees.get("titre"),
    communaute: donnees.get("communaute"),
    contenu: donnees.get("contenu") || "",
    url_externe: donnees.get("url_externe") || "",
    image_url: donnees.get("image_url") || "",
  };
  try {
    const post = await requete("posts/", { method: "POST", body: corps });
    toast("Publication créée !", "succes");
    fermerModale();
    location.hash = "#/p/" + post.id;
  } catch (erreur) {
    afficherErreurFormulaire(form, erreur.message);
  }
}

async function soumettreCommunaute(form) {
  const donnees = new FormData(form);
  try {
    const communaute = await requete("communautes/", {
      method: "POST",
      body: {
        nom: donnees.get("nom"),
        description: donnees.get("description"),
        image_url: donnees.get("image_url"),
      },
    });
    etat.communautes = [];
    await chargerCommunautes();
    toast("Communauté r/" + communaute.nom + " créée !", "succes");
    fermerModale();
    location.hash = "#/c/" + communaute.nom;
  } catch (erreur) {
    afficherErreurFormulaire(form, erreur.message);
  }
}

async function soumettreCommentaire(form) {
  const donnees = new FormData(form);
  if (!exigerConnexion()) return;
  const corps = {
    contenu: donnees.get("contenu"),
    post: donnees.get("post") || form.dataset.post,
  };
  const parent = form.dataset.parent;
  if (parent) corps.commentaire_parent = Number(parent);
  try {
    await requete("commentaires/", { method: "POST", body: corps });
    toast("Commentaire publié.", "succes");
    // Recharge la page pour afficher le nouvel arbre
    naviguer();
  } catch (erreur) {
    afficherErreurFormulaire(form, erreur.message);
  }
}

async function soumettreSignalement(form) {
  const donnees = new FormData(form);
  if (!exigerConnexion()) return;
  const corps = { raison: donnees.get("raison") };
  corps[donnees.get("cible_type")] = Number(donnees.get("cible_id"));
  try {
    await requete("signalements/", { method: "POST", body: corps });
    toast("Signalement envoyé. Merci de votre vigilance.", "succes");
    fermerModale();
  } catch (erreur) {
    afficherErreurFormulaire(form, erreur.message);
  }
}

function afficherErreurFormulaire(form, message) {
  const zone = form.querySelector(".modale-erreur");
  if (zone) {
    zone.textContent = message;
    zone.hidden = false;
  } else {
    toast(message, "erreur");
  }
}

async function soumettreEditionPost(form) {
  const donnees = new FormData(form);
  try {
    await requete("posts/" + donnees.get("id") + "/", {
      method: "PATCH",
      body: {
        titre: donnees.get("titre"),
        contenu: donnees.get("contenu") || "",
        url_externe: donnees.get("url_externe") || "",
        image_url: donnees.get("image_url") || "",
      },
    });
    toast("Publication modifiée.", "succes");
    fermerModale();
    naviguer();
  } catch (erreur) {
    afficherErreurFormulaire(form, erreur.message);
  }
}

async function soumettreEditionCommentaire(form) {
  try {
    await requete("commentaires/" + form.dataset.id + "/", {
      method: "PATCH",
      body: { contenu: new FormData(form).get("contenu") },
    });
    toast("Commentaire modifié.", "succes");
    naviguer();
  } catch (erreur) {
    afficherErreurFormulaire(form, erreur.message);
  }
}

async function soumettreProfil(form) {
  const donnees = new FormData(form);
  try {
    const profil = await requete("utilisateurs/profil/", {
      method: "PATCH",
      body: {
        username: donnees.get("username"),
        email: donnees.get("email"),
        bio: donnees.get("bio") || "",
        avatar_url: donnees.get("avatar_url") || "",
      },
    });
    etat.utilisateur = { ...etat.utilisateur, ...profil };
    toast("Profil mis à jour.", "succes");
    fermerModale();
    naviguer();
  } catch (erreur) {
    afficherErreurFormulaire(form, erreur.message);
  }
}

async function soumettreMotDePasse(form) {
  const donnees = new FormData(form);
  try {
    await requete("utilisateurs/mdp/", {
      method: "POST",
      body: {
        ancien_mot_de_passe: donnees.get("ancien_mot_de_passe"),
        nouveau_mot_de_passe: donnees.get("nouveau_mot_de_passe"),
        confirmation: donnees.get("confirmation"),
      },
    });
    toast("Mot de passe modifié.", "succes");
    fermerModale();
  } catch (erreur) {
    afficherErreurFormulaire(form, erreur.message);
  }
}

async function soumettreSupprimerCompte(form) {
  const donnees = new FormData(form);
  try {
    await requete("utilisateurs/supprimer-compte/", {
      method: "DELETE",
      body: { mot_de_passe: donnees.get("mot_de_passe") },
    });
    fermerModale();
    toast("Votre compte a été supprimé.", "succes");
    deconnecter(false);
    location.hash = "#/";
  } catch (erreur) {
    afficherErreurFormulaire(form, erreur.message);
  }
}

async function soumettreDemandeReset(form) {
  const donnees = new FormData(form);
  try {
    await requete("auth/reinitialiser-mdp/", {
      method: "POST",
      body: { email: donnees.get("email") },
    });
    document.getElementById("contenu").innerHTML = `
      <div class="carte etat-vide">
        <strong>Lien envoyé</strong>
        Si un compte existe avec cette adresse, vous avez reçu un e-mail.
      </div>
      <div class="carte pagination"><a class="bouton" href="#/">← Retour à l'accueil</a></div>`;
  } catch (erreur) {
    afficherErreurFormulaire(form, erreur.message);
  }
}

async function soumettreConfirmationReset(form) {
  const donnees = new FormData(form);
  try {
    await requete("auth/reinitialiser-mdp/confirmer/", {
      method: "POST",
      body: {
        jeton: form.dataset.jeton,
        nouveau_mot_de_passe: donnees.get("nouveau_mot_de_passe"),
        confirmation: donnees.get("confirmation"),
      },
    });
    document.getElementById("contenu").innerHTML = `
      <div class="carte etat-vide">
        <strong>Mot de passe réinitialisé</strong>
        Vous pouvez maintenant vous connecter avec votre nouveau mot de passe.
      </div>
      <div class="carte pagination">
        <button class="bouton bouton-principal" data-action="connexion">Se connecter</button>
      </div>`;
  } catch (erreur) {
    afficherErreurFormulaire(form, erreur.message);
  }
}

/* --- Délégation d'événements --------------------------------------------------------------- */

function gererClic(evenement) {
  const cible = evenement.target.closest("[data-action]");
  if (!cible) return;

  const action = cible.dataset.action;
  switch (action) {
    case "connexion":
      ouvrirModale("connexion");
      break;
    case "inscription":
      ouvrirModale("inscription");
      break;
    case "bascule-inscription":
      evenement.preventDefault();
      ouvrirModale("inscription");
      break;
    case "bascule-connexion":
      evenement.preventDefault();
      ouvrirModale("connexion");
      break;
    case "fermer-modale":
      fermerModale();
      break;
    case "nouveau-post":
      ouvrirModale("nouveau-post");
      break;
    case "nouvelle-communaute":
      ouvrirModale("nouvelle-communaute");
      break;
    case "menu-utilisateur":
      basculerMenuUtilisateur(cible);
      break;
    case "aller-reinitialiser":
      evenement.preventDefault();
      fermerModale();
      location.hash = "#/reinitialiser-mdp";
      break;
    case "modifier-mot-de-passe":
      fermerMenuUtilisateur();
      ouvrirModale("mot-de-passe");
      break;
    case "supprimer-compte":
      fermerMenuUtilisateur();
      ouvrirModale("supprimer-compte");
      break;
    case "renvoyer-verification":
      fermerMenuUtilisateur();
      requete("auth/verifier-email/", { method: "POST" })
        .then(() => toast("Lien de vérification envoyé par e-mail.", "succes"))
        .catch((erreur) => toast(erreur.message, "erreur"));
      break;
    case "profil":
    case "mes-abonnements":
      fermerMenuUtilisateur();
      break;
    case "deconnexion":
      fermerMenuUtilisateur();
      deconnecter();
      break;
    case "vote":
      evenement.preventDefault();
      voter(cible.dataset.type, cible.dataset.id, Number(cible.dataset.valeur));
      break;
    case "abonner":
      abonner(decodeURIComponent(cible.dataset.nom));
      break;
    case "signaler":
      ouvrirSignalement(cible.dataset.type, cible.dataset.id);
      break;
    case "editer-post":
      editerPost(cible.dataset.id);
      break;
    case "supprimer-post":
      supprimerPost(cible.dataset.id);
      break;
    case "editer-commentaire":
      editerCommentaire(cible.dataset.id);
      break;
    case "supprimer-commentaire":
      supprimerCommentaire(cible.dataset.id);
      break;
    case "annuler-edition-commentaire":
      naviguer();
      break;
    case "fermer-reponse": {
      const formulaireReponse = cible.closest(".formulaire-reponse");
      if (formulaireReponse) formulaireReponse.remove();
      break;
    }
    case "modifier-profil":
      ouvrirModale("profil");
      break;
    case "filtre-signalement":
      etat.statutFiltre = cible.dataset.valeur;
      naviguer();
      break;
    case "traiter-signalement":
      traiterSignalement(cible.dataset.id, cible.dataset.statut);
      break;
    case "supprimer-signalement":
      supprimerSignalement(cible.dataset.id);
      break;
    case "nommer-moderateur":
      ouvrirModale("nommer-moderateur");
      break;
    case "changer-role-moderateur":
      changerRoleModerateur(cible.dataset.id, cible.dataset.role);
      break;
    case "demettre-moderateur":
      demettreModerateur(cible.dataset.id);
      break;
    case "repondre":
      ouvrirZoneReponse(cible.dataset.id);
      break;
    case "commenter":
      location.hash = "#/p/" + cible.dataset.id;
      break;
    case "tri":
      etat.tri = cible.dataset.valeur;
      naviguer();
      break;
    case "suite":
      chargerSuite(cible);
      break;
    case "type-post":
      basculerTypePost(cible);
      break;
    case "publier-ici":
      evenement.preventDefault();
      if (ouvrirModale("nouveau-post")) {
        const select = document.querySelector('form[data-action="form-post"] select[name="communaute"]');
        if (select) select.value = decodeURIComponent(cible.dataset.communaute || "");
      }
      break;
    case "aller-creer-communaute":
      ouvrirModale("nouvelle-communaute");
      break;
    default:
      break;
  }
}

function basculerMenuUtilisateur(bouton) {
  const menu = bouton.parentElement.querySelector(".menu-utilisateur-contenu");
  if (!menu) return;
  menu.hidden = !menu.hidden;
}

function fermerMenuUtilisateur() {
  document.querySelectorAll(".menu-utilisateur-contenu").forEach((m) => (m.hidden = true));
}

function ouvrirSignalement(type, id) {
  if (!exigerConnexion()) return;
  ouvrirModale("signalement");
  const form = document.querySelector('form[data-action="form-signalement"]');
  if (form) {
    form.cible_type.value = type;
    form.cible_id.value = id;
  }
}

function ouvrirZoneReponse(commentaireId) {
  if (!exigerConnexion()) return;
  const commentaire = document.querySelector(`.commentaire[data-id="${commentaireId}"]`);
  if (!commentaire) return;
  const zone = commentaire.querySelector("[data-zone='reponses']");
  if (!zone) return;
  const postId = document.querySelector('form[data-action="form-commentaire"]')?.dataset.post;
  zone.insertAdjacentHTML(
    "afterbegin",
    `
    <form class="formulaire-reponse" data-action="form-commentaire" data-post="${postId}" data-parent="${commentaireId}">
      <textarea name="contenu" rows="2" placeholder="Votre réponse…" required></textarea>
      <div style="display:flex;gap:8px">
        <button class="bouton bouton-principal" type="submit">Répondre</button>
        <button class="bouton" type="button" data-action="fermer-reponse">Annuler</button>
      </div>
    </form>`
  );
  zone.querySelector("textarea").focus();
}

function basculerTypePost(bouton) {
  const form = bouton.closest("form");
  form.querySelectorAll(".choix-type").forEach((b) => b.classList.remove("actif"));
  bouton.classList.add("actif");
  const label = document.getElementById("champ-contenu-post");
  const zoneTexte = label.querySelector("textarea");
  const etiquette = label.firstChild; // nœud texte « Contenu »
  if (bouton.dataset.type === "lien") {
    etiquette.textContent = "Lien externe";
    zoneTexte.placeholder = "https://exemple.com/article…";
    zoneTexte.name = "url_externe";
  } else if (bouton.dataset.type === "image") {
    etiquette.textContent = "URL de l'image";
    zoneTexte.placeholder = "https://exemple.com/image.jpg…";
    zoneTexte.name = "image_url";
  } else {
    etiquette.textContent = "Contenu";
    zoneTexte.placeholder = "Votre contenu…";
    zoneTexte.name = "contenu";
  }
}

async function chargerSuite(bouton) {
  bouton.disabled = true;
  bouton.textContent = "Chargement…";
  try {
    const donnees = await requete(bouton.dataset.suite.split("/api/")[1]);
    const cartes = donnees.results.map(cartePost).join("");
    const zone = bouton.closest("div");
    zone.insertAdjacentHTML("beforebegin", cartes);
    if (donnees.next) {
      bouton.dataset.suite = donnees.next;
      bouton.disabled = false;
      bouton.textContent = "Charger plus";
    } else {
      zone.remove();
    }
  } catch (erreur) {
    bouton.disabled = false;
    bouton.textContent = "Charger plus";
    toast(erreur.message, "erreur");
  }
}

function gererSoumission(evenement) {
  const form = evenement.target.closest("[data-action]");
  if (!form || !["form-connexion", "form-inscription", "form-post", "form-communaute", "form-commentaire", "form-signalement", "form-edition-post", "form-edition-commentaire", "form-profil", "form-moderateur", "form-mot-de-passe", "form-supprimer-compte", "form-demande-reset", "form-confirmation-reset"].includes(form.dataset.action)) return;
  evenement.preventDefault();
  switch (form.dataset.action) {
    case "form-connexion":
      soumettreConnexion(form);
      break;
    case "form-inscription":
      soumettreInscription(form);
      break;
    case "form-post":
      soumettrePost(form);
      break;
    case "form-communaute":
      soumettreCommunaute(form);
      break;
    case "form-commentaire":
      soumettreCommentaire(form);
      break;
    case "form-signalement":
      soumettreSignalement(form);
      break;
    case "form-edition-post":
      soumettreEditionPost(form);
      break;
    case "form-edition-commentaire":
      soumettreEditionCommentaire(form);
      break;
    case "form-profil":
      soumettreProfil(form);
      break;
    case "form-moderateur":
      soumettreModerateur(form);
      break;
    case "form-mot-de-passe":
      soumettreMotDePasse(form);
      break;
    case "form-supprimer-compte":
      soumettreSupprimerCompte(form);
      break;
    case "form-demande-reset":
      soumettreDemandeReset(form);
      break;
    case "form-confirmation-reset":
      soumettreConfirmationReset(form);
      break;
  }
}

/* --- Recherche ------------------------------------------------------------------------------- */

async function rechercher(evenement) {
  evenement.preventDefault();
  const terme = document.getElementById("champ-recherche").value.trim();
  etat.recherche = terme || null;
  location.hash = "#/";
}

/* --- Menu mobile et voile ----------------------------------------------------------------------- */

function basculerMenuMobile() {
  const sidebar = document.getElementById("sidebar");
  const voile = document.getElementById("voile");
  const ouverte = sidebar.classList.toggle("ouverte");
  voile.hidden = !ouverte;
  document.getElementById("btn-menu").setAttribute("aria-expanded", String(ouverte));
}

function fermerMenuMobile() {
  document.getElementById("sidebar").classList.remove("ouverte");
  document.getElementById("voile").hidden = true;
}

/* --- Thème --------------------------------------------------------------------------------------- */

function appliquerTheme() {
  const theme = localStorage.getItem("redafrik.theme") || "sombre";
  document.documentElement.dataset.theme = theme;
  document.getElementById("icone-soleil").hidden = theme === "clair";
  document.getElementById("icone-lune").hidden = theme === "sombre";
}

function basculerTheme() {
  const actuel = document.documentElement.dataset.theme;
  const nouveau = actuel === "sombre" ? "clair" : "sombre";
  localStorage.setItem("redafrik.theme", nouveau);
  appliquerTheme();
}

/* --- Initialisation ------------------------------------------------------------------------------ */

async function init() {
  chargerJetons();
  appliquerTheme();
  normaliserChemin();

  document.addEventListener("click", gererClic);
  document.addEventListener("submit", gererSoumission);
  document.getElementById("form-recherche").addEventListener("submit", rechercher);
  document.getElementById("btn-menu").addEventListener("click", basculerMenuMobile);
  document.getElementById("btn-theme").addEventListener("click", basculerTheme);
  document.getElementById("btn-nouvelle-communaute").addEventListener("click", () => ouvrirModale("nouvelle-communaute"));
  document.getElementById("voile").addEventListener("click", fermerMenuMobile);
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".menu-utilisateur")) fermerMenuUtilisateur();
  });

  await chargerUtilisateur();
  rendreBarreActions();
  chargerCommunautes();
  window.addEventListener("hashchange", naviguer);
  naviguer();
}

document.addEventListener("DOMContentLoaded", init);
