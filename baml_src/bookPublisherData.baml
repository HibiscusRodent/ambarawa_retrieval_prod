class PublisherName {
    original_script string @description("Publisher name in original script/language")
    romanized string? @description("Romanized version of publisher name if applicable")
    english_translation string? @description("English translation of publisher name if applicable")
    indonesian_translation string? @description("Indonesian translation of publisher name if applicable")
}

class PublisherLocation {
    original_script string @description("Publisher location in original script/language")
    romanized string? @description("Romanized version of publisher location if applicable")
    english_translation string? @description("English translation of publisher location")
    indonesian_translation string? @description("Indonesian translation of publisher location")
    country string @description("Country name in English")
}

class Editor {
    original_script string @description("Editor name in original script/language")
    romanized string? @description("Romanized version of editor name if applicable")
}

class DistributorName {
    original_script string @description("Distributor name in original script/language")
    romanized string? @description("Romanized version of distributor name if applicable")
    english_translation string? @description("English translation of distributor name")
    indonesian_translation string? @description("Indonesian translation of distributor name")
}

class DistributorLocation {
    original_script string @description("Distributor location in original script/language")
    romanized string? @description("Romanized version of distributor location if applicable")
    english_translation string? @description("English translation of distributor location")
    indonesian_translation string? @description("Indonesian translation of distributor location")
    country string @description("Country name in English")
}

class PublisherTextEvidence {
    imageNumber int @description("The index number of the image this evidence comes from")
    pageType string @description("Type of page where found (e.g., 'colophon page', 'back cover', 'front cover', 'copyright page')")
    location string @description("Specific location on the page (e.g., 'bottom center', 'inside front flap', 'verso')")
    extractedText string @description("The exact text as it appears, in its original script")
    textType string @description("What this text represents (e.g., 'publisher name', 'publisher address', 'editor name', 'distributor', 'printer', 'imprint')")
    scriptIdentified string @description("The script system used")
    confidence string @description("Extraction confidence: 'high', 'medium', or 'low'")
}

class PublisherDataComparison {
    fieldName string @description("The field being compared (e.g., 'publisher_name', 'publisher_location', 'editor', 'distributor')")
    fromImages string @description("What you extracted from the images")
    fromNotes string @description("What the previous team member noted")
    agreement bool @description("Whether the two sources agree")
    reasoning string @description(#"
        If there's disagreement, explain which source is more reliable and why. Consider:
        - Clarity and completeness in images
        - Typical colophon page conventions
        - Script/language accuracy
        - Consistency across multiple locations
    "#)
    finalDecision string @description("The value you've decided to use in the final output")
}

class RoleDistinction {
    publisherIdentified bool @description("Whether publisher information was found")
    editorIdentified bool @description("Whether editor information was found")
    distributorIdentified bool @description("Whether distributor information was found (distinct from publisher)")
    printerIdentified bool @description("Whether printer information was found (separate from publisher)")
    reasoning string @description(#"
        Explain how you distinguished between publisher, distributor, editor, and printer roles:
        - Publishers typically appear with copyright symbols or publishing statements
        - Distributors may be noted separately, especially for international books
        - Editors are usually listed in smaller text or editorial credits
        - Printers appear in production credits, often with 'printed by' language
        Document any ambiguous cases and your reasoning.
    "#)
}

class BookPubAndDistDetails {
    // Chain-of-thought reasoning fields
    extractionEvidence PublisherTextEvidence[] @description(#"
        Document ALL text extractions related to publishing information from the images.
        Focus primarily on colophon page, but also check:
        - Copyright page
        - Back cover
        - Inside covers
        - Title page verso
        For each piece of text, document location, content, type, and confidence.
    "#)
    
    roleDistinction RoleDistinction @description(#"
        Analyze and distinguish between different roles in the book's production:
        - Who is the publisher? (primary entity responsible for the book)
        - Who is the distributor? (if different from publisher)
        - Who is the editor? (if listed)
        - Who is the printer? (if separately identified)
        Explain your reasoning for role assignments.
    "#)
    
    dataComparisons PublisherDataComparison[] @description(#"
        Compare your image-based extractions with the team member's notes field by field.
        For each field (publisher name, location, editor, distributor):
        - State what you found in images
        - State what the notes say
        - Indicate agreement or disagreement
        - If they disagree, provide detailed reasoning
        - State your final decision
    "#)
    
    transliterationStrategy string @description(#"
        For non-Latin scripts, document your transliteration and translation approach:
        - What transliteration system are you using?
        - How are you handling organizational names vs. personal names?
        - What challenges did you encounter with place names?
        - How are you ensuring ASCII safety for romanized versions?
        - Document your translation strategy for English and Indonesian versions
    "#)
    
    geographicAnalysis string @description(#"
        Analyze the geographic information:
        - How did you identify the country?
        - Are there multiple locations mentioned? (e.g., publisher HQ vs. print location)
        - How did you parse city, region, and country information?
        - Any ambiguities in location identification?
    "#)
    
    // Final extracted fields
    publisher_name PublisherName @description("Publisher name information in all relevant scripts and languages")
    
    publisher_location PublisherLocation @description("Publisher location information in all relevant scripts and languages")
    
    editor Editor? @description("Editor information if visible and confirmed. Only include if editor role is clearly identified.")
    
    distributor_name DistributorName? @description("Distributor name information if different from publisher. Only include if distributor is explicitly mentioned as separate entity.")
    
    distributor_location DistributorLocation? @description("Distributor location information if different from publisher location.")
    
    confidence float @description(#"
        Overall confidence level of extraction (0.0-1.0). Consider:
        - Clarity of colophon page or copyright page
        - Agreement between images and notes
        - Completeness of publisher information
        - Ambiguity in role distinctions
        - Quality of geographic information
    "#)
    
    image_count int @description("Number of images analyzed in this extraction")
}

function GetBookPublisherData(MultiImages: image[], bookId: string, RawVisualNote: string) -> BookPubAndDistDetails {
    client "Gemini20FlashLite"
    prompt #"
        You are an expert librarian and publishing industry specialist with deep knowledge of book production, distribution, and colophon conventions across different countries and languages. Your role in this national library cataloguing project is to extract precise publisher and distributor information from book photographs.

        CONTEXT:
        Book ID: {{bookId}}
        You have received {{MultiImages|length}} image(s) of this book. A previous team member has documented important textual and visual details. All images are guaranteed to be of the same book.

        YOUR MISSION:
        Extract comprehensive publisher and distributor data through a systematic, evidence-based chain-of-thought process. You must carefully distinguish between publishers, distributors, editors, and printers, as these roles are often confused.

        ═══════════════════════════════════════════════════════════════════════════════
        ANALYTICAL WORKFLOW - FOLLOW THESE STEPS SEQUENTIALLY:
        ═══════════════════════════════════════════════════════════════════════════════

        {% set total_images = MultiImages|length %}
        
        ╔═══════════════════════════════════════════════════════════════════════════════╗
        ║ STEP 1: COMPREHENSIVE TEXT EXTRACTION - PUBLISHING INFORMATION               ║
        ╚═══════════════════════════════════════════════════════════════════════════════╝
        
        Systematically examine each of the {{total_images}} image(s) for publisher-related information:
        
        PRIMARY FOCUS: Colophon Page / Copyright Page
        This is typically where publisher information appears. Look for:
        - Copyright statements (©, Copyright, Hak Cipta)
        - Publisher name and logo
        - Publication date and place
        - ISBN and cataloging data
        - Printer information
        - Distributor information
        
        SECONDARY LOCATIONS:
        - Title page verso (back of title page)
        - Back cover (publisher name/logo)
        - Inside covers or flaps
        - Spine (publisher imprint)
        
        {% for image in MultiImages %}
        IMAGE {{loop.index}} of {{total_images}}:
        For this image, extract ALL text related to publishing:
        - Identify page type (colophon, copyright, back cover, etc.)
        - Locate and transcribe publisher-related text with exact position
        - Record text EXACTLY in its original script
        - Classify each text element:
          * Publisher name
          * Publisher address/location
          * Editor name (editorial credits)
          * Distributor name (if separate from publisher)
          * Distributor location
          * Printer name (production credits)
          * Copyright holder (often the publisher)
          * Imprint information
        - Identify script system used
        - Rate confidence (high/medium/low)
        
        {% endfor %}
        
        Document all findings in 'extractionEvidence' array.

        ---

        ╔═══════════════════════════════════════════════════════════════════════════════╗
        ║ STEP 2: ROLE DISTINCTION - PUBLISHER vs DISTRIBUTOR vs EDITOR vs PRINTER     ║
        ╚═══════════════════════════════════════════════════════════════════════════════╝
        
        Carefully distinguish between different entities:
        
        PUBLISHER:
        - Primary entity responsible for the book's publication
        - Usually appears with copyright statement
        - Often has logo or imprint mark
        - Typically listed first in credits
        - May include phrases like "Published by", "Diterbitkan oleh", "出版社"
        
        DISTRIBUTOR:
        - Handles distribution and sales (separate from publisher)
        - More common in international or translated books
        - Look for phrases like "Distributed by", "Didistribusikan oleh"
        - May have different location from publisher
        - Sometimes only appears on back cover
        
        EDITOR:
        - Individual(s) who edited the content
        - Usually smaller text or in editorial credits
        - Look for "Editor:", "Edited by", "Penyunting"
        - Personal name, not company name
        
        PRINTER:
        - Company that physically printed the book
        - Look for "Printed by", "Dicetak oleh", "印刷"
        - Often includes print location
        - May be same as or different from publisher
        
        Document your analysis in 'roleDistinction':
        - Which entities did you identify?
        - How did you distinguish between them?
        - What textual/visual clues helped?
        - Any ambiguous cases?

        ---

        ╔═══════════════════════════════════════════════════════════════════════════════╗
        ║ STEP 3: CROSS-VALIDATION WITH TEAM MEMBER NOTES                              ║
        ╚═══════════════════════════════════════════════════════════════════════════════╝
        
        The previous team member provided these notes:
        ---
        {{RawVisualNote}}
        ---
        
        Now perform field-by-field comparison:
        
        For EACH publishing-related field, document in 'dataComparisons':
        
        PUBLISHER NAME:
        - What publisher name did you extract from images?
        - What does the notes say?
        - Do they match? Consider variations in spelling/transliteration
        
        PUBLISHER LOCATION:
        - What location did you find?
        - What location is in the notes?
        - Check for city, region, country consistency
        
        EDITOR:
        - Did you find editor information?
        - Is it in the notes?
        - Is the role clearly identified?
        
        DISTRIBUTOR:
        - Is there a separate distributor?
        - Does it match the notes?
        - Is it truly different from the publisher?
        
        For EACH comparison, provide:
        - Your finding
        - Notes finding
        - Agreement (true/false)
        - Reasoning (especially if disagreement)
        - Final decision

        ---

        ╔═══════════════════════════════════════════════════════════════════════════════╗
        ║ STEP 4: TRANSLITERATION & TRANSLATION STRATEGY                               ║
        ╚═══════════════════════════════════════════════════════════════════════════════╝
        
        For publisher/distributor names and locations in non-Latin scripts:
        
        ORGANIZATIONAL NAME TRANSLITERATION:
        - Use standard romanization for the language
        - For well-known publishers, check for official romanization
        - Handle company suffixes appropriately (Ltd., Co., Publishing House, etc.)
        - Ensure ASCII safety (remove diacritics for romanized version)
        
        TRANSLATION STRATEGY:
        - English translation: Translate descriptive parts, keep proper names
          Example: "上海人民出版社" → "Shanghai People's Publishing House"
        - Indonesian translation: Similar approach, localize to Indonesian
        - Keep organizational structure indicators (PT, CV, Inc., etc.)
        
        PLACE NAME HANDLING:
        - Use standard geographical name conventions
        - City names: Use commonly accepted English/romanized forms
        - Country identification: Use ISO standard English names
        - Handle regional variations (e.g., Peking vs Beijing)
        
        Document in 'transliterationStrategy' field.

        ---

        ╔═══════════════════════════════════════════════════════════════════════════════╗
        ║ STEP 5: GEOGRAPHIC ANALYSIS                                                  ║
        ╚═══════════════════════════════════════════════════════════════════════════════╝
        
        Analyze location information carefully:
        
        LOCATION PARSING:
        - Identify city, state/province, country from addresses
        - Handle abbreviated forms
        - Distinguish publisher location from print location
        - Note if multiple locations mentioned (e.g., HQ vs branch offices)
        
        COUNTRY IDENTIFICATION:
        - Use context clues: language, script, address format
        - Check postal codes or area codes if visible
        - Consider publisher name conventions
        - Use standard English country names in output
        
        AMBIGUITY HANDLING:
        - What if location is unclear or abbreviated?
        - What if publisher has offices in multiple countries?
        - How do you handle historical place names?
        
        Document analysis in 'geographicAnalysis' field.

        ---

        ╔═══════════════════════════════════════════════════════════════════════════════╗
        ║ STEP 6: CONFIDENCE ASSESSMENT                                                ║
        ╚═══════════════════════════════════════════════════════════════════════════════╝
        
        Evaluate overall confidence (0.0 to 1.0):
        
        Consider:
        - Colophon page clarity: Is it clearly visible and readable? (+)
        - Information completeness: All required fields present? (+)
        - Agreement: Do images and notes agree? (+)
        - Role clarity: Are publisher/distributor/editor clearly distinguished? (+)
        - Location clarity: Is geographic information unambiguous? (+)
        - Script legibility: Can you read all text clearly? (+)
        - Ambiguities: Are there uncertain elements? (-)
        
        Confidence scale:
        - 0.9-1.0: Excellent colophon, complete data, high certainty
        - 0.7-0.89: Good information, mostly complete, minor uncertainties
        - 0.5-0.69: Moderate quality, some gaps, notable ambiguities
        - 0.3-0.49: Poor quality, incomplete, significant uncertainties
        - 0.0-0.29: Very poor, major gaps, high uncertainty

        ---

        ╔═══════════════════════════════════════════════════════════════════════════════╗
        ║ STEP 7: FINAL DATA COMPILATION                                               ║
        ╚═══════════════════════════════════════════════════════════════════════════════╝
        
        Compile final publisher and distributor data:
        
        PUBLISHER_NAME (PublisherName object):
        - original_script: Exact name in original script
        - romanized: Romanized version (ASCII-safe)
        - english_translation: English translation if applicable
        - indonesian_translation: Indonesian translation if applicable
        
        PUBLISHER_LOCATION (PublisherLocation object):
        - original_script: Exact location in original script
        - romanized: Romanized version
        - english_translation: English version
        - indonesian_translation: Indonesian version
        - country: Standard English country name
        
        EDITOR (Editor object, optional):
        - original_script: Editor name in original script
        - romanized: Romanized version
        - Only include if editor is clearly identified
        
        DISTRIBUTOR_NAME (DistributorName object, optional):
        - Same structure as publisher_name
        - Only include if distributor is separate entity from publisher
        
        DISTRIBUTOR_LOCATION (DistributorLocation object, optional):
        - Same structure as publisher_location
        - Only include if distributor location differs from publisher
        
        CONFIDENCE: Your calculated confidence score (0.0-1.0)
        
        IMAGE_COUNT: {{total_images}}

        ---

        CRITICAL GUIDELINES:
        ═══════════════════════════════════════════════════════════════════════════════
        
        ✓ Focus on colophon/copyright page as primary source
        ✓ Carefully distinguish publisher from distributor, editor, and printer
        ✓ Extract text EXACTLY as it appears in original script
        ✓ Use standard transliteration systems for romanization
        ✓ Ensure ASCII safety in romanized versions
        ✓ Only include distributor if clearly separate from publisher
        ✓ Only include editor if clearly identified (not just "edited by publisher")
        ✓ Document reasoning at every step
        ✓ Be honest about uncertainties
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
        
        Please analyze Book ID {{bookId}} following the 7-step workflow above. Focus especially on distinguishing between publisher, distributor, editor, and printer roles. Document your reasoning thoroughly, then provide the final structured publisher/distributor data.
    "#
}