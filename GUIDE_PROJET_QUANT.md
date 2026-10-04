# Guide : construire un projet de trading quantitatif

Ce document explique, étape par étape, comment construire un système qui utilise la finance quantitative pour **décider quand entrer (et sortir) d'un trade**. Lis-le en entier avant de commencer à coder : il définit le plan du projet.

> **Avertissement important**
> Le trading comporte un risque réel de perte en capital. Aucune stratégie quantitative ne garantit des gains. La grande majorité des stratégies qui semblent rentables en backtest échouent en réel. Ce projet doit d'abord être un outil d'apprentissage et de test, **pas** un moyen de jouer de l'argent que tu ne peux pas te permettre de perdre.

---

## 0. Décisions du projet (Phase 0)

Ces choix sont fixés **avant** d'écrire du code. On ne les modifie pas après avoir vu des résultats de backtest.

### 0.1 Marché et fréquence
- **Marché** : ETF (actions, obligations, matières premières, immobilier).
- **Fréquence** : **daily**. Le signal est calculé sur la clôture du jour `t`, l'ordre est exécuté à l'ouverture du jour `t+1`.
- **Source de données** : `yfinance` (prix ajustés des splits et dividendes).

### 0.2 Univers de départ
Des ETF très liquides et diversifiés, ce qui évite le survivorship bias et donne assez de trades :

| ETF | Classe d'actifs |
|---|---|
| SPY | Actions US (S&P 500) |
| QQQ | Actions US tech (Nasdaq 100) |
| IWM | Actions US petites capitalisations |
| EFA | Actions pays développés hors US |
| EEM | Actions pays émergents |
| TLT | Obligations US long terme |
| IEF | Obligations US moyen terme |
| GLD | Or |
| DBC | Matières premières |
| VNQ | Immobilier coté US |

Historique commun disponible : à partir de 2006 environ.

> **Note réglementaire** : un particulier résidant dans l'UE ne peut généralement pas acheter ces ETF américains (réglementation PRIIPs / document KID). Ce n'est pas un problème pour le backtest et le paper trading. Pour le trading réel, on utilisera leurs **équivalents UCITS** (ex. CSPX ou VUAA pour le S&P 500) via un broker européen compatible (ex. Interactive Brokers).

### 0.3 Première stratégie
- **Suivi de tendance** (non-ML) : croisement de moyennes mobiles.
- MA courte > MA longue → **LONG** ; sinon → **CASH**.
- Pas de vente à découvert (short) ni d'effet de levier au départ.

### 0.4 Objectifs de risque
| Règle | Valeur de départ |
|---|---|
| Effet de levier | Aucun (exposition totale ≤ 100 % du capital) |
| Exposition maximale par ETF | 20 % du capital |
| Risque par trade (si stop-loss) | 1 % du capital |
| Coûts simulés (commission + slippage) | 0,05 % par ordre, test de stress à 0,10 % |
| Arrêt d'urgence | Si le drawdown dépasse 20 %, le système s'arrête et on analyse |

### 0.5 Critères de réussite (fixés à l'avance)
Une stratégie n'est acceptée que si, **sur les données de test (out-of-sample) et après coûts** :
- le ratio de Sharpe est **≥ 0,7** ;
- le max drawdown est **≤ 25 %** ;
- son rendement ajusté du risque est **meilleur que le buy & hold** du même univers (équipondéré) ;
- le backtest contient **au moins 100 trades** (allers-retours) sur l'**historique complet** (développement + validation + test) ;
- la stratégie reste **rentable après retrait de ses 3 meilleurs trades** (le résultat ne doit pas dépendre de quelques coups de chance) ;
- le Sharpe hors-échantillon n'est **pas inférieur à la moitié** du Sharpe in-sample (sinon : overfitting probable).

### 0.6 Découpage des données (verrouillé dès la Phase 1)
Découpage **chronologique** :

| Période | Rôle | Part |
|---|---|---|
| 2006 → 2017 | Développement (in-sample) | ~60 % |
| 2018 → 2021 | Validation | ~20 % |
| 2022 → aujourd'hui | **Test final** — on ne le regarde qu'une seule fois, à la fin | ~20 % |

Les données de test sont mises de côté dès le téléchargement et ne sont **ni tracées, ni analysées** pendant le développement.

### 0.7 Machine learning
**Pas de ML pour l'instant.** Le ML viendra en **dernière phase**, uniquement comme un filtre ajouté à une stratégie non-ML qui fonctionne déjà. Il ne sera conservé que s'il améliore les résultats hors-échantillon après coûts.

---

## 1. C'est quoi la finance quantitative appliquée au trading ?

Au lieu de prendre des décisions "au feeling", on utilise :

- des **données** (prix, volumes, indicateurs, données macro…),
- des **modèles mathématiques et statistiques** pour détecter des opportunités,
- des **règles précises et automatisables** pour entrer et sortir des positions,
- une **gestion du risque** chiffrée (combien risquer par trade, quand couper).

L'idée centrale : **une règle qui ne peut pas être écrite en code et testée sur des données historiques n'est pas une stratégie quantitative.**

---

## 2. Ce qu'il faut savoir avant de commencer

| Domaine | Niveau nécessaire |
|---|---|
| Python | Bases solides (fonctions, classes, listes, dictionnaires) |
| Bibliothèques data | `pandas`, `numpy`, `matplotlib` |
| Statistiques | Moyenne, écart-type, corrélation, régression, distributions |
| Finance | Rendements, volatilité, ordres (market, limit, stop), frais |

Si un de ces points est faible, ce n'est pas bloquant : on les apprendra au fil du projet.

---

## 3. Architecture générale du système

Un système de trading quantitatif se découpe en 6 blocs indépendants :

```
 ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
 │ 1. Données   │──>│ 2. Signaux   │──>│ 3. Risque &  │
 │ (collecte,   │   │ (stratégie,  │   │ taille de    │
 │  nettoyage)  │   │  indicateurs)│   │ position)    │
 └──────────────┘   └──────────────┘   └──────┬───────┘
                                              │
 ┌──────────────┐   ┌──────────────┐   ┌──────▼───────┐
 │ 6. Suivi &   │<──│ 5. Exécution │<──│ 4. Backtest  │
 │ rapports     │   │ (broker API) │   │ (validation) │
 └──────────────┘   └──────────────┘   └──────────────┘
```

### Bloc 1 — Les données
- **Sources gratuites** : `yfinance` (actions, ETF, indices, forex), `ccxt` (crypto, toutes les grandes plateformes), Alpha Vantage, FRED (données macro).
- **Format standard** : bougies OHLCV (Open, High, Low, Close, Volume) avec un horodatage.
- **Nettoyage** : valeurs manquantes, splits/dividendes (utiliser les prix ajustés), doublons, fuseaux horaires.
- **Stockage** : fichiers CSV au début, puis éventuellement une base SQLite.

### Bloc 2 — Les signaux (la stratégie)
C'est le cœur : une fonction qui, à partir des données disponibles **jusqu'à l'instant t**, produit un signal : `+1` (acheter), `-1` (vendre/short), `0` (ne rien faire).

### Bloc 3 — Gestion du risque et taille de position
Décide **combien** acheter et **quand couper**. C'est souvent plus important que le signal lui-même.

### Bloc 4 — Backtest
Simule la stratégie sur l'historique pour savoir si elle aurait fonctionné, **en incluant les frais et le slippage**.

### Bloc 5 — Exécution
Envoie les ordres à un broker via son API (d'abord en **paper trading**, c'est-à-dire avec de l'argent fictif).

### Bloc 6 — Suivi
Journal de tous les trades, performance en temps réel, alertes en cas de problème.

---

## 4. Les familles de stratégies quantitatives (pour débuter)

### 4.1 Suivi de tendance / Momentum
**Idée** : ce qui monte a tendance à continuer de monter (à court/moyen terme).
- Exemple simple : croisement de moyennes mobiles. Acheter quand la moyenne mobile 50 jours passe au-dessus de la 200 jours.
- Exemple plus robuste : *time-series momentum* — acheter si le rendement des 12 derniers mois est positif.

### 4.2 Retour à la moyenne (Mean Reversion)
**Idée** : un prix qui s'écarte trop de sa moyenne a tendance à y revenir.
- Outil : le **z-score** : `z = (prix - moyenne) / écart-type` sur une fenêtre glissante.
- Règle : acheter si `z < -2`, vendre si `z > +2`, sortir quand `z` revient vers 0.
- Variante classique : Bandes de Bollinger, RSI.

### 4.3 Pairs Trading (arbitrage statistique)
**Idée** : deux actifs très liés (ex. Coca-Cola / Pepsi) évoluent ensemble. Quand l'écart entre eux devient anormal, on achète l'un et on vend l'autre en pariant sur le retour à la normale.
- Outils : test de **cointégration** (Engle-Granger, `statsmodels`), régression linéaire pour le ratio de couverture.

### 4.4 Stratégies basées sur la volatilité
- Réduire l'exposition quand la volatilité monte (*volatility targeting*).
- Modèles : volatilité historique, GARCH (`arch`).

> **Pas de ML pour l'instant** : toutes les stratégies reposent sur des règles explicites et des modèles statistiques classiques. Le ML est prévu en dernière phase, comme filtre optionnel (voir section 0.7).

**Recommandation** : commencer par **4.1** (notre première stratégie), puis **4.2**. Elles sont simples, bien documentées et faciles à backtester.

---

## 5. Gestion du risque (indispensable)

### Règles de base
- **Risque par trade** : ne jamais risquer plus de **1 à 2 % du capital** sur un seul trade.
- **Stop-loss** systématique, défini **avant** d'entrer.
- **Limite de perte journalière/hebdomadaire** : le système s'arrête automatiquement si elle est atteinte.
- **Diversification** : ne pas tout mettre sur un seul actif.

### Calcul de la taille de position
**Méthode "fixed fractional"** :
```
taille_position = (capital × risque_par_trade) / (prix_entrée - prix_stop)
```
Exemple : capital 10 000 €, risque 1 % (100 €), entrée à 50 €, stop à 48 € → `100 / 2 = 50 actions`.

**Méthode par volatilité (ATR)** : le stop est placé à `k × ATR` du prix d'entrée, ce qui adapte la taille à la nervosité du marché.

**Critère de Kelly** : formule optimale théorique, mais trop agressive en pratique. Si utilisé, prendre **un quart ou la moitié** de Kelly.

---

## 6. Le backtest : comment ne pas se mentir

Le backtest est l'étape où la plupart des débutants se trompent. Les pièges principaux :

| Piège | Explication | Solution |
|---|---|---|
| **Look-ahead bias** | Utiliser une donnée du futur (ex. le prix de clôture du jour pour décider d'acheter le même jour à l'ouverture) | Décaler les signaux : `signal.shift(1)` |
| **Overfitting** | Optimiser les paramètres jusqu'à ce que ça marche parfaitement sur le passé | Peu de paramètres, test hors-échantillon |
| **Survivorship bias** | Tester seulement sur des actions qui existent encore aujourd'hui | Utiliser des univers historiques complets, ou de grands ETF diversifiés (notre choix) |
| **Frais oubliés** | Commissions, spread, slippage | Intégrés au moteur dès sa première version |
| **Trop peu de trades** | 10 trades ne prouvent rien | Viser au moins 100+ trades (plusieurs ETF, longue période) |
| **Data snooping** | Tester des dizaines de variantes et garder la meilleure, qui est bonne par hasard | Journal de recherche : noter chaque variante testée |
| **Bug du moteur** | Le backtester calcule mal les rendements, les frais ou les positions | Tests unitaires sur des données synthétiques au résultat connu |

### Le backtester doit lui-même être testé
Avant d'y faire confiance, on vérifie le moteur avec des cas simples dont on connaît le résultat exact :
- un prix qui monte de 1 % par jour + position toujours longue + 0 frais → rendement exact attendu ;
- un signal toujours à 0 → capital inchangé ;
- un aller-retour avec frais → perte exactement égale aux frais ;
- un signal à `t` ne doit jamais utiliser le rendement de `t` (vérification du décalage).

### Journal de recherche
Fichier `research/journal.md` : pour chaque test, on note la date, la stratégie, les paramètres, la période utilisée et le résultat. Cela permet de savoir combien de variantes ont été essayées avant de trouver « la bonne ».

### Méthode de validation recommandée
1. **Découper les données** : 60 % développement (in-sample), 20 % validation, 20 % test final (out-of-sample) qu'on ne touche **qu'une seule fois** (voir section 0.6).
2. **Walk-forward analysis** : réoptimiser périodiquement sur une fenêtre glissante et tester sur la période suivante.
3. **Test de robustesse** : la stratégie doit rester correcte si on change légèrement les paramètres (ex. moyenne 48 ou 52 jours au lieu de 50).

### Indicateurs de performance à calculer
- **Rendement annualisé (CAGR)**
- **Volatilité annualisée**
- **Ratio de Sharpe** = rendement moyen excédentaire / volatilité (annualisé). > 1 est bon, > 2 est très bon (et suspect en backtest).
- **Ratio de Sortino** (comme Sharpe, mais ne pénalise que la volatilité à la baisse)
- **Max Drawdown** : la pire baisse depuis un sommet. C'est ce que tu devras supporter psychologiquement.
- **Nombre de trades**, **taux de réussite**, **gain moyen** et **perte moyenne**
- **Profit factor** = somme des gains / somme des pertes
- **Comparaison au benchmark** (buy & hold équipondéré de l'univers, et SPY seul)

> Si ta stratégie ne bat pas le "buy and hold" après frais, elle n'a pas d'intérêt.

---

## 7. Passer au réel : exécution

### Étapes obligatoires dans cet ordre
1. **Backtest** concluant (hors-échantillon inclus).
2. **Paper trading** pendant au moins **1 à 3 mois** : le système tourne en conditions réelles avec de l'argent fictif.
3. Comparer les résultats du paper trading avec le backtest. S'ils divergent fortement, il y a un problème.
4. **Réel avec un petit capital**, puis augmentation progressive.

### Brokers / plateformes avec API
| Plateforme | Marché | Paper trading | Bibliothèque Python |
|---|---|---|---|
| Alpaca | Actions US, crypto | Oui (gratuit) | `alpaca-py` |
| Interactive Brokers | Presque tout | Oui | `ib_insync` / `ib_async` |
| Binance, Kraken, Bybit… | Crypto | Testnet | `ccxt` |
| MetaTrader 5 | Forex, CFD | Compte démo | `MetaTrader5` |

**Notre choix** : **Alpaca** pour le paper trading (gratuit, API simple, ETF US), puis **Interactive Brokers** pour le réel, avec les équivalents UCITS des ETF (voir section 0.2).

### Sécurité
- Ne **jamais** écrire les clés API dans le code : utiliser un fichier `.env` (bibliothèque `python-dotenv`) exclu de Git.
- Désactiver le droit de **retrait** sur les clés API.
- Prévoir un **bouton d'arrêt d'urgence** (kill switch) qui ferme toutes les positions.

---

## 8. Stack technique proposée

| Besoin | Outil |
|---|---|
| Langage | Python 3.11+ |
| Données | `pandas`, `numpy`, `yfinance` |
| Stockage | CSV, un fichier par ETF (ex. `data/raw/SPY.csv`) |
| Indicateurs | `pandas-ta` ou calcul manuel |
| Statistiques | `scipy`, `statsmodels`, `arch` |
| Backtest | Moteur maison, vérifié ensuite en le comparant à `vectorbt` |
| Visualisation | `matplotlib`, `plotly` |
| Exécution | `alpaca-py` (paper), `ib_async` (réel) |
| Planification | `schedule` ou `APScheduler` |
| Config / secrets | `python-dotenv`, fichiers YAML |
| Tests | `pytest` |
| Interface (optionnel) | `streamlit` pour un tableau de bord |

---

## 9. Structure du projet prévue

```
trading project/
├── GUIDE_PROJET_QUANT.md     ← ce fichier
├── README.md
├── requirements.txt
├── .env.example              ← modèle des clés API (sans vraies valeurs)
├── .gitignore
├── config/
│   └── config.yaml           ← univers d'ETF, dates de découpage, paramètres, risque
├── data/
│   ├── raw/                  ← données brutes téléchargées
│   ├── processed/
│   │   ├── development/      ← données nettoyées 2006-2017
│   │   └── validation/       ← données nettoyées 2018-2021
│   └── locked_test/          ← données de test final, à ne pas ouvrir avant la fin
├── research/
│   └── journal.md            ← journal de toutes les variantes testées
├── src/
│   ├── data/
│   │   ├── loader.py         ← téléchargement (yfinance)
│   │   ├── cleaner.py        ← validation, nettoyage et alignement (n'écrit rien)
│   │   └── splitter.py       ← découpage, écriture, verrouillage du test, load_split()
│   ├── features/
│   │   └── indicators.py     ← moyennes mobiles, z-score, ATR, RSI…
│   ├── strategies/
│   │   ├── base.py           ← classe abstraite Strategy
│   │   ├── trend_following.py
│   │   └── mean_reversion.py
│   ├── risk/
│   │   ├── risk_manager.py   ← reçoit les signaux, renvoie les ordres dimensionnés
│   │   └── position_sizing.py
│   ├── backtest/
│   │   ├── engine.py         ← moteur de backtest
│   │   └── metrics.py        ← Sharpe, drawdown, CAGR…
│   ├── execution/
│   │   ├── broker.py         ← interface commune
│   │   └── paper_broker.py   ← broker simulé
│   └── monitoring/
│       └── logger.py         ← journal des trades
├── notebooks/                ← exploration et recherche
├── tests/                    ← tests unitaires (dont tests du backtester)
└── main.py                   ← point d'entrée (backtest / paper / live)
```

---

## 10. Feuille de route (roadmap)

À chaque étape : on explique l'objectif → on crée les fichiers → on écrit le code → tu l'exécutes → on vérifie le résultat → étape suivante.

### Phase 0 — Définir le système ✅
- Marché, fréquence, univers, première stratégie, objectifs de risque, critères de réussite, découpage des données (section 0).

### Phase 1 — Moteur de données
- Environnement Python, `requirements.txt`, `config.yaml`, `.gitignore`.
- Chaîne : API (`yfinance`) → OHLCV → validation → nettoyage → stockage local (CSV).
- Découpage chronologique et **verrouillage des données de test** dès cette phase.
- Pas de trading à ce stade.

### Phase 2 — Première stratégie
- Indicateurs (moyennes mobiles).
- Classe `Strategy` de base, puis stratégie de suivi de tendance : prix → indicateurs → signal → position.
- Interface simple avec le Risk Manager (fraction fixe du capital) pour pouvoir backtester tout de suite.

### Phase 3 — Backtester maison
- Capital initial → signal → taille de position → entrée → frais → slippage → sortie → capital.
- Décalage des signaux, frais et slippage **intégrés dès la première version**.
- Métriques : CAGR, volatilité, Sharpe, Sortino, max drawdown, nombre de trades, taux de réussite, gain/perte moyens, profit factor, comparaison buy & hold.
- **Tests unitaires du moteur** sur des données synthétiques.

### Phase 4 — Empêcher le faux rendement
- Vérification look-ahead, survivorship, coûts (test de stress à 0,10 %).
- Validation sur la période 2018-2021, walk-forward, sensibilité des paramètres.
- Journal de recherche à jour.
- Test final unique sur 2022 → aujourd'hui, jugé avec les critères de la section 0.5.

### Phase 5 — Risk Engine
- Risk Manager isolé : capital disponible, risque maximum, stop, volatilité, taille de position → ordre.
- On peut changer de stratégie sans toucher à la gestion du risque.

### Phase 6 — Paper trading (1 à 3 mois)
- Connexion à Alpaca en mode paper.
- Boucle quotidienne : données → signal → risque → ordre.
- Journal des trades, alertes, comparaison backtest vs paper trading.

### Phase 7 — Trading réel
- Petit capital d'abord, équivalents UCITS via Interactive Brokers.
- Clés API hors de Git, retrait désactivé, kill switch, limites de pertes, journal des transactions.

### Phase 8 — ML (optionnel)
- Uniquement comme filtre sur la stratégie non-ML existante.
- Comparaison stratégie sans ML vs stratégie + ML, hors-échantillon et après coûts. Si le ML n'apporte rien, on le retire.

---

## 11. Checklist avant de risquer de l'argent réel

- [ ] La stratégie a une **logique économique** (pourquoi devrait-elle marcher ?).
- [ ] Backtest sur **plusieurs années** et plusieurs conditions de marché (hausse, baisse, crise).
- [ ] Résultats positifs **hors-échantillon**, après frais et slippage.
- [ ] Au moins **100 trades** sur l'historique complet, et rentable sans les 3 meilleurs trades.
- [ ] Paramètres **robustes** (pas un seul réglage "magique").
- [ ] Max drawdown **acceptable psychologiquement**.
- [ ] **Paper trading** de 1 à 3 mois cohérent avec le backtest.
- [ ] Stop-loss, limites de perte et kill switch **en place et testés**.
- [ ] Clés API sécurisées, sans droit de retrait.
- [ ] Capital engagé = argent que je peux **perdre entièrement**.

---

## 12. Ressources pour apprendre

**Livres**
- *Quantitative Trading* et *Algorithmic Trading* — Ernest P. Chan (très accessibles, idéaux pour commencer)
- *Trading Systems and Methods* — Perry Kaufman

**En ligne**
- QuantStart (articles et tutoriels)
- Documentation de `pandas`, `vectorbt`, `ccxt`, `alpaca-py`
- QuantConnect (plateforme de backtest en ligne, gratuite pour tester des idées)

---

## Prochaine étape

La Phase 0 est terminée. Prochaine étape : **Phase 1 — Moteur de données** :
1. Créer l'environnement Python et la structure des dossiers.
2. Écrire `config.yaml` (univers d'ETF, dates de découpage).
3. Écrire `loader.py` pour télécharger les données OHLCV journalières des 10 ETF.
