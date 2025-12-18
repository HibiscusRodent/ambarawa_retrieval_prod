enum BookCondition {
    BARU @alias("c1") @description(#"
        The book is in brand new condition, with no visible wear or damage. Often still in original shrink wrap, or in the case where the no shrinkwarp present, it is clear that special preservation and storage measures have been done to keep the book pristine.
    "#)
    SANGAT_BAIK @alias("c2") @description(#" 
        The book is in excellent condition, showing almost no or minimal signs of wear. It has no shrink wrap but looks almost new. The pages are clean and intact, and the cover is in great shape with no visible defects or discoloration.
    "#)
    BAIK @alias("c3") @description(#"
        The book is in very good condition, with some minor wear but no major defects. Pages are clean and intact, and the cover may have slight signs of use but is still in great shape.
    "#)
    CUKUP_BAIK @alias("c4") @description(#"
        The book is in good condition, with noticeable wear and defects. Texts are perfectly readable, and the book is still fully intact. The colors on the cover may be slightly faded, but there are no major damages. The pages may be slightly yellowed due to age, but the prints are still clear and legible.
    "#)
    DITERIMA @alias("c5") @description(#"
        The book is heavily damaged, with significant wear, major defects, tears or signs of water, mold and other damage. Some text may be missing or illegible, but the some texts are still readable, and one can still infer the metadata of the book (title, author, publisher, and/or year) from the remaining text.
    "#)
    BURUK @alias("c6") @description(#"
        The book is in extremely poor condition. Pages are torn, missing or is too deteriorated by water and other damages, that may caused the prints to be blurry and fading. It is barely readable and the metadata of the book cannot be inferred.
    "#)
}

enum BookPrintType {
    HARDCOVER @alias("pt1") @description("The book has a hard cover.")
    PAPERBACK @alias("pt2") @description("The book has a soft cover.")
    FOTOKOPI @alias("pt3") @description("The book is a photocopy or printout.")
}

class PhysicalObservation {
    imageNumber int @description("The index number of the image this observation comes from")
    bookComponent string @description("Which part of the book (e.g., 'front cover', 'back cover', 'spine', 'pages', 'binding', 'edges')")
    observedFeatures string[] @description(#"
        List of specific physical features observed:
        - Discoloration (yellowing, fading, staining)
        - Structural damage (tears, creases, bent corners, warping)
        - Water damage (water stains, rippling, warping)
        - Biological damage (mold, mildew, foxing, insect damage)
        - Wear patterns (edge wear, scuffing, scratches)
        - Binding condition (loose, tight, broken, intact)
        - Page condition (brittle, yellowed, clean, intact)
        - Print quality (clear, faded, smudged, legible)
        - Preservation indicators (shrink wrap, dust jacket, protective covering)
    "#)
    severityLevel string @description("Severity of issues observed: 'none', 'minimal', 'minor', 'moderate', 'major', 'severe', 'critical'")
    readabilityImpact string @description("How the observed damage affects text readability: 'no impact', 'slight impact', 'moderate impact', 'significant impact', 'severe impact', 'illegible'")
}

class ConditionAnalysis {
    overallAssessment string @description(#"
        Comprehensive assessment of the book's physical condition:
        - Summary of all observed damage and wear
        - Evaluation of structural integrity
        - Assessment of readability and usability
        - Notable preservation or deterioration factors
        - Comparison across all images
    "#)
    
    conditionReasoning string @description(#"
        Detailed reasoning for condition classification:
        - Why this condition level was chosen
        - Key factors that determined the classification
        - Comparison with condition enum descriptions
        - Edge cases or borderline considerations
        - Supporting evidence from observations
    "#)
    
    preservationUrgency string @description(#"
        Assessment of preservation urgency: 'none needed', 'routine care', 'preventive measures', 'immediate attention', 'critical intervention required'
        Explain what factors contribute to this urgency level.
    "#)
}

class PrintTypeAnalysis {
    coverMaterial string @description("Observed cover material: 'rigid cardboard/board', 'flexible card stock', 'paper', 'cloth', 'leather', 'synthetic material', 'unknown'")
    
    bindingType string @description("Observed binding type: 'sewn binding', 'perfect binding (glued)', 'saddle stitch (stapled)', 'spiral bound', 'loose leaf', 'unknown'")
    
    printQualityIndicators string[] @description(#"
        Observable indicators of print type:
        - Professional printing (even ink, high quality paper, commercial binding)
        - Photocopy indicators (uneven ink density, copy artifacts, simple binding)
        - Paper quality (coated, uncoated, recycled, newsprint, premium)
        - Cover finish (glossy, matte, laminated, unfinished)
        - Spine construction (professionally bound, stapled, glued, sewn)
        - Overall production quality
    "#)
    
    printTypeReasoning string @description(#"
        Detailed reasoning for print type classification:
        - Why this print type was chosen
        - Key visual indicators that support this classification
        - Comparison with print type enum descriptions
        - Any ambiguous factors considered
    "#)
}

class BookConditionData {
    // Chain-of-thought reasoning fields
    physicalObservations PhysicalObservation[] @description(#"
        Document ALL physical observations from each image:
        - Systematically examine each book component visible
        - List specific features and damage observed
        - Rate severity of each issue
        - Assess impact on readability
        Document observations for each image separately to enable cross-validation.
    "#)
    
    conditionAnalysis ConditionAnalysis @description(#"
        Comprehensive analysis of the book's physical condition:
        - Synthesize observations into overall assessment
        - Explain reasoning for condition classification
        - Evaluate preservation urgency
        This guides the final condition classification.
    "#)
    
    printTypeAnalysis PrintTypeAnalysis @description(#"
        Analysis of the book's print type and construction:
        - Examine cover material and binding
        - Identify print quality indicators
        - Explain reasoning for print type classification
        This guides the final print type classification.
    "#)
    
    // Final classification fields
    Condition BookCondition @description(#"
        Final condition classification based on the detailed analysis above.
        Must align with the conditionAnalysis reasoning and observed damage severity.
    "#)
    
    PrintType BookPrintType @description(#"
        Final print type classification based on the detailed analysis above.
        Must align with the printTypeAnalysis reasoning and observed construction features.
    "#)
}

function GetBookConditionData(MultiImages: image[], bookId: string) -> BookConditionData {
    client "FreeLLMWithFallback"
    prompt #"
        You are an expert book conservator and preservation specialist with extensive experience in assessing the physical condition of books and manuscripts. Your expertise includes identifying various types of damage, evaluating deterioration patterns, and recommending appropriate preservation measures. You are working on a national library cataloguing and preservation project.

        CONTEXT:
        Book ID: {{bookId}}
        You have received {{MultiImages|length}} image(s) showing different aspects of this book. Your assessment will guide preservation decisions and resource allocation for conservation efforts. All images are guaranteed to be of the same book.

        YOUR MISSION:
        Conduct a systematic, evidence-based assessment of the book's physical condition and print type. Your analysis will directly impact preservation planning, so accuracy and thoroughness are critical.

        ANALYTICAL WORKFLOW - FOLLOW THESE STEPS SEQUENTIALLY:

        {% set total_images = MultiImages|length %}
        
        STEP 1: SYSTEMATIC PHYSICAL EXAMINATION                                      ║
        
        Examine each of the {{total_images}} image(s) systematically, documenting all physical observations:
        
        {% for image in MultiImages %}
        IMAGE {{loop.index}} of {{total_images}}:
        
        For this image, conduct a component-by-component examination:
        
        COVER EXAMINATION:
        Front Cover:
        - Surface condition: discoloration, fading, staining
        - Structural integrity: tears, creases, dents, warping
        - Corner condition: bent, rounded, torn, intact
        - Edge condition: fraying, chipping, wear
        - Print/image quality: clear, faded, scratched
        - Protective elements: lamination, dust jacket, shrink wrap
        
        Back Cover:
        - Similar assessment as front cover
        - Spine attachment condition
        - Flap condition (if applicable)
        
        Spine:
        - Structural integrity: intact, cracked, broken, detached
        - Title/text legibility
        - Fading or wear patterns
        - Binding visibility and condition
        
        BINDING EXAMINATION:
        - Binding type: sewn, glued, stapled, spiral
        - Binding integrity: tight, loose, broken, separating
        - Hinge condition: flexible, stiff, broken
        - Thread/glue condition (if visible)
        
        PAGE EXAMINATION (if visible):
        - Page color: white, cream, yellowed, browned, foxed
        - Page brittleness indicators: edges, handling marks
        - Stains or spots: location, type, extent
        - Tears or missing sections
        - Text legibility: clear, faded, smudged
        - Page attachment to binding
        
        DAMAGE ASSESSMENT:
        For each observed issue, rate severity:
        - NONE: No damage present
        - MINIMAL: Barely noticeable, no functional impact
        - MINOR: Noticeable but not affecting usability
        - MODERATE: Clearly visible, some functional impact
        - MAJOR: Significant damage, substantial impact
        - SEVERE: Extensive damage, major functional issues
        - CRITICAL: Extreme deterioration, barely functional
        
        READABILITY IMPACT:
        - Can all text be read clearly?
        - Are there any areas where text is obscured?
        - How does damage affect book usability?
        
        {% endfor %}
        
        Document all observations in 'physicalObservations' array, one entry per image.

        ---

        STEP 2: CONDITION SYNTHESIS & CLASSIFICATION
        
        Synthesize observations to determine overall condition:
        
        CONDITION CLASSIFICATION CRITERIA:
        
        BARU (Brand New):
        - No visible wear or damage whatsoever
        - May have original shrink wrap
        - Pristine preservation condition
        - Perfect structural integrity
        → Use this ONLY if book appears completely unused
        
        SANGAT_BAIK (Excellent):
        - Almost no signs of wear
        - No shrink wrap but looks almost new
        - All pages clean and intact
        - Cover in great shape, no defects
        - Minimal to no discoloration
        → Use for books in near-mint condition
        
        BAIK (Very Good):
        - Minor wear but no major defects
        - Pages clean and intact
        - Cover shows slight use
        - All text clearly legible
        - Minimal age-related changes
        → Use for well-maintained books with light use
        
        CUKUP_BAIK (Good):
        - Noticeable wear and defects
        - Text perfectly readable
        - Book fully intact
        - Cover colors may be faded
        - Pages may be yellowed but prints clear
        → Use for books showing normal aging and use
        
        DITERIMA (Acceptable/Poor):
        - Heavy damage present
        - Significant wear, tears, or water/mold damage
        - Some text may be missing or illegible
        - Metadata still inferable
        - Structural integrity compromised but functional
        → Use for damaged books still containing useful information
        
        BURUK (Bad):
        - Extremely poor condition
        - Extensive deterioration
        - Pages torn, missing, or severely damaged
        - Text barely readable or illegible
        - Metadata cannot be reliably inferred
        - Requires immediate conservation or may be unsalvageable
        → Use only for severely damaged books
        
        ANALYSIS REQUIRED:
        - What is the overall condition across all images?
        - What are the most significant condition factors?
        - How does the damage pattern compare to enum criteria?
        - Are there any edge cases or borderline situations?
        - What preservation urgency does this condition suggest?
        
        Document in 'conditionAnalysis' field.

        ---

        STEP 3: PRINT TYPE DETERMINATION
        
        Determine the book's print type based on construction and production quality:
        
        PRINT TYPE CLASSIFICATION CRITERIA:
        
        HARDCOVER:
        Indicators:
        - Rigid cover made of thick board/cardboard
        - Cover wrapped in cloth, paper, or synthetic material
        - Professional binding (sewn or high-quality perfect binding)
        - Spine typically reinforced
        - May have dust jacket
        - Higher production quality
        - Substantial weight and feel
        → Look for: rigidity, professional binding, quality materials
        
        PAPERBACK:
        Indicators:
        - Flexible cover made of card stock or thick paper
        - Perfect binding (glued spine) or saddle stitch
        - Lighter weight than hardcover
        - Cover may be glossy or matte finish
        - Professional commercial printing
        - Mass-market or trade paperback quality
        - Spine shows paper/card construction
        → Look for: flexibility, commercial quality, standard binding
        
        FOTOKOPI (Photocopy/Reproduction):
        Indicators:
        - Lower print quality (uneven ink density, copy artifacts)
        - Simple binding (stapled, comb-bound, thermal-bound)
        - Basic paper quality (often plain copier paper)
        - No professional cover design
        - May show copy machine artifacts (edge marks, alignment issues)
        - Binding typically minimal or improvised
        - Text may show characteristic photocopy appearance
        → Look for: copy artifacts, simple binding, basic materials
        
        AMBIGUOUS CASES:
        - High-quality print-on-demand: May look like paperback
        - Professionally reproduced academic works: Check for binding quality
        - Damaged hardcovers: Original structure may be visible
        - Rebound books: Check for signs of rebinding
        
        ANALYSIS REQUIRED:
        - What cover material do you observe?
        - What type of binding is present?
        - What production quality indicators are visible?
        - Does it match commercial printing standards?
        - Are there photocopy or reproduction indicators?
        
        Document in 'printTypeAnalysis' field.

        ---

        STEP 4: FINAL CLASSIFICATION
        
        Make final classification decisions:
        
        CONDITION:
        Based on your conditionAnalysis, select the most appropriate BookCondition enum:
        - Review all observed damage
        - Compare with condition criteria
        - Consider preservation urgency
        - Make final classification
        → Must align with your documented reasoning
        
        PRINTTYPE:
        Based on your printTypeAnalysis, select the most appropriate BookPrintType enum:
        - Review cover and binding observations
        - Compare with print type criteria
        - Consider production quality indicators
        - Make final classification
        → Must align with your documented reasoning

        ---

        CRITICAL GUIDELINES:
        
        ✓ Examine each image systematically and thoroughly
        ✓ Document all physical observations objectively
        ✓ Rate severity accurately using the provided scale
        ✓ Assess readability impact for preservation planning
        ✓ Compare observations across all images for consistency
        ✓ Use condition criteria strictly - don't over- or under-classify
        ✓ Distinguish between age-related wear and damage
        ✓ Consider both aesthetic and functional condition
        ✓ For print type, look for specific construction indicators
        ✓ Don't confuse poor condition with photocopy indicators
        ✓ Be conservative in classification when borderline
        ✓ Document reasoning clearly for quality control
        ✓ The final JSON may include comments explaining your reasoning
        ✓ It's ok if the JSON isn't fully valid initially, we will clean it afterwards
        ✓ Write a codeblock ONLY for the final JSON data containing your analysis
        
        {{ ctx.output_format }}

        {{ _.role("user") }}
        
        BOOK IMAGES FOR CONDITION ASSESSMENT:
        {% for image in MultiImages %}
        Image {{loop.index}} of {{total_images}}: {{image}}
        {% endfor %}
        
        Please assess Book ID {{bookId}} following the 4-step workflow above. Conduct a thorough physical examination, synthesize your observations into condition and print type analyses, then provide final classifications with clear reasoning.
        
        Remember: Your assessment will guide preservation decisions. Be thorough, objective, and precise.
    "#
}