# Frame handoff contract

Use generated frames for a rare, memorable sequence—not routine buttons, lists, or navigation.

## Prompt template to send the user

```text
Create [COUNT] sequential UI art frames for [MOMENT].

Canvas: [WIDTH]×[HEIGHT], [ASPECT RATIO], [PNG/WebP], [transparent/solid BACKGROUND].
Camera and composition: [LOCKED CAMERA + SUBJECT POSITION].
Must remain identical in every frame: [LIST].
Only change between frames: [PRECISE DELTA].

Frame 01: [STATE]
Frame 02: [STATE]
...
Frame NN: [STATE]

Visual direction: [PALETTE, MATERIAL, LIGHT, TEXTURE].
Do not include: text, logos, watermarks, camera drift, changing proportions, extra objects, or background flicker.
Name files: [PREFIX]-01.png through [PREFIX]-NN.png.
```

## Integration

- Inspect every returned frame for size, alignment, and continuity before coding.
- Prefer an image sequence or crossfade driven by one Motion value; do not animate layout around it.
- Preload the first useful frames and lazy-load the remainder.
- Set an explicit transfer and decoded-memory budget before accepting a long sequence; reduce resolution, frame count, or format when it exceeds that budget.
- Map scroll or time monotonically; never make a functional control depend on completing the sequence.
- Use the clearest representative frame when reduced motion is requested.
- Provide meaningful alternative text for content-bearing imagery; mark pure atmosphere decorative.
