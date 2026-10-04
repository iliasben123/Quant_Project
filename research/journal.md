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
| Backtests lancés sur le développement | 0 |
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
- **Résultats** : à compléter en Phase 3 (backtester pas encore construit)
- **Conclusion** : —
- **Statut** : définie
