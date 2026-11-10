# Så använder du Day Trader-skillsen

En kort guide på svenska. Den visar hur du går från "vad ska jag titta på idag?"
till en färdig ordersedel, steg för steg.

> **Inte finansiell rådgivning.** De flesta som daytradar förlorar pengar.
> Ingen order läggs härifrån. Du lägger varje order själv i Avanza eller Nordnet.

---

## 1. Kom igång

### Installera

Välj ett av två sätt.

**Som plugin i Claude Code:**

```
/plugin marketplace add maxaakre/day-trader-skill-se
/plugin install day-trader-skill-se@day-trader-skill-se
```

- Då heter kommandona till exempel `/day-trader-skill-se:trader-scanner`.

**Som vanliga skills (kortare kommandon):**

```bash
git clone https://github.com/maxaakre/day-trader-skill-se.git
cp -r day-trader-skill-se/trader-* ~/.claude/skills/
```

- Då heter kommandona `/trader-scanner`, `/trader-news` och så vidare.

### Det här behöver du

- **Python 3.8 eller nyare.** Inget annat att installera.
- **Internet.** Verktygen hämtar gratis data från Yahoo Finance.
- Kör i Claude Code på din egen dator, inte i en sandlåda utan nät.

### Skapa din config

Kör detta i mappen där du vill handla från:

```bash
mkdir -p trader
cp ~/.claude/skills/trader-budget/config.example.se.json trader/config.json
```

Allt som skillsen skriver hamnar sedan i mappen **`trader/`**.

---

## 2. Ställ in dina regler

Öppna `trader/config.json`. De viktigaste raderna:

| Nyckel | Standard | Betyder |
| --- | --- | --- |
| `budget` | 20000 | Hur många kronor du handlar med |
| `max_loss_per_trade_sek` | 200 | Max förlust per affär, i kronor |
| `max_daily_loss_sek` | 600 | Max förlust per dag, i kronor |
| `max_trades_per_day` | 3 | Max antal affärer per dag |
| `max_position_pct` | 75 | Max andel av budgeten i en aktie |
| `cash_buffer_pct` | 10 | Andel som alltid ska ligga kvar som kontanter |
| `no_entries_before` | 09:15 | Inga nya köp före denna tid |
| `no_entries_after` | 17:00 | Inga nya köp efter denna tid |
| `flat_by` | 17:15 | Sälj allt senast denna tid |

- **Tips:** sänk `max_loss_per_trade_sek` medan du lär dig.
- Vill du handla i USA i stället? Sätt `"market": "US"`.

---

## 3. En dag, steg för steg

Varje steg läser det som förra steget skrev. Kör dem i den här ordningen.

```
scanner → news → entry → exit → timemachine → budget → risk → broker
alerts: stop, mål och "ut senast 17:15" medan affären är öppen
```

### Före 09:00: hitta kandidater

**`/trader-scanner`**
- Skannar 291 aktier i Large Cap och Mid Cap.
- Hittar till exempel utbrott över 20-dagars högsta, bull flags och översålda aktier.
- Skriver `trader/watchlist.json`.
- Säg till exempel: *"skanna marknaden"* eller *"vad bryter ut idag?"*

**`/trader-news`**
- Visar rubriker för aktierna på din lista.
- Visar **nästa rapportdatum**. Undvik aktier som rapporterar samma dag.
- Säg till exempel: *"några nyheter på VOLV-B?"*

### Efter 09:15: vänta på rätt läge

**`/trader-scanner`** igen, nu för **öppningsintervallet** (09:00–09:15).
- Hittar aktier som stängt över intervallets högsta.

**`/trader-entry`**
- Följer en aktie bar för bar.
- Svarar **väntar**, **triggad**, **utgången** eller **inte öppet än**.
- Skriver `trader/entry.json`.
- Säg till exempel: *"säg till när VOLV-B bryter ut"*

### Innan du köper: planera utgången

**`/trader-exit`**
- Sätter din **stop loss** (standard: mitten av öppningsintervallet).
- Sätter ditt **mål** (standard: 2R, alltså dubbla risken).
- Vägrar planer som inte går ihop, och säger varför.
- Skriver `trader/plan.json`.

**`/trader-timemachine`**
- Spelar upp resten av dagen **10 000 gånger** från aktiens egna 5-minutersbarer.
- Kör också samma regel på alla tidigare dagar.
- Visar oddsen: mål först, stop först eller ingetdera.
- **Är det nära slantsingling? Då kan du låta bli.**

### Storlek och kontroll

**`/trader-budget`**
- Räknar ut hur många aktier du kan köpa.
- Håller dig inom max förlust, positionstak och kontantbuffert.
- Säger vilken gräns som bestämde antalet.
- Skriver `trader/orders.json`.

**`/trader-risk`**
- Kontrollerar ordern mot alla dina regler.
- Svarar **PASS** eller **BLOCK**, med orsak.
- **Kör alltid detta steg.** Utan PASS blir det ingen ordersedel.

### Lägg ordern själv

**`/trader-broker`**
- Visar en **ordersedel** i klartext: antal, köppris, stop loss och mål.
- Visar max förlust vid stop.
- Du skriver **ja** för just den ordern.
- Sedan lägger du ordern själv i **Avanza** eller **Nordnet**.

### Medan affären är öppen

**`/trader-alerts`**
- Lägger tre larm i ett svep: **stop**, **mål** och **"ut senast 17:15"**.
- Varje larm ringer bara en gång.
- Säg till exempel: *"bevaka min stop"*

---

## 4. Ett riktigt exempel: Volvo B, 9 november 2026

| Steg | Resultat |
| --- | --- |
| Scanner, 09:40 | Stängde 09:20 över intervallet 311.30–312.80, på 313.30 kr |
| News | Nästa rapport 27 januari, alltså inte idag |
| Entry | Triggad 09:20 på 313.30 kr |
| Exit | Stop 312.05, mål 315.80, ut senast 17:15 |
| Timemachine | 10 000 omspelningar av resten av dagen |
| Budget | 47 aktier (14 725.10 kr). Förlust vid stop: 58.75 kr |
| Risk | PASS |
| Broker | Köp 47 VOLV B, stop loss 312.05, mål 315.80 |
| Alerts | Larm på stop, mål och 17:15 |

---

## 5. Tickers

Alla de här fungerar:

- `VOLV-B.ST`
- `VOLV-B`
- `VOLV B`

---

## 6. Bra att veta

- **Courtage ingår inte.** På små affärer kan det äta upp vinsten. Räkna med din courtageklass.
- **Datan kan vara fördröjd.** Yahoo är gratis och inofficiellt. Kolla priset hos din mäklare innan du agerar.
- **En stop loss är en plan, inte en garanti.** Vid snabba rörelser kan du få sämre pris.
- **Bara köp (long).** Blankning, optioner och belåning är avstängt som standard.
- **Skatt:** vanlig kapitalvinst. I ett ISK gäller schablonskatten.

---

## 7. Om något krånglar

| Problem | Gör så här |
| --- | --- |
| Ingen data hämtas | Kontrollera att du har internet och inte kör i en sandlåda |
| "Inte öppet än" | Börsen är stängd eller det är helgdag. Prova `/trader-alerts` och fråga *"är börsen öppen?"* |
| Budget vägrar | Stoppen ligger för långt bort för din max förlust. Flytta stoppen eller hoppa över affären |
| Risk ger BLOCK | Läs orsaken. Ofta är det fel tid, för många affärer eller dagens förlustgräns |

Kör testerna för att se att allt fungerar:

```bash
python3 -m unittest discover -s tests
```
