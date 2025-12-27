class RawAnalysis {
    coverPageDescription string @description(#"
        A complete list of all readable text and  detailed visual analysis of the cover page of the book from the given set of the images, including texts that are present on the cover page, including but not limited to the book's title, author(s), publisher, edition, and any other relevant information that can be found on the cover page.
    "#)
    backCoverDescription string @description(#"
        A complete list of all readable text and detailed visual analysis of the back cover page of the book from the given set of the images, including texts that are present on the back cover page, including but not limited to the book's summary, author biography, publisher information, ISBN number and any other relevant information that can be found on the back cover page.
    "#)
    colophonPageDescription string @description(#"
        A complete list of all readable text and detailed visual analysis of the colophon page of the book from the given set of the images, including texts that are present on the colophon page, including but not limited to the book's publication details, printing history, edition information, and any other relevant information that can be found on the colophon page.
    "#)
    otherPageDescriptions string? @description(#"
        A complete list of all readable text and detailed visual analysis of the other pages of the book from the given set of the images, including texts that are present on the other pages, including but not limited to the book's alternative titles, forewords, prefaces, introductions, appendices, indexes, and any other relevant information that can be found on the other pages.
    "#)
    }

function GetBookrawVisual(MultiImages: image[], bookId: string) -> RawAnalysis {
    client "Gemini20FlashLite"
    prompt #"
        You are an expert librarian, and archivist. Your daily tasks is cataloging books, based on photos gathered by the field workers that visits libraries across the country. Your job in the team is to process the initial photos, and jot down in extreme detail, what each photo shows. This will be useful for other team members that will come after you, as they might not have access to the books directly or its photos, and therefore will rely on your detailed description to understand and catalogue the book.

        You will receive 2 or more photos of a book. Each photo shows different parts of the book. Some books might have varying intactness. Some books might have damaged pages. Some books, might also have unusual layouts, or special pages. Some photos shows the front cover, some shows the back cover, some shows the colophon page, and some shows other pages. All photos are guaranteed to be of the same book, and is captured by the field team to gather as much information as possible about the book from the fieldwork.

        You will analyze ALL images together to get the most complete and accurate information. Please write down any detail present on each part of the book shown in the photos. You should write down your analysis in the same format as the following example: 
        
        " This is a photo image number 1, it shows the front cover of the book. The cover has a blue background with an illustration of a tree in the center. The title of the book is "The Great Adventure" written in bold white letters at the top. The author's name, John Doe, is written in smaller white letters at the bottom. There is also a publisher's logo in the bottom right corner. " . 
        
        Please do this for each part of the book shown in the photos. Prioritize the analysis of the front cover, back cover, and colophon page. If any of these types of pages are not present, please note the absence in your analysis. In the case where you don't find another type of page, please also mention briefly your guess on what kind of page it might be, based on your analysis of the photo.
        
        After your thorough analysis, please relay the result of your analysis and extraction in the form of a JSON data, for each of the images you received. However, It's ok if this isn't fully valid JSON, we will fix it afterwards and remove the comments. But, please note that you should write a codeblock ONLY for the final JSON data containing only your analysis.

        {{ ctx.output_format }}

        {{ _.role("user") }}
        { _.role("user") }}

        Hi, the team at field have gathered the photos of this book, with the ID of {{bookId}}. Please analyze these book cover images and extract descriptive information about the book from the images.

        {% for image in MultiImages %}
        The image number {{loop.index}} is this image: {{image}}
        {% endfor %}
        
        Extract comprehensive book data from all {{MultiImages|length}} images.
    "#
}