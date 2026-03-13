"""
Style Checker Module for Romanian Translations.

Detects anglicisms, false friends, calques, and corporate jargon
that make translations look like rough drafts instead of polished work.

Categories:
1. VERBE_HIBRIDE - Forcefully adapted English verbs
2. CALCURI - Literal translations (word-for-word mistakes)
3. FALSE_FRIENDS - Words that exist in both languages with different meanings
4. JARGON_CORPORATE - Filler words that pollute everyday speech
"""
import re
from typing import List, Dict, Tuple, Optional


# =============================================================================
# 1. VERBE HIBRIDE (Forcefully Adapted English Verbs)
# These mutilate the English root to make it look like a Romanian verb
# =============================================================================
VERBE_HIBRIDE = {
    r'\ba deleta\b': ('a șterge', 'Verb hibrid inutil - avem verb de bază clar'),
    r'\ba bookui\b': ('a rezerva', 'Verb hibrid forțat în context turism/restaurante'),
    r'\ba forwarda\b': ('a redirecționa', 'Verb hibrid specific e-mailurilor, fonetic greoi'),
    r'\ba cancela\b': ('a anula', 'Calc inutil după "to cancel"'),
    r'\ba updata\b': ('a actualiza', 'Foarte des întâlnit, dar redundant'),
    r'\ba uploada\b': ('a încărca', 'Verb hibrid tehnic'),
    r'\ba downloada\b': ('a descărca', 'Verb hibrid tehnic'),
    r'\ba customiza\b': ('a personaliza', '"A personaliza" acoperă perfect sensul'),
    r'\ba debuga\b': ('a depana / a corecta', 'Folosit în programare, dar există alternative'),
    r'\ba share-ui\b': ('a distribui', 'Standard în social media, dar sună rău oral'),
    r'\ba shareui\b': ('a distribui', 'Standard în social media, dar sună rău oral'),
    r'\ba atașui\b': ('a atașa', 'Confuzie între „a atașa" și „attachment"'),
    r'\ba printa\b': ('a tipări / a imprima', 'Verb hibrid inutil'),
    r'\ba scana\b': ('a scana', 'Acceptabil în context tehnic, dar verifică'),
    r'\ba reseta\b': ('a reseta / a reinițializa', 'Acceptabil tehnic'),
    r'\ba salva\b': ('a salva', 'Acceptabil, dar verifică contextul'),
    r'\ba edita\b': ('a edita', 'Acceptabil, intrat în uz'),
    r'\ba instala\b': ('a instala', 'Corect, deja în DEX'),
    r'\ba formata\b': ('a formata', 'Acceptabil tehnic'),
    r'\ba upgrada\b': ('a actualiza / a îmbunătăți', 'Verb hibrid'),
    r'\ba loga\b': ('a se conecta / a se autentifica', 'Verb hibrid'),
    r'\ba deloga\b': ('a se deconecta', 'Verb hibrid'),
    r'\ba testa\b': ('a testa', 'Corect, deja în DEX'),
    r'\ba procesa\b': ('a procesa / a prelucra', 'Verifică contextul'),
    r'\ba accesa\b': ('a accesa', 'Corect, deja în DEX'),
    r'\ba clipui\b': ('a tunde / a tăia', 'Verb hibrid din "to clip"'),
    r'\ba trenda\b': ('a fi în tendință', 'Verb hibrid din "to trend"'),
}

# =============================================================================
# 2. CALCURI LINGVISTICE (Literal Word-for-Word Translations)
# These seem correct at first glance but violate Romanian logic
# =============================================================================
CALCURI_LINGVISTICE = {
    # === EXPRESII ȘI LOCUȚIUNI (Calcuri de structură) ===
    r'\bface sens\b': ('are sens', 'În română sensul se „are", nu se „face" (to make sense)'),
    r'\ba face sens\b': ('a avea sens', 'În română sensul se „are", nu se „face"'),
    r'\bla sfârșitul zilei\b': ('în cele din urmă / în concluzie', 'Calc din "at the end of the day"'),
    r'\bîn termeni de\b': ('în ceea ce privește / referitor la', 'Calc din "in terms of"'),
    r'\bface o diferență\b': ('contează / schimbă lucrurile', 'Calc din "makes a difference"'),
    r'\ba face o diferență\b': ('a conta / a schimba lucrurile', 'Calc din "to make a difference"'),
    r'\bnu chiar\b': ('nu tocmai / nu prea / deloc', 'Calc din "not really"'),
    r'\ba lua ceva de-a gata\b': ('a considera de la sine înțeles', 'Calc din "to take for granted"'),
    r'\ba juca un rol\b': ('a avea un rol', 'În RO „joci" doar în piese, nu roluri abstracte'),
    r'\bjoacă un rol\b': ('are un rol', 'În RO „joci" doar în piese'),
    r'\bsună familiar\b': ('îmi pare cunoscut', 'Calc din "sounds familiar"'),
    r'\ba ridica întrebări\b': ('a trezi semne de întrebare', 'Calc din "to raise questions"'),
    r'\bridică întrebări\b': ('trezește semne de întrebare', 'Calc din "raises questions"'),
    r'\ba face o programare\b': ('a se programa / a face o rezervare', 'Calc din "to make an appointment"'),
    
    # === VERBE CU SENSURI FORȚATE ===
    r'\ba adresa o problemă\b': ('a aborda / a trata / a rezolva', '"To address" ≠ a pune o adresă'),
    r'\badresez această problemă\b': ('abordez această problemă', '"To address" ≠ a pune o adresă'),
    r'\badresează problema\b': ('abordează problema', '"To address" ≠ a pune o adresă'),
    r'\ba salva timp\b': ('a economisi timp / a câștiga timp', '"To save time" = a economisi, nu a salva'),
    r'\bsalvează timp\b': ('economisește timp', '"Saves time" = economisește'),
    r'\ba salva bani\b': ('a economisi bani', '"To save money" = a economisi'),
    r'\bsalvează bani\b': ('economisește bani', '"Saves money" = economisește'),
    r'\ba rula o afacere\b': ('a conduce / a gestiona o afacere', '"To run a business" ≠ a rula'),
    r'\brulează afacerea\b': ('conduce afacerea', '"Runs the business" ≠ rulează'),
    r'\ba aplica pentru\b': ('a candida / a se înscrie', '"To apply for" = a candida'),
    r'\baplic pentru\b': ('candidez pentru / solicit', '"I apply for" = candidez'),
    r'\ba asista pe cineva\b': ('a ajuta pe cineva', 'În RO „a asista" = a fi prezent'),
    r'\bîl asistă\b': ('îl ajută', '"Assists him" = îl ajută'),
    r'\ba livra rezultate\b': ('a obține / a prezenta rezultate', '"To deliver results" = a obține'),
    r'\blivrează rezultate\b': ('obține rezultate', '"Delivers results" = obține'),
    r'\ba servi un scop\b': ('a deservi / a fi util pentru', '"To serve a purpose"'),
    r'\bservește un scop\b': ('este util pentru / deservește', '"Serves a purpose"'),
    r'\ba naviga o situație\b': ('a gestiona / a se descurca în', '"To navigate a situation"'),
    r'\bnavighează situația\b': ('gestionează situația', '"Navigates the situation"'),
    
    # === Din lista anterioară ===
    r'\baplicant\b': ('candidat', 'În română, aplicantul aplică un strat de vopsea'),
    r'\baplicanți\b': ('candidați', 'În română, aplicantul aplică un strat de vopsea'),
    r'\ba asuma\b': ('a presupune', '"I assume" = presupun. În RO, „a-și asuma" = a-și lua răspunderea'),
    r'\basumez\b': ('presupun', '"I assume" = presupun'),
    r'\bdeterminare\b': ('hotărâre / ambiție', '"Determination" adesea confundat cu ambiția'),
    r'\bexpertiză\b': ('experiență / competență', 'În RO, expertiza = raportul unui expert'),
    r'\blocație\b': ('loc / sediu / spațiu', 'Locația = chiria plătită (termen juridic)'),
    r'\blocații\b': ('locuri / sedii / spații', 'Locația = chiria plătită (termen juridic)'),
    r'\bîn ordine să\b': ('pentru a', 'Calc din "in order to"'),
    r'\ba lua loc\b': ('a avea loc / a se întâmpla', 'Calc din "to take place"'),
    r'\bia loc\b': ('are loc / se întâmplă', 'Calc din "takes place"'),
    r'\ba realiza\b': ('a-și da seama / a înțelege', 'Calc din "to realize" când e înțelegere'),
    r'\brealizez că\b': ('îmi dau seama că', '"I realize that" = îmi dau seama'),
    r'\ba suporta\b': ('a sprijini / a susține', 'Calc: "to support" ≠ "a suporta" (a tolera)'),
    r'\bte suport\b': ('te sprijin / te susțin', 'Calc: "I support you" ≠ "te suport"'),
    r'\bîn același timp\b': ('totodată / simultan', 'Calc din "at the same time" - uneori OK'),
    r'\bpe de altă parte\b': ('pe de altă parte', 'Verifică dacă există și "pe de o parte"'),
    r'\bdin punct de vedere\b': ('sub aspectul / referitor la', 'Calc din "from the point of view"'),
    r'\ba lua o decizie\b': ('a decide / a hotărî', 'Calc din "to take a decision"'),
    r'\bia o decizie\b': ('decide / hotărăște', '"Takes a decision"'),
    r'\bîn ceea ce privește\b': ('referitor la / despre', 'Calc din franceză "en ce qui concerne"'),
    r'\bla nivel de\b': ('la nivelul / în privința', 'Calc din franceză "au niveau de"'),
    
    # === PREPOZIȚII GREȘITE ===
    r'\bsub presiune\b': ('la presiune / presat', 'Calc din "under pressure" - verifică'),
    r'\bsub circumstanțe\b': ('în aceste circumstanțe', 'Calc din "under the circumstances"'),
    r'\bpentru moment\b': ('deocamdată', 'Calc din "for the moment"'),
    r'\bbazat pe\b': ('pe baza / fundamentat pe', 'Calc din "based on"'),
    r'\bdepinde pe\b': ('depinde de', 'Greșeală frecventă - corect: depinde DE'),
}


# =============================================================================
# 3. FALSE FRIENDS (Words with deturned meaning)
# Words existing in both languages with totally different meanings
# =============================================================================
FALSE_FRIENDS = {
    # === CLASICI ===
    r'\bpatetic\b': ('emoționant / plin de patos', 'Greșit: penibil. Corect în RO: emoționant'),
    r'\bevidență\b': ('caracter evident', 'Greșit: dovadă. "Evidence" = probă/dovadă'),
    r'\bfacilitate\b': ('ușurință', 'Greșit: instalație/clădire. "Facility" = clădire'),
    r'\bfacilități\b': ('ușurințe / dotări', 'Greșit: instalații. "Facilities" = dotări'),
    r'\beventual\b': ('posibil / în caz de nevoie', 'Greșit: în cele din urmă. "Eventually" = în final'),
    r'\bpreservativ\b': ('articol protecție intimă', 'Greșit: conservant. "Preservative" = conservant'),
    r'\bactualmente\b': ('în prezent / în mod real', '"Actually" = de fapt, nu "actualmente"'),
    r'\bsensibil\b': ('înțelept / rezonabil', '"Sensible" = înțelept, nu sensibil (sensitive)'),
    r'\blibrar\b': ('bibliotecar', '"Librarian" = bibliotecar, nu librar'),
    r'\blibrărie\b': ('bibliotecă', '"Library" = bibliotecă, nu librărie (bookshop)'),
    r'\bsimpatic\b': ('compătimitor', '"Sympathetic" = compătimitor, nu simpatic'),
    r'\bcomprehensiv\b': ('cuprinzător', '"Comprehensive" = cuprinzător, nu comprehensibil'),
    r'\brealizare\b': ('conștientizare', 'Verifică: "realization" poate fi conștientizare'),
    r'\brezumă\b': ('reia', '"Resume" = a relua, nu a rezuma'),
    r'\bnovel\b': ('roman', '"Novel" = roman, nu nuvelă'),
    r'\bcarpet\b': ('covor', '"Carpet" = covor, nu carpetă'),
    r'\bmagazin\b': ('revistă', '"Magazine" = revistă. Magazin RO = shop/store'),
    
    # === ADJECTIVE ȘI SUBSTANTIVE PĂCĂLITOARE ===
    r'\bagresiv\b': ('puternic / hotărât', 'Greșit: violent. "Aggressive plan" = plan hotărât'),
    r'\bplan agresiv\b': ('plan ambițios / hotărât', '"Aggressive plan" ≠ plan violent'),
    r'\bdomestic\b': ('intern / casnic', 'Greșit: îmblânzit. "Domestic flight" = zbor intern'),
    r'\bzbor domestic\b': ('zbor intern', '"Domestic flight" = zbor intern'),
    r'\barie\b': ('suprafață / melodie', 'Greșit: domeniu. "Area of expertise" = domeniu'),
    r'\barie de expertiză\b': ('domeniu de expertiză', '"Area of expertise" = domeniu'),
    r'\bsuport\b': ('asistență / sprijin', '"Support" = asistență, nu susținere fizică doar'),
    r'\bsuport clienți\b': ('asistență clienți', '"Customer support" = asistență'),
    r'\bviziune încețoșată\b': ('vedere încețoșată', '"Blurred vision" = vedere, nu viziune'),
}


# =============================================================================
# 4. JARGON CORPORATE & FILLERS
# Filler words that pollute everyday speech
# =============================================================================
JARGON_CORPORATE = {
    r'\bbasically\b': ('în principiu / practic', 'Anglicism de umplutură'),
    r'\bactually\b': ('de fapt / în realitate', 'Anglicism de umplutură'),
    r'\banyway\b': ('oricum / în fine', 'Anglicism de umplutură'),
    r'\bmeeting\b': ('ședință / întâlnire', 'Anglicism corporate'),
    r'\bmeetinguri\b': ('ședințe / întâlniri', 'Anglicism corporate'),
    r'\bfeedback\b': ('reacție / opinie / impresie', 'Anglicism - acceptabil în context tehnic'),
    r'\binsight\b': ('perspectivă / înțelegere profundă', 'Anglicism corporate'),
    r'\binsighturi\b': ('perspective / înțelegeri', 'Anglicism corporate'),
    r'\boverwhelming\b': ('copleșitor', 'Anglicism - avem cuvânt românesc'),
    r'\bchallenging\b': ('provocator / dificil', 'Anglicism corporate'),
    r'\bsketchy\b': ('dubios / suspect', 'Anglicism slang'),
    r'\bokay\b': ('bine / în regulă', 'Anglicism - acceptabil informal'),
    r'\bok\b': ('bine / în regulă', 'Anglicism - acceptabil informal'),
    r'\bcool\b': ('grozav / mișto', 'Anglicism - acceptabil informal'),
    r'\bsorry\b': ('scuze / îmi pare rău', 'Anglicism'),
    r'\bweekend\b': ('sfârșit de săptămână', 'Anglicism - intrat în uz, acceptabil'),
    r'\bdeadline\b': ('termen limită', 'Anglicism corporate'),
    r'\bdeadlineuri\b': ('termene limită', 'Anglicism corporate'),
    r'\btarget\b': ('țintă / obiectiv', 'Anglicism corporate'),
    r'\btargeturi\b': ('ținte / obiective', 'Anglicism corporate'),
    r'\bcheck\b': ('verifică / bifează', 'Anglicism'),
    r'\bbrand\b': ('marcă', 'Anglicism - intrat în uz'),
    r'\bbranduri\b': ('mărci', 'Anglicism'),
    r'\btraining\b': ('instruire / pregătire', 'Anglicism - acceptabil în context HR'),
    r'\btraininguri\b': ('instruiri / pregătiri', 'Anglicism'),
    r'\bmanager\b': ('director / administrator', 'Anglicism - intrat în uz'),
    r'\bteam\b': ('echipă', 'Anglicism'),
    r'\bteamuri\b': ('echipe', 'Anglicism'),
    r'\bperformance\b': ('performanță', 'OK în română, dar verifică'),
    r'\bdeliverabil\b': ('livrabil', 'Anglicism corporate'),
    r'\bdeliverabileuri\b': ('livrabile', 'Anglicism corporate'),
    r'\bescala\b': ('a escala / a intensifica', 'Anglicism corporate'),
    r'\bprioritiza\b': ('a prioritiza', 'Acceptabil, dar verifică'),
    r'\bfocusa\b': ('a se concentra', 'Anglicism'),
}

# =============================================================================
# 5. CONSTRUCȚII NENATURALE
# Patterns that suggest literal/artificial translation
# =============================================================================
CONSTRUCTII_NENATURALE = {
    # === Construcții artificiale ===
    r'\bel/ea\b': ('Alege pronumele potrivit', 'Construcție artificială - omite sau alege'),
    r'\bsău/sa\b': ('Alege forma potrivită', 'Construcție artificială'),
    r'\b-ul/-a\b': ('Alege articolul potrivit', 'Construcție artificială'),
    
    # === Hispanisme (perifrază progresivă) ===
    r'\bsunt făcând\b': ('fac', 'Hispanism: perifrază progresivă'),
    r'\beste făcând\b': ('face', 'Hispanism: perifrază progresivă'),
    r'\beste citind\b': ('citește', 'Hispanism: perifrază progresivă'),
    r'\beste vorbind\b': ('vorbește', 'Hispanism: perifrază progresivă'),
    r'\beste mâncând\b': ('mănâncă', 'Hispanism: perifrază progresivă'),
    r'\beste dormind\b': ('doarme', 'Hispanism: perifrază progresivă'),
    
    # === VERBE DE PLASTIC (Evită construcții cu "a face + substantiv") ===
    r'\ba face un apel\b': ('a telefona / a suna', 'Verb de plastic - folosește verb direct'),
    r'\bface un apel\b': ('telefonează / sună', 'Verb de plastic - folosește verb direct'),
    r'\ba face o investigație\b': ('a investiga / a ancheta', 'Verb de plastic'),
    r'\bface o investigație\b': ('investighează / anchetează', 'Verb de plastic'),
    r'\ba face o vizită\b': ('a vizita', 'Verb de plastic - folosește verb direct'),
    r'\bface o vizită\b': ('vizitează', 'Verb de plastic'),
    r'\ba face o plimbare\b': ('a se plimba', 'Verb de plastic'),
    r'\bface o plimbare\b': ('se plimbă', 'Verb de plastic'),
    r'\ba face o baie\b': ('a face baie / a se spăla', 'Verifică contextul'),
    r'\ba face o greșeală\b': ('a greși', 'Verb de plastic - poți simplifica'),
    r'\bface o greșeală\b': ('greșește', 'Verb de plastic'),
    r'\ba face o încercare\b': ('a încerca', 'Verb de plastic'),
    r'\bface o încercare\b': ('încearcă', 'Verb de plastic'),
    r'\ba face o alegere\b': ('a alege', 'Verb de plastic'),
    r'\bface o alegere\b': ('alege', 'Verb de plastic'),
    r'\ba face o comparație\b': ('a compara', 'Verb de plastic'),
    r'\bface o comparație\b': ('compară', 'Verb de plastic'),
    r'\ba face o propunere\b': ('a propune', 'Verb de plastic'),
    r'\bface o propunere\b': ('propune', 'Verb de plastic'),
    
    # === ABUZ DE PRONUME POSESIVE (în RO se omit adesea) ===
    r'\bmâna mea\b': ('mâna', 'Posibil abuz de posesiv - în RO se omite adesea'),
    r'\bmâinile mele\b': ('mâinile', 'Posibil abuz de posesiv'),
    r'\bochii mei\b': ('ochii', 'Posibil abuz de posesiv'),
    r'\bcapul meu\b': ('capul', 'Posibil abuz de posesiv'),
    r'\binima mea\b': ('inima', 'Posibil abuz de posesiv - verifică contextul'),
    r'\bbuzunarul meu\b': ('buzunarul', 'Posibil abuz de posesiv'),
    r'\bcasa mea\b': ('casa', 'Verifică dacă posesivul e necesar'),
    r'\bmașina mea\b': ('mașina', 'Verifică dacă posesivul e necesar'),
    
    # === EXCLAMAȚII TRADUSE LITERAL ===
    r'\bHey!\b': ('Hei! / Ascultă! / Măi!', 'Exclamație - adaptează la context'),
    r'\bHey,\b': ('Hei, / Ascultă, / Uite,', 'Exclamație - adaptează la context'),
    r'\bWow!\b': ('Uau! / Ce tare!', 'Exclamație - adaptează'),
    r'\bOh my God\b': ('Doamne! / Dumnezeule!', 'Exclamație - adaptează la context'),
    r'\bOh God\b': ('Doamne! / Vai!', 'Exclamație - adaptează'),
    r'\bOops\b': ('Ups / Oops', 'OK, dar verifică'),
    r'\bYeah\b': ('Da / Așa e', 'Anglicism informal'),
    r'\bNope\b': ('Nu / Ba nu', 'Anglicism informal'),
    r'\bYep\b': ('Da / Mda', 'Anglicism informal'),
    
    # === SUGESTII DE VARIETATE ===
    # Notă: "doar" nu e greșit, dar AI-ul îl folosește excesiv
    # Detectăm doar când apare de mai multe ori aproape
}

# =============================================================================
# 6. LOCUȚIUNI ȘI EXPRESII IDIOMATICE TRADUSE LITERAL
# =============================================================================
LOCUTIUNI_LITERALE = {
    r'\bla capătul zilei\b': ('în cele din urmă / până la urmă', 'Calc din "at the end of the day"'),
    r'\ba lua în considerare\b': ('a considera / a ține cont de', 'OK, dar uneori se poate simplifica'),
    r'\ba avea de-a face cu\b': ('a se confrunta cu', 'Verifică dacă sună natural'),
    r'\bdin când în când\b': ('uneori / câteodată', 'OK, dar verifică varietatea'),
    r'\bpână la un punct\b': ('într-o oarecare măsură', 'Calc din "up to a point"'),
    r'\bîn ciuda faptului că\b': ('deși / cu toate că', 'Poate fi simplificat'),
    r'\bdin acest motiv\b': ('de aceea / astfel', 'OK, dar verifică'),
    r'\bca rezultat\b': ('prin urmare / așadar', 'Calc din "as a result"'),
    r'\bîn mod normal\b': ('de obicei / în general', 'Galicism'),
    r'\bîn mod evident\b': ('evident / clar', 'Poate fi simplificat'),
    r'\bîn mod special\b': ('în special / mai ales', 'Poate fi simplificat'),
}

# =============================================================================
# 7. DIATEZA PASIVĂ ABUZIVĂ (The Passive Trap)
# În română, diateza activă e mai dinamică
# =============================================================================
DIATEZA_PASIVA = {
    r'\ba fost deschis de\b': ('X a deschis', 'Diateza pasivă - consideră diateza activă'),
    r'\ba fost închis de\b': ('X a închis', 'Diateza pasivă'),
    r'\ba fost găsit de\b': ('X a găsit', 'Diateza pasivă'),
    r'\ba fost văzut de\b': ('X a văzut', 'Diateza pasivă'),
    r'\ba fost făcut de\b': ('X a făcut', 'Diateza pasivă'),
    r'\ba fost scris de\b': ('X a scris', 'Diateza pasivă'),
    r'\ba fost spus de\b': ('X a spus', 'Diateza pasivă'),
    r'\ba fost luat de\b': ('X a luat', 'Diateza pasivă'),
    r'\ba fost trimis de\b': ('X a trimis', 'Diateza pasivă'),
    r'\ba fost rezolvat de\b': ('X a rezolvat', 'Diateza pasivă - sună birocratic'),
    r'\ba fost creat de\b': ('X a creat', 'Diateza pasivă'),
    r'\ba fost lovit de\b': ('X l-a lovit', 'Diateza pasivă'),
    r'\ba fost omorât de\b': ('X l-a omorât', 'Diateza pasivă'),
    r'\ba fost salvat de\b': ('X l-a salvat', 'Diateza pasivă'),
    r'\bau fost găsiți de\b': ('X i-a găsit', 'Diateza pasivă'),
    r'\bau fost văzuți de\b': ('X i-a văzut', 'Diateza pasivă'),
}

# =============================================================================
# 8. ADJECTIVE PLATE (Very/Really Overuse)
# În română avem adjective puternice, nu "foarte + adj"
# =============================================================================
ADJECTIVE_PLATE = {
    r'\bfoarte speriat\b': ('terorizat / înspăimântat', 'Adjectiv plat - folosește sinonim puternic'),
    r'\bfoarte speriată\b': ('terorizată / înspăimântată', 'Adjectiv plat'),
    r'\bfoarte frig\b': ('un ger de crapă pietrele / un frig năprasnic', 'Adjectiv plat'),
    r'\bfoarte cald\b': ('o căldură toridă / arzător', 'Adjectiv plat'),
    r'\bfoarte mare\b': ('imens / uriaș / colosal', 'Adjectiv plat - folosește sinonim'),
    r'\bfoarte mic\b': ('minuscul / infim / pirpiriu', 'Adjectiv plat'),
    r'\bfoarte frumos\b': ('superb / splendid / minunat', 'Adjectiv plat'),
    r'\bfoarte frumoasă\b': ('superbă / splendidă', 'Adjectiv plat'),
    r'\bfoarte urât\b': ('oribil / hidoș / respingător', 'Adjectiv plat'),
    r'\bfoarte bun\b': ('excelent / remarcabil', 'Adjectiv plat'),
    r'\bfoarte rău\b': ('groaznic / îngrozitor', 'Adjectiv plat'),
    r'\bfoarte trist\b': ('devastat / abătut / îndurerat', 'Adjectiv plat'),
    r'\bfoarte tristă\b': ('devastată / abătută', 'Adjectiv plat'),
    r'\bfoarte fericit\b': ('extaziat / în al nouălea cer', 'Adjectiv plat'),
    r'\bfoarte fericită\b': ('extaziată / în culmea fericirii', 'Adjectiv plat'),
    r'\bfoarte furios\b': ('înfuriat / turbat de furie', 'Adjectiv plat'),
    r'\bfoarte obosit\b': ('epuizat / frânt de oboseală', 'Adjectiv plat'),
    r'\bfoarte obosită\b': ('epuizată / frântă', 'Adjectiv plat'),
    r'\bfoarte important\b': ('crucial / esențial / vital', 'Adjectiv plat'),
    r'\bfoarte importantă\b': ('crucială / esențială', 'Adjectiv plat'),
    r'\bfoarte înalt\b': ('înalt cât un brad / uriaș', 'Adjectiv plat'),
    r'\bfoarte scund\b': ('pitic / scund de tot', 'Adjectiv plat'),
    r'\bfoarte greu\b': ('extrem de greu / dificil', 'Adjectiv plat'),
    r'\bfoarte ușor\b': ('simplu / o joacă de copii', 'Adjectiv plat'),
    r'\bfoarte repede\b': ('fulgerător / în trombă', 'Adjectiv plat'),
    r'\bfoarte încet\b': ('în slow motion / agale', 'Adjectiv plat'),
    r'\bfoarte bogat\b': ('plin de bani / nabab', 'Adjectiv plat'),
    r'\bfoarte sărac\b': ('lefter / muritor de foame', 'Adjectiv plat'),
    r'\bfoarte mult\b': ('enorm / o grămadă', 'Adjectiv plat'),
    r'\bfoarte puțin\b': ('aproape nimic / un strop', 'Adjectiv plat'),
    # Really
    r'\bchiar speriat\b': ('terorizat', 'Adjectiv plat'),
    r'\bchiar frumos\b': ('superb', 'Adjectiv plat'),
}

# =============================================================================
# 9. PREPOZIȚII TRADUSE LITERAL
# =============================================================================
PREPOZITII_LITERALE = {
    r'\bîn soare\b': ('la soare', '"In the sun" = la soare, nu în soare'),
    r'\bîn ploaie\b': ('prin ploaie / pe ploaie', 'Verifică contextul'),
    r'\bfrică de\b': ('teamă de / se teme de', 'Verifică: "afraid of" poate fi "teme-te de"'),
    r'\binteresată în\b': ('interesată de', '"Interested in" = interesată DE'),
    r'\binteresat în\b': ('interesat de', '"Interested in" = interesat DE'),
    r'\bbun la\b': ('priceput la / talentat la', '"Good at" = priceput la'),
    r'\bdiferit de\b': ('diferit de', 'Corect, dar verifică fluiditatea'),
    r'\bsimilar cu\b': ('asemănător cu / similar cu', 'OK'),
}

# =============================================================================
# 10. REPETIȚIA PRONUMELOR (Pronume inutile)
# În română, persoana reiese din terminația verbului
# =============================================================================
PRONUME_REPETATE = {
    r'\bEl a\b.*\.\s*El a\b': ('Omite al doilea "El"', 'Repetiție de pronume - în RO verbul include persoana'),
    r'\bEa a\b.*\.\s*Ea a\b': ('Omite al doilea "Ea"', 'Repetiție de pronume'),
    r'\bEl s-a\b.*\.\s*El s-a\b': ('Omite al doilea "El"', 'Repetiție de pronume'),
    r'\bEa s-a\b.*\.\s*Ea s-a\b': ('Omite al doilea "Ea"', 'Repetiție de pronume'),
    # Pronume la început de propoziție (prea frecvent)
    r'^El ': ('Vezi dacă poți omite', 'Pronumele la început - în RO se poate omite'),
    r'^\s*Ea ': ('Vezi dacă poți omite', 'Pronumele la început'),
}

# =============================================================================
# 11. TOPICA ADJECTIVULUI (Adjectiv înaintea substantivului)
# În română, ordinea firească e Substantiv + Adjectiv
# =============================================================================
TOPICA_ADJECTIV = {
    r'\bmisteriosul bărbat\b': ('bărbatul misterios', 'Topică inversă - "bărbatul misterios" sună mai natural'),
    r'\bmisterioasa femeie\b': ('femeia misterioasă', 'Topică inversă'),
    r'\bfrumoasa fată\b': ('fata frumoasă', 'Topică inversă - sau păstrează pentru efect stilistic'),
    r'\bînaltul bărbat\b': ('bărbatul înalt', 'Topică inversă'),
    r'\bînalta femeie\b': ('femeia înaltă', 'Topică inversă'),
    r'\btânărul bărbat\b': ('bărbatul tânăr', 'Topică inversă'),
    r'\btânăra femeie\b': ('femeia tânără', 'OK stilistic în unele contexte'),
    r'\bbătrânul om\b': ('bătrânul / omul bătrân', 'Verifică contextul'),
    r'\bvechiul prieten\b': ('prietenul vechi', 'OK, dar verifică'),
    r'\bîntunecoasa pădure\b': ('pădurea întunecată', 'Topică inversă'),
    r'\bluminoasa cameră\b': ('camera luminoasă', 'Topică inversă'),
}

# =============================================================================
# 12. ERORI DE DOMENIU SPECIFIC (Termeni financiari, juridici, tehnici)
# Traduceri literal greșite în contexte specializate
# =============================================================================
ERORI_DOMENIU = {
    # === TERMENI FINANCIARI ===
    r'\bpiețe ursine\b': ('piață bear / piață în declin', '"Bear market" = piață bear, nu "ursină"'),
    r'\bpiață ursină\b': ('piață bear / piață în scădere', '"Bear market" = piață bear'),
    r'\bpiețe taurine\b': ('piață bull / piață în creștere', '"Bull market" = piață bull'),
    r'\bpiață taurină\b': ('piață bull / piață în creștere', '"Bull market" = piață bull'),
    r'\bîn mod fiabil\b': ('cu precizie / garantat / constant', 'Construcție ciudată în română'),
    r'\be în regulă în mod fiabil\b': ('funcționează cu precizie / dă rezultate garantate', 'Traducere nenaturală'),
    
    # === TERMENI JURIDICI/BUSINESS ===
    r'\bîncorporare\b': ('înființare / constituire', '"Incorporation" = înființare firmă, nu încorporare'),
    r'\bîncorporarea sa\b': ('înființarea sa / constituirea sa', '"Its incorporation" = înființarea firmei'),
    r'\bîncorporării sale\b': ('înființării sale', '"Incorporation" = înființare'),
    r'\bincorporat\b': ('înființat / constituit', '"Incorporated" în context juridic = înființat'),
    
    # === EXPRESII CIUDATE / HALUCINAȚII ===
    r'\ba fost puteți\b': ('EROARE GRAVĂ', 'Probabil halucinație AI - verifică originalul'),
    r'\bputeți pleca la acea vreme\b': ('era desconsiderat / era luat în derâdere', 'Traducere complet greșită'),
    r'\bera desconsiderat la acea vreme\b': ('verifică contextul', 'OK, dar verifică'),
    
    # === TERMENI TEHNICI/CRYPTO ===
    r'\botravă de șobolani\b': ('otravă pentru șobolani', 'Genitiv mai natural'),
    r'\bmonedă cripto\b': ('criptomonedă', 'Termenul consacrat e "criptomonedă"'),
    r'\bvalută virtuală\b': ('monedă virtuală / criptomonedă', 'Verifică contextul'),
    
    # === ALTE ERORI FRECVENTE ===
    r'\bun grup mare\b': ('un grup numeros / o mulțime', '"A large group" = grup numeros'),
    r'\bo cantitate mare\b': ('o cantitate considerabilă', 'OK, dar verifică'),
    r'\bîntr-un mod\b': ('într-o anumită manieră', 'Poate fi simplificat'),
    
    # === NUANȚE ȘI EXPRESII IDIOMATICE (Feedback User) ===
    r'\bscris pe perete\b': ('semnele dezastrului / semnele erau evidente', 'Idiom "writing on the wall" tradus literal'),
    r'\bechipă veselă\b': ('echipă entuziastă / grup pestriț', 'În context business, "veselă" e prea ludic'),
    r'\bm-a lovit mai tare\b': ('m-a afectat mai mult / a avut un impact mai mare', 'Expresie literală - adaptează contextul emoțional'),
    r'\bam intrat all in\b': ('am mers pe mâna lor / am riscat totul', 'Sugestie literară pentru "all in"'),
    r'\bsincronizare imposibilă\b': ('noroc chior / sincronizare perfectă', 'Contextul "timing" se referă adesea la oportunitate/noroc'),
    r'\brezistența de a continua\b': ('dârzenia / perseverența', '"Grit" este activ (dârzenie), nu pasiv (rezistență)'),
    
    # === TERMENI CRYPTO & TECH (Feedback User 2) ===
    r'\bcartea albă\b': ('White Paper', 'În crypto/tech se folosește "White Paper"'),
    r'\bmoderator cheie\b': ('rol-cheie în organizare', 'Context: implicare în succesul evenimentului'),
    r'\bhashrate\b': ('putere de calcul (hashrate)', 'Explică termenul pentru publicul larg'),
    r'\bspațiul bitcoin\b': ('industria Bitcoin / ecosistemul Bitcoin', '"Space" = domeniu/industrie'),
    r'\bspațiul minier\b': ('industria minieră / sectorul minier', '"Space" = sector'),
    r'\bpunct contrare\b': ('contrapunct / punct de contrast', 'Calc din "counterpoint"'),
    r'\baproape de moarte\b': ('la limita falimentului / moment critic', 'În business: "near-death" = critic'),
    r'\bcine este cine\b': ('elita / figurile emblematice', '"Who\'s who" = cei mai importanți'),
    r'\bsă-i prezint o copie\b': ('să-i ofer un exemplar', '"Copy" (carte) = exemplar, nu copie'),
    r'\bgestionare a averilor\b': ('managementul averii / gestionarea activelor', 'Pluralul "averilor" sună nefiresc'),
    r'\btradiția de toastare\b': ('arta toastului / toasturile', '"Toasting" = a ține un toast, nu a prăji pâine'),
    r'\bne îmbibam acolo\b': ('ne relaxam / stăteam la înmuiat', '"Soaking" (jacuzzi) = relaxare, nu îmbibare'),
    r'\bne-a împuiat cu întrebări\b': ('ne-a asaltat / ne-a bombardat', '"Împuiat" e informal/negativ'),
    r'\bcompania lui\b': ('prezența lui / societatea lui', 'Context social: "his company" = prezența sa'),
    r'\btranzacțiile bitcoin.*este opusul\b': ('sunt opusul', 'Dezacord subiect-predicat'),
    r'\bacesta ar fi transmis pentru toasturi\b': ('era dat din mână în mână', 'Idiom: "passed around"'),
    r'\bexchange\b': ('bursă / platformă de tranzacționare', 'Preferabil termen românesc în context formal'),
    r'\bhack major\b': ('atac informatic major / compromitere a securității', 'Mai elegant'),
    r'\bactorii nelegiuiți\b': ('actori rău-intenționați / elemente infracționale', '"Nelegiuit" sună arhaic'),
    r'\bamintiri grozave\b': ('experiențe memorabile', 'Context: "of that great memory" = experiență, nu amintire'),
    r'\btitlurile\b': ('senzaționalul din presă / titlurile de cancan', 'Context: "headlines" vs realitate'),
    r'\bdecalajul critic\b': ('prăpastia / lipsa de comunicare', 'În business: "gap" = prăpastie/lipsă, nu decalaj'),
    r'\baccelera calendarul\b': ('devansa calendarul de implementare', 'Termen management proiect'),
    r'\bnumerar\b': ('lichidități', 'În tranzacții corporative: "cash" = lichidități'),
    r'\bzgârierea stilourilor\b': ('sunetul discret al penițelor', 'Stil narativ: atmosferă de "putere discretă"'),
    r'\ba toastat\b': ('a ridicat un toast', '"Toasted" = a ridicat un toast, nu a toastat'),
    r'\borizontul sclipitor\b': ('Orizontul sclipitor (Portul Victoria)', 'Localizare: adaugă context geografic Hong Kong'),
    
    # === LITERALISME DE BUSINESS (False Friends) ===
    r'\bconductă de clienți\b': ('flux de clienți / portofoliu de proiecte', '"Pipeline" = flux/portofoliu, nu conductă'),
    r'\bemisiune suprascrisă\b': ('subscrisă în exces / cerere peste ofertă', '"Oversubscribed" = cerere mare'),
    r'\blichidități pe bilanț\b': ('în bilanț / în activele companiei', 'Prepoziția corectă e "în", nu "pe"'),
    
    # === ANGLICISME DE STRUCTURĂ (Copy-Paste) ===
    r'\binutil să mai spunem\b': ('nici nu mai trebuie menționat / de la sine înțeles', 'Structură fixă din engleză'),
    r'\bfactor de schimbare\b': ('motorul schimbării / cel care aduce schimbarea', '"Change agent" = motorul schimbării'),
    r'\bagent de schimbare\b': ('motorul schimbării', '"Change agent" = motorul schimbării'),
    r'\bbăieții bitcoin\b': ('grupul cu Bitcoin-ul / echipa Bitcoin', '"Boys" poate suna pueril/peiorativ'),
    
    # === ERORI DE NUANȚĂ TEHNICĂ ===
    r'\ba raportat prețul\b': ('afișa prețul / indica prețul', 'Aplicațiile afișează, nu raportează'),
    r'\balocare\b': ('cotă / participare', 'În investiții: "allocation" = cotă'),
    
    # === CONTEXT POLIȚIE/ACȚIUNE ===
    r'\bplecai țopăind\b': ('ai dispărut imediat / te-ai îndepărtat rapid', '"Hopping away" = a pleca rapid, nu a țopăi'),
    r'\bdificil de contactat\b': ('greu de găsit', '"Hard to reach" = greu de găsit'),
}

class StyleChecker:
    """
    Real-time style checker for Romanian translations.
    Detects issues during translation, not just at verification.
    """
    
    # Severity levels
    CRITICAL = 'critical'  # Obvious mistakes - red
    WARNING = 'warning'    # Worth checking - purple  
    INFO = 'info'          # Suggestions only - no highlight
    
    # Categories with their severities
    CATEGORY_SEVERITY = {
        'verb_hibrid': WARNING,
        'calc': WARNING,
        'false_friend': CRITICAL,  # These are usually errors
        'jargon': INFO,
        'constructie': WARNING,
    }
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize style checker.
        
        Args:
            strict_mode: If True, also flag INFO-level issues
        """
        self.strict_mode = strict_mode
        
        # Compile all patterns for efficiency
        self._compiled_patterns = []
        
        for pattern, (suggestion, explanation) in VERBE_HIBRIDE.items():
            self._compiled_patterns.append({
                'regex': re.compile(pattern, re.IGNORECASE),
                'suggestion': suggestion,
                'explanation': explanation,
                'category': 'verb_hibrid',
                'severity': self.WARNING,
            })
        
        for pattern, (suggestion, explanation) in CALCURI_LINGVISTICE.items():
            self._compiled_patterns.append({
                'regex': re.compile(pattern, re.IGNORECASE),
                'suggestion': suggestion,
                'explanation': explanation,
                'category': 'calc',
                'severity': self.WARNING,
            })
        
        for pattern, (suggestion, explanation) in FALSE_FRIENDS.items():
            self._compiled_patterns.append({
                'regex': re.compile(pattern, re.IGNORECASE),
                'suggestion': suggestion,
                'explanation': explanation,
                'category': 'false_friend',
                'severity': self.CRITICAL,
            })
        
        for pattern, (suggestion, explanation) in JARGON_CORPORATE.items():
            self._compiled_patterns.append({
                'regex': re.compile(pattern, re.IGNORECASE),
                'suggestion': suggestion,
                'explanation': explanation,
                'category': 'jargon',
                'severity': self.INFO,
            })
        
        for pattern, (suggestion, explanation) in CONSTRUCTII_NENATURALE.items():
            self._compiled_patterns.append({
                'regex': re.compile(pattern, re.IGNORECASE),
                'suggestion': suggestion,
                'explanation': explanation,
                'category': 'constructie',
                'severity': self.WARNING,
            })
        
        for pattern, (suggestion, explanation) in LOCUTIUNI_LITERALE.items():
            self._compiled_patterns.append({
                'regex': re.compile(pattern, re.IGNORECASE),
                'suggestion': suggestion,
                'explanation': explanation,
                'category': 'locutiune',
                'severity': self.WARNING,
            })
        
        for pattern, (suggestion, explanation) in DIATEZA_PASIVA.items():
            self._compiled_patterns.append({
                'regex': re.compile(pattern, re.IGNORECASE),
                'suggestion': suggestion,
                'explanation': explanation,
                'category': 'pasiv',
                'severity': self.WARNING,
            })
        
        for pattern, (suggestion, explanation) in ADJECTIVE_PLATE.items():
            self._compiled_patterns.append({
                'regex': re.compile(pattern, re.IGNORECASE),
                'suggestion': suggestion,
                'explanation': explanation,
                'category': 'adj_plat',
                'severity': self.INFO,  # Sugestie, nu eroare
            })
        
        for pattern, (suggestion, explanation) in PREPOZITII_LITERALE.items():
            self._compiled_patterns.append({
                'regex': re.compile(pattern, re.IGNORECASE),
                'suggestion': suggestion,
                'explanation': explanation,
                'category': 'prepozitie',
                'severity': self.WARNING,
            })
        
        for pattern, (suggestion, explanation) in PRONUME_REPETATE.items():
            self._compiled_patterns.append({
                'regex': re.compile(pattern, re.IGNORECASE | re.MULTILINE),
                'suggestion': suggestion,
                'explanation': explanation,
                'category': 'pronume',
                'severity': self.WARNING,
            })
        
        for pattern, (suggestion, explanation) in TOPICA_ADJECTIV.items():
            self._compiled_patterns.append({
                'regex': re.compile(pattern, re.IGNORECASE),
                'suggestion': suggestion,
                'explanation': explanation,
                'category': 'topica',
                'severity': self.INFO,  # Stilistic, nu eroare
            })
        
        for pattern, (suggestion, explanation) in ERORI_DOMENIU.items():
            self._compiled_patterns.append({
                'regex': re.compile(pattern, re.IGNORECASE),
                'suggestion': suggestion,
                'explanation': explanation,
                'category': 'domeniu',
                'severity': self.CRITICAL,  # Erori de sens grave
            })
    
    def check(self, text: str) -> List[Dict]:
        """
        Check text for style issues.
        
        Args:
            text: Romanian text to check
            
        Returns:
            List of issues found, each with:
            - matched_text: The problematic text
            - suggestion: Recommended replacement
            - explanation: Why it's an issue
            - category: Type of issue
            - severity: critical/warning/info
            - start: Start position in text
            - end: End position in text
        """
        issues = []
        
        for pattern_info in self._compiled_patterns:
            # Skip INFO level unless in strict mode
            if not self.strict_mode and pattern_info['severity'] == self.INFO:
                continue
            
            for match in pattern_info['regex'].finditer(text):
                issues.append({
                    'matched_text': match.group(),
                    'suggestion': pattern_info['suggestion'],
                    'explanation': pattern_info['explanation'],
                    'category': pattern_info['category'],
                    'severity': pattern_info['severity'],
                    'start': match.start(),
                    'end': match.end(),
                })
        
        return issues
    
    def has_issues(self, text: str) -> bool:
        """Quick check if text has any issues."""
        for pattern_info in self._compiled_patterns:
            if not self.strict_mode and pattern_info['severity'] == self.INFO:
                continue
            if pattern_info['regex'].search(text):
                return True
        return False
    
    def get_severity(self, text: str) -> Optional[str]:
        """
        Get the highest severity of issues in text.
        
        Returns:
            'critical', 'warning', 'info', or None if no issues
        """
        issues = self.check(text)
        if not issues:
            return None
        
        severities = [i['severity'] for i in issues]
        if self.CRITICAL in severities:
            return self.CRITICAL
        if self.WARNING in severities:
            return self.WARNING
        return self.INFO


# Singleton instance
_checker: Optional[StyleChecker] = None

def get_style_checker(strict_mode: bool = False) -> StyleChecker:
    """Get or create singleton style checker."""
    global _checker
    if _checker is None or _checker.strict_mode != strict_mode:
        _checker = StyleChecker(strict_mode=strict_mode)
    return _checker


def check_translation_style(text: str, strict: bool = False) -> List[Dict]:
    """
    Convenience function to check translation style.
    
    Args:
        text: Romanian text to check
        strict: Include INFO-level issues
        
    Returns:
        List of style issues
    """
    checker = get_style_checker(strict_mode=strict)
    return checker.check(text)
