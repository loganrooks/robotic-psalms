# **Independent Formant Shifting with Pitch Preservation in Python: Analysis and Implementation Strategies**

## **I. Introduction**

This report addresses the challenge of modifying the formant frequencies of a speech signal independently of its fundamental frequency (F0) within a Python environment. Formant frequencies, resonant peaks in the speech spectrum determined by the vocal tract configuration, are primary correlates of perceived timbre and vowel identity.1 Fundamental frequency, the rate of vocal fold vibration, corresponds primarily to perceived pitch. The objective is to alter the timbre, simulating changes in vocal tract characteristics, without affecting the perceived pitch of the speech signal. This capability is valuable in applications such as speech synthesis, voice transformation, and audio effects.

The user initiating this query is engaged in a speech synthesis project and requires a method to shift formants while preserving pitch. Previous attempts leveraging librosa with the pyrubberband backend, librosa's internal time-stretching and pitch-shifting functions, and the parselmouth wrapper for Praat's Change gender command have yielded unsatisfactory results or encountered errors.

This report provides an expert analysis of techniques suitable for achieving independent formant shifting with pitch preservation in Python. It begins by explaining the fundamental relationship between pitch and formants and the inherent coupling challenges in naive signal processing approaches. Subsequently, it evaluates the methods previously attempted by the user, diagnosing the reasons for their failure and exploring correct usage where applicable. The report then investigates robust alternative methods, including enhancements to the phase vocoder, source-filter modeling techniques like Linear Predictive Coding (LPC), and the capabilities of high-quality vocoders such as WORLD. A comparative analysis of these methods follows, evaluating them based on criteria including potential quality, ease of implementation, computational requirements, and suitability for real-time processing. Finally, actionable recommendations and implementation guidance are provided for the most promising approaches within the Python ecosystem.

## **II. Fundamentals: Pitch, Formants, and Their Coupling**

Understanding the distinction between pitch and formants, and why they are often inadvertently linked in simple audio processing, is crucial for developing effective decoupling strategies.

**Pitch (F0):** The perception of pitch in voiced speech is primarily determined by the fundamental frequency (F0) of the glottal source signal, which corresponds to the rate at which the vocal folds vibrate. This vibration produces a quasi-periodic waveform rich in harmonics (integer multiples of F0).

**Formants:** Formants are peaks in the spectral envelope of the speech signal.1 These peaks arise from the acoustic resonances of the vocal tract (including the pharynx, oral cavity, and nasal cavity). The shape and size of these cavities filter the glottal source signal, amplifying energy at formant frequencies and attenuating it elsewhere. The frequencies of the first few formants (F1, F2, F3, etc.) are particularly important for distinguishing different vowels and contribute significantly to the perceived timbre or quality of a voice.

**The Coupling Problem:** In many basic signal processing operations, pitch and formants are inherently coupled. A simple illustration is changing the playback speed of a recording.3 If an audio signal is played back faster, its duration decreases, and all frequency components are scaled upwards proportionally. This increases the F0 (higher pitch) but also shifts the formant frequencies higher, leading to the unnatural "chipmunk effect". Conversely, slowing playback lowers both pitch and formants.1 This coupling occurs because both the harmonic structure related to F0 and the formant peaks related to the vocal tract resonance exist within the same frequency spectrum.

* **Time-Domain Scaling / Resampling:** The most basic form of pitch shifting involves resampling the digital audio signal. This operation effectively stretches or compresses the time axis, which inversely compresses or stretches the frequency axis. Since all frequencies are scaled by the same factor, the ratio between harmonics (determining timbre) is preserved, but both the fundamental frequency (pitch) and the absolute frequencies of the formant peaks are shifted.3  
* **Standard Phase Vocoder:** The phase vocoder is a common technique for time-stretching and pitch-shifting that operates in the frequency domain.3 It analyzes the signal using the Short-Time Fourier Transform (STFT), breaking it into overlapping time frames. For time-stretching, it manipulates the phase difference between frames to synthesize a longer or shorter signal while attempting to preserve the original frequency content. For pitch-shifting, it typically involves time-stretching followed by resampling, or directly manipulating the frequency components within each STFT frame (e.g., by resampling the spectral data or adjusting frequency estimates) before inverse STFT and overlap-add synthesis.4 In standard implementations, this frequency scaling shifts the entire spectrum, including both the harmonics (changing F0) and the spectral envelope peaks (changing formants).3 While phase locking can improve the quality of transients 6, the fundamental coupling remains unless specific modifications are made.

The core challenge arises because the spectrum represents both F0 (via harmonic spacing) and formants (via envelope peaks). Naive spectral scaling affects both simultaneously. Achieving independent control requires methods that can conceptually or algorithmically separate the source (pitch) characteristics from the filter (formant) characteristics. Techniques aiming for formant preservation during pitch shifting tackle one aspect of this decoupling 2; the user's goal requires the complementary capability – shifting formants while preserving pitch. This necessitates methods that explicitly model or manipulate the spectral envelope independently from the underlying harmonic structure or F0.

## **III. Evaluation of User's Attempted Methods**

The user explored three distinct approaches, each encountering issues. Analyzing these attempts reveals common pitfalls and clarifies the limitations of standard library functions for the specific task of independent formant shifting.

### **A. rubberband (pyrubberband/rubberband-cli)**

Rubber Band is a well-regarded library for high-quality time-stretching and pitch-shifting, available as a C++ library and a command-line utility.10

* **Functionality and Formant Preservation:** The library's core function is to modify tempo and pitch independently.11 The command-line interface (CLI) provides a \-F or \--formant flag.11 Critically, this flag enables *formant preservation* during pitch shifting.11 Its purpose is to maintain the original vocal timbre by preventing the spectral envelope from scaling along with the fundamental frequency, thus avoiding the "chipmunk effect".11 It does *not* provide a mechanism for applying an arbitrary, independent formant scaling factor via the CLI.  
* **Independent Formant Scaling via C++ API:** Deeper investigation reveals that the underlying C++ class, RubberBandStretcher, *does* possess a method setFormantScale(double scale).14 This method explicitly allows setting a formant scaling ratio independent of the pitch scale, intended for special effects rather than standard formant preservation.14 This functionality requires the more computationally intensive R3 engine (OptionEngineFiner) and is not available in the older R2 engine (OptionEngineFaster).14  
* **Python Wrappers and User Failure:**  
  * The user attempted to use pyrubberband by passing \--formant \<factor\> and \--pitch 0 via rbargs. This failed for two key reasons. Firstly, the CLI syntax is simply \-F (a boolean flag), not \--formant \<factor\>; any provided factor was likely ignored.11 Secondly, the conceptual application was incorrect. The \-F flag aims to counteract the formant shift that *normally occurs during pitch shifting*. When combined with \--pitch 0 (which correctly specifies no pitch shift 11), the \-F flag effectively instructs the algorithm to maintain the formants at their original positions relative to the (unchanged) pitch. The net result is no change to the audio signal, consistent with the user's observation. The CLI flag is not designed for the user's goal of *applying* an independent formant shift.  
  * Existing Python wrappers like pyrubberband 15 and the native extension rubberband 16 do not appear to expose the setFormantScale C++ method directly. The rubberband extension's formants=False argument likely controls the standard preservation flag.16  
* **Correct Usage for Independent Shift:** Achieving the desired independent formant scaling using Rubberband would necessitate either using the C++ API directly or employing a Python wrapper that specifically binds the setFormantScale method and allows selection of the R3 engine. Standard CLI usage or existing common Python wrappers seem insufficient. No specific bugs related to the \-F flag were identified in the reviewed materials 17, confirming the issue lies in the flag's intended purpose versus the user's requirement.

### **B. librosa**

librosa is a cornerstone library for audio analysis and feature extraction in Python.19 While powerful, its built-in effects have limitations regarding formant manipulation.

* **time\_stretch \+ pitch\_shift Failure:** The user's attempt to combine librosa.effects.time\_stretch and librosa.effects.pitch\_shift failed to preserve pitch because librosa.effects.pitch\_shift itself relies on a standard phase vocoder implementation.20 As established previously, basic phase vocoder pitch shifting inherently scales both the fundamental frequency and the formant frequencies together.3 Applying time stretching beforehand modifies the signal's duration but does not alter the subsequent pitch shifter's behavior concerning formant coupling. The result is that formants are shifted along with the pitch.  
* **Parameter Tuning:** The pitch\_shift function accepts additional keyword arguments (\*\*kwargs) that are passed to the underlying STFT function (librosa.decompose.stft).20 Parameters like n\_fft, hop\_length, and window type influence the resolution and quality of the STFT analysis and subsequent phase vocoder processing. However, tuning these parameters cannot decouple the pitch and formant shifting inherent in the algorithm itself. The metallic artifacts sometimes associated with phase vocoder pitch shifting ("phasiness") can be related to phase inconsistencies introduced during processing, which STFT parameters might subtly affect, but the formant coupling issue is fundamental to the spectral scaling operation.23  
* **Built-in Capabilities:** librosa does not provide a dedicated function for independent formant shifting while preserving pitch. Its documentation for pitch\_shift points towards pyrubberband for higher-quality pitch shifting, implicitly acknowledging the limitations of its own simpler implementation.20 librosa excels at providing building blocks (STFT, feature extraction, etc.) that could be used to *implement* more advanced techniques, but does not offer this specific transformation out-of-the-box.

### **C. parselmouth/Praat**

parselmouth provides Python bindings for the Praat speech analysis software 24, allowing access to Praat's extensive functionality via Python code.

* **Change gender Command:** This Praat command is explicitly designed for modifying vocal characteristics by adjusting formants and pitch.27 It typically uses a combination of resampling (to shift formants) and Pitch-Synchronous Overlap-Add (PSOLA) (to adjust pitch and duration while attempting to preserve the *new* formant structure).28 It accepts parameters for Formant shift ratio, New pitch median, Pitch range factor, and Duration factor.28  
* **Resolving the PraatError:** The user encountered PraatError: Argument "Pitch ceiling" must be greater than 0.. This error arises because the Change gender command performs an internal pitch analysis on the input sound to determine its original pitch characteristics (median and range), which are needed to correctly apply the New pitch median and Pitch range factor modifications.28 This internal analysis requires valid Pitch floor and Pitch ceiling parameters to function correctly; these define the frequency range searched for pitch candidates.28 Passing a value of 0 or invalid ranges for these parameters via parselmouth.praat.call causes this internal analysis step to fail, triggering the error.  
  * **Solution 1 (Direct Parameters):** Provide sensible, non-zero values for these analysis parameters when calling the function. Typical values for human speech are a floor of 75 Hz and a ceiling of 600 Hz.28 The parselmouth.praat.call syntax would be:  
    Python  
    \# Example: Shift formants up by 10%, keep pitch/duration same  
    formant\_ratio \= 1.1  
    new\_median \= 0.0  \# 0.0 means use original median  
    pitch\_range\_factor \= 1.0 \# 1.0 means keep original range relative to median  
    duration\_factor \= 1.0  
    pitch\_floor \= 75  
    pitch\_ceiling \= 600  
    modified\_sound \= parselmouth.praat.call(  
        sound, "Change gender",  
        pitch\_floor, pitch\_ceiling, \# Pitch analysis parameters  
        formant\_ratio, new\_median, pitch\_range\_factor, duration\_factor  
    )

  * **Solution 2 (External Pitch Object \- Recommended):** A more robust approach, particularly if Praat's internal pitch analysis struggles with the audio (which can cause hangs or errors 30), is to compute a Praat Pitch object explicitly beforehand and pass it along with the Sound object. This bypasses the command's internal pitch analysis.30 The call syntax changes, omitting the floor and ceiling arguments:  
    Python  
    \# Example: Shift formants up by 10%, keep pitch/duration same  
    formant\_ratio \= 1.1  
    new\_median \= 0.0  
    pitch\_range\_factor \= 1.0  
    duration\_factor \= 1.0  
    \# Calculate Pitch object first (adjust parameters as needed)  
    \# Time step matching internal Praat default: 0.8 / pitch\_floor \[30\]  
    pitch \= sound.to\_pitch(time\_step=0.8 / 75, pitch\_floor=75, pitch\_ceiling=600)  
    modified\_sound \= parselmouth.praat.call(  
        (sound, pitch), "Change gender", \# Pass both objects  
        formant\_ratio, new\_median, pitch\_range\_factor, duration\_factor  
    )

* **Formant-Only Shift Parameters:** To achieve formant shifting *without* altering pitch using Change gender, set new\_pitch\_median to 0.0 (which instructs Praat to use the original median pitch) and pitch\_range\_factor to 1.0 (which maintains the original pitch variation relative to the median).28 Set the desired formant\_shift\_ratio (e.g., 1.1 or 1.2 for male-to-female approximation, 1/1.1 or 0.83 for female-to-male 27). Keep duration\_factor at 1.0.  
* **Alternative Praat Functions:**  
  * **Manipulation Object:** Praat's Manipulation object allows fine-grained control over pitch and duration tiers.32 However, direct manipulation of formants via this object is not straightforward using parselmouth.praat.call, and Parselmouth currently lacks a dedicated Python Manipulation class wrapper.34 While pitch can be modified by extracting, manipulating, and replacing the PitchTier 33, a similar direct path for formants is not readily available.35  
  * **External Scripts/Plugins:** The "Praat Vocal Toolkit" plugin provides a Change formants... command 35 that might offer more control. This could potentially be executed via parselmouth.praat.run\_file 35, but requires the plugin to be installed within the Praat application accessible to Parselmouth, and some users have reported quality concerns.35 Other custom Praat scripts for formant manipulation also exist.39  
  * **Shift frequencies:** This command performs a linear frequency shift 40, adding a constant offset to all frequencies. This is fundamentally different from formant shifting (which involves scaling or warping) and will severely distort the harmonic relationships and timbre of speech.  
* **Limitations:** The quality of Change gender is limited by the underlying PSOLA algorithm, which can introduce audible artifacts ("glitches"), especially for large modification factors or non-monophonic signals.41 The quality may not match specialized commercial pitch/formant manipulation tools.41

## **IV. Alternative Python Libraries and DSP Techniques**

Beyond the user's initial attempts, several other Python libraries and DSP techniques offer potential solutions for independent formant and pitch control.

### **A. Phase Vocoder Enhancements (Spectral Envelope Separation)**

Standard phase vocoders couple pitch and formant shifts. Enhanced approaches address this by separating the signal processing applied to the fine spectral structure (harmonics related to pitch) and the coarse spectral envelope (related to formants).

* **Concept:** The core idea is to decompose each STFT frame into two components: a spectral envelope representing the vocal tract resonances (formants), and a residual or excitation signal representing the source (pitch information).4 Pitch shifting is then applied *only* to the residual component. The modified residual is subsequently recombined with the spectral envelope, which can be either the original envelope (for formant preservation) or a *modified* envelope (for independent formant shifting).43  
* **Envelope Estimation:** Common methods for estimating the spectral envelope include Cepstral analysis (often involving "liftering," which is low-pass filtering in the cepstral domain) 43 or Linear Predictive Coding (LPC).43  
* **Implementation Workflow (for Formant Shift):**  
  1. Compute STFT of the input signal.  
  2. For each frame: a. Estimate the spectral envelope (e.g., via cepstrum or LPC). b. Compute the residual spectrum by dividing the original spectrum by the envelope (spectral whitening).4 c. **Warp the spectral envelope:** Apply the desired formant shift by warping the frequency axis of the estimated envelope (e.g., using interpolation). d. Keep the residual spectrum unchanged (as pitch is preserved). e. Recombine: Multiply the original residual spectrum by the *warped* spectral envelope.  
  3. Compute inverse STFT (ISTFT) and perform overlap-add synthesis.  
* **stftPitchShift Library:**  
  * This Python library implements a phase vocoder approach with formant preservation capabilities.45 It uses cepstral liftering to estimate and separate the spectral envelope.45  
  * It provides a Python class StftPitchShift and a command-line tool.45 The primary function shiftpitch takes pitch shifting factors as input.45  
  * Formant *preservation* is enabled using the quefrency parameter (or \-q CLI flag), which controls the cutoff for the cepstral lifter.45  
  * While its public API is geared towards pitch shifting with optional formant preservation, the underlying mechanism of envelope separation is present. To achieve independent formant *shifting* (preserving original pitch), one would conceptually need to: (1) Extract the spectral envelope using the library's Cepster module.45 (2) Warp this envelope in the frequency domain using standard NumPy/SciPy interpolation functions (e.g., numpy.interp) according to the desired formant shift factor. (3) Use the library's Vocoder module 45 to encode the original signal (obtaining magnitude and frequency estimates without pitch shift), potentially separate the envelope influence, apply the *warped* envelope, and then decode back to complex STFT representation for synthesis via the STFT module.45 This likely requires using the library's components at a lower level than the main shiftpitch function or potentially modifying the library's internal logic.  
* **pvc Library:** This is another Python phase vocoder implementation found on GitHub that explicitly mentions optional formant correction.48 It might employ similar envelope separation techniques and could be another avenue for investigation, although less documentation was available in the provided materials compared to stftPitchShift.

### **B. Source-Filter Modeling (LPC & Cepstral)**

Source-filter models represent speech production as a source signal (glottal excitation) passed through a filter (vocal tract). Manipulating the filter parameters allows for formant modification.

* **LPC (Linear Predictive Coding):**  
  * **Concept:** LPC models the vocal tract filter as an all-pole digital filter. The coefficients of this filter are estimated from the speech signal. The poles of this filter's transfer function correspond to the resonant frequencies of the vocal tract, i.e., the formants.49 Specifically, formants correspond to complex conjugate pole pairs within the unit circle in the z-plane. Shifting formant frequencies involves modifying the *angles* of these poles; modifying the *magnitudes* (distance from the origin) affects the formant bandwidths.49 To resynthesize speech with shifted formants but original pitch, the original excitation signal (estimated as the LPC residual, or synthesized from the F0 contour) is passed through the *modified* LPC filter.51  
  * **Workflow:**  
    1. Segment the input signal into frames.  
    2. For each frame: a. Apply a window function (e.g., Hamming). b. Optionally apply pre-emphasis (e.g., using scipy.signal.lfilter 53). c. Compute the autocorrelation of the windowed frame.54 d. Compute LPC coefficients from the autocorrelation using the Levinson-Durbin algorithm.54 The order p is typically chosen based on the sampling rate and expected number of formants (e.g., 2 \+ fs / 1000 50). e. Find the roots of the LPC polynomial A(z) (these are the poles of the synthesis filter 1/A(z)) using numpy.roots.50 f. Filter the roots to keep only those inside/near the unit circle and with positive imaginary parts (representing formants).53 g. Modify the angles of the selected poles: new\_angle \= old\_angle \* formant\_shift\_factor. Keep the magnitudes the same to preserve bandwidths.51 Reconstruct the complex conjugate pairs. h. Compute the new LPC polynomial coefficients from the set of modified poles using numpy.poly. Ensure stability (all poles inside unit circle). i. Estimate the excitation signal for the frame (either the LPC residual from the original analysis or an impulse train generated from the F0 estimate). j. Synthesize the output frame by filtering the excitation signal with the *new* LPC filter coefficients (using scipy.signal.lfilter).  
    3. Overlap-add the synthesized frames to reconstruct the output signal.  
  * **Python Libraries:**  
    * pysptk: Provides functions for LPC analysis (pysptk.sptk.lpc 56), conversions between representations (e.g., lpc2lsp 56), pitch estimation (swipe, rapt 56), excitation generation (excite 57), and synthesis filters (e.g., MLSADF, LMADF based on cepstral coefficients 57). While it contains many necessary building blocks, the core pole manipulation logic (root finding, angle modification, polynomial reconstruction from modified roots) would need to be implemented separately using NumPy/SciPy.58  
    * audiolazy: Offers LPC analysis via audiolazy.lpc with multiple algorithms (including Levinson-Durbin).55 It represents filters as ZFilter objects and includes methods for finding poles and zeros (.poles, .zeros properties, requiring NumPy).55 This might provide a more integrated framework for manipulating the filter representation.  
    * Other Resources: Several GitHub repositories and examples demonstrate LPC concepts or implementations in Python.49 clpcnet 60 represents a more advanced deep learning approach based on LPCNet, offering controllable pitch shifting and time stretching, but is likely more complex than traditional DSP methods.  
  * LPC offers a theoretically direct path to formant manipulation via pole modification. However, the implementation requires careful handling of several DSP steps, including robust analysis, root-finding, ensuring stability after pole modification, and reconstructing the filter coefficients accurately. Energy normalization between frames might also be needed to avoid discontinuities.51  
* **Cepstral Methods:**  
  * **Concept:** The cepstrum transforms the log power spectrum, effectively separating the slowly varying component (spectral envelope/formants) from the rapidly varying component (excitation/pitch harmonics) into different "quefrency" regions. Applying a low-pass filter ("lifter") in the cepstral domain isolates the envelope component.43 Formant shifting could theoretically be achieved by warping this isolated envelope in the frequency domain (after transforming back from cepstrum) and then recombining it with the original excitation information.  
  * **pysptk:** This library is particularly strong in cepstral processing, offering functions for Mel-cepstrum (mcep), Mel-generalized cepstrum (mgcep), and related conversions and synthesis filters (MLSA, MGLSA).56 While directly manipulating cepstral coefficients can alter the spectral envelope, achieving a precise, targeted formant shift requires understanding the complex mapping between cepstral coefficients and formant frequencies. A potentially more feasible approach within pysptk would be to: (1) Analyze frames to get Mel-generalized cepstral coefficients (mgcep). (2) Convert these to the spectral envelope using mgc2sp.57 (3) Warp this spectral envelope in the frequency domain using numpy.interp. (4) Potentially convert the warped envelope back to modified cepstral coefficients (if required by the synthesis filter) or use a synthesis method that directly accepts the spectral envelope. (5) Synthesize using the original excitation (pysptk.excite based on original pitch) and the modified filter representation.

### **C. High-Quality Vocoders (WORLD)**

WORLD is a popular open-source vocoder known for its high-quality speech analysis and synthesis.63

* **Concept:** WORLD decomposes the speech signal into three key parameters: the F0 contour (pitch), the smoothed spectral envelope (SP, representing formants/timbre), and an aperiodicity envelope (AP, representing noise components).63 Synthesis reconstructs the speech from these parameters.  
* **Formant Shifting Potential:** The explicit separation of F0 and SP makes WORLD highly suitable for independent formant shifting. The strategy involves:  
  1. Analyzing the input speech using WORLD to extract F0, SP, and AP.  
  2. Keeping the original F0 and AP parameters unchanged.  
  3. Modifying the spectral envelope parameter (SP) by warping its frequency axis according to the desired formant shift factor.  
  4. Synthesizing the output speech using the original F0, original AP, and the *modified* SP.  
* **pyworldvocoder:** This Python library provides a wrapper around the C++ WORLD implementation.63 It exposes the necessary functions for analysis (pw.dio, pw.stonemask, pw.cheaptrick, pw.d4c, or the combined pw.wav2world) and synthesis (pw.synthesize).64  
* **Implementation Challenge:** The primary task is implementing the frequency warping of the spectral envelope (SP). The sp output from pyworld is typically a 2D NumPy array where each row corresponds to a time frame and each column represents a frequency bin of the smoothed spectral envelope. The warping needs to be applied frame by frame (or to the entire array along the frequency axis). This involves:  
  1. Defining the original frequency axis corresponding to the columns of sp. The number of columns relates to the FFT size used internally by pw.cheaptrick.  
  2. Defining the target (warped) frequency axis based on the formant\_shift\_factor.  
  3. For each time frame (row in sp), use an interpolation function like numpy.interp to find the spectral envelope values at the *original* frequency points based on the values along the *warped* frequency axis.  
  4. Construct the new sp\_warped array with the interpolated values.  
* WORLD offers a very promising route due to its high analysis/synthesis quality and explicit source-filter separation. The main implementation effort lies in correctly performing the frequency-axis warping on the sp data structure using NumPy/SciPy.

### **D. Other Libraries**

Some other libraries mentioned in the research snippets are less directly applicable:

* **ProMo:** Focuses on morphing pitch and duration contours between utterances, relying on Praat for the underlying resynthesis. It does not offer independent formant control.66  
* **PyTSMod:** A library for Time-Scale Modification algorithms. While it includes TD-PSOLA which can preserve formants during pitch shift, it's not designed for applying independent formant shifts.42  
* **CLEESE:** An IRCAM tool for generating variations (including pitch shift and time stretch) using phase vocoder methods, seemingly for perceptual experiments.67 Not a general-purpose formant shifting library.

## **V. Comparative Analysis of Methods**

Choosing the best method depends on balancing factors like desired audio quality, implementation complexity, real-time requirements, and dependencies. The following table compares the most viable approaches identified:

| Feature | rubberband (R3+API) | parselmouth/Praat (Change gender) | stftPitchShift (Adapted) | LPC (Custom Pole Mod.) | pyworldvocoder (Custom SP Warp) |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **Formant Shift Quality** | Potentially Good (R3 Engine) | Moderate (PSOLA limitations) | Potentially Good (Cepstral) | Variable (Model Order) | Potentially High (WORLD) |
| **Pitch Preservation** | High (Designed for it) | High (PSOLA based) | High (Phase Vocoder based) | High (Excitation Reuse) | High (Explicit F0 Separation) |
| **Common Artifacts** | Phasey (PV nature) | Glitches, Pulsiness (PSOLA) | Phasey, Transients (PV) | Depends on Stability | Potentially Few (High Quality) |
| **Underlying Technique** | Phase Vocoder (R3) | Resampling \+ PSOLA | PV \+ Cepstral Envelope | LPC Analysis/Synthesis | WORLD Analysis/Synthesis |
| **Ease of Python Impl.** | Difficult (Wrapper needed) | Moderate (Parselmouth API) | Moderate (Library adaptation) | Difficult (Requires DSP) | Difficult (SP Warping Logic) |
| **Key Dependencies** | librubberband (C++) | Praat Binary, parselmouth | Python \+ NumPy/SciPy | NumPy/SciPy | pyworld, NumPy/SciPy, C++ |
| **numpy/soundfile Integ.** | Good (via wrappers) | Moderate (via Parselmouth objects) | Good | Excellent | Good |
| **Real-time Potential** | Yes (R3 engine) | No (Praat process call) | Yes (STFT based) | Possible (Frame-based) | Yes (WORLD designed for RT) |
| **Formant Control Granularity** | Uniform Scale Factor (API) | Uniform Ratio (Command) | Uniform (via Envelope Warp) | Potential per-Pole | Uniform (via SP Warp) |

This comparison highlights a significant trade-off. Methods leveraging existing high-level interfaces like parselmouth offer the simplest implementation path but might be constrained by the quality limitations of the underlying Praat command (PSOLA artifacts 41). Libraries like stftPitchShift provide relevant building blocks (envelope separation) but may require adaptation or lower-level usage to achieve independent formant shifting rather than just preservation. Techniques requiring more explicit DSP implementation, such as LPC pole modification or warping WORLD's spectral envelope, demand greater effort and DSP knowledge but potentially offer higher fidelity or finer control, leveraging robust underlying models (LPC 51, WORLD 63). Real-time processing capability is often linked to the underlying algorithm's suitability for frame-based or streaming operation, favoring phase vocoder variants, WORLD, and potentially well-implemented LPC.

## **VI. Recommendations and Implementation Guidance**

Based on the analysis, the following recommendations are provided, tiered by likely user priorities:

**1\. Recommendation for Ease of Implementation (Accepting Moderate Quality): parselmouth/Praat Change gender**

This is likely the quickest path to achieving the desired effect, leveraging the existing Praat functionality via Parselmouth.

* **Rationale:** The Change gender command is designed for this type of manipulation.28 Parselmouth provides a convenient Python interface.25 The primary implementation hurdle (the PraatError) is addressable.  
* **Implementation Guidance:**  
  Python  
  import parselmouth  
  import numpy as np  
  import soundfile as sf

  def formant\_shift\_praat(  
      input\_wav\_path,  
      output\_wav\_path,  
      formant\_shift\_ratio,  
      pitch\_floor=75.0,  
      pitch\_ceiling=600.0,  
      use\_external\_pitch=True \# Recommended for robustness  
  ):  
      """  
      Shifts formants using Praat's 'Change gender' command via Parselmouth.  
      Preserves original pitch median and range.  
      """  
      snd \= parselmouth.Sound(input\_wav\_path)

      \# Parameters for formant shift only  
      new\_pitch\_median \= 0.0  \# 0.0 means use original median  
      pitch\_range\_factor \= 1.0 \# 1.0 means keep original range relative to median  
      duration\_factor \= 1.0 \# 1.0 means keep original duration

      try:  
          if use\_external\_pitch:  
              \# Robust approach: Calculate Pitch object first  
              \# Praat's internal time step for Change Gender is 0.8 / pitch\_floor  
              time\_step \= 0.8 / pitch\_floor  
              pitch \= snd.to\_pitch(  
                  time\_step=time\_step,  
                  pitch\_floor=pitch\_floor,  
                  pitch\_ceiling=pitch\_ceiling  
              )  
              \# Check if pitch object is valid (contains points)  
              if parselmouth.praat.call(pitch, "Get number of points") \== 0:  
                   print(f"Warning: Pitch analysis failed for {input\_wav\_path}. Skipping.")  
                   return \# Or handle error appropriately

              modified\_snd \= parselmouth.praat.call(  
                  (snd, pitch), \# Pass both Sound and Pitch  
                  "Change gender",  
                  formant\_shift\_ratio,  
                  new\_pitch\_median,  
                  pitch\_range\_factor,  
                  duration\_factor,  
              )  
          else:  
              \# Direct approach (less robust)  
              modified\_snd \= parselmouth.praat.call(  
                  snd,  
                  "Change gender",  
                  pitch\_floor, \# Pitch analysis floor  
                  pitch\_ceiling, \# Pitch analysis ceiling  
                  formant\_shift\_ratio,  
                  new\_pitch\_median,  
                  pitch\_range\_factor,  
                  duration\_factor,  
              )

          modified\_snd.save(output\_wav\_path, parselmouth.SoundFileFormat.WAV)

      except parselmouth.PraatError as e:  
          print(f"PraatError processing {input\_wav\_path}: {e}")  
      except Exception as e:  
           print(f"An unexpected error occurred processing {input\_wav\_path}: {e}")

  \# Example Usage:  
  \# formant\_shift\_praat("input.wav", "output\_praat.wav", formant\_shift\_ratio=1.15)

* **Considerations:** Ensure Praat executable is accessible by Parselmouth. Quality is subject to PSOLA limitations.41 Not suitable for real-time processing.

**2\. Recommendation for Higher Quality / Real-time Potential (Moderate Implementation Effort): stftPitchShift or pyworldvocoder**

These approaches offer potentially higher quality and real-time capability but require more DSP coding.

* **A. stftPitchShift (Adaptation Required):**  
  * **Rationale:** The library implements the necessary phase vocoder and cepstral envelope separation.45 Real-time potential exists.  
  * **Implementation Guidance:**  
    1. Install: pip install stftpitchshift.  
    2. Explore using the library's components:  
       * Use stftpitchshift.STFT for analysis/synthesis.  
       * Use stftpitchshift.Cepster to estimate the spectral envelope from the magnitude spectrum of each frame.  
       * Warp the frequency axis of the envelope using numpy.interp. Define original\_freqs \= np.linspace(0, sr/2, num\_bins) and warped\_freqs \= original\_freqs / formant\_shift\_ratio. Then warped\_envelope \= np.interp(original\_freqs, warped\_freqs, original\_envelope). Handle edge cases where warped\_freqs go out of bounds.  
       * Obtain the original residual: Divide the original magnitude spectrum by the original envelope.  
       * Recombine: Multiply the original residual by the *warped* envelope.  
       * Use stftpitchshift.Vocoder (or manual phase reconstruction) and stftpitchshift.STFT.synthesize for the ISTFT and overlap-add.  
  * **Considerations:** This requires understanding the library's internal data structures and potentially modifying its workflow. The quality of cepstral envelope estimation and the warping process will impact the final result. Check the library's license if modification is intended.  
* **B. pyworldvocoder \+ Custom Spectral Envelope Warping:**  
  * **Rationale:** WORLD provides high-quality analysis/synthesis and explicit F0/SP separation.63 Real-time potential exists.  
  * **Implementation Guidance:**  
    1. Install pyworld and dependencies: pip install pyworld numpy scipy.  
    2. Analysis: f0, sp, ap \= pw.wav2world(x, fs).64 x should be float64 NumPy array.  
    3. Warp sp:  
       Python  
       import pyworld as pw  
       import numpy as np  
       import scipy.interpolate

       def warp\_spectral\_envelope(sp, fs, formant\_shift\_ratio):  
           num\_frames, num\_bins \= sp.shape  
           fft\_size \= (num\_bins \- 1) \* 2 \# CheapTrick uses fft\_size / 2 \+ 1 bins  
           original\_freqs \= np.linspace(0, fs / 2, num\_bins)  
           warped\_freqs \= original\_freqs / formant\_shift\_ratio

           sp\_warped \= np.zeros\_like(sp)

           for i in range(num\_frames):  
               \# Interpolate envelope of current frame  
               \# Use linear interpolation, handle extrapolation carefully (e.g., fill with edge values)  
               interp\_func \= scipy.interpolate.interp1d(  
                   warped\_freqs, sp\[i\], kind='linear', bounds\_error=False, fill\_value=(sp\[i, 0\], sp\[i, \-1\])  
               )  
               sp\_warped\[i\] \= interp\_func(original\_freqs)

           \# Ensure non-negative values (numerical precision might cause small negatives)  
           sp\_warped\[sp\_warped \< 1e-16\] \= 1e-16 \# Or a small positive floor

           return sp\_warped.astype(np.float64) \# Ensure correct dtype for synthesize

       \#... load audio x, fs...  
       f0, t \= pw.dio(x, fs)  
       f0 \= pw.stonemask(x, f0, t, fs)  
       sp \= pw.cheaptrick(x, f0, t, fs)  
       ap \= pw.d4c(x, f0, t, fs)

       sp\_warped \= warp\_spectral\_envelope(sp, fs, formant\_shift\_ratio=1.15)

       \# Ensure f0 is C-contiguous double array  
       f0\_cont \= np.ascontiguousarray(f0, dtype=np.float64)

       y \= pw.synthesize(f0\_cont, sp\_warped, ap, fs)  
       \#... save y...

  * **Considerations:** Requires careful implementation of the warp\_spectral\_envelope function. Understanding the exact frequency mapping of sp bins is important. WORLD is generally robust and high quality.

**3\. Recommendation for Maximum Control / Advanced Users: LPC Pole Modification**

This method offers direct manipulation of the vocal tract model but is the most complex to implement correctly.

* **Rationale:** Directly modifies the parameters (poles) corresponding to formants in the LPC model.49  
* **Implementation Guidance (Conceptual Outline):**  
  1. Use librosa.util.frame for framing.  
  2. For each frame:  
     * Window (e.g., numpy.hamming).  
     * Calculate autocorrelation (numpy.correlate).  
     * Calculate LPC coefficients (e.g., audiolazy.lpc(..., method='kautocor') 55 or implement Levinson-Durbin).  
     * Find roots (numpy.roots).  
     * Identify formant poles (complex pairs near unit circle, positive imaginary part).  
     * Calculate angle \= np.angle(pole), magnitude \= np.abs(pole).  
     * Calculate new\_angle \= angle \* formant\_shift\_ratio.  
     * Reconstruct new\_pole \= magnitude \* np.exp(1j \* new\_angle). Add conjugate np.conj(new\_pole). Include other non-formant poles/zeros if necessary for stability/accuracy.  
     * Get new polynomial coefficients new\_A \= numpy.poly(all\_modified\_poles).  
     * Estimate excitation (e.g., LPC residual scipy.signal.lfilter(frame, A, 1) or impulse train from F0).  
     * Synthesize frame y\_frame \= scipy.signal.lfilter(1, new\_A, excitation).  
  3. Overlap-add frames.  
* **Considerations:** Requires significant DSP expertise. Stability of the modified filter is critical. Root finding and polynomial reconstruction can be numerically sensitive. LPC model order selection impacts quality.53

**Parameter Tuning:** Regardless of the method, some parameter tuning might be necessary. Key parameters include:

* **STFT:** Window size, hop length, window type (affect time-frequency resolution).  
* **LPC:** Model order (influences how many formants are captured, typically 2 \+ fs/1000 53).  
* **Cepstral:** Lifter cutoff/quefrency (controls envelope smoothness 45).  
* **WORLD:** Parameters for dio/harvest, cheaptrick, d4c if defaults are suboptimal for the specific audio. Experimentation is often required to find optimal settings for specific voice characteristics and desired output quality.

## **VII. Conclusion**

The task of shifting formant frequencies while preserving pitch in Python requires techniques that explicitly decouple the spectral envelope (formants) from the fundamental frequency (pitch). Simple methods like direct resampling or standard phase vocoder implementations (as found in librosa.effects.pitch\_shift) inherently couple these two aspects and are unsuitable for this specific goal.

Analysis of the user's attempts confirmed these limitations. rubberband's CLI \--formant flag is for preservation during pitch shift, not independent scaling; the necessary C++ API feature (setFormantScale) lacks readily available Python bindings. librosa's internal pitch shifter scales the entire spectrum. parselmouth's PraatError with the Change gender command stems from invalid pitch analysis parameters, which can be resolved by providing valid defaults (e.g., 75 Hz floor, 600 Hz ceiling) or, more robustly, by pre-calculating and supplying a Praat Pitch object.

Viable approaches involve more sophisticated DSP techniques:

1. **parselmouth/Praat:** Using the Change gender command with appropriate parameters (median=0.0, range=1.0) offers the simplest implementation path, though quality is limited by the underlying PSOLA algorithm.  
2. **Phase Vocoder with Envelope Separation:** Techniques like those potentially adaptable from the stftPitchShift library (using cepstral liftering) separate envelope and residual, allowing the envelope to be warped before resynthesis. This requires moderate implementation effort, possibly involving lower-level use of the library's components.  
3. **LPC Pole Modification:** Directly manipulating the angles of LPC filter poles offers precise control over the vocal tract model but demands significant DSP implementation effort and careful handling of stability. Libraries like audiolazy and pysptk provide building blocks.  
4. **WORLD Vocoder:** Leveraging pyworldvocoder allows analysis into F0, Spectral Envelope (SP), and Aperiodicity (AP). Warping the frequency axis of the SP data before resynthesis offers high potential quality due to WORLD's robust decomposition, but requires custom code for the SP warping step.

The most suitable recommendation depends on the user's priorities. For rapid prototyping or where moderate quality suffices, **parselmouth/Praat Change gender (using an external Pitch object)** is the most straightforward. For potentially higher quality and real-time capability, investigating **pyworldvocoder with custom spectral envelope warping** appears promising, assuming the user is comfortable implementing the NumPy-based warping logic. Adapting **stftPitchShift** is another viable route if its components can be effectively leveraged for envelope warping. The **LPC pole modification** method remains an option for users with strong DSP backgrounds seeking maximum control over the filter model.

Future advancements in deep learning-based vocoding and voice conversion 60 may offer increasingly sophisticated and high-quality methods for such manipulations, but currently, the discussed DSP techniques provide more readily implementable solutions within standard Python libraries.

#### **Works cited**

1. Formant Analysis Frequency \- What makes a peak value?, accessed April 11, 2025, [https://dsp.stackexchange.com/questions/56138/formant-analysis-frequency-what-makes-a-peak-value](https://dsp.stackexchange.com/questions/56138/formant-analysis-frequency-what-makes-a-peak-value)  
2. Formant preservation in realtime pitch shifting · Issue \#5902 \- GitHub, accessed April 11, 2025, [https://github.com/audacity/audacity/issues/5902](https://github.com/audacity/audacity/issues/5902)  
3. Audio time stretching and pitch scaling \- Wikipedia, accessed April 11, 2025, [https://en.wikipedia.org/wiki/Audio\_time\_stretching\_and\_pitch\_scaling](https://en.wikipedia.org/wiki/Audio_time_stretching_and_pitch_scaling)  
4. Real Time Pitch Shifting with Formant Structure Preservation Using the Phase Vocoder \- ISCA Archive, accessed April 11, 2025, [https://www.isca-archive.org/interspeech\_2017/lenarczyk17\_interspeech.pdf](https://www.isca-archive.org/interspeech_2017/lenarczyk17_interspeech.pdf)  
5. What is a Phase Vocoder? How Pitch Correction Works in Music Production \- BABY Audio, accessed April 11, 2025, [https://babyaud.io/blog/phase-vocoder](https://babyaud.io/blog/phase-vocoder)  
6. Pitch-shifting algorithm design and applications in music \- DiVA portal, accessed April 11, 2025, [https://www.diva-portal.org/smash/get/diva2:1381398/FULLTEXT01.pdf](https://www.diva-portal.org/smash/get/diva2:1381398/FULLTEXT01.pdf)  
7. Pitch shifting effects on formants \- Signal Processing Stack Exchange, accessed April 11, 2025, [https://dsp.stackexchange.com/questions/91548/pitch-shifting-effects-on-formants](https://dsp.stackexchange.com/questions/91548/pitch-shifting-effects-on-formants)  
8. On the Importance Of Formants In Pitch Shifting | Stephan Bernsee's Blog \- Zynaptiq, accessed April 11, 2025, [http://blogs.zynaptiq.com/bernsee/formants-pitch-shifting/](http://blogs.zynaptiq.com/bernsee/formants-pitch-shifting/)  
9. Spectral Envelope Transformation in Singing Voice for Advanced Pitch Shifting \- MDPI, accessed April 11, 2025, [https://www.mdpi.com/2076-3417/6/11/368](https://www.mdpi.com/2076-3417/6/11/368)  
10. 12.2. Pitch Shifting \- Hydrogen, accessed April 11, 2025, [http://hydrogen-music.org/documentation/manual/manual\_en\_chunked/ch12s02.html](http://hydrogen-music.org/documentation/manual/manual_en_chunked/ch12s02.html)  
11. rubberband-cli — Debian unstable, accessed April 11, 2025, [https://manpages.debian.org/unstable/rubberband-cli/rubberband.1.en.html](https://manpages.debian.org/unstable/rubberband-cli/rubberband.1.en.html)  
12. Rubber Band Audio Time Stretcher Library \- Breakfast Quay, accessed April 11, 2025, [https://breakfastquay.com/rubberband/](https://breakfastquay.com/rubberband/)  
13. Error: Please verify that rubberband-cli is installed · Issue \#18 · bmcfee/pyrubberband, accessed April 11, 2025, [https://github.com/bmcfee/pyrubberband/issues/18](https://github.com/bmcfee/pyrubberband/issues/18)  
14. Rubber Band Library: RubberBand::RubberBandStretcher Class ..., accessed April 11, 2025, [https://breakfastquay.com/rubberband/code-doc/classRubberBand\_1\_1RubberBandStretcher.html](https://breakfastquay.com/rubberband/code-doc/classRubberBand_1_1RubberBandStretcher.html)  
15. Migrate to using librosa and librubberband for formant shifting · Issue \#37 \- GitHub, accessed April 11, 2025, [https://github.com/chxrlt/lyrebird/issues/37](https://github.com/chxrlt/lyrebird/issues/37)  
16. rubberband \- PyPI, accessed April 11, 2025, [https://pypi.org/project/rubberband/](https://pypi.org/project/rubberband/)  
17. Rubber band elasticity problem \- General Discussion \- VEX Forum, accessed April 11, 2025, [https://www.vexforum.com/t/rubber-band-elasticity-problem/122928](https://www.vexforum.com/t/rubber-band-elasticity-problem/122928)  
18. Preset settings not active after system boot or starting PulseEffects manually · Issue \#1644 · wwmm/easyeffects \- GitHub, accessed April 11, 2025, [https://github.com/wwmm/easyeffects/issues/1644](https://github.com/wwmm/easyeffects/issues/1644)  
19. Audio Signal Processing with Python's Librosa \- Elena Daehnhardt, accessed April 11, 2025, [https://daehnhardt.com/blog/2023/03/05/python-audio-signal-processing-with-librosa/](https://daehnhardt.com/blog/2023/03/05/python-audio-signal-processing-with-librosa/)  
20. librosa.effects.pitch\_shift, accessed April 11, 2025, [https://librosa.org/doc-playground/latest/generated/librosa.effects.pitch\_shift.html](https://librosa.org/doc-playground/latest/generated/librosa.effects.pitch_shift.html)  
21. librosa.effects.pitch\_shift — librosa 0.10.2 documentation, accessed April 11, 2025, [https://librosa.org/doc/0.10.2/generated/librosa.effects.pitch\_shift.html](https://librosa.org/doc/0.10.2/generated/librosa.effects.pitch_shift.html)  
22. librosa.effects.pitch\_shift — librosa 0.11.0 documentation, accessed April 11, 2025, [https://librosa.org/doc/main/generated/librosa.effects.pitch\_shift.html](https://librosa.org/doc/main/generated/librosa.effects.pitch_shift.html)  
23. How to properly use pitch\_shift (librosa)? \- Stack Overflow, accessed April 11, 2025, [https://stackoverflow.com/questions/57362543/how-to-properly-use-pitch-shift-librosa](https://stackoverflow.com/questions/57362543/how-to-properly-use-pitch-shift-librosa)  
24. API Reference — Parselmouth 0.5.0.dev0 documentation \- VUB AI-lab, accessed April 11, 2025, [https://ai.vub.ac.be/\~yajadoul/sample\_docs/api\_reference.html](https://ai.vub.ac.be/~yajadoul/sample_docs/api_reference.html)  
25. Full article: Parselmouth for bioacoustics: automated acoustic analysis in Python, accessed April 11, 2025, [https://www.tandfonline.com/doi/full/10.1080/09524622.2023.2259327](https://www.tandfonline.com/doi/full/10.1080/09524622.2023.2259327)  
26. Introducing Parselmouth: A Python interface to Praat \- MPG.PuRe, accessed April 11, 2025, [https://pure.mpg.de/rest/items/item\_2627915/component/file\_2627914/content](https://pure.mpg.de/rest/items/item_2627915/component/file_2627914/content)  
27. \[praat-users\] "Change gender" documentation improvements, accessed April 11, 2025, [https://praat-users.yahoogroups.co.narkive.com/x1topFJ4/change-gender-documentation-improvements](https://praat-users.yahoogroups.co.narkive.com/x1topFJ4/change-gender-documentation-improvements)  
28. Sound: Change gender, accessed April 11, 2025, [https://www.fon.hum.uva.nl/praat/manual/Sound\_\_Change\_gender\_\_\_.html](https://www.fon.hum.uva.nl/praat/manual/Sound__Change_gender___.html)  
29. Voice Lab Interface — VoiceLab: Automated Reproducible Acoustic Analysis, accessed April 11, 2025, [https://voice-lab.github.io/VoiceLab/](https://voice-lab.github.io/VoiceLab/)  
30. parselmouth.praat.call stuck in "Change gender" · Issue \#68 \- GitHub, accessed April 11, 2025, [https://github.com/YannickJadoul/Parselmouth/issues/68](https://github.com/YannickJadoul/Parselmouth/issues/68)  
31. processors/data\_augment.py · Svngoku/maskgct-audio-lab at 6ec52a1a191ffe5f43b63217928dbd9c8eda5129 \- Hugging Face, accessed April 11, 2025, [https://huggingface.co/spaces/Svngoku/maskgct-audio-lab/blob/6ec52a1a191ffe5f43b63217928dbd9c8eda5129/processors/data\_augment.py](https://huggingface.co/spaces/Svngoku/maskgct-audio-lab/blob/6ec52a1a191ffe5f43b63217928dbd9c8eda5129/processors/data_augment.py)  
32. Praat \- Manipulation of Pitch and Duration \- YouTube, accessed April 11, 2025, [https://www.youtube.com/watch?v=VNZlSvzHHHk](https://www.youtube.com/watch?v=VNZlSvzHHHk)  
33. Pitch manipulation and Praat commands — Parselmouth 0.4.5 documentation, accessed April 11, 2025, [https://parselmouth.readthedocs.io/en/stable/examples/pitch\_manipulation.html](https://parselmouth.readthedocs.io/en/stable/examples/pitch_manipulation.html)  
34. Pitch manipulation and Praat commands — Parselmouth 0.5.0.dev0 documentation, accessed April 11, 2025, [https://parselmouth.readthedocs.io/en/latest/examples/pitch\_manipulation.html](https://parselmouth.readthedocs.io/en/latest/examples/pitch_manipulation.html)  
35. Change pitch and formant with praat-parselmouth · Issue \#25 \- GitHub, accessed April 11, 2025, [https://github.com/YannickJadoul/Parselmouth/issues/25](https://github.com/YannickJadoul/Parselmouth/issues/25)  
36. Adding Values to Klatt Grids using Parselmouth \- Google Groups, accessed April 11, 2025, [https://groups.google.com/g/parselmouth/c/iI5ly3B2uu0](https://groups.google.com/g/parselmouth/c/iI5ly3B2uu0)  
37. Change formants \- Praat Vocal Toolkit, accessed April 11, 2025, [https://www.praatvocaltoolkit.com/change-formants.html](https://www.praatvocaltoolkit.com/change-formants.html)  
38. Is there a way to change formants using parselmouth (python PRAAT wrapper) or other python libraries? \- Stack Overflow, accessed April 11, 2025, [https://stackoverflow.com/questions/63620262/is-there-a-way-to-change-formants-using-parselmouth-python-praat-wrapper-or-ot](https://stackoverflow.com/questions/63620262/is-there-a-way-to-change-formants-using-parselmouth-python-praat-wrapper-or-ot)  
39. Scripts | SPEAC | Hans Rutger Bosker, accessed April 11, 2025, [https://hrbosker.github.io/resources/scripts/](https://hrbosker.github.io/resources/scripts/)  
40. Shift frequencies \- Praat Vocal Toolkit, accessed April 11, 2025, [https://www.praatvocaltoolkit.com/shift-frequencies.html](https://www.praatvocaltoolkit.com/shift-frequencies.html)  
41. Change pitch and formant · Issue \#18 · timmahrt/praatIO \- GitHub, accessed April 11, 2025, [https://github.com/timmahrt/praatIO/issues/18](https://github.com/timmahrt/praatIO/issues/18)  
42. PyTSMod: A Python Implementation of Time-Scale Modification Algorithms \- Sangeon Yong, accessed April 11, 2025, [https://seyong92.github.io/publications/yong\_ISMIR\_LBD\_2020.pdf](https://seyong92.github.io/publications/yong_ISMIR_LBD_2020.pdf)  
43. fft \- Preserving formants using Cepstrum \- Signal Processing Stack Exchange, accessed April 11, 2025, [https://dsp.stackexchange.com/questions/37141/preserving-formants-using-cepstrum](https://dsp.stackexchange.com/questions/37141/preserving-formants-using-cepstrum)  
44. FFT Pitch Shifting with Formant Preservation Revisited | synSinger \- WordPress.com, accessed April 11, 2025, [https://synsinger.wordpress.com/2013/03/24/fft-pitch-shifting-with-formant-preservation-revisited/](https://synsinger.wordpress.com/2013/03/24/fft-pitch-shifting-with-formant-preservation-revisited/)  
45. jurihock/stftPitchShift: STFT based real-time pitch and timbre shifting in C++ and Python, accessed April 11, 2025, [https://github.com/jurihock/stftPitchShift](https://github.com/jurihock/stftPitchShift)  
46. shiftPitch \- MathWorks, accessed April 11, 2025, [https://www.mathworks.com/help/audio/ref/shiftpitch.html](https://www.mathworks.com/help/audio/ref/shiftpitch.html)  
47. stftpitchshift \- PyPI, accessed April 11, 2025, [https://pypi.org/project/stftpitchshift/](https://pypi.org/project/stftpitchshift/)  
48. lewark/pvc: Python phase-vocoder implementation with pitch shifting and formant correction, accessed April 11, 2025, [https://github.com/lewark/pvc](https://github.com/lewark/pvc)  
49. georgiee/lip-sync-lpc: LPC, vowels, formants. A repo to save my research on this topic \- GitHub, accessed April 11, 2025, [https://github.com/georgiee/lip-sync-lpc](https://github.com/georgiee/lip-sync-lpc)  
50. Week-3, accessed April 11, 2025, [https://himani2000.github.io/gsoc/blog\_six.html](https://himani2000.github.io/gsoc/blog_six.html)  
51. LPC Formant-Shifting \- DSPRelated.com, accessed April 11, 2025, [https://www.dsprelated.com/thread/5684/lpc-formant-shifting](https://www.dsprelated.com/thread/5684/lpc-formant-shifting)  
52. Shifting formants without changing pitch? \- DSP and Plugin Development Forum \- KVR Audio, accessed April 11, 2025, [https://www.kvraudio.com/forum/viewtopic.php?t=455877](https://www.kvraudio.com/forum/viewtopic.php?t=455877)  
53. Estimate formants using LPC in Python \- Stack Overflow, accessed April 11, 2025, [https://stackoverflow.com/questions/25107806/estimate-formants-using-lpc-in-python](https://stackoverflow.com/questions/25107806/estimate-formants-using-lpc-in-python)  
54. lpc.py \- jmandel/fun-with-formants \- GitHub, accessed April 11, 2025, [https://github.com/jmandel/fun-with-formants/blob/master/lpc.py](https://github.com/jmandel/fun-with-formants/blob/master/lpc.py)  
55. audiolazy \- PyPI, accessed April 11, 2025, [https://pypi.org/project/audiolazy/](https://pypi.org/project/audiolazy/)  
56. pysptk — pysptk 0.1.21 documentation, accessed April 11, 2025, [https://pysptk.readthedocs.io/](https://pysptk.readthedocs.io/)  
57. pysptk/examples/Speech analysis and re-synthesis.ipynb at master \- GitHub, accessed April 11, 2025, [https://github.com/r9y9/pysptk/blob/master/examples/Speech%20analysis%20and%20re-synthesis.ipynb](https://github.com/r9y9/pysptk/blob/master/examples/Speech%20analysis%20and%20re-synthesis.ipynb)  
58. How to extract prosodic cues from a wav file using Python, accessed April 11, 2025, [https://dsp.stackexchange.com/questions/41115/how-to-extract-prosodic-cues-from-a-wav-file-using-python](https://dsp.stackexchange.com/questions/41115/how-to-extract-prosodic-cues-from-a-wav-file-using-python)  
59. hcy71o/LPC\_Speech\_Synthesis: Speech synthesis using LPC \- GitHub, accessed April 11, 2025, [https://github.com/hcy71o/LPC\_Speech\_Synthesis](https://github.com/hcy71o/LPC_Speech_Synthesis)  
60. Pitch-shifting, time-stretching, and vocoding of speech with Controllable LPCNet (CLPCNet) \- GitHub, accessed April 11, 2025, [https://github.com/maxrmorrison/clpcnet](https://github.com/maxrmorrison/clpcnet)  
61. Linear Predictive Coding in Python, accessed April 11, 2025, [https://www.kuniga.me/blog/2021/05/13/lpc-in-python.html](https://www.kuniga.me/blog/2021/05/13/lpc-in-python.html)  
62. r9y9/pysptk: A python wrapper for Speech Signal Processing Toolkit (SPTK). \- GitHub, accessed April 11, 2025, [https://github.com/r9y9/pysptk](https://github.com/r9y9/pysptk)  
63. pylon/world-vocoder: A high-quality speech analysis, manipulation and synthesis system \- GitHub, accessed April 11, 2025, [https://github.com/pylon/world-vocoder](https://github.com/pylon/world-vocoder)  
64. Python-Wrapper-for-World-Vocoder/README.md at master \- GitHub, accessed April 11, 2025, [https://github.com/JeremyCCHsu/Python-Wrapper-for-World-Vocoder/blob/master/README.md](https://github.com/JeremyCCHsu/Python-Wrapper-for-World-Vocoder/blob/master/README.md)  
65. Visualization of Speech data. Speech is one of the most important… | by Dr. Sandipan Dhar (Ph.D.) | Medium, accessed April 11, 2025, [https://medium.com/@sandipandhar\_6564/visualization-of-speech-data-f6504af6096c](https://medium.com/@sandipandhar_6564/visualization-of-speech-data-f6504af6096c)  
66. timmahrt/ProMo: Prososdy Morph: A python library for manipulating pitch and duration in an algorithmic way, for resynthesizing speech. \- GitHub, accessed April 11, 2025, [https://github.com/timmahrt/ProMo](https://github.com/timmahrt/ProMo)  
67. CLEESE | Ircam Forum, accessed April 11, 2025, [https://forum.ircam.fr/projects/detail/cleese/](https://forum.ircam.fr/projects/detail/cleese/)  
68. Normalization Driven Zero-Shot Multi-Speaker Speech Synthesis \- ISCA Archive, accessed April 11, 2025, [https://www.isca-archive.org/interspeech\_2021/kumar21c\_interspeech.pdf](https://www.isca-archive.org/interspeech_2021/kumar21c_interspeech.pdf)