# The Critical Four

**Rad-Lad: The Final Read.** *Four examiners. One champion. Every finding counts.*

This is an embeddable, top-down pixel-art game in the style of the 90s Pokémon games, made for the Rad-Lad website. The player is a newly graduated radiographer sitting their final assessment. Instead of battling creatures, they identify clinically urgent findings on X-rays and scrollable CT and MRI studies.

## How it plays

1. **Registration.** The player enters a name and picks one of four graduate sprites.
2. **The examination hall.** The lecturer explains the rules (and never mentions the champion), then the door at the back opens. Five classmates wait by the desks; walk up and press Space/A (or tap) to hear their nerves. One of them, Alden Vidal, has a word of encouragement.
3. **Four examiner rooms, then the champion.** Each room has its own introduction, a shared battle transition and a defeat scene:

| # | Opponent | Focus | Room | Intro | After defeat |
|---|---|---|---|---|---|
| 1 | Dominic | Chest, lines and tubes | City at night | A parody caped hero (teal suit, purple cape, domino mask, lungs on his chest). Swings down on a line, lands, points, spreads his cape and the city lights come on | Nods, swings away and reveals the door |
| 2 | Matilda | Neuro emergencies | Enchanted purple parlour: chandelier, candles, potion shelf, crystal ball, moonlit windows; four original plush fox-like creatures | Fighting stance; the four big dolls twitch their ears, turn to face you and bounce | The dolls freeze; her shoulder companion runs to the door and unlocks it |
| 3 | Hannah | Abdominal and vascular | Stone tournament ring on a grassy plain | Stomps forward, the screen shakes and cracks spread across the tiles | Opens a purple portal; you step in and the screen fades to purple |
| 4 | My-Vi | Musculoskeletal | Star chamber: constellation mural, emerald braziers, floating crystals, a glowing rune circle and drifting motes | Raises her hands and the glyphs light up one by one | The glyphs fly across the room and form a glowing doorway |
| 5 | The Lightbox | Mixed | Pitch dark except the Lightbox; after the win, the alcove lightboxes and chandeliers light up one by one, revealing a grand hall | Walk up and press A: *"What were you expecting—a radiologist?"*, then **CHAMPION LIGHTBOX** | Flickers and powers down; the lights come on, confetti falls, fanfare, and the banner **CONGRATULATIONS, RADIOGRAPHER!** |

4. **The battle.** The screen flashes, then a pixelated wipe. The graduate slides in from the left (back view) and the opponent from the right. Three hearts and six case icons appear, then each study opens in the study panel:
   - The study viewer handles single images, several views (tabs) and scrollable stacks. Scroll with the wheel, by dragging, with the slider or with ↑/↓. Zoom with Ctrl+wheel, pinch or +/−. **INV** inverts the image and **⛶** goes full screen.
   - There are four answers (shuffled each time) and you answer by clicking or tapping, or with keys 1–4.
   - **Correct:** the opponent loses a case icon ("It's super effective!"), then an explanation card shows *the finding*, *the key imaging clue* and *why it matters*, with a **Look again** option.
   - **Wrong:** you lose a heart, that option is disabled and the same study stays open.
   - **Out of hearts:** the encounter restarts with the same six studies in a new order. Rooms you've already cleared stay cleared.
   - **Victory:** your hearts are restored and progress is saved.
5. **Saving.** Progress saves after each examiner. The title screen offers **Continue** and **New game**. Markers are kept across new games.

## Markers

Markers use the Rad-Lad "Marker Unlocked" stamp animation. The **MARKERS** button in the header shows the full collection. The two Lightbox-related markers show as **???** until they're unlocked, so the champion stays a surprise.

| Marker | Unlock |
|---|---|
| The Dark Lung Rises | Defeat Dominic |
| Mind Over Matilda | Defeat Matilda |
| Go With the Flow | Defeat Hannah |
| Bone to Be Wild | Defeat My-Vi |
| Thanks for the Enlightenment *(hidden)* | Defeat the Lightbox |
| Qualified to Glow *(hidden)* | Complete the game (the marker shows the player's initials) |
| Critical Hit! | First correct answer |
| Six Appeal | Defeat any examiner without losing a heart |
| First, Do No Guessing | All 30 studies right first time. Restarting an encounter doesn't clear earlier mistakes. |
| Scroll Model | Solve a scrollable CT/MRI study on the first attempt |
| A Heartbreaking Interpretation | Lose all three hearts for the first time |
| Read Another Day | Defeat an examiner after losing to them |
| Beyond the Lightbox *(hidden entirely)* | Enter the concealed room inside the giant Easter egg |

The marker icons are first drafts drawn in code (`MARK_ART` in `game.html`).

## Files

| File | Purpose |
|---|---|
| `index.html` / `critical-four.embed.html` | Built, self-contained game. Embed this. |
| `game.html` | Source page. The build fills in its placeholders. |
| `build.py` | **The 30 cases** (questions, answers, explanations, image series), image credits and the build |
| `assets/src/` | Original images, one folder per case |
| `assets/cases/` | Generated greyscale JPEGs |

## Linked cases

Cases that share a `"group"` (with `"group_order"` 1, 2, ...) are shuffled as a single unit, so they always play back to back in order, for example one patient asked about twice (`lbx3` then `lbx4`, and `mat4` then `mat5`).

## Adding the real studies

All 30 cases are real now. The placeholder helper `ph(...)` is still in `build.py`: it draws a labelled stand-in film or fake CT stack, so a new slot can be played before its images arrive. To make a case real:

1. Put its images in `assets/src/<case id>/`. Use one file per X-ray view, and one folder of slices per CT/MRI series.
2. Replace its `ph(...)` line with a full entry:

```python
{
    "id": "dom1", "opponent": "dominic", "modality": "X-ray", "label": "Chest X-ray, PA",
    "history": "Sudden breathlessness after a fall.",
    "question": "What is the urgent finding?",
    "options": ["Right tension pneumothorax", "Right pleural effusion", "Left lower lobe collapse", "Normal study"],
    "answer": 0,                       # index into options; the game shuffles the order on screen
    "finding": "...", "clue": "...", "why": "...",
    "series": [{"label": "PA", "file": "dom1/pa.png"}],
    "source": None,                    # or a key into SOURCES for the image credit
},
```

   For CT/MRI, list the series in viewing order. Slices load in natural filename order. Add `"reverse": True` if a stack runs the wrong way:

```python
    "series": [{"label": "Axial", "dir": "mat1/axial"}, {"label": "Coronal", "dir": "mat1/coronal"}],
```

   A case can also have a **reveal**: more images shown after a correct answer, while the examiner explains them line by line (see `myv3`, where the lateral shows the pronator quadratus fat pad sign and the AP reveal shows the fracture):

```python
    "reveal": {"series": [{"label": "AP", "file": "myv3/ap.png"}],
               "lines": ["Now look at the AP view...", "..."]},
```

   A single-image series can carry an `"overlay"`: a white-on-black mask, framed the same as the image (see `dom1`). It's drawn as a red fill with a gold edge, the same look as Pneumo Patrol, and the player can switch it on and off with the **OVERLAY** button.

   Images with coloured annotation, such as a red arrow, are kept in colour. Everything else is converted to greyscale.

3. Run `python build.py`. It checks that every opponent has six cases and every case has four options and a valid answer. `python build.py --preview` writes `_preview.html`, which loads images from `assets/` for quicker local testing.

## Cases so far

| Case | Opponent | Study | Answer | Images |
|---|---|---|---|---|
| dom1 | Dominic | Chest X-ray, PA (marked view with the pneumothorax overlay shown after a correct answer) | Right pneumothorax | PTX-498 (Wang 2021), [Zenodo](https://doi.org/10.5281/zenodo.8266529), CC BY 4.0 |
| dom2 | Dominic | Chest X-ray panel with the original red arrows as a hint (the coronal CT panel is shown after a correct answer) | Pneumomediastinum (plus a small right interlobar pneumothorax on CT) | Adapted from Hellerhoff (2015), [Mediastinalemphysem - Roe vs CT LF](https://commons.wikimedia.org/wiki/File:Mediastinalemphysem_-_Roe_vs_CT_LF.jpg), Wikimedia Commons, CC BY-SA 3.0. The original was split into its two panels, shared under the same licence; the original and both panels can be downloaded from the credit. |
| dom3 | Dominic | Ward AP chest X-ray, clean (the original annotated version is shown after a correct answer) | Endotracheal tube in the right main bronchus, poorly aerated left lung | Hellerhoff (2022), [clean](https://commons.wikimedia.org/wiki/File:Tubusspitze_im_rechten_Hauptbronchus_64W_-_CR_ap_-_001.jpg) and [annotated](https://commons.wikimedia.org/wiki/File:Tubusspitze_im_rechten_Hauptbronchus_64W_-_CR_ap_-_001_-_Annotation.jpg) versions, Wikimedia Commons, CC BY-SA 4.0 |
| dom4 | Dominic | Child's AP chest X-ray with the authors' red line and blue arrows digitally removed (the annotated original is shown after a correct answer) | Right tension pneumothorax with mediastinal shift to the left | Adapted from Tritsch Z, Galan G, Oates G (2021), Case Report: Traumatic Tension Pneumothorax in a Pediatric Patient, J Educ Teach Emerg Med 6(1), [doi:10.5070/M561051823](https://doi.org/10.5070/M561051823), CC BY 4.0 |
| dom5 | Dominic | Child's chest and upper abdomen AP, red arrow digitally removed (the original arrowed image is shown after a correct answer) | Ingested button battery, in the stomach just below the left hemidiaphragm | Adapted from Doc James (2024), [ButtonBatteryIngestion](https://commons.wikimedia.org/wiki/File:ButtonBatteryIngestion.png), Wikimedia Commons, CC BY-SA 4.0. The arrow-removed version is shared under the same licence; both images can be downloaded from the credit. |
| dom6 | Dominic | Child's neck X-ray, AP (halo) and lateral (step-off), with the authors' annotations | A trick: two coins stuck together (coin stack) mimicking a button battery | Ware PJ et al. (2026), A Case Report of a Coin Stack Masquerading as a Button Battery, J Educ Teach Emerg Med 11(3):V31-V34, [doi:10.5070/M5.53886](https://doi.org/10.5070/M5.53886), CC BY 4.0 |
| mat3 | Matilda | CT head, non-contrast (the labelled illustration is shown after a correct answer) | Acute intracerebral haemorrhage | Adapted from OpenStax College (2013), [1602 The Hemorrhagic Stroke-02](https://commons.wikimedia.org/wiki/File:1602_The_Hemorrhagic_Stroke-02.jpg), Anatomy & Physiology, Wikimedia Commons, CC BY 3.0. The two panels were split and the labels cropped; the original and both panels can be downloaded from the credit. |
| mat4 | Matilda | CT head, one axial slice with only the black circle kept (first of a linked pair) | Haemorrhagic frontal contusions | Adapted from Basit J, Javed S, Shahzad F, Yaqoob E, Saeed S, Anand A (2023), Coexistence of ipsilateral acute-on-chronic subdural hematoma and acute extradural hematoma: A case report, Clin Case Rep 11(7):e7684, Figure 1, [doi:10.1002/ccr3.7684](https://doi.org/10.1002/ccr3.7684), CC BY 4.0. The other arrows and circle were digitally removed. |
| mat5 | Matilda | Same slice with only the red circle kept (second of the pair; the fully labelled original is shown after a correct answer) | Acute extradural haematoma (with an acute-on-chronic subdural in front of it) | Same article and figure, CC BY 4.0 |
| mat6 | Matilda | MRI lumbar spine, sagittal fat-suppressed T2 | Cauda equina syndrome from an epidural abscess | Chan, J., Oh, J.J. (2016). A rare case of multiple spinal epidural abscesses and cauda equina syndrome presenting to the emergency department following acupuncture. Int J Emerg Med 9, 22. [doi:10.1186/s12245-016-0116-5](https://doi.org/10.1186/s12245-016-0116-5), CC BY 4.0 |
| han1 | Hannah | Supine abdominal X-ray (original yellow arrow kept) | Large bowel obstruction | James Heilman, MD, [LargeBowelObsFlat2008](https://commons.wikimedia.org/wiki/File:LargeBowelObsFlat2008.jpg), Wikimedia Commons, CC BY-SA 3.0 |
| han2 | Hannah | **image 23**: non-contrast CT KUB, single axial image (stones outlined after a correct answer) | Left renal calculi, plus a tiny right renal stone | Abdalla, Mahmood & Hama (2025), Axial CT Imaging Dataset for AI-Powered Kidney Stone Detection, [Mendeley Data V1](https://doi.org/10.17632/fwhytt5mzd.1), CC BY 4.0. The outline is drawn for the game (bright pixels inside each kidney), not supplied with the dataset. |
| han3 | Hannah | **patient 7**: CT pulmonary angiogram, 99 scrollable 2 mm axial slabs (clots shaded after a correct answer) | Bilateral pulmonary emboli, including a large clot in the right pulmonary artery | FUMPE, Patient 7 (Masoudi & Saadatmand-Tarzjan 2018), [figshare collection](https://doi.org/10.6084/m9.figshare.c.4107803.v1), CC BY 4.0. The overlay is the dataset's radiologist ground truth (`PAT007.mat`, read with `tools/prep_ct_stack.py --mat`). |
| han5 | Hannah | Supine abdominal X-ray (axial and sagittal CT shown after a correct answer) | Sigmoid volvulus (coffee bean, whirl and bird's beak signs) | Adapted from Yigit M, Turkdogan KA (2014), Pan Afr Med J 19:56, Figure 1, [doi:10.11604/pamj.2014.19.56.5142](https://doi.org/10.11604/pamj.2014.19.56.5142), CC BY 2.0. Split into its panels with the letters removed. |
| han4 | Hannah | **patient 4**: CT aortogram, 144 scrollable 3 mm axial slabs (aorta shaded after a correct answer) | Stanford type A aortic dissection | AortaSeg-60, Dissec_04 (El Rahal, Rotzinger & Fahrni 2026), [Zenodo](https://doi.org/10.5281/zenodo.18147026), CC0 1.0. Made with `tools/prep_ct_stack.py`. The overlay is the dataset's TotalSegmentator aorta mask, not the flap. |
| han6 | Hannah | CT abdomen, portal venous (the oral-contrast scan is added after a correct answer) | Large pneumoperitoneum (idiopathic, managed conservatively in the source) | Liu Y, Auld M, Stieler G (2026), The Silent Abdomen: The Conservative Management of Large Idiopathic Pneumoperitoneum, Cureus 18(5):e109171, Figures 1 and 3, [doi:10.7759/cureus.109171](https://doi.org/10.7759/cureus.109171), CC BY 4.0 |
| mat1 | Matilda | MRI brain, scrollable DWI + FLAIR (72 axial slices; lesion shaded after a correct answer) | Acute left MCA territory infarct | ISLES 2022, sub-strokecase0003 (Hernandez Petzsche et al. 2022), [Zenodo](https://doi.org/10.5281/zenodo.7153326), CC BY 4.0. FLAIR resampled onto the DWI planes with `tools/prep_mr_stack.py`. ADC not used. |
| mat2 | Matilda | **patient 0004**: MRI brain, scrollable T1, T1+C, T2, FLAIR, SWI and DWI (all 155 axial slices each; tumour shaded after a correct answer) | High-grade glioma: glioblastoma, IDH-wildtype, WHO grade 4 (from the collection's clinical metadata) | Calabrese et al. (2022), UCSF-PDGM (Version 5), The Cancer Imaging Archive, [doi:10.7937/tcia.bdgf-8v37](https://doi.org/10.7937/tcia.bdgf-8v37), CC BY 4.0 |
| lbx1 | The Lightbox | CT cervical spine, axial (C1) and coronal tabs, with the authors' arrows | Jefferson fracture (C1 burst) | Martinez-Romo MA, McCoy CE (2021), Jefferson Fracture and the Classification System for Atlas Fractures, J Educ Teach Emerg Med 6(2):V16-V19, Figures 1 and 3, [doi:10.21980/J88P9C](https://doi.org/10.21980/J88P9C), CC BY 4.0 |
| lbx2 | The Lightbox | Infant skull, lateral, arrow digitally removed (the original arrowed image is shown after a correct answer) | Depressed skull fracture | National Institutes of Health, [Skull Fracture.jpg](https://commons.wikimedia.org/wiki/File:Skull_Fracture.jpg), Wikimedia Commons, public domain (no attribution required; listed so it can be traced). |
| myv6 | My-Vi | Right hand PA with the original arrow; the player names the fracture | Boxer's fracture (fifth metacarpal neck) | Madushani Rodrigo (2024), [Bone Fracture Multi-Region X-ray Data](https://www.kaggle.com/datasets/bmadushanirodrigo/fracture-multi-region-x-ray-data), Kaggle, ODC PDDL 1.0 (public domain; listed for traceability). |
| myv1 | My-Vi | Right ankle mortise with the original arrow; the player classifies the fracture | Weber A (below the joint) | Surmanowicz et al. (2025), Diagnostics 15(16):2085, Figure 1, [doi:10.3390/diagnostics15162085](https://doi.org/10.3390/diagnostics15162085), CC BY 4.0 |
| myv5 | My-Vi | Right ankle mortise with the original arrow; the player classifies the fracture | Weber B (at the joint) | Same article, Figure 2, CC BY 4.0 |
| lbx3 | The Lightbox | Ventilated patient's portable chest X-ray (first of a linked pair) | Large (total) left pneumothorax | Voucharas C, Tagarakis G, Vouchara A (2024), Cureus 16(2):e55236, Figure 2, [doi:10.7759/cureus.55236](https://doi.org/10.7759/cureus.55236), CC BY 4.0 |
| lbx4 | The Lightbox | Same patient after the chest drain (second of the pair; the corrected film is added after a correct answer) | Endotracheal tube too low, past the carina, so the left lung collapsed | Same article, Figures 3 and 4 |
| lbx5 | The Lightbox | CT pelvis and hips, coronal and axial tabs; the authors' arrows digitally removed from the axial (the arrowed original is shown after a correct answer) | Bilateral femoral neck fractures (3-part on the right) | Sahan I, De Deken J, Anagnostakos K (2019), Bilateral Femoral Neck Fracture in a Postpartum Woman: Beware of the Risk Factors, Case Rep Orthop 2019:4134351, Figure 2, [doi:10.1155/2019/4134351](https://doi.org/10.1155/2019/4134351), CC BY 4.0 |
| lbx6 | The Lightbox | CT cervical spine, sagittal and coronal tabs; the authors' red arrow digitally removed from the sagittal (the arrowed original is shown after a correct answer) | Odontoid fracture, type II (with atlantoaxial dislocation) | Budhi AT et al. (2020), Traumatic Atlantoaxial Dislocation with Type II Odontoid Fractures: A Case Report, Ethiop J Health Sci 30(6):1047-1050, Figure 2, [doi:10.4314/ejhs.v30i6.25](https://doi.org/10.4314/ejhs.v30i6.25), CC BY 4.0 |
| myv2 | My-Vi | **patient 3**: knee, horizontal-beam lateral, arrow removed (the original arrowed image is shown after a correct answer) | Lipohaemarthrosis (fat-fluid level) | Adapted from James Heilman, MD (2011), [Lipohemarthrosis](https://commons.wikimedia.org/wiki/File:Lipohemarthrosis.png), Wikimedia Commons, CC BY-SA 3.0. The adaptation (arrow removed) is shared under the same licence, and both images can be downloaded from the credit. |
| myv3 | My-Vi | Wrist, lateral (AP shown after a correct answer) | Pronator quadratus fat pad sign (undisplaced intra-articular distal radius fracture) | Hellerhoff, Wikimedia Commons, CC BY-SA 3.0 ([lateral](https://commons.wikimedia.org/wiki/File:Pronator_quadratus_-_fatpad-sign_pathologisch_bei_Fraktur_Erwachsener.png), [AP](https://commons.wikimedia.org/wiki/File:Distale_Radiusfraktur_laengs_zu_Fatpadsign_erwachsen.png)) |
| myv4 | My-Vi | Ankle, lateral (lateral and AP with the fracture outlined, shown after a correct answer) | Distal fibula fracture | FracAtlas IMG0002348 (lateral) and IMG0002347 (AP), Abedeen et al. 2023, [figshare](https://doi.org/10.6084/m9.figshare.22363012), CC BY 4.0. The overlay is the dataset's own fracture outline. |

Each study's image credit sits in a closed **Image credit & licence** drop-down (so a title like "Lipohemarthrosis" can't give the answer away). It's the study's own full credit (marked "Adapted from:" with the adaptations listed when we changed the image, plus download links where a case lists `downloads`) while it's on screen: under the answers, on the explanation card and in the page footer. Outside a battle, the footer just says credits are shown with each study. Both files are CC BY-SA 3.0, so the converted copies in `assets/cases/` stay under that licence.

## After the credits (spoilers)

Once the Champion is beaten, the hall can be explored, and the title screen's **Continue** returns to it.
1. **The switch:** a small switch box on a post just right of the Lightbox's podium. It looks like the Lightbox's own on/off switch, and it's visible from the start, but it only does anything after the Champion is beaten. Walk up and press Space/A, or tap it. No hint is shown.
2. **The passage:** a doorway opens in the left wall, between the two pillars, and leads to a vast hidden chamber with a giant decorated Easter egg and a thank-you plaque.
3. **The egg:** walk to the door at its base. Inside, the hooded **Altrad** fades in (his illustration, `assets/src/art/altrad_source.webp`, fades in behind the dialogue), says "No, not yet." and "Soon.", then fades away. A thank-you card follows.
4. **Beyond the Lightbox:** a hidden marker for entering the egg. It doesn't appear in the Markers menu at all until it's unlocked.

## Battle art

The examiners' battle sprites come from the character sheets in `assets/src/art/`. `python tools/cut_poses.py` cuts the **challenge**, **attack** and **defeat** poses out of each sheet into `assets/art/`, and the build embeds them.
- **Challenge:** standing in battle.
- **Attack:** while each new study is sent out, when you run out of hearts, and as a quick cut-in across the study panel when you lose a heart.
- **Defeat:** after their last study.

The player's graduate uses `assets/src/art/grad_sheet.webp`: one back-view panel per look (01 short brown, 02 blonde ponytail, 03 dark curly, 04 copper), cut to `grad_0`–`grad_3` and matched to the look chosen at registration. The registration screen shows them too. The Lightbox has no sheet, so it stays pixel art. The characters in the rooms are still the small pixel sprites.

A case can carry `"patient": "patient 4"`, which shows as a small heading above the study.

## Scrollable CT from DICOM

`tools/prep_ct_stack.py` averages a thin-slice CT into slabs (3 mm by default), windows it (600/150 for CTA), limits it to the labelled structure plus a margin, and writes per-slice masks from a matching SEG series.

## Scrollable MR from DICOM

`tools/prep_mr_stack.py` turns a DICOM MR case into slice images. It resamples every series, and the lesion mask, onto the reference series' axial planes, crops to the head and windows to 8-bit:

```bash
python tools/prep_mr_stack.py "<case folder>" assets/src/<id> --ref DWI --series DWI FLAIR --mask Lesion_Mask
```

The series then scroll in step: switching tabs keeps the same slice. Use `overlay_dir` for the per-slice masks and `start` for the slice the reveal opens on (see `mat1`).

## Testing shortcut

Add `?jump=dominic` (or `hall`, `matilda`, `hannah`, `myvi`, `lightbox`) to the URL to start in that room. This overwrites the saved progress in that browser.

## Controls

Arrow keys or WASD to move, Space/Enter/Z to talk or advance, 1–4 to answer, ↑/↓ to scroll slices. On touch screens there's a D-pad with A/B buttons, and you can tap to walk.

## Still to come

- The 30 clinical studies: images, four answer choices, the verified correct answer, explanations and series order
- Final marker designs and character appearances
- Optional: the lecturer and examiners joining the final celebration

Educational use only; not for clinical decisions.
