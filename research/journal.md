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
| Backtests lancés sur le développement | 1 |
| Backtests lancés sur la validation | 0 |
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
- **Statut** : testée sur le développement
