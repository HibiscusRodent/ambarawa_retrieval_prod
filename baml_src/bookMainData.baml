class BookTitle {
    title_in_origin_script string @description(#"
        The title of the book in its original script. Aims for accuracy in the spelling, diacritics, and the use of special characters. If the title is in a non-Latin script (e.g., Chinese, Arabic, Cyrillic), please provide the title in that script as is.
    "#)
    title_in_latin_script string @description(#"
        The title of the book transliterated into the Latin script. This is especially important for titles originally in non-Latin scripts (e.g., Chinese, Arabic, Cyrillic). Do not translate the title; instead, provide a phonetic representation using Latin characters. Make sure that you transliterate special characters and diacritics, so that the final title is ASCII-safe string.
    "#)
    title_in_indonesian string @description(#"
        The title of the book translated into Indonesian. If the book is originally in Indonesian, please input the title as is.
    "#)
}

class BookAuthor {
    author_in_origin_script string @description("Author name in original script/language")
    author_in_latin_script string @description(#"
    Author name transliterated into Latin script. Make sure that you transliterate special characters and diacritics, so that the final title is ASCII-safe string. In the case that the author name is already in Latin script, please input the name as is.
    "#)
}

class BookTranslator {
    translators_in_origin_script string @description("The translator name in original script/language")
    translators_in_latin_script string @description(#"
    Translator name transliterated into Latin script. Make sure that you transliterate special characters and diacritics, so that the final title is ASCII-safe string. In the case that the translator name is already in Latin script, please input the name as is.
    "#)
}

class TextExtractionEvidence {
    imageNumber int @description("The index number of the image this evidence comes from")
    location string @description("Where on the page this text was found (e.g., 'front cover - top', 'spine', 'back cover - bottom', 'colophon page - center')")
    extractedText string @description("The exact text as it appears, in its original script")
    textType string @description("What this text likely represents (e.g., 'title', 'author name', 'publisher', 'ISBN', 'publication year', 'translator', 'edition info')")
    scriptIdentified string @description("The script system used (e.g., 'Latin', 'Cyrillic', 'Arabic', 'Chinese', 'Japanese', 'Korean', 'Devanagari')")
    confidence string @description("Your confidence in this extraction: 'high', 'medium', or 'low'")
}

class DataComparison {
    fieldName string @description("The bibliographic field being compared (e.g., 'title', 'author', 'ISBN')")
    fromImages string @description("What you extracted from the images")
    fromNotes string @description("What the previous team member noted")
    agreement bool @description("Whether the two sources agree")
    reasoning string @description(#"
        If there's disagreement, explain which source is more reliable and why. Consider factors like:
        - Image quality and clarity
        - Completeness of information
        - Consistency across multiple image locations
        - Script/language accuracy
    "#)
    finalDecision string @description("The value you've decided to use in the final output")
}

class BookMainData {
    // Chain-of-thought reasoning fields
    extractionEvidence TextExtractionEvidence[] @description(#"
        Document ALL text extractions from the images. For each piece of text you can read from any image:
        - Note which image it comes from
        - Specify the location on that page
        - Record the exact text in its original script
        - Identify what type of information it likely represents
        - Identify the script system
        - Rate your confidence in the extraction
    "#)
    
    languageScriptAnalysis string @description(#"
        Analyze the linguistic and script characteristics observed:
        - What language(s) appear in the book's text?
        - What script system(s) are used for writing?
        - Are there multiple languages (e.g., original + translation)?
        - How did you determine the language(s) and script(s)?
        - Note any special characters, diacritics, or writing system features
    "#)
    
    dataComparisons DataComparison[] @description(#"
        Compare your image-based extractions with the team member's notes field by field.
        For each bibliographic field (title, author, ISBN, year, etc.):
        - State what you found in images
        - State what the notes say
        - Indicate if they agree or disagree
        - If they disagree, provide detailed reasoning about which is more accurate
        - State your final decision
    "#)
    
    transliterationReasoning string @description(#"
        For non-Latin scripts, explain your transliteration approach:
        - What transliteration system are you using? (e.g., Pinyin for Chinese, Hepburn for Japanese)
        - How are you handling special characters and diacritics?
        - What challenges did you encounter in creating ASCII-safe versions?
        - Document any ambiguous cases and how you resolved them
    "#)
    
    // Final extracted fields
    title BookTitle @description("Book title information, in original script, latin script, and indonesian translation. Based on your analysis and comparisons above.")
    
    language string[] @description(#"
        The language(s) that exists within the given book's data. Based on your languageScriptAnalysis.
        Examples: ["English"], ["Indonesian"], ["Russian", "English"], ["Japanese"]
    "#)
    
    script string[] @description(#"
        The script(s) that exists within the given book's data. Based on your languageScriptAnalysis.
        Examples: ["Latin"], ["Cyrillic"], ["Arabic"], ["Chinese (Simplified)"], ["Devanagari"], ["Latin", "Cyrillic"]
    "#)
    
    authors BookAuthor[] @description("List of book authors. Each author should have both original script and transliterated versions based on your extraction evidence.")
    
    translator BookTranslator[]? @description("List of translators if applicable. Only include if translation information is present in the evidence.")
    
    isbn_13 string? @description("13-digit ISBN if visible and/or present. Verify format: should be exactly 13 digits, possibly with hyphens.")
    
    isbn_10 string? @description("10-digit ISBN if visible and/or present. Verify format: should be exactly 10 digits, possibly with hyphens.")
    
    published_year int? @description("The year the book was published, if visible and/or present. Should be a 4-digit year.")
    
    confidence float @description(#"
        Overall confidence level of extraction (0.0-1.0). Consider:
        - Image quality and readability
        - Agreement between images and notes
        - Completeness of information
        - Clarity of critical fields (title, author)
        - Any ambiguities or uncertainties in the process
    "#)
}

function GetBookMainData(MultiImages: image[], bookId: string, RawVisualNote: string) -> BookMainData {
    client "FreeLLMWithFallback"
    prompt #"
        You are an expert librarian and archivist specializing in multilingual bibliographic data extraction. Your role in this national library cataloguing project is to perform precise, systematic extraction of bibliographic metadata from book photographs, ensuring accuracy across different scripts and languages.

        CONTEXT:
        Book ID: {{bookId}}
        You have received {{MultiImages|length}} image(s) of this book, showing various parts including front cover, back cover, spine, colophon page, and potentially other relevant pages. A previous team member has provided detailed notes about the visual content. All images are guaranteed to be of the same book.

        YOUR MISSION:
        Extract comprehensive bibliographic data through a systematic, evidence-based chain-of-thought process. You must document your reasoning at each step to ensure accuracy and enable verification.

        ═══════════════════════════════════════════════════════════════════════════════
        ANALYTICAL WORKFLOW - FOLLOW THESE STEPS SEQUENTIALLY:
        ═══════════════════════════════════════════════════════════════════════════════

        {% set total_images = MultiImages|length %}
        
        ╔═══════════════════════════════════════════════════════════════════════════════╗
        ║ STEP 1: COMPREHENSIVE TEXT EXTRACTION FROM ALL IMAGES                        ║
        ╚═══════════════════════════════════════════════════════════════════════════════╝
        
        Systematically examine each of the {{total_images}} image(s):
        
        {% for image in MultiImages %}
        IMAGE {{loop.index}} of {{total_images}}:
        For this image, extract ALL readable text regardless of script or language:
        - Identify the page type (front cover, back cover, spine, colophon, etc.)
        - Locate and transcribe each text element with its position
        - Record text EXACTLY as it appears in its original script
        - Determine what each text element likely represents:
          * Title (main title, subtitle)
          * Author name(s)
          * Translator name(s)
          * Publisher name
          * Publication year
          * ISBN numbers (10-digit or 13-digit)
          * Edition information
          * Series information
        - Identify the script system used (Latin, Cyrillic, Arabic, Chinese, Japanese, Korean, Devanagari, etc.)
        - Rate your confidence (high/medium/low) based on image quality and text clarity
        
        {% endfor %}
        
        Document all findings in the 'extractionEvidence' array. Be thorough and systematic.

        ---

        ╔═══════════════════════════════════════════════════════════════════════════════╗
        ║ STEP 2: LANGUAGE AND SCRIPT ANALYSIS                                         ║
        ╚═══════════════════════════════════════════════════════════════════════════════╝
        
        Based on the text you extracted, analyze linguistic characteristics:
        
        LANGUAGE IDENTIFICATION:
        - What language(s) is the book written in?
        - Are there multiple languages present? (e.g., bilingual edition, translation)
        - What textual clues indicate the language? (vocabulary, grammar, character sets)
        
        SCRIPT IDENTIFICATION:
        - What writing system(s) are used?
        - Are there mixed scripts? (e.g., Latin with Japanese, Arabic with English)
        - Note any special characters, diacritics, or unique script features
        
        Document your analysis in 'languageScriptAnalysis' with clear reasoning.

        ---

        ╔═══════════════════════════════════════════════════════════════════════════════╗
        ║ STEP 3: CROSS-VALIDATION WITH TEAM MEMBER NOTES                              ║
        ╚═══════════════════════════════════════════════════════════════════════════════╝
        
        The previous team member provided these notes:
        ---
        {{RawVisualNote}}
        ---
        
        Now perform field-by-field comparison:
        
        For EACH bibliographic field, document in 'dataComparisons':
        
        TITLE:
        - What title did you extract from images?
        - What title is in the notes?
        - Do they match? If not, which is more accurate and why?
        
        AUTHOR(S):
        - What author name(s) did you find?
        - What does the notes say?
        - Evaluate discrepancies considering: name spelling, script variations, completeness
        
        ISBN:
        - Did you find ISBN-13 or ISBN-10?
        - Does it match the notes?
        - Verify the format is correct (13 or 10 digits)
        
        PUBLICATION YEAR:
        - What year did you extract?
        - What year is in the notes?
        - Which source is more reliable?
        
        PUBLISHER:
        - Publisher information from images vs. notes
        - Consistency check
        
        TRANSLATOR (if applicable):
        - Is this a translation?
        - Who is listed as translator?
        - Cross-check sources
        
        For EACH comparison, provide:
        - Your finding
        - Notes finding
        - Agreement (true/false)
        - Reasoning (especially if disagreement)
        - Final decision on which value to use

        ---

        ╔═══════════════════════════════════════════════════════════════════════════════╗
        ║ STEP 4: TRANSLITERATION STRATEGY (For Non-Latin Scripts)                     ║
        ╚═══════════════════════════════════════════════════════════════════════════════╝
        
        {% if total_images > 0 %}
        If the book uses non-Latin scripts, document your transliteration approach:
        {% endif %}
        
        TRANSLITERATION SYSTEM:
        - For Chinese: Use Pinyin romanization
        - For Japanese: Use Hepburn romanization
        - For Korean: Use Revised Romanization of Korean
        - For Russian/Cyrillic: Use BGN/PCGN romanization or ISO 9
        - For Arabic: Use ALA-LC romanization
        - For other scripts: Specify the system used
        
        ASCII SAFETY:
        - How are you converting special characters?
        - How are diacritics being handled? (e.g., ü → u, ñ → n)
        - What about special letters? (e.g., ø → o, ß → ss)
        
        AMBIGUITY RESOLUTION:
        - Document any challenging cases
        - Explain your decision-making process
        - Note alternative transliterations considered
        
        Record in 'transliterationReasoning' field.

        ---

        ╔═══════════════════════════════════════════════════════════════════════════════╗
        ║ STEP 5: CONFIDENCE ASSESSMENT                                                ║
        ╚═══════════════════════════════════════════════════════════════════════════════╝
        
        Evaluate your overall confidence (0.0 to 1.0):
        
        Consider these factors:
        - Image quality: Are all images clear and readable? (+)
        - Text legibility: Can you read all critical information clearly? (+)
        - Agreement: Do images and notes agree? (+)
        - Completeness: Is all bibliographic data present? (+)
        - Ambiguity: Are there uncertain or unclear elements? (-)
        - Script complexity: Are non-Latin scripts clear and identifiable? (+/-)
        - Discrepancies: Are there conflicts between sources? (-)
        
        Confidence scale:
        - 0.9-1.0: Excellent quality, complete data, high certainty
        - 0.7-0.89: Good quality, mostly complete, minor uncertainties
        - 0.5-0.69: Moderate quality, some missing data, notable uncertainties
        - 0.3-0.49: Poor quality, incomplete data, significant uncertainties
        - 0.0-0.29: Very poor quality, major data gaps, high uncertainty

        ---

        ╔═══════════════════════════════════════════════════════════════════════════════╗
        ║ STEP 6: FINAL DATA COMPILATION                                               ║
        ╚═══════════════════════════════════════════════════════════════════════════════╝
        
        Now compile your final bibliographic data:
        
        TITLE (BookTitle object):
        - title_in_origin_script: Exact title in original script
        - title_in_latin_script: Transliterated title (ASCII-safe)
        - title_in_indonesian: Indonesian translation (or original if already Indonesian)
        
        AUTHORS (BookAuthor array):
        - For each author: original script + Latin transliteration
        
        TRANSLATORS (BookTranslator array, if applicable):
        - For each translator: original script + Latin transliteration
        - Only include if translation is confirmed
        
        LANGUAGE array: List all languages present
        SCRIPT array: List all writing systems used
        
        ISBN_13: 13-digit ISBN if present (format: XXX-X-XXX-XXXXX-X or XXXXXXXXXXXXX)
        ISBN_10: 10-digit ISBN if present (format: X-XXX-XXXXX-X or XXXXXXXXXX)
        
        PUBLISHED_YEAR: 4-digit year (YYYY format)
        
        CONFIDENCE: Your calculated confidence score (0.0-1.0)

        ---

        CRITICAL GUIDELINES:
        ═══════════════════════════════════════════════════════════════════════════════
        
        ✓ Extract text EXACTLY as it appears - preserve original script accuracy
        ✓ Document your reasoning at every step
        ✓ When sources conflict, explain which is more reliable and why
        ✓ For non-Latin scripts, follow standard transliteration systems
        ✓ Ensure ASCII safety in Latin transliterations
        ✓ Be honest about uncertainties - don't fabricate data
        ✓ Cross-validate information across multiple image locations when possible
        ✓ The final JSON may include comments explaining your reasoning
        ✓ It's ok if the JSON isn't fully valid initially, we will clean it afterwards
        ✓ Write a codeblock ONLY for the final JSON data containing your analysis
        
        ═══════════════════════════════════════════════════════════════════════════════

        {{ ctx.output_format }}

        {{ _.role("user") }}
        
        BOOK IMAGES:
        {% for image in MultiImages %}
        Image {{loop.index}} of {{total_images}}: {{image}}
        {% endfor %}
        
        TEAM MEMBER NOTES:
        ---
        {{RawVisualNote}}
        ---
        
        Please analyze Book ID {{bookId}} following the 6-step workflow above. Document your reasoning thoroughly, then provide the final structured bibliographic data.
    "#
}