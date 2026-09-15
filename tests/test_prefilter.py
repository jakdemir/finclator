from src.prefilter import detect_assets

cases = {
    "#onsaltın Orta & uzun vade gözüm $3728": ["GOLD"],
    "$Onsaltın $4000 aşağısına kaydıkça #onsgümüş yeni dip yapmıyor": ["GOLD"],
    "S&amp;P'den 4550 , gümüşte 24.20.": ["SPX"],
    "Günaydın, Dow teorisi çok katmanlı": ["SPX"],
    "Kripto rallisine yönelik fikrim değişmedi": ["BTC"],
    "Altının yükselişi sürer mi?": ["GOLD"],
    "Rekor üstüne rekor kıran Borsaları olan ABD Ekonomisi": ["SPX"],
    "Thy’den Aselsan’a tüm büyük hisselerin derin eksi gittiği günde #bist": [],
    "Borsada doğru yatırımda kullanılmayacak cümleler": [],
    "Nasdaq 100 de yeni zirve": ["SPX"],
    "Bitcoin yeni rekorlar kırarken": ["BTC"],
    "Gümüşşşş! #onsgümüş 14 yılın zirvesinde": [],
    "Ortadoğu endeks kapanışları: Mısır Hermes 30": [],
    "The cost of transporting oil is going hockey stick": [],
    "Gold to $5,000 and BTC to 150k by year end. Nvidia is a bubble.": ["BTC", "GOLD", "SPX"],
    "ABD hisse senetleri pahalı": ["SPX"],
    "10-year yield 5%. Don't be fooled. Gold wins.": ["GOLD"],
}
bad = 0
for text, want in cases.items():
    got = detect_assets(text)
    ok = got == want
    bad += not ok
    print(("ok  " if ok else "FAIL"), got, "|", text[:60])
print("failures:", bad)
