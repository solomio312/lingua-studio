# Prompt extensions for specific languages
# These are appended to the base prompt when translating to the specified language
# Supports style-specific rules for context-aware translation

# =============================================================================
# MASTER PROMPT - Prepended to ALL style rules
# =============================================================================
# Uses <slang> and <tlang> placeholders that get replaced dynamically with 
# actual source/target languages when the prompt is constructed.

master_prompt = '''TRANSLATION TASK: Translate the following text from <slang> to <tlang>.

You are a professional literary translator specializing in <tlang>. Your task is to produce a natural, idiomatic translation that reads as if it were originally written in <tlang>.

CORE PRINCIPLES:
- Translate meaning and intent, not words
- Adapt idioms and cultural references appropriately
- Maintain the author's voice and style
- Preserve emotional tone and narrative flow
- Never add explanations or commentary
- Never omit any content from the source

'''

anthropic = {
    'Hebrew (with Niqqud)': 'Ensure that all text in Hebrew is with Niqqud, '
    'a system of diacritical signs used to represent vowels or distinguish '
    'between alternative pronunciations of letters.',
}

# =============================================================================
# ROMANIAN STYLE RULES - Modular System
# =============================================================================

# Base rules applied to ALL Romanian translations
romanian_base_rules = '''
CRITICAL: TAG MASKING MARKERS PRESERVATION
===========================================
The text MAY contain special markers formatted as [[t1]], [[t2]], [[t3]], etc.
These markers represent HTML structure (links, footnotes, formatting) that MUST be preserved.

YOU MUST:
1. PRESERVE all markers EXACTLY as they appear (including the double brackets)
2. Keep markers in the SAME RELATIVE POSITION within translated sentences
3. Do NOT translate, modify, or remove ANY marker
4. If a marker is between words, keep it between the corresponding translated words

Example:
Original: "This is a [[t1]]footnote[[t2]] in the text."
Correct: "Aceasta este o [[t1]]notă de subsol[[t2]] în text."
WRONG: "Aceasta este o notă de subsol în text." (markers removed!)
WRONG: "[[t1]][[t2]]Aceasta este o notă de subsol în text." (markers moved!)
===========================================

CRITICAL STYLISTIC RULES for natural Romanian (MUST FOLLOW):


1. ACTIVE VOICE: Use active voice, NOT passive. 
   ❌ "Ușa a fost deschisă de Alex" → ✅ "Alex a deschis ușa"

2. OMIT UNNECESSARY PRONOUNS: Romanian verbs include the person.
   ❌ "El s-a uitat la ea. El i-a spus..." → ✅ "S-a uitat la ea și i-a spus..."

3. AVOID "foarte + adjectiv": Use powerful synonyms.
   ❌ "Era foarte speriat" → ✅ "Era terorizat"

4. USE DIRECT VERBS, not "a face + noun":
   ❌ "a face un apel" → ✅ "a telefona"

5. POSSESSIVE PRONOUNS: Omit when obvious from context.
   ❌ "mâna mea în buzunarul meu" → ✅ "mâna în buzunar"

6. ADJECTIVE ORDER: Adjective usually follows noun.
   ❌ "misteriosul bărbat" → ✅ "bărbatul misterios"

7. AVOID literal calques:
   ❌ "face sens" → ✅ "are sens"
   ❌ "la sfârșitul zilei" → ✅ "până la urmă"

8. Watch PREPOSITIONS:
   ❌ "în soare" → ✅ "la soare"
   ❌ "interesat în" → ✅ "interesat de"

9. IDIOMS - AVOID LITERAL TRANSLATIONS:
   ❌ "to toast someone" → "a toasta"
   ✅ USE: "a ridica un toast" / "a ține un toast"
   
   ❌ "X is a generous term" → literal
   ✅ USE: "e exagerat să spui X" / "X e un termen prea blând"
   
   ❌ "lose my shirt" → "a pierde cămașa"
   ✅ USE: "a pierde totul" / "a rămâne în pielea goală"
   
   ❌ "worked for luck" → "a funcționat pentru noroc"
   ✅ USE: "a adus noroc" / "a insuflat noroc"
   
   ❌ "in accented English" → "în engleză cu accent"
   ✅ USE: "într-o engleză cu un ușor accent" (structură mai fluidă)
   
   ❌ "ready to puff?" → "sunteți gata să trageți?"
   ✅ USE: "sunteți gata pentru un fum?" / "să-i dăm foc?" (context trabuc)
   
   ❌ "embark on an amazing journey" → clișeu corporatist
   ✅ USE: Evită traducerea literală, reformulează natural (ex: "a începe o aventură")

10. PROVERBE - FOLOSEȘTE FORMA CONSACRATĂ:
   ❌ "Piatra rostogolita nu prinde mușchi" (literal)
   ✅ USE: "Piatra care se rostogolește nu prinde mușchi"

11. TOPICA & FLUENȚĂ:
   - Evită frazele prea lungi care păstrează ordinea din engleză
   - Reformulează pentru a suna decisiv, concis
   - Împarte propozițiile complexe în unități mai scurte
   - Ordinea SVO din engleză trebuie adesea adaptată cu particule de legătură

12. GENITIV/DATIV (LIMBA FLEXIONARĂ - CRITICAL!):
   - Română are declinări! Folosește "al", "a", "ai", "ale" corect
   - Terminațiile substantivelor se schimbă:
     ❌ "procesul de deconvertire" când trebuie genitiv
     ✅ "procesul deconvertirii" / "perspectivă asupra deconvertirii"
   - ATENȚIE la articolul hotărât în genitiv:
     ❌ "circumstanțele pierdere credinței"
     ✅ "circumstanțele pierderii credinței"

13. PREPOZIȚII LA FINAL DE FRAZĂ (EN→RO):
   - În engleză: propoziții terminate cu prepoziție sunt normale
   - În română: prepoziția vine ÎNAINTEA pronumelui relativ
     ❌ "what they came from" → "de unde au venit ei din"
     ✅ "de unde au venit" / "locul din care au venit"
     ❌ "what they deconverted from" → "ceea ce au deconvertit de la"
     ✅ "de la care s-au deconvertit"

14. EXPRESII FIZICE & EMOȚIONALE:
   ❌ "visible gasp" → "am răsuflat vizibil"
   ✅ USE: "mi s-a tăiat răsuflarea" / "am rămas mut de uimire"
   
   ❌ "făcut cu ochiul" (fără subiect)
   ✅ USE: "mi-a făcut cu ochiul" (structură fireasca)

15. CONTEXT CULTURAL:
   ❌ "conserve de pepene verde" (pentru deserturi orientale)
   ✅ USE: "dulceață" / "gem" ("⎋ conserve" = murături/carne la borcan)
   
   ❌ "deversorare" (termen incorect)
   ✅ USE: "deversoare" (plural de la deversor)

16. IDIOMURI CRITICE (schimbă sensul complet):
   LEGAL/POLIȚIENESC:
   • "slam dunk" → "caz beton" (NOT "slam dunk")
   • "mob hit" → "asasinat mafiot"
   • "cold case" → "dosar cu autor necunoscut"
   • "due process" → "proces echitabil"
   • "beyond reasonable doubt" → "dincolo de orice îndoială rezonabilă"
   • "open and shut case" → "caz clar"
   • "throw the book at" → "a pedepsi sever"
   
   BUSINESS/CORPORATE:
   • "game changer" → "schimbare radicală" (NOT "schimbător de joc")
   • "low-hanging fruit" → "rezultat ușor de obținut"
   • "move the needle" → "a produce un impact semnificativ"
   • "circle back" → "a reveni asupra subiectului"
   • "deep dive" → "analiză aprofundată"
   • "pain point" → "problemă critică"
   • "touch base" → "a lua legătura"
   • "run it up the flagpole" → "a testa o idee"
   
   EXPRESII COMUNE:
   • "elephant in the room" → "subiectul sensibil ignorat"
   • "throw under the bus" → "a sacrifica pe cineva"
   • "skeleton in the closet" → "secret compromițător"
   • "writing on the wall" → "semne prevestitoare"
   • "cost an arm and a leg" → "costă o avere"
   • "once in a blue moon" → "o dată la Paștele cailor"
   • "kick the bucket" → "a da colțul"
   • "piece of cake" → "floare la ureche"
   
   IDIOMURI INTELECTUALE/ACADEMICE:
   ❌ "all heat and no light" → "doar căldură și fără lumină" (NONSENS!)
   ✅ USE: "zel orb" / "pasiune lipsită de rigoare intelectuală"
   (= multă pasiune dar fără discernământ)
   
   ❌ "the proof is in the pudding" → "dovada este în budincă" (NONSENS!)
   ✅ USE: "rezultatul este cel care confirmă realitatea" / "faptele vorbesc"
   
   ❌ "to break the news" → "a sparge vestea"
   ✅ USE: "a le comunica vestea" / "a le da vestea"
   
   ❌ "out of the blue" → "din albastru"
   ✅ USE: "din senin" / "fără niciun avertisment"
   
   ❌ "coming in my space" → "venind în spațiul meu"
   ✅ USE: "nu te apropia de mine!" / "nu-mi invada spațiul!"
   
   ❌ "to compound the problem" → "pentru a agrava compus problema"
   ✅ USE: "pentru ca situația să fie și mai gravă" / "suficient de problematic este și..."
   
   ❌ "straitjacket" (metaforă) → "cămașă de forță"
   ✅ USE: "cămașă de forță" (OK) / "corset dogmatic" (mai elevat în context spiritual)

   
   TERMINOLOGIE JURIDICĂ/ACADEMICĂ:
   ❌ "body of evidence" → "corpul de probe"
   ✅ USE: "probatoriul" / "dosarul de probe"
   
   ❌ "juvenile offender" → "infractor juvenil"
   ✅ USE: "delincvent juvenil" / "minor infractor"
   
   ❌ "working knowledge" → "cunoaștere practică"
   ✅ USE: "cunoștințe temeinice" / "cunoștințe de bază"
   
   ❌ "to debunk" → "a demitiza"
   ✅ USE: "a desființa" / "a deconstrui" / "a demonta"
   
   ADJECTIVUL "DEFUNCT" (ATENȚIE!):
   ❌ "defunct publication" → "defuncta publicație"
   ✅ USE: "dispăruta publicație" / "fosta revistă"
   ("defunct" în RO = mort, pentru persoane, nu pentru publicații!)
   
   TERMINOLOGIE ACADEMICĂ/ȘTIINȚIFICĂ:
   ❌ "pinning" (specimens) → "prindeam cu ace"
   ✅ USE: "fixam cu ace" / "montam pe ace"
   
   ❌ "complete account" → "relatare completă"
   ✅ USE: "prezentare exhaustivă" / "tablou complet"
   
   ❌ "firsthand accounts" (context medical/observație) → "relatări directe"
   ✅ USE: "observație directă" / "informații de la sursă"
   
   EXPRESII ACADEMICE/FORMALE:
   ❌ "It depends" → "Totul depinde"
   ✅ USE: "Depinde de un singur lucru" / "Totul depinde de modul în care..."
   
   ❌ "assume" (premise) → "presupune"
   ✅ USE: "ce premise adoptă" / "pornește de la premisa că"
   (context: "What does this book assume?" nu e "presupune")
   
   ❌ "miscommunication" → "erori de comunicare"
   ✅ USE: "confuzii" / "erori de interpretare" / "neînțelegeri"
   
   ❌ "social scientists" → "oamenii de știință sociali"
   ✅ USE: "sociologii" / "cercetătorii în științe sociale"
   
   ❌ "undergo a transformation" → "a suferit o transformare"
   ✅ USE: "a trecut printr-o transformare" / "a experimentat"
   ("a suferi" în RO = durere, conotație negativă!)
   
   ❌ "identify with the Christian faith" → "se autointitulează cu credința"
   ✅ USE: "se autoidentifică drept creștini" / "se declară creștini"

STILISTICĂ GENERALĂ (EVITĂ LITERALISME):
   ❌ "significantly dedicated" → "dedicați cu însemnătate"
   ✅ USE: "profund dedicați" / "extrem de devotați"
   
   ❌ "judgmental persons" → "persoane care judecă"
   ✅ USE: "persoane hipercritice" / "predispuse la judecată"
   
   ❌ "for starters" → "pentru început"
   ✅ USE: "în primul rând" / "mai ales că..."
   
   ❌ "dismissed just about everything" → "desconsideram cam tot"
   ✅ USE: "îi desconsideram aproape complet spusele" (nu "cam tot"!)
   
   ❌ "she is not alone" → "nu este deloc singură"
   ✅ USE: "[Nume] nu este un caz izolat" (evită calcul lingvistic)
   
   ❌ "attribute to themselves" → "atribuie lor înșiși"
   ✅ USE: "se descriu adesea ca fiind..."
   
   ❌ "lack of willingness to believe" → "lipsa bunăvoinței de a crede"
   ✅ USE: "refuzul de a crede" ("bunăvoință" = amabilitate, nu voință!)
   
   ❌ "driving an hour and a half" → "conducerea o oră și jumătate"
   ✅ USE: "făceau un drum de o oră și jumătate" (nu "conducerea" ca substantiv)
   
   ❌ "clear from the data" → "dovedit de date"
   ✅ USE: "datele arată clar că..." (evită pasivul greoi)
   
   ❌ "counting the cost" → "numărând costul"
   ✅ USE: "evaluarea prețului plătit" / "calcularea costurilor"
   
   ❌ "high premium" → "la un preț ridicat"
   ✅ USE: "cu un cost ridicat" (pentru beneficii)
   
   ❌ "ripple effect" → "efect de undă"
   ✅ USE: "repercusiuni în lanț" / "efect de domino"
   
   ❌ "social world in which they operated" → "lumea socială în care operau"
   ✅ USE: "lumea socială în care activau" / "mediul social în care trăiau"
   ("a opera" = anglicism în acest context)
   
   ❌ "ultimate reality" → "realitatea ultimă"
   ✅ USE: "realitatea supremă" (termen filozofic consacrat)
   
   ❌ "charged at me" → "m-a încărcat"
   ✅ USE: "s-a repezit spre mine" / "m-a atacat"
   
   ❌ "bolted out the door" → "a bolțuit pe ușă"
   ✅ USE: "a ieșit val-vârtej pe ușă" / "a fugit mâncând pământul"
   
   ❌ "tantamount to" → "tantamount cu"
   ✅ USE: "echivalent cu" / "egal cu"
   
   ❌ "upstanding citizen" → "cetățean în picioare"
   ✅ USE: "cetățean onest" / "cetățean model"
   
   ❌ "detecting a pattern" → "detectând un tipar"
   ✅ USE: "a observa un tipar" / "a remarca un tipar"
   
   ❌ "cut deeply" → "a tăiat adânc"
   ✅ USE: "a lăsat o rană adâncă" / "a rănit profund"
   
   ❌ "whitewater rafting" → "rafting pe apă albă"
   ✅ USE: "rafting pe ape repezi"
   
   ❌ "built-in community" → "comunitate încorporată"
   ✅ USE: "comunitate de-a gata" / "comunitate implicită"
   
   ❌ "moving beyond the bounds" → "mutarea dincolo de granițe"
   ✅ USE: "ieșirea dincolo de granițele" (dogmatice)
   
   ❌ "lived to tell the tale" → "a trăit să spună povestea"
   ✅ USE: "au supraviețuit pentru a-și spune povestea" (nuanță de reziliență)
   
   ❌ "populate the Internet" → "populează internetul"
   ✅ USE: "populează internetul" (OK - conținut digital masiv)
   
   ❌ "emotional well-being" → "bunăstare emoțională"
   ✅ USE: "echilibru emoțional" (mai precis psihologic)
   
   ❌ "emotional vertigo" → "vertij emoțional"
   ✅ USE: "vertij emoțional" (precis)
   
   ❌ "akin to losing a close confidant" → "asemănător cu pierderea unui confident"
   ✅ USE: "asemănător cu pierderea unui confident apropiat"
   
   ❌ "snail out of its shell" → "melc din cochilie"
   ✅ USE: "melc fără cochilie" (vulnerabilitate)
   
   ❌ "bottom had dropped out" → "fundul căzuse"
   ✅ USE: "podeaua căzuse" / "senzația de prăbușire în gol"
   
   ❌ "sexual learning curve" → "curbă de învățare sexuală"
   ✅ USE: "curbă de învățare sexuală" (termen sociologic corect)
   
   ❌ "stunted his sex life" → "i-a piticit viața sexuală"
   ✅ USE: "i-a atenuat viața sexuală" / "i-a stagnat viața sexuală"
   
   ❌ "momentous loss" → "pierdere momentană" (false friend!)
   ✅ USE: "eveniment existențial major" / "pierdere capitală"
   
   ❌ "ultimate significance" → "semnificație ultimă"
   ✅ USE: "semnificație supremă" / "sens ultim"
   
   ❌ "a big blow" → "o suflare mare"
   ✅ USE: "o lovitură puternică" / "un șoc major"
   
   ❌ "captain of their ship" → "căpitanul navei lor"
   ✅ USE: "căpitanul propriei nave" (autonomie)
   
   ❌ "foundation was swept away" → "fundația a fost măturată"
   ✅ USE: "fundația a fost spulberată" (forță distructivă)
   
   ❌ "vested interest" → "interes vestit"
   ✅ USE: "interes direct" / "interes profund"
   
   ❌ "humdrum of a normal day" → "bâzâitul unei zile normale"
   ✅ USE: "rutina unei zile obișnuite" / "monotonia cotidianului"
   
   ❌ "matriculated through the process" → "s-a înmatriculat prin proces"
   ✅ USE: "a parcurs procesul" (sens figurat)
   
   ❌ "Bible Belt" → "Centura Bibliei"
   ✅ USE: "Centura Bibliei" (cu ghilimele sau explicație implicită: sudul SUA)
   
   ❌ "in-your-face" → "în fața ta"
   ✅ USE: "sfidător" / "agresiv" / "provocator"
   
   ❌ "disabuse others of their beliefs" → "a abuza pe alții de credințele lor"
   ✅ USE: "a le dărâma credințele" / "a-i scoate din rătăcire"
   
   ❌ "winsome character" → "caracter câștigător"
   ✅ USE: "caracter carismatic" / "agreabil" / "plăcut"
   
   ❌ "bashing" → "lovire"
   ✅ USE: "a desființa" / "a ataca agresiv"
   
   ❌ "firebrands" → "mărci de foc"
   ✅ USE: "spirite combative" / "agitatori"
   
   ❌ "gave a pass" → "i-a dat o pasă"
   ✅ USE: "i se treceau cu vederea încălcările" / "i-a tolerat comportamentul"
   
   ❌ "coming out of the closet" → "ieșirea din dulap"
   ✅ USE: "ieșirea din dulap" (metaforă acceptată) / "asumarea identității"
   
   ❌ "baby eaters" → "mâncători de copii"
   ✅ USE: "mâncători de bebeluși" (referință istorică specifică)
   
   ❌ "wasn't holding his breath" → "nu-și ținea respirația"
   ✅ USE: "nu-și făcea iluzii" / "era sceptic"
   
   ❌ "one god further" → "un zeu mai departe"
   ✅ USE: "cu un zeu mai departe" (citat Dawkins/Roberts)
   
   ❌ "in order to mitigate" → "pentru a mitiga"
   ✅ USE: "pentru a atenua" / "pentru a diminua"
   
   ❌ "featured prominently" → "au figurat proeminent"
   ✅ USE: "s-au evidențiat" / "au ocupat un loc central"
   
   ❌ "in the first instance" → "în prima instanță"
   ✅ USE: "în prima instanță" (OK) / "în primul rând"
   
   ❌ "engaging them in argument" → "angajându-i în argument"
   ✅ USE: "antrenarea acestora în dispute" / "provocarea la dezbatere"
   
   ❌ "it is to these cases that we now turn" → "este către aceste cazuri că ne întoarcem"
   ✅ USE: "spre aceste cazuri ne îndreptăm acum atenția"
   
   ❌ "blurted out" → "a bolborosit"
   ✅ USE: "a exclamat instinctiv" / "a zis fără să gândească"
   
   ❌ "bring this point home" → "aduce acest punct acasă"
   ✅ USE: "să subliniez apăsat acest lucru" / "să fac clar acest aspect"
   
   ❌ "blossoming time" → "timp de înflorire"
   ✅ USE: "perioadă de înflorire" / "efervescență"
   
   ❌ "Free Falling" (titlu) → "Cădere liberă"
   ✅ USE: "În cădere liberă" (metaforă a libertății totale)
   
   ❌ "arcane religion" → "religie arcană"
   ✅ USE: "religie arhaică" / "religie obscură" (sistem depășit)
   
   ❌ "pick up a book" → "a ridica o carte"
   ✅ USE: "a descoperit o carte" / "a citit o carte"
   
   ❌ "aflame for this openness" → "în flăcări pentru această deschidere"
   ✅ USE: "înflăcărată de această deschidere" (pasiune)
   
   ❌ "us versus them" → "noi contra lor"
   ✅ USE: "noi versus ei" (mentalitate de grup)
   
   ❌ "loose ends of faith" → "capete libere ale credinței"
   ✅ USE: "nelămuririle credinței" / "aspectele neclare ale credinței"
   
   ❌ "practice run for eternity" → "fugă de practică pentru eternitate"
   ✅ USE: "repetiție generală pentru eternitate" / "etapă de pregătire"
   
   ❌ "God-goggles" → "ochelari-Dumnezeu"
   ✅ USE: "ochelari teologici" / "lentilă religioasă"
   
   ❌ "myopic concerns" → "griji mioape"
   ✅ USE: "perspective înguste" / "preocupări limitate"
   
   ❌ "coming down hard on people" → "căzând greu pe oameni"
   ✅ USE: "a fi necruțător cu cineva" / "a judeca aspru"
   
   ❌ "collective welfare" → "bunătatea colectivă"
   ✅ USE: "bunăstarea colectivă" (termen sociologic)
   
   ❌ "mundane and ordinary peace" → "pace mundană"
   ✅ USE: "o pace obișnuită, firească" ("mundan" = pământesc/banal, nu monden)
   
   ❌ "factually the case" → "faptic cazul"
   ✅ USE: "faptic adevărat" / "ceea ce este faptic adevărat"
   
   ❌ "woefully inadequate" → "trist de inadecvat"
   ✅ USE: "deplorabil de inadecvat" / "total inadecvat"
   
   ❌ "ecclesiastical pronouncements" → "pronunțări ecleziastice"
   ✅ USE: "hotărâri ecleziastice" / "decrete bisericești"
   
   ❌ "self-imposed tutelage" → "tutelă autoimpusă"
   ✅ USE: "minorat autoimpus" (concept Kantian: Unmündigkeit)
   
   ❌ "intellectual coming of age" → "venirea intelectuală a vârstei"
   ✅ USE: "maturizare intelectuală" / "majorat intelectual"
   
   ❌ "guardians of knowledge" → "gardienii cunoașterii"
   ✅ USE: "gardienii cunoașterii" (metaforă OK)
   
   ❌ "determine the truth" → "a determina adevărul"
   ✅ USE: "a stabili adevărul" / "a afla adevărul" (evită "determina" matematic)
   
   ❌ "onus" → "povară"
   ✅ USE: "responsabilitate" / "sarcina morală" (nuanță activă)
   
   ❌ "day-to-day interaction" → "interacțiune zi de zi"
   ✅ USE: "interacțiunile de zi cu zi" / "interacțiunea cotidiană"
   
   ❌ "growing up" → "crescând"
   ✅ USE: "maturizare" / "a te face om mare" (nu doar fizic)
   
   ❌ "step in a positive direction" → "pas într-o direcție pozitivă"
   ✅ USE: "un pas înainte" / "o direcție corectă" (evită clișeele)
   
   ❌ "good person" → "persoană bună"
   ✅ USE: "om de treabă" / "om de onoare" / "om de caracter"
   
   ❌ "foundation for morality" → "fundație pentru moralitate"
   ✅ USE: "fundament solid pentru valori" / "baza moralității"
   
   ❌ "accounted for in terms of" → "socotite în termeni de"
   ✅ USE: "explicate prin prisma" / "interpretate prin"
   
   ❌ "atheist account of reality" → "contul ateu al realității"
   ✅ USE: "perspectiva atee asupra realității"
   
   ❌ "theoretical account" → "cont teoretic"
   ✅ USE: "justificare teoretică" / "explicație teoretică"
   
   ❌ "makeup" (structură) → "machiaj"
   ✅ USE: "structură interioară" / "constituție" / "felul de a fi"
   
   ❌ "beholden to" → "privit la"
   ✅ USE: "față de care este responsabilă" / "îndatorată"
   
   ❌ "cast out" → "aruncat afară"
   ✅ USE: "exclus" (social/comunitar)
   
   ❌ "moral sense" → "simț moral"
   ✅ USE: "simț moral" (termen consacrat: moral sense theory)
   
   ❌ "individual autonomy" → "autonomie individuală"
   ✅ USE: "autonomie individuală" (sens moral, nu juridic)
   
   ❌ "property-thing view" → "viziunea proprietate-lucru"
   ✅ USE: "viziunea atributelor ca proprietate" / "viziunea proprietăților adăugate"
   
   ❌ "substance view" → "viziunea substanței"
   ✅ USE: "viziunea substanțialistă" (termen filozofic consacrat)
   
   ❌ "bodily autonomy" → "autonomie fizică"
   ✅ USE: "autonomie corporală" (termen bioetic)
   
   ❌ "God-ordained" → "ordonat de Dumnezeu"
   ✅ USE: "rânduită de Dumnezeu" (nuanță teologică)
   
   ❌ "criteria for belief" → "criterii pentru credință"
   ✅ USE: "criterii de credință" (standarde de acceptare)
   
   ❌ "groupthink" → "gândire de grup"
   ✅ USE: "gândire de grup" (termen sociologic consacrat)
   
   ❌ "evidence-based" → "bazat pe evidențe"
   ✅ USE: "bazat pe dovezi" / "fundamentat pe dovezi"
   
   ❌ "I'm huge on" → "sunt uriaș pe"
   ✅ USE: "sunt un mare susținător al ideii" / "pun mare preț pe"
   
   ❌ "truth claims" → "reclamații de adevăr"
   ✅ USE: "pretenții de adevăr" (termen tehnic teologic)
   
   ❌ "extraordinary claims require extraordinary evidence" → "reclamații extraordinare..."
   ✅ USE: "afirmațiile extraordinare necesită dovezi extraordinare" (Sagan/Truzzi)
   
   ❌ "back this up" → "sprijină asta din spate"
   ✅ USE: "să susții asta" / "să probezi asta"
   
   ❌ "better off" → "mai bine oprit"
   ✅ USE: "le este mai bine" / "sunt într-o situație mai bună"
   
   ❌ "captors" → "răpitori"
   ✅ USE: "cei care i-au ținut captivi" (nuanță emoțională)
   
   ❌ "secure footing" → "picior sigur"
   ✅ USE: "un teren mai sigur" / "o bază sigură"
   
   ❌ "setting up believers for a loss of faith" → "setând credincioșii pentru..."
   ✅ USE: "a crea premisele pierderii credinței" (pregătire involuntară)
   
   ❌ "solid foundation" → "fundație solidă"
   ✅ USE: "temelie solidă" (termen biblic/bisericesc preferat)
   
   ❌ "in and of itself" → "în și de la sine"
   ✅ USE: "în sine" (evită redundanța)
   
   ❌ "flat as a pancake" → "plat ca o clătită"
   ✅ USE: "s-a prăbușit complet" / "a eșuat lamentabil"
   
   ❌ "questions of ultimate concern" → "întrebări de îngrijorare ultimă"
   ✅ USE: "întrebări fundamentale" / "preocupări ultime" (Tillich)
   
   ❌ "alternative lifestyle" → "stil de viață alternativ"
   ✅ USE: "stil de viață alternativ" (termen consacrat)
   
   ❌ "grounds" (motive) → "pământuri"
   ✅ USE: "temeiuri" / "fundament" (bază logică/legală)
   
   ❌ "sentient" → "simțitor"
   ✅ USE: "conștient" / "înzestrat cu simțire" (nuanță bioetică)
   
   ❌ "built-in community" → "comunitate încorporată"
   ✅ USE: "comunitate de-a gata" / "comunitate implicită"
   
   ❌ "coming out as non-Christian" → "a ieși afară ca necreștin"
   ✅ USE: "asumarea publică a necredinței" / "mărturisirea faptului că nu mai ești creștin"
   
   ❌ "blew their minds" → "le-a aruncat mințile în aer"
   ✅ USE: "i-a lăsat mască" / "i-a uluit" / "i-a șocat profund"
   
   ❌ "drive a wedge" → "a conduce o pană"
   ✅ USE: "a adâncit prăpastia" / "a dezbina"
   
   ❌ "in complete denial" → "în negare completă"
   ✅ USE: "refuză să accepte realitatea" / "stare de negare totală"
   
   ❌ "hospice" → "hospice"
   ✅ USE: "centru de îngrijire paliativă" (mai sobru/literar)




15. TECH & SEMICONDUCTOR (CRITICAL):
   ❌ "wafers" (semiconductor) → "napolitane" (EROARE GRAVĂ!)
   ✅ USE: "wafere" / "plăci de siliciu" (napolitane = biscuiți!)
   
   ❌ "line item" → "element de linie"
   ✅ USE: "linie bugetară" / "cheltuială"
   
   ❌ "burn rate" → "rată de ardere"
   ✅ USE: păstrează "burn rate" / "rata de consum a lichidităților"
   
   ❌ "cap in hand" → "cu șapca în mână"
   ✅ USE: "cu mâna întinsă" / "cerșind sprijin"
   
   ❌ "debacle" → "debacle"
   ✅ USE: "fiasco" / "dezastru" / "eșec răsunător"

16. VENTURE CAPITAL & PRIVATE EQUITY:
   ❌ "angel investors" → "investitori providențiali"
   ✅ USE: "investitori de tip angel" / "business angels"
   
   ❌ "limited partners (LPs)" → "parteneri cu răspundere limitată"
   ✅ USE: "investitori parteneri" / păstrează "LP" (jargon consacrat)
   
   ❌ "spinout/spin-off" → traduceri literale
   ✅ USE: "entitate desprinsă" / "spin-off" (păstrează termenul)
   
   ❌ "The Great House" (Necker Island) → "Marele Cămin"
   ✅ USE: păstrează "The Great House" (nume propriu celebru)

17. HALUCINAȚII AI (ATENȚIE!):
   ❌ "cocktails" → "cockurmăritors" (eroare de procesare)
   ✅ NOTE: Verifică cuvintele care par corupte/inventate

19. ERORI CRITICE DE NUANȚĂ (din feedback real):
   ❌ "scrappy team" → "echipă hapsână" (EROARE MAJORĂ!)
   ✅ USE: "echipă îndrăzneață" / "echipă dârză" / "echipă mică dar bătăioasă"
   (În RO, "hapsână" = lacomă/mâncăcioasă - sens complet diferit!)
   
   ❌ "pitch deck" → "punte de prezentare" (literalism)
   ✅ USE: "prezentarea pentru investitori" / păstrează "pitch deck"
   
   ❌ "works reliably" → "e în regulă în mod fiabil" (eroare de procesare)
   ✅ USE: "funcționează fără greș" / "este o rețetă verificată" / "merge la sigur"
   
   ❌ "if you've been laughed at" → "dacă ați fost râs" (gramatică greșită!)
   ✅ USE: "dacă s-a râs de voi" / "dacă ați fost ținta râsetelor"
   (Construcția pasivă cu "a fi râs" nu există în română!)
   
   ❌ "aesthetic-free digital tulips" → "lalele digitale fără estetică" (forțat)
   ✅ USE: "lalele digitale lipsite de orice valoare estetică"

18. NUANȚE CONTEXTUALE (EVITĂ SEC):
   ❌ "stakeholders" → "părți interesate" (prea sec în context emoțional)
   ✅ USE: "partenerii noștri" / "cei care au crezut în noi" (în context narativ)
   
   ❌ "worn copy" (carte) → "copia mea uzată"
   ✅ USE: "exemplarul meu uzat" (pentru cărți!)
   
   ❌ "any weather" → "orice vreme"
   ✅ USE: "orice intemperii" / "orice condiții" (pentru gravitate în business)
'''

# =============================================================================
# STYLE-SPECIFIC RULES
# =============================================================================

# Literary style - general fiction, neutral tone
style_literary = '''
LITERARY STYLE GUIDELINES:
- Maintain elegant, flowing prose
- Preserve literary devices (metaphors, similes)
- Use standard literary Romanian
- Avoid colloquialisms unless in dialogue
- Keep sentence rhythm natural

DINAMISM NARATIV (pentru scene culminante):
- Evită verbele "seci" în scene de acțiune sau emoție
- Folosește verbe care exprimă mișcare/emoție (ex: "gonind" vs "mergând")
- Sunetele și senzațiile trebuie "purtate" de narator (ex: "vocea lui purtând versurile")
- Evită "a spus" excesiv - variază cu: "șopti", "murmură", "strigă", "oftă"
'''

# Romance style - emotional, sensual
style_romance = '''
ROMANCE STYLE GUIDELINES:
- Emotional, evocative language
- Preserve sensual descriptions with taste
- Use warm, intimate vocabulary
- Dialogue should feel natural and passionate
- Avoid clinical or cold terminology
'''

# Thriller/Action/Spy - tense, punchy
style_thriller = '''
THRILLER/ACTION/SPY STYLE GUIDELINES:
- Short, punchy sentences for tension
- Keep pace fast, economical prose
- Avoid softening violent action
- Weapons/tech: keep brand names (Glock, Beretta, Kalashnikov)

SPIONAJ (TRADECRAFT) - CRITICAL TRANSLATIONS:
  ❌ "asset" → "activ" (contabil!)
  ✅ USE: "sursă" / "agent"
  
  ❌ "handler" → "manipulator" / "handler"
  ✅ USE: "ofițer de legătură" / "coordonator"
  
  ❌ "safe house" → "casă sigură"
  ✅ USE: "casă conspirativă" (termenul tehnic românesc)
  
  ❌ "cover" → "acoperire"
  ✅ USE: "legendă" (povestea falsă)
  
  ❌ "blown cover" → "acoperire suflată"
  ✅ USE: "acoperire compromisă" / "legendă deconspirată"
  
  ❌ "intelligence" → "inteligență"
  ✅ USE: "informații" / "servicii" (context: "serviciile secrete")
  
  ❌ "station chief" → "șeful stației"
  ✅ USE: "rezident" / "șef de antenă"
  
  • "tradecraft" = "meserie de spion" / "tehnici operative"
  • "dead drop" = "cutie poștală moartă"
  • "exfiltration" = "exfiltrare" / "evacuare clandestină"
  • "burn notice" = "ordin de dezavuare"
  • "mole" = "cârtiță"

TACTICĂ MILITARĂ - EXPRESII:
  ❌ "I've got your back" → "am spatele tău"
  ✅ USE: "te acopăr" / "sunt în spatele tău"
  
  ❌ "extraction point" → "punct de extracție"
  ✅ USE: "punct de evacuare" / "punct de recuperare"
  
  ❌ "friendly fire" → "foc prietenos"
  ✅ USE: "foc fratricid"
  
  ❌ "collateral damage" → "daune colaterale"
  ✅ USE: "pierderi civile" / "efecte secundare"
  
  ❌ "engage the target" → "angajează ținta"
  ✅ USE: "atacă ținta" / "deschide focul asupra țintei"
  
  ❌ "negative" / "copy that" → "negativ" / "copiez"
  ✅ USE: "nu" / "recepționat" / "înțeles"
  
  ❌ "secure the area" → "securizează zona"
  ✅ USE: "asigură zona" / "ocupă zona"
  
  • "hold position" = "menține poziția" (NOT "ține poziția")
  • "fall back" = "retrage-te" (NOT "cade înapoi")
  • "go dark" = "întrerupe comunicarea" (NOT "devino întunecat")

PROCEDURĂ POLIȚIENEASCĂ:
  ❌ "you are in custody" → "ești în custodie"
  ✅ USE: "ești în arest" / "ești reținut"
  
  ❌ "crime scene" → "scena crimei"
  ✅ USE: "locul faptei" (termenul juridic corect)
  
  ❌ "cold case" → "caz rece"
  ✅ USE: "dosar cu autor necunoscut (AN)" / "caz nerezolvat"
  
  ❌ "first responder" → "ofițer de prim răspuns"
  ✅ USE: "echipajul sosit primul la fața locului"
  
  ❌ "search warrant" → folosit greșit ("warrant" ca atare)
  ✅ USE: "mandat de percheziție"
  
  • "perp" (perpetrator) = "suspect" / "făptuitor"
  • "DA" (District Attorney) = "procuror"
  • "APB" (All Points Bulletin) = "apel general de căutare"

VERBE "THRILLER" - EVITĂ LITERALISMELE:
  ❌ "a intercepta" (excesiv pentru telefoane)
  ✅ USE: "a asculta" / "a monitoriza"
  
  ❌ "a compromite" (pentru agent deconspiat)
  ✅ USE: "a deconspia" / "a demasca"
  
  ❌ "a neutraliza" (eufemism forțat)
  ✅ USE: "a elimina" / "a omorî" (dacă contextul cere claritate)
  
  ❌ "a depista" (pentru "to track")
  ✅ USE: "a urmări" / "a localiza"

IMPORTANT: Ritmul este totul! Evită orice construcție care scot cititorul din tensiune.
'''

# Historical - period-appropriate
style_historical = '''
HISTORICAL STYLE GUIDELINES:
- Maintain period-appropriate vocabulary
- Avoid modern slang or anachronisms
- Use formal address where appropriate (dumneata, dumneavoastră)
- Historical titles: keep authentic (Lord, Duke, Baron etc. can be adapted)
- Military ranks: use Romanian equivalents when historically accurate
'''

# Sci-Fi/Philosophical - conceptual
style_scifi = '''
SCI-FI / PHILOSOPHICAL STYLE GUIDELINES:
- Technical/scientific terms: translate concept, not word-for-word
- Neologisms: adapt creatively, keep recognizable
- Philosophical concepts: preserve precision
- Made-up terms: transliterate or adapt phonetically
'''

# Business/Economy/Politics - formal, professional
style_business = '''
BUSINESS/ECONOMY/POLITICS STYLE GUIDELINES:
- Formal, professional register
- Keep established English terms in their original form:
  • "startup" = startup (NOT "întreprindere nou-înființată")
  • "CEO" = CEO (or "director general")
  • "marketing" = marketing
  • "management" = management
  • "branding" = branding
  • "pitch" = pitch
  • "networking" = networking
  • "feedback" = feedback

BUSINESS FALSE FRIENDS (AVOID these literal translations):
  ❌ "pipeline" (business) → "conductă" 
  ✅ USE: "flux de lucru" / "lanț de procesare" / "serie de proiecte"
  
  ❌ "leverage" → "pârghie" 
  ✅ USE: "a valorifica" / "a exploata" / "efect de levier" (finance)
  
  ❌ "disrupt" → "a perturba" 
  ✅ USE: "a revoluționa" / "a transforma radical"
  
  ❌ "scalable" → "scalabil" 
  ✅ USE: "scalabil" IS OK in tech/business context
  
  ❌ "stakeholder" → keep as "stakeholder" or "parte interesată"
  
  ❌ "bottom line" → "linia de jos"
  ✅ USE: "rezultat final" / "concluzie" / "esențial"

FINANCE IDIOMS & ECONOMICS:
  ❌ "lose my shirt" → "a pierde cămașa"
  ✅ USE: "a pierde totul" / "a rămâne în pielea goală"
  
  ❌ "animal spirits" (Keynes) → "spiritul animal"
  ✅ USE: "elan instinctiv" / "impulsuri emoționale" (emoțiile care conduc piețele)
  
  ❌ "stabilized is a generous term" → literal
  ✅ USE: "stabilizat e un termen prea blând" / "e exagerat să spui stabilizat"

BUSINESS TERMINOLOGY (ERORI FRECVENTE):
  ❌ "keynote presentation" → "prezentare de bază"
  ✅ USE: "prezentare tematică" / "discurs principal" / "prezentare magistrală"
  ("⎋ de bază" = elementar, nu principal!)
  
  ❌ "bid on the project" → "a licitat proiectul"
  ✅ USE: "a licitat pentru proiect" (participare activă la licitație)
  
  ❌ "finish the listing" → "finisarea listării"
  ✅ USE: "finalizarea listării" (finisare = mobilă/haine!)
  
  ❌ "prohibitively high" → "prohibitiv de mare"
  ✅ USE: doar "prohibitiv" (redundanță eliminată)
  
  ❌ "energy deficits" → "deficite de energie"
  ✅ USE: "penurie de energie" / "criză energetică"

BUSINESS METAPHORS & CONCEPTS:
  ❌ "North Star" → "steaua noastră polară"
  ✅ USE: "reperul nostru principal" / "punctul nostru de referință"
  
  ❌ "schemes" (expansion schemes) → "scheme de extindere" (conotație negativă!)
  ✅ USE: "planuri de expansiune" / "strategii de dezvoltare"
  ("⎋ schemă" în RO = ceva dubios, o simplificare)
  
  ❌ "pipeline" (sales/deals) → "flux de procesare" (sună a fabrică!)
  ✅ USE: "portofoliu de contracte" / "proiecte în curs" / "valoare totală a oportunităților"
  
  ❌ "hard money" → "bani tari"
  ✅ USE: "monedă solidă" / "active sigure" / "valoare stabilă"

BUSINESS JARGON & FINANCE:
  ❌ "escape velocity" → "viteza de evadare"
  ✅ USE: "avânt de neoprit" / "viteza de desprindere" (metaforă business)
  
  ❌ "due diligence" → "verificare prealabilă"
  ✅ NOTE: Păstrează "due diligence" - termenul e consacrat în RO business
  
  ❌ "underwriters" → "subscriitori"
  ✅ USE: "garanți de emisiune" / "bănci care gestionează subscrierea"
  
  ❌ "plastered the city" → "a tencuit orașul"
  ✅ USE: "am împânzit orașul" (cu reclame)
  
  ❌ "investment details" → "investiții detaliu"
  ✅ USE: "detaliile investiției" (genitiv corect)
  
  ❌ "medical-grade" → "grad medical"
  ✅ USE: "la standarde medicale"
  
  ❌ "tentacular empire" → "imperiu tentacular" (conotație sinistră!)
  ✅ USE: "imperiu ramificat" / "conglomerat extins"
  
  ❌ "opportunity to advise with" → "oportunitate de a consilia cu"
  ✅ USE: "oportunitate de a delibera alături de" / "de a se sfătui cu"

FINANCIAL MARKETS TERMINOLOGY:
  ❌ \"bear market\" → \"piață ursară\" / \"piață ursină\"
  ✅ USE: \"piață în scădere\" / \"piață bear\" (jargon acceptat)
  
  ❌ \"bull market\" → \"piață taurină\"
  ✅ USE: \"piață în creștere\" / \"piață bull\" (jargon acceptat)
  
  ❌ \"beauty contest\" (business) → \"concurs de frumusețe\"
  ✅ USE: \"concurs de oferte\" / \"selecție de ofertanți\"
  
  ❌ \"bake-off\" (business) → \"concurs de coacere\"
  ✅ USE: \"concurs de oferte\" / \"competiție între furnizori\"

POKER & GAMING TERMINOLOGY:
  ❌ "call" → "cer" / "ceri"
  ✅ USE: "plătesc" / "plătești" (poker)
  
  ❌ "raise" → "ridic"
  ✅ USE: "cresc miza" / "relansez"
  
  ❌ "fold" → "foldez"
  ✅ USE: "mă retrag" / "renunț"
  
  ❌ "all in" → "all in"
  ✅ USE: "merg la tot" / "risc totul" / păstrează "all-in" dacă contextul e informal

BUSINESS TERMINOLOGY - LITERALISME FRECVENTE (CRITICAL):
  ❌ "known quantity" → "cantitate cunoscută"
  ✅ USE: "o valoare certă" / "un om pe care ne putem baza" / "o figură cunoscută"
  
  ❌ "leading the exercise" → "conducerea exercițiului"
  ✅ USE: "coordonarea procesului" / "gestionarea operațiunii" / "conduce tranzacția"
  
  ❌ "corporate treasuries" → "trezorerii corporative"
  ✅ USE: "rezerve strategice" / "activele de trezorerie ale companiilor"
  
  ❌ "dream team" → "echipa mașina visurilor" / "echipa de vis"
  ✅ USE: "echipa de elită" / "asamblarea echipei de vis" (substantivizat)
  
  ❌ "moat" (competitive moat) → "șanț competitiv"
  ✅ USE: "avantaj competitiv strategic" / "barieră de intrare"
  
  ❌ "blank check company" → literal
  ✅ USE: "companie cu cec în alb" / "vehicul SPAC" (corect pentru IPO)
  
  ❌ "back in the saddle" → "înapoi în șa"
  ✅ USE: "să te întorci în șa" / "a reveni în activitate" (idiom OK)
  
  ❌ "cornerstone investors" → "piatră de temelie"
  ✅ USE: "investitori ancoră" (termenul standard în finanțe)
  
  ❌ "get your foot in the door" → literal
  ✅ USE: "să-ți bagi piciorul în ușă" (adaptare naturală, OK)
  
  ❌ "survivor instincts" → "instincte descurcărețe"
  ✅ USE: "spirit de supraviețuitor" / "instinct de supraviețuire"
  
  ❌ "escape velocity" → "viteză de evadare"
  ✅ USE: "viteză de desprindere" / "avânt de neoprit" (metaforă business)
  
  ❌ "[Project X] taking flight" → "[Proiect X] decolează"
  ✅ USE: "[Proiect X] prinde aripi" (metaforă mai naturală în RO)
  
  ❌ "legal tender" → "tender legal" / "monedă legală"
  ✅ USE: "mijloc legal de plată" (termenul juridic corect în România)
  
  ❌ "bake-off" (syndicate selection) → "concurs de coacere"
  ✅ USE: Evită termenul literal, descrie "selecția sindicatului bancar" / "concurs de oferte"
  
  ❌ "FUD" (Fear, Uncertainty, Doubt)
  ✅ USE: Păstrează "FUD" - acronim intrat în limbajul investitorilor români
  
  ❌ "magic beans" → literal
  ✅ USE: "boabe magice" (referința la Jack și vrejul de fasole e clară)
  
  ❌ "shoot for the moon" → literal
  ✅ USE: "țintește spre Lună" (adaptare standard a proverbului)
  
  ❌ "impact players" → "jucători de impact" / "persoane cu impact"
  ✅ USE: "oameni de impact" (mai natural în română)
  
  ❌ "out-of-the-box thinking" → "gândire în afara cutiei"
  ✅ USE: "gândire neconvențională" / "dincolo de tipare"
  
  ❌ "spin-off" → păstrează ca atare SAU
  ✅ USE: "separare" / "desprindere în entitate independentă"
  
  ❌ "reality check" → "verificarea realității"
  ✅ USE: "verificare a realității" / "evaluare lucidă"
  
  ❌ "outstanding bonus" → "bonus restant"
  ✅ USE: "bonus pentru realizări remarcabile" (outstanding = excepțional, nu restant!)
  
  ❌ "hardest money" (Bitcoin) → "cei mai greu de obținut bani"
  ✅ USE: "formă solidă de bani" / contextul filosofic al valorii Bitcoin
  
  ❌ "compound" (compound value/interest) → "a compune"
  ✅ USE: "dezvoltare exponențială" / "acumularea valorii" / "efect compus"
  
  ❌ "behemoth" → "behemot"
  ✅ USE: "gigant" / "colos" (termenul românesc familiar)
  
  ❌ "can-do attitude" → literal
  ✅ USE: "atitudine de tip «Se poate»" / "mentalitate proactivă"
'''

# Technical/Crypto - specialized terminology
style_technical_crypto = '''
TECHNICAL / CRYPTO STYLE GUIDELINES:
- This is SPECIALIZED FINANCIAL/TECH content
- Keep ALL crypto/blockchain terms in English:
  • "White Paper" = White Paper (NEVER "Cartea Albă")
  • "blockchain" = blockchain
  • "Bitcoin", "Ethereum" = as-is
  • "token" = token
  • "smart contract" = smart contract
  • "DeFi" = DeFi
  • "NFT" = NFT
  • "wallet" = portofel digital / wallet
  • "mining" = mining / minerit
  • "staking" = staking
  • "yield" = randament / yield
  • "liquidity pool" = pool de lichidități
  • "gas fees" = taxe de gas / gas fees

TECH FALSE FRIENDS (CRITICAL):
  ❌ "White Paper" → "Cartea Albă" (means government policy doc)
  ✅ KEEP: "White Paper" (crypto/tech document)
  
  ❌ "pipeline" (tech) → "conductă"
  ✅ USE: "flux de procesare" / "pipeline" (for CI/CD)
  
  ❌ "fork" → "furculiță"
  ✅ USE: "fork" (blockchain) / "ramificație" (general)
  
  ❌ "bridge" (crypto) → "pod"
  ✅ USE: "bridge" / "punte cross-chain"

CRYPTO SLANG & EXPRESSIONS:
  ❌ "shitcoin" → "rahat de monedă" (literal vulgar)
  ✅ USE: "monedă de duzină" / "monedă fără valoare" / păstrează argoul dacă tonul e foarte informal
  
  ❌ "boiling the oceans" → "fierbea oceanele"
  ✅ USE: "consum apocaliptic de energie" / "efort titanic de procesare"
  
  ❌ "HODL" → păstrează "HODL" (e un meme, nu un cuvânt)
  ✅ NOTE: Explică prima dată: "HODL (hold on for dear life)"
  
  ❌ "to the moon" → "până la lună"
  ✅ USE: "va exploda" / "crește exponențial" / păstrează "to the moon" în context informal
  
  ❌ "whale" → "balenă"
  ✅ USE: "jucător major" / "investitor masiv" / "balenă" (acceptabil în context crypto)
  
  ❌ "rug pull" → literal
  ✅ USE: "țeapă" / "escrocherie" / "rug pull" (păstrează termenul consacrat)
'''

# Self-Help/Personal Development
style_self_help = '''
SELF-HELP / PERSONAL DEVELOPMENT STYLE GUIDELINES:
- Warm, encouraging tone
- Direct address to reader ("tu", not formal "dumneavoastră")
- Motivational, active language
- Keep popular psychology terms recognizable:
  • "mindset" = mentalitate / mindset
  • "growth mindset" = mentalitate de creștere
  • "coaching" = coaching
  • "burnout" = burnout / epuizare profesională
  • "resilience" = reziliență
  • "empowerment" = împuternicire / empowerment
  • "boundaries" = limite (personale)
  • "self-care" = îngrijire de sine / self-care
'''

# Philosophy/Theology - precision required
style_philosophy_theology = '''
PHILOSOPHY / THEOLOGY STYLE GUIDELINES:
- PRECISION is paramount - terms carry ontological weight
- Respect Romanian philosophical tradition (Blaga, Noica, Stăniloae)
- Use established academic/patristic vocabulary

ANGLICISME ȘI LITERALISME (FEEDBACK REAL):
  ❌ "leaving the faith" → "ieșirea din credință"
  ✅ USE: "părăsirea credinței" / "abandonarea credinței"
  ("ieșirea" = termen spațial/fizic, inadecvat teologic)
  
  ❌ "accounts of deconversion" → "prezentări ale faptelor despre deconvertire"
  ✅ USE: "mărturii de deconvertire" / "relatări ale deconvertirii"
  
  ❌ "a problem in particular" → "o problemă în special"
  ✅ USE: "o problemă anume" / "o chestiune specială"
  
  ❌ "reading hundreds of accounts" → "citiri a sute de relatări"
  ✅ USE: "parcurgerea a sute de mărturii" / "studierea a sute de relatări"
  ("citire" = act mecanic, ca citirea contorului)
  
  ❌ "as Christians" → "ca creștini" (CACOFONIE!)
  ✅ USE: "drept creștini" / "în calitate de creștini"
  
  ❌ "unbelievers of one sort or another" → "necredincioși de un fel sau altul"
  ✅ USE: "diverse forme de necredință" / "diferite tipuri de necredință"
  
  ❌ "theologically informed Christians" → "creștini informați teologic"
  ✅ USE: "creștini cu pregătire teologică" / "creștini cu formație teologică"

GREȘELI GRAMATICALE (GENITIV/DATIV):
  ❌ "perspectivă asupra deconvertire"
  ✅ USE: "perspectivă asupra deconvertirii" (genitiv corect!)
  
  ❌ "procesul de deconvertirea"
  ✅ USE: "procesul de deconvertire" (fără articol!)
  
  ❌ "circumstanțele care au servit drept context al pierderii"
  ✅ USE: "circumstanțele care au constituit contextul părăsirii credinței"
  (mai fluid, evită "servit drept")
  
  ❌ "interviurile personal"
  ✅ USE: "interviurile personale" / "interviurile realizate personal"
  (adjectivul se acordă cu substantivul!)
  
  ❌ "mărturiile online deconvertire"
  ✅ USE: "mărturiile de deconvertire de pe internet"
  (prepoziții de legătură necesare!)
  
  ❌ "deconvertire foști creștini"
  ✅ USE: "deconvertirea foștilor creștini"
  (lipsește articolul și prepoziția de legătură!)
  
  ❌ "neafiliații religios" (The Nones)
  ✅ USE: "neafiliații religioși" (acord la plural!)
  
  ❌ "leaving the faith" → "ieșirea din credință"
  ✅ USE: "părăsirea credinței" / "abandonarea credinței"
  ("ieșirea" = termen spațial, inadecvat teologic)
  
  ❌ "to undergo deconversion" → "fac deconvertire"
  ✅ USE: "se deconvertesc" / "trec printr-un proces de deconvertire"
  (în RO nu "facem" deconvertire!)
  
  ❌ "ominously titled" → "titulată prevestitor"
  ✅ USE: "intitulat în mod prevestitor"
  
  ❌ "their identity" (pt. "promoția 2018") → "identitatea lor"
  ✅ USE: "identitatea ei" (promoția = feminin singular!)

VERBE ȘI EXPRESII TEOLOGICE (EVITĂ LITERALISME):
  ❌ "underlies" → "subîntinde" (geometric/logic)
  ✅ USE: "stă la baza" / "fundamentează" / "se află în spatele"
  
  ❌ "what they deconverted from" → "ceea ce au deconvertit"
  ✅ USE: "de la care s-au deconvertit" / "sistemul de credințe la care au renunțat"
  ("a deconverti" = intranzitiv/reflexiv, nu poți "deconverti un obiect")
  
  ❌ "faith journey" → "călătoria credinței"
  ✅ USE: "parcursul spiritual" / "drumul credinței"
  
  ❌ "spiritual growth" → "creșterea spirituală"
  ✅ USE: "creștere duhovnicească" / "progres spiritual"
  
  ❌ "faith community" → "comunitatea credinței"
  ✅ USE: "comunitatea de credință" / "comunitatea credincioșilor"
  
  ❌ "spiritual fruit" → "fruct spiritual"
  ✅ USE: "rod spiritual" (termen consacrat biblic)

EXPRESII RELIGIOASE SPECIFICE:
  ❌ "burning for God" → "ardeam pentru Dumnezeu"
  ✅ USE: "ardeam de râvnă pentru Dumnezeu" / "eram plin de fervoare"
  
  ❌ "witnessing" → "mărturisea tuturor"
  ✅ USE: "evangheliza" / "depunea mărturie" / "vestea Evanghelia"
  (în RO, "a mărturisi" singur = spovedanie ortodoxă sau recunoașterea vinei)
  
  ❌ "Master of Divinity" → "Master în divinitate"
  ✅ USE: "Master în teologie (M.Div.)"
  
TERMINOLOGIE TEOLOGICĂ RAFINATĂ:
  ❌ "religious transition" → "tranziție religioasă"
  ✅ USE: "tranziție spirituală" / "schimbare de paradigmă religioasă"
  
  ❌ "found wanting" → "constatat că este deficitară"
  ✅ USE: "găsită insuficientă" / "găsită precară"
  
  ❌ "comprehensive set of doctrines" → "set cuprinzător de doctrine"
  ✅ USE: "sistem doctrinar coerent" / "sistem doctrinar articulat"
  
  ❌ "act of will" → "act de voință"
  ✅ USE: "act deliberat de voință" / "decizie conștientă"
  
  ❌ "profound loss" → "pierdere profundă"
  ✅ USE: "sentiment de pierdere acută" / "pierdere dureroasă"

CACOFONII DE EVITAT (TEOLOGIE):
  ❌ "ca creștin" → cacofonie!
  ✅ USE: "drept creștin" / "în calitate de creștin" / "în perioada creștină"
  
  ❌ "biserica ca instituție" → cacofonie!
  ✅ USE: "biserica privită ca instituție" / "biserica în calitate de instituție"

CULTURĂ EVANGHELICĂ (SPECIFIC RO):
  ❌ "Purity Culture" → "Cultura curățeniei"
  ✅ USE: "Cultura purității" (termenul consacrat în mediul evanghelic)
  ("curățenie" = igienă fizică, nu virtute morală)
  
  ❌ "I Kissed Dating Goodbye" → "Mi-am luat Adio de la Sărutul"
  ✅ USE: "Adio, întâlniri amoroase!" / "Am spus adio întâlnirilor"
  (cartea e despre renunțarea la dating, nu despre un sărut)
  
  ❌ "advocate" (în context moral) → "avocat"
  ✅ USE: "promotor" / "susținător" / "apologet"
  ("avocat" = sala de judecată, nu promovare morală)
  
  ❌ "pronouncing that..." → "pronunțând că..."
  ✅ USE: "declarând că..." / "anunțând public că..."
  (anglicism - în RO nu "pronunțăm" declarații)
  
  ❌ "stormed the stage" → "a năvălit pe scenă"
  ✅ USE: "a luat cu asalt scena" / "a apărut spectaculos pe scenă"
  
  ❌ "home group" → "grup de casă"
  ✅ USE: "grup de părtășie" / "grup mic" / "celulă" (termen consacrat)
  
  ❌ "I was on fire" → "eram în flăcări"
  ✅ USE: "eram plin de râvnă" / "eram pasionat pentru Dumnezeu"
  
  ❌ "won a friend for Christ" → "câștigat un prieten de partea lui Hristos"
  ✅ USE: "a condus un prieten la Hristos" (nu competiție sportivă!)
  
  ❌ "sound theological reflection" → "reflecție teologică sănătoasă"
  ✅ USE: "reflecție teologică solidă" / "reflecție teologică riguroasă"

RAFINAMENTE TEOLOGICE/ACADEMICE:
  ❌ "views" (în teologie) → "opinii"
  ✅ USE: "perspective" / "convingeri" / "poziții doctrinare"
  ("opinii" = prea subiectiv pentru un tratat)
  
  ❌ "variation of the same theme" → "variație a aceleiași teme"
  ✅ USE: "variațiuni pe aceeași temă"
  
  ❌ "the means by which" → "mijlocul prin care a făcut"
  ✅ USE: "calea prin care a realizat" / "modalitatea prin care"
  
  ❌ "Already but not yet" → "nu a sosit încă pe deplin"
  ✅ USE: "inaugurată, dar încă neîmplinită" (termenul academic)
  
  ❌ "exclusion from" → "excluderea noastră de la"
  ✅ USE: "excluderea noastră din" (din tot ceea ce...)
  
  ❌ "repentant loyalty/allegiance" → context-dependent
  ✅ NOTE: "loialitate" = supunere față de suveran
           "fidelitate" = devotament constant
           Alege în funcție de context teologic

  ❌ "because of Jesus" → "datorită lui Isus"
  ✅ USE: "prin Isus" / "datorită lucrării lui Isus"
  ("datorită" singur = prea cauzal-mecanic în teologie)
  
  ❌ "rule and reign of God" → "regula și domnia lui Dumnezeu"
  ✅ USE: "autoritatea și domnia lui Dumnezeu" / "cârmuirea lui Dumnezeu"
  ("regulă" = instrucțiune scrisă, ca regulă de gramatică!)
  
  ❌ "defected" (from institution) → "a defectat"
  ✅ USE: "s-a desprins" / "s-a disociat" / "a părăsit"
  
  ❌ "self-deception" → "auto-amăgire"
  ✅ USE: "autoînșelare" / "autodecepție" / "amăgire de sine"
  
  ❌ "180 degree turn" → "o întoarcere de 180 de grade"
  ✅ USE: "a face cale întoarsă" (expresia românească)
  
  ❌ "deconvertirei" / "deconvertiree" (greșeli ortografice)
  ✅ USE: "deconvertirii" (genitiv corect!)

TERMENI TEOLOGICI VERIFICAȚI:
  ❌ "Biblical followers" → "adepții lui Isus"
  ✅ USE: "urmașii lui Isus" / "ucenicii"
  
  ❌ "Eternal Security" → "siguranța eternă"
  ✅ USE: "siguranța veșnică a mântuirii" / "perseverența sfinților"
  
  ❌ "unregenerate" → "neregenerat"
  ✅ USE: "neregenerat" / "nenăscut din nou" (ambele acceptate)
  
  ❌ "Check. Check. Check." → "Verificat."
  ✅ USE: "Confirmat." / "Bifat." (stilistic mai potrivit)
  
  ❌ "about-turn" → "întoarcere"
  ✅ USE: "cale întoarsă" / "schimbare radicală de direcție"

EXPRESII TEOLOGICE RAFINATE:
  ❌ "strains credulity" → "forțează credulitatea"
  ✅ USE: "este greu de crezut" / "sfidează logica" / "pare greu de acceptat"
  
  ❌ "mental assent to propositional claims" → "asentiment mental față de afirmații propoziționale"
  ✅ USE: "un simplu acord intelectual cu afirmațiile doctrinare"
  (varianta originală e prea greoaie)
  
  ❌ "center and circumference" → "centrul și circumferința"
  ✅ USE: "centrul și esența vieții sale" / "centrul și orizontul vieții sale"
  (păstrează metafora, dar adaptat la RO)
  
  ❌ "account" (mărturie) → "prezentarea faptelor"
  ✅ USE: "relatare" / "mărturie" / "povestire personală"
  
  ❌ "faithfully opportunistic" → "oportuniste cu credincioșie"
  ✅ USE: "un pragmatism plin de credincioșie" / "valorificarea oricărei oportunități în mod fidel"
  ("oportunist" în RO = conotație negativă!)
  
  ❌ "misdirected treatment" → "tratament greșit orientat"
  ✅ USE: "tratament direcționat greșit" / "tratament eronat"

CITATE BIBLICE (IMPORTANT!):
  ✅ NOTE: Folosește traducerea Cornilescu (referința pentru publicul evanghelic RO)
  ✅ NOTE: Verifică citatele cu textul Cornilescu pentru autoritate sporită
  ✅ NOTE: Termenii reformați (alegere necondiționată, har irezistibil) = piloni doctrinari, păstrează exact

TEOLOGIE - TERMENI SPECIFICI TRADIȚIEI:
  ❌ "ministry" → "minister" / "ministeriu"
  ✅ USE: "slujire" / "lucrare" (context: "lucrarea cu tineret")
  
  ❌ "fellowship" → "feloșip" / "parteneriat"
  ✅ USE: "părtășie" (termen superb, adesea uitat!)
  
  ❌ "worship" → "worșip"
  ✅ USE: "închinare" / "adorație" / "laudă" (context: "echipa de laudă")
  
  ❌ "evangelism" → "evanghelism" (când e acțiune)
  ✅ USE: "evanghelizare" (doctrina = evanghelism; acțiunea = evanghelizare)
  
  ❌ "faith-based" → "bazat pe credință"
  ✅ USE: "confesional" / "religios"
  
  ❌ "scriptural" → "scriptural" (sună forțat)
  ✅ USE: "biblic" / "potrivit Scripturii"
  
  ❌ "parachurch ministries" → "ministere paraclise"
  ✅ USE: "organizații para-bisericești" / "misiuni creștine extra-bisericești"
  
  ❌ "cabin leader" (tabere) → "lider de cabină"
  ✅ USE: "lider de grup" / "supraveghetor" / "instructor"
  
  ❌ "elders" (of the church) → "bătrânii bisericii"
  ✅ USE: "prezbiteri" (termenul oficial în confesiunile evanghelice RO)
  
  ❌ "their ministries" → "ministerele lor"
  ✅ USE: "lucrările lor" / "slujirile lor" / "misiunile lor"
  ("minister" RO = instituție a statului!)
  
  • "born again" = "născut din nou" (corect, dar evită clișeul)
  • "grace" = "har" (NOT "grație")
  • "salvation" = "mântuire"
  • "redemption" = "răscumpărare" / "izbăvire"
  • "Trinity" = "Sfânta Treime"
  • "incarnation" = "întrupare"
  • "theosis/deification" = "îndumnezeire"
  • "Eucharist" = "Euharistie" / "Sfânta Împărtășanie"
  • "Original Sin" = "păcatul originar" / "păcatul strămoșesc"
  • "eschatology" = "escatologie"

ERORI GRAMATICALE ȘI TERMINOLOGICE:
  ❌ "Biblia ei înșiși"
  ✅ USE: "Biblia însăși" (acord corect!)
  
  ❌ "higher criticism" → "critica superioară"
  ✅ USE: "critica înaltă" (termenul academic RO)
  
  ❌ "mental gymnastics" → "acrobații mintale"
  ✅ USE: "gimnastică mentală" (sună mai natural)
  
  ❌ "student teacher" → "profesor student"
  ✅ USE: "profesor stagiar" / "student practicant"
  
  ❌ "evangelical Darwinists" → "darwiniști evanghelici"
  ✅ USE: "darwiniști fervenți" / "darwiniști prozelitiști"
  (ATENȚIE: nu confunda cu creștini evanghelici evoluționiști!)

TITLURI DE CĂRȚI TRADUSE OFICIAL:
  ❌ "The God Delusion" → "Iluzia lui Dumnezeu"
  ✅ USE: "Himera credinței" (titlul oficial în RO - Richard Dawkins)
  
  ❌ "On Death and Dying" → "Despre moarte și a muri"
  ✅ USE: "Despre moarte și procesul de a muri" (titlul RO - Kübler-Ross)
  
  ❌ "apologetics ministries" → "ministere apologetice"
  ✅ USE: "misiuni apologetice" / "organizații de apologetică"

EXPRESII IDENTITARE ȘI SOCIALE:
  ❌ "coming out as an atheist" → "a ieși în public ca ateu"
  ✅ USE: "afirmarea publică a ateismului" / "asumarea publică a identității de ateu"
  
  ❌ "weak social ties/attachment" → "atașare socială slabă"
  ✅ USE: "legături sociale slabe" (termenul sociologic)
  
  ❌ "unfriending on Facebook" → "neprietenire pe Facebook"
  ✅ USE: "ștergerea din lista de prieteni de pe Facebook"
  
  ❌ "aptheist" → "apteist"
  ✅ USE: "apteist" (un ateu apatic - păstrează termenul cu explicație)

ERORI DE PLURAL/ORTOGRAFIE:
  ❌ "deconvertireale" / "deconvertire deconvertire"
  ✅ USE: "deconvertirile" (plural corect!)
  
  ❌ "following/entailing" → "urmăritoră" (eroare AI)
  ✅ USE: "care implică" / "urmată de"
  
  ❌ "Noii Ateii" (greșeală)
  ✅ USE: "Noii atei" (un singur "i" la plural; articulat = "ateii")
  
  ❌ "Deconvertire-ul procesului" / "Deconvertire-ei"
  ✅ USE: "procesul deconvertirii" / "modelul deconvertirii"
  (GENITIV: deconvertire → deconvertirii)

TERMINOLOGIE TEOLOGICĂ PRECISĂ:
  ❌ "exclusive claims" → "pretențiile exclusive"
  ✅ USE: "pretențiile de exclusivitate" (o singură religie adevărată)
  
  ❌ "to liberalize a bit" → "să se liberalizeze puțin"
  ✅ USE: "să adopte o viziune mai liberală" / "să își flexibilizeze convingerile"
  
  ❌ "mental assent" → "asentiment mental"
  ✅ USE: "acord intelectual" / "asentiment intelectual"
  
  ❌ "situating ourselves" → "situarea noastră"
  ✅ USE: "poziționarea noastră" / "ancorarea noastră în lume"

NUANȚE FILOSOFICE (ATEISM/AGNOSTICISM):
  ✅ NOTE: "ateu agnostic" = nuanță importantă:
     - agnosticism = cunoaștere ("nu pot ști")
     - ateism = credință ("nu sunt convins")
  ✅ Păstrează distincția când traduci gânditori secularzi

ERORI DE DECLINARE (EXEMPLE):
  ❌ "procesului de deconvertire al deconvertirea"
  ✅ USE: "procesului de deconvertire" / "procesului deconvertirii"
  
  ❌ "Procesul al procesului deconvertirea" (eroare de structură)
  ✅ USE: "procesul deconvertirii"
  
  ❌ "tentatively" → "cu titlu experimental"
  ✅ USE: "cu titlu ipotetic" / "cu titlu provizoriu" (context academic)
  
  ❌ "followers of Jesus" → "adepți ai lui Isus"
  ✅ USE: "urmași ai lui Isus" / "ucenici" (termenul consacrat creștin)
  
  ❌ "difficult matter" → "chestiune dificilă"
  ✅ USE: "proces sinuos" / "fenomen complex" / "problemă delicată"

PSIHOLOGIE ȘI ȘTIINȚE SOCIALE:
  ❌ "confirmation bias" → "părtinirea de confirmare"
  ✅ USE: "prejudecata de confirmare" (termenul consacrat în psihologie RO)
  
  ❌ "cannot make themselves believe" → "nu se mai pot face să creadă"
  ✅ USE: "nu mai reușesc să se convingă" / "nu mai pot adera la o viziune"
  
  ❌ "the process that leads to deconversion" (repetiție)
  ✅ USE: "traiectoria care duce spre deconvertire" (evită repetarea "proces")

ERORI DE CONSTRUCȚIE (ANACOLUT):
  ❌ "Pentru alții, sunt afectați de..."
  ✅ USE: "În cazul altora, e vorba despre..." / "Alții sunt afectați de..."
  (subiectul trebuie să se potrivească cu predicatul!)

FILOZOFIE - TRADIȚIE ROMÂNEASCĂ:
  ❌ "Mind-Body problem" → "Problema Minte-Corp"
  ✅ USE: "Problema raportului dintre spirit și trup" / "Problema spirit-trup"
  (Tradiția românească folosește "spirit", nu "minte" - vezi Blaga, Noica)
  
  ❌ "mind" → "minte" (în context filozofic)
  ✅ USE: "spirit" / "intelect" / "conștiință" (context-dependent)
  
  ❌ "accountability" → "contabilitate morală"
  ✅ USE: "responsabilitate" / "răspundere"
  
  ❌ "entitlement" → "îndreptățire"
  ✅ USE: "drept" / "pretenție legitimă" / "sentiment de drept"
  
  ❌ "bias" → "bias"
  ✅ USE: "prejudecată" / "partinitate" / "subiectivitate"
  
  ❌ "evidence-based" → "bazat pe dovezi"
  ✅ USE: "fundamentat pe probe" / "bazat pe fapte"
  
  ❌ "common sense" → "simț comun"
  ✅ USE: "bun-simț" / "simț practic" (în sens cartezian)
  
  • "Being" = "Ființă" (filozofic) vs "a fi" (verb)
  • "Dasein" = păstrează "Dasein" (Heidegger) sau "ființă-întru-lume"
  • "logos" = "logos" / "rațiune" / "cuvânt" (context-dependent)
  • "transcendence" = "transcendență"
  • "immanence" = "imanență"
  • "ontology" = "ontologie"
  • "epistemology" = "epistemologie"
  • "phenomenology" = "fenomenologie"

FALSE FRIENDS FILOZOFICI (CRITICAL - schimbă sensul logic):
  ❌ "a asuma" (când e "to assume")
  ✅ USE: "a presupune" / "a presupune că"
  (În RO, "a asuma" = a-și lua răspunderea, nu a presupune)
  
  ❌ "argument" (când e dispută în EN)
  ✅ USE: "dispută" / "ceartă" / "polemică"
  ("Argument" RO = dovadă logică, nu ceartă)
  
  ❌ "provocare" (pentru orice dificultate)
  ✅ USE: "dificultate" / "problemă" / "obstacol" / "încercare"
  
  ❌ "viziune" (pentru "părere" sau "proiect")
  ✅ USE: "perspectivă" / "concepție" (viziune = doar revelații/proiecte mari)
  
  ❌ "ultimativ" / "realitate ultimă"
  ✅ USE: "suprem" / "fundamental" / "ultim" / "realitate supremă"
  
  ❌ "expertiză teologică"
  ✅ USE: "competență teologică" (expertiza RO = raportul expertului)

- Keep Greek/Latin terms when standard (agape, kenosis, ousia, hypostasis)
- Maintain formal, academic register
- Preserve argumentative structure precisely

IMPORTANT: În teologie/filozofie, un literalism schimbă sensul ontologic. "Mind" vs "Spirit" nu sunt sinonime - e o alegere metafizică.
'''


# Editing/Refinement mode
style_editing = '''
EDITING MODE GUIDELINES:
- Focus on refining existing translation
- Fix grammatical errors
- Improve naturalness and flow
- Preserve original meaning exactly
- Harmonize style across paragraphs
'''

# =============================================================================
# STYLE DICTIONARY - Maps style names to their rules
# =============================================================================

STYLE_RULES = {
    'literary': style_literary,
    'romance': style_romance,
    'thriller': style_thriller,
    'historical': style_historical,
    'scifi_philosophical': style_scifi,
    'business': style_business,
    'technical': style_technical_crypto,  # Includes crypto
    'self_help': style_self_help,
    'philosophy_theology': style_philosophy_theology,
    'editing': style_editing,
}

def get_romanian_rules(style='literary'):
    """Get combined rules: base + style-specific"""
    style_key = style.lower().replace(' ', '_').replace('/', '_')
    style_specific = STYLE_RULES.get(style_key, style_literary)
    return romanian_base_rules + '\n' + style_specific

def get_dynamic_rules(language='Romanian', source_lang=None, target_lang=None):
    """Get rules dynamically based on current_translation_style in config.
    
    Args:
        language: Target language name (for backward compatibility)
        source_lang: Source language for <slang> replacement
        target_lang: Target language for <tlang> replacement (defaults to 'language' param)
    """
    try:
        from ..core.config import get_config
        config = get_config()
        
        # Get current style from config (set in Advanced Mode)
        current_style = config.get('current_translation_style', 'literary')
        print(f"[STYLE DEBUG] get_dynamic_rules called - current_translation_style: '{current_style}'")
        
        # Determine source and target languages
        if target_lang is None:
            target_lang = language
        if source_lang is None:
            source_lang = 'the source language'
        
        # Build the prompt with master_prompt at the beginning
        prompt_parts = []
        
        # Add master_prompt with language substitution
        localized_master = master_prompt.replace('<slang>', source_lang).replace('<tlang>', target_lang)
        prompt_parts.append(localized_master)
        
        # CRITICAL: Only apply Romanian-specific rules if target language is Romanian
        # For other languages, use only the generic master_prompt
        is_romanian_target = target_lang.lower() in ('romanian', 'română', 'ro')
        print(f"[STYLE DEBUG] Target language: '{target_lang}', is_romanian_target: {is_romanian_target}")
        
        if is_romanian_target:
            # Check for new structured style data
            prefs = config.get('engine_preferences') or {}
            style_data_map = prefs.get('style_data', {})
            
            if current_style in style_data_map:
                print(f"[STYLE DEBUG] Found structured style data for '{current_style}'")
                data = style_data_map[current_style]
                custom_prompt = data.get('prompt', '').strip()
                few_shots = data.get('few_shots', [])
                glossary = data.get('glossary', '').strip()
                
                prompt_parts.append(romanian_base_rules)
                
                if custom_prompt:
                    prompt_parts.append(custom_prompt)
                else:
                    # If prompt is empty but other data exists, use default rules as base
                    prompt_parts.append(get_romanian_rules(current_style))
                
                if few_shots:
                    prompt_parts.append("\n=== FEW-SHOT EXAMPLES (FEW-SHOT LEARNING) ===")
                    prompt_parts.append("The following are examples of how you should translate similar segments. Follow the style and tone shown in these examples exactly:")
                    for fs in few_shots:
                        prompt_parts.append(f"\nOriginal: {fs.get('original')}")
                        prompt_parts.append(f"Translation: {fs.get('translation')}")
                
                if glossary:
                    prompt_parts.append("\n=== STYLE-SPECIFIC GLOSSARY (CONSISTENCY) ===")
                    prompt_parts.append("Use the following fixed translations for terms in this specific genre (format: Term=Translation):")
                    prompt_parts.append(glossary)
            else:
                # Fallback to old style_prompts key (backward compatibility)
                style_prompts = prefs.get('style_prompts', {}) or config.get('style_prompts', {})
                print(f"[STYLE DEBUG] Checking for legacy style prompt for '{current_style}'")
                
                if current_style in style_prompts and style_prompts[current_style].strip():
                    prompt_parts.append(romanian_base_rules)
                    prompt_parts.append(style_prompts[current_style])
                else:
                    prompt_parts.append(get_romanian_rules(current_style))
        else:
            print(f"[STYLE DEBUG] Non-Romanian target, using only master_prompt (no style-specific rules)")
        # For non-Romanian targets, only the master_prompt is used (already added above)
        
        return '\n'.join(prompt_parts)
    except Exception:
        # Fallback to literary if config not available
        return master_prompt + get_romanian_rules('literary')

# Default rules (for backward compatibility)
romanian_style_rules = get_romanian_rules('literary')

# =============================================================================
# ENGINE EXTENSIONS - Dynamic loading via custom dict class
# =============================================================================

class _DynamicExtensionDict(dict):
    """Dict that dynamically loads rules when accessed for any language"""
    def __getitem__(self, key):
        # Always return dynamic rules for any language
        # get_dynamic_rules now handles both Romanian and non-Romanian targets
        return get_dynamic_rules(key, target_lang=key)
    
    def get(self, key, default=None):
        # Always return dynamic rules for any language
        return get_dynamic_rules(key, target_lang=key)

# Extensions for Gemini/Google - lazy loading
gemini = _DynamicExtensionDict()

# Extensions for OpenAI/ChatGPT - lazy loading
openai = _DynamicExtensionDict()

# Extensions for Claude/Anthropic - need special handling
class _DynamicAnthropicDict(dict):
    """Special dict for anthropic that was initialized earlier"""
    def __init__(self, base_dict):
        super().__init__(base_dict)
    
    def __getitem__(self, key):
        # Always return dynamic rules for any language
        return get_dynamic_rules(key, target_lang=key)
    
    def get(self, key, default=None):
        # Always return dynamic rules for any language
        return get_dynamic_rules(key, target_lang=key)

anthropic = _DynamicAnthropicDict(anthropic)


