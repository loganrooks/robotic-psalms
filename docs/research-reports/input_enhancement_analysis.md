# Analysis Report: User Input Enhancement Options

**Date:** 2025-04-13
**Author:** Architect Mode

## 1. Introduction

This report analyzes two proposed approaches for enhancing user input in the "Robotic Psalms" project, moving beyond the current separate lyrics text files and MIDI files (`midi_path` in `config.yml`). The goal is to provide more user-friendly and integrated methods for specifying musical and lyrical content.

The two primary approaches considered are:

1.  **Parsing Standard Music Formats:** Automatically extracting data from PDF sheet music (via Optical Music Recognition - OMR) or structured MusicXML files.
2.  **Custom Domain-Specific Language (DSL):** Designing a text-based language tailored for users to define lyrics, notes, durations, and potentially effects within a single file.

This analysis evaluates the feasibility, complexity, user experience, flexibility, accuracy, implementation effort, and dependencies of each approach to provide a recommendation.

## 2. Analysis of PDF/MusicXML Parsing

This approach leverages existing musical notation standards.

### 2.1. PDF Parsing (Optical Music Recognition - OMR)

*   **Concept:** Use computer vision and potentially machine learning techniques to "read" a PDF image of sheet music and extract notes, rhythms, lyrics, etc.
*   **Research Findings (Python Libraries):**
    *   No single, dominant, mature OMR library readily available for general use in Python was identified through web searches.
    *   Existing projects (e.g., `cadenCV`) often involve significant computer vision code (using libraries like OpenCV) and may be research-oriented or specific to certain notation styles.
    *   Commercial OMR software exists, but integrating it might be complex or costly. Open-source efforts are often complex academic projects.
*   **Accuracy & Limitations:**
    *   OMR accuracy is highly variable and depends heavily on the quality of the scanned PDF, the complexity of the music, and the sophistication of the OMR engine. Handwritten scores are particularly challenging.
    *   Extracting lyrics accurately and associating them correctly with notes adds another layer of complexity and potential error.
    *   Recognizing less common musical symbols or unconventional notation is often problematic.
*   **Implementation Effort:** Very High. Requires deep expertise in computer vision, image processing, and potentially machine learning. Significant development and tuning effort would be needed to achieve reasonable accuracy.
*   **Dependencies:** Heavy (OpenCV, potentially TensorFlow/PyTorch, large datasets for training/tuning).
*   **User Experience:** Potentially high if accurate, as users could use existing PDFs. However, inaccuracy leads to frustration and manual correction, negating the benefit.

### 2.2. MusicXML Parsing

*   **Concept:** Parse MusicXML files, which are a standard XML-based format for representing musical scores in a structured way.
*   **Research Findings (Python Libraries):**
    *   **`music21`**: A comprehensive, mature, and widely recommended Python toolkit for musicology. It has robust MusicXML parsing capabilities, representing the score as a hierarchy of Python objects (scores, parts, measures, notes, rests, lyrics, etc.).
    *   Other libraries exist (`musicxml_parser`, `MuseParse`) but seem less comprehensive or focused on specific outputs (pianoroll, Lilypond).
*   **Accuracy & Limitations:**
    *   Accuracy depends on the correctness and completeness of the source MusicXML file. Well-formed files should parse reliably.
    *   The main challenge is mapping the rich `music21` object structure to the specific inputs required by "Robotic Psalms" (primarily lists of note frequencies in Hz, durations in seconds, and associated lyrics text). This requires understanding both the MusicXML standard and the `music21` API.
    *   MusicXML can represent complex scores; extracting only the necessary information might require careful filtering. Handling different MusicXML versions or software-specific quirks might add complexity.
*   **Implementation Effort:** Moderate. The primary effort lies in learning the `music21` library and developing the logic to traverse the parsed score object and extract the required data (notes, durations, lyrics). The parsing itself is handled by the library.
*   **Dependencies:** Primarily `music21`, which is a substantial library but well-maintained.
*   **User Experience:** Good for users who already have or can easily generate MusicXML files (e.g., from notation software like MuseScore, Sibelius, Finale). Less useful if users primarily have PDFs or handwritten scores.

### 2.3. Data Flow Diagram (PDF/MusicXML)

```mermaid
graph TD
    subgraph Input Phase
        A[User provides PDF/MusicXML file] --> B{Format Check};
    end

    subgraph Parsing Phase
        B -- PDF --> C[OMR Engine (Complex CV/ML)];
        B -- MusicXML --> D[MusicXML Parser (e.g., music21)];
        C --> E{Recognized Music Data (Potentially inaccurate)};
        D --> F[Structured Music Object (e.g., music21 Score)];
    end

    subgraph Mapping Phase
        E --> G[Mapping Logic (Heuristics, Correction?)]
        F --> H[Mapping Logic (Object Traversal)];
        G --> I{Extracted Data (Notes Hz, Durations sec, Lyrics)};
        H --> I;
    end

    subgraph Application Input
        I --> J[Robotic Psalms Synthesis Engine];
    end

    style C fill:#f9d,stroke:#333,stroke-width:2px
    style G fill:#f9d,stroke:#333,stroke-width:2px
    style D fill:#ccf,stroke:#333,stroke-width:2px
    style H fill:#ccf,stroke:#333,stroke-width:2px
```

## 3. Analysis of Custom Domain-Specific Language (DSL)

*   **Concept:** Define a simple, text-based format specifically for "Robotic Psalms" inputs, allowing users to specify lyrics, notes, durations, and potentially effects in one place.
*   **Requirements:**
    *   Associate lyrics syllables/words with specific notes (pitch/frequency).
    *   Define note durations.
    *   Allow specification of rests/silence.
    *   Potentially define sections with specific effects applied.
    *   Be relatively easy for users (potentially non-programmers) to learn and write.
    *   Provide clear error feedback for syntax mistakes.
*   **Syntax Exploration:**
    *   **Markdown-like Inline:** `This is [C4:0.5]a [D4:0.5]psalm [Rest:1.0] with notes.` (Concise but potentially hard to read for complex sequences).
    *   **YAML-based:**
        ```yaml
        - lyric: This
          note: C4
          duration: 0.5
        - lyric: is
        - lyric: a
          note: D4
          duration: 0.5
        - lyric: psalm
        - rest: 1.0
        - lyric: with
          note: E4
          duration: 0.25
        # ...
        ```
        (Structured, readable, parsable with standard YAML libraries, but verbose).
    *   **Custom Line-Based:**
        ```
        LYRIC: This is a psalm
        NOTE: C4 D4 E4
        DURATION: 0.5 0.5 1.0
        ---
        EFFECT: reverb_wet=0.8
        LYRIC: another line
        NOTE: G4 F4
        DURATION: 0.75 1.25
        ```
        (Requires custom parser, balance between simplicity and expressiveness).
    *   **Syllable-Focused:**
        ```
        Psa-[C4:0.5]-lm [D4:1.0] 1.[E4:0.5]
        Glo-[F4:0.4]-ri-[G4:0.6]-a [A4:1.0]
        ```
        (Directly links syllables, potentially intuitive for singers).
*   **Parser Implementation:**
    *   Simple regex might suffice for very basic syntax but quickly becomes brittle and hard to maintain.
    *   Using established parsing libraries like `lark-parser` or `pyparsing` is recommended. This involves defining a formal grammar (EBNF for Lark) and writing code to traverse the parse tree and extract data.
    *   Effort is moderate: designing a good grammar and implementing the tree traversal logic. Error reporting needs careful consideration.
*   **Flexibility vs. Ease of Use:**
    *   A DSL offers maximum flexibility to tailor the input format precisely to the project's needs, including custom effects or notations not present in standard formats.
    *   Requires users to learn a new syntax. The learning curve depends heavily on the chosen syntax's simplicity and clarity. Good documentation and examples are crucial.
*   **Implementation Effort:** Moderate. Involves designing the grammar, implementing the parser (using a library is recommended), and writing the logic to convert parsed data into application inputs.
*   **Dependencies:** A parsing library (e.g., `lark-parser`, `pyparsing`) or potentially just standard Python (`re`, `yaml`). Relatively lightweight compared to OMR.

### 3.1. Data Flow Diagram (DSL)

```mermaid
graph TD
    subgraph Input Phase
        A[User creates/edits DSL text file] --> B[DSL File (.rpsalm? .txt?)];
    end

    subgraph Parsing Phase
        B --> C[DSL Parser (e.g., Lark/Pyparsing)];
        C --> D{Parse Tree / Structured Data};
    end

    subgraph Mapping Phase
        D --> E[Mapping Logic (Tree Traversal)];
        E --> F{Extracted Data (Notes Hz, Durations sec, Lyrics, Effects?)};
    end

    subgraph Application Input
        F --> G[Robotic Psalms Synthesis Engine];
    end

    style C fill:#cfc,stroke:#333,stroke-width:2px
    style E fill:#cfc,stroke:#333,stroke-width:2px
```

## 4. Comparison

| Feature               | PDF Parsing (OMR)                     | MusicXML Parsing                      | Custom DSL                            |
| :-------------------- | :------------------------------------ | :------------------------------------ | :------------------------------------ |
| **User Experience**   | Potentially easy (use existing PDFs) BUT highly prone to frustrating errors. | Good if users have MusicXML source. Requires specific software/workflow. | Requires learning new syntax. Can be intuitive if well-designed. Direct control. |
| **Flexibility**       | Low-Moderate (Limited by OMR capabilities & standard notation). | Moderate-High (Standard format, rich representation). Custom effects harder. | High (Tailored exactly to project needs, including effects). |
| **Accuracy/Robustness**| Low (Highly sensitive to input quality, complex recognition task). | High (If source MusicXML is valid and well-formed). | Moderate (Prone to user syntax errors, needs good parser/validation). |
| **Implementation Effort**| Very High (Complex CV/ML, tuning). | Moderate (Learning `music21`, mapping logic). | Moderate (Grammar design, parser implementation using library). |
| **Dependencies**      | Heavy (OpenCV, ML libs?).             | Moderate (`music21` toolkit).         | Low-Moderate (Parsing lib like `lark` or just `re`/`yaml`). |
| **Source Availability**| PDFs common, but quality varies.      | Less common than PDF, requires specific tools. | User must create/learn.             |

## 5. Recommendation

Based on the analysis, the **Custom DSL approach is recommended** as the primary focus for enhancing user input at this stage.

**Justification:**

1.  **Control & Flexibility:** A DSL provides the most direct control over the input required by "Robotic Psalms," including potential future extensions for specific effects or synthesis parameters not easily represented in standard notation.
2.  **Implementation Feasibility:** While requiring effort in grammar design and parser implementation (using libraries like `lark-parser` is strongly advised), it appears significantly less complex and resource-intensive than building a reliable OMR system. The complexity seems comparable to, or potentially less than, deeply integrating and mapping data from `music21`.
3.  **Reduced Dependencies:** Compared to OMR, the DSL approach has much lighter dependencies. Compared to MusicXML, it avoids relying on the large `music21` toolkit, keeping the project's dependency footprint smaller.
4.  **User Focus:** While requiring learning, a well-designed DSL can be made intuitive, especially if focused on the core task (lyrics + notes + durations). It empowers users to specify exactly what they want the system to produce.
5.  **Iterative Development:** A DSL can start simple (lyrics, basic notes/durations) and be extended incrementally to support more complex features (effects, rests, dynamics) as needed.

**Secondary Recommendation:** Consider adding **MusicXML parsing using `music21` as a secondary input method** *after* the DSL is established. This caters to users who already work with notation software and provides an alternative workflow. OMR from PDF is deemed too complex and unreliable for the current project scope.

## 6. High-Level Considerations for DSL Approach

*   **Syntax Design:** Crucial for usability. Needs careful thought. A syllable-focused or YAML-like structure might be good starting points. Prioritize clarity and ease of writing.
*   **Parser Choice:** Use a robust parsing library (`lark-parser` recommended for its EBNF grammar and ease of use). Avoid relying solely on regex.
*   **Error Reporting:** The parser must provide clear, user-friendly error messages indicating the location and nature of syntax errors.
*   **Documentation:** Excellent documentation with clear examples will be essential for user adoption.
*   **Tooling (Future):** Consider simple validation tools or even basic syntax highlighting support (e.g., via VS Code extensions) to improve the user experience further down the line.
*   **Integration:** The parser needs to output data in a format easily consumable by the existing `SacredMachineryEngine` (likely similar to the data currently derived from `config.yml` and `midi_parser.py`).

## 7. Memory Bank Update

This analysis and recommendation should be recorded in the Architect's specific memory and potentially referenced in the global context's decision log.