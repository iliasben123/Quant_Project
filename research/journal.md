# Journal de recherche

Chaque variante testée est notée ici, **y compris celles qui échouent**, dès le premier essai.
Ce journal sert à savoir combien d'essais ont été faits avant de retenir une stratégie (risque de data snooping).

## Règles

1. Une entrée par variante (stratégie + paramètres + période).
2. On note l'hypothèse **avant** de lancer le test.
3. Période autorisée pendant la recherche : **développement** (2006-2017) uniquement.
4. La **validation** (2018-2021) sert seulement à départager des variantes déjà construites.
5. Le **test** (2022 → aujourd'hui) n'est ouvert qu'une seule fois, à la fin.
6. On ne supprime jamais une entrée.

## Compteurs

| Indicateur | Valeur |
|---|---|
| Variantes définies | 1 |
| Backtests lancés sur le développement | 35 (1 + 34 exploratoires de sensibilité) |
| Backtests lancés sur la validation | 1 |
| Ouverture de la période de test | 0 / 1 |

---

## Modèle d'entrée

```
### #NNN — Nom de la variante
- Date :
- Stratégie : (sortie de strategy.describe())
- Univers :
- Période :
- Hypothèse :
- Coûts simulés :
- Résultats : CAGR / Vol / Sharpe / Max DD / Nb trades / vs buy & hold
- Conclusion :
- Statut : définie / testée / rejetée / retenue
```

---

## Entrées

### #001 — Croisement de moyennes mobiles 50/200
- **Date** : 2026-10-05
- **Stratégie** : `MovingAverageCrossover(short=50, long=200, ma=sma)`
- **Univers** : 10 ETF (SPY, QQQ, IWM, EFA, EEM, TLT, IEF, GLD, DBC, VNQ)
- **Période** : développement (2006-02-06 → 2017-12-29)
- **Hypothèse** : les marchés présentent des tendances persistantes sur plusieurs mois. Être investi seulement quand la tendance est haussière doit réduire fortement les drawdowns (crise de 2008 notamment) au prix d'un rendement un peu plus faible que le buy & hold.
- **Choix des paramètres** : 50/200 jours, valeurs classiques choisies **a priori**, sans optimisation.
- **Coûts simulés** : 0,05 % par ordre (stress test à 0,10 %)
- **Observation des signaux (2026-10-05, développement, sans rendements)** :
  - signaux valides à partir du 2006-11-17 (chauffe de 199 jours) ;
  - temps en position longue : de 51 % (DBC) à 80 % (QQQ) ;
  - **82 entrées au total** (6 à 11 par ETF, ~0,7 par an et par ETF), donc sous le seuil de 100 trades sur le développement seul ;
  - durée moyenne d'une position : ~1 an (ex. SPY ≈ 350 jours) → impact des frais faible.
- **Décision (2026-10-05, avant tout backtest)** : le critère des 100 trades est précisé. Il s'applique à l'historique complet (développement + validation + test), avec en plus l'obligation de rester rentable sans les 3 meilleurs trades. Paramètres 50/200 inchangés.
- **Backtest n°1 — développement (2026-10-05)** : du 2006-11-20 au 2017-12-29, 100 000 €, poches égales, cash à 0 %.

  | | Stratégie 0,05 % | Stratégie 0,10 % | B&H 10 ETF | B&H SPY |
  |---|---|---|---|---|
  | CAGR | +5,23 % | +5,16 % | +6,44 % | +8,26 % |
  | Volatilité | 8,41 % | 8,41 % | 12,35 % | 19,45 % |
  | Sharpe | 0,65 | 0,64 | 0,57 | 0,51 |
  | Sortino | 0,90 | 0,89 | 0,80 | 0,71 |
  | Max drawdown | −13,1 % | −13,3 % | −35,9 % | −55,4 % |
  | CAGR / Max DD | 0,40 | 0,39 | 0,18 | 0,15 |
  | Temps investi | 68 % | 68 % | 100 % | 100 % |

  - Trades : 82, réussite 57 %, gain moyen +19,7 %, perte moyenne −6,9 %, profit factor 3,35, durée moyenne 232 jours.
  - Gain sans les 3 meilleurs trades : 47 235 € sur 76 130 € (les 3 meilleurs = 38 % du gain).
  - Les 10 ETF sont gagnants. Contributeurs principaux : QQQ (21 218 €), SPY (14 594 €). Plus faibles : EFA (1 552 €), DBC (2 284 €).
  - Critères (indicatif) : Sharpe 0,65 < 0,7 **NON** ; Max DD 13 % ≤ 25 % OK ; Sharpe > B&H OK ; rentable sans top 3 OK.
- **Conclusion** : hypothèse confirmée. Drawdown divisé par ~2,7 par rapport au B&H 10 ETF, pour ~1,2 point de CAGR en moins. Insensible aux frais (stress test quasi identique). L'écart de Sharpe avec le B&H (0,65 vs 0,57) est faible et **pas statistiquement significatif** sur 11 ans (erreur type du Sharpe ≈ 0,3) : l'apport réel de la stratégie est la **réduction du risque de perte**, pas un meilleur rendement ajusté de la volatilité. Le Sharpe est juste sous le seuil de 0,7. **Paramètres 50/200 non modifiés.**
- **Biais connu** : le cash rapporte 0 % dans le moteur alors que la stratégie est en cash 32 % du temps (taux courts US ~5 % en 2006-2007). Ce biais pénalise la stratégie, pas le B&H. À traiter éventuellement comme correction du modèle (pas comme optimisation), décision à noter ici avant tout nouveau backtest.
- **Décision cash (2026-10-06, avant tout nouveau backtest)** : cash maintenu à 0 % pendant toute la Phase 4. Le modèle est cohérent (cash 0 % et taux sans risque 0 % dans le Sharpe). Rémunérer le cash au taux des T-bills augmenterait le CAGR mais pas le Sharpe de la stratégie (la part en cash a un rendement excédentaire nul) et baisserait celui du B&H. Reporté à la Phase 5.
- **Statut** : testée sur le développement et la validation → Phase 5

---

## Phase 4 — Analyse de sensibilité (développement)

### Protocole (fixé le 2026-10-06, avant exécution)
- **But** : vérifier que 50/200 est sur un **plateau** de résultats stables, pas sur un pic isolé. On ne choisit **pas** les meilleurs paramètres : 50/200 reste la variante retenue quel que soit le résultat.
- **Grille** : moyenne courte ∈ {20, 30, 40, 50, 60, 75, 100} × moyenne longue ∈ {100, 150, 200, 250, 300}, avec courte < longue → 34 variantes, toutes en SMA.
- **Période** : développement. Toutes les variantes démarrent le même jour (après la chauffe de la plus longue moyenne, 300 jours), avec le B&H 10 ETF sur la même période. Les chiffres de 50/200 différeront donc légèrement du backtest n°1.
- **Coûts** : 0,05 % par ordre.
- **Critères de robustesse** — 50/200 est jugé robuste si :
  1. au moins **80 %** des variantes ont un Sharpe ≥ celui du B&H 10 ETF ;
  2. au moins **80 %** des variantes ont un max drawdown ≤ 25 % ;
  3. **toutes** les variantes ont un CAGR positif ;
  4. le Sharpe moyen des **voisins directs** de 50/200 (courte ∈ {40, 50, 60} × longue ∈ {150, 200, 250}, hors 50/200) est à moins de **0,15** du Sharpe de 50/200.
- Ces 34 variantes sont des backtests **exploratoires** et seront comptées comme tels.

### Résultats (2026-10-06)
Période : 2007-04-18 → 2017-12-29. B&H 10 ETF : Sharpe 0,55, CAGR +6,13 %, max DD −35,2 %.

| Critère | Résultat | |
|---|---|---|
| Variantes avec Sharpe ≥ B&H | 100 % | OK |
| Variantes avec max DD ≤ 25 % | 100 % | OK |
| Toutes les variantes CAGR > 0 | oui | OK |
| Écart Sharpe voisins / 50-200 | 0,04 | OK |

- **Verdict : 50/200 ROBUSTE.**
- Sur toute la grille : Sharpe 0,58 → 0,78, CAGR +4,5 % → +6,2 %, max DD −9,4 % → −16,8 %, trades 53 → 171.
- 50/200 : Sharpe 0,62, dans la moitié basse de la grille (pas de sélection du meilleur).
- Meilleure case : 40/150 (Sharpe 0,78). **Non retenue** : maximum de 34 essais, écart inférieur à l'erreur type du Sharpe (~0,3).
- Observation (piste éventuelle, à traiter comme nouvelle hypothèse) : les moyennes longues de 100-150 jours donnent plus de trades (100-171) et un Sharpe légèrement supérieur.

### Analyse par année (variante #001, développement)

| Année | Stratégie | B&H 10 ETF | B&H SPY | Écart |
|---|---|---|---|---|
| 2006 (partielle) | +1,9 % | +2,0 % | +1,8 % | −0,1 |
| 2007 | +12,9 % | +13,8 % | +5,5 % | −1,0 |
| 2008 | −6,1 % | −23,1 % | −38,0 % | **+17,0** |
| 2009 | +15,5 % | +20,9 % | +29,5 % | −5,5 |
| 2010 | +8,5 % | +16,3 % | +13,5 % | −7,8 |
| 2011 | −0,4 % | +4,5 % | +2,5 % | −5,0 |
| 2012 | +1,7 % | +9,9 % | +13,3 % | −8,2 |
| 2013 | +7,9 % | +3,5 % | +34,5 % | +4,4 |
| 2014 | +6,4 % | +8,6 % | +15,2 % | −2,1 |
| 2015 | −3,6 % | −3,0 % | +0,7 % | −0,5 |
| 2016 | +2,2 % | +8,2 % | +11,9 % | −6,0 |
| 2017 | +13,7 % | +17,6 % | +21,8 % | −3,9 |

- La stratégie bat le B&H 10 ETF **2 années sur 12** (2008, 2013).
- **Profil d'assurance** : retard de 2 à 8 points la plupart des années (ré-entrée tardive après les krachs, whipsaws en marché sans tendance), compensé par une seule année de krach (2008).
- **Conséquence** : l'avantage sur le développement dépend de la présence de 2008. Sans krach dans une période, la stratégie doit faire moins bien que le B&H.
- **Risque comportemental** : 4 années consécutives sous le B&H (2009-2012) en réel.

---

## Phase 4 — Validation (2018-2021)

### Protocole (fixé le 2026-10-06, avant exécution)
- **Variante** : #001 `MovingAverageCrossover(short=50, long=200, ma=sma)`, inchangée.
- **Commande** : `python -m src.backtest.report --period validation`, lancée **une seule fois**.
- **Indicateurs** : moyennes calculées avec la fin du développement comme historique ; le backtest commence le 2018-01-02 en cash. Coûts 0,05 % (stress 0,10 %), cash 0 %.
- **Hypothèse (basée sur le mécanisme)** : la période contient deux baisses rapides (fin 2018, krach Covid de février-mars 2020 suivi d'un rebond très rapide). Une moyenne de 200 jours est lente : elle sort après une grande partie de la baisse et rentre tard dans le rebond. On s'attend donc à un **CAGR inférieur au B&H**, et à un avantage en drawdown **plus faible qu'en 2008**.
- **Limite connue** : l'histoire de cette période est connue de tous (pas de vrai « aveugle ») ; seule la période de test reste réellement non regardée dans ce projet.
- **Règle de décision** :
  - les critères de réussite sont affichés à titre indicatif (la décision finale se prend sur le test) ;
  - **arrêt et réexamen avant le test** si max drawdown > 25 % ou CAGR < 0 ;
  - sinon : la variante #001 passe en Phase 5, **sans modification des paramètres**, quel que soit l'écart avec le B&H.

### Résultats (2026-10-06, exécution unique)
Du 2018-01-02 au 2021-12-31.

| | Stratégie 0,05 % | Stratégie 0,10 % | B&H 10 ETF | B&H SPY |
|---|---|---|---|---|
| CAGR | +5,25 % | +5,17 % | +10,91 % | +17,47 % |
| Volatilité | 9,26 % | 9,26 % | 11,99 % | 19,03 % |
| Sharpe | 0,60 | 0,59 | 0,92 | 0,94 |
| Sortino | 0,76 | 0,75 | 1,25 | 1,27 |
| Max drawdown | −20,5 % | −20,5 % | −22,6 % | −32,0 % |
| Temps investi | 71 % | 71 % | 100 % | 100 % |

- Trades : 34, réussite 41 %, gain moyen +31,7 %, perte moyenne −8,9 %, profit factor 2,32.
- Gain sans les 3 meilleurs trades : 3 760 € sur 22 672 € → **les 3 meilleurs trades font 83 % du gain** (critère passé de justesse).
- QQQ fait la moitié du gain (11 380 €). 4 ETF perdants : IWM (−1 204 €), EEM (−1 441 €), EFA (−393 €) ; VNQ quasi nul.
- Par année : 2018 +3,1 pts (sortie fin 2018) ; 2019 −10,5 pts ; **2020 −15,7 pts** (+0,5 % contre +16,2 %) ; 2021 −0,7 pt.
- Critères (indicatif) : Sharpe 0,60 < 0,7 NON ; max DD 20,5 % ≤ 25 % OK ; Sharpe > B&H **NON** ; rentable sans top 3 OK (de justesse).

### Conclusion
- **Hypothèse confirmée** : CAGR très inférieur au B&H, avantage en drawdown presque nul (−20,5 % contre −22,6 %). En 2020, la moyenne de 200 jours a fait sortir après la chute et rentrer après le rebond : la stratégie a subi la baisse sans profiter de la reprise.
- **Ce qui est stable entre les deux périodes : la stratégie elle-même** (Sharpe 0,65 → 0,60, CAGR 5,2 % → 5,3 %, volatilité 8,4 % → 9,3 %). **Ce qui change : le B&H** (Sharpe 0,57 → 0,92). Battre ou non le B&H dépend du type de marché : baisse lente et prolongée (2008) → la stratégie gagne ; krach rapide en V (2020) → elle perd.
- **Point faible** : forte concentration des gains (83 % sur 3 trades), le critère « rentable sans les 3 meilleurs trades » est fragile.
- **Nombre de trades** : 82 (développement) + 34 (validation) = 116, le seuil de 100 sur l'historique complet est déjà atteint avant le test.
- **Décision (règle fixée avant exécution)** : max DD ≤ 25 % et CAGR > 0 → pas d'arrêt. La variante #001 passe en **Phase 5 sans modification**.
- La validation a été utilisée une fois pour #001. Toute nouvelle variante devra être définie et testée sur le développement d'abord ; chaque nouvel usage de la validation réduit sa valeur et sera compté.
