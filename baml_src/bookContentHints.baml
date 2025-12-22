class ContentHints {
    // Chain-of-thought reasoning fields
    extractedTextSnippets string[] @description(#"
        List all relevant text snippets found in the images and notes that might contain blurb text, descriptions, or content-related information. Include quotes from back cover, inside flaps, book descriptions, or any promotional text. Each snippet should be a direct quote from the source material.
    "#)
    
    nerCandidates string[] @description(#"
        List all potential named entities identified from the text snippets. Include names of people, places, organizations, historical figures, dates, events, etc. Be comprehensive in this initial extraction phase.
    "#)
    
    contentClues string[] @description(#"
        Before making final decisions, list out observable clues about the book's nature:
        - Keywords or phrases suggesting fiction vs non-fiction
        - Narrative style indicators (e.g., "once upon a time", "this study examines")
        - Presence of character names vs. real people/events
        - Academic or scholarly language vs. narrative prose
        - Any genre-specific terminology or themes
    "#)
    
    // Final analysis fields
    bookBlurbText string? @description(#"
        The finalized blurb text or book description extracted from the identified text snippets. Synthesize the most relevant descriptive text about the book's content. If multiple description texts are found, combine them coherently. If not available, state "no blurb text available"
    "#)
    
    bookNERData string[] @description(#"
        Final curated list of named entities extracted from the blurb text and other relevant content. Remove duplicates and false positives from the nerCandidates. Entities should be organized and verified. Include:
        - Person names (authors, characters, historical figures)
        - Place names (cities, countries, regions)
        - Organizations (companies, institutions)
        - Temporal references (dates, time periods, events)
    "#)
    
    fictionAnalysis string @description(#"
        Detailed reasoning for determining whether this book is fiction or non-fiction. Reference specific clues from contentClues and explain your logical reasoning process. Consider:
        - Is this telling a fabricated story or presenting factual information?
        - Does it feature invented characters or real people/events?
        - What is the author's intent based on available evidence?
    "#)
    
    isFiction bool @description("Final determination: true if fiction, false if non-fiction. This should align with the fictionAnalysis reasoning.")
    
    genreAnalysis string @description(#"
        Detailed reasoning for genre classification. Explain what specific elements, themes, keywords, or patterns led you to each genre determination. Reference the contentClues and other extracted information. Consider multiple genre possibilities and explain why certain genres fit better than others.
    "#)
    
    bookGenre string[] @description(#"
        Final genre classification(s) for the book. Can include multiple genres if the book spans categories. Common genres include but not limited to:
        Fiction: Literary Fiction, Science Fiction, Fantasy, Mystery, Thriller, Romance, Historical Fiction, Horror, Adventure
        Non-fiction: Biography, Autobiography, History, Science, Philosophy, Self-help, Travel, Memoir, Essay, Academic/Textbook
        Specialized: Poetry, Drama, Graphic Novel, Children's Literature, Young Adult
    "#)
    
    bookContextHints string? @description(#"
        Synthesized contextual information that enriches understanding of the book. Include:
        - Historical or cultural context referenced in the content
        - Thematic elements and their significance
        - Potential target audience or reading level
        - Literary or intellectual traditions it might belong to
        - Any unique characteristics or notable aspects
        Base this only on evidence from the analyzed material, avoid speculation.
    "#)
}

function GetBookContentHints(MultiImages: image[], bookId: string, RawVisualNote: string) -> ContentHints {
    client "FreeLLMWithFallback"
    prompt #"
        You are an expert literary analyst and librarian specializing in content classification and metadata extraction. Your role is to perform a thorough, step-by-step analysis of book content to extract meaningful insights about its nature, themes, and classification.

        CONTEXT:
        The field team has collected photos of a book (ID: {{bookId}}). A previous team member has documented important visual and textual details from these images. Your task is to analyze this information systematically using a chain-of-thought approach to extract content hints, classify the book, and identify key entities and themes.

        ANALYTICAL WORKFLOW:
        You must follow this step-by-step reasoning process. Think carefully through each stage:

        {% set total_images = MultiImages|length %}
        
        STEP 1: TEXT EXTRACTION & COMPILATION
        First, examine all available sources to extract text snippets that describe the book's content:
        
        {% if total_images > 0 %}
        - Analyze ALL {{total_images}} image(s) provided
        - Look for blurb text (often on back cover or inside flaps)
        - Identify promotional descriptions or summaries
        - Note any review quotes or endorsements
        {% endif %}
        
        - Review the detailed notes from the previous team member: 
        {{RawVisualNote}}
        
        Extract and list ALL relevant text snippets in the 'extractedTextSnippets' field. Be thorough.

        ---

        STEP 2: NAMED ENTITY RECOGNITION (NER)
        Based on the text snippets you extracted, identify ALL potential named entities:
        - Scan for proper nouns (capitalized words that could be names)
        - Identify person names (could be authors, characters, historical figures)
        - Identify place names (cities, countries, regions, landmarks)
        - Identify organizations (companies, institutions, groups)
        - Identify temporal references (dates, years, time periods, historical events)
        
        List all candidates in 'nerCandidates' - it's better to be over-inclusive at this stage.

        ---

        STEP 3: CONTENT ANALYSIS & CLUE GATHERING
        Examine the extracted text for clues about the book's nature:
        
        {% if total_images > 1 %}
        Consider patterns across the {{total_images}} images:
        {% endif %}
        
        - What type of language is used? (narrative, academic, poetic, technical, etc.)
        - Are there indicators of fictional storytelling vs. factual reporting?
        - What themes or subjects are explicitly mentioned?
        - What genre-specific keywords appear? (e.g., "mystery", "history of", "guide to")
        - Are there character names vs. historical/real person names?
        - Does it describe a plot/story or explain factual information?
        
        Document your observations in 'contentClues'.

        ---

        STEP 4: FICTION VS NON-FICTION DETERMINATION
        Now, synthesize your observations to determine if this is fiction or non-fiction:
        
        Consider:
        - Does it present imagined events and characters, or real-world information?
        - Is the primary purpose to tell a story or to inform/educate?
        - What does the language style suggest?
        - What do the named entities tell you? (fictional characters vs. historical figures)
        
        Write your detailed reasoning in 'fictionAnalysis', then set 'isFiction' (true/false).

        ---

        STEP 5: GENRE CLASSIFICATION
        Based on all the evidence gathered, classify the book into appropriate genre(s):
        
        Think through:
        - What are the primary themes and subject matter?
        - What genre conventions or markers are present?
        - Does it fit into multiple genres (e.g., historical fiction, science fiction mystery)?
        - What specific textual evidence supports each genre choice?
        
        Document your reasoning in 'genreAnalysis', then list the genre(s) in 'bookGenre'.

        ---

        STEP 6: FINALIZATION & SYNTHESIS
        Finally, compile your final outputs:
        
        - Synthesize the best blurb text from your extracted snippets ('bookBlurbText')
        - Curate and deduplicate the NER candidates into a final list ('bookNERData')
        - Compile contextual insights about the book's significance ('bookContextHints')

        ---

        IMPORTANT GUIDELINES:
        - Base ALL conclusions on observable evidence from the images and notes
        - When uncertain, acknowledge it - don't fabricate information
        - If a field cannot be determined, explain why in your reasoning
        - Think step-by-step, showing your work in the reasoning fields
        - The final JSON may include comments with your reasoning inline
        - It's ok if this isn't fully valid JSON initially, we will clean it afterwards, but please write a codeblock ONLY for the final JSON data containing only your analysis.

        {{ ctx.output_format }}

        {{ _.role("user") }}
        
        {% for image in MultiImages %}
        Image {{loop.index}} of {{total_images}}: {{image}}
        {% endfor %}
        
        Field Team Notes:
        ---
        {{RawVisualNote}}
        ---

        Please analyze book ID {{bookId}} following the step-by-step workflow above. Show your reasoning at each stage, then provide the final structured output.
    "#
}