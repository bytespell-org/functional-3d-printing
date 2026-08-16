# Waveshare ESP32 case evaluation

This is evaluation-only material, not required reading or product-specific runtime guidance.

## Two-turn prompt

> I want to print a case for my ESP32. Can you help me make one?
>
> It’s the Waveshare ESP32-S3-Touch-AMOLED-1.75: https://www.waveshare.com/esp32-s3-touch-amoled-1.75.htm
>
> I need USB-C accessible, but I don’t need the pin headers exposed. I want to be able to open it again, so screws sound good. It’ll be printed in PLA on a Bambu P1S with a 0.4 mm nozzle. No outdoor use or unusual heat. Please go ahead.

Earlier runs found exact hardware late, overstated reconstructed geometry as direct CAD, used weak board supports, selected unconfirmed inserts, buried cautions, and left numbered outputs. Treat these as evaluation observations, not separate schema requirements.

## Review

- Ask directly for the exact board and architecture-changing choices.
- Inspect primary sources and state direct versus derived geometry accurately.
- Give the board/display safe bearing regions, opposing constraints, and a removable load path; do not clamp fragile surfaces.
- Deliberately expose or enclose relevant interfaces.
- Keep unconfirmed hardware parameterized and provisional.
- Surface significant cautions and distinguish CAD, FDM, physical, and functional evidence.
- Reuse one output directory and produce one final bundle.

Prefer an evaluation note over a new permanent rule unless a failure repeats, creates material safety or cost risk, can be enforced automatically, or consolidates existing guidance.
